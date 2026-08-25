"""
Integracion de Compras con el Document Intake Service (FASE 23/24).

register() conecta PurchaseDocumentHandler al dispatcher compartido,
demostrando que agregar un segundo dominio consumidor no requiere tocar
IMAP/ZIP/detector/pipeline/Celery ni el handler de Facturas.
"""
from __future__ import annotations


def register() -> None:
    from apps.services.document_intake.dispatcher import dispatcher
    from apps.tenant.compras.document_intake.purchase_handler import PurchaseDocumentHandler

    dispatcher.register("purchase_document", PurchaseDocumentHandler())
