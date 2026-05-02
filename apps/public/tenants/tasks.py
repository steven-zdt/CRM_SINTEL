"""
Tareas Celery para onboarding asíncrono de tenants.

Referencia: https://docs.celeryproject.org/en/stable/django/first-steps-with-django.html

[WARNING] LAZY IMPORTS:
- Los imports pesados se hacen dentro de las funciones (lazy import)
- Evita ImportError durante autodiscovery del worker
- Mejora la robustez del arranque de Celery
"""

import logging

from celery import shared_task
from django.db import connection

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    queue="high_priority",  # [WARNING] CRÍTICO: Forzar cola de alta prioridad
)
def onboard_tenant_task(self, nombre: str, admin_user_id: int, schema_name: str = None) -> dict:
    """
    Tarea Celery para crear tenant de forma asíncrona.

    [WARNING] v2.17: Estandarización de subdominios
    - El dominio se construye automáticamente como: {schema_name}.{TENANT_DOMAIN_BASE}
    - Ya no se acepta el parámetro 'dominio' - todos los tenants usan subdominios
    - El dominio se crea automáticamente por la señal post_save en signals.py
    - Crea Client, migra el schema del tenant, y asigna admin global como primary admin
    - Ejecuta en cola 'high_priority' para garantizar procesamiento inmediato

    Args:
        nombre: Nombre de la empresa
        admin_user_id: ID del usuario administrador existente
        schema_name: Schema name (opcional, se genera desde nombre si no se proporciona, sin puntos)

    Returns:
        Dict con client_id, schema_name, domain, login_url

    Referencias:
    - https://climbtheladder.com/django-celery-tasks/
    - https://pypi.org/project/django-tenants/
    """
    # [WARNING] LOG CRÍTICO: Confirmar que el worker tomó la tarea
    logger.info(
        "🚀 INICIANDO ONBOARDING TASK [ID: %s] | Schema: %s | Nombre: %s | Admin ID: %s",
        self.request.id,
        schema_name,
        nombre,
        admin_user_id,
    )

    # Asegurar que corremos en PUBLIC schema antes de crear Client
    # (evita contaminación si el worker quedó con otro search_path)
    # Referencia: https://django-tenants.readthedocs.io/en/latest/use.html#schema-context
    connection.set_schema_to_public()

    try:
        # [WARNING] LAZY IMPORT: Import interno para evitar ImportError en autodiscovery del worker
        # El servicio real vive en apps/services/onboarding/empresa_service.py
        # Re-export disponible en apps.public.tenants.services para compatibilidad
        from apps.services.onboarding.empresa_service import crear_tenant_con_owner

        # Crear tenant usando el servicio centralizado
        tenant, domain, login_url = crear_tenant_con_owner(
            nombre=nombre,
            admin_user_id=admin_user_id,
            schema_name=schema_name,
        )

        logger.info(
            "[OK] Tenant creado: %s (%s) -> %s", tenant.schema_name, domain.domain, login_url
        )

        result = {
            "client_id": tenant.id,
            "schema_name": tenant.schema_name,
            "domain": domain.domain,
            "login_url": login_url,
        }

        logger.info(
            "[OK] ONBOARDING TASK COMPLETADA [ID: %s] | Tenant: %s (%s) | Login URL: %s",
            self.request.id,
            tenant.nombre,
            tenant.schema_name,
            login_url,
        )

        return result
    except Exception as ex:
        # Log detallado en servidor
        logger.error(
            "[ERROR] ERROR EN ONBOARDING TASK [ID: %s] | Tenant: '%s' (schema_name: %s) | Error: %s",
            self.request.id,
            nombre,
            schema_name,
            str(ex),
            exc_info=True,
        )

        # [ARCHITECTURE v2.61.4] REGLA 11: DLQ al fallar definitivamente
        if self.request.retries >= self.max_retries:
            try:
                from .models import FailedTenantTask
                import traceback
                FailedTenantTask.objects.create(
                    task_id=self.request.id,
                    task_name=self.name,
                    args=[nombre, admin_user_id],
                    kwargs={"schema_name": schema_name},
                    exception=str(ex),
                    traceback=traceback.format_exc(),
                    tenant_schema=schema_name,
                    retries=self.request.retries
                )
                logger.info("[DLQ] Fallo registrado en FailedTenantTask para revisión manual.")
            except Exception as dlq_err:
                logger.error(f"[DLQ] Error registrando fallo en BD: {dlq_err}")

        # Re-lanzar con mensaje enriquecido para que el frontend lo muestre en la tarjeta de estado
        raise Exception(
            f"Error al crear el tenant '{nombre}' (schema='{schema_name}'): {str(ex)}"
        ) from ex
