import re
import json
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from expenses.models import Category, CategoryKeyword, Expense
from users.models import OTPVerification
from users.services import generate_otp_for_user

logger = logging.getLogger(__name__)


def parse_receipt_image(image_path: str, user):
    from .receipt_processor import parse_receipt_image as _parse_receipt_image

    return _parse_receipt_image(image_path, user)


def process_receipt_image(image_path: str, user):
    from .receipt_processor import process_receipt as _process_receipt

    return _process_receipt(image_path, user)


class ExpenseParser:
    """
    Parse natural language expense messages from WhatsApp using a 3-tier
    cascading category resolution system:
    
    Tier 1: Exact Match - Direct category name match (case-insensitive)
    Tier 2: Keyword Map - Match against category keywords database
    Tier 3: Gemini Fallback - Use Gemini 2.5 Flash-Lite to categorize,
                              then auto-save the keyword
    """
    
    def __init__(self, user):
        self.user = user
        self.currency_symbol = user.currency_symbol
        self.gemini_key = settings.GEMINI_API_KEY if hasattr(settings, 'GEMINI_API_KEY') else None
    
    def parse(self, message):
        """
        Parse expense message in format: <amount> <category> [description]
        Examples:
            - "120 petrol"
            - "450 groceries bought vegetables"
            - "200 food dinner at restaurant"
        
        Returns dict with keys: amount, category, description, date
        Or error dict with keys: error, message
        """
        message = message.strip()

        multi_results = self._preprocess_multi_expense(message)
        if multi_results:
            normalized_results = []
            for item in multi_results:
                category_name = item.get('category_name', '')
                category = Category.objects.filter(
                    user=self.user,
                    name__iexact=category_name,
                    is_active=True
                ).first()

                if not category and category_name.lower() == 'fuel':
                    for fallback_name in ('Fuel', 'Transport', 'Travel'):
                        category = Category.objects.filter(
                            user=self.user,
                            name__iexact=fallback_name,
                            is_active=True
                        ).first()
                        if category:
                            break

                if not category:
                    category = Category.objects.filter(
                        user=self.user,
                        name__iexact='Other',
                        is_active=True
                    ).first()

                if not category:
                    continue

                normalized_results.append(
                    {
                        'amount': item['amount'],
                        'category': category,
                        'description': item['description'],
                        'date': timezone.now().date(),
                    }
                )

            if normalized_results:
                return normalized_results
        
        # Pattern: number followed by category name
        pattern = r'^(\d+(?:\.\d{1,2})?)\s+(\w+)(?:\s+(.+))?$'
        match = re.match(pattern, message, re.IGNORECASE)
        
        if not match:
            return self._parse_natural_language(message)
        
        amount_str, category_word, description = match.groups()
        amount = Decimal(amount_str)
        description = description or ""
        
        # ===== TIER 1: EXACT MATCH =====
        category = self._tier1_exact_match(category_word)
        if category:
            logger.info(f"[Tier 1] Exact Match hit for '{category_word}' -> {category.name}")
            return {
                'amount': amount,
                'category': category,
                'description': description.strip(),
                'date': timezone.now().date()
            }
        
        # ===== TIER 2: KEYWORD MAP =====
        category = self._tier2_keyword_match(category_word)
        if category:
            logger.info(f"[Tier 2] Keyword Match hit for '{category_word}' -> {category.name}")
            return {
                'amount': amount,
                'category': category,
                'description': description.strip(),
                'date': timezone.now().date()
            }
        
        # ===== TIER 3: GEMINI FALLBACK =====
        if self.gemini_key:
            result = self._tier3_gemini_fallback(amount_str, category_word, description)
            if result.get('category'):
                logger.info(f"[Tier 3] Gemini hit for '{category_word}' -> {result['category'].name}")
                return result
            elif result.get('error'):
                # Gemini failed, return error
                return result
        
        # ===== ALL TIERS FAILED =====
        return {
            'error': 'category_not_found',
            'message': f"Category '{category_word}' not found. Available categories: {self._get_category_list()}"
        }

    def _preprocess_multi_expense(self, message: str):
        if not message:
            return None

        filler_words = {'ka', 'ke', 'ki', 'for', 'and', 'with', 'on', 'at', 'to'}
        keywords = {
            'Food': ['food', 'burger', 'pizza', 'chicken', 'zomato', 'swiggy'],
            'Fuel': ['petrol', 'fuel', 'diesel'],
            'Travel': ['uber', 'auto', 'taxi', 'bus', 'train'],
            'Shopping': ['amazon', 'flipkart', 'shopping', 'clothes'],
        }

        keyword_to_category = {}
        for category_name, category_keywords in keywords.items():
            for keyword in category_keywords:
                keyword_to_category[keyword] = category_name

        normalized_message = message.lower()
        punctuation_map = str.maketrans({
            ',': ' ',
            '&': ' ',
            ';': ' ',
            ':': ' ',
            '/': ' ',
            '|': ' ',
        })
        normalized_message = normalized_message.translate(punctuation_map)

        tokens = [
            token.strip()
            for token in normalized_message.split()
            if token.strip() and token.strip() not in filler_words
        ]

        if not tokens:
            return None

        def is_number_token(token: str) -> bool:
            if token.count('.') > 1:
                return False
            numeric = token.replace('.', '', 1)
            return numeric.isdigit()

        important_tokens = [
            token for token in tokens
            if is_number_token(token) or token in keyword_to_category
        ]

        if not important_tokens:
            return None

        results = []
        i = 0
        while i < len(important_tokens):
            token = important_tokens[i]
            if not is_number_token(token):
                i += 1
                continue

            try:
                amount = Decimal(token)
            except Exception:
                i += 1
                continue

            if amount <= 0:
                i += 1
                continue

            category_name = None
            description = None
            j = i + 1
            while j < len(important_tokens):
                candidate = important_tokens[j]
                if candidate in keyword_to_category:
                    category_name = keyword_to_category[candidate]
                    description = candidate
                    break
                if is_number_token(candidate):
                    break
                j += 1

            if category_name:
                results.append(
                    {
                        'amount': amount,
                        'category_name': category_name,
                        'description': description or category_name.lower(),
                    }
                )
                i = j + 1
            else:
                i += 1

        return results or None

    def _safe_json_parse(self, text: str) -> dict:
        payload = (text or '').strip()
        if not payload:
            return None

        if payload.startswith('```'):
            lines = payload.splitlines()
            if lines and lines[0].strip().startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith('```'):
                lines = lines[:-1]
            payload = '\n'.join(lines).strip()
            if payload.lower().startswith('json'):
                payload = payload[4:].strip()

        try:
            return json.loads(payload)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        match = re.search(r'\{[\s\S]*\}', payload)
        if not match:
            return None

        try:
            return json.loads(match.group(0))
        except (json.JSONDecodeError, TypeError, ValueError):
            return None

    def _parse_natural_language(self, message: str):
        if not self.gemini_key:
            return {
                'error': 'parse_failed',
                'message': 'Could not parse expense message. Please use format: 120 petrol'
            }

        try:
            from google import genai
        except ImportError:
            logger.warning('google-genai not installed, skipping natural language parsing')
            return {
                'error': 'parse_failed',
                'message': 'Could not parse expense message. Please use format: 120 petrol'
            }

        prompt = f"""Extract expense details from this message:

\"{message}\"

Return ONLY valid JSON:
{{
"amount": number,
"category": "string",
"description": "string"
}}

Rules:

* Extract amount from sentence
* Infer category (Food, Travel, Groceries, etc.)
* Description should be short (e.g. "burger", "zomato dinner")
* If unsure:
  {{
  "amount": 0,
  "category": "Other",
  "description": "Unable to parse"
  }}
"""

        retry_prompt = """Extract ONLY the essential expense details.

Return STRICT JSON:
{
"amount": number,
"category": "string",
"description": "string"
}

Rules:

* Focus only on amount and category
* Ignore extra text
* Category must be simple (Food, Travel, Groceries, etc.)
* If unsure:
  {
  "amount": 0,
  "category": "Other",
  "description": "Unable to parse"
  }
"""

        prompts = [prompt, retry_prompt]

        for attempt, prompt_text in enumerate(prompts, start=1):
            try:
                client = genai.Client(api_key=self.gemini_key)
                response = client.models.generate_content(
                    model='gemini-2.5-flash-lite',
                    contents=prompt_text,
                    config={'temperature': 0.2},
                )
            except Exception as e:
                logger.warning('Natural language Gemini API error (attempt %d): %s', attempt, e)
                if attempt < len(prompts):
                    continue
                return {
                    'error': 'parse_failed',
                    'message': 'Could not parse expense message. Please use format: 120 petrol'
                }

            response_text = (response.text or '').strip()
            parsed = self._safe_json_parse(response_text)
            if parsed is None:
                logger.warning('Natural language Gemini JSON parse failed (attempt %d)', attempt)
                if attempt < len(prompts):
                    continue
                return {
                    'error': 'parse_failed',
                    'message': 'Could not parse expense message. Please use format: 120 petrol'
                }

            amount = parsed.get('amount', 0)
            description = str(parsed.get('description', '')).strip() or message[:120]
            category_name = str(parsed.get('category', 'Other')).strip() or 'Other'

            try:
                amount = Decimal(str(amount))
            except (ValueError, TypeError):
                amount = Decimal('0')

            if amount <= 0:
                return {
                    'error': 'parse_failed',
                    'message': 'Could not parse expense message. Please use format: 120 petrol'
                }

            category = Category.objects.filter(
                user=self.user,
                name__iexact=category_name,
                is_active=True,
            ).first()

            if not category:
                category = Category.objects.filter(
                    user=self.user,
                    name__iexact='Other',
                    is_active=True,
                ).first()

            if not category:
                return {
                    'error': 'category_not_found',
                    'message': f"Category not found. Available categories: {self._get_category_list()}"
                }

            return {
                'amount': amount,
                'category': category,
                'description': description,
                'date': timezone.now().date(),
            }

        return {
            'error': 'parse_failed',
            'message': 'Could not parse expense message. Please use format: 120 petrol'
        }
    
    def _tier1_exact_match(self, category_word):
        """Tier 1: Check if the word exactly matches any category name (case-insensitive)"""
        return Category.objects.filter(
            user=self.user,
            name__iexact=category_word,
            is_active=True
        ).first()
    
    def _tier2_keyword_match(self, category_word):
        """Tier 2: Check if the word exists in the keyword map for this user's categories"""
        keyword_entry = CategoryKeyword.objects.select_related('category').filter(
            category__user=self.user,
            category__is_active=True,
            keyword__iexact=category_word
        ).first()
        
        if keyword_entry:
            return keyword_entry.category
        
        return None
    
    def _tier3_gemini_fallback(self, amount_str, category_word, description):
        """
        Tier 3: Use Gemini 2.5 Flash-Lite to categorize the expense.
        On success, AUTO-SAVE the keyword to prevent future Gemini calls.
        """
        try:
            from google import genai
        except ImportError:
            logger.warning("google-genai not installed, skipping Gemini fallback")
            return self._get_fallback_error()
        
        try:
            # Get user's active categories for context
            user_categories = list(
                Category.objects.filter(user=self.user, is_active=True)
                .values_list('name', flat=True)
            )
            
            if not user_categories:
                logger.warning(f"User {self.user.username} has no active categories")
                return self._get_fallback_error()
            
            # Build Gemini prompt
            categories_str = ', '.join(user_categories)
            full_text = f"{amount_str} {category_word}" + (f" {description}" if description else "")
            
            prompt = f"""You are an expense categorization assistant. Parse the following expense text and return JSON.

User's available categories: {categories_str}

Expense text: "{full_text}"

Return only valid JSON (no markdown, no code blocks) with these exact fields:
{{
    "amount": <number>,
    "category": "<exact category from the list above>",
    "description": "<short description>"
}}

If you cannot categorize or the category is not in the list, return:
{{
    "amount": 0,
    "category": "Other",
    "description": "Unable to categorize"
}}"""

            retry_prompt = """Extract ONLY the essential expense details.

Return STRICT JSON:
{
"amount": number,
"category": "string",
"description": "string"
}

Rules:

* Focus only on amount and category
* Ignore extra text
* Category must be simple (Food, Travel, Groceries, etc.)
* If unsure:
  {
  "amount": 0,
  "category": "Other",
  "description": "Unable to parse"
  }
"""

            prompts = [prompt, retry_prompt]
            
            # Call Gemini 2.5 Flash-Lite (fastest model)
            client = genai.Client(api_key=self.gemini_key)
            parsed = None
            api_error = None
            for attempt, prompt_text in enumerate(prompts, start=1):
                try:
                    response = client.models.generate_content(
                        model="gemini-2.5-flash-lite",
                        contents=prompt_text,
                        config={"temperature": 0.3}
                    )
                except Exception as e:
                    api_error = e
                    logger.warning('Tier 3 Gemini API error (attempt %d): %s', attempt, e)
                    if attempt < len(prompts):
                        continue
                    break

                parsed = self._safe_json_parse((response.text or '').strip())
                if parsed is None:
                    logger.warning('Tier 3 Gemini JSON parse failed (attempt %d)', attempt)
                    if attempt < len(prompts):
                        continue
                    break

                api_error = None
                break

            if parsed is None:
                if api_error:
                    error_str = str(api_error).lower()
                    if '429' in str(api_error) or 'resource_exhausted' in error_str or 'quota' in error_str:
                        logger.warning(f"Gemini quota exhausted: {api_error}")
                        return {
                            'error': 'gemini_quota_exceeded',
                            'message': f"AI is temporarily unavailable. Please try later or use one of these categories: {self._get_category_list()}"
                        }

                    logger.error(f"Gemini API error: {api_error}", exc_info=True)
                    return {
                        'error': 'gemini_error',
                        'message': f"Unable to categorize. Available categories: {self._get_category_list()}"
                    }

                return self._get_fallback_error()
            
            # Validate response structure
            if not all(k in parsed for k in ['amount', 'category', 'description']):
                logger.warning(f"Invalid Gemini response structure: {parsed}")
                return self._get_fallback_error()
            
            # Find the category in user's categories
            category = Category.objects.filter(
                user=self.user,
                name__iexact=parsed['category'],
                is_active=True
            ).first()
            
            if not category:
                # Category not found in user's list, return error
                logger.warning(f"Gemini returned unknown category: {parsed['category']}")
                return self._get_fallback_error()
            
            # SUCCESS! Auto-save the keyword for future use
            try:
                CategoryKeyword.objects.get_or_create(
                    category=category,
                    keyword=category_word.lower(),
                    defaults={'added_by': 'system'}
                )
                logger.info(f"[AutoSave] Saved keyword '{category_word}' -> {category.name}")
            except Exception as e:
                logger.warning(f"Failed to auto-save keyword: {e}")
            
            return {
                'amount': Decimal(str(parsed['amount'])),
                'category': category,
                'description': str(parsed['description']).strip(),
                'date': timezone.now().date()
            }
        
        except Exception as e:
            # Handle API errors (429, RESOURCE_EXHAUSTED, etc.)
            error_str = str(e).lower()
            
            if '429' in str(e) or 'resource_exhausted' in error_str or 'quota' in error_str:
                logger.warning(f"Gemini quota exhausted: {e}")
                return {
                    'error': 'gemini_quota_exceeded',
                    'message': f"AI is temporarily unavailable. Please try later or use one of these categories: {self._get_category_list()}"
                }
            
            logger.error(f"Gemini API error: {e}", exc_info=True)
            return {
                'error': 'gemini_error',
                'message': f"Unable to categorize. Available categories: {self._get_category_list()}"
            }
    
    def _get_fallback_error(self):
        """Return a user-friendly error when all tiers fail"""
        return {
            'error': 'categorization_failed',
            'message': f"Unable to categorize. Available categories: {self._get_category_list()}"
        }
    
    def _get_category_list(self):
        """Get formatted list of available categories"""
        categories = Category.objects.filter(user=self.user, is_active=True)
        return ', '.join([f"{cat.icon} {cat.name}" for cat in categories])



class StatementGenerator:
    """Generate expense statements and summaries"""
    
    def __init__(self, user):
        self.user = user
        self.currency_symbol = user.currency_symbol
    
    def generate_today(self):
        """Generate today's expense statement"""
        today = timezone.now().date()
        expenses = Expense.objects.filter(
            user=self.user,
            date=today,
            is_deleted=False
        ).select_related('category')
        
        return self._format_expenses(expenses, f"📊 Today's Expenses ({today.strftime('%d %b %Y')})")
    
    def generate_week(self):
        """Generate this week's expense statement"""
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        
        expenses = Expense.objects.filter(
            user=self.user,
            date__gte=week_start,
            date__lte=today,
            is_deleted=False
        ).select_related('category')
        
        return self._format_expenses(expenses, f"📊 This Week's Expenses ({week_start.strftime('%d %b')} - {today.strftime('%d %b')})")
    
    def generate_month(self):
        """Generate this month's expense statement"""
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        expenses = Expense.objects.filter(
            user=self.user,
            date__gte=month_start,
            date__lte=today,
            is_deleted=False
        ).select_related('category')
        
        return self._format_expenses(expenses, f"📊 This Month's Expenses ({month_start.strftime('%B %Y')})")
    
    def generate_category(self, category_name):
        """Generate expenses for a specific category"""
        category = Category.objects.filter(
            user=self.user,
            name__iexact=category_name,
            is_active=True
        ).first()
        
        if not category:
            return f"❌ Category '{category_name}' not found."
        
        # Get last 30 days for this category
        today = timezone.now().date()
        start_date = today - timedelta(days=30)
        
        expenses = Expense.objects.filter(
            user=self.user,
            category=category,
            date__gte=start_date,
            is_deleted=False
        ).select_related('category')
        
        return self._format_expenses(expenses, f"📊 {category.icon} {category.name} - Last 30 Days")
    
    def generate_summary(self):
        """Generate overall expense summary"""
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # Monthly expenses by category
        expenses = Expense.objects.filter(
            user=self.user,
            date__gte=month_start,
            is_deleted=False
        ).select_related('category')
        
        # Group by category
        from django.db.models import Sum
        category_totals = expenses.values('category__name', 'category__icon').annotate(
            total=Sum('amount')
        ).order_by('-total')
        
        if not category_totals:
            return f"📊 Monthly Summary ({month_start.strftime('%B %Y')})\n\nNo expenses recorded yet."
        
        message = f"📊 Monthly Summary ({month_start.strftime('%B %Y')})\n\n"
        
        total = 0
        for item in category_totals:
            amount = float(item['total'])
            total += amount
            message += f"{item['category__icon']} {item['category__name']}: {self.currency_symbol}{amount:.2f}\n"
        
        message += f"\n{'='*25}\n"
        message += f"💰 Total: {self.currency_symbol}{total:.2f}"
        
        return message

    def _format_expenses(self, expenses, title):
        """Format expenses into a readable message"""
        if not expenses:
            return f"{title}\n\nNo expenses recorded."

        # Group by category
        category_totals = {}
        for expense in expenses:
            cat_name = expense.category.name
            cat_icon = expense.category.icon
            key = f"{cat_icon} {cat_name}"

            if key not in category_totals:
                category_totals[key] = 0
            category_totals[key] += float(expense.amount)

        message = f"{title}\n\n"

        total = 0
        for cat, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
            message += f"{cat}: {self.currency_symbol}{amount:.2f}\n"
            total += amount

        message += f"\n{'='*25}\n"
        message += f"💰 Total: {self.currency_symbol}{total:.2f}"

        return message


def handle_login_command(user):
    """Generate login OTP and return WhatsApp message for dashboard sign-in."""
    otp_record = generate_otp_for_user(user, purpose=OTPVerification.PURPOSE_LOGIN)
    login_url = getattr(settings, 'XPENSEDIARY_LOGIN_URL', 'https://xpensediary.com/login/')

    return (
        f"🔗 Your dashboard login OTP: *{otp_record.otp}*\n"
        f"Visit: {login_url}\n"
        "Enter your number + this OTP to login.\n"
        "Valid 10 minutes.\n"
        "— *TechSpark*"
    )
