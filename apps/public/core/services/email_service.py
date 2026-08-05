"""
Servicio centralizado de envio de correos electronicos (v2.61.4).

[WARNING] SSoT: Este es el UNICO lugar para configurar el envio de emails.
Centraliza templates, logica de reintentos y logging de comunicaciones.
"""

import logging
from urllib.parse import urlparse
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def _send_email(subject: str, recipient_list: list, template_name: str, context: dict) -> bool:
        """Metodo interno para renderizar y enviar email."""
        try:
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
    def send_tenant_activation_email(cls, user, tenant) -> bool:
        """
        SSoT — Unica funcion autorizada para enviar el email de activacion
        a cualquier owner de tenant privado (nuevo o reenvio).

        Genera internamente el token firmado y construye la URL del tenant privado:
            https://{schema}.sintel.net.co/static/tenant/core/auth/activate.html?token=...

        Aplica para TODOS los flujos:
          - Onboarding nuevo tenant (crear_tenant_con_owner)
          - Reenvio desde consola (resend-invitation)
          - Activacion manual de emergencia (manual-activate)
          - Cualquier creacion futura de tenant privado
        """
        from apps.public.core.tasks import send_tenant_activation_email_task
        send_tenant_activation_email_task.delay(user.pk, tenant.pk)
        return True

    @classmethod
    def send_tenant_activation_email_sync(cls, user, tenant) -> bool:
        """
        Sincrono: genera codigo de activacion (8 chars, Redis, TTL 48h) y envia email.

        Esquema canonico (v3.15.1):
          - El codigo se genera con generate_activation_code() y se persiste en Redis.
          - El email muestra el codigo prominentemente.
          - El link apunta a la pagina de activacion del tenant:
              https://{schema}.sintel.net.co/static/tenant/core/auth/activate.html
            El usuario ingresa email + codigo + contrasena en esa pagina.
          - NO se usa URL firmada con token embebido.
        """
        from apps.public.tenants.services.invitations import generate_activation_code
        schema = getattr(tenant, "schema_name", "")
        domain_base = getattr(settings, "TENANT_DOMAIN_BASE", "sintel.net.co")
        protocol = getattr(settings, "SITE_PROTOCOL", "https")

        # Generar codigo Redis (8 chars alfanumericos, TTL 48h, uso unico)
        code = generate_activation_code(user_id=user.id, tenant_id=tenant.id, ttl_hours=48)

        # URL de la pagina de activacion del tenant (sin token en URL)
        activate_url = f"{protocol}://{schema}.{domain_base}/static/tenant/core/auth/activate.html"
        login_url = f"{protocol}://{schema}.{domain_base}/static/tenant/core/auth/login.html"
        tenant_name = getattr(tenant, "nombre", schema)

        context = {
            "user": user,
            "tenant": tenant,
            "tenant_name": tenant_name,
            "code": code,
            "activate_url": activate_url,
            "login_url": login_url,
            "contact_email": getattr(settings, "CONTACT_EMAIL", getattr(settings, "DEFAULT_FROM_EMAIL", "")),
        }
        subject = f"Activa tu cuenta en {tenant_name} - SINTEL"
        return cls._send_email(subject, [user.email], "owner_invitation", context)

    @classmethod
    def send_invitation_code_email(cls, user, tenant, code: str) -> bool:
        """Mantiene compatibilidad — delega a send_tenant_activation_email."""
        return cls.send_tenant_activation_email(user, tenant)

    @classmethod
    def send_invitation_code_email_sync(cls, user, tenant, code: str) -> bool:
        """
        Envia email de invitacion al owner del tenant.

        URL de activacion: apunta directamente a la pagina de activacion del TENANT
        (https://{schema}.sintel.net.co/static/tenant/core/auth/activate.html?token=...)
        con un token firmado. El tenant tiene un endpoint propio que valida el token
        y establece la contrasena antes de redirigir al workspace.

        El codigo de 8 chars se incluye como metodo alternativo (via sintel.net.co/activate/).
        """
        tenant_name = getattr(tenant, "nombre", "Tenant")
        schema = getattr(tenant, "schema_name", "")
        domain_base = getattr(settings, "TENANT_DOMAIN_BASE", "sintel.net.co")
        protocol = getattr(settings, "SITE_PROTOCOL", "https")

        # Generar token firmado para el link directo de activacion del tenant
        from apps.public.tenants.services.invitations import generate_invitation_token
        try:
            signed_token = generate_invitation_token(
                user_id=user.id,
                tenant_id=tenant.id,
                ttl_hours=48,
            )
            # URL directa a la pagina de activacion del TENANT PRIVADO
            activate_url = (
                f"{protocol}://{schema}.{domain_base}"
                f"/static/tenant/core/auth/activate.html?token={signed_token}"
            )
        except Exception:
            # Fallback al dominio publico si hay error generando el token
            activate_url = f"{protocol}://{schema}.{domain_base}/static/tenant/core/auth/activate.html"

        login_url = f"{protocol}://{schema}.{domain_base}/static/tenant/core/auth/login.html"

        context = {
            "user": user,
            "tenant": tenant,
            "tenant_name": tenant_name,
            "code": code,
            "activate_url": activate_url,
            "login_url": login_url,
            "contact_email": getattr(settings, "CONTACT_EMAIL", getattr(settings, "DEFAULT_FROM_EMAIL", "")),
        }
        subject = f"Activa tu cuenta en {tenant_name} - SINTEL"
        return cls._send_email(subject, [user.email], "owner_invitation", context)

    @classmethod
    def send_invitation_email(cls, user, tenant, activation_url: str) -> bool:
        """Planifica el envio de email de invitacion de forma asincrona via Celery."""
        from apps.public.core.tasks import send_invitation_email_task
        send_invitation_email_task.delay(user.pk, tenant.pk, activation_url)
        return True

    @classmethod
    def send_invitation_email_sync(cls, user, tenant, activation_url: str) -> bool:
        """Metodo sincrono real para enviar el email de invitacion."""
        parsed = urlparse(activation_url)
        login_url = f"{parsed.scheme}://{parsed.netloc}/"

        context = {
            "user": user,
            "tenant": tenant,
            "activation_url": activation_url,  # clave legacy
            "activate_url": activation_url,     # alias — clave del template actual
            "login_url": login_url,
            "code": "",
            "tenant_name": getattr(tenant, "nombre", "Tenant"),
            "contact_email": getattr(settings, "CONTACT_EMAIL", getattr(settings, "DEFAULT_FROM_EMAIL", "")),
        }

        subject = f"Activa tu cuenta en {context['tenant_name']}"
        return cls._send_email(subject, [user.email], "owner_invitation", context)

    @classmethod
    def send_password_reset_code_email(cls, user, tenant, code: str) -> bool:
        """Despacha tarea Celery para enviar email de reset con codigo de 8 chars (v3.13.0)."""
        from apps.public.core.tasks import send_password_reset_code_email_task
        send_password_reset_code_email_task.delay(user.pk, tenant.pk, code)
        return True

    @classmethod
    def send_password_reset_code_email_sync(cls, user, tenant, code: str) -> bool:
        """Sincrono: envia email de reset con codigo alfanumerico de 8 chars."""
        tenant_name = getattr(tenant, "nombre", "Tenant")
        schema = getattr(tenant, "schema_name", "")
        domain_base = getattr(settings, "TENANT_DOMAIN_BASE", "sintel.net.co")
        protocol = getattr(settings, "SITE_PROTOCOL", "https")
        reset_url = f"{protocol}://{schema}.{domain_base}/static/tenant/core/auth/reset-confirm.html"
        context = {
            "user": user,
            "tenant": tenant,
            "tenant_name": tenant_name,
            "code": code,
            "reset_url": reset_url,
            "contact_email": getattr(settings, "CONTACT_EMAIL", getattr(settings, "DEFAULT_FROM_EMAIL", "")),
        }
        subject = f"Codigo para restablecer tu contrasena en {tenant_name} - SINTEL"
        return cls._send_email(subject, [user.email], "password_reset", context)

    @classmethod
    def send_password_reset_email(cls, user, tenant, reset_url: str) -> bool:
        """Legacy: despacha tarea Celery con URL de reset (mantenido por compatibilidad)."""
        from apps.public.core.tasks import send_password_reset_email_task
        send_password_reset_email_task.delay(user.pk, tenant.pk, reset_url)
        return True

    @classmethod
    def send_password_reset_email_sync(cls, user, tenant, reset_url: str) -> bool:
        """Legacy sincrono: envia email con URL de reset."""
        context = {
            "user": user,
            "tenant": tenant,
            "reset_url": reset_url,
            "tenant_name": getattr(tenant, "nombre", "Tenant"),
        }
        subject = f"Restablecer contrasena en {context['tenant_name']}"
        return cls._send_email(subject, [user.email], "password_reset", context)

