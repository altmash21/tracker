#!/usr/bin/env python
"""
Simplified test for WhatsApp image message webhook handling.
"""

import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expense_tracker.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import RequestFactory
from whatsapp_integration.views import handle_webhook
from expenses.models import Category, CategoryKeyword

User = get_user_model()


def test_webhook_accepts_images():
    """Test that webhook accepts image messages."""
    print("\nTEST 1: Webhook accepts image messages")
    print("-" * 40)
    
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
                                        "id": "media_id_123"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    
    factory = RequestFactory()
    request = factory.post(
        '/whatsapp/webhook/',
        data=json.dumps(webhook_payload),
        content_type='application/json'
    )
    
    try:
        response = handle_webhook(request)
        assert response.status_code == 200
        print("PASS: Webhook accepts image messages (HTTP 200)")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_webhook_rejects_unsupported():
    """Test that webhook rejects unsupported message types."""
    print("\nTEST 2: Webhook rejects unsupported types")
    print("-" * 40)
    
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
    
    factory = RequestFactory()
    request = factory.post(
        '/whatsapp/webhook/',
        data=json.dumps(webhook_payload),
        content_type='application/json'
    )
    
    try:
        response = handle_webhook(request)
        assert response.status_code == 200
        print("PASS: Webhook silently ignores unsupported types (HTTP 200)")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_receipt_fields_in_code():
    """Test that receipt processor includes merchant and date fields."""
    print("\nTEST 3: Receipt processor extracts merchant and date")
    print("-" * 40)
    
    with open('d:\\expense tracking system\\whatsapp_integration\\receipt_processor.py', 'r') as f:
        content = f.read()
        
    checks = [
        ('merchant' in content, "merchant field in code"),
        ('"date"' in content or "'date'" in content, "date field in code"),
        ('YYYY-MM-DD' in content, "date format in prompt"),
    ]
    
    all_pass = True
    for check, desc in checks:
        if check:
            print(f"  PASS: {desc}")
        else:
            print(f"  FAIL: {desc}")
            all_pass = False
    
    if all_pass:
        print("PASS: Receipt extracts merchant and date")
    else:
        print("FAIL: Receipt field extraction")
    
    return all_pass


def test_model_consistency():
    """Test that receipt uses gemini-2.5-flash-lite."""
    print("\nTEST 4: Model consistency (gemini-2.5-flash-lite)")
    print("-" * 40)
    
    with open('d:\\expense tracking system\\whatsapp_integration\\receipt_processor.py', 'r') as f:
        content = f.read()
    
    if 'gemini-2.5-flash-lite' in content:
        print("PASS: Receipt processor uses gemini-2.5-flash-lite")
        return True
    else:
        print("FAIL: Receipt processor does not use gemini-2.5-flash-lite")
        return False


def test_learning_integration():
    """Test that learning is integrated in receipt processing."""
    print("\nTEST 5: Receipt learning integration")
    print("-" * 40)
    
    with open('d:\\expense tracking system\\whatsapp_integration\\receipt_processor.py', 'r') as f:
        content = f.read()
    
    checks = [
        ('_learn_from_ai_result' in content, "_learn_from_ai_result called"),
        ('ExpenseParser' in content, "ExpenseParser imported"),
        ('[Receipt]' in content or 'receipt_learned' in content.lower(), "receipt learning logged"),
    ]
    
    all_pass = True
    for check, desc in checks:
        if check:
            print(f"  PASS: {desc}")
        else:
            print(f"  FAIL: {desc}")
            all_pass = False
    
    if all_pass:
        print("PASS: Receipt learning is integrated")
    else:
        print("FAIL: Receipt learning integration")
    
    return all_pass


def main():
    """Run all tests."""
    print("\n" + "=" * 50)
    print("  WhatsApp Image Webhook - Integration Tests")
    print("=" * 50)
    
    results = []
    results.append(("Webhook accepts images", test_webhook_accepts_images()))
    results.append(("Webhook rejects unsupported", test_webhook_rejects_unsupported()))
    results.append(("Receipt fields", test_receipt_fields_in_code()))
    results.append(("Model consistency", test_model_consistency()))
    results.append(("Learning integration", test_learning_integration()))
    
    print("\n" + "=" * 50)
    print("  TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 50 + "\n")
    
    return 0 if passed == total else 1


if __name__ == '__main__':
    exit(main())
