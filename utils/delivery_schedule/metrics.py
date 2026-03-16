# utils/delivery_schedule/metrics.py
"""Top-level KPI metric cards for Delivery Schedule page"""

import streamlit as st
import pandas as pd


def display_metrics(df):
    """Display key metrics from the dataframe"""
    # Main metrics row
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Deliveries", f"{df['delivery_id'].nunique():,}")

    with col2:
        st.metric("Total Line Items", f"{len(df):,}")

    with col3:
        total_qty = df['standard_quantity'].sum()
        st.metric("Total Quantity", f"{total_qty:,.0f}")

    with col4:
        remaining_qty = df['remaining_quantity_to_deliver'].sum()
        st.metric("Remaining to Deliver", f"{remaining_qty:,.0f}")

    with col5:
        overdue_count = df[df['delivery_timeline_status'] == 'Overdue']['delivery_id'].nunique()
        st.metric("Overdue Deliveries", f"{overdue_count:,}",
                  delta_color="inverse" if overdue_count > 0 else "off")

    # Advanced metrics
    with st.expander("📊 Advanced Metrics", expanded=False):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            avg_fulfill_rate = df['product_fulfill_rate_percent'].mean()
            st.metric("Avg Product Fulfillment Rate", f"{avg_fulfill_rate:.1f}%")

        with col2:
            unique_products = df['product_id'].nunique()
            st.metric("Unique Products", f"{unique_products:,}")

        with col3:
            out_of_stock = df[df['product_fulfillment_status'] == 'Out of Stock']['product_id'].nunique()
            st.metric("Products Out of Stock", f"{out_of_stock:,}")

        with col4:
            total_gap = df.groupby('product_id')['product_gap_quantity'].first().sum()
            st.metric("Total Product Gap", f"{abs(total_gap):,.0f}")
