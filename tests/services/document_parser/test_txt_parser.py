"""
Tests para parser TXT (FASE 9).

[WARNING] PRINCIPIOS:
- Extraer texto
- Detectar tipo de documento
- Generar DTO unificado
"""

import pytest

from apps.services.document_parser.txt_parser.parser import parse_to_dto


class TestTXTParser:
    """Tests para parser TXT."""

    def test_parse_txt_basic(self):
        """Test: Parsear TXT básico."""
        txt_content = b"""FACTURA
Numero: FAC001
Fecha: 2026-01-01
Total: 1000.00"""

        dto = parse_to_dto(txt_content, filename="test.txt")

        assert "document_type" in dto
        assert "type" in dto
        assert "numero" in dto or dto.get("numero") == ""
