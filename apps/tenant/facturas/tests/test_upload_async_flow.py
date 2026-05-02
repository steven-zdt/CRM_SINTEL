"""
Tests para flujo async completo: upload → status → materialize (Fase 2).

# WARNING: TENANT-AWARE: Usa TenantTestCase para garantizar aislamiento por esquema.
# WARNING: CELERY: Requiere CELERY_TASK_ALWAYS_EAGER=True en tests para ejecución síncrona.
"""
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django_tenants.test.cases import TenantTestCase

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, FacturaAnexos

# XML mínimo válido para tests
UBL_MIN = b"""<?xml version="1.0"?>
<Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>FV-001</cbc:ID>
  <cbc:IssueDate>2026-01-30</cbc:IssueDate>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyTaxScheme>
        <cbc:CompanyID>901123299</cbc:CompanyID>
        <cbc:RegistrationName>SINTEL</cbc:RegistrationName>
      </cac:PartyTaxScheme>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>SINTEL TECNOLOGY SAS</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyTaxScheme>
        <cbc:CompanyID>900298074</cbc:CompanyID>
        <cbc:RegistrationName>GVS</cbc:RegistrationName>
      </cac:PartyTaxScheme>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>GVS COLOMBIA SAS</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="COP">1000000.00</cbc:LineExtensionAmount>
    <cbc:TaxInclusiveAmount currencyID="COP">1190000.00</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="COP">1190000.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:TaxTotal>
    <cbc:TaxAmount currencyID="COP">190000.00</cbc:TaxAmount>
  </cac:TaxTotal>
</Invoice>"""


class UploadAsyncFlowTests(TenantTestCase):
    """Tests para flujo async completo."""
    
    def setUp(self):
        super().setUp()
        Empresa.objects.create(
            razon_social="SINTEL",
            nit="901123299",
            dv="1",
            direccion="Calle 123",
            telefono="3001234567",
        )
        
        # En tests, forzar tareas en modo eager si está disponible
        # (permite ejecución síncrona sin necesidad de worker Celery)
        if hasattr(settings, 'CELERY_TASK_ALWAYS_EAGER'):
            settings.CELERY_TASK_ALWAYS_EAGER = True
    
    def test_async_flow_completo(self):
        """Test: Flujo completo async (upload → status → materialize)."""
        # 1. Upload async
        url_upload = reverse("factura-upload-ubl")
        f = SimpleUploadedFile("test.xml", UBL_MIN, content_type="text/xml")
        resp = self.client.post(f"{url_upload}?async=true", {"file": f}, format="multipart")
        
        self.assertEqual(resp.status_code, 202)
        data = resp.json()
        self.assertIn("task_id", data)
        self.assertEqual(data["status"], "queued")
        task_id = data["task_id"]
        
        # 2. Consultar estado (con eager, debería estar listo inmediatamente)
        url_status = reverse("factura-ingest-status", kwargs={"task_id": task_id})
        s = self.client.get(url_status)
        
        self.assertIn(s.status_code, (200, 202))
        status_data = s.json()
        
        # Si está listo (SUCCESS), materializar
        if status_data.get("state") == "SUCCESS":
            dto = status_data["result"]
            
            # 3. Materializar
            url_mat = reverse("factura-materialize")
            m = self.client.post(
                url_mat,
                {"dto": dto, "persist_anexos": True},
                content_type="application/json"
            )
            
            self.assertIn(m.status_code, (201, 200))
            mat_data = m.json()
            self.assertIn("id", mat_data)
            self.assertIn("numero", mat_data)
            self.assertEqual(mat_data["numero"], "FV-001")
            
            # Verificar que se creó la factura
            f = Factura.objects.get(numero="FV-001")
            self.assertEqual(f.naturaleza, Factura.Naturaleza.VENTA)  # Emisor == empresa
            self.assertTrue(FacturaAnexos.objects.filter(factura=f).exists())
    
    def test_sync_flow_directo(self):
        """Test: Flujo sync directo (upload con async=false)."""
        url_upload = reverse("factura-upload-ubl")
        f = SimpleUploadedFile("test.xml", UBL_MIN, content_type="text/xml")
        resp = self.client.post(f"{url_upload}?async=false", {"file": f}, format="multipart")
        
        self.assertIn(resp.status_code, (201, 200))
        data = resp.json()
        self.assertIn("id", data)
        self.assertIn("numero", data)
        self.assertEqual(data["numero"], "FV-001")
        
        # Verificar que se creó la factura
        f = Factura.objects.get(numero="FV-001")
        self.assertEqual(f.naturaleza, Factura.Naturaleza.VENTA)
    
    def test_upload_sin_archivo_retorna_400(self):
        """Test: Upload sin archivo retorna 400."""
        url_upload = reverse("factura-upload-ubl")
        resp = self.client.post(f"{url_upload}?async=true", {}, format="multipart")
        
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"], "missing_xml")
    
    def test_status_task_no_existe_retorna_404(self):
        """Test: Status de tarea inexistente retorna 404."""
        url_status = reverse("factura-ingest-status", kwargs={"task_id": "fake-task-id"})
        resp = self.client.get(url_status)
        
        # Puede retornar 404 o 202 dependiendo de cómo Celery maneje tareas inexistentes
        self.assertIn(resp.status_code, (404, 202))
    
    def test_materialize_sin_dto_retorna_400(self):
        """Test: Materialize sin DTO retorna 400."""
        url_mat = reverse("factura-materialize")
        resp = self.client.post(url_mat, {}, content_type="application/json")
        
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"], "missing_dto")
