"""
Management command to seed default category keywords.

Usage:
    python manage.py seed_category_keywords
"""
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from expenses.models import Category, CategoryKeyword


class Command(BaseCommand):
    help = 'Seed default category keywords for intelligent categorization'

    # Default keyword mappings for common categories
    DEFAULT_KEYWORDS = {
        'Travel': [
            'petrol', 'fuel', 'gas', 'uber', 'ola', 'auto', 'bus', 'train',
            'taxi', 'diesel', 'cng', 'metro', 'toll', 'parking', 'flight',
            'transport', 'bike', 'car', 'ride'
        ],
        'Food': [
            'lunch', 'dinner', 'breakfast', 'snack', 'meal', 'restaurant',
            'cafe', 'hotel', 'zomato', 'swiggy', 'eating', 'food', 'eat'
        ],
        'Groceries': [
            'grocery', 'vegetables', 'fruits', 'sabzi', 'kirana', 'market',
            'dmart', 'bigbasket', 'milk', 'eggs', 'bread', 'shopping',
            'supermarket', 'bakery'
        ],
        'Health': [
            'doctor', 'medicine', 'hospital', 'pharmacy', 'clinic', 'chemist',
            'medical', 'tablet', 'injection', 'health', 'doctor', 'wellness'
        ],
        'Bills': [
            'electricity', 'water', 'internet', 'mobile', 'recharge',
            'broadband', 'wifi', 'gas bill', 'ott', 'subscription', 'bill',
            'utilities'
        ],
        'Entertainment': [
            'movie', 'cinema', 'netflix', 'spotify', 'game', 'fun', 'theatre',
            'concert', 'amazon prime', 'entertainment', 'music', 'streaming'
        ],
        'Education': [
            'books', 'notebook', 'fees', 'tuition', 'course', 'coaching',
            'stationery', 'pen', 'school', 'college', 'exam', 'education',
            'learning'
        ],
        'Shopping': [
            'clothes', 'clothing', 'shoes', 'amazon', 'flipkart', 'mall',
            'dress', 'jeans', 'shirt', 'shopping', 'retail', 'apparel'
        ]
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Seed keywords only for a specific user ID',
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')

        if user_id:
            self._seed_for_user(user_id)
        else:
            self._seed_all_default_categories()

    def _seed_all_default_categories(self):
        """Seed keywords for default categories across all users"""
        self.stdout.write("🌱 Seeding default category keywords for all users...")

        total_keywords_added = 0

        for category_name, keywords in self.DEFAULT_KEYWORDS.items():
            # Find all active categories with this name across all users
            categories = Category.objects.filter(
                name__iexact=category_name,
                is_active=True
            )

            if not categories.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  No categories found with name '{category_name}'"
                    )
                )
                continue

            for category in categories:
                added_count = self._add_keywords_for_category(category, keywords)
                total_keywords_added += added_count
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ {category.user.username} / {category.name}: +{added_count} keywords"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Seeding complete! Added {total_keywords_added} keywords total."
            )
        )

    def _seed_for_user(self, user_id):
        """Seed keywords only for a specific user"""
        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ User with id {user_id} not found"))
            return

        self.stdout.write(f"🌱 Seeding keywords for user: {user.username}")

        total_keywords_added = 0

        for category_name, keywords in self.DEFAULT_KEYWORDS.items():
            category = Category.objects.filter(
                user=user,
                name__iexact=category_name,
                is_active=True
            ).first()

            if not category:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  User '{user.username}' has no category '{category_name}'"
                    )
                )
                continue

            added_count = self._add_keywords_for_category(category, keywords)
            total_keywords_added += added_count
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ {category.name}: +{added_count} keywords"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Seeding complete! Added {total_keywords_added} keywords for {user.username}."
            )
        )

    def _add_keywords_for_category(self, category, keywords):
        """Add keywords to a specific category, skipping duplicates"""
        added_count = 0

        for keyword in keywords:
            try:
                obj, created = CategoryKeyword.objects.get_or_create(
                    category=category,
                    keyword=keyword.lower(),
                    defaults={'added_by': 'system'}
                )
                if created:
                    added_count += 1
            except IntegrityError:
                # Already exists, skip silently
                pass

        return added_count
