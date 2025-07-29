# utils/data_loader.py - Data loading module for delivery data

import pandas as pd
import streamlit as st
from sqlalchemy import text
from .db import get_db_engine
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DeliveryDataLoader:
    """Load and process delivery data from database"""
    
    def __init__(self):
        self.engine = get_db_engine()
    
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def load_delivery_data(_self, filters=None):
        """Load delivery data from delivery_full_view"""
        try:
            # Base query - Updated with new fields
            query = """
            SELECT 
                delivery_id,
                dn_number,
                created_by_email,
                created_by_name,
                created_date,
                shipment_status,
                shipment_status_vn,
                dispatched_date,
                delivered_date,
                sto_delivery_status,
                sto_etd_date,
                is_delivered,
                delivery_confirmed,
                delivery_timeline_status,
                days_overdue,
                notify_email,
                reference_packing_list,
                shipping_cost,
                total_weight,
                
                -- Order info
                oc_id,
                oc_number,
                oc_date,
                oc_line_id,
                oc_product_pn,
                standard_quantity,
                selling_quantity,
                uom_conversion,
                etd,
                
                -- Product info
                product_id,
                product_pn,
                pt_code,
                package_size,
                
                -- Stock info
                sto_dr_line_id,
                selling_stock_out_quantity,
                selling_stock_out_request_quantity,
                stock_out_quantity,
                stock_out_request_quantity,
                stockin_line_id,
                export_tax,
                remaining_quantity_to_deliver,
                total_instock_at_preferred_warehouse,
                total_instock_all_warehouses,
                gap_quantity,
                fulfill_rate_percent,
                fulfillment_status,
                
                -- New accurate gap analysis fields
                product_total_remaining_demand,
                product_active_delivery_count,
                product_gap_quantity,
                product_fulfill_rate_percent,
                delivery_demand_percentage,
                product_fulfillment_status,
                
                -- Customer info
                customer,
                customer_code,
                customer_street,
                customer_zip_code,
                customer_state_province,
                customer_country_code,
                customer_country_name,
                customer_contact,
                customer_contact_email,
                customer_contact_phone,
                
                -- Recipient info
                recipient_company,
                recipient_company_code,
                recipient_contact,
                recipient_contact_email,
                recipient_contact_phone,
                recipient_address,
                recipient_state_province,
                recipient_country_code,
                recipient_country_name,
                
                -- Other info
                is_epe_company,
                intl_charge,
                local_charge,
                legal_entity,
                legal_entity_code,
                legal_entity_state_province,
                legal_entity_country_code,
                legal_entity_country_name,
                preferred_warehouse
                
            FROM delivery_full_view
            WHERE 1=1
            """
            
            # Apply filters if provided
            params = {}
            
            if filters:
                if filters.get('products'):
                    # Extract pt_codes từ các product display đã chọn
                    pt_codes = [p.split(' - ')[0] for p in filters['products']]
                    query += " AND pt_code IN :pt_codes"
                    params['pt_codes'] = tuple(pt_codes)
                    
                if filters.get('date_from'):
                    query += " AND etd >= :date_from"
                    params['date_from'] = filters['date_from']
                
                if filters.get('date_to'):
                    query += " AND etd <= :date_to"
                    params['date_to'] = filters['date_to']
                
                if filters.get('creators'):
                    query += " AND created_by_name IN :creators"
                    params['creators'] = tuple(filters['creators'])
                
                if filters.get('customers'):
                    query += " AND customer IN :customers"
                    params['customers'] = tuple(filters['customers'])
                
                if filters.get('ship_to_companies'):
                    query += " AND recipient_company IN :ship_to_companies"
                    params['ship_to_companies'] = tuple(filters['ship_to_companies'])
                
                if filters.get('states'):
                    query += " AND recipient_state_province IN :states"
                    params['states'] = tuple(filters['states'])
                
                if filters.get('countries'):
                    query += " AND recipient_country_name IN :countries"
                    params['countries'] = tuple(filters['countries'])
                
                if filters.get('statuses'):
                    query += " AND shipment_status IN :statuses"
                    params['statuses'] = tuple(filters['statuses'])
                
                if filters.get('legal_entities'):
                    query += " AND legal_entity IN :legal_entities"
                    params['legal_entities'] = tuple(filters['legal_entities'])
                
                # EPE Company filter
                if filters.get('epe_filter'):
                    if filters['epe_filter'] == 'EPE Companies Only':
                        query += " AND is_epe_company = 'Yes'"
                    elif filters['epe_filter'] == 'Non-EPE Companies Only':
                        query += " AND is_epe_company = 'No'"
                
                # Foreign customer filter
                if filters.get('foreign_filter'):
                    if filters['foreign_filter'] == 'Foreign Only':
                        query += " AND customer_country_code != legal_entity_country_code"
                    elif filters['foreign_filter'] == 'Domestic Only':
                        query += " AND customer_country_code = legal_entity_country_code"
                
                # Timeline status filter (new)
                if filters.get('timeline_status'):
                    query += " AND delivery_timeline_status IN :timeline_status"
                    params['timeline_status'] = tuple(filters['timeline_status'])
            
            # Order by
            query += " ORDER BY delivery_id DESC, sto_dr_line_id DESC"
            
            # Execute query
            with _self.engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params=params)
            
            logger.info(f"Loaded {len(df)} delivery records")
            return df
            
        except Exception as e:
            logger.error(f"Error loading delivery data: {e}")
            st.error(f"Failed to load delivery data: {str(e)}")
            return pd.DataFrame()

    def get_filter_options(self):
        """Get unique values for filters"""
        try:
            queries = {
                'creators': "SELECT DISTINCT created_by_name FROM delivery_full_view WHERE created_by_name IS NOT NULL ORDER BY created_by_name",
                'customers': "SELECT DISTINCT customer FROM delivery_full_view WHERE customer IS NOT NULL ORDER BY customer",
                'ship_to_companies': "SELECT DISTINCT recipient_company FROM delivery_full_view WHERE recipient_company IS NOT NULL ORDER BY recipient_company",
                'states': "SELECT DISTINCT recipient_state_province FROM delivery_full_view WHERE recipient_state_province IS NOT NULL ORDER BY recipient_state_province",
                'countries': "SELECT DISTINCT recipient_country_name FROM delivery_full_view WHERE recipient_country_name IS NOT NULL ORDER BY recipient_country_name",
                'statuses': "SELECT DISTINCT shipment_status FROM delivery_full_view WHERE shipment_status IS NOT NULL ORDER BY shipment_status",
                'timeline_statuses': "SELECT DISTINCT delivery_timeline_status FROM delivery_full_view WHERE delivery_timeline_status IS NOT NULL ORDER BY delivery_timeline_status",
                'legal_entities': "SELECT DISTINCT legal_entity FROM delivery_full_view WHERE legal_entity IS NOT NULL ORDER BY legal_entity",
                # Product query - sử dụng CONCAT trực tiếp
                'products': """
                    SELECT DISTINCT 
                        CONCAT(pt_code, ' - ', product_pn) as product_display
                    FROM delivery_full_view 
                    WHERE pt_code IS NOT NULL 
                        AND product_pn IS NOT NULL
                    ORDER BY pt_code
                """
            }
            
            options = {}
            with self.engine.connect() as conn:
                for key, query in queries.items():
                    result = conn.execute(text(query))
                    options[key] = [row[0] for row in result]
                
                # NEW: Get date range from ETD
                date_range_query = """
                SELECT 
                    MIN(etd) as min_date,
                    MAX(etd) as max_date
                FROM delivery_full_view
                WHERE etd IS NOT NULL
                """
                date_result = conn.execute(text(date_range_query)).fetchone()
                options['date_range'] = {
                    'min_date': date_result[0] if date_result[0] else datetime.now().date() - timedelta(days=365),
                    'max_date': date_result[1] if date_result[1] else datetime.now().date() + timedelta(days=365)
                }
                
                # NEW: Get EPE company options
                epe_query = """
                SELECT DISTINCT is_epe_company 
                FROM delivery_full_view 
                WHERE is_epe_company IS NOT NULL 
                ORDER BY is_epe_company
                """
                epe_result = conn.execute(text(epe_query))
                epe_values = [row[0] for row in epe_result]
                
                # Create EPE filter options based on actual data
                epe_options = ["All"]
                if 'Yes' in epe_values:
                    epe_options.append("EPE Companies Only")
                if 'No' in epe_values:
                    epe_options.append("Non-EPE Companies Only")
                options['epe_options'] = epe_options
                
                # NEW: Get Foreign/Domestic customer options
                foreign_query = """
                SELECT DISTINCT
                    CASE 
                        WHEN customer_country_code = legal_entity_country_code THEN 'Domestic'
                        WHEN customer_country_code != legal_entity_country_code THEN 'Foreign'
                        ELSE 'Unknown'
                    END as customer_type
                FROM delivery_full_view
                WHERE customer_country_code IS NOT NULL 
                    AND legal_entity_country_code IS NOT NULL
                """
                foreign_result = conn.execute(text(foreign_query))
                foreign_types = [row[0] for row in foreign_result if row[0] != 'Unknown']
                
                # Create foreign filter options based on actual data
                foreign_options = ["All Customers"]
                if 'Domestic' in foreign_types:
                    foreign_options.append("Domestic Only")
                if 'Foreign' in foreign_types:
                    foreign_options.append("Foreign Only")
                options['foreign_options'] = foreign_options
            
            return options
            
        except Exception as e:
            logger.error(f"Error getting filter options: {e}")
            return {}

    def pivot_delivery_data(self, df, period='weekly'):
        """Pivot delivery data by period"""
        try:
            if df.empty:
                return pd.DataFrame()
            
            # Ensure etd is datetime
            df['etd'] = pd.to_datetime(df['etd'])
            
            # Create period column
            if period == 'daily':
                df['period'] = df['etd'].dt.date
                period_format = '%Y-%m-%d'
            elif period == 'weekly':
                df['period'] = df['etd'].dt.to_period('W').dt.start_time
                period_format = 'Week of %Y-%m-%d'
            else:  # monthly
                df['period'] = df['etd'].dt.to_period('M').dt.start_time
                period_format = '%B %Y'
            
            # Group by period and aggregate - include new gap analysis
            pivot_df = df.groupby(['period', 'customer', 'recipient_company']).agg({
                'delivery_id': 'count',
                'standard_quantity': 'sum',
                'remaining_quantity_to_deliver': 'sum',
                'gap_quantity': 'sum',
                'product_gap_quantity': 'sum',  # New accurate gap
                'product_total_remaining_demand': 'sum'  # Total demand
            }).reset_index()
            
            pivot_df.columns = ['Period', 'Customer', 'Ship To', 'Deliveries', 
                               'Total Quantity', 'Remaining to Deliver', 'Gap (Legacy)',
                               'Product Gap', 'Total Product Demand']
            
            # Format period
            pivot_df['Period'] = pd.to_datetime(pivot_df['Period']).dt.strftime(period_format)
            
            return pivot_df
            
        except Exception as e:
            logger.error(f"Error pivoting data: {e}")
            return pd.DataFrame()
   
    def get_sales_delivery_summary(self, creator_name, weeks_ahead=4):
        """Get delivery summary for a specific sales person - with line item details"""
        try:
            today = datetime.now().date()
            end_date = today + timedelta(weeks=weeks_ahead)
            
            query = text("""
            SELECT 
                DATE(etd) as delivery_date,
                customer,
                customer_code,
                recipient_company,
                recipient_company_code,
                recipient_contact,
                recipient_contact_email,
                recipient_contact_phone,
                recipient_address,
                recipient_state_province,
                recipient_country_name,
                delivery_id,
                dn_number,
                sto_dr_line_id,
                oc_number,
                oc_line_id,
                product_pn,
                product_id,
                pt_code,
                package_size,
                standard_quantity,
                selling_quantity,
                uom_conversion,
                remaining_quantity_to_deliver,
                total_instock_at_preferred_warehouse,
                gap_quantity,
                product_gap_quantity,
                product_total_remaining_demand,
                product_fulfill_rate_percent,
                delivery_demand_percentage,
                shipment_status,
                shipment_status_vn,
                fulfillment_status,
                product_fulfillment_status,
                delivery_timeline_status,
                days_overdue,
                preferred_warehouse,
                is_epe_company,
                legal_entity,
                created_by_name,
                created_date
            FROM delivery_full_view
            WHERE created_by_name = :creator_name
                AND etd >= :today
                AND etd <= :end_date
                AND remaining_quantity_to_deliver > 0
            ORDER BY delivery_date, customer, delivery_id, sto_dr_line_id
            """)
            
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn, params={
                    'creator_name': creator_name,
                    'today': today,
                    'end_date': end_date
                })
            
            # Debug: Check for duplicate columns
            if not df.empty:
                duplicate_cols = df.columns[df.columns.duplicated()].tolist()
                if duplicate_cols:
                    logger.warning(f"Duplicate columns found in sales delivery summary: {duplicate_cols}")
                    # Remove duplicates
                    df = df.loc[:, ~df.columns.duplicated()]
                
                # Add total_quantity as alias for remaining_quantity_to_deliver
                df['total_quantity'] = df['remaining_quantity_to_deliver']
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting sales delivery summary: {e}")
            return pd.DataFrame()
    
    def get_sales_urgent_deliveries(self, creator_name):
        """Get overdue and due today deliveries for a specific sales person (NEW)"""
        try:
            query = text("""
            SELECT 
                DATE(etd) as delivery_date,
                customer,
                customer_code,
                recipient_company,
                recipient_company_code,
                recipient_contact,
                recipient_contact_email,
                recipient_contact_phone,
                recipient_address,
                recipient_state_province,
                recipient_country_name,
                delivery_id,
                dn_number,
                sto_dr_line_id,
                oc_number,
                oc_line_id,
                product_pn,
                product_id,
                pt_code,
                package_size,
                standard_quantity,
                selling_quantity,
                uom_conversion,
                remaining_quantity_to_deliver,
                total_instock_at_preferred_warehouse,
                total_instock_all_warehouses,
                gap_quantity,
                product_gap_quantity,
                product_total_remaining_demand,
                product_fulfill_rate_percent,
                delivery_demand_percentage,
                shipment_status,
                shipment_status_vn,
                fulfillment_status,
                product_fulfillment_status,
                delivery_timeline_status,
                days_overdue,
                preferred_warehouse,
                is_epe_company,
                legal_entity,
                created_by_name,
                created_date
            FROM delivery_full_view
            WHERE created_by_name = :creator_name
                AND delivery_timeline_status IN ('Overdue', 'Due Today')
                AND remaining_quantity_to_deliver > 0
                AND shipment_status NOT IN ('DELIVERED', 'COMPLETED')
            ORDER BY 
                delivery_timeline_status DESC,  -- Overdue first, then Due Today
                days_overdue DESC,              -- Most overdue first
                delivery_date,
                customer,
                delivery_id,
                sto_dr_line_id
            """)
            
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn, params={
                    'creator_name': creator_name
                })
            
            # Debug: Check for duplicate columns
            if not df.empty:
                duplicate_cols = df.columns[df.columns.duplicated()].tolist()
                if duplicate_cols:
                    logger.warning(f"Duplicate columns found in urgent deliveries: {duplicate_cols}")
                    # Remove duplicates
                    df = df.loc[:, ~df.columns.duplicated()]
                
                # Add total_quantity as alias
                df['total_quantity'] = df['remaining_quantity_to_deliver']
                
                # Log summary
                overdue_count = df[df['delivery_timeline_status'] == 'Overdue']['delivery_id'].nunique()
                due_today_count = df[df['delivery_timeline_status'] == 'Due Today']['delivery_id'].nunique()
                logger.info(f"Loaded {overdue_count} overdue and {due_today_count} due today deliveries for {creator_name}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting urgent deliveries: {e}")
            return pd.DataFrame()
    
    def get_overdue_deliveries(self):
        """Get overdue deliveries that need attention"""
        try:
            query = text("""
            SELECT 
                delivery_id,
                dn_number,
                customer,
                recipient_company,
                etd,
                days_overdue,
                remaining_quantity_to_deliver,
                shipment_status,
                shipment_status_vn,
                fulfillment_status,
                product_fulfillment_status,
                created_by_name,
                is_epe_company
            FROM delivery_full_view
            WHERE delivery_timeline_status = 'Overdue'
                AND remaining_quantity_to_deliver > 0
                AND shipment_status NOT IN ('DELIVERED', 'ON_DELIVERY', 'DISPATCHED')
            ORDER BY days_overdue DESC, delivery_id DESC
            """)
            
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn)
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting overdue deliveries: {e}")
            return pd.DataFrame()
    
    def get_product_demand_analysis(self, product_id=None):
        """Get product demand analysis with accurate gap calculation"""
        try:
            query = """
            SELECT 
                product_id,
                product_pn,
                pt_code,
                COUNT(DISTINCT delivery_id) as active_deliveries,
                SUM(remaining_quantity_to_deliver) as total_remaining_demand,
                MAX(total_instock_all_warehouses) as total_inventory,
                MAX(product_gap_quantity) as gap_quantity,
                MAX(product_fulfill_rate_percent) as fulfill_rate,
                MAX(product_fulfillment_status) as fulfillment_status,
                GROUP_CONCAT(DISTINCT customer SEPARATOR ', ') as customers
            FROM delivery_full_view
            WHERE remaining_quantity_to_deliver > 0
                AND shipment_status != 'DELIVERED'
            """
            
            params = {}
            if product_id:
                query += " AND product_id = :product_id"
                params['product_id'] = product_id
            
            query += " GROUP BY product_id, product_pn, pt_code ORDER BY total_remaining_demand DESC"
            
            with self.engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params=params)
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting product demand analysis: {e}")
            return pd.DataFrame()
        
    # Add these methods to utils/data_loader.py

    def get_customs_clearance_summary(self):
        """Get summary of customs clearance deliveries (EPE + Foreign)"""
        try:
            query = text("""
            SELECT 
                COUNT(DISTINCT CASE WHEN is_epe_company = 'Yes' THEN delivery_id END) as epe_deliveries,
                COUNT(DISTINCT CASE WHEN customer_country_code != legal_entity_country_code THEN delivery_id END) as foreign_deliveries,
                COUNT(DISTINCT CASE WHEN customer_country_code != legal_entity_country_code THEN customer_country_name END) as countries
            FROM delivery_full_view
            WHERE etd >= CURDATE()
                AND etd <= DATE_ADD(CURDATE(), INTERVAL 4 WEEK)
                AND remaining_quantity_to_deliver > 0
                AND shipment_status NOT IN ('DELIVERED', 'COMPLETED')
                AND (is_epe_company = 'Yes' OR customer_country_code != legal_entity_country_code)
            """)
            
            with self.engine.connect() as conn:
                result = conn.execute(query).fetchone()
                
            return pd.DataFrame([{
                'epe_deliveries': result[0] or 0,
                'foreign_deliveries': result[1] or 0,
                'countries': result[2] or 0
            }])
            
        except Exception as e:
            logger.error(f"Error getting customs clearance summary: {e}")
            return pd.DataFrame()

    def get_customs_clearance_schedule(self):
        """Get customs clearance schedule for EPE and Foreign customers"""
        try:
            today = datetime.now().date()
            end_date = today + timedelta(weeks=4)
            
            query = text("""
            SELECT DISTINCT
                DATE(etd) as delivery_date,
                etd,
                customer,
                customer_code,
                customer_street,
                customer_state_province,
                customer_country_code,
                customer_country_name,
                recipient_company,
                recipient_company_code,
                recipient_contact,
                recipient_contact_email,
                recipient_contact_phone,
                recipient_address,
                recipient_state_province,
                recipient_country_code,
                recipient_country_name,
                delivery_id,
                dn_number,
                sto_dr_line_id,
                oc_number,
                oc_line_id,
                product_pn,
                product_id,
                pt_code,
                package_size,
                standard_quantity,
                selling_quantity,
                uom_conversion,
                remaining_quantity_to_deliver,
                total_instock_at_preferred_warehouse,
                total_instock_all_warehouses,
                gap_quantity,
                product_gap_quantity,
                product_total_remaining_demand,
                product_fulfill_rate_percent,
                delivery_demand_percentage,
                shipment_status,
                shipment_status_vn,
                fulfillment_status,
                product_fulfillment_status,
                delivery_timeline_status,
                days_overdue,
                preferred_warehouse,
                is_epe_company,
                legal_entity,
                legal_entity_code,
                legal_entity_state_province,
                legal_entity_country_code,
                legal_entity_country_name,
                created_by_name,
                created_date,
                -- Calculate customs type
                CASE 
                    WHEN is_epe_company = 'Yes' THEN 'EPE'
                    WHEN customer_country_code != legal_entity_country_code THEN 'Foreign'
                    ELSE 'Domestic'
                END as customs_type,
                -- EPE location info
                CASE 
                    WHEN is_epe_company = 'Yes' THEN 
                        CONCAT(recipient_state_province, ' - ', recipient_company)
                    ELSE NULL
                END as epe_location
            FROM delivery_full_view
            WHERE etd >= :today
                AND etd <= :end_date
                AND remaining_quantity_to_deliver > 0
                AND shipment_status NOT IN ('DELIVERED', 'COMPLETED')
                AND (
                    is_epe_company = 'Yes' 
                    OR customer_country_code != legal_entity_country_code
                )
            ORDER BY 
                customs_type,
                CASE 
                    WHEN is_epe_company = 'Yes' THEN recipient_state_province
                    ELSE customer_country_name
                END,
                delivery_date,
                customer,
                delivery_id,
                sto_dr_line_id
            """)
            
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn, params={
                    'today': today,
                    'end_date': end_date
                })
            
            # Debug: Log columns
            logger.info(f"Columns retrieved from customs query: {df.columns.tolist()}")
            
            # Debug: Check for duplicate columns
            if not df.empty:
                duplicate_cols = df.columns[df.columns.duplicated()].tolist()
                if duplicate_cols:
                    logger.warning(f"Duplicate columns found in customs clearance data: {duplicate_cols}")
                    # Remove duplicates
                    df = df.loc[:, ~df.columns.duplicated()]
                
                # Add total_quantity as alias for remaining_quantity_to_deliver
                df['total_quantity'] = df['remaining_quantity_to_deliver']
                
                # Log summary
                epe_count = df[df['customs_type'] == 'EPE']['delivery_id'].nunique()
                foreign_count = df[df['customs_type'] == 'Foreign']['delivery_id'].nunique()
                logger.info(f"Loaded {epe_count} EPE and {foreign_count} Foreign deliveries for customs clearance")
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting customs clearance schedule: {e}")
            return pd.DataFrame()

    def get_customs_clearance_by_type(self, customs_type='EPE'):
        """Get customs clearance data filtered by type (EPE or Foreign)"""
        try:
            df = self.get_customs_clearance_schedule()
            
            if df.empty:
                return pd.DataFrame()
            
            # Filter by customs type
            if customs_type == 'EPE':
                filtered_df = df[df['customs_type'] == 'EPE'].copy()
            elif customs_type == 'Foreign':
                filtered_df = df[df['customs_type'] == 'Foreign'].copy()
            else:
                filtered_df = df.copy()
            
            return filtered_df
            
        except Exception as e:
            logger.error(f"Error filtering customs clearance by type: {e}")
            return pd.DataFrame()

    def get_customs_country_summary(self):
        """Get summary of foreign deliveries by country"""
        try:
            today = datetime.now().date()
            end_date = today + timedelta(weeks=4)
            
            query = text("""
            SELECT 
                customer_country_name as country,
                customer_country_code as country_code,
                COUNT(DISTINCT delivery_id) as deliveries,
                COUNT(DISTINCT customer) as customers,
                SUM(remaining_quantity_to_deliver) as total_quantity,
                COUNT(DISTINCT product_id) as products,
                MIN(etd) as first_delivery,
                MAX(etd) as last_delivery
            FROM delivery_full_view
            WHERE etd >= :today
                AND etd <= :end_date
                AND remaining_quantity_to_deliver > 0
                AND shipment_status NOT IN ('DELIVERED', 'COMPLETED')
                AND customer_country_code != legal_entity_country_code
            GROUP BY customer_country_name, customer_country_code
            ORDER BY deliveries DESC, country
            """)
            
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn, params={
                    'today': today,
                    'end_date': end_date
                })
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting customs country summary: {e}")
            return pd.DataFrame()

    def get_epe_location_summary(self):
        """Get summary of EPE deliveries by location/industrial zone"""
        try:
            today = datetime.now().date()
            end_date = today + timedelta(weeks=4)
            
            query = text("""
            SELECT 
                recipient_state_province as location,
                COUNT(DISTINCT delivery_id) as deliveries,
                COUNT(DISTINCT customer) as customers,
                COUNT(DISTINCT recipient_company) as epe_companies,
                SUM(remaining_quantity_to_deliver) as total_quantity,
                COUNT(DISTINCT product_id) as products,
                MIN(etd) as first_delivery,
                MAX(etd) as last_delivery
            FROM delivery_full_view
            WHERE etd >= :today
                AND etd <= :end_date
                AND remaining_quantity_to_deliver > 0
                AND shipment_status NOT IN ('DELIVERED', 'COMPLETED')
                AND is_epe_company = 'Yes'
            GROUP BY recipient_state_province
            ORDER BY deliveries DESC, location
            """)
            
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn, params={
                    'today': today,
                    'end_date': end_date
                })
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting EPE location summary: {e}")
            return pd.DataFrame()
        
            