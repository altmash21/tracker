"""
Test sending WhatsApp message via Twilio
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expense_tracker.settings')
django.setup()

from whatsapp_integration.whatsapp_service import WhatsAppService

# Initialize service
ws = WhatsAppService()

# Test phone number (replace with your actual number)
test_number = "+919151726993"  # Your Indian number from the logs

print("="*50)
print("Testing WhatsApp Message Send")
print("="*50)
print(f"Sending test message to: {test_number}")

message = "This is a test message from your Expense Tracker app. If you receive this, Twilio integration is working!"

result = ws.send_message(test_number, message)

if result:
    print(f"\n✓ Message sent successfully!")
    print(f"  SID: {result.get('sid')}")
    print(f"  Status: {result.get('status')}")
else:
    print(f"\n✗ Failed to send message. Check logs above for error details.")

print("="*50)
