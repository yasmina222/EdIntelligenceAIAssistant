"""
School Research Assistant - Data Loader
========================================
UPDATED: Now loads and MERGES two CSV files:
1. Financial data (government benchmarking) - spending figures
2. GIAS data (school contacts) - headteacher, phone, address, website

Both files are linked by URN (Unique Reference Number)
"""

import csv
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from models_v2 import (
    School, 
    Contact, 
    ContactRole, 
    FinancialData, 
    OfstedData
)
from config_v2 import (
    DATA_SOURCE, 
    CSV_FILE_PATH_FINANCIAL, 
    CSV_FILE_PATH_GIAS,
    DATABRICKS_CONFIG
)

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Loads and merges school data from two CSV sources:
    - Financial CSV: Spending data from government benchmarking tool
    - GIAS CSV: Contact details (headteacher, phone, address, etc.)
    
    Both are merged using URN as the common key.
    """
    
    def __init__(self, source: str = None):
        self.source = source or DATA_SOURCE
        self._schools_cache: Optional[List[School]] = None
        self._schools_by_name: Dict[str, School] = {}
        self._schools_by_urn: Dict[str, School] = {}
        
        logger.info(f"📚 DataLoader initialized with source: {self.source}")
    
    def load(self) -> List[School]:
        """Load all schools from the data source."""
        if self._schools_cache is not None:
            logger.info(f"📦 Returning {len(self._schools_cache)} cached schools")
            return self._schools_cache
        
        if self.source == "csv":
            schools = self._load_and_merge_csvs()
        elif self.source == "databricks":
            schools = self._load_from_databricks()
        else:
            raise ValueError(f"Unknown data source: {self.source}")
        
        # Build lookup indexes
        self._schools_cache = schools
        self._schools_by_name = {s.school_name: s for s in schools}
        self._schools_by_urn = {s.urn: s for s in schools}
        
        logger.info(f"✅ Loaded {len(schools)} schools from {self.source}")
        return schools
    
    def _find_csv_file(self, csv_path: str) -> Optional[Path]:
        """Find a CSV file, trying multiple possible locations"""
        possible_paths = [
            csv_path,
            Path(__file__).parent / csv_path,
            Path(__file__).parent / "data" / Path(csv_path).name,
            f"data/{Path(csv_path).name}",
            Path(csv_path).name,
        ]
        
        for path in possible_paths:
            p = Path(path)
            if p.exists():
                return p
        
        return None
    
    def _load_and_merge_csvs(self) -> List[School]:
        """
        Load both CSV files and merge them on URN.
        
        Strategy:
        1. Load GIAS data first (has contact details)
        2. Load Financial data
        3. Merge: GIAS provides base school info, Financial adds spending data
        """
        schools = []
        
        # Step 1: Load GIAS data (contacts, addresses, etc.)
        gias_data = self._load_gias_csv()
        logger.info(f"📖 Loaded {len(gias_data)} schools from GIAS")
        
        # Step 2: Load Financial data
        financial_data = self._load_financial_csv()
        logger.info(f"💰 Loaded {len(financial_data)} schools from Financial data")
        
        # Step 3: Merge on URN
        # Use GIAS as the base (it has better contact info)
        # Add financial data where available
        
        all_urns = set(gias_data.keys()) | set(financial_data.keys())
        logger.info(f"🔗 Merging {len(all_urns)} unique schools")
        
        for urn in all_urns:
            gias = gias_data.get(urn, {})
            fin = financial_data.get(urn, {})
            
            # Merge the two dictionaries (GIAS takes priority for contact info)
            merged = {**fin, **gias}  # gias overwrites fin where both exist
            
            # But keep financial data for spending fields
            if fin:
                merged['_financial'] = fin
            
            try:
                school = self._merged_row_to_school(merged, urn)
                if school:
                    schools.append(school)
            except Exception as e:
                logger.warning(f"⚠️ Error creating school {urn}: {e}")
                continue
        
        return schools
    
    def _load_gias_csv(self) -> Dict[str, Dict]:
        """Load GIAS CSV and return dict keyed by URN"""
        gias_path = self._find_csv_file(CSV_FILE_PATH_GIAS)
        
        if not gias_path:
            logger.warning(f"⚠️ GIAS CSV not found: {CSV_FILE_PATH_GIAS}")
            return {}
        
        logger.info(f"📖 Reading GIAS from: {gias_path}")
        
        data = {}
        with open(gias_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                urn = self._clean_urn(row.get('urn') or row.get('URN'))
                if urn:
                    data[urn] = row
        
        return data
    
    def _load_financial_csv(self) -> Dict[str, Dict]:
        """Load Financial CSV and return dict keyed by URN"""
        fin_path = self._find_csv_file(CSV_FILE_PATH_FINANCIAL)
        
        if not fin_path:
            logger.warning(f"⚠️ Financial CSV not found: {CSV_FILE_PATH_FINANCIAL}")
            return {}
        
        logger.info(f"💰 Reading Financial data from: {fin_path}")
        
        data = {}
        with open(fin_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip failed rows
                if row.get('status') and row.get('status') != 'success':
                    continue
                    
                urn = self._clean_urn(row.get('URN') or row.get('urn'))
                if urn:
                    data[urn] = row
        
        return data
    
    def _clean_urn(self, urn) -> Optional[str]:
        """Clean and standardize URN format"""
        if urn is None or urn == '' or str(urn).lower() == 'nan':
            return None
        try:
            return str(int(float(urn)))
        except (ValueError, TypeError):
            return str(urn).strip()
    
    def _safe_float(self, value) -> Optional[float]:
        """Safely convert a value to float"""
        if value is None or value == '' or str(value).lower() == 'nan':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_int(self, value) -> Optional[int]:
        """Safely convert a value to int"""
        if value is None or value == '' or str(value).lower() == 'nan':
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _get_value(self, row: Dict[str, Any], *keys) -> Optional[str]:
        """Get value from row, trying multiple possible column names"""
        for key in keys:
            value = row.get(key)
            if value is not None and value != '' and str(value).lower() != 'nan':
                return str(value).strip()
        return None
    
    def _clean_phone(self, phone) -> Optional[str]:
        """Clean phone number format"""
        if phone is None:
            return None
        phone = str(phone).strip()
        
        # Remove .0 from float conversion
        if phone.endswith('.0'):
            phone = phone[:-2]
        
        # Format UK phone numbers
        if phone.startswith('20') and len(phone) == 10:
            phone = f"020 {phone[2:6]} {phone[6:]}"
        elif phone.startswith('2') and len(phone) == 10:
            phone = f"020 {phone[1:5]} {phone[5:]}"
        
        return phone if phone else None
    
    def _merged_row_to_school(self, row: Dict[str, Any], urn: str) -> Optional[School]:
        """
        Convert a merged row (GIAS + Financial) to a School object.
        """
        # Get school name - prefer GIAS
        school_name = self._get_value(
            row, 
            'school_name',      # GIAS
            'SchoolName',       # Financial
            'school_name_gias'
        ) or f"School {urn}"
        
        # Get Local Authority name
        la_name = self._get_value(
            row, 
            'la_name',          # GIAS
            'LAName',           # Financial
            'la_name_gias'
        )
        
        # Get school type and phase - prefer GIAS
        school_type = self._get_value(row, 'school_type', 'SchoolType')
        phase = self._get_value(row, 'phase', 'Phase')
        
        # Get pupil count
        pupil_count = self._safe_int(
            row.get('pupil_count') or row.get('TotalPupils')
        )
        
        # Get contact details from GIAS
        phone = self._clean_phone(row.get('phone'))
        website = self._get_value(row, 'website')
        
        # Build headteacher contact from GIAS data
        headteacher = None
        head_title = self._get_value(row, 'head_title')
        head_first = self._get_value(row, 'head_first_name')
        head_last = self._get_value(row, 'head_last_name')
        head_full = self._get_value(row, 'headteacher')
        
        if head_full or (head_first and head_last):
            full_name = head_full or f"{head_title or ''} {head_first or ''} {head_last or ''}".strip()
            headteacher = Contact(
                full_name=full_name,
                role=ContactRole.HEADTEACHER,
                title=head_title,
                first_name=head_first,
                last_name=head_last,
                phone=phone,
                confidence_score=1.0
            )
        
        # Build financial data from Financial CSV
        fin = row.get('_financial', row)  # Use _financial if available, else row
        
        financial = FinancialData(
            total_expenditure=self._safe_float(
                fin.get('TotalExpenditure') or fin.get('total_expenditure')
            ),
            total_pupils=self._safe_float(
                fin.get('TotalPupils') or row.get('pupil_count')
            ),
            total_teaching_support_costs=self._safe_float(
                fin.get('TotalTeachingSupportStaffCosts') or fin.get('total_teaching_support_costs')
            ),
            teaching_staff_costs=self._safe_float(
                fin.get('TeachingStaffCosts') or fin.get('teaching_staff_costs')
            ),
            supply_teaching_costs=self._safe_float(
                fin.get('SupplyTeachingStaffCosts') or fin.get('supply_teaching_costs')
            ),
            agency_supply_costs=self._safe_float(
                fin.get('AgencySupplyTeachingStaffCosts') or fin.get('agency_supply_costs')
            ),
            educational_support_costs=self._safe_float(
                fin.get('EducationSupportStaffCosts') or fin.get('educational_support_costs')
            ),
            educational_consultancy_costs=self._safe_float(
                fin.get('EducationalConsultancyCosts') or fin.get('educational_consultancy_costs')
            ),
        )
        
        # Get address from GIAS
        address_1 = self._get_value(row, 'address_1')
        address_2 = self._get_value(row, 'address_2')
        address_3 = self._get_value(row, 'address_3')
        town = self._get_value(row, 'town')
        county = self._get_value(row, 'county')
        postcode = self._get_value(row, 'postcode')
        
        # Get trust info
        trust_code = self._get_value(row, 'trust_code')
        trust_name = self._get_value(row, 'trust_name')
        
        # Create school object
        school = School(
            urn=urn,
            school_name=school_name,
            la_name=la_name,
            school_type=school_type,
            phase=phase,
            address_1=address_1,
            address_2=address_2,
            address_3=address_3,
            town=town,
            county=county,
            postcode=postcode,
            phone=phone,
            website=website,
            trust_code=trust_code,
            trust_name=trust_name,
            pupil_count=pupil_count,
            headteacher=headteacher,
            contacts=[headteacher] if headteacher else [],
            financial=financial,
            data_source="csv_merged"
        )
        
        return school
    
    def _load_from_databricks(self) -> List[School]:
        """Databricks connection - placeholder for future"""
        logger.warning("⚠️ Databricks connection not yet implemented")
        return self._load_and_merge_csvs()
    
    
    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================
    
    def get_all_schools(self) -> List[School]:
        """Get all schools from the data source."""
        return self.load()
    
    def get_school_names(self) -> List[str]:
        """Get list of all school names (for dropdown)."""
        schools = self.load()
        return sorted([s.school_name for s in schools])
    
    def get_school_by_name(self, name: str) -> Optional[School]:
        """Get a school by its name."""
        self.load()
        return self._schools_by_name.get(name)
    
    def get_school_by_urn(self, urn: str) -> Optional[School]:
        """Get a school by its URN."""
        self.load()
        # Try both with and without leading zeros
        clean_urn = self._clean_urn(urn)
        return self._schools_by_urn.get(clean_urn)
    
    def search_schools(self, query: str) -> List[School]:
        """Search schools by name."""
        schools = self.load()
        query_lower = query.lower()
        return [s for s in schools if query_lower in s.school_name.lower()]
    
    def get_schools_by_priority(self, priority: str) -> List[School]:
        """Get schools by sales priority level."""
        schools = self.load()
        return [s for s in schools if s.get_sales_priority() == priority]
    
    def get_schools_by_borough(self, borough: str) -> List[School]:
        """Get schools by local authority/borough."""
        schools = self.load()
        return [s for s in schools if s.la_name and s.la_name.lower() == borough.lower()]
    
    def get_schools_with_staffing_spend(self, min_spend: float = 0) -> List[School]:
        """
        Get schools that have staffing spend data.
        
        Args:
            min_spend: Minimum total staffing spend to filter by
        """
        schools = self.load()
        return [
            s for s in schools 
            if s.financial and s.financial.total_teaching_support_costs 
            and s.financial.total_teaching_support_costs > min_spend
        ]
    
    def get_schools_with_agency_spend(self, min_spend: float = 0) -> List[School]:
        """
        Get schools that spend on agency staff.
        
        Args:
            min_spend: Minimum agency spend to filter by (default 0 = any spend)
        """
        schools = self.load()
        return [
            s for s in schools 
            if s.financial and s.financial.agency_supply_costs 
            and s.financial.agency_supply_costs > min_spend
        ]
    
    def get_top_spenders(self, limit: int = 20, spend_type: str = "total") -> List[School]:
        """
        Get schools with highest spending.
        
        Args:
            limit: Number of schools to return
            spend_type: "total" for total staffing, "agency" for agency only
        """
        schools = self.load()
        
        if spend_type == "agency":
            schools_with_spend = [s for s in schools if s.financial and s.financial.agency_supply_costs]
            return sorted(
                schools_with_spend,
                key=lambda s: s.financial.agency_supply_costs or 0,
                reverse=True
            )[:limit]
        else:
            schools_with_spend = [s for s in schools if s.financial and s.financial.total_teaching_support_costs]
            return sorted(
                schools_with_spend,
                key=lambda s: s.financial.total_teaching_support_costs or 0,
                reverse=True
            )[:limit]
    
    def get_top_agency_spenders(self, limit: int = 20) -> List[School]:
        """Get schools with highest agency spend (backwards compatibility)."""
        return self.get_top_spenders(limit=limit, spend_type="agency")
    
    def get_boroughs(self) -> List[str]:
        """Get list of all boroughs/Local Authorities in the data."""
        schools = self.load()
        boroughs = set(s.la_name for s in schools if s.la_name)
        return sorted(list(boroughs))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get summary statistics about the loaded data."""
        schools = self.load()
        
        # Calculate total staffing spend
        total_staffing_spend = sum(
            s.financial.total_teaching_support_costs or 0 
            for s in schools 
            if s.financial
        )
        
        # Calculate total agency spend
        total_agency_spend = sum(
            s.financial.agency_supply_costs or 0 
            for s in schools 
            if s.financial
        )
        
        # Count by priority
        high = len([s for s in schools if s.get_sales_priority() == "HIGH"])
        medium = len([s for s in schools if s.get_sales_priority() == "MEDIUM"])
        low = len([s for s in schools if s.get_sales_priority() == "LOW"])
        
        # Count with contact details
        with_contacts = len([s for s in schools if s.headteacher])
        with_phone = len([s for s in schools if s.phone])
        with_financial = len([s for s in schools if s.financial and s.financial.total_teaching_support_costs])
        
        return {
            "total_schools": len(schools),
            "with_contacts": with_contacts,
            "with_phone": with_phone,
            "with_financial_data": with_financial,
            "with_agency_spend": len(self.get_schools_with_agency_spend()),
            "total_staffing_spend": f"£{total_staffing_spend:,.0f}",
            "total_agency_spend": f"£{total_agency_spend:,.0f}",
            "high_priority": high,
            "medium_priority": medium,
            "low_priority": low,
            "boroughs": len(self.get_boroughs()),
            "data_source": self.source,
        }
    
    def refresh(self) -> List[School]:
        """Force reload data from source."""
        self._schools_cache = None
        self._schools_by_name = {}
        self._schools_by_urn = {}
        return self.load()


# Singleton instance
_loader_instance: Optional[DataLoader] = None

def get_data_loader() -> DataLoader:
    """Get the global DataLoader instance."""
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = DataLoader()
    return _loader_instance


if __name__ == "__main__":
    # Test the data loader
    logging.basicConfig(level=logging.INFO)
    
    loader = DataLoader()
    
    # Load all schools
    schools = loader.get_all_schools()
    print(f"\n📚 Loaded {len(schools)} schools")
    
    # Get statistics
    stats = loader.get_statistics()
    print(f"\n📊 Statistics:")
    for k, v in stats.items():
        print(f"   {k}: {v}")
    
    # Get top staffing spenders
    top_spenders = loader.get_top_spenders(limit=5, spend_type="total")
    print(f"\n💰 Top 5 Total Staffing Spenders:")
    for school in top_spenders:
        spend = school.financial.total_teaching_support_costs or 0
        print(f"   • {school.school_name}: £{spend:,.0f}")
        if school.headteacher:
            print(f"     Contact: {school.headteacher.full_name}")
    
    # Get boroughs (Local Authorities)
    boroughs = loader.get_boroughs()
    print(f"\n🏛️ Local Authorities ({len(boroughs)}):")
    for b in boroughs[:10]:
        print(f"   • {b}")
