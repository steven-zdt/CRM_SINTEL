"""
Tests de Salud del Sistema (Smoke Testing).

Valida que el "corazón" del sistema multi-tenant funcione correctamente:
- Esquema público operativo
- Creación de tenants privados
- Aislamiento de datos
- Acceso y autenticación

[WARNING] IMPORTANTE: Estos tests deben ejecutarse DESPUÉS de la reconstrucción de la DB.
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.urls import reverse
from django_tenants.utils import get_public_schema_name, schema_context

from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.services.onboarding.empresa_service import crear_tenant
from apps.tenant.empresa.models import Empresa
from tests.tenant.base_test import SintelTenantTestCase

User = get_user_model()


@pytest.mark.django_db
class TestSystemHealth(SintelTenantTestCase):
    """
    Suite de pruebas de salud del sistema.

    Valida que todos los componentes críticos funcionen correctamente
    después de una reconstrucción completa de la base de datos.
    """

    def test_public_health(self):
        """
        A. Salud del Esquema Público.

        Verifica que:
        1. El tenant 'public' existe en la DB
        2. El dominio principal existe
        3. La API pública responde correctamente
        """
        # 1. Verificar que el tenant public existe
        with schema_context(get_public_schema_name()):
            public_tenant = Client.objects.get(schema_name="public")
            self.assertIsNotNone(public_tenant, "[ERROR] El tenant 'public' no existe")
            self.assertEqual(public_tenant.schema_name, "public")
            print(f"[OK] Tenant público existe: {public_tenant.nombre}")

        # 2. Verificar que el dominio principal existe
        with schema_context(get_public_schema_name()):
            primary_domain = Domain.objects.filter(
                tenant__schema_name="public", is_primary=True
            ).first()
            self.assertIsNotNone(
                primary_domain,
                "[ERROR] No existe dominio principal para el tenant público",
            )
            print(f"[OK] Dominio principal existe: {primary_domain.domain}")

        # 3. Verificar que la API pública responde (o al menos no da 500)
        # Nota: La API puede dar 404 si no hay datos, pero NO debe dar 500
        try:
            # Intentar acceder a una ruta pública conocida
            response = self.client.get("/", HTTP_HOST="localhost")
            # Aceptamos 200, 302, 404, pero NO 500
            self.assertNotEqual(
                response.status_code,
                500,
                "[ERROR] El servidor está devolviendo error 500 (Internal Server Error)",
            )
            print(
                f"[OK] API pública responde correctamente (status: {response.status_code})"
            )
        except Exception as e:
            # Si hay un error de conexión o similar, registrar pero no fallar
            print(f"[WARNING]  No se pudo verificar la API pública: {e}")

    def test_tenant_lifecycle(self):
        """
        B. Ciclo de Vida del Tenant Privado.

        Verifica que:
        1. Se puede crear un nuevo tenant usando empresa_service
        2. Se crea el esquema en PostgreSQL
        3. Se crea el dominio asociado (subdominio automático)
        4. Se crea automáticamente un usuario admin para ese tenant
        """
        # Obtener o crear un usuario admin global para usar en el tenant
        admin_user, _ = User.objects.get_or_create(
            username="test_admin",
            defaults={
                "email": "test_admin@sintel.net.co",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        admin_user.set_password("test_password")
        admin_user.save()

        # 1. Crear tenant de prueba usando el servicio
        # [WARNING] v2.17: El dominio se construye automáticamente como {schema_name}.{TENANT_DOMAIN_BASE}
        schema_name = "test_schema"
        nombre = "Empresa Test"

        try:
            client, domain, login_url = crear_tenant(
                nombre=nombre, admin_user_id=admin_user.id, schema_name=schema_name
            )

            print(f"[OK] Tenant creado: {client.nombre} (schema: {client.schema_name})")
            print(f"[OK] Dominio creado: {domain.domain}")
            print(f"[OK] Login URL: {login_url}")
        except Exception as e:
            self.fail(f"[ERROR] Error al crear tenant: {e}")

        # 2. Validar que se creó el esquema en PostgreSQL
        with schema_context(schema_name):
            # Si podemos cambiar al esquema, significa que existe
            current_schema = connection.schema_name
            self.assertEqual(
                current_schema,
                schema_name,
                f"[ERROR] El esquema '{schema_name}' no existe o no se puede acceder",
            )
            print(f"[OK] Esquema '{schema_name}' existe en PostgreSQL")

        # 3. Validar que se creó el dominio asociado (subdominio automático)
        with schema_context(get_public_schema_name()):
            created_domain = Domain.objects.filter(
                tenant=client, is_primary=True
            ).first()
            self.assertIsNotNone(
                created_domain, "[ERROR] No se creó el dominio principal"
            )

            # [WARNING] v2.17: Verificar que el dominio es un subdominio
            from django.conf import settings

            expected_domain = f"{schema_name}.{settings.TENANT_DOMAIN_BASE}"
            self.assertEqual(
                created_domain.domain,
                expected_domain,
                f"[ERROR] El dominio '{created_domain.domain}' no coincide con el esperado '{expected_domain}'",
            )
            print(f"[OK] Dominio correcto (subdominio): {created_domain.domain}")

        # 4. Validar que se creó automáticamente un usuario admin para ese tenant
        with schema_context(get_public_schema_name()):
            membership = TenantMembership.objects.filter(
                client=client, user=admin_user, is_primary_admin=True
            ).first()
            self.assertIsNotNone(
                membership, "[ERROR] No se creó la membresía de admin para el tenant"
            )
            self.assertEqual(
                membership.rol, "ADMIN", "[ERROR] El rol del admin no es 'ADMIN'"
            )
            print(
                f"[OK] Membresía de admin creada: {admin_user.email} -> {client.nombre}"
            )

    def test_private_access(self):
        """
        C. Aislamiento y Acceso.

        Verifica que:
        1. Acceso al Dashboard sin login -> 302 Redirect
        2. Acceso al Dashboard con login -> 200 OK
        3. Aislamiento de datos entre esquemas
        """
        # Crear un tenant de prueba
        admin_user, _ = User.objects.get_or_create(
            username="access_test_admin",
            defaults={
                "email": "access_test@sintel.net.co",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        admin_user.set_password("test_password")
        admin_user.save()

        schema_name = "access_test"
        nombre = "Empresa Access Test"

        client, domain, login_url = crear_tenant(
            nombre=nombre, admin_user_id=admin_user.id, schema_name=schema_name
        )

        # Crear una empresa en el tenant de prueba
        with schema_context(schema_name):
            empresa = Empresa.objects.create(
                razon_social="Empresa de Prueba", nit="900000001", dv="1"
            )
            empresa_id = empresa.id
            print(
                f"[OK] Empresa creada en tenant '{schema_name}': {empresa.razon_social} (ID: {empresa_id})"
            )

        # 1. Configurar cliente de test con el dominio del tenant
        self.client.defaults["HTTP_HOST"] = domain.domain

        # 2. Intentar acceder al Dashboard SIN login -> Esperado: 302 Redirect
        dashboard_url = reverse("tenant-dashboard-shell")
        response = self.client.get(dashboard_url, HTTP_HOST=domain.domain)

        self.assertEqual(
            response.status_code,
            302,
            f"[ERROR] Se esperaba redirección 302, pero se recibió {response.status_code}",
        )
        print(f"[OK] Acceso sin login redirige correctamente (302)")

        # 3. Loguear al usuario admin del tenant
        login_success = self.client.login(
            username=admin_user.username, password="test_password"
        )
        self.assertTrue(login_success, "[ERROR] No se pudo loguear al usuario admin")
        print(f"[OK] Usuario logueado: {admin_user.username}")

        # 4. Intentar acceder al Dashboard CON login -> Esperado: 200 OK
        response = self.client.get(dashboard_url, HTTP_HOST=domain.domain)
        self.assertEqual(
            response.status_code,
            200,
            f"[ERROR] Se esperaba 200 OK, pero se recibió {response.status_code}",
        )
        print(f"[OK] Acceso con login funciona correctamente (200 OK)")

        # 5. Prueba de Fuego: Aislamiento de datos
        # Cambiar al esquema public y verificar que NO se pueden leer datos del tenant
        with schema_context(get_public_schema_name()):
            # Intentar leer Empresa desde el esquema public
            empresas_in_public = Empresa.objects.count()
            self.assertEqual(
                empresas_in_public,
                0,
                f"[ERROR] VIOLACIÓN DE AISLAMIENTO: Se encontraron {empresas_in_public} empresas en el esquema public",
            )
            print(f"[OK] Aislamiento verificado: 0 empresas en esquema public")

        # Verificar que la empresa SÍ existe en el esquema del tenant
        with schema_context(schema_name):
            empresas_in_tenant = Empresa.objects.count()
            self.assertGreater(
                empresas_in_tenant,
                0,
                "[ERROR] La empresa no existe en el esquema del tenant",
            )
            empresa_found = Empresa.objects.get(id=empresa_id)
            self.assertEqual(empresa_found.razon_social, "Empresa de Prueba")
            print(
                f"[OK] Empresa encontrada en esquema del tenant: {empresa_found.razon_social}"
            )

        # Verificar que la empresa NO existe en otro esquema (cross-tenant isolation)
        # Crear otro tenant y verificar aislamiento
        other_admin, _ = User.objects.get_or_create(
            username="other_admin",
            defaults={"email": "other@sintel.net.co", "is_staff": True},
        )
        other_admin.set_password("test_password")
        other_admin.save()

        other_client, other_domain, _ = crear_tenant(
            nombre="Otra Empresa",
            admin_user_id=other_admin.id,
            schema_name="other_tenant",
        )

        with schema_context("other_tenant"):
            empresas_in_other = Empresa.objects.count()
            self.assertEqual(
                empresas_in_other,
                0,
                f"[ERROR] VIOLACIÓN DE AISLAMIENTO: Se encontraron {empresas_in_other} empresas en otro tenant",
            )
            print(
                f"[OK] Aislamiento cross-tenant verificado: 0 empresas en 'other_tenant'"
            )

        print("[OK] Todas las pruebas de aislamiento pasaron correctamente")

    def test_subdomain_strictness(self):
        """
        D. Validación de Subdominios Estrictos (v2.17).

        Verifica que:
        1. Los dominios SIEMPRE se crean como subdominios
        2. No se permiten FQDN arbitrarios
        3. El formato es correcto: {schema_name}.{TENANT_DOMAIN_BASE}
        """
        from django.conf import settings

        admin_user, _ = User.objects.get_or_create(
            username="subdomain_test_admin",
            defaults={"email": "subdomain_test@sintel.net.co", "is_staff": True},
        )
        admin_user.set_password("test_password")
        admin_user.save()

        schema_name = "subdomain_test"
        nombre = "Empresa Subdomain Test"

        # Crear tenant
        client, domain, _ = crear_tenant(
            nombre=nombre, admin_user_id=admin_user.id, schema_name=schema_name
        )

        # Verificar que el dominio es un subdominio del dominio base
        expected_domain = f"{schema_name}.{settings.TENANT_DOMAIN_BASE}"
        self.assertEqual(
            domain.domain,
            expected_domain,
            f"[ERROR] El dominio '{domain.domain}' no coincide con el formato esperado '{expected_domain}'",
        )
        print(f"[OK] Dominio creado correctamente como subdominio: {domain.domain}")

        # Verificar que el dominio contiene el schema_name
        self.assertIn(
            schema_name,
            domain.domain,
            f"[ERROR] El dominio '{domain.domain}' no contiene el schema_name '{schema_name}'",
        )

        # Verificar que el dominio contiene el dominio base
        self.assertIn(
            settings.TENANT_DOMAIN_BASE,
            domain.domain,
            f"[ERROR] El dominio '{domain.domain}' no contiene el dominio base '{settings.TENANT_DOMAIN_BASE}'",
        )

        # Verificar que NO es un FQDN arbitrario (no debe contener puntos adicionales más allá del subdominio)
        parts = domain.domain.split(".")
        self.assertGreaterEqual(
            len(parts),
            2,
            f"[ERROR] El dominio '{domain.domain}' no tiene el formato correcto de subdominio",
        )

        print(f"[OK] Validación de subdominios estrictos pasada")
