import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Service for interacting with WhatsApp Business Cloud API"""
    
    def __init__(self):
        self.api_url = settings.WHATSAPP_API_URL
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
        }
    
    def send_message(self, to_number, message):
        """Send a text message to a WhatsApp number"""
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            logger.info(f"Message sent to {to_number}: {message[:50]}...")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending message to {to_number}: {str(e)}")
            return None
    
    def send_template_message(self, to_number, template_name, language_code='en'):
        """Send a template message (for initial outreach)"""
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
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
