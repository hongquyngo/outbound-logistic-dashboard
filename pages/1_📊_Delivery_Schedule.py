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
# st.markdown("---")

# Filter Section
with st.expander("🔍 Filters", expanded=True):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Date range
        date_range = st.date_input(
            "Date Range",
            value=(datetime.now().date(), datetime.now().date() + timedelta(days=30)),
            min_value=datetime.now().date() - timedelta(days=365),
            max_value=datetime.now().date() + timedelta(days=365)
        )
        
        # View period
        view_period = st.radio(
            "View By",
            options=['daily', 'weekly', 'monthly'],
            index=1,
            horizontal=True
        )
    
    # Get filter options
    filter_options = data_loader.get_filter_options()
    
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
        # EPE Company filter
        epe_filter = st.selectbox(
            "EPE Company Filter",
            options=["All", "EPE Companies Only", "Non-EPE Companies Only"],
            index=0,
            help="Filter by EPE company type. EPE companies are a specific customer category."
        )

    with col5:
        # Foreign customer filter
        foreign_filter = st.selectbox(
            "Customer Type",
            options=["All Customers", "Domestic Only", "Foreign Only"],
            index=0,
            help="Filter by customer location. Domestic = same country as seller, Foreign = different country."
        )

    with col6:
        # Timeline status filter (NEW)
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
    'ship_to_companies': selected_ship_to if selected_ship_to else None,
    'states': selected_states if selected_states else None,
    'countries': selected_countries if selected_countries else None,
    'epe_filter': epe_filter,
    'foreign_filter': foreign_filter,
    'timeline_status': selected_timeline if selected_timeline else None
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
            unique_products = df['product_pn'].nunique()
            st.metric("Unique Products", f"{unique_products:,}")
        
        with col3:
            out_of_stock = df[df['product_fulfillment_status'] == 'Out of Stock']['product_pn'].nunique()
            st.metric("Products Out of Stock", f"{out_of_stock:,}")
        
        with col4:
            total_gap = df.groupby('product_id')['product_gap_quantity'].first().sum()
            st.metric("Total Product Gap", f"{abs(total_gap):,.0f}")
    
    # st.markdown("---")
    
    # Pivot view
    st.subheader(f"📅 Delivery Schedule - {view_period.capitalize()} View")
    
    # Get pivoted data
    pivot_df = data_loader.pivot_delivery_data(df, view_period)
    
    if not pivot_df.empty:
        # Create tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Pivot Table", "📈 Charts", "📋 Detailed List", "🔍 Product Analysis"])
        
        with tab1:
            # Pivot table view
            if st.checkbox("Group by Customer"):
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
            else:
                st.dataframe(pivot_df, use_container_width=True)
            
            # Download button
            csv = pivot_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"delivery_schedule_{datetime.now().strftime('%Y%m%d')}.csv",
                mime='text/csv'
            )
        
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
                fulfillment_df = df.groupby('product_fulfillment_status')['product_pn'].nunique().reset_index()
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
                             'product_pn', 'standard_quantity', 'remaining_quantity_to_deliver',
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
                
                styled_df = display_df.style
                
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
                
                st.dataframe(styled_df, use_container_width=True)
        
        with tab4:
            # Product Analysis tab (NEW)
            st.subheader("🔍 Product Demand Analysis")
            
            # Get product demand analysis
            product_analysis = data_loader.get_product_demand_analysis()
            
            if not product_analysis.empty:
                # Show top products with gaps
                st.markdown("#### Top Products by Demand Gap")
                gap_products = product_analysis[product_analysis['gap_quantity'] > 0].head(10)
                
                if not gap_products.empty:
                    fig4 = px.bar(
                        gap_products,
                        x='product_pn',
                        y='gap_quantity',
                        title='Top 10 Products with Supply Gap',
                        labels={'gap_quantity': 'Gap Quantity', 'product_pn': 'Product'},
                        color='fulfill_rate',
                        color_continuous_scale='RdYlGn'
                    )
                    st.plotly_chart(fig4, use_container_width=True)
                
                # Product demand details
                st.markdown("#### Product Demand Details")
                st.dataframe(
                    product_analysis[['product_pn', 'active_deliveries', 'total_remaining_demand',
                                    'total_inventory', 'gap_quantity', 'fulfill_rate', 
                                    'fulfillment_status']].style.format({
                        'total_remaining_demand': '{:,.0f}',
                        'total_inventory': '{:,.0f}',
                        'gap_quantity': '{:,.0f}',
                        'fulfill_rate': '{:.1f}%'
                    }).background_gradient(subset=['fulfill_rate'], cmap='RdYlGn'),
                    use_container_width=True
                )
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
                    'Total Qty': '{:,.0f}'
                }).background_gradient(subset=['Max Days Overdue'], cmap='Reds'),
                use_container_width=True
            )

# Add footer
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")