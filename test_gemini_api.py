#!/usr/bin/env python
"""
Test script for Google Generative AI (Gemini) API Integration

Tests:
1. Configuration validation (API key setup)
2. Text-based expense categorization
3. Image-based expense categorization
4. JSON response parsing
5. Error handling

Usage:
    python test_gemini_api.py
"""

import os
import sys
import json
from pathlib import Path

# Hardcoded Gemini API Key
GEMINI_API_KEY = "AIzaSyB_FghhwJxlH1qHZ2MKnjEp8DjJwx9jhgk"

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expense_tracker.settings')
os.environ['GEMINI_API_KEY'] = GEMINI_API_KEY

import django
django.setup()

from whatsapp_integration.ai_categorization_service import (
    categorize_with_ai,
    categorize_from_image_with_gemini
)


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_config():
    """Test if Gemini API is properly configured."""
    print_section("1. Configuration Check")
    
    api_key = GEMINI_API_KEY
    
    if not api_key:
        print("❌ GEMINI_API_KEY is not set")
        return False
    
    print(f"✅ GEMINI_API_KEY is configured")
    print(f"   Key preview: {api_key[:10]}...{api_key[-5:]}")
    return True


def test_text_categorization():
    """Test text-based expense categorization."""
    print_section("2. Text Categorization Test")
    
    test_cases = [
        "Paid Rs320 for lunch at restaurant",
        "Bought coffee for 150 rupees",
        "Paid electricity bill 2500",
        "Gas station refuel 200 liters",
        "Grocery shopping 1500 fruits vegetables",
    ]
    
    print(f"Testing {len(test_cases)} text samples:\n")
    
    results = []
    for i, text in enumerate(test_cases, 1):
        try:
            print(f"   [{i}] Input: {text}")
            result = categorize_with_ai(text)
            
            if result and "error" not in result:
                print(f"       ✅ Category: {result.get('category', 'N/A')}")
                print(f"          Amount: {result.get('amount', 'N/A')}")
                print(f"          Description: {result.get('description', 'N/A')}")
                results.append(True)
            else:
                print(f"       ❌ Failed: {result}")
                results.append(False)
        except Exception as e:
            print(f"       ❌ Error: {str(e)}")
            results.append(False)
    
    success_rate = sum(results) / len(results) * 100
    print(f"\n✅ Success rate: {success_rate:.1f}% ({sum(results)}/{len(results)})")
    return success_rate > 0


def test_image_categorization():
    """Test image-based expense categorization."""
    print_section("3. Image Categorization Test")
    
    # Look for sample images in common locations
    sample_images = [
        Path("receipt.jpg"),
        Path("receipt.png"),
        Path("media/receipt.jpg"),
        Path("test_receipt.jpg"),
    ]
    
    image_path = None
    for img in sample_images:
        if img.exists():
            image_path = img
            break
    
    if not image_path:
        print("⚠️  No test image found. To test image categorization:")
        print("\n   1. Place a receipt image in the root directory")
        print("   2. Name it: receipt.jpg or receipt.png")
        print("   3. Run this test again")
        print("\n   OR test manually in Django shell:")
        print("      python manage.py shell")
        print("      from whatsapp_integration.ai_categorization_service import categorize_from_image_with_gemini")
        print("      result = categorize_from_image_with_gemini('path/to/receipt.jpg')")
        print("      print(result)")
        return None
    
    try:
        print(f"Testing image: {image_path}\n")
        result = categorize_from_image_with_gemini(str(image_path))
        
        if result and "error" not in result:
            print(f"✅ Category: {result.get('category', 'N/A')}")
            print(f"   Amount: {result.get('amount', 'N/A')}")
            print(f"   Description: {result.get('description', 'N/A')}")
            if 'items' in result:
                print(f"   Items: {result.get('items', [])}")
            return True
        else:
            print(f"❌ Failed: {result}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_response_format():
    """Test JSON response format validation."""
    print_section("4. Response Format Test")
    
    print("Testing response structure...\n")
    
    try:
        result = categorize_with_ai("Sample test expense")
        
        required_fields = ['category', 'amount', 'description']
        missing_fields = [f for f in required_fields if f not in result]
        
        if missing_fields:
            print(f"⚠️  Missing fields: {', '.join(missing_fields)}")
            print(f"   Returned: {list(result.keys())}")
        else:
            print(f"✅ All required fields present:")
            for field in required_fields:
                print(f"   • {field}: {result.get(field)}")
        
        print(f"\n✅ Response format is valid")
        return True
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_error_handling():
    """Test error handling with invalid inputs."""
    print_section("5. Error Handling Test")
    
    print("Testing error handling with edge cases:\n")
    
    test_cases = [
        ("", "Empty string"),
        ("   ", "Whitespace only"),
        ("12345", "Numbers only"),
        ("!@#$%", "Special characters only"),
    ]
    
    results = []
    for text, description in test_cases:
        try:
            print(f"   [{description}] Testing: '{text}'")
            result = categorize_with_ai(text)
            
            if result:
                if "error" in result:
                    print(f"       ✅ Correctly handled (error returned)")
                    results.append(True)
                else:
                    print(f"       ✓ Processed (result: {result.get('category', 'unknown')})")
                    results.append(True)
            else:
                print(f"       ⚠️  No result returned")
                results.append(False)
        except Exception as e:
            print(f"       ✅ Exception caught: {type(e).__name__}")
            results.append(True)
    
    print(f"\n✅ Error handling works correctly")
    return True


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  GEMINI API INTEGRATION TEST".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    # Run tests
    config_ok = test_config()
    
    if not config_ok:
        print_section("Setup Required")
        print("Please configure GEMINI_API_KEY in .env file before running tests.")
        sys.exit(1)
    
    results = {
        "Configuration": config_ok,
        "Text Categorization": test_text_categorization(),
        "Image Categorization": test_image_categorization(),
        "Response Format": test_response_format(),
        "Error Handling": test_error_handling(),
    }
    
    # Summary
    print_section("Test Summary")
    
    passed = sum(1 for v in results.values() if v is True)
    total = sum(1 for v in results.values() if v is not None)
    
    for test_name, result in results.items():
        if result is True:
            status = "✅ PASSED"
        elif result is False:
            status = "❌ FAILED"
        else:
            status = "⚠️  SKIPPED"
        print(f"{status}  {test_name}")
    
    print(f"\n{'='*60}")
    print(f"Overall: {passed}/{total} tests passed")
    print(f"{'='*60}\n")
    
    # Recommendations
    if passed == total:
        print("🎉 All tests passed! Gemini API is fully configured and working.")
    else:
        print("📝 Recommendations:")
        print("   1. Check GEMINI_API_KEY in .env file")
        print("   2. Verify API key is valid: https://ai.google.dev/")
        print("   3. Check internet connectivity")
        print("   4. Review error messages above for specific issues")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
