"""
Pruebas de humo para el Link Registry (anti "link rot").

⚠️ POLÍTICA:
- Verifica que el Link Registry retorne rutas válidas
- Verifica que cada ruta API/UI no retorne 404
"""
from tests.tenant.base_test import SintelTenantTestCase
from rest_framework import status


class TestLinksRegistry(SintelTenantTestCase):
    """
    Pruebas de humo para /api/v1/core/links/
    """
    
    def test_links_registry_returns_200(self):
        """Verifica que el Link Registry retorne 200."""
        self.client.force_login(self.user)
        
        response = self.client.get(
            '/api/v1/core/links/',
            HTTP_HOST=f'{self.tenant.schema_name}.sintel.com'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Verificar estructura básica
        self.assertIsInstance(data, dict)
    
    def test_links_registry_structure(self):
        """Verifica la estructura del Link Registry."""
        self.client.force_login(self.user)
        
        response = self.client.get(
            '/api/v1/core/links/',
            HTTP_HOST=f'{self.tenant.schema_name}.sintel.com'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Verificar que cada app tiene api y ui
        expected_apps = ['empresa', 'facturas', 'contabilidad', 'perfil', 'dashboard', 'core']
        
        for app in expected_apps:
            self.assertIn(app, data, f"Link Registry debe incluir '{app}'")
            if app in data:
                self.assertIn('api', data[app], f"Link Registry para '{app}' debe incluir 'api'")
                self.assertIn('ui', data[app], f"Link Registry para '{app}' debe incluir 'ui'")
    
    def test_links_registry_no_404(self):
        """Verifica que las rutas del Link Registry no retornen 404."""
        self.client.force_login(self.user)
        
        response = self.client.get(
            '/api/v1/core/links/',
            HTTP_HOST=f'{self.tenant.schema_name}.sintel.com'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Verificar que cada ruta API no retorne 404
        for app, links in data.items():
            if 'api' in links:
                api_url = links['api']
                # Hacer GET a la ruta API
                api_response = self.client.get(
                    api_url,
                    HTTP_HOST=f'{self.tenant.schema_name}.sintel.com'
                )
                # Puede ser 200, 204, 401, 403, 405, pero NO 404
                self.assertNotEqual(api_response.status_code, status.HTTP_404_NOT_FOUND,
                                  f"Ruta API '{api_url}' retornó 404")
