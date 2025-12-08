from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from expenses.models import Category

User = get_user_model()


class Command(BaseCommand):
    help = 'Create default categories for all users who don\'t have any'

    def handle(self, *args, **options):
        default_categories = [
            ('Food', '🍔', '#FF6B6B'),
            ('Travel', '🚗', '#4ECDC4'),
            ('Shopping', '🛍️', '#95E1D3'),
            ('Bills', '📄', '#F38181'),
            ('Entertainment', '🎬', '#AA96DA'),
            ('Health', '💊', '#FCBAD3'),
            ('Groceries', '🛒', '#A8D8EA'),
            ('Education', '📚', '#FFDEB4'),
            ('Utilities', '⚡', '#FFD93D'),
            ('Transportation', '🚌', '#6BCB77'),
        ]
        
        users = User.objects.all()
        
        for user in users:
            # Check if user has categories
            existing_count = Category.objects.filter(user=user).count()
            
            if existing_count == 0:
                # Create default categories
                for name, icon, color in default_categories:
                    Category.objects.create(
                        user=user,
                        name=name,
                        icon=icon,
                        color=color,
                        is_default=True
                    )
                
                self.stdout.write(
                    self.style.SUCCESS(f'Created {len(default_categories)} categories for user: {user.username}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'User {user.username} already has {existing_count} categories')
                )
        
        self.stdout.write(self.style.SUCCESS('Done!'))
