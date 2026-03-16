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
    display_email_notifications,
    needs_completed_data,
    apply_client_filters,
)

# ── Page config & auth ───────────────────────────────────────────

st.set_page_config(page_title="Delivery Schedule", page_icon="📊", layout="wide")

auth_manager = AuthManager()
if not auth_manager.check_session():
    st.warning("⚠️ Please login to access this page")
    st.stop()

data_loader = DeliveryDataLoader()
email_sender = EmailSender()


# ── Smart data loading ───────────────────────────────────────────

def _load_smart(data_loader, filters):
    """Two-tier cache: DB hit only when completed-data scope changes.

    Tier 1 — st.cache_data inside load_base_data (TTL 5 min, keyed by
             include_completed bool).  Two possible cached DataFrames.
    Tier 2 — client-side pandas filtering on the cached DataFrame.
             Instant, no DB round-trip.

    Flow:
      1. Determine if current filters need completed rows.
      2. Call load_base_data(include_completed) — cache hit most of the time.
      3. Apply every other filter client-side.
    """
    include_completed = needs_completed_data(filters)

    with st.spinner(
        "Loading all deliveries (incl. completed)..."
        if include_completed
        else "Loading active deliveries..."
    ):
        df_base = data_loader.load_base_data(include_completed)

    if df_base is None or df_base.empty:
        return None

    # Client-side filtering — sub-second
    df = apply_client_filters(df_base, filters)
    return df


# ── Main ─────────────────────────────────────────────────────────

def main():
    st.title("📊 Delivery Schedule")

    # Filters (form — no rerun until submit)
    filter_options = data_loader.get_filter_options()
    filters = create_filter_section(filter_options)

    # Load data — smart 2-tier cache
    df = _load_smart(data_loader, filters)

    if df is None or df.empty:
        st.info("No delivery data found for the selected filters")
        return

    # Track selected PT codes for cross-page use
    if filters.get('products'):
        st.session_state.selected_pt_codes = [
            p.split(' - ')[0] for p in filters['products']
        ]
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

    # Footer
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()