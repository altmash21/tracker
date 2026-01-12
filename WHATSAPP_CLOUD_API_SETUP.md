# WhatsApp Cloud API Setup Guide - Step by Step

This guide will walk you through setting up Meta's WhatsApp Business Cloud API from scratch.

---

## Prerequisites

- A Facebook account
- A phone number for WhatsApp Business verification (can be your personal number for testing)
- Your VPS/server public URL with HTTPS (for webhook setup)

---

## Step 1: Create Meta Developer Account (5 minutes)

1. Go to **https://developers.facebook.com/**
2. Click **"Get Started"** in the top right
3. Log in with your Facebook account
4. Complete the registration:
   - Accept Terms & Conditions
   - Verify your email if prompted
   - Fill in basic information

---

## Step 2: Create a WhatsApp Business App (3 minutes)

1. Once logged in, click **"My Apps"** in the top menu
2. Click **"Create App"** button
3. Select app type: **"Business"**
4. Fill in app details:
   - **App Name**: `Expense Tracker WhatsApp` (or your preferred name)
   - **Contact Email**: Your email address
   - **Business Portfolio**: Select existing or create new
5. Click **"Create App"**
6. Complete security check if prompted

---

## Step 3: Add WhatsApp Product (2 minutes)

1. On your app dashboard, scroll to **"Add products to your app"**
2. Find **"WhatsApp"** card
3. Click **"Set up"** button
4. WhatsApp will be added to your app

---

## Step 4: Get Your Credentials (5 minutes)

### A. Get Business Account ID

1. In the left sidebar, click **"WhatsApp" → "Getting Started"**
2. You'll see a section called **"Business Account ID"**
3. Copy this ID (looks like: `123456789012345`)
4. Save it for later: `WHATSAPP_BUSINESS_ACCOUNT_ID`

### B. Get Phone Number ID

1. Still on the "Getting Started" page
2. Look for **"Phone Number ID"** section
3. Copy the Phone Number ID (looks like: `109876543210987`)
4. Save it for later: `WHATSAPP_PHONE_NUMBER_ID`

### C. Get Temporary Access Token

1. On the same page, look for **"Temporary Access Token"**
2. Click **"Copy"** to copy the token
3. **IMPORTANT**: This token expires in 24 hours - we'll generate a permanent one later
4. For now, save it temporarily

### D. See Your Test Number

1. You'll see a **"From"** field showing a test phone number
2. This is Meta's test number you can send messages from
3. Note: You can only send to 5 pre-approved numbers in test mode

---

## Step 5: Add Test Recipient Numbers (2 minutes)

1. On the "Getting Started" page, find **"To"** section
2. Click **"Add phone number"** or **"Manage phone number list"**
3. Enter your WhatsApp number (with country code, e.g., +919876543210)
4. Click **"Send code"**
5. Check your WhatsApp for a verification code
6. Enter the code and verify
7. You can add up to 5 numbers for testing

---

## Step 6: Test Sending a Message (2 minutes)

1. On the "Getting Started" page, you'll see an **API setup** section
2. Make sure your verified number is selected in the **"To"** field
3. Click **"Send message"** button
4. Check your WhatsApp - you should receive a "Hello World" message!

✅ If you received the message, your basic setup is working!

---

## Step 7: Generate Permanent Access Token (5 minutes)

The temporary token expires in 24 hours. Let's create a permanent one:

### Option A: System User Token (Recommended for Production)

1. Go to **Meta Business Settings**: https://business.facebook.com/settings/
2. Click **"Users" → "System Users"** in left sidebar
3. Click **"Add"** button
4. Enter a name: `WhatsApp API User`
5. Select role: **Admin**
6. Click **"Create System User"**
7. Click on the newly created system user
8. Click **"Add Assets"**
9. Select **"Apps"** tab
10. Find your app and toggle it on
11. Select **"Full control"** or **"Manage app"** permission
12. Click **"Save Changes"**
13. Click **"Generate New Token"** button
14. Select your app from dropdown
15. Check these permissions:
    - `whatsapp_business_management`
    - `whatsapp_business_messaging`
16. Click **"Generate Token"**
17. **IMPORTANT**: Copy this token immediately and save it securely
18. This is your `WHATSAPP_ACCESS_TOKEN` - it doesn't expire!

### Option B: User Access Token (Simpler, for Testing)

1. In your app dashboard, go to **"WhatsApp" → "Getting Started"**
2. Scroll to **"Temporary access token"**
3. Click the small settings/config icon next to it
4. Or go to **"Settings" → "Basic"** in left sidebar
5. Note: User tokens expire every 60 days
6. For production, use System User Token (Option A)

---

## Step 8: Update Your .env File (2 minutes)

Open your `.env` file and update these values:

```bash
# WhatsApp Business Cloud API Configuration
WHATSAPP_BUSINESS_ACCOUNT_ID=123456789012345        # From Step 4A
WHATSAPP_PHONE_NUMBER_ID=109876543210987           # From Step 4B
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxxxxxxxx     # From Step 7
WHATSAPP_VERIFY_TOKEN=my_secure_verify_token_123   # Create any random string

# Webhook Security
WEBHOOK_SECRET=another_random_secure_string_456    # Create any random string
```

---

## Step 9: Test Your Configuration (1 minute)

Run the test script:

```bash
python test_whatsapp_api.py
```

When prompted:
- Press Enter to use values from .env OR
- Enter the credentials manually

If successful, you should see:
```
Message sent! Response: {'id': 'wamid.xxxxx', 'status': 'sent'}
```

Check your WhatsApp for the message!

---

## Step 10: Deploy Your App to VPS (Required for Webhooks)

Before setting up webhooks, you need a public HTTPS URL. Follow these steps:

1. Deploy your Django app to your VPS (see `VPS_DEPLOYMENT_GUIDE.md`)
2. Make sure your app is running on HTTPS (use Let's Encrypt/Certbot)
3. Your webhook URL will be: `https://yourdomain.com/whatsapp/webhook/`
4. Make sure port 443 (HTTPS) is open in your firewall

---

## Step 11: Configure Webhook (5 minutes)

Once your app is deployed with HTTPS:

1. Go to your Meta App Dashboard
2. Click **"WhatsApp" → "Configuration"** in left sidebar
3. Find the **"Webhook"** section
4. Click **"Edit"** button

### Webhook Setup:

1. **Callback URL**: Enter your webhook URL
   ```
   https://yourdomain.com/whatsapp/webhook/
   ```

2. **Verify Token**: Enter the same value you set in `.env` for `WHATSAPP_VERIFY_TOKEN`
   ```
   my_secure_verify_token_123
   ```

3. Click **"Verify and Save"**
   - Meta will send a GET request to your webhook
   - If successful, you'll see a green checkmark ✅
   - If it fails, check:
     - Your server is running
     - HTTPS is working
     - Verify token matches exactly
     - URL is correct

4. **Subscribe to Webhook Fields**:
   - Check **"messages"** - to receive incoming messages
   - Optionally check:
     - `message_template_status_update` - for template status
     - `messaging_optins` - for user opt-ins
     - `messaging_optouts` - for user opt-outs

5. Click **"Save"**

---

## Step 12: Test Incoming Messages (2 minutes)

1. Open WhatsApp on your phone
2. Send a message to your WhatsApp Business number (the test number from Step 4D)
3. Try sending: `help`
4. You should receive a response with available commands!
5. Try adding an expense: `120 food lunch`
6. You should receive a confirmation message

---

## Step 13: Verify Your Business (For Production)

⚠️ **Important**: Test mode limits you to:
- 5 verified recipient numbers
- 1,000 conversations per month
- Limited features

To go live:

1. In your app dashboard, go to **"WhatsApp" → "Getting Started"**
2. Click **"Start Verification"** or **"Get Verified"**
3. You'll need:
   - Business website or Facebook Page
   - Business documents (registration, tax ID, etc.)
   - Phone number to verify
4. Follow the verification process (can take 1-3 days)
5. Once verified, you can:
   - Use your own phone number
   - Send to unlimited recipients
   - Access higher limits

---

## Troubleshooting

### Issue: "Access token is invalid"
**Solution**: 
- Regenerate token in Step 7
- Make sure you copied the entire token
- Check for extra spaces in .env file

### Issue: "Phone number not verified"
**Solution**: 
- Add your number in Step 5
- Complete WhatsApp verification
- Wait a few minutes after verification

### Issue: "Webhook verification failed"
**Solution**: 
- Verify token in .env matches exactly what you entered in Meta dashboard
- Check your Django server is running
- Ensure HTTPS is working (use `https://` not `http://`)
- Check server logs for errors

### Issue: "Message not received on WhatsApp"
**Solution**: 
- Check the phone number format (e.g., 919876543210, no + or spaces)
- Verify the number is added to test numbers (Step 5)
- Check your access token is valid
- Look at Django logs for error messages

### Issue: "Cannot send to this number"
**Solution**: 
- In test mode, you can only send to verified numbers (max 5)
- Add the number in Meta dashboard under "Phone Numbers"
- Wait for WhatsApp verification code and verify

---

## Quick Reference

### Required Credentials:
```
WHATSAPP_BUSINESS_ACCOUNT_ID = [from Meta Dashboard]
WHATSAPP_PHONE_NUMBER_ID = [from Meta Dashboard]
WHATSAPP_ACCESS_TOKEN = [from System User Token]
WHATSAPP_VERIFY_TOKEN = [any random string you create]
WEBHOOK_SECRET = [any random string you create]
```

### Important URLs:
- **Meta Developer Console**: https://developers.facebook.com/apps/
- **Business Settings**: https://business.facebook.com/settings/
- **WhatsApp API Docs**: https://developers.facebook.com/docs/whatsapp/cloud-api/
- **Webhook Setup Docs**: https://developers.facebook.com/docs/graph-api/webhooks/

### Testing Commands:
```bash
# Test configuration
python test_whatsapp_api.py

# Test Django server
python manage.py runserver

# View logs
tail -f debug.log
```

---

## Next Steps

1. ✅ Complete all setup steps above
2. ✅ Test sending and receiving messages
3. ✅ Configure webhook for incoming messages
4. ✅ Deploy to production VPS
5. ✅ Get business verified (for production use)
6. 📱 Start using WhatsApp to track expenses!

---

## Support

- **Meta Support**: https://developers.facebook.com/support/
- **WhatsApp Business API Docs**: https://developers.facebook.com/docs/whatsapp/
- **Community Forum**: https://developers.facebook.com/community/

---

**Congratulations! 🎉**

Your WhatsApp Cloud API is now set up and ready to use. You can track expenses via WhatsApp messages!

