"""
Parser para documentos XML (UBL 2.1, etc.) (FASE 2.3).

⚠️ PRINCIPIOS:
- Migra pipeline UBL v2.34
- Soporta Invoice y CreditNote UBL 2.1
- Detecta documentos embebidos en AttachedDocument CDATA
- Retorna DTO JSON unificado
"""
from .parser import parse_to_dto

__all__ = ['parse_to_dto']