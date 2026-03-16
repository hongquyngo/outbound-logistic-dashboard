# utils/delivery_schedule/metrics.py
"""Single-row KPI metrics for Delivery Schedule page.

Consolidated into one meaningful set — no expander, no duplicates.
Chosen metrics:
  1. Total Deliveries (unique DN)
  2. Total Line Items
  3. Remaining Qty to Deliver
  4. Overdue Deliveries (attention-grabber) + popover detail
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
        overdue_df = df[df['delivery_timeline_status'] == 'Overdue']
        overdue_count = overdue_df['delivery_id'].nunique()
        st.metric(
            "Overdue",
            f"{overdue_count:,}",
            delta=f"{overdue_count} need attention" if overdue_count > 0 else None,
            delta_color="inverse" if overdue_count > 0 else "off",
        )
        if overdue_count > 0:
            _render_overdue_popover(overdue_df)

    with c5:
        avg_rate = df['product_fulfill_rate_percent'].mean()
        st.metric("Avg Fulfill %", f"{avg_rate:.1f}%")

    with c6:
        oos = df[df['product_fulfillment_status'] == 'Out of Stock']['product_id'].nunique()
        st.metric("Out of Stock", f"{oos:,}")


def _render_overdue_popover(overdue_df):
    """Popover with overdue summary table, sits right below the metric."""
    with st.popover("⚠️ View overdue details", use_container_width=True):
        summary = (
            overdue_df
            .groupby(['customer', 'recipient_company'])
            .agg(
                Deliveries=('delivery_id', 'nunique'),
                Max_Days_Overdue=('days_overdue', 'max'),
                Total_Qty=('remaining_quantity_to_deliver', 'sum'),
            )
            .reset_index()
            .rename(columns={
                'customer': 'Customer',
                'recipient_company': 'Ship To',
                'Max_Days_Overdue': 'Max Days Overdue',
                'Total_Qty': 'Total Qty',
            })
            .sort_values('Max Days Overdue', ascending=False)
        )

        st.dataframe(
            summary.style
            .format({
                'Total Qty': '{:,.0f}',
                'Max Days Overdue': '{:.0f} days',
                'Deliveries': '{:,.0f}',
            }, na_rep='-')
            .background_gradient(subset=['Max Days Overdue'], cmap='Reds')
            .bar(subset=['Total Qty'], color='#ff6b6b'),
            use_container_width=True,
            hide_index=True,
        )