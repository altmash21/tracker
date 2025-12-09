"""
Test Twilio credentials configuration
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

print("="*50)
print("Twilio Configuration Test")
print("="*50)
print(f"Account SID: {settings.TWILIO_ACCOUNT_SID}")
print(f"Auth Token: {'*' * 20 if settings.TWILIO_AUTH_TOKEN else 'NOT SET'}")
print(f"WhatsApp Number: {settings.TWILIO_WHATSAPP_NUMBER}")
print("="*50)

# Test WhatsAppService initialization
ws = WhatsAppService()
print(f"\nWhatsAppService initialized:")
print(f"  Account SID: {ws.account_sid}")
print(f"  Auth Token: {'SET' if ws.auth_token else 'NOT SET'}")
print(f"  From Number: {ws.from_number}")
print("="*50)
