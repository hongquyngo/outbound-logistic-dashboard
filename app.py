# app.py - Main Outbound Logistics Dashboard

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from utils.auth import AuthManager
from utils.data_loader import DeliveryDataLoader
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Outbound Logistics Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize auth manager
auth_manager = AuthManager()

# CSS styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .kpi-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: bold;
        color: #0066cc;
    }
    .kpi-label {
        font-size: 1rem;
        color: #666;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

def show_login_page():
    """Display login page"""
    st.markdown('<h1 class="main-header">🚚 Outbound Logistics Dashboard</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            st.subheader("🔐 Login")
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            if st.form_submit_button("Login", use_container_width=True, type="primary"):
                if username and password:
                    success, user_info = auth_manager.authenticate(username, password)
                    if success:
                        auth_manager.login(user_info)
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error(f"❌ {user_info.get('error', 'Login failed')}")
                else:
                    st.error("Please enter both username and password")

def show_main_dashboard():
    """Display main dashboard"""
    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {auth_manager.get_user_display_name()}")
        st.markdown(f"**Role:** {st.session_state.get('user_role', 'N/A')}")
        st.markdown("---")
        
        # Navigation info
        st.info("📌 Use the navigation menu above to access different sections")
        
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            auth_manager.logout()
            st.rerun()
    
    # Main content
    st.markdown('<h1 class="main-header">📦 Outbound Logistics Dashboard</h1>', unsafe_allow_html=True)
    
    # Load data
    data_loader = DeliveryDataLoader()
    
    try:
        with st.spinner("Loading delivery data..."):
            df = data_loader.load_delivery_data()
        
        if df is not None and not df.empty:
            # Date calculations
            today = datetime.now().date()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            month_start = today.replace(day=1)
            
            # Filter data for calculations
            df['etd'] = pd.to_datetime(df['etd'])
            this_week_df = df[(df['etd'].dt.date >= week_start) & (df['etd'].dt.date <= week_end)]
            this_month_df = df[df['etd'].dt.date >= month_start]
            pending_df = df[df['shipment_status'].isin(['PENDING', 'PROCESSING'])]
            overdue_df = df[(df['etd'].dt.date < today) & (df['is_delivered'] == 0)]
            
            # KPI Cards
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown("""
                <div class="kpi-card">
                    <div class="kpi-value">{:,}</div>
                    <div class="kpi-label">This Week Deliveries</div>
                </div>
                """.format(len(this_week_df)), unsafe_allow_html=True)
            
            with col2:
                st.markdown("""
                <div class="kpi-card">
                    <div class="kpi-value">{:,}</div>
                    <div class="kpi-label">This Month Deliveries</div>
                </div>
                """.format(len(this_month_df)), unsafe_allow_html=True)
            
            with col3:
                st.markdown("""
                <div class="kpi-card">
                    <div class="kpi-value">{:,}</div>
                    <div class="kpi-label">Pending Shipments</div>
                </div>
                """.format(len(pending_df)), unsafe_allow_html=True)
            
            with col4:
                st.markdown("""
                <div class="kpi-card">
                    <div class="kpi-value" style="color: #ff4444;">{:,}</div>
                    <div class="kpi-label">Overdue Deliveries</div>
                </div>
                """.format(len(overdue_df)), unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Quick Stats by Status
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Delivery Status Distribution")
                status_counts = df['shipment_status'].value_counts()
                st.bar_chart(status_counts)
            
            with col2:
                st.subheader("🌍 Deliveries by Country")
                country_counts = df['recipient_country_name'].value_counts().head(10)
                st.bar_chart(country_counts)
            
            # Recent Deliveries Table
            st.markdown("---")
            st.subheader("📋 Recent Delivery Requests")
            
            recent_df = df.nlargest(10, 'delivery_id')[['dn_number', 'customer', 'recipient_company', 
                                                         'etd', 'shipment_status', 'fulfillment_status']]
            recent_df['etd'] = recent_df['etd'].dt.strftime('%Y-%m-%d')
            
            # Apply status colors
            def highlight_status(val):
                if val == 'DELIVERED':
                    return 'background-color: #90EE90'
                elif val in ['PENDING', 'PROCESSING']:
                    return 'background-color: #FFE4B5'
                elif val == 'OVERDUE':
                    return 'background-color: #FFB6C1'
                return ''
            
            styled_df = recent_df.style.applymap(highlight_status, subset=['shipment_status'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
        else:
            st.warning("No delivery data available")
            
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        logger.error(f"Dashboard error: {e}")

def main():
    """Main application entry point"""
    # Check authentication
    if not auth_manager.check_session():
        show_login_page()
    else:
        show_main_dashboard()

if __name__ == "__main__":
    main()