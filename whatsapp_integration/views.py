import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from expenses.models import Category, Expense
from users.services import get_or_create_whatsapp_user

from .exceptions import AICategoriaztionException, AmountNotFoundException, OCRException
from .ai_categorization_service import categorize_with_ai
from .expense_handler import ExpenseParser, StatementGenerator, handle_login_command
from .receipt_processor import process_receipt
from .whatsapp_service import WhatsAppService


logger = logging.getLogger(__name__)


def with_techspark_footer(message):
    if not message:
        return message

    if message.strip().endswith('— *TechSpark*'):
        return message

    if message.strip().endswith('XpenseDiary by TechSpark'):
        return message

    return f'{message}\n\n— *TechSpark*'


def get_welcome_message():
    return (
        '👋 Welcome to *XpenseDiary* by TechSpark!\n\n'
        'Your account has been created automatically.\n'
        'Just send expenses like:\n'
        '• *250 food* — adds ₹250 under Food\n'
        '• *500 petrol* — adds ₹500 under Transport\n\n'
        'Type *help* to see all commands.\n'
        'Type *login* to get a link to your dashboard.\n\n'
        '— *TechSpark*'
    )


def webhook_test(request):
    return HttpResponse('Webhook test OK')


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def whatsapp_webhook(request):
    logger.info('========== WHATSAPP WEBHOOK HIT ==========' )
    logger.info('Method: %s', request.method)
    logger.info('Path: %s', request.path)

    if request.method == 'GET':
        return verify_webhook(request)

    return handle_webhook(request)


def verify_webhook(request):
    mode = request.GET.get('hub.mode')
    token = request.GET.get('hub.verify_token')
    challenge = request.GET.get('hub.challenge')

    logger.info('Webhook verification request received')

    if mode == 'subscribe' and token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info('Webhook verification SUCCESS')
        return HttpResponse(challenge, content_type='text/plain')

    logger.warning('Webhook verification FAILED')
    return HttpResponse('Verification failed', status=403)


def handle_webhook(request):
    try:
        data = json.loads(request.body)

        entry = data.get('entry', [])
        if not entry:
            return HttpResponse(status=200)

        changes = entry[0].get('changes', [])
        if not changes:
            return HttpResponse(status=200)

        value = changes[0].get('value', {})

        if 'messages' not in value:
            return HttpResponse(status=200)

        messages = value.get('messages', [])
        if not messages:
            return HttpResponse(status=200)

        message = messages[0]
        if message.get('type') != 'text':
            return HttpResponse(status=200)

        message_text = message.get('text', {}).get('body', '').strip()
        if not message_text:
            return HttpResponse(status=200)

        logger.info('Processing user message: %s', message_text)
        process_message(message)
        return HttpResponse(status=200)

    except json.JSONDecodeError:
        logger.error('Invalid JSON payload')
        return HttpResponse(status=200)
    except Exception:
        logger.exception('Unhandled webhook error')
        return HttpResponse(status=200)


def process_message(message):
    message_type = message.get('type')
    from_number = message.get('from')
    message_id = message.get('id')

    logger.info('Incoming message from %s | type=%s', from_number, message_type)

    whatsapp_service = WhatsAppService()

    try:
        user, was_created = get_or_create_whatsapp_user(from_number)
        if was_created:
            whatsapp_service.send_message(from_number, get_welcome_message())

        if message_type == 'text':
            text = message.get('text', {}).get('body', '').strip()
            if not text:
                return

            logger.info('Message text: %s', text)
            response_text = process_user_message(user, text)
            whatsapp_service.send_message(from_number, with_techspark_footer(response_text))
            return

        if message_type == 'image':
            image_id = message.get('image', {}).get('id')
            if not image_id:
                whatsapp_service.send_message(
                    from_number,
                    with_techspark_footer('❌ Receipt image is missing media details.')
                )
                return

            image_path = whatsapp_service.download_media(image_id)
            if not image_path:
                whatsapp_service.send_message(
                    from_number,
                    with_techspark_footer('❌ Could not download receipt image.')
                )
                return

            try:
                expense = process_receipt(image_path, user)

                whatsapp_service.send_message(
                    from_number,
                    with_techspark_footer(
                        "✅ Receipt scanned!\n"
                        f"💰 Amount: {user.currency_symbol}{expense.amount}\n"
                        f"📂 Category: {expense.category.icon} {expense.category.name}\n"
                        f"📝 {expense.description}"
                    )
                )
            except Exception:
                logger.exception('Failed processing receipt with Gemini image parser')
                whatsapp_service.send_message(
                    from_number,
                    with_techspark_footer(
                        "📷 Couldn't read this receipt clearly.\n"
                        "Try sending a clearer image."
                    )
                )
            return

        logger.info('Ignoring unsupported message type: %s', message_type)

    except Exception:
        logger.exception('Error processing message')
        whatsapp_service.send_message(
            from_number,
            with_techspark_footer('❌ Unable to process your message right now.')
        )
    finally:
        if message_id:
            whatsapp_service.mark_message_read(message_id)


def process_user_message(user, text):
    text_lower = text.lower().strip()

    if text_lower == 'login':
        return handle_login_command(user)

    if text_lower == 'today':
        return StatementGenerator(user).generate_today()

    if text_lower in ('week', 'this week'):
        return StatementGenerator(user).generate_week()

    if text_lower in ('month', 'this month'):
        return StatementGenerator(user).generate_month()

    if text_lower == 'summary':
        return StatementGenerator(user).generate_summary()

    if text_lower.startswith('category '):
        category = text[9:].strip()
        return StatementGenerator(user).generate_category(category)

    if text_lower in ('help', 'commands'):
        return get_help_message()

    if text_lower == 'categories':
        return get_categories_message(user)

    parser = ExpenseParser(user)
    result = parser.parse(text)

    if not result:
        return get_help_message()

    if isinstance(result, list):
        created_expenses = []
        for item in result:
            expense = Expense.objects.create(
                user=user,
                category=item['category'],
                amount=item['amount'],
                description=item['description'],
                date=item['date'],
                source='whatsapp',
            )
            created_expenses.append(expense)

        if not created_expenses:
            return get_help_message()

        if len(created_expenses) == 1:
            expense = created_expenses[0]
            return (
                f'✅ Recorded: {user.currency_symbol}{expense.amount} '
                f'under {expense.category.icon} {expense.category.name}'
            )

        lines = []
        total = 0
        for expense in created_expenses:
            total += float(expense.amount)
            lines.append(
                f"• {user.currency_symbol}{expense.amount} - {expense.category.icon} {expense.category.name} ({expense.description})"
            )

        return (
            f"✅ Recorded {len(created_expenses)} expenses:\n"
            + "\n".join(lines)
            + f"\n\n💰 Total: {user.currency_symbol}{total:.2f}"
        )

    if 'error' in result:
        if result.get('error') == 'category_not_found':
            category_names = list(
                Category.objects.filter(user=user, is_active=True).values_list('name', flat=True)
            )
            ai_result = categorize_with_ai(text, category_names=category_names)

            ai_amount = ai_result.get('amount')
            ai_category_name = ai_result.get('category')
            ai_description = (ai_result.get('description') or '').strip() or text[:120]

            ai_category = Category.objects.filter(
                user=user,
                name__iexact=ai_category_name,
                is_active=True,
            ).first()

            if ai_category and ai_amount and float(ai_amount) > 0:
                expense = Expense.objects.create(
                    user=user,
                    category=ai_category,
                    amount=ai_amount,
                    description=ai_description,
                    date=timezone.now().date(),
                    source='whatsapp',
                )
                return (
                    f'✅ Recorded: {user.currency_symbol}{expense.amount} '
                    f'under {expense.category.icon} {expense.category.name}'
                )

        return f"❌ {result['message']}"

    expense = Expense.objects.create(
        user=user,
        category=result['category'],
        amount=result['amount'],
        description=result['description'],
        date=result['date'],
        source='whatsapp',
    )

    return (
        f'✅ Recorded: {user.currency_symbol}{expense.amount} '
        f'under {expense.category.icon} {expense.category.name}'
    )


def get_help_message():
    return (
        '📱 *Expense Tracker Commands*\n\n'
        '*Add Expense:*\n'
        '<amount> <category> [description]\n'
        'Example: 120 petrol\n'
        'Example: 450 food lunch\n\n'
        '*View Statements:*\n'
        '• today\n'
        '• week\n'
        '• month\n'
        '• summary\n'
        '• category <name>\n\n'
        '*Other:*\n'
        '• categories\n'
        '• help'
    )


def get_categories_message(user):
    from expenses.models import Category

    categories = Category.objects.filter(user=user, is_active=True).order_by('name')

    if not categories:
        return '❌ No categories found. Add categories from the web dashboard.'

    message = '📂 *Your Categories:*\n\n'
    for cat in categories:
        message += f'{cat.icon} {cat.name}\n'

    return message
