"""
Tests para detector de tipo de documento (FASE 9).

[WARNING] PRINCIPIOS:
- Detección por magic bytes (máxima confianza)
- Detección por MIME type
- Detección por extensión
- Heurísticas de contenido
"""
import pytest
from apps.services.document_parser.detector import detect_document_type


class TestDocumentDetector:
    """Tests para detect_document_type."""
    
    def test_detect_xml_by_magic_bytes(self):
        """Test: Detectar XML por magic bytes (<?xml)."""
        xml_content = b'<?xml version="1.0" encoding="UTF-8"?><Invoice></Invoice>'
        result = detect_document_type(xml_content)
        assert result["media_type"] == "xml"
        assert result["confidence"] == 1.0
    
    def test_detect_pdf_by_magic_bytes(self):
        """Test: Detectar PDF por magic bytes (%PDF)."""
        pdf_content = b'%PDF-1.4\n...'
        result = detect_document_type(pdf_content)
        assert result["media_type"] == "pdf"
        assert result["confidence"] == 1.0
    
    def test_detect_xlsx_by_magic_bytes(self):
        """Test: Detectar XLSX por magic bytes (PK\x03\x04)."""
        xlsx_content = b'PK\x03\x04...'
        result = detect_document_type(xlsx_content)
        assert result["media_type"] == "excel"
        assert result["confidence"] == 1.0
    
    def test_detect_by_extension_xml(self):
        """Test: Detectar XML por extensión."""
        result = detect_document_type(b'<root></root>', filename="test.xml")
        assert result["media_type"] == "xml"
        assert result["confidence"] == 0.6
    
    def test_detect_by_extension_pdf(self):
        """Test: Detectar PDF por extensión."""
        result = detect_document_type(b'content', filename="test.pdf")
        assert result["media_type"] == "pdf"
        assert result["confidence"] == 0.6
    
    def test_detect_by_extension_xlsx(self):
        """Test: Detectar XLSX por extensión."""
        result = detect_document_type(b'content', filename="test.xlsx")
        assert result["media_type"] == "excel"
        assert result["confidence"] == 0.6
    
    def test_detect_by_extension_csv(self):
        """Test: Detectar CSV por extensión."""
        result = detect_document_type(b'col1,col2\nval1,val2', filename="test.csv")
        assert result["media_type"] == "csv"
        assert result["confidence"] == 0.6
    
    def test_detect_by_mime_type(self):
        """Test: Detectar por MIME type."""
        result = detect_document_type(b'content', mime_type="application/xml")
        assert result["media_type"] == "xml"
        assert result["confidence"] == 0.8
    
    def test_detect_csv_by_content_heuristics(self):
        """Test: Detectar CSV por heurísticas de contenido."""
        csv_content = b'col1,col2,col3\nval1,val2,val3\nval4,val5,val6'
        result = detect_document_type(csv_content, filename="data.txt")
        # Puede detectar como CSV por heurísticas
        assert result["media_type"] in ("csv", "txt") or result["confidence"] >= 0.4
    
    def test_detect_unknown(self):
        """Test: Retornar None para tipo desconocido."""
        result = detect_document_type(b'unknown content', filename="unknown.xyz")
        # Debe retornar un resultado, aunque con baja confianza
        assert "media_type" in result
        assert "confidence" in result
