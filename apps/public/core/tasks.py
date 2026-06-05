"""
Tareas de Celery para procesamiento asincrono de correo electronico.

[WARNING] REGLA 0: Cero caracteres especiales o emojis. Solo ASCII.
[WARNING] LAZY IMPORTS:
- Los imports de Django y base de datos se realizan dentro de cada tarea.
- Previene problemas de autodiscovery y dependencias circulares.
"""

import logging
import traceback as tb

from celery import shared_task
from django.db import connection

logger = logging.getLogger(__name__)


def _registrar_dlq(
    task_id: str,
    task_name: str,
    args: list,
    kwargs: dict,
    exception: Exception,
    schema_name: str | None,
    retries: int,
) -> None:
    """Registra una tarea fallida en FailedTenantTask (Dead Letter Queue)."""
    try:
        from apps.public.tenants.models import FailedTenantTask
        FailedTenantTask.objects.create(
            task_id=task_id or "unknown",
            task_name=task_name,
            args=args,
            kwargs=kwargs,
            exception=str(exception),
            traceback=tb.format_exc(),
            tenant_schema=schema_name,
            retries=retries,
        )
        logger.info("[DLQ] Registrado en FailedTenantTask: task=%s", task_name)
    except Exception as dlq_err:
        logger.error("[DLQ] Error registrando en BD: %s", dlq_err)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, queue="high_priority")
def send_tenant_activation_email_task(self, user_id: int, tenant_id: int) -> dict:
    """
    SSoT Celery: envia email de activacion para cualquier owner de tenant privado.
    Genera el token firmado y la URL tenant-especifica internamente.
    """
    logger.info("[send_tenant_activation_email_task] user_id=%s tenant_id=%s [retry=%s]",
                user_id, tenant_id, self.request.retries)
    connection.set_schema_to_public()
    try:
        from django.contrib.auth import get_user_model
        from apps.public.tenants.models import Client
        from apps.public.core.services.email_service import EmailService
        User = get_user_model()
        user = User.objects.get(pk=user_id)
        tenant = Client.objects.get(pk=tenant_id)
        sent = EmailService.send_tenant_activation_email_sync(user, tenant)
        if not sent:
            raise RuntimeError(f"send_tenant_activation_email_sync retorno False para user={user.email}")
        logger.info("[send_tenant_activation_email_task] OK: email enviado a %s | tenant=%s", user.email, tenant.schema_name)
        return {"status": "sent", "user": user.email, "tenant": tenant.schema_name}
    except Exception as ex:
        logger.error("[send_tenant_activation_email_task] ERROR [retry=%s/%s]: %s",
                     self.request.retries, self.max_retries, str(ex), exc_info=True)
        if self.request.retries >= self.max_retries:
            _registrar_dlq(task_id=self.request.id, task_name=self.name,
                           args=[user_id, tenant_id], kwargs={}, exception=ex,
                           schema_name=None, retries=self.request.retries)
            return {"status": "failed_dlq", "user_id": user_id, "tenant_id": tenant_id}
        raise self.retry(exc=ex)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, queue="high_priority")
def send_password_reset_code_email_task(self, user_id: int, tenant_id: int, code: str) -> dict:
    """Tarea Celery: envia email de reset de contrasena con codigo de 8 chars (v3.13.0)."""
    logger.info("[send_password_reset_code_email_task] user_id=%s tenant_id=%s [retry=%s]", user_id, tenant_id, self.request.retries)
    connection.set_schema_to_public()
    try:
        from django.contrib.auth import get_user_model
        from apps.public.tenants.models import Client
        from apps.public.core.services.email_service import EmailService
        User = get_user_model()
        user = User.objects.get(pk=user_id)
        tenant = Client.objects.get(pk=tenant_id)
        sent = EmailService.send_password_reset_code_email_sync(user, tenant, code)
        if not sent:
            raise RuntimeError(f"send_password_reset_code_email_sync retorno False para user={user.email}")
        logger.info("[send_password_reset_code_email_task] OK: codigo enviado a %s | tenant=%s", user.email, tenant.schema_name)
        return {"status": "sent", "user": user.email, "tenant": tenant.schema_name}
    except Exception as ex:
        logger.error("[send_password_reset_code_email_task] ERROR [retry=%s/%s]: %s", self.request.retries, self.max_retries, str(ex), exc_info=True)
        if self.request.retries >= self.max_retries:
            _registrar_dlq(task_id=self.request.id, task_name=self.name, args=[user_id, tenant_id, code], kwargs={}, exception=ex, schema_name=None, retries=self.request.retries)
            return {"status": "failed_dlq", "user_id": user_id, "tenant_id": tenant_id}
        raise self.retry(exc=ex)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="high_priority",
)
def send_invitation_code_email_task(self, user_id: int, tenant_id: int, code: str) -> dict:
    """Tarea Celery asincrona para enviar el email con codigo de activacion de 6 digitos."""
    logger.info(
        "[send_invitation_code_email_task] Iniciando: user_id=%s, tenant_id=%s [retry=%s]",
        user_id, tenant_id, self.request.retries,
    )
    connection.set_schema_to_public()
    try:
        from django.contrib.auth import get_user_model
        from apps.public.tenants.models import Client
        from apps.public.core.services.email_service import EmailService
        User = get_user_model()
        user = User.objects.get(pk=user_id)
        tenant = Client.objects.get(pk=tenant_id)
        sent = EmailService.send_invitation_code_email_sync(user, tenant, code)
        if not sent:
            raise RuntimeError(f"send_invitation_code_email_sync retorno False para user={user.email}")
        logger.info("[send_invitation_code_email_task] OK: Codigo enviado a %s | tenant=%s", user.email, tenant.schema_name)
        return {"status": "sent", "user": user.email, "tenant": tenant.schema_name}
    except Exception as ex:
        logger.error("[send_invitation_code_email_task] ERROR [retry=%s/%s]: %s", self.request.retries, self.max_retries, str(ex), exc_info=True)
        if self.request.retries >= self.max_retries:
            _registrar_dlq(task_id=self.request.id, task_name=self.name, args=[user_id, tenant_id, code], kwargs={}, exception=ex, schema_name=None, retries=self.request.retries)
            return {"status": "failed_dlq", "user_id": user_id, "tenant_id": tenant_id}
        raise self.retry(exc=ex)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="high_priority",
)
def send_invitation_email_task(self, user_id: int, tenant_id: int, activation_url: str) -> dict:
    """
    Tarea Celery asincrona para enviar el email de invitacion al owner.
    """
    logger.info(
        "[send_invitation_email_task] Iniciando: user_id=%s, tenant_id=%s [retry=%s]",
        user_id, tenant_id, self.request.retries,
    )

    connection.set_schema_to_public()

    try:
        from django.contrib.auth import get_user_model
        from apps.public.tenants.models import Client
        from apps.public.core.services.email_service import EmailService

        User = get_user_model()
        user = User.objects.get(pk=user_id)
        tenant = Client.objects.get(pk=tenant_id)

        sent = EmailService.send_invitation_email_sync(user, tenant, activation_url)

        if not sent:
            raise RuntimeError(
                f"send_invitation_email_sync retorno False para user={user.email}"
            )

        logger.info(
            "[send_invitation_email_task] OK: Email enviado a %s | tenant=%s",
            user.email, tenant.schema_name,
        )
        return {"status": "sent", "user": user.email, "tenant": tenant.schema_name}

    except Exception as ex:
        logger.error(
            "[send_invitation_email_task] ERROR [retry=%s/%s]: %s",
            self.request.retries, self.max_retries, str(ex), exc_info=True,
        )

        if self.request.retries >= self.max_retries:
            _registrar_dlq(
                task_id=self.request.id,
                task_name=self.name,
                args=[user_id, tenant_id, activation_url],
                kwargs={},
                exception=ex,
                schema_name=None,
                retries=self.request.retries,
            )
            return {"status": "failed_dlq", "user_id": user_id, "tenant_id": tenant_id}

        raise self.retry(exc=ex)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="high_priority",
)
def send_password_reset_email_task(self, user_id: int, tenant_id: int, reset_url: str) -> dict:
    """
    Tarea Celery asincrona para enviar el email de restablecimiento de contrasena.
    """
    logger.info(
        "[send_password_reset_email_task] Iniciando: user_id=%s, tenant_id=%s [retry=%s]",
        user_id, tenant_id, self.request.retries,
    )

    connection.set_schema_to_public()

    try:
        from django.contrib.auth import get_user_model
        from apps.public.tenants.models import Client
        from apps.public.core.services.email_service import EmailService

        User = get_user_model()
        user = User.objects.get(pk=user_id)
        tenant = Client.objects.get(pk=tenant_id)

        sent = EmailService.send_password_reset_email_sync(user, tenant, reset_url)

        if not sent:
            raise RuntimeError(
                f"send_password_reset_email_sync retorno False para user={user.email}"
            )

        logger.info(
            "[send_password_reset_email_task] OK: Email enviado a %s | tenant=%s",
            user.email, tenant.schema_name,
        )
        return {"status": "sent", "user": user.email, "tenant": tenant.schema_name}

    except Exception as ex:
        logger.error(
            "[send_password_reset_email_task] ERROR [retry=%s/%s]: %s",
            self.request.retries, self.max_retries, str(ex), exc_info=True,
        )

        if self.request.retries >= self.max_retries:
            _registrar_dlq(
                task_id=self.request.id,
                task_name=self.name,
                args=[user_id, tenant_id, reset_url],
                kwargs={},
                exception=ex,
                schema_name=None,
                retries=self.request.retries,
            )
            return {"status": "failed_dlq", "user_id": user_id, "tenant_id": tenant_id}

        raise self.retry(exc=ex)
