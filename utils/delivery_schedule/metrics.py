# utils/delivery_schedule/metrics.py
"""Single-row KPI metrics for Delivery Schedule page.

Consolidated into one meaningful set — no expander, no duplicates.
Chosen metrics:
  1. Total Deliveries (unique DN)
  2. Total Line Items
  3. Remaining Qty to Deliver
  4. Overdue Deliveries (attention-grabber)
  5. Avg Fulfillment Rate (overall health)
  6. Out-of-Stock Products (action needed)
"""

import streamlit as st
import pandas as pd


def display_metrics(df):
    """Display a single row of key delivery metrics."""
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        st.metric("Deliveries", f"{df['delivery_id'].nunique():,}")

    with c2:
        st.metric("Line Items", f"{len(df):,}")

    with c3:
        remaining = df['remaining_quantity_to_deliver'].sum()
        st.metric("Remaining Qty", f"{remaining:,.0f}")

    with c4:
        overdue = df[df['delivery_timeline_status'] == 'Overdue']['delivery_id'].nunique()
        st.metric(
            "Overdue",
            f"{overdue:,}",
            delta=f"{overdue} need attention" if overdue > 0 else None,
            delta_color="inverse" if overdue > 0 else "off",
        )

    with c5:
        avg_rate = df['product_fulfill_rate_percent'].mean()
        st.metric("Avg Fulfill %", f"{avg_rate:.1f}%")

    with c6:
        oos = df[df['product_fulfillment_status'] == 'Out of Stock']['product_id'].nunique()
        st.metric("Out of Stock", f"{oos:,}")