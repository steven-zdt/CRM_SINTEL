"""
PurchaseDocumentHandler -- Compras como segundo consumidor del Document Intake
Service (FASE 23/24).

WARNING: ALCANCE DELIBERADO: este handler demuestra que Compras PUEDE
registrarse como consumidor sin tocar IMAP/ZIP/detector/pipeline/Celery (la
prueba de extensibilidad de FASE 24), y sin duplicar Factura ni Proveedor
(REGLA #1/#2/#3). NO implementa persistencia real todavia -- eso requiere
definir junto al dueno del dominio Compras la regla explicita de "cuando un
documento de compra genera una OrdenCompra/RecepcionCompra real" y si debe
disparar creacion de Inventario (la mision prohibe expresamente crear
Inventario automaticamente "sin regla explicita" -- esa regla no existe
todavia, inventarla aqui seria exceder el alcance minimo).

Por eso `handle()` retorna REQUIRES_REVIEW en vez de fingir un SUCCESS que
no persiste nada -- mismo principio de FASE 2 (nunca reportar exito falso)
aplicado a un handler nuevo, no solo al pipeline de mail original.
"""
from __future__ import annotations

from apps.services.document_intake.contracts import (
    ProcessingResult,
    ProcessingStatus,
    ReceivedDocument,
)

PURCHASE_DOCUMENT_TYPES = frozenset({"purchase_document"})


class PurchaseDocumentHandler:
    """Handler de Compras -- listo para registrar, pendiente de regla de negocio real."""

    def can_handle(self, document: ReceivedDocument) -> bool:
        doc_type = (document.document_type or "").split(".")[0].lower()
        return doc_type in PURCHASE_DOCUMENT_TYPES

    def handle(self, document: ReceivedDocument) -> ProcessingResult:
        return ProcessingResult(
            status=ProcessingStatus.REQUIRES_REVIEW,
            document_id=document.document_id,
            source=document.source,
            handler=type(self).__name__,
            domain="compras",
            warnings=[
                "purchase_document_handler_not_yet_implemented: "
                "requiere definir junto a Compras la regla real de persistencia "
                "(y si corresponde generacion de Inventario) antes de pasar a SUCCESS"
            ],
        )
