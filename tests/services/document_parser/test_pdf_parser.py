"""
Tests para parser PDF (FASE 9).

⚠️ PRINCIPIOS:
- Extraer texto de PDF
- Detectar tipo de documento (invoice/creditnote)
- Generar DTO unificado
"""
import pytest
from apps.services.document_parser.pdf_parser.parser import parse_to_dto


class TestPDFParser:
    """Tests para parser PDF."""
    
    @pytest.mark.skip(reason="Requiere pdfminer.six y PDF de prueba")
    def test_parse_pdf_invoice(self):
        """Test: Parsear PDF de factura."""
        # Este test requiere un PDF real o mock de pdfminer
        # Por ahora se marca como skip
        pass
    
    @pytest.mark.skip(reason="Requiere pdfminer.six y PDF de prueba")
    def test_parse_pdf_creditnote(self):
        """Test: Parsear PDF de nota crédito."""
        # Este test requiere un PDF real o mock de pdfminer
        # Por ahora se marca como skip
        pass
