# Migration Guide: Twilio → WhatsApp Business Cloud API

## Overview
This guide documents the complete migration from Twilio to Meta's WhatsApp Business Cloud API.

## Changes Made

### 1. Dependencies
**Removed:** `twilio==9.0.4`  
**Kept:** `requests==2.32.5` (for HTTP calls to Meta API)

Update your environment:
```bash
pip uninstall twilio
# or simply:
pip install -r requirements.txt
```

### 2. Configuration Variables

**Old (Twilio):**
```
TWILIO_ACCOUNT_SID=xxxx
TWILIO_AUTH_TOKEN=xxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

**New (Meta WhatsApp API):**
```
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_permanent_access_token
WHATSAPP_VERIFY_TOKEN=your_webhook_verify_token
WEBHOOK_SECRET=your_webhook_secret_key
```

### 3. Files Modified

#### settings.py
- Replaced Twilio config with Meta API config
- Updated environment variable names

#### whatsapp_service.py
- Complete rewrite using `requests` library instead of Twilio SDK
- Added webhook signature verification using HMAC-SHA256
- Updated API endpoint to Meta's Graph API v20.0
- New methods: `verify_webhook_signature()`
- Enhanced error handling and logging

#### views.py
- Removed `handle_twilio_webhook()` - replaced with `handle_webhook()`
- Webhook now expects JSON payloads from Meta
- Added webhook signature verification
- Updated message parsing for Meta format
- Improved phone number normalization

#### Test Files
- `test_twilio_config.py` → Now tests Meta API configuration
- `test_send_message.py` → Tests Meta API message sending
- `test_registration_flow.py` → Updated to use Meta API for OTP delivery

## Setup Instructions

### Step 1: Get Meta Credentials

1. Go to [Meta Developers](https://developers.facebook.com/)
2. Create a Business Account if you don't have one
3. Create an app and select "WhatsApp Business Platform"
4. In App Dashboard, go to "Configuration"
5. Get your:
   - Business Account ID
   - Phone Number ID
   - Access Token (generate a permanent one)
6. Set a Webhook Verify Token (any random string)

### Step 2: Update .env File

Copy `.env.example` to `.env` and fill in:
```bash
WHATSAPP_BUSINESS_ACCOUNT_ID=123456789
WHATSAPP_PHONE_NUMBER_ID=1234567890123456
WHATSAPP_ACCESS_TOKEN=EAAxxxxxx...
WHATSAPP_VERIFY_TOKEN=my_webhook_token_12345
WEBHOOK_SECRET=my_webhook_secret_key
```

### Step 3: Test Configuration

```bash
python test_twilio_config.py
```

Should output:
```
WhatsApp Business Cloud API Configuration Test
==============================================================
Business Account ID: 123456789...
Phone Number ID: 1234567890123456
Access Token: SET
Verify Token: SET
==============================================================

WhatsAppService initialized:
  Phone Number ID: 1234567890123456
  Access Token: SET
  API URL: https://graph.instagram.com/v20.0/1234567890123456/messages
```

### Step 4: Test Sending Messages

```bash
# Update test number in the script
python test_send_message.py
```

### Step 5: Configure Webhook

1. Get your deployment URL (e.g., https://yourdomain.com/whatsapp/webhook/)
2. In Meta App Dashboard → Settings → Webhook
3. Set Callback URL to: `https://yourdomain.com/whatsapp/webhook/`
4. Set Verify Token to the value in your .env
5. Subscribe to messages webhook
6. Click "Verify and Save"

### Step 6: Restart Application

```bash
python manage.py runserver
```

## API Differences

### Sending Messages

**Twilio:**
```python
client.messages.create(
    from_='whatsapp:+14155238886',
    body='Hello',
    to='whatsapp:+919xxxxxxxxxx'
)
```

**Meta API:**
```python
requests.post(
    'https://graph.instagram.com/v20.0/{phone_id}/messages',
    json={
        "messaging_product": "whatsapp",
        "to": "919xxxxxxxxxx",
        "type": "text",
        "text": {"body": "Hello"}
    },
    headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
)
```

### Receiving Messages

**Twilio:**
- Form-encoded POST data
- No signature verification required
- Fields: `From`, `To`, `Body`, `MessageSid`

**Meta API:**
- JSON POST data
- HMAC-SHA256 signature verification required
- Webhook verification via GET with challenge token
- Fields: `entry.changes.value.messages[].from`, `.text.body`, `.id`

## Webhook Response Format

### Verification Request (GET)
```
GET /whatsapp/webhook/?hub.mode=subscribe&hub.verify_token=xxx&hub.challenge=yyy
```

Response: Challenge value in plaintext

### Message Webhook (POST)
```json
{
  "entry": [
    {
      "changes": [
        {
          "value": {
            "messages": [
              {
                "from": "919xxxxxxxxxx",
                "id": "wamid.xxxxx",
                "type": "text",
                "text": {
                  "body": "User message"
                }
              }
            ]
          }
        }
      ]
    }
  ]
}
```

## Troubleshooting

### Issue: "WhatsApp Access Token not configured"
**Solution:** Check that `WHATSAPP_ACCESS_TOKEN` is set in `.env`

### Issue: "Invalid phone number" errors
**Solution:** 
- Phone numbers must be in international format (country code + number)
- Remove any special characters except digits
- Examples: `919876543210`, `14155238086`

### Issue: Webhook verification fails
**Solution:**
- Verify token must match exactly in Meta Dashboard and .env
- Check webhook URL is publicly accessible (use ngrok for local testing)
- Ensure HTTPS is enabled in production

### Issue: Message sending returns 403
**Solution:**
- Access token may be expired - regenerate it
- Phone number may not be verified - verify in Meta Dashboard
- Rate limiting - wait a moment and retry

### Issue: Webhook not receiving messages
**Solution:**
- Check webhook URL is correct in Meta Dashboard
- Verify webhook is receiving GET requests for setup
- Check application logs with: `tail -f debug.log`
- Test with curl to ensure endpoint is accessible

## Rollback (if needed)

If you need to go back to Twilio:

1. Restore original files from git/backup
2. `pip install twilio==9.0.4`
3. Update .env with Twilio credentials
4. Restart application

## References

- [Meta WhatsApp Business API Docs](https://developers.facebook.com/docs/whatsapp/cloud-api/)
- [Graph API Reference](https://developers.facebook.com/docs/graph-api/)
- [Webhook Reference](https://developers.facebook.com/docs/whatsapp/webhooks/inbound)
- [Meta Developers Dashboard](https://developers.facebook.com/)

## Cost Comparison

| Aspect | Twilio | Meta API |
|--------|--------|----------|
| Setup | Sandbox available | Business verification required |
| Per Message | $0.01-0.02 | $0.005-0.0075 (cheaper) |
| Scale | Paid from start | Free tier available |
| Features | Basic | Advanced (templates, media, etc.) |

---

**Migration completed successfully!** Your app now uses Meta's WhatsApp Business Cloud API.
