"""
Normalizers específicos para Facturas (v2.40).

⚠️ PRINCIPIOS:
- Normalizadores específicos para el módulo de facturas
- Reutiliza normalizers genéricos cuando es posible
- Agrega lógica específica para facturas cuando es necesario
"""
from typing import Optional, Dict, Any
# Reutilizar normalizers genéricos
from apps.services.document_parser.normalizers import (
    normalize_excel_to_dataframe,
    extract_text_from_pdf,
    sanitize_text,
    normalize_nit,
    normalize_currency,
    normalize_numeric_to_decimal_string,
    normalize_whitespace,
)

__all__ = [
    'normalize_excel_to_dataframe',
    'extract_text_from_pdf',
    'sanitize_text',
    'normalize_nit',
    'normalize_currency',
    'normalize_numeric_to_decimal_string',
    'normalize_whitespace',
]
