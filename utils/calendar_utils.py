# utils/calendar_utils.py - Calendar event generator for delivery schedules

from datetime import datetime, timedelta
import uuid
import base64
import pandas as pd

class CalendarEventGenerator:
    """Generate iCalendar (.ics) files for delivery schedules"""
    """Generate iCalendar (.ics) files for delivery schedules"""
    
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
            
            # Create summary and description for this date
            total_deliveries = date_df.get('delivery_count', len(date_df)) if isinstance(date_df, pd.DataFrame) else len(date_df)
            total_line_items = date_df.get('line_items', len(date_df)) if isinstance(date_df, pd.DataFrame) else len(date_df)
            total_quantity = date_df['total_quantity'].sum()
            customers = date_df['customer'].unique()
            
            summary = f"📦 Deliveries ({total_deliveries}) - {delivery_date.strftime('%b %d')}"
            
            description = f"Delivery Schedule for {delivery_date.strftime('%B %d, %Y')}\\n\\n"
            description += f"Total Deliveries: {total_deliveries}\\n"
            description += f"Total Line Items: {total_line_items}\\n"
            description += f"Total Quantity: {total_quantity:,.0f}\\n\\n"
            description += "DELIVERIES:\\n"
            
            for _, row in date_df.iterrows():
                description += f"\\n• {row['customer']}\\n"
                description += f"  Ship To: {row['recipient_company']}\\n"
                description += f"  Location: {row['recipient_state_province']}, {row['recipient_country_name']}\\n"
                description += f"  Products: {row['products'][:50]}...\\n"
                description += f"  Quantity: {row['total_quantity']:,.0f}\\n"
                description += f"  Status: {row['fulfillment_status']}\\n"
            
            # Get locations for this date
            locations = date_df.apply(lambda x: f"{x['recipient_state_province']}, {x['recipient_country_name']}", axis=1).unique()
            location_str = "; ".join(locations[:3])  # Limit to first 3 locations
            if len(locations) > 3:
                location_str += f" and {len(locations)-3} more"
            
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
TRIGGER:-PT15M
ACTION:DISPLAY
DESCRIPTION:Delivery reminder - Check today's deliveries
END:VALARM
END:VEVENT
"""
        
        # ICS footer
        ics_content += "END:VCALENDAR"
        
        return ics_content
    
    @staticmethod
    def create_google_calendar_links(sales_name, delivery_df):
        """Create Google Calendar event links for each delivery date"""
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
            
            # Create title and details
            total_deliveries = date_df.get('delivery_count', len(date_df)) if isinstance(date_df, pd.DataFrame) else len(date_df)
            total_line_items = date_df.get('line_items', len(date_df)) if isinstance(date_df, pd.DataFrame) else len(date_df)
            total_quantity = date_df['total_quantity'].sum()
            
            title = f"📦 Deliveries ({total_deliveries}) - {delivery_date.strftime('%b %d')}"
            
            details = f"Delivery Schedule for {delivery_date.strftime('%B %d, %Y')}\n\n"
            details += f"Total Deliveries: {total_deliveries}\n"
            details += f"Total Line Items: {total_line_items}\n"
            details += f"Total Quantity: {total_quantity:,.0f}\n\n"
            details += "DELIVERIES:\n"
            
            for _, row in date_df.iterrows():
                details += f"\n• {row['customer']}\n"
                details += f"  → {row['recipient_company']}\n"
                details += f"  📍 {row['recipient_state_province']}, {row['recipient_country_name']}\n"
                details += f"  📦 {row['total_quantity']:,.0f} units\n"
            
            # Get locations
            locations = date_df.apply(lambda x: f"{x['recipient_state_province']}, {x['recipient_country_name']}", axis=1).unique()
            location_str = "; ".join(locations[:3])
            if len(locations) > 3:
                location_str += f" +{len(locations)-3} more"
            
            # URL encode the parameters
            import urllib.parse
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
                'count': total_deliveries
            })
        
        return links
    
    @staticmethod
    def create_google_calendar_link(sales_name, delivery_df):
        """Create a single Google Calendar link for the first delivery date (backward compatibility)"""
        links = CalendarEventGenerator.create_google_calendar_links(sales_name, delivery_df)
        return links[0]['link'] if links else "#"
    
    @staticmethod
    def create_outlook_calendar_links(sales_name, delivery_df):
        """Create Outlook/Office 365 calendar event links for each delivery date"""
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
            
            # Create title and body
            total_deliveries = date_df.get('delivery_count', len(date_df)) if isinstance(date_df, pd.DataFrame) else len(date_df)
            total_line_items = date_df.get('line_items', len(date_df)) if isinstance(date_df, pd.DataFrame) else len(date_df)
            total_quantity = date_df['total_quantity'].sum()
            
            subject = f"📦 Deliveries ({total_deliveries}) - {delivery_date.strftime('%b %d')}"
            
            body = f"Delivery Schedule for {delivery_date.strftime('%B %d, %Y')}<br><br>"
            body += f"Total Deliveries: {total_deliveries}<br>"
            body += f"Total Line Items: {total_line_items}<br>"
            body += f"Total Quantity: {total_quantity:,.0f}<br><br>"
            body += "DELIVERIES:<br>"
            
            for _, row in date_df.iterrows():
                body += f"<br>• {row['customer']}<br>"
                body += f"  → {row['recipient_company']}<br>"
                body += f"  📍 {row['recipient_state_province']}, {row['recipient_country_name']}<br>"
                body += f"  📦 {row['total_quantity']:,.0f} units<br>"
            
            # Get locations
            locations = date_df.apply(lambda x: f"{x['recipient_state_province']}, {x['recipient_country_name']}", axis=1).unique()
            location_str = "; ".join(locations[:3])
            if len(locations) > 3:
                location_str += f" +{len(locations)-3} more"
            
            # URL encode the parameters
            import urllib.parse
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
                'count': total_deliveries
            })
        
        return links
    
    @staticmethod
    def create_outlook_calendar_link(sales_name, delivery_df):
        """Create a single Outlook calendar link for the first delivery date (backward compatibility)"""
        links = CalendarEventGenerator.create_outlook_calendar_links(sales_name, delivery_df)
        return links[0]['link'] if links else "#"