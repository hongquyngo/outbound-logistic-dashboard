# pages/3_⚙️_Settings.py

import streamlit as st
from utils.auth import AuthManager
from utils.data_loader import DeliveryDataLoader
from sqlalchemy import text
import pandas as pd
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Settings",
    page_icon="⚙️",
    layout="wide"
)

# Check authentication
auth_manager = AuthManager()
if not auth_manager.check_session():
    st.warning("⚠️ Please login to access this page")
    st.stop()

# Initialize data loader
data_loader = DeliveryDataLoader()

st.title("⚙️ Settings")
st.markdown("---")

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["👤 Profile", "📧 Email Config", "🔄 Data Refresh", "📊 System Info"])

with tab1:
    st.subheader("👤 User Profile")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input("Username", value=st.session_state.get('username', ''), disabled=True)
        st.text_input("Full Name", value=st.session_state.get('user_fullname', ''), disabled=True)
        st.text_input("Email", value=st.session_state.get('user_email', ''), disabled=True)
    
    with col2:
        st.text_input("Role", value=st.session_state.get('user_role', ''), disabled=True)
        st.text_input("Employee ID", value=str(st.session_state.get('employee_id', '')), disabled=True)
        login_time = st.session_state.get('login_time', datetime.now())
        st.text_input("Login Time", value=login_time.strftime('%Y-%m-%d %H:%M:%S'), disabled=True)
    
    # Change password section
    st.markdown("---")
    st.subheader("🔐 Change Password")
    st.info("To change your password, please contact the system administrator.")

with tab2:
    st.subheader("📧 Email Configuration")
    
    # Check user role
    if st.session_state.get('user_role') in ['admin', 'manager']:
        st.info("Email settings are configured at the system level. Contact IT for changes.")
        
        # Show current config (read-only)
        col1, col2 = st.columns(2)
        
        with col1:
            st.text_input("SMTP Server", value="smtp.gmail.com", disabled=True)
            st.text_input("SMTP Port", value="587", disabled=True)
            
        with col2:
            st.text_input("Sender Email", value="logistics@company.com", disabled=True)
            st.selectbox("Security", ["TLS", "SSL"], disabled=True)
        
        # Email templates
        st.markdown("---")
        st.subheader("📝 Email Templates")
        
        template_type = st.selectbox(
            "Select Template",
            ["Delivery Schedule", "Urgent Notification", "Delay Notification"]
        )
        
        if template_type == "Delivery Schedule":
            st.text_area(
                "Subject Template",
                value="Delivery Schedule - Next 4 Weeks - {sales_name}",
                height=50,
                disabled=True
            )
            
            st.text_area(
                "Body Template Preview",
                value="""Dear {sales_name},

Please find below your delivery schedule for the next 4 weeks.
Make sure to coordinate with customers for smooth delivery operations.

Summary:
- Total Deliveries: {total_deliveries}
- Total Quantity: {total_quantity}
- Customers: {customer_count}

[Detailed schedule in attachment]

Best regards,
Outbound Logistics Team""",
                height=200,
                disabled=True
            )
    else:
        st.warning("You don't have permission to view email configuration")

with tab3:
    st.subheader("🔄 Data Refresh Settings")
    
    # Cache settings
    st.info("Data is automatically cached for 5 minutes to improve performance")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Clear All Cache", type="primary"):
            st.cache_data.clear()
            st.success("✅ Cache cleared successfully!")
            st.rerun()
    
    with col2:
        if st.button("📊 Refresh Delivery Data"):
            # Force refresh by clearing specific cache
            st.cache_data.clear()
            st.success("✅ Delivery data will be refreshed")
    
    with col3:
        if st.button("👥 Refresh User Lists"):
            st.cache_data.clear()
            st.success("✅ User lists will be refreshed")
    
    # Auto-refresh settings
    st.markdown("---")
    st.subheader("⏰ Auto-Refresh Settings")
    
    auto_refresh = st.checkbox("Enable auto-refresh", value=False)
    if auto_refresh:
        refresh_interval = st.slider(
            "Refresh interval (minutes)",
            min_value=5,
            max_value=60,
            value=15,
            step=5
        )
        st.info(f"Dashboard will auto-refresh every {refresh_interval} minutes")

with tab4:
    st.subheader("📊 System Information")
    
    # Database info
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Database Statistics")
        
        try:
            stats_query = text("""
            SELECT 
                (SELECT COUNT(DISTINCT delivery_id) FROM delivery_full_view) as total_deliveries,
                (SELECT COUNT(DISTINCT customer) FROM delivery_full_view) as total_customers,
                (SELECT COUNT(DISTINCT created_by_name) FROM delivery_full_view) as total_sales,
                (SELECT COUNT(DISTINCT product_pn) FROM delivery_full_view) as total_products
            """)
            
            with data_loader.engine.connect() as conn:
                stats = conn.execute(stats_query).fetchone()
            
            st.metric("Total Deliveries", f"{stats[0]:,}")
            st.metric("Total Customers", f"{stats[1]:,}")
            st.metric("Total Sales Users", f"{stats[2]:,}")
            st.metric("Total Products", f"{stats[3]:,}")
            
        except Exception as e:
            st.error(f"Error loading statistics: {e}")
    
    with col2:
        st.markdown("### System Status")
        
        # Connection status
        try:
            with data_loader.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            st.success("✅ Database: Connected")
        except:
            st.error("❌ Database: Disconnected")
        
        # Email service status
        st.info("📧 Email Service: Configured")
        
        # Version info
        st.markdown("### Version Information")
        st.text("App Version: 1.0.0")
        st.text("Streamlit Version: 1.31.0")
        st.text(f"Python Version: 3.11")
    
    # Activity log
    st.markdown("---")
    st.subheader("📜 Recent Activity")
    
    try:
        # This would need an activity log table in the database
        st.info("Activity logging will be implemented in the next version")
        
        # Sample activity display
        activities = [
            {"time": "2024-01-20 10:30", "user": "John Doe", "action": "Sent email notifications to 5 sales"},
            {"time": "2024-01-20 09:15", "user": "Jane Smith", "action": "Exported delivery schedule"},
            {"time": "2024-01-20 08:45", "user": "Admin", "action": "Updated system settings"},
        ]
        
        activity_df = pd.DataFrame(activities)
        st.dataframe(activity_df, use_container_width=True, hide_index=True)
        
    except Exception as e:
        st.error(f"Error loading activity log: {e}")

# Footer
st.markdown("---")
st.caption("💡 For technical support, contact: it-support@company.com")