# WhatsApp-Integrated Expense Tracking System

A WhatsApp-first expense tracking system that allows users to record daily expenses using WhatsApp messages and view statements and summaries directly inside WhatsApp, with a comprehensive web dashboard for analytics and management.

## 🚀 Features

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

## 📋 Prerequisites

- Python 3.8+
- WhatsApp Business Platform Account (Meta)
- Virtual environment (already created)

## 🛠️ Installation & Setup

### 1. Install Dependencies
Already installed:
- Django 5.2.9
- Django REST Framework
- python-decouple
- requests
- psycopg2-binary (for PostgreSQL in production)

### 2. Environment Configuration

Edit `.env` file with your WhatsApp Business API credentials:

```env
# WhatsApp Business API Configuration
WHATSAPP_API_URL=https://graph.facebook.com/v18.0
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_access_token
WHATSAPP_VERIFY_TOKEN=your_verify_token_for_webhook
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id
```

### 3. Create Superuser

```powershell
python manage.py createsuperuser
```

### 4. Run Development Server

```powershell
python manage.py runserver
```

Visit: http://127.0.0.1:8000

## 📱 WhatsApp Setup

### 1. Get WhatsApp Business API Access
1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create an app and add WhatsApp product
3. Get your Phone Number ID and Access Token
4. Add them to `.env` file

### 2. Configure Webhook
1. Set webhook URL: `https://your-domain.com/whatsapp/webhook/`
2. Set verify token (same as in `.env`)
3. Subscribe to message events

### 3. Test Integration
Send a message to your WhatsApp Business number:
```
120 petrol
```

Expected response:
```
✅ Recorded: ₹120 under 🚗 Travel
```

## 💬 WhatsApp Commands

### Adding Expenses
```
<amount> <category> [description]

Examples:
120 petrol
450 food lunch at restaurant
200 groceries vegetables
```

### Viewing Statements
```
today          - Today's expenses
week           - This week's expenses
month          - This month's expenses
summary        - Monthly summary by category
category food  - View expenses for specific category
```

### Other Commands
```
categories     - List all available categories
help           - Show help message
```

## 🌐 Web Dashboard

### Registration
1. Visit `/register/`
2. Create account with username, email, password
3. Provide WhatsApp number (with country code)

### Link WhatsApp
1. Login to dashboard
2. Click "Link WhatsApp"
3. Enter WhatsApp number
4. Receive OTP on WhatsApp
5. Verify OTP

### Features
- **Dashboard**: View expense overview and analytics
- **Expenses**: Add, view, delete expenses
- **Categories**: Manage expense categories
- **Reports**: Visual breakdown by category

## 📊 Project Structure

```
expense tracking system/
├── dashboard/              # Web dashboard app
│   ├── templates/         # HTML templates
│   ├── views.py          # Dashboard views
│   └── urls.py           # URL routing
├── expenses/              # Expense management
│   ├── models.py         # Category, Expense models
│   └── admin.py          # Admin configuration
├── users/                 # User management
│   ├── models.py         # User, WhatsAppMapping models
│   └── admin.py          # Admin configuration
├── whatsapp_integration/  # WhatsApp integration
│   ├── views.py          # Webhook handling
│   ├── whatsapp_service.py  # WhatsApp API client
│   ├── expense_handler.py   # Expense parsing & statements
│   └── urls.py           # Webhook routing
├── expense_tracker/       # Project settings
│   ├── settings.py       # Django settings
│   └── urls.py           # Main URL configuration
├── .env                   # Environment variables
├── requirements.txt       # Python dependencies
└── manage.py             # Django management script
```

## 🗄️ Database Models

### User
- Extended Django User model
- WhatsApp number and verification status
- OTP for verification
- Currency preferences

### WhatsAppMapping
- Maps WhatsApp numbers to users
- Enables quick lookup for incoming messages

### Category
- User-defined expense categories
- Icon and color customization
- Default categories created on registration

### Expense
- Individual expense entries
- Links to user and category
- Tracks source (WhatsApp/Web/API)
- Soft delete support

## 🚀 Deployment

### For Production:

1. **Update Settings**:
   - Set `DEBUG=False` in `.env`
   - Add your domain to `ALLOWED_HOSTS`
   - Use PostgreSQL instead of SQLite

2. **Database Migration**:
   ```powershell
   python manage.py migrate --settings=expense_tracker.settings
   ```

3. **Collect Static Files**:
   ```powershell
   python manage.py collectstatic
   ```

4. **Deploy to Cloud**:
   - AWS Elastic Beanstalk / EC2
   - DigitalOcean App Platform
   - Render
   - Heroku

5. **Set up SSL**:
   - WhatsApp webhooks require HTTPS
   - Use Let's Encrypt or cloud provider SSL

## 🔐 Security Best Practices

- Never commit `.env` file
- Use strong SECRET_KEY in production
- Enable HTTPS only
- Verify webhook signatures
- Rate limit webhook endpoint
- Regular database backups

## 📈 Future Enhancements

- [ ] Budget alerts via WhatsApp
- [ ] Family/team accounts
- [ ] Scheduled daily/weekly summaries
- [ ] Multi-language support
- [ ] AI-assisted natural language parsing
- [ ] Receipt photo upload
- [ ] Export to CSV/PDF
- [ ] Mobile app (React Native)
- [ ] Voice message support
- [ ] Recurring expenses

## 🐛 Troubleshooting

### WhatsApp messages not working?
- Check WhatsApp API credentials in `.env`
- Verify webhook is publicly accessible (HTTPS)
- Check webhook verification token matches
- Review logs: `python manage.py runserver` output

### Database errors?
- Run: `python manage.py makemigrations`
- Then: `python manage.py migrate`

### Can't login?
- Create superuser: `python manage.py createsuperuser`
- Or register via `/register/`

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review WhatsApp Business API documentation
3. Check Django error logs

## 📄 License

This project is for educational and personal use.

---

**Built with Django 5.2.9, WhatsApp Business Cloud API, and ❤️**
