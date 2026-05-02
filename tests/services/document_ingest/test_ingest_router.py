"""
Tests para router de ingestión (FASE 9).

[WARNING] PRINCIPIOS:
- Routing por tipo de documento detectado
- Selección correcta de parser
- Manejo de tipos no soportados
"""
import pytest
from apps.services.document_ingest.router import route


class TestIngestRouter:
    """Tests para router de ingestión."""
    
    def test_route_xml(self):
        """Test: Enrutar XML a parser XML."""
        xml_content = b'<?xml version="1.0"?><Invoice></Invoice>'
        result = route(xml_content, filename="test.xml")
        
        assert "document_type" in result
        assert "dto" in result
        assert result["document_type"] == "invoice.ubl21" or "invoice" in result["document_type"]
    
    def test_route_unknown_type(self):
        """Test: Manejar tipo desconocido."""
        unknown_content = b'unknown content'
        with pytest.raises(ValueError, match="No se pudo detectar"):
            route(unknown_content, filename="unknown.xyz")
    
    def test_route_with_mime_type(self):
        """Test: Usar MIME type para routing."""
        content = b'<root></root>'
        result = route(content, filename="test.xml", mime_type="application/xml")
        
        assert "document_type" in result
        assert "dto" in result
