import logging
import os

from google.cloud import vision
from google.protobuf.json_format import MessageToDict

from .exceptions import OCRException

logger = logging.getLogger(__name__)


def extract_text_from_image(image_path: str) -> dict:
    """Run Google Vision OCR on a local image file."""
    credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not credentials_path:
        raise OCRException('GOOGLE_APPLICATION_CREDENTIALS is not set')

    if not os.path.exists(credentials_path):
        raise OCRException(f'Google credentials file not found: {credentials_path}')

    if not image_path or not os.path.exists(image_path):
        raise OCRException(f'Image file not found: {image_path}')

    try:
        client = vision.ImageAnnotatorClient()
        with open(image_path, 'rb') as image_file:
            content = image_file.read()

        image = vision.Image(content=content)
        response = client.document_text_detection(image=image)
        raw_response = MessageToDict(response._pb, preserving_proto_field_name=True)

        logger.info('Google Vision raw response for %s: %s', image_path, raw_response)

        if response.error.message:
            raise OCRException(response.error.message)

        text = ''
        confidence = 0.0

        if response.full_text_annotation:
            text = response.full_text_annotation.text or ''
            pages = getattr(response.full_text_annotation, 'pages', []) or []
            confidences = [getattr(page, 'confidence', None) for page in pages if getattr(page, 'confidence', None) is not None]
            if confidences:
                confidence = float(sum(confidences) / len(confidences))

        if not text.strip() and raw_response.get('text_annotations'):
            text = raw_response['text_annotations'][0].get('description', '')

        if not text.strip():
            raise OCRException('No text detected in receipt image')

        return {
            'text': text.strip(),
            'confidence': float(confidence),
            'raw': raw_response,
        }

    except OCRException:
        raise
    except Exception as exc:
        logger.exception('OCR failed for %s', image_path)
        raise OCRException(str(exc))