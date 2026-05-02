"""
Tests contractuales para detectores de maildigester.

FASE 1: Valida firmas y tipos de las funciones de detección.
"""
import pytest
from apps.services.maildigester.detectors import (
    guess_file_kind,
    extract_xml_from_attacheddocument,
    is_ubl_invoice
)


def test_guess_file_kind_returns_literal():
    """
    Verifica que guess_file_kind retorna uno de los tipos soportados.
    """
    result = guess_file_kind("factura.xml", "application/xml", b"<?xml version='1.0'?>")
    
    assert result in ("xml", "zip", "rar", "7z", "other")


def test_guess_file_kind_detects_xml_by_extension():
    """
    Verifica detección de XML por extensión.
    """
    result = guess_file_kind("factura.xml", "application/octet-stream", b"")
    
    assert result == "xml"


def test_guess_file_kind_detects_zip_by_magic_bytes():
    """
    Verifica detección de ZIP por magic bytes.
    """
    result = guess_file_kind("archivo.bin", "application/octet-stream", b"PK\x03\x04...")
    
    assert result == "zip"


def test_extract_xml_from_attacheddocument_returns_list():
    """
    Verifica que extract_xml_from_attacheddocument retorna lista de strings.
    """
    xml_text = '<?xml version="1.0"?><Invoice>...</Invoice>'
    result = extract_xml_from_attacheddocument(xml_text)
    
    assert isinstance(result, list)
    # Todos los elementos deben ser strings
    for item in result:
        assert isinstance(item, str)


def test_is_ubl_invoice_detects_valid_ubl():
    """
    Verifica que is_ubl_invoice detecta XML UBL válido.
    """
    valid_ubl = '''<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>FAC-123</cbc:ID>
  <cbc:IssueDate>2024-01-15</cbc:IssueDate>
</Invoice>'''
    
    result = is_ubl_invoice(valid_ubl)
    
    assert result is True


def test_is_ubl_invoice_rejects_invalid_xml():
    """
    Verifica que is_ubl_invoice rechaza XML que no es UBL.
    """
    invalid_xml = '<?xml version="1.0"?><NotInvoice>...</NotInvoice>'
    
    result = is_ubl_invoice(invalid_xml)
    
    assert result is False


def test_is_ubl_invoice_handles_empty_string():
    """
    Verifica que is_ubl_invoice maneja strings vacíos.
    """
    result = is_ubl_invoice("")
    
    assert result is False


def test_is_ubl_invoice_handles_none():
    """
    Verifica que is_ubl_invoice maneja None.
    """
    result = is_ubl_invoice(None)  # type: ignore
    
    assert result is False
