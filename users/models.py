from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """Extended User model with additional fields"""
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    whatsapp_number = models.CharField(max_length=15, blank=True, null=True, unique=True)
    whatsapp_verified = models.BooleanField(default=False)
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)
    currency = models.CharField(max_length=3, default='INR')
    currency_symbol = models.CharField(max_length=5, default='₹')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username

    def generate_otp(self):
        """Generate a 6-digit OTP for WhatsApp verification"""
        import random
        self.otp = str(random.randint(100000, 999999))
        self.otp_created_at = timezone.now()
        self.save()
        return self.otp

    def verify_otp(self, otp):
        """Verify OTP within 10 minutes"""
        if not self.otp or not self.otp_created_at:
            return False
        
        time_diff = timezone.now() - self.otp_created_at
        if time_diff.total_seconds() > 600:  # 10 minutes
            return False
        
        if self.otp == otp:
            self.whatsapp_verified = True
            self.otp = None
            self.otp_created_at = None
            self.save()
            return True
        return False


class WhatsAppMapping(models.Model):
    """Map WhatsApp number to user for incoming messages"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='whatsapp_mapping')
    whatsapp_number = models.CharField(max_length=15, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    last_interaction = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'whatsapp_mappings'
        verbose_name = 'WhatsApp Mapping'
        verbose_name_plural = 'WhatsApp Mappings'

    def __str__(self):
        return f"{self.whatsapp_number} -> {self.user.username}"

