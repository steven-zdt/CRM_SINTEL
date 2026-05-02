"""
Pruebas de humo para detección automática de naturaleza (VENTA/COMPRA) en importación UBL.

# WARNING: MULTI-TENANT: Usa TenantTestCase de django-tenants para tests tenant-aware.
"""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django_tenants.test.cases import TenantTestCase

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura

# XML de ejemplo para VENTA (emisor == empresa del tenant)
XML_VENTA = b"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:ID>FST001</cbc:ID>
    <cbc:IssueDate>2026-01-15</cbc:IssueDate>
    <cbc:IssueTime>10:00:00</cbc:IssueTime>
    <cac:AccountingSupplierParty>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID schemeID="4">900123456</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>ACME Corp</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingSupplierParty>
    <cac:AccountingCustomerParty>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID schemeID="4">800765432</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>Cliente XYZ</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingCustomerParty>
    <cac:LegalMonetaryTotal>
        <cbc:TaxExclusiveAmount currencyID="COP">1000000.00</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount currencyID="COP">1190000.00</cbc:TaxInclusiveAmount>
        <cbc:PayableAmount currencyID="COP">1190000.00</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
</Invoice>"""

# XML de ejemplo para COMPRA (emisor != empresa del tenant)
XML_COMPRA = b"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:ID>FST002</cbc:ID>
    <cbc:IssueDate>2026-01-15</cbc:IssueDate>
    <cbc:IssueTime>10:00:00</cbc:IssueTime>
    <cac:AccountingSupplierParty>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID schemeID="4">800765432</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>Proveedor ABC</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingSupplierParty>
    <cac:AccountingCustomerParty>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID schemeID="4">900123456</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>ACME Corp</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingCustomerParty>
    <cac:LegalMonetaryTotal>
        <cbc:TaxExclusiveAmount currencyID="COP">500000.00</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount currencyID="COP">595000.00</cbc:TaxInclusiveAmount>
        <cbc:PayableAmount currencyID="COP">595000.00</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
</Invoice>"""


class NaturalezaImportTests(TenantTestCase):
    """Tests para detección automática de naturaleza en importación UBL."""
    
    def setUp(self):
        super().setUp()
        # Crear empresa del tenant (SSoT) con NIT que coincide con emisor en XML_VENTA
        self.empresa = Empresa.objects.create(
            razon_social="ACME Corp",
            nit="900123456",
            dv="1",
            direccion="Calle 123",
            telefono="1234567890"
        )
    
    def _post_upload(self, xml_bytes, preview=True):
        """Helper para hacer POST a upload-ubl."""
        # El router DRF genera el nombre como "factura-upload-ubl" (basename + action)
        url = reverse("factura-upload-ubl")
        f = SimpleUploadedFile("fact.xml", xml_bytes, content_type="text/xml")
        return self.client.post(
            f"{url}?preview={'true' if preview else 'false'}",
            {"file": f},
            format="multipart"
        )
    
    def test_preview_venta(self):
        """Test: Preview de XML con emisor == empresa debe retornar naturaleza=VENTA."""
        resp = self._post_upload(XML_VENTA, preview=True)
        self.assertEqual(resp.status_code, 200, f"Response: {resp.data}")
        self.assertTrue(resp.json().get("preview"))
        self.assertEqual(
            resp.json()["factura"]["naturaleza"],
            Factura.Naturaleza.VENTA,
            f"Esperado VENTA, obtenido: {resp.json()['factura'].get('naturaleza')}"
        )
    
    def test_preview_compra(self):
        """Test: Preview de XML con emisor != empresa debe retornar naturaleza=COMPRA."""
        resp = self._post_upload(XML_COMPRA, preview=True)
        self.assertEqual(resp.status_code, 200, f"Response: {resp.data}")
        self.assertEqual(
            resp.json()["factura"]["naturaleza"],
            Factura.Naturaleza.COMPRA,
            f"Esperado COMPRA, obtenido: {resp.json()['factura'].get('naturaleza')}"
        )
    
    def test_persistencia_asigna_naturaleza_venta(self):
        """Test: Persistencia de XML con emisor == empresa debe asignar naturaleza=VENTA."""
        resp = self._post_upload(XML_VENTA, preview=False)
        self.assertEqual(resp.status_code, 201, f"Response: {resp.data}")
        self.assertTrue(Factura.objects.exists())
        factura = Factura.objects.first()
        self.assertEqual(factura.naturaleza, Factura.Naturaleza.VENTA)
    
    def test_persistencia_asigna_naturaleza_compra(self):
        """Test: Persistencia de XML con emisor != empresa debe asignar naturaleza=COMPRA."""
        resp = self._post_upload(XML_COMPRA, preview=False)
        self.assertEqual(resp.status_code, 201, f"Response: {resp.data}")
        self.assertTrue(Factura.objects.exists())
        factura = Factura.objects.first()
        self.assertEqual(factura.naturaleza, Factura.Naturaleza.COMPRA)
    
    def test_ignora_naturaleza_del_cliente(self):
        """Test: La naturaleza enviada por el cliente es ignorada."""
        # Intentar enviar naturaleza=COMPRA para XML_VENTA (debería ser ignorado)
        url = reverse("factura-upload-ubl")
        f = SimpleUploadedFile("fact.xml", XML_VENTA, content_type="text/xml")
        resp = self.client.post(
            f"{url}?preview=true",
            {"file": f, "naturaleza": "COMPRA"},  # Cliente envía COMPRA
            format="multipart"
        )
        self.assertEqual(resp.status_code, 200)
        # Debe ser VENTA (calculado automáticamente), no COMPRA (ignorado)
        self.assertEqual(resp.json()["factura"]["naturaleza"], Factura.Naturaleza.VENTA)
