"""
Tests para parser CSV (FASE 9).

[WARNING] PRINCIPIOS:
- Leer CSV a DataFrame
- Detectar tipo de documento
- Generar DTO unificado
"""
import pytest
from apps.services.document_parser.csv_parser.parser import parse_to_dto


class TestCSVParser:
    """Tests para parser CSV."""
    
    def test_parse_csv_basic(self):
        """Test: Parsear CSV básico."""
        csv_content = b'''numero,fecha_emision,emisor_nit,emisor_razon_social,total
FAC001,2026-01-01,900123456-7,Empresa Test,1000.00'''
        
        dto = parse_to_dto(csv_content, filename="test.csv")
        
        assert "document_type" in dto
        assert "type" in dto
        assert "numero" in dto
        assert "fecha_emision" in dto
    
    @pytest.mark.skip(reason="Requiere implementación completa del parser CSV")
    def test_parse_csv_gasto(self):
        """Test: Parsear CSV de gasto."""
        # Este test requiere implementación completa del parser
        pass
