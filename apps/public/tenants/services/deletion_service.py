"""
Servicio de eliminación permanente de tenants (Hard Delete).

WARNING: OPERACIÓN IRREVERSIBLE:
- Elimina el esquema PostgreSQL del tenant
- Elimina Client, Domain(s) y TenantMembership(s) del esquema public
- No se puede deshacer

Precondición obligatoria: Client.is_active == False
"""

import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django_tenants.utils import get_public_schema_name, schema_exists

from apps.public.tenants.models import Client, TenantMembership

logger = logging.getLogger(__name__)


@transaction.atomic
def hard_delete_tenant(
    client_id: int, actor_user_id: int | None = None, delete_orphan_users: bool = False
) -> None:
    """
    Elimina de forma PERMANENTE el tenant (drop schema + borrado de registros en public).

    WARNING: OPERACIÓN IRREVERSIBLE:
    - Drop del esquema PostgreSQL del tenant
    - Eliminación de Client, Domain(s) y TenantMembership(s) en public
    - Los usuarios globales (User) NO se eliminan (pueden pertenecer a otros tenants)

    Precondición obligatoria: Client.is_active == False

    Args:
        client_id: ID del Client a eliminar
        actor_user_id: ID del usuario que ejecuta la eliminación (para auditoría)

    Raises:
        ValidationError: Si el tenant está activo, no existe, o es el tenant público

    Referencias:
    - django-tenants: https://django-tenants.readthedocs.io/en/latest/use.html
    - auto_drop_schema: Mecanismo oficial para drop del esquema al eliminar Client
    """
    # 1) Obtener tenant con lock (select_for_update)
    try:
        client = Client.objects.select_for_update().get(id=client_id)
    except Client.DoesNotExist:
        raise ValidationError(f"El tenant con ID {client_id} no existe.")

    # 2) BLOQUEO ABSOLUTO DEL TENANT PÚBLICO (defensa en profundidad - PRIMERO)
    # WARNING: CRÍTICO: Esta validación debe ir ANTES de verificar is_active
    # para proteger el tenant público incluso si está activo
    public_schema = get_public_schema_name()
    if client.schema_name == public_schema:
        error_msg = "El esquema público no puede eliminarse bajo ningún motivo. Es el núcleo del sistema y es indeletable."

        # Logging de seguridad con información completa (categoría security.tenants)
        import datetime

        security_logger = logging.getLogger("security.tenants")
        security_logger.critical(
            f"🚨 INTENTO DE ELIMINAR TENANT PÚBLICO RECHAZADO | "
            f"schema={public_schema} | "
            f"actor_user_id={actor_user_id} | "
            f"time={datetime.datetime.now().isoformat()} | "
            f"client_id={client_id}"
        )
        # También registrar en el logger general
        logger.critical(
            f"INTENTO DE ELIMINAR TENANT PÚBLICO: {public_schema} (actor: {actor_user_id})"
        )

        raise ValidationError(error_msg)

    # 3) Precondición obligatoria: is_active == False
    # (Solo después de verificar que no es el tenant público)
    if client.is_active:
        raise ValidationError(
            "El tenant debe estar suspendido (is_active=False) antes de eliminarlo definitivamente. "
            "Primero desactiva el tenant usando el botón 'Desactivar'."
        )

    # 4) Recopilar información para auditoría (antes de eliminar)
    schema_name = client.schema_name
    nombre = client.nombre
    domains = list(client.domains.values_list("domain", flat=True))
    # Usar related_name correcto: 'memberships' (no 'tenantmembership_set')
    memberships_count = client.memberships.count()
    # Recopilar IDs de usuarios asociados a este tenant (antes de borrarlo)
    membership_user_ids = list(
        TenantMembership.objects.filter(client=client).values_list("user_id", flat=True)
    )
    # Determinar qué usuarios son "huérfanos" (solo tenían membresía en este tenant)
    orphan_user_ids = []
    if delete_orphan_users and membership_user_ids:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        for uid in membership_user_ids:
            cnt = TenantMembership.objects.filter(user_id=uid).count()
            if cnt == 1:
                # Solo asociado a este tenant
                try:
                    u = User.objects.only("id", "is_staff", "is_superuser").get(id=uid)
                except User.DoesNotExist:
                    continue
                # Evitar borrar staff o superusers por seguridad (a menos que se quiera explícito)
                if not u.is_staff and not u.is_superuser:
                    orphan_user_ids.append(uid)

    # 5) Verificar que el esquema existe (para logging)
    schema_existed = schema_exists(schema_name)

    # 6) Logging de seguridad (ANTES de eliminar)
    logger.warning(
        f"WARNING: HARD DELETE TENANT INICIADO: "
        f"id={client_id}, schema={schema_name}, nombre={nombre}, "
        f"domains={domains}, memberships={memberships_count}, "
        f"schema_existed={schema_existed}, actor={actor_user_id}"
    )

    # 7) Drop del esquema soportado por django-tenants:
    #    activar temporalmente auto_drop_schema y ejecutar delete()
    #    Esto es el mecanismo oficial/soportado para drop del schema
    original_auto_drop = getattr(client, "auto_drop_schema", False)
    try:
        # Activar auto_drop_schema temporalmente para que delete() haga el drop del schema
        # (mecanismo oficial de django-tenants, evita SQL manual y estados inconsistentes)
        client.auto_drop_schema = True
        client.delete()  # django-tenants manejará el drop del esquema automáticamente
    except Exception as e:
        logger.error(
            f"ERROR: ERROR EN HARD DELETE TENANT: "
            f"id={client_id}, schema={schema_name}, error={str(e)}",
            exc_info=True,
        )
        raise
    finally:
        # No se reutiliza la instancia; por higiene restauramos el flag en memoria
        # (aunque la instancia ya fue eliminada, esto es solo por limpieza de código)
        client.auto_drop_schema = original_auto_drop

    # 8) Verificar que el esquema fue eliminado (post-eliminación)
    if schema_existed and schema_exists(schema_name):
        logger.error(
            f"WARNING: ADVERTENCIA: El esquema '{schema_name}' aún existe después de eliminar el tenant. "
            f"Esto no debería ocurrir si auto_drop_schema=True está configurado correctamente."
        )
    else:
        logger.info(f"OK: Esquema '{schema_name}' eliminado correctamente")

    # 9) Logging final de auditoría
    logger.warning(
        f"OK: HARD DELETE TENANT COMPLETADO: "
        f"id={client_id}, schema={schema_name}, nombre={nombre}, "
        f"domains={domains}, actor={actor_user_id}"
    )
    # 10) Borrar usuarios huérfanos opcionalmente (seguro y conservador)
    if delete_orphan_users and orphan_user_ids:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        try:
            deleted, _ = User.objects.filter(id__in=orphan_user_ids).delete()
            logger.warning(
                f"INFO: Usuarios huérfanos eliminados: user_ids={orphan_user_ids}, deleted_count={deleted}"
            )
        except Exception as e:
            logger.error(
                f"ERROR: No se pudieron eliminar usuarios huérfanos {orphan_user_ids}: {e}",
                exc_info=True,
            )
