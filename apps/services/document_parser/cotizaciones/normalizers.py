"""
Normalizers específicos para Cotizaciones (v2.40).

WARNING: PRINCIPIOS:
- Normalizadores específicos para el módulo de cotizaciones
- Reutiliza normalizers genéricos cuando es posible
- Agrega lógica específica para catálogos de productos cuando es necesario
"""
# Reutilizar normalizers genéricos
from apps.services.document_parser.normalizers import (
    SemanticMapper,
    normalize_excel_to_dataframe,
    normalize_whitespace,
    sanitize_text,
)

__all__ = [
    'normalize_excel_to_dataframe',
    'sanitize_text',
    'normalize_whitespace',
    'SemanticMapper',
]
