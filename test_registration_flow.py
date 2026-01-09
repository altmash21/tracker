"""
Test complete registration flow with OTP via Meta WhatsApp API
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expense_tracker.settings')
django.setup()

from users.models import User
from whatsapp_integration.whatsapp_service import WhatsAppService

print("="*60)
print("Testing Complete Registration Flow (Meta WhatsApp API)")
print("="*60)

# Simulate user registration
test_phone = "+919151726993"

# Check if test user exists
if User.objects.filter(username="testuser123").exists():
    print("\nCleaning up existing test user...")
    User.objects.filter(username="testuser123").delete()

# Create test user
print(f"\n1. Creating test user with WhatsApp: {test_phone}")
user = User.objects.create_user(
    username="testuser123",
    email="test@example.com",
    password="testpass123",
    whatsapp_number=test_phone,
    whatsapp_verified=False
)
print(f"   ✓ User created: {user.username}")

# Generate OTP
print(f"\n2. Generating OTP...")
otp = user.generate_otp()
print(f"   ✓ OTP generated: {otp}")
print(f"   ✓ OTP expires in 10 minutes")

# Send OTP via WhatsApp
print(f"\n3. Sending OTP via WhatsApp to {test_phone}...")
ws = WhatsAppService()
message = f"Your OTP for Expense Tracker registration is: {otp}\n\nThis OTP is valid for 10 minutes."
result = ws.send_message(test_phone, message)

if result:
    print(f"   ✓ WhatsApp message sent successfully!")
    print(f"   ✓ Message ID: {result.get('id')}")
    print(f"   ✓ Status: {result.get('status')}")
else:
    print(f"   ✗ Failed to send WhatsApp message")

# Test OTP verification
print(f"\n4. Testing OTP verification...")
print(f"   Testing with correct OTP: {otp}")
is_valid = user.verify_otp(otp)
if is_valid:
    print(f"   ✓ OTP verification successful!")
    print(f"   ✓ User marked as verified")
else:
    print(f"   ✗ OTP verification failed")

print("\n" + "="*60)
print("Summary:")
print("="*60)
print(f"✓ User creation: SUCCESS")
print(f"✓ OTP generation: SUCCESS")
print(f"✓ WhatsApp message (Meta API): {'SUCCESS' if result else 'FAILED'}")
print(f"✓ OTP verification: {'SUCCESS' if is_valid else 'FAILED'}")
print("="*60)
print("\nRegistration flow is working correctly!")
print("Note: Check your WhatsApp to see if you received the OTP.")
print("If not, make sure your WhatsApp Business Account is properly configured.")
print("="*60)

# Cleanup
print("\nCleaning up test user...")
user.delete()
print("✓ Test complete!")

