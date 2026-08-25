"""
InvoiceHandler -- primer consumidor real del Document Intake Service (FASE 11).

Traduce un ReceivedDocument generico al pipeline real de Facturas,
reutilizando integramente FacturaBusinessService: parsing via
document_ingest (SSoT, sin duplicar el parser UBL), persistencia,
_resolver_naturaleza(), vinculacion cliente/proveedor e idempotencia por
CUFE -- ninguno de esos mecanismos se reimplementa aqui (REGLA #1/#2 de la
mision).

Cubre factura (invoice), nota credito (creditnote) y nota debito (debitnote)
porque FacturaBusinessService.guardar_desde_dto() ya distingue internamente
entre ellas via is_credit_note -- un solo handler, no tres.
"""
from __future__ import annotations

from apps.services.document_intake.contracts import (
    ProcessingResult,
    ProcessingStatus,
    ReceivedDocument,
)

INVOICE_DOCUMENT_TYPES = frozenset({"invoice", "creditnote", "debitnote"})


class InvoiceHandler:
    """Handler de Facturas (factura / nota credito / nota debito)."""

    def can_handle(self, document: ReceivedDocument) -> bool:
        doc_type = (document.document_type or "").split(".")[0].lower()
        return doc_type in INVOICE_DOCUMENT_TYPES

    def handle(self, document: ReceivedDocument) -> ProcessingResult:
        from apps.tenant.facturas.services.business_service import FacturaBusinessService

        empresa_id = document.metadata.get("empresa_id")
        if not empresa_id:
            return ProcessingResult(
                status=ProcessingStatus.INVALID,
                document_id=document.document_id,
                source=document.source,
                handler=type(self).__name__,
                domain="facturas",
                errors=["missing_empresa_id"],
            )

        # WARNING: MAIL-16: si el productor del canal (ej. tasks.py) ya parseo el
        # documento para determinar document_type ANTES de dispatch (necesario para
        # el ruteo), puede adjuntar el dto resultante en metadata["dto"] para evitar
        # parsearlo dos veces. Si no viene, este handler sigue siendo autosuficiente
        # (ej. para canales UPLOAD/API que aun no preparsean) y lo parsea el mismo.
        dto = document.metadata.get("dto")
        if dto is None:
            from apps.services.document_ingest.ingest_service import ingest_document

            parsed, status_code = ingest_document(
                content=document.content,
                filename=document.filename,
                mime_type=document.mime_type or "application/xml",
                kind_hint="xml",
                preview=True,  # document_ingest SOLO parsea -- la persistencia es responsabilidad de este handler
                async_mode=False,
            )
            if status_code != 200 or parsed.get("error") or not parsed.get("dto"):
                return ProcessingResult(
                    status=ProcessingStatus.INVALID,
                    document_id=document.document_id,
                    source=document.source,
                    handler=type(self).__name__,
                    domain="facturas",
                    errors=[parsed.get("message", "parse_error")],
                )
            dto = parsed["dto"]

        content_bytes = document.content if isinstance(document.content, bytes) else document.content.encode("utf-8")
        xml_text = content_bytes.decode("utf-8")

        try:
            payload, code = FacturaBusinessService.guardar_desde_dto(
                dto=dto,
                xml_text=xml_text,
                file_bytes=content_bytes,
                file_type="xml",
                empresa_id=empresa_id,
            )
        except Exception as exc:
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                document_id=document.document_id,
                source=document.source,
                handler=type(self).__name__,
                domain="facturas",
                errors=[str(exc)],
            )

        if code == 201:
            status = ProcessingStatus.SUCCESS
        elif code == 200 and payload.get("created") is False:
            status = ProcessingStatus.DUPLICATE
        else:
            status = ProcessingStatus.FAILED

        return ProcessingResult(
            status=status,
            document_id=document.document_id,
            source=document.source,
            handler=type(self).__name__,
            domain="facturas",
            errors=[] if status != ProcessingStatus.FAILED else [payload.get("message", "error")],
            metadata={
                "numero": payload.get("numero"),
                "naturaleza": payload.get("naturaleza"),
                "cufe": payload.get("cufe") or payload.get("cude"),
            },
        )
