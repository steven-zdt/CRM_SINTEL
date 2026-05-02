"""
Servicio centralizado de envío de correos electrónicos (v2.61.4).

[WARNING] SSoT: Este es el ÚNICO lugar para configurar el envío de emails.
Centraliza templates, lógica de reintentos y logging de comunicaciones.
"""

import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def _send_email(subject: str, recipient_list: list, template_name: str, context: dict) -> bool:
        """Método interno para renderizar y enviar email."""
        try:
            # SINTEL v2.61 Standard: Templates en core
            full_template_path = f"public/core/emails/{template_name}"
            
            logger.info(f"[EMAIL:SEND] Enviando a {recipient_list}: {subject}")
            
            html_message = render_to_string(f"{full_template_path}.html", context)
            text_message = render_to_string(f"{full_template_path}.txt", context)
            
            send_mail(
                subject=subject,
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"[EMAIL:OK] Enviado exitosamente a {recipient_list}")
            return True
            
        except Exception as e:
            logger.error(f"[EMAIL:ERROR] Fallo al enviar a {recipient_list}: {str(e)}", exc_info=True)
            if settings.DEBUG:
                logger.warning(
                    f"[EMAIL:DEBUG] Email NO enviado (excepcion capturada). "
                    f"Destinatario: {recipient_list} | Asunto: {subject} | "
                    f"Causa: {type(e).__name__}: {e}"
                )
            return False

    @classmethod
    def send_invitation_email(cls, user, tenant, activation_url: str) -> bool:
        """Envía email de invitación al administrador del tenant."""
        from urllib.parse import urlparse
        
        parsed = urlparse(activation_url)
        login_url = f"{parsed.scheme}://{parsed.netloc}/"
        
        context = {
            "user": user,
            "tenant": tenant,
            "activation_url": activation_url,
            "login_url": login_url,
            "tenant_name": getattr(tenant, "nombre", "Tenant"),
            "contact_email": getattr(settings, "CONTACT_EMAIL", getattr(settings, "DEFAULT_FROM_EMAIL", "")),
        }
        
        subject = f"Activa tu cuenta en {context['tenant_name']}"
        return cls._send_email(subject, [user.email], "owner_invitation", context)

    @classmethod
    def send_password_reset_email(cls, user, tenant, reset_url: str) -> bool:
        """Envía email de restablecimiento de contraseña."""
        context = {
            "user": user,
            "tenant": tenant,
            "reset_url": reset_url,
            "tenant_name": getattr(tenant, "nombre", "Tenant"),
        }
        
        subject = f"Restablecer contraseña en {context['tenant_name']}"
        return cls._send_email(subject, [user.email], "password_reset", context)
