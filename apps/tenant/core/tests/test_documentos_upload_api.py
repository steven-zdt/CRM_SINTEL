"""
Tests para endpoint universal de documentos (FASE 8).

# WARNING: PRINCIPIOS:
- Tests multitenant: Verificar aislamiento por esquema
- API-First: Verificar respuestas JSON-only
- Preview mode: Verificar que preview=true no persiste
- Validación: Verificar códigos HTTP apropiados
"""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status

from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase

# URL real (config/settings.py, apps/tenant/core/api/urls.py): el endpoint
# universal de documentos vive bajo el gateway de facturas, no en
# /api/v1/documentos/upload/ como asumia este archivo originalmente.
UPLOAD_URL = '/api/v1/core/_apps/facturas/upload-document/'

# XML UBL minimo pero REAL (mismo que apps/tenant/facturas/tests/test_ingesta_ubl.py,
# probado contra el pipeline real): el XML original de este archivo (sin
# cac:InvoiceLine) era rechazado con 422 por el validador real
# (document_ingest_validation_failed) -- una factura sin ninguna linea no es
# un documento valido.
XML_VALIDO = b'''
<Invoice xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
  <cbc:ID>F001</cbc:ID>
  <cbc:UUID>1234567890ABCDEFGHIJKLMN</cbc:UUID>
  <cbc:IssueDate>2026-03-25</cbc:IssueDate>
  <cbc:IssueTime>12:00:00</cbc:IssueTime>
  <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyTaxScheme>
        <cbc:CompanyID>900123456</cbc:CompanyID>
      </cac:PartyTaxScheme>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>Proveedor S.A.S.</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyTaxScheme>
        <cbc:CompanyID>901999888</cbc:CompanyID>
      </cac:PartyTaxScheme>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>Mi Empresa S.A.S.</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:LegalMonetaryTotal>
    <cbc:TaxExclusiveAmount>100000.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount>119000.00</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount>119000.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:InvoiceLine>
    <cbc:ID>1</cbc:ID>
    <cbc:InvoicedQuantity unitCode="UND">1</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount>100000.00</cbc:LineExtensionAmount>
    <cac:Item>
      <cbc:Description>Producto de prueba</cbc:Description>
      <cac:SellersItemIdentification>
        <cbc:ID>PROD001</cbc:ID>
      </cac:SellersItemIdentification>
    </cac:Item>
    <cac:Price>
      <cbc:PriceAmount>100000.00</cbc:PriceAmount>
    </cac:Price>
  </cac:InvoiceLine>
</Invoice>
'''


class DocumentoUploadAPITests(SintelTenantTestCase):
    """Tests para endpoint universal de documentos (FASE 8).

    Hallazgo real (3 capas, confirmadas con evidencia -- traceback y
    print de diagnostico, no supuestas):
    1. El endpoint esta protegido por settings.FEATURE_UPLOAD_DOCUMENT_ENDPOINT
       (default False, factura_ubl_mixin.py linea 511) -- sin el
       override retorna 403 {"error":"endpoint_disabled"}.
       @override_settings(...) como DECORADOR DE CLASE no tiene efecto
       aqui (confirmado: un print del valor real de settings dentro
       del test seguia mostrando False con el decorador de clase
       puesto) -- TenantTestCase (django_tenants) no dispara el hook
       de clase de Django de la forma esperada. Por eso cada test usa
       `with override_settings(...):` alrededor de la request, que si
       aplica el override en el momento exacto (confirmado empiricamente
       via el mismo print).
    2. Este archivo usaba TenantTestCase (django_tenants) directo con
       un APIClient() plano -- su dominio auto-generado
       ('tenant.test.com') es rechazado por
       TenantSecurityAndURLConfMiddleware ('BLOQUEO PRIVADO: dominio
       no permitido, se exige *.sintel.net.co o dominio de
       desarrollo'). La base correcta para tests de apps/tenant/core/
       es SintelTenantTestCase (tests/tenant/base_test.py), que fija
       el dominio a '{schema}.sintel.local' (dominio de desarrollo
       aceptado) y expone self.client ya autenticado -- mismo patron
       que el resto de tests en este directorio
       (test_organizational_resolver.py, test_workspace_*.py).
    3. upload_document() exige metodo POST, y FacturaViewSet usa
       IsTenantAdminOrReadOnly, que resuelve el rol via
       TenantProfile.rol (tenant schema) -- NO via TenantMembership.rol
       (public schema, que SintelTenantTestCase.setup_membership() si
       crea). Sin un TenantProfile(rol='ADMIN') real, toda escritura
       cae en 403 aunque el usuario tenga membership admin. Se crea
       explicitamente en setUp() (junto con el singleton Empresa que
       TenantProfile requiere).
    """

    def setUp(self):
        """Configurar cliente y usuario de prueba."""
        super().setUp()
        # self.user / self.client (Django test Client, force_login'd,
        # HTTP_HOST correcto) ya vienen de SintelTenantTestCase.setUp().
        # DRF necesita format='multipart', asi que usamos el
        # api_client (APIClient) que la base tambien provee.
        self.client = self.api_client

        empresa = Empresa.objects.only('id').first()
        if not empresa:
            empresa = Empresa.objects.create(
                razon_social='EMPRESA TEST S.A.S.',
                nit='901234567',
                direccion='Direccion de prueba',
                telefono='3000000000',
            )
        TenantProfile.objects.get_or_create(
            user=self.user, defaults={'empresa': empresa, 'rol': 'ADMIN'}
        )

    def test_upload_missing_file(self):
        """Test: Error 400 si no se envía archivo."""
        with override_settings(FEATURE_UPLOAD_DOCUMENT_ENDPOINT=True):
            response = self.client.post(UPLOAD_URL)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())
        self.assertEqual(response.json()['error'], 'missing_file')

    def test_upload_preview_mode(self):
        """Test: Preview mode retorna DTO sin persistir."""
        file = SimpleUploadedFile("test.xml", XML_VALIDO, content_type="application/xml")

        with override_settings(FEATURE_UPLOAD_DOCUMENT_ENDPOINT=True):
            response = self.client.post(
                f'{UPLOAD_URL}?preview=true',
                {'file': file},
                format='multipart'
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data.get('persisted', True))
        self.assertIn('dto', data)
        self.assertIn('sha256', data)
        self.assertIn('metadata', data)

    def test_upload_invalid_file(self):
        """Test: Error 400 para archivo inválido."""
        file = SimpleUploadedFile("test.txt", b"invalid content", content_type="text/plain")

        with override_settings(FEATURE_UPLOAD_DOCUMENT_ENDPOINT=True):
            response = self.client.post(
                UPLOAD_URL,
                {'file': file},
                format='multipart'
            )

        # Puede ser 400 (parsing error) o 422 (validación)
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ])
        self.assertIn('error', response.json())

    def test_upload_with_tipo_hint(self):
        """Test: Parámetro tipo_hint se pasa al pipeline."""
        file = SimpleUploadedFile("test.xml", XML_VALIDO, content_type="application/xml")

        with override_settings(FEATURE_UPLOAD_DOCUMENT_ENDPOINT=True):
            response = self.client.post(
                f'{UPLOAD_URL}?preview=true&tipo=invoice',
                {'file': file},
                format='multipart'
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_structure(self):
        """Test: Respuesta tiene estructura correcta."""
        file = SimpleUploadedFile("test.xml", XML_VALIDO, content_type="application/xml")

        with override_settings(FEATURE_UPLOAD_DOCUMENT_ENDPOINT=True):
            response = self.client.post(
                f'{UPLOAD_URL}?preview=true',
                {'file': file},
                format='multipart'
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # Verificar estructura mínima
        self.assertIn('persisted', data)
        self.assertIn('dto', data)
        self.assertIn('sha256', data)
        self.assertIn('metadata', data)
        # Hallazgo real: el payload usa 'type'/'document_type', no 'tipo'
        # (verificado con la respuesta real: {'type': 'invoice',
        # 'document_type': 'invoice.ubl21', ...}).
        self.assertIn('type', data)

    def test_multitenant_isolation(self):
        """Test: Verificar aislamiento multitenant."""
        # Este test requiere múltiples tenants, se puede expandir más adelante
        # Por ahora, verificamos que el endpoint funciona en el tenant actual
        file = SimpleUploadedFile("test.xml", XML_VALIDO, content_type="application/xml")

        with override_settings(FEATURE_UPLOAD_DOCUMENT_ENDPOINT=True):
            response = self.client.post(
                f'{UPLOAD_URL}?preview=true',
                {'file': file},
                format='multipart'
            )

        # Debe procesar en el contexto del tenant actual
        self.assertEqual(response.status_code, status.HTTP_200_OK)
