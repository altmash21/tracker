# XPENSEDIARY - WhatsApp-Integrated Expense Tracking System

XPENSEDIARY is a WhatsApp-first expense tracker with a modern multi-page dashboard, OTP-based authentication, budget management, receipt OCR, and AI-assisted categorization.

## Features

### WhatsApp Integration
- Add expenses using simple messages like `120 petrol`.
- Get statements directly in WhatsApp (`today`, `week`, `month`, `summary`).
- Natural-language expense parsing and confirmation responses.
- WhatsApp number linking and OTP verification.

### Dashboard Experience
- Dedicated pages for Dashboard, Analytics, Transactions, Budget, and Settings.
- Category breakdown and monthly trends.
- Transaction history with filters, pagination, and CSV export.
- Category-level monthly budgets and utilization tracking.
- Receipt upload workflow from dashboard.

### AI and OCR
- Google Vision OCR support for receipt text extraction.
- Gemini-based categorization for text and image receipts.
- Fallback logic:
  - If Gemini key is missing, keyword-based categorization is used.
  - If Gemini quota is exhausted (`429` / `RESOURCE_EXHAUSTED`), fallback is applied.

### Security and Reliability
- Django auth with OTP login flow.
- Webhook verification and environment-driven secrets.
- CSRF protection and soft-delete support for expenses.

## Prerequisites

- Python 3.10+ (recommended: 3.11+)
- WhatsApp Business Platform account (Meta)
- Google Cloud project (for Vision OCR)
- Google AI Studio API key (for Gemini)

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py create_default_categories
python manage.py runserver
```

Open: http://127.0.0.1:8000

## Environment Configuration

Create or update `.env` in project root:

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1

# WhatsApp Cloud API
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_access_token
WHATSAPP_VERIFY_TOKEN=your_verify_token
WEBHOOK_SECRET=your_meta_app_secret

# AI / OCR
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
GEMINI_API_KEY=your_gemini_api_key

# Database (default SQLite)
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
```

## WhatsApp Setup

1. Create a Meta app and add WhatsApp product at https://developers.facebook.com/
2. Copy `WHATSAPP_BUSINESS_ACCOUNT_ID`, `WHATSAPP_PHONE_NUMBER_ID`, and token.
3. Configure webhook callback:
   - `https://your-domain.com/whatsapp/webhook/`
4. Use the same verify token in Meta and `.env`.
5. Subscribe to `messages` webhook field.

## AI and OCR Setup

### Google Vision
1. Enable Vision API in Google Cloud.
2. Create service account key JSON.
3. Set `GOOGLE_APPLICATION_CREDENTIALS` to that JSON path.

### Gemini
1. Generate API key in Google AI Studio.
2. Set `GEMINI_API_KEY` in `.env`.

## Main Routes

- `/login/` - WhatsApp OTP login
- `/register/` - account registration
- `/dashboard/` - overview page
- `/analytics/` - trend and category analytics
- `/transactions/` - transaction ledger
- `/transactions/export/` - CSV export
- `/budget/` - category budget tracking
- `/settings/` - profile/preferences/WhatsApp settings
- `/link-whatsapp/` - WhatsApp linking flow
- `/verify-whatsapp/` - WhatsApp OTP verification

## Database Models

- `User` - extended auth user with WhatsApp fields and currency fields
- `WhatsAppMapping` - maps incoming WhatsApp numbers to users
- `Category` - user categories with icon and color
- `Expense` - expense entries with source and soft delete
- `Receipt` - uploaded receipt and processing metadata
- `Budget` - monthly category budget per user

## Useful Commands

```powershell
# Run Django checks
python manage.py check

# Apply migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Gemini test script
python test_gemini_api.py
```

## Troubleshooting

### WhatsApp webhook not receiving messages
- Verify callback URL and token in Meta.
- Ensure public HTTPS endpoint is reachable.
- Confirm `WEBHOOK_SECRET` and access token are correct.

### Vision OCR fails
- Check `GOOGLE_APPLICATION_CREDENTIALS` path exists and is readable.
- Ensure Vision API is enabled for the same GCP project.

### Gemini fails or rate-limited
- Validate `GEMINI_API_KEY`.
- If you hit quota limits, fallback categorization is used for text paths.

### Auth or OTP issues
- Ensure WhatsApp number is stored with country code.
- Retry OTP from login/link flow pages.

## Tech Stack

- Django 5.2.9
- Django REST Framework
- Google Cloud Vision
- Google GenAI (`google-genai>=1.0.0`)
- WhatsApp Business Cloud API

## License

For educational and personal use.
