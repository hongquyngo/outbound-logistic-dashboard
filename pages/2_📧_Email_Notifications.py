# pages/2_📧_Email_Notifications.py

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.auth import AuthManager
from utils.data_loader import DeliveryDataLoader
from utils.email_sender import EmailSender
from sqlalchemy import text

# Page config
st.set_page_config(
    page_title="Email Notifications",
    page_icon="📧",
    layout="wide"
)

# Check authentication
auth_manager = AuthManager()
if not auth_manager.check_session():
    st.warning("⚠️ Please login to access this page")
    st.stop()

# Check user role - only allow admin and manager
user_role = st.session_state.get('user_role', '')
if user_role not in ['admin', 'manager', 'logistics_manager']:
    st.error("❌ You don't have permission to access this page")
    st.stop()

# Initialize services
data_loader = DeliveryDataLoader()
email_sender = EmailSender()

st.title("📧 Email Notifications")
st.markdown("Send delivery schedules to sales team for the next 4 weeks")
st.markdown("---")

# Get sales list
@st.cache_data(ttl=300)
def get_sales_list():
    """Get list of sales people from database"""
    try:
        query = text("""
        SELECT DISTINCT 
            e.id,
            e.keycloak_id,
            CONCAT(e.first_name, ' ', e.last_name) as name,
            e.email,
            COUNT(DISTINCT d.delivery_id) as active_deliveries
        FROM employees e
        INNER JOIN delivery_full_view d ON d.created_by_email = e.email
        WHERE d.etd >= CURDATE()
            AND d.etd <= DATE_ADD(CURDATE(), INTERVAL 4 WEEK)
            AND d.remaining_quantity_to_deliver > 0
        GROUP BY e.id, e.keycloak_id, e.first_name, e.last_name, e.email
        ORDER BY name
        """)
        
        engine = data_loader.engine
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.error(f"Error loading sales list: {e}")
        return pd.DataFrame()

# Email configuration section
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📋 Sales Selection")
    
    sales_df = get_sales_list()
    
    if not sales_df.empty:
        # Selection mode
        selection_mode = st.radio(
            "Select recipients",
            ["All Sales", "Selected Sales Only"],
            horizontal=True
        )
        
        if selection_mode == "Selected Sales Only":
            selected_sales = st.multiselect(
                "Choose sales people",
                options=sales_df['name'].tolist(),
                default=None,
                format_func=lambda x: f"{x} ({sales_df[sales_df['name']==x]['active_deliveries'].values[0]} deliveries)"
            )
        else:
            selected_sales = sales_df['name'].tolist()
            st.info(f"Will send to all {len(selected_sales)} sales people")
        
        # Show selected sales summary
        if selected_sales:
            selected_df = sales_df[sales_df['name'].isin(selected_sales)]
            st.dataframe(
                selected_df[['name', 'email', 'active_deliveries']],
                use_container_width=True,
                hide_index=True
            )
    else:
        st.warning("No sales with active deliveries found")
        selected_sales = []

with col2:
    st.subheader("⚙️ Email Settings")
    
    # CC options
    include_cc = st.checkbox("Include CC to managers")
    if include_cc:
        cc_emails = st.text_area(
            "CC Email addresses (one per line)",
            placeholder="manager1@company.com\nmanager2@company.com"
        ).strip().split('\n') if include_cc else []
    else:
        cc_emails = []
    
    # Schedule type
    schedule_type = st.radio(
        "Schedule Type",
        ["Send Now", "Preview Only"],
        index=1
    )
    
    # Email template preview
    if st.checkbox("Show email template preview"):
        st.info("Email will include:\n"
                "- Greeting with sales person name\n"
                "- Summary of deliveries\n"
                "- Weekly breakdown with details\n"
                "- Excel attachment with full data\n"
                "- Action items if any")

st.markdown("---")

# Preview section
if selected_sales and st.button("👁️ Preview Email Content", type="secondary"):
    with st.spinner("Generating preview..."):
        # Get data for first selected sales
        preview_sales = sales_df[sales_df['name'] == selected_sales[0]].iloc[0]
        preview_df = data_loader.get_sales_delivery_summary(preview_sales['name'], weeks_ahead=4)
        
        if not preview_df.empty:
            st.subheader(f"📧 Preview for {preview_sales['name']}")
            
            # Show summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Deliveries", len(preview_df))
            with col2:
                st.metric("Total Quantity", f"{preview_df['total_quantity'].sum():,.0f}")
            with col3:
                st.metric("Unique Customers", preview_df['customer'].nunique())
            
            # Show sample data
            st.dataframe(
                preview_df[['delivery_date', 'customer', 'recipient_company', 
                          'total_quantity', 'products']].head(10),
                use_container_width=True
            )
        else:
            st.info("No deliveries found for preview")

# Send emails section
if selected_sales and schedule_type == "Send Now":
    st.markdown("---")
    st.subheader("📤 Send Emails")
    
    # Confirmation
    st.warning(f"⚠️ You are about to send emails to {len(selected_sales)} sales people")
    
    confirm = st.checkbox("I confirm to send these emails")
    
    if confirm and st.button("🚀 Send Emails Now", type="primary"):
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Collect results
        results = []
        errors = []
        
        # Send emails
        for idx, sales_name in enumerate(selected_sales):
            progress = (idx + 1) / len(selected_sales)
            progress_bar.progress(progress)
            status_text.text(f"Sending to {sales_name}... ({idx+1}/{len(selected_sales)})")
            
            try:
                # Get sales info
                sales_info = sales_df[sales_df['name'] == sales_name].iloc[0]
                
                # Get delivery data
                delivery_df = data_loader.get_sales_delivery_summary(sales_name, weeks_ahead=4)
                
                if not delivery_df.empty:
                    # Send email
                    success, message = email_sender.send_delivery_schedule_email(
                        sales_info['email'],
                        sales_name,
                        delivery_df,
                        cc_emails=cc_emails if include_cc else None
                    )
                    
                    results.append({
                        'Sales': sales_name,
                        'Email': sales_info['email'],
                        'Status': '✅ Success' if success else '❌ Failed',
                        'Deliveries': len(delivery_df),
                        'Message': message
                    })
                else:
                    results.append({
                        'Sales': sales_name,
                        'Email': sales_info['email'],
                        'Status': '⚠️ Skipped',
                        'Deliveries': 0,
                        'Message': 'No deliveries found'
                    })
                    
            except Exception as e:
                errors.append(f"Error for {sales_name}: {str(e)}")
                results.append({
                    'Sales': sales_name,
                    'Email': 'N/A',
                    'Status': '❌ Error',
                    'Deliveries': 0,
                    'Message': str(e)
                })
        
        # Clear progress
        progress_bar.empty()
        status_text.empty()
        
        # Show results
        st.success(f"✅ Email process completed!")
        
        # Results summary
        results_df = pd.DataFrame(results)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            success_count = len(results_df[results_df['Status'] == '✅ Success'])
            st.metric("Successful", success_count)
        with col2:
            failed_count = len(results_df[results_df['Status'] == '❌ Failed'])
            st.metric("Failed", failed_count)
        with col3:
            skipped_count = len(results_df[results_df['Status'] == '⚠️ Skipped'])
            st.metric("Skipped", skipped_count)
        
        # Detailed results
        st.dataframe(results_df, use_container_width=True, hide_index=True)
        
        # Show errors if any
        if errors:
            with st.expander("❌ Error Details"):
                for error in errors:
                    st.error(error)
        
        # Log activity
        try:
            log_query = text("""
            INSERT INTO email_logs (
                sender_id, 
                email_type, 
                recipients_count,
                success_count,
                failed_count,
                created_date
            ) VALUES (
                :sender_id,
                'delivery_schedule',
                :total,
                :success,
                :failed,
                NOW()
            )
            """)
            
            with data_loader.engine.connect() as conn:
                conn.execute(log_query, {
                    'sender_id': st.session_state.get('user_id'),
                    'total': len(selected_sales),
                    'success': success_count,
                    'failed': failed_count
                })
                conn.commit()
        except:
            pass  # Ignore logging errors

# Help section
with st.expander("ℹ️ Help & Information"):
    st.markdown("""
    ### How to use this page:
    
    1. **Select Recipients**: Choose to send to all sales or select specific ones
    2. **Configure Settings**: Add CC recipients if needed
    3. **Preview**: Check the email content before sending
    4. **Send**: Confirm and send emails
    
    ### Email Content:
    - Delivery schedule for the next 4 weeks
    - Grouped by week for easy planning
    - Excel attachment with detailed data
    - Highlighting of urgent/out-of-stock items
    
    ### Notes:
    - Emails are sent to the registered email address of each sales person
    - Only deliveries with remaining quantities are included
    - The system uses company SMTP settings for sending emails
    """)