"""
Tests para parser Excel (XLS/XLSX) (FASE 9).

⚠️ PRINCIPIOS:
- Leer Excel a DataFrame
- Detectar tipo de documento
- Generar DTO unificado
"""
import pytest
from apps.services.document_parser.excel_parser.parser import parse_to_dto


class TestExcelParser:
    """Tests para parser Excel."""
    
    @pytest.mark.skip(reason="Requiere pandas/openpyxl y archivo Excel de prueba")
    def test_parse_xlsx_invoice(self):
        """Test: Parsear XLSX de factura."""
        # Este test requiere un Excel real o mock de pandas
        # Por ahora se marca como skip
        pass
    
    @pytest.mark.skip(reason="Requiere pandas/xlrd y archivo Excel de prueba")
    def test_parse_xls_invoice(self):
        """Test: Parsear XLS de factura."""
        # Este test requiere un Excel real o mock de pandas
        # Por ahora se marca como skip
        pass
