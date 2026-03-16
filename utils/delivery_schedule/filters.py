# utils/delivery_schedule/filters.py
"""Filter section — date preset lives OUTSIDE the form so it can
conditionally show/hide date pickers without waiting for submit."""

import streamlit as st
from datetime import datetime, timedelta


def create_filter_section(filter_options):
    """Create the filter section with all filter controls.

    Date preset is rendered outside the form so that changing it
    immediately shows/hides the manual date pickers.  Everything
    else stays inside the form to prevent full-page reruns.
    """

    # ── Compact exclude-checkbox styling ─────────────────────────
    st.markdown("""
    <style>
        /* ── Exclude checkbox: inline with filter label ── */
        .excl-row {
            display: flex;
            align-items: center;
            margin-bottom: -1.1rem;
            min-height: 1.6rem;
        }
        .excl-row .filter-label {
            font-size: 0.875rem;
            font-weight: 400;
            white-space: nowrap;
        }
        /* Shrink the checkbox widget */
        .excl-row [data-testid="stCheckbox"] {
            margin: 0; padding: 0;
        }
        .excl-row [data-testid="stCheckbox"] > label {
            gap: 0.25rem;
            min-height: unset;
            padding: 0;
            align-items: center;
        }
        .excl-row [data-testid="stCheckbox"] > label p {
            font-size: 0.72rem !important;
            color: rgba(130,130,130,0.9);
            line-height: 1;
        }
        .excl-row [data-testid="stCheckbox"] > label > div[role="checkbox"] {
            width: 0.85rem; height: 0.85rem;
        }

        /* ── Overdue popover: full width ── */
        [data-testid="stPopoverBody"] {
            width: calc(100vw - 6rem);
            max-width: calc(100vw - 6rem);
        }
    </style>
    """, unsafe_allow_html=True)

    # ── Pre-compute date bounds ──────────────────────────────────
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

    # ── Date Preset (outside form — reruns immediately) ──────────
    preset_col, range_col = st.columns([1, 3])

    with preset_col:
        preset = st.selectbox(
            "📅 Date Range",
            options=["All Data", "This Week", "This Month",
                     "Next 30 Days", "Next 90 Days", "Custom"],
            index=1,
            key="date_preset",
        )

    # Compute the resolved range for non-Custom presets
    resolved_from, resolved_to = _resolve_date_preset(
        preset, None, None, today, data_min, data_max,
    )

    with range_col:
        if preset == "Custom":
            # Show editable date pickers
            dc1, dc2 = st.columns(2)
            with dc1:
                date_from = st.date_input(
                    "From", value=data_min,
                    min_value=extended_min, max_value=extended_max,
                    key="input_date_from",
                )
            with dc2:
                date_to = st.date_input(
                    "To", value=data_max,
                    min_value=extended_min, max_value=extended_max,
                    key="input_date_to",
                )
            if date_from > date_to:
                date_from, date_to = date_to, date_from
            resolved_from, resolved_to = date_from, date_to
        else:
            # Show read-only label with computed range
            st.markdown("")  # vertical spacer to align with selectbox
            st.info(
                f"📅  **{resolved_from.strftime('%Y/%m/%d')}**  →  "
                f"**{resolved_to.strftime('%Y/%m/%d')}**"
                f"{'  ·  Data range: ' + data_min.strftime('%Y/%m/%d') + ' → ' + data_max.strftime('%Y/%m/%d') if preset == 'All Data' else ''}"
            )

    # ── Main filter form ─────────────────────────────────────────
    with st.form("delivery_filters"):
        # ROW 1: Timeline + Legal Entity + Creator + Customer
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)

        timeline_options = filter_options.get('timeline_statuses', [])
        default_timeline = ["Completed"] if "Completed" in timeline_options else None
        with r1c1:
            selected_timeline, exclude_timeline = _multiselect_excl(
                "Timeline Status", timeline_options, "timeline",
                default=default_timeline, excl_default=True,
            )
        with r1c2:
            selected_legal_entities, exclude_legal_entities = _multiselect_excl(
                "Legal Entity", filter_options.get('legal_entities', []),
                "legal_entities",
            )
        with r1c3:
            selected_creators, exclude_creators = _multiselect_excl(
                "Creator/Sales", filter_options.get('creators', []),
                "creators",
            )
        with r1c4:
            selected_customers, exclude_customers = _multiselect_excl(
                "Customer (Sold-To)", filter_options.get('customers', []),
                "customers",
            )

        # ROW 2: Ship-To, Product, Brand
        r3c1, r3c2, r3c3 = st.columns(3)
        with r3c1:
            selected_ship_to, exclude_ship_to = _multiselect_excl(
                "Ship-To Company", filter_options.get('ship_to_companies', []),
                "ship_to",
            )
        with r3c2:
            selected_products, exclude_products = _multiselect_excl(
                "Product", filter_options.get('products', []),
                "products",
            )
        with r3c3:
            selected_brands, exclude_brands = _multiselect_excl(
                "Brand", filter_options.get('brands', []),
                "brands",
            )

        # ROW 3: Location & Company Type
        r4c1, r4c2, r4c3, r4c4 = st.columns(4)
        with r4c1:
            selected_states = st.multiselect(
                "State/Province",
                options=filter_options.get('states', []),
                placeholder="All states", key="filter_states",
            )
        with r4c2:
            lc, ec = st.columns([4, 1])
            with lc:
                st.markdown(
                    '<div class="excl-row"><span class="filter-label">Country</span></div>',
                    unsafe_allow_html=True,
                )
            with ec:
                st.markdown('<div class="excl-row">', unsafe_allow_html=True)
                exclude_countries = st.checkbox(
                    "Excl", key="exclude_countries", value=False,
                    help="Exclude selected countries",
                )
                st.markdown('</div>', unsafe_allow_html=True)
            selected_countries = st.multiselect(
                "Country",
                options=filter_options.get('countries', []),
                placeholder="All countries", key="filter_countries",
                label_visibility="collapsed",
            )
        with r4c3:
            epe_filter = st.selectbox(
                "EPE Company",
                options=filter_options.get('epe_options', ["All"]),
                index=0, key="epe_filter",
            )
        with r4c4:
            foreign_filter = st.selectbox(
                "Customer Type",
                options=filter_options.get('foreign_options', ["All Customers"]),
                index=0, key="foreign_filter",
            )

        # Submit
        st.form_submit_button(
            "🔄 Apply Filters", type="primary", use_container_width=True,
        )

    # ── Compile filters dict ─────────────────────────────────────
    filters = {
        'date_from': resolved_from,
        'date_to': resolved_to,
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
        'exclude_statuses': False,
    }

    return filters


# ── Helpers ──────────────────────────────────────────────────────

def _resolve_date_preset(preset, date_from, date_to, today, data_min, data_max):
    """Compute actual date range from a preset name."""
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
    elif preset == "Custom":
        if date_from and date_to:
            if date_from > date_to:
                date_from, date_to = date_to, date_from
            return date_from, date_to
        return data_min, data_max
    else:  # All Data
        return data_min, data_max


def _multiselect_excl(label, options, key_prefix, default=None, excl_default=False):
    """Label + tiny Excl checkbox on one line, multiselect below."""
    lc, ec = st.columns([4, 1])
    with lc:
        st.markdown(
            f'<div class="excl-row"><span class="filter-label">{label}</span></div>',
            unsafe_allow_html=True,
        )
    with ec:
        st.markdown('<div class="excl-row">', unsafe_allow_html=True)
        exclude = st.checkbox(
            "Excl", key=f"exclude_{key_prefix}", value=excl_default,
            help=f"Exclude selected {label.lower()}",
        )
        st.markdown('</div>', unsafe_allow_html=True)

    selected = st.multiselect(
        label, options=options, default=default,
        placeholder=f"All {label.lower()}", key=f"filter_{key_prefix}",
        label_visibility="collapsed",
    )
    return selected, exclude