"""
Tests de humo para validar que listado no trae blobs y detalle sí (opcional).
"""
from django.urls import reverse

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, FacturaAnexos, NaturalezaFactura
from tests.tenant.base_test import SintelTenantTestCase


class PayloadsTests(SintelTenantTestCase):
    """Tests para validar payloads mínimos en lista y anexos en detalle."""
    
    def setUp(self):
        super().setUp()
        # Crear empresa del tenant (SSoT)
        Empresa.objects.create(
            razon_social="SINTEL",
            nit="901123299",
            dv="1",
            direccion="Calle 123",
            telefono="3001234567"
        )
        
        # Crear factura con anexos
        self.f = Factura.objects.create(
            numero="10020298",
            emisor_nit="900298074",
            emisor_razon_social="Proveedor Test",
            receptor_nit="901123299",
            receptor_razon_social="SINTEL",
            naturaleza=NaturalezaFactura.COMPRA,
            subtotal=10764,
            impuestos=2045.16,
            total=12809.16,
            moneda="COP"
        )
        FacturaAnexos.objects.create(
            factura=self.f,
            ubl_xml="<Invoice>...</Invoice>",
            application_response_xml="<ApplicationResponse>...</ApplicationResponse>"
        )
    
    def test_list_minima(self):
        """Valida que el listado incluye naturaleza pero NO incluye blobs."""
        url = reverse("factura-list")
        resp = self.client.get(url)
        
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        results = data.get("results", data)
        
        if results:
            row = results[0]
            # Validar que incluye naturaleza
            self.assertIn("naturaleza", row)
            self.assertEqual(row["naturaleza"], NaturalezaFactura.COMPRA)
            
            # Validar que NO incluye blobs
            self.assertNotIn("ubl_xml", row, "El listado NO debe incluir ubl_xml")
            self.assertNotIn("application_response_xml", row,
                           "El listado NO debe incluir application_response_xml")
    
    def test_detail_con_anexos(self):
        """Valida que el detalle reporta metadatos de anexos sin incluir blobs."""
        # F29-001: BaseTenantViewSet.lookup_field = "uuid", no PK entero.
        url = reverse("factura-detail", args=[self.f.uuid])
        resp = self.client.get(url)
        
        self.assertEqual(resp.status_code, 200)
        row = resp.json()
        
        # Contrato actual: metadatos y flags, no contenido XML pesado
        self.assertTrue(row.get("has_ubl_xml"), "El detalle debe reportar has_ubl_xml=true")
        self.assertTrue(row.get("has_application_response_xml"),
                "El detalle debe reportar has_application_response_xml=true")
        self.assertIn("anexos_meta", row)
        self.assertNotIn("ubl_xml", row)
        self.assertNotIn("application_response_xml", row)
        
        # Validar que la naturaleza está presente
        self.assertEqual(row.get("naturaleza"), NaturalezaFactura.COMPRA)
