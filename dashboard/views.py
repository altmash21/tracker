import hashlib
import logging
import os
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from expenses.models import Category, Expense, Receipt
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
    
    context = {
        'today_total': today_total,
        'week_total': week_total,
        'month_total': month_total,
        'category_data': category_data,
        'recent_expenses': recent_expenses,
        'recent_receipts': recent_receipts,
        'receipt_total': receipt_total,
        'receipt_success': receipt_success,
        'receipt_failed': receipt_failed,
        'receipt_pending': receipt_pending,
        'top_category': top_category,
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

