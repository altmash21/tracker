import json
import logging
import os

import google.genai as genai
from PIL import Image

from .exceptions import AICategoriaztionException

logger = logging.getLogger(__name__)


KEYWORD_CATEGORIES = {
    'Food': [
        'food', 'lunch', 'dinner', 'breakfast', 'restaurant', 'cafe',
        'coffee', 'swiggy', 'zomato',
    ],
    'Transport': [
        'petrol', 'fuel', 'diesel', 'uber', 'ola', 'auto', 'bus',
        'train', 'metro', 'cab', 'toll',
    ],
    'Utilities': [
        'electricity', 'water', 'gas', 'bill', 'recharge', 'internet',
        'wifi', 'mobile', 'phone',
    ],
    'Shopping': [
        'shopping', 'clothes', 'amazon', 'flipkart', 'grocery',
        'groceries', 'vegetables', 'fruits',
    ],
    'Healthcare': [
        'medicine', 'doctor', 'hospital', 'pharmacy', 'medical',
        'health', 'clinic',
    ],
    'Entertainment': [
        'movie', 'cinema', 'netflix', 'game', 'gym', 'fitness',
        'concert', 'ticket',
    ],
    'Education': [
        'book', 'course', 'school', 'college', 'tuition', 'fee',
        'stationery', 'notebook',
    ],
}


def _keyword_categorize(text: str) -> str:
    """Return best-match category from keywords, else 'Other'."""
    text_lower = text.lower()
    for category, keywords in KEYWORD_CATEGORIES.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return 'Other'


def _extract_amount(text: str):
    """Try to extract a number from text."""
    import re

    numbers = re.findall(r'\d+(?:\.\d+)?', text)
    return float(numbers[0]) if numbers else 0.0


def _keyword_fallback(text: str) -> dict:
    """Full fallback using keyword matching when AI is unavailable."""
    return {
        'amount': _extract_amount(text),
        'category': _keyword_categorize(text),
        'description': text.strip(),
    }


def _parse_json_payload(content):
    content = (content or '').strip()
    if content.startswith('```'):
        content = content.strip('`')
        if content.lower().startswith('json'):
            content = content[4:].strip()
    return json.loads(content)




def _build_client(api_key):
    """Create and return a Genai API client."""
    return genai.Client(api_key=api_key)


def _normalize_result(parsed):
    """Normalize and validate parsed AI response."""
    amount = parsed.get('amount')
    category = parsed.get('category')
    description = parsed.get('description', '')

    if amount is None or category is None:
        raise AICategoriaztionException('AI response missing required fields')

    return {
        'amount': float(amount),
        'category': str(category).strip(),
        'description': str(description).strip(),
    }


def categorize_with_ai(text: str) -> dict:
    """Use Gemini to infer amount, category, and description from receipt text."""
    # NOTE: OPENAI_API_KEY is no longer used; remove it from your .env and use GEMINI_API_KEY.
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        logger.warning('GEMINI_API_KEY not set, using keyword fallback')
        return _keyword_fallback(text)

    try:
        client = _build_client(api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=[
                {
                    'role': 'user',
                    'parts': [
                        {
                            'text': (
                                'You extract structured expense data from receipts. '
                                'Return ONLY valid JSON with keys: amount (number), category (string), description (string). '
                                'Do not include markdown, code fences, or explanation text.\n\n'
                                'Extract amount, category, and description from this receipt text:\n'
                                + text
                            )
                        }
                    ]
                }
            ],
            config={
                'response_mime_type': 'application/json',
                'temperature': 0,
            },
        )

        content = response.text if hasattr(response, 'text') else ''
        parsed = _parse_json_payload(content)

        return _normalize_result(parsed)

    except AICategoriaztionException:
        raise
    except Exception as exc:
        err = str(exc)
        if '429' in err or 'RESOURCE_EXHAUSTED' in err:
            logger.warning('Gemini quota exceeded, using keyword fallback')
            return _keyword_fallback(text)
        logger.exception('AI categorization failed')
        raise AICategoriaztionException(err)


def categorize_from_image_with_gemini(image_path: str) -> dict:
    """Use Gemini multimodal input to categorize directly from a local receipt image."""
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise AICategoriaztionException('GEMINI_API_KEY is not set')

    if not image_path or not os.path.exists(image_path):
        raise AICategoriaztionException(f'Image file not found: {image_path}')

    try:
        client = _build_client(api_key)
        image = Image.open(image_path)
        
        # Convert PIL image to bytes for the API
        import io
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='JPEG')
        image_bytes.seek(0)
        image_data = image_bytes.read()
        
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=[
                {
                    'role': 'user',
                    'parts': [
                        {
                            'text': (
                                'You extract structured expense data from receipts. '
                                'Return ONLY valid JSON with keys: amount (number), category (string), description (string). '
                                'Do not include markdown, code fences, or explanation text.\n\n'
                                'Extract amount, category, and description from this receipt image.'
                            )
                        },
                        {
                            'inline_data': {
                                'mime_type': 'image/jpeg',
                                'data': image_data,
                            }
                        }
                    ]
                }
            ],
            config={
                'response_mime_type': 'application/json',
                'temperature': 0,
            },
        )

        content = response.text if hasattr(response, 'text') else ''
        parsed = _parse_json_payload(content)

        return _normalize_result(parsed)

    except AICategoriaztionException:
        raise
    except Exception as exc:
        err = str(exc)
        if '429' in err or 'RESOURCE_EXHAUSTED' in err:
            logger.warning('Gemini quota exceeded on image, returning fallback')
            return {'amount': 0.0, 'category': 'Other', 'description': 'Image receipt'}
        logger.exception('Gemini image categorization failed')
        raise AICategoriaztionException(err)