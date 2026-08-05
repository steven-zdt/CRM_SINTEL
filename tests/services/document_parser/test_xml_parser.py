"""
Tests para parser XML (UBL 2.1) (FASE 9).

[WARNING] PRINCIPIOS:
- Parsear Invoice UBL 2.1
- Parsear CreditNote UBL 2.1
- Generar DTO unificado
- Incluir campo 'type'
"""

import pytest

from apps.services.document_parser.xml_parser.parser import parse_to_dto


class TestXMLParser:
    """Tests para parser XML."""

    def test_parse_invoice_ubl21(self):
        """Test: Parsear Invoice UBL 2.1."""
        xml_content = ("""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:ID>FAC001</cbc:ID>
    <cbc:IssueDate>2026-01-01</cbc:IssueDate>
    <cac:AccountingSupplierParty>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID>900123456-7</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>Empresa Test</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingSupplierParty>
    <cac:AccountingCustomerParty>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID>800987654-3</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>Cliente Test</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingCustomerParty>
    <cac:LegalMonetaryTotal>
        <cbc:LineExtensionAmount>1000.00</cbc:LineExtensionAmount>
        <cbc:TaxExclusiveAmount>1000.00</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount>1190.00</cbc:TaxInclusiveAmount>
        <cbc:PayableAmount>1190.00</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
</Invoice>""").encode("utf-8")

        dto = parse_to_dto(xml_content)

        assert dto["document_type"] == "invoice.ubl21"
        assert dto["type"] == "invoice"
        assert dto["numero"] == "FAC001"
        assert "identificadores" in dto
        assert "emisor" in dto
        assert "receptor" in dto
        assert "totales" in dto

    def test_parse_creditnote_ubl21(self):
        """Test: Parsear CreditNote UBL 2.1."""
        xml_content = ("""<?xml version="1.0" encoding="UTF-8"?>
<CreditNote xmlns="urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
            xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
            xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:ID>NC001</cbc:ID>
    <cbc:IssueDate>2026-01-01</cbc:IssueDate>
    <cac:DiscrepancyResponse>
        <cbc:Description>Anulación</cbc:Description>
    </cac:DiscrepancyResponse>
    <cac:AccountingSupplierParty>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID>900123456-7</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>Empresa Test</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingSupplierParty>
    <cac:AccountingCustomerParty>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID>800987654-3</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>Cliente Test</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingCustomerParty>
    <cac:LegalMonetaryTotal>
        <cbc:LineExtensionAmount>1000.00</cbc:LineExtensionAmount>
        <cbc:TaxExclusiveAmount>1000.00</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount>1190.00</cbc:TaxInclusiveAmount>
        <cbc:PayableAmount>1190.00</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
</CreditNote>""").encode("utf-8")

        dto = parse_to_dto(xml_content)

        assert dto["document_type"] == "creditnote.ubl21"
        assert dto["type"] == "creditnote"
        assert dto["numero"] == "NC001"
        assert "identificadores" in dto
        assert "emisor" in dto
        assert "receptor" in dto
        assert "totales" in dto

    def test_parse_invalid_xml(self):
        """Test: Manejar XML inválido."""
        invalid_xml = "<invalid>".encode("utf-8")
        with pytest.raises(Exception):  # Puede ser ValueError, XMLSyntaxError, etc.
            parse_to_dto(invalid_xml)
