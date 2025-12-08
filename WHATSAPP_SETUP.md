# WhatsApp Business API Setup Guide

## 📱 Step-by-Step WhatsApp Configuration

### Prerequisites
- [ ] Facebook/Meta account
- [ ] Phone number (not used with personal WhatsApp)
- [ ] Business verification (for production)

---

## Part 1: Meta Developer Account Setup

### Step 1: Create Meta App
1. Go to https://developers.facebook.com/
2. Click **"My Apps"** → **"Create App"**
3. Select **"Business"** as app type
4. Fill in:
   - App Name: "Expense Tracker"
   - App Contact Email: your-email@example.com
   - Business Account: Create new or select existing
5. Click **"Create App"**

### Step 2: Add WhatsApp Product
1. In your app dashboard, find **"WhatsApp"**
2. Click **"Set Up"**
3. You'll be taken to WhatsApp setup page

---

## Part 2: Get WhatsApp Credentials

### Step 3: Get Test Number (For Development)
1. In WhatsApp setup, you'll see a **test phone number**
2. Note down:
   - **Phone Number ID**: `911177822082119` (from your dashboard)
   - **WhatsApp Business Account ID**: `789128127482529` (from your dashboard)
   - **Test number**: `+1 555 616 5015`
3. Add your personal WhatsApp number to receive test messages
4. Click **"Send message"** to test

### Step 4: Get Access Token
1. In WhatsApp setup, find **"Temporary access token"**
2. Copy the token (valid for 24 hours)
3. For production, generate **Permanent Token**:
   - Go to **App Settings** → **Basic**
   - Copy **App ID** and **App Secret**
   - Use these to generate long-lived token

### Step 5: Generate Permanent Access Token (Production)
```bash
curl -X GET "https://graph.facebook.com/v18.0/oauth/access_token? \
  grant_type=fb_exchange_token& \
  client_id=YOUR_APP_ID& \
  client_secret=YOUR_APP_SECRET& \
  fb_exchange_token=YOUR_TEMPORARY_TOKEN"
```

Save the permanent token returned.

---

## Part 3: Configure Webhook

### Step 6: Deploy Your Application
Before configuring webhook, your app must be:
1. Deployed to a public server (not localhost)
2. Accessible via HTTPS
3. Have a valid SSL certificate

**Quick Deploy Options:**
- DigitalOcean App Platform (recommended)
- Render
- Heroku
- AWS

See `DEPLOYMENT.md` for detailed steps.

### Step 7: Set Up Webhook in Meta
1. In WhatsApp setup, click **"Configuration"**
2. In **"Webhook"** section, click **"Edit"**
3. Enter:
   - **Callback URL**: `https://your-domain.com/whatsapp/webhook/`
   - **Verify Token**: (create a random string, e.g., `my_secure_verify_token_123`)
4. Click **"Verify and Save"**

Meta will send a GET request to verify your webhook.

### Step 8: Update .env File
```env
WHATSAPP_API_URL=https://graph.facebook.com/v18.0
WHATSAPP_PHONE_NUMBER_ID=911177822082119
WHATSAPP_ACCESS_TOKEN=your_test_or_temporary_token
WHATSAPP_VERIFY_TOKEN=my_secure_verify_token_123
WHATSAPP_BUSINESS_ACCOUNT_ID=789128127482529
```

### Step 9: Subscribe to Webhook Fields
1. In Webhook configuration, click **"Manage"**
2. Subscribe to: **messages**
3. Click **"Subscribe"**

---

## Part 4: Testing

### Step 10: Test Webhook
1. Send a test message to your WhatsApp Business number:
   ```
   help
   ```

2. Expected response:
   ```
   📱 Expense Tracker Commands
   
   Add Expense:
   <amount> <category> [description]
   ...
   ```

3. Check server logs:
   ```bash
   # Check webhook logs
   tail -f /var/log/django/debug.log
   ```

### Step 11: Test Expense Entry
1. Register a user on your web app
2. Link WhatsApp number (you'll receive OTP)
3. Verify OTP
4. Send expense message:
   ```
   120 petrol
   ```

5. Expected response:
   ```
   ✅ Recorded: ₹120 under 🚗 Travel
   ```

6. Check dashboard - expense should appear!

---

## Part 5: Production Setup

### Step 12: Business Verification (Required for Production)
1. Go to **Business Settings** → **Business Info**
2. Complete business verification:
   - Business name
   - Business address
   - Business phone number
   - Business documents
3. Wait for approval (1-7 days)

### Step 13: Get Your Own Phone Number
After business verification:
1. Go to **WhatsApp** → **Phone Numbers**
2. Click **"Add Phone Number"**
3. Options:
   - **Own number**: Port existing business number
   - **New number**: Get new number from Meta
4. Complete setup and verification

### Step 14: Update Configuration
Replace test credentials with production credentials in `.env`.

---

## Troubleshooting

### Webhook Not Receiving Messages

**Check 1: URL Accessibility**
```bash
curl -I https://your-domain.com/whatsapp/webhook/
# Should return 200 or 405 (GET not allowed is ok)
```

**Check 2: SSL Certificate**
```bash
curl -v https://your-domain.com
# Should show valid SSL certificate
```

**Check 3: Verify Token Match**
Ensure verify token in `.env` matches what you entered in Meta dashboard.

**Check 4: Webhook Subscription**
- Go to Meta dashboard → WhatsApp → Configuration
- Ensure "messages" is subscribed

**Check 5: Server Logs**
```bash
# Check for errors
tail -100 /var/log/django/debug.log
```

### Messages Not Sending

**Check 1: Access Token**
```bash
curl -X POST "https://graph.facebook.com/v18.0/PHONE_NUMBER_ID/messages" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messaging_product": "whatsapp",
    "to": "919876543210",
    "type": "text",
    "text": {"body": "Test message"}
  }'
```

**Check 2: Phone Number Format**
- Must include country code
- No + symbol in API calls
- Example: `919876543210` (not `+91 98765 43210`)

**Check 3: Rate Limits**
- Development: 50 messages per minute
- Production: Higher limits after business verification

### OTP Not Received

**Check 1: WhatsApp Number Registered**
User's WhatsApp number must be active on WhatsApp.

**Check 2: Template Message (Production)**
In production, you may need to use template messages for OTP.

**Check 3: API Response**
Check server logs for WhatsApp API response errors.

---

## Quick Reference

### Important URLs
- Meta Developer Dashboard: https://developers.facebook.com/
- WhatsApp Business API Docs: https://developers.facebook.com/docs/whatsapp
- Graph API Explorer: https://developers.facebook.com/tools/explorer

### Environment Variables
```env
WHATSAPP_API_URL=https://graph.facebook.com/v18.0
WHATSAPP_PHONE_NUMBER_ID=911177822082119
WHATSAPP_ACCESS_TOKEN=your_test_or_temporary_token
WHATSAPP_VERIFY_TOKEN=your_verify_token
WHATSAPP_BUSINESS_ACCOUNT_ID=789128127482529
```

### Webhook URL Format
```
https://your-domain.com/whatsapp/webhook/
```

### Test Commands
```
help                    # Get help message
120 petrol              # Add expense
today                   # View today's expenses
summary                 # View monthly summary
categories              # List categories
```

---

## Cost Structure

### Development/Testing
- **Free** with test number
- 1,000 free service conversations per month
- Unlimited with test numbers

### Production
- First 1,000 conversations/month: **Free**
- After that: **$0.005 - $0.05 per conversation**
  (varies by country)
- Business verification: **Free**
- Phone number: **Free** (Meta-provided) or **$XX/month** (own number)

### Conversation Windows
- 24-hour window after user message
- Template messages to initiate conversation

---

## Security Best Practices

### 1. Protect Access Token
```python
# Never commit to git
# Store in environment variables
# Rotate regularly (every 60 days)
```

### 2. Verify Webhook Signatures
```python
# Implement in production
import hmac
import hashlib

def verify_signature(payload, signature):
    expected = hmac.new(
        key=APP_SECRET.encode(),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

### 3. Rate Limiting
```python
# Implement rate limiting on webhook
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='50/m')
def whatsapp_webhook(request):
    ...
```

### 4. Input Validation
```python
# Sanitize all user input
# Validate message formats
# Check for malicious content
```

---

## Support & Resources

### Official Documentation
- [WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Getting Started Guide](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started)
- [Message Templates](https://developers.facebook.com/docs/whatsapp/message-templates)

### Community
- [Meta Developers Community](https://developers.facebook.com/community/)
- [WhatsApp Business API Forum](https://developers.facebook.com/community/threads/?tags=whatsapp)

### Tools
- [Graph API Explorer](https://developers.facebook.com/tools/explorer)
- [Webhook Tester](https://webhook.site/)
- [Postman Collection](https://www.postman.com/meta-platforms)

---

## Checklist Summary

- [ ] Created Meta Developer account
- [ ] Created WhatsApp Business app
- [ ] Got Phone Number ID
- [ ] Got Access Token (permanent)
- [ ] Got Business Account ID
- [ ] Set verify token
- [ ] Updated .env file
- [ ] Deployed application (HTTPS)
- [ ] Configured webhook URL
- [ ] Subscribed to "messages" field
- [ ] Tested webhook with "help" message
- [ ] Registered test user
- [ ] Linked WhatsApp number
- [ ] Verified OTP
- [ ] Tested expense entry
- [ ] Verified dashboard sync
- [ ] (Production) Completed business verification
- [ ] (Production) Added own phone number

---

**Once all steps are complete, your WhatsApp Expense Tracker is fully operational! 🎉**
