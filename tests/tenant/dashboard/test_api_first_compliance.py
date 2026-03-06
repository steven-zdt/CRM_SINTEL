"""
Pruebas de cumplimiento API-First para dashboard.

⚠️ POLÍTICA:
- Verificar que no hay vistas HTML clásicas
- Verificar que el shell estático consume solo Core API
- Verificar que no hay hardcodes de marca
"""
from tests.tenant.base_test import SintelTenantTestCase


class TestDashboardAPIFirstCompliance(SintelTenantTestCase):
    """
    Pruebas de cumplimiento API-First para dashboard.
    """
    
    def test_dashboard_api_endpoints_exist(self):
        """
        Verifica que los endpoints API del dashboard existen (aunque estén deprecados).
        """
        self.client.force_login(self.user)
        
        # Verificar que /api/v1/dashboard/summary/ existe (deprecado pero funcional)
        response = self.client.get(
            '/api/v1/dashboard/summary/',
            HTTP_HOST=f'{self.tenant.schema_name}.sintel.com'
        )
        # Puede ser 200, 401, 403, pero no 404
        self.assertNotEqual(response.status_code, 404,
                          "Endpoint /api/v1/dashboard/summary/ no debe retornar 404")
    
    def test_core_api_is_primary_source(self):
        """
        Verifica que Core API es la fuente principal de datos.
        """
        self.client.force_login(self.user)
        
        # Verificar que Core API retorna toda la información necesaria
        response = self.client.get(
            '/api/v1/core/dashboard/sections/',
            HTTP_HOST=f'{self.tenant.schema_name}.sintel.com'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verificar que incluye toda la información necesaria
        required_keys = ['user', 'tenant', 'branding', 'kpis', 'empresas', 'facturas', 'contabilidad', 'perfil']
        for key in required_keys:
            self.assertIn(key, data,
                         f"Core API debe incluir '{key}' para ser la fuente única de datos")
    
    def test_no_hardcoded_branding(self):
        """
        Verifica que no hay hardcodes de marca en las respuestas API.
        """
        self.client.force_login(self.user)
        
        # Verificar Core API
        response = self.client.get(
            '/api/v1/core/dashboard/sections/',
            HTTP_HOST=f'{self.tenant.schema_name}.sintel.com'
        )
        
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        
        # Verificar ausencia de hardcodes
        hardcodes = ['SINTEL', 'ACME', 'Mi Empresa']
        for hardcode in hardcodes:
            self.assertNotIn(hardcode, content,
                            f"Found hardcoded brand literal: {hardcode}")
    
    def test_dashboard_urls_not_included(self):
        """
        Verifica que apps/tenant/dashboard/urls.py está vacío (API-First).
        """
        from apps.tenant.dashboard import urls
        
        # Verificar que urlpatterns está vacío
        self.assertEqual(len(urls.urlpatterns), 0,
                         "apps/tenant/dashboard/urls.py debe estar vacío (API-First)")
    
    def test_dashboard_views_no_html(self):
        """
        Verifica que apps/tenant/dashboard/views.py no tiene vistas HTML.
        """
        import inspect
        from apps.tenant.dashboard import views
        
        # Verificar que no hay funciones/clases que rendericen HTML
        members = inspect.getmembers(views)
        
        # Buscar funciones/clases que puedan renderizar HTML
        html_indicators = ['TemplateView', 'ListView', 'DetailView', 'render', 'TemplateResponse']
        
        for name, obj in members:
            if inspect.isclass(obj) or inspect.isfunction(obj):
                obj_str = str(obj).lower()
                for indicator in html_indicators:
                    self.assertNotIn(indicator.lower(), obj_str,
                                   f"Found HTML rendering indicator '{indicator}' in {name}")
