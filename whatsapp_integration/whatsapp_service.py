import logging
import requests
import hmac
import hashlib
from django.conf import settings

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Service for interacting with WhatsApp Business Cloud API (Meta)"""
    
    def __init__(self):
        self.business_account_id = settings.WHATSAPP_BUSINESS_ACCOUNT_ID
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.verify_token = settings.WHATSAPP_VERIFY_TOKEN
        
        # Validate credentials
        if not self.phone_number_id or not self.access_token:
            logger.error("WhatsApp Business API credentials are not configured properly")
        
        # Meta API endpoint
        self.api_url = f"https://graph.instagram.com/v20.0/{self.phone_number_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def format_phone_number(self, phone):
        """Format phone number for WhatsApp API (remove all non-numeric, add country code)"""
        if not phone:
            return None
        
        # Remove all non-numeric characters
        formatted = ''.join(filter(str.isdigit, phone))
        
        # Remove leading zeros
        formatted = formatted.lstrip('0')
        
        # If the number doesn't have country code, assume India (91)
        if len(formatted) == 10:
            formatted = '91' + formatted
        
        return formatted
    
    def send_message(self, to_number, message):
        """Send a text message to a WhatsApp number using Meta API"""
        try:
            # Format phone number
            to_number = self.format_phone_number(to_number)
            if not to_number:
                logger.error("Invalid phone number provided")
                return None
            
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to_number,
                "type": "text",
                "text": {
                    "body": message
                }
            }
            
            logger.info(f"Sending message to {to_number}...")
            response = requests.post(
                self.api_url,
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                response_data = response.json()
                message_id = response_data.get('messages', [{}])[0].get('id', '')
                logger.info(f"Message sent successfully to {to_number}. Message ID: {message_id}")
                return {'id': message_id, 'status': 'sent'}
            else:
                logger.error(f"Error sending message to {to_number}: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout sending message to {to_number}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending message to {to_number}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error sending message to {to_number}: {str(e)}")
            return None
    
    def send_template_message(self, to_number, template_name, language_code='en', parameters=None):
        """Send a template message"""
        try:
            to_number = self.format_phone_number(to_number)
            if not to_number:
                logger.error("Invalid phone number provided")
                return None
            
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
            
            # Add parameters if provided
            if parameters:
                payload["template"]["parameters"] = {
                    "body": {
                        "parameters": parameters
                    }
                }
            
            logger.info(f"Sending template message to {to_number}: {template_name}")
            response = requests.post(
                self.api_url,
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                response_data = response.json()
                message_id = response_data.get('messages', [{}])[0].get('id', '')
                logger.info(f"Template message sent to {to_number}: {template_name}")
                return {'id': message_id, 'status': 'sent'}
            else:
                logger.error(f"Error sending template to {to_number}: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending template to {to_number}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error sending template: {str(e)}")
            return None
    
    def mark_message_read(self, message_id):
        """Mark a message as read"""
        try:
            url = f"https://graph.instagram.com/v20.0/{self.phone_number_id}/messages"
            
            payload = {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id
            }
            
            response = requests.post(url, json=payload, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Message {message_id} marked as read")
                return True
            else:
                logger.error(f"Error marking message as read: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error marking message as read: {str(e)}")
            return False
    
    def verify_webhook_signature(self, request):
        """Verify webhook signature from Meta to ensure authenticity"""
        try:
            # Get the signature from the request header
            signature = request.META.get('HTTP_X_HUB_SIGNATURE_256', '')
            
            if not signature:
                logger.warning("No X-Hub-Signature-256 header found")
                return False
            
            # Get the request body
            body = request.body
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            
            # Generate the signature using the app secret
            expected_signature = 'sha256=' + hmac.new(
                settings.WEBHOOK_SECRET.encode('utf-8'),
                body.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            if hmac.compare_digest(signature, expected_signature):
                logger.info("Webhook signature verified successfully")
                return True
            else:
                logger.warning("Webhook signature verification failed")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {str(e)}")
            return False
