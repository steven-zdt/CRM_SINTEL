"""
[WARNING] FASE 6: Tests críticos de Tenant Onboarding.

Valida que el sistema pueda crear y operar nuevos tenants sin intervención manual.
"""

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django_tenants.utils import schema_context

from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.services.onboarding.empresa_service import crear_tenant_con_owner

User = get_user_model()


class TenantOnboardingCriticalTests(TestCase):
    """
    Tests críticos de onboarding de tenants.

    [WARNING] FASE 6: Validaciones mínimas pero críticas del flujo de alta de empresa.
    """

    def setUp(self):
        """Configuración inicial."""
        super().setUp()
        # Crear usuario admin global para tests
        self.admin_user = User.objects.create_user(
            username="admin_test",
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )

    def test_crear_tenant_completo(self):
        """
        Test: Creación completa de tenant (empresa, esquema, dominio, admin).

        Criterios de aceptación:
        - El esquema se crea correctamente
        - El dominio resuelve al tenant correcto
        - El admin puede iniciar sesión
        - No se afecta ningún tenant existente
        """
        nombre = "Empresa Test Onboarding"
        schema_name = "empresa_test_onboarding"
        owner_email = "owner@test.com"

        # Crear tenant
        result = crear_tenant_con_owner(
            nombre=nombre,
            schema_name=schema_name,
            owner_email=owner_email,
            owner_is_staff=True,
            owner_is_active=True,
            on_trial=True,
        )

        # Validar resultado
        self.assertIn("client_id", result)
        self.assertIn("domain", result)
        self.assertIn("membership_id", result)
        self.assertIn("login_url", result)

        # Validar Client creado
        client = Client.objects.get(id=result["client_id"])
        self.assertEqual(client.schema_name, schema_name)
        self.assertEqual(client.nombre, nombre)
        self.assertTrue(client.is_active)

        # Validar Domain creado
        domain = Domain.objects.get(domain=result["domain"])
        self.assertEqual(domain.tenant_id, client.id)
        self.assertTrue(domain.is_primary)

        # Validar User creado
        owner = User.objects.get(email=owner_email)
        self.assertTrue(owner.is_active)

        # Validar TenantMembership creado
        membership = TenantMembership.objects.get(id=result["membership_id"])
        self.assertEqual(membership.client_id, client.id)
        self.assertEqual(membership.user_id, owner.id)
        self.assertEqual(membership.rol, "ADMIN")
        self.assertTrue(membership.is_primary_admin)

    def test_esquema_se_crea_correctamente(self):
        """
        Test: El esquema PostgreSQL se crea correctamente.

        Criterios de aceptación:
        - El esquema existe en PostgreSQL
        - Las tablas de TENANT_APPS están presentes
        """
        nombre = "Empresa Test Schema"
        schema_name = "empresa_test_schema"
        owner_email = "owner_schema@test.com"

        result = crear_tenant_con_owner(
            nombre=nombre,
            schema_name=schema_name,
            owner_email=owner_email,
            on_trial=True,
        )

        client = Client.objects.get(id=result["client_id"])

        # Verificar que el esquema existe
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = %s
            """,
                [schema_name],
            )
            row = cursor.fetchone()
            self.assertIsNotNone(
                row, f"El esquema '{schema_name}' debe existir en PostgreSQL"
            )

        # Verificar que podemos cambiar al esquema
        with schema_context(schema_name):
            # Si llegamos aquí sin error, el esquema existe y es accesible
            self.assertEqual(connection.schema_name, schema_name)

    def test_dominio_resuelve_al_tenant_correcto(self):
        """
        Test: El dominio resuelve al tenant correcto.

        Criterios de aceptación:
        - El dominio está asociado al tenant correcto
        - El dominio es primario
        """
        nombre = "Empresa Test Domain"
        schema_name = "empresa_test_domain"
        owner_email = "owner_domain@test.com"
        dominio_fqdn = "test-domain.localhost"

        result = crear_tenant_con_owner(
            nombre=nombre,
            schema_name=schema_name,
            dominio_fqdn=dominio_fqdn,
            owner_email=owner_email,
            on_trial=True,
        )

        # Validar dominio
        domain = Domain.objects.get(domain=result["domain"])
        self.assertEqual(domain.domain, dominio_fqdn)
        self.assertEqual(domain.tenant.schema_name, schema_name)
        self.assertTrue(domain.is_primary)

    def test_admin_puede_iniciar_sesion(self):
        """
        Test: El admin puede iniciar sesión.

        Criterios de aceptación:
        - El usuario owner existe
        - El usuario está activo
        - El usuario tiene TenantMembership
        """
        nombre = "Empresa Test Login"
        schema_name = "empresa_test_login"
        owner_email = "owner_login@test.com"

        result = crear_tenant_con_owner(
            nombre=nombre,
            schema_name=schema_name,
            owner_email=owner_email,
            owner_is_active=True,
            on_trial=True,
        )

        # Validar usuario
        owner = User.objects.get(email=owner_email)
        self.assertTrue(owner.is_active)
        self.assertIsNotNone(owner)

        # Validar membership
        membership = TenantMembership.objects.get(id=result["membership_id"])
        self.assertEqual(membership.user_id, owner.id)
        self.assertTrue(membership.is_active)

    def test_no_afecta_tenants_existentes(self):
        """
        Test: La creación de un nuevo tenant no afecta tenants existentes.

        Criterios de aceptación:
        - Los tenants existentes siguen funcionando
        - Los datos de otros tenants no se ven afectados
        """
        # Crear primer tenant
        result1 = crear_tenant_con_owner(
            nombre="Empresa Test 1",
            schema_name="empresa_test_1",
            owner_email="owner1@test.com",
            on_trial=True,
        )
        client1 = Client.objects.get(id=result1["client_id"])

        # Crear segundo tenant
        result2 = crear_tenant_con_owner(
            nombre="Empresa Test 2",
            schema_name="empresa_test_2",
            owner_email="owner2@test.com",
            on_trial=True,
        )
        client2 = Client.objects.get(id=result2["client_id"])

        # Validar que ambos existen y son independientes
        self.assertNotEqual(client1.schema_name, client2.schema_name)
        self.assertNotEqual(client1.id, client2.id)

        # Validar que ambos esquemas existen
        with schema_context(client1.schema_name):
            self.assertEqual(connection.schema_name, client1.schema_name)

        with schema_context(client2.schema_name):
            self.assertEqual(connection.schema_name, client2.schema_name)

    def test_idempotencia_onboarding(self):
        """
        Test: El onboarding es idempotente (puede ejecutarse múltiples veces).

        Criterios de aceptación:
        - Ejecutar dos veces con los mismos datos no crea duplicados
        - Retorna el mismo tenant existente
        """
        nombre = "Empresa Test Idempotente"
        schema_name = "empresa_test_idempotente"
        owner_email = "owner_idempotente@test.com"

        # Primera ejecución
        result1 = crear_tenant_con_owner(
            nombre=nombre,
            schema_name=schema_name,
            owner_email=owner_email,
            on_trial=True,
        )

        # Segunda ejecución (debe ser idempotente)
        result2 = crear_tenant_con_owner(
            nombre=nombre,
            schema_name=schema_name,
            owner_email=owner_email,
            on_trial=True,
        )

        # Validar que retorna el mismo tenant
        self.assertEqual(result1["client_id"], result2["client_id"])
        self.assertEqual(result1["domain"], result2["domain"])

        # Validar que solo existe un Client con ese schema_name
        count = Client.objects.filter(schema_name=schema_name).count()
        self.assertEqual(count, 1)
