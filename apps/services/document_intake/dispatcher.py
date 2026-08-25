"""
DocumentDispatcher -- FASE 10 (mision Mail Hub -> Document Intake).

Identifica el tipo documental de un ReceivedDocument, selecciona el
DocumentHandler de dominio registrado para ese tipo, y lo ejecuta. NO
contiene logica fiscal, contable, ni de ningun dominio especifico -- eso
vive exclusivamente en cada handler (apps/tenant/<dominio>/document_intake/).
"""
from __future__ import annotations

import logging

from apps.services.document_intake.contracts import (
    DocumentHandler,
    ProcessingResult,
    ProcessingStatus,
    ReceivedDocument,
)

logger = logging.getLogger("apps.services.document_intake")


class DocumentDispatcher:
    """Registro de handlers por tipo documental + ejecucion."""

    def __init__(self) -> None:
        self._handlers: dict[str, DocumentHandler] = {}

    def register(self, document_type: str, handler: DocumentHandler) -> None:
        self._handlers[document_type] = handler
        logger.info(
            "document_intake.handler_registered",
            extra={"document_type": document_type, "handler": type(handler).__name__},
        )

    def get_handler(self, document_type: str) -> DocumentHandler | None:
        return self._handlers.get(document_type)

    def registered_types(self) -> list[str]:
        return list(self._handlers.keys())

    def dispatch(self, document: ReceivedDocument) -> ProcessingResult:
        doc_type_base = (document.document_type or "").split(".")[0].lower()

        if not doc_type_base:
            logger.warning(
                "document_intake.missing_type",
                extra={"tenant_schema": document.tenant_schema, "source": document.source},
            )
            return ProcessingResult(
                status=ProcessingStatus.INVALID,
                document_id=document.document_id,
                source=document.source,
                errors=["missing_document_type"],
            )

        handler = self._handlers.get(doc_type_base)
        if handler is None or not handler.can_handle(document):
            logger.warning(
                "document_intake.no_handler",
                extra={
                    "document_type": doc_type_base,
                    "available": self.registered_types(),
                    "tenant_schema": document.tenant_schema,
                },
            )
            return ProcessingResult(
                status=ProcessingStatus.REQUIRES_REVIEW,
                document_id=document.document_id,
                source=document.source,
                errors=[f"no_handler_for_type:{doc_type_base}"],
            )

        logger.info(
            "document_intake.dispatching",
            extra={
                "document_type": doc_type_base,
                "handler": type(handler).__name__,
                "tenant_schema": document.tenant_schema,
                "source": document.source,
                "document_id": document.document_id,
            },
        )
        try:
            result = handler.handle(document)
        except Exception as exc:
            logger.error(
                "document_intake.handler_exception",
                exc_info=True,
                extra={
                    "document_type": doc_type_base,
                    "handler": type(handler).__name__,
                    "tenant_schema": document.tenant_schema,
                    "document_id": document.document_id,
                },
            )
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                document_id=document.document_id,
                source=document.source,
                handler=type(handler).__name__,
                errors=[str(exc)],
            )

        logger.info(
            "document_intake.dispatched",
            extra={
                "document_type": doc_type_base,
                "handler": type(handler).__name__,
                "status": result.status,
                "tenant_schema": document.tenant_schema,
                "document_id": document.document_id,
            },
        )
        return result


# Instancia modulo-level compartida: registro global de handlers, poblado
# lazily por cada dominio consumidor (ver apps/tenant/facturas/document_intake/).
# Un solo dispatcher para todo el proyecto -- evita que cada canal (mail/upload/
# api) tenga que conocer la lista de dominios consumidores.
dispatcher = DocumentDispatcher()
