"""
Tests de humo para validar importación de XMLs pesados sin error 500.
"""
import textwrap

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, FacturaAnexos, NaturalezaFactura
from tests.tenant.base_test import SintelTenantTestCase

# XML pesado simulado (con bloques grandes de firma y AttachedDocument)
HEAVY_XML = textwrap.dedent("""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:ID>FST355</cbc:ID>
    <cbc:IssueDate>2025-01-15</cbc:IssueDate>
    <cbc:IssueTime>10:30:00</cbc:IssueTime>
    <cac:AccountingSupplierParty>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID>901123299</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyName>
                <cbc:Name>SINTEL TECNOLOGY SAS</cbc:Name>
            </cac:PartyName>
        </cac:Party>
    </cac:AccountingSupplierParty>
    <cac:AccountingCustomerParty>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID>901761387</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyName>
                <cbc:Name>Cliente Test</cbc:Name>
            </cac:PartyName>
        </cac:Party>
    </cac:AccountingCustomerParty>
    <cac:LegalMonetaryTotal>
        <cbc:TaxExclusiveAmount>190974.20</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount>3855769.10</cbc:TaxInclusiveAmount>
        <cbc:PayableAmount>3855769.10</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
    <cac:Signature>
        <cbc:ID>Signature1</cbc:ID>
        <cac:SignatoryParty>
            <cac:PartyIdentification>
                <cbc:ID>901123299</cbc:ID>
            </cac:PartyIdentification>
        </cac:SignatoryParty>
        <cac:DigitalSignatureAttachment>
            <cac:ExternalReference>
                <cbc:URI>#Signature1</cbc:URI>
            </cac:ExternalReference>
        </cac:DigitalSignatureAttachment>
    </cac:Signature>
    <!-- Bloque grande simulado (firma digital) -->
    <cac:AdditionalDocumentReference>
        <cbc:ID>1</cbc:ID>
        <cbc:DocumentType>AttachedDocument</cbc:DocumentType>
        <cac:Attachment>
            <cbc:EmbeddedDocumentBinaryObject mimeCode="text/xml" encodingCode="Base64">
                {base64_large_content}
            </cbc:EmbeddedDocumentBinaryObject>
        </cac:Attachment>
    </cac:AdditionalDocumentReference>
</Invoice>
""").format(
    base64_large_content="A" * 10000  # Simular contenido grande
).encode("utf-8")


class HeavyUBLTests(SintelTenantTestCase):
    """Tests para validar importación de XMLs pesados sin error 500."""
    
    def setUp(self):
        super().setUp()
        # Crear empresa del tenant (SSoT)
        Empresa.objects.create(
            razon_social="SINTEL TECNOLOGY SAS",
            nit="901123299",
            dv="1",
            direccion="Calle 123",
            telefono="3001234567"
        )
    
    def test_upload_heavy_ok(self):
        """Valida que XMLs pesados se importan correctamente (201 o 413 según umbral)."""
        url = reverse("factura-upload-ubl")
        f = SimpleUploadedFile("heavy.xml", HEAVY_XML, content_type="text/xml")
        
        resp = self.client.post(f"{url}?preview=false", {"file": f})
        
        # Esperado: 201 con persistencia y SIN 500
        # Si supera umbral, 413 (pero no 500)
        self.assertIn(resp.status_code, (201, 413), 
                     f"Status inesperado: {resp.status_code}. Respuesta: {resp.data}")
        
        if resp.status_code == 201:
            # Validar que la factura se creó
            self.assertTrue(Factura.objects.exists(), "La factura debería haberse creado")
            
            # Validar que los anexos se guardaron
            factura = Factura.objects.first()
            self.assertTrue(
                FacturaAnexos.objects.filter(factura=factura).exists(),
                "Los anexos deberían haberse guardado en FacturaAnexos"
            )
            
            # Validar que la naturaleza se calculó correctamente
            self.assertEqual(factura.naturaleza, NaturalezaFactura.VENTA,
                           "La naturaleza debería ser VENTA (emisor = empresa)")
    
    def test_list_no_incluye_blobs(self):
        """Valida que el listado NO incluye campos XML pesados."""
        # Crear factura con anexos
        factura = Factura.objects.create(
            numero="TEST001",
            emisor_nit="901123299",
            emisor_razon_social="SINTEL",
            receptor_nit="900298074",
            receptor_razon_social="Proveedor",
            naturaleza=NaturalezaFactura.VENTA,
            subtotal=1000,
            impuestos=190,
            total=1190,
            moneda="COP"
        )
        FacturaAnexos.objects.create(
            factura=factura,
            ubl_xml="<Invoice>...</Invoice>" * 1000,  # XML grande
            application_response_xml="<ApplicationResponse>...</ApplicationResponse>" * 1000
        )
        
        url = reverse("factura-list")
        resp = self.client.get(url)
        
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        results = data.get("results", data)
        
        # Validar que el listado NO incluye campos XML
        if results:
            row = results[0]
            self.assertIn("naturaleza", row)
            self.assertNotIn("ubl_xml", row, "El listado NO debe incluir ubl_xml")
            self.assertNotIn("application_response_xml", row, 
                           "El listado NO debe incluir application_response_xml")
    
    def test_detail_incluye_anexos(self):
        """Valida que el detalle SÍ incluye anexos bajo demanda."""
        # Crear factura con anexos
        factura = Factura.objects.create(
            numero="TEST002",
            emisor_nit="901123299",
            emisor_razon_social="SINTEL",
            receptor_nit="900298074",
            receptor_razon_social="Proveedor",
            naturaleza=NaturalezaFactura.VENTA,
            subtotal=1000,
            impuestos=190,
            total=1190,
            moneda="COP"
        )
        FacturaAnexos.objects.create(
            factura=factura,
            ubl_xml="<Invoice>XML completo</Invoice>",
            application_response_xml="<ApplicationResponse>Respuesta DIAN</ApplicationResponse>"
        )
        
        # F29-001: BaseTenantViewSet.lookup_field = "uuid", no PK entero.
        url = reverse("factura-detail", args=[factura.uuid])
        resp = self.client.get(url)
        
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Validar que el detalle SÍ incluye anexos
        self.assertIn("ubl_xml", data, "El detalle debe incluir ubl_xml")
        self.assertIn("application_response_xml", data, 
                     "El detalle debe incluir application_response_xml")
        self.assertEqual(data["ubl_xml"], "<Invoice>XML completo</Invoice>")
        self.assertEqual(data["application_response_xml"], "<ApplicationResponse>Respuesta DIAN</ApplicationResponse>")
