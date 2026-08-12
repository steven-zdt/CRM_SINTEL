"""
Tests tenant-aware para Fase 4: Detalle de Factura + Anexos bajo demanda.

# WARNING: VALIDACIONES:
- Detalle retorna metadatos de anexos (no contenido)
- Acciones detail para XML retornan HttpResponse con Content-Type correcto
- Tamaños y tipos de contenido correctos
- 200/204/404 esperados según existencia de anexos
"""
from django.urls import reverse
from django.utils import timezone

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, FacturaAnexos
from tests.tenant.base_test import SintelTenantTestCase

# F29-001: BaseTenantViewSet.lookup_field = "uuid" -- las URLs de
# detalle/acciones de Factura esperan el UUID, no el PK entero. Este
# archivo pasaba `self.f.id` (PK) donde el ViewSet espera `.uuid`; antes
# de F28 esto quedaba oculto detras de un NoReverseMatch previo (causa no
# relacionada), asi que nunca se habia llegado a ejercitar esta parte.


class FacturaDetailAnexosAPITests(SintelTenantTestCase):
    """Tests para detalle de factura y anexos XML."""
    
    def setUp(self):
        super().setUp()
        Empresa.objects.create(
            razon_social="SINTEL",
            nit="901123299",
            dv="1",
            direccion="Calle 123",
            telefono="3001234567",
        )
        self.f = Factura.objects.create(
            numero="DET-001",
            prefijo="DET",
            consecutivo=1,
            fecha_emision=timezone.now(),
            emisor_nit="900298074",
            receptor_nit="901123299",
            naturaleza=Factura.Naturaleza.COMPRA,
            subtotal=100,
            impuestos=19,
            total=119,
            moneda="COP"
        )
        FacturaAnexos.objects.create(
            factura=self.f,
            ubl_xml="<Invoice xmlns=\"urn:oasis:names:specification:ubl:schema:xsd:Invoice-2\"><cbc:ID>DET-001</cbc:ID></Invoice>",
            application_response_xml="<ApplicationResponse xmlns=\"urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2\"><cbc:ResponseCode>OK</cbc:ResponseCode></ApplicationResponse>"
        )
    
    def test_retrieve_detail_has_meta(self):
        """Test: Detalle retorna metadatos de anexos sin contenido XML."""
        url = reverse("factura-detail", args=[self.f.uuid])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        j = r.json()

        # Verificar que tiene metadatos
        self.assertTrue(j["has_ubl_xml"])
        self.assertTrue(j["has_application_response_xml"])
        self.assertGreater(j["anexos_meta"]["ubl_size"], 0)
        self.assertGreater(j["anexos_meta"]["app_response_size"], 0)
        
        # Verificar que NO incluye el contenido XML
        self.assertNotIn("ubl_xml", j)
        self.assertNotIn("application_response_xml", j)
    
    def test_get_ubl_xml(self):
        """Test: GET /xml/ retorna XML con Content-Type correcto."""
        url = reverse("factura-xml-ubl", args=[self.f.uuid])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertIn("application/xml", r["Content-Type"])
        self.assertIn("charset=utf-8", r["Content-Type"])
        self.assertIn("<Invoice", r.content.decode("utf-8"))
        self.assertIn("X-Content-Type-Options", r)
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")
    
    def test_get_app_response(self):
        """Test: GET /app-response/ retorna XML con Content-Type correcto."""
        url = reverse("factura-xml-app-response", args=[self.f.uuid])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertIn("application/xml", r["Content-Type"])
        self.assertIn("charset=utf-8", r["Content-Type"])
        self.assertIn("<ApplicationResponse", r.content.decode("utf-8"))
        self.assertIn("X-Content-Type-Options", r)
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")
    
    def test_get_ubl_xml_sin_anexos(self):
        """Test: GET /xml/ retorna 204 si no hay anexos."""
        f2 = Factura.objects.create(
            numero="DET-002",
            prefijo="DET",
            consecutivo=2,
            fecha_emision=timezone.now(),
            emisor_nit="900298074",
            receptor_nit="901123299",
            naturaleza=Factura.Naturaleza.COMPRA,
            subtotal=100,
            impuestos=19,
            total=119,
            moneda="COP"
        )
        # No crear FacturaAnexos
        
        url = reverse("factura-xml-ubl", args=[f2.uuid])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 204)
        j = r.json()
        self.assertEqual(j["error"], "no_content")
    
    def test_get_app_response_sin_contenido(self):
        """Test: GET /app-response/ retorna 204 si no hay ApplicationResponse."""
        f3 = Factura.objects.create(
            numero="DET-003",
            prefijo="DET",
            consecutivo=3,
            fecha_emision=timezone.now(),
            emisor_nit="900298074",
            receptor_nit="901123299",
            naturaleza=Factura.Naturaleza.COMPRA,
            subtotal=100,
            impuestos=19,
            total=119,
            moneda="COP"
        )
        FacturaAnexos.objects.create(
            factura=f3,
            ubl_xml="<Invoice/>",
            application_response_xml=None  # Sin ApplicationResponse
        )
        
        url = reverse("factura-xml-app-response", args=[f3.uuid])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 204)
        j = r.json()
        self.assertEqual(j["error"], "no_content")
    
    def test_get_ubl_xml_404(self):
        """Test: GET /xml/ retorna 404 si la factura no existe."""
        url = reverse("factura-xml-ubl", args=[999999])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)
