"""
Contratos genericos del Document Intake Service (FASE 6-9, mision Mail Hub -> Document Intake).

WARNING: PRINCIPIO CENTRAL: este modulo NO conoce Factura/Venta/Compra/Cliente/
Proveedor/Inventario/Banco/Contabilidad/Nomina. Solo conoce documento/adjunto/
tipo documental/origen/contexto tenant -- las apps de dominio deciden que hacer
con el documento implementando DocumentHandler en su propio paquete.
"""
from __future__ import annotations

import enum
import uuid as _uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


class DocumentSource(str, enum.Enum):
    """Canal de origen del documento (FASE 25 -- el mismo contrato sirve a todos)."""
    EMAIL = "EMAIL"
    UPLOAD = "UPLOAD"
    API = "API"
    IMPORT = "IMPORT"


@dataclass(frozen=True)
class ReceivedDocument:
    """
    Envoltura generica de un documento recibido (FASE 6), independiente del
    canal de origen y del dominio que terminara consumiendolo.

    NO incluye factura_id/compra_id/cliente_id/proveedor_id ni CUFE
    obligatorio -- esos son conceptos de dominio, no de intake. `metadata`
    es la via de escape para datos que el handler de dominio necesita (ej:
    empresa_id resuelto por el canal de entrada) sin que este contrato los
    conozca por nombre.
    """
    tenant_schema: str
    source: DocumentSource
    content: bytes
    filename: str | None = None
    mime_type: str | None = None
    document_type: str | None = None  # se puebla en deteccion si no se conoce aun
    message_id: str | None = None      # id del correo/mensaje origen (canal EMAIL)
    attachment_id: str | None = None   # id del adjunto dentro del mensaje (canal EMAIL)
    sender: str | None = None
    received_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    document_id: str = field(default_factory=lambda: str(_uuid.uuid4()))


class ProcessingStatus(str, enum.Enum):
    """Resultado de procesar un ReceivedDocument (FASE 8)."""
    SUCCESS = "SUCCESS"
    DUPLICATE = "DUPLICATE"
    INVALID = "INVALID"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


@dataclass
class ProcessingResult:
    """Resultado estandar de dispatch/handle (FASE 8)."""
    status: ProcessingStatus
    document_id: str
    source: DocumentSource
    handler: str | None = None       # nombre del handler que proceso el documento
    domain: str | None = None        # dominio consumidor (ej: "facturas", "compras")
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status in (ProcessingStatus.SUCCESS, ProcessingStatus.DUPLICATE)


@runtime_checkable
class DocumentHandler(Protocol):
    """
    Contrato que cada dominio consumidor implementa (FASE 9).

    Cada handler vive en su propio dominio (ej:
    apps/tenant/facturas/document_intake/invoice_handler.py). El
    DocumentDispatcher NO conoce la logica interna de ningun handler --
    solo llama can_handle()/handle().
    """

    def can_handle(self, document: ReceivedDocument) -> bool:
        ...

    def handle(self, document: ReceivedDocument) -> ProcessingResult:
        ...
