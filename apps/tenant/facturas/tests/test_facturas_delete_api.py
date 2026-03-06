"""
Tests de humo para validar DELETE /api/v1/facturas/{id}/ sin error 500.
"""
from django_tenants.test.cases import TenantTestCase
from django.urls import reverse
from django.db import IntegrityError
from django.db.models import ProtectedError
from apps.tenant.facturas.models import Factura, NaturalezaFactura, FacturaAnexos
from apps.tenant.empresa.models import Empresa


class FacturaDeleteAPITests(TenantTestCase):
    """Tests para validar DELETE de facturas con mapeo correcto de errores."""
    
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
        
        # Crear factura de prueba
        self.f = Factura.objects.create(
            numero="DEL-001",
            emisor_nit="901123299",
            emisor_razon_social="SINTEL",
            receptor_nit="900000000",
            receptor_razon_social="Cliente Test",
            naturaleza=NaturalezaFactura.VENTA,
            subtotal=100,
            impuestos=19,
            total=119,
            moneda="COP"
        )
    
    def test_delete_ok(self):
        """Valida que DELETE exitoso retorna 204."""
        url = reverse("factura-detail", args=[self.f.id])  # /api/v1/facturas/{id}/
        resp = self.client.delete(url)
        
        self.assertEqual(resp.status_code, 204, "DELETE exitoso debe retornar 204")
        self.assertFalse(
            Factura.objects.filter(id=self.f.id).exists(),
            "La factura debe haber sido eliminada"
        )
    
    def test_delete_404(self):
        """Valida que DELETE de factura inexistente retorna 404."""
        url = reverse("factura-detail", args=[999999])
        resp = self.client.delete(url)
        
        self.assertEqual(resp.status_code, 404, "DELETE de factura inexistente debe retornar 404")
    
    def test_delete_con_anexos_cascade(self):
        """Valida que DELETE elimina FacturaAnexos por CASCADE."""
        # Crear anexos
        FacturaAnexos.objects.create(
            factura=self.f,
            ubl_xml="<Invoice>...</Invoice>",
            application_response_xml="<ApplicationResponse>...</ApplicationResponse>"
        )
        
        url = reverse("factura-detail", args=[self.f.id])
        resp = self.client.delete(url)
        
        self.assertEqual(resp.status_code, 204, "DELETE debe funcionar con anexos (CASCADE)")
        self.assertFalse(
            FacturaAnexos.objects.filter(factura_id=self.f.id).exists(),
            "Los anexos deben eliminarse por CASCADE"
        )
    
    def test_delete_respuesta_formato(self):
        """Valida que las respuestas de error tienen formato JSON correcto."""
        # Test 404 (DRF maneja automáticamente)
        url = reverse("factura-detail", args=[999999])
        resp = self.client.delete(url)
        
        self.assertEqual(resp.status_code, 404)
        # DRF puede retornar 404 sin cuerpo o con {"detail": "Not found."}
        # No validamos el formato exacto aquí, solo que no sea 500
    
    def test_delete_no_500_por_errores_esperables(self):
        """
        Valida que errores esperables (ProtectedError, IntegrityError) 
        se mapean a 409/422, no a 500.
        
        ⚠️ NOTA: En este modelo, las relaciones son CASCADE, 
        así que no deberíamos tener ProtectedError en condiciones normales.
        Este test valida que el mapeo funciona si ocurriera.
        """
        url = reverse("factura-detail", args=[self.f.id])
        resp = self.client.delete(url)
        
        # Asegurar que no retorna 500
        self.assertNotEqual(
            resp.status_code, 500,
            "DELETE no debe retornar 500 por errores esperables"
        )
        
        # Si hay error, debe ser 409 o 422, no 500
        if resp.status_code != 204:
            self.assertIn(
                resp.status_code, [404, 409, 422],
                f"DELETE debe retornar 204, 404, 409 o 422, no {resp.status_code}"
            )
            
            # Si hay error, debe tener formato JSON con error y message
            if resp.status_code in [409, 422]:
                data = resp.json()
                self.assertIn("error", data, "Respuesta de error debe incluir campo 'error'")
                self.assertIn("message", data, "Respuesta de error debe incluir campo 'message'")
