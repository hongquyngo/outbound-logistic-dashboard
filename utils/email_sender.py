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

logger = logging.getLogger(__name__)

class EmailSender:
    """Handle email notifications for delivery schedules"""
    
    def __init__(self, smtp_host="smtp.gmail.com", smtp_port=587):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender_email = os.getenv("EMAIL_SENDER", "logistics@company.com")
        self.sender_password = os.getenv("EMAIL_PASSWORD", "")
    
    def create_delivery_schedule_html(self, delivery_df, sales_name):
        """Create HTML content for delivery schedule email"""
        
        # Group by week
        delivery_df['delivery_date'] = pd.to_datetime(delivery_df['delivery_date'])
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
                        <li>Total Deliveries: <strong>{len(delivery_df)}</strong></li>
                        <li>Total Quantity: <strong>{delivery_df['total_quantity'].sum():,.0f}</strong></li>
                        <li>Customers: <strong>{delivery_df['customer'].nunique()}</strong></li>
                    </ul>
                </div>
        """
        
        # Group by week and create sections
        for (year, week), week_df in delivery_df.groupby(['year', 'week']):
            week_start = datetime.strptime(f'{year}-W{week}-1', "%Y-W%W-%w").date()
            week_end = week_start + timedelta(days=6)
            
            html += f"""
                <div class="week-section">
                    <div class="week-header">
                        Week {week} ({week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')})
                    </div>
                    <table>
                        <tr>
                            <th>Date</th>
                            <th>Customer</th>
                            <th>Ship To</th>
                            <th>Location</th>
                            <th>Products</th>
                            <th>Quantity</th>
                            <th>Status</th>
                        </tr>
            """
            
            for _, row in week_df.iterrows():
                status_class = 'urgent' if row['fulfillment_status'] == 'Out of Stock' else ''
                location = f"{row['recipient_state_province']}, {row['recipient_country_name']}"
                
                html += f"""
                        <tr>
                            <td>{row['delivery_date'].strftime('%b %d')}</td>
                            <td>{row['customer']}</td>
                            <td>{row['recipient_company']}</td>
                            <td>{location}</td>
                            <td>{row['products'][:50]}...</td>
                            <td>{row['total_quantity']:,.0f}</td>
                            <td class="{status_class}">{row['fulfillment_status']}</td>
                        </tr>
                """
            
            html += """
                    </table>
                </div>
            """
        
        # Add warnings if any
        out_of_stock = delivery_df[delivery_df['fulfillment_status'] == 'Out of Stock']
        if len(out_of_stock) > 0:
            html += f"""
                <div class="warning">
                    <strong>⚠️ Attention Required:</strong><br>
                    {len(out_of_stock)} deliveries have inventory issues. Please coordinate with warehouse team.
                </div>
            """
        
        # Add calendar buttons
        calendar_gen = CalendarEventGenerator()
        google_cal_link = calendar_gen.create_google_calendar_link(sales_name, delivery_df)
        outlook_cal_link = calendar_gen.create_outlook_calendar_link(sales_name, delivery_df)
        
        html += f"""
            <div style="text-align: center; margin: 30px 0;">
                <h3>📅 Add to Your Calendar</h3>
                <p style="margin-bottom: 20px;">Click below to add this delivery schedule to your calendar:</p>
                <a href="{google_cal_link}" 
                   style="display: inline-block; background-color: #4285f4; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 5px; margin: 0 10px; font-weight: bold;">
                    📅 Add to Google Calendar
                </a>
                <a href="{outlook_cal_link}" 
                   style="display: inline-block; background-color: #0078d4; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 5px; margin: 0 10px; font-weight: bold;">
                    📅 Add to Outlook Calendar
                </a>
                <p style="margin-top: 15px; font-size: 12px; color: #666;">
                    Or download the attached .ics file to import into any calendar application
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
        """Create Excel file as attachment"""
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Write main data
            delivery_df.to_excel(writer, sheet_name='Delivery Schedule', index=False)
            
            # Get worksheet
            workbook = writer.book
            worksheet = writer.sheets['Delivery Schedule']
            
            # Format
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#1f77b4',
                'font_color': 'white',
                'border': 1
            })
            
            # Apply header format
            for col_num, value in enumerate(delivery_df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Auto-adjust columns width
            for column in delivery_df:
                column_width = max(delivery_df[column].astype(str).map(len).max(), len(column))
                col_idx = delivery_df.columns.get_loc(column)
                worksheet.set_column(col_idx, col_idx, column_width + 2)
        
        output.seek(0)
        return output
    
    def send_delivery_schedule_email(self, recipient_email, sales_name, delivery_df, cc_emails=None):
        """Send delivery schedule email"""
        try:
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
            ics_part = MIMEBase('text', 'calendar')
            ics_part.set_payload(ics_content.encode('utf-8'))
            encoders.encode_base64(ics_part)
            ics_part.add_header(
                'Content-Disposition',
                f'attachment; filename="delivery_schedule_{sales_name}_{datetime.now().strftime("%Y%m%d")}.ics"'
            )
            msg.attach(ics_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                
                recipients = [recipient_email]
                if cc_emails:
                    recipients.extend(cc_emails)
                
                server.sendmail(self.sender_email, recipients, msg.as_string())
            
            logger.info(f"Email sent successfully to {recipient_email}")
            return True, "Email sent successfully"
            
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