# utils/delivery_schedule/detailed_list.py
"""Detailed delivery list fragment with native column visibility.

Instead of a multiselect widget, we pass ALL columns to st.dataframe
with proper column_config labels.  Users toggle visibility via the
native column-header menu (⋮ → Hide column) built into Streamlit's
dataframe widget.

`column_order` controls the DEFAULT visible set and ordering.
Columns NOT in `column_order` are hidden but can be re-shown by
the user via the dataframe toolbar (click ⋮ on any column header).
"""

import streamlit as st
import pandas as pd


# ── User-friendly column labels ──────────────────────────────────

COLUMN_LABELS = {
    'dn_number':                          'DN Number',
    'delivery_id':                        'Delivery ID',
    'customer':                           'Customer',
    'recipient_company':                  'Ship-To Company',
    'recipient_state_province':           'State/Province',
    'recipient_country_name':             'Country',
    'etd':                                'ETD',
    'pt_code':                            'PT Code',
    'product_pn':                         'Product Name',
    'product_id':                         'Product ID',
    'brand':                              'Brand',
    'package_size':                       'Package Size',
    'standard_quantity':                  'Std Qty',
    'selling_quantity':                   'Selling Qty',
    'remaining_quantity_to_deliver':      'Remaining Qty',
    'stock_out_quantity':                 'Stock Out Qty',
    'stock_out_request_quantity':         'Stock Out Request Qty',
    'total_instock_at_preferred_warehouse': 'In-Stock (Preferred WH)',
    'total_instock_all_warehouses':       'In-Stock (All WH)',
    'gap_quantity':                       'Gap Qty',
    'product_gap_quantity':               'Product Gap Qty',
    'product_total_remaining_demand':     'Total Remaining Demand',
    'product_fulfill_rate_percent':       'Fulfill Rate %',
    'fulfill_rate_percent':               'Line Fulfill %',
    'delivery_demand_percentage':         'Demand %',
    'delivery_timeline_status':           'Timeline Status',
    'days_overdue':                       'Days Overdue',
    'shipment_status':                    'Shipment Status',
    'product_fulfillment_status':         'Fulfillment Status',
    'is_epe_company':                     'EPE Company',
    'legal_entity':                       'Legal Entity',
    'created_by_name':                    'Creator/Sales',
    'created_date':                       'Created Date',
    'delivered_date':                     'Delivered Date',
    'dispatched_date':                    'Dispatched Date',
    'preferred_warehouse':                'Preferred WH',
    'shipping_cost':                      'Shipping Cost',
    'export_tax':                         'Export Tax',
    'customer_country_code':              'Customer Country',
    'legal_entity_country_code':          'Entity Country',
}

# Columns visible by default (order matters)
DEFAULT_COLUMNS = [
    'dn_number', 'customer', 'recipient_company', 'etd',
    'pt_code', 'product_pn', 'brand', 'standard_quantity',
    'remaining_quantity_to_deliver', 'product_fulfill_rate_percent',
    'delivery_timeline_status', 'days_overdue', 'shipment_status',
    'product_fulfillment_status', 'is_epe_company',
]


@st.fragment
def display_detailed_list(df):
    """Display detailed delivery list with native column visibility."""
    st.subheader("📋 Detailed Delivery List")

    display_df = df.copy()

    # ── Format date columns to string for display ────────────────
    date_columns = ['etd', 'created_date', 'delivered_date', 'dispatched_date']
    for col in date_columns:
        if col in display_df.columns:
            display_df[col] = pd.to_datetime(display_df[col], errors='coerce').dt.strftime('%Y-%m-%d')

    # ── Build column_config ──────────────────────────────────────
    column_config = _build_column_config(display_df)

    # ── Default column order (only existing columns) ─────────────
    col_order = [c for c in DEFAULT_COLUMNS if c in display_df.columns]

    # ── Render dataframe ─────────────────────────────────────────
    st.dataframe(
        display_df,
        column_order=col_order,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        height=min(700, 50 + len(display_df) * 35),
    )


# ── Column config builder ────────────────────────────────────────

def _build_column_config(df):
    """Build st.column_config dict with proper types, labels, and formats."""

    quantity_cols = {
        'standard_quantity', 'selling_quantity', 'remaining_quantity_to_deliver',
        'stock_out_quantity', 'stock_out_request_quantity',
        'total_instock_at_preferred_warehouse', 'total_instock_all_warehouses',
        'gap_quantity', 'product_gap_quantity', 'product_total_remaining_demand',
    }
    rate_cols = {
        'product_fulfill_rate_percent', 'fulfill_rate_percent',
        'delivery_demand_percentage',
    }
    currency_cols = {'shipping_cost', 'export_tax'}

    config = {}

    for col in df.columns:
        label = COLUMN_LABELS.get(col, col.replace('_', ' ').title())

        if col in quantity_cols:
            config[col] = st.column_config.NumberColumn(
                label, format="%,.0f",
            )
        elif col in rate_cols:
            config[col] = st.column_config.ProgressColumn(
                label, format="%.1f%%", min_value=0, max_value=100,
            )
        elif col in currency_cols:
            config[col] = st.column_config.NumberColumn(
                label, format="%,.2f",
            )
        elif col == 'days_overdue':
            config[col] = st.column_config.NumberColumn(
                label, format="%,.0f",
            )
        else:
            config[col] = st.column_config.TextColumn(label)

    return config