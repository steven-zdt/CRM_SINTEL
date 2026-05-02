"""
DTOs específicos para Facturas (v2.40).

WARNING: PRINCIPIOS:
- DTOs específicos para el módulo de facturas
- Reutiliza DTOs genéricos cuando es posible
- Agrega estructuras específicas para facturas cuando es necesario
"""
from typing import Literal

# Reutilizar DTOs genéricos
# WARNING: v2.40: Los parsers de facturas retornan dicts, no objetos DocumentDTO
# Se importan los DTOs base para referencia, pero los parsers retornan dicts JSON
from apps.services.document_parser.dto import (
    IdentificadoresDTO,
    PartyDTO,
    TotalesDTO,
)

# Tipos de documentos específicos de facturas
FacturaDocumentType = Literal[
    "invoice.ubl21",
    "creditnote.ubl21",
]

__all__ = [
    'IdentificadoresDTO',
    'PartyDTO',
    'TotalesDTO',
    'FacturaDocumentType',
]
