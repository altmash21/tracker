import json
import logging

from .receipt_processor import parse_receipt_image

logger = logging.getLogger(__name__)


def extract_expense_from_image(image_path: str):
    return parse_receipt_image(image_path, user=None)


def extract_text_from_image(image_path: str) -> str:
    result = parse_receipt_image(image_path, user=None)
    if not result:
        return ''
    return json.dumps(result, ensure_ascii=False)
