# utils/delivery_schedule/filters.py
"""Filter section with form-based layout to prevent full-page rerun"""

import streamlit as st
from datetime import datetime, timedelta


def create_filter_section(filter_options):
    """Create the filter section with all filter controls - form-based to prevent rerun"""

    # Pre-compute date range info (needed before form)
    date_range_options = filter_options.get('date_range', {})
    today = datetime.now().date()
    data_min = date_range_options.get('min_date', today - timedelta(days=365))
    data_max = date_range_options.get('max_date', today + timedelta(days=365))
    if hasattr(data_min, 'date'):
        data_min = data_min.date()
    if hasattr(data_max, 'date'):
        data_max = data_max.date()
    if data_min > data_max:
        data_min, data_max = data_max, data_min
    extended_min = data_min.replace(month=1, day=1)
    extended_max = data_max.replace(month=12, day=31)

    with st.form("delivery_filters"):
        # ── ROW 1: Date Range & Timeline ──────────────────────────
        r1c1, r1c2, r1c3, r1c4 = st.columns([1.2, 1, 1, 1.8])

        with r1c1:
            preset = st.selectbox(
                "📅 Date Range",
                options=["All Data", "This Week", "This Month", "Next 30 Days", "Next 90 Days", "Custom"],
                index=0, key="date_preset"
            )

        with r1c2:
            date_from = st.date_input("From", value=data_min, min_value=extended_min,
                                       max_value=extended_max, key="input_date_from")

        with r1c3:
            date_to = st.date_input("To", value=data_max, min_value=extended_min,
                                     max_value=extended_max, key="input_date_to")

        with r1c4:
            timeline_options = filter_options.get('timeline_statuses', [])
            default_timeline = ["Completed"] if "Completed" in timeline_options else None
            tl_col1, tl_col2 = st.columns([5, 1])
            with tl_col1:
                selected_timeline = st.multiselect(
                    "Timeline Status", options=timeline_options, default=default_timeline,
                    placeholder="All statuses", key="timeline_filter"
                )
            with tl_col2:
                exclude_timeline = st.checkbox("Excl", key="exclude_timeline", value=True,
                                                help="Exclude selected timeline statuses")

        st.caption(
            f"💡 Data: **{data_min.strftime('%Y/%m/%d')}** → **{data_max.strftime('%Y/%m/%d')}** · "
            f"Preset overrides manual dates unless set to **Custom**"
        )

        # ── ROW 2: Who ────────────────────────────────────────────
        r2c1, r2c2, r2c3 = st.columns(3)

        with r2c1:
            selected_legal_entities, exclude_legal_entities = _multiselect_excl(
                "Legal Entity", filter_options.get('legal_entities', []), "legal_entities")

        with r2c2:
            selected_creators, exclude_creators = _multiselect_excl(
                "Creator/Sales", filter_options.get('creators', []), "creators")

        with r2c3:
            selected_customers, exclude_customers = _multiselect_excl(
                "Customer (Sold-To)", filter_options.get('customers', []), "customers")

        # ── ROW 3: Where & What ───────────────────────────────────
        r3c1, r3c2, r3c3 = st.columns(3)

        with r3c1:
            selected_ship_to, exclude_ship_to = _multiselect_excl(
                "Ship-To Company", filter_options.get('ship_to_companies', []), "ship_to")

        with r3c2:
            selected_products, exclude_products = _multiselect_excl(
                "Product", filter_options.get('products', []), "products")

        with r3c3:
            selected_brands, exclude_brands = _multiselect_excl(
                "Brand", filter_options.get('brands', []), "brands")

        # ── ROW 4: Location & Company Type ────────────────────────
        r4c1, r4c2, r4c3, r4c4 = st.columns(4)

        with r4c1:
            selected_states = st.multiselect(
                "State/Province", options=filter_options.get('states', []),
                placeholder="All states", key="filter_states")

        with r4c2:
            loc_col1, loc_col2 = st.columns([5, 1])
            with loc_col1:
                selected_countries = st.multiselect(
                    "Country", options=filter_options.get('countries', []),
                    placeholder="All countries", key="filter_countries")
            with loc_col2:
                exclude_countries = st.checkbox("Excl", key="exclude_countries",
                                                help="Exclude selected countries")

        with r4c3:
            epe_filter = st.selectbox(
                "EPE Company", options=filter_options.get('epe_options', ["All"]),
                index=0, key="epe_filter")

        with r4c4:
            foreign_filter = st.selectbox(
                "Customer Type", options=filter_options.get('foreign_options', ["All Customers"]),
                index=0, key="foreign_filter")

        # ── Submit Button ─────────────────────────────────────────
        st.form_submit_button("🔄 Apply Filters", type="primary", use_container_width=True)

    # ── Compute final dates (AFTER form, so preset always wins) ──
    date_from, date_to = _resolve_date_preset(
        preset, date_from, date_to, today, data_min, data_max
    )

    # Compile filters
    filters = {
        'date_from': date_from,
        'date_to': date_to,
        'creators': selected_creators or None,
        'exclude_creators': exclude_creators,
        'customers': selected_customers or None,
        'exclude_customers': exclude_customers,
        'products': selected_products or None,
        'exclude_products': exclude_products,
        'brands': selected_brands or None,
        'exclude_brands': exclude_brands,
        'ship_to_companies': selected_ship_to or None,
        'exclude_ship_to_companies': exclude_ship_to,
        'states': selected_states or None,
        'countries': selected_countries or None,
        'exclude_countries': exclude_countries,
        'epe_filter': epe_filter,
        'foreign_filter': foreign_filter,
        'timeline_status': selected_timeline or None,
        'exclude_timeline_status': exclude_timeline,
        'legal_entities': selected_legal_entities or None,
        'exclude_legal_entities': exclude_legal_entities,
        'statuses': None,
        'exclude_statuses': False
    }

    return filters


def _resolve_date_preset(preset, date_from, date_to, today, data_min, data_max):
    """Compute actual date range from preset — called AFTER form submission"""
    if preset == "This Week":
        ws = today - timedelta(days=today.weekday())
        return max(ws, data_min), min(ws + timedelta(days=6), data_max)
    elif preset == "This Month":
        ms = today.replace(day=1)
        nm = today.replace(day=28) + timedelta(days=4)
        return max(ms, data_min), min(nm - timedelta(days=nm.day), data_max)
    elif preset == "Next 30 Days":
        return max(today, data_min), min(today + timedelta(days=30), data_max)
    elif preset == "Next 90 Days":
        return max(today, data_min), min(today + timedelta(days=90), data_max)
    elif preset == "All Data":
        return data_min, data_max
    else:  # Custom — use date_input values
        if date_from > date_to:
            date_from, date_to = date_to, date_from
        return date_from, date_to


def _multiselect_excl(label, options, key_prefix):
    """Compact multiselect with exclude checkbox — single-line layout"""
    col1, col2 = st.columns([5, 1])
    with col1:
        selected = st.multiselect(
            label, options=options, default=None,
            placeholder=f"All {label.lower()}", key=f"filter_{key_prefix}"
        )
    with col2:
        exclude = st.checkbox("Excl", key=f"exclude_{key_prefix}",
                               help=f"Exclude selected {label.lower()}")
    return selected, exclude
