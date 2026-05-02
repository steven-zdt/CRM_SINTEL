"""
Parser para documentos PDF (FASE 2.3).

WARNING: PRINCIPIOS:
- Extracción de texto usando pdfminer
- Regex + tablas DIAN para extraer datos estructurados
- Retorna DTO JSON unificado
"""
from .parser import parse_to_dto

__all__ = ['parse_to_dto']