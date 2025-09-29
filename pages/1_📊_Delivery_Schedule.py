# pages/1_📊_Delivery_Schedule.py

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.auth import AuthManager
from utils.data_loader import DeliveryDataLoader
import plotly.express as px
import plotly.graph_objects as go

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Delivery Schedule",
    page_icon="📊",
    layout="wide"
)

# ============================================================================
# AUTHENTICATION CHECK
# ============================================================================

auth_manager = AuthManager()
if not auth_manager.check_session():
    st.warning("⚠️ Please login to access this page")
    st.stop()

# Initialize data loader
data_loader = DeliveryDataLoader()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_filter_section(filter_options):
    """Create the filter section with all filter controls"""
    
    with st.expander("🔍 Filters", expanded=True):
        # First row of filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Date range filter
            date_range = create_date_filter(filter_options)
            
            # Legal Entity filter
            selected_legal_entities, exclude_legal_entities = create_multiselect_with_exclude(
                "Legal Entity",
                filter_options.get('legal_entities', []),
                "legal_entities",
                "Filter by selling company/legal entity"
            )
        
        with col2:
            # Creator filter
            selected_creators, exclude_creators = create_multiselect_with_exclude(
                "Creator/Sales",
                filter_options.get('creators', []),
                "creators"
            )
            
            # Customer filter
            selected_customers, exclude_customers = create_multiselect_with_exclude(
                "Customer (Sold-To)",
                filter_options.get('customers', []),
                "customers"
            )
        
        with col3:
            # Ship-to filter
            selected_ship_to, exclude_ship_to = create_multiselect_with_exclude(
                "Ship-To Company",
                filter_options.get('ship_to_companies', []),
                "ship_to"
            )
            
            # Location filters
            selected_states, selected_countries, exclude_countries = create_location_filters(filter_options)
        
        # Second row of filters
        col4, col5, col6 = st.columns(3)
        
        with col4:
            epe_filter, foreign_filter = create_company_type_filters(filter_options)
        
        with col5:
            # Product filter
            selected_products, exclude_products = create_multiselect_with_exclude(
                "Product",
                filter_options.get('products', []),
                "products",
                "Filter by product PT Code or Product PN"
            )
            
            # Brand filter
            selected_brands, exclude_brands = create_multiselect_with_exclude(
                "Brand",
                filter_options.get('brands', []),
                "brands",
                "Filter by product brand"
            )
        
        with col6:
            # Timeline status filter
            selected_timeline, exclude_timeline = create_timeline_filter(filter_options)
    
    # Compile filters
    filters = {
        'date_from': date_range[0] if len(date_range) >= 1 else None,
        'date_to': date_range[1] if len(date_range) >= 2 else date_range[0],
        'creators': selected_creators if selected_creators else None,
        'exclude_creators': exclude_creators,
        'customers': selected_customers if selected_customers else None,
        'exclude_customers': exclude_customers,
        'products': selected_products if selected_products else None,
        'exclude_products': exclude_products,
        'brands': selected_brands if selected_brands else None,
        'exclude_brands': exclude_brands,
        'ship_to_companies': selected_ship_to if selected_ship_to else None,
        'exclude_ship_to_companies': exclude_ship_to,
        'states': selected_states if selected_states else None,
        'countries': selected_countries if selected_countries else None,
        'exclude_countries': exclude_countries,
        'epe_filter': epe_filter,
        'foreign_filter': foreign_filter,
        'timeline_status': selected_timeline if selected_timeline else None,
        'exclude_timeline_status': exclude_timeline,
        'legal_entities': selected_legal_entities if selected_legal_entities else None,
        'exclude_legal_entities': exclude_legal_entities,
        'statuses': None,
        'exclude_statuses': False
    }
    
    return filters

def create_date_filter(filter_options):
    """Create date range filter"""
    date_range_options = filter_options.get('date_range', {})
    min_date = date_range_options.get('min_date', datetime.now().date() - timedelta(days=365))
    max_date = date_range_options.get('max_date', datetime.now().date() + timedelta(days=365))
    
    # Convert to date if datetime
    if hasattr(min_date, 'date'):
        min_date = min_date.date()
    if hasattr(max_date, 'date'):
        max_date = max_date.date()
    
    # Set default date range
    default_start = min_date if min_date else datetime.now().date() - timedelta(days=365)
    default_end = max_date if max_date else datetime.now().date() + timedelta(days=365)
    
    return st.date_input(
        "Date Range",
        value=(default_start, default_end),
        min_value=min_date,
        max_value=max_date,
        help=f"Available data from {min_date} to {max_date}"
    )

def create_multiselect_with_exclude(label, options, key_prefix, help_text=None):
    """Create a multiselect with exclude checkbox"""
    st.markdown(f"**{label}**")
    col1, col2 = st.columns([5, 1])
    
    with col1:
        selected = st.multiselect(
            f"Select {label}",
            options=options,
            default=None,
            placeholder=f"All {label.lower()}",
            help=help_text,
            label_visibility="collapsed"
        )
    
    with col2:
        exclude = st.checkbox(
            "Excl",
            key=f"exclude_{key_prefix}",
            help=f"Exclude selected {label.lower()} instead of including them"
        )
    
    return selected, exclude

def create_location_filters(filter_options):
    """Create location-based filters"""
    st.markdown("**Location Filters**")
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        selected_states = st.multiselect(
            "State/Province",
            options=filter_options.get('states', []),
            default=None,
            placeholder="All states"
        )
    
    with col2:
        selected_countries = st.multiselect(
            "Country",
            options=filter_options.get('countries', []),
            default=None,
            placeholder="All countries"
        )
    
    with col3:
        exclude_countries = st.checkbox(
            "Excl",
            key="exclude_countries",
            help="Exclude selected countries"
        )
    
    return selected_states, selected_countries, exclude_countries

def create_company_type_filters(filter_options):
    """Create EPE and foreign customer filters"""
    col1, col2 = st.columns(2)
    
    with col1:
        epe_options = filter_options.get('epe_options', ["All"])
        epe_filter = st.selectbox(
            "EPE Company Filter",
            options=epe_options,
            index=0,
            help="Filter by EPE company type. EPE companies are a specific customer category."
        )
    
    with col2:
        foreign_options = filter_options.get('foreign_options', ["All Customers"])
        foreign_filter = st.selectbox(
            "Customer Type",
            options=foreign_options,
            index=0,
            help="Filter by customer location. Domestic = same country as seller, Foreign = different country."
        )
    
    return epe_filter, foreign_filter

def create_timeline_filter(filter_options):
    """Create timeline status filter"""
    st.markdown("**Delivery Timeline Status**")
    col1, col2 = st.columns([5, 1])
    
    timeline_options = filter_options.get('timeline_statuses', [])
    default_timeline = ["Completed"] if "Completed" in timeline_options else None
    
    with col1:
        selected_timeline = st.multiselect(
            "Select Timeline Status",
            options=timeline_options,
            default=default_timeline,
            placeholder="All statuses",
            help="Filter by delivery timeline: Overdue, Due Today, On Schedule, Completed",
            label_visibility="collapsed"
        )
    
    with col2:
        exclude_timeline = st.checkbox(
            "Excl",
            key="exclude_timeline",
            value=True,
            help="Exclude selected timeline statuses instead of including them"
        )
    
    return selected_timeline, exclude_timeline

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

# ============================================================================
# PIVOT TABLE FUNCTIONS
# ============================================================================

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
        pivot_table = create_customer_product_pivot(df, view_period)
        filename_prefix = "delivery_by_customer_product"
    elif group_by_customer:
        pivot_table = create_customer_pivot(pivot_df)
        filename_prefix = "delivery_by_customer"
    elif group_by_product:
        pivot_table = create_product_pivot(df, view_period)
        filename_prefix = "delivery_by_product"
    else:
        display_default_pivot(pivot_df)
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

def create_customer_product_pivot(df, view_period):
    """Create pivot table grouped by customer and product"""
    # Create pivot with customer and pt_code
    pivot_table = df.pivot_table(
        index=['customer', 'pt_code'],
        columns=pd.Grouper(key='etd', freq='W' if view_period == 'weekly' else 'D' if view_period == 'daily' else 'M'),
        values='standard_quantity',
        aggfunc='sum',
        fill_value=0
    )
    
    # Format column headers
    pivot_table.columns = pivot_table.columns.strftime(
        '%Y-%m-%d' if view_period == 'daily' else 
        'Week of %Y-%m-%d' if view_period == 'weekly' else 
        '%B %Y'
    )
    
    # Reset index and merge product details
    pivot_table = pivot_table.reset_index()
    
    # Get product details
    product_cols = ['pt_code', 'product_pn', 'brand', 'package_size']
    available_product_cols = [col for col in product_cols if col in df.columns]
    product_info = df[available_product_cols].drop_duplicates(subset=['pt_code'])
    
    # Merge product details
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
    
    # Rename columns
    column_rename = {
        'customer': 'Customer',
        'pt_code': 'PT Code',
        'brand': 'Brand',
        'product_pn': 'Product Name',
        'package_size': 'Package Size'
    }
    final_table = final_table.rename(columns=column_rename)
    
    # Sort by customer and total quantity
    total_col = final_table[period_cols].sum(axis=1)
    final_table['_sort'] = total_col
    final_table = final_table.sort_values(['Customer', '_sort'], ascending=[True, False])
    final_table = final_table.drop('_sort', axis=1)
    
    # Display with styling
    display_styled_pivot(final_table, period_cols, freeze_up_to='Package Size')
    
    return final_table

def create_customer_pivot(pivot_df):
    """Create pivot table grouped by customer only"""
    pivot_table = pivot_df.pivot_table(
        index='Customer',
        columns='Period',
        values='Total Quantity',
        aggfunc='sum',
        fill_value=0
    )
    
    st.dataframe(
        pivot_table.style.format("{:,.0f}").background_gradient(cmap='Blues'),
        use_container_width=True
    )
    
    return pivot_table

def create_product_pivot(df, view_period):
    """Create pivot table grouped by product"""
    # Get product info
    product_cols = ['pt_code', 'product_pn', 'brand', 'package_size']
    available_product_cols = [col for col in product_cols if col in df.columns]
    product_info = df[available_product_cols].drop_duplicates(subset=['pt_code'])
    product_info = product_info.set_index('pt_code')
    
    # Create pivot table
    pivot_table = df.pivot_table(
        index='pt_code',
        columns=pd.Grouper(key='etd', freq='W' if view_period == 'weekly' else 'D' if view_period == 'daily' else 'M'),
        values='standard_quantity',
        aggfunc='sum',
        fill_value=0
    )
    
    # Format column headers
    period_columns = pivot_table.columns.strftime(
        '%Y-%m-%d' if view_period == 'daily' else 
        'Week of %Y-%m-%d' if view_period == 'weekly' else 
        '%B %Y'
    )
    pivot_table.columns = period_columns
    
    # Calculate total for sorting
    total_series = pivot_table.sum(axis=1)
    
    # Merge product info with pivot table
    final_table = pd.concat([product_info, pivot_table], axis=1)
    
    # Sort by total quantity
    final_table = final_table.loc[total_series.sort_values(ascending=False).index]
    
    # Reset index
    final_table = final_table.reset_index()
    
    # Reorder and rename columns
    column_order = []
    column_rename = {}
    
    if 'pt_code' in final_table.columns:
        column_order.append('pt_code')
        column_rename['pt_code'] = 'PT Code'
    if 'brand' in final_table.columns:
        column_order.append('brand')
        column_rename['brand'] = 'Brand'
    if 'product_pn' in final_table.columns:
        column_order.append('product_pn')
        column_rename['product_pn'] = 'Product Name'
    if 'package_size' in final_table.columns:
        column_order.append('package_size')
        column_rename['package_size'] = 'Package Size'
    
    column_order.extend(period_columns)
    final_table = final_table[column_order]
    final_table = final_table.rename(columns=column_rename)
    
    # Display with styling
    period_col_names = [col for col in final_table.columns if col not in column_rename.values()]
    display_styled_pivot(final_table, period_col_names, freeze_up_to='Package Size')
    
    return final_table

def display_styled_pivot(table, period_columns, freeze_up_to='Package Size'):
    """Display a styled pivot table with frozen columns"""
    # Create format dict for period columns
    format_dict = {col: '{:,.0f}' for col in period_columns}
    
    # Apply base styling
    styled_table = table.style.format(format_dict, na_rep='-')
    
    # Apply gradient to period columns
    if period_columns:
        styled_table = styled_table.background_gradient(
            subset=period_columns, 
            cmap='Blues'
        )
    
    # Determine columns to freeze
    freeze_columns = []
    for col in table.columns:
        freeze_columns.append(col)
        if col == freeze_up_to:
            break
    
    # Apply sticky columns
    num_freeze = len(freeze_columns)
    if num_freeze > 0:
        styled_table = styled_table.set_sticky(
            axis="columns",
            levels=list(range(num_freeze))
        )
    
    # Display with column configuration for better control
    column_config = {}
    for i, col in enumerate(table.columns):
        if col in ['Customer', 'PT Code', 'Brand', 'Product Name', 'Package Size']:
            # Text columns with specific widths
            if col == 'Customer':
                width = "large"
            elif col in ['PT Code', 'Brand', 'Package Size']:
                width = "small"
            else:
                width = "medium"
            
            column_config[col] = st.column_config.TextColumn(
                col,
                width=width
            )
        elif col in period_columns:
            # Number columns for periods
            column_config[col] = st.column_config.NumberColumn(
                col,
                format="%.0f",
                width="small"
            )
    
    # Display the dataframe
    st.dataframe(
        styled_table,
        use_container_width=True,
        height=600,
        column_config=column_config
    )

def display_default_pivot(pivot_df):
    """Display default pivot view without grouping"""
    format_dict = {
        'Total Quantity': '{:,.0f}',
        'Remaining to Deliver': '{:,.0f}',
        'Gap (Legacy)': '{:,.0f}',
        'Product Gap': '{:,.0f}',
        'Total Product Demand': '{:,.0f}',
        'Deliveries': '{:,.0f}'
    }
    
    existing_formats = {col: fmt for col, fmt in format_dict.items() if col in pivot_df.columns}
    
    st.dataframe(
        pivot_df.style.format(existing_formats, na_rep='-'),
        use_container_width=True
    )

# ============================================================================
# DETAILED LIST FUNCTIONS
# ============================================================================

def display_detailed_list(df):
    """Display detailed delivery list"""
    st.subheader("📋 Detailed Delivery List")
    
    # Column selection
    default_columns = ['dn_number', 'customer', 'recipient_company', 'etd', 
                       'pt_code', 'product_pn', 'brand', 'standard_quantity', 
                       'remaining_quantity_to_deliver', 'product_fulfill_rate_percent', 
                       'delivery_timeline_status', 'days_overdue', 'shipment_status_vn', 
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
    
    # Apply styling
    styled_df = style_detailed_list(display_df)
    
    st.dataframe(styled_df, use_container_width=True)

def style_detailed_list(df):
    """Apply styling to detailed list dataframe"""
    # Define column types
    quantity_columns = ['standard_quantity', 'selling_quantity', 'remaining_quantity_to_deliver',
                       'stock_out_quantity', 'stock_out_request_quantity', 
                       'total_instock_at_preferred_warehouse', 'total_instock_all_warehouses',
                       'gap_quantity', 'product_gap_quantity', 'product_total_remaining_demand']
    
    rate_columns = ['product_fulfill_rate_percent', 'fulfill_rate_percent', 'delivery_demand_percentage']
    
    currency_columns = ['shipping_cost', 'export_tax']
    
    # Create format dict
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
    
    # Apply base formatting
    styled = df.style.format(format_dict, na_rep='-')
    
    # Apply conditional formatting
    if 'delivery_timeline_status' in df.columns:
        styled = styled.applymap(
            highlight_timeline_status,
            subset=['delivery_timeline_status']
        )
    
    if 'product_fulfillment_status' in df.columns:
        styled = styled.applymap(
            highlight_fulfillment_status,
            subset=['product_fulfillment_status']
        )
    
    if 'is_epe_company' in df.columns:
        styled = styled.applymap(
            highlight_epe_company,
            subset=['is_epe_company']
        )
    
    # Color code fulfillment rates
    for col in rate_columns:
        if col in df.columns:
            styled = styled.applymap(
                color_fulfill_rate,
                subset=[col]
            )
    
    return styled

def highlight_timeline_status(val):
    """Color code timeline status"""
    if val == 'Overdue':
        return 'background-color: #ffcccb'
    elif val == 'Due Today':
        return 'background-color: #ffe4b5'
    elif val == 'On Schedule':
        return 'background-color: #90ee90'
    elif val == 'Completed':
        return 'background-color: #e0e0e0'
    return ''

def highlight_fulfillment_status(val):
    """Color code fulfillment status"""
    if val == 'Out of Stock':
        return 'background-color: #ffcccb'
    elif val == 'Can Fulfill Partial':
        return 'background-color: #ffe4b5'
    elif val == 'Can Fulfill All':
        return 'background-color: #90ee90'
    return ''

def highlight_epe_company(val):
    """Highlight EPE companies"""
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

# ============================================================================
# PRODUCT ANALYSIS FUNCTIONS
# ============================================================================

def display_product_analysis(df, data_loader):
    """Display product demand analysis"""
    st.subheader("🔍 Product Demand Analysis")
    
    # Get product analysis
    product_analysis = data_loader.get_product_demand_from_dataframe(df)
    
    if product_analysis.empty:
        st.info("No product data available for the selected filters")
        return
    
    # Check data quality
    check_data_quality(product_analysis)
    
    # Display metrics
    display_product_metrics(product_analysis)
    
    # Display shortage analysis
    display_shortage_analysis(product_analysis)
    
    # Display product detail table
    display_product_detail_table(product_analysis)

def check_data_quality(product_analysis):
    """Check and report data quality issues"""
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
            st.info("This may be due to missing columns in the source data.")

def display_product_metrics(product_analysis):
    """Display product analysis metrics"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        multi_delivery_products = len(product_analysis[product_analysis['active_deliveries'] > 1])
        st.metric(
            "Multi-Delivery Products",
            f"{multi_delivery_products:,}",
            help="Products being delivered to multiple locations/orders"
        )
    
    with col2:
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
        if 'gap_percentage' in product_analysis.columns:
            avg_gap_percentage = product_analysis[product_analysis['gap_quantity'] > 0]['gap_percentage'].mean()
            st.metric(
                "Avg Gap %",
                f"{avg_gap_percentage:.1f}%" if not pd.isna(avg_gap_percentage) else "0%",
                help="Average shortage percentage for products with gaps"
            )
        else:
            st.metric("Avg Gap %", "N/A")

def display_shortage_analysis(product_analysis):
    """Display product shortage analysis chart"""
    st.markdown("#### Product Shortage Analysis")
    
    # Help text
    with st.expander("ℹ️ Understanding Sort Options", expanded=False):
        st.markdown("""
        - **Gap Quantity (Units)**: Sort by actual number of units short
        - **Gap Percentage (%)**: Sort by percentage of demand that cannot be fulfilled
        - **Total Demand (Units)**: Sort by total demand volume
        """)
    
    # Configuration
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        num_products = st.number_input(
            "Products to display",
            min_value=5,
            max_value=50,
            value=15,
            step=1,
            help="Number of products to show in the chart"
        )
    
    with col2:
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
    
    # Create shortage chart
    create_shortage_chart(product_analysis, num_products, sort_column)

def create_shortage_chart(product_analysis, num_products, sort_column):
    """Create product shortage chart"""
    # Filter and sort data
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
    
    # Sort and get top products
    if sort_column in shortage_products.columns:
        shortage_products = shortage_products.sort_values(sort_column, ascending=False)
    
    top_shortage = shortage_products.head(num_products)
    
    # Create chart
    if 'gap_quantity' not in top_shortage.columns or top_shortage['gap_quantity'].isna().all():
        create_demand_chart(top_shortage)
    else:
        create_gap_chart(top_shortage, sort_column)
    
    # Summary statistics
    display_shortage_summary(top_shortage)

def create_gap_chart(chart_data, sort_column):
    """Create chart for products with gap data"""
    # Create product label
    if 'brand' in chart_data.columns:
        chart_data['product_label'] = (
            chart_data['pt_code'] + '<br>' + 
            chart_data['product_pn'].str[:25] + '<br><i>' + 
            chart_data['brand'].fillna('No Brand') + '</i>'
        )
    else:
        chart_data['product_label'] = (
            chart_data['pt_code'] + '<br>' + 
            chart_data['product_pn'].str[:30]
        )
    
    # Determine X-axis metric
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
    
    # Build hover template
    hover_template = build_hover_template(chart_data)
    customdata_cols = get_customdata_columns(chart_data)
    
    # Create figure
    fig = go.Figure()
    
    # Add bars with color coding
    if 'fulfill_rate' in chart_data.columns and chart_data['fulfill_rate'].notna().any():
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
        title=f'Top {len(chart_data)} Products by {sort_display}',
        xaxis_title=x_title,
        yaxis_title='',
        height=max(400, len(chart_data) * 50),
        showlegend=False,
        margin=dict(l=250),
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
    
    # Add value labels
    fig.update_traces(
        texttemplate=text_template,
        textposition='outside'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_demand_chart(chart_data):
    """Create fallback chart based on demand only"""
    st.info("Gap quantity data not available. Showing products by total demand.")
    
    # Create product label
    if 'brand' in chart_data.columns:
        chart_data['product_label'] = (
            chart_data['pt_code'] + '<br>' + 
            chart_data['product_pn'].str[:25] + '<br><i>' + 
            chart_data['brand'].fillna('No Brand') + '</i>'
        )
    else:
        chart_data['product_label'] = (
            chart_data['pt_code'] + '<br>' + 
            chart_data['product_pn'].str[:30]
        )
    
    # Build hover template
    hover_parts = [
        '<b>%{customdata[0]}</b>',
        'Product: %{customdata[1]}',
        'Total Demand: %{x:,.0f}'
    ]
    customdata_cols = ['pt_code', 'product_pn']
    
    if 'brand' in chart_data.columns:
        hover_parts.insert(2, 'Brand: %{customdata[2]}')
        customdata_cols.append('brand')
    
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
        title=f'Top {len(chart_data)} Products by Total Demand',
        xaxis_title='Total Remaining Demand',
        yaxis_title='',
        height=max(400, len(chart_data) * 50),
        showlegend=False,
        margin=dict(l=250),
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

def build_hover_template(chart_data):
    """Build dynamic hover template based on available columns"""
    hover_parts = [
        '<b>%{customdata[0]}</b>',
        'Product: %{customdata[1]}'
    ]
    
    idx = 2
    if 'brand' in chart_data.columns:
        hover_parts.append(f'Brand: %{{customdata[{idx}]}}')
        idx += 1
    
    if 'gap_quantity' in chart_data.columns:
        hover_parts.append(f'Gap Quantity: %{{customdata[{idx}]:,.0f}}')
        idx += 1
    
    hover_parts.append(f'Total Demand: %{{customdata[{idx}]:,.0f}}')
    idx += 1
    
    if 'fulfill_rate' in chart_data.columns:
        hover_parts.append(f'Fulfillment Rate: %{{customdata[{idx}]:.1f}}%')
        idx += 1
    
    if 'gap_percentage' in chart_data.columns:
        hover_parts.append(f'Gap %: %{{customdata[{idx}]:.1f}}%')
        idx += 1
    
    return '<br>'.join(hover_parts)

def get_customdata_columns(chart_data):
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

def display_shortage_summary(top_shortage):
    """Display summary statistics for shortage analysis"""
    with st.expander("📊 Summary Statistics", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if 'gap_quantity' in top_shortage.columns:
                total_gap = top_shortage['gap_quantity'].sum()
                st.metric("Total Gap (Top Products)", f"{total_gap:,.0f}")
            else:
                st.metric("Total Gap", "N/A")
        
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

def display_product_detail_table(product_analysis):
    """Display detailed product table with filters"""
    st.markdown("#### Product Detail Table")
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    with col1:
        show_critical_only = st.checkbox("Show critical products only", value=False)
    with col2:
        show_gaps_only = st.checkbox("Show products with gaps only", value=False)
    with col3:
        min_deliveries = st.number_input("Min active deliveries", min_value=0, value=0)
    
    # Apply filters
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
    
    # Display table
    display_columns = get_product_table_columns(table_data)
    styled_table = style_product_table(table_data[display_columns])
    
    st.dataframe(
        styled_table,
        use_container_width=True,
        height=400
    )
    
    st.caption(f"Showing {len(table_data)} of {len(product_analysis)} products")
    
    # Export functionality
    csv = table_data[display_columns].to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Filtered Product Data",
        data=csv,
        file_name=f"product_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime='text/csv'
    )

def get_product_table_columns(table_data):
    """Get columns for product detail table"""
    default_columns = [
        'pt_code', 'product_pn', 'brand', 'active_deliveries',
        'total_remaining_demand', 'total_inventory',
        'gap_quantity', 'gap_percentage', 'fulfill_rate',
        'fulfillment_status', 'warehouse_count'
    ]
    
    return [col for col in default_columns if col in table_data.columns]

def style_product_table(df):
    """Apply styling to product table"""
    # Build format dict
    format_spec = {}
    
    numeric_formats = {
        'total_remaining_demand': '{:,.0f}',
        'total_inventory': '{:,.0f}',
        'gap_quantity': '{:,.0f}',
        'gap_percentage': '{:.1f}%',
        'fulfill_rate': '{:.1f}%',
        'active_deliveries': '{:,}',
        'warehouse_count': '{:,}'
    }
    
    for col, fmt in numeric_formats.items():
        if col in df.columns:
            format_spec[col] = fmt
    
    styled = df.style.format(format_spec, na_rep='-')
    
    # Apply gradient to fulfill_rate
    if 'fulfill_rate' in df.columns:
        styled = styled.background_gradient(
            subset=['fulfill_rate'],
            cmap='RdYlGn',
            vmin=0,
            vmax=100
        )
    
    # Apply conditional formatting
    if 'fulfillment_status' in df.columns:
        styled = styled.applymap(
            color_fulfillment_status,
            subset=['fulfillment_status']
        )
    
    return styled

def color_fulfillment_status(val):
    """Color code fulfillment status"""
    if val == 'Out of Stock':
        return 'background-color: #ffcccb; color: #721c24; font-weight: bold'
    elif val == 'Can Fulfill Partial':
        return 'background-color: #fff3cd; color: #856404'
    elif val in ['Can Fulfill All', 'Fulfilled', 'Ready to Ship']:
        return 'background-color: #d4edda; color: #155724'
    return ''

# ============================================================================
# ALERT FUNCTIONS
# ============================================================================

def display_overdue_alert(df):
    """Display overdue deliveries alert"""
    overdue_df = df[df['delivery_timeline_status'] == 'Overdue']
    
    if overdue_df.empty:
        return
    
    with st.expander("⚠️ Overdue Deliveries Alert", expanded=True):
        st.warning(f"There are {overdue_df['delivery_id'].nunique()} overdue deliveries requiring attention!")
        
        # Show summary
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

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application function"""
    st.title("📊 Delivery Schedule")
    
    # Get filter options
    filter_options = data_loader.get_filter_options()
    
    # Create filters
    filters = create_filter_section(filter_options)
    
    # Apply filters button
    if st.button("🔄 Apply Filters", type="primary", use_container_width=True):
        st.session_state.filters_applied = True
    
    # Load data
    with st.spinner("Loading delivery data..."):
        df = data_loader.load_delivery_data(filters)
    
    if df is None or df.empty:
        st.info("No delivery data found for the selected filters")
        return
    
    # Store selected PT codes if products are filtered
    if filters.get('products'):
        st.session_state.selected_pt_codes = [p.split(' - ')[0] for p in filters['products']]
    else:
        st.session_state.selected_pt_codes = None
    
    # Display metrics
    display_metrics(df)
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📊 Pivot Table", "📋 Detailed List", "🔍 Product Analysis"])
    
    with tab1:
        display_pivot_table(df, data_loader)
    
    with tab2:
        display_detailed_list(df)
    
    with tab3:
        display_product_analysis(df, data_loader)
    
    # Display alerts
    display_overdue_alert(df)
    
    # Footer
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ============================================================================
# RUN APPLICATION
# ============================================================================

if __name__ == "__main__":
    main()