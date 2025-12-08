# ⚡ Quick Reference Card - WhatsApp Expense Tracker

## 🚀 Essential Commands

### Start Server
```powershell
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```
**URL:** http://127.0.0.1:8000

### Create Demo User
```powershell
python setup_demo.py
```
**Login:** demo / demo123

### Create Admin
```powershell
python manage.py createsuperuser
```
**URL:** http://127.0.0.1:8000/admin/

---

## 📱 WhatsApp Commands (Once API is setup)

| Command | Example | Result |
|---------|---------|--------|
| Add expense | `120 petrol` | ✅ Recorded: ₹120 under 🚗 Travel |
| Today | `today` | 📊 Today's Expenses... |
| Week | `week` | 📊 This Week's Expenses... |
| Month | `month` | 📊 This Month's Expenses... |
| Summary | `summary` | 📊 Monthly Summary... |
| Category | `category food` | 📊 Food - Last 30 Days... |
| List | `categories` | 📂 Your Categories: 🍔 Food... |
| Help | `help` | 📱 Expense Tracker Commands... |

---

## 🌐 Web URLs

| Page | URL | Purpose |
|------|-----|---------|
| Home | `/` | Landing page |
| Login | `/login/` | User login |
| Register | `/register/` | Create account |
| Dashboard | `/dashboard/` | Main analytics |
| Expenses | `/expenses/` | Manage expenses |
| Categories | `/categories/` | Manage categories |
| Link WhatsApp | `/link-whatsapp/` | Connect WhatsApp |
| Verify | `/verify-whatsapp/` | Enter OTP |
| Admin | `/admin/` | Django admin |

---

## 📂 Key Files

| File | Purpose |
|------|---------|
| `manage.py` | Django management |
| `requirements.txt` | Dependencies |
| `.env` | Environment variables (SECRET!) |
| `setup_demo.py` | Create demo data |
| `README.md` | Full documentation |
| `QUICKSTART.md` | 5-min guide |
| `DEPLOYMENT.md` | Deploy guide |
| `WHATSAPP_SETUP.md` | API setup |

---

## 🔧 Management Commands

```powershell
# Database
python manage.py makemigrations
python manage.py migrate
python manage.py dbshell

# Users
python manage.py createsuperuser
python manage.py changepassword <username>

# Custom
python manage.py create_default_categories

# Development
python manage.py shell
python manage.py check
python manage.py runserver 0.0.0.0:8000
```

---

## 🗄️ Database Models

```python
# Users
User                # username, email, whatsapp_number
WhatsAppMapping     # whatsapp_number → user

# Expenses
Category            # name, icon, color
Expense             # amount, date, category, user
```

---

## 🔐 Environment Variables (.env)

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

WHATSAPP_API_URL=https://graph.facebook.com/v18.0
WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
WHATSAPP_ACCESS_TOKEN=your-access-token
WHATSAPP_VERIFY_TOKEN=your-verify-token
WHATSAPP_BUSINESS_ACCOUNT_ID=your-business-id
```

---

## 📊 Default Categories

| Icon | Name | Color |
|------|------|-------|
| 🍔 | Food | #FF6B6B |
| 🚗 | Travel | #4ECDC4 |
| 🛍️ | Shopping | #95E1D3 |
| 📄 | Bills | #F38181 |
| 🎬 | Entertainment | #AA96DA |
| 💊 | Health | #FCBAD3 |
| 🛒 | Groceries | #A8D8EA |
| 📚 | Education | #FFDEB4 |

---

## 🐛 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Port in use | `python manage.py runserver 8001` |
| Module not found | `pip install -r requirements.txt` |
| Database locked | Close other processes, restart |
| Static files missing | `python manage.py collectstatic` |
| Migration error | `python manage.py migrate --fake` |
| Server won't start | Check `.env` file exists |

---

## 📈 Testing URLs

```powershell
# Home page
http://127.0.0.1:8000/

# API endpoints
http://127.0.0.1:8000/whatsapp/webhook/
http://127.0.0.1:8000/admin/

# Test data
python setup_demo.py
```

---

## 🎯 Quick Feature Test

1. ✅ Visit http://127.0.0.1:8000
2. ✅ Click "Register"
3. ✅ Create account (testuser / test@example.com)
4. ✅ Login
5. ✅ View dashboard (default categories created)
6. ✅ Go to "Expenses"
7. ✅ Add expense (120 / Travel / Petrol / Today)
8. ✅ View updated dashboard
9. ✅ Go to "Categories"
10. ✅ Add custom category (☕ Coffee / #FFA500)

---

## 📱 WhatsApp Integration Status

| Feature | Status |
|---------|--------|
| Webhook endpoint | ✅ Ready |
| Message parser | ✅ Ready |
| Statement generator | ✅ Ready |
| API service | ✅ Ready |
| OTP system | ✅ Ready |
| **Needs:** Meta API setup | ⏳ Pending |

---

## 🚀 Deployment Checklist

- [ ] Register for WhatsApp Business API
- [ ] Get Phone Number ID & Access Token
- [ ] Choose hosting (DigitalOcean/Render/AWS)
- [ ] Create PostgreSQL database
- [ ] Set environment variables
- [ ] Deploy code
- [ ] Run migrations
- [ ] Configure webhook URL
- [ ] Test end-to-end
- [ ] Set up SSL certificate
- [ ] Configure domain
- [ ] Enable monitoring

---

## 💡 Pro Tips

1. **Always activate venv** before running commands
2. **Backup .env** before making changes
3. **Test locally** before deploying
4. **Use PostgreSQL** in production
5. **Enable DEBUG=False** in production
6. **Set strong SECRET_KEY** for production
7. **Check logs** when debugging
8. **Use admin panel** for quick data management

---

## 📞 Quick Links

- **Documentation:** All `.md` files in root
- **Django Docs:** https://docs.djangoproject.com/
- **WhatsApp API:** https://developers.facebook.com/docs/whatsapp
- **Meta Developer:** https://developers.facebook.com/

---

## 🎊 You're All Set!

**Everything is working and ready to use!**

Just need to:
1. Try it locally (already running!)
2. Set up WhatsApp API (see WHATSAPP_SETUP.md)
3. Deploy to production (see DEPLOYMENT.md)

**Happy coding! 💰📱✨**
