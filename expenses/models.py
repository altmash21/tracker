from django.db import models
from django.conf import settings
from django.utils import timezone


class Category(models.Model):
    """Expense categories for organizing spending"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=50)
    icon = models.CharField(max_length=10, blank=True, default='💰')
    color = models.CharField(max_length=7, default='#4CAF50')  # Hex color code
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        unique_together = ('user', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.icon} {self.name}"


class Expense(models.Model):
    """Individual expense entries"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='expenses')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='expenses')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    date = models.DateField(default=timezone.now)
    
    # Track source of expense entry
    SOURCE_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('web', 'Web Dashboard'),
        ('api', 'API'),
    ]
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='whatsapp')
    
    # Soft delete support
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'expenses'
        verbose_name = 'Expense'
        verbose_name_plural = 'Expenses'
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['is_deleted']),
        ]

    def __str__(self):
        return f"{self.user.currency_symbol}{self.amount} - {self.category.name} ({self.date})"

    def delete(self, using=None, keep_parents=False):
        """Soft delete implementation"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def hard_delete(self):
        """Permanent deletion"""
        super().delete()

