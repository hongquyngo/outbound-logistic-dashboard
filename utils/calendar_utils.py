# utils/calendar_utils.py - Calendar event generator for delivery schedules

from datetime import datetime, timedelta
import uuid
import pandas as pd
import urllib.parse


class CalendarEventGenerator:
    """Generate iCalendar (.ics) files for delivery schedules with enhanced information"""
    
    @staticmethod
    def create_ics_content(sales_name, delivery_df, organizer_email):
        """Create ICS content with multiple events - one for each delivery date"""
        
        # ICS header
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Outbound Logistics//Delivery Schedule//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
"""
        
        # Group deliveries by date
        delivery_df['delivery_date'] = pd.to_datetime(delivery_df['delivery_date'])
        grouped = delivery_df.groupby('delivery_date')
        
        # Create an event for each delivery date
        for delivery_date, date_df in grouped:
            # Generate unique ID for each event
            uid = str(uuid.uuid4())
            
            # Current timestamp
            now = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            
            # Set event time: 8:30 AM - 5:30 PM local time
            # Convert to UTC (assuming Vietnam timezone GMT+7)
            start_datetime = delivery_date.replace(hour=8, minute=30) - timedelta(hours=7)
            end_datetime = delivery_date.replace(hour=17, minute=30) - timedelta(hours=7)
            
            # Format for ICS
            dtstart = start_datetime.strftime('%Y%m%dT%H%M%SZ')
            dtend = end_datetime.strftime('%Y%m%dT%H%M%SZ')
            
            # Create summary and description for this date with enhanced info
            # Aggregate quantities by product for accurate totals
            products_agg = date_df.groupby('product_pn').agg({
                'remaining_quantity_to_deliver': 'sum'
            }).reset_index()
            
            total_deliveries = len(date_df.groupby(['customer', 'recipient_company'])) if isinstance(date_df, pd.DataFrame) else 1
            total_line_items = len(date_df)
            total_quantity = date_df['remaining_quantity_to_deliver'].sum()
            
            # Check for overdue or critical items
            overdue_count = 0
            out_of_stock_count = 0
            if 'delivery_timeline_status' in date_df.columns:
                overdue_count = date_df[date_df['delivery_timeline_status'] == 'Overdue']['delivery_id'].nunique()
            if 'product_fulfillment_status' in date_df.columns:
                out_of_stock_count = date_df[date_df['product_fulfillment_status'] == 'Out of Stock']['product_pn'].nunique()
            
            # Add status indicator to summary
            status_indicator = ""
            if overdue_count > 0:
                status_indicator = " ⚠️"
            
            summary = f"📦 Deliveries ({total_deliveries}){status_indicator} - {delivery_date.strftime('%b %d')}"
            
            description = f"Delivery Schedule for {delivery_date.strftime('%B %d, %Y')}\\n\\n"
            description += f"Total Deliveries: {total_deliveries}\\n"
            description += f"Total Line Items: {total_line_items}\\n"
            description += f"Total Remaining Quantity: {total_quantity:,.0f}\\n"
            
            if overdue_count > 0:
                description += f"⚠️ OVERDUE: {overdue_count} deliveries\\n"
            if out_of_stock_count > 0:
                description += f"❌ OUT OF STOCK: {out_of_stock_count} products\\n"
                
            description += "\\nDELIVERIES:\\n"
            
            # Group by customer and recipient for description
            for (customer, recipient), cust_df in date_df.groupby(['customer', 'recipient_company']):
                description += f"\\n• {customer} → {recipient}\\n"
                location = f"{cust_df.iloc[0]['recipient_state_province']}, {cust_df.iloc[0]['recipient_country_name']}"
                description += f"  Location: {location}\\n"
                
                # Check timeline status if available
                if 'delivery_timeline_status' in cust_df.columns:
                    timeline_status = cust_df['delivery_timeline_status'].iloc[0]
                    if timeline_status == 'Overdue' and 'days_overdue' in cust_df.columns:
                        days_overdue = cust_df['days_overdue'].iloc[0]
                        description += f"  ⚠️ OVERDUE by {days_overdue} days\\n"
                
                # Aggregate products and quantities
                prod_summary = cust_df.groupby('product_pn').agg({
                    'remaining_quantity_to_deliver': 'sum',
                    'product_fulfillment_status': lambda x: x.iloc[0] if 'product_fulfillment_status' in cust_df.columns else 'Unknown'
                })
                
                for prod, data in prod_summary.iterrows():
                    qty = data['remaining_quantity_to_deliver']
                    status_icon = ""
                    if 'product_fulfillment_status' in data:
                        if data['product_fulfillment_status'] == 'Out of Stock':
                            status_icon = " ❌"
                        elif data['product_fulfillment_status'] == 'Can Fulfill Partial':
                            status_icon = " ⚠️"
                    description += f"  - {prod}: {qty:,.0f} units{status_icon}\\n"
                
                # Add fulfillment status
                if 'fulfillment_status' in cust_df.columns:
                    status = cust_df['fulfillment_status'].unique()
                    if len(status) > 1:
                        description += f"  Status: Mixed\\n"
                    else:
                        description += f"  Status: {status[0]}\\n"
            
            # Get locations for this date
            locations = date_df.apply(lambda x: f"{x['recipient_state_province']}, {x['recipient_country_name']}", axis=1).unique()
            location_str = "; ".join(locations[:3])  # Limit to first 3 locations
            if len(locations) > 3:
                location_str += f" and {len(locations)-3} more"
            
            # Set alarm earlier for overdue items
            alarm_minutes = 30 if overdue_count > 0 else 15
            
            # Add event to ICS
            ics_content += f"""BEGIN:VEVENT
UID:{uid}@outbound.prostech.vn
DTSTAMP:{now}
ORGANIZER;CN=Outbound Logistics:mailto:{organizer_email}
DTSTART:{dtstart}
DTEND:{dtend}
SUMMARY:{summary}
DESCRIPTION:{description}
LOCATION:{location_str}
STATUS:CONFIRMED
SEQUENCE:0
TRANSP:OPAQUE
BEGIN:VALARM
TRIGGER:-PT{alarm_minutes}M
ACTION:DISPLAY
DESCRIPTION:Delivery reminder - Check today's deliveries{' (OVERDUE ITEMS!)' if overdue_count > 0 else ''}
END:VALARM
END:VEVENT
"""
        
        # ICS footer
        ics_content += "END:VCALENDAR"
        
        return ics_content
    
    @staticmethod
    def create_google_calendar_links(sales_name, delivery_df):
        """Create Google Calendar event links for each delivery date with enhanced info"""
        links = []
        
        # Group deliveries by date
        delivery_df['delivery_date'] = pd.to_datetime(delivery_df['delivery_date'])
        grouped = delivery_df.groupby('delivery_date')
        
        for delivery_date, date_df in grouped:
            # Format date and time for Google Calendar (Vietnam timezone)
            # Start: 8:30 AM, End: 5:30 PM
            start_dt = delivery_date.replace(hour=8, minute=30)
            end_dt = delivery_date.replace(hour=17, minute=30)
            
            # Format: YYYYMMDDTHHmmSS/YYYYMMDDTHHmmSS
            dates = f"{start_dt.strftime('%Y%m%dT%H%M%S')}/{end_dt.strftime('%Y%m%dT%H%M%S')}"
            
            # Create title and details with enhanced information
            # Aggregate quantities by product for accurate totals
            products_agg = date_df.groupby('product_pn').agg({
                'remaining_quantity_to_deliver': 'sum'
            }).reset_index()
            
            total_deliveries = len(date_df.groupby(['customer', 'recipient_company'])) if isinstance(date_df, pd.DataFrame) else 1
            total_line_items = len(date_df)
            total_quantity = date_df['remaining_quantity_to_deliver'].sum()
            
            # Check for critical items
            overdue_count = 0
            out_of_stock_count = 0
            if 'delivery_timeline_status' in date_df.columns:
                overdue_count = date_df[date_df['delivery_timeline_status'] == 'Overdue']['delivery_id'].nunique()
            if 'product_fulfillment_status' in date_df.columns:
                out_of_stock_count = date_df[date_df['product_fulfillment_status'] == 'Out of Stock']['product_pn'].nunique()
            
            # Add status indicator
            status_indicator = ""
            if overdue_count > 0:
                status_indicator = " ⚠️ URGENT"
            
            title = f"📦 Deliveries ({total_deliveries}){status_indicator} - {delivery_date.strftime('%b %d')}"
            
            details = f"Delivery Schedule for {delivery_date.strftime('%B %d, %Y')}\n\n"
            details += f"Total Deliveries: {total_deliveries}\n"
            details += f"Total Line Items: {total_line_items}\n"
            details += f"Total Remaining Quantity: {total_quantity:,.0f}\n"
            
            # Add alerts
            if overdue_count > 0:
                details += f"\n⚠️ ALERT: {overdue_count} OVERDUE deliveries!\n"
            if out_of_stock_count > 0:
                details += f"❌ WARNING: {out_of_stock_count} products OUT OF STOCK\n"
            
            details += "\nDELIVERIES:\n"
            
            # Group by customer and recipient for details
            for (customer, recipient), cust_df in date_df.groupby(['customer', 'recipient_company']):
                details += f"\n• {customer} → {recipient}\n"
                location = f"{cust_df.iloc[0]['recipient_state_province']}, {cust_df.iloc[0]['recipient_country_name']}"
                details += f"  📍 {location}\n"
                
                # Add timeline status
                if 'delivery_timeline_status' in cust_df.columns:
                    timeline_status = cust_df['delivery_timeline_status'].iloc[0]
                    if timeline_status == 'Overdue' and 'days_overdue' in cust_df.columns:
                        days_overdue = cust_df['days_overdue'].iloc[0]
                        details += f"  ⚠️ OVERDUE by {days_overdue} days\n"
                
                # Aggregate products and quantities with status
                if 'product_fulfillment_status' in cust_df.columns:
                    prod_summary = cust_df.groupby(['product_pn', 'product_fulfillment_status'])['remaining_quantity_to_deliver'].sum()
                    for (prod, status), qty in prod_summary.items():
                        status_icon = ""
                        if status == 'Out of Stock':
                            status_icon = " ❌"
                        elif status == 'Can Fulfill Partial':
                            status_icon = " ⚠️"
                        details += f"  📦 {prod}: {qty:,.0f} units{status_icon}\n"
                else:
                    prod_summary = cust_df.groupby('product_pn')['remaining_quantity_to_deliver'].sum()
                    for prod, qty in prod_summary.items():
                        details += f"  📦 {prod}: {qty:,.0f} units\n"
            
            # Get locations
            locations = date_df.apply(lambda x: f"{x['recipient_state_province']}, {x['recipient_country_name']}", axis=1).unique()
            location_str = "; ".join(locations[:3])
            if len(locations) > 3:
                location_str += f" +{len(locations)-3} more"
            
            # URL encode the parameters
            params = {
                'action': 'TEMPLATE',
                'text': title,
                'dates': dates,
                'details': details,
                'location': location_str,
                'sf': 'true'
            }
            
            base_url = 'https://calendar.google.com/calendar/render'
            link = f"{base_url}?{urllib.parse.urlencode(params)}"
            
            links.append({
                'date': delivery_date,
                'link': link,
                'count': total_deliveries,
                'is_urgent': overdue_count > 0 or out_of_stock_count > 0
            })
        
        return links
    
    @staticmethod
    def create_google_calendar_link(sales_name, delivery_df):
        """Create a single Google Calendar link for the first delivery date (backward compatibility)"""
        links = CalendarEventGenerator.create_google_calendar_links(sales_name, delivery_df)
        return links[0]['link'] if links else "#"
    
    @staticmethod
    def create_outlook_calendar_links(sales_name, delivery_df):
        """Create Outlook/Office 365 calendar event links for each delivery date with enhanced info"""
        links = []
        
        # Group deliveries by date
        delivery_df['delivery_date'] = pd.to_datetime(delivery_df['delivery_date'])
        grouped = delivery_df.groupby('delivery_date')
        
        for delivery_date, date_df in grouped:
            # Format date and time for Outlook
            # Start: 8:30 AM, End: 5:30 PM
            start_dt = delivery_date.replace(hour=8, minute=30)
            end_dt = delivery_date.replace(hour=17, minute=30)
            
            # Format for Outlook (ISO format)
            startdt = start_dt.strftime('%Y-%m-%dT%H:%M:%S')
            enddt = end_dt.strftime('%Y-%m-%dT%H:%M:%S')
            
            # Create title and body with enhanced information
            # Aggregate quantities by product for accurate totals
            products_agg = date_df.groupby('product_pn').agg({
                'remaining_quantity_to_deliver': 'sum'
            }).reset_index()
            
            total_deliveries = len(date_df.groupby(['customer', 'recipient_company'])) if isinstance(date_df, pd.DataFrame) else 1
            total_line_items = len(date_df)
            total_quantity = date_df['remaining_quantity_to_deliver'].sum()
            
            # Check for critical items
            overdue_count = 0
            out_of_stock_count = 0
            if 'delivery_timeline_status' in date_df.columns:
                overdue_count = date_df[date_df['delivery_timeline_status'] == 'Overdue']['delivery_id'].nunique()
            if 'product_fulfillment_status' in date_df.columns:
                out_of_stock_count = date_df[date_df['product_fulfillment_status'] == 'Out of Stock']['product_pn'].nunique()
            
            # Add status indicator
            status_indicator = ""
            if overdue_count > 0:
                status_indicator = " ⚠️ URGENT"
            
            subject = f"📦 Deliveries ({total_deliveries}){status_indicator} - {delivery_date.strftime('%b %d')}"
            
            body = f"Delivery Schedule for {delivery_date.strftime('%B %d, %Y')}<br><br>"
            body += f"Total Deliveries: {total_deliveries}<br>"
            body += f"Total Line Items: {total_line_items}<br>"
            body += f"Total Remaining Quantity: {total_quantity:,.0f}<br>"
            
            # Add alerts
            if overdue_count > 0:
                body += f"<br><strong style='color:red'>⚠️ ALERT: {overdue_count} OVERDUE deliveries!</strong><br>"
            if out_of_stock_count > 0:
                body += f"<strong style='color:red'>❌ WARNING: {out_of_stock_count} products OUT OF STOCK</strong><br>"
            
            body += "<br>DELIVERIES:<br>"
            
            # Group by customer and recipient for body
            for (customer, recipient), cust_df in date_df.groupby(['customer', 'recipient_company']):
                body += f"<br>• {customer} → {recipient}<br>"
                location = f"{cust_df.iloc[0]['recipient_state_province']}, {cust_df.iloc[0]['recipient_country_name']}"
                body += f"  📍 {location}<br>"
                
                # Add timeline status
                if 'delivery_timeline_status' in cust_df.columns:
                    timeline_status = cust_df['delivery_timeline_status'].iloc[0]
                    if timeline_status == 'Overdue' and 'days_overdue' in cust_df.columns:
                        days_overdue = cust_df['days_overdue'].iloc[0]
                        body += f"  <strong style='color:red'>⚠️ OVERDUE by {days_overdue} days</strong><br>"
                
                # Aggregate products and quantities with status
                if 'product_fulfillment_status' in cust_df.columns:
                    prod_summary = cust_df.groupby(['product_pn', 'product_fulfillment_status'])['remaining_quantity_to_deliver'].sum()
                    for (prod, status), qty in prod_summary.items():
                        status_style = ""
                        if status == 'Out of Stock':
                            status_style = " style='color:red'"
                        elif status == 'Can Fulfill Partial':
                            status_style = " style='color:orange'"
                        body += f"  📦 <span{status_style}>{prod}: {qty:,.0f} units</span><br>"
                else:
                    prod_summary = cust_df.groupby('product_pn')['remaining_quantity_to_deliver'].sum()
                    for prod, qty in prod_summary.items():
                        body += f"  📦 {prod}: {qty:,.0f} units<br>"
            
            # Get locations
            locations = date_df.apply(lambda x: f"{x['recipient_state_province']}, {x['recipient_country_name']}", axis=1).unique()
            location_str = "; ".join(locations[:3])
            if len(locations) > 3:
                location_str += f" +{len(locations)-3} more"
            
            # URL encode the parameters
            params = {
                'subject': subject,
                'startdt': startdt,
                'enddt': enddt,
                'body': body,
                'location': location_str
            }
            
            base_url = 'https://outlook.live.com/calendar/0/deeplink/compose'
            link = f"{base_url}?{urllib.parse.urlencode(params)}"
            
            links.append({
                'date': delivery_date,
                'link': link,
                'count': total_deliveries,
                'is_urgent': overdue_count > 0 or out_of_stock_count > 0
            })
        
        return links
    
    @staticmethod
    def create_outlook_calendar_link(sales_name, delivery_df):
        """Create a single Outlook calendar link for the first delivery date (backward compatibility)"""
        links = CalendarEventGenerator.create_outlook_calendar_links(sales_name, delivery_df)
        return links[0]['link'] if links else "#"
    
    @staticmethod
    def create_urgent_delivery_reminder(delivery_df, recipient_email):
        """Create special ICS for urgent/overdue deliveries only"""
        # Filter only urgent deliveries
        urgent_df = delivery_df[
            (delivery_df.get('delivery_timeline_status') == 'Overdue') |
            (delivery_df.get('product_fulfillment_status').isin(['Out of Stock', 'Can Fulfill Partial']))
        ] if 'delivery_timeline_status' in delivery_df.columns else pd.DataFrame()
        
        if urgent_df.empty:
            return None
        
        # ICS header
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Outbound Logistics//URGENT Delivery Alert//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
"""
        
        # Create a single urgent event for today
        uid = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Set event for today at 9 AM - 10 AM local time
        today = datetime.now().date()
        start_datetime = datetime.combine(today, datetime.min.time()).replace(hour=9, minute=0) - timedelta(hours=7)
        end_datetime = start_datetime + timedelta(hours=1)
        
        dtstart = start_datetime.strftime('%Y%m%dT%H%M%SZ')
        dtend = end_datetime.strftime('%Y%m%dT%H%M%SZ')
        dtstamp = now.strftime('%Y%m%dT%H%M%SZ')
        
        # Count urgent items
        overdue_deliveries = urgent_df[urgent_df.get('delivery_timeline_status') == 'Overdue']['delivery_id'].nunique() if 'delivery_timeline_status' in urgent_df.columns else 0
        out_of_stock_products = urgent_df[urgent_df.get('product_fulfillment_status') == 'Out of Stock']['product_pn'].nunique() if 'product_fulfillment_status' in urgent_df.columns else 0
        
        summary = f"🚨 URGENT: {overdue_deliveries} Overdue Deliveries, {out_of_stock_products} Out of Stock"
        
        description = "URGENT DELIVERY ISSUES REQUIRING IMMEDIATE ATTENTION\\n\\n"
        description += f"Overdue Deliveries: {overdue_deliveries}\\n"
        description += f"Out of Stock Products: {out_of_stock_products}\\n\\n"
        
        # List overdue deliveries
        if overdue_deliveries > 0:
            description += "OVERDUE DELIVERIES:\\n"
            overdue_df = urgent_df[urgent_df.get('delivery_timeline_status') == 'Overdue']
            for _, row in overdue_df.iterrows():
                description += f"- {row['customer']} ({row['days_overdue']} days overdue)\\n"
        
        # Add event
        ics_content += f"""BEGIN:VEVENT
UID:{uid}@urgent.outbound.prostech.vn
DTSTAMP:{dtstamp}
ORGANIZER;CN=Outbound Logistics URGENT:mailto:{recipient_email}
DTSTART:{dtstart}
DTEND:{dtend}
SUMMARY:{summary}
DESCRIPTION:{description}
LOCATION:Logistics Office
STATUS:CONFIRMED
PRIORITY:1
SEQUENCE:0
TRANSP:OPAQUE
BEGIN:VALARM
TRIGGER:-PT30M
ACTION:DISPLAY
DESCRIPTION:URGENT delivery issues need your immediate attention!
END:VALARM
BEGIN:VALARM
TRIGGER:-PT15M
ACTION:DISPLAY
DESCRIPTION:URGENT delivery issues - action required NOW!
END:VALARM
END:VEVENT
"""
        
        ics_content += "END:VCALENDAR"
        
        return ics_content