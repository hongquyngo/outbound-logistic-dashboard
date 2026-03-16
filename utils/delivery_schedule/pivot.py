# utils/delivery_schedule/pivot.py
"""Pivot table fragment and helpers for Delivery Schedule page"""

import streamlit as st
import pandas as pd
from datetime import datetime


@st.fragment
def display_pivot_table(df, data_loader):
    """Display pivot table view"""
    st.subheader("📊 Pivot Table View")

    # View period selector
    col1, col2 = st.columns([1, 3])
    with col1:
        view_period = st.radio(
            "View Period:",
            options=['daily', 'weekly', 'monthly'],
            index=1,
            horizontal=True,
            help="Select how to group delivery data in the pivot table"
        )

    # Get pivoted data
    pivot_df = data_loader.pivot_delivery_data(df, view_period)

    if pivot_df.empty:
        st.info("No data available for pivot view")
        return

    # Grouping options
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        group_by_customer = st.checkbox("Group by Customer")
    with col2:
        group_by_product = st.checkbox("Group by Product (PT Code)")

    # Handle different grouping scenarios
    if group_by_customer and group_by_product:
        pivot_table = _create_customer_product_pivot(df, view_period)
        filename_prefix = "delivery_by_customer_product"
    elif group_by_customer:
        pivot_table = _create_customer_pivot(pivot_df)
        filename_prefix = "delivery_by_customer"
    elif group_by_product:
        pivot_table = _create_product_pivot(df, view_period)
        filename_prefix = "delivery_by_product"
    else:
        _display_default_pivot(pivot_df)
        pivot_table = pivot_df
        filename_prefix = "delivery_schedule"

    # Download button
    if 'pivot_table' in locals():
        csv = pivot_table.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"{filename_prefix}_{view_period}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime='text/csv'
        )


# ── Private helpers ──────────────────────────────────────────────

def _create_customer_product_pivot(df, view_period):
    """Create pivot table grouped by customer and product"""
    pivot_table = df.pivot_table(
        index=['customer', 'pt_code'],
        columns=pd.Grouper(key='etd', freq='W' if view_period == 'weekly' else 'D' if view_period == 'daily' else 'M'),
        values='standard_quantity',
        aggfunc='sum',
        fill_value=0
    )

    pivot_table.columns = pivot_table.columns.strftime(
        '%Y-%m-%d' if view_period == 'daily' else
        'Week of %Y-%m-%d' if view_period == 'weekly' else
        '%B %Y'
    )

    pivot_table = pivot_table.reset_index()

    # Merge product details
    product_cols = ['pt_code', 'product_pn', 'brand', 'package_size']
    available_product_cols = [col for col in product_cols if col in df.columns]
    product_info = df[available_product_cols].drop_duplicates(subset=['pt_code'])
    final_table = pd.merge(pivot_table, product_info, on='pt_code', how='left')

    # Reorder columns
    base_cols = ['customer', 'pt_code']
    if 'brand' in final_table.columns:
        base_cols.append('brand')
    if 'product_pn' in final_table.columns:
        base_cols.append('product_pn')
    if 'package_size' in final_table.columns:
        base_cols.append('package_size')

    period_cols = [col for col in final_table.columns if col not in base_cols + available_product_cols + ['customer']]
    final_table = final_table[base_cols + period_cols]

    column_rename = {
        'customer': 'Customer', 'pt_code': 'PT Code', 'brand': 'Brand',
        'product_pn': 'Product Name', 'package_size': 'Package Size'
    }
    final_table = final_table.rename(columns=column_rename)

    total_col = final_table[period_cols].sum(axis=1)
    final_table['_sort'] = total_col
    final_table = final_table.sort_values(['Customer', '_sort'], ascending=[True, False])
    final_table = final_table.drop('_sort', axis=1)

    _display_styled_pivot(final_table, period_cols, freeze_up_to='Package Size')
    return final_table


def _create_customer_pivot(pivot_df):
    """Create pivot table grouped by customer only"""
    pivot_table = pivot_df.pivot_table(
        index='Customer', columns='Period',
        values='Total Quantity', aggfunc='sum', fill_value=0
    )

    st.dataframe(
        pivot_table.style.format("{:,.0f}").background_gradient(cmap='Blues'),
        width="stretch"
    )
    return pivot_table


def _create_product_pivot(df, view_period):
    """Create pivot table grouped by product"""
    product_cols = ['pt_code', 'product_pn', 'brand', 'package_size']
    available_product_cols = [col for col in product_cols if col in df.columns]
    product_info = df[available_product_cols].drop_duplicates(subset=['pt_code']).set_index('pt_code')

    pivot_table = df.pivot_table(
        index='pt_code',
        columns=pd.Grouper(key='etd', freq='W' if view_period == 'weekly' else 'D' if view_period == 'daily' else 'M'),
        values='standard_quantity', aggfunc='sum', fill_value=0
    )

    period_columns = pivot_table.columns.strftime(
        '%Y-%m-%d' if view_period == 'daily' else
        'Week of %Y-%m-%d' if view_period == 'weekly' else
        '%B %Y'
    )
    pivot_table.columns = period_columns

    total_series = pivot_table.sum(axis=1)
    final_table = pd.concat([product_info, pivot_table], axis=1)
    final_table = final_table.loc[total_series.sort_values(ascending=False).index]
    final_table = final_table.reset_index()

    column_order = []
    column_rename = {}
    for col_name, display_name in [('pt_code', 'PT Code'), ('brand', 'Brand'),
                                    ('product_pn', 'Product Name'), ('package_size', 'Package Size')]:
        if col_name in final_table.columns:
            column_order.append(col_name)
            column_rename[col_name] = display_name

    column_order.extend(period_columns)
    final_table = final_table[column_order].rename(columns=column_rename)

    period_col_names = [col for col in final_table.columns if col not in column_rename.values()]
    _display_styled_pivot(final_table, period_col_names, freeze_up_to='Package Size')
    return final_table


def _display_styled_pivot(table, period_columns, freeze_up_to='Package Size'):
    """Display a styled pivot table with frozen columns"""
    format_dict = {col: '{:,.0f}' for col in period_columns}
    styled_table = table.style.format(format_dict, na_rep='-')

    if period_columns:
        styled_table = styled_table.background_gradient(subset=period_columns, cmap='Blues')

    freeze_columns = []
    for col in table.columns:
        freeze_columns.append(col)
        if col == freeze_up_to:
            break

    num_freeze = len(freeze_columns)
    if num_freeze > 0:
        styled_table = styled_table.set_sticky(axis="columns", levels=list(range(num_freeze)))

    column_config = {}
    for col in table.columns:
        if col in ['Customer', 'PT Code', 'Brand', 'Product Name', 'Package Size']:
            width = "large" if col == 'Customer' else ("small" if col in ['PT Code', 'Brand', 'Package Size'] else "medium")
            column_config[col] = st.column_config.TextColumn(col, width=width)
        elif col in period_columns:
            column_config[col] = st.column_config.NumberColumn(col, format="%.0f", width="small")

    st.dataframe(styled_table, width="stretch", height=600, column_config=column_config)


def _display_default_pivot(pivot_df):
    """Display default pivot view without grouping"""
    format_dict = {
        'Total Quantity': '{:,.0f}', 'Remaining to Deliver': '{:,.0f}',
        'Gap (Legacy)': '{:,.0f}', 'Product Gap': '{:,.0f}',
        'Total Product Demand': '{:,.0f}', 'Deliveries': '{:,.0f}'
    }
    existing_formats = {col: fmt for col, fmt in format_dict.items() if col in pivot_df.columns}
    st.dataframe(pivot_df.style.format(existing_formats, na_rep='-'), width="stretch")
