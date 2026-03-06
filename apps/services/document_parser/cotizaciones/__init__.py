"""
Parsers específicos para la app Cotizaciones (v2.40).

⚠️ PRINCIPIOS:
- Lógica independiente del parser genérico
- Parsers específicos para cotizaciones (Excel para catálogos)
- Normalizers y DTOs específicos para cotizaciones
- Extensible y mantenible
"""
from .excel_parser import parse_catalogo_to_dto

# Exportar normalizers y DTOs
from . import normalizers as cotizaciones_normalizers
from . import dto as cotizaciones_dto

__all__ = [
    'parse_catalogo_to_dto',
    'cotizaciones_normalizers',
    'cotizaciones_dto',
]
