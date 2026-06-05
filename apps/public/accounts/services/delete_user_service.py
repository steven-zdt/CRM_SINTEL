"""
Servicio de eliminacion de usuarios globales con cascada cross-schema.

Patron de desacoplamiento via signal:
--------------------------------------
La limpieza de datos tenant (TenantProfile) NO se hace con raw SQL iterando
schemas. En su lugar se emite el signal `global_user_hard_deleting` ANTES
de borrar el usuario. El receiver registrado en apps.tenant.core.services.membership
usa tenant_context() para limpiar TenantProfile en cada schema de forma ORM-safe.

Esto elimina la dependencia de nombres de tabla hardcodeados y mantiene
la unidireccionalidad public → tenant via signal/receiver.
"""
import logging

from django.contrib.auth import get_user_model
from django.db import connection, transaction

from apps.public.accounts.signals import global_user_hard_deleting

logger = logging.getLogger(__name__)

User = get_user_model()


def delete_user_service(
    user_id: int, *, cascade: bool = True, deleted_by_id: int | None = None
) -> None:
    """
    Elimina un usuario global y sus referencias en todos los schemas.

    Orden de operaciones:
    1. Limpiar public: token blacklist, memberships, admin log.
    2. Emitir global_user_hard_deleting — receiver en tenant.core limpia TenantProfile.
    3. Registrar DeletionAudit.
    4. Eliminar el registro User de la BD.
    """
    table = User._meta.db_table

    # 1. Limpiar referencias publicas (best-effort, cada una en su savepoint)
    public_sqls = [
        (
            "DELETE FROM token_blacklist_blacklistedtoken "
            "WHERE token_id IN (SELECT id FROM token_blacklist_outstandingtoken WHERE user_id = %s)",
            [user_id],
        ),
        ("DELETE FROM token_blacklist_outstandingtoken WHERE user_id = %s", [user_id]),
        ("DELETE FROM tenants_tenantmembership WHERE user_id = %s", [user_id]),
        ("DELETE FROM django_admin_log WHERE user_id = %s", [user_id]),
    ]

    for sql, params in public_sqls:
        try:
            with transaction.atomic(), connection.cursor() as cur:
                cur.execute(sql, params)
                logger.info("delete_user_service: %s rows=%s", sql.split()[1], cur.rowcount)
        except Exception as exc:
            logger.warning("delete_user_service: public cleanup failed: %s -> %s", sql, exc)

    # 2. Emitir signal para limpieza tenant (TenantProfile en cada schema).
    # El receiver en apps.tenant.core.services.membership usa tenant_context()
    # para iterar schemas de forma ORM-safe sin raw SQL ni search_path.
    try:
        user_instance = User.objects.filter(pk=user_id).first()
        if user_instance:
            global_user_hard_deleting.send(sender=User, user=user_instance)
            logger.info("delete_user_service: signal sent for user_id=%s", user_id)
        else:
            logger.warning("delete_user_service: user_id=%s not found, skipping signal", user_id)
    except Exception as exc:
        logger.warning("delete_user_service: signal dispatch error: %s", exc)

    # 3. Audit (best-effort, antes del DELETE para preservar trazabilidad)
    try:
        from apps.public.accounts.models import DeletionAudit
        audit = DeletionAudit.objects.create(
            target_user_id=user_id,
            deleted_by_id=deleted_by_id,
            reason="admin_deleted_via_service",
            details={"cascade": bool(cascade)},
        )
        logger.info(
            "delete_user_service: DeletionAudit id=%s target=%s by=%s",
            audit.id, user_id, deleted_by_id,
        )
    except Exception as exc:
        logger.warning("delete_user_service: DeletionAudit failed: %s", exc)

    # 4. Eliminar usuario
    try:
        with transaction.atomic(), connection.cursor() as cur:
            cur.execute(f'DELETE FROM "{table}" WHERE id = %s', [user_id])
            logger.info("delete_user_service: deleted user id=%s rows=%s", user_id, cur.rowcount)
    except Exception as exc:
        logger.error("delete_user_service: failed to delete user id=%s -> %s", user_id, exc)
        raise
