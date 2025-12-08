from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, WhatsAppMapping


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'whatsapp_number', 'whatsapp_verified', 'is_staff', 'created_at')
    list_filter = ('whatsapp_verified', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'whatsapp_number', 'phone_number')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('WhatsApp Info', {'fields': ('whatsapp_number', 'whatsapp_verified', 'phone_number')}),
        ('Currency', {'fields': ('currency', 'currency_symbol')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'otp', 'otp_created_at')


@admin.register(WhatsAppMapping)
class WhatsAppMappingAdmin(admin.ModelAdmin):
    list_display = ('whatsapp_number', 'user', 'is_active', 'last_interaction', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('whatsapp_number', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'last_interaction')

