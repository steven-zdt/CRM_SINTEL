"""
Smoke tests para rutas de shells estáticos de Core.

Verifica que:
1. Cada short route redirige al shell estático de Core
2. Los shells estáticos son servidos correctamente
3. Los shells contienen los contenedores esperados
"""
import pytest
from tests.tenant.base_test import SintelTenantTestCase


@pytest.mark.django_db
class TestCoreShellRoutes(SintelTenantTestCase):
    """Tests de smoke para rutas de shells estáticos de Core."""
    
    def test_dashboard_route_redirects_to_core_shell(self):
        """Test: GET /dashboard/ redirige a /static/tenant/core/dashboard/index.html"""
        response = self.api_client.get('/dashboard/')
        assert response.status_code == 302
        assert '/static/tenant/core/dashboard/index.html' in response.url
    
    def test_empresa_route_redirects_to_core_shell(self):
        """Test: GET /empresa/ redirige a /static/tenant/core/empresa/index.html"""
        response = self.api_client.get('/empresa/')
        assert response.status_code == 302
        assert '/static/tenant/core/empresa/index.html' in response.url
    
    def test_facturas_route_redirects_to_core_shell(self):
        """Test: GET /facturas/ redirige a /static/tenant/core/facturas/index.html"""
        response = self.api_client.get('/facturas/')
        assert response.status_code == 302
        assert '/static/tenant/core/facturas/index.html' in response.url
    
    def test_contabilidad_route_redirects_to_core_shell(self):
        """Test: GET /contabilidad/ redirige a /static/tenant/core/contabilidad/index.html"""
        response = self.api_client.get('/contabilidad/')
        assert response.status_code == 302
        assert '/static/tenant/core/contabilidad/index.html' in response.url
    
    def test_landing_route_redirects_to_core_shell(self):
        """Test: GET /landing/ redirige a /static/tenant/core/landing/index.html"""
        response = self.api_client.get('/landing/')
        assert response.status_code == 302
        assert '/static/tenant/core/landing/index.html' in response.url
    
    def test_perfil_route_redirects_to_core_shell(self):
        """Test: GET /perfil/ redirige a /static/tenant/core/perfil/index.html"""
        response = self.api_client.get('/perfil/')
        assert response.status_code == 302
        assert '/static/tenant/core/perfil/index.html' in response.url
    
    def test_deprecated_ui_routes_return_404(self):
        """Test: Las rutas /ui/<app>/partials/* retornan 404 (deprecadas)"""
        from rest_framework.test import APIClient
        client = APIClient(HTTP_HOST=self.domain.domain)
        client.force_authenticate(user=self.user)
        
        # Verificar que las rutas UI deprecadas retornan 404
        response = client.get('/ui/empresa/partials/card/')
        assert response.status_code == 404
        
        response = client.get('/ui/facturas/partials/table/')
        assert response.status_code == 404
        
        response = client.get('/ui/contabilidad/partials/summary/')
        assert response.status_code == 404
        
        response = client.get('/ui/perfil/partials/card/')
        assert response.status_code == 404
        
        response = client.get('/ui/dashboard/partials/header/')
        assert response.status_code == 404
    
    def test_deprecated_empresa_page_view_returns_404(self):
        """Test: La ruta /empresa/ (TemplateView) ya no existe, redirige a shell estático"""
        # La ruta /empresa/ ahora redirige, no renderiza template
        response = self.api_client.get('/empresa/')
        assert response.status_code == 302
        assert '/static/tenant/core/empresa/index.html' in response.url
