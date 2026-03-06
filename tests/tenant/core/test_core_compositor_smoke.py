"""
Smoke tests para el compositor de workspace (core).

Verifica que:
- GET /workspace/ retorna 200 con base markers
- GET cada /ui/<app>/partials/<name>/ retorna 200 y contiene data-partial
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.public.tenants.models import Client, Domain, TenantMembership
from django_tenants.utils import schema_context

User = get_user_model()


class CoreCompositorSmokeTests(TestCase):
    """Tests de smoke para el compositor de workspace."""
    
    @classmethod
    def setUpTestData(cls):
        """Crear tenant y usuario de prueba."""
        with schema_context('public'):
            # Crear tenant
            cls.tenant = Client.objects.create(
                nombre='Test Tenant',
                schema_name='test_tenant',
                on_trial=True,
            )
            Domain.objects.create(
                domain='test.localhost',
                tenant=cls.tenant,
                is_primary=True,
            )
            
            # Crear usuario
            cls.user = User.objects.create_user(
                email='test@example.com',
                password='testpass123',
                is_active=True,
            )
            
            # Crear membresía
            TenantMembership.objects.create(
                user=cls.user,
                tenant=cls.tenant,
                role='USER',
                is_active=True,
            )
    
    def setUp(self):
        """Configurar para cada test."""
        self.client.force_login(self.user)
        # Configurar host para django-tenants
        self.client.defaults['HTTP_HOST'] = 'test.localhost'
    
    def test_workspace_view_returns_200(self):
        """Test: GET /workspace/ retorna 200 con base markers."""
        response = self.client.get('/workspace/', HTTP_HOST='test.localhost')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'slot-empresa')
        self.assertContains(response, 'slot-facturas')
        self.assertContains(response, 'slot-contabilidad')
        self.assertContains(response, 'slot-perfil')
        self.assertContains(response, 'hx-get')
    
    def test_empresa_card_partial_returns_200(self):
        """Test: GET /ui/empresa/partials/card/ retorna 200 y contiene data-partial."""
        response = self.client.get('/ui/empresa/partials/card/', HTTP_HOST='test.localhost')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-partial="empresa-card"')
    
    def test_facturas_table_partial_returns_200(self):
        """Test: GET /ui/facturas/partials/table/ retorna 200 y contiene data-partial."""
        response = self.client.get('/ui/facturas/partials/table/', HTTP_HOST='test.localhost')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-partial="facturas-table"')
    
    def test_contabilidad_summary_partial_returns_200(self):
        """Test: GET /ui/contabilidad/partials/summary/ retorna 200 y contiene data-partial."""
        response = self.client.get('/ui/contabilidad/partials/summary/', HTTP_HOST='test.localhost')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-partial="contabilidad-summary"')
    
    def test_perfil_card_partial_returns_200(self):
        """Test: GET /ui/perfil/partials/card/ retorna 200 y contiene data-partial."""
        response = self.client.get('/ui/perfil/partials/card/', HTTP_HOST='test.localhost')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-partial="perfil-card"')
    
    def test_partials_require_authentication(self):
        """Test: Los partials requieren autenticación."""
        self.client.logout()
        
        response = self.client.get('/ui/empresa/partials/card/', HTTP_HOST='test.localhost')
        self.assertEqual(response.status_code, 302)  # Redirect to login
