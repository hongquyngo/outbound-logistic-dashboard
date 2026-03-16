# pages/1_📊_Delivery_Schedule.py

import streamlit as st
from datetime import datetime
from utils.auth import AuthManager
from utils.delivery_schedule import (
    DeliveryDataLoader,
    EmailSender,
    create_filter_section,
    display_metrics,
    display_pivot_table,
    display_detailed_list,
    display_overdue_alert,
    display_email_notifications,
)

# ── Page config & auth ───────────────────────────────────────────

st.set_page_config(page_title="Delivery Schedule", page_icon="📊", layout="wide")

auth_manager = AuthManager()
if not auth_manager.check_session():
    st.warning("⚠️ Please login to access this page")
    st.stop()

data_loader = DeliveryDataLoader()
email_sender = EmailSender()


# ── Main ─────────────────────────────────────────────────────────

def main():
    st.title("📊 Delivery Schedule")

    # Filters (form — no rerun until submit)
    filter_options = data_loader.get_filter_options()
    filters = create_filter_section(filter_options)

    # Load data
    with st.spinner("Loading delivery data..."):
        df = data_loader.load_delivery_data(filters)

    if df is None or df.empty:
        st.info("No delivery data found for the selected filters")
        return

    # Track selected PT codes for cross-page use
    if filters.get('products'):
        st.session_state.selected_pt_codes = [p.split(' - ')[0] for p in filters['products']]
    else:
        st.session_state.selected_pt_codes = None

    # KPI cards
    display_metrics(df)

    # Tabs — each @st.fragment runs independently
    tab1, tab2, tab3 = st.tabs([
        "📊 Pivot Table",
        "📋 Detailed List",
        "📧 Email Notifications",
    ])

    with tab1:
        display_pivot_table(df, data_loader)
    with tab2:
        display_detailed_list(df)
    with tab3:
        display_email_notifications(data_loader, email_sender)

    # Alerts
    display_overdue_alert(df)

    # Footer
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()