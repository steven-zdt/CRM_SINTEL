"""
Test de Penetración: Aislamiento de Rutas Públicas vs Privadas.

[WARNING] CRÍTICO: Este test valida que los tenants privados NO pueden acceder
a rutas exclusivas del esquema público (ej: /console/).

Escenarios de Ataque:
1. Ataque 1: Intentar GET a /console/ desde tenant privado -> 404 Not Found
2. Ataque 2: Intentar GET a /api/public/v1/ desde tenant privado -> 404 Not Found
3. Ataque 3: Intentar GET a /api/admin/v1/ desde tenant privado -> 404 Not Found
4. Control: Intentar GET a /dashboard/ desde tenant privado -> 200/302 (debe funcionar)

Arquitectura:
- Usa SintelTenantTestCase para configurar tenant privado
- Simula acceso real con HTTP_HOST configurado
- Valida que el router de URLs no conoce estas rutas (404, no 403)
"""
from django.test import Client
from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_public_schema_name
from rest_framework.test import APIClient
from rest_framework import status
from django.db import connection

from apps.public.tenants.models import Client as TenantClient, Domain, TenantMembership
from tests.tenant.base_test import SintelTenantTestCase

User = get_user_model()


class PublicRouteIsolationPenetrationTests(SintelTenantTestCase):
    """
    Tests de penetración para validar aislamiento de rutas públicas.
    
    [WARNING] OBJETIVO: Garantizar que rutas exclusivas del esquema público
    (como /console/) devuelvan 404 Not Found cuando se accede desde
    un tenant privado.
    
    [WARNING] REGLA DE ORO: Si devuelve 200, 302 o 403, significa que la ruta
    EXISTE en el tenant, lo cual es un ERROR DE SEGURIDAD.
    """
    
    def setUp(self):
        """
        Configuración inicial para cada test.
        
        SintelTenantTestCase ya configura:
        - self.tenant (tenant privado)
        - self.domain (dominio del tenant)
        - self.user (usuario admin del tenant)
        - self.client (cliente HTTP con HTTP_HOST configurado)
        """
        super().setUp()
        
        # Asegurar que estamos en el esquema del tenant privado
        connection.set_schema(self.tenant.schema_name)
    
    def test_console_route_returns_404_in_private_tenant(self):
        """
        Ataque 1: Intentar acceder a /console/ desde tenant privado.
        
        [WARNING] RESULTADO ESPERADO: 404 Not Found
        [WARNING] FALLO CRÍTICO: Si devuelve 200, 302 o 403, la ruta EXISTE en el tenant.
        """
        # Intentar acceder a /console/ desde tenant privado
        response = self.client.get('/console/')
        
        # [WARNING] VALIDACIÓN CRÍTICA: Debe devolver 404 (ruta no existe)
        self.assertEqual(
            response.status_code,
            404,
            "[ERROR] VULNERABILIDAD: /console/ existe en tenant privado. "
            "Debe devolver 404 Not Found, no 200/302/403."
        )
        
        # Verificar que NO es una redirección (302)
        self.assertNotEqual(
            response.status_code,
            302,
            "[ERROR] VULNERABILIDAD: /console/ redirige en tenant privado. "
            "Debe devolver 404 Not Found."
        )
        
        # Verificar que NO es un error de permisos (403)
        self.assertNotEqual(
            response.status_code,
            403,
            "[ERROR] VULNERABILIDAD: /console/ existe pero está protegida en tenant privado. "
            "Debe devolver 404 Not Found (la ruta no debe existir)."
        )
    
    def test_console_tenants_route_returns_404_in_private_tenant(self):
        """
        Ataque 1.1: Intentar acceder a /console/tenants/ desde tenant privado.
        
        [WARNING] RESULTADO ESPERADO: 404 Not Found
        """
        response = self.client.get('/console/tenants/')
        
        self.assertEqual(
            response.status_code,
            404,
            "[ERROR] VULNERABILIDAD: /console/tenants/ existe en tenant privado. "
            "Debe devolver 404 Not Found."
        )
    
    def test_public_api_route_returns_404_in_private_tenant(self):
        """
        Ataque 2: Intentar acceder a /api/public/v1/ desde tenant privado.
        
        [WARNING] RESULTADO ESPERADO: 404 Not Found
        """
        # Intentar acceder a API pública desde tenant privado
        response = self.client.get('/api/public/v1/users/')
        
        # [WARNING] VALIDACIÓN CRÍTICA: Debe devolver 404 (ruta no existe)
        self.assertEqual(
            response.status_code,
            404,
            "[ERROR] VULNERABILIDAD: /api/public/v1/ existe en tenant privado. "
            "Debe devolver 404 Not Found."
        )
    
    def test_admin_api_route_returns_404_in_private_tenant(self):
        """
        Ataque 3: Intentar acceder a /api/admin/v1/ desde tenant privado.
        
        [WARNING] RESULTADO ESPERADO: 404 Not Found
        """
        # Intentar acceder a API admin desde tenant privado
        response = self.client.get('/api/admin/v1/tenants/')
        
        # [WARNING] VALIDACIÓN CRÍTICA: Debe devolver 404 (ruta no existe)
        self.assertEqual(
            response.status_code,
            404,
            "[ERROR] VULNERABILIDAD: /api/admin/v1/ existe en tenant privado. "
            "Debe devolver 404 Not Found."
        )
    
    def test_control_dashboard_route_works_in_private_tenant(self):
        """
        Control: Verificar que /dashboard/ funciona en tenant privado.
        
        [WARNING] RESULTADO ESPERADO: 200 OK (si autenticado) o 302 Redirect (si no autenticado)
        Esto confirma que el tenant está activo y las rutas privadas funcionan.
        """
        # Acceder a /dashboard/ desde tenant privado (usuario autenticado)
        response = self.client.get('/dashboard/')
        
        # [WARNING] VALIDACIÓN: Debe funcionar (200 o 302, NO 404)
        self.assertIn(
            response.status_code,
            [200, 302],
            "[OK] Control: /dashboard/ debe funcionar en tenant privado. "
            "Si devuelve 404, hay un problema con el routing del tenant."
        )
        
        # Si es 200, verificar que el contenido es del dashboard
        if response.status_code == 200:
            self.assertNotEqual(
                len(response.content),
                0,
                "[OK] Control: /dashboard/ debe retornar contenido en tenant privado."
            )
    
    def test_control_landing_route_works_in_private_tenant(self):
        """
        Control: Verificar que / (landing) funciona en tenant privado.
        
        [WARNING] RESULTADO ESPERADO: 200 OK
        Esto confirma que el tenant está activo y las rutas privadas funcionan.
        """
        # Acceder a / desde tenant privado
        response = self.client.get('/')
        
        # [WARNING] VALIDACIÓN: Debe funcionar (200, NO 404)
        self.assertEqual(
            response.status_code,
            200,
            "[OK] Control: / (landing) debe funcionar en tenant privado. "
            "Si devuelve 404, hay un problema con el routing del tenant."
        )
    
    def test_control_tenant_api_route_works_in_private_tenant(self):
        """
        Control: Verificar que /api/v1/ funciona en tenant privado.
        
        [WARNING] RESULTADO ESPERADO: 200 OK o 401/403 (según autenticación)
        Esto confirma que las APIs del tenant funcionan correctamente.
        """
        # Acceder a API del tenant desde tenant privado
        response = self.api_client.get('/api/v1/empresa/empresas/')
        
        # [WARNING] VALIDACIÓN: Debe funcionar (200, 401, 403, NO 404)
        self.assertIn(
            response.status_code,
            [200, 401, 403],
            "[OK] Control: /api/v1/ debe funcionar en tenant privado. "
            "Si devuelve 404, hay un problema con el routing del tenant."
        )
    
    def test_console_route_with_authenticated_user_still_returns_404(self):
        """
        Ataque 4: Intentar acceder a /console/ con usuario autenticado en tenant privado.
        
        [WARNING] RESULTADO ESPERADO: 404 Not Found (incluso con usuario autenticado)
        [WARNING] IMPORTANTE: El usuario puede ser staff, pero la ruta NO debe existir en el tenant.
        """
        # Usuario ya está autenticado (self.client.force_login en setUp)
        response = self.client.get('/console/')
        
        # [WARNING] VALIDACIÓN CRÍTICA: Debe devolver 404 (ruta no existe)
        self.assertEqual(
            response.status_code,
            404,
            "[ERROR] VULNERABILIDAD: /console/ existe en tenant privado incluso con usuario autenticado. "
            "Debe devolver 404 Not Found (la ruta no debe existir en el tenant)."
        )
    
    def test_multiple_public_routes_return_404(self):
        """
        Ataque 5: Verificar múltiples rutas públicas devuelven 404.
        
        [WARNING] RESULTADO ESPERADO: Todas deben devolver 404 Not Found
        """
        public_routes = [
            '/console/',
            '/console/tenants/',
            '/console/impuestos/',
            '/api/public/v1/users/',
            '/api/admin/v1/tenants/',
            '/api/admin/v1/tenants/onboard/',
        ]
        
        for route in public_routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(
                    response.status_code,
                    404,
                    f"[ERROR] VULNERABILIDAD: {route} existe en tenant privado. "
                    "Debe devolver 404 Not Found."
                )
