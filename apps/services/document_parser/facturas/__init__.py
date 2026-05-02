"""
Parsers específicos para la app Facturas (v2.40).

WARNING: PRINCIPIOS:
- Lógica independiente del parser genérico
- Parsers específicos para facturas (PDF, Excel, XML)
- Normalizers y DTOs específicos para facturas
- Extensible y mantenible
"""
from . import dto as facturas_dto

# Exportar normalizers y DTOs
from . import normalizers as facturas_normalizers
from .excel_parser import parse_factura_excel_to_dto
from .pdf_parser import parse_factura_pdf_to_dto

__all__ = [
    'parse_factura_excel_to_dto',
    'parse_factura_pdf_to_dto',
    'facturas_normalizers',
    'facturas_dto',
]
