import hashlib
import logging
import os
import csv
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from expenses.models import Budget, Category, Expense, Receipt
from users.models import OTPVerification, User, WhatsAppMapping
from users.services import generate_otp_for_user, normalize_whatsapp_number, verify_otp_for_user
from whatsapp_integration.exceptions import AICategoriaztionException, AmountNotFoundException, OCRException
from whatsapp_integration.receipt_processor import process_receipt
from whatsapp_integration.whatsapp_service import WhatsAppService


logger = logging.getLogger(__name__)

# --- WhatsApp Spend Reminder ---
@login_required
def send_spend_reminder(request):
    """Send WhatsApp reminder to register spend"""
    whatsapp_number = request.user.whatsapp_number
    if not whatsapp_number:
        messages.error(request, 'No WhatsApp number linked to your account.')
        return redirect('dashboard:dashboard')

    whatsapp_service = WhatsAppService()
    # Use template message for sandbox, or free-form for production
    if settings.DEBUG:
        message = "Please reply with your expense details via WhatsApp. Example: 120 petrol lunch"
        result = whatsapp_service.send_message(whatsapp_number, message)
    else:
        # Replace 'remind_spend' with your approved template name
        result = whatsapp_service.send_template_message(
            whatsapp_number,
            template_name='remind_spend',
            language_code='en_US'
        )

    if result:
        messages.success(request, f'Reminder sent to {whatsapp_number}!')
    else:
        messages.error(request, 'Failed to send WhatsApp reminder.')
    return redirect('dashboard:dashboard')

def home(request):
    """Landing page"""
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')
    return render(request, 'dashboard/home.html')


def about(request):
    """Public about page."""
    return render(request, 'dashboard/about.html')


def contact(request):
    """Public contact page."""
    return render(request, 'dashboard/contact.html')


def privacy_policy(request):
    """Public privacy policy page."""
    return render(request, 'dashboard/privacy_policy.html')


def terms_of_service(request):
    """Public terms of service page."""
    return render(request, 'dashboard/terms_of_service.html')


def register(request):
    """User registration without OTP or WhatsApp verification"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        whatsapp_number = request.POST.get('whatsapp_number')

        # Validation
        if password != password2:
            messages.error(request, 'Passwords do not match')
            return render(request, 'dashboard/register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'dashboard/register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists')
            return render(request, 'dashboard/register.html')

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            whatsapp_number=whatsapp_number,
            whatsapp_verified=True
        )

        # Create default categories
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

        for name, icon, color in default_categories:
            Category.objects.create(
                user=user,
                name=name,
                icon=icon,
                color=color,
                is_default=True
            )

        messages.success(request, 'Registration successful! Please login.')
        return redirect('dashboard:login')

    return render(request, 'dashboard/register.html')


def user_login(request):
    """Passwordless login using WhatsApp OTP."""
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')

    if request.method == 'POST':
        phone_number = request.POST.get('phone_number', '').strip()
        normalized_number = normalize_whatsapp_number(phone_number)

        if not normalized_number:
            messages.error(request, 'Please enter a valid WhatsApp number with country code.')
            return render(request, 'dashboard/login.html', {'show_otp_form': False})

        user = get_user_by_whatsapp_number(normalized_number)
        if not user:
            messages.error(request, 'No account found for this number. Send a WhatsApp message first to auto-create your account.')
            return render(request, 'dashboard/login.html', {'show_otp_form': False})

        otp_record = generate_otp_for_user(user, purpose=OTPVerification.PURPOSE_LOGIN)
        otp_message = (
            f'🔐 Your XpenseDiary login OTP is: *{otp_record.otp}*\n\n'
            'Valid for 10 minutes. Do not share this with anyone.\n'
            '— *TechSpark*'
        )

        whatsapp_service = WhatsAppService()
        send_result = whatsapp_service.send_message(normalized_number, otp_message)

        if send_result:
            messages.success(request, 'OTP sent to your WhatsApp number.')
        else:
            if settings.DEBUG:
                messages.warning(request, f'WhatsApp send failed in development. OTP: {otp_record.otp}')
            else:
                messages.error(request, 'Could not send OTP right now. Please try again.')

        return render(
            request,
            'dashboard/login.html',
            {
                'show_otp_form': True,
                'phone_number': normalized_number,
            },
        )

    return render(request, 'dashboard/login.html', {'show_otp_form': False})


def verify_otp_login(request):
    """Validate OTP and start authenticated dashboard session."""
    if request.method != 'POST':
        return redirect('dashboard:login')

    phone_number = request.POST.get('phone_number', '').strip()
    otp = request.POST.get('otp', '').strip()
    normalized_number = normalize_whatsapp_number(phone_number)

    if not normalized_number or not otp:
        messages.error(request, 'Both phone number and OTP are required.')
        return render(
            request,
            'dashboard/login.html',
            {
                'show_otp_form': True,
                'phone_number': normalized_number,
            },
        )

    user = get_user_by_whatsapp_number(normalized_number)
    if not user:
        messages.error(request, 'No account found for this number.')
        return redirect('dashboard:login')

    if not verify_otp_for_user(user, otp, purpose=OTPVerification.PURPOSE_LOGIN):
        messages.error(request, 'Invalid or expired OTP.')
        return render(
            request,
            'dashboard/login.html',
            {
                'show_otp_form': True,
                'phone_number': normalized_number,
            },
        )

    login(request, user)
    messages.success(request, 'Login successful.')
    return redirect('dashboard:dashboard')


def get_user_by_whatsapp_number(normalized_number):
    user = User.objects.filter(whatsapp_number=normalized_number).first()
    if user:
        return user

    user = User.objects.filter(phone_number=normalized_number).first()
    if user:
        return user

    mapping = (
        WhatsAppMapping.objects
        .select_related('user')
        .filter(whatsapp_number=normalized_number, is_active=True)
        .first()
    )
    if mapping:
        return mapping.user

    return None


def user_logout(request):
    """User logout"""
    logout(request)
    messages.success(request, 'Logged out successfully')
    return redirect('dashboard:home')


@login_required
def dashboard(request):
    """Main dashboard"""
    user = request.user
    today = timezone.now().date()
    
    # Date ranges
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    # Expenses
    today_expenses = Expense.objects.filter(user=user, date=today, is_deleted=False)
    week_expenses = Expense.objects.filter(user=user, date__gte=week_start, is_deleted=False)
    month_expenses = Expense.objects.filter(user=user, date__gte=month_start, is_deleted=False)
    
    # Totals
    today_total = today_expenses.aggregate(total=Sum('amount'))['total'] or 0
    week_total = week_expenses.aggregate(total=Sum('amount'))['total'] or 0
    month_total = month_expenses.aggregate(total=Sum('amount'))['total'] or 0
    
    # Category breakdown (monthly)
    category_data = list(month_expenses.values('category__name', 'category__icon', 'category__color').annotate(
        total=Sum('amount')
    ).order_by('-total'))

    for item in category_data:
        item['percentage'] = 0
        if month_total:
            item['percentage'] = round((float(item['total']) / float(month_total)) * 100, 1)
    
    # Recent expenses
    recent_expenses = Expense.objects.filter(user=user, is_deleted=False).select_related('category')[:10]

    # Receipt analytics
    recent_receipts = Receipt.objects.filter(user=user).order_by('-created_at')[:5]
    receipt_total = Receipt.objects.filter(user=user).count()
    receipt_success = Receipt.objects.filter(user=user, processing_status='success').count()
    receipt_failed = Receipt.objects.filter(user=user, processing_status='failed').count()
    receipt_pending = Receipt.objects.filter(user=user, processing_status='pending').count()

    top_category = category_data[0] if category_data else None
    
    stats_cards = [
        {
            'label': 'Today',
            'value': f"{user.currency_symbol}{today_total:,.0f}",
            'trend_text': 'Live',
            'trend_icon': 'schedule',
            'trend_color': 'text-slate-500',
        },
        {
            'label': 'This Week',
            'value': f"{user.currency_symbol}{week_total:,.0f}",
            'trend_text': 'Current week',
            'trend_icon': 'calendar_view_week',
            'trend_color': 'text-slate-500',
        },
        {
            'label': 'This Month',
            'value': f"{user.currency_symbol}{month_total:,.0f}",
            'trend_text': 'Total spend',
            'trend_icon': 'insights',
            'trend_color': 'text-slate-500',
        },
        {
            'label': 'Receipts',
            'value': str(receipt_total),
            'trend_text': f"{receipt_success} processed",
            'trend_icon': 'receipt_long',
            'trend_color': 'text-emerald-600',
        },
        {
            'label': 'Categories',
            'value': str(len(category_data)),
            'trend_text': top_category['category__name'] if top_category else 'No data',
            'trend_icon': 'category',
            'trend_color': 'text-slate-500',
        },
    ]

    recent_transactions = []
    icon_map = {
        'Food': 'restaurant',
        'Travel': 'directions_car',
        'Transport': 'directions_car',
        'Bills': 'receipt_long',
        'Shopping': 'shopping_bag',
        'Entertainment': 'movie',
        'Health': 'health_and_safety',
        'Groceries': 'local_grocery_store',
        'Education': 'school',
    }
    for expense in recent_expenses[:8]:
        category_name = expense.category.name if expense.category else 'Other'
        recent_transactions.append({
            'merchant': expense.description or category_name,
            'category': category_name,
            'date': expense.date.strftime('%d %b %Y'),
            'amount': f"{float(expense.amount):,.2f}",
            'icon': icon_map.get(category_name, 'payments'),
        })

    budget_map = {
        b.category_id: float(b.monthly_limit)
        for b in Budget.objects.filter(user=user, is_active=True).select_related('category')
    }
    color_cycle = ['emerald-500', 'cyan-500', 'amber-500', 'rose-500', 'indigo-500']
    category_breakdown = []
    for idx, item in enumerate(category_data[:6]):
        category_name = item.get('category__name') or 'Other'
        spent = float(item.get('total') or 0)
        limit = budget_map.get(
            next((c.id for c in Category.objects.filter(user=user, name=category_name)[:1]), None),
            max(spent * 1.2, spent),
        )
        percent = round((spent / limit) * 100, 1) if limit else 0
        category_breakdown.append({
            'name': category_name,
            'spent': f"{spent:,.0f}",
            'limit': f"{limit:,.0f}",
            'percent': min(percent, 100),
            'color': color_cycle[idx % len(color_cycle)],
        })

    receipt_statuses = []
    status_meta = {
        'success': ('Processed', 'check_circle', 'emerald-500', 'emerald-600', True),
        'failed': ('Failed', 'error', 'rose-500', 'rose-600', True),
        'pending': ('Pending', 'schedule', 'amber-500', 'amber-600', False),
    }
    for receipt in recent_receipts:
        status_text, icon, status_color, icon_color, fill = status_meta.get(
            receipt.processing_status,
            ('Unknown', 'help', 'slate-400', 'slate-500', False),
        )
        receipt_statuses.append({
            'filename': os.path.basename(receipt.image.name),
            'status_text': status_text,
            'status_color': status_color,
            'icon': icon,
            'icon_color': icon_color,
            'fill': fill,
        })

    month_total_decimal = Decimal(str(month_total))
    month_whole = int(month_total_decimal)
    month_cents = int((month_total_decimal - month_whole) * 100)

    context = {
        'today_total': today_total,
        'week_total': week_total,
        'month_total': month_total,
        'monthly_total': month_whole,
        'monthly_total_cents': f"{month_cents:02d}",
        'last_updated': timezone.now().strftime('%I:%M %p'),
        'stats_cards': stats_cards,
        'recent_transactions': recent_transactions,
        'category_breakdown': category_breakdown,
        'receipt_statuses': receipt_statuses,
        'category_data': category_data,
        'recent_expenses': recent_expenses,
        'recent_receipts': recent_receipts,
        'receipt_total': receipt_total,
        'receipt_success': receipt_success,
        'receipt_failed': receipt_failed,
        'receipt_pending': receipt_pending,
        'top_category': top_category,
        'whatsapp_verified': user.whatsapp_verified,
        'active_page': 'dashboard',
    }
    
    return render(request, 'dashboard/dashboard.html', context)


@login_required
def analytics(request):
    """Analytics page with trends and category summaries."""
    user = request.user
    today = timezone.now().date()
    month_start = today.replace(day=1)

    month_expenses = Expense.objects.filter(user=user, date__gte=month_start, is_deleted=False)
    month_total = month_expenses.aggregate(total=Sum('amount'))['total'] or 0

    category_data = list(
        month_expenses
        .values('category__name', 'category__icon', 'category__color')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    for item in category_data:
        item['percentage'] = 0
        if month_total:
            item['percentage'] = round((float(item['total']) / float(month_total)) * 100, 1)

    trend_qs = (
        Expense.objects.filter(user=user, is_deleted=False)
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-month')[:6]
    )

    monthly_trend = []
    for row in reversed(list(trend_qs)):
        month_value = row.get('month')
        monthly_trend.append({
            'label': month_value.strftime('%b %Y') if month_value else 'Unknown',
            'total': float(row.get('total') or 0),
            'count': row.get('count') or 0,
        })

    chart_bars = []
    max_total = max([point['total'] for point in monthly_trend], default=0) or 1
    bar_palette = ['bg-emerald-500', 'bg-cyan-500', 'bg-indigo-500', 'bg-amber-500', 'bg-rose-500', 'bg-slate-500']
    for idx, point in enumerate(monthly_trend[-6:]):
        chart_bars.append({
            'height': max(8, round((point['total'] / max_total) * 100, 1)),
            'color': bar_palette[idx % len(bar_palette)],
        })

    category_mix = []
    for idx, item in enumerate(category_data[:5]):
        total_val = float(item.get('total') or 0)
        pct = round((total_val / float(month_total)) * 100, 1) if month_total else 0
        category_mix.append({
            'name': item.get('category__name') or 'Other',
            'percent': pct,
            'color': ['emerald-500', 'cyan-500', 'indigo-500', 'amber-500', 'rose-500'][idx % 5],
        })

    donut_segments = []
    circumference = 565
    offset = 0
    for mix in category_mix:
        donut_segments.append({'color': mix['color'], 'offset': offset})
        offset += (mix['percent'] / 100) * circumference

    top_category_name = category_data[0].get('category__name') if category_data else 'None'
    previous_month_start = (month_start - timedelta(days=1)).replace(day=1)
    previous_month_total = (
        Expense.objects.filter(user=user, date__gte=previous_month_start, date__lt=month_start, is_deleted=False)
        .aggregate(total=Sum('amount'))['total']
        or 0
    )
    trend_pct = 0
    if previous_month_total:
        trend_pct = round(((float(month_total) - float(previous_month_total)) / float(previous_month_total)) * 100, 1)

    recent_shift_qs = Expense.objects.filter(user=user, is_deleted=False).select_related('category')[:6]
    outflow_shifts = []
    for expense in recent_shift_qs:
        cat_name = expense.category.name if expense.category else 'Other'
        outflow_shifts.append({
            'icon': 'payments',
            'name': expense.description or cat_name,
            'category': cat_name,
            'date': expense.date.strftime('%d %b'),
            'type': expense.source.title(),
            'amount': f"{float(expense.amount):,.2f}",
            'change': f"{trend_pct:+.1f}% vs last month",
            'change_color': 'text-emerald-600' if trend_pct <= 0 else 'text-rose-500',
        })

    total_budget = sum(float(b.monthly_limit) for b in Budget.objects.filter(user=user, is_active=True))
    savings_target = max(total_budget * 0.25, 1)
    savings_now = max(total_budget - float(month_total), 0)
    savings_percent = round((savings_now / savings_target) * 100, 1) if savings_target else 0

    context = {
        'month_total': month_total,
        'category_data': category_data,
        'monthly_trend': monthly_trend,
        'analytics_headline': f"Spending is {abs(trend_pct):.1f}% {'up' if trend_pct > 0 else 'down'} versus last month.",
        'efficiency_score': max(0, min(100, int(100 - (float(month_total) / (total_budget or (float(month_total) + 1))) * 100))),
        'chart_bars': chart_bars,
        'inflow': f"{max(total_budget, float(month_total)):,.0f}",
        'outflow': f"{float(month_total):,.0f}",
        'net_flow': f"{max(total_budget - float(month_total), 0):,.0f}",
        'donut_segments': donut_segments,
        'top_category': top_category_name,
        'category_mix': category_mix,
        'savings_goal': {
            'name': 'Quarterly Buffer',
            'target': f"{savings_target:,.0f}",
            'percent': min(savings_percent, 100),
            'months_left': 3,
        },
        'alert': {
            'title': 'Watch Spending',
            'message': 'One or more categories are above 80% utilization this month.',
            'cta': 'Review budgets',
        },
        'ai_insight': 'Food and transport spending are the strongest drivers this month; reducing each by 8% can materially improve your monthly surplus.',
        'outflow_shifts': outflow_shifts,
        'active_page': 'analytics',
    }
    return render(request, 'dashboard/analytics.html', context)


@login_required
def transactions(request):
    """Dedicated transactions page."""
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            category_id = request.POST.get('category')
            amount = request.POST.get('amount')
            description = request.POST.get('description', '')
            date = request.POST.get('date')

            try:
                category = Category.objects.get(id=category_id, user=request.user)
                Expense.objects.create(
                    user=request.user,
                    category=category,
                    amount=amount,
                    description=description,
                    date=date,
                    source='web'
                )
                messages.success(request, 'Transaction added successfully')
            except Category.DoesNotExist:
                messages.error(request, 'Invalid category')

        elif action == 'delete':
            expense_id = request.POST.get('expense_id')
            try:
                expense = Expense.objects.get(id=expense_id, user=request.user)
                expense.delete()
                messages.success(request, 'Transaction deleted successfully')
            except Expense.DoesNotExist:
                messages.error(request, 'Transaction not found')

        return redirect('dashboard:transactions')

    expenses = (
        Expense.objects.filter(user=request.user, is_deleted=False)
        .select_related('category')
        .order_by('-date', '-created_at')
    )
    q = (request.GET.get('q') or '').strip()
    kind = (request.GET.get('kind') or 'all').lower()
    if q:
        expenses = expenses.filter(description__icontains=q)
    if kind == 'income':
        expenses = expenses.none()
    elif kind == 'expenses':
        expenses = expenses

    tx_rows = []
    for item in expenses:
        category_name = item.category.name if item.category else 'Other'
        tx_rows.append({
            'id': item.id,
            'merchant': item.description or category_name,
            'datetime': f"{item.date.strftime('%d %b %Y')} • {item.created_at.strftime('%I:%M %p')}",
            'category': category_name,
            'category_style': 'bg-emerald-100 text-emerald-800',
            'status': 'Posted',
            'status_color': 'text-emerald-600',
            'payment_method': item.source.upper(),
            'payment_icon': 'account_balance_wallet' if item.source == 'web' else 'chat',
            'amount': f"{float(item.amount):,.2f}",
            'is_income': False,
            'icon': 'payments',
        })

    paginator = Paginator(tx_rows, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    categories_list = Category.objects.filter(user=request.user, is_active=True).order_by('name')

    context = {
        'transactions': page_obj,
        'ledger_subtitle': 'Detailed transaction history with source and status.',
        'total_outbound': f"{sum(float(e.amount) for e in expenses):,.0f}",
        'expenses': expenses[:100],
        'categories': categories_list,
        'today': timezone.now().date(),
        'active_page': 'transactions',
    }
    return render(request, 'dashboard/transactions.html', context)


@login_required
def budget(request):
    """Monthly budget page with category-level limits."""
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'save':
            category_id = request.POST.get('category')
            monthly_limit = request.POST.get('monthly_limit')

            try:
                category = Category.objects.get(id=category_id, user=request.user, is_active=True)
                budget_obj, _ = Budget.objects.get_or_create(
                    user=request.user,
                    category=category,
                    defaults={'monthly_limit': monthly_limit}
                )
                budget_obj.monthly_limit = Decimal(monthly_limit)
                budget_obj.is_active = True
                budget_obj.save()
                messages.success(request, f'Budget saved for {category.name}')
            except Category.DoesNotExist:
                messages.error(request, 'Invalid category selected')
            except Exception:
                messages.error(request, 'Please enter a valid monthly limit')

        elif action == 'delete':
            budget_id = request.POST.get('budget_id')
            try:
                budget_obj = Budget.objects.get(id=budget_id, user=request.user)
                budget_obj.is_active = False
                budget_obj.save(update_fields=['is_active', 'updated_at'])
                messages.success(request, 'Budget removed successfully')
            except Budget.DoesNotExist:
                messages.error(request, 'Budget not found')

        return redirect('dashboard:budget')

    today = timezone.now().date()
    month_start = today.replace(day=1)
    month_expenses = Expense.objects.filter(user=request.user, date__gte=month_start, is_deleted=False)
    spent_by_category = {
        row['category']: float(row['total'] or 0)
        for row in month_expenses.values('category').annotate(total=Sum('amount'))
    }

    active_budgets = (
        Budget.objects.filter(user=request.user, is_active=True)
        .select_related('category')
        .order_by('category__name')
    )

    budget_rows = []
    total_limit = 0.0
    total_spent = 0.0
    for item in active_budgets:
        spent = spent_by_category.get(item.category_id, 0.0)
        limit = float(item.monthly_limit)
        total_limit += limit
        total_spent += spent
        utilization = round((spent / limit) * 100, 1) if limit > 0 else 0
        budget_rows.append({
            'id': item.id,
            'category': item.category,
            'limit': limit,
            'spent': spent,
            'remaining': round(limit - spent, 2),
            'utilization': utilization,
        })

    current_month = timezone.now().strftime('%B %Y')
    budget_cards = []
    for row in budget_rows:
        utilization = row['utilization']
        at_risk = utilization >= 85
        category_name = row['category'].name if row['category'] else 'Other'
        budget_cards.append({
            'id': row['id'],
            'name': category_name,
            'description': f"Monthly budget for {category_name.lower()}.",
            'icon': 'account_balance_wallet',
            'spent': f"{row['spent']:,.0f}",
            'limit': f"{row['limit']:,.0f}",
            'remaining': f"{row['remaining']:,.0f}",
            'percent': min(utilization, 100),
            'status': 'At Risk' if at_risk else 'Healthy',
            'badge_style': 'bg-rose-100 text-rose-700' if at_risk else 'bg-emerald-100 text-emerald-700',
            'forecast': 'May exceed by month-end' if at_risk else 'On track this month',
            'at_risk': at_risk,
        })

    total_remaining = max(total_limit - total_spent, 0)

    context = {
        'categories': Category.objects.filter(user=request.user, is_active=True).order_by('name'),
        'budget_rows': budget_rows,
        'budgets': budget_cards,
        'current_month': current_month,
        'total_limit': total_limit,
        'total_spent': total_spent,
        'total_remaining': f"{total_remaining:,.0f}",
        'overall_utilization': round((total_spent / total_limit) * 100, 1) if total_limit > 0 else 0,
        'savings_forecast': f"{(total_remaining * 3):,.0f}",
        'efficiency_score': max(0, min(100, int(100 - ((total_spent / total_limit) * 100)))) if total_limit > 0 else 100,
        'advisor_image_url': 'https://ui-avatars.com/api/?name=AI+Advisor&background=006c49&color=fff',
        'advisor_quote': 'Your fixed spending looks healthy. Consider reducing variable food and transport budgets by <strong>5-8%</strong> to improve quarterly savings.',
        'active_page': 'budgets',
    }
    return render(request, 'dashboard/budget.html', context)


@login_required
def settings_page(request):
    """User settings page with profile and preferences."""
    user = request.user
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'profile':
            first_name = (request.POST.get('first_name') or '').strip()
            last_name = (request.POST.get('last_name') or '').strip()
            email = (request.POST.get('email') or '').strip()
            currency = (request.POST.get('currency') or user.currency or 'INR').strip().upper()

            if email and User.objects.exclude(id=user.id).filter(email=email).exists():
                messages.error(request, 'That email is already in use by another account.')
            else:
                user.first_name = first_name
                user.last_name = last_name
                if email:
                    user.email = email
                user.currency = currency
                currency_map = {'INR': '₹', 'USD': '$', 'EUR': '€', 'AED': 'AED'}
                user.currency_symbol = currency_map.get(currency, user.currency_symbol)
                user.save()
                messages.success(request, 'Profile settings updated.')

        elif action == 'whatsapp':
            new_number = normalize_whatsapp_number(request.POST.get('whatsapp_number', ''))
            if not new_number:
                messages.error(request, 'Enter a valid WhatsApp number with country code.')
            else:
                user.whatsapp_number = new_number
                user.whatsapp_verified = False
                user.save(update_fields=['whatsapp_number', 'whatsapp_verified', 'updated_at'])
                messages.success(request, 'WhatsApp number updated. Please verify again.')

        return redirect('dashboard:settings')

    context = {
        'settings_section': request.GET.get('section', 'profile'),
        'user_prefs': {
            'weekly_digest': True,
            'privacy_mask': False,
        },
        'active_page': 'settings',
    }
    return render(request, 'dashboard/settings.html', context)


@login_required
def support(request):
    """Support redirect placeholder for sidebar link."""
    messages.info(request, 'Support is available via the contact page.')
    return redirect('dashboard:contact')


@login_required
def export_transactions_csv(request):
    """Export user transactions to CSV."""
    expenses = (
        Expense.objects.filter(user=request.user, is_deleted=False)
        .select_related('category')
        .order_by('-date', '-created_at')
    )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Category', 'Description', 'Amount', 'Source', 'Created At'])

    for item in expenses:
        writer.writerow([
            item.date.isoformat(),
            item.category.name if item.category else 'Other',
            item.description,
            str(item.amount),
            item.source,
            item.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    return response


@login_required
def link_whatsapp(request):
    """Link WhatsApp number"""
    if request.method == 'POST':
        whatsapp_number = request.POST.get('whatsapp_number')
        
        # Validate phone number
        if not whatsapp_number:
            messages.error(request, 'Please enter a WhatsApp number')
            return render(request, 'dashboard/link_whatsapp.html')
        
        # Update user's WhatsApp number
        request.user.whatsapp_number = whatsapp_number
        request.user.save()
        
        # Generate OTP
        otp = request.user.generate_otp()
        
        # Send OTP via WhatsApp
        whatsapp_service = WhatsAppService()
        message = f"Your OTP for Expense Tracker verification is: {otp}\n\nThis OTP is valid for 10 minutes."
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Attempting to send OTP to {whatsapp_number}")
        
        result = whatsapp_service.send_message(whatsapp_number, message)
        
        # For development: Show OTP since test accounts can only send template messages
        if settings.DEBUG:
            messages.success(request, f'OTP sent to {whatsapp_number}. For testing, your OTP is: {otp}')
            logger.info(f"Development mode - OTP for {whatsapp_number}: {otp}")
            return redirect('dashboard:verify_whatsapp')
        
        if result:
            messages.success(request, f'OTP sent to {whatsapp_number}. Check your WhatsApp messages.')
            return redirect('dashboard:verify_whatsapp')
        else:
            messages.error(request, 'Failed to send OTP. Please ensure: 1) Your number is added as a test user in Meta Dashboard, 2) Number format includes country code (e.g., 919876543210), 3) WhatsApp API credentials are correct.')
            logger.error(f"Failed to send OTP to {whatsapp_number}")
    
    return render(request, 'dashboard/link_whatsapp.html')


@login_required
def verify_whatsapp(request):
    """Verify WhatsApp OTP"""
    if request.method == 'POST':
        otp = request.POST.get('otp')
        
        if request.user.verify_otp(otp):
            # Create WhatsApp mapping
            WhatsAppMapping.objects.get_or_create(
                user=request.user,
                defaults={'whatsapp_number': request.user.whatsapp_number}
            )
            
            messages.success(request, 'WhatsApp number verified successfully!')
            return redirect('dashboard:dashboard')
        else:
            messages.error(request, 'Invalid or expired OTP')
    
    return render(request, 'dashboard/verify_whatsapp.html')


@login_required
def categories(request):
    """Manage categories"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            name = request.POST.get('name')
            icon = request.POST.get('icon', '💰')
            color = request.POST.get('color', '#4CAF50')
            
            Category.objects.create(
                user=request.user,
                name=name,
                icon=icon,
                color=color
            )
            messages.success(request, f'Category "{name}" added successfully')
        
        elif action == 'delete':
            category_id = request.POST.get('category_id')
            try:
                category = Category.objects.get(id=category_id, user=request.user)
                category.is_active = False
                category.save()
                messages.success(request, 'Category deleted successfully')
            except Category.DoesNotExist:
                messages.error(request, 'Category not found')
        
        return redirect('dashboard:categories')
    
    user_categories = Category.objects.filter(user=request.user, is_active=True).order_by('name')
    
    return render(request, 'dashboard/categories.html', {'categories': user_categories})


@login_required
def expenses_list(request):
    """List and manage expenses"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            category_id = request.POST.get('category')
            amount = request.POST.get('amount')
            description = request.POST.get('description', '')
            date = request.POST.get('date')
            
            try:
                category = Category.objects.get(id=category_id, user=request.user)
                Expense.objects.create(
                    user=request.user,
                    category=category,
                    amount=amount,
                    description=description,
                    date=date,
                    source='web'
                )
                messages.success(request, 'Expense added successfully')
            except Category.DoesNotExist:
                messages.error(request, 'Invalid category')
        
        elif action == 'delete':
            expense_id = request.POST.get('expense_id')
            try:
                expense = Expense.objects.get(id=expense_id, user=request.user)
                expense.delete()  # Soft delete
                messages.success(request, 'Expense deleted successfully')
            except Expense.DoesNotExist:
                messages.error(request, 'Expense not found')
        
        return redirect('dashboard:expenses')
    
    # Filter expenses
    expenses = Expense.objects.filter(user=request.user, is_deleted=False).select_related('category').order_by('-date', '-created_at')
    categories_list = Category.objects.filter(user=request.user, is_active=True).order_by('name')
    
    context = {
        'expenses': expenses[:100],  # Limit to 100 recent expenses
        'categories': categories_list,
    }
    
    return render(request, 'dashboard/expenses.html', context)


@login_required
@require_POST
def upload_receipt_view(request):
    """Upload a receipt image and process it synchronously."""
    uploaded_file = request.FILES.get('image') or request.FILES.get('receipt')

    if not uploaded_file:
        return JsonResponse({'status': 'error', 'message': 'No receipt image was uploaded.'}, status=400)

    if uploaded_file.size > 5 * 1024 * 1024:
        return JsonResponse({'status': 'error', 'message': 'Receipt image must be 5MB or smaller.'}, status=400)

    allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    allowed_content_types = {'image/jpeg', 'image/png', 'image/webp'}
    file_name = (uploaded_file.name or '').lower()
    file_extension = os.path.splitext(file_name)[1]
    content_type = (getattr(uploaded_file, 'content_type', '') or '').lower()

    if file_extension not in allowed_extensions and content_type not in allowed_content_types:
        return JsonResponse({'status': 'error', 'message': 'Only JPG, PNG, and WEBP files are allowed.'}, status=400)

    receipt = Receipt.objects.create(
        user=request.user,
        image=uploaded_file,
        processing_status='pending',
    )

    try:
        expense = process_receipt(receipt.image.path, request.user)

        cache_key = hashlib.md5(receipt.image.path.encode('utf-8')).hexdigest()
        cached_payload = cache.get(cache_key) or {}

        receipt.extracted_text = cached_payload.get('extracted_text', '')
        receipt.raw_ocr_response = cached_payload.get('raw_ocr_response', {})
        receipt.processing_status = 'success'
        receipt.save(update_fields=['extracted_text', 'raw_ocr_response', 'processing_status'])

        return JsonResponse({
            'status': 'success',
            'expense_id': expense.id,
            'amount': float(expense.amount),
            'category': expense.category.name,
        }, status=200)

    except OCRException:
        receipt.processing_status = 'failed'
        receipt.save(update_fields=['processing_status'])
        return JsonResponse({
            'status': 'error',
            'message': 'Could not read the receipt. Please upload a clearer image or type the amount and category manually.',
        }, status=400)

    except AmountNotFoundException:
        receipt.processing_status = 'failed'
        receipt.save(update_fields=['processing_status'])
        return JsonResponse({
            'status': 'error',
            'message': 'Found the receipt but could not detect the total amount. Please reply with the amount to confirm.',
        }, status=400)

    except AICategoriaztionException:
        receipt.processing_status = 'failed'
        receipt.save(update_fields=['processing_status'])
        return JsonResponse({
            'status': 'error',
            'message': 'Could not categorize the receipt automatically. Please enter amount and category manually.',
        }, status=400)

    except Exception:
        logger.exception('Unexpected error while processing receipt upload')
        receipt.processing_status = 'failed'
        receipt.save(update_fields=['processing_status'])
        return JsonResponse({
            'status': 'error',
            'message': 'Unable to process the receipt right now.',
        }, status=500)

