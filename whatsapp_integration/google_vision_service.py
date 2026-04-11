import logging
import os
import mimetypes

import google.genai as genai
from django.conf import settings

logger = logging.getLogger(__name__)


def extract_text_from_image(image_path: str) -> str:
    """Run Gemini multimodal OCR on a local image file and return raw extracted text."""
    api_key = getattr(settings, 'GEMINI_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')
    if not api_key:
        logger.warning('GEMINI_API_KEY is not set; OCR skipped')
        return ''

    if not image_path or not os.path.exists(image_path):
        logger.error('Image file not found for OCR: %s', image_path)
        return ''

    try:
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()

        mime_type, _ = mimetypes.guess_type(image_path)
        mime_type = mime_type or 'image/jpeg'

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=[
                {
                    'role': 'user',
                    'parts': [
                        {
                            'text': (
                                'You are a receipt OCR engine. Extract ALL text from this '
                                'receipt image exactly as it appears. Return only the raw '
                                'text, no formatting, no explanation.'
                            )
                        },
                        {
                            'inline_data': {
                                'mime_type': mime_type,
                                'data': image_data,
                            }
                        }
                    ]
                }
            ],
            config={
                'temperature': 0,
            },
        )

        extracted = (response.text or '').strip()
        logger.info('Gemini OCR extracted %d characters from %s', len(extracted), image_path)
        return extracted

    except Exception:
        logger.exception('Gemini OCR failed for %s', image_path)
        return ''