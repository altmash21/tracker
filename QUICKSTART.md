# Quick Start Guide - WhatsApp Expense Tracker

## 🚀 Getting Started (5 minutes)

### Step 1: Start the Development Server

```powershell
# Activate virtual environment (if not already active)
.\.venv\Scripts\Activate.ps1

# Run the server
python manage.py runserver
```

Open your browser: **http://127.0.0.1:8000**

---

### Step 2: Create an Account

1. Click **"Register"**
2. Fill in:
   - Username: `testuser`
   - Email: `test@example.com`
   - WhatsApp: `+919876543210` (use your actual number)
   - Password: `test123456`
3. Click **"Register"**

---

### Step 3: Login

1. Username: `testuser`
2. Password: `test123456`
3. Click **"Login"**

You'll see your dashboard with default categories already created!

---

### Step 4: Link WhatsApp (Optional - requires WhatsApp Business API)

**Note**: This requires WhatsApp Business API setup. Skip this step for now and use the web dashboard.

1. Click **"Link WhatsApp"** in navigation
2. Enter your WhatsApp number
3. You'll receive an OTP (requires API setup)
4. Verify the OTP

---

### Step 5: Add Your First Expense

#### Via Web Dashboard:
1. Go to **"Expenses"** page
2. Click **"Add New Expense"**
3. Fill in:
   - Amount: `120`
   - Category: `Travel` (🚗)
   - Description: `Petrol for bike`
   - Date: Today
4. Click **"Add"**

You'll see it appear in the expenses list!

---

### Step 6: View Dashboard

1. Go to **"Dashboard"**
2. See:
   - Today's total: ₹120
   - This week: ₹120
   - This month: ₹120
   - Category breakdown chart
   - Recent expenses

---

### Step 7: Manage Categories

1. Go to **"Categories"**
2. Add a new category:
   - Name: `Coffee`
   - Icon: `☕`
   - Color: Pick a color
3. Click **"Add"**

Now you can use this category for expenses!

---

## 📱 Using WhatsApp (After API Setup)

Once you've configured WhatsApp Business API:

### Add Expenses
Send messages like:
```
120 petrol
450 food lunch
200 coffee morning coffee
```

### View Statements
Send commands:
```
today
week
month
summary
category food
help
```

---

## 🔧 Admin Panel

### Access Admin
1. Create superuser:
```powershell
python manage.py createsuperuser
```

2. Visit: **http://127.0.0.1:8000/admin/**

3. Login with superuser credentials

### What You Can Do:
- View all users
- Manage categories
- View all expenses
- Check WhatsApp mappings

---

## 📊 Sample Data

### Add Some Test Expenses

```powershell
# Via Django shell
python manage.py shell
```

```python
from users.models import User
from expenses.models import Category, Expense
from datetime import datetime, timedelta

# Get your user
user = User.objects.get(username='testuser')

# Get categories
food = Category.objects.get(user=user, name='Food')
travel = Category.objects.get(user=user, name='Travel')
shopping = Category.objects.get(user=user, name='Shopping')

# Add expenses
Expense.objects.create(user=user, category=food, amount=250, description='Lunch', date=datetime.now().date())
Expense.objects.create(user=user, category=travel, amount=120, description='Petrol', date=datetime.now().date())
Expense.objects.create(user=user, category=shopping, amount=1500, description='Clothes', date=datetime.now().date() - timedelta(days=1))
Expense.objects.create(user=user, category=food, amount=180, description='Dinner', date=datetime.now().date() - timedelta(days=2))

print("Sample expenses added!")
```

Refresh your dashboard to see the data!

---

## 🧪 Testing WhatsApp Integration (Without API)

### Simulate Expense Parsing

```powershell
python manage.py shell
```

```python
from users.models import User
from whatsapp_integration.expense_handler import ExpenseParser, StatementGenerator

# Get user
user = User.objects.get(username='testuser')

# Test parser
parser = ExpenseParser(user)
result = parser.parse("120 petrol")
print(result)

# Test statement generator
generator = StatementGenerator(user)
print(generator.generate_today())
print(generator.generate_summary())
```

---

## 🐛 Common Issues & Solutions

### Issue: Port already in use
```powershell
# Use a different port
python manage.py runserver 8001
```

### Issue: Database locked
```powershell
# Close any other processes using the database
# Restart the server
```

### Issue: Static files not loading
```powershell
# Collect static files
python manage.py collectstatic --noinput
```

### Issue: Module not found
```powershell
# Reinstall requirements
pip install -r requirements.txt
```

---

## 📚 Next Steps

1. **WhatsApp Setup**: Follow `DEPLOYMENT.md` for WhatsApp Business API setup
2. **Customize**: Modify categories, colors, icons
3. **Explore**: Try different expense patterns
4. **Deploy**: Use DigitalOcean or Render for production

---

## 🎯 Key Features to Try

- [ ] Add expenses via web
- [ ] View dashboard analytics
- [ ] Create custom categories
- [ ] Filter expenses by date
- [ ] Delete expenses
- [ ] View category breakdown
- [ ] Link WhatsApp (requires API)
- [ ] Test webhook (requires API)

---

## 📞 Need Help?

Check:
1. **README.md** - Full documentation
2. **DEPLOYMENT.md** - Production deployment guide
3. Django admin logs
4. Browser console for errors

---

**Enjoy tracking your expenses! 💰**
