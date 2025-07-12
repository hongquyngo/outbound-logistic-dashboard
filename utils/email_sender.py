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
        self.sender_email = EMAIL_SENDER or os.getenv("EMAIL_SENDER", "logistics@company.com")
        self.sender_password = EMAIL_PASSWORD or os.getenv("EMAIL_PASSWORD", "")
        
        # Log configuration
        logger.info(f"Email sender initialized with: {self.sender_email} via {self.smtp_host}:{self.smtp_port}")
    
    def create_delivery_schedule_html(self, delivery_df, sales_name):
        """Create HTML content for delivery schedule email"""
        
        # Group by week - Fixed week calculation
        delivery_df['delivery_date'] = pd.to_datetime(delivery_df['delivery_date'])
        
        # Calculate week start (Monday) for each delivery date
        delivery_df['week_start'] = delivery_df['delivery_date'] - pd.to_timedelta(delivery_df['delivery_date'].dt.dayofweek, unit='D')
        delivery_df['week_end'] = delivery_df['week_start'] + timedelta(days=6)
        delivery_df['week_key'] = delivery_df['week_start'].dt.strftime('%Y-%m-%d')
        
        # Calculate ISO week number for display
        delivery_df['week'] = delivery_df['delivery_date'].dt.isocalendar().week
        delivery_df['year'] = delivery_df['delivery_date'].dt.year
        
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
                    <ul>
                        <li>Total Deliveries: <strong>{delivery_df.groupby(['delivery_date', 'customer', 'recipient_company']).ngroups}</strong></li>
                        <li>Total Product Types: <strong>{delivery_df['product_pn'].nunique()}</strong></li>
                        <li>Total Line Items: <strong>{len(delivery_df)}</strong></li>
                        <li>Total Remaining Quantity: <strong>{delivery_df['remaining_quantity_to_deliver'].sum():,.0f}</strong></li>
                        <li>Customers: <strong>{delivery_df['customer'].nunique()}</strong></li>
                    </ul>
                </div>
        """
        
        # Group by week and create sections
        for week_key, week_df in delivery_df.groupby('week_key', sort=True):
            week_start = week_df['week_start'].iloc[0]
            week_end = week_df['week_end'].iloc[0]
            week_number = week_df['week'].iloc[0]
            
            # Calculate totals for this week - count unique delivery/customer combinations
            # but show actual product lines after grouping
            week_unique_deliveries = week_df.groupby(['delivery_date', 'customer', 'recipient_company']).ngroups
            week_unique_products = week_df.groupby(['delivery_date', 'customer', 'recipient_company', 'product_pn']).ngroups
            week_line_items = len(week_df)  # Original line items count
            week_total_qty = week_df['remaining_quantity_to_deliver'].sum()
            
            html += f"""
                <div class="week-section">
                    <div class="week-header">
                        Week {week_number} ({week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')})
                        <span style="float: right; font-size: 14px;">
                            {week_unique_deliveries} deliveries | {week_unique_products} products | {week_line_items} line items | {week_total_qty:,.0f} units
                        </span>
                    </div>
                    <table>
                        <tr>
                            <th style="width: 80px;">Date</th>
                            <th style="width: 200px;">Customer</th>
                            <th style="width: 200px;">Ship To</th>
                            <th style="width: 150px;">Location</th>
                            <th style="width: 150px;">Product</th>
                            <th style="width: 100px;">Remaining Qty</th>
                            <th style="width: 100px;">Status</th>
                        </tr>
            """
            
            # Group by date, customer, recipient, and PRODUCT for display
            # This will show each product on its own row with aggregated quantity
            display_group = week_df.groupby(['delivery_date', 'customer', 'recipient_company', 
                                           'recipient_state_province', 'recipient_country_name', 
                                           'product_pn']).agg({
                'remaining_quantity_to_deliver': 'sum',
                'fulfillment_status': lambda x: 'Mixed' if x.nunique() > 1 else x.iloc[0]
            }).reset_index()
            
            # Sort by date and product
            display_group = display_group.sort_values(['delivery_date', 'product_pn'])
            
            # Add rows to table
            for _, row in display_group.iterrows():
                location = f"{row['recipient_state_province']}, {row['recipient_country_name']}"
                status_class = 'urgent' if row['fulfillment_status'] == 'Out of Stock' else ''
                
                html += f"""
                        <tr>
                            <td>{row['delivery_date'].strftime('%b %d')}</td>
                            <td>{row['customer']}</td>
                            <td>{row['recipient_company']}</td>
                            <td>{location}</td>
                            <td>{row['product_pn']}</td>
                            <td>{row['remaining_quantity_to_deliver']:,.0f}</td>
                            <td class="{status_class}">{row['fulfillment_status']}</td>
                        </tr>
                """
            
            html += """
                    </table>
                </div>
            """
        
        # Add warnings if any
        if 'fulfillment_status' in delivery_df.columns:
            out_of_stock = delivery_df[delivery_df['fulfillment_status'] == 'Out of Stock']
            if len(out_of_stock) > 0:
                # Count unique deliveries with out of stock
                out_of_stock_deliveries = out_of_stock.groupby(['delivery_date', 'customer', 'recipient_company']).ngroups
                html += f"""
                    <div class="warning">
                        <strong>⚠️ Attention Required:</strong><br>
                        {out_of_stock_deliveries} deliveries have inventory issues ({len(out_of_stock)} line items). 
                        Please coordinate with outbound team.
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
                <p>For questions, please contact: <a href="mailto:logistics@company.com">logistics@company.com</a></p>
            </div>
        </div>
        </body>
        </html>
        """
        
        return html
    
    def create_excel_attachment(self, delivery_df):
        """Create Excel file as attachment with detailed line items"""
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
        
        # Select and order important columns for better readability
        important_columns = [
            'delivery_date',
            'dn_number',
            'customer',
            'customer_code',
            'recipient_company',
            'recipient_company_code',
            'recipient_contact',
            'recipient_address',
            'recipient_state_province',
            'recipient_country_name',
            'product_pn',  # Individual product code
            'product_id',
            'pt_code',
            'package_size',
            'standard_quantity',  # Original order quantity
            'remaining_quantity_to_deliver',  # Actual quantity to deliver
            'gap_quantity',
            'fulfillment_status',
            'shipment_status',
            'oc_number',
            'oc_line_id',
            'preferred_warehouse',
            'total_instock_at_preferred_warehouse',
            'created_by_name',
            'is_epe_company'
        ]
        
        # Filter to only include columns that exist
        available_columns = [col for col in important_columns if col in excel_df.columns]
        
        # Add any remaining columns not in the important list
        remaining_columns = [col for col in excel_df.columns if col not in available_columns]
        final_columns = available_columns + remaining_columns
        
        # Reorder dataframe
        excel_df = excel_df[final_columns]
        
        # Sort by delivery date and customer for better organization
        sort_columns = ['delivery_date', 'customer', 'dn_number', 'oc_line_id']
        sort_columns = [col for col in sort_columns if col in excel_df.columns]
        if sort_columns:
            excel_df = excel_df.sort_values(sort_columns)
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Write main data sheet with line items
            excel_df.to_excel(writer, sheet_name='Line Items Detail', index=False)
            
            # Create summary sheet
            summary_df = self._create_summary_sheet(delivery_df)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Get workbook and worksheets
            workbook = writer.book
            detail_worksheet = writer.sheets['Line Items Detail']
            summary_worksheet = writer.sheets['Summary']
            
            # Define formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#1f77b4',
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
            
            urgent_format = workbook.add_format({
                'bg_color': '#ffcccb',
                'border': 1
            })
            
            epe_format = workbook.add_format({
                'bg_color': '#e3f2fd',
                'font_color': '#1976d2',
                'bold': True,
                'border': 1
            })
            
            # Format Line Items Detail sheet
            # Apply header format
            for col_num, value in enumerate(excel_df.columns.values):
                detail_worksheet.write(0, col_num, value, header_format)
            
            # Set column widths and apply formatting
            for idx, column in enumerate(excel_df.columns):
                # Calculate column width
                max_len = max(
                    excel_df[column].astype(str).map(len).max(),
                    len(column)
                ) + 2
                
                # Set specific widths for certain columns
                if column == 'recipient_address':
                    max_len = min(max_len, 40)
                elif column in ['product_pn', 'product_id']:
                    max_len = min(max_len, 25)
                else:
                    max_len = min(max_len, 20)
                
                detail_worksheet.set_column(idx, idx, max_len)
                
                # Apply number format to quantity columns
                if 'quantity' in column.lower() or column in ['standard_quantity', 'remaining_quantity_to_deliver', 'gap_quantity']:
                    detail_worksheet.set_column(idx, idx, max_len, number_format)
            
            # Apply conditional formatting for urgent items
            if 'fulfillment_status' in excel_df.columns:
                status_col = excel_df.columns.get_loc('fulfillment_status')
                for row_num in range(1, len(excel_df) + 1):
                    if excel_df.iloc[row_num - 1]['fulfillment_status'] == 'Out of Stock':
                        detail_worksheet.set_row(row_num, None, urgent_format)
            
            # Highlight EPE companies
            if 'is_epe_company' in excel_df.columns:
                epe_col = excel_df.columns.get_loc('is_epe_company')
                for row_num in range(1, len(excel_df) + 1):
                    if excel_df.iloc[row_num - 1]['is_epe_company'] == 'Yes':
                        detail_worksheet.write(row_num, epe_col, 'Yes', epe_format)
            
            # Add filters
            detail_worksheet.autofilter(0, 0, len(excel_df), len(excel_df.columns) - 1)
            
            # Freeze panes (freeze first row and first 3 columns)
            detail_worksheet.freeze_panes(1, 3)
            
            # Format Summary sheet
            for col_num, value in enumerate(summary_df.columns.values):
                summary_worksheet.write(0, col_num, value, header_format)
            
            # Auto-adjust summary columns
            for idx, column in enumerate(summary_df.columns):
                max_len = max(
                    summary_df[column].astype(str).map(len).max(),
                    len(column)
                ) + 2
                summary_worksheet.set_column(idx, idx, min(max_len, 30))
        
        output.seek(0)
        return output
    
    def _create_summary_sheet(self, delivery_df):
        """Create summary data for Excel"""
        # Direct grouping - no need to group twice
        summary = delivery_df.groupby(['delivery_date', 'customer', 'recipient_company']).agg({
            'dn_number': lambda x: ', '.join(x.unique()),
            'product_pn': lambda x: len(x.unique()),  # Count of unique products
            'standard_quantity': 'sum',  # Total ordered quantity
            'remaining_quantity_to_deliver': 'sum',  # Total remaining quantity
            'fulfillment_status': lambda x: 'Mixed' if x.nunique() > 1 else x.iloc[0]
        }).reset_index()
        
        # Calculate line items count
        line_items = delivery_df.groupby(['delivery_date', 'customer', 'recipient_company']).size().reset_index(name='line_items_count')
        
        # Merge line items count
        summary = summary.merge(line_items, on=['delivery_date', 'customer', 'recipient_company'])
        
        # Rename and reorder columns
        summary = summary[[
            'delivery_date', 'customer', 'recipient_company', 'dn_number',
            'line_items_count', 'product_pn', 'standard_quantity', 
            'remaining_quantity_to_deliver', 'fulfillment_status'
        ]]
        
        summary.columns = [
            'Delivery Date',
            'Customer', 
            'Ship To',
            'DN Numbers',
            'Line Items',
            'Product Types',
            'Order Quantity',
            'Remaining Quantity',
            'Fulfillment Status'
        ]
        
        # Sort by delivery date
        summary = summary.sort_values('Delivery Date')
        
        return summary
    
    def send_delivery_schedule_email(self, recipient_email, sales_name, delivery_df, cc_emails=None):
        """Send delivery schedule email"""
        try:
            # Check email configuration
            if not self.sender_email or not self.sender_password:
                logger.error("Email configuration missing. Please set EMAIL_SENDER and EMAIL_PASSWORD.")
                return False, "Email configuration missing. Please check environment variables."
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Delivery Schedule - Next 4 Weeks - {sales_name}"
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
            
            # Create HTML content
            html_content = self.create_delivery_schedule_html(delivery_df, sales_name)
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Create Excel attachment
            excel_data = self.create_excel_attachment(delivery_df)
            excel_part = MIMEBase('application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            excel_part.set_payload(excel_data.read())
            encoders.encode_base64(excel_part)
            excel_part.add_header(
                'Content-Disposition',
                f'attachment; filename="delivery_schedule_{sales_name}_{datetime.now().strftime("%Y%m%d")}.xlsx"'
            )
            msg.attach(excel_part)
            
            # Create ICS calendar attachment
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
            
            # Send email
            logger.info(f"Attempting to send email to {recipient_email}...")
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
            logger.error(f"Error sending email: {e}")
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