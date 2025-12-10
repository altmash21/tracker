from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from users.models import User, WhatsAppMapping
from expenses.models import Category, Expense
from whatsapp_integration.whatsapp_service import WhatsAppService

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

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from users.models import User, WhatsAppMapping
from expenses.models import Category, Expense
from whatsapp_integration.whatsapp_service import WhatsAppService


def home(request):
    """Landing page"""
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')
    return render(request, 'dashboard/home.html')


def register(request):
    """User registration with WhatsApp OTP verification"""
    if request.method == 'POST':
        # Check if we're verifying OTP
        if 'verify_otp' in request.POST:
            user_id = request.session.get('pending_user_id')
            otp = request.POST.get('otp')
            
            if not user_id:
                messages.error(request, 'Session expired. Please register again.')
                return redirect('dashboard:register')
            
            try:
                user = User.objects.get(id=user_id)
                if user.verify_otp(otp):
                    # OTP verification sets whatsapp_verified to True
                    # Clear session
                    del request.session['pending_user_id']
                    
                    messages.success(request, 'Registration successful! Please login.')
                    return redirect('dashboard:login')
                else:
                    messages.error(request, 'Invalid or expired OTP')
                    return render(request, 'dashboard/verify_otp.html', {'user_id': user_id})
            except User.DoesNotExist:
                messages.error(request, 'User not found')
                return redirect('dashboard:register')
        
        # Initial registration
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
            whatsapp_verified=False
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
        
        # Generate OTP
        otp = user.generate_otp()
        if settings.DEBUG:
            # In local/dev, show OTP on screen, do not send WhatsApp
            request.session['pending_user_id'] = user.id
            messages.success(request, f'Your OTP is: {otp} (for demo only, not sent via WhatsApp)')
            return render(request, 'dashboard/verify_otp.html', {'user_id': user.id, 'otp': otp})
        else:
            # In production, send OTP via WhatsApp
            whatsapp_service = WhatsAppService()
            message = f"Your OTP for Expense Tracker registration is: {otp}\n\nThis OTP is valid for 10 minutes."
            result = whatsapp_service.send_message(whatsapp_number, message)
            if result:
                request.session['pending_user_id'] = user.id
                messages.success(request, f'OTP sent to {whatsapp_number}. Please check your WhatsApp.')
                return render(request, 'dashboard/verify_otp.html', {'user_id': user.id})
            else:
                messages.error(request, 'Failed to send OTP. Please try again.')
                user.delete()  # Clean up user if OTP sending failed
                return render(request, 'dashboard/register.html')
    
    return render(request, 'dashboard/register.html')


def user_login(request):
    """User login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard:dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'dashboard/login.html')


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
    category_data = month_expenses.values('category__name', 'category__icon', 'category__color').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    # Recent expenses
    recent_expenses = Expense.objects.filter(user=user, is_deleted=False).select_related('category')[:10]
    
    context = {
        'today_total': today_total,
        'week_total': week_total,
        'month_total': month_total,
        'category_data': category_data,
        'recent_expenses': recent_expenses,
        'whatsapp_verified': user.whatsapp_verified,
    }
    
    return render(request, 'dashboard/dashboard.html', context)


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

