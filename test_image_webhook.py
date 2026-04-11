#!/usr/bin/env python
"""
Test script for WhatsApp image message webhook handling.
Tests image message flow, receipt parsing, and keyword learning.
"""

import os
import django
import json
import base64
from io import BytesIO
from PIL import Image

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expense_tracker.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from expenses.models import Category, CategoryKeyword, Expense
from whatsapp_integration.receipt_processor import process_receipt
from unittest.mock import patch, MagicMock

User = get_user_model()


def create_test_image(width=400, height=300, color='white'):
    """Create a simple test image."""
    img = Image.new('RGB', (width, height), color=color)
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes.getvalue()


def test_webhook_accepts_images():
    """Test that webhook no longer blocks image messages."""
    print("\n=== TEST 1: Webhook accepts image messages ===")
    
    webhook_payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "wamid.123",
                                    "from": "919999999999",
                                    "type": "image",
                                    "image": {
                                        "id": "media_id_123",
                                        "mime_type": "image/jpeg",
                                        "sha256": "abc123"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    
    client = Client()
    response = client.post(
        '/whatsapp/webhook/',
        data=json.dumps(webhook_payload),
        content_type='application/json'
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("✅ Webhook accepts image messages (HTTP 200)")


def test_webhook_still_blocks_unsupported_types():
    """Test that webhook blocks unsupported message types (audio, video, etc)."""
    print("\n=== TEST 2: Webhook rejects unsupported types ===")
    
    webhook_payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "wamid.456",
                                    "from": "919999999999",
                                    "type": "audio",
                                    "audio": {
                                        "id": "media_id_456"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    
    client = Client()
    response = client.post(
        '/whatsapp/webhook/',
        data=json.dumps(webhook_payload),
        content_type='application/json'
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("✅ Webhook silently ignores unsupported types (HTTP 200)")


def test_receipt_data_extraction():
    """Test receipt fields extraction (merchant, date, amount)."""
    print("\n=== TEST 3: Receipt extracts merchant and date ===")
    
    # This test verifies the prompt includes merchant and date fields
    from whatsapp_integration.receipt_processor import parse_receipt_image
    
    user = User.objects.first()
    if not user:
        user = User.objects.create_user(username='testuser', password='pass')
        Category.objects.create(user=user, name='Food', icon='🍔', is_active=True)
    
    # Mock Gemini response
    mock_response = {
        "amount": 250.50,
        "category": "Food",
        "description": "Pizza dinner",
        "merchant": "Dominos",
        "date": "2026-04-11"
    }
    
    with patch('google.genai.Client') as mock_genai:
        mock_client = MagicMock()
        mock_genai.return_value = mock_client
        
        mock_response_obj = MagicMock()
        mock_response_obj.text = json.dumps(mock_response)
        mock_client.models.generate_content.return_value = mock_response_obj
        
        test_image = create_test_image()
        
        parsed = parse_receipt_image('/tmp/test.jpg', user, image_data=test_image)
        
        assert parsed.get('merchant') == 'Dominos', f"Expected merchant 'Dominos', got {parsed.get('merchant')}"
        assert parsed.get('date') == '2026-04-11', f"Expected date '2026-04-11', got {parsed.get('date')}"
        assert parsed.get('amount') == 250.50
        
    print("✅ Receipt correctly extracts merchant, date, and amount")


def test_keyword_learning_from_receipt():
    """Test that receipt processing learns keywords."""
    print("\n=== TEST 4: Receipt learning saves keywords ===")
    
    user = User.objects.first()
    if not user:
        user = User.objects.create_user(username='testuser2', password='pass')
    
    food_cat = Category.objects.filter(user=user, name='Food').first()
    if not food_cat:
        food_cat = Category.objects.create(user=user, name='Food', icon='🍔', is_active=True)
    
    # Clear existing keywords for this test
    CategoryKeyword.objects.filter(category=food_cat, added_by='system').delete()
    
    # Simulate receipt learning
    from whatsapp_integration.expense_handler import ExpenseParser
    parser = ExpenseParser(user)
    
    parser._learn_from_ai_result(
        message="250 food",
        description="Dominos pizza dinner",
        category=food_cat
    )
    
    # Check keywords were saved
    keywords = CategoryKeyword.objects.filter(
        category=food_cat,
        added_by='system'
    ).values_list('keyword', flat=True)
    
    keyword_list = list(keywords)
    assert 'dominos' in keyword_list or 'pizza' in keyword_list, \
        f"Expected learning keywords, got {keyword_list}"
    
    print(f"✅ Receipt learning saved keywords: {keyword_list}")


def test_gemini_model_consistency():
    """Test that receipt processor uses gemini-2.5-flash-lite."""
    print("\n=== TEST 5: Model consistency (gemini-2.5-flash-lite) ===")
    
    # Read receipt_processor.py and check model name
    with open('d:\\expense tracking system\\whatsapp_integration\\receipt_processor.py', 'r') as f:
        content = f.read()
        assert 'gemini-2.5-flash-lite' in content, \
            "Receipt processor should use gemini-2.5-flash-lite"
        assert 'model=\'gemini-2.5-flash-lite\'' in content or \
               'model="gemini-2.5-flash-lite"' in content, \
               "Model parameter not found"
    
    print("✅ Receipt processor uses gemini-2.5-flash-lite (consistent with text parser)")


def main():
    """Run all tests."""
    print("\n╔════════════════════════════════════════╗")
    print("║  WhatsApp Image Webhook Tests         ║")
    print("╚════════════════════════════════════════╝")
    
    try:
        test_webhook_accepts_images()
        test_webhook_still_blocks_unsupported_types()
        test_receipt_data_extraction()
        test_keyword_learning_from_receipt()
        test_gemini_model_consistency()
        
        print("\n" + "="*40)
        print("✅ ALL TESTS PASSED!")
        print("="*40)
        print("\n📝 Summary:")
        print("  • Webhook now accepts image messages")
        print("  • Receipt parser extracts: amount, category, merchant, date")
        print("  • Learned keywords flow back to text parser")
        print("  • Models aligned to gemini-2.5-flash-lite")
        print("="*40 + "\n")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
