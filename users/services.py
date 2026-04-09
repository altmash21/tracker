import logging
import random
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from expenses.models import Category

from .models import OTPVerification, User, WhatsAppMapping


logger = logging.getLogger(__name__)


def normalize_whatsapp_number(phone_number):
    """Keep only digits and trim leading zeros for mapping consistency."""
    if not phone_number:
        return ''
    digits = ''.join(ch for ch in str(phone_number) if ch.isdigit())
    return digits.lstrip('0')


def _create_default_categories_for_user(user):
    if Category.objects.filter(user=user).exists():
        return

    default_categories = [
        ('Food', '🍔', '#FF6B6B'),
        ('Travel', '🚗', '#4ECDC4'),
        ('Shopping', '🛍️', '#95E1D3'),
        ('Bills', '📄', '#F38181'),
        ('Entertainment', '🎬', '#AA96DA'),
        ('Health', '💊', '#FCBAD3'),
        ('Groceries', '🛒', '#A8D8EA'),
        ('Education', '📚', '#FFDEB4'),
    ]

    categories = [
        Category(
            user=user,
            name=name,
            icon=icon,
            color=color,
            is_default=True,
            is_active=True,
        )
        for name, icon, color in default_categories
    ]
    Category.objects.bulk_create(categories)


def get_or_create_whatsapp_user(phone_number):
    """Return existing mapped user, or silently auto-create one for first WhatsApp message."""
    normalized_number = normalize_whatsapp_number(phone_number)
    if not normalized_number:
        raise ValueError('Phone number is required to create WhatsApp user')

    mapping = (
        WhatsAppMapping.objects
        .select_related('user')
        .filter(whatsapp_number=normalized_number)
        .first()
    )
    if mapping:
        return mapping.user, False

    existing_user = User.objects.filter(whatsapp_number=normalized_number).first()
    if existing_user:
        mapping, created = WhatsAppMapping.objects.get_or_create(
            user=existing_user,
            defaults={
                'whatsapp_number': normalized_number,
                'is_active': True,
                'is_verified': True,
            },
        )
        if not mapping.is_verified or not mapping.is_active:
            mapping.is_verified = True
            mapping.is_active = True
            mapping.save(update_fields=['is_verified', 'is_active', 'last_interaction'])
        return existing_user, created

    username = f'wa_{normalized_number}'

    with transaction.atomic():
        user = User.objects.create(
            username=username,
            phone_number=normalized_number,
            whatsapp_number=normalized_number,
            whatsapp_verified=True,
            account_type=User.ACCOUNT_TYPE_WHATSAPP_CREATED,
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])

        WhatsAppMapping.objects.create(
            user=user,
            whatsapp_number=normalized_number,
            is_active=True,
            is_verified=True,
        )

        _create_default_categories_for_user(user)

    logger.info('Auto-created WhatsApp-first user for %s', normalized_number)
    return user, True


def generate_otp_for_user(user, purpose=OTPVerification.PURPOSE_LOGIN, validity_minutes=10):
    """Create a fresh OTP record and invalidate older pending OTPs for the same purpose."""
    otp = f'{random.randint(0, 999999):06d}'
    now = timezone.now()

    OTPVerification.objects.filter(
        user=user,
        purpose=purpose,
        is_used=False,
        expires_at__gt=now,
    ).update(is_used=True)

    return OTPVerification.objects.create(
        user=user,
        otp=otp,
        purpose=purpose,
        expires_at=now + timedelta(minutes=validity_minutes),
    )


def verify_otp_for_user(user, otp, purpose=OTPVerification.PURPOSE_LOGIN):
    """Validate OTP for user and purpose, consuming it on success."""
    if not otp:
        return False

    otp_record = (
        OTPVerification.objects
        .filter(
            user=user,
            otp=str(otp).strip(),
            purpose=purpose,
            is_used=False,
            expires_at__gt=timezone.now(),
        )
        .order_by('-created_at')
        .first()
    )
    if not otp_record:
        return False

    otp_record.is_used = True
    otp_record.save(update_fields=['is_used'])
    return True
