"""
Integracion de Facturas con el Document Intake Service (FASE 11).

register() conecta InvoiceHandler al dispatcher compartido. Se llama de
forma explicita (no via signals/AppConfig.ready() automatico) para mantener
"CERO SIGNALS" y dependencias explicitas, siguiendo la convencion del
proyecto.
"""
from __future__ import annotations


def register() -> None:
    from apps.services.document_intake.dispatcher import dispatcher
    from apps.tenant.facturas.document_intake.invoice_handler import InvoiceHandler

    handler = InvoiceHandler()
    for document_type in ("invoice", "creditnote", "debitnote"):
        dispatcher.register(document_type, handler)
