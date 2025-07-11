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
st.markdown("---")

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
        index=0
    )

with col5:
    # Foreign customer filter
    foreign_filter = st.selectbox(
        "Customer Type",
        options=["All Customers", "Domestic Only", "Foreign Only"],
        index=0
    )

with col6:
    # Help text
    with st.expander("ℹ️ Filter Help"):
        st.markdown("""
        **EPE Company**: Filters by EPE company type
        - EPE Companies: Shows only EPE type companies
        - Non-EPE: Shows all other companies
        
        **Customer Type**: Filters by customer location
        - Domestic: Same country as seller
        - Foreign: Different country from seller
        """)

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
    'foreign_filter': foreign_filter
}

# Load data
with st.spinner("Loading delivery data..."):
    df = data_loader.load_delivery_data(filters)

if df is not None and not df.empty:
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
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
    
    st.markdown("---")
    
    # Pivot view
    st.subheader(f"📅 Delivery Schedule - {view_period.capitalize()} View")
    
    # Get pivoted data
    pivot_df = data_loader.pivot_delivery_data(df, view_period)
    
    if not pivot_df.empty:
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["📊 Pivot Table", "📈 Charts", "📋 Detailed List"])
        
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
                # Timeline chart
                timeline_df = df.groupby(pd.to_datetime(df['etd']).dt.date).agg({
                    'delivery_id': 'nunique',
                    'standard_quantity': 'sum'
                }).reset_index()
                timeline_df.columns = ['Date', 'Deliveries', 'Quantity']
                
                fig1 = go.Figure()
                fig1.add_trace(go.Bar(
                    x=timeline_df['Date'],
                    y=timeline_df['Deliveries'],
                    name='Deliveries',
                    yaxis='y',
                    marker_color='lightblue'
                ))
                fig1.add_trace(go.Scatter(
                    x=timeline_df['Date'],
                    y=timeline_df['Quantity'],
                    name='Quantity',
                    yaxis='y2',
                    marker_color='darkblue'
                ))
                fig1.update_layout(
                    title='Delivery Timeline',
                    yaxis=dict(title='Number of Deliveries', side='left'),
                    yaxis2=dict(title='Total Quantity', side='right', overlaying='y'),
                    hovermode='x unified'
                )
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # Status distribution
                status_df = df.groupby('fulfillment_status')['delivery_id'].nunique().reset_index()
                status_df.columns = ['Status', 'Count']
                
                fig2 = px.pie(
                    status_df, 
                    values='Count', 
                    names='Status',
                    title='Fulfillment Status Distribution',
                    color_discrete_map={
                        'Fulfilled': '#2ecc71',
                        'Partial Fulfilled': '#f39c12',
                        'Out of Stock': '#e74c3c',
                        'No Remaining': '#95a5a6'
                    }
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            # Geographic distribution
            if 'recipient_country_name' in df.columns:
                geo_df = df.groupby('recipient_country_name')['delivery_id'].nunique().reset_index()
                geo_df.columns = ['Country', 'Deliveries']
                geo_df = geo_df.sort_values('Deliveries', ascending=False).head(15)
                
                fig3 = px.bar(
                    geo_df,
                    x='Deliveries',
                    y='Country',
                    orientation='h',
                    title='Top 15 Delivery Destinations',
                    color='Deliveries',
                    color_continuous_scale='Blues'
                )
                st.plotly_chart(fig3, use_container_width=True)
        
        with tab3:
            # Detailed list
            st.subheader("📋 Detailed Delivery List")
            
            # Select columns to display
            display_columns = st.multiselect(
                "Select columns to display",
                options=df.columns.tolist(),
                default=['dn_number', 'customer', 'recipient_company', 'etd', 
                        'product_pn', 'standard_quantity', 'remaining_quantity_to_deliver',
                        'fulfillment_status', 'shipment_status', 'is_epe_company']
            )
            
            if display_columns:
                display_df = df[display_columns].copy()
                
                # Format date columns
                date_columns = ['etd', 'created_date', 'delivered_date', 'dispatched_date']
                for col in date_columns:
                    if col in display_df.columns:
                        display_df[col] = pd.to_datetime(display_df[col]).dt.strftime('%Y-%m-%d')
                
                # Apply conditional formatting
                def highlight_fulfillment(val):
                    if val == 'Out of Stock':
                        return 'background-color: #ffcccb'
                    elif val == 'Partial Fulfilled':
                        return 'background-color: #ffe4b5'
                    elif val == 'Fulfilled':
                        return 'background-color: #90ee90'
                    return ''
                
                def highlight_epe(val):
                    if val == 'Yes':
                        return 'font-weight: bold; color: #1976d2'
                    return ''
                
                styled_df = display_df.style
                
                if 'fulfillment_status' in display_df.columns:
                    styled_df = styled_df.applymap(
                        highlight_fulfillment, 
                        subset=['fulfillment_status']
                    )
                
                if 'is_epe_company' in display_df.columns:
                    styled_df = styled_df.applymap(
                        highlight_epe,
                        subset=['is_epe_company']
                    )
                
                st.dataframe(styled_df, use_container_width=True)
else:
    st.info("No delivery data found for the selected filters")

# Add footer
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")