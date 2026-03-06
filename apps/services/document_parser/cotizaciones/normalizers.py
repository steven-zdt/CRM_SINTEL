"""
Normalizers específicos para Cotizaciones (v2.40).

⚠️ PRINCIPIOS:
- Normalizadores específicos para el módulo de cotizaciones
- Reutiliza normalizers genéricos cuando es posible
- Agrega lógica específica para catálogos de productos cuando es necesario
"""
from typing import Optional, Dict, Any
# Reutilizar normalizers genéricos
from apps.services.document_parser.normalizers import (
    normalize_excel_to_dataframe,
    sanitize_text,
    normalize_whitespace,
    SemanticMapper,
)

__all__ = [
    'normalize_excel_to_dataframe',
    'sanitize_text',
    'normalize_whitespace',
    'SemanticMapper',
]
