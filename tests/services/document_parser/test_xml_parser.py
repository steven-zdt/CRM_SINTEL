"""
Tests para parser XML (UBL 2.1) (FASE 9).

[WARNING] PRINCIPIOS:
- Parsear Invoice UBL 2.1
- Parsear CreditNote UBL 2.1
- Generar DTO unificado
- Incluir campo 'type'
"""

from decimal import Decimal

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

    def test_invoice_line_cantidad_y_precio_sin_punto_decimal_no_se_dividen_por_100(self):
        """
        Bug real (2026-09-18, reportado via "sincronizar factura -> Venta"):
        InvoicedQuantity="1" y PriceAmount="582992" (enteros validos UBL,
        SIN punto decimal -- muy comun, DIAN no lo exige) se persistian como
        cantidad=0.01 y valor_unitario=5829.92 -- ambos divididos por 100.

        Causa raiz: normalize_numeric_to_decimal_string() hacia
        value.replace('.', '') y LUEGO comprobaba '.' not in value (siempre
        True tras el replace) para decidir dividir por 100. Corregido:
        xml_parser/parser.py ya no usa esa funcion para valores UBL, usa
        _decimal_desde_xml() (parseo directo, sin heuristicas de miles --
        UBL/DIAN nunca usa separadores de miles).

        Este test reproduce el caso real EXACTO (mismos valores que la
        Factura FST391 que disparo el hallazgo): cantidad=1, PriceAmount=
        582992 (sin ".00"), IVA 19% con Percent="19.00" (CON punto, para
        confirmar que ese caso tambien sigue funcionando).
        """
        xml_content = ("""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:ID>FST391</cbc:ID>
    <cbc:IssueDate>2026-09-18</cbc:IssueDate>
    <cac:AccountingSupplierParty>
        <cac:Party>
            <cac:PartyIdentification><cbc:ID>901123299-1</cbc:ID></cac:PartyIdentification>
            <cac:PartyLegalEntity><cbc:RegistrationName>Sintel Technology</cbc:RegistrationName></cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingSupplierParty>
    <cac:AccountingCustomerParty>
        <cac:Party>
            <cac:PartyIdentification><cbc:ID>800987654-3</cbc:ID></cac:PartyIdentification>
            <cac:PartyLegalEntity><cbc:RegistrationName>Cliente Test</cbc:RegistrationName></cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingCustomerParty>
    <cac:LegalMonetaryTotal>
        <cbc:LineExtensionAmount currencyID="COP">582992.00</cbc:LineExtensionAmount>
        <cbc:TaxExclusiveAmount currencyID="COP">582992.00</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount currencyID="COP">693760.48</cbc:TaxInclusiveAmount>
        <cbc:PayableAmount currencyID="COP">693760.48</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
    <cac:InvoiceLine>
        <cbc:ID>1</cbc:ID>
        <cbc:Note>Reubicación de dispositivos de seguridad</cbc:Note>
        <cbc:InvoicedQuantity unitCode="ZZ">1</cbc:InvoicedQuantity>
        <cbc:LineExtensionAmount currencyID="COP">582992</cbc:LineExtensionAmount>
        <cac:TaxTotal>
            <cbc:TaxAmount currencyID="COP">110768.48</cbc:TaxAmount>
            <cac:TaxSubtotal>
                <cbc:TaxableAmount currencyID="COP">582992</cbc:TaxableAmount>
                <cbc:TaxAmount currencyID="COP">110768.48</cbc:TaxAmount>
                <cac:TaxCategory>
                    <cbc:Percent>19.00</cbc:Percent>
                    <cac:TaxScheme><cbc:ID>01</cbc:ID><cbc:Name>IVA</cbc:Name></cac:TaxScheme>
                </cac:TaxCategory>
            </cac:TaxSubtotal>
        </cac:TaxTotal>
        <cac:Item>
            <cbc:Description>Reubicación de dispositivos de seguridad</cbc:Description>
        </cac:Item>
        <cac:Price>
            <cbc:PriceAmount currencyID="COP">582992</cbc:PriceAmount>
            <cbc:BaseQuantity unitCode="ZZ">1</cbc:BaseQuantity>
        </cac:Price>
    </cac:InvoiceLine>
</Invoice>""").encode("utf-8")

        dto = parse_to_dto(xml_content)

        assert len(dto["items"]) == 1
        item = dto["items"][0]
        assert item["cantidad"] == Decimal("1")
        assert item["valor_unitario"] == Decimal("582992")
        assert item["porcentaje_iva"] == Decimal("19.00")
        assert item["subtotal"] == Decimal("582992")
        assert item["total"] == Decimal("693760.48")

        # Los totales de cabecera (que ya tenian punto decimal en el XML)
        # deben seguir siendo correctos -- no es una regresion de estos.
        assert dto["totales"]["subtotal"] == "582992.00"
        assert dto["totales"]["total"] == "693760.48"
