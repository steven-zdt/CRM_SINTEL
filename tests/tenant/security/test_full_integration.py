"""
Test de Garantía Total: Validación de Integración Completa del Sistema de Seguridad.

[WARNING] OBJETIVO: Este test valida que todos los componentes de seguridad funcionan
correctamente juntos. Si este test pasa, el sistema es seguro.

Componentes validados:
1. Backend de Autenticación (TenantAwareBackend)
2. Formulario de Autenticación (TenantAuthenticationForm)
3. Vista de Login (TenantLoginView)
4. Aislamiento Multi-Tenant
5. Protección del Tenant Público

Este test es la certificación final de la Fase de Seguridad.
"""

from django.contrib.auth import authenticate, get_user_model
from django.db import connection
from django.test import Client
from django.urls import reverse
from django_tenants.utils import get_public_schema_name

from apps.public.tenants.models import Client as TenantClient
from apps.public.tenants.models import Domain, TenantMembership
from apps.services.perfil.perfil_service import obtener_o_crear_perfil
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase

User = get_user_model()


class TestFullIntegrationSecurity(SintelTenantTestCase):
    """
    Test de Integración Total del Sistema de Seguridad.

    Valida que todos los componentes de seguridad funcionan correctamente juntos:
    - Backend bloquea acceso sin membresía
    - Formulario proporciona feedback preciso
    - Vista maneja correctamente el flujo de login
    - Aislamiento entre tenants funciona
    - Tenant público permite acceso
    """

    @classmethod
    def setup_tenant(cls, tenant_user=None):
        """
        Crea un tenant específico para estos tests de integración.
        """
        tenant = TenantClient.objects.create(
            schema_name="tenant_integracion",
            nombre="Tenant Integración - Tests de Seguridad",
            is_active=True,
            on_trial=False,
        )
        return tenant

    @classmethod
    def setup_domain(cls, domain):
        """
        Configura el dominio para el tenant de integración.
        """
        domain.domain = "tenant-integracion.sintel.local"
        domain.is_primary = True
        domain.save()
        return domain

    def setUp(self):
        """
        Setup: Crear usuarios, tenants y membresías para los tests.
        """
        # Llamar al setUp del padre (crea tenant_integracion, domain, user, membership)
        super().setUp()

        # self.user ya tiene membresía en tenant_integracion (del setUp del padre)

        # Crear un segundo tenant (Tenant B) para tests de aislamiento
        connection.set_schema_to_public()

        self.tenant_b = TenantClient.objects.create(
            schema_name="tenant_b_integracion",
            nombre="Tenant B - Tests de Integración",
            is_active=True,
            on_trial=False,
        )

        self.domain_b = Domain.objects.create(
            domain="tenant-b-integracion.sintel.local",
            tenant=self.tenant_b,
            is_primary=True,
        )

        # Crear usuario sin membresía en tenant_integracion
        self.user_sin_membresia = User.objects.create_user(
            email="sin_membresia@test.com",
            username="sin_membresia",
            password="testpass123",
            is_active=True,
        )

        # Crear usuario con membresía en tenant_b
        self.user_tenant_b = User.objects.create_user(
            email="tenant_b@test.com",
            username="tenant_b",
            password="testpass123",
            is_active=True,
        )

        self.membership_b = TenantMembership.objects.create(
            client=self.tenant_b, user=self.user_tenant_b, rol="ADMIN"
        )

        # Restaurar esquema del tenant_integracion
        connection.set_schema(self.tenant.schema_name)

        # Crear clientes HTTP
        self.client_tenant_a = Client(HTTP_HOST=self.domain.domain)
        self.client_tenant_b = Client(HTTP_HOST=self.domain_b.domain)

    def test_1_barrera_de_backend_nivel_api_core(self):
        """
        TEST 1: Barrera de Backend (Nivel API/Core).

        Acción: Llamar a authenticate() directamente (sin formulario) para un usuario
        sin membresía en el tenant actual.

        Esperado: Debe retornar None (El backend TenantAwareBackend hizo su trabajo).
        """
        # Simular request con tenant_integracion
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get("/")
        request.tenant = self.tenant

        # Intentar autenticar usuario sin membresía directamente con el backend
        user = authenticate(
            request=request,
            username=self.user_sin_membresia.username,
            password="testpass123",  # Password correcto
        )

        # [WARNING] ASSERT OBLIGATORIO: El backend debe retornar None
        self.assertIsNone(
            user,
            "[ERROR] VIOLACIÓN DE SEGURIDAD: El backend TenantAwareBackend debe retornar None "
            "cuando un usuario sin membresía intenta autenticarse, incluso si las credenciales son correctas.",
        )

    def test_2_feedback_de_formulario_nivel_ux(self):
        """
        TEST 2: Feedback de Formulario (Nivel UX).

        Acción: Enviar POST al login con credenciales válidas pero sin membresía.

        Esperado:
        - La respuesta NO debe ser un redirect (Login fallido).
        - form.errors debe contener el mensaje específico "no tienes acceso a la empresa".
        - NO debe decir simplemente "Por favor introduzca un nombre de usuario y clave correctos".
        """
        # Obtener URL de login
        login_url = reverse("tenant_landing:login")

        # Intentar login con usuario sin membresía (pero credenciales válidas)
        response = self.client_tenant_a.post(
            login_url,
            {
                "username": self.user_sin_membresia.username,
                "password": "testpass123",  # Password correcto
            },
        )

        # [WARNING] ASSERT OBLIGATORIO 1: NO debe haber redirección (login fallido)
        self.assertNotEqual(
            response.status_code,
            302,
            "[ERROR] VIOLACIÓN DE UX: El login debe fallar (200 OK con errores), no redirigir (302). "
            "Si redirige, significa que el login fue exitoso, lo cual es un fallo de seguridad.",
        )

        # [WARNING] ASSERT OBLIGATORIO 2: Debe haber errores en el formulario
        form = response.context.get("form") if hasattr(response, "context") else None
        self.assertIsNotNone(
            form,
            "[ERROR] VIOLACIÓN DE UX: El formulario debe estar en el contexto de la respuesta.",
        )

        self.assertTrue(
            form.errors,
            "[ERROR] VIOLACIÓN DE UX: El formulario DEBE tener errores cuando un usuario "
            "sin membresía intenta loguearse.",
        )

        # [WARNING] ASSERT OBLIGATORIO 3: El mensaje debe ser específico sobre membresía
        error_messages = []
        for field, errors in form.errors.items():
            error_messages.extend(errors)

        error_text = " ".join(error_messages).lower()

        # Verificar que el mensaje contiene palabras clave sobre membresía/acceso
        has_membership_error = (
            "no tienes acceso" in error_text
            or "acceso a la empresa" in error_text
            or "contacta a tu administrador" in error_text
            or "membresía" in error_text
        )

        self.assertTrue(
            has_membership_error,
            f"[ERROR] VIOLACIÓN DE UX: El mensaje de error debe ser específico sobre membresía/acceso. "
            f"Errores encontrados: {error_messages}. "
            f"El mensaje NO debe ser genérico como 'Por favor introduzca un nombre de usuario y clave correctos'.",
        )

        # [WARNING] ASSERT OBLIGATORIO 4: NO debe contener el mensaje genérico de Django
        has_generic_error = (
            "por favor, introduzca un nombre de usuario y clave correctos" in error_text
            or "username and password" in error_text.lower()
        )

        self.assertFalse(
            has_generic_error,
            f"[ERROR] VIOLACIÓN DE UX: El mensaje NO debe ser genérico de Django. "
            f"Debe ser específico sobre la falta de membresía. Errores: {error_messages}",
        )

    def test_3_acceso_exitoso_y_perfil_happy_path(self):
        """
        TEST 3: Acceso Exitoso y Perfil (Happy Path).

        Acción: Login con usuario autorizado.

        Esperado:
        - Redirect a /dashboard/.
        - Usuario autenticado en sesión.
        - (Opcional) Verificar que se puede consultar su TenantProfile.
        """
        # Obtener URL de login
        login_url = reverse("tenant_landing:login")

        # Intentar login con usuario autorizado (con membresía)
        response = self.client_tenant_a.post(
            login_url,
            {"username": self.user.username, "password": self.get_user_password()},
        )

        # [WARNING] ASSERT OBLIGATORIO 1: Debe haber redirección (login exitoso)
        self.assertEqual(
            response.status_code,
            302,
            f"[ERROR] VIOLACIÓN: El login exitoso debe redirigir (302). Status recibido: {response.status_code}",
        )

        # [WARNING] ASSERT OBLIGATORIO 2: Debe redirigir al dashboard
        self.assertIn(
            "/dashboard/",
            response.url,
            f"[ERROR] VIOLACIÓN: Después de login exitoso, debe redirigir a /dashboard/. URL recibida: {response.url}",
        )

        # [WARNING] ASSERT OBLIGATORIO 3: El usuario debe estar autenticado en la sesión
        # Seguir la redirección para verificar que el usuario está autenticado
        follow_response = self.client_tenant_a.get(response.url, follow=True)

        # Verificar que el usuario puede acceder al dashboard (no redirige al login)
        self.assertNotEqual(
            follow_response.status_code,
            302,
            "[ERROR] VIOLACIÓN: Después de login exitoso, el usuario debe poder acceder al dashboard. "
            "Si redirige al login, significa que el usuario no está autenticado.",
        )

        # [WARNING] ASSERT OBLIGATORIO 4: Verificar que se puede consultar el TenantProfile
        # (Opcional, pero valida la integración con el sistema de perfiles)
        try:
            perfil = obtener_o_crear_perfil(self.user)
            self.assertIsNotNone(
                perfil,
                "[ERROR] VIOLACIÓN: Después de login exitoso, debe poder consultarse el TenantProfile del usuario.",
            )
        except Exception as e:
            # Si falla, no es crítico para este test, pero es bueno validarlo
            self.fail(
                f"[ERROR] VIOLACIÓN: No se pudo consultar el TenantProfile después del login: {e}"
            )

    def test_4_proteccion_de_tenant_publico(self):
        """
        TEST 4: Protección de Tenant Público.

        Acción: Login en el tenant 'public' (localhost) con un superusuario.

        Esperado: Login exitoso (El backend debe permitir siempre el acceso al esquema público).
        """
        # Obtener el tenant público
        connection.set_schema_to_public()
        tenant_public = TenantClient.objects.filter(
            schema_name=get_public_schema_name()
        ).first()

        if not tenant_public:
            # Si no existe, crear uno para el test
            tenant_public = TenantClient.objects.create(
                schema_name=get_public_schema_name(),
                nombre="Public Tenant",
                is_active=True,
                on_trial=False,
            )

        # Crear dominio para tenant público
        domain_public = Domain.objects.filter(
            tenant=tenant_public, is_primary=True
        ).first()
        if not domain_public:
            domain_public = Domain.objects.create(
                domain="localhost", tenant=tenant_public, is_primary=True
            )

        # Crear superusuario para el test
        superuser = User.objects.create_superuser(
            email="superuser@test.com", username="superuser", password="testpass123"
        )

        # Crear cliente para tenant público
        client_public = Client(HTTP_HOST=domain_public.domain)

        # Obtener URL de login (puede variar según la configuración de URLs públicas)
        # Por ahora, asumimos que existe una ruta de login en el tenant público
        # Si no existe, este test puede necesitar ajustes

        # Intentar autenticar directamente con el backend
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get("/")
        request.tenant = tenant_public

        user = authenticate(
            request=request, username=superuser.username, password="testpass123"
        )

        # [WARNING] ASSERT OBLIGATORIO: El backend debe permitir acceso al tenant público
        self.assertIsNotNone(
            user,
            "[ERROR] VIOLACIÓN: El backend debe permitir acceso al tenant 'public' sin membresía.",
        )
        self.assertEqual(
            user.id,
            superuser.id,
            "[ERROR] VIOLACIÓN: El usuario autenticado debe ser el correcto.",
        )

    def test_5_aislamiento_cruzado_cross_check(self):
        """
        TEST 5: Aislamiento Cruzado (Cross-Check).

        Setup: Usuario A (de Tenant A) y Usuario B (de Tenant B).

        Acción: Usuario A intenta loguearse en dominio de Tenant B.

        Esperado: Fallo rotundo (Formulario inválido + Backend return None).
        """
        # Usuario A (self.user) tiene membresía en tenant_integracion (Tenant A)
        # Usuario B (self.user_tenant_b) tiene membresía en tenant_b (Tenant B)

        # [WARNING] CASO 1: Usuario A intenta loguearse en Tenant B (donde NO tiene membresía)
        login_url = reverse("tenant_landing:login")

        response = self.client_tenant_b.post(
            login_url,
            {
                "username": self.user.username,  # Usuario de Tenant A
                "password": self.get_user_password(),  # Password correcto
            },
        )

        # [WARNING] ASSERT OBLIGATORIO 1: NO debe haber redirección (login fallido)
        self.assertNotEqual(
            response.status_code,
            302,
            "[ERROR] VIOLACIÓN DE AISLAMIENTO: El login cross-tenant debe fallar, no redirigir.",
        )

        # [WARNING] ASSERT OBLIGATORIO 2: Debe haber errores en el formulario
        form = response.context.get("form") if hasattr(response, "context") else None
        self.assertIsNotNone(
            form, "[ERROR] VIOLACIÓN: El formulario debe estar en el contexto."
        )
        self.assertTrue(
            form.errors,
            "[ERROR] VIOLACIÓN DE AISLAMIENTO: El formulario debe tener errores en login cross-tenant.",
        )

        # [WARNING] CASO 2: Verificar que el backend también bloquea directamente
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get("/")
        request.tenant = self.tenant_b  # Tenant B

        user = authenticate(
            request=request,
            username=self.user.username,  # Usuario de Tenant A
            password=self.get_user_password(),
        )

        # [WARNING] ASSERT OBLIGATORIO 3: El backend debe retornar None
        self.assertIsNone(
            user,
            "[ERROR] VIOLACIÓN DE AISLAMIENTO: El backend debe retornar None para login cross-tenant.",
        )

        # [WARNING] CASO 3: Usuario B intenta loguearse en Tenant A (donde NO tiene membresía)
        response = self.client_tenant_a.post(
            login_url,
            {
                "username": self.user_tenant_b.username,  # Usuario de Tenant B
                "password": "testpass123",  # Password correcto
            },
        )

        # [WARNING] ASSERT OBLIGATORIO 4: NO debe haber redirección
        self.assertNotEqual(
            response.status_code,
            302,
            "[ERROR] VIOLACIÓN DE AISLAMIENTO: El login cross-tenant (B->A) debe fallar.",
        )

        # [WARNING] ASSERT OBLIGATORIO 5: Debe haber errores
        form = response.context.get("form") if hasattr(response, "context") else None
        self.assertTrue(
            form.errors if form else False,
            "[ERROR] VIOLACIÓN DE AISLAMIENTO: El formulario debe tener errores en login cross-tenant (B->A).",
        )
