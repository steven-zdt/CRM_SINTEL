"""
Publicador de eventos de dominio hacia integraciones externas (N8N-SINTEL-01,
Fase 8). Deliberadamente NO es un signal de Django (regla del proyecto: cero
signals para logica de negocio/integracion) -- los dominios llaman a
`publish_event()` explicitamente, en el punto exacto donde la operacion de
negocio ya se completo con exito, nunca antes.
"""
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

from apps.services.integration_events.contracts import DomainEvent

logger = logging.getLogger("apps.services.integration_events")


def publish_event(
    *, event_type: str, tenant: str, aggregate_type: str, aggregate_uuid: str,
    payload: dict[str, Any] | None = None,
) -> DomainEvent:
    """
    Construye el DomainEvent y encola su entrega asincrona (Celery) --
    nunca bloquea la transaccion de negocio que lo origino. Si
    N8N_WEBHOOK_URL no esta configurada (entorno sin n8n), registra y no
    hace nada mas -- publicar un evento nunca debe romper la operacion de
    negocio que lo dispara.
    """
    event = DomainEvent(
        event_type=event_type, tenant=tenant, aggregate_type=aggregate_type,
        aggregate_uuid=str(aggregate_uuid), payload=payload or {},
    )

    webhook_url = getattr(settings, "N8N_WEBHOOK_URL", "") or ""
    if not webhook_url:
        logger.info(
            "integration_events.publish_skipped_no_webhook_url",
            extra={"event_type": event_type, "event_id": event.event_id, "tenant": tenant},
        )
        return event

    from apps.services.integration_events.tasks import send_webhook_event

    send_webhook_event.apply_async(kwargs={"event": event.to_dict()}, queue="default")
    logger.info(
        "integration_events.publish_enqueued",
        extra={
            "event_type": event_type, "event_id": event.event_id, "tenant": tenant,
            "aggregate_type": aggregate_type, "aggregate_uuid": aggregate_uuid,
        },
    )
    return event
