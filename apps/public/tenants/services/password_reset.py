"""
Servicio de password reset para tenants privados (API-First).

⚠️ v2.30: API-First - Envía emails con URLs que apuntan a endpoints REST.
Usa tokens Django estándar (PasswordResetTokenGenerator) con uidb64.
"""
import logging
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

User = get_user_model()
logger = logging.getLogger(__name__)


def send_password_reset_email(user: User, tenant, reset_url: str) -> bool:
    """
    Envía email de reset de contraseña al usuario.
    
    ⚠️ v2.30: API-First - Email incluye URL que apunta a endpoint REST.
    
    Args:
        user: Usuario que solicita el reset
        tenant: Tenant al que pertenece
        reset_url: URL absoluta de reset (ej: https://tenant.com/reset-password/confirm/?uidb64=...&token=...)
    
    Returns:
        bool: True si se envió exitosamente, False en caso de error
    """
    logger.info(
        "📧 Iniciando envío de email de reset de contraseña: user=%s, tenant=%s, reset_url=%s",
        user.email, tenant.schema_name, reset_url
    )
    
    try:
        # Contexto para el template
        context = {
            'user': user,
            'tenant': tenant,
            'reset_url': reset_url,
            'tenant_name': getattr(tenant, 'nombre', 'Tenant'),
        }
        
        logger.info("📝 Renderizando templates de email para %s", user.email)
        
        # Renderizar template HTML
        html_message = render_to_string('emails/password_reset.html', context)
        logger.debug("✅ Template HTML renderizado (%d caracteres)", len(html_message))
        
        # Renderizar texto plano (fallback)
        text_message = render_to_string('emails/password_reset.txt', context)
        logger.debug("✅ Template texto plano renderizado (%d caracteres)", len(text_message))
        
        # Preparar datos del email
        subject = f'Restablecer contraseña en {context["tenant_name"]}'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user.email]
        
        logger.info(
            "📤 Enviando email: from=%s, to=%s, subject='%s', backend=%s, host=%s, port=%s",
            from_email, recipient_list, subject, settings.EMAIL_BACKEND,
            settings.EMAIL_HOST, settings.EMAIL_PORT
        )
        
        # Enviar email
        send_mail(
            subject=subject,
            message=text_message,
            from_email=from_email,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,  # No silenciar errores - queremos verlos y manejarlos
        )
        
        logger.info(
            "✅ Email de reset de contraseña ENVIADO EXITOSAMENTE: user=%s, tenant=%s, reset_url=%s",
            user.email, tenant.schema_name, reset_url
        )
        return True
        
    except Exception as e:
        # Logging detallado del error
        logger.error(
            "❌ ERROR enviando email de reset de contraseña: user=%s, tenant=%s, error=%s",
            user.email, tenant.schema_name, str(e),
            exc_info=True  # Incluye stacktrace completo
        )
        
        # En desarrollo sin SMTP, solo loguear pero no fallar
        if settings.DEBUG:
            logger.warning(
                "⚠️ Modo desarrollo: continuando sin email. "
                "URL de reset disponible: %s",
                reset_url
            )
            # Retornar True para no romper el flujo en desarrollo
            return True
        else:
            # En producción, retornar False para que se pueda manejar el error
            logger.error(
                "❌ FALLO CRÍTICO en producción: No se pudo enviar email de reset de contraseña. "
                "Revisar configuración SMTP."
            )
            return False
