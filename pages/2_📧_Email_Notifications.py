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
st.markdown("Send delivery schedules and urgent alerts to sales team")
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
            COUNT(DISTINCT d.delivery_id) as active_deliveries,
            e.manager_id,
            m.email as manager_email,
            CONCAT(m.first_name, ' ', m.last_name) as manager_name
        FROM employees e
        LEFT JOIN employees m ON e.manager_id = m.id
        INNER JOIN delivery_full_view d ON d.created_by_email = e.email
        WHERE d.etd >= CURDATE()
            AND d.etd <= DATE_ADD(CURDATE(), INTERVAL 4 WEEK)
            AND d.remaining_quantity_to_deliver > 0
        GROUP BY e.id, e.keycloak_id, e.first_name, e.last_name, e.email, e.manager_id, m.email, m.first_name, m.last_name
        ORDER BY name
        """)
        
        engine = data_loader.engine
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.error(f"Error loading sales list: {e}")
        return pd.DataFrame()

# Get sales list for overdue alerts
@st.cache_data(ttl=300)
def get_sales_list_overdue():
    """Get list of sales people with overdue or due today deliveries"""
    try:
        query = text("""
        SELECT DISTINCT 
            e.id,
            e.keycloak_id,
            CONCAT(e.first_name, ' ', e.last_name) as name,
            e.email,
            COUNT(DISTINCT CASE WHEN d.delivery_timeline_status = 'Overdue' THEN d.delivery_id END) as overdue_deliveries,
            COUNT(DISTINCT CASE WHEN d.delivery_timeline_status = 'Due Today' THEN d.delivery_id END) as due_today_deliveries,
            e.manager_id,
            m.email as manager_email,
            CONCAT(m.first_name, ' ', m.last_name) as manager_name
        FROM employees e
        LEFT JOIN employees m ON e.manager_id = m.id
        INNER JOIN delivery_full_view d ON d.created_by_email = e.email
        WHERE d.delivery_timeline_status IN ('Overdue', 'Due Today')
            AND d.remaining_quantity_to_deliver > 0
            AND d.shipment_status NOT IN ('DELIVERED', 'COMPLETED')
        GROUP BY e.id, e.keycloak_id, e.first_name, e.last_name, e.email, e.manager_id, m.email, m.first_name, m.last_name
        HAVING (overdue_deliveries > 0 OR due_today_deliveries > 0)
        ORDER BY overdue_deliveries DESC, due_today_deliveries DESC, name
        """)
        
        engine = data_loader.engine
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.error(f"Error loading sales list for overdue alerts: {e}")
        return pd.DataFrame()

# Email configuration section
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📋 Sales Selection")
    
    # Get notification type from session state first
    notification_type = st.session_state.get('notification_type', '📅 Delivery Schedule')
    
    # Special handling for Custom Clearance
    if notification_type == "🛃 Custom Clearance":
        st.info("📌 Custom Clearance notifications will be sent to the customs team with EPE & Foreign customer deliveries")
        
        # Show summary of what will be included
        customs_summary = data_loader.get_customs_clearance_summary()
        if not customs_summary.empty:
            col1_1, col1_2, col1_3 = st.columns(3)
            with col1_1:
                st.metric("EPE Deliveries", customs_summary['epe_deliveries'].sum())
            with col1_2:
                st.metric("Foreign Deliveries", customs_summary['foreign_deliveries'].sum())
            with col1_3:
                st.metric("Total Countries", customs_summary['countries'].sum())
            
            # Show filter info
            st.caption("🔍 Auto-applied filters: EPE Companies + Foreign Customers | Next 4 weeks | Not delivered")
        else:
            st.warning("No customs clearance deliveries found for the next 4 weeks")
        
        selected_sales = []  # No sales selection for customs
    else:
        # Original sales selection logic for other notification types
        if notification_type == "🚨 Overdue Alerts":
            sales_df = get_sales_list_overdue()
        else:
            sales_df = get_sales_list()
        
        if not sales_df.empty:
            # Selection mode
            selection_mode = st.radio(
                "Select recipients",
                ["All Sales", "Selected Sales Only"],
                horizontal=True
            )
            
            if selection_mode == "Selected Sales Only":
                # Format function based on notification type
                if notification_type == "🚨 Overdue Alerts":
                    format_func = lambda x: f"{x} (Overdue: {sales_df[sales_df['name']==x]['overdue_deliveries'].values[0]}, Due Today: {sales_df[sales_df['name']==x]['due_today_deliveries'].values[0]})"
                else:
                    format_func = lambda x: f"{x} ({sales_df[sales_df['name']==x]['active_deliveries'].values[0]} deliveries)"
                
                selected_sales = st.multiselect(
                    "Choose sales people",
                    options=sales_df['name'].tolist(),
                    default=None,
                    format_func=format_func
                )
            else:
                selected_sales = sales_df['name'].tolist()
                if notification_type == "🚨 Overdue Alerts":
                    total_overdue = sales_df['overdue_deliveries'].sum()
                    total_due_today = sales_df['due_today_deliveries'].sum()
                    st.info(f"Will send to {len(selected_sales)} sales people with {total_overdue} overdue and {total_due_today} due today deliveries")
                else:
                    st.info(f"Will send to all {len(selected_sales)} sales people")
            
            # Show selected sales summary
            if selected_sales:
                selected_df = sales_df[sales_df['name'].isin(selected_sales)]
                if notification_type == "🚨 Overdue Alerts":
                    display_df = selected_df[['name', 'email', 'overdue_deliveries', 'due_today_deliveries']]
                else:
                    display_df = selected_df[['name', 'email', 'active_deliveries']]
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True
                )
        else:
            if notification_type == "🚨 Overdue Alerts":
                st.warning("No sales with overdue or due today deliveries found")
            else:
                st.warning("No sales with active deliveries found")
            selected_sales = []

with col2:
    st.subheader("⚙️ Email Settings")
    
    # Notification Type Selection (UPDATED)
    notification_type = st.radio(
        "📧 Notification Type",
        ["📅 Delivery Schedule", "🚨 Overdue Alerts", "🛃 Custom Clearance"],
        index=["📅 Delivery Schedule", "🚨 Overdue Alerts", "🛃 Custom Clearance"].index(
            st.session_state.get('notification_type', '📅 Delivery Schedule')
        ),
        help="""
        Delivery Schedule: Next 4 weeks schedule
        Overdue Alerts: Only overdue and due today deliveries
        Custom Clearance: EPE & Foreign customers for customs team
        """
    )
    
    # Store in session state to reload sales list if changed
    if notification_type != st.session_state.get('notification_type'):
        st.session_state.notification_type = notification_type
        st.rerun()
    
    # Special email settings for Custom Clearance
    if notification_type == "🛃 Custom Clearance":
        # Default recipient for customs
        default_recipient = st.text_input(
            "Primary Recipient",
            value="custom.clearance@prostech.vn",
            disabled=True,
            help="Default email for customs clearance team"
        )
        
        # Additional CC
        additional_cc = st.text_area(
            "Additional CC Recipients (one per line)",
            placeholder="manager@company.com\nlogistics@company.com",
            help="Add any additional recipients for customs notifications"
        )
        
        cc_emails = [default_recipient]
        if additional_cc:
            additional_emails = [email.strip() for email in additional_cc.split('\n') if email.strip()]
            cc_emails.extend(additional_emails)
        
        # Remove duplicates
        cc_emails = list(dict.fromkeys(cc_emails))
        
    else:
        # Original CC logic for sales notifications
        include_cc = st.checkbox("Include CC to managers", value=True)
        
        if include_cc and selected_sales and 'sales_df' in locals():
            # Get unique manager emails from selected sales
            selected_df = sales_df[sales_df['name'].isin(selected_sales)]
            manager_emails = selected_df[selected_df['manager_email'].notna()]['manager_email'].unique().tolist()
            
            # Show auto-detected managers
            if manager_emails:
                st.info(f"Auto-detected managers: {', '.join(manager_emails)}")
            
            # Additional CC emails
            additional_cc = st.text_area(
                "Additional CC Email addresses (one per line)",
                placeholder="manager1@company.com\nmanager2@company.com",
                help="Manager emails are automatically included. Add any additional recipients here."
            ).strip()
            
            # Combine manager emails with additional emails
            cc_emails = manager_emails.copy()
            if additional_cc:
                additional_emails = [email.strip() for email in additional_cc.split('\n') if email.strip()]
                cc_emails.extend(additional_emails)
            
            # Remove duplicates while preserving order
            cc_emails = list(dict.fromkeys(cc_emails))
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
        if notification_type == "📅 Delivery Schedule":
            st.info("Email will include:\n"
                    "- Greeting with sales person name\n"
                    "- Summary of deliveries for next 4 weeks\n"
                    "- Weekly breakdown with details\n"
                    "- Excel attachment with full data\n"
                    "- Calendar integration for planning")
        elif notification_type == "🚨 Overdue Alerts":
            st.info("Email will include:\n"
                    "- 🚨 Urgent alert header\n"
                    "- Summary of overdue and due today items\n"
                    "- Overdue deliveries sorted by days overdue\n"
                    "- Due today deliveries with priority\n"
                    "- Excel attachment with urgent items only\n"
                    "- Action items and contacts")
        else:  # Custom Clearance
            st.info("Email will include:\n"
                    "- 🛃 Custom clearance schedule header\n"
                    "- EPE companies (export at place) summary\n"
                    "- Foreign customers by country\n"
                    "- Weekly timeline for customs planning\n"
                    "- Excel with separate EPE and Foreign sheets\n"
                    "- Calendar events for customs deadlines")

st.markdown("---")

# Preview section
if notification_type == "🛃 Custom Clearance":
    # Custom Clearance Preview
    if st.button("👁️ Preview Email Content", type="secondary"):
        with st.spinner("Generating customs clearance preview..."):
            preview_df = data_loader.get_customs_clearance_schedule()
            
            if not preview_df.empty:
                st.subheader("📧 Preview for Custom Clearance Team")
                
                # Show summary metrics
                col1, col2, col3, col4 = st.columns(4)
                
                # EPE metrics
                epe_df = preview_df[preview_df['is_epe_company'] == 'Yes']
                foreign_df = preview_df[preview_df['customer_country_code'] != preview_df['legal_entity_country_code']]
                
                with col1:
                    st.metric("EPE Deliveries", epe_df['delivery_id'].nunique())
                with col2:
                    st.metric("Foreign Deliveries", foreign_df['delivery_id'].nunique())
                with col3:
                    st.metric("Total Quantity", f"{preview_df['remaining_quantity_to_deliver'].sum():,.0f}")
                with col4:
                    countries = preview_df[preview_df['customer_country_code'] != preview_df['legal_entity_country_code']]['customer_country_name'].nunique()
                    st.metric("Countries", countries)
                
                # Show sample data grouped by type
                st.markdown("#### 📦 EPE Companies (Xuất khẩu tại chỗ)")
                if not epe_df.empty:
                    epe_display = epe_df.head(5)[['delivery_date', 'customer', 'recipient_company', 
                                                  'pt_code', 'product_pn', 'remaining_quantity_to_deliver']]
                    st.dataframe(epe_display, use_container_width=True, hide_index=True)
                else:
                    st.info("No EPE deliveries in the next 4 weeks")
                
                st.markdown("#### 🌍 Foreign Customers")
                if not foreign_df.empty:
                    foreign_display = foreign_df.head(5)[['delivery_date', 'customer_country_name', 'customer', 
                                                         'pt_code', 'product_pn', 'remaining_quantity_to_deliver']]
                    st.dataframe(foreign_display, use_container_width=True, hide_index=True)
                else:
                    st.info("No foreign deliveries in the next 4 weeks")
            else:
                st.warning("No customs clearance deliveries found for preview")
    
elif selected_sales and st.button("👁️ Preview Email Content", type="secondary"):
    # Original preview logic for sales notifications
    with st.spinner("Generating preview..."):
        # Get data for first selected sales
        preview_sales = sales_df[sales_df['name'] == selected_sales[0]].iloc[0]
        
        if notification_type == "📅 Delivery Schedule":
            preview_df = data_loader.get_sales_delivery_summary(preview_sales['name'], weeks_ahead=4)
        else:
            preview_df = data_loader.get_sales_urgent_deliveries(preview_sales['name'])
        
        if not preview_df.empty:
            st.subheader(f"📧 Preview for {preview_sales['name']}")
            
            # [Rest of original preview code remains the same...]
            # [Keeping the original preview logic for sales notifications]

# Send emails section
if (notification_type == "🛃 Custom Clearance" or selected_sales) and schedule_type == "Send Now":
    st.markdown("---")
    st.subheader("📤 Send Emails")
    
    # Warning message based on notification type
    if notification_type == "🛃 Custom Clearance":
        st.warning(f"⚠️ You are about to send customs clearance schedule to {', '.join(cc_emails)}")
    elif notification_type == "🚨 Overdue Alerts":
        st.warning(f"⚠️ You are about to send URGENT ALERT emails to {len(selected_sales)} sales people about overdue and due today deliveries")
    else:
        st.warning(f"⚠️ You are about to send delivery schedule emails to {len(selected_sales)} sales people")
    
    confirm = st.checkbox("I confirm to send these emails")
    
    if confirm and st.button("🚀 Send Emails Now", type="primary"):
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Collect results
        results = []
        errors = []
        
        if notification_type == "🛃 Custom Clearance":
            # Send single email to customs team
            status_text.text("Sending customs clearance schedule...")
            
            try:
                # Get customs clearance data
                customs_df = data_loader.get_customs_clearance_schedule()
                
                if not customs_df.empty:
                    # Send email
                    success, message = email_sender.send_customs_clearance_email(
                        cc_emails[0],  # Primary recipient
                        customs_df,
                        cc_emails=cc_emails[1:] if len(cc_emails) > 1 else None
                    )
                    
                    results.append({
                        'Recipient': 'Custom Clearance Team',
                        'Email': cc_emails[0],
                        'Status': '✅ Success' if success else '❌ Failed',
                        'Deliveries': customs_df['delivery_id'].nunique(),
                        'Message': message
                    })
                else:
                    results.append({
                        'Recipient': 'Custom Clearance Team',
                        'Email': cc_emails[0],
                        'Status': '⚠️ Skipped',
                        'Deliveries': 0,
                        'Message': 'No customs deliveries found'
                    })
                    
            except Exception as e:
                errors.append(f"Error sending customs email: {str(e)}")
                results.append({
                    'Recipient': 'Custom Clearance Team',
                    'Email': cc_emails[0],
                    'Status': '❌ Error',
                    'Deliveries': 0,
                    'Message': str(e)
                })
            
            progress_bar.progress(1.0)
            
        else:
            # Original logic for sales emails
            for idx, sales_name in enumerate(selected_sales):
                progress = (idx + 1) / len(selected_sales)
                progress_bar.progress(progress)
                status_text.text(f"Sending to {sales_name}... ({idx+1}/{len(selected_sales)})")
                
                try:
                    # Get sales info
                    sales_info = sales_df[sales_df['name'] == sales_name].iloc[0]
                    
                    # Get delivery data based on notification type
                    if notification_type == "📅 Delivery Schedule":
                        delivery_df = data_loader.get_sales_delivery_summary(sales_name, weeks_ahead=4)
                    else:
                        delivery_df = data_loader.get_sales_urgent_deliveries(sales_name)
                    
                    if not delivery_df.empty:
                        # Send email
                        success, message = email_sender.send_delivery_schedule_email(
                            sales_info['email'],
                            sales_name,
                            delivery_df,
                            cc_emails=cc_emails if include_cc else None,
                            notification_type=notification_type
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

# Help section (Updated)
with st.expander("ℹ️ Help & Information"):
    st.markdown("""
    ### How to use this page:
    
    1. **Select Notification Type**:
       - **📅 Delivery Schedule**: Send upcoming 4 weeks delivery plan to sales
       - **🚨 Overdue Alerts**: Send urgent notifications for overdue and due today items
       - **🛃 Custom Clearance**: Send EPE & Foreign customer deliveries to customs team
    
    2. **Select Recipients**: 
       - For sales notifications: Choose all or specific sales
       - For customs: Automatically sent to custom.clearance@prostech.vn
    
    3. **Configure Settings**: Add CC recipients if needed
    4. **Preview**: Check the email content before sending
    5. **Send**: Confirm and send emails
    
    ### Email Content by Type:
    
    #### 📅 Delivery Schedule:
    - Delivery schedule for the next 4 weeks
    - Grouped by week for easy planning
    - Excel attachment with detailed data
    - Calendar integration (.ics file)
    
    #### 🚨 Overdue Alerts:
    - Only overdue and due today deliveries
    - Sorted by urgency (days overdue)
    - Highlighted out-of-stock items
    - Excel with urgent items only
    - Clear action items
    
    #### 🛃 Custom Clearance (NEW):
    - EPE companies (export at place) deliveries
    - Foreign customer deliveries by country
    - Grouped by type and week
    - Excel with EPE and Foreign sheets
    - Calendar events for customs planning
    
    ### Notes:
    - Emails are sent to the registered email address
    - Only deliveries with remaining quantities are included
    - Custom clearance includes both EPE and Foreign customers
    - The system uses company SMTP settings for sending emails
    """)