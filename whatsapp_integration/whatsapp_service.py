import logging
from django.conf import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Service for interacting with Twilio WhatsApp API"""
    
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_WHATSAPP_NUMBER
        
        # Validate credentials
        if not self.account_sid or not self.auth_token or not self.from_number:
            logger.error("Twilio credentials are not configured properly")
        
        self.client = Client(self.account_sid, self.auth_token)
    
    def format_phone_number(self, phone):
        """Format phone number for WhatsApp API (ensure whatsapp: prefix and + for country code)"""
        if not phone:
            return None
        # Remove all non-numeric characters except +
        formatted = ''.join(filter(lambda x: x.isdigit() or x == '+', phone))
        # Add + if not present
        if not formatted.startswith('+'):
            formatted = '+' + formatted
        # Add whatsapp: prefix
        return f'whatsapp:{formatted}'
    
    def send_message(self, to_number, message):
        """Send a text message to a WhatsApp number"""
        # Format phone number
        to_number = self.format_phone_number(to_number)
        if not to_number:
            logger.error("Invalid phone number provided")
            return None
        
        try:
            logger.info(f"Sending message to {to_number}...")
            message_response = self.client.messages.create(
                from_=self.from_number,
                body=message,
                to=to_number
            )
            
            logger.info(f"Message sent successfully to {to_number}. SID: {message_response.sid}")
            return {'sid': message_response.sid, 'status': message_response.status}
        except TwilioRestException as e:
            logger.error(f"Twilio error sending message to {to_number}: {e.msg}")
            logger.error(f"Error code: {e.code}")
            return None
        except Exception as e:
            logger.error(f"Error sending message to {to_number}: {str(e)}")
            return None
    
    def send_template_message(self, to_number, template_name, language_code='en'):
        """Send a template message - For Twilio, use content SID"""
        # Twilio uses Content SID for templates
        # For now, fall back to regular message
        logger.warning("Template messages not implemented for Twilio. Sending regular message.")
        return self.send_message(to_number, f"Template: {template_name}")
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            logger.info(f"Template message sent to {to_number}: {template_name}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending template to {to_number}: {str(e)}")
            return None
    
    def mark_message_read(self, message_id):
        """Mark a message as read"""
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error marking message as read: {str(e)}")
            return None
