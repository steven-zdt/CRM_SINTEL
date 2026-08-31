"""
Servicio de lifecycle/trial de tenants (Console Tenants CRUD + Lifecycle).

SSoT del trial: NO se agregan campos nuevos. Se reutilizan los ya
existentes en `Client` (docs/console/CONSOLE_TENANTS_BASELINE.md):

    - `on_trial`    (bool)      -- si el tenant está en régimen de prueba
    - `paid_until`  (DateField) -- fecha hasta la cual el tenant tiene
                                    acceso (fin del trial o de la
                                    suscripción), sin hora
    - `is_active`   (bool)      -- YA tiene enforcement real via
                                    TenantSecurityMiddleware (403 si False)

Política de expiración (sin ambigüedad de hora, per Fase 14 del plan):
el tenant permanece activo durante TODO el día calendario `paid_until`
(zona horaria `settings.TIME_ZONE`). Expira al iniciar el día siguiente.
Comparación: `timezone.localdate() > client.paid_until`.

Este módulo es el único lugar que decide si un trial expiró. El
middleware y la tarea periódica de Celery llaman a la MISMA función
(`reconcile_tenant_lifecycle`) -- nunca se duplica la regla de negocio.
"""
from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

logger = logging.getLogger(__name__)


# Estados derivados (nunca almacenados -- siempre calculados desde
# on_trial/paid_until/is_active, per Fase 11: "el resto debe ser
# derivado, calculado, o no existir").
class LifecycleStatus:
    ACTIVE_TRIAL = "ACTIVE_TRIAL"
    ACTIVE_SUBSCRIPTION = "ACTIVE_SUBSCRIPTION"
    NO_EXPIRATION = "NO_EXPIRATION"
    EXPIRED = "EXPIRED"
    SUSPENDED_BY_ADMIN = "SUSPENDED_BY_ADMIN"


def is_trial_expired(client) -> bool:
    """
    True si el trial de `client` ya venció segun la fecha de HOY (zona
    horaria local, no UTC) -- independiente del valor actual de
    is_active (esta funcion solo mira la fecha).
    """
    if not client.on_trial:
        return False
    if not client.paid_until:
        return False
    return timezone.localdate() > client.paid_until


def compute_lifecycle_status(client) -> str:
    """
    Deriva el estado visible del tenant SIN modificar nada en BD.

    Reglas (en orden):
    1. Trial vencido (on_trial=True, paid_until en el pasado) -> EXPIRED,
       sin importar el valor actual de is_active (la fecha es la fuente
       de verdad, per Fase 16 -- "la fecha debe ser determinante").
    2. is_active=False y no corresponde a un trial vencido -> fue
       suspendido manualmente por un admin -> SUSPENDED_BY_ADMIN.
    3. on_trial=True, con paid_until vigente o sin definir -> ACTIVE_TRIAL.
    4. on_trial=False, con paid_until definido -> ACTIVE_SUBSCRIPTION
       (régimen fuera de trial -- reservado para un futuro modelo de
       facturación real; no se inventa lógica de cobro aquí).
    5. on_trial=False, sin paid_until -> NO_EXPIRATION (tenant sin
       límite de acceso definido -- preserva el comportamiento actual
       de los tenants existentes que nunca tuvieron trial).
    """
    if is_trial_expired(client):
        return LifecycleStatus.EXPIRED
    if not client.is_active:
        return LifecycleStatus.SUSPENDED_BY_ADMIN
    if client.on_trial:
        return LifecycleStatus.ACTIVE_TRIAL
    if client.paid_until:
        return LifecycleStatus.ACTIVE_SUBSCRIPTION
    return LifecycleStatus.NO_EXPIRATION


def trial_days_remaining(client) -> int | None:
    """Dias restantes de trial (puede ser negativo si ya vencio). None si
    no aplica (on_trial=False o paid_until no definido)."""
    if not client.on_trial or not client.paid_until:
        return None
    return (client.paid_until - timezone.localdate()).days


def reconcile_tenant_lifecycle(client, *, save: bool = True) -> bool:
    """
    Reconcilia el estado EFECTIVO (is_active) de `client` contra la
    fecha de expiracion real.

    Se puede llamar desde:
    - El middleware de resolucion de request (runtime, por cada request
      al tenant) -- garantiza que el bloqueo NO dependa de que Celery
      haya corrido (Fase 17/18).
    - La tarea periodica de Celery (apps/public/tenants/tasks.py) --
      refleja el estado en el admin aunque el tenant no reciba trafico.
    - Acciones administrativas explicitas (activar/reactivar/extender).

    Regla: SOLO desactiva por expiracion de trial (on_trial=True,
    paid_until vencido). NUNCA reactiva automaticamente un tenant
    suspendido manualmente por un admin (SUSPENDED_BY_ADMIN) -- eso
    requiere una accion administrativa explicita (Fase 26 -- "no debe
    simplemente is_active=true sin resolver el modelo de lifecycle").

    Retorna True si se modifico el estado (is_active paso de True a
    False), False si no hubo cambio.
    """
    if not is_trial_expired(client):
        return False
    if not client.is_active:
        # Ya estaba inactivo (ya expirado antes, o suspendido manualmente
        # -- en cualquier caso no hay nada que reconciliar).
        return False

    client.is_active = False
    if save:
        client.save(update_fields=["is_active"])
    logger.warning(
        "[LIFECYCLE] Trial expirado -- tenant desactivado automaticamente: "
        "schema=%s paid_until=%s hoy=%s",
        client.schema_name, client.paid_until, timezone.localdate(),
    )
    return True


def reconcile_all_tenants(*, exclude_public: bool = True) -> dict[str, Any]:
    """
    Reconcilia TODOS los tenants (usado por la tarea periodica de
    Celery). Retorna un resumen -- nunca falla silenciosamente por un
    tenant individual (un error en uno no debe abortar el resto).
    """
    from django_tenants.utils import get_public_schema_name

    from apps.public.tenants.models import Client

    qs = Client.objects.filter(on_trial=True, is_active=True, paid_until__isnull=False)
    if exclude_public:
        qs = qs.exclude(schema_name=get_public_schema_name())

    reconciled = []
    errors = []
    for client in qs.only("id", "schema_name", "on_trial", "paid_until", "is_active"):
        try:
            if reconcile_tenant_lifecycle(client):
                reconciled.append(client.schema_name)
        except Exception as exc:  # noqa: BLE001 -- un tenant no debe abortar el resto
            logger.error(
                "[LIFECYCLE] Error reconciliando tenant schema=%s: %s",
                client.schema_name, exc, exc_info=True,
            )
            errors.append({"schema_name": client.schema_name, "error": str(exc)})

    return {"reconciled": reconciled, "errors": errors, "checked": qs.count()}
