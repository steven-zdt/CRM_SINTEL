"""
Tests automatizados para validar que cada tenant creado tiene:
1. Dominio creado automáticamente
2. Dominio principal marcado correctamente
3. Acceso web funcionando
4. Tenant activo por defecto
"""

from django.conf import settings
from django.db import connection
from django.test import Client
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_public_schema_name, schema_exists

from apps.public.accounts.models import User
from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.services.onboarding.empresa_service import crear_tenant


class TenantDomainActivationTests(TenantTestCase):
    """
    Tests para validar que la creación de tenants activa correctamente
    el dominio y el acceso web.
    """

    def setUp(self):
        """Configuración inicial para cada test."""
        # Asegurar que estamos en el esquema public
        connection.set_schema_to_public()

        # Crear usuario administrador de prueba
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            username="admin",
            password="testpass123",
            is_staff=True,
            is_active=True,
        )

    def test_crear_tenant_crea_dominio_automaticamente(self):
        """Verifica que al crear un tenant, se crea automáticamente el dominio."""
        # Crear tenant
        client, domain, login_url = crear_tenant(
            nombre="Empresa Test",
            admin_user_id=self.admin_user.id,
            schema_name="test-empresa",
        )

        # Verificar que el dominio fue creado
        self.assertIsNotNone(domain)
        self.assertEqual(domain.tenant, client)
        self.assertTrue(domain.is_primary)

        # Verificar formato del dominio (debe ser subdominio)
        expected_domain = f"test-empresa.{settings.TENANT_DOMAIN_BASE}"
        self.assertEqual(domain.domain, expected_domain)

    def test_crear_tenant_dominio_principal_marcado(self):
        """Verifica que el dominio creado está marcado como principal."""
        # Crear tenant
        client, domain, login_url = crear_tenant(
            nombre="Empresa Test 2",
            admin_user_id=self.admin_user.id,
            schema_name="test-empresa-2",
        )

        # Verificar que es el dominio principal
        self.assertTrue(domain.is_primary)

        # Verificar que no hay otros dominios principales
        primary_domains = Domain.objects.filter(tenant=client, is_primary=True)
        self.assertEqual(primary_domains.count(), 1)
        self.assertEqual(primary_domains.first(), domain)

    def test_crear_tenant_esta_activo_por_defecto(self):
        """Verifica que el tenant creado está activo por defecto."""
        # Crear tenant
        client, domain, login_url = crear_tenant(
            nombre="Empresa Test 3",
            admin_user_id=self.admin_user.id,
            schema_name="test-empresa-3",
        )

        # Verificar que está activo
        self.assertTrue(client.is_active)

    def test_crear_tenant_esquema_postgresql_existe(self):
        """Verifica que el esquema PostgreSQL fue creado."""
        # Crear tenant
        client, domain, login_url = crear_tenant(
            nombre="Empresa Test 4",
            admin_user_id=self.admin_user.id,
            schema_name="test-empresa-4",
        )

        # Verificar que el esquema existe
        self.assertTrue(schema_exists(client.schema_name))

    def test_crear_tenant_acceso_web_funciona(self):
        """Verifica que el acceso web al tenant funciona correctamente."""
        # Crear tenant
        client, domain, login_url = crear_tenant(
            nombre="Empresa Test 5",
            admin_user_id=self.admin_user.id,
            schema_name="test-empresa-5",
        )

        # Simular petición HTTP al dominio del tenant
        test_client = Client(HTTP_HOST=domain.domain)
        response = test_client.get("/", follow=False)

        # Verificar que la respuesta no sea 404 (tenant no encontrado)
        # Puede ser 200 (landing page) o 302 (redirect)
        self.assertIn(
            response.status_code,
            [200, 302, 301],
            f"El acceso web falló con código {response.status_code}",
        )

    def test_crear_tenant_url_login_correcta(self):
        """Verifica que la URL de login generada es correcta."""
        # Crear tenant
        client, domain, login_url = crear_tenant(
            nombre="Empresa Test 6",
            admin_user_id=self.admin_user.id,
            schema_name="test-empresa-6",
        )

        # Verificar formato de la URL
        self.assertTrue(login_url.startswith("http://"))
        self.assertIn(domain.domain, login_url)
        self.assertTrue(login_url.endswith("/"))

    def test_crear_tenant_membresia_admin_creada(self):
        """Verifica que se crea la membresía del administrador."""
        # Crear tenant
        client, domain, login_url = crear_tenant(
            nombre="Empresa Test 7",
            admin_user_id=self.admin_user.id,
            schema_name="test-empresa-7",
        )

        # Verificar que existe la membresía
        membership = TenantMembership.objects.filter(
            client=client, user=self.admin_user, is_primary_admin=True
        ).first()

        self.assertIsNotNone(membership)
        self.assertEqual(membership.rol, "ADMIN")
        self.assertTrue(membership.is_active)

    def test_crear_tenant_dominio_no_duplicado(self):
        """Verifica que no se crean dominios duplicados."""
        # Crear primer tenant
        client1, domain1, login_url1 = crear_tenant(
            nombre="Empresa Test 8",
            admin_user_id=self.admin_user.id,
            schema_name="test-empresa-8",
        )

        # Intentar crear segundo tenant con mismo schema_name (debe fallar)
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            crear_tenant(
                nombre="Empresa Test 8 Duplicado",
                admin_user_id=self.admin_user.id,
                schema_name="test-empresa-8",  # Mismo schema_name
            )

    def test_crear_tenant_dominio_formato_subdominio(self):
        """Verifica que el dominio siempre sigue el formato de subdominio."""
        # Crear tenant
        client, domain, login_url = crear_tenant(
            nombre="Empresa Test 9",
            admin_user_id=self.admin_user.id,
            schema_name="test-empresa-9",
        )

        # Verificar formato: {schema_name}.{TENANT_DOMAIN_BASE}
        expected_domain = f"test-empresa-9.{settings.TENANT_DOMAIN_BASE}"
        self.assertEqual(domain.domain, expected_domain)

        # Verificar que no contiene puntos adicionales (no es FQDN)
        parts = domain.domain.split(".")
        self.assertEqual(
            len(parts),
            2,
            "El dominio debe tener exactamente 2 partes (subdominio.base)",
        )
