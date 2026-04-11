import hashlib
import json
import logging
import mimetypes
import os

import google.genai as genai
from django.core.cache import cache
from django.conf import settings

from expenses.models import Category, Expense

logger = logging.getLogger(__name__)


FALLBACK_EXPENSE = {
    'amount': 0,
    'category': 'Other',
    'description': 'Unable to parse',
    'merchant': 'Unknown',
    'date': None,
}

ALLOWED_CATEGORIES = {
    'food': 'Food',
    'travel': 'Travel',
    'groceries': 'Groceries',
    'shopping': 'Shopping',
    'bills': 'Bills',
    'entertainment': 'Entertainment',
    'other': 'Other',
}

FUZZY_MAP = {
    'restaurant': 'Food',
    'cafe': 'Food',
    'pizza': 'Food',
    'uber': 'Travel',
    'ola': 'Travel',
    'taxi': 'Travel',
    'bus': 'Travel',
    'movie': 'Entertainment',
    'netflix': 'Entertainment',
}


def _get_api_key():
    return getattr(settings, 'GEMINI_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')


def _strip_markdown(content: str) -> str:
    text = (content or '').strip()
    if text.startswith('```'):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        text = '\n'.join(lines).strip()
        if text.lower().startswith('json'):
            text = text[4:].strip()
    return text


def _extract_json_payload(content: str) -> str:
    text = _strip_markdown(content)
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text


def _parse_expense_payload(content: str) -> dict:
    payload = json.loads(_extract_json_payload(content))
    amount = payload.get('amount', 0)
    category = str(payload.get('category', 'Other')).strip() or 'Other'
    description = str(payload.get('description', 'Unable to parse')).strip() or 'Unable to parse'
    merchant = str(payload.get('merchant', 'Unknown')).strip() or 'Unknown'
    date = payload.get('date')

    try:
        amount = float(amount)
    except (TypeError, ValueError):
        amount = 0

    if amount < 0:
        amount = 0

    return {
        'amount': amount,
        'category': category,
        'description': description,
        'merchant': merchant,
        'date': date,
    }


def _normalize_category_name(category_name: str) -> str:
    normalized = (category_name or '').strip()
    if not normalized:
        return 'Other'
    normalized_lower = normalized.lower()
    for keyword, mapped_category in FUZZY_MAP.items():
        if keyword in normalized_lower:
            return mapped_category
    return ALLOWED_CATEGORIES.get(normalized_lower, 'Other')


def _calculate_confidence(parsed_data: dict) -> float:
    amount = parsed_data.get('amount') or 0
    category = str(parsed_data.get('category') or '').strip()
    description = str(parsed_data.get('description') or '').strip()

    confidence = 1.0
    if amount == 0:
        return 0.0
    if len(description) < 5:
        confidence -= 0.3
    if category == 'Other':
        confidence -= 0.2
    if amount < 10:
        confidence -= 0.2

    if confidence < 0:
        return 0.0
    if confidence > 1:
        return 1.0
    return confidence


def _clean_description(text):
    cleaned = ' '.join((text or '').split()).strip()
    return cleaned[:100]


def _get_cache_key(image_data: bytes):
    return f"receipt:{hashlib.md5(image_data).hexdigest()}"


def _get_existing_or_other_category(user, category_name):
    normalized_name = _normalize_category_name(category_name)
    category = Category.objects.filter(user=user, name__iexact=normalized_name, is_active=True).first()
    if category:
        return category

    other_category = Category.objects.filter(user=user, name__iexact='Other', is_active=True).first()
    if other_category:
        return other_category

    return Category.objects.create(
        user=user,
        name='Other',
        icon='💰',
        is_active=True,
    )


def _read_image_data(image_path: str) -> bytes:
    try:
        with open(image_path, 'rb') as image_file:
            return image_file.read()
    except OSError as exc:
        raise ValueError(f'Unable to read receipt image: {image_path}') from exc


def parse_receipt_image(image_path: str, user, image_data: bytes = None):
    api_key = _get_api_key()
    if not api_key:
        logger.warning('GEMINI_API_KEY is not set; receipt parsing skipped')
        return dict(FALLBACK_EXPENSE)

    if not image_path or not os.path.exists(image_path):
        logger.error('Receipt image file not found: %s', image_path)
        return dict(FALLBACK_EXPENSE)

    mime_type, _ = mimetypes.guess_type(image_path)
    mime_type = mime_type or 'image/jpeg'
    image_data = image_data if image_data is not None else _read_image_data(image_path)

    primary_prompt = """Extract expense details from this receipt image.

Return ONLY valid JSON:
{
"amount": number,
"category": "string",
"description": "string",
"merchant": "string",
"date": "YYYY-MM-DD"
}

Strict Rules:

* Always extract the FINAL TOTAL (look for "Total", "Grand Total", "Amount Paid")
* Ignore subtotal, taxes, discounts if final total exists
* If multiple totals exist, choose the largest final payable amount
* Category must be one of: Food, Travel, Groceries, Shopping, Bills, Entertainment, Other
* Match category to the closest logical type
* Description must include merchant name + short context (e.g. "Dominos pizza", "Uber ride")
* Merchant: extract the business/store name
* Date: extract the transaction date in YYYY-MM-DD format (or use today's date if not found)

If uncertain:
{
"amount": 0,
"category": "Other",
"description": "Unable to parse",
"merchant": "Unknown",
"date": null
}
"""

    retry_prompt = """Extract ONLY the FINAL payable amount, merchant, and category from this receipt.

Return STRICT JSON ONLY:
{
"amount": number,
"category": "string",
"description": "string",
"merchant": "string",
"date": "YYYY-MM-DD"
}

Rules:

* Focus only on final amount
* Ignore all other numbers
* Category must be one of: Food, Travel, Groceries, Shopping, Bills, Entertainment, Other
* Merchant is the business/store name
* Date in YYYY-MM-DD format or null
* If unsure, return fallback JSON
"""

    client = genai.Client(api_key=api_key)
    prompts = [primary_prompt, retry_prompt]

    for attempt, prompt in enumerate(prompts, start=1):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=[
                    {
                        'role': 'user',
                        'parts': [
                            {
                                'text': prompt
                            },
                            {
                                'inline_data': {
                                    'mime_type': mime_type,
                                    'data': image_data,
                                }
                            },
                        ],
                    }
                ],
                config={
                    'temperature': 0,
                    'response_mime_type': 'application/json',
                },
            )

            response_text = (getattr(response, 'text', '') or '').strip()
            logger.info(
                'Gemini receipt parse returned %d characters for %s (attempt %d)',
                len(response_text),
                image_path,
                attempt,
            )

            if not response_text:
                logger.warning('Gemini returned an empty receipt response for %s (attempt %d)', image_path, attempt)
                if attempt < len(prompts):
                    continue
                return dict(FALLBACK_EXPENSE)

            try:
                parsed = _parse_expense_payload(response_text)
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                logger.warning('Failed to parse Gemini receipt response for %s: %s (attempt %d)', image_path, exc, attempt)
                if attempt < len(prompts):
                    continue
                return dict(FALLBACK_EXPENSE)

            parsed['category'] = _normalize_category_name(parsed.get('category'))
            parsed['confidence'] = _calculate_confidence(parsed)

            if parsed['confidence'] < 0.5:
                logger.warning('Low confidence receipt parse for %s: %.2f', image_path, parsed['confidence'])
                if attempt < len(prompts):
                    continue
                return dict(FALLBACK_EXPENSE)

            logger.info(
                'Gemini receipt parse success for %s: amount=%s category=%s confidence=%.2f',
                image_path,
                parsed.get('amount'),
                parsed.get('category'),
                parsed.get('confidence', 0.0),
            )
            return parsed

        except Exception as exc:
            err = str(exc).lower()
            if '429' in err or 'quota' in err or 'resource_exhausted' in err:
                logger.warning('Gemini receipt parse quota/rate limit for %s: %s', image_path, exc)
                if attempt < len(prompts):
                    continue
                return dict(FALLBACK_EXPENSE)
            logger.error('Gemini receipt parse failed for %s: %s (attempt %d)', image_path, exc, attempt, exc_info=True)
            if attempt < len(prompts):
                continue
            return dict(FALLBACK_EXPENSE)

    return dict(FALLBACK_EXPENSE)


def process_receipt(image_path: str, user) -> Expense:
    """Parse a receipt image with Gemini and create the expense."""
    from datetime import datetime, date as date_type
    
    if not image_path or not os.path.exists(image_path):
        raise ValueError('Receipt image file not found')

    image_data = _read_image_data(image_path)
    cache_key = _get_cache_key(image_data)
    cached = cache.get(cache_key)
    if cached and cached.get('expense_id'):
        existing_expense = Expense.objects.filter(id=cached['expense_id'], user=user).select_related('category').first()
        if existing_expense:
            return existing_expense

    parsed = parse_receipt_image(image_path, user, image_data=image_data)
    if not parsed:
        raise ValueError('Unable to parse receipt image')

    try:
        amount = float(parsed.get('amount') or 0)
    except (TypeError, ValueError):
        amount = 0

    category_name = parsed.get('category') or 'Other'
    description = _clean_description(parsed.get('description') or '') or 'Unable to parse'
    merchant = str(parsed.get('merchant') or 'Unknown').strip() or 'Unknown'
    
    # Enhance description with merchant if available
    if merchant and merchant.lower() != 'unknown':
        if merchant not in description:
            description = f"{merchant}: {description}" if description != 'Unable to parse' else merchant

    if amount <= 0:
        raise ValueError('No bill amount found in receipt image')

    if amount < 5:
        raise ValueError('Suspiciously low amount detected in receipt image')

    category = _get_existing_or_other_category(user, category_name)

    # Parse receipt date if available
    receipt_date = None
    date_str = parsed.get('date')
    if date_str:
        try:
            receipt_date = datetime.strptime(str(date_str), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            pass
    
    # Use current date if receipt date not found
    if not receipt_date:
        from django.utils import timezone
        receipt_date = timezone.now().date()

    expense = Expense.objects.create(
        user=user,
        amount=amount,
        category=category,
        description=description,
        date=receipt_date,
        source='ocr',
    )

    # Learn keywords from receipt (similar to text parser)
    try:
        from .expense_handler import ExpenseParser
        parser = ExpenseParser(user)
        parser._learn_from_ai_result(description, merchant, category)
        logger.info('[Receipt] Auto-learned keywords for category %s from merchant %s', category.name, merchant)
    except Exception as e:
        logger.warning('[Receipt] Failed to learn keywords: %s', e)

    cache.set(
        cache_key,
        {
            'expense_id': expense.id,
            'extracted_text': '',
            'raw_ocr_response': parsed,
            'amount': float(expense.amount),
            'category': expense.category.name,
            'description': expense.description,
            'merchant': merchant,
            'date': str(receipt_date),
        },
        timeout=86400,
    )

    return expense