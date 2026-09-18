"""
Entrega asincrona de eventos de dominio hacia n8n (N8N-SINTEL-01, Fase 8).
Mismo patron de retry que apps/services/maildigester/tasks.py -- solo
reintenta errores transitorios (red/timeout), nunca errores de programa.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging

import requests
from celery import shared_task
from django.conf import settings

logger = logging.getLogger("apps.services.integration_events")

_WEBHOOK_TIMEOUT_S = 10


def _firmar(body: bytes) -> str:
    """HMAC-SHA256 del body con N8N_WEBHOOK_SECRET (Fase 13 -- 'signed
    webhook'). n8n valida esta firma en el nodo Webhook antes de procesar
    -- nunca confia en el payload solo porque llego a la URL correcta."""
    secret = getattr(settings, "N8N_WEBHOOK_SECRET", "") or ""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


@shared_task(
    bind=True,
    name="apps.services.integration_events.tasks.send_webhook_event",
    autoretry_for=(ConnectionError, TimeoutError, requests.exceptions.RequestException),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_webhook_event(self, event: dict) -> None:
    webhook_url = getattr(settings, "N8N_WEBHOOK_URL", "") or ""
    if not webhook_url:
        logger.warning(
            "integration_events.send_skipped_no_webhook_url",
            extra={"event_id": event.get("event_id"), "event_type": event.get("event_type")},
        )
        return

    body = json.dumps(event, sort_keys=True).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Sintel-Signature": _firmar(body),
        "X-Sintel-Event-Id": event.get("event_id", ""),
        "X-Sintel-Event-Type": event.get("event_type", ""),
    }

    try:
        resp = requests.post(webhook_url, data=body, headers=headers, timeout=_WEBHOOK_TIMEOUT_S)
    except (ConnectionError, TimeoutError, requests.exceptions.RequestException):
        logger.warning(
            "integration_events.send_transient_error_will_retry",
            extra={
                "event_id": event.get("event_id"), "event_type": event.get("event_type"),
                "attempt": self.request.retries + 1,
            },
        )
        raise

    if resp.status_code >= 500:
        # Error transitorio del lado de n8n -- reintentar igual que un error de red.
        logger.warning(
            "integration_events.send_5xx_will_retry",
            extra={
                "event_id": event.get("event_id"), "status_code": resp.status_code,
                "attempt": self.request.retries + 1,
            },
        )
        raise requests.exceptions.RequestException(f"n8n webhook respondio {resp.status_code}")

    if resp.status_code >= 400:
        # Error del propio evento (4xx) -- reintentar no lo arregla. Log y
        # NO relanzar (Fase 17: nunca perder silenciosamente, pero tampoco
        # reintentar infinitamente algo que nunca va a funcionar).
        logger.error(
            "integration_events.send_rejected_by_n8n",
            extra={
                "event_id": event.get("event_id"), "event_type": event.get("event_type"),
                "status_code": resp.status_code, "response_body": resp.text[:500],
            },
        )
        return

    logger.info(
        "integration_events.send_success",
        extra={
            "event_id": event.get("event_id"), "event_type": event.get("event_type"),
            "status_code": resp.status_code,
        },
    )
