"""
School Research Assistant - Streamlit App (v2)
===============================================
Replaces: streamlit_app.py

WHAT'S NEW:
- Schools load automatically on startup (no waiting)
- Dropdown shows all 28 schools
- Click a school → see data instantly
- Click "Generate Insights" → LLM creates conversation starters
- Much simpler, cleaner code

HOW TO RUN:
    streamlit run streamlit_app_v2.py
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import logging
import sys
import os
from pathlib import Path

# Add the project root to Python path (fixes Streamlit Cloud imports)
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import our modules
from school_intelligence_service import get_intelligence_service
from models_v2 import School, ConversationStarter
from config_v2 import get_app_password, LLM_PROVIDER, FEATURES

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="School Research Assistant",
    page_icon="🎓",
    layout="wide"
)


# =============================================================================
# PASSWORD PROTECTION
# =============================================================================

def check_password() -> bool:
    """Simple password protection"""
    
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if st.session_state.authenticated:
        return True
    
    st.title("🔒 School Research Assistant")
    
    password = st.text_input("Enter Password", type="password", key="password_input")
    
    if st.button("Login", type="primary"):
        if password == get_app_password():
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ Incorrect password")
    
    st.caption("Contact IT for access credentials")
    return False


# =============================================================================
# STYLING
# =============================================================================

st.markdown("""
<style>
    /* Make all main text visible on dark background */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
        color: #E8E8E8 !important;
    }
    
    /* Regular text and paragraphs */
    .stApp p, .stApp span, .stApp label, .stApp div {
        color: #D0D0D0 !important;
    }
    
    /* Markdown text */
    .stMarkdown, .stMarkdown p, .stMarkdown span {
        color: #D0D0D0 !important;
    }
    
    /* Metric labels and values */
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {
        color: #E8E8E8 !important;
    }
    
    /* Tab labels */
    .stTabs [data-baseweb="tab"] {
        color: #D0D0D0 !important;
    }
    
    /* Cards for conversation starters */
    .starter-card {
        background-color: #2D2D3A;
        border-left: 4px solid #0066ff;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    
    .starter-topic {
        font-weight: 600;
        color: #5CA8FF !important;
        margin-bottom: 0.5rem;
    }
    
    .starter-detail {
        color: #E0E0E0 !important;
        line-height: 1.6;
    }
    
    /* Priority badges */
    .priority-high {
        background-color: #dc3545;
        color: white !important;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    
    .priority-medium {
        background-color: #ffc107;
        color: black !important;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    
    .priority-low {
        background-color: #28a745;
        color: white !important;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    
    /* Financial data card */
    .financial-highlight {
        background-color: #3D3D2A;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    /* Contact card */
    .contact-card {
        background-color: #2A3D4D;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# MAIN APP
# =============================================================================

def main():
    """Main application logic"""
    
    # Check password
    if not check_password():
        return
    
    # Initialize service
    service = get_intelligence_service()
    
    # Header
    st.title("🎓 School Research Assistant")
    
    # Load schools on startup (this is instant - from CSV)
    with st.spinner("Loading schools..."):
        school_names = service.get_school_names()
        stats = service.get_statistics()
    
    # Sidebar
    with st.sidebar:
        st.header("📊 Dashboard")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Schools", stats["total_schools"])
        with col2:
            st.metric("High Priority", stats["high_priority"])
        
        st.divider()
        
        st.subheader("🎯 Quick Filters")
        
        if st.button("Show High Priority"):
            st.session_state.filter = "high"
        if st.button("Show with Agency Spend"):
            st.session_state.filter = "agency"
        if st.button("Show All"):
            st.session_state.filter = "all"
    
    # Main content
    st.header("🔍 Search Schools")
    
    # School selector - THE DROPDOWN!
    selected_school_name = st.selectbox(
        "Select a school",
        options=[""] + school_names,  # Empty option first
        index=0,
        placeholder="Choose a school...",
        help="Select a school to view details and generate conversation starters"
    )
    
    # If a school is selected
    if selected_school_name:
        
        # Get the school data (instant - from cache)
        school = service.get_school_by_name(selected_school_name)
        
        if school:
            display_school(school, service)
        else:
            st.error(f"School not found: {selected_school_name}")
    
    else:
        # Show high priority schools as suggestions
        st.subheader("🎯 Suggested Schools to Call")
        
        high_priority = service.get_high_priority_schools(limit=5)
        
        for school in high_priority:
            col1, col2, col3 = st.columns([4, 1, 1])
            
            with col1:
                # Make the school name clickable
                if st.button(f"📍 **{school.school_name}**", key=f"select_{school.urn}"):
                    st.session_state.selected_school = school.school_name
                    st.rerun()
            with col2:
                priority = school.get_sales_priority()
                if priority == "HIGH":
                    st.markdown('<span class="priority-high">HIGH</span>', unsafe_allow_html=True)
                elif priority == "MEDIUM":
                    st.markdown('<span class="priority-medium">MEDIUM</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="priority-low">LOW</span>', unsafe_allow_html=True)
            with col3:
                if school.financial and school.financial.agency_supply_costs:
                    st.write(school.financial.agency_supply_costs)


def display_school(school: School, service):
    """Display school details and conversation starters"""
    
    # School header
    st.subheader(f"🏫 {school.school_name}")
    
    # Quick info row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("URN", school.urn)
    with col2:
        st.metric("Type", school.phase or "Unknown")
    with col3:
        st.metric("Pupils", school.pupil_count or "Unknown")
    with col4:
        priority = school.get_sales_priority()
        st.metric("Priority", priority)
    
    st.divider()
    
    # Tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "💬 Conversation Starters",
        "👤 Contact Info",
        "💰 Financial Data",
        "📋 Full Details"
    ])
    
    # TAB 1: Conversation Starters
    with tab1:
        display_conversation_starters(school, service)
    
    # TAB 2: Contact Info
    with tab2:
        display_contact_info(school)
    
    # TAB 3: Financial Data
    with tab3:
        display_financial_data(school)
    
    # TAB 4: Full Details
    with tab4:
        display_full_details(school)


def display_conversation_starters(school: School, service):
    """Display or generate conversation starters"""
    
    st.subheader("💬 Conversation Starters")
    
    # Check if we already have starters
    if school.conversation_starters:
        st.success(f"✅ {len(school.conversation_starters)} conversation starters ready")
        
        for i, starter in enumerate(school.conversation_starters, 1):
            with st.expander(f"**{i}. {starter.topic}**", expanded=(i == 1)):
                st.markdown(f"""
                <div class="starter-card">
                    <div class="starter-detail">{starter.detail}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Source attribution - YOU LOVE THIS!
                if starter.source:
                    if starter.source.startswith("http"):
                        # It's a URL (likely Ofsted report)
                        st.markdown(f"📄 **Source:** [View Ofsted Report]({starter.source})")
                    else:
                        st.caption(f"📊 Source: {starter.source}")
                
                # Copy button
                st.code(starter.detail, language=None)
    
    # Ofsted info display (if available)
    if school.ofsted and school.ofsted.rating:
        st.info(f"📋 **Ofsted Rating:** {school.ofsted.rating} | **Inspected:** {school.ofsted.inspection_date or 'Unknown'}")
        if school.ofsted.report_url:
            st.markdown(f"[📄 View Full Ofsted Report]({school.ofsted.report_url})")
    
    st.divider()
    
    # Generate button with Ofsted toggle
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        num_starters = st.number_input(
            "How many?", 
            min_value=1, 
            max_value=10, 
            value=5
        )
    
    with col2:
        include_ofsted = st.checkbox(
            "Include Ofsted",
            value=True,
            help="Fetch and analyze Ofsted report (adds 10-15 seconds)"
        )
    
    with col3:
        if st.button("🤖 Generate Conversation Starters", type="primary"):
            if include_ofsted:
                with st.spinner("🔍 Analyzing Ofsted report + generating insights..."):
                    # Use the new method that includes Ofsted
                    school_with_starters = service.get_school_intelligence_with_ofsted(
                        school.school_name,
                        force_refresh=True,
                        num_starters=num_starters,
                        include_ofsted=True
                    )
            else:
                with st.spinner("Generating insights with AI..."):
                    # Use the basic method (faster, no Ofsted)
                    school_with_starters = service.get_school_intelligence(
                        school.school_name,
                        force_refresh=True,
                        num_starters=num_starters
                    )
                
            if school_with_starters and school_with_starters.conversation_starters:
                st.success(f"✅ Generated {len(school_with_starters.conversation_starters)} starters!")
                st.rerun()
            else:
                st.error("Failed to generate starters. Check your API key.")


def display_contact_info(school: School):
    """Display contact information"""
    
    st.subheader("👤 Key Contacts")
    
    if school.headteacher:
        st.markdown(f"""
        <div class="contact-card">
            <h4>{school.headteacher.full_name}</h4>
            <p><strong>Role:</strong> Headteacher</p>
            <p><strong>Phone:</strong> {school.phone or 'Not available'}</p>
            <p><strong>Website:</strong> <a href="{school.website}" target="_blank">{school.website}</a></p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No headteacher information available")
    
    # Address
    st.write("**Address:**")
    st.write(school.get_full_address())


def display_financial_data(school: School):
    """Display financial data"""
    
    st.subheader("💰 Financial Data")
    
    if school.financial:
        fin = school.financial
        
        # Highlight box for key metric
        if fin.total_teaching_support_spend_per_pupil:
            st.markdown(f"""
            <div class="financial-highlight">
                <h4>📊 {fin.total_teaching_support_spend_per_pupil}</h4>
                <p>{fin.comparison_to_other_schools or ''}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Detailed breakdown
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Cost Breakdown:**")
            if fin.teaching_staff_costs:
                st.write(f"• Teaching Staff: {fin.teaching_staff_costs}")
            if fin.supply_teaching_costs:
                st.write(f"• Supply Teaching: {fin.supply_teaching_costs}")
            if fin.agency_supply_costs:
                if fin.has_agency_spend():
                    st.error(f"• **Agency Supply: {fin.agency_supply_costs}** ⚠️")
                else:
                    st.write(f"• Agency Supply: {fin.agency_supply_costs}")
        
        with col2:
            if fin.educational_support_costs:
                st.write(f"• Educational Support: {fin.educational_support_costs}")
            if fin.educational_consultancy_costs:
                st.write(f"• Consultancy: {fin.educational_consultancy_costs}")
        
        # Sales insight
        if fin.has_agency_spend():
            st.warning("💡 **Sales Insight:** This school is spending on agency staff. Strong opportunity to offer our services!")
    else:
        st.info("No financial data available")


def display_full_details(school: School):
    """Display all school details in a structured way"""
    
    st.subheader("📋 Full School Details")
    
    # Convert to dict for display
    details = {
        "URN": school.urn,
        "School Name": school.school_name,
        "Local Authority": school.la_name,
        "School Type": school.school_type,
        "Phase": school.phase,
        "Address": school.get_full_address(),
        "Phone": school.phone,
        "Website": school.website,
        "Pupil Count": school.pupil_count,
        "Trust Name": school.trust_name or "N/A",
        "Sales Priority": school.get_sales_priority(),
    }
    
    # Display as table
    df = pd.DataFrame([
        {"Field": k, "Value": str(v) if v else "N/A"} 
        for k, v in details.items()
    ])
    
    st.dataframe(df, hide_index=True, use_container_width=True)


# =============================================================================
# RUN THE APP
# =============================================================================

if __name__ == "__main__":
    main()

Complete File 2: school_intelligence_service.py
Copy everything below and replace the entire file in GitHub:
python"""
School Research Assistant - Intelligence Service
=================================================
Replaces: processor_premium.py

WHAT THIS FILE DOES:
- Orchestrates the entire flow: load data → generate insights → cache
- This is the "brain" that coordinates everything
- Calls the LangChain conversation chain
- Handles caching to avoid redundant LLM calls

HOW TO USE:
    service = SchoolIntelligenceService()
    
    # Get a school with conversation starters
    school = service.get_school_intelligence("Thomas Coram Centre")
    
    # Access the starters
    for starter in school.conversation_starters:
        print(starter.detail)
"""

import logging
import json
import hashlib
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# Add the project root to Python path (fixes Streamlit Cloud imports)
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)

from models_v2 import School, ConversationStarter, ConversationStarterResponse
from data_loader import DataLoader, get_data_loader
from chains.conversation_chain import ConversationChain
from config_v2 import ENABLE_CACHE, CACHE_TTL_HOURS, CACHE_DIR, FEATURES

# Import Ofsted chain (optional - may fail if dependencies missing)
try:
    from chains.ofsted_chain import OfstedChain, get_ofsted_chain
    OFSTED_AVAILABLE = True
except ImportError as e:
    OFSTED_AVAILABLE = False
    logger.warning(f"Ofsted chain not available: {e}")


class SimpleCache:
    """
    Simple file-based cache for conversation starters.
    
    WHY WE CACHE:
    - LLM calls cost money (and take time)
    - If we already generated starters for a school, reuse them
    - Cache expires after CACHE_TTL_HOURS (default 24)
    
    FUTURE: Replace with LangChain's built-in caching for production
    """
    
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.enabled = ENABLE_CACHE
        
    def _get_cache_key(self, school_urn: str) -> str:
        """Generate cache key from school URN"""
        return hashlib.md5(f"starters_{school_urn}".encode()).hexdigest()
    
    def _get_cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"
    
    def get(self, school_urn: str) -> Optional[List[dict]]:
        """Get cached conversation starters if valid"""
        if not self.enabled:
            return None
            
        key = self._get_cache_key(school_urn)
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            
            # Check if expired
            cached_at = datetime.fromisoformat(data['cached_at'])
            if datetime.now() - cached_at > timedelta(hours=CACHE_TTL_HOURS):
                logger.info(f"🕐 Cache expired for {school_urn}")
                return None
            
            logger.info(f"📦 Cache HIT for {school_urn}")
            return data['starters']
            
        except Exception as e:
            logger.warning(f"⚠️ Cache read error: {e}")
            return None
    
    def set(self, school_urn: str, starters: List[ConversationStarter]) -> bool:
        """Save conversation starters to cache"""
        if not self.enabled:
            return False
            
        key = self._get_cache_key(school_urn)
        cache_path = self._get_cache_path(key)
        
        try:
            data = {
                'school_urn': school_urn,
                'cached_at': datetime.now().isoformat(),
                'starters': [s.model_dump() for s in starters]
            }
            
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"💾 Cached {len(starters)} starters for {school_urn}")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Cache write error: {e}")
            return False
    
    def clear(self, school_urn: str = None) -> int:
        """Clear cache for one school or all schools"""
        count = 0
        
        if school_urn:
            key = self._get_cache_key(school_urn)
            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                cache_path.unlink()
                count = 1
        else:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
                count += 1
        
        logger.info(f"🧹 Cleared {count} cache entries")
        return count


class SchoolIntelligenceService:
    """
    Main service that orchestrates everything.
    
    This is what the Streamlit app talks to.
    """
    
    def __init__(self):
        """Initialize all components"""
        self.data_loader = get_data_loader()
        self.conversation_chain = None  # Lazy load to avoid API calls at startup
        self.ofsted_chain = None  # Lazy load Ofsted analyzer
        self.cache = SimpleCache()
        
        logger.info("✅ SchoolIntelligenceService initialized")
    
    def _get_chain(self) -> ConversationChain:
        """Lazy-load the conversation chain (avoids API calls at startup)"""
        if self.conversation_chain is None:
            self.conversation_chain = ConversationChain()
        return self.conversation_chain
    
    def _get_ofsted_chain(self) -> Optional['OfstedChain']:
        """Lazy-load the Ofsted chain"""
        if not OFSTED_AVAILABLE:
            return None
        if self.ofsted_chain is None:
            self.ofsted_chain = get_ofsted_chain()
        return self.ofsted_chain
    
    # =========================================================================
    # DATA ACCESS METHODS
    # =========================================================================
    
    def get_all_schools(self) -> List[School]:
        """Get all schools from the data source"""
        return self.data_loader.get_all_schools()
    
    def get_school_names(self) -> List[str]:
        """Get school names for dropdown"""
        return self.data_loader.get_school_names()
    
    def get_school_by_name(self, name: str) -> Optional[School]:
        """Get a school by name (without generating starters)"""
        return self.data_loader.get_school_by_name(name)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get data statistics"""
        return self.data_loader.get_statistics()
    
    # =========================================================================
    # INTELLIGENCE METHODS (with LLM calls)
    # =========================================================================
    
    def get_school_intelligence(
        self, 
        school_name: str, 
        force_refresh: bool = False,
        num_starters: int = 5
    ) -> Optional[School]:
        """
        Get a school WITH conversation starters generated.
        
        This is the main method for the UI:
        1. Gets school data from cache/CSV
        2. Generates conversation starters using LLM
        3. Caches the results
        
        Args:
            school_name: Name of the school
            force_refresh: If True, regenerate starters even if cached
            num_starters: How many starters to generate
            
        Returns:
            School object with conversation_starters populated
        """
        # Get the school
        school = self.data_loader.get_school_by_name(school_name)
        if not school:
            logger.warning(f"⚠️ School not found: {school_name}")
            return None
        
        # Check if conversation starters are enabled
        if not FEATURES.get("conversation_starters", True):
            logger.info("ℹ️ Conversation starters disabled in config")
            return school
        
        # Check cache first
        if not force_refresh:
            cached_starters = self.cache.get(school.urn)
            if cached_starters:
                school.conversation_starters = [
                    ConversationStarter(**s) for s in cached_starters
                ]
                return school
        
        # Generate new starters using LLM
        try:
            chain = self._get_chain()
            response = chain.generate(school, num_starters)
            
            # Add starters to school
            school.conversation_starters = response.conversation_starters
            
            # Cache the results
            self.cache.set(school.urn, response.conversation_starters)
            
            return school
            
        except Exception as e:
            logger.error(f"❌ Error generating intelligence: {e}")
            # Return school without starters on error
            return school
    
    async def get_school_intelligence_async(
        self, 
        school_name: str, 
        force_refresh: bool = False,
        num_starters: int = 5
    ) -> Optional[School]:
        """
        Async version of get_school_intelligence.
        
        Use this when processing multiple schools in parallel.
        """
        school = self.data_loader.get_school_by_name(school_name)
        if not school:
            return None
        
        if not FEATURES.get("conversation_starters", True):
            return school
        
        if not force_refresh:
            cached_starters = self.cache.get(school.urn)
            if cached_starters:
                school.conversation_starters = [
                    ConversationStarter(**s) for s in cached_starters
                ]
                return school
        
        try:
            chain = self._get_chain()
            response = await chain.agenerate(school, num_starters)
            
            school.conversation_starters = response.conversation_starters
            self.cache.set(school.urn, response.conversation_starters)
            
            return school
            
        except Exception as e:
            logger.error(f"❌ Async error: {e}")
            return school
    
    def get_school_intelligence_with_ofsted(
        self,
        school_name: str,
        force_refresh: bool = False,
        num_starters: int = 5,
        include_ofsted: bool = True
    ) -> Optional[School]:
        """
        Get school intelligence WITH Ofsted analysis.
        
        This method:
        1. Gets school data from CSV
        2. Analyzes Ofsted report (downloads PDF, extracts improvements)
        3. Generates conversation starters using BOTH financial + Ofsted data
        
        Args:
            school_name: Name of the school
            force_refresh: If True, bypass cache
            num_starters: Number of conversation starters
            include_ofsted: If True, fetch and analyze Ofsted report
            
        Returns:
            School object with conversation_starters including Ofsted insights
        """
        # Get the school
        school = self.data_loader.get_school_by_name(school_name)
        if not school:
            logger.warning(f"⚠️ School not found: {school_name}")
            return None
        
        # Check cache first
        if not force_refresh:
            cached_starters = self.cache.get(school.urn)
            if cached_starters:
                school.conversation_starters = [
                    ConversationStarter(**s) for s in cached_starters
                ]
                logger.info(f"📦 Using cached starters for {school_name}")
                return school
        
        all_starters = []
        ofsted_data = None
        
        # Step 1: Ofsted analysis (if enabled and available)
        if include_ofsted and OFSTED_AVAILABLE and FEATURES.get("ofsted_analysis", True):
            try:
                logger.info(f"🔍 Fetching Ofsted data for {school_name}...")
                ofsted_chain = self._get_ofsted_chain()
                
                if ofsted_chain:
                    ofsted_result = ofsted_chain.analyze(school_name, school.urn)
                    
                    if ofsted_result and not ofsted_result.get("error"):
                        # Update school with Ofsted data
                        from models_v2 import OfstedData
                        school.ofsted = OfstedData(
                            rating=ofsted_result.get("rating"),
                            inspection_date=ofsted_result.get("inspection_date"),
                            report_url=ofsted_result.get("report_url"),
                            areas_for_improvement=[
                                imp.get("description", "") 
                                for imp in ofsted_result.get("improvements", [])[:5]
                            ]
                        )
                        
                        # Add Ofsted conversation starters (WITH SOURCE URLs!)
                        ofsted_starters = ofsted_result.get("conversation_starters", [])
                        all_starters.extend(ofsted_starters)
                        
                        logger.info(f"✅ Got {len(ofsted_starters)} Ofsted-based starters")
                    else:
                        logger.warning(f"⚠️ Ofsted analysis returned error: {ofsted_result.get('error')}")
                        
            except Exception as e:
                logger.error(f"❌ Ofsted analysis failed: {e}")
                # Continue without Ofsted data
        
        # Step 2: Generate financial-based conversation starters
        # Target ratio: ~60% Ofsted, ~40% Financial (e.g., 3 Ofsted + 2 Financial for 5 total)
        if FEATURES.get("conversation_starters", True):
            try:
                chain = self._get_chain()
                
                # Calculate how many financial starters we need
                # For 5 starters: want 3 Ofsted + 2 Financial
                # For 10 starters: want 6 Ofsted + 4 Financial
                ofsted_count = len(all_starters)
                target_ofsted = int(num_starters * 0.6)  # 60% Ofsted
                target_financial = num_starters - target_ofsted  # 40% Financial
                
                # If we have fewer Ofsted than target, get more financial to compensate
                if ofsted_count < target_ofsted:
                    financial_needed = num_starters - ofsted_count
                else:
                    financial_needed = target_financial
                
                # Always get at least 2 financial starters
                financial_needed = max(2, financial_needed)
                
                logger.info(f"📊 Generating {financial_needed} financial starters (have {ofsted_count} Ofsted)")
                
                response = chain.generate(school, financial_needed)
                all_starters.extend(response.conversation_starters)
                
            except Exception as e:
                logger.error(f"❌ Error generating starters: {e}")
        
        # Combine starters with balanced order: Ofsted first, then Financial
        # This ensures the mix is visible to users
        ofsted_starters = [s for s in all_starters if s.source and s.source.startswith("http")]
        financial_starters = [s for s in all_starters if not s.source or not s.source.startswith("http")]
        
        # Interleave: O, O, F, O, F (for 5 starters with 3 Ofsted + 2 Financial)
        balanced_starters = []
        o_idx, f_idx = 0, 0
        
        for i in range(num_starters):
            # Pattern: 2 Ofsted, then 1 Financial, repeat
            if (i % 3 < 2) and o_idx < len(ofsted_starters):
                balanced_starters.append(ofsted_starters[o_idx])
                o_idx += 1
            elif f_idx < len(financial_starters):
                balanced_starters.append(financial_starters[f_idx])
                f_idx += 1
            elif o_idx < len(ofsted_starters):
                balanced_starters.append(ofsted_starters[o_idx])
                o_idx += 1
            elif f_idx < len(financial_starters):
                balanced_starters.append(financial_starters[f_idx])
                f_idx += 1
        
        # Deduplicate by topic
        seen_topics = set()
        unique_starters = []
        
        for starter in balanced_starters:
            if starter.topic not in seen_topics:
                seen_topics.add(starter.topic)
                unique_starters.append(starter)
        
        # Limit to requested number
        school.conversation_starters = unique_starters[:num_starters]
        
        # Cache the results
        self.cache.set(school.urn, school.conversation_starters)
        
        logger.info(f"✅ Generated {len(school.conversation_starters)} total starters for {school_name}")
        return school

    def get_high_priority_schools(self, limit: int = 10) -> List[School]:
        """
        Get top priority schools for calling.
        
        Returns schools sorted by sales priority.
        """
        schools = self.data_loader.get_all_schools()
        
        # Sort by priority (HIGH first)
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "UNKNOWN": 3}
        sorted_schools = sorted(
            schools, 
            key=lambda s: priority_order.get(s.get_sales_priority(), 3)
        )
        
        return sorted_schools[:limit]
    
    def get_schools_with_agency_spend(self) -> List[School]:
        """Get schools that spend on agency staff"""
        return self.data_loader.get_schools_with_agency_spend()
    
    # =========================================================================
    # CACHE MANAGEMENT
    # =========================================================================
    
    def clear_cache(self, school_name: str = None) -> int:
        """Clear cache for one school or all schools"""
        if school_name:
            school = self.data_loader.get_school_by_name(school_name)
            if school:
                return self.cache.clear(school.urn)
            return 0
        return self.cache.clear()
    
    def refresh_data(self) -> List[School]:
        """Force reload data from source"""
        return self.data_loader.refresh()


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_service_instance: Optional[SchoolIntelligenceService] = None

def get_intelligence_service() -> SchoolIntelligenceService:
    """
    Get the global service instance.
    
    Usage:
        from school_intelligence_service import get_intelligence_service
        service = get_intelligence_service()
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = SchoolIntelligenceService()
    return _service_instance


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Test the service
    service = SchoolIntelligenceService()
    
    # Get all school names
    names = service.get_school_names()
    print(f"\n📚 Available schools ({len(names)}):")
    for name in names[:5]:
        print(f"   • {name}")
    
    # Get statistics
    stats = service.get_statistics()
    print(f"\n📊 Statistics:")
    for k, v in stats.items():
        print(f"   {k}: {v}")
    
    # Get high priority schools
    high_priority = service.get_high_priority_schools(limit=3)
    print(f"\n🎯 High priority schools:")
    for school in high_priority:
        print(f"   • {school.school_name} ({school.get_sales_priority()})")
