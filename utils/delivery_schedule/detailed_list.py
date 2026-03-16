# utils/delivery_schedule/detailed_list.py
"""Detailed delivery list fragment with conditional formatting"""

import streamlit as st
import pandas as pd


@st.fragment
def display_detailed_list(df):
    """Display detailed delivery list"""
    st.subheader("📋 Detailed Delivery List")

    # Column selection
    default_columns = ['dn_number', 'customer', 'recipient_company', 'etd',
                       'pt_code', 'product_pn', 'brand', 'standard_quantity',
                       'remaining_quantity_to_deliver', 'product_fulfill_rate_percent',
                       'delivery_timeline_status', 'days_overdue', 'shipment_status',
                       'product_fulfillment_status', 'is_epe_company']

    display_columns = st.multiselect(
        "Select columns to display",
        options=df.columns.tolist(),
        default=[col for col in default_columns if col in df.columns]
    )

    if not display_columns:
        st.info("Please select columns to display")
        return

    display_df = df[display_columns].copy()

    # Format date columns
    date_columns = ['etd', 'created_date', 'delivered_date', 'dispatched_date']
    for col in date_columns:
        if col in display_df.columns:
            display_df[col] = pd.to_datetime(display_df[col]).dt.strftime('%Y-%m-%d')

    styled_df = _style_detailed_list(display_df)
    st.dataframe(styled_df, width="stretch")


# ── Styling helpers ──────────────────────────────────────────────

def _style_detailed_list(df):
    """Apply styling to detailed list dataframe"""
    quantity_columns = ['standard_quantity', 'selling_quantity', 'remaining_quantity_to_deliver',
                        'stock_out_quantity', 'stock_out_request_quantity',
                        'total_instock_at_preferred_warehouse', 'total_instock_all_warehouses',
                        'gap_quantity', 'product_gap_quantity', 'product_total_remaining_demand']
    rate_columns = ['product_fulfill_rate_percent', 'fulfill_rate_percent', 'delivery_demand_percentage']
    currency_columns = ['shipping_cost', 'export_tax']

    format_dict = {}
    for col in quantity_columns:
        if col in df.columns:
            format_dict[col] = '{:,.0f}'
    for col in rate_columns:
        if col in df.columns:
            format_dict[col] = '{:.1f}%'
    for col in currency_columns:
        if col in df.columns:
            format_dict[col] = '{:,.2f}'
    if 'days_overdue' in df.columns:
        format_dict['days_overdue'] = '{:.0f}'

    styled = df.style.format(format_dict, na_rep='-')

    if 'delivery_timeline_status' in df.columns:
        styled = styled.map(_highlight_timeline_status, subset=['delivery_timeline_status'])
    if 'product_fulfillment_status' in df.columns:
        styled = styled.map(_highlight_fulfillment_status, subset=['product_fulfillment_status'])
    if 'is_epe_company' in df.columns:
        styled = styled.map(_highlight_epe_company, subset=['is_epe_company'])
    for col in rate_columns:
        if col in df.columns:
            styled = styled.map(_color_fulfill_rate, subset=[col])

    return styled


def _highlight_timeline_status(val):
    colors = {'Overdue': '#ffcccb', 'Due Today': '#ffe4b5', 'On Schedule': '#90ee90', 'Completed': '#e0e0e0'}
    return f'background-color: {colors[val]}' if val in colors else ''


def _highlight_fulfillment_status(val):
    colors = {'Out of Stock': '#ffcccb', 'Can Fulfill Partial': '#ffe4b5', 'Can Fulfill All': '#90ee90'}
    return f'background-color: {colors[val]}' if val in colors else ''


def _highlight_epe_company(val):
    return 'font-weight: bold; color: #1976d2' if val == 'Yes' else ''


def _color_fulfill_rate(val):
    try:
        if pd.isna(val):
            return ''
        num_val = float(str(val).replace('%', ''))
        if num_val >= 100:
            return 'color: green; font-weight: bold'
        elif num_val >= 50:
            return 'color: orange'
        else:
            return 'color: red; font-weight: bold'
    except Exception:
        return ''