# utils/calendar_utils.py - Calendar event generator for delivery schedules

from datetime import datetime, timedelta
import uuid
import base64

class CalendarEventGenerator:
    """Generate iCalendar (.ics) files for delivery schedules"""
    
    @staticmethod
    def create_ics_content(sales_name, delivery_df, organizer_email):
        """Create ICS content for calendar event"""
        
        # Get date range
        start_date = delivery_df['delivery_date'].min()
        end_date = delivery_df['delivery_date'].max()
        
        # Create event summary
        total_deliveries = len(delivery_df)
        total_customers = delivery_df['customer'].nunique()
        
        # Generate unique ID
        uid = str(uuid.uuid4())
        
        # Current timestamp
        now = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        
        # Create description with delivery details
        description = f"Delivery Schedule for {sales_name}\\n\\n"
        description += f"Period: {start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}\\n"
        description += f"Total Deliveries: {total_deliveries}\\n"
        description += f"Total Customers: {total_customers}\\n\\n"
        description += "DELIVERY BREAKDOWN:\\n"
        
        # Group by date for summary
        for date, date_df in delivery_df.groupby('delivery_date'):
            description += f"\\n{date.strftime('%b %d')}:\\n"
            for _, row in date_df.iterrows():
                description += f"- {row['customer']} → {row['recipient_company']} ({row['total_quantity']:,.0f} units)\\n"
        
        # Create ICS content
        ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Outbound Logistics//Delivery Schedule//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:{uid}@outbound.prostech.vn
DTSTAMP:{now}
ORGANIZER;CN=Outbound Logistics:mailto:{organizer_email}
DTSTART;VALUE=DATE:{start_date.strftime('%Y%m%d')}
DTEND;VALUE=DATE:{(end_date + timedelta(days=1)).strftime('%Y%m%d')}
SUMMARY:📦 Delivery Schedule - {sales_name}
DESCRIPTION:{description}
LOCATION:Various Locations
STATUS:CONFIRMED
SEQUENCE:0
TRANSP:TRANSPARENT
BEGIN:VALARM
TRIGGER:-P1D
ACTION:DISPLAY
DESCRIPTION:Reminder: Review tomorrow's deliveries
END:VALARM
END:VEVENT
END:VCALENDAR"""
        
        return ics_content
    
    @staticmethod
    def create_google_calendar_link(sales_name, delivery_df):
        """Create Google Calendar event link"""
        
        # Get date range
        start_date = delivery_df['delivery_date'].min()
        end_date = delivery_df['delivery_date'].max() + timedelta(days=1)
        
        # Format dates for Google Calendar
        dates = f"{start_date.strftime('%Y%m%d')}/{end_date.strftime('%Y%m%d')}"
        
        # Create title and details
        title = f"📦 Delivery Schedule - {sales_name}"
        
        details = f"Delivery Schedule for {sales_name}\n\n"
        details += f"Period: {start_date.strftime('%B %d')} - {(end_date - timedelta(days=1)).strftime('%B %d, %Y')}\n"
        details += f"Total Deliveries: {len(delivery_df)}\n"
        details += f"Total Customers: {delivery_df['customer'].nunique()}\n\n"
        details += "Check email for detailed schedule and Excel attachment."
        
        # URL encode the parameters
        import urllib.parse
        params = {
            'action': 'TEMPLATE',
            'text': title,
            'dates': dates,
            'details': details,
            'location': 'Various Locations',
            'sf': 'true'
        }
        
        base_url = 'https://calendar.google.com/calendar/render'
        return f"{base_url}?{urllib.parse.urlencode(params)}"
    
    @staticmethod
    def create_outlook_calendar_link(sales_name, delivery_df):
        """Create Outlook/Office 365 calendar event link"""
        
        # Get date range
        start_date = delivery_df['delivery_date'].min()
        end_date = delivery_df['delivery_date'].max() + timedelta(days=1)
        
        # Format dates for Outlook (ISO format)
        startdt = start_date.strftime('%Y-%m-%d')
        enddt = end_date.strftime('%Y-%m-%d')
        
        # Create title and body
        subject = f"📦 Delivery Schedule - {sales_name}"
        
        body = f"Delivery Schedule for {sales_name}<br><br>"
        body += f"Period: {start_date.strftime('%B %d')} - {(end_date - timedelta(days=1)).strftime('%B %d, %Y')}<br>"
        body += f"Total Deliveries: {len(delivery_df)}<br>"
        body += f"Total Customers: {delivery_df['customer'].nunique()}<br><br>"
        body += "Check email for detailed schedule and Excel attachment."
        
        # URL encode the parameters
        import urllib.parse
        params = {
            'subject': subject,
            'startdt': startdt,
            'enddt': enddt,
            'body': body,
            'allday': 'true'
        }
        
        base_url = 'https://outlook.live.com/calendar/0/deeplink/compose'
        return f"{base_url}?{urllib.parse.urlencode(params)}"