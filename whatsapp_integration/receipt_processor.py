import hashlib
import logging
import re

from django.core.cache import cache

from expenses.models import Category, Expense

from .ai_categorization_service import categorize_with_ai
from .exceptions import AmountNotFoundException, AICategoriaztionException, OCRException
from .google_vision_service import extract_text_from_image

logger = logging.getLogger(__name__)


CATEGORY_KEYWORDS = {
    'Food': ['pizza', 'restaurant', 'cafe', 'swiggy', 'zomato', 'dominos', 'burger', 'biryani'],
    'Transport': ['petrol', 'fuel', 'uber', 'ola', 'rapido', 'diesel', 'cab'],
    'Shopping': ['amazon', 'flipkart', 'myntra', 'meesho', 'mall', 'supermarket'],
    'Bills': ['electricity', 'recharge', 'rent', 'wifi', 'broadband', 'insurance'],
}

TOTAL_KEYWORDS = ['total', 'amount due', 'grand total', 'net payable', 'to pay']


def _normalize_number(value):
    return value.replace(',', '').replace('₹', '').strip()


def _clean_description(text):
    cleaned = re.sub(r'\s+', ' ', text or '').strip()
    return cleaned[:100]


def _get_cache_key(image_path):
    return hashlib.md5(image_path.encode('utf-8')).hexdigest()


def extract_amount(text: str):
    """Extract an amount using receipt heuristics."""
    if not text:
        return None

    number_pattern = r'(?:₹\s*)?(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)'
    lower_text = text.lower()

    for keyword in TOTAL_KEYWORDS:
        pattern_after = rf'{re.escape(keyword)}[^\d₹]{{0,30}}{number_pattern}'
        match_after = re.search(pattern_after, lower_text, re.IGNORECASE)
        if match_after:
            return float(_normalize_number(match_after.group(1)))

        pattern_before = rf'{number_pattern}[^\d\w]{{0,30}}{re.escape(keyword)}'
        match_before = re.search(pattern_before, lower_text, re.IGNORECASE)
        if match_before:
            return float(_normalize_number(match_before.group(1)))

    matches = re.findall(number_pattern, text)
    if not matches:
        return None

    numbers = [float(_normalize_number(match)) for match in matches]
    return max(numbers) if numbers else None


def rule_based_category(text: str):
    """Return a category name and whether the match is high confidence."""
    if not text:
        return 'Other', False

    lower_text = text.lower()
    for category_name, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', lower_text):
                return category_name, True

    return 'Other', False


def _get_or_create_category(user, category_name):
    category_name = (category_name or 'Other').strip() or 'Other'
    category = Category.objects.filter(user=user, name__iexact=category_name, is_active=True).first()
    if category:
        return category

    return Category.objects.create(
        user=user,
        name=category_name.title(),
        icon='💰',
        is_active=True,
    )


def process_receipt(image_path: str, user) -> Expense:
    """Full OCR + categorization pipeline for a receipt image."""
    cache_key = _get_cache_key(image_path)
    cached = cache.get(cache_key)
    if cached and cached.get('expense_id'):
        existing_expense = Expense.objects.filter(id=cached['expense_id'], user=user).select_related('category').first()
        if existing_expense:
            return existing_expense

    ocr_result = extract_text_from_image(image_path)
    text = (ocr_result.get('text') or '').strip()
    if not text:
        raise OCRException('No readable text found in receipt')

    amount = extract_amount(text)
    if amount is None:
        raise AmountNotFoundException('No bill amount found in receipt text')

    category_name, is_confident = rule_based_category(text)
    description = _clean_description(text)

    if not is_confident:
        ai_result = categorize_with_ai(text)
        amount = ai_result.get('amount') or amount
        category_name = ai_result.get('category') or category_name
        description = ai_result.get('description') or description

    category = _get_or_create_category(user, category_name)

    expense = Expense.objects.create(
        user=user,
        amount=amount,
        category=category,
        description=description,
        source='ocr',
    )

    cache.set(
        cache_key,
        {
            'expense_id': expense.id,
            'extracted_text': text,
            'raw_ocr_response': ocr_result.get('raw', {}),
            'amount': float(expense.amount),
            'category': expense.category.name,
            'description': expense.description,
        },
        timeout=86400,
    )

    return expense