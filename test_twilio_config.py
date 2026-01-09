"""
Test WhatsApp Business Cloud API credentials configuration (Meta)
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expense_tracker.settings')
django.setup()

from django.conf import settings
from whatsapp_integration.whatsapp_service import WhatsAppService

print("="*60)
print("WhatsApp Business Cloud API Configuration Test")
print("="*60)
print(f"Business Account ID: {settings.WHATSAPP_BUSINESS_ACCOUNT_ID[:10]}..." if settings.WHATSAPP_BUSINESS_ACCOUNT_ID else "NOT SET")
print(f"Phone Number ID: {settings.WHATSAPP_PHONE_NUMBER_ID}")
print(f"Access Token: {'SET' if settings.WHATSAPP_ACCESS_TOKEN else 'NOT SET'}")
print(f"Verify Token: {'SET' if settings.WHATSAPP_VERIFY_TOKEN else 'NOT SET'}")
print("="*60)

# Test WhatsAppService initialization
ws = WhatsAppService()
print(f"\nWhatsAppService initialized:")
print(f"  Phone Number ID: {ws.phone_number_id}")
print(f"  Access Token: {'SET' if ws.access_token else 'NOT SET'}")
print(f"  API URL: {ws.api_url}")
print("="*60)

print("\n✓ Configuration loaded successfully!")
print("\nNext steps:")
print("1. Make sure you have WhatsApp Business Account set up at Meta")
print("2. Get your Phone Number ID from Facebook Business Manager")
print("3. Generate a permanent access token")
print("4. Update .env file with these credentials")
print("5. Run test_send_message.py to test message sending")
print("="*60)

