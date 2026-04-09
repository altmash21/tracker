import json
import logging
import os

import google.generativeai as genai
from PIL import Image

from .exceptions import AICategoriaztionException

logger = logging.getLogger(__name__)


def _parse_json_payload(content):
    content = (content or '').strip()
    if content.startswith('```'):
        content = content.strip('`')
        if content.lower().startswith('json'):
            content = content[4:].strip()
    return json.loads(content)


def _build_model(api_key):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        system_instruction=(
            'You extract structured expense data from receipts. '
            'Return ONLY valid JSON with keys: amount (number), category (string), description (string). '
            'Do not include markdown, code fences, or explanation text.'
        ),
    )


def _normalize_result(parsed):
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
        raise AICategoriaztionException('GEMINI_API_KEY is not set')

    try:
        model = _build_model(api_key)
        response = model.generate_content(
            [
                'Extract amount, category, and description from this receipt text.',
                text,
            ],
            generation_config={
                'response_mime_type': 'application/json',
                'temperature': 0,
            },
            request_options={'timeout': 10},
        )

        content = getattr(response, 'text', '')
        parsed = _parse_json_payload(content)

        return _normalize_result(parsed)

    except AICategoriaztionException:
        raise
    except Exception as exc:
        logger.exception('AI categorization failed')
        raise AICategoriaztionException(str(exc))


def categorize_from_image_with_gemini(image_path: str) -> dict:
    """Use Gemini multimodal input to categorize directly from a local receipt image."""
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise AICategoriaztionException('GEMINI_API_KEY is not set')

    if not image_path or not os.path.exists(image_path):
        raise AICategoriaztionException(f'Image file not found: {image_path}')

    try:
        model = _build_model(api_key)
        image = Image.open(image_path)
        response = model.generate_content(
            [
                'Extract amount, category, and description from this receipt image.',
                image,
            ],
            generation_config={
                'response_mime_type': 'application/json',
                'temperature': 0,
            },
            request_options={'timeout': 10},
        )

        content = getattr(response, 'text', '')
        parsed = _parse_json_payload(content)

        return _normalize_result(parsed)

    except AICategoriaztionException:
        raise
    except Exception as exc:
        logger.exception('Gemini image categorization failed')
        raise AICategoriaztionException(str(exc))