"""
Smoke test para verificar que el endpoint GET /api/v1/facturas/ responde 200 OK.

[WARNING] MULTI-TENANT: Este test verifica que el endpoint está correctamente registrado
en el TENANT_URLCONF y responde correctamente desde el dominio del tenant.

Referencia: SINTEL v2.30 - API-First JSON-only, TENANT_URLCONF para privados.
"""
from django.test import Client
from django_tenants.utils import schema_context
from apps.public.tenants.models import Client as TenantClient, Domain
from apps.tenant.facturas.models import Factura
from django.utils import timezone
from tests.tenant.base_test import SintelTenantTestCase


class TestFacturasEndpointSmoke(SintelTenantTestCase):
    """
    Smoke tests para verificar que el endpoint de facturas está disponible.
    
    [WARNING] OBJETIVO: Verificar que el router está correctamente configurado
    y que el endpoint responde 200 OK desde el dominio del tenant.
    """
    
    def test_listado_facturas_devuelve_200(self):
        """
        Verifica que GET /api/v1/facturas/ responde 200 OK desde el dominio del tenant.
        
        [WARNING] MULTI-TENANT: SintelTenantTestCase maneja automáticamente el tenant y el dominio.
        """
        # Crear factura de prueba en el esquema del tenant
        # (self.tenant ya está configurado por SintelTenantTestCase)
        factura = Factura.objects.create(
            numero="TEST-001",
            naturaleza="VENTA",
            estado="BORRADOR",
            fecha_emision=timezone.now(),
            moneda="COP",
            subtotal=1000,
            impuestos=190,
            total=1190,
            emisor_nit="123456789",
            emisor_razon_social="EMISOR TEST",
            receptor_nit="987654321",
            receptor_razon_social="RECEPTOR TEST",
        )
        
        # Hacer petición al endpoint usando el api_client autenticado
        url = "/api/v1/facturas/?ordering=-fecha_emision&page=1&page_size=10"
        response = self.api_client.get(url)
        
        # Verificar respuesta
        self.assertEqual(response.status_code, 200, (
            f"Expected 200 OK, got {response.status_code}. "
            f"Response: {response.content.decode('utf-8')[:500]}"
        ))
        
        # Verificar que la respuesta es JSON
        self.assertTrue(
            response.get("Content-Type", "").startswith("application/json"),
            f"Expected JSON response, got {response.get('Content-Type')}"
        )
        
        # Verificar estructura básica de respuesta paginada
        data = response.json()
        self.assertIsInstance(data, dict, "Response should be a JSON object")
        self.assertTrue(
            "results" in data or "count" in data,
            "Response should have pagination structure (results or count)"
        )
    
    def test_listado_facturas_vacio_devuelve_200(self):
        """
        Verifica que GET /api/v1/facturas/ responde 200 OK incluso sin facturas.
        
        [WARNING] MULTI-TENANT: Verifica que el endpoint existe aunque no haya datos.
        """
        # Hacer petición al endpoint (sin facturas)
        url = "/api/v1/facturas/?ordering=-fecha_emision&page=1&page_size=10"
        response = self.api_client.get(url)
        
        # Verificar respuesta (debe ser 200 incluso sin datos)
        self.assertEqual(response.status_code, 200, (
            f"Expected 200 OK even with no data, got {response.status_code}. "
            f"Response: {response.content.decode('utf-8')[:500]}"
        ))
        
        # Verificar que la respuesta es JSON
        self.assertTrue(
            response.get("Content-Type", "").startswith("application/json"),
            f"Expected JSON response, got {response.get('Content-Type')}"
        )
    
    def test_listado_facturas_404_en_dominio_publico(self):
        """
        Verifica que GET /api/v1/facturas/ devuelve 404 desde el dominio público.
        
        [WARNING] SEGURIDAD: Las facturas solo están disponibles en el ámbito del tenant.
        """
        # Cliente HTTP sin autenticación y sin tenant (simula dominio público)
        from django.test import Client
        client = Client()
        
        # Hacer petición al endpoint desde contexto público (sin HTTP_HOST de tenant)
        url = "/api/v1/facturas/"
        response = client.get(url)
        
        # Verificar que devuelve 404 (porque no existe en ROOT_URLCONF)
        # O 403 si hay algún middleware que bloquea
        self.assertIn(
            response.status_code, [404, 403],
            f"Expected 404 or 403 from public domain, got {response.status_code}. "
            f"This confirms that facturas endpoint is only available in TENANT_URLCONF."
        )
