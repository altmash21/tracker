"""
Script to create a test user with sample expenses for demonstration
Usage: python setup_demo.py
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expense_tracker.settings')
django.setup()

from users.models import User, WhatsAppMapping
from expenses.models import Category, Expense


def create_demo_user():
    """Create a demo user with sample data"""
    
    print("🚀 Creating demo user and sample data...\n")
    
    # Create demo user
    username = "demo"
    email = "demo@example.com"
    password = "demo123"
    whatsapp_number = "+919876543210"
    
    # Check if user exists
    if User.objects.filter(username=username).exists():
        print(f"⚠️  User '{username}' already exists!")
        user = User.objects.get(username=username)
    else:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            whatsapp_number=whatsapp_number
        )
        print(f"✅ Created user: {username}")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   WhatsApp: {whatsapp_number}\n")
    
    # Create default categories if not exist
    default_categories = [
        ('Food', '🍔', '#FF6B6B'),
        ('Travel', '🚗', '#4ECDC4'),
        ('Shopping', '🛍️', '#95E1D3'),
        ('Bills', '📄', '#F38181'),
        ('Entertainment', '🎬', '#AA96DA'),
        ('Health', '💊', '#FCBAD3'),
        ('Groceries', '🛒', '#A8D8EA'),
        ('Education', '📚', '#FFDEB4'),
    ]
    
    categories_created = 0
    for name, icon, color in default_categories:
        _, created = Category.objects.get_or_create(
            user=user,
            name=name,
            defaults={'icon': icon, 'color': color, 'is_default': True}
        )
        if created:
            categories_created += 1
    
    if categories_created > 0:
        print(f"✅ Created {categories_created} default categories\n")
    else:
        print(f"ℹ️  Categories already exist\n")
    
    # Create sample expenses for the last 7 days
    sample_expenses = [
        # Today
        ('Food', 250, 'Lunch at restaurant', 0),
        ('Travel', 120, 'Petrol', 0),
        ('Groceries', 450, 'Weekly groceries', 0),
        
        # Yesterday
        ('Food', 180, 'Dinner', 1),
        ('Entertainment', 500, 'Movie tickets', 1),
        
        # 2 days ago
        ('Shopping', 1500, 'New clothes', 2),
        ('Food', 200, 'Breakfast', 2),
        
        # 3 days ago
        ('Bills', 2000, 'Electricity bill', 3),
        ('Travel', 150, 'Auto fare', 3),
        
        # 4 days ago
        ('Health', 350, 'Medicine', 4),
        ('Food', 280, 'Lunch', 4),
        
        # 5 days ago
        ('Groceries', 600, 'Vegetables and fruits', 5),
        ('Travel', 100, 'Bus fare', 5),
        
        # 6 days ago
        ('Entertainment', 300, 'Gaming subscription', 6),
        ('Food', 220, 'Dinner', 6),
    ]
    
    expenses_created = 0
    for cat_name, amount, description, days_ago in sample_expenses:
        category = Category.objects.get(user=user, name=cat_name)
        date = datetime.now().date() - timedelta(days=days_ago)
        
        # Only create if doesn't exist
        if not Expense.objects.filter(user=user, category=category, amount=amount, date=date).exists():
            Expense.objects.create(
                user=user,
                category=category,
                amount=amount,
                description=description,
                date=date,
                source='web'
            )
            expenses_created += 1
    
    if expenses_created > 0:
        print(f"✅ Created {expenses_created} sample expenses\n")
    else:
        print(f"ℹ️  Sample expenses already exist\n")
    
    # Calculate totals
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    
    today_total = Expense.objects.filter(user=user, date=today).aggregate(
        total=django.db.models.Sum('amount')
    )['total'] or 0
    
    week_total = Expense.objects.filter(user=user, date__gte=week_start).aggregate(
        total=django.db.models.Sum('amount')
    )['total'] or 0
    
    print("📊 Summary:")
    print(f"   Today's expenses: ₹{today_total}")
    print(f"   This week's expenses: ₹{week_total}")
    print(f"   Total expenses: ₹{Expense.objects.filter(user=user).aggregate(total=django.db.models.Sum('amount'))['total'] or 0}\n")
    
    print("🎉 Demo setup complete!")
    print("\n📝 Login credentials:")
    print(f"   URL: http://127.0.0.1:8000/login/")
    print(f"   Username: {username}")
    print(f"   Password: {password}")
    print("\n✨ You can now explore the dashboard with sample data!")


if __name__ == "__main__":
    try:
        create_demo_user()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
