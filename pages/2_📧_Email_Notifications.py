# pages/2_📧_Email_Notifications.py

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.auth import AuthManager
from utils.data_loader import DeliveryDataLoader
from utils.email_sender import EmailSender
from sqlalchemy import text
import re
import logging

# Setup logging
logger = logging.getLogger(__name__)

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

# Check user role
user_role = st.session_state.get('user_role', '')
if user_role not in ['admin', 'manager', 'logistics_manager']:
    st.error("❌ You don't have permission to access this page")
    st.stop()

# Initialize services
data_loader = DeliveryDataLoader()
email_sender = EmailSender()

st.title("📧 Email Notifications - Delivery Schedule")
st.markdown("Send delivery schedules and urgent alerts to sales teams, customers, or custom recipients")
st.markdown("---")

# Helper function for email validation
def validate_email(email):
    """Validate email format"""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

# Get sales list with active deliveries
@st.cache_data(ttl=300)
def get_sales_list(weeks_ahead=4):
    """Get list of sales people with active deliveries"""
    try:
        query = text("""
        SELECT DISTINCT 
            e.id,
            e.keycloak_id,
            CONCAT(e.first_name, ' ', e.last_name) as name,
            e.email,
            COUNT(DISTINCT d.delivery_id) as active_deliveries,
            SUM(d.remaining_quantity_to_deliver) as total_quantity,
            COUNT(DISTINCT CASE WHEN d.delivery_timeline_status = 'Overdue' THEN d.delivery_id END) as overdue_deliveries,
            e.manager_id,
            m.email as manager_email,
            CONCAT(m.first_name, ' ', m.last_name) as manager_name
        FROM employees e
        LEFT JOIN employees m ON e.manager_id = m.id
        INNER JOIN delivery_full_view d ON d.created_by_email = e.email
        WHERE d.etd >= CURDATE()
            AND d.etd <= DATE_ADD(CURDATE(), INTERVAL :weeks WEEK)
            AND d.remaining_quantity_to_deliver > 0
            AND d.shipment_status NOT IN ('DELIVERED', 'COMPLETED')
        GROUP BY e.id, e.keycloak_id, e.first_name, e.last_name, e.email, 
                 e.manager_id, m.email, m.first_name, m.last_name
        ORDER BY name
        """)
        
        engine = data_loader.engine
        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params={'weeks': weeks_ahead})
        return df
    except Exception as e:
        logger.error(f"Error loading sales list: {e}")
        st.error(f"Error loading sales list: {e}")
        return pd.DataFrame()

# Get customers with active deliveries
@st.cache_data(ttl=300)
def get_customers_list(weeks_ahead=4):
    """Get list of customers with active deliveries"""
    try:
        query = text("""
        SELECT DISTINCT 
            d.customer,
            d.customer_code,
            MIN(d.customer_contact_email) as customer_email,
            COUNT(DISTINCT d.delivery_id) as active_deliveries,
            SUM(d.remaining_quantity_to_deliver) as total_quantity,
            COUNT(DISTINCT d.created_by_name) as sales_count,
            GROUP_CONCAT(DISTINCT d.recipient_state_province) as provinces
        FROM delivery_full_view d
        WHERE d.etd >= CURDATE()
            AND d.etd <= DATE_ADD(CURDATE(), INTERVAL :weeks WEEK)
            AND d.remaining_quantity_to_deliver > 0
            AND d.shipment_status NOT IN ('DELIVERED', 'COMPLETED')
            AND d.customer_contact_email IS NOT NULL
            AND d.customer_contact_email != ''
        GROUP BY d.customer, d.customer_code
        HAVING customer_email IS NOT NULL
        ORDER BY customer
        """)
        
        engine = data_loader.engine
        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params={'weeks': weeks_ahead})
        return df
    except Exception as e:
        logger.error(f"Error loading customers list: {e}")
        st.error(f"Error loading customers list: {e}")
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
            MAX(d.days_overdue) as max_days_overdue,
            e.manager_id,
            m.email as manager_email,
            CONCAT(m.first_name, ' ', m.last_name) as manager_name
        FROM employees e
        LEFT JOIN employees m ON e.manager_id = m.id
        INNER JOIN delivery_full_view d ON d.created_by_email = e.email
        WHERE d.delivery_timeline_status IN ('Overdue', 'Due Today')
            AND d.remaining_quantity_to_deliver > 0
            AND d.shipment_status NOT IN ('DELIVERED', 'COMPLETED')
        GROUP BY e.id, e.keycloak_id, e.first_name, e.last_name, e.email,
                 e.manager_id, m.email, m.first_name, m.last_name
        HAVING (overdue_deliveries > 0 OR due_today_deliveries > 0)
        ORDER BY overdue_deliveries DESC, due_today_deliveries DESC, name
        """)
        
        engine = data_loader.engine
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        logger.error(f"Error loading sales list for overdue alerts: {e}")
        st.error(f"Error loading sales list for overdue alerts: {e}")
        return pd.DataFrame()

# Initialize session state
if 'notification_type' not in st.session_state:
    st.session_state.notification_type = '📅 Delivery Schedule'
if 'recipient_type' not in st.session_state:
    st.session_state.recipient_type = 'creators'
if 'weeks_ahead' not in st.session_state:
    st.session_state.weeks_ahead = 4

# Email configuration section
col1, col2 = st.columns([2, 1])

with col2:
    st.subheader("⚙️ Email Settings")
    
    # Notification Type Selection
    notification_type = st.radio(
        "📧 Notification Type",
        ["📅 Delivery Schedule", "🚨 Overdue Alerts", "🛃 Custom Clearance"],
        index=["📅 Delivery Schedule", "🚨 Overdue Alerts", "🛃 Custom Clearance"].index(
            st.session_state.get('notification_type', '📅 Delivery Schedule')
        ),
        help="""
        Delivery Schedule: Next X weeks schedule
        Overdue Alerts: Only overdue and due today deliveries
        Custom Clearance: EPE & Foreign customers for customs team
        """
    )
    
    # Store in session state
    if notification_type != st.session_state.notification_type:
        st.session_state.notification_type = notification_type
        st.rerun()
    
    # Time Period selection for relevant notification types
    if notification_type in ["📅 Delivery Schedule", "🛃 Custom Clearance"]:
        weeks_ahead = st.selectbox(
            "📅 Time Period",
            options=[1, 2, 3, 4, 5, 6, 7, 8],
            index=3,  # Default to 4 weeks
            format_func=lambda x: f"{x} week{'s' if x > 1 else ''}",
            help="Select how many weeks ahead to include in the schedule"
        )
        st.session_state.weeks_ahead = weeks_ahead
    else:
        weeks_ahead = st.session_state.get('weeks_ahead', 4)
    
    # Schedule type
    schedule_type = st.radio(
        "Schedule Type",
        ["Send Now", "Preview Only"],
        index=1
    )

with col1:
    st.subheader("📋 Recipient Selection")
    
    # Initialize variables
    selected_recipients = []
    selected_customers = []
    custom_recipients = []
    
    # Special handling for Custom Clearance
    if notification_type == "🛃 Custom Clearance":
        st.info(f"📌 Custom Clearance notifications will be sent to the customs team with EPE & Foreign customer deliveries for the next {weeks_ahead} weeks")
        
        # Show summary
        customs_summary = data_loader.get_customs_clearance_summary(weeks_ahead)
        if not customs_summary.empty:
            col1_1, col1_2, col1_3 = st.columns(3)
            with col1_1:
                st.metric("EPE Deliveries", customs_summary['epe_deliveries'].sum())
            with col1_2:
                st.metric("Foreign Deliveries", customs_summary['foreign_deliveries'].sum())
            with col1_3:
                st.metric("Total Countries", customs_summary['countries'].sum())
            
            st.caption(f"🔍 Auto-applied filters: EPE Companies + Foreign Customers | Next {weeks_ahead} weeks | Not delivered")
        else:
            st.warning(f"No customs clearance deliveries found for the next {weeks_ahead} weeks")
        
        recipient_type = "customs"
    
    else:
        # Recipient type selection
        recipient_type = st.selectbox(
            "Send to:",
            ["creators", "customers", "custom"],
            format_func=lambda x: {
                "creators": "👤 Sales/Creators",
                "customers": "🏢 Customers",
                "custom": "✉️ Custom Recipients"
            }[x],
            index=["creators", "customers", "custom"].index(st.session_state.get('recipient_type', 'creators'))
        )
        
        # Update session state
        if recipient_type != st.session_state.recipient_type:
            st.session_state.recipient_type = recipient_type
            st.rerun()
        
        # Handle different recipient types
        if recipient_type == "creators":
            # Get appropriate sales list based on notification type
            if notification_type == "🚨 Overdue Alerts":
                sales_df = get_sales_list_overdue()
            else:
                sales_df = get_sales_list(weeks_ahead)
            
            if not sales_df.empty:
                # Format function based on notification type
                if notification_type == "🚨 Overdue Alerts":
                    def format_func(x):
                        creator = sales_df[sales_df['name']==x].iloc[0]
                        return f"{x} (Overdue: {creator['overdue_deliveries']}, Due Today: {creator['due_today_deliveries']})"
                else:
                    def format_func(x):
                        creator = sales_df[sales_df['name']==x].iloc[0]
                        return f"{x} ({creator['active_deliveries']} deliveries, {creator['total_quantity']:.0f} units)"
                
                selected_recipients = st.multiselect(
                    "Select sales people:",
                    options=sales_df['name'].tolist(),
                    default=None,
                    format_func=format_func
                )
                
                # Show selected recipients summary
                if selected_recipients:
                    selected_df = sales_df[sales_df['name'].isin(selected_recipients)]
                    
                    if notification_type == "🚨 Overdue Alerts":
                        display_df = selected_df[['name', 'email', 'overdue_deliveries', 'due_today_deliveries', 'max_days_overdue']]
                        display_df.columns = ['Name', 'Email', 'Overdue', 'Due Today', 'Max Days Overdue']
                    else:
                        display_df = selected_df[['name', 'email', 'active_deliveries', 'total_quantity']]
                        display_df['total_quantity'] = display_df['total_quantity'].apply(lambda x: f"{x:,.0f}")
                        display_df.columns = ['Name', 'Email', 'Active Deliveries', 'Total Quantity']
                    
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                if notification_type == "🚨 Overdue Alerts":
                    st.warning("No sales with overdue or due today deliveries found")
                else:
                    st.warning("No sales with active deliveries found")
        
        elif recipient_type == "customers":
            # Get customers list
            customers_df = get_customers_list(weeks_ahead)
            
            if not customers_df.empty:
                def format_customer(x):
                    customer = customers_df[customers_df['customer']==x].iloc[0]
                    return f"{x} ({customer['active_deliveries']} deliveries, {customer['total_quantity']:.0f} units)"
                
                selected_customers = st.multiselect(
                    "Select customers:",
                    options=customers_df['customer'].tolist(),
                    default=None,
                    format_func=format_customer
                )
                
                # Show selected customers summary
                if selected_customers:
                    selected_df = customers_df[customers_df['customer'].isin(selected_customers)]
                    display_df = selected_df[['customer', 'customer_email', 'active_deliveries', 'total_quantity', 'provinces']]
                    display_df['total_quantity'] = display_df['total_quantity'].apply(lambda x: f"{x:,.0f}")
                    display_df.columns = ['Customer', 'Email', 'Deliveries', 'Quantity', 'Provinces']
                    
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.warning("No customers with active deliveries and valid email found")
        
        else:  # custom recipients
            st.markdown("#### Enter Custom Recipients")
            custom_email_text = st.text_area(
                "Email addresses (one per line)",
                placeholder="john.doe@company.com\njane.smith@company.com\nlogistics.team@company.com",
                height=150
            )
            
            if custom_email_text:
                # Parse and validate emails
                custom_emails = [email.strip() for email in custom_email_text.split('\n') if email.strip()]
                valid_emails = []
                invalid_emails = []
                
                for email in custom_emails:
                    if validate_email(email):
                        valid_emails.append(email)
                    else:
                        invalid_emails.append(email)
                
                if invalid_emails:
                    st.error(f"❌ Invalid email addresses: {', '.join(invalid_emails)}")
                
                if valid_emails:
                    custom_recipients = valid_emails
                    st.success(f"✅ {len(valid_emails)} valid email addresses")
                    
                    # Display valid emails
                    custom_df = pd.DataFrame({
                        'Email': valid_emails,
                        'Status': ['✅ Valid'] * len(valid_emails)
                    })
                    st.dataframe(custom_df, use_container_width=True, hide_index=True)

# CC settings (back in col2)
with col2:
    cc_emails = []
    
    if notification_type == "🛃 Custom Clearance":
        # Default recipient for customs
        default_recipient = st.text_input(
            "Primary Recipient",
            value="custom.clearance@prostech.vn",
            disabled=True,
            help="Default email for customs clearance team"
        )
        cc_emails = [default_recipient]
    
    else:
        # CC to managers for creator notifications
        if recipient_type == "creators" and notification_type != "🚨 Overdue Alerts":
            include_cc = st.checkbox("Include CC to managers", value=True)
            
            if include_cc and selected_recipients and 'sales_df' in locals():
                # Get unique manager emails
                selected_df = sales_df[sales_df['name'].isin(selected_recipients)]
                manager_emails = selected_df[selected_df['manager_email'].notna()]['manager_email'].unique().tolist()
                
                if manager_emails:
                    st.info(f"Managers will be CC'd: {', '.join(manager_emails)}")
                    cc_emails.extend(manager_emails)
    
    # Additional CC emails
    st.markdown("#### Additional CC Recipients")
    additional_cc = st.text_area(
        "CC Email addresses (one per line)",
        placeholder="manager@company.com\nlogistics@company.com",
        height=100
    )
    
    if additional_cc:
        additional_emails = [email.strip() for email in additional_cc.split('\n') if email.strip()]
        valid_cc = [email for email in additional_emails if validate_email(email)]
        invalid_cc = [email for email in additional_emails if not validate_email(email)]
        
        if invalid_cc:
            st.warning(f"⚠️ Invalid CC emails will be skipped: {', '.join(invalid_cc)}")
        
        if valid_cc:
            cc_emails.extend(valid_cc)
    
    # Remove duplicates
    cc_emails = list(dict.fromkeys(cc_emails))
    
    if cc_emails:
        st.caption(f"Total CC recipients: {len(cc_emails)}")

st.markdown("---")

# Preview section
show_preview = False
if notification_type == "🛃 Custom Clearance":
    show_preview = True
elif recipient_type == "creators" and selected_recipients:
    show_preview = True
elif recipient_type == "customers" and selected_customers:
    show_preview = True
elif recipient_type == "custom" and custom_recipients:
    show_preview = True

if show_preview and st.button("👁️ Preview Email Content", type="secondary"):
    with st.spinner("Generating preview..."):
        try:
            if notification_type == "🛃 Custom Clearance":
                # Custom clearance preview
                preview_df = data_loader.get_customs_clearance_schedule(weeks_ahead)
                
                if not preview_df.empty:
                    st.subheader("📧 Preview - Custom Clearance Schedule")
                    
                    # Show summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    
                    epe_df = preview_df[preview_df['is_epe_company'] == 'Yes']
                    foreign_df = preview_df[preview_df['customer_country_code'] != preview_df['legal_entity_country_code']]
                    
                    with col1:
                        st.metric("EPE Deliveries", epe_df['delivery_id'].nunique())
                    with col2:
                        st.metric("Foreign Deliveries", foreign_df['delivery_id'].nunique())
                    with col3:
                        st.metric("Total Quantity", f"{preview_df['remaining_quantity_to_deliver'].sum():,.0f}")
                    with col4:
                        countries = foreign_df['customer_country_name'].nunique()
                        st.metric("Countries", countries)
                    
                    st.info("Email will include EPE companies and foreign customer deliveries grouped by type and week")
                else:
                    st.warning("No customs clearance deliveries found")
            
            elif recipient_type == "customers" and selected_customers:
                # Customer preview - show first customer
                customer_name = selected_customers[0]
                customer_info = customers_df[customers_df['customer'] == customer_name].iloc[0]
                
                st.subheader(f"📧 Preview for {customer_name}")
                
                # Get deliveries for this customer
                preview_df = data_loader.get_customer_deliveries(customer_name, weeks_ahead)
                
                if not preview_df.empty:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Deliveries", preview_df['delivery_id'].nunique())
                    with col2:
                        st.metric("Products", preview_df['product_pn'].nunique())
                    with col3:
                        st.metric("Total Quantity", f"{preview_df['remaining_quantity_to_deliver'].sum():,.0f}")
                    with col4:
                        overdue = preview_df[preview_df['delivery_timeline_status'] == 'Overdue']
                        st.metric("Overdue", overdue['delivery_id'].nunique())
                    
                    # Show sample deliveries
                    st.markdown("#### Sample Deliveries")
                    display_cols = ['delivery_date', 'dn_number', 'recipient_company', 'recipient_state_province', 
                                   'pt_code', 'product_pn', 'remaining_quantity_to_deliver', 'delivery_timeline_status']
                    display_df = preview_df.head(5)[display_cols]
                    display_df.columns = ['Date', 'DN Number', 'Ship To', 'Province', 'PT Code', 'Product', 'Quantity', 'Status']
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No deliveries found for this customer")
            
            elif recipient_type == "creators" and selected_recipients:
                # Creator preview (existing logic)
                preview_sales = sales_df[sales_df['name'] == selected_recipients[0]].iloc[0]
                
                if notification_type == "📅 Delivery Schedule":
                    preview_df = data_loader.get_sales_delivery_summary(preview_sales['name'], weeks_ahead)
                else:
                    preview_df = data_loader.get_sales_urgent_deliveries(preview_sales['name'])
                
                if not preview_df.empty:
                    st.subheader(f"📧 Preview for {preview_sales['name']}")
                    
                    # Show metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Deliveries", preview_df['delivery_id'].nunique())
                    with col2:
                        st.metric("Customers", preview_df['customer'].nunique())
                    with col3:
                        st.metric("Total Quantity", f"{preview_df['remaining_quantity_to_deliver'].sum():,.0f}")
                    with col4:
                        if 'product_fulfillment_status' in preview_df.columns:
                            out_of_stock = preview_df[preview_df['product_fulfillment_status'] == 'Out of Stock']['product_pn'].nunique()
                            st.metric("Out of Stock", out_of_stock)
                    
                    # Show sample data
                    st.markdown("#### Sample Deliveries")
                    display_cols = ['delivery_date', 'dn_number', 'customer', 'recipient_state_province', 
                                   'pt_code', 'product_pn', 'remaining_quantity_to_deliver']
                    if display_cols[0] in preview_df.columns:
                        display_df = preview_df.head(5)[display_cols]
                        display_df.columns = ['Date', 'DN Number', 'Customer', 'Province', 'PT Code', 'Product', 'Quantity']
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No deliveries found")
                    
            elif recipient_type == "custom" and custom_recipients:
                # Custom recipient preview
                st.subheader("📧 Preview for Custom Recipients")
                st.info("Custom recipients will receive a comprehensive delivery schedule for all active deliveries")
                
                # Get all deliveries
                preview_df = data_loader.get_all_deliveries_summary(weeks_ahead)
                
                if not preview_df.empty:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Deliveries", preview_df['delivery_id'].nunique())
                    with col2:
                        st.metric("Customers", preview_df['customer'].nunique())
                    with col3:
                        st.metric("Total Quantity", f"{preview_df['remaining_quantity_to_deliver'].sum():,.0f}")
                    with col4:
                        st.metric("Sales People", preview_df['created_by_name'].nunique())
                    
                    st.caption("Note: Custom recipients will receive an overview of all deliveries across the organization")
                else:
                    st.warning("No delivery data found for preview")
                    
        except Exception as e:
            st.error(f"Error generating preview: {str(e)}")
            logger.error(f"Error in preview: {e}", exc_info=True)

# Send emails section
ready_to_send = False
if notification_type == "🛃 Custom Clearance":
    ready_to_send = True
elif recipient_type == "creators" and selected_recipients:
    ready_to_send = True
elif recipient_type == "customers" and selected_customers:
    ready_to_send = True
elif recipient_type == "custom" and custom_recipients:
    ready_to_send = True

if ready_to_send and schedule_type == "Send Now":
    st.markdown("---")
    st.subheader("📤 Send Emails")
    
    # Warning message
    if notification_type == "🛃 Custom Clearance":
        st.warning(f"⚠️ You are about to send customs clearance schedule to {', '.join(cc_emails)}")
    elif notification_type == "🚨 Overdue Alerts":
        if recipient_type == "creators":
            st.warning(f"⚠️ You are about to send URGENT ALERT emails to {len(selected_recipients)} sales people")
        elif recipient_type == "customers":
            st.warning(f"⚠️ You are about to send URGENT ALERT emails to {len(selected_customers)} customers")
        else:
            st.warning(f"⚠️ You are about to send URGENT ALERT emails to {len(custom_recipients)} custom recipients")
    else:
        if recipient_type == "creators":
            st.warning(f"⚠️ You are about to send delivery schedule emails to {len(selected_recipients)} sales people")
        elif recipient_type == "customers":
            st.warning(f"⚠️ You are about to send delivery schedule emails to {len(selected_customers)} customers")
        else:
            st.warning(f"⚠️ You are about to send delivery schedule emails to {len(custom_recipients)} custom recipients")
    
    confirm = st.checkbox("I confirm to send these emails")
    
    if confirm and st.button("🚀 Send Emails Now", type="primary"):
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Collect results
        results = []
        errors = []
        
        try:
            if notification_type == "🛃 Custom Clearance":
                # Send customs clearance email
                status_text.text("Sending customs clearance schedule...")
                
                customs_df = data_loader.get_customs_clearance_schedule(weeks_ahead)
                
                if not customs_df.empty:
                    success, message = email_sender.send_customs_clearance_email(
                        cc_emails[0],
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
                
                progress_bar.progress(1.0)
            
            elif recipient_type == "customers":
                # Send to customers
                total_customers = len(selected_customers)
                
                for idx, customer_name in enumerate(selected_customers):
                    progress = (idx + 1) / total_customers
                    progress_bar.progress(progress)
                    status_text.text(f"Sending to {customer_name}... ({idx+1}/{total_customers})")
                    
                    try:
                        customer_info = customers_df[customers_df['customer'] == customer_name].iloc[0]
                        delivery_df = data_loader.get_customer_deliveries(customer_name, weeks_ahead)
                        
                        if not delivery_df.empty:
                            success, message = email_sender.send_delivery_schedule_email(
                                customer_info['customer_email'],
                                customer_name,
                                delivery_df,
                                cc_emails=cc_emails if cc_emails else None,
                                notification_type=notification_type,
                                weeks_ahead=weeks_ahead  # Add weeks_ahead parameter
                            )
                            
                            results.append({
                                'Customer': customer_name,
                                'Email': customer_info['customer_email'],
                                'Status': '✅ Success' if success else '❌ Failed',
                                'Deliveries': delivery_df['delivery_id'].nunique(),
                                'Message': message
                            })
                        else:
                            results.append({
                                'Customer': customer_name,
                                'Email': customer_info['customer_email'],
                                'Status': '⚠️ Skipped',
                                'Deliveries': 0,
                                'Message': 'No deliveries found'
                            })
                            
                    except Exception as e:
                        errors.append(f"Error for {customer_name}: {str(e)}")
                        results.append({
                            'Customer': customer_name,
                            'Email': 'N/A',
                            'Status': '❌ Error',
                            'Deliveries': 0,
                            'Message': str(e)
                        })
            
            elif recipient_type == "custom":
                # Send to custom recipients
                total_recipients = len(custom_recipients)
                
                for idx, email in enumerate(custom_recipients):
                    progress = (idx + 1) / total_recipients
                    progress_bar.progress(progress)
                    status_text.text(f"Sending to {email}... ({idx+1}/{total_recipients})")
                    
                    try:
                        recipient_name = email.split('@')[0].title()
                        
                        if notification_type == "📅 Delivery Schedule":
                            delivery_df = data_loader.get_all_deliveries_summary(weeks_ahead)
                        else:
                            delivery_df = data_loader.get_all_urgent_deliveries()
                        
                        if not delivery_df.empty:
                            success, message = email_sender.send_delivery_schedule_email(
                                email,
                                recipient_name,
                                delivery_df,
                                cc_emails=cc_emails if cc_emails else None,
                                notification_type=notification_type,
                                weeks_ahead=weeks_ahead  # Add weeks_ahead parameter
                            )
                            
                            results.append({
                                'Recipient': recipient_name,
                                'Email': email,
                                'Status': '✅ Success' if success else '❌ Failed',
                                'Deliveries': delivery_df['delivery_id'].nunique(),
                                'Message': message
                            })
                        else:
                            results.append({
                                'Recipient': recipient_name,
                                'Email': email,
                                'Status': '⚠️ Skipped',
                                'Deliveries': 0,
                                'Message': 'No deliveries found'
                            })
                            
                    except Exception as e:
                        errors.append(f"Error for {email}: {str(e)}")
                        results.append({
                            'Recipient': email.split('@')[0].title(),
                            'Email': email,
                            'Status': '❌ Error',
                            'Deliveries': 0,
                            'Message': str(e)
                        })
            
            else:  # creators
                # Send to sales/creators (existing logic)
                total_sales = len(selected_recipients)
                
                for idx, sales_name in enumerate(selected_recipients):
                    progress = (idx + 1) / total_sales
                    progress_bar.progress(progress)
                    status_text.text(f"Sending to {sales_name}... ({idx+1}/{total_sales})")
                    
                    try:
                        sales_info = sales_df[sales_df['name'] == sales_name].iloc[0]
                        
                        if notification_type == "📅 Delivery Schedule":
                            delivery_df = data_loader.get_sales_delivery_summary(sales_name, weeks_ahead)
                        else:
                            delivery_df = data_loader.get_sales_urgent_deliveries(sales_name)
                        
                        if not delivery_df.empty:
                            success, message = email_sender.send_delivery_schedule_email(
                                sales_info['email'],
                                sales_name,
                                delivery_df,
                                cc_emails=cc_emails if cc_emails else None,
                                notification_type=notification_type,
                                weeks_ahead=weeks_ahead  # Add weeks_ahead parameter
                            )
                            
                            results.append({
                                'Sales': sales_name,
                                'Email': sales_info['email'],
                                'Status': '✅ Success' if success else '❌ Failed',
                                'Deliveries': delivery_df['delivery_id'].nunique(),
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
            
        except Exception as e:
            st.error(f"Critical error: {str(e)}")
            logger.error(f"Critical error in email sending: {e}", exc_info=True)
        
        # Clear progress
        progress_bar.empty()
        status_text.empty()
        
        # Show results
        if results:
            st.success("✅ Email process completed!")
            
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

# Help section
with st.expander("ℹ️ Help & Information"):
    st.markdown("""
    ### How to use this page:
    
    1. **Select Notification Type**:
       - **📅 Delivery Schedule**: Send upcoming delivery plan for selected time period
       - **🚨 Overdue Alerts**: Send urgent notifications for overdue and due today items
       - **🛃 Custom Clearance**: Send EPE & Foreign customer deliveries to customs team
    
    2. **Select Time Period** (for Delivery Schedule & Custom Clearance):
       - Choose 1-8 weeks ahead
       - Default is 4 weeks
    
    3. **Select Recipients**: 
       - **👤 Sales/Creators**: Send to sales people who created the deliveries
       - **🏢 Customers**: Send directly to customers (if email available)
       - **✉️ Custom Recipients**: Enter any email addresses manually
       - For customs: Automatically sent to custom.clearance@prostech.vn
    
    4. **Configure Settings**: Add CC recipients if needed
    5. **Preview**: Check the email content before sending
    6. **Send**: Confirm and send emails
    
    ### Email Content by Type:
    
    #### 📅 Delivery Schedule:
    - Includes DN Number and Province information
    - Delivery schedule for the selected time period (1-8 weeks)
    - Grouped by week for easy planning
    - Excel attachment with detailed data
    - Calendar integration (.ics file)
    
    #### 🚨 Overdue Alerts:
    - Only overdue and due today deliveries
    - Sorted by urgency (days overdue)
    - Highlighted out-of-stock items
    - Excel with urgent items only
    - Clear action items
    
    #### 🛃 Custom Clearance:
    - EPE companies (export at place) deliveries
    - Foreign customer deliveries by country
    - For selected time period (1-8 weeks)
    - Grouped by type and week
    - Excel with EPE and Foreign sheets
    - Calendar events for customs planning
    
    ### Notes:
    - Emails include DN Number and Province (recipient_state_province) information
    - Customer emails are taken from customer_contact_email field
    - Custom recipients receive a comprehensive view of all deliveries
    - Only deliveries with remaining quantities are included
    - The system uses company SMTP settings for sending emails
    """)

# Footer
st.markdown("---")
st.caption(f"Delivery Email Notification System | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")