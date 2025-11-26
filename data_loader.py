"""
School Research Assistant - Data Loader
========================================
NEW FILE (doesn't replace anything - this is new functionality)

GOAL:
- Loads schools from the CSV file
- Converts each row into a School Pydantic model
- Provides search/filter functions
- FUTURE: Will connect to Databricks with minimal code changes

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
    """
    
    def __init__(self, source: str = None):
        """
        Initialize the data loader.
        
        Args:
            source: Override the config source ("csv" or "databricks")
        """
        self.source = source or DATA_SOURCE
        self._schools_cache: Optional[List[School]] = None
        self._schools_by_name: Dict[str, School] = {}
        self._schools_by_urn: Dict[str, School] = {}
        
        logger.info(f"📚 DataLoader initialized with source: {self.source}")
    
    def load(self) -> List[School]:
        """
        Load all schools from the data source.
        
        This is called once when the app starts.
        Results are cached so we don't reload on every request.
        """
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
        
        This reads your camden_schools_llm_ready.csv and converts
        each row into a School object with proper validation.
        """
        schools = []
        
        # Find the CSV file
        csv_path = Path(CSV_FILE_PATH)
        if not csv_path.exists():
            # Try relative to current directory
            csv_path = Path(__file__).parent / CSV_FILE_PATH
        if not csv_path.exists():
            # Try data folder
            csv_path = Path(__file__).parent / "data" / "camden_schools_llm_ready.csv"
        if not csv_path.exists():
            logger.error(f"❌ CSV file not found: {CSV_FILE_PATH}")
            return []
        
        logger.info(f"📖 Reading CSV from: {csv_path}")
        
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    school = self._row_to_school(row)
                    schools.append(school)
                except Exception as e:
                    logger.warning(f"⚠️ Error parsing row: {e}")
                    continue
        
        return schools
    
    def _row_to_school(self, row: Dict[str, Any]) -> School:
        """
        Convert a CSV row to a School object.
        
        This handles the mapping between your CSV columns 
        and our Pydantic models.
        """
        # Create headteacher contact
        headteacher = None
        if row.get('headteacher') and row.get('headteacher') != '':
            headteacher = Contact(
                full_name=row.get('headteacher', ''),
                role=ContactRole.HEADTEACHER,
                title=row.get('head_title'),
                first_name=row.get('head_first_name'),
                last_name=row.get('head_last_name'),
                phone=row.get('phone'),
                confidence_score=1.0  # From official data
            )
        
        # Create financial data
        financial = FinancialData(
            total_teaching_support_spend_per_pupil=row.get('total_teaching_support_spend_per_pupil'),
            comparison_to_other_schools=row.get('comparison_to_other_schools'),
            total_teaching_support_per_pupil=row.get('total_teaching_support_per_pupil'),
            teaching_staff_costs=row.get('teaching_staff_costs'),
            supply_teaching_costs=row.get('supply_teaching_costs'),
            agency_supply_costs=row.get('agency_supply_costs'),
            educational_support_costs=row.get('educational_support_costs'),
            educational_consultancy_costs=row.get('educational_consultancy_costs'),
        )
        
        # Create school object
        school = School(
            urn=str(row.get('urn', '')),
            school_name=row.get('school_name', ''),
            la_name=row.get('la_name'),
            school_type=row.get('school_type'),
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
            pupil_count=row.get('pupil_count'),
            headteacher=headteacher,
            contacts=[headteacher] if headteacher else [],
            financial=financial,
            data_source="csv"
        )
        
        return school
    
    def _load_from_databricks(self) -> List[School]:

        logger.warning("⚠️ Databricks connection not yet implemented")
        logger.info("📝 When ready, configure DATABRICKS_CONFIG in config_v2.py")
        
        # For now, fall back to CSV
        return self._load_from_csv()
        
        # FUTURE IMPLEMENTATION:
        # from databricks import sql
        # 
        # connection = sql.connect(
        #     server_hostname=DATABRICKS_CONFIG["host"],
        #     http_path=f"/sql/1.0/warehouses/{DATABRICKS_CONFIG['warehouse_id']}",
        #     access_token=DATABRICKS_CONFIG["token"]
        # )
        # 
        # cursor = connection.cursor()
        # cursor.execute(f"SELECT * FROM {DATABRICKS_CONFIG['catalog']}.{DATABRICKS_CONFIG['schema']}.{DATABRICKS_CONFIG['table']}")
        # rows = cursor.fetchall()
        # 
        # return [self._row_to_school(row) for row in rows]
    
    
    def get_all_schools(self) -> List[School]:
        """Get all schools from the data source."""
        return self.load()
    
    def get_school_names(self) -> List[str]:
        """
        Get list of all school names (for dropdown).
        
        Returns sorted list of school names.
        """
        schools = self.load()
        return sorted([s.school_name for s in schools])
    
    def get_school_by_name(self, name: str) -> Optional[School]:
        """
        Get a school by its name.
        
        Args:
            name: The school name to look up
            
        Returns:
            School object or None if not found
        """
        self.load()  # Ensure data is loaded
        return self._schools_by_name.get(name)
    
    def get_school_by_urn(self, urn: str) -> Optional[School]:
        """Get a school by its URN (Unique Reference Number)."""
        self.load()
        return self._schools_by_urn.get(urn)
    
    def search_schools(self, query: str) -> List[School]:
        """
        Search schools by name (simple text matching).
        
        For 28 schools, this is fine. For 24,000, we'll use vectors.
        
        Args:
            query: Search term
            
        Returns:
            List of matching schools
        """
        schools = self.load()
        query_lower = query.lower()
        
        return [
            s for s in schools 
            if query_lower in s.school_name.lower()
        ]
    
    def get_schools_by_priority(self, priority: str) -> List[School]:
        """
        Get schools by sales priority level.
        
        Args:
            priority: "HIGH", "MEDIUM", or "LOW"
            
        Returns:
            Schools with that priority level
        """
        schools = self.load()
        return [s for s in schools if s.get_sales_priority() == priority]
    
    def get_schools_with_agency_spend(self) -> List[School]:
        """
        Get schools that spend on agency staff.
        
        These are the best sales prospects!
        """
        schools = self.load()
        return [
            s for s in schools 
            if s.financial and s.financial.has_agency_spend()
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get summary statistics about the loaded data.
        
        Useful for the dashboard.
        """
        schools = self.load()
        
        return {
            "total_schools": len(schools),
            "with_agency_spend": len(self.get_schools_with_agency_spend()),
            "high_priority": len(self.get_schools_by_priority("HIGH")),
            "medium_priority": len(self.get_schools_by_priority("MEDIUM")),
            "low_priority": len(self.get_schools_by_priority("LOW")),
            "data_source": self.source,
        }
    
    def refresh(self) -> List[School]:
        """
        Force reload data from source.
        
        Clears the cache and reloads.
        """
        self._schools_cache = None
        self._schools_by_name = {}
        self._schools_by_urn = {}
        return self.load()


_loader_instance: Optional[DataLoader] = None

def get_data_loader() -> DataLoader:
    """
    Get the global DataLoader instance.
    
    Usage:
        from data_loader import get_data_loader
        loader = get_data_loader()
        schools = loader.get_all_schools()
    """
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = DataLoader()
    return _loader_instance


if __name__ == "__main__":
    # Test the data loader
    loader = DataLoader()
    
    # Load all schools
    schools = loader.get_all_schools()
    print(f"\n📚 Loaded {len(schools)} schools")
    
    # Get school names for dropdown
    names = loader.get_school_names()
    print(f"\n📋 School names for dropdown:")
    for name in names[:5]:
        print(f"   • {name}")
    print(f"   ... and {len(names) - 5} more")
    
    # Get a specific school
    school = loader.get_school_by_name("Thomas Coram Centre")
    if school:
        print(f"\n🏫 School details:")
        print(f"   Name: {school.school_name}")
        print(f"   URN: {school.urn}")
        print(f"   Type: {school.school_type}")
        print(f"   Headteacher: {school.headteacher.full_name if school.headteacher else 'Unknown'}")
        print(f"   Priority: {school.get_sales_priority()}")
        if school.financial:
            print(f"   Agency costs: {school.financial.agency_supply_costs}")
    
    # Get statistics
    stats = loader.get_statistics()
    print(f"\n📊 Statistics:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
