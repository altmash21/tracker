import json
import logging
import os

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from users.models import WhatsAppMapping
from expenses.models import Expense
from .whatsapp_service import WhatsAppService
from .expense_handler import ExpenseParser, StatementGenerator


# -------------------------------------------------------------------
# LOGGER (IMPORTANT: must match LOGGING config in settings.py)
# -------------------------------------------------------------------
logger = logging.getLogger("whatsapp")

# Test endpoint to verify routing
from django.http import HttpResponse
def webhook_test(request):
    return HttpResponse("Webhook test OK")


# -------------------------------------------------------------------
# MAIN WEBHOOK ENDPOINT
# -------------------------------------------------------------------
@csrf_exempt
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    """
    WhatsApp Cloud API webhook
    GET  -> Verification
    POST -> Incoming messages
    """

    # Log immediately when request hits Django
    logger.info("========== WHATSAPP WEBHOOK HIT ==========")
    logger.info("Method: %s", request.method)
    logger.info("Path: %s", request.path)

    if request.method == "GET":
        return verify_webhook(request)

    return handle_webhook(request)


# -------------------------------------------------------------------
# WEBHOOK VERIFICATION (META)
# -------------------------------------------------------------------
def verify_webhook(request):
    """
    Meta webhook verification
    """
    mode = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    challenge = request.GET.get("hub.challenge")

    logger.info("Webhook verification request received")

    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verification SUCCESS")
        return HttpResponse(challenge, content_type="text/plain")

    logger.warning("Webhook verification FAILED")
    return HttpResponse("Verification failed", status=403)


# -------------------------------------------------------------------
# HANDLE INCOMING WEBHOOK (POST)
# -------------------------------------------------------------------
def handle_webhook(request):
    """
    Handle incoming WhatsApp messages
    """
    try:
        body = request.body.decode("utf-8")
        logger.info("Raw webhook body: %s", body)

        # ------------------------------------------------------------
        # OPTIONAL: Signature verification (ENABLE IN PRODUCTION)
        # ------------------------------------------------------------
        # if not settings.DEBUG:
        #     service = WhatsAppService()
        #     if not service.verify_webhook_signature(request):
        #         logger.warning("Invalid webhook signature")
        #         return JsonResponse({"status": "invalid_signature"}, status=200)

        data = json.loads(body)

        # Meta sometimes sends events without messages
        if "entry" not in data:
            logger.info("No entry in webhook payload")
            return JsonResponse({"status": "no_entry"}, status=200)

        for entry in data["entry"]:
            for change in entry.get("changes", []):
                value = change.get("value", {})

                messages = value.get("messages", [])
                for message in messages:
                    process_message(message)

        return JsonResponse({"status": "success"}, status=200)

    except json.JSONDecodeError:
        logger.error("Invalid JSON payload")
        return JsonResponse({"status": "invalid_json"}, status=200)

    except Exception as e:
        logger.exception("Unhandled webhook error")
        return JsonResponse({"status": "error"}, status=200)


# -------------------------------------------------------------------
# PROCESS INDIVIDUAL MESSAGE
# -------------------------------------------------------------------
def process_message(message):
    """
    Process a single WhatsApp message
    """
    try:
        message_type = message.get("type")
        from_number = message.get("from")
        message_id = message.get("id")

        logger.info("Incoming message from %s | type=%s", from_number, message_type)

        # Only text messages supported
        if message_type != "text":
            logger.info("Ignoring non-text message")
            return

        text = message.get("text", {}).get("body", "").strip()
        if not text:
            return

        logger.info("Message text: %s", text)

        # ------------------------------------------------------------
        # FIND USER BY WHATSAPP NUMBER
        # ------------------------------------------------------------
        normalized = from_number.lstrip("0")

        mapping = (
            WhatsAppMapping.objects
            .select_related("user")
            .filter(is_active=True)
            .filter(whatsapp_number__in=[from_number, normalized])
            .first()
        )

        whatsapp_service = WhatsAppService()

        if not mapping:
            logger.info("Unregistered number: %s", from_number)
            whatsapp_service.send_message(
                from_number,
                "❌ Your number is not registered. Please sign up on the website."
            )
            return

        user = mapping.user

        # ------------------------------------------------------------
        # PROCESS MESSAGE CONTENT
        # ------------------------------------------------------------
        response_text = process_user_message(user, text)

        whatsapp_service.send_message(from_number, response_text)
        whatsapp_service.mark_message_read(message_id)

    except Exception:
        logger.exception("Error processing message")


# -------------------------------------------------------------------
# PROCESS USER MESSAGE CONTENT
# -------------------------------------------------------------------
def process_user_message(user, text):
    text_lower = text.lower().strip()

    if text_lower == "today":
        return StatementGenerator(user).generate_today()

    if text_lower in ("week", "this week"):
        return StatementGenerator(user).generate_week()

    if text_lower in ("month", "this month"):
        return StatementGenerator(user).generate_month()

    if text_lower == "summary":
        return StatementGenerator(user).generate_summary()

    if text_lower.startswith("category "):
        category = text[9:].strip()
        return StatementGenerator(user).generate_category(category)

    if text_lower in ("help", "commands"):
        return get_help_message()

    if text_lower == "categories":
        return get_categories_message(user)

    # ------------------------------------------------------------
    # TRY PARSING AS EXPENSE
    # ------------------------------------------------------------
    parser = ExpenseParser(user)
    result = parser.parse(text)

    if not result:
        return get_help_message()

    if "error" in result:
        return f"❌ {result['message']}"

    expense = Expense.objects.create(
        user=user,
        category=result["category"],
        amount=result["amount"],
        description=result["description"],
        date=result["date"],
        source="whatsapp",
    )

    return (
        f"✅ Recorded: {user.currency_symbol}{expense.amount} "
        f"under {expense.category.icon} {expense.category.name}"
    )


# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------
def get_help_message():
    return (
        "📱 *Expense Tracker Commands*\n\n"
        "*Add Expense:*\n"
        "<amount> <category> [description]\n"
        "Example: 120 petrol\n"
        "Example: 450 food lunch\n\n"
        "*View Statements:*\n"
        "• today\n"
        "• week\n"
        "• month\n"
        "• summary\n"
        "• category <name>\n\n"
        "*Other:*\n"
        "• categories\n"
        "• help"
    )


def get_categories_message(user):
    from expenses.models import Category

    categories = Category.objects.filter(user=user, is_active=True).order_by("name")

    if not categories:
        return "❌ No categories found. Add categories from the web dashboard."

    message = "📂 *Your Categories:*\n\n"
    for cat in categories:
        message += f"{cat.icon} {cat.name}\n"

    return message


# -------------------------------------------------------------------
# MAIN WEBHOOK ENDPOINT
# -------------------------------------------------------------------
@csrf_exempt
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    """
    WhatsApp Cloud API webhook
    GET  -> Verification
    POST -> Incoming messages
    """

    # Log immediately when request hits Django
    logger.info("========== WHATSAPP WEBHOOK HIT ==========")
    logger.info("Method: %s", request.method)
    logger.info("Path: %s", request.path)

    if request.method == "GET":
        return verify_webhook(request)

    return handle_webhook(request)


# -------------------------------------------------------------------
# WEBHOOK VERIFICATION (META)
# -------------------------------------------------------------------
def verify_webhook(request):
    """
    Meta webhook verification
    """
    mode = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    challenge = request.GET.get("hub.challenge")

    logger.info("Webhook verification request received")

    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verification SUCCESS")
        return HttpResponse(challenge, content_type="text/plain")

    logger.warning("Webhook verification FAILED")
    return HttpResponse("Verification failed", status=403)


# -------------------------------------------------------------------
# HANDLE INCOMING WEBHOOK (POST)
# -------------------------------------------------------------------
def handle_webhook(request):
    """
    Handle incoming WhatsApp messages
    """
    try:
        body = request.body.decode("utf-8")
        logger.info("Raw webhook body: %s", body)

        # ------------------------------------------------------------
        # OPTIONAL: Signature verification (ENABLE IN PRODUCTION)
        # ------------------------------------------------------------
        # if not settings.DEBUG:
        #     service = WhatsAppService()
        #     if not service.verify_webhook_signature(request):
        #         logger.warning("Invalid webhook signature")
        #         return JsonResponse({"status": "invalid_signature"}, status=200)

        data = json.loads(body)

        # Meta sometimes sends events without messages
        if "entry" not in data:
            logger.info("No entry in webhook payload")
            return JsonResponse({"status": "no_entry"}, status=200)

        for entry in data["entry"]:
            for change in entry.get("changes", []):
                value = change.get("value", {})

                messages = value.get("messages", [])
                for message in messages:
                    process_message(message)

        return JsonResponse({"status": "success"}, status=200)

    except json.JSONDecodeError:
        logger.error("Invalid JSON payload")
        return JsonResponse({"status": "invalid_json"}, status=200)

    except Exception as e:
        logger.exception("Unhandled webhook error")
        return JsonResponse({"status": "error"}, status=200)


# -------------------------------------------------------------------
# PROCESS INDIVIDUAL MESSAGE
# -------------------------------------------------------------------
def process_message(message):
    """
    Process a single WhatsApp message
    """
    try:
        message_type = message.get("type")
        from_number = message.get("from")
        message_id = message.get("id")

        logger.info("Incoming message from %s | type=%s", from_number, message_type)

        # Only text messages supported
        if message_type != "text":
            logger.info("Ignoring non-text message")
            return

        text = message.get("text", {}).get("body", "").strip()
        if not text:
            return

        logger.info("Message text: %s", text)

        # ------------------------------------------------------------
        # FIND USER BY WHATSAPP NUMBER
        # ------------------------------------------------------------
        normalized = from_number.lstrip("0")

        mapping = (
            WhatsAppMapping.objects
            .select_related("user")
            .filter(is_active=True)
            .filter(whatsapp_number__in=[from_number, normalized])
            .first()
        )

        whatsapp_service = WhatsAppService()

        if not mapping:
            logger.info("Unregistered number: %s", from_number)
            whatsapp_service.send_message(
                from_number,
                "❌ Your number is not registered. Please sign up on the website."
            )
            return

        user = mapping.user

        # ------------------------------------------------------------
        # PROCESS MESSAGE CONTENT
        # ------------------------------------------------------------
        response_text = process_user_message(user, text)

        whatsapp_service.send_message(from_number, response_text)
        whatsapp_service.mark_message_read(message_id)

    except Exception:
        logger.exception("Error processing message")


# -------------------------------------------------------------------
# PROCESS USER MESSAGE CONTENT
# -------------------------------------------------------------------
def process_user_message(user, text):
    text_lower = text.lower().strip()

    if text_lower == "today":
        return StatementGenerator(user).generate_today()

    if text_lower in ("week", "this week"):
        return StatementGenerator(user).generate_week()

    if text_lower in ("month", "this month"):
        return StatementGenerator(user).generate_month()

    if text_lower == "summary":
        return StatementGenerator(user).generate_summary()

    if text_lower.startswith("category "):
        category = text[9:].strip()
        return StatementGenerator(user).generate_category(category)

    if text_lower in ("help", "commands"):
        return get_help_message()

    if text_lower == "categories":
        return get_categories_message(user)

    # ------------------------------------------------------------
    # TRY PARSING AS EXPENSE
    # ------------------------------------------------------------
    parser = ExpenseParser(user)
    result = parser.parse(text)

    if not result:
        return get_help_message()

    if "error" in result:
        return f"❌ {result['message']}"

    expense = Expense.objects.create(
        user=user,
        category=result["category"],
        amount=result["amount"],
        description=result["description"],
        date=result["date"],
        source="whatsapp",
    )

    return (
        f"✅ Recorded: {user.currency_symbol}{expense.amount} "
        f"under {expense.category.icon} {expense.category.name}"
    )


# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------
def get_help_message():
    return (
        "📱 *Expense Tracker Commands*\n\n"
        "*Add Expense:*\n"
        "<amount> <category> [description]\n"
        "Example: 120 petrol\n"
        "Example: 450 food lunch\n\n"
        "*View Statements:*\n"
        "• today\n"
        "• week\n"
        "• month\n"
        "• summary\n"
        "• category <name>\n\n"
        "*Other:*\n"
        "• categories\n"
        "• help"
    )


def get_categories_message(user):
    from expenses.models import Category

    categories = Category.objects.filter(user=user, is_active=True).order_by("name")

    if not categories:
        return "❌ No categories found. Add categories from the web dashboard."

    message = "📂 *Your Categories:*\n\n"
    for cat in categories:
        message += f"{cat.icon} {cat.name}\n"

    return message
