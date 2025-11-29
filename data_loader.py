"""
School Research Assistant - Data Loader
========================================
UPDATED: Now loads from london_schools_financial_CLEAN.csv with total spend values

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
from config_v2 import DATA_SOURCE, CSV_FILE_PATH, DATABRICKS_CONFIG

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Loads school data from CSV (POC) or Databricks (Production).
    
    UPDATED: Now handles the new financial data format with total spend values.
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
            schools = self._load_from_csv()
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
    
    def _load_from_csv(self) -> List[School]:
        """
        Load schools from CSV file.
        
        UPDATED: Now reads from london_schools_financial_CLEAN.csv
        with the new column format from the government download.
        """
        schools = []
        
        # Try multiple possible paths
        possible_paths = [
            CSV_FILE_PATH,
            Path(__file__).parent / CSV_FILE_PATH,
            Path(__file__).parent / "data" / "london_schools_financial_CLEAN.csv",
            "data/london_schools_financial_CLEAN.csv",
            "london_schools_financial_CLEAN.csv",
        ]
        
        csv_path = None
        for path in possible_paths:
            p = Path(path)
            if p.exists():
                csv_path = p
                break
        
        if not csv_path:
            logger.error(f"❌ CSV file not found. Tried: {possible_paths}")
            return []
        
        logger.info(f"📖 Reading CSV from: {csv_path}")
        
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    school = self._row_to_school(row)
                    if school:
                        schools.append(school)
                except Exception as e:
                    logger.warning(f"⚠️ Error parsing row: {e}")
                    continue
        
        return schools
    
    def _safe_float(self, value) -> Optional[float]:
        """Safely convert a value to float"""
        if value is None or value == '' or value == 'nan':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_int(self, value) -> Optional[int]:
        """Safely convert a value to int"""
        if value is None or value == '' or value == 'nan':
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _row_to_school(self, row: Dict[str, Any]) -> Optional[School]:
        """
        Convert a CSV row to a School object.
        
        UPDATED: Maps from the new government download format:
        - URN, SchoolName, LAName, SchoolType, TotalPupils
        - TeachingStaffCosts, SupplyTeachingStaffCosts, AgencySupplyTeachingStaffCosts
        - EducationSupportStaffCosts, EducationalConsultancyCosts
        """
        # Skip rows without URN or marked as failed
        status = row.get('status', 'success')
        if status != 'success':
            return None
        
        urn = row.get('URN') or row.get('urn')
        if not urn:
            return None
        
        # Get school name (try multiple column names)
        school_name = (
            row.get('SchoolName') or 
            row.get('school_name') or 
            row.get('school_name_gias') or
            f"School {urn}"
        )
        
        # Get LA name
        la_name = (
            row.get('LAName') or 
            row.get('la_name') or 
            row.get('la_name_gias')
        )
        
        # Get pupil count
        pupil_count = self._safe_int(
            row.get('TotalPupils') or row.get('pupil_count')
        )
        
        # Create financial data with TOTAL SPEND values
        financial = FinancialData(
            total_expenditure=self._safe_float(row.get('TotalExpenditure')),
            total_pupils=self._safe_float(row.get('TotalPupils')),
            total_teaching_support_costs=self._safe_float(row.get('TotalTeachingSupportStaffCosts')),
            teaching_staff_costs=self._safe_float(row.get('TeachingStaffCosts')),
            supply_teaching_costs=self._safe_float(row.get('SupplyTeachingStaffCosts')),
            agency_supply_costs=self._safe_float(row.get('AgencySupplyTeachingStaffCosts')),
            educational_support_costs=self._safe_float(row.get('EducationSupportStaffCosts')),
            educational_consultancy_costs=self._safe_float(row.get('EducationalConsultancyCosts')),
        )
        
        # Create headteacher contact if we have GIAS data
        headteacher = None
        head_name = row.get('headteacher') or row.get('HeadTeacher')
        if head_name and head_name != '' and head_name != 'nan':
            headteacher = Contact(
                full_name=str(head_name),
                role=ContactRole.HEADTEACHER,
                title=row.get('head_title'),
                first_name=row.get('head_first_name'),
                last_name=row.get('head_last_name'),
                phone=row.get('phone'),
                confidence_score=1.0
            )
        
        # Create school object
        school = School(
            urn=str(int(float(urn))),  # Clean URN format
            school_name=school_name,
            la_name=la_name,
            school_type=row.get('SchoolType') or row.get('school_type'),
            phase=row.get('phase'),
            address_1=row.get('address_1'),
            address_2=row.get('address_2'),
            address_3=row.get('address_3'),
            town=row.get('town'),
            county=row.get('county'),
            postcode=row.get('postcode'),
            phone=row.get('phone'),
            website=row.get('website'),
            trust_code=row.get('trust_code'),
            trust_name=row.get('trust_name'),
            pupil_count=pupil_count,
            headteacher=headteacher,
            contacts=[headteacher] if headteacher else [],
            financial=financial,
            data_source="csv"
        )
        
        return school
    
    def _load_from_databricks(self) -> List[School]:
        """Databricks connection - placeholder for future"""
        logger.warning("⚠️ Databricks connection not yet implemented")
        return self._load_from_csv()
    
    
    # PUBLIC METHODS
    
    
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
        return self._schools_by_urn.get(urn)
    
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
    
    def get_schools_with_agency_spend(self, min_spend: float = 0) -> List[School]:
        """
        Get schools that spend on agency staff.
        
        Args:
            min_spend: Minimum agency spend to filter by (default 0 = any spend)
        """
        schools = self.load()
        return [
            s for s in schools 
            if s.financial and s.financial.agency_supply_costs and s.financial.agency_supply_costs > min_spend
        ]
    
    def get_top_agency_spenders(self, limit: int = 20) -> List[School]:
        """Get schools with highest agency spend."""
        schools = self.get_schools_with_agency_spend()
        return sorted(
            schools,
            key=lambda s: s.financial.agency_supply_costs or 0,
            reverse=True
        )[:limit]
    
    def get_boroughs(self) -> List[str]:
        """Get list of all boroughs/LAs in the data."""
        schools = self.load()
        boroughs = set(s.la_name for s in schools if s.la_name)
        return sorted(list(boroughs))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get summary statistics about the loaded data."""
        schools = self.load()
        
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
        
        return {
            "total_schools": len(schools),
            "with_agency_spend": len(self.get_schools_with_agency_spend()),
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
    
    # Get top agency spenders
    top_spenders = loader.get_top_agency_spenders(limit=5)
    print(f"\n🔥 Top 5 Agency Spenders:")
    for school in top_spenders:
        spend = school.financial.agency_supply_costs
        print(f"   • {school.school_name}: £{spend:,.0f}")
    
    # Get boroughs
    boroughs = loader.get_boroughs()
    print(f"\n🏛️ Boroughs ({len(boroughs)}):")
    for b in boroughs[:10]:
        print(f"   • {b}")
