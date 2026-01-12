import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from users.models import User, WhatsAppMapping
from expenses.models import Expense
from .whatsapp_service import WhatsAppService
from .expense_handler import ExpenseParser, StatementGenerator

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    """
    WhatsApp webhook endpoint for receiving messages from Meta Cloud API
    GET: Webhook verification
    POST: Message handling
    """
    # CRITICAL: Log IMMEDIATELY when request arrives
    logger.info(f"========== WEBHOOK REQUEST RECEIVED ==========")
    logger.info(f"Method: {request.method}")
    logger.info(f"Path: {request.path}")
    logger.info(f"Headers: {dict(request.META)}")
    
    if request.method == "GET":
        return verify_webhook(request)
    elif request.method == "POST":
        return handle_webhook(request)


@csrf_exempt
def webhook_test(request):
    """Test endpoint to verify Django routing is working"""
    logger.info("========== TEST ENDPOINT HIT ==========")
    logger.info(f"Method: {request.method}")
    logger.info(f"Path: {request.path}")
    return JsonResponse({
        'status': 'success',
        'message': 'Django routing is working correctly',
        'method': request.method,
        'path': request.path
    })


def verify_webhook(request):
    """Verify webhook during setup (Meta API format)"""
    mode = request.GET.get('hub.mode')
    token = request.GET.get('hub.verify_token')
    challenge = request.GET.get('hub.challenge')
    
    if mode == 'subscribe' and token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return HttpResponse(challenge, content_type='text/plain')
    else:
        logger.warning("Webhook verification failed")
        return HttpResponse('Verification failed', status=403)


def handle_webhook(request):
    """Process incoming WhatsApp messages (Meta Cloud API format)"""
    try:
        # Log raw request body BEFORE any processing
        logger.info(f"Raw request body: {request.body.decode('utf-8')}")
        
        # TEMPORARILY DISABLED: Signature verification to diagnose webhook issue
        # TODO: Re-enable after confirming webhooks work
        # whatsapp_service = WhatsAppService()
        # if not whatsapp_service.verify_webhook_signature(request):
        #     logger.warning("Webhook signature verification failed")
        #     return HttpResponse('Signature verification failed', status=403)
        
        logger.info("Signature verification SKIPPED (temporarily disabled)")
        
        data = json.loads(request.body.decode('utf-8'))
        logger.info(f"Received webhook data: {json.dumps(data, indent=2)}")
        
        # Extract message data
        if 'entry' not in data:
            return JsonResponse({'status': 'no_entry'})
        
        for entry in data['entry']:
            for change in entry.get('changes', []):
                value = change.get('value', {})
                
                # Process messages
                if 'messages' in value:
                    for message in value['messages']:
                        process_message(message, value)
        
        return JsonResponse({'status': 'success'})
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def process_message(message, value):
    """Process individual WhatsApp message"""
    try:
        message_type = message.get('type')
        from_number = message.get('from')
        message_id = message.get('id')
        
        # Only process text messages
        if message_type != 'text':
            logger.info(f"Ignoring non-text message type: {message_type}")
            return
        
        text = message.get('text', {}).get('body', '').strip()
        
        if not text:
            return
        
        logger.info(f"Processing message from {from_number}: {text}")
        
        # Find user by WhatsApp number
        try:
            # Normalize phone number for matching
            normalized_number = from_number.lstrip('0')
            mapping = WhatsAppMapping.objects.select_related('user').filter(
                is_active=True
            ).filter(
                whatsapp_number__in=[from_number, normalized_number]
            ).first()
            
            if not mapping:
                raise WhatsAppMapping.DoesNotExist()
            
            user = mapping.user
        except WhatsAppMapping.DoesNotExist:
            # User not registered
            whatsapp_service = WhatsAppService()
            whatsapp_service.send_message(
                from_number,
                "❌ Your WhatsApp number is not registered. Please register at our website first."
            )
            return
        
        # Process the message
        response_message = process_user_message(user, text)
        
        # Send response
        whatsapp_service = WhatsAppService()
        whatsapp_service.send_message(from_number, response_message)
        
        # Mark message as read
        whatsapp_service.mark_message_read(message_id)
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)


def process_user_message(user, text):
    """Process user message and return appropriate response"""
    text_lower = text.lower().strip()
    
    # Check for commands
    if text_lower == 'today':
        generator = StatementGenerator(user)
        return generator.generate_today()
    
    elif text_lower in ['this week', 'week']:
        generator = StatementGenerator(user)
        return generator.generate_week()
    
    elif text_lower in ['this month', 'month']:
        generator = StatementGenerator(user)
        return generator.generate_month()
    
    elif text_lower == 'summary':
        generator = StatementGenerator(user)
        return generator.generate_summary()
    
    elif text_lower.startswith('category '):
        category_name = text[9:].strip()
        generator = StatementGenerator(user)
        return generator.generate_category(category_name)
    
    elif text_lower in ['help', 'commands']:
        return get_help_message(user)
    
    elif text_lower == 'categories':
        return get_categories_message(user)
    
    else:
        # Try to parse as expense entry
        parser = ExpenseParser(user)
        result = parser.parse(text)
        
        if result is None:
            return get_help_message(user)
        
        if 'error' in result:
            return f"❌ {result['message']}"
        
        # Create expense
        expense = Expense.objects.create(
            user=user,
            category=result['category'],
            amount=result['amount'],
            description=result['description'],
            date=result['date'],
            source='whatsapp'
        )
        
        return f"✅ Recorded: {user.currency_symbol}{expense.amount} under {expense.category.icon} {expense.category.name}"


def get_help_message(user):
    """Get help message with available commands"""
    return """📱 *Expense Tracker Commands*

*Add Expense:*
<amount> <category> [description]
Example: 120 petrol
Example: 450 food lunch

*View Statements:*
• today - Today's expenses
• week - This week's expenses  
• month - This month's expenses
• summary - Monthly summary
• category <name> - Category expenses

*Other:*
• categories - List categories
• help - Show this message"""


def get_categories_message(user):
    """Get list of user's categories"""
    from expenses.models import Category
    
    categories = Category.objects.filter(user=user, is_active=True).order_by('name')
    
    if not categories:
        return "❌ No categories found. Please add categories from the web dashboard."
    
    message = "📂 *Your Categories:*\n\n"
    for cat in categories:
        message += f"{cat.icon} {cat.name}\n"
    
    return message

