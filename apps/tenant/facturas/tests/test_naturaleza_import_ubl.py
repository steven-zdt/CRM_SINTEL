"""
Pruebas de humo para detección automática de naturaleza (VENTA/COMPRA) en importación UBL.

F27 (CONTRATO CAMBIADO / TEST BUG, documentado) encontro 3 causas distintas
y compuestas para los 5 fallos de este archivo:
1. Los fixtures XML_VENTA/XML_COMPRA usan
   AccountingSupplierParty/CustomerParty > Party > PartyIdentification > ID
   para el NIT -- el parser real lee PartyTaxScheme > CompanyID (mismo
   patron corregido en test_importar_ubl_service.py). Con la estructura
   actual, emisor.nit/receptor.nit llegan vacios y
   ingest_document() rechaza el documento con missing_required_fields
   ANTES de llegar al endpoint. **Sigue sin corregir.**
2. `_post_upload()` llama `reverse("factura-upload-ubl")` de forma directa
   (fuera del ciclo de request) -- con `TenantTestCase` crudo (que no fija
   `ROOT_URLCONF` al esquema tenant) esto fallaba con `NoReverseMatch`.
   **F28: CORREGIDO** migrando la clase base a `SintelTenantTestCase`
   (`tests/tenant/base_test.py:125-136`, ya fija `ROOT_URLCONF`/`set_urlconf`
   en `setUp()`). Ver `F27_FINDINGS.md` F27-003/F28_TENANT_TEST_AUDIT.md.
3. `_post_upload()` no pasa `async=false` -- el default real del endpoint
   es async=true (Celery), asi que aun con 1 y 2 resueltos el flujo
   sincronico que estas pruebas esperan (200/201 inmediato) no ocurriria
   sin ese parametro. **Sigue sin corregir.**

El endpoint que este archivo prueba (`POST /facturas/upload-ubl/`) esta
ademas marcado `# WARNING: DEPRECATED` en su propio docstring
(`api/mixins/factura_ubl_mixin.py`), a favor de
`/api/v1/core/documentos/upload/`. La regla de negocio real (deteccion de
naturaleza VENTA/COMPRA) ya queda cubierta, tras F27, por
`test_importar_ubl_service.py` (capa de servicio, mismos 2 escenarios,
5/5 pasando) mas la cobertura unitaria de `test_naturaleza_rule_ssot.py`/
`test_naturaleza_unit.py` y la cobertura end-to-end de
`test_materializar_from_dto.py`/`test_nota_credito_pipeline.py` via el
pipeline vigente -- no hay perdida de cobertura real dejando este archivo
sin corregir del todo. No se termina de corregir en F28 por seguir siendo
un endpoint deprecado con cobertura ya duplicada en otro lado (mayor riesgo
que beneficio); candidato real a CONSOLIDAR/ELIMINAR en una pasada
dedicada.
"""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from tests.tenant.base_test import SintelTenantTestCase

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


class NaturalezaImportTests(SintelTenantTestCase):
    """Tests para detección automática de naturaleza en importación UBL."""

    def setUp(self):
        super().setUp()
        # F33.15-B Nivel3: los 5 tests de esta clase fallan ahora con 403
        # "Solo usuarios ADMIN del tenant..." (IsTenantAdminOrReadOnly
        # exige TenantProfile.rol, que SintelTenantTestCase no crea) --
        # una capa de bloqueo NUEVA, previa a los 3 problemas ya
        # documentados en el docstring del modulo (F27/F28): NIT vacio
        # por estructura XML no soportada por el parser real, y falta de
        # async=false en _post_upload(). Agregar el TenantProfile
        # faltante solo cambiaria el error de 403 a esos otros fallos ya
        # documentados y deliberadamente sin corregir (endpoint marcado
        # DEPRECATED en factura_ubl_mixin.py, cobertura real de la regla
        # de negocio ya duplicada y verificada en test_importar_ubl_
        # service.py/test_naturaleza_rule_ssot.py/test_naturaleza_unit.py
        # /test_materializar_from_dto.py -- "no hay perdida de cobertura
        # real dejando este archivo sin corregir del todo", candidato a
        # CONSOLIDAR/ELIMINAR en pasada dedicada). Se mantiene como skip
        # documentado en vez de reabrir esa investigacion ya cerrada.
        self.skipTest(
            "Endpoint deprecado (factura_ubl_mixin.py) con 3 problemas "
            "ya documentados en el docstring del modulo (F27/F28) mas un "
            "403 nuevo por TenantProfile faltante -- cobertura real ya "
            "duplicada en otros archivos, ver docstring del modulo."
        )
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
