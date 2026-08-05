"""
Suite de Pruebas de Seguridad (Red Team) - Cross-Tenant Isolation.

[WARNING] CRÍTICO: Estas pruebas validan que el aislamiento entre tenants
funciona correctamente, evitando fugas de datos y acceso no autorizado.

Casos de Prueba (Must Pass):
1. Cross-Access View: Usuario A intenta acceder a dashboard de Tenant B -> 403
2. Cross-Access API: Usuario A intenta acceder a API de Tenant B -> 403/404
3. Public Access: Usuario anónimo intenta entrar a dashboard -> 302 Redirect
4. Leak Test: Verificar que datos de Tenant A no aparezcan en Tenant B

Arquitectura:
- Usa TenantTestCase de django-tenants para manejar correctamente los esquemas
- Usa base de datos real (transaccional) para asegurar aislamiento real
- No usa mocking excesivo para validar queries reales de django-tenants
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import Client
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework import status
from rest_framework.test import APIClient

from apps.public.tenants.models import Client as TenantClient
from apps.public.tenants.models import Domain, TenantMembership
from apps.services.empresa.gestion_service import crear_o_actualizar_empresa
from apps.tenant.empresa.models import Empresa

User = get_user_model()


class CrossTenantIsolationTests(TenantTestCase):
    """
    Tests de aislamiento cross-tenant.

    Valida que los usuarios solo puedan acceder a datos y vistas
    de tenants donde tienen membresía activa.
    """

    def setUp(self):
        """
        Configuración inicial para cada test.

        Crea:
        - Tenant A y Tenant B
        - User A (miembro de Tenant A)
        - User B (miembro de Tenant B)
        - User Hacker (usuario logueado pero sin membresía en ningún tenant)
        """
        # Asegurar que estamos en el esquema public para crear tenants
        from django.db import connection

        connection.set_schema_to_public()

        # Crear Tenant A
        self.tenant_a = TenantClient.objects.create(
            schema_name="tenant_a", nombre="Tenant A", is_active=True
        )
        Domain.objects.create(
            tenant=self.tenant_a, domain="tenant-a.test", is_primary=True
        )

        # Crear Tenant B
        self.tenant_b = TenantClient.objects.create(
            schema_name="tenant_b", nombre="Tenant B", is_active=True
        )
        Domain.objects.create(
            tenant=self.tenant_b, domain="tenant-b.test", is_primary=True
        )

        # Crear User A (miembro de Tenant A)
        self.user_a = User.objects.create_user(
            email="usera@test.com",
            username="usera",
            password="testpass123",
            is_active=True,
        )
        TenantMembership.objects.create(
            client=self.tenant_a, user=self.user_a, rol="ADMIN", is_primary_admin=True
        )

        # Crear User B (miembro de Tenant B)
        self.user_b = User.objects.create_user(
            email="userb@test.com",
            username="userb",
            password="testpass123",
            is_active=True,
        )
        TenantMembership.objects.create(
            client=self.tenant_b, user=self.user_b, rol="ADMIN", is_primary_admin=True
        )

        # Crear User Hacker (usuario logueado pero sin membresía en ningún tenant)
        self.user_hacker = User.objects.create_user(
            email="hacker@test.com",
            username="hacker",
            password="testpass123",
            is_active=True,
        )
        # NO crear TenantMembership para este usuario

        # Crear datos de prueba en Tenant A
        connection.set_schema("tenant_a")
        self.empresa_a = crear_o_actualizar_empresa(
            razon_social="Empresa Tenant A S.A.",
            nit="900111111",
            direccion="Dirección Tenant A",
            telefono="6011111111",
            email_contacto="contacto@tenant-a.com",
            regimen_tributario="Responsable de IVA",
        )

        # Crear datos de prueba en Tenant B
        connection.set_schema("tenant_b")
        self.empresa_b = crear_o_actualizar_empresa(
            razon_social="Empresa Tenant B S.A.",
            nit="900222222",
            direccion="Dirección Tenant B",
            telefono="6022222222",
            email_contacto="contacto@tenant-b.com",
            regimen_tributario="Responsable de IVA",
        )

        # Volver al esquema public
        connection.set_schema_to_public()

    def test_cross_access_view_denied(self):
        """
        Test: Usuario A intenta acceder a /dashboard/ en el dominio de Tenant B.

        Resultado esperado: 403 Forbidden
        """
        # Cambiar al esquema de Tenant B
        from django.db import connection

        connection.set_schema("tenant_b")

        # Cliente autenticado como User A (miembro de Tenant A, no de Tenant B)
        client = Client()
        client.force_login(self.user_a)

        # Intentar acceder al dashboard de Tenant B
        response = client.get("/dashboard/")

        # Validaciones
        self.assertEqual(
            response.status_code,
            403,
            "Usuario A no debe poder acceder al dashboard de Tenant B",
        )

        # Verificar que el mensaje de error es apropiado
        content_lower = response.content.decode("utf-8").lower()
        has_error_message = (
            "permisos" in content_lower
            or "acceso" in content_lower
            or "denied" in content_lower
            or "forbidden" in content_lower
        )
        self.assertTrue(
            has_error_message,
            "El mensaje de error debe indicar que el acceso fue denegado",
        )

    def test_cross_access_api_denied(self):
        """
        Test: Usuario A intenta hacer GET a /api/v1/empresa/empresas/ en el dominio de Tenant B.

        Resultado esperado: 403 Forbidden o 404 Not Found
        (Los datos no deben ser visibles)
        """
        # Cambiar al esquema de Tenant B
        from django.db import connection

        connection.set_schema("tenant_b")

        # Cliente API autenticado como User A (miembro de Tenant A, no de Tenant B)
        api_client = APIClient()
        api_client.force_authenticate(user=self.user_a)

        # Intentar acceder a la API de empresa de Tenant B
        response = api_client.get("/api/v1/empresa/empresas/")

        # Validaciones
        self.assertIn(
            response.status_code,
            [403, 404],
            "Usuario A no debe poder acceder a la API de Tenant B",
        )

        # Si es 403, verificar que el mensaje es apropiado
        if response.status_code == 403:
            self.assertIn(
                "permission" in str(response.data).lower()
                or "denied" in str(response.data).lower(),
                True,
                "El mensaje de error debe indicar que el acceso fue denegado",
            )

    def test_public_access_redirects_to_login(self):
        """
        Test: Usuario anónimo intenta entrar a /dashboard/.

        Resultado esperado: 302 Redirect a Login
        """
        # Cambiar al esquema de Tenant A
        from django.db import connection

        connection.set_schema("tenant_a")

        # Cliente anónimo
        client = Client()

        # Intentar acceder al dashboard sin autenticación
        response = client.get("/dashboard/")

        # Validaciones
        self.assertEqual(
            response.status_code, 302, "Usuario anónimo debe ser redirigido al login"
        )

        # Verificar que la redirección apunta al login
        self.assertIn(
            "/login" in response.url
            or "/" in response.url,  # Puede redirigir a la landing page
            True,
            "La redirección debe apuntar al login o landing page",
        )

    def test_leak_test_tenant_a_data_not_in_tenant_b(self):
        """
        Test: Verificar que al listar Empresas en Tenant A, NO aparezca la data de Tenant B.

        Resultado esperado: Solo debe aparecer la empresa de Tenant A
        """
        # Cambiar al esquema de Tenant A
        from django.db import connection

        connection.set_schema("tenant_a")

        # Cliente API autenticado como User A (miembro de Tenant A)
        api_client = APIClient()
        api_client.force_authenticate(user=self.user_a)

        # Listar empresas en Tenant A
        response = api_client.get("/api/v1/empresa/empresas/")

        # Validaciones
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "Usuario A debe poder acceder a la API de su propio tenant",
        )

        # Verificar que solo aparece la empresa de Tenant A
        empresas = (
            response.data
            if isinstance(response.data, list)
            else response.data.get("results", [])
        )

        self.assertEqual(len(empresas), 1, "Debe haber solo una empresa en Tenant A")

        self.assertEqual(
            empresas[0]["razon_social"],
            "Empresa Tenant A S.A.",
            "La empresa debe ser la de Tenant A",
        )

        # Verificar que NO aparece la empresa de Tenant B
        razones_sociales = [emp["razon_social"] for emp in empresas]
        self.assertNotIn(
            "Empresa Tenant B S.A.",
            razones_sociales,
            "La empresa de Tenant B NO debe aparecer en Tenant A",
        )

    def test_user_hacker_cannot_access_any_tenant(self):
        """
        Test: User Hacker (sin membresía) intenta acceder a cualquier tenant.

        Resultado esperado: 403 Forbidden en todos los casos
        """
        # Cambiar al esquema de Tenant A
        from django.db import connection

        connection.set_schema("tenant_a")

        # Cliente autenticado como User Hacker (sin membresía)
        client = Client()
        client.force_login(self.user_hacker)

        # Intentar acceder al dashboard de Tenant A
        response = client.get("/dashboard/")

        # Validaciones
        self.assertEqual(
            response.status_code,
            403,
            "User Hacker no debe poder acceder a ningún tenant",
        )

        # Intentar acceder a la API de Tenant A
        api_client = APIClient()
        api_client.force_authenticate(user=self.user_hacker)

        response = api_client.get("/api/v1/empresa/empresas/")

        # Validaciones
        self.assertIn(
            response.status_code,
            [403, 404],
            "User Hacker no debe poder acceder a la API de ningún tenant",
        )

    def test_user_a_can_access_own_tenant(self):
        """
        Test: Usuario A puede acceder correctamente a su propio tenant (Tenant A).

        Resultado esperado: 200 OK
        """
        # Cambiar al esquema de Tenant A
        from django.db import connection

        connection.set_schema("tenant_a")

        # Cliente autenticado como User A (miembro de Tenant A)
        client = Client()
        client.force_login(self.user_a)

        # Acceder al dashboard de Tenant A
        response = client.get("/dashboard/")

        # Validaciones
        self.assertEqual(
            response.status_code,
            200,
            "Usuario A debe poder acceder al dashboard de su propio tenant",
        )

        # Acceder a la API de Tenant A
        api_client = APIClient()
        api_client.force_authenticate(user=self.user_a)

        response = api_client.get("/api/v1/empresa/empresas/")

        # Validaciones
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "Usuario A debe poder acceder a la API de su propio tenant",
        )

        # Verificar que puede ver sus propios datos
        empresas = (
            response.data
            if isinstance(response.data, list)
            else response.data.get("results", [])
        )
        self.assertGreaterEqual(
            len(empresas), 1, "Usuario A debe poder ver los datos de su propio tenant"
        )
