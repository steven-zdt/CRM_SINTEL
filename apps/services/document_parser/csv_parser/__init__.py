"""
Parser para documentos CSV (FASE 2.3).

⚠️ PRINCIPIOS:
- Convierte CSV a DataFrame normalizado
- DataFrame → DTO JSON unificado
- Retorna DTO según apps/services/document_parser/dto.py
"""
from .parser import parse_to_dto

__all__ = ['parse_to_dto']