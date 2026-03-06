"""
Parser para documentos de texto plano (TXT) (FASE 2.3).

⚠️ PRINCIPIOS:
- Heurísticas para extraer datos estructurados
- Retorna DTO JSON unificado según apps/services/document_parser/dto.py
"""
from .parser import parse_to_dto

__all__ = ['parse_to_dto']