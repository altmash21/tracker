from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import OTPVerification, User, WhatsAppMapping


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'whatsapp_number', 'account_type', 'whatsapp_verified', 'is_staff', 'created_at')
    list_filter = ('account_type', 'whatsapp_verified', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'whatsapp_number', 'phone_number')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('WhatsApp Info', {'fields': ('whatsapp_number', 'whatsapp_verified', 'phone_number', 'account_type')}),
        ('Currency', {'fields': ('currency', 'currency_symbol')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'otp', 'otp_created_at')


@admin.register(WhatsAppMapping)
class WhatsAppMappingAdmin(admin.ModelAdmin):
    list_display = ('whatsapp_number', 'user', 'is_active', 'is_verified', 'last_interaction', 'created_at')
    list_filter = ('is_active', 'is_verified', 'created_at')
    search_fields = ('whatsapp_number', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'last_interaction')


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'purpose', 'otp', 'is_used', 'expires_at', 'created_at')
    list_filter = ('purpose', 'is_used', 'created_at')
    search_fields = ('user__username', 'user__whatsapp_number', 'otp')
    readonly_fields = ('created_at',)

