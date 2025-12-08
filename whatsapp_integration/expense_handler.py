import re
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from expenses.models import Category, Expense

logger = logging.getLogger(__name__)


class ExpenseParser:
    """Parse natural language expense messages from WhatsApp"""
    
    def __init__(self, user):
        self.user = user
        self.currency_symbol = user.currency_symbol
    
    def parse(self, message):
        """
        Parse expense message in format: <amount> <category> [description]
        Examples:
            - "120 petrol"
            - "450 groceries bought vegetables"
            - "200 food dinner at restaurant"
        """
        message = message.strip()
        
        # Pattern: number followed by category name
        pattern = r'^(\d+(?:\.\d{1,2})?)\s+(\w+)(?:\s+(.+))?$'
        match = re.match(pattern, message, re.IGNORECASE)
        
        if not match:
            return None
        
        amount_str, category_name, description = match.groups()
        amount = float(amount_str)
        description = description or ""
        
        # Find matching category (case-insensitive)
        category = Category.objects.filter(
            user=self.user,
            name__iexact=category_name,
            is_active=True
        ).first()
        
        if not category:
            # Try fuzzy matching with common categories
            category = self._find_similar_category(category_name)
        
        if not category:
            return {
                'error': 'category_not_found',
                'message': f"Category '{category_name}' not found. Available categories: {self._get_category_list()}"
            }
        
        return {
            'amount': amount,
            'category': category,
            'description': description.strip(),
            'date': timezone.now().date()
        }
    
    def _find_similar_category(self, category_name):
        """Try to find similar category name"""
        categories = Category.objects.filter(user=self.user, is_active=True)
        
        # Common aliases
        aliases = {
            'food': ['eat', 'lunch', 'dinner', 'breakfast', 'snack', 'meal'],
            'travel': ['transport', 'taxi', 'uber', 'bus', 'train', 'petrol', 'fuel'],
            'shopping': ['shop', 'clothes', 'buy'],
            'groceries': ['grocery', 'vegetables', 'fruits', 'market'],
            'entertainment': ['movie', 'cinema', 'game', 'fun'],
            'health': ['medical', 'doctor', 'medicine', 'hospital'],
            'bills': ['electricity', 'water', 'internet', 'mobile'],
        }
        
        category_name_lower = category_name.lower()
        
        for category in categories:
            cat_name_lower = category.name.lower()
            
            # Exact match
            if cat_name_lower == category_name_lower:
                return category
            
            # Check aliases
            if cat_name_lower in aliases:
                if category_name_lower in aliases[cat_name_lower]:
                    return category
        
        return None
    
    def _get_category_list(self):
        """Get formatted list of available categories"""
        categories = Category.objects.filter(user=self.user, is_active=True)
        return ', '.join([f"{cat.icon} {cat.name}" for cat in categories])


class StatementGenerator:
    """Generate expense statements and summaries"""
    
    def __init__(self, user):
        self.user = user
        self.currency_symbol = user.currency_symbol
    
    def generate_today(self):
        """Generate today's expense statement"""
        today = timezone.now().date()
        expenses = Expense.objects.filter(
            user=self.user,
            date=today,
            is_deleted=False
        ).select_related('category')
        
        return self._format_expenses(expenses, f"📊 Today's Expenses ({today.strftime('%d %b %Y')})")
    
    def generate_week(self):
        """Generate this week's expense statement"""
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        
        expenses = Expense.objects.filter(
            user=self.user,
            date__gte=week_start,
            date__lte=today,
            is_deleted=False
        ).select_related('category')
        
        return self._format_expenses(expenses, f"📊 This Week's Expenses ({week_start.strftime('%d %b')} - {today.strftime('%d %b')})")
    
    def generate_month(self):
        """Generate this month's expense statement"""
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        expenses = Expense.objects.filter(
            user=self.user,
            date__gte=month_start,
            date__lte=today,
            is_deleted=False
        ).select_related('category')
        
        return self._format_expenses(expenses, f"📊 This Month's Expenses ({month_start.strftime('%B %Y')})")
    
    def generate_category(self, category_name):
        """Generate expenses for a specific category"""
        category = Category.objects.filter(
            user=self.user,
            name__iexact=category_name,
            is_active=True
        ).first()
        
        if not category:
            return f"❌ Category '{category_name}' not found."
        
        # Get last 30 days for this category
        today = timezone.now().date()
        start_date = today - timedelta(days=30)
        
        expenses = Expense.objects.filter(
            user=self.user,
            category=category,
            date__gte=start_date,
            is_deleted=False
        ).select_related('category')
        
        return self._format_expenses(expenses, f"📊 {category.icon} {category.name} - Last 30 Days")
    
    def generate_summary(self):
        """Generate overall expense summary"""
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # Monthly expenses by category
        expenses = Expense.objects.filter(
            user=self.user,
            date__gte=month_start,
            is_deleted=False
        ).select_related('category')
        
        # Group by category
        from django.db.models import Sum
        category_totals = expenses.values('category__name', 'category__icon').annotate(
            total=Sum('amount')
        ).order_by('-total')
        
        if not category_totals:
            return f"📊 Monthly Summary ({month_start.strftime('%B %Y')})\n\nNo expenses recorded yet."
        
        message = f"📊 Monthly Summary ({month_start.strftime('%B %Y')})\n\n"
        
        total = 0
        for item in category_totals:
            amount = float(item['total'])
            total += amount
            message += f"{item['category__icon']} {item['category__name']}: {self.currency_symbol}{amount:.2f}\n"
        
        message += f"\n{'='*25}\n"
        message += f"💰 Total: {self.currency_symbol}{total:.2f}"
        
        return message
    
    def _format_expenses(self, expenses, title):
        """Format expenses into a readable message"""
        if not expenses:
            return f"{title}\n\nNo expenses recorded."
        
        from django.db.models import Sum
        
        # Group by category
        category_totals = {}
        for expense in expenses:
            cat_name = expense.category.name
            cat_icon = expense.category.icon
            key = f"{cat_icon} {cat_name}"
            
            if key not in category_totals:
                category_totals[key] = 0
            category_totals[key] += float(expense.amount)
        
        message = f"{title}\n\n"
        
        total = 0
        for cat, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
            message += f"{cat}: {self.currency_symbol}{amount:.2f}\n"
            total += amount
        
        message += f"\n{'='*25}\n"
        message += f"💰 Total: {self.currency_symbol}{total:.2f}"
        
        return message
