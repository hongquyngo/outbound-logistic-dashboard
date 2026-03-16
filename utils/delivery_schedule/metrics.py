# utils/delivery_schedule/metrics.py
"""Single-row KPI metrics for Delivery Schedule page.

Consolidated into one meaningful set — no expander, no duplicates.
Chosen metrics:
  1. Total Deliveries (unique DN)         — from filtered data
  2. Total Line Items                     — from filtered data
  3. Remaining Qty to Deliver             — from filtered data
  4. Overdue Deliveries (⚠️ GLOBAL)       — from ALL active data, ignores filters
  5. Avg Fulfillment Rate (overall health)— from filtered data
  6. Out-of-Stock Products (action needed)— from filtered data
"""

import streamlit as st
import pandas as pd


def display_metrics(df, df_all_active=None):
    """Display a single row of key delivery metrics.

    Parameters
    ----------
    df : DataFrame
        Filtered data — used for most KPIs.
    df_all_active : DataFrame, optional
        ALL active (non-completed) deliveries, unfiltered.
        Used exclusively for the Overdue metric so it always
        reflects the true global overdue count regardless of
        the user's current filter selection.
        Falls back to *df* when not provided.
    """
    # Overdue source: always the full active dataset
    overdue_source = df_all_active if df_all_active is not None and not df_all_active.empty else df

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        st.metric("Deliveries", f"{df['delivery_id'].nunique():,}")

    with c2:
        st.metric("Line Items", f"{len(df):,}")

    with c3:
        remaining = df['remaining_quantity_to_deliver'].sum()
        st.metric("Remaining Qty", f"{remaining:,.0f}")

    with c4:
        overdue_df = overdue_source[overdue_source['delivery_timeline_status'] == 'Overdue']
        overdue_count = overdue_df['delivery_id'].nunique()
        st.metric("⚠️ Overdue", f"{overdue_count:,}")
        if overdue_count > 0:
            _render_overdue_popover(overdue_df)

    with c5:
        avg_rate = df['product_fulfill_rate_percent'].mean()
        st.metric("Avg Fulfill %", f"{avg_rate:.1f}%")

    with c6:
        oos_df = df[df['product_fulfillment_status'] == 'Out of Stock']
        oos = oos_df['product_id'].nunique()
        st.metric("Out of Stock", f"{oos:,}")
        if oos > 0:
            _render_oos_popover(oos_df)


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


def _render_oos_popover(oos_df):
    """Popover with out-of-stock summary: product → customer → DN detail."""
    with st.popover("🔍 View out-of-stock details", use_container_width=True):

        # ── Summary by product ───────────────────────────────────
        st.markdown("**By Product**")

        # Build optional columns dynamically
        agg_dict = dict(
            DNs=('dn_number', 'nunique'),
            Customers=('customer', 'nunique'),
            Remaining_Qty=('remaining_quantity_to_deliver', 'sum'),
        )
        group_cols = ['pt_code', 'product_pn']
        group_cols = [c for c in group_cols if c in oos_df.columns]

        if not group_cols:
            st.info("No product columns available for summary.")
            return

        product_summary = (
            oos_df
            .groupby(group_cols)
            .agg(**agg_dict)
            .reset_index()
            .rename(columns={
                'pt_code': 'PT Code',
                'product_pn': 'Product',
                'Remaining_Qty': 'Remaining Qty',
            })
            .sort_values('Remaining Qty', ascending=False)
        )

        st.dataframe(
            product_summary.style
            .format({
                'Remaining Qty': '{:,.0f}',
                'DNs': '{:,.0f}',
                'Customers': '{:,.0f}',
            }, na_rep='-')
            .bar(subset=['Remaining Qty'], color='#ff9999'),
            use_container_width=True,
            hide_index=True,
        )

        # ── Detail by customer + DN ──────────────────────────────
        st.markdown("**By Customer / DN**")

        detail_cols = ['dn_number', 'customer', 'recipient_company',
                       'pt_code', 'product_pn', 'brand', 'etd',
                       'remaining_quantity_to_deliver']
        detail_cols = [c for c in detail_cols if c in oos_df.columns]

        detail_df = (
            oos_df[detail_cols]
            .drop_duplicates()
            .sort_values(
                [c for c in ['customer', 'etd', 'dn_number'] if c in detail_cols]
            )
            .rename(columns={
                'dn_number': 'DN Number',
                'customer': 'Customer',
                'recipient_company': 'Ship To',
                'pt_code': 'PT Code',
                'product_pn': 'Product',
                'brand': 'Brand',
                'etd': 'ETD',
                'remaining_quantity_to_deliver': 'Remaining Qty',
            })
        )

        fmt = {}
        if 'Remaining Qty' in detail_df.columns:
            fmt['Remaining Qty'] = '{:,.0f}'

        st.dataframe(
            detail_df.style.format(fmt, na_rep='-'),
            use_container_width=True,
            hide_index=True,
            height=min(400, 40 + len(detail_df) * 35),
        )