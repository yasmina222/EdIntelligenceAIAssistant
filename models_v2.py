"""
School Research Assistant - Pydantic Models (v2)
================================================
UPDATED: Priority now based on TOTAL STAFFING SPEND (not just agency)
Because Protocol Education offers permanent, temporary, AND agency staff
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ContactRole(str, Enum):
    """Types of contacts we track"""
    HEADTEACHER = "headteacher"
    DEPUTY_HEAD = "deputy_head"
    ASSISTANT_HEAD = "assistant_head"
    BUSINESS_MANAGER = "business_manager"
    SENCO = "senco"
    UNKNOWN = "unknown"


class Contact(BaseModel):
    """
    A school contact (headteacher, deputy, etc.)
    """
    full_name: str = Field(description="Full name of the contact")
    role: ContactRole = Field(default=ContactRole.UNKNOWN, description="Their role at the school")
    title: Optional[str] = Field(default=None, description="Mr, Ms, Mrs, Dr, etc.")
    first_name: Optional[str] = Field(default=None)
    last_name: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None, description="Email address if known")
    phone: Optional[str] = Field(default=None, description="Phone number")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="How confident we are in this data (0-1)")
    
    @field_validator('phone', mode='before')
    @classmethod
    def clean_phone(cls, v):
        """Clean phone number - remove .0 from float conversion"""
        if v is None:
            return None
        v = str(v)
        if v.endswith('.0'):
            v = v[:-2]
        # Format UK phone numbers
        if v.startswith('20') and len(v) == 10:
            v = f"020 {v[2:6]} {v[6:]}"
        return v


class FinancialData(BaseModel):
    """
    School financial data from government sources
    
    Stores TOTAL SPEND values (numbers) not per-pupil strings.
    We calculate per-pupil when needed using pupil_count.
    """
    # Total values (from government CSV)
    total_expenditure: Optional[float] = Field(default=None, description="Total school expenditure")
    total_pupils: Optional[float] = Field(default=None, description="Total number of pupils")
    
    # Teaching staff costs (E01-E27)
    teaching_staff_costs: Optional[float] = Field(default=None, description="E01: Teaching staff costs (total £)")
    supply_teaching_costs: Optional[float] = Field(default=None, description="E02: Supply teaching staff costs (total £)")
    educational_support_costs: Optional[float] = Field(default=None, description="E03: Educational support staff costs (total £)")
    agency_supply_costs: Optional[float] = Field(default=None, description="E26: Agency supply teaching staff costs (total £)")
    educational_consultancy_costs: Optional[float] = Field(default=None, description="E27: Educational consultancy costs (total £)")
    
    # Total teaching and support
    total_teaching_support_costs: Optional[float] = Field(default=None, description="Total teaching and support staff costs")
    
    # Legacy per-pupil fields (for backwards compatibility)
    total_teaching_support_spend_per_pupil: Optional[str] = Field(default=None)
    comparison_to_other_schools: Optional[str] = Field(default=None)
    
    def has_financial_data(self) -> bool:
        """Check if we have any financial data"""
        return self.total_teaching_support_costs is not None or self.total_expenditure is not None
    
    def has_agency_spend(self) -> bool:
        """Check if school spends on agency staff"""
        if self.agency_supply_costs is None:
            return False
        return self.agency_supply_costs > 0
    
    def get_total_staffing_formatted(self) -> str:
        """Get total staffing spend as formatted string"""
        if self.total_teaching_support_costs is None or self.total_teaching_support_costs == 0:
            return "No data"
        return f"£{self.total_teaching_support_costs:,.0f}"
    
    def get_agency_spend_formatted(self) -> str:
        """Get agency spend as formatted string"""
        if self.agency_supply_costs is None or self.agency_supply_costs == 0:
            return "£0"
        return f"£{self.agency_supply_costs:,.0f}"
    
    def get_agency_per_pupil(self) -> Optional[float]:
        """Calculate agency spend per pupil"""
        if self.agency_supply_costs and self.total_pupils and self.total_pupils > 0:
            return self.agency_supply_costs / self.total_pupils
        return None
    
    def get_agency_per_pupil_formatted(self) -> str:
        """Get agency spend per pupil as formatted string"""
        per_pupil = self.get_agency_per_pupil()
        if per_pupil is None or per_pupil == 0:
            return "£0 per pupil"
        return f"£{per_pupil:,.0f} per pupil"
    
    def get_teaching_per_pupil(self) -> Optional[float]:
        """Calculate teaching staff costs per pupil"""
        if self.teaching_staff_costs and self.total_pupils and self.total_pupils > 0:
            return self.teaching_staff_costs / self.total_pupils
        return None
    
    def get_priority_level(self) -> str:
        """
        Determine priority based on TOTAL STAFFING SPEND.
        
        This is the key change from v1 - we now look at total spend
        because Protocol offers permanent, temporary, AND agency staff.
        
        HIGH: £500k+ total staffing costs (big school, big opportunity)
        MEDIUM: £200k-500k total staffing costs
        LOW: <£200k or no data
        """
        # Use total staffing spend as primary indicator
        spend = self.total_teaching_support_costs
        
        if spend is None:
            return "UNKNOWN"
        
        if spend >= 500000:
            return "HIGH"
        elif spend >= 200000:
            return "MEDIUM"
        else:
            return "LOW"
    
    def get_financial_summary(self) -> str:
        """Get a text summary for LLM context"""
        lines = []
        
        if self.total_pupils:
            lines.append(f"Total Pupils: {int(self.total_pupils)}")
        
        if self.total_expenditure:
            lines.append(f"Total Expenditure: £{self.total_expenditure:,.0f}")
        
        if self.total_teaching_support_costs:
            lines.append(f"Total Staffing Costs: £{self.total_teaching_support_costs:,.0f} ⭐ KEY METRIC")
            if self.total_pupils and self.total_pupils > 0:
                per_pupil = self.total_teaching_support_costs / self.total_pupils
                lines.append(f"  → £{per_pupil:,.0f} per pupil on staffing")
        
        if self.teaching_staff_costs:
            lines.append(f"Teaching Staff Costs (E01): £{self.teaching_staff_costs:,.0f}")
        
        if self.supply_teaching_costs and self.supply_teaching_costs > 0:
            lines.append(f"Supply Teaching Costs (E02): £{self.supply_teaching_costs:,.0f}")
        
        if self.agency_supply_costs and self.agency_supply_costs > 0:
            lines.append(f"Agency Supply Costs (E26): £{self.agency_supply_costs:,.0f}")
            if self.total_pupils and self.total_pupils > 0:
                per_pupil = self.agency_supply_costs / self.total_pupils
                lines.append(f"  → £{per_pupil:,.0f} per pupil on agency staff")
        
        if self.educational_support_costs:
            lines.append(f"Educational Support Costs (E03): £{self.educational_support_costs:,.0f}")
        
        if self.educational_consultancy_costs and self.educational_consultancy_costs > 0:
            lines.append(f"Educational Consultancy (E27): £{self.educational_consultancy_costs:,.0f}")
        
        return "\n".join(lines) if lines else "No financial data available"


class OfstedData(BaseModel):
    """Ofsted inspection data"""
    rating: Optional[str] = Field(default=None, description="Outstanding, Good, Requires Improvement, Inadequate")
    inspection_date: Optional[str] = Field(default=None)
    report_url: Optional[str] = Field(default=None)
    areas_for_improvement: List[str] = Field(default_factory=list)
    key_strengths: List[str] = Field(default_factory=list)


class ConversationStarter(BaseModel):
    """
    A talking point for sales consultants
    """
    topic: str = Field(description="Brief topic heading")
    detail: str = Field(description="The actual conversation starter script")
    source: Optional[str] = Field(default=None, description="Where this insight came from")
    relevance_score: float = Field(default=0.8, ge=0.0, le=1.0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "topic": "Staffing Budget Opportunity",
                "detail": "I noticed from government data that you invest over £2 million annually in staffing. We work with schools of similar size to help them find the right permanent and temporary staff. Would you be open to a conversation about how we support schools like yours?",
                "source": "Financial Benchmarking Data",
                "relevance_score": 0.95
            }
        }


class School(BaseModel):
    """
    Complete school record - merged from GIAS (contacts) and Financial data
    """
    # Identifiers
    urn: str = Field(description="Unique Reference Number - the school's ID")
    school_name: str = Field(description="Official school name")
    
    # Location
    la_name: Optional[str] = Field(default=None, description="Local Authority name")
    address_1: Optional[str] = Field(default=None)
    address_2: Optional[str] = Field(default=None)
    address_3: Optional[str] = Field(default=None)
    town: Optional[str] = Field(default=None)
    county: Optional[str] = Field(default=None)
    postcode: Optional[str] = Field(default=None)
    
    # School type
    school_type: Optional[str] = Field(default=None, description="Academy, Community school, etc.")
    phase: Optional[str] = Field(default=None, description="Primary, Secondary, Nursery, etc.")
    pupil_count: Optional[int] = Field(default=None)
    
    # Trust info
    trust_code: Optional[str] = Field(default=None)
    trust_name: Optional[str] = Field(default=None)
    
    # Contact info
    phone: Optional[str] = Field(default=None)
    website: Optional[str] = Field(default=None)
    
    # Key contacts
    headteacher: Optional[Contact] = Field(default=None)
    contacts: List[Contact] = Field(default_factory=list)
    
    # Financial data
    financial: Optional[FinancialData] = Field(default=None)
    
    # Ofsted data
    ofsted: Optional[OfstedData] = Field(default=None)
    
    # Generated insights
    conversation_starters: List[ConversationStarter] = Field(default_factory=list)
    
    # Metadata
    last_updated: datetime = Field(default_factory=datetime.now)
    data_source: str = Field(default="csv", description="csv, csv_merged, databricks, or live")
    
    @field_validator('pupil_count', mode='before')
    @classmethod
    def parse_pupil_count(cls, v):
        """Convert pupil count to integer"""
        if v is None or v == '':
            return None
        try:
            return int(float(v))
        except (ValueError, TypeError):
            return None
    
    @field_validator('phone', mode='before')
    @classmethod
    def clean_phone(cls, v):
        """Clean phone number format"""
        if v is None:
            return None
        v = str(v)
        if v.endswith('.0'):
            v = v[:-2]
        return v
    
    def get_full_address(self) -> str:
        """Combine address fields into single string"""
        parts = [
            self.address_1, 
            self.address_2, 
            self.address_3, 
            self.town, 
            self.county, 
            self.postcode
        ]
        return ", ".join([p for p in parts if p])
    
    def get_sales_priority(self) -> str:
        """Determine sales priority based on financial data"""
        if not self.financial:
            return "UNKNOWN"
        return self.financial.get_priority_level()
    
    def has_contact_details(self) -> bool:
        """Check if we have headteacher contact details"""
        return self.headteacher is not None
    
    def to_llm_context(self) -> str:
        """
        Convert school data to text format for LLM analysis.
        Includes both contact and financial data.
        """
        lines = [
            f"SCHOOL: {self.school_name}",
            f"URN: {self.urn}",
            f"Type: {self.school_type or 'Unknown'} ({self.phase or 'Unknown phase'})",
            f"Local Authority: {self.la_name or 'Unknown'}",
            f"Pupil Count: {self.pupil_count or 'Unknown'}",
        ]
        
        # Add headteacher info (from GIAS)
        if self.headteacher:
            lines.append(f"\nHEADTEACHER: {self.headteacher.full_name}")
            if self.phone:
                lines.append(f"School Phone: {self.phone}")
            if self.website:
                lines.append(f"Website: {self.website}")
        
        # Add address
        address = self.get_full_address()
        if address:
            lines.append(f"Address: {address}")
        
        # Add financial data
        if self.financial:
            lines.append("\nFINANCIAL DATA (from Government Benchmarking Tool):")
            lines.append(self.financial.get_financial_summary())
            
            # Add priority indicator
            priority = self.financial.get_priority_level()
            if priority == "HIGH":
                lines.append("\n⭐ SALES PRIORITY: HIGH - Large staffing budget!")
            elif priority == "MEDIUM":
                lines.append("\n📊 SALES PRIORITY: MEDIUM - Mid-size staffing budget")
        
        # Add Ofsted data
        if self.ofsted:
            lines.append(f"\nOFSTED RATING: {self.ofsted.rating or 'Unknown'}")
            if self.ofsted.inspection_date:
                lines.append(f"Inspection Date: {self.ofsted.inspection_date}")
            if self.ofsted.areas_for_improvement:
                lines.append("Areas for improvement:")
                for area in self.ofsted.areas_for_improvement:
                    lines.append(f"  - {area}")
        
        return "\n".join(lines)


class SchoolSearchResult(BaseModel):
    """Result from searching for schools"""
    schools: List[School] = Field(default_factory=list)
    total_count: int = Field(default=0)
    query: Optional[str] = Field(default=None)


class ConversationStarterResponse(BaseModel):
    """
    Response from the LLM when generating conversation starters.
    """
    conversation_starters: List[ConversationStarter] = Field(
        description="List of conversation starters for sales consultants"
    )
    summary: Optional[str] = Field(
        default=None,
        description="Brief summary of the school's key characteristics"
    )
    sales_priority: str = Field(
        default="MEDIUM",
        description="HIGH, MEDIUM, or LOW priority for sales outreach"
    )
