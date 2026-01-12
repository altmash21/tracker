# WhatsApp-Integrated Expense Tracking System
## Complete Documentation & Setup Guide

**Last Updated:** January 12, 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Quick Start](#quick-start)
4. [System Architecture](#system-architecture)
5. [Installation & Setup](#installation--setup)
6. [WhatsApp Cloud API Setup](#whatsapp-cloud-api-setup)
7. [VPS Deployment Guide](#vps-deployment-guide)
8. [Webhook Configuration & Troubleshooting](#webhook-configuration--troubleshooting)
9. [API Reference](#api-reference)
10. [Project Status](#project-status)

---

## Overview

A WhatsApp-first expense tracking system that allows users to record daily expenses using WhatsApp messages and view statements and summaries directly inside WhatsApp, with a comprehensive web dashboard for analytics and management.

**Technology Stack:**
- Backend: Django 5.2.9
- Frontend: HTML, CSS, JavaScript
- Database: SQLite (development) / PostgreSQL (production)
- Integration: WhatsApp Business Cloud API (Meta)
- Deployment: Nginx + Gunicorn on Ubuntu VPS

---

## Features

### WhatsApp Integration
- ✅ Add expenses via simple WhatsApp messages (e.g., "120 petrol")
- ✅ View daily, weekly, monthly statements in WhatsApp
- ✅ Category-wise expense summaries
- ✅ Natural language parsing for easy entry
- ✅ Real-time confirmation messages

### Web Dashboard
- 📊 Interactive analytics and charts
- 💰 View expense totals (today, week, month)
- 📈 Category-wise breakdown with visual charts
- 📝 Add, edit, delete expenses via web interface
- 🏷️ Manage custom categories
- 📱 WhatsApp number linking and verification
- 📋 Export capabilities

### Security
- 🔒 Secure password hashing
- 🔐 WhatsApp OTP verification
- 🛡️ Webhook signature verification
- 🔑 Environment-based configuration
- ✅ CSRF protection

---

## Quick Start

### Prerequisites
- Python 3.8+
- WhatsApp Business Platform Account (Meta)
- Virtual environment

### Local Development (5 minutes)

#### Step 1: Install Dependencies

```powershell
# Create virtual environment (if not exists)
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

#### Step 2: Configure Environment

Create/edit `.env` file:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# WhatsApp Cloud API (Meta)
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_access_token
WHATSAPP_VERIFY_TOKEN=your_verify_token
WEBHOOK_SECRET=your_meta_app_secret

# Database (SQLite for development)
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
```

#### Step 3: Run Migrations

```powershell
python manage.py migrate
python manage.py create_default_categories
```

#### Step 4: Start Server

```powershell
python manage.py runserver
```

Open browser: **http://127.0.0.1:8000**

#### Step 5: Register & Link WhatsApp

1. Click **"Register"** and create account
2. Go to **Dashboard** → **Link WhatsApp**
3. Enter your WhatsApp number
4. Verify OTP sent via WhatsApp
5. Start sending expenses!

---

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERACTIONS                           │
│  ┌──────────────────┐              ┌──────────────────┐            │
│  │   WhatsApp App   │              │   Web Browser    │            │
│  │  • Send messages │              │  • Dashboard     │            │
│  │  • Receive msgs  │              │  • Manage data   │            │
│  └────────┬─────────┘              └────────┬─────────┘            │
└───────────┼─────────────────────────────────┼──────────────────────┘
            │                                 │
            ▼                                 ▼
┌───────────────────────────────────────────────────────────────────┐
│              WHATSAPP BUSINESS CLOUD API (Meta)                   │
└──────────────────────────┬────────────────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────────────────┐
│                      DJANGO APPLICATION                           │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐           │
│  │  Webhook    │  │  Dashboard   │  │  API Endpoints │           │
│  │  Handler    │  │  Views       │  │                │           │
│  └─────────────┘  └──────────────┘  └────────────────┘           │
│                                                                   │
│  ┌────────────────────────────────────────────────────┐          │
│  │              Business Logic Layer                  │          │
│  │  • ExpenseParser  • StatementGenerator             │          │
│  │  • WhatsAppService  • CategoryManager              │          │
│  └────────────────────────────────────────────────────┘          │
│                                                                   │
│  ┌────────────────────────────────────────────────────┐          │
│  │              Database Models                       │          │
│  │  • User  • Expense  • Category  • WhatsAppMapping  │          │
│  └────────────────────────────────────────────────────┘          │
└───────────────────────────────────────────────────────────────────┘
```

### Django Apps Structure

```
expense_tracker/           # Project root
├── dashboard/            # Web UI & authentication
│   ├── views.py         # Login, register, dashboard views
│   ├── urls.py          # Web routes
│   └── templates/       # HTML templates
│
├── users/               # User management
│   └── models.py        # User, WhatsAppMapping models
│
├── expenses/            # Expense tracking
│   ├── models.py        # Expense, Category models
│   └── management/      # CLI commands
│
├── whatsapp_integration/  # WhatsApp features
│   ├── views.py           # Webhook handler
│   ├── whatsapp_service.py # Meta API client
│   ├── expense_handler.py  # Message parser
│   └── middleware.py       # Debug middleware
│
└── expense_tracker/       # Project settings
    ├── settings.py
    └── urls.py
```

### Request Flow

#### 1. WhatsApp Message → Django
```
User sends "120 petrol"
    ↓
Meta Cloud API receives message
    ↓
Meta sends POST to /whatsapp/webhook/
    ↓
WebhookDebugMiddleware logs request
    ↓
whatsapp_webhook() view processes
    ↓
Signature verification (if enabled)
    ↓
ExpenseParser parses "120 petrol"
    ↓
Expense saved to database
    ↓
Confirmation sent via WhatsAppService
    ↓
Return HTTP 200 to Meta
```

#### 2. Web Dashboard Access
```
User visits /dashboard/
    ↓
AuthenticationMiddleware checks session
    ↓
dashboard_view() fetches expenses
    ↓
Template renders with charts
    ↓
HTML returned to browser
```

### Database Schema

```sql
-- Users
users_user:
  - id (PK)
  - username
  - email
  - password_hash
  - currency_symbol
  - created_at

-- WhatsApp Mapping
users_whatsappmapping:
  - id (PK)
  - user_id (FK → users_user)
  - whatsapp_number
  - verification_code
  - is_verified
  - is_active

-- Categories
expenses_category:
  - id (PK)
  - user_id (FK → users_user)
  - name
  - icon
  - is_active

-- Expenses
expenses_expense:
  - id (PK)
  - user_id (FK → users_user)
  - category_id (FK → expenses_category)
  - amount
  - description
  - date
  - source (whatsapp/web)
  - created_at
```

---

## Installation & Setup

### Development Setup

#### 1. Clone Repository
```bash
git clone <repository-url>
cd expense-tracking-system
```

#### 2. Create Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

#### 4. Configure Environment Variables
Create `.env` file in project root with all required settings (see Quick Start section)

#### 5. Run Migrations
```powershell
python manage.py migrate
python manage.py create_default_categories
```

#### 6. Create Superuser (Optional)
```powershell
python manage.py createsuperuser
```

#### 7. Run Development Server
```powershell
python manage.py runserver
```

### Production Setup

See [VPS Deployment Guide](#vps-deployment-guide) section below.

---

## WhatsApp Cloud API Setup

### Step 1: Create Meta Developer Account

1. Go to https://developers.facebook.com
2. Create account or login
3. Click **"My Apps"** → **"Create App"**
4. Select **"Business"** type
5. Fill in app details

### Step 2: Add WhatsApp Product

1. In your app dashboard, click **"Add Product"**
2. Find **"WhatsApp"** and click **"Set Up"**
3. Select **"Business Account"** or create new one

### Step 3: Get API Credentials

#### Business Account ID
- WhatsApp → Getting Started → Copy Business Account ID

#### Phone Number ID
- WhatsApp → Getting Started → Copy Phone Number ID

#### Access Token
- WhatsApp → Getting Started → Copy temporary token
- For production: Create permanent token in System Users

#### Verify Token
- Create your own random string (e.g., "my_secure_verify_token_2024")
- Save this for webhook configuration

#### App Secret
- Settings → Basic → Show App Secret → Copy

### Step 4: Configure Webhook

1. WhatsApp → Configuration → Edit webhook
2. **Callback URL:** `https://yourdomain.com/whatsapp/webhook/`
3. **Verify Token:** (the token you created above)
4. Click **"Verify and Save"**

### Step 5: Subscribe to Webhook Fields

In Webhook configuration, enable:
- ✅ **messages** (required for receiving messages)

### Step 6: Add Phone Numbers to Whitelist

During development (Test Mode):
1. WhatsApp → Getting Started → Add recipient phone numbers
2. Enter phone numbers that can send/receive messages

### Step 7: Update Django Settings

Add to `.env`:
```env
WHATSAPP_BUSINESS_ACCOUNT_ID=123456789012345
WHATSAPP_PHONE_NUMBER_ID=987654321098765
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxxxxx
WHATSAPP_VERIFY_TOKEN=my_secure_verify_token_2024
WEBHOOK_SECRET=your_app_secret_here
```

### Step 8: Test the Integration

1. Register on your website
2. Link WhatsApp number in dashboard
3. Send message to your WhatsApp Business number: `"50 food lunch"`
4. Check logs for processing
5. Should receive confirmation

---

## VPS Deployment Guide

### Prerequisites

- Ubuntu 20.04+ VPS
- Domain name with DNS configured
- SSH access to server

### Step 1: Prepare Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3-pip python3-venv nginx git -y

# Install PostgreSQL (optional)
sudo apt install postgresql postgresql-contrib -y
```

### Step 2: Create Project User

```bash
sudo adduser expense_tracker
sudo usermod -aG sudo expense_tracker
su - expense_tracker
```

### Step 3: Clone & Setup Project

```bash
# Clone repository
git clone <repository-url>
cd expense-tracking-system

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

### Step 4: Configure Environment

```bash
nano .env
```

Add production settings:
```env
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

WHATSAPP_BUSINESS_ACCOUNT_ID=your_id
WHATSAPP_PHONE_NUMBER_ID=your_id
WHATSAPP_ACCESS_TOKEN=your_token
WHATSAPP_VERIFY_TOKEN=your_verify_token
WEBHOOK_SECRET=your_app_secret

# PostgreSQL (if using)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=expense_tracker_db
DB_USER=expense_tracker_user
DB_PASSWORD=secure_password
DB_HOST=localhost
DB_PORT=5432
```

### Step 5: Setup PostgreSQL (Optional)

```bash
sudo -u postgres psql

# In PostgreSQL shell:
CREATE DATABASE expense_tracker_db;
CREATE USER expense_tracker_user WITH PASSWORD 'secure_password';
ALTER ROLE expense_tracker_user SET client_encoding TO 'utf8';
ALTER ROLE expense_tracker_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE expense_tracker_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE expense_tracker_db TO expense_tracker_user;
\q
```

### Step 6: Run Migrations

```bash
python manage.py migrate
python manage.py create_default_categories
python manage.py collectstatic --noinput
```

### Step 7: Configure Gunicorn

Create systemd service file:
```bash
sudo nano /etc/systemd/system/gunicorn.service
```

Add:
```ini
[Unit]
Description=Gunicorn daemon for expense tracker
After=network.target

[Service]
User=expense_tracker
Group=www-data
WorkingDirectory=/home/expense_tracker/expense-tracking-system
Environment="PATH=/home/expense_tracker/expense-tracking-system/.venv/bin"
ExecStart=/home/expense_tracker/expense-tracking-system/.venv/bin/gunicorn \
          --workers 3 \
          --bind unix:/run/gunicorn.sock \
          expense_tracker.wsgi:application

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
sudo systemctl status gunicorn
```

### Step 8: Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/expense_tracker
```

Add:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://unix:/run/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /home/expense_tracker/expense-tracking-system/staticfiles/;
    }

    location /media/ {
        alias /home/expense_tracker/expense-tracking-system/media/;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/expense_tracker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 9: Setup SSL with Certbot

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Follow prompts. Certbot will auto-configure HTTPS.

### Step 10: Configure Firewall

```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
```

### Step 11: Test Deployment

1. Visit https://yourdomain.com
2. Register account
3. Link WhatsApp
4. Send test message
5. Check logs: `sudo journalctl -u gunicorn -f`

---

## Webhook Configuration & Troubleshooting

### Common Webhook Issues & Solutions

#### Issue 1: Webhook Not Receiving POST Requests

**Symptoms:**
- Website loads correctly
- Clicking "Test" in Meta shows no logs in Django
- No errors visible

**Root Causes & Fixes:**

##### A. Signature Verification Blocking Requests ⚠️

**Problem:** Django code verifies `X-Hub-Signature-256` header. If `WEBHOOK_SECRET` is missing/wrong, ALL requests get HTTP 403 silently.

**Solution:**
1. Temporarily disable signature verification in `whatsapp_integration/views.py`:
   ```python
   # Comment out these lines:
   # whatsapp_service = WhatsAppService()
   # if not whatsapp_service.verify_webhook_signature(request):
   #     return HttpResponse('Signature verification failed', status=403)
   ```

2. Test webhook - should now work
3. Get App Secret from Meta: Developer Console → Settings → Basic
4. Add to `.env`: `WEBHOOK_SECRET=your_app_secret_here`
5. Re-enable signature verification
6. Restart Gunicorn

##### B. URL Routing Conflicts

**Problem:** Multiple webhook routes causing confusion.

**Solution:** Ensure only ONE webhook route exists in `expense_tracker/urls.py`:
```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('whatsapp/', include('whatsapp_integration.urls')),  # This creates /whatsapp/webhook/
    path('', include('dashboard.urls')),
]
```

##### C. Missing Early Logging

**Problem:** Can't see if requests reach Django.

**Solution:** Added `WebhookDebugMiddleware` that logs ALL webhook requests before any processing.

Check logs:
```bash
tail -f /path/to/debug.log
# or
sudo journalctl -u gunicorn -f
```

Look for:
```
▶▶▶ MIDDLEWARE: Request to /whatsapp/webhook/
========== WEBHOOK REQUEST RECEIVED ==========
```

#### Issue 2: Webhook Returns Non-200 Status

**Problem:** Meta expects HTTP 200 within 5 seconds or retries webhook.

**Symptoms:**
- Duplicate expenses
- Message loops
- Meta shows errors

**Solution:** All webhook responses now return 200:
```python
# Success
return JsonResponse({'status': 'success'}, status=200)

# Errors (still return 200 to prevent retries)
return JsonResponse({'status': 'error'}, status=200)
```

#### Issue 3: Nginx Not Proxying Webhook Requests

**Check Nginx config:**
```bash
sudo nginx -t
sudo cat /etc/nginx/sites-enabled/expense_tracker
```

Should include:
```nginx
location / {
    proxy_pass http://unix:/run/gunicorn.sock;
    # Headers required for webhook signature verification
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

#### Issue 4: Gunicorn Not Running

**Check status:**
```bash
sudo systemctl status gunicorn
```

**View logs:**
```bash
sudo journalctl -u gunicorn -n 50
```

**Restart:**
```bash
sudo systemctl restart gunicorn
```

### Diagnostic Steps (In Order)

#### Step 1: Test Basic Routing
```bash
curl -X POST https://yourdomain.com/whatsapp/test/
```
Expected: `{"status": "success"}`

If fails → Problem is Nginx/Gunicorn, not Django

#### Step 2: Check Django Logs
```bash
tail -f /path/to/debug.log
```

Send test from Meta. Look for:
- `▶▶▶ MIDDLEWARE: Request to /whatsapp/webhook/` (proves request arrived)
- `========== WEBHOOK REQUEST RECEIVED ==========`
- `Raw request body: {...}`

#### Step 3: Verify Meta Configuration

In Meta Developer Console:
- Webhook URL: `https://yourdomain.com/whatsapp/webhook/` (exact match)
- Verify Token: Matches `WHATSAPP_VERIFY_TOKEN` in .env
- Subscribed to: `messages` field

#### Step 4: Test Signature Verification

If signature is enabled, verify:
```python
# In .env
WEBHOOK_SECRET=your_actual_app_secret_from_meta
```

Get from: Meta Console → Settings → Basic → App Secret

#### Step 5: Check ALLOWED_HOSTS

In `.env`:
```env
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

Must match exactly.

### Testing Checklist

- [ ] Gunicorn running: `sudo systemctl status gunicorn`
- [ ] Nginx running: `sudo systemctl status nginx`
- [ ] SSL valid: Visit https://yourdomain.com
- [ ] Webhook URL correct in Meta
- [ ] `ALLOWED_HOSTS` includes domain
- [ ] `CSRF_TRUSTED_ORIGINS` includes https://yourdomain.com
- [ ] Test endpoint works: `curl https://yourdomain.com/whatsapp/test/`
- [ ] Logs show middleware catching requests
- [ ] Signature verification disabled for initial testing
- [ ] Return 200 on all webhook responses

---

## API Reference

### WhatsApp Commands

#### Add Expense
```
<amount> <category> [description]

Examples:
50 food
120 petrol tank full
450 groceries weekly shopping
```

#### View Statements
```
today          - Today's expenses
week           - This week's expenses
month          - This month's expenses
summary        - Monthly summary with totals
category food  - All food expenses
```

#### Other Commands
```
categories     - List all available categories
help           - Show help message
```

### Web Dashboard Routes

```
/                      - Landing page
/register/             - User registration
/login/                - User login
/logout/               - User logout
/dashboard/            - Main dashboard
/dashboard/expenses/   - Expense management
/dashboard/categories/ - Category management
/link-whatsapp/        - WhatsApp linking
/verify-whatsapp/      - OTP verification
```

### Webhook Endpoints

```
GET  /whatsapp/webhook/  - Webhook verification (Meta)
POST /whatsapp/webhook/  - Message handling
POST /whatsapp/test/     - Test routing (debug)
```

---

## Project Status

### ✅ Completed Features

#### Core Functionality
- [x] User registration and authentication
- [x] WhatsApp number linking with OTP
- [x] Expense tracking (web + WhatsApp)
- [x] Category management
- [x] Dashboard with analytics

#### WhatsApp Integration
- [x] Meta Cloud API integration
- [x] Webhook handler with signature verification
- [x] Natural language expense parsing
- [x] Statement generation (daily/weekly/monthly)
- [x] Real-time message responses
- [x] Error handling and validation

#### Deployment
- [x] VPS deployment with Nginx + Gunicorn
- [x] SSL/HTTPS configuration
- [x] Environment-based configuration
- [x] Production-ready logging
- [x] Database migrations
- [x] Static file serving

#### Recent Fixes (January 12, 2026)
- [x] Fixed duplicate webhook URL routes
- [x] Added webhook debug middleware
- [x] Temporarily disabled signature verification for testing
- [x] Added comprehensive logging throughout webhook flow
- [x] Fixed webhook responses to always return HTTP 200
- [x] Added JSON decode error handling
- [x] Created complete unified documentation

### 🔄 Known Issues

1. **Signature Verification:** Temporarily disabled - needs to be re-enabled with proper `WEBHOOK_SECRET` after testing
2. **WhatsApp Test Mode:** Limited to whitelisted phone numbers until app is approved by Meta

### 📋 Future Enhancements

- [ ] Recurring expense tracking
- [ ] Budget limits and alerts
- [ ] Multi-currency support
- [ ] Export to CSV/Excel
- [ ] Mobile app (React Native)
- [ ] Voice message expense entry
- [ ] Receipt image parsing with OCR
- [ ] Shared expense groups
- [ ] Monthly budget planning
- [ ] Expense categories with subcategories
- [ ] Advanced analytics and reports

---

## Support & Maintenance

### Logs Location

**Development:**
- `debug.log` in project root
- Console output

**Production:**
- Gunicorn: `sudo journalctl -u gunicorn`
- Nginx Access: `/var/log/nginx/access.log`
- Nginx Error: `/var/log/nginx/error.log`
- Application: `/home/expense_tracker/expense-tracking-system/debug.log`

### Common Commands

**Restart Services:**
```bash
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

**View Logs:**
```bash
# Gunicorn
sudo journalctl -u gunicorn -f

# Django
tail -f /path/to/debug.log

# Nginx
sudo tail -f /var/log/nginx/error.log
```

**Update Code:**
```bash
cd /home/expense_tracker/expense-tracking-system
git pull
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
```

### Database Backups

```bash
# SQLite
cp db.sqlite3 db.sqlite3.backup

# PostgreSQL
pg_dump expense_tracker_db > backup.sql
```

---

## License

MIT License - See LICENSE file for details

---

## Contributors

- Primary Developer: [Your Name]
- Documentation: AI Assistant
- Framework: Django Community

---

**End of Documentation**

For issues or questions, check the troubleshooting section or review the detailed logs.
