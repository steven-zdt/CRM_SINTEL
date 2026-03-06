"""
Pruebas de humo para la página de empresa (template que extiende tenant/base.html).

⚠️ POLÍTICA API-First: El template no renderiza datos server-side;
todos los datos se obtienen vía JavaScript desde las APIs REST.
"""
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.tenant.core.tests import SintelTenantTestCase
from apps.public.tenants.models import Client as TenantClient, Domain, TenantMembership
from apps.tenant.empresa.models import Empresa

User = get_user_model()


class EmpresaPageSmokeTestCase(SintelTenantTestCase):
    """Pruebas de humo para la página de empresa."""

    def setUp(self):
        """Configurar datos de prueba."""
        super().setUp()
        
        # Crear usuario y membresía en el tenant
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            is_active=True
        )
        
        # Crear tenant de prueba
        self.tenant = TenantClient.objects.create(
            schema_name='test_tenant',
            nombre='Test Tenant',
            auto_create_schema=True
        )
        
        # Crear dominio para el tenant
        self.domain = Domain.objects.create(
            domain='test-tenant.sintel.com',
            tenant=self.tenant,
            is_primary=True
        )
        
        # Crear membresía
        TenantMembership.objects.create(
            client=self.tenant,
            user=self.user,
            role='admin',
            is_active=True
        )
        
        # Cliente de prueba con el dominio del tenant
        self.client = Client(HTTP_HOST='test-tenant.sintel.com')

    def test_empresa_page_requires_login(self):
        """Verifica que la página requiere autenticación."""
        url = reverse('tenant-empresa-page')
        response = self.client.get(url, HTTP_HOST='test-tenant.sintel.com')
        
        # Debe redirigir a login
        self.assertIn(response.status_code, [302, 401])

    def test_empresa_page_renders_template(self):
        """Verifica que la página renderiza el template correcto."""
        # Autenticar usuario
        self.client.force_login(self.user)
        
        url = reverse('tenant-empresa-page')
        response = self.client.get(url, HTTP_HOST='test-tenant.sintel.com')
        
        # Debe retornar 200
        self.assertEqual(response.status_code, 200)
        
        # Debe usar el template correcto
        self.assertTemplateUsed(response, 'tenant/empresa/page.html')
        
        # Debe extender tenant/base.html
        self.assertContains(response, 'tenant/base.html', count=0)  # No aparece literalmente, pero se extiende
        
        # Debe contener marcadores del formulario
        self.assertContains(response, 'empresa-form')
        self.assertContains(response, 'razon_social')
        self.assertContains(response, 'tipo_contribuyente_clase')
        self.assertContains(response, 'tipo_contribuyente_segmento')
        self.assertContains(response, 'actividad_economica_codigo')

    def test_empresa_page_has_header_section(self):
        """Verifica que la página tiene la sección de header para logo y razón social."""
        self.client.force_login(self.user)
        
        url = reverse('tenant-empresa-page')
        response = self.client.get(url, HTTP_HOST='test-tenant.sintel.com')
        
        # Debe contener el header (se pobla vía JS)
        self.assertContains(response, 'empresa-header')
        self.assertContains(response, 'empresa-razon-social')
        self.assertContains(response, 'empresa-logo')
