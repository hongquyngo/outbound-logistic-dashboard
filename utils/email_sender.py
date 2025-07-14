# utils/email_sender.py - Email sending module

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import pandas as pd
from datetime import datetime, timedelta
import logging
import io
import os
from utils.calendar_utils import CalendarEventGenerator
from utils.config import EMAIL_SENDER, EMAIL_PASSWORD

logger = logging.getLogger(__name__)


class EmailSender:
    """Handle email notifications for delivery schedules"""
    
    def __init__(self, smtp_host=None, smtp_port=None):
        # Use environment variables or defaults
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = EMAIL_SENDER or os.getenv("EMAIL_SENDER", "outbound@prostech.vn")
        self.sender_password = EMAIL_PASSWORD or os.getenv("EMAIL_PASSWORD", "")
        
        # Log configuration
        logger.info(f"Email sender initialized with: {self.sender_email} via {self.smtp_host}:{self.smtp_port}")
    
    def create_overdue_alerts_html(self, delivery_df, sales_name):
        """Create HTML content for overdue alerts email (NEW)"""
        
        # Ensure delivery_date is datetime
        delivery_df['delivery_date'] = pd.to_datetime(delivery_df['delivery_date'])
        
        # Separate overdue and due today
        overdue_df = delivery_df[delivery_df['delivery_timeline_status'] == 'Overdue'].copy()
        due_today_df = delivery_df[delivery_df['delivery_timeline_status'] == 'Due Today'].copy()
        
        # Calculate summary statistics
        total_overdue = overdue_df['delivery_id'].nunique() if not overdue_df.empty else 0
        total_due_today = due_today_df['delivery_id'].nunique() if not due_today_df.empty else 0
        max_days_overdue = overdue_df['days_overdue'].max() if not overdue_df.empty and 'days_overdue' in overdue_df.columns else 0
        
        # Out of stock products
        out_of_stock_products = 0
        if 'product_fulfillment_status' in delivery_df.columns and 'product_id' in delivery_df.columns:
            out_of_stock_products = delivery_df[delivery_df['product_fulfillment_status'] == 'Out of Stock']['product_id'].nunique()
        
        # Start HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .header {{
                    background-color: #d32f2f;
                    color: white;
                    padding: 20px;
                    text-align: center;
                }}
                .content {{
                    padding: 20px;
                }}
                .alert-box {{
                    background-color: #ffebee;
                    border: 2px solid #ef5350;
                    border-radius: 5px;
                    padding: 15px;
                    margin: 20px 0;
                }}
                .summary-grid {{
                    display: table;
                    width: 100%;
                    margin: 20px 0;
                }}
                .summary-item {{
                    display: table-cell;
                    text-align: center;
                    padding: 10px;
                }}
                .metric-value {{
                    font-size: 36px;
                    font-weight: bold;
                    color: #d32f2f;
                }}
                .metric-label {{
                    font-size: 14px;
                    color: #666;
                    margin-top: 5px;
                }}
                .section-header {{
                    background-color: #f5f5f5;
                    padding: 10px;
                    margin: 20px 0 10px 0;
                    border-left: 4px solid #d32f2f;
                    font-weight: bold;
                    font-size: 18px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                }}
                th, td {{
                    padding: 8px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background-color: #f8f9fa;
                    font-weight: bold;
                }}
                .overdue-row {{
                    background-color: #ffcccb;
                }}
                .due-today-row {{
                    background-color: #ffe4b5;
                }}
                .out-of-stock {{
                    color: #d32f2f;
                    font-weight: bold;
                }}
                .days-overdue {{
                    color: #d32f2f;
                    font-weight: bold;
                    font-size: 16px;
                }}
                .action-box {{
                    background-color: #e3f2fd;
                    border: 1px solid #2196f3;
                    border-radius: 5px;
                    padding: 15px;
                    margin: 20px 0;
                }}
                .footer {{
                    margin-top: 30px;
                    padding: 20px;
                    background-color: #f8f9fa;
                    text-align: center;
                    font-size: 12px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚨 URGENT DELIVERY ALERT</h1>
                <p>Immediate Action Required</p>
            </div>
            
            <div class="content">
                <p>Dear {sales_name},</p>
                
                <div class="alert-box">
                    <strong>⚠️ CRITICAL ALERT:</strong> You have deliveries that require immediate attention. 
                    Please review the details below and take necessary action to avoid further delays.
                </div>
                
                <div class="summary-grid">
                    <div class="summary-item">
                        <div class="metric-value">{total_overdue}</div>
                        <div class="metric-label">Overdue Deliveries</div>
                    </div>
                    <div class="summary-item">
                        <div class="metric-value">{total_due_today}</div>
                        <div class="metric-label">Due Today</div>
                    </div>
                    <div class="summary-item">
                        <div class="metric-value">{int(max_days_overdue)}</div>
                        <div class="metric-label">Max Days Overdue</div>
                    </div>
                    <div class="summary-item">
                        <div class="metric-value">{out_of_stock_products}</div>
                        <div class="metric-label">Out of Stock Products</div>
                    </div>
                </div>
        """
        
        # Overdue Section
        if not overdue_df.empty:
            html += """
                <div class="section-header">🔴 OVERDUE DELIVERIES</div>
                <p>These deliveries are past their expected delivery date and need immediate attention:</p>
                <table>
                    <tr>
                        <th width="80">Days Overdue</th>
                        <th width="100">Delivery Date</th>
                        <th width="150">Customer</th>
                        <th width="150">Ship To</th>
                        <th width="80">PT Code</th>
                        <th width="120">Product</th>
                        <th width="80">Quantity</th>
                        <th width="100">Fulfillment</th>
                        <th width="120">DN Number</th>
                    </tr>
            """
            
            # Group and sort overdue deliveries
            overdue_display = overdue_df.sort_values(['days_overdue', 'delivery_date'], ascending=[False, True])
            
            for _, row in overdue_display.iterrows():
                days_overdue = int(row['days_overdue']) if pd.notna(row['days_overdue']) else 0
                fulfillment_status = row.get('product_fulfillment_status', row.get('fulfillment_status', 'Unknown'))
                fulfillment_class = 'out-of-stock' if fulfillment_status == 'Out of Stock' else ''
                
                html += f"""
                    <tr class="overdue-row">
                        <td class="days-overdue">{days_overdue} days</td>
                        <td>{row['delivery_date'].strftime('%Y-%m-%d')}</td>
                        <td>{row['customer']}</td>
                        <td>{row['recipient_company']}</td>
                        <td>{row['pt_code']}</td>
                        <td>{row['product_pn']}</td>
                        <td>{row['remaining_quantity_to_deliver']:,.0f}</td>
                        <td class="{fulfillment_class}">{fulfillment_status}</td>
                        <td>{row['dn_number']}</td>
                    </tr>
                """
            
            html += "</table>"
        
        # Due Today Section
        if not due_today_df.empty:
            html += """
                <div class="section-header">🟡 DUE TODAY</div>
                <p>These deliveries are scheduled for today and should be prioritized:</p>
                <table>
                    <tr>
                        <th width="100">Delivery Date</th>
                        <th width="150">Customer</th>
                        <th width="150">Ship To</th>
                        <th width="80">PT Code</th>
                        <th width="120">Product</th>
                        <th width="80">Quantity</th>
                        <th width="100">Fulfillment</th>
                        <th width="120">DN Number</th>
                    </tr>
            """
            
            # Sort by fulfillment status (out of stock first)
            due_today_display = due_today_df.sort_values(['product_fulfillment_status', 'customer'])
            
            for _, row in due_today_display.iterrows():
                fulfillment_status = row.get('product_fulfillment_status', row.get('fulfillment_status', 'Unknown'))
                fulfillment_class = 'out-of-stock' if fulfillment_status == 'Out of Stock' else ''
                
                html += f"""
                    <tr class="due-today-row">
                        <td>{row['delivery_date'].strftime('%Y-%m-%d')}</td>
                        <td>{row['customer']}</td>
                        <td>{row['recipient_company']}</td>
                        <td>{row['pt_code']}</td>
                        <td>{row['product_pn']}</td>
                        <td>{row['remaining_quantity_to_deliver']:,.0f}</td>
                        <td class="{fulfillment_class}">{fulfillment_status}</td>
                        <td>{row['dn_number']}</td>
                    </tr>
                """
            
            html += "</table>"
        
        # Action Items
        html += """
            <div class="action-box">
                <h3>📋 Required Actions:</h3>
                <ol>
                    <li><strong>Contact Customers:</strong> Inform customers about delivery delays and provide updated ETAs</li>
                    <li><strong>Coordinate with Warehouse:</strong> Check inventory availability for out-of-stock items</li>
                    <li><strong>Update Delivery Status:</strong> Ensure all delivery statuses are current in the system</li>
                    <li><strong>Escalate if Needed:</strong> For deliveries overdue by 5+ days, escalate to management</li>
                </ol>
                
                <p><strong>Logistics Team Contact:</strong><br>
                📧 Email: outbound@prostech.vn<br>
                📞 Phone: +84 33 476273</p>
            </div>
            
            <div class="footer">
                <p>This is an automated urgent alert from Outbound Logistics System</p>
                <p>Please take immediate action on the items listed above</p>
                <p>For questions, contact: <a href="mailto:outbound@prostech.vn">outbound@prostech.vn</a></p>
            </div>
        </div>
        </body>
        </html>
        """
        
        return html
    
    def create_delivery_schedule_html(self, delivery_df, sales_name):
        """Create HTML content for delivery schedule email with enhanced information"""
        
        # Group by week - Fixed week calculation
        delivery_df['delivery_date'] = pd.to_datetime(delivery_df['delivery_date'])
        
        # Calculate week start (Monday) for each delivery date
        delivery_df['week_start'] = delivery_df['delivery_date'] - pd.to_timedelta(delivery_df['delivery_date'].dt.dayofweek, unit='D')
        delivery_df['week_end'] = delivery_df['week_start'] + timedelta(days=6)
        delivery_df['week_key'] = delivery_df['week_start'].dt.strftime('%Y-%m-%d')
        
        # Calculate ISO week number for display
        delivery_df['week'] = delivery_df['delivery_date'].dt.isocalendar().week
        delivery_df['year'] = delivery_df['delivery_date'].dt.year
        
        # Debug: Check columns
        logger.debug(f"Columns in delivery_df: {delivery_df.columns.tolist()}")
        
        # Calculate summary statistics with new fields
        out_of_stock_products = 0
        avg_fulfill_rate = 100.0
        
        if 'product_fulfillment_status' in delivery_df.columns and 'product_id' in delivery_df.columns:
            out_of_stock_products = delivery_df[delivery_df['product_fulfillment_status'] == 'Out of Stock']['product_id'].nunique()
        
        if 'product_fulfill_rate_percent' in delivery_df.columns and 'product_id' in delivery_df.columns:
            avg_fulfill_rate = delivery_df.groupby('product_id')['product_fulfill_rate_percent'].first().mean()
        
        # Start HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .header {{
                    background-color: #1f77b4;
                    color: white;
                    padding: 20px;
                    text-align: center;
                }}
                .content {{
                    padding: 20px;
                }}
                .week-section {{
                    margin-bottom: 30px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    padding: 15px;
                }}
                .week-header {{
                    background-color: #f0f2f6;
                    padding: 10px;
                    margin: -15px -15px 15px -15px;
                    border-radius: 5px 5px 0 0;
                    font-weight: bold;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                }}
                th, td {{
                    padding: 8px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background-color: #f8f9fa;
                    font-weight: bold;
                }}
                .urgent {{
                    color: #d32f2f;
                    font-weight: bold;
                }}
                .overdue {{
                    background-color: #ffcccb;
                    font-weight: bold;
                }}
                .warning {{
                    background-color: #fff3cd;
                    padding: 10px;
                    border-radius: 5px;
                    margin: 10px 0;
                }}
                .footer {{
                    margin-top: 30px;
                    padding: 20px;
                    background-color: #f8f9fa;
                    text-align: center;
                    font-size: 12px;
                    color: #666;
                }}
                .metric-box {{
                    display: inline-block;
                    background-color: #f0f2f6;
                    padding: 15px;
                    margin: 10px;
                    border-radius: 5px;
                    text-align: center;
                }}
                .metric-value {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #1f77b4;
                }}
                .metric-label {{
                    font-size: 12px;
                    color: #666;
                    margin-top: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📦 Delivery Schedule Notification</h1>
                <p>Your Next 4 Weeks Delivery Plan</p>
            </div>
            
            <div class="content">
                <p>Dear {sales_name},</p>
                <p>Please find below your delivery schedule for the next 4 weeks. 
                   Make sure to coordinate with customers for smooth delivery operations.</p>
                
                <div class="summary">
                    <h3>📊 Summary</h3>
                    <div style="text-align: center;">
                        <div class="metric-box">
                            <div class="metric-value">{delivery_df.groupby(['delivery_date', 'customer', 'recipient_company']).ngroups}</div>
                            <div class="metric-label">Total Deliveries</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-value">{delivery_df['product_id'].nunique() if 'product_id' in delivery_df.columns else delivery_df['product_pn'].nunique()}</div>
                            <div class="metric-label">Product Types</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-value">{delivery_df['remaining_quantity_to_deliver'].sum():,.0f}</div>
                            <div class="metric-label">Total Quantity</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-value">{avg_fulfill_rate:.1f}%</div>
                            <div class="metric-label">Avg Fulfillment Rate</div>
                        </div>
                    </div>
                </div>
        """
        
        # Add alerts if any out of stock products
        if out_of_stock_products > 0:
            html += f"""
                <div class="warning">
                    <strong>⚠️ Attention Required:</strong><br>
                    • {out_of_stock_products} products are out of stock<br>
                    Please coordinate with the logistics team to resolve these issues.
                </div>
            """
        
        # Group by week and create sections
        for week_key, week_df in delivery_df.groupby('week_key', sort=True):
            week_start = week_df['week_start'].iloc[0]
            week_end = week_df['week_end'].iloc[0]
            week_number = week_df['week'].iloc[0]
            
            # Calculate totals for this week
            week_unique_deliveries = week_df.groupby(['delivery_date', 'customer', 'recipient_company']).ngroups
            week_unique_products = week_df['product_id'].nunique()
            week_line_items = len(week_df)
            week_total_qty = week_df['remaining_quantity_to_deliver'].sum()
            
            html += f"""
                <div class="week-section">
                    <div class="week-header">
                        Week {week_number} ({week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')})
                        <span style="float: right; font-size: 14px;">
                            {week_unique_deliveries} deliveries | {week_unique_products} products | {week_total_qty:,.0f} units
                        </span>
                    </div>
            """
            
            html += """
                    <table>
                        <tr>
                            <th style="width: 80px;">Date</th>
                            <th style="width: 180px;">Customer</th>
                            <th style="width: 180px;">Ship To</th>
                            <th style="width: 100px;">PT Code</th>
                            <th style="width: 140px;">Product</th>
                            <th style="width: 80px;">Qty</th>
                            <th style="width: 100px;">Fulfillment</th>
                        </tr>
            """
            
            # Group by date, customer, recipient, and PRODUCT ID (not product_pn) for display
            # Keep groupby columns separate from aggregation columns
            if 'product_id' in week_df.columns:
                group_cols = ['delivery_date', 'customer', 'recipient_company', 
                             'recipient_state_province', 'recipient_country_name', 
                             'product_id', 'pt_code', 'product_pn']
            else:
                # Fallback if product_id not available
                group_cols = ['delivery_date', 'customer', 'recipient_company', 
                             'recipient_state_province', 'recipient_country_name', 
                             'pt_code', 'product_pn']
            
            # Create a copy for aggregation to avoid modifying original
            agg_df = week_df.copy()
            
            # Build aggregation dictionary
            agg_dict = {
                'remaining_quantity_to_deliver': 'sum'
            }
            
            # Add status columns for aggregation (take first value after grouping)
            if 'fulfillment_status' in agg_df.columns:
                agg_dict['fulfillment_status'] = lambda x: 'Mixed' if x.nunique() > 1 else x.iloc[0]
            
            if 'product_fulfillment_status' in agg_df.columns:
                agg_dict['product_fulfillment_status'] = 'first'
            
            try:
                display_group = agg_df.groupby(group_cols, as_index=False).agg(agg_dict)
                # Sort by date and product - use pt_code if product_id not available
                if 'product_id' in display_group.columns:
                    display_group = display_group.sort_values(['delivery_date', 'product_id'])
                else:
                    display_group = display_group.sort_values(['delivery_date', 'pt_code'])
            except Exception as e:
                logger.error(f"Error in groupby: {e}")
                # Fallback: simple grouping without status columns
                display_group = agg_df.groupby(group_cols, as_index=False).agg({
                    'remaining_quantity_to_deliver': 'sum'
                })
                if 'product_id' in display_group.columns:
                    display_group = display_group.sort_values(['delivery_date', 'product_id'])
                else:
                    display_group = display_group.sort_values(['delivery_date', 'pt_code'])
            
            # Add rows to table
            for _, row in display_group.iterrows():
                # Product fulfillment status
                product_status = row.get('product_fulfillment_status', row.get('fulfillment_status', 'Unknown'))
                status_class = 'urgent' if product_status in ['Out of Stock', 'Can Fulfill Partial'] else ''
                
                html += f"""
                        <tr>
                            <td>{row['delivery_date'].strftime('%b %d')}</td>
                            <td>{row['customer']}</td>
                            <td>{row['recipient_company']}</td>
                            <td>{row['pt_code']}</td>
                            <td>{row['product_pn']}</td>
                            <td>{row['remaining_quantity_to_deliver']:,.0f}</td>
                            <td class="{status_class}">{product_status}</td>
                        </tr>
                """
            
            html += """
                    </table>
                </div>
            """
        
        # Add legend
        html += """
            <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
                <h4>Fulfillment Status:</h4>
                <p>• <strong>Can Fulfill All:</strong> Sufficient inventory for all deliveries<br>
                   • <strong>Can Fulfill Partial:</strong> Limited inventory available<br>
                   • <strong>Out of Stock:</strong> No inventory available</p>
            </div>
        """
        
        # Add calendar buttons
        calendar_gen = CalendarEventGenerator()
        google_cal_links = calendar_gen.create_google_calendar_links(sales_name, delivery_df)
        outlook_cal_links = calendar_gen.create_outlook_calendar_links(sales_name, delivery_df)
        
        # Show calendar links for each date
        html += """
            <div style="margin: 30px 0;">
                <h3>📅 Add to Your Calendar</h3>
                <p style="margin-bottom: 20px;">Click below to add individual delivery dates to your calendar:</p>
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px;">
        """
        
        # Add individual date links
        for i, gcal_link in enumerate(google_cal_links[:5]):  # Show first 5 dates
            date_str = gcal_link['date'].strftime('%b %d')
            html += f"""
                    <div style="margin: 10px 0;">
                        <span style="font-weight: bold;">{date_str}:</span>
                        <a href="{gcal_link['link']}" target="_blank" 
                           style="margin: 0 10px; color: #4285f4;">📅 Google Calendar</a>
                        <a href="{outlook_cal_links[i]['link']}" target="_blank" 
                           style="margin: 0 10px; color: #0078d4;">📅 Outlook</a>
                    </div>
            """
        
        if len(google_cal_links) > 5:
            html += f"""
                    <p style="margin-top: 10px; font-style: italic;">
                        ... and {len(google_cal_links) - 5} more dates
                    </p>
            """
        
        html += """
                </div>
                <p style="margin-top: 15px; font-size: 12px; color: #666;">
                    Or download the attached .ics file to import all dates into any calendar application
                </p>
            </div>
            
            <div class="footer">
                <p>This is an automated email from Outbound Logistics System</p>
                <p>For questions, please contact: <a href="mailto:outbound@prostech.vn">outbound@prostech.vn</a></p>
            </div>
        </div>
        </body>
        </html>
        """
        
        return html
    
    def create_excel_attachment(self, delivery_df, notification_type="📅 Delivery Schedule"):
        """Create Excel file as attachment with enhanced information"""
        output = io.BytesIO()
        
        # Create a copy for Excel export - NO AGGREGATION, show all line items
        excel_df = delivery_df.copy()
        
        # Format date columns for Excel
        date_columns = ['delivery_date', 'created_date', 'delivered_date', 'dispatched_date', 'sto_etd_date', 'oc_date']
        for col in date_columns:
            if col in excel_df.columns:
                excel_df[col] = pd.to_datetime(excel_df[col]).dt.strftime('%Y-%m-%d')
        
        # Drop internal calculation columns if they exist
        columns_to_drop = ['week_start', 'week_end', 'week_key', 'week', 'year', 'total_quantity']
        excel_df = excel_df.drop(columns=[col for col in columns_to_drop if col in excel_df.columns])
        
        # Remove duplicate columns before processing
        excel_df = excel_df.loc[:, ~excel_df.columns.duplicated()]
        
        # Select and order important columns for better readability - Updated with new fields
        important_columns = [
            'delivery_date',
            'delivery_timeline_status',
            'days_overdue',
            'dn_number',
            'customer',
            'customer_code',
            'recipient_company',
            'recipient_company_code',
            'recipient_contact',
            'recipient_address',
            'recipient_state_province',
            'recipient_country_name',
            'product_pn',
            'product_id',
            'pt_code',
            'package_size',
            'standard_quantity',
            'remaining_quantity_to_deliver',
            'product_total_remaining_demand',
            'delivery_demand_percentage',
            'product_gap_quantity',
            'product_fulfill_rate_percent',
            'fulfillment_status',
            'product_fulfillment_status',
            'shipment_status',
            'shipment_status_vn',
            'oc_number',
            'oc_line_id',
            'preferred_warehouse',
            'total_instock_at_preferred_warehouse',
            'total_instock_all_warehouses',
            'created_by_name',
            'is_epe_company'
        ]
        
        # Filter to only include columns that exist and are not duplicated
        available_columns = [col for col in important_columns if col in excel_df.columns]
        
        # Add any remaining columns not in the important list
        remaining_columns = [col for col in excel_df.columns if col not in available_columns]
        final_columns = available_columns + remaining_columns
        
        # Remove duplicates from final columns list
        final_columns = list(dict.fromkeys(final_columns))
        
        # Reorder dataframe
        excel_df = excel_df[final_columns]
        
        # Sort by delivery date and customer for better organization
        sort_columns = ['delivery_date', 'customer', 'dn_number', 'oc_line_id']
        sort_columns = [col for col in sort_columns if col in excel_df.columns]
        if sort_columns:
            excel_df = excel_df.sort_values(sort_columns)
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            try:
                # For Overdue Alerts, create different sheets
                if notification_type == "🚨 Overdue Alerts":
                    # Separate overdue and due today
                    overdue_df = excel_df[excel_df['delivery_timeline_status'] == 'Overdue'].copy()
                    due_today_df = excel_df[excel_df['delivery_timeline_status'] == 'Due Today'].copy()
                    
                    # Write overdue sheet
                    if not overdue_df.empty:
                        overdue_df = overdue_df.sort_values('days_overdue', ascending=False)
                        overdue_df.to_excel(writer, sheet_name='Overdue Deliveries', index=False)
                    
                    # Write due today sheet
                    if not due_today_df.empty:
                        due_today_df.to_excel(writer, sheet_name='Due Today', index=False)
                    
                    # Create summary sheet
                    summary_df = self._create_urgent_summary_sheet(delivery_df)
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
                else:
                    # Regular delivery schedule sheets
                    excel_df.to_excel(writer, sheet_name='Line Items Detail', index=False)
                    
                    # Create summary sheet
                    summary_df = self._create_summary_sheet(delivery_df)
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
                    
                    # Create product analysis sheet (only if columns exist)
                    if 'product_gap_quantity' in delivery_df.columns:
                        try:
                            product_analysis_df = self._create_product_analysis_sheet(delivery_df)
                            product_analysis_df.to_excel(writer, sheet_name='Product Analysis', index=False)
                        except Exception as e:
                            logger.warning(f"Could not create Product Analysis sheet: {e}")
                
                # Get workbook and apply formatting
                workbook = writer.book
                
                # Define formats
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#1f77b4' if notification_type == "📅 Delivery Schedule" else '#d32f2f',
                    'font_color': 'white',
                    'border': 1,
                    'text_wrap': True,
                    'valign': 'vcenter'
                })
                
                date_format = workbook.add_format({
                    'num_format': 'yyyy-mm-dd',
                    'border': 1
                })
                
                number_format = workbook.add_format({
                    'num_format': '#,##0',
                    'border': 1
                })
                
                percent_format = workbook.add_format({
                    'num_format': '0.0%',
                    'border': 1
                })
                
                urgent_format = workbook.add_format({
                    'bg_color': '#ffcccb',
                    'border': 1
                })
                
                overdue_format = workbook.add_format({
                    'bg_color': '#ffcccb',
                    'font_color': '#d32f2f',
                    'bold': True,
                    'border': 1
                })
                
                # Apply formatting to all sheets
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    
                    # Set column widths and formatting
                    worksheet.set_column(0, 50, 15)  # Default width
                    
                    # Freeze first row
                    worksheet.freeze_panes(1, 0)
                    
                    # Add filters
                    if sheet_name in ['Line Items Detail', 'Overdue Deliveries', 'Due Today']:
                        last_row = len(excel_df) if sheet_name == 'Line Items Detail' else len(overdue_df) + len(due_today_df)
                        last_col = len(final_columns) - 1
                        worksheet.autofilter(0, 0, last_row, last_col)
                
            except Exception as e:
                logger.error(f"Error creating Excel sheets: {e}")
                raise
        
        output.seek(0)
        return output
    
    def _create_urgent_summary_sheet(self, delivery_df):
        """Create summary sheet for urgent alerts (NEW)"""
        # Remove duplicate columns first
        delivery_df_clean = delivery_df.loc[:, ~delivery_df.columns.duplicated()]
        
        # Calculate summary by customer and status
        summary_data = []
        
        # Group by customer and timeline status
        for (customer, status), group_df in delivery_df_clean.groupby(['customer', 'delivery_timeline_status']):
            summary_data.append({
                'Customer': customer,
                'Status': status,
                'Deliveries': group_df['delivery_id'].nunique(),
                'Line Items': len(group_df),
                'Total Quantity': group_df['remaining_quantity_to_deliver'].sum(),
                'Max Days Overdue': group_df['days_overdue'].max() if status == 'Overdue' else 0,
                'Out of Stock Products': group_df[group_df['product_fulfillment_status'] == 'Out of Stock']['product_pn'].nunique()
            })
        
        summary_df = pd.DataFrame(summary_data)
        
        # Sort by status (Overdue first) and days overdue
        summary_df['Status_Sort'] = summary_df['Status'].map({'Overdue': 0, 'Due Today': 1})
        summary_df = summary_df.sort_values(['Status_Sort', 'Max Days Overdue'], ascending=[True, False])
        summary_df = summary_df.drop('Status_Sort', axis=1)
        
        return summary_df
    
    def _create_summary_sheet(self, delivery_df):
        """Create summary data for Excel"""
        # Remove duplicate columns first
        delivery_df_clean = delivery_df.loc[:, ~delivery_df.columns.duplicated()]
        
        # Direct grouping - no need to group twice
        agg_dict = {
            'dn_number': lambda x: ', '.join(x.unique()),
            'product_pn': lambda x: len(x.unique()),
            'standard_quantity': 'sum',
            'remaining_quantity_to_deliver': 'sum'
        }
        
        # Add conditional aggregations only if columns exist
        if 'fulfillment_status' in delivery_df_clean.columns:
            agg_dict['fulfillment_status'] = lambda x: 'Mixed' if x.nunique() > 1 else x.iloc[0]
        
        if 'delivery_timeline_status' in delivery_df_clean.columns:
            agg_dict['delivery_timeline_status'] = lambda x: x.iloc[0]
            
        if 'days_overdue' in delivery_df_clean.columns:
            agg_dict['days_overdue'] = 'max'
        
        summary = delivery_df_clean.groupby(['delivery_date', 'customer', 'recipient_company']).agg(agg_dict).reset_index()
        
        # Calculate line items count
        line_items = delivery_df_clean.groupby(['delivery_date', 'customer', 'recipient_company']).size().reset_index(name='line_items_count')
        
        # Merge line items count
        summary = summary.merge(line_items, on=['delivery_date', 'customer', 'recipient_company'])
        
        # Build columns list dynamically
        cols = ['delivery_date', 'customer', 'recipient_company', 'dn_number',
                'line_items_count', 'product_pn', 'standard_quantity', 
                'remaining_quantity_to_deliver']
        
        # Add optional columns only if they exist in summary
        if 'delivery_timeline_status' in summary.columns:
            cols.append('delivery_timeline_status')
        if 'days_overdue' in summary.columns:
            cols.append('days_overdue')
        if 'fulfillment_status' in summary.columns:
            cols.append('fulfillment_status')
        
        # Select only existing columns
        cols = [col for col in cols if col in summary.columns]
        summary = summary[cols]
        
        # Rename columns
        summary.columns = [col.replace('_', ' ').title() for col in summary.columns]
        
        # Sort by delivery date
        summary = summary.sort_values('Delivery Date')
        
        return summary
    
    def _create_product_analysis_sheet(self, delivery_df):
        """Create product analysis sheet for Excel"""
        # Remove duplicate columns first
        delivery_df_clean = delivery_df.loc[:, ~delivery_df.columns.duplicated()]
        
        # Check if product_id exists
        if 'product_id' not in delivery_df_clean.columns:
            return pd.DataFrame()  # Return empty if no product_id
        
        # Group by product for analysis
        product_analysis = delivery_df_clean.groupby(['product_id', 'pt_code', 'product_pn']).agg({
            'delivery_id': 'nunique',
            'remaining_quantity_to_deliver': 'sum',
            'product_total_remaining_demand': 'first',
            'total_instock_all_warehouses': 'first',
            'product_gap_quantity': 'first',
            'product_fulfill_rate_percent': 'first',
            'product_fulfillment_status': 'first'
        }).reset_index()
        
        # Rename columns
        product_analysis.columns = [
            'Product ID',
            'PT Code',
            'Product',
            'Active Deliveries',
            'This Sales Demand',
            'Total Product Demand',
            'Total Inventory',
            'Gap Quantity',
            'Fulfillment Rate %',
            'Fulfillment Status'
        ]
        
        # Sort by gap quantity (descending)
        product_analysis = product_analysis.sort_values('Gap Quantity', ascending=False)
        
        return product_analysis
    
    def send_delivery_schedule_email(self, recipient_email, sales_name, delivery_df, cc_emails=None, notification_type="📅 Delivery Schedule"):
        """Send delivery schedule email with enhanced content"""
        try:
            # Check email configuration
            if not self.sender_email or not self.sender_password:
                logger.error("Email configuration missing. Please set EMAIL_SENDER and EMAIL_PASSWORD.")
                return False, "Email configuration missing. Please check environment variables."
            
            # Debug: Check for duplicate columns
            logger.info(f"Columns in delivery_df: {delivery_df.columns.tolist()}")
            duplicate_cols = delivery_df.columns[delivery_df.columns.duplicated()].tolist()
            if duplicate_cols:
                logger.warning(f"Duplicate columns found: {duplicate_cols}")
                # Remove duplicates
                delivery_df = delivery_df.loc[:, ~delivery_df.columns.duplicated()]
            
            # Create message
            msg = MIMEMultipart('alternative')
            
            # Set subject based on notification type
            if notification_type == "🚨 Overdue Alerts":
                # Count overdue and due today
                overdue_count = delivery_df[delivery_df['delivery_timeline_status'] == 'Overdue']['delivery_id'].nunique()
                due_today_count = delivery_df[delivery_df['delivery_timeline_status'] == 'Due Today']['delivery_id'].nunique()
                msg['Subject'] = f"🚨 URGENT: {overdue_count} Overdue & {due_today_count} Due Today Deliveries - {sales_name}"
            else:
                msg['Subject'] = f"Delivery Schedule - Next 4 Weeks - {sales_name}"
            
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
            
            # Create HTML content based on notification type
            if notification_type == "🚨 Overdue Alerts":
                html_content = self.create_overdue_alerts_html(delivery_df, sales_name)
            else:
                html_content = self.create_delivery_schedule_html(delivery_df, sales_name)
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Create Excel attachment
            try:
                excel_data = self.create_excel_attachment(delivery_df, notification_type)
                excel_part = MIMEBase('application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                excel_part.set_payload(excel_data.read())
                encoders.encode_base64(excel_part)
                
                # Set filename based on notification type
                if notification_type == "🚨 Overdue Alerts":
                    filename = f"urgent_deliveries_{sales_name}_{datetime.now().strftime('%Y%m%d')}.xlsx"
                else:
                    filename = f"delivery_schedule_{sales_name}_{datetime.now().strftime('%Y%m%d')}.xlsx"
                
                excel_part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{filename}"'
                )
                msg.attach(excel_part)
            except Exception as e:
                logger.error(f"Error creating Excel attachment: {e}")
                # Continue without Excel attachment
                return False, f"Error creating Excel attachment: {str(e)}"
            
            # Create ICS calendar attachment (only for delivery schedule)
            if notification_type == "📅 Delivery Schedule":
                try:
                    calendar_gen = CalendarEventGenerator()
                    ics_content = calendar_gen.create_ics_content(sales_name, delivery_df, self.sender_email)
                    
                    if ics_content:  # Check if content was generated
                        ics_part = MIMEBase('text', 'calendar')
                        ics_part.set_payload(ics_content.encode('utf-8'))
                        encoders.encode_base64(ics_part)
                        ics_part.add_header(
                            'Content-Disposition',
                            f'attachment; filename="delivery_schedule_{sales_name}_{datetime.now().strftime("%Y%m%d")}.ics"'
                        )
                        msg.attach(ics_part)
                except Exception as e:
                    logger.warning(f"Error creating calendar attachment: {e}")
                    # Continue without calendar attachment
            
            # Send email
            logger.info(f"Attempting to send {notification_type} email to {recipient_email}...")
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                
                recipients = [recipient_email]
                if cc_emails:
                    recipients.extend(cc_emails)
                
                server.sendmail(self.sender_email, recipients, msg.as_string())
            
            logger.info(f"Email sent successfully to {recipient_email}")
            return True, "Email sent successfully"
            
        except smtplib.SMTPAuthenticationError:
            error_msg = "Email authentication failed. Please check your email credentials."
            logger.error(error_msg)
            return False, error_msg
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            logger.error(f"Error sending email: {e}", exc_info=True)
            return False, str(e)
    
    def send_bulk_delivery_schedules(self, sales_deliveries, progress_callback=None):
        """Send delivery schedules to multiple sales people"""
        results = []
        total = len(sales_deliveries)
        
        for idx, (sales_info, delivery_df) in enumerate(sales_deliveries):
            if progress_callback:
                progress_callback(idx + 1, total, f"Sending to {sales_info['name']}...")
            
            success, message = self.send_delivery_schedule_email(
                sales_info['email'],
                sales_info['name'],
                delivery_df
            )
            
            results.append({
                'sales': sales_info['name'],
                'email': sales_info['email'],
                'success': success,
                'message': message,
                'deliveries': len(delivery_df)
            })
        
        return results