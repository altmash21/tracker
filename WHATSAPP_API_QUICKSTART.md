# 🚀 Quick Start: Meta WhatsApp API Setup

## 30-Second Overview

Your app now uses **Meta's WhatsApp Business Cloud API** instead of Twilio. Here's what you need to do:

## ⚙️ 1. Get Credentials (5 minutes)

1. Go to https://developers.facebook.com/
2. Create/Select WhatsApp Business App
3. Get these values from App Dashboard:
   ```
   Business Account ID
   Phone Number ID  
   Access Token (permanent)
   ```
4. Create a Verify Token (any random string)

## 📝 2. Update .env File

```bash
# Copy .env.example to .env if you don't have it
cp .env.example .env

# Edit .env and add Meta credentials:
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_permanent_access_token
WHATSAPP_VERIFY_TOKEN=your_webhook_verify_token
WEBHOOK_SECRET=random_secret_key_here
```

## 🔧 3. Update Code (Already Done!)

✅ requirements.txt - Twilio removed  
✅ settings.py - Config updated  
✅ whatsapp_service.py - Uses Meta API  
✅ views.py - Webhook updated  
✅ All test files - Updated  

**Just run:** `pip install -r requirements.txt`

## ✅ 4. Test Configuration

```bash
python test_twilio_config.py
```

Expected output:
```
WhatsApp Business Cloud API Configuration Test
==============================================================
Phone Number ID: 1234567890123456
Access Token: SET
```

## ✉️ 5. Test Sending Messages

```bash
# Edit test_send_message.py and change test_number
python test_send_message.py
```

Should see:
```
✓ Message sent successfully!
  Message ID: wamid.xxxxx
  Status: sent
```

## 🔗 6. Configure Webhook (When Deploying)

In Meta Developer Dashboard:
- Callback URL: `https://your-domain.com/whatsapp/webhook/`
- Verify Token: (same as WHATSAPP_VERIFY_TOKEN)
- Subscribe to: messages, message_template_status_update

Click "Verify and Save"

## 🎯 Common Tasks

### Send a Message
```python
from whatsapp_integration.whatsapp_service import WhatsAppService

ws = WhatsAppService()
ws.send_message("+919876543210", "Hello!")
```

### Format a Phone Number
```python
from whatsapp_integration.whatsapp_service import WhatsAppService

ws = WhatsAppService()
formatted = ws.format_phone_number("+91-9876-543210")
# Returns: "919876543210"
```

### Send Template Message
```python
ws = WhatsAppService()
ws.send_template_message(
    "+919876543210", 
    "hello_world",  # template name
    "en",           # language
    ["John"]        # parameters
)
```

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| "Token not configured" | Add WHATSAPP_ACCESS_TOKEN to .env |
| "Phone Number ID not set" | Add WHATSAPP_PHONE_NUMBER_ID to .env |
| "Invalid phone number" | Use format: 919876543210 (no +, no spaces) |
| Webhook not receiving | Check URL is HTTPS and publicly accessible |
| 403 Forbidden errors | Access token may be expired - regenerate |
| "Signature verification failed" | WHATSAPP_VERIFY_TOKEN doesn't match dashboard |

## 📚 Documentation

- **MIGRATION_COMPLETE.md** - Full migration details
- **TWILIO_TO_META_MIGRATION.md** - Step-by-step guide
- **WHATSAPP_SETUP.md** - Original setup guide
- **.env.example** - Configuration template

## 🔗 Useful Links

- [Meta WhatsApp API](https://developers.facebook.com/docs/whatsapp)
- [Developer Dashboard](https://developers.facebook.com/)
- [API Reference](https://developers.facebook.com/docs/graph-api)
- [Webhook Docs](https://developers.facebook.com/docs/whatsapp/webhooks)

## ✨ Key Differences from Twilio

| Feature | Twilio | Meta API |
|---------|--------|----------|
| Webhook Format | Form-encoded | JSON |
| Authentication | SID + Token | Bearer Token |
| Cost | $0.01-0.02/msg | $0.005-0.0075/msg ✨ |
| Verification | Not required | HMAC-SHA256 ✨ |
| Setup | Sandbox | Business verification |

---

**You're all set!** Start testing with the commands above.

For detailed information, see **MIGRATION_COMPLETE.md**
