from django.contrib import admin
from .models import Budget, Category, Expense, Receipt


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'user', 'is_default', 'is_active', 'created_at')
    list_filter = ('is_default', 'is_active', 'created_at')
    search_fields = ('name', 'user__username')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'category', 'date', 'source', 'is_deleted', 'created_at')
    list_filter = ('source', 'is_deleted', 'date', 'category')
    search_fields = ('user__username', 'description', 'category__name')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'date'
    
    def get_queryset(self, request):
        # Show all expenses including soft-deleted ones in admin
        return super().get_queryset(request)


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'processing_status', 'created_at')
    list_filter = ('processing_status', 'created_at')
    search_fields = ('user__username', 'extracted_text')
    readonly_fields = ('created_at',)


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'monthly_limit', 'is_active', 'updated_at')
    list_filter = ('is_active', 'category')
    search_fields = ('user__username', 'category__name')
    readonly_fields = ('created_at', 'updated_at')

