# Deployment Guide - WhatsApp Expense Tracker

## Pre-Deployment Checklist

### 1. WhatsApp Business API Setup
- [ ] Create Meta Developer Account
- [ ] Create WhatsApp Business App
- [ ] Get Phone Number ID
- [ ] Get Permanent Access Token
- [ ] Note Business Account ID

### 2. Environment Configuration
- [ ] Update `.env` with production values
- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set strong `SECRET_KEY`
- [ ] Add WhatsApp API credentials

### 3. Database Setup
- [ ] Choose production database (PostgreSQL recommended)
- [ ] Create database
- [ ] Update database settings in `.env`

---

## Deployment Options

### Option 1: DigitalOcean App Platform (Recommended)

#### Step 1: Prepare Repository
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-repo-url>
git push -u origin main
```

#### Step 2: Create App
1. Go to DigitalOcean → Apps → Create App
2. Connect your GitHub repository
3. Select branch: `main`
4. Detect Python app automatically

#### Step 3: Configure Environment
Add environment variables in App Settings:
```
SECRET_KEY=<generate-strong-secret-key>
DEBUG=False
ALLOWED_HOSTS=.ondigitalocean.app,your-domain.com
DATABASE_URL=<provided-by-digitalocean>
WHATSAPP_API_URL=https://graph.facebook.com/v18.0
WHATSAPP_PHONE_NUMBER_ID=<your-phone-number-id>
WHATSAPP_ACCESS_TOKEN=<your-access-token>
WHATSAPP_VERIFY_TOKEN=<your-verify-token>
WHATSAPP_BUSINESS_ACCOUNT_ID=<your-business-account-id>
```

#### Step 4: Add Database
1. Add PostgreSQL database component
2. Note the connection string

#### Step 5: Deploy
1. Click "Deploy"
2. Wait for build to complete
3. Note your app URL

#### Step 6: Run Migrations
```bash
# Via DigitalOcean Console
python manage.py migrate
python manage.py createsuperuser
```

---

### Option 2: Render

#### Step 1: Create Web Service
1. Go to Render → New → Web Service
2. Connect repository
3. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn expense_tracker.wsgi:application`

#### Step 2: Add Environment Variables
Same as DigitalOcean above

#### Step 3: Add PostgreSQL
1. Create PostgreSQL database
2. Copy database URL
3. Add to environment variables

#### Step 4: Deploy
Auto-deploys on git push

---

### Option 3: AWS (Advanced)

#### Using Elastic Beanstalk

1. **Install EB CLI**:
```bash
pip install awsebcli
```

2. **Initialize**:
```bash
eb init -p python-3.10 expense-tracker
```

3. **Create Environment**:
```bash
eb create expense-tracker-env
```

4. **Configure Environment Variables**:
```bash
eb setenv SECRET_KEY=xxx DEBUG=False ALLOWED_HOSTS=xxx ...
```

5. **Deploy**:
```bash
eb deploy
```

---

## Post-Deployment Steps

### 1. Configure WhatsApp Webhook

1. Go to Meta Developer Console
2. WhatsApp → Configuration → Webhook
3. Set Callback URL: `https://your-domain.com/whatsapp/webhook/`
4. Set Verify Token: (same as in `.env`)
5. Subscribe to fields: `messages`

### 2. Test Webhook

Send test message to your WhatsApp Business number:
```
help
```

Expected response:
```
📱 Expense Tracker Commands
...
```

### 3. Create Admin User

```bash
python manage.py createsuperuser
```

### 4. Access Admin Panel

Visit: `https://your-domain.com/admin/`

### 5. Create Test User

1. Register: `https://your-domain.com/register/`
2. Login
3. Link WhatsApp number
4. Verify OTP

---

## SSL/HTTPS Setup

### DigitalOcean / Render
- Automatic SSL via Let's Encrypt
- Just add custom domain in settings

### AWS
```bash
# Request certificate via AWS Certificate Manager
# Add to Load Balancer
```

---

## Monitoring & Logging

### 1. Enable Django Logging

Add to `settings.py`:
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### 2. Monitor Webhook Logs
Check `/whatsapp/webhook/` logs for incoming messages

### 3. Set Up Error Tracking
- Sentry
- Rollbar
- CloudWatch (AWS)

---

## Scaling Considerations

### 1. Database Optimization
- Add indexes on frequently queried fields
- Use connection pooling
- Regular backups

### 2. Caching
```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379',
    }
}
```

### 3. Static Files
Use CDN for static files:
```python
# settings.py
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

### 4. Background Tasks
For scheduled reports, use Celery:
```bash
pip install celery redis
```

---

## Backup Strategy

### 1. Database Backups
```bash
# Daily automated backups
pg_dump dbname > backup_$(date +%Y%m%d).sql
```

### 2. Code Backups
- Use Git for version control
- Regular commits and pushes

---

## Security Hardening

### 1. Django Security Settings
```python
# settings.py (production)
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
```

### 2. Rate Limiting
```bash
pip install django-ratelimit
```

### 3. Firewall Rules
- Allow only ports 80 (HTTP), 443 (HTTPS)
- Whitelist Meta IP ranges for webhook

---

## Troubleshooting

### Webhook Not Receiving Messages
1. Check webhook URL is publicly accessible
2. Verify SSL certificate is valid
3. Check verify token matches
4. Review WhatsApp webhook logs

### Database Connection Issues
1. Check `DATABASE_URL` environment variable
2. Verify database credentials
3. Check network/firewall rules

### Static Files Not Loading
1. Run `python manage.py collectstatic`
2. Check `STATIC_ROOT` and `STATIC_URL` settings
3. Verify web server configuration

---

## Maintenance

### Regular Tasks
- [ ] Weekly database backups
- [ ] Monthly dependency updates
- [ ] Security patches
- [ ] Log review
- [ ] Performance monitoring

### Updates
```bash
# Update dependencies
pip install -r requirements.txt --upgrade

# Run migrations
python manage.py migrate

# Restart application
```

---

## Cost Estimates

### DigitalOcean App Platform
- Basic: $5/month (app) + $7/month (database) = **$12/month**

### Render
- Free tier available (with limitations)
- Paid: $7/month (app) + $7/month (database) = **$14/month**

### AWS
- Variable based on usage
- Estimated: **$15-30/month**

### WhatsApp Business API
- Free for first 1,000 conversations/month
- $0.005-0.05 per conversation after

---

**Ready for Production! 🚀**
