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
    print("Note: Only Phone Number ID, Business Account ID, and Access Token are required for sending messages.\n")
    
    # Prompt for API configs (only what's needed for sending)
    phone_number_id = get_input("Enter WhatsApp Phone Number ID", os.environ.get('WHATSAPP_PHONE_NUMBER_ID'))
    access_token = get_input("Enter WhatsApp Access Token", os.environ.get('WHATSAPP_ACCESS_TOKEN'))
    business_account_id = get_input("Enter WhatsApp Business Account ID", os.environ.get('WHATSAPP_BUSINESS_ACCOUNT_ID'))

    # Prompt for message details
    print("\nChoose message type:")
    print("1. Template message (hello_world) - Works anytime")
    print("2. Regular text message - Requires active 24hr conversation window")
    choice = get_input("Enter choice (1 or 2)", "1")
    
    to_number = get_input("Enter recipient WhatsApp number (with country code, e.g. 919151726993)")

    # Patch Django settings for this test
    from django.conf import settings
    settings.WHATSAPP_PHONE_NUMBER_ID = phone_number_id
    settings.WHATSAPP_ACCESS_TOKEN = access_token
    settings.WHATSAPP_BUSINESS_ACCOUNT_ID = business_account_id

    try:
        service = WhatsAppService()
        
        if choice == "1":
            # Send template message
            print("\nSending hello_world template message...")
            response = service.send_template_message(to_number, "hello_world", "en_US")
            print('Template message sent! Response:', response)
            print("\nIMPORTANT: Reply to this message on WhatsApp to open a 24-hour conversation window!")
        else:
            # Send regular text message
            message = get_input("Enter message to send", "Hello from the WhatsApp API test script!")
            response = service.send_message(to_number, message)
            print('Message sent! Response:', response)
            
    except Exception as e:
        print('Error sending message:', e)
