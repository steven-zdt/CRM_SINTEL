"""
Pruebas de humo para Link Registry de Core API.

Verifica que:
- El Link Registry retorna todas las rutas necesarias
- Todas las rutas API y UI son accesibles (no 404)
- La redirección de compatibilidad funciona (singular → plural)
"""
from django.test import Client
from django.urls import reverse
from tests.tenant.base_test import SintelTenantTestCase


class LinkRegistrySmokeTests(SintelTenantTestCase):
    """Tests de humo para Link Registry."""
    
    def setUp(self):
        """Configurar tenant y usuario de prueba."""
        super().setUp()
        self.client = Client(HTTP_HOST=self.domain.domain)
        self.client.force_login(self.user)
    
    def test_link_registry_200(self):
        """Test: GET /api/v1/core/links/ retorna 200 con estructura correcta."""
        response = self.client.get('/api/v1/core/links/')
        
        self.assertEqual(response.status_code, 200, 
                        f"Expected 200, got {response.status_code}. Response: {response.content[:500]}")
        
        data = response.json()
        
        # Verificar estructura
        self.assertIn('empresa', data)
        self.assertIn('facturas', data)
        self.assertIn('contabilidad', data)
        self.assertIn('perfil', data)
        self.assertIn('dashboard', data)
        self.assertIn('core', data)
        
        # Verificar que cada módulo tiene api y ui
        for module_name, module_data in data.items():
            self.assertIn('api', module_data, f"Módulo '{module_name}' no tiene 'api'")
            self.assertIn('ui', module_data, f"Módulo '{module_name}' no tiene 'ui'")
            
            # Verificar que las URLs son relativas (no absolutas)
            self.assertFalse(module_data['api'].startswith('http://') or module_data['api'].startswith('https://'),
                           f"URL API de '{module_name}' es absoluta: {module_data['api']}")
            self.assertFalse(module_data['ui'].startswith('http://') or module_data['ui'].startswith('https://'),
                           f"URL UI de '{module_name}' es absoluta: {module_data['ui']}")
            
            # Verificar que las URLs empiezan con /
            self.assertTrue(module_data['api'].startswith('/'),
                          f"URL API de '{module_name}' no empieza con /: {module_data['api']}")
            self.assertTrue(module_data['ui'].startswith('/'),
                          f"URL UI de '{module_name}' no empieza con /: {module_data['ui']}")
    
    def test_link_registry_api_routes_accessible(self):
        """Test: Todas las rutas API del registry son accesibles (no 404)."""
        response = self.client.get('/api/v1/core/links/')
        self.assertEqual(response.status_code, 200)
        
        links = response.json()
        
        # Verificar cada ruta API
        for module_name, module_data in links.items():
            api_url = module_data['api']
            
            # Hacer GET a la ruta API
            api_response = self.client.get(api_url)
            
            # Verificar que no es 404
            self.assertNotEqual(api_response.status_code, 404,
                              f"Ruta API '{api_url}' del módulo '{module_name}' retorna 404")
            
            # Aceptar 200, 401, 403, 405 (Method Not Allowed), pero no 404
            self.assertIn(api_response.status_code, [200, 401, 403, 405],
                         f"Ruta API '{api_url}' del módulo '{module_name}' retorna {api_response.status_code} (esperado 200/401/403/405)")
    
    def test_empresa_singular_redirect(self):
        """Test: GET /api/v1/empresa/ redirige a /api/v1/empresas/ (compatibilidad)."""
        response = self.client.get('/api/v1/empresa/')
        
        # Debe ser redirección (301, 302, 307, 308) o 200/405 (pero NO 404)
        self.assertIn(response.status_code, [200, 301, 302, 307, 308, 405],
                     f"Ruta singular '/api/v1/empresa/' retorna {response.status_code} (esperado redirección o 200/405)")
        
        # Si es redirección, verificar que apunta a /api/v1/empresas/
        if response.status_code in [301, 302, 307, 308]:
            self.assertIn('/api/v1/empresas/', response.url,
                         f"Redirección de '/api/v1/empresa/' no apunta a '/api/v1/empresas/': {response.url}")
    
    def test_empresa_plural_accessible(self):
        """Test: GET /api/v1/empresas/ es accesible (ruta canónica)."""
        response = self.client.get('/api/v1/empresas/')
        
        # Debe ser 200 (list) o 401/403 (autenticación/permisos), pero NO 404
        self.assertIn(response.status_code, [200, 401, 403],
                     f"Ruta canónica '/api/v1/empresas/' retorna {response.status_code} (esperado 200/401/403)")
    
    def test_link_registry_no_hardcodes(self):
        """Test: El Link Registry no contiene hardcodes de marca."""
        response = self.client.get('/api/v1/core/links/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        response_text = response.content.decode('utf-8')
        
        # Verificar que no hay hardcodes de marca
        self.assertNotIn('SINTEL', response_text)
        self.assertNotIn('ACME', response_text)
        self.assertNotIn('Mi Empresa', response_text)
        
        # Verificar que las URLs son genéricas (no específicas de tenant)
        for module_name, module_data in data.items():
            # No debe contener dominios específicos
            self.assertNotIn('home.sintel.com', module_data['api'])
            self.assertNotIn('cliente.sintel.com', module_data['api'])
    
    def test_link_registry_unauthenticated(self):
        """Test: Link Registry requiere autenticación."""
        # Cliente sin autenticación
        client = Client(HTTP_HOST=self.domain.domain)
        
        response = client.get('/api/v1/core/links/')
        
        # Debe retornar 401 o 403
        self.assertIn(response.status_code, [401, 403],
                     f"Link Registry debería requerir autenticación (got {response.status_code})")
