"""
School Research Assistant - Streamlit App (v2)
UPDATED: Now displays total spend values and supports 2,400 London schools
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import logging
import sys
import os
from pathlib import Path

# Add the project root to Python path
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
    
    st.title("🎓 School Research Assistant")
    
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
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
        color: #E8E8E8 !important;
    }
    
    .stApp p, .stApp span, .stApp label, .stApp div {
        color: #D0D0D0 !important;
    }
    
    .stMarkdown, .stMarkdown p, .stMarkdown span {
        color: #D0D0D0 !important;
    }
    
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {
        color: #E8E8E8 !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #D0D0D0 !important;
    }
    
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
    
    .financial-highlight {
        background-color: #3D3D2A;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    .agency-spend-high {
        background-color: #5D2A2A;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #dc3545;
    }
    
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
    
    if not check_password():
        return
    
    service = get_intelligence_service()
    
    st.title("🎓 School Research Assistant")
    st.caption("Powered by AI • 2,400+ London Schools • Financial Intelligence")
    
    # Load schools
    with st.spinner("Loading schools..."):
        school_names = service.get_school_names()
        stats = service.get_statistics()
    
    # Sidebar
    with st.sidebar:
        st.header("📊 Dashboard")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Schools", f"{stats['total_schools']:,}")
        with col2:
            st.metric("High Priority", stats["high_priority"])
        
        col3, col4 = st.columns(2)
        with col3:
            st.metric("With Agency Spend", stats["with_agency_spend"])
        with col4:
            st.metric("Boroughs", stats.get("boroughs", 33))
        
        # Total agency spend
        st.metric("Total Agency Spend", stats.get("total_agency_spend", "N/A"))
        
        st.divider()
        
        # Borough filter
        st.subheader("🏛️ Filter by Borough")
        from data_loader import get_data_loader
        boroughs = get_data_loader().get_boroughs()
        selected_borough = st.selectbox(
            "Select Borough",
            options=["All Boroughs"] + boroughs,
            index=0
        )
        
        st.divider()
        
        st.subheader("🎯 Quick Filters")
        
        if st.button("🔥 Top Agency Spenders"):
            st.session_state.filter = "top_spenders"
        if st.button("⚡ High Priority"):
            st.session_state.filter = "high"
        if st.button("📊 All Schools"):
            st.session_state.filter = "all"
    
    # Main content
    st.header("🔍 Search Schools")
    
    # Filter by borough if selected
    if selected_borough and selected_borough != "All Boroughs":
        filtered_names = [
            s.school_name for s in get_data_loader().get_schools_by_borough(selected_borough)
        ]
        display_names = sorted(filtered_names)
        st.info(f"Showing {len(display_names)} schools in {selected_borough}")
    else:
        display_names = school_names
    
    # School selector
    selected_school_name = st.selectbox(
        "Select a school",
        options=[""] + display_names,
        index=0,
        placeholder="Choose a school...",
        help="Select a school to view details and generate conversation starters"
    )
    
    if selected_school_name:
        school = service.get_school_by_name(selected_school_name)
        if school:
            display_school(school, service)
        else:
            st.error(f"School not found: {selected_school_name}")
    else:
        # Show top agency spenders
        st.subheader("🔥 Top Agency Spenders (Best Sales Opportunities)")
        
        top_spenders = get_data_loader().get_top_agency_spenders(limit=10)
        
        if top_spenders:
            for school in top_spenders:
                col1, col2, col3, col4 = st.columns([4, 2, 1, 1])
                
                with col1:
                    if st.button(f"📍 {school.school_name}", key=f"select_{school.urn}"):
                        st.session_state.selected_school = school.school_name
                        st.rerun()
                
                with col2:
                    spend = school.financial.agency_supply_costs or 0
                    st.markdown(f"**£{spend:,.0f}**")
                
                with col3:
                    st.caption(school.la_name or "")
                
                with col4:
                    priority = school.get_sales_priority()
                    if priority == "HIGH":
                        st.markdown('<span class="priority-high">HIGH</span>', unsafe_allow_html=True)
                    elif priority == "MEDIUM":
                        st.markdown('<span class="priority-medium">MED</span>', unsafe_allow_html=True)


def display_school(school: School, service):
    """Display school details and conversation starters"""
    
    st.subheader(f"🏫 {school.school_name}")
    
    # Quick info row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("URN", school.urn)
    with col2:
        st.metric("Borough", school.la_name or "Unknown")
    with col3:
        st.metric("Type", school.school_type or "Unknown")
    with col4:
        st.metric("Pupils", school.pupil_count or "Unknown")
    with col5:
        priority = school.get_sales_priority()
        st.metric("Priority", priority)
    
    # Agency spend highlight
    if school.financial and school.financial.has_agency_spend():
        spend = school.financial.agency_supply_costs
        st.markdown(f"""
        <div class="agency-spend-high">
            <h3>🔥 Agency Spend: £{spend:,.0f}</h3>
            <p>This school is already spending on agency staff - strong sales opportunity!</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "💬 Conversation Starters",
        "👤 Contact Info",
        "💰 Financial Data",
        "📋 Full Details"
    ])
    
    with tab1:
        display_conversation_starters(school, service)
    
    with tab2:
        display_contact_info(school)
    
    with tab3:
        display_financial_data(school)
    
    with tab4:
        display_full_details(school)


def display_conversation_starters(school: School, service):
    """Display or generate conversation starters"""
    
    st.subheader("💬 Conversation Starters")
    
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
                    if starter.source.startswith("http"):
                        st.markdown(f"📎 **Source:** [View Ofsted Report]({starter.source})")
                    else:
                        st.caption(f"📊 Source: {starter.source}")
                
                st.code(starter.detail, language=None)
    
    # Ofsted info
    if school.ofsted and school.ofsted.rating:
        st.info(f"📋 **Ofsted Rating:** {school.ofsted.rating} | **Inspected:** {school.ofsted.inspection_date or 'Unknown'}")
        if school.ofsted.report_url:
            st.markdown(f"[📄 View Full Ofsted Report]({school.ofsted.report_url})")
    
    st.divider()
    
    # Generate button
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        num_starters = st.number_input("How many?", min_value=1, max_value=10, value=5)
    
    with col2:
        include_ofsted = st.checkbox("Include Ofsted", value=True, help="Adds 10-15 seconds")
    
    with col3:
        if st.button("🚀 Generate Conversation Starters", type="primary"):
            if include_ofsted:
                with st.spinner("🔍 Analyzing Ofsted + generating insights..."):
                    school_with_starters = service.get_school_intelligence_with_ofsted(
                        school.school_name,
                        force_refresh=True,
                        num_starters=num_starters,
                        include_ofsted=True
                    )
            else:
                with st.spinner("Generating insights with AI..."):
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
            <p><strong>Website:</strong> <a href="{school.website}" target="_blank">{school.website or 'Not available'}</a></p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No headteacher information available")
    
    st.write("**Address:**")
    st.write(school.get_full_address() or "Address not available")


def display_financial_data(school: School):
    """Display financial data - UPDATED FOR TOTAL SPEND"""
    
    st.subheader("💰 Financial Data")
    
    if school.financial:
        fin = school.financial
        
        # Key metrics row
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if fin.total_expenditure:
                st.metric("Total Expenditure", f"£{fin.total_expenditure:,.0f}")
        
        with col2:
            if fin.teaching_staff_costs:
                st.metric("Teaching Staff (E01)", f"£{fin.teaching_staff_costs:,.0f}")
        
        with col3:
            if fin.agency_supply_costs:
                st.metric("Agency Supply (E26)", f"£{fin.agency_supply_costs:,.0f}")
        
        # Detailed breakdown
        st.divider()
        st.write("**Cost Breakdown:**")
        
        costs = [
            ("Teaching Staff (E01)", fin.teaching_staff_costs),
            ("Supply Teaching (E02)", fin.supply_teaching_costs),
            ("Educational Support (E03)", fin.educational_support_costs),
            ("Agency Supply (E26)", fin.agency_supply_costs),
            ("Consultancy (E27)", fin.educational_consultancy_costs),
        ]
        
        for label, value in costs:
            if value and value > 0:
                # Calculate per pupil if we have pupil count
                if fin.total_pupils and fin.total_pupils > 0:
                    per_pupil = value / fin.total_pupils
                    st.write(f"• **{label}:** £{value:,.0f} (£{per_pupil:,.0f} per pupil)")
                else:
                    st.write(f"• **{label}:** £{value:,.0f}")
        
        # Sales insight
        if fin.has_agency_spend():
            spend = fin.agency_supply_costs
            st.warning(f"""
            💡 **Sales Insight:** This school is spending **£{spend:,.0f}** on agency staff annually. 
            That's a significant budget we could help them use more effectively!
            """)
    else:
        st.info("No financial data available")


def display_full_details(school: School):
    """Display all school details"""
    
    st.subheader("📋 Full School Details")
    
    details = {
        "URN": school.urn,
        "School Name": school.school_name,
        "Local Authority": school.la_name,
        "School Type": school.school_type,
        "Phase": school.phase,
        "Pupil Count": school.pupil_count,
        "Address": school.get_full_address(),
        "Phone": school.phone,
        "Website": school.website,
        "Trust Name": school.trust_name or "N/A",
        "Sales Priority": school.get_sales_priority(),
    }
    
    # Add financial summary
    if school.financial:
        details["Agency Spend"] = school.financial.get_agency_spend_formatted()
        details["Agency Per Pupil"] = school.financial.get_agency_per_pupil_formatted()
    
    df = pd.DataFrame([
        {"Field": k, "Value": str(v) if v else "N/A"} 
        for k, v in details.items()
    ])
    
    st.dataframe(df, hide_index=True, use_container_width=True)


# =============================================================================
# RUN
# =============================================================================

if __name__ == "__main__":
    main()
