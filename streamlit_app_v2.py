"""
School Research Assistant - Streamlit App (v2)
===============================================
UPDATED: 
- Now merges GIAS contacts + Financial data
- Shows "Local Authority" instead of "Borough"
- Priority based on total staffing spend (not just agency)
- Displays headteacher contact details
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
from data_loader import get_data_loader
from models_v2 import School, ConversationStarter
from config_v2 import get_app_password, LLM_PROVIDER, FEATURES, get_display_label

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
    
    .staffing-spend-high {
        background-color: #2A4D3D;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #28a745;
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
    data_loader = get_data_loader()
    
    st.title("🎓 School Research Assistant")
    st.caption("Powered by AI • London Schools • Financial & Contact Intelligence")
    
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
            st.metric("With Contacts", stats.get("with_contacts", 0))
        with col4:
            st.metric("Local Authorities", stats.get("boroughs", 33))
        
        # Total staffing spend
        st.metric("Total Staffing Spend", stats.get("total_staffing_spend", "N/A"))
        
        st.divider()
        
        # Local Authority filter (not "Borough")
        st.subheader("🏛️ Filter by Local Authority")
        local_authorities = data_loader.get_boroughs()
        selected_la = st.selectbox(
            "Select Local Authority",
            options=["All Local Authorities"] + local_authorities,
            index=0
        )
        
        st.divider()
        
        st.subheader("🎯 Quick Filters")
        
        if st.button("💰 Top Staffing Spenders"):
            st.session_state.filter = "top_spenders"
        if st.button("⚡ High Priority"):
            st.session_state.filter = "high"
        if st.button("📊 All Schools"):
            st.session_state.filter = "all"
    
    # Main content
    st.header("🔍 Search Schools")
    
    # Filter by Local Authority if selected
    if selected_la and selected_la != "All Local Authorities":
        filtered_names = [
            s.school_name for s in data_loader.get_schools_by_borough(selected_la)
        ]
        display_names = sorted(filtered_names)
        st.info(f"Showing {len(display_names)} schools in {selected_la}")
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
        # Show top staffing spenders (not agency-only)
        st.subheader("💰 Top Staffing Spenders (Best Opportunities)")
        st.caption("Schools with largest staffing budgets - opportunities for permanent, temporary & agency placements")
        
        top_spenders = data_loader.get_top_spenders(limit=10, spend_type="total")
        
        if top_spenders:
            for school in top_spenders:
                col1, col2, col3, col4 = st.columns([4, 2, 1, 1])
                
                with col1:
                    if st.button(f"📍 {school.school_name}", key=f"select_{school.urn}"):
                        st.session_state.selected_school = school.school_name
                        st.rerun()
                
                with col2:
                    spend = school.financial.total_teaching_support_costs or 0
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
        st.metric("Local Authority", school.la_name or "Unknown")
    with col3:
        st.metric("Type", school.school_type or "Unknown")
    with col4:
        st.metric("Pupils", school.pupil_count or "Unknown")
    with col5:
        priority = school.get_sales_priority()
        st.metric("Priority", priority)
    
    # Total staffing spend highlight (not just agency)
    if school.financial and school.financial.total_teaching_support_costs:
        spend = school.financial.total_teaching_support_costs
        st.markdown(f"""
        <div class="staffing-spend-high">
            <h3>💰 Total Staffing Budget: £{spend:,.0f}</h3>
            <p>This school invests significantly in staffing - opportunity for permanent, temporary & agency placements.</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "💬 Conversation Starters",
        "👤 Contact Details",
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
    """Display contact information - UPDATED to show GIAS data"""
    
    st.subheader("👤 Key Contacts")
    
    if school.headteacher:
        # Parse headteacher name for title
        head = school.headteacher
        
        st.markdown(f"""
        <div class="contact-card">
            <h4>🎓 {head.full_name}</h4>
            <p><strong>Role:</strong> Headteacher</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Contact details in columns
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**📞 Phone:**")
            if school.phone:
                st.write(school.phone)
            else:
                st.write("Not available")
        
        with col2:
            st.write("**🌐 Website:**")
            if school.website:
                # Clean up website URL
                website = school.website
                if not website.startswith('http'):
                    website = f"http://{website}"
                st.markdown(f"[{school.website}]({website})")
            else:
                st.write("Not available")
    else:
        st.info("No headteacher information available in GIAS data")
    
    st.divider()
    
    # Address section
    st.write("**📍 Address:**")
    address = school.get_full_address()
    if address:
        st.write(address)
    else:
        st.write("Address not available")
    
    # Trust info if available
    if school.trust_name:
        st.divider()
        st.write("**🏛️ Trust:**")
        st.write(school.trust_name)


def display_financial_data(school: School):
    """Display financial data - UPDATED to highlight total staffing"""
    
    st.subheader("💰 Financial Data")
    st.caption("Data from Government Financial Benchmarking Tool")
    
    if school.financial and school.financial.has_financial_data():
        fin = school.financial
        
        # Key metrics row - highlight total staffing first
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if fin.total_teaching_support_costs:
                st.metric("Total Staffing Costs ⭐", f"£{fin.total_teaching_support_costs:,.0f}")
            else:
                st.metric("Total Staffing Costs", "No data")
        
        with col2:
            if fin.total_expenditure:
                st.metric("Total Expenditure", f"£{fin.total_expenditure:,.0f}")
        
        with col3:
            if fin.agency_supply_costs and fin.agency_supply_costs > 0:
                st.metric("Agency Supply", f"£{fin.agency_supply_costs:,.0f}")
            else:
                st.metric("Agency Supply", "£0")
        
        # Detailed breakdown
        st.divider()
        st.write("**Cost Breakdown:**")
        
        costs = [
            ("Total Staffing Costs", fin.total_teaching_support_costs, True),
            ("Teaching Staff (E01)", fin.teaching_staff_costs, False),
            ("Supply Teaching (E02)", fin.supply_teaching_costs, False),
            ("Educational Support (E03)", fin.educational_support_costs, False),
            ("Agency Supply (E26)", fin.agency_supply_costs, False),
            ("Consultancy (E27)", fin.educational_consultancy_costs, False),
        ]
        
        for label, value, highlight in costs:
            if value and value > 0:
                # Calculate per pupil if we have pupil count
                if fin.total_pupils and fin.total_pupils > 0:
                    per_pupil = value / fin.total_pupils
                    if highlight:
                        st.write(f"• **{label}:** £{value:,.0f} (£{per_pupil:,.0f} per pupil) ⭐")
                    else:
                        st.write(f"• {label}: £{value:,.0f} (£{per_pupil:,.0f} per pupil)")
                else:
                    st.write(f"• {label}: £{value:,.0f}")
        
        # Sales insight - now about total staffing
        st.divider()
        if fin.total_teaching_support_costs and fin.total_teaching_support_costs >= 500000:
            st.success(f"""
            💡 **Sales Insight:** This school invests **£{fin.total_teaching_support_costs:,.0f}** in staffing annually. 
            That's a HIGH priority opportunity for permanent, temporary, and agency placements!
            """)
        elif fin.total_teaching_support_costs and fin.total_teaching_support_costs >= 200000:
            st.info(f"""
            💡 **Sales Insight:** This school invests **£{fin.total_teaching_support_costs:,.0f}** in staffing annually. 
            Good opportunity for our recruitment services.
            """)
    else:
        st.info("No financial data available for this school")


def display_full_details(school: School):
    """Display all school details"""
    
    st.subheader("📋 Full School Details")
    
    details = {
        "URN": school.urn,
        "School Name": school.school_name,
        "Local Authority": school.la_name,
        "School Type": school.school_type,
        "Phase": school.phase,
        "Number of Pupils": school.pupil_count,
        "Headteacher": school.headteacher.full_name if school.headteacher else "N/A",
        "Phone": school.phone,
        "Website": school.website,
        "Address": school.get_full_address(),
        "Trust Name": school.trust_name or "N/A",
        "Sales Priority": school.get_sales_priority(),
    }
    
    # Add financial summary
    if school.financial:
        details["Total Staffing Spend"] = school.financial.get_total_staffing_formatted()
        if school.financial.agency_supply_costs:
            details["Agency Spend"] = school.financial.get_agency_spend_formatted()
    
    df = pd.DataFrame([
        {"Field": k, "Value": str(v) if v else "N/A"} 
        for k, v in details.items()
    ])
    
    st.dataframe(df, hide_index=True, use_container_width=True)
    
    # Data source info
    st.divider()
    st.caption(f"📊 Data source: {school.data_source}")


# =============================================================================
# RUN
# =============================================================================

if __name__ == "__main__":
    main()
