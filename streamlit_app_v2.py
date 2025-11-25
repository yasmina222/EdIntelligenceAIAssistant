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
    /* Clean, professional styling */
    .stApp {
        background-color: #FFFFFF;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #1a1a2e;
    }
    
    /* Cards for conversation starters */
    .starter-card {
        background-color: #f8f9fa;
        border-left: 4px solid #0066ff;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    
    .starter-topic {
        font-weight: 600;
        color: #0066ff;
        margin-bottom: 0.5rem;
    }
    
    .starter-detail {
        color: #333;
        line-height: 1.6;
    }
    
    /* Priority badges */
    .priority-high {
        background-color: #dc3545;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    
    .priority-medium {
        background-color: #ffc107;
        color: black;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    
    .priority-low {
        background-color: #28a745;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    
    /* Financial data */
    .financial-highlight {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    /* Contact card */
    .contact-card {
        background-color: #e7f3ff;
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
    st.markdown(f"*Using {LLM_PROVIDER.upper()} for analysis*")
    
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
        
        st.divider()
        
        st.subheader("⚙️ Settings")
        st.caption(f"LLM: {LLM_PROVIDER}")
        st.caption(f"Data source: {stats['data_source']}")
        
        if st.button("Clear Cache"):
            cleared = service.clear_cache()
            st.success(f"Cleared {cleared} cached entries")
    
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
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                st.write(f"**{school.school_name}**")
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
            with col4:
                if st.button("View", key=f"view_{school.urn}"):
                    st.session_state.selected_school = school.school_name
                    st.rerun()


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
                
                if starter.source:
                    st.caption(f"📊 Source: {starter.source}")
                
                # Copy button
                st.code(starter.detail, language=None)
    
    # Generate button
    col1, col2 = st.columns([1, 3])
    
    with col1:
        num_starters = st.number_input(
            "How many?", 
            min_value=1, 
            max_value=10, 
            value=5
        )
    
    with col2:
        if st.button("🤖 Generate Conversation Starters", type="primary"):
            with st.spinner("Generating insights with AI..."):
                # This makes the LLM call
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
    
    # LLM Context (what gets sent to the AI)
    with st.expander("🤖 View LLM Context (what the AI sees)"):
        st.code(school.to_llm_context())


# =============================================================================
# RUN THE APP
# =============================================================================

if __name__ == "__main__":
    main()
