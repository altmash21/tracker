"""
Test sending WhatsApp message via Meta Business Cloud API
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expense_tracker.settings')
django.setup()

from whatsapp_integration.whatsapp_service import WhatsAppService
from django.conf import settings

# Initialize service
ws = WhatsAppService()

# Test phone number (replace with your actual number)
test_number = "+919151726993"  # Replace with your WhatsApp number

print("="*60)
print("Testing WhatsApp Message Send (Meta Business Cloud API)")
print("="*60)

if not settings.WHATSAPP_ACCESS_TOKEN:
    print("\n❌ ERROR: WhatsApp Access Token not configured!")
    print("Please add WHATSAPP_ACCESS_TOKEN to your .env file")
    sys.exit(1)

if not settings.WHATSAPP_PHONE_NUMBER_ID:
    print("\n❌ ERROR: WhatsApp Phone Number ID not configured!")
    print("Please add WHATSAPP_PHONE_NUMBER_ID to your .env file")
    sys.exit(1)

print(f"\nSending test message to: {test_number}")

message = "✅ This is a test message from your WhatsApp Expense Tracker app. If you receive this, Meta API integration is working!"

result = ws.send_message(test_number, message)

if result:
    print(f"\n✓ Message sent successfully!")
    print(f"  Message ID: {result.get('id')}")
    print(f"  Status: {result.get('status')}")
else:
    print(f"\n✗ Failed to send message. Check logs above for error details.")
    print("\nTroubleshooting:")
    print("1. Check that WHATSAPP_PHONE_NUMBER_ID is correct")
    print("2. Check that WHATSAPP_ACCESS_TOKEN is valid and not expired")
    print("3. Ensure the phone number is registered with WhatsApp Business")
    print("4. Check WhatsApp dashboard logs for more details")

print("="*60)

