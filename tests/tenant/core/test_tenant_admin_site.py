"""
Tests para el Admin Site Aislado de Tenants.

Verifica que:
1. TenantAdminSite solo muestra modelos de TENANT_APPS
2. Los modelos del esquema público NO aparecen
3. El registro automático funciona correctamente
4. Los permisos se validan correctamente
"""

from django.contrib.admin.sites import AlreadyRegistered
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase

from apps.public.accounts.models import User
from apps.public.tenants.models import Client, Domain
from apps.tenant.core.admin import ensure_tenant_apps_registered, tenant_admin_site
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura

User = get_user_model()


class TenantAdminSiteIsolationTests(TestCase):
    """
    Tests de aislamiento del TenantAdminSite.

    Verifica que el admin site aislado solo muestre modelos de TENANT_APPS
    y excluya completamente los modelos del esquema público.
    """

    def setUp(self):
        """Configuración inicial para cada test."""
        # Asegurar que los modelos estén registrados
        ensure_tenant_apps_registered()

    def test_tenant_models_are_registered(self):
        """
        Verifica que los modelos de tenant están registrados en tenant_admin_site.

        [OK] Debe pasar: Empresa, Factura, etc. deben estar registrados
        """
        # Modelos de tenant que DEBEN estar registrados
        tenant_models = [
            Empresa,
            Factura,
        ]

        for model in tenant_models:
            with self.subTest(model=model.__name__):
                self.assertTrue(
                    tenant_admin_site.is_registered(model),
                    f"[ERROR] {model.__name__} NO está registrado en tenant_admin_site. "
                    "Debe estar registrado porque pertenece a TENANT_APPS.",
                )

    def test_public_models_are_not_registered(self):
        """
        Verifica que los modelos del esquema público NO están registrados.

        [OK] Debe pasar: Client, Domain, User (global) NO deben estar registrados
        """
        # Modelos del esquema público que NO deben estar registrados
        public_models = [
            Client,
            Domain,
        ]

        for model in public_models:
            with self.subTest(model=model.__name__):
                self.assertFalse(
                    tenant_admin_site.is_registered(model),
                    f"[ERROR] VULNERABILIDAD: {model.__name__} está registrado en tenant_admin_site. "
                    "Este modelo pertenece al esquema público y NO debe aparecer en el admin de tenant.",
                )

    def test_tenant_admin_site_has_correct_configuration(self):
        """
        Verifica que TenantAdminSite tiene la configuración correcta.

        [OK] Debe pasar: site_header, site_title, index_title deben estar configurados
        """
        self.assertEqual(
            tenant_admin_site.site_header,
            "Administración de la Empresa",
            "El header del admin debe ser 'Administración de la Empresa'",
        )

        self.assertEqual(
            tenant_admin_site.site_title,
            "Portal de Empresa",
            "El título del admin debe ser 'Portal de Empresa'",
        )

        self.assertEqual(
            tenant_admin_site.index_title,
            "Gestión del Tenant",
            "El título del índice debe ser 'Gestión del Tenant'",
        )

    def test_tenant_admin_site_permissions(self):
        """
        Verifica que TenantAdminSite valida permisos correctamente.

        [OK] Debe pasar: Solo usuarios activos y staff pueden acceder
        """
        factory = RequestFactory()

        # Usuario activo y staff (debe tener permiso)
        staff_user = User.objects.create_user(
            email="staff@test.com",
            username="staff",
            password="testpass123",
            is_active=True,
            is_staff=True,
        )

        request = factory.get("/admin/")
        request.user = staff_user

        self.assertTrue(
            tenant_admin_site.has_permission(request),
            "Usuario staff y activo debe tener permiso para acceder al admin de tenant",
        )

        # Usuario activo pero NO staff (NO debe tener permiso)
        regular_user = User.objects.create_user(
            email="regular@test.com",
            username="regular",
            password="testpass123",
            is_active=True,
            is_staff=False,
        )

        request.user = regular_user
        self.assertFalse(
            tenant_admin_site.has_permission(request),
            "Usuario NO staff NO debe tener permiso para acceder al admin de tenant",
        )

        # Usuario staff pero NO activo (NO debe tener permiso)
        inactive_staff = User.objects.create_user(
            email="inactive@test.com",
            username="inactive",
            password="testpass123",
            is_active=False,
            is_staff=True,
        )

        request.user = inactive_staff
        self.assertFalse(
            tenant_admin_site.has_permission(request),
            "Usuario inactivo NO debe tener permiso para acceder al admin de tenant",
        )

    def test_registered_models_list(self):
        """
        Verifica que la lista de modelos registrados solo contiene modelos de tenant.

        [OK] Debe pasar: Solo modelos de TENANT_APPS deben estar en la lista
        """
        registered_models = list(tenant_admin_site._registry.keys())
        registered_model_names = [model.__name__ for model in registered_models]

        # Verificar que hay modelos registrados
        self.assertGreater(
            len(registered_models),
            0,
            "Debe haber al menos un modelo registrado en tenant_admin_site",
        )

        # Verificar que NO hay modelos del esquema público
        public_model_names = ["Client", "Domain", "TenantMembership"]
        for public_model_name in public_model_names:
            self.assertNotIn(
                public_model_name,
                registered_model_names,
                f"[ERROR] VULNERABILIDAD: {public_model_name} está registrado en tenant_admin_site. "
                "Este modelo pertenece al esquema público y NO debe aparecer.",
            )

        # Verificar que SÍ hay modelos de tenant
        tenant_model_names = ["Empresa", "Factura", "AsientoContable"]
        found_tenant_models = [
            name for name in tenant_model_names if name in registered_model_names
        ]

        self.assertGreater(
            len(found_tenant_models),
            0,
            f"Debe haber al menos un modelo de tenant registrado. "
            f"Modelos encontrados: {registered_model_names}",
        )

    def test_ensure_tenant_apps_registered_is_idempotent(self):
        """
        Verifica que ensure_tenant_apps_registered() es idempotente.

        [OK] Debe pasar: Llamar la función múltiples veces no debe causar errores
        """
        # Llamar la función múltiples veces
        ensure_tenant_apps_registered()
        ensure_tenant_apps_registered()
        ensure_tenant_apps_registered()

        # No debe lanzar excepciones
        # Si llegamos aquí, el test pasa
        self.assertTrue(True, "ensure_tenant_apps_registered() debe ser idempotente")

    def test_tenant_admin_site_is_independent(self):
        """
        Verifica que tenant_admin_site es independiente de admin.site.

        [OK] Debe pasar: Los registros en tenant_admin_site no afectan admin.site
        """
        from django.contrib import admin

        # Verificar que Empresa está en tenant_admin_site
        self.assertTrue(
            tenant_admin_site.is_registered(Empresa),
            "Empresa debe estar registrado en tenant_admin_site",
        )

        # Verificar que Empresa también está en admin.site (porque se registró con @admin.register)
        self.assertTrue(
            admin.site.is_registered(Empresa),
            "Empresa debe estar registrado en admin.site también",
        )

        # Verificar que Client NO está en tenant_admin_site
        self.assertFalse(
            tenant_admin_site.is_registered(Client),
            "Client NO debe estar registrado en tenant_admin_site",
        )

        # Verificar que Client SÍ está en admin.site (esquema público)
        self.assertTrue(
            admin.site.is_registered(Client),
            "Client debe estar registrado en admin.site (esquema público)",
        )
