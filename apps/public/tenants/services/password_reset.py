"""
Servicio de password reset para tenants privados (API-First).

[WARNING] v2.30: API-First - Envía emails con URLs que apuntan a endpoints REST.
Usa tokens Django estándar (PasswordResetTokenGenerator) con uidb64.
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string

User = get_user_model()
logger = logging.getLogger(__name__)


def send_password_reset_email(user, tenant, reset_url: str) -> bool:
    """
    Envía email de reset de contraseña via EmailService centralizado.
    """
    from apps.public.core.services.email_service import EmailService
    return EmailService.send_password_reset_email(user, tenant, reset_url)
