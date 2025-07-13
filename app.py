# app.py - Main Outbound Logistics Dashboard

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from utils.auth import AuthManager
from utils.data_loader import DeliveryDataLoader
import plotly.graph_objects as go
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

# App version - Updated
APP_VERSION = "1.2.0"

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
    .alert-card {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .status-overdue {
        color: #d32f2f;
        font-weight: bold;
    }
    .status-due-today {
        color: #f57c00;
        font-weight: bold;
    }
    .status-on-schedule {
        color: #388e3c;
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
        
        # App version
        st.caption(f"Version: {APP_VERSION}")
        
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
            overdue_df = df[df['delivery_timeline_status'] == 'Overdue']
            due_today_df = df[df['delivery_timeline_status'] == 'Due Today']
            
            # Enhanced KPI Cards - Row 1
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.markdown("""
                <div class="kpi-card">
                    <div class="kpi-value">{:,}</div>
                    <div class="kpi-label">This Week Deliveries</div>
                </div>
                """.format(this_week_df['delivery_id'].nunique()), unsafe_allow_html=True)
            
            with col2:
                st.markdown("""
                <div class="kpi-card">
                    <div class="kpi-value">{:,}</div>
                    <div class="kpi-label">This Month Deliveries</div>
                </div>
                """.format(this_month_df['delivery_id'].nunique()), unsafe_allow_html=True)
            
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
                """.format(overdue_df['delivery_id'].nunique()), unsafe_allow_html=True)
            
            with col5:
                st.markdown("""
                <div class="kpi-card">
                    <div class="kpi-value" style="color: #f39c12;">{:,}</div>
                    <div class="kpi-label">Due Today</div>
                </div>
                """.format(due_today_df['delivery_id'].nunique()), unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Alert Section (NEW)
            if not overdue_df.empty:
                st.markdown("""
                <div class="alert-card">
                    <h4>⚠️ Attention Required</h4>
                    <p>There are <strong>{}</strong> overdue deliveries with a maximum delay of <strong>{}</strong> days. 
                    Please coordinate with the logistics team to resolve these urgently.</p>
                </div>
                """.format(
                    overdue_df['delivery_id'].nunique(),
                    overdue_df['days_overdue'].max()
                ), unsafe_allow_html=True)
            
            # Quick Stats by Status and Timeline
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Shipment Status Distribution")
                # Use Vietnamese status names
                status_counts = df['shipment_status_vn'].value_counts()
                fig1 = go.Figure(data=[
                    go.Bar(
                        x=status_counts.index,
                        y=status_counts.values,
                        marker_color=['#2ecc71' if 'Đã giao' in x else 
                                    '#3498db' if 'Đang giao' in x else
                                    '#f39c12' if 'Đã xuất kho' in x else
                                    '#e74c3c' for x in status_counts.index]
                    )
                ])
                fig1.update_layout(
                    xaxis_title="Status",
                    yaxis_title="Count",
                    showlegend=False,
                    height=300
                )
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                st.subheader("⏱️ Delivery Timeline Analysis")
                timeline_counts = df['delivery_timeline_status'].value_counts()
                fig2 = go.Figure(data=[
                    go.Pie(
                        labels=timeline_counts.index,
                        values=timeline_counts.values,
                        marker_colors=['#2ecc71' if x == 'Completed' else
                                     '#3498db' if x == 'On Schedule' else
                                     '#f39c12' if x == 'Due Today' else
                                     '#e74c3c' if x == 'Overdue' else
                                     '#95a5a6' for x in timeline_counts.index]
                    )
                ])
                fig2.update_layout(height=300)
                st.plotly_chart(fig2, use_container_width=True)
            
            # Product Analysis Section (NEW)
            st.markdown("---")
            st.subheader("📦 Product Fulfillment Analysis")
            
            col1, col2, col3 = st.columns(3)
            
            # Get unique products with issues
            out_of_stock_products = df[df['product_fulfillment_status'] == 'Out of Stock']['product_pn'].nunique()
            partial_fulfill_products = df[df['product_fulfillment_status'] == 'Can Fulfill Partial']['product_pn'].nunique()
            avg_fulfill_rate = df.groupby('product_id')['product_fulfill_rate_percent'].first().mean()
            
            with col1:
                st.metric("Products Out of Stock", f"{out_of_stock_products:,}")
            
            with col2:
                st.metric("Products Partial Fulfillment", f"{partial_fulfill_products:,}")
            
            with col3:
                st.metric("Avg Product Fulfillment Rate", f"{avg_fulfill_rate:.1f}%")
            
            # Recent Deliveries Table with enhanced information
            st.markdown("---")
            st.subheader("📋 Recent Delivery Requests")
            
            recent_df = df.nlargest(10, 'delivery_id')[[
                'dn_number', 'customer', 'recipient_company', 
                'etd', 'delivery_timeline_status', 'shipment_status_vn',
                'product_fulfillment_status', 'days_overdue'
            ]].copy()
            
            recent_df['etd'] = recent_df['etd'].dt.strftime('%Y-%m-%d')
            recent_df = recent_df.rename(columns={
                'delivery_timeline_status': 'Timeline',
                'shipment_status_vn': 'Status',
                'product_fulfillment_status': 'Fulfillment'
            })
            
            # Apply status colors
            def highlight_timeline(row):
                styles = [''] * len(row)
                if row['Timeline'] == 'Overdue':
                    styles[4] = 'background-color: #ffcccb'
                elif row['Timeline'] == 'Due Today':
                    styles[4] = 'background-color: #ffe4b5'
                elif row['Timeline'] == 'On Schedule':
                    styles[4] = 'background-color: #c8e6c9'
                elif row['Timeline'] == 'Completed':
                    styles[4] = 'background-color: #e0e0e0'
                
                if row['Fulfillment'] == 'Out of Stock':
                    styles[6] = 'background-color: #ffcccb'
                elif row['Fulfillment'] == 'Can Fulfill Partial':
                    styles[6] = 'background-color: #ffe4b5'
                
                return styles
            
            styled_df = recent_df.style.apply(highlight_timeline, axis=1)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            # Overdue Details (NEW)
            if not overdue_df.empty:
                with st.expander("🚨 Overdue Delivery Details", expanded=False):
                    overdue_summary = data_loader.get_overdue_deliveries()
                    if not overdue_summary.empty:
                        st.dataframe(
                            overdue_summary[['dn_number', 'customer', 'days_overdue', 
                                           'remaining_quantity_to_deliver', 'product_fulfillment_status']]
                            .style.format({'remaining_quantity_to_deliver': '{:,.0f}'}),
                            use_container_width=True
                        )
            
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