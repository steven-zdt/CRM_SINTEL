"""
Test de integración para verificar que el admin de tenant NO muestra modelos públicos.

Simula el acceso real a http://{schema}.sintel.net.co:8000/admin/
"""

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, TestCase
from django.urls import reverse
from django_tenants.test.cases import TenantTestCase

from apps.public.tenants.models import Client
from apps.public.tenants.models import Client as TenantClient
from apps.public.tenants.models import Domain
from apps.public.tenants.models import Domain as PublicDomain
from apps.tenant.core.admin import tenant_admin_site

User = get_user_model()


class TenantAdminIntegrationTests(TenantTestCase):
    """
    Tests de integración para verificar el aislamiento del admin de tenant.

    Simula el acceso real al admin desde un tenant privado.
    """

    @classmethod
    def setup_tenant(cls, tenant_user=None):
        """Crear un tenant de prueba."""
        connection.set_schema_to_public()
        tenant = TenantClient.objects.create(
            schema_name="test_admin", nombre="Test Admin Tenant", is_active=True
        )
        Domain.objects.create(
            domain="test-admin.sintel.net.co", tenant=tenant, is_primary=True
        )
        return tenant

    @classmethod
    def setup_domain(cls, domain):
        """Configurar el dominio del tenant."""
        # TenantTestCase ya crea el dominio, solo necesitamos asegurarnos de que esté configurado
        if not domain.domain or domain.domain == "localhost":
            domain.domain = f"{domain.tenant.schema_name}.sintel.net.co"
        domain.is_primary = True
        domain.save()
        return domain

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()

        # Crear usuario staff en el esquema public
        connection.set_schema_to_public()
        self.staff_user = User.objects.create_user(
            email="staff@test.com",
            username="staff",
            password="testpass123",
            is_active=True,
            is_staff=True,
        )

        # Cambiar al esquema del tenant
        connection.set_schema(self.tenant.schema_name)

        # Configurar cliente HTTP
        self.client = Client(HTTP_HOST=f"{self.tenant.schema_name}.sintel.net.co")
        self.client.force_login(self.staff_user)

    def test_admin_index_only_shows_tenant_models(self):
        """
        Verifica que el índice del admin solo muestra modelos de tenant.

        [OK] Debe pasar: Solo modelos de TENANT_APPS deben aparecer
        """
        # Acceder al índice del admin
        response = self.client.get("/admin/")

        # Verificar que la respuesta es exitosa
        self.assertEqual(
            response.status_code, 200, "El admin debe ser accesible para usuarios staff"
        )

        # Verificar que NO aparece "Client" o "Domain" en el contenido
        content = response.content.decode("utf-8")

        # Modelos públicos que NO deben aparecer
        public_model_names = ["Client", "Domain", "TenantMembership", "Tenants"]
        for model_name in public_model_names:
            self.assertNotIn(
                model_name,
                content,
                f"[ERROR] VULNERABILIDAD: '{model_name}' aparece en el admin de tenant. "
                "Este modelo pertenece al esquema público y NO debe aparecer.",
            )

        # Modelos de tenant que SÍ deben aparecer
        tenant_model_names = ["Empresa", "Factura", "Contabilidad"]
        found_tenant_models = [name for name in tenant_model_names if name in content]

        self.assertGreater(
            len(found_tenant_models),
            0,
            f"Debe haber al menos un modelo de tenant visible. "
            f"Modelos encontrados: {found_tenant_models}",
        )

    def test_admin_uses_tenant_admin_site(self):
        """
        Verifica que el admin está usando tenant_admin_site.

        [OK] Debe pasar: El admin debe usar tenant_admin_site, no admin.site
        """
        # Verificar que tenant_admin_site tiene modelos registrados
        self.assertGreater(
            len(tenant_admin_site._registry),
            0,
            "tenant_admin_site debe tener modelos registrados",
        )

        # Verificar que los modelos públicos NO están en tenant_admin_site
        self.assertFalse(
            tenant_admin_site.is_registered(Client),
            "Client NO debe estar registrado en tenant_admin_site",
        )

        self.assertFalse(
            tenant_admin_site.is_registered(PublicDomain),
            "Domain NO debe estar registrado en tenant_admin_site",
        )
