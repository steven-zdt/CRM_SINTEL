"""
Tareas Celery para onboarding asincrono de tenants.

[WARNING] LAZY IMPORTS:
- Los imports pesados se hacen dentro de las funciones (lazy import)
- Evita ImportError durante autodiscovery del worker
- Mejora la robustez del arranque de Celery
"""

import logging
import traceback as tb

from celery import shared_task
from django.db import connection

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    queue="high_priority",
)
def onboard_tenant_task(self, nombre: str, admin_user_id: int, schema_name: str = None) -> dict:
    """
    Tarea Celery para crear tenant de forma asincrona.

    Args:
        nombre: Nombre de la empresa
        admin_user_id: ID del usuario administrador existente
        schema_name: Schema name (opcional, se genera desde nombre si no se proporciona)

    Returns:
        Dict con client_id, schema_name, domain, login_url
    """
    logger.info(
        "INICIANDO ONBOARDING TASK [ID: %s] | Schema: %s | Nombre: %s | Admin ID: %s",
        self.request.id, schema_name, nombre, admin_user_id,
    )

    # Asegurar PUBLIC schema antes de crear Client
    connection.set_schema_to_public()

    try:
        from apps.services.onboarding.empresa_service import crear_tenant_con_owner

        # CRITICO: crear_tenant_con_owner retorna dict, NO tupla
        result = crear_tenant_con_owner(
            nombre=nombre,
            admin_user_id=admin_user_id,
            schema_name=schema_name,
        )

        logger.info(
            "ONBOARDING TASK COMPLETADA [ID: %s] | client_id=%s | domain=%s | login_url=%s",
            self.request.id,
            result.get("client_id"),
            result.get("domain"),
            result.get("login_url"),
        )

        return {
            "client_id": result.get("client_id"),
            "schema_name": schema_name,
            "domain": result.get("domain"),
            "login_url": result.get("login_url"),
        }

    except Exception as ex:
        logger.error(
            "ERROR EN ONBOARDING TASK [ID: %s] | Tenant: '%s' (schema: %s) | Error: %s",
            self.request.id, nombre, schema_name, str(ex), exc_info=True,
        )

        if self.request.retries >= self.max_retries:
            _registrar_dlq(
                task_id=self.request.id,
                task_name=self.name,
                args=[nombre, admin_user_id],
                kwargs={"schema_name": schema_name},
                exception=ex,
                schema_name=schema_name,
                retries=self.request.retries,
            )

        raise Exception(
            f"Error al crear el tenant '{nombre}' (schema='{schema_name}'): {str(ex)}"
        ) from ex


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="high_priority",
)
def send_activation_email_task(self, user_id: int, token: str, domain: str) -> dict:
    """
    Envia el email de activacion al owner del nuevo tenant.

    v3.14.0: Delega a send_tenant_activation_email_task (SSoT).
    El token y domain recibidos se ignoran — la URL se genera en el SSoT.
    """
    logger.info(
        "[send_activation_email_task] user_id=%s domain=%s [retry=%s] → delegando a SSoT",
        user_id, domain, self.request.retries,
    )

    try:
        from django.contrib.auth import get_user_model
        from apps.public.tenants.models import Domain
        from apps.public.core.services.email_service import EmailService

        User = get_user_model()
        user = User.objects.get(pk=user_id)
        domain_obj = Domain.objects.select_related("tenant").get(domain=domain)
        tenant = domain_obj.tenant

        # SSoT: genera token + URL tenant-especifica internamente
        sent = EmailService.send_tenant_activation_email_sync(user, tenant)

        if not sent:
            raise RuntimeError(
                f"send_tenant_activation_email_sync retorno False para user={user.email}"
            )

        logger.info(
            "[send_activation_email_task] OK: Email enviado a %s | tenant=%s",
            user.email, tenant.schema_name,
        )
        return {"status": "sent", "user": user.email, "domain": domain}

    except Exception as ex:
        logger.error(
            "[send_activation_email_task] ERROR [retry=%s/%s]: %s",
            self.request.retries, self.max_retries, str(ex), exc_info=True,
        )

        if self.request.retries >= self.max_retries:
            _registrar_dlq(
                task_id=self.request.id,
                task_name=self.name,
                args=[user_id, token, domain],
                kwargs={},
                exception=ex,
                schema_name=None,
                retries=self.request.retries,
            )
            logger.error(
                "[DLQ] send_activation_email_task registrada en FailedTenantTask "
                "tras %s intentos | user_id=%s domain=%s",
                self.request.retries, user_id, domain,
            )
            return {"status": "failed_dlq", "user_id": user_id}

        raise self.retry(exc=ex)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    queue="high_priority",
)
def provision_tenant_certificates_task(self, domain: str, schema_name: str) -> dict:
    """
    Aprovisiona y/o verifica el certificado SSL del dominio del nuevo tenant.

    Comportamiento segun arquitectura:
    - Wildcard cert (*.sintel.net.co): verifica cobertura, no requiere accion adicional.
    - Cert individual: ejecuta CERT_PROVISION_SCRIPT si esta configurado en settings.
    - En ambos casos: verifica resolucion DNS y registra el resultado.

    Variables de entorno relevantes:
        TENANT_DOMAIN_BASE   Base del dominio (ej: sintel.net.co)
        CERT_PROVISION_SCRIPT Ruta absoluta al script bash de aprovisionamiento (opcional)
    """
    import os
    import socket
    import subprocess

    logger.info(
        "[provision_tenant_certificates_task] Iniciando: domain=%s, schema=%s [retry=%s]",
        domain, schema_name, self.request.retries,
    )

    try:
        from django.conf import settings

        # -- Verificacion DNS -------------------------------------------------
        try:
            ip = socket.gethostbyname(domain)
            logger.info(
                "[provision_tenant_certificates_task] DNS OK: %s -> %s", domain, ip
            )
        except socket.gaierror as dns_err:
            # No es critico en desarrollo; el dominio puede propagarse despues
            logger.warning(
                "[provision_tenant_certificates_task] DNS no resuelve %s: %s "
                "(puede ser normal en desarrollo o propagacion pendiente)",
                domain, dns_err,
            )

        # -- Certificado wildcard: ya cubre todos los subdominios -------------
        wildcard_base = getattr(settings, "TENANT_DOMAIN_BASE", "sintel.net.co")
        if domain.endswith(f".{wildcard_base}"):
            logger.info(
                "[provision_tenant_certificates_task] Wildcard *.%s cubre %s. "
                "No se requiere aprovisionamiento individual.",
                wildcard_base, domain,
            )
            return {
                "status": "wildcard_covered",
                "domain": domain,
                "schema": schema_name,
                "cert_type": f"*.{wildcard_base}",
            }

        # -- Certificado individual via script externo (Let's Encrypt, etc.) --
        cert_script = getattr(settings, "CERT_PROVISION_SCRIPT", None)
        if cert_script and os.path.isfile(cert_script):
            logger.info(
                "[provision_tenant_certificates_task] Ejecutando script: %s %s %s",
                cert_script, domain, schema_name,
            )
            proc = subprocess.run(
                [cert_script, domain, schema_name],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"Script de certificados fallo (rc={proc.returncode}): "
                    f"{proc.stderr[:500]}"
                )
            logger.info(
                "[provision_tenant_certificates_task] Script OK: %s",
                proc.stdout[:200],
            )
            return {
                "status": "provisioned",
                "domain": domain,
                "schema": schema_name,
                "output": proc.stdout[:200],
            }

        # -- Sin script configurado: solo loguear para accion manual ----------
        logger.warning(
            "[provision_tenant_certificates_task] CERT_PROVISION_SCRIPT no configurado. "
            "Dominio %s requiere configuracion manual de certificado SSL.",
            domain,
        )
        return {"status": "manual_required", "domain": domain, "schema": schema_name}

    except Exception as ex:
        logger.error(
            "[provision_tenant_certificates_task] ERROR [retry=%s/%s]: %s",
            self.request.retries, self.max_retries, str(ex), exc_info=True,
        )

        if self.request.retries >= self.max_retries:
            _registrar_dlq(
                task_id=self.request.id,
                task_name=self.name,
                args=[domain, schema_name],
                kwargs={},
                exception=ex,
                schema_name=schema_name,
                retries=self.request.retries,
            )
            logger.error(
                "[DLQ] provision_tenant_certificates_task registrada en FailedTenantTask "
                "tras %s intentos | domain=%s",
                self.request.retries, domain,
            )
            return {"status": "failed_dlq", "domain": domain, "schema": schema_name}

        raise self.retry(exc=ex)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def reconcile_tenants_lifecycle_task(self) -> dict:
    """
    Tarea periodica: reconcilia el is_active de todos los tenants con
    trial vencido (docs/console/TENANT_LIFECYCLE.md).

    IMPORTANTE (Fase 17-19 del plan Console Tenants): esta tarea es
    SECUNDARIA -- refleja el estado en el admin (util para el listado de
    /console/tenants/ y para tenants sin trafico entrante), pero el
    bloqueo de acceso REAL ya ocurre en tiempo real via
    TenantSecurityMiddleware (que llama a la misma funcion de
    reconciliacion en cada request). El acceso NUNCA depende de que esta
    tarea haya corrido.
    """
    from apps.public.tenants.services.lifecycle import reconcile_all_tenants

    try:
        resultado = reconcile_all_tenants()
        if resultado["reconciled"]:
            logger.warning(
                "[LIFECYCLE] Reconciliacion periodica: %s tenant(s) desactivados por trial vencido: %s",
                len(resultado["reconciled"]), resultado["reconciled"],
            )
        if resultado["errors"]:
            logger.error(
                "[LIFECYCLE] Reconciliacion periodica: %s error(es): %s",
                len(resultado["errors"]), resultado["errors"],
            )
        return resultado
    except Exception as ex:
        if self.request.retries >= self.max_retries:
            _registrar_dlq(
                task_id=self.request.id,
                task_name="reconcile_tenants_lifecycle_task",
                args=[],
                kwargs={},
                exception=ex,
                schema_name=None,
                retries=self.request.retries,
            )
            return {"status": "failed_dlq"}
        raise self.retry(exc=ex)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

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
        from .models import FailedTenantTask
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
