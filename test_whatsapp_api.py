# WhatsApp API Test Script
# This script sends a test message using the WhatsApp API integration in your Django project.
# Update the variables below with valid values before running.

import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expense_tracker.settings')
django.setup()

from whatsapp_integration.whatsapp_service import WhatsAppService

def get_input(prompt, default=None):
    value = input(f"{prompt} [{default if default else ''}]: ").strip()
    return value if value else default

if __name__ == '__main__':
    print("--- WhatsApp API Test Script ---")
    # Prompt for API configs
    phone_number_id = get_input("Enter WhatsApp Phone Number ID", os.environ.get('WHATSAPP_PHONE_NUMBER_ID'))
    access_token = get_input("Enter WhatsApp Access Token", os.environ.get('WHATSAPP_ACCESS_TOKEN'))
    business_account_id = get_input("Enter WhatsApp Business Account ID", os.environ.get('WHATSAPP_BUSINESS_ACCOUNT_ID'))
    verify_token = get_input("Enter WhatsApp Verify Token", os.environ.get('WHATSAPP_VERIFY_TOKEN'))

    # Prompt for message details
    to_number = get_input("Enter recipient WhatsApp number (with country code, e.g. 919151726993)")
    message = get_input("Enter message to send", "Hello from the WhatsApp API test script!")

    # Patch Django settings for this test
    from django.conf import settings
    settings.WHATSAPP_PHONE_NUMBER_ID = phone_number_id
    settings.WHATSAPP_ACCESS_TOKEN = access_token
    settings.WHATSAPP_BUSINESS_ACCOUNT_ID = business_account_id
    settings.WHATSAPP_VERIFY_TOKEN = verify_token

    try:
        service = WhatsAppService()
        response = service.send_message(to_number, message)
        print('Message sent! Response:', response)
    except Exception as e:
        print('Error sending message:', e)
