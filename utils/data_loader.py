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
            # Base query
            query = """
            SELECT 
                delivery_id,
                dn_number,
                created_by_email,
                created_by_name,
                created_date,
                shipment_status,
                dispatched_date,
                delivered_date,
                sto_delivery_status,
                sto_etd_date,
                is_delivered,
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
                remaining_quantity_to_deliver,
                total_instock_at_preferred_warehouse,
                total_instock_all_warehouses,
                gap_quantity,
                fulfill_rate_percent,
                fulfillment_status,
                
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
                'statuses': "SELECT DISTINCT shipment_status FROM delivery_full_view WHERE shipment_status IS NOT NULL ORDER BY shipment_status"
            }
            
            options = {}
            with self.engine.connect() as conn:
                for key, query in queries.items():
                    result = conn.execute(text(query))
                    options[key] = [row[0] for row in result]
            
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
            
            # Group by period and aggregate
            pivot_df = df.groupby(['period', 'customer', 'recipient_company']).agg({
                'delivery_id': 'count',
                'standard_quantity': 'sum',
                'remaining_quantity_to_deliver': 'sum',
                'gap_quantity': 'sum'
            }).reset_index()
            
            pivot_df.columns = ['Period', 'Customer', 'Ship To', 'Deliveries', 
                               'Total Quantity', 'Remaining to Deliver', 'Gap']
            
            # Format period
            pivot_df['Period'] = pd.to_datetime(pivot_df['Period']).dt.strftime(period_format)
            
            return pivot_df
            
        except Exception as e:
            logger.error(f"Error pivoting data: {e}")
            return pd.DataFrame()
    
    def get_sales_delivery_summary(self, creator_name, weeks_ahead=4):
        """Get delivery summary for a specific sales person"""
        try:
            today = datetime.now().date()
            end_date = today + timedelta(weeks=weeks_ahead)
            
            query = text("""
            SELECT 
                DATE(etd) as delivery_date,
                customer,
                recipient_company,
                recipient_contact,
                recipient_address,
                recipient_state_province,
                recipient_country_name,
                COUNT(DISTINCT delivery_id) as delivery_count,
                COUNT(DISTINCT sto_dr_line_id) as line_items,
                SUM(standard_quantity) as total_quantity,
                SUM(remaining_quantity_to_deliver) as remaining_quantity,
                GROUP_CONCAT(DISTINCT product_pn SEPARATOR ', ') as products,
                GROUP_CONCAT(DISTINCT dn_number SEPARATOR ', ') as dn_numbers,
                MIN(shipment_status) as status,
                MIN(fulfillment_status) as fulfillment_status
            FROM delivery_full_view
            WHERE created_by_name = :creator_name
                AND etd >= :today
                AND etd <= :end_date
                AND remaining_quantity_to_deliver > 0
            GROUP BY DATE(etd), customer, recipient_company, recipient_contact, 
                     recipient_address, recipient_state_province, recipient_country_name
            ORDER BY delivery_date, customer
            """)
            
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn, params={
                    'creator_name': creator_name,
                    'today': today,
                    'end_date': end_date
                })
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting sales delivery summary: {e}")
            return pd.DataFrame()