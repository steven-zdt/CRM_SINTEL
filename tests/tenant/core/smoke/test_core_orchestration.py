"""
Smoke tests para orquestación Core (dashboard, mi-empresa, mi-perfil).

⚠️ POLÍTICA v2.30: Validar que Core orquesta correctamente los servicios de TENANT_APPS.
"""
from rest_framework import status
from tests.tenant.base_test import SintelTenantTestCase


class TestCoreOrchestration(SintelTenantTestCase):
    """Tests de humo para orquestación Core."""
    
    def test_dashboard_200_structure(self):
        """GET /api/v1/core/dashboard/ → 200 con estructura mínima esperada."""
        response = self.api_client.get('/api/v1/core/dashboard/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = response.json()
        
        # Estructura mínima esperada
        self.assertIn('tenant', data, "Falta clave 'tenant'")
        self.assertIn('user', data, "Falta clave 'user'")
        self.assertIn('empresa', data, "Falta clave 'empresa'")
        self.assertIn('facturas', data, "Falta clave 'facturas'")
        self.assertIn('contabilidad', data, "Falta clave 'contabilidad'")
        self.assertIn('perfil', data, "Falta clave 'perfil'")
        self.assertIn('branding', data, "Falta clave 'branding'")
        self.assertIn('redirect_url', data, "Falta clave 'redirect_url'")
        
        # Verificar estructura de secciones
        facturas = data['facturas']
        self.assertIn('total', facturas)
        self.assertIn('mes_actual', facturas)
        self.assertIsInstance(facturas['total'], int)
        
        contabilidad = data['contabilidad']
        self.assertIn('total_asientos', contabilidad)
        self.assertIsInstance(contabilidad['total_asientos'], int)
    
    def test_mi_empresa_200_coherente_ssoT(self):
        """GET /api/v1/core/mi-empresa/ → 200 con contenido coherente con SSoT de empresa."""
        response = self.api_client.get('/api/v1/core/mi-empresa/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = response.json()
        
        # Estructura esperada
        self.assertIn('empresa', data)
        self.assertIn('branding', data)
        
        empresa_data = data['empresa']
        # Verificar que tiene campos básicos (puede estar vacío si no hay empresa)
        self.assertIsInstance(empresa_data, dict)
        
        branding = data['branding']
        self.assertIn('nombre', branding)
        # El nombre debe venir de BD (tenant o empresa), no hardcode
        self.assertIsInstance(branding['nombre'], str)
        self.assertGreater(len(branding['nombre']), 0)
    
    def test_mi_perfil_200_tenant_aware(self):
        """GET /api/v1/core/mi-perfil/ → 200 con datos del usuario autenticado (tenant-aware)."""
        response = self.api_client.get('/api/v1/core/mi-perfil/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = response.json()
        
        # Estructura esperada
        self.assertIn('perfil', data)
        self.assertIn('user', data)
        
        user_data = data['user']
        self.assertIn('email', user_data)
        self.assertEqual(user_data['email'], self.user.email)
        
        perfil_data = data['perfil']
        # Verificar que tiene campos básicos
        self.assertIsInstance(perfil_data, dict)
    
    def test_dashboard_requires_authentication(self):
        """GET /api/v1/core/dashboard/ sin autenticación → 401/403."""
        from rest_framework.test import APIClient
        client = APIClient(HTTP_HOST=self.domain.domain)
        
        response = client.get('/api/v1/core/dashboard/')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_mi_empresa_requires_authentication(self):
        """GET /api/v1/core/mi-empresa/ sin autenticación → 401/403."""
        from rest_framework.test import APIClient
        client = APIClient(HTTP_HOST=self.domain.domain)
        
        response = client.get('/api/v1/core/mi-empresa/')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_mi_perfil_requires_authentication(self):
        """GET /api/v1/core/mi-perfil/ sin autenticación → 401/403."""
        from rest_framework.test import APIClient
        client = APIClient(HTTP_HOST=self.domain.domain)
        
        response = client.get('/api/v1/core/mi-perfil/')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
