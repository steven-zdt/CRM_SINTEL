"""
Contrato de evento de dominio para integraciones externas (N8N-SINTEL-01,
Fase 8/11). Mismo principio que apps/services/document_intake/contracts.py:
este modulo NO conoce reglas de Factura/Venta/Compra -- solo la envoltura
generica del evento. Los dominios publican eventos, nunca lo contrario.
"""
from __future__ import annotations

import uuid as _uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class DomainEvent:
    """
    Evento de dominio saliente hacia integraciones externas (n8n).

    Fase 11 (idempotencia): `event_id` es el identificador real que el
    consumidor debe usar para detectar duplicados -- NUNCA el asunto de un
    correo, un timestamp, o un nombre de archivo.
    Fase 12 (multi-tenant): `tenant` viaja siempre en el evento; el
    consumidor (n8n) nunca elige el tenant, SINTEL lo fija al publicar.
    """
    event_type: str            # ej: "invoice.processed", "invoice.failed"
    tenant: str                 # schema_name real del tenant que origino el evento
    aggregate_type: str         # ej: "Factura", "Venta"
    aggregate_uuid: str         # uuid del registro de negocio afectado
    payload: dict[str, Any] = field(default_factory=dict)
    version: int = 1
    event_id: str = field(default_factory=lambda: str(_uuid.uuid4()))
    occurred_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
