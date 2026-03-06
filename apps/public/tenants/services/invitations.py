"""
Servicio de invitaciones para activación de owners en subdominios de tenants.

⚠️ IMPORTANTE:
- Genera tokens firmados con TTL (24 horas por defecto)
- Tokens incluyen user_id y tenant_id para validación
- Invalidación tras uso (one-time use)
- Sin signals: toda la lógica está aquí

Referencias:
- Django signing: https://docs.djangoproject.com/en/6.0/topics/signing/
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from django.core import signing
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

User = get_user_model()
logger = logging.getLogger(__name__)

# TTL por defecto: 24 horas
DEFAULT_TOKEN_TTL_HOURS = 24


def generate_invitation_token(user_id: int, tenant_id: int, ttl_hours: int = DEFAULT_TOKEN_TTL_HOURS) -> str:
    """
    Genera un token de invitación firmado con TTL.
    
    ⚠️ SEGURIDAD:
    - Token firmado con SECRET_KEY de Django
    - Incluye user_id y tenant_id para validación
    - TTL configurable (default: 24 horas)
    - One-time use (se invalida tras uso)
    
    Args:
        user_id: ID del usuario a invitar
        tenant_id: ID del tenant al que pertenece
        ttl_hours: TTL del token en horas (default: 24)
    
    Returns:
        str: Token firmado (URL-safe)
    """
    # Payload del token
    payload = {
        'user_id': user_id,
        'tenant_id': tenant_id,
        'expires_at': (datetime.now() + timedelta(hours=ttl_hours)).isoformat(),
    }
    
    # Firmar con SECRET_KEY
    token = signing.dumps(payload, salt='tenant-owner-invitation')
    
    logger.info(
        "✅ Token de invitación generado: user_id=%s, tenant_id=%s, ttl=%s horas",
        user_id, tenant_id, ttl_hours
    )
    
    return token


def verify_invitation_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verifica y decodifica un token de invitación.
    
    ⚠️ SEGURIDAD:
    - Valida la firma del token
    - Verifica que no haya expirado
    - Retorna payload si es válido, None si es inválido/expirado
    
    Args:
        token: Token firmado a verificar
    
    Returns:
        Dict con 'user_id' y 'tenant_id' si es válido, None si es inválido/expirado
    """
    try:
        # Decodificar token (valida firma automáticamente)
        payload = signing.loads(token, salt='tenant-owner-invitation', max_age=timedelta(hours=DEFAULT_TOKEN_TTL_HOURS))
        
        # Verificar expiración manualmente (defensivo)
        expires_at = datetime.fromisoformat(payload['expires_at'])
        if datetime.now() > expires_at:
            logger.warning("⚠️ Token de invitación expirado: expires_at=%s", expires_at)
            return None
        
        logger.info(
            "✅ Token de invitación válido: user_id=%s, tenant_id=%s",
            payload['user_id'], payload['tenant_id']
        )
        
        return payload
    except signing.BadSignature:
        logger.warning("⚠️ Token de invitación con firma inválida")
        return None
    except signing.SignatureExpired:
        logger.warning("⚠️ Token de invitación expirado (max_age)")
        return None
    except Exception as e:
        logger.error("❌ Error verificando token de invitación: %s", e, exc_info=True)
        return None


def send_invitation_email(user: User, tenant, activation_url: str) -> bool:
    """
    Envía email de invitación al owner.
    
    ⚠️ IMPORTANTE:
    - Si no hay SMTP configurado, solo loguea (no falla)
    - Email incluye link absoluto al subdominio del tenant
    - Template HTML/texto plano
    - Logging detallado de cada paso del proceso
    
    Args:
        user: Usuario a invitar
        tenant: Tenant al que pertenece
        activation_url: URL absoluta de activación (ej: https://acme.sintel.com/activate?token=...)
    
    Returns:
        bool: True si se envió (o se logueó en modo desarrollo), False si hubo error
    """
    logger.info(
        "📧 Iniciando envío de email de invitación: user=%s, tenant=%s, activation_url=%s",
        user.email, tenant.schema_name, activation_url
    )
    
    try:
        # Contexto para el template
        context = {
            'user': user,
            'tenant': tenant,
            'activation_url': activation_url,
            'tenant_name': getattr(tenant, 'nombre', 'Tenant'),
        }
        
        logger.info("📝 Renderizando templates de email para %s", user.email)
        
        # Renderizar template HTML
        html_message = render_to_string('emails/owner_invitation.html', context)
        logger.debug("✅ Template HTML renderizado (%d caracteres)", len(html_message))
        
        # Renderizar texto plano (fallback)
        text_message = render_to_string('emails/owner_invitation.txt', context)
        logger.debug("✅ Template texto plano renderizado (%d caracteres)", len(text_message))
        
        # Preparar datos del email
        subject = f'Activa tu cuenta en {context["tenant_name"]}'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user.email]
        
        logger.info(
            "📤 Enviando email: from=%s, to=%s, subject='%s', backend=%s, host=%s, port=%s",
            from_email, recipient_list, subject, settings.EMAIL_BACKEND, 
            settings.EMAIL_HOST, settings.EMAIL_PORT
        )
        
        # Enviar email
        # ⚠️ IMPORTANTE: fail_silently=False para que se lancen excepciones y se manejen correctamente
        send_mail(
            subject=subject,
            message=text_message,
            from_email=from_email,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,  # No silenciar errores - queremos verlos y manejarlos
        )
        
        logger.info(
            "✅ Email de invitación ENVIADO EXITOSAMENTE: user=%s, tenant=%s, activation_url=%s",
            user.email, tenant.schema_name, activation_url
        )
        return True
        
    except Exception as e:
        # Logging detallado del error
        logger.error(
            "❌ ERROR enviando email de invitación: user=%s, tenant=%s, error=%s",
            user.email, tenant.schema_name, str(e),
            exc_info=True  # Incluye stacktrace completo
        )
        
        # En desarrollo sin SMTP, solo loguear pero no fallar
        if settings.DEBUG:
            logger.warning(
                "⚠️ Modo desarrollo: continuando sin email. "
                "URL de activación disponible: %s",
                activation_url
            )
            # Retornar True para no romper el flujo en desarrollo
            return True
        else:
            # En producción, retornar False para que se pueda manejar el error
            logger.error(
                "❌ FALLO CRÍTICO en producción: No se pudo enviar email de invitación. "
                "Revisar configuración SMTP."
            )
            return False


def build_activation_url(domain: str, token: str) -> str:
    """
    Construye URL absoluta de activación en el subdominio del tenant.
    
    ⚠️ v2.30: Shell estático - URL apunta a /activate/?token=... que sirve el shell HTML
    El shell HTML consume la API /api/v1/landing/auth/activate/ internamente.
    
    ⚠️ v2.30: Hardening - Incluye puerto en DEV cuando APP_PORT está configurado.
    - Domain.domain SIEMPRE es FQDN puro (sin puerto), tal como dicta la normalización.
    - En DEV, si APP_PORT=8000, se agrega :8000 a la URL.
    - En PROD, se omite puerto (80/443 implícitos).
    
    Args:
        domain: Dominio del tenant FQDN puro (ej: acme.localhost, acme.sintel.com) - SIN puerto
        token: Token de invitación
    
    Returns:
        str: URL absoluta (ej: http://acme.localhost:8000/activate/?token=... en DEV, http://acme.sintel.com/activate/?token=... en PROD)
    """
    from django.conf import settings
    
    # Determinar protocolo
    if not settings.DEBUG and getattr(settings, "SECURE_SSL_REDIRECT", False):
        protocol = "https"
    else:
        protocol = "http"
    
    # ⚠️ v2.30: Incluir puerto en DEV si APP_PORT está configurado
    app_port = getattr(settings, 'APP_PORT', None)
    if settings.DEBUG and app_port and str(app_port) not in ('80', '443'):
        # En DEV, agregar puerto a la URL
        domain_with_port = f"{domain}:{app_port}"
    else:
        # En PROD o sin puerto, usar dominio sin puerto
        domain_with_port = domain
    
    # Construir URL al shell estático (v2.30)
    # El shell HTML consume la API /api/v1/landing/auth/activate/ internamente
    url = f"{protocol}://{domain_with_port}/activate/?token={token}"
    
    logger.info("✅ URL de activación construida (Shell estático v2.30): %s", url)
    return url
