# WhatsApp Webhook Diagnosis - CRITICAL FIXES APPLIED

## ISSUES FOUND AND FIXED

### 🔴 CRITICAL ISSUE #1: URL Routing Conflict
**Problem:** You had TWO different webhook routes defined:
- `/whatsapp/webhook/` (via include)
- `/webhooks/whatsapp/` (direct route)

**Fix Applied:** Removed duplicate route. Now only `/whatsapp/webhook/` exists.

**Action Required:** Ensure Meta webhook URL is set to:
```
https://mytestapp.tech/whatsapp/webhook/
```

---

### 🔴 CRITICAL ISSUE #2: Signature Verification Blocking Requests
**Problem:** The webhook handler was IMMEDIATELY verifying the signature and returning HTTP 403 if it failed. This happened BEFORE any logging, so you had no visibility.

**Fix Applied:** Temporarily disabled signature verification with detailed comments. Added logging BEFORE verification.

**Why This Matters:** If `WEBHOOK_SECRET` is missing, misconfigured, or doesn't match Meta's app secret, ALL POST requests were silently rejected with 403.

---

### 🔴 CRITICAL ISSUE #3: No Early Request Logging
**Problem:** Logs only appeared AFTER signature verification passed.

**Fix Applied:** 
1. Added middleware that logs ALL requests to paths containing "whatsapp"
2. Added logging at the very start of the webhook view
3. Added logging of raw request body

**Result:** You'll now see logs even if the request fails early.

---

### ✅ ADDITIONAL DIAGNOSTIC TOOLS ADDED

1. **WebhookDebugMiddleware** - Catches ALL requests before any Django processing
2. **Test endpoint** at `/whatsapp/test/` - Verify routing works
3. **Enhanced logging** throughout the webhook flow

---

## TESTING STEPS (DO THESE IN ORDER)

### Step 1: Restart Gunicorn
```bash
sudo systemctl restart gunicorn
sudo systemctl status gunicorn
```

### Step 2: Test Django Routing (Confirm it reaches Django)
```bash
curl -X POST https://mytestapp.tech/whatsapp/test/ -H "Content-Type: application/json" -d '{"test": "data"}'
```

**Expected:** Should return JSON with `"status": "success"`

If this fails, the problem is Nginx/Gunicorn, NOT Django.

### Step 3: Check Logs
```bash
# Check Django logs
tail -f /path/to/your/debug.log

# Check Gunicorn logs
sudo journalctl -u gunicorn -f

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### Step 4: Send Test Webhook from Meta
In Meta Developer Console, click "Test" or "Send to server" button.

### Step 5: Watch for These Log Patterns

**If you see this - Django IS receiving the request:**
```
▶▶▶ MIDDLEWARE: Request to /whatsapp/webhook/
========== WEBHOOK REQUEST RECEIVED ==========
```

**If you see this - Signature verification was the issue:**
```
Signature verification SKIPPED (temporarily disabled)
Raw request body: {...}
```

**If you see NOTHING - Request never reached Django:**
- Check Nginx config
- Check Gunicorn socket
- Check firewall rules

---

## WHAT TO DO NEXT

### Scenario A: Logs Now Show Requests Arriving ✅
**This means signature verification was blocking you.**

To fix permanently:
1. Add `WEBHOOK_SECRET` to your settings (or .env file)
2. Get the App Secret from Meta Developer Console → App Settings → Basic
3. Set it: `WEBHOOK_SECRET = 'your_app_secret_from_meta'`
4. Re-enable signature verification in views.py (uncomment the lines)

### Scenario B: Still No Logs 🔴
**This means requests aren't reaching Django at all.**

Check these in order:
1. **Nginx config** - Is `/whatsapp/webhook/` proxied to Gunicorn?
2. **Gunicorn socket** - Is it running and connected?
3. **Meta webhook URL** - Exact match including trailing slash?
4. **Firewall** - Is port 443 open?
5. **DNS** - Does mytestapp.tech resolve correctly?

---

## NGINX CONFIGURATION CHECK

Your Nginx config should look like this:

```nginx
server {
    listen 443 ssl;
    server_name mytestapp.tech;

    # SSL config...

    location / {
        proxy_pass http://unix:/run/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Important:** The location block should handle ALL paths including `/whatsapp/webhook/`

---

## COMMON MISTAKES THAT ALLOW PAGES TO WORK BUT BLOCK WEBHOOKS

1. **CSRF middleware blocking POST requests** ✅ FIXED - Used `@csrf_exempt`
2. **Signature verification failing silently** ✅ FIXED - Temporarily disabled with logging
3. **URL path mismatch** ✅ FIXED - Removed duplicate routes
4. **Missing ALLOWED_HOSTS** - Check your settings.py includes your domain
5. **Wrong HTTP method** ✅ FIXED - View accepts both GET and POST
6. **Slow response (timeout)** ✅ FIXED - Returns 200 immediately before processing

---

## RE-ENABLING SECURITY (After Testing)

Once webhooks work, re-enable signature verification:

1. Add to settings.py or .env:
```python
WEBHOOK_SECRET = 'your_meta_app_secret_here'
```

2. In views.py, uncomment these lines:
```python
whatsapp_service = WhatsAppService()
if not whatsapp_service.verify_webhook_signature(request):
    logger.warning("Webhook signature verification failed")
    return HttpResponse('Signature verification failed', status=403)
```

3. Remove the "SKIPPED" log line

---

## FILE CHANGES SUMMARY

**Modified:**
- `expense_tracker/urls.py` - Removed duplicate route
- `whatsapp_integration/views.py` - Added logging, disabled signature verification temporarily
- `expense_tracker/settings.py` - Added webhook debug middleware
- `whatsapp_integration/urls.py` - Added test endpoint

**Created:**
- `whatsapp_integration/middleware.py` - Debug middleware for early request logging

**Next:** Test and monitor logs to identify exact failure point.
