"""
Tests para normalizadores de contenido (FASE 9).

⚠️ PRINCIPIOS:
- UTF-8 encoding
- Limpieza de acentos y caracteres ilegales
- Normalización de whitespace
- Sanitización de texto
- Conversión numérica a decimal-string
"""
import pytest
from apps.services.document_parser.normalizers import (
    normalize_encoding,
    normalize_whitespace,
    clean_accents,
    sanitize_text,
    normalize_numeric_to_decimal_string,
    normalize_nit,
    normalize_currency,
)


class TestNormalizers:
    """Tests para funciones de normalización."""
    
    def test_normalize_encoding_utf8(self):
        """Test: Normalizar encoding a UTF-8."""
        content = b'\xc3\xa1\xc3\xa9\xc3\xad'  # áéí en UTF-8
        result = normalize_encoding(content)
        assert isinstance(result, bytes)
        assert b'\xc3\xa1' in result
    
    def test_normalize_whitespace(self):
        """Test: Normalizar espacios en blanco."""
        text = "  texto   con    espacios  "
        result = normalize_whitespace(text)
        assert result == "texto con espacios"
    
    def test_normalize_whitespace_none(self):
        """Test: Normalizar whitespace con None."""
        result = normalize_whitespace(None)
        assert result is None
    
    def test_clean_accents(self):
        """Test: Limpiar acentos."""
        text = "áéíóúñ"
        result = clean_accents(text)
        assert result == "aeioun"
    
    def test_clean_accents_none(self):
        """Test: Limpiar acentos con None."""
        result = clean_accents(None)
        assert result is None
    
    def test_sanitize_text(self):
        """Test: Sanitizar texto."""
        text = "  Texto   con   espacios  y\n\nsaltos  "
        result = sanitize_text(text)
        assert "  " not in result
        assert "\n\n" not in result
    
    def test_sanitize_text_none(self):
        """Test: Sanitizar texto con None."""
        result = sanitize_text(None)
        assert result is None
    
    def test_normalize_numeric_to_decimal_string(self):
        """Test: Convertir numérico a decimal-string."""
        assert normalize_numeric_to_decimal_string(100) == "100.00"
        assert normalize_numeric_to_decimal_string(100.5) == "100.50"
        assert normalize_numeric_to_decimal_string("100.5") == "100.50"
        assert normalize_numeric_to_decimal_string(None) == "0.00"
        assert normalize_numeric_to_decimal_string("") == "0.00"
    
    def test_normalize_nit(self):
        """Test: Normalizar NIT."""
        assert normalize_nit("900123456-7") == "9001234567"
        assert normalize_nit("900.123.456-7") == "9001234567"
        assert normalize_nit(None) is None
    
    def test_normalize_currency(self):
        """Test: Normalizar moneda."""
        assert normalize_currency("COP") == "COP"
        assert normalize_currency("cop") == "COP"
        assert normalize_currency(None) == "COP"  # Default
