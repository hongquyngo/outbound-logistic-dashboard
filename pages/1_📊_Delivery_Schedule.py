# pages/1_📊_Delivery_Schedule.py

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.auth import AuthManager
from utils.data_loader import DeliveryDataLoader
import plotly.express as px
import plotly.graph_objects as go

# Page config
st.set_page_config(
    page_title="Delivery Schedule",
    page_icon="📊",
    layout="wide"
)

# Check authentication
auth_manager = AuthManager()
if not auth_manager.check_session():
    st.warning("⚠️ Please login to access this page")
    st.stop()

# Initialize data loader
data_loader = DeliveryDataLoader()

st.title("📊 Delivery Schedule")


# Get filter options
filter_options = data_loader.get_filter_options()

# Filter Section
with st.expander("🔍 Filters", expanded=True):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Date range - NOW DYNAMIC
        date_range_options = filter_options.get('date_range', {})
        min_date = date_range_options.get('min_date', datetime.now().date() - timedelta(days=365))
        max_date = date_range_options.get('max_date', datetime.now().date() + timedelta(days=365))
        
        # Convert to date if datetime
        if hasattr(min_date, 'date'):
            min_date = min_date.date()
        if hasattr(max_date, 'date'):
            max_date = max_date.date()
        
        # Set default date range to full available range
        default_start = min_date if min_date else datetime.now().date() - timedelta(days=365)
        default_end = max_date if max_date else datetime.now().date() + timedelta(days=365)

        date_range = st.date_input(
            "Date Range",
            value=(default_start, default_end),
            min_value=min_date,
            max_value=max_date,
            help=f"Available data from {min_date} to {max_date}"
        )

        # Legal Entity filter
        selected_legal_entities = st.multiselect(
            "Legal Entity",
            options=filter_options.get('legal_entities', []),
            default=None,
            placeholder="All legal entities",
            help="Filter by selling company/legal entity"
        )

    with col2:
        # Creator filter
        selected_creators = st.multiselect(
            "Creator/Sales",
            options=filter_options.get('creators', []),
            default=None,
            placeholder="All creators"
        )
        
        # Customer filter
        selected_customers = st.multiselect(
            "Customer (Sold-To)",
            options=filter_options.get('customers', []),
            default=None,
            placeholder="All customers"
        )
    
    with col3:
        # Ship-to filter
        selected_ship_to = st.multiselect(
            "Ship-To Company",
            options=filter_options.get('ship_to_companies', []),
            default=None,
            placeholder="All ship-to companies"
        )
        
        # Location filter
        col3_1, col3_2 = st.columns(2)
        with col3_1:
            selected_states = st.multiselect(
                "State/Province",
                options=filter_options.get('states', []),
                default=None,
                placeholder="All states"
            )
        
        with col3_2:
            selected_countries = st.multiselect(
                "Country",
                options=filter_options.get('countries', []),
                default=None,
                placeholder="All countries"
            )

    # Second row of filters
    col4, col5, col6 = st.columns(3)

    with col4:
        col4_1, col4_2 = st.columns(2)
        with col4_1:
            # EPE Company filter - NOW DYNAMIC
            epe_options = filter_options.get('epe_options', ["All"])
            epe_filter = st.selectbox(
                "EPE Company Filter",
                options=epe_options,
                index=0,
                help="Filter by EPE company type. EPE companies are a specific customer category."
            )

        with col4_2:
            # Foreign customer filter - NOW DYNAMIC
            foreign_options = filter_options.get('foreign_options', ["All Customers"])
            foreign_filter = st.selectbox(
                "Customer Type",
                options=foreign_options,
                index=0,
                help="Filter by customer location. Domestic = same country as seller, Foreign = different country."
            )

    with col5:
        # Product filter - NOW DYNAMIC
        product_options = filter_options.get('products', [])
        selected_products = st.multiselect(
            "Product",
            options=product_options,
            default=None,
            placeholder="All products",
            help="Filter by product PT Code or Product PN"
        )
        
        # If products are selected, extract pt_codes
        if selected_products:
            pt_codes = [p.split(' - ')[0] for p in selected_products]
            st.session_state.selected_pt_codes = pt_codes
        else:
            st.session_state.selected_pt_codes = None

    with col6:
        # Timeline status filter
        selected_timeline = st.multiselect(
            "Delivery Timeline Status",
            options=filter_options.get('timeline_statuses', []),
            default=None,
            placeholder="All statuses",
            help="Filter by delivery timeline: Overdue, Due Today, On Schedule, Completed"
        )

# Apply filters button
if st.button("🔄 Apply Filters", type="primary", use_container_width=True):
    st.session_state.filters_applied = True

# Prepare filters
filters = {
    'date_from': date_range[0] if len(date_range) >= 1 else None,
    'date_to': date_range[1] if len(date_range) >= 2 else date_range[0],
    'creators': selected_creators if selected_creators else None,
    'customers': selected_customers if selected_customers else None,
    'products': selected_products if selected_products else None,
    'ship_to_companies': selected_ship_to if selected_ship_to else None,
    'states': selected_states if selected_states else None,
    'countries': selected_countries if selected_countries else None,
    'epe_filter': epe_filter,
    'foreign_filter': foreign_filter,
    'timeline_status': selected_timeline if selected_timeline else None,
    'legal_entities': selected_legal_entities if selected_legal_entities else None
}

# Load data
with st.spinner("Loading delivery data..."):
    df = data_loader.load_delivery_data(filters)

if df is not None and not df.empty:
    # Display enhanced metrics
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
        # New metric: Overdue deliveries
        overdue_count = df[df['delivery_timeline_status'] == 'Overdue']['delivery_id'].nunique()
        st.metric("Overdue Deliveries", f"{overdue_count:,}", 
                 delta_color="inverse" if overdue_count > 0 else "off")
    
    # Additional metrics row (NEW)
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
    
    # st.markdown("---")
    

    # Create tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Pivot Table", "📈 Charts", "📋 Detailed List", "🔍 Product Analysis"])

    with tab1:
        st.subheader("📊 Pivot Table View")
        
        # View period selector - NOW HERE
        col1, col2 = st.columns([1, 3])
        with col1:
            view_period = st.radio(
                "View Period:",
                options=['daily', 'weekly', 'monthly'],
                index=1,  # Default to weekly
                horizontal=True,
                help="Select how to group delivery data in the pivot table"
            )
        
        # Get pivoted data with selected period
        pivot_df = data_loader.pivot_delivery_data(df, view_period)
        
        if not pivot_df.empty:
            # Rest of pivot table code
            if st.checkbox("Group by Customer"):
                pivot_table = pivot_df.pivot_table(
                    index='Customer',
                    columns='Period',
                    values='Total Quantity',
                    aggfunc='sum',
                    fill_value=0
                )
                # Format pivot table with thousand separator
                st.dataframe(
                    pivot_table.style.format("{:,.0f}").background_gradient(cmap='Blues'),
                    use_container_width=True
                )
            else:
                # Format pivot dataframe columns
                format_dict = {
                    'Total Quantity': '{:,.0f}',
                    'Remaining to Deliver': '{:,.0f}',
                    'Gap (Legacy)': '{:,.0f}',
                    'Product Gap': '{:,.0f}',
                    'Total Product Demand': '{:,.0f}',
                    'Deliveries': '{:,.0f}'
                }
                
                # Apply formats that exist in the dataframe
                existing_formats = {col: fmt for col, fmt in format_dict.items() if col in pivot_df.columns}
                
                st.dataframe(
                    pivot_df.style.format(existing_formats, na_rep='-'),
                    use_container_width=True
                )
            
            # Download button
            csv = pivot_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"delivery_schedule_{view_period}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime='text/csv'
            )
        else:
            st.info("No data available for pivot view")

    with tab2:
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Timeline chart with status breakdown
            timeline_df = df.groupby([pd.to_datetime(df['etd']).dt.date, 'delivery_timeline_status']).agg({
                'delivery_id': 'nunique'
            }).reset_index()
            timeline_df.columns = ['Date', 'Status', 'Count']
            
            fig1 = px.bar(
                timeline_df,
                x='Date',
                y='Count',
                color='Status',
                title='Delivery Timeline Status',
                color_discrete_map={
                    'Completed': '#2ecc71',
                    'On Schedule': '#3498db',
                    'Due Today': '#f39c12',
                    'Overdue': '#e74c3c',
                    'No ETD': '#95a5a6'
                }
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Product fulfillment status distribution
            fulfillment_df = df.groupby('product_fulfillment_status')['product_id'].nunique().reset_index()
            fulfillment_df.columns = ['Status', 'Product Count']
            
            fig2 = px.pie(
                fulfillment_df, 
                values='Product Count', 
                names='Status',
                title='Product Fulfillment Status',
                color_discrete_map={
                    'Can Fulfill All': '#2ecc71',
                    'Can Fulfill Partial': '#f39c12',
                    'Out of Stock': '#e74c3c',
                    'Ready to Ship': '#3498db',
                    'Delivered': '#95a5a6'
                }
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # Days overdue distribution (NEW)
        overdue_df = df[df['days_overdue'].notna()].copy()
        if not overdue_df.empty:
            fig3 = px.histogram(
                overdue_df,
                x='days_overdue',
                nbins=20,
                title='Distribution of Overdue Days',
                labels={'days_overdue': 'Days Overdue', 'count': 'Number of Deliveries'}
            )
            fig3.update_traces(marker_color='#e74c3c')
            st.plotly_chart(fig3, use_container_width=True)
    
    with tab3:
        # Detailed list
        st.subheader("📋 Detailed Delivery List")
        
        # Select columns to display - Updated with new fields
        default_columns = ['dn_number', 'customer', 'recipient_company', 'etd', 
                            'pt_code', 'product_pn', 'standard_quantity', 'remaining_quantity_to_deliver',
                            'product_fulfill_rate_percent', 'delivery_timeline_status',
                            'days_overdue', 'shipment_status_vn', 'product_fulfillment_status', 
                            'is_epe_company']
        
        display_columns = st.multiselect(
            "Select columns to display",
            options=df.columns.tolist(),
            default=[col for col in default_columns if col in df.columns]
        )
        
        if display_columns:
            display_df = df[display_columns].copy()
            
            # Format date columns
            date_columns = ['etd', 'created_date', 'delivered_date', 'dispatched_date']
            for col in date_columns:
                if col in display_df.columns:
                    display_df[col] = pd.to_datetime(display_df[col]).dt.strftime('%Y-%m-%d')
            
            # Define quantity and numeric columns for formatting
            quantity_columns = ['standard_quantity', 'selling_quantity', 'remaining_quantity_to_deliver',
                              'stock_out_quantity', 'stock_out_request_quantity', 
                              'total_instock_at_preferred_warehouse', 'total_instock_all_warehouses',
                              'gap_quantity', 'product_gap_quantity', 'product_total_remaining_demand']
            
            rate_columns = ['product_fulfill_rate_percent', 'fulfill_rate_percent', 'delivery_demand_percentage']
            
            # Apply conditional formatting
            def highlight_timeline(val):
                if val == 'Overdue':
                    return 'background-color: #ffcccb'
                elif val == 'Due Today':
                    return 'background-color: #ffe4b5'
                elif val == 'On Schedule':
                    return 'background-color: #90ee90'
                elif val == 'Completed':
                    return 'background-color: #e0e0e0'
                return ''
            
            def highlight_fulfillment(val):
                if val == 'Out of Stock':
                    return 'background-color: #ffcccb'
                elif val == 'Can Fulfill Partial':
                    return 'background-color: #ffe4b5'
                elif val == 'Can Fulfill All':
                    return 'background-color: #90ee90'
                return ''
            
            def highlight_epe(val):
                if val == 'Yes':
                    return 'font-weight: bold; color: #1976d2'
                return ''
            
            def color_fulfill_rate(val):
                """Color code fulfillment rate"""
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
                except:
                    return ''
            
            # Create format dict for numeric columns
            format_dict = {}
            
            # Format quantity columns - no decimals, thousand separator
            for col in quantity_columns:
                if col in display_df.columns:
                    format_dict[col] = '{:,.0f}'
            
            # Format rate columns - 1 decimal place with % sign
            for col in rate_columns:
                if col in display_df.columns:
                    format_dict[col] = '{:.1f}%'
            
            # Format days overdue - no decimals
            if 'days_overdue' in display_df.columns:
                format_dict['days_overdue'] = '{:.0f}'
            
            # Format currency columns if any
            currency_columns = ['shipping_cost', 'export_tax']
            for col in currency_columns:
                if col in display_df.columns:
                    format_dict[col] = '{:,.2f}'
            
            # Apply styling
            styled_df = display_df.style.format(format_dict, na_rep='-')
            
            if 'delivery_timeline_status' in display_df.columns:
                styled_df = styled_df.applymap(
                    highlight_timeline, 
                    subset=['delivery_timeline_status']
                )
            
            if 'product_fulfillment_status' in display_df.columns:
                styled_df = styled_df.applymap(
                    highlight_fulfillment,
                    subset=['product_fulfillment_status']
                )
            
            if 'is_epe_company' in display_df.columns:
                styled_df = styled_df.applymap(
                    highlight_epe,
                    subset=['is_epe_company']
                )
            
            # Apply color to fulfillment rate columns
            for col in rate_columns:
                if col in display_df.columns:
                    styled_df = styled_df.applymap(
                        color_fulfill_rate,
                        subset=[col]
                    )
            
            st.dataframe(styled_df, use_container_width=True)
    
    with tab4:
        # Product Analysis tab - Focus on unique product insights
        st.subheader("🔍 Product Demand Analysis")
        
        # Use the new hybrid method - now filtered!
        product_analysis = data_loader.get_product_demand_from_dataframe(df)
        
        if not product_analysis.empty:
            # Check data quality issues
            data_quality_issues = []
            if 'fulfill_rate' not in product_analysis.columns:
                data_quality_issues.append("Product fulfillment rate data not available")
            elif product_analysis['fulfill_rate'].isna().all():
                data_quality_issues.append("Product fulfillment rate values are missing")
            
            if 'gap_quantity' not in product_analysis.columns:
                data_quality_issues.append("Product gap quantity data not available")
            elif product_analysis['gap_quantity'].isna().all():
                data_quality_issues.append("Product gap quantity values are missing")
                
            if data_quality_issues:
                with st.expander("⚠️ Data Quality Notice", expanded=False):
                    st.warning("Some product-level metrics are missing or incomplete:")
                    for issue in data_quality_issues:
                        st.write(f"• {issue}")
                    st.info("This may be due to missing 'product_fulfill_rate_percent' or 'product_gap_quantity' columns in the source data.")
            
            # Display unique metrics not shown in other tabs
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                # Products with multiple delivery points
                multi_delivery_products = len(product_analysis[product_analysis['active_deliveries'] > 1])
                st.metric(
                    "Multi-Delivery Products", 
                    f"{multi_delivery_products:,}",
                    help="Products being delivered to multiple locations/orders"
                )
            
            with col2:
                # Products requiring multiple warehouses
                if 'warehouse_count' in product_analysis.columns:
                    multi_warehouse_products = len(product_analysis[product_analysis['warehouse_count'] > 1])
                    st.metric(
                        "Multi-Warehouse Products", 
                        f"{multi_warehouse_products:,}",
                        help="Products that need inventory from multiple warehouses"
                    )
                else:
                    st.metric("Multi-Warehouse Products", "N/A")
            
            with col3:
                # Critical products (unique metric)
                if 'gap_quantity' in product_analysis.columns and 'fulfill_rate' in product_analysis.columns:
                    critical_products = len(product_analysis[
                        (product_analysis['gap_quantity'] > 0) & 
                        (product_analysis['fulfill_rate'] < 50)
                    ])
                    st.metric(
                        "Critical Products", 
                        f"{critical_products:,}",
                        help="Products with gap > 0 and fulfillment < 50%"
                    )
                else:
                    st.metric("Critical Products", "N/A")
            
            with col4:
                # Average gap percentage
                if 'gap_percentage' in product_analysis.columns:
                    avg_gap_percentage = product_analysis[product_analysis['gap_quantity'] > 0]['gap_percentage'].mean()
                    st.metric(
                        "Avg Gap %", 
                        f"{avg_gap_percentage:.1f}%" if not pd.isna(avg_gap_percentage) else "0%",
                        help="Average shortage percentage for products with gaps"
                    )
                else:
                    st.metric("Avg Gap %", "N/A")
            
            # Product shortage analysis with configurable display
            st.markdown("#### Product Shortage Analysis")
            
            # Help text about sorting options
            with st.expander("ℹ️ Understanding Sort Options", expanded=False):
                st.markdown("""
                - **Gap Quantity (Units)**: Sort by actual number of units short
                - Use when: Volume matters most (e.g., warehouse space, shipping capacity)
                - Example: Product A missing 1,000 units > Product B missing 100 units
                
                - **Gap Percentage (%)**: Sort by percentage of demand that cannot be fulfilled  
                - Use when: Service level matters most (e.g., customer satisfaction)
                - Example: Product B missing 90% (90/100) > Product A missing 10% (1,000/10,000)
                
                - **Total Demand (Units)**: Sort by total demand volume
                - Use when: Focusing on high-volume products
                """)
            
            # Configuration section
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                # Number of products to display
                num_products = st.number_input(
                    "Products to display",
                    min_value=5,
                    max_value=50,
                    value=15,
                    step=1,
                    help="Number of products to show in the chart"
                )
            
            with col2:
                # Sort criteria
                # Only show available sort options
                available_sort_options = {}
                if 'gap_quantity' in product_analysis.columns:
                    available_sort_options['Gap Quantity (Units)'] = 'gap_quantity'
                if 'gap_percentage' in product_analysis.columns:
                    available_sort_options['Gap Percentage (%)'] = 'gap_percentage'
                available_sort_options['Total Demand (Units)'] = 'total_remaining_demand'
                
                sort_by = st.selectbox(
                    "Sort by",
                    options=list(available_sort_options.keys()),
                    index=0,
                    help="Choose how to prioritize products"
                )
                sort_column = available_sort_options[sort_by]
            
            # Filter and sort data
            if 'gap_quantity' in product_analysis.columns and sort_column in ['gap_quantity', 'gap_percentage']:
                # Focus on products with shortage when sorting by gap metrics
                shortage_products = product_analysis[product_analysis['gap_quantity'] > 0].copy()
            else:
                # If no gap data or sorting by demand, show all products
                shortage_products = product_analysis.copy()
            
            if not shortage_products.empty:
                # Apply sorting
                if sort_column in shortage_products.columns:
                    shortage_products = shortage_products.sort_values(sort_column, ascending=False)
                
                # Get top N products
                top_shortage = shortage_products.head(num_products)
                
                # Create comprehensive chart
                if 'gap_quantity' in top_shortage.columns and top_shortage['gap_quantity'].notna().any():
                    # Main metric is gap quantity
                    chart_data = top_shortage.copy()
                    
                    # Create product label with PT code and PN
                    chart_data['product_label'] = chart_data['pt_code'] + '<br>' + chart_data['product_pn'].str[:30]
                    
                    # Determine which metric to display on X-axis based on sort
                    if sort_column == 'gap_percentage' and 'gap_percentage' in chart_data.columns:
                        x_column = 'gap_percentage'
                        x_title = 'Gap Percentage (%)'
                        text_template = '%{x:.1f}%'
                    elif sort_column == 'total_remaining_demand':
                        x_column = 'total_remaining_demand'
                        x_title = 'Total Remaining Demand'
                        text_template = '%{x:,.0f}'
                    else:
                        x_column = 'gap_quantity'
                        x_title = 'Gap Quantity'
                        text_template = '%{x:,.0f}'
                    
                    # Build hover template dynamically
                    hover_parts = [
                        '<b>%{customdata[0]}</b>',
                        'Product: %{customdata[1]}'
                    ]
                    customdata_cols = ['pt_code', 'product_pn']
                    
                    # Always show key metrics
                    idx = 2
                    if 'gap_quantity' in chart_data.columns:
                        hover_parts.append(f'Gap Quantity: %{{customdata[{idx}]:,.0f}}')
                        customdata_cols.append('gap_quantity')
                        idx += 1
                    
                    hover_parts.append(f'Total Demand: %{{customdata[{idx}]:,.0f}}')
                    customdata_cols.append('total_remaining_demand')
                    idx += 1
                    
                    # Add optional fields if they exist
                    if 'fulfill_rate' in chart_data.columns:
                        hover_parts.append(f'Fulfillment Rate: %{{customdata[{idx}]:.1f}}%')
                        customdata_cols.append('fulfill_rate')
                        idx += 1
                    
                    if 'gap_percentage' in chart_data.columns:
                        hover_parts.append(f'Gap %: %{{customdata[{idx}]:.1f}}%')
                        customdata_cols.append('gap_percentage')
                        idx += 1
                    
                    if 'total_inventory' in chart_data.columns:
                        hover_parts.append(f'Current Inventory: %{{customdata[{idx}]:,.0f}}')
                        customdata_cols.append('total_inventory')
                        idx += 1
                    
                    if 'active_deliveries' in chart_data.columns:
                        hover_parts.append(f'Active Deliveries: %{{customdata[{idx}]}}')
                        customdata_cols.append('active_deliveries')
                        idx += 1
                    
                    if 'warehouse_count' in chart_data.columns:
                        hover_parts.append(f'Warehouses: %{{customdata[{idx}]}}')
                        customdata_cols.append('warehouse_count')
                    
                    hover_template = '<br>'.join(hover_parts)
                    
                    # Create figure
                    fig = go.Figure()
                    
                    # Add bars
                    if 'fulfill_rate' in chart_data.columns and chart_data['fulfill_rate'].notna().any():
                        # Color by fulfillment rate
                        fig.add_trace(go.Bar(
                            y=chart_data['product_label'],
                            x=chart_data[x_column],
                            orientation='h',
                            marker=dict(
                                color=chart_data['fulfill_rate'],
                                colorscale='RdYlGn',
                                cmin=0,
                                cmax=100,
                                colorbar=dict(
                                    title='Fulfill<br>Rate %',
                                    thickness=15,
                                    len=0.7
                                )
                            ),
                            customdata=chart_data[customdata_cols].values,
                            hovertemplate=hover_template,
                            name=''
                        ))
                    else:
                        # Single color if no fulfill rate
                        fig.add_trace(go.Bar(
                            y=chart_data['product_label'],
                            x=chart_data[x_column],
                            orientation='h',
                            marker_color='#ff6b6b',
                            customdata=chart_data[customdata_cols].values,
                            hovertemplate=hover_template,
                            name=''
                        ))
                    
                    # Update layout
                    sort_display = {
                        'gap_quantity': 'Gap Quantity',
                        'gap_percentage': 'Gap Percentage', 
                        'total_remaining_demand': 'Total Demand'
                    }.get(sort_column, 'Shortage')
                    
                    fig.update_layout(
                        title=f'Top {len(top_shortage)} Products by {sort_display}',
                        xaxis_title=x_title,
                        yaxis_title='',
                        height=max(400, len(top_shortage) * 40),  # Dynamic height
                        showlegend=False,
                        margin=dict(l=200),  # More space for product labels
                        plot_bgcolor='white',
                        xaxis=dict(
                            gridcolor='lightgray',
                            showgrid=True,
                            zeroline=True,
                            zerolinecolor='gray'
                        ),
                        yaxis=dict(
                            tickmode='linear',
                            autorange='reversed'  # Top product at top
                        )
                    )
                    
                    # Add value labels on bars
                    fig.update_traces(
                        texttemplate=text_template,
                        textposition='outside'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Summary statistics below chart
                    with st.expander("📊 Summary Statistics", expanded=False):
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            total_gap = top_shortage['gap_quantity'].sum()
                            st.metric("Total Gap (Top Products)", f"{total_gap:,.0f}")
                        
                        with col2:
                            total_demand = top_shortage['total_remaining_demand'].sum()
                            st.metric("Total Demand (Top Products)", f"{total_demand:,.0f}")
                        
                        with col3:
                            if 'fulfill_rate' in top_shortage.columns:
                                avg_fulfill = top_shortage['fulfill_rate'].mean()
                                st.metric("Avg Fulfillment Rate", f"{avg_fulfill:.1f}%")
                            else:
                                st.metric("Avg Fulfillment Rate", "N/A")
                        
                        with col4:
                            if 'gap_percentage' in top_shortage.columns:
                                avg_gap_pct = top_shortage['gap_percentage'].mean()
                                st.metric("Avg Gap %", f"{avg_gap_pct:.1f}%")
                            else:
                                st.metric("Avg Gap %", "N/A")
                else:
                    # Fallback to demand-based chart if no gap data
                    st.info("Gap quantity data not available. Showing products by total demand.")
                    
                    chart_data = top_shortage.copy()
                    chart_data['product_label'] = chart_data['pt_code'] + '<br>' + chart_data['product_pn'].str[:30]
                    
                    # Build dynamic hover template
                    hover_parts = [
                        '<b>%{customdata[0]}</b>',
                        'Product: %{customdata[1]}',
                        'Total Demand: %{x:,.0f}'
                    ]
                    customdata_cols = ['pt_code', 'product_pn']
                    
                    idx = 2
                    if 'active_deliveries' in chart_data.columns:
                        hover_parts.append(f'Active Deliveries: %{{customdata[{idx}]}}')
                        customdata_cols.append('active_deliveries')
                        idx += 1
                    
                    if 'warehouse_count' in chart_data.columns:
                        hover_parts.append(f'Warehouses: %{{customdata[{idx}]}}')
                        customdata_cols.append('warehouse_count')
                        idx += 1
                    
                    if 'total_inventory' in chart_data.columns:
                        hover_parts.append(f'Current Inventory: %{{customdata[{idx}]:,.0f}}')
                        customdata_cols.append('total_inventory')
                    
                    fig = go.Figure(go.Bar(
                        y=chart_data['product_label'],
                        x=chart_data['total_remaining_demand'],
                        orientation='h',
                        marker_color='#3498db',
                        text=chart_data['total_remaining_demand'],
                        texttemplate='%{text:,.0f}',
                        textposition='outside',
                        hovertemplate='<br>'.join(hover_parts),
                        customdata=chart_data[customdata_cols].values,
                        name=''
                    ))
                    
                    fig.update_layout(
                        title=f'Top {len(top_shortage)} Products by Total Demand',
                        xaxis_title='Total Remaining Demand',
                        yaxis_title='',
                        height=max(400, len(top_shortage) * 40),
                        showlegend=False,
                        margin=dict(l=200),
                        plot_bgcolor='white',
                        xaxis=dict(
                            gridcolor='lightgray',
                            showgrid=True,
                            zeroline=True,
                            zerolinecolor='gray'
                        ),
                        yaxis=dict(
                            tickmode='linear',
                            autorange='reversed'
                        )
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
            else:
                if 'gap_quantity' in product_analysis.columns:
                    st.success("✅ No products with shortage found in the filtered data!")
                else:
                    st.info("No product data available for analysis")
            
            # Product detail table
            st.markdown("#### Product Detail Table")
            
            # Filter options for the table
            col1, col2, col3 = st.columns(3)
            with col1:
                show_critical_only = st.checkbox("Show critical products only", value=False)
            with col2:
                show_gaps_only = st.checkbox("Show products with gaps only", value=False)
            with col3:
                min_deliveries = st.number_input("Min active deliveries", min_value=0, value=0)
            
            # Apply table filters
            table_data = product_analysis.copy()
            if show_critical_only and 'gap_quantity' in table_data.columns and 'fulfill_rate' in table_data.columns:
                table_data = table_data[(table_data['gap_quantity'] > 0) & (table_data['fulfill_rate'] < 50)]
            if show_gaps_only and 'gap_quantity' in table_data.columns:
                table_data = table_data[table_data['gap_quantity'] > 0]
            if min_deliveries > 0:
                table_data = table_data[table_data['active_deliveries'] >= min_deliveries]
            
            if not table_data.empty:
                # Select columns for display - dynamically build based on available columns
                possible_columns = [
                    'pt_code', 'product_pn', 'active_deliveries', 'unique_orders',
                    'total_remaining_demand', 'total_inventory', 'preferred_warehouse_inventory',
                    'gap_quantity', 'gap_percentage', 'fulfill_rate', 
                    'fulfillment_status', 'warehouse_count', 'avg_demand_percentage'
                ]
                
                # Default columns - only include those that exist
                default_columns = [
                    'pt_code', 'product_pn', 'active_deliveries', 
                    'total_remaining_demand', 'total_inventory',
                    'gap_quantity', 'gap_percentage', 'fulfill_rate', 
                    'fulfillment_status', 'warehouse_count'
                ]
                
                display_columns = [col for col in default_columns if col in table_data.columns]
                
                available_columns = [col for col in display_columns if col in table_data.columns]
                
                # Enhanced styling function
                def style_product_table(df):
                    # Apply styling
                    format_spec = {}
                    # Build format dict based on available columns
                    if 'total_remaining_demand' in available_columns:
                        format_spec['total_remaining_demand'] = '{:,.0f}'
                    if 'total_inventory' in available_columns:
                        format_spec['total_inventory'] = '{:,.0f}'
                    if 'preferred_warehouse_inventory' in available_columns:
                        format_spec['preferred_warehouse_inventory'] = '{:,.0f}'
                    if 'gap_quantity' in available_columns:
                        format_spec['gap_quantity'] = '{:,.0f}'
                    if 'gap_percentage' in available_columns:
                        format_spec['gap_percentage'] = '{:.1f}%'
                    if 'fulfill_rate' in available_columns:
                        format_spec['fulfill_rate'] = '{:.1f}%'
                    if 'active_deliveries' in available_columns:
                        format_spec['active_deliveries'] = '{:,}'
                    if 'unique_orders' in available_columns:
                        format_spec['unique_orders'] = '{:,}'
                    if 'warehouse_count' in available_columns:
                        format_spec['warehouse_count'] = '{:,}'
                    if 'avg_demand_percentage' in available_columns:
                        format_spec['avg_demand_percentage'] = '{:.1f}%'
                    
                    styled = df[available_columns].style.format(format_spec, na_rep='-')
                    
                    # Apply gradient to fulfill_rate - FIXED: Red at 0%
                    if 'fulfill_rate' in available_columns:
                        styled = styled.background_gradient(
                            subset=['fulfill_rate'], 
                            cmap='RdYlGn',
                            vmin=0,
                            vmax=100
                        )
                    
                    # Conditional formatting for fulfillment status
                    def color_fulfillment_status(val):
                        if val == 'Out of Stock':
                            return 'background-color: #ffcccb; color: #721c24; font-weight: bold'
                        elif val == 'Can Fulfill Partial':
                            return 'background-color: #fff3cd; color: #856404'
                        elif val in ['Can Fulfill All', 'Fulfilled', 'Ready to Ship']:
                            return 'background-color: #d4edda; color: #155724'
                        return ''
                    
                    if 'fulfillment_status' in available_columns:
                        styled = styled.applymap(
                            color_fulfillment_status,
                            subset=['fulfillment_status']
                        )
                    
                    # Highlight critical products
                    def highlight_critical(s):
                        if 'gap_quantity' in s.index and 'fulfill_rate' in s.index:
                            if s['gap_quantity'] > 0 and s['fulfill_rate'] < 50:
                                return ['border-left: 4px solid #dc3545; font-weight: bold' if col == 'pt_code' 
                                    else '' for col in s.index]
                        return [''] * len(s)
                    
                    styled = styled.apply(highlight_critical, axis=1)
                    
                    return styled
                
                # Display table with styling
                st.dataframe(
                    style_product_table(table_data),
                    use_container_width=True,
                    height=400
                )
                
                # Summary below table
                st.caption(f"Showing {len(table_data)} of {len(product_analysis)} products")
                
                # Export functionality
                csv = table_data[available_columns].to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export Filtered Product Data",
                    data=csv,
                    file_name=f"product_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime='text/csv'
                )
            else:
                st.info("No products match the selected criteria")
            
            # Top customers analysis for critical products
            if show_critical_only and not table_data.empty and 'top_customers' in table_data.columns:
                with st.expander("🎯 Top Customers for Critical Products", expanded=False):
                    # Build columns list dynamically
                    customer_columns = ['pt_code', 'product_pn']
                    if 'gap_quantity' in table_data.columns:
                        customer_columns.append('gap_quantity')
                    if 'fulfill_rate' in table_data.columns:
                        customer_columns.append('fulfill_rate')
                    customer_columns.append('top_customers')
                    
                    # Filter for available columns
                    available_customer_cols = [col for col in customer_columns if col in table_data.columns]
                    customer_data = table_data[available_customer_cols].head(10)
                    
                    # Build format dict
                    format_dict = {}
                    if 'gap_quantity' in customer_data.columns:
                        format_dict['gap_quantity'] = '{:,.0f}'
                    if 'fulfill_rate' in customer_data.columns:
                        format_dict['fulfill_rate'] = '{:.1f}%'
                    
                    st.dataframe(
                        customer_data.style.format(format_dict),
                        use_container_width=True
                    )
        else:
            st.info("No product data available for the selected filters")

else:
    st.info("No delivery data found for the selected filters")

# Show overdue deliveries alert (NEW)
if df is not None and not df.empty:
    overdue_df = df[df['delivery_timeline_status'] == 'Overdue']
    if not overdue_df.empty:
        with st.expander("⚠️ Overdue Deliveries Alert", expanded=True):
            st.warning(f"There are {overdue_df['delivery_id'].nunique()} overdue deliveries requiring attention!")
            
            # Show summary of overdue deliveries
            overdue_summary = overdue_df.groupby(['customer', 'recipient_company']).agg({
                'delivery_id': 'nunique',
                'days_overdue': 'max',
                'remaining_quantity_to_deliver': 'sum'
            }).reset_index()
            overdue_summary.columns = ['Customer', 'Ship To', 'Deliveries', 'Max Days Overdue', 'Total Qty']
            
            st.dataframe(
                overdue_summary.style.format({
                    'Total Qty': '{:,.0f}',
                    'Max Days Overdue': '{:.0f} days',
                    'Deliveries': '{:,.0f}'
                }, na_rep='-').background_gradient(
                    subset=['Max Days Overdue'], 
                    cmap='Reds'
                ).bar(
                    subset=['Total Qty'],
                    color='#ff6b6b'
                ),
                use_container_width=True
            )

# Add footer
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")