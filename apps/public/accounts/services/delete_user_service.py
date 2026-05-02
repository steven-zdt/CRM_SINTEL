import logging
from collections.abc import Iterable

from django.db import connection, transaction

logger = logging.getLogger(__name__)


def _get_tenant_schemas() -> Iterable[str]:
    try:
        from apps.public.tenants.models import Client

        return [c["schema_name"] for c in Client.objects.values("schema_name")]
    except Exception:
        return []


def delete_user_service(
    user_id: int, *, cascade: bool = True, deleted_by_id: int | None = None
) -> None:
    """
    Delete a user and cascade-clean related public and tenant data.

    This function performs best-effort cleanup in the following order:
    1. Delete public app rows that reference the user (token blacklist, memberships, admin logs)
    2. For each tenant schema, delete tenant profile rows referencing the user
    3. Delete the user row from the public user table

    The function uses raw SQL for predictable behavior across schemas.
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    table = User._meta.db_table

    # Public cleanup statements (best-effort) - each statement in its own savepoint
    public_sqls = [
        (
            "DELETE FROM token_blacklist_blacklistedtoken WHERE token_id IN (SELECT id FROM token_blacklist_outstandingtoken WHERE user_id = %s)",
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
                logger.info(
                    "delete_user_service: executed %s rows=%s", sql.split()[1], cur.rowcount
                )
        except Exception as e:
            logger.warning("delete_user_service: failed %s -> %s", sql, e)

    # Tenant schemas: delete tenant profile rows that reference this user. Each schema in its own savepoint.
    schemas = _get_tenant_schemas()
    for schema in schemas:
        try:
            with transaction.atomic(), connection.cursor() as cur:
                cur.execute(f'SET search_path TO "{schema}"')
                cur.execute("DELETE FROM perfil_tenantprofile WHERE user_id = %s", [user_id])
                logger.info(
                    "delete_user_service: deleted tenant profiles in %s rows=%s",
                    schema,
                    cur.rowcount,
                )
        except Exception as e:
            logger.warning(
                "delete_user_service: schema=%s skip/profile-delete failed: %s", schema, e
            )

    # Finally delete the user row in its own atomic block
    try:
        # Record audit BEFORE deleting the user so we retain who triggered it
        try:
            from django.contrib.auth import get_user_model

            from apps.public.accounts.models import DeletionAudit

            User = get_user_model()
            # best-effort: deleted_by may not exist (caller's context)
            deleted_by = None
        except Exception:
            DeletionAudit = None
            deleted_by = None

        if DeletionAudit is not None:
            try:
                # Insert audit row using ORM to ensure proper types
                audit = DeletionAudit.objects.create(
                    target_user_id=user_id,
                    deleted_by_id=deleted_by_id,
                    reason="admin_deleted_via_service",
                    details={"cascade": bool(cascade)},
                )
                logger.info(
                    "delete_user_service: created DeletionAudit id=%s target=%s by=%s",
                    getattr(audit, 'id', None),
                    user_id,
                    deleted_by_id,
                )
            except Exception as e:
                logger.warning("delete_user_service: failed to write DeletionAudit: %s", e)
        else:
            logger.info("delete_user_service: DeletionAudit model not available, skipping audit write")

        with transaction.atomic(), connection.cursor() as cur:
            cur.execute(f'DELETE FROM "{table}" WHERE id = %s', [user_id])
            logger.info(
                "delete_user_service: deleted user id=%s rows=%s", user_id, cur.rowcount
            )
    except Exception as e:
        logger.error("delete_user_service: failed to delete user id=%s -> %s", user_id, e)
        raise
