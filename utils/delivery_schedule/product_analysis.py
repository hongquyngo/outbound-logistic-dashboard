# utils/delivery_schedule/product_analysis.py
"""Product demand analysis fragment with shortage charts and detail tables"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime


@st.fragment
def display_product_analysis(df, data_loader):
    """Display product demand analysis"""
    st.subheader("🔍 Product Demand Analysis")

    product_analysis = data_loader.get_product_demand_from_dataframe(df)

    if product_analysis.empty:
        st.info("No product data available for the selected filters")
        return

    _check_data_quality(product_analysis)
    _display_product_metrics(product_analysis)
    _display_shortage_analysis(product_analysis)
    _display_product_detail_table(product_analysis)


# ── Data quality ─────────────────────────────────────────────────

def _check_data_quality(product_analysis):
    """Check and report data quality issues"""
    issues = []
    if 'fulfill_rate' not in product_analysis.columns:
        issues.append("Product fulfillment rate data not available")
    elif product_analysis['fulfill_rate'].isna().all():
        issues.append("Product fulfillment rate values are missing")
    if 'gap_quantity' not in product_analysis.columns:
        issues.append("Product gap quantity data not available")
    elif product_analysis['gap_quantity'].isna().all():
        issues.append("Product gap quantity values are missing")

    if issues:
        with st.expander("⚠️ Data Quality Notice", expanded=False):
            st.warning("Some product-level metrics are missing or incomplete:")
            for issue in issues:
                st.write(f"• {issue}")
            st.info("This may be due to missing columns in the source data.")


# ── Metrics ──────────────────────────────────────────────────────

def _display_product_metrics(product_analysis):
    """Display product analysis metrics"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        multi_delivery = len(product_analysis[product_analysis['active_deliveries'] > 1])
        st.metric("Multi-Delivery Products", f"{multi_delivery:,}",
                  help="Products being delivered to multiple locations/orders")

    with col2:
        if 'warehouse_count' in product_analysis.columns:
            multi_wh = len(product_analysis[product_analysis['warehouse_count'] > 1])
            st.metric("Multi-Warehouse Products", f"{multi_wh:,}",
                      help="Products that need inventory from multiple warehouses")
        else:
            st.metric("Multi-Warehouse Products", "N/A")

    with col3:
        if 'gap_quantity' in product_analysis.columns and 'fulfill_rate' in product_analysis.columns:
            critical = len(product_analysis[
                (product_analysis['gap_quantity'] > 0) & (product_analysis['fulfill_rate'] < 50)
            ])
            st.metric("Critical Products", f"{critical:,}",
                      help="Products with gap > 0 and fulfillment < 50%")
        else:
            st.metric("Critical Products", "N/A")

    with col4:
        if 'gap_percentage' in product_analysis.columns:
            avg_gap = product_analysis[product_analysis['gap_quantity'] > 0]['gap_percentage'].mean()
            st.metric("Avg Gap %", f"{avg_gap:.1f}%" if not pd.isna(avg_gap) else "0%",
                      help="Average shortage percentage for products with gaps")
        else:
            st.metric("Avg Gap %", "N/A")


# ── Shortage analysis ────────────────────────────────────────────

def _display_shortage_analysis(product_analysis):
    """Display product shortage analysis chart"""
    st.markdown("#### Product Shortage Analysis")

    with st.expander("ℹ️ Understanding Sort Options", expanded=False):
        st.markdown("""
        - **Gap Quantity (Units)**: Sort by actual number of units short
        - **Gap Percentage (%)**: Sort by percentage of demand that cannot be fulfilled
        - **Total Demand (Units)**: Sort by total demand volume
        """)

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        num_products = st.number_input("Products to display", min_value=5, max_value=50, value=15, step=1)
    with col2:
        sort_options = {}
        if 'gap_quantity' in product_analysis.columns:
            sort_options['Gap Quantity (Units)'] = 'gap_quantity'
        if 'gap_percentage' in product_analysis.columns:
            sort_options['Gap Percentage (%)'] = 'gap_percentage'
        sort_options['Total Demand (Units)'] = 'total_remaining_demand'

        sort_by = st.selectbox("Sort by", options=list(sort_options.keys()), index=0)
        sort_column = sort_options[sort_by]

    _create_shortage_chart(product_analysis, num_products, sort_column)


def _create_shortage_chart(product_analysis, num_products, sort_column):
    """Create product shortage chart"""
    if 'gap_quantity' in product_analysis.columns and sort_column in ['gap_quantity', 'gap_percentage']:
        shortage_products = product_analysis[product_analysis['gap_quantity'] > 0].copy()
    else:
        shortage_products = product_analysis.copy()

    if shortage_products.empty:
        if 'gap_quantity' in product_analysis.columns:
            st.success("✅ No products with shortage found in the filtered data!")
        else:
            st.info("No product data available for analysis")
        return

    if sort_column in shortage_products.columns:
        shortage_products = shortage_products.sort_values(sort_column, ascending=False)

    top_shortage = shortage_products.head(num_products).copy()

    if 'gap_quantity' not in top_shortage.columns or top_shortage['gap_quantity'].isna().all():
        _create_demand_chart(top_shortage)
    else:
        _create_gap_chart(top_shortage, sort_column)

    _display_shortage_summary(top_shortage)


def _create_gap_chart(chart_data, sort_column):
    """Create chart for products with gap data"""
    if 'brand' in chart_data.columns:
        chart_data['product_label'] = (
            chart_data['pt_code'] + '<br>' +
            chart_data['product_pn'].str[:25] + '<br><i>' +
            chart_data['brand'].fillna('No Brand') + '</i>'
        )
    else:
        chart_data['product_label'] = (
            chart_data['pt_code'] + '<br>' + chart_data['product_pn'].str[:30]
        )

    if sort_column == 'gap_percentage' and 'gap_percentage' in chart_data.columns:
        x_column, x_title, text_template = 'gap_percentage', 'Gap Percentage (%)', '%{x:.1f}%'
    elif sort_column == 'total_remaining_demand':
        x_column, x_title, text_template = 'total_remaining_demand', 'Total Remaining Demand', '%{x:,.0f}'
    else:
        x_column, x_title, text_template = 'gap_quantity', 'Gap Quantity', '%{x:,.0f}'

    hover_template = _build_hover_template(chart_data)
    customdata_cols = _get_customdata_columns(chart_data)

    fig = go.Figure()

    if 'fulfill_rate' in chart_data.columns and chart_data['fulfill_rate'].notna().any():
        fig.add_trace(go.Bar(
            y=chart_data['product_label'], x=chart_data[x_column], orientation='h',
            marker=dict(
                color=chart_data['fulfill_rate'], colorscale='RdYlGn', cmin=0, cmax=100,
                colorbar=dict(title='Fulfill<br>Rate %', thickness=15, len=0.7)
            ),
            customdata=chart_data[customdata_cols].values,
            hovertemplate=hover_template, name=''
        ))
    else:
        fig.add_trace(go.Bar(
            y=chart_data['product_label'], x=chart_data[x_column], orientation='h',
            marker_color='#ff6b6b',
            customdata=chart_data[customdata_cols].values,
            hovertemplate=hover_template, name=''
        ))

    sort_display = {
        'gap_quantity': 'Gap Quantity', 'gap_percentage': 'Gap Percentage',
        'total_remaining_demand': 'Total Demand'
    }.get(sort_column, 'Shortage')

    fig.update_layout(
        title=f'Top {len(chart_data)} Products by {sort_display}',
        xaxis_title=x_title, yaxis_title='',
        height=max(400, len(chart_data) * 50), showlegend=False,
        margin=dict(l=250), plot_bgcolor='white',
        xaxis=dict(gridcolor='lightgray', showgrid=True, zeroline=True, zerolinecolor='gray'),
        yaxis=dict(tickmode='linear', autorange='reversed')
    )
    fig.update_traces(texttemplate=text_template, textposition='outside')

    st.plotly_chart(fig, width="stretch")


def _create_demand_chart(chart_data):
    """Create fallback chart based on demand only"""
    st.info("Gap quantity data not available. Showing products by total demand.")

    if 'brand' in chart_data.columns:
        chart_data['product_label'] = (
            chart_data['pt_code'] + '<br>' +
            chart_data['product_pn'].str[:25] + '<br><i>' +
            chart_data['brand'].fillna('No Brand') + '</i>'
        )
    else:
        chart_data['product_label'] = (
            chart_data['pt_code'] + '<br>' + chart_data['product_pn'].str[:30]
        )

    hover_parts = ['<b>%{customdata[0]}</b>', 'Product: %{customdata[1]}', 'Total Demand: %{x:,.0f}']
    customdata_cols = ['pt_code', 'product_pn']
    if 'brand' in chart_data.columns:
        hover_parts.insert(2, 'Brand: %{customdata[2]}')
        customdata_cols.append('brand')

    fig = go.Figure(go.Bar(
        y=chart_data['product_label'], x=chart_data['total_remaining_demand'],
        orientation='h', marker_color='#3498db',
        text=chart_data['total_remaining_demand'], texttemplate='%{text:,.0f}', textposition='outside',
        hovertemplate='<br>'.join(hover_parts),
        customdata=chart_data[customdata_cols].values, name=''
    ))

    fig.update_layout(
        title=f'Top {len(chart_data)} Products by Total Demand',
        xaxis_title='Total Remaining Demand', yaxis_title='',
        height=max(400, len(chart_data) * 50), showlegend=False,
        margin=dict(l=250), plot_bgcolor='white',
        xaxis=dict(gridcolor='lightgray', showgrid=True, zeroline=True, zerolinecolor='gray'),
        yaxis=dict(tickmode='linear', autorange='reversed')
    )

    st.plotly_chart(fig, width="stretch")


def _build_hover_template(chart_data):
    """Build dynamic hover template based on available columns"""
    hover_parts = ['<b>%{customdata[0]}</b>', 'Product: %{customdata[1]}']
    idx = 2
    if 'brand' in chart_data.columns:
        hover_parts.append(f'Brand: %{{customdata[{idx}]}}'); idx += 1
    if 'gap_quantity' in chart_data.columns:
        hover_parts.append(f'Gap Quantity: %{{customdata[{idx}]:,.0f}}'); idx += 1
    hover_parts.append(f'Total Demand: %{{customdata[{idx}]:,.0f}}'); idx += 1
    if 'fulfill_rate' in chart_data.columns:
        hover_parts.append(f'Fulfillment Rate: %{{customdata[{idx}]:.1f}}%'); idx += 1
    if 'gap_percentage' in chart_data.columns:
        hover_parts.append(f'Gap %: %{{customdata[{idx}]:.1f}}%'); idx += 1
    return '<br>'.join(hover_parts)


def _get_customdata_columns(chart_data):
    """Get columns for customdata based on available columns"""
    cols = ['pt_code', 'product_pn']
    if 'brand' in chart_data.columns:
        cols.append('brand')
    if 'gap_quantity' in chart_data.columns:
        cols.append('gap_quantity')
    cols.append('total_remaining_demand')
    if 'fulfill_rate' in chart_data.columns:
        cols.append('fulfill_rate')
    if 'gap_percentage' in chart_data.columns:
        cols.append('gap_percentage')
    return cols


def _display_shortage_summary(top_shortage):
    """Display summary statistics for shortage analysis"""
    with st.expander("📊 Summary Statistics", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if 'gap_quantity' in top_shortage.columns:
                st.metric("Total Gap (Top Products)", f"{top_shortage['gap_quantity'].sum():,.0f}")
            else:
                st.metric("Total Gap", "N/A")
        with col2:
            st.metric("Total Demand (Top Products)", f"{top_shortage['total_remaining_demand'].sum():,.0f}")
        with col3:
            if 'fulfill_rate' in top_shortage.columns:
                st.metric("Avg Fulfillment Rate", f"{top_shortage['fulfill_rate'].mean():.1f}%")
            else:
                st.metric("Avg Fulfillment Rate", "N/A")
        with col4:
            if 'gap_percentage' in top_shortage.columns:
                st.metric("Avg Gap %", f"{top_shortage['gap_percentage'].mean():.1f}%")
            else:
                st.metric("Avg Gap %", "N/A")


# ── Product detail table ─────────────────────────────────────────

def _display_product_detail_table(product_analysis):
    """Display detailed product table with filters"""
    st.markdown("#### Product Detail Table")

    col1, col2, col3 = st.columns(3)
    with col1:
        show_critical_only = st.checkbox("Show critical products only", value=False)
    with col2:
        show_gaps_only = st.checkbox("Show products with gaps only", value=False)
    with col3:
        min_deliveries = st.number_input("Min active deliveries", min_value=0, value=0)

    table_data = product_analysis.copy()

    if show_critical_only and 'gap_quantity' in table_data.columns and 'fulfill_rate' in table_data.columns:
        table_data = table_data[(table_data['gap_quantity'] > 0) & (table_data['fulfill_rate'] < 50)]
    if show_gaps_only and 'gap_quantity' in table_data.columns:
        table_data = table_data[table_data['gap_quantity'] > 0]
    if min_deliveries > 0:
        table_data = table_data[table_data['active_deliveries'] >= min_deliveries]

    if table_data.empty:
        st.info("No products match the selected criteria")
        return

    display_cols = _get_product_table_columns(table_data)
    styled_table = _style_product_table(table_data[display_cols])

    st.dataframe(styled_table, width="stretch", height=400)
    st.caption(f"Showing {len(table_data)} of {len(product_analysis)} products")

    csv = table_data[display_cols].to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Filtered Product Data", data=csv,
        file_name=f"product_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime='text/csv'
    )


def _get_product_table_columns(table_data):
    default_columns = [
        'pt_code', 'product_pn', 'brand', 'active_deliveries',
        'total_remaining_demand', 'total_inventory',
        'gap_quantity', 'gap_percentage', 'fulfill_rate',
        'fulfillment_status', 'warehouse_count'
    ]
    return [col for col in default_columns if col in table_data.columns]


def _style_product_table(df):
    """Apply styling to product table"""
    numeric_formats = {
        'total_remaining_demand': '{:,.0f}', 'total_inventory': '{:,.0f}',
        'gap_quantity': '{:,.0f}', 'gap_percentage': '{:.1f}%',
        'fulfill_rate': '{:.1f}%', 'active_deliveries': '{:,}', 'warehouse_count': '{:,}'
    }
    format_spec = {col: fmt for col, fmt in numeric_formats.items() if col in df.columns}

    styled = df.style.format(format_spec, na_rep='-')
    if 'fulfill_rate' in df.columns:
        styled = styled.background_gradient(subset=['fulfill_rate'], cmap='RdYlGn', vmin=0, vmax=100)
    if 'fulfillment_status' in df.columns:
        styled = styled.map(_color_fulfillment_status, subset=['fulfillment_status'])
    return styled


def _color_fulfillment_status(val):
    colors = {
        'Out of Stock': 'background-color: #ffcccb; color: #721c24; font-weight: bold',
        'Can Fulfill Partial': 'background-color: #fff3cd; color: #856404',
        'Can Fulfill All': 'background-color: #d4edda; color: #155724',
        'Fulfilled': 'background-color: #d4edda; color: #155724',
        'Ready to Ship': 'background-color: #d4edda; color: #155724',
    }
    return colors.get(val, '')
