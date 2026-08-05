"""
Tests para servicio de ingestión en modo preview (FASE 9).

[WARNING] PRINCIPIOS:
- Preview no persiste
- Retorna DTO completo
- Validaciones se ejecutan
"""

import pytest

from apps.services.document_ingest.ingest_service import ingest_document


class TestIngestServicePreview:
    """Tests para ingest_service en modo preview."""

    def test_preview_xml_invoice(self):
        """Test: Preview de XML Invoice no persiste."""
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
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
</Invoice>"""

        result, status_code = ingest_document(
            content=xml_content, filename="test.xml", preview=True
        )

        assert result["persisted"] is False
        assert "dto" in result
        assert "sha256" in result
        assert "metadata" in result
        assert status_code == 200

    def test_preview_invalid_document(self):
        """Test: Preview de documento inválido retorna error."""
        invalid_content = b"invalid content"

        result, status_code = ingest_document(
            content=invalid_content, filename="test.txt", preview=True
        )

        assert result["persisted"] is False
        assert status_code in (400, 422)
        assert "error" in result
