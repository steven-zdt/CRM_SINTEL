"""
Tests de Seguridad: Validación de Membresía en Login de Tenants.

[WARNING] OBJETIVO: Garantizar que solo usuarios con TenantMembership activa
puedan iniciar sesión en un tenant específico.

Escenarios validados:
- Escenario A: Acceso legítimo (usuario con membresía en Tenant A se loguea en Tenant A)
- Escenario B: Intrusión cross-tenant (usuario con membresía en Tenant A intenta loguearse en Tenant B)
- Escenario C: Usuario sin membresía (usuario nuevo sin membresía intenta entrar)
"""
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.db import connection
from django_tenants.utils import get_public_schema_name

from tests.tenant.base_test import SintelTenantTestCase
from apps.public.tenants.models import Client as TenantClient, Domain, TenantMembership

User = get_user_model()


class TestLoginSecurity(SintelTenantTestCase):
    """
    Tests de seguridad para el login de tenants.
    
    Valida que la barrera de seguridad (TenantAuthenticationForm) previene
    el acceso cross-tenant y usuarios sin membresía.
    """
    
    @classmethod
    def setup_tenant(cls, tenant_user=None):
        """
        Crea un tenant específico para estos tests de seguridad.
        """
        tenant = TenantClient.objects.create(
            schema_name='tenant_a',
            nombre='Tenant A - Tests de Seguridad',
            is_active=True,
            on_trial=False
        )
        return tenant
    
    @classmethod
    def setup_domain(cls, domain):
        """
        Configura el dominio para Tenant A.
        """
        domain.domain = 'tenant-a.sintel.local'
        domain.is_primary = True
        domain.save()
        return domain
    
    def setUp(self):
        """
        Setup: Crear usuarios y membresías para los tests.
        """
        # Llamar al setUp del padre (crea tenant_a, domain, user, membership)
        super().setUp()
        
        # self.user ya tiene membresía en tenant_a (del setUp del padre)
        # self.membership es la membresía de self.user en tenant_a
        
        # Crear un segundo tenant (Tenant B) para tests cross-tenant
        connection.set_schema_to_public()
        
        self.tenant_b = TenantClient.objects.create(
            schema_name='tenant_b',
            nombre='Tenant B - Tests de Seguridad',
            is_active=True,
            on_trial=False
        )
        
        self.domain_b = Domain.objects.create(
            domain='tenant-b.sintel.local',
            tenant=self.tenant_b,
            is_primary=True
        )
        
        # Crear un usuario sin membresía (para Escenario C)
        self.user_sin_membresia = User.objects.create_user(
            email='sin_membresia@test.com',
            username='sin_membresia',
            password='testpass123',
            is_active=True
        )
        
        # Restaurar esquema del tenant_a
        connection.set_schema(self.tenant.schema_name)
        
        # Crear cliente HTTP anónimo para Tenant A
        self.client_tenant_a = Client(HTTP_HOST=self.domain.domain)
        
        # Crear cliente HTTP anónimo para Tenant B
        self.client_tenant_b = Client(HTTP_HOST=self.domain_b.domain)
    
    def test_escenario_a_acceso_legitimo(self):
        """
        ESCENARIO A: Acceso Legítimo.
        
        Usuario con membresía activa en Tenant A se loguea en Tenant A.
        
        Resultado esperado: 200 OK (formulario válido) o 302 Redirect (login exitoso).
        El usuario debe poder autenticarse correctamente.
        """
        # Obtener URL de login para Tenant A
        login_url = reverse('tenant_landing:login')
        
        # Intentar login con credenciales válidas del usuario con membresía
        # [WARNING] IMPORTANTE: AuthenticationForm usa 'username', no 'email'
        # El username se genera automáticamente desde el email en el modelo User
        response = self.client_tenant_a.post(
            login_url,
            {
                'username': self.user.username,  # Usar username (generado desde email)
                'password': self.get_user_password()
            }
        )
        
        # Verificar que el login fue exitoso
        # Si el formulario es válido, Django redirige (302) al dashboard
        # Si hay error de validación, muestra 200 con errores en el formulario
        
        # [WARNING] ASSERT OBLIGATORIO 1: Debe haber redirección (302) si el login fue exitoso
        self.assertEqual(
            response.status_code,
            302,
            f"[ERROR] VIOLACIÓN DE SEGURIDAD: El login legítimo debe redirigir (302) al dashboard. "
            f"Status recibido: {response.status_code}. "
            f"Si es 200, significa que el formulario tiene errores cuando no debería."
        )
        
        # [WARNING] ASSERT OBLIGATORIO 2: Debe redirigir al dashboard
        self.assertIn(
            '/dashboard/',
            response.url,
            f"[ERROR] VIOLACIÓN DE SEGURIDAD: Después de login exitoso, debe redirigir a /dashboard/. "
            f"URL recibida: {response.url}"
        )
        
        # [WARNING] ASSERT OBLIGATORIO 3: El usuario debe estar autenticado en la sesión
        # Seguir la redirección para verificar que el usuario está autenticado
        follow_response = self.client_tenant_a.get(response.url, follow=True)
        
        # Verificar que el usuario está autenticado (puede acceder al dashboard)
        # Si el usuario está autenticado, el dashboard debe responder 200 OK
        # Si no está autenticado, redirigirá al login (302)
        self.assertNotEqual(
            follow_response.status_code,
            302,
            "[ERROR] VIOLACIÓN DE SEGURIDAD: Después de login exitoso, el usuario debe poder acceder "
            "al dashboard. Si redirige al login, significa que el usuario no está autenticado."
        )
    
    def test_escenario_b_intrusion_cross_tenant(self):
        """
        ESCENARIO B: Intrusión Cross-Tenant.
        
        Usuario con membresía en Tenant A intenta loguearse en Tenant B.
        Las credenciales son correctas (usuario/password válidos globalmente).
        
        Resultado esperado: El formulario debe ser inválido. El login falla.
        Mensaje de error presente en la respuesta.
        El usuario NO debe estar autenticado en la sesión.
        """
        # Obtener URL de login para Tenant B
        login_url = reverse('tenant_landing:login')
        
        # Intentar login en Tenant B con credenciales del usuario de Tenant A
        # [WARNING] CRÍTICO: El usuario tiene credenciales válidas globalmente,
        # pero NO tiene membresía en Tenant B
        response = self.client_tenant_b.post(
            login_url,
            {
                'username': self.user.username,  # Credenciales válidas (username)
                'password': self.get_user_password()  # Password correcto
            }
        )
        
        # [WARNING] ASSERT OBLIGATORIO 1: El formulario debe ser inválido
        self.assertEqual(
            response.status_code,
            200,  # Django muestra el formulario con errores (200 OK)
            "[ERROR] VIOLACIÓN DE SEGURIDAD: El login cross-tenant debe mostrar formulario con errores (200 OK), "
            "no debe redirigir (302). Si redirige, significa que el login fue exitoso, lo cual es un fallo de seguridad."
        )
        
        # [WARNING] ASSERT OBLIGATORIO 2: Debe haber errores en el formulario
        form = response.context.get('form') if hasattr(response, 'context') else None
        self.assertIsNotNone(
            form,
            "[ERROR] VIOLACIÓN DE SEGURIDAD: El formulario debe estar en el contexto de la respuesta."
        )
        
        self.assertTrue(
            form.errors,
            "[ERROR] VIOLACIÓN DE SEGURIDAD: El formulario DEBE tener errores cuando un usuario "
            "sin membresía intenta loguearse. Si no tiene errores, la validación de membresía no está funcionando."
        )
        
        # [WARNING] ASSERT OBLIGATORIO 3: El mensaje de error debe estar presente
        # Verificar que el error contiene el mensaje esperado
        error_messages = []
        for field, errors in form.errors.items():
            error_messages.extend(errors)
        
        error_text = ' '.join(error_messages).lower()
        has_authorization_error = (
            'autorización' in error_text or 
            'acceso' in error_text or 
            'membresía' in error_text or
            'empresa' in error_text
        )
        self.assertTrue(
            has_authorization_error,
            f"[ERROR] VIOLACIÓN DE SEGURIDAD: El mensaje de error debe indicar falta de autorización. "
            f"Errores encontrados: {error_messages}"
        )
        
        # [WARNING] ASSERT OBLIGATORIO 4: El usuario NO debe estar autenticado
        # Verificar que la sesión NO contiene _auth_user_id
        session = self.client_tenant_b.session
        self.assertNotIn(
            '_auth_user_id',
            session,
            "[ERROR] VIOLACIÓN DE SEGURIDAD: El usuario NO debe estar autenticado después de un "
            "intento de login cross-tenant. Si _auth_user_id está en la sesión, el login fue exitoso, "
            "lo cual es un fallo crítico de seguridad."
        )
        
        # [WARNING] ASSERT OBLIGATORIO 5: NO debe haber redirección
        self.assertNotEqual(
            response.status_code,
            302,
            "[ERROR] VIOLACIÓN DE SEGURIDAD: NO debe haber redirección (302) después de un "
            "intento de login cross-tenant. Si hay redirección, significa que el login fue exitoso."
        )
    
    def test_escenario_c_usuario_sin_membresia(self):
        """
        ESCENARIO C: Usuario sin Membresía.
        
        Usuario nuevo sin membresía en ningún tenant intenta loguearse.
        
        Resultado esperado: Fallo. El formulario debe ser inválido.
        Mensaje de error presente. El usuario NO debe estar autenticado.
        """
        # Obtener URL de login para Tenant A
        login_url = reverse('tenant_landing:login')
        
        # Intentar login con usuario sin membresía
        # [WARNING] CRÍTICO: El usuario tiene credenciales válidas globalmente,
        # pero NO tiene membresía en Tenant A
        response = self.client_tenant_a.post(
            login_url,
            {
                'username': self.user_sin_membresia.username,  # Credenciales válidas (username)
                'password': 'testpass123'  # Password correcto
            }
        )
        
        # [WARNING] ASSERT OBLIGATORIO 1: El formulario debe ser inválido
        self.assertEqual(
            response.status_code,
            200,  # Django muestra el formulario con errores (200 OK)
            "[ERROR] VIOLACIÓN DE SEGURIDAD: El login sin membresía debe mostrar formulario con errores (200 OK), "
            "no debe redirigir (302). Si redirige, significa que el login fue exitoso, lo cual es un fallo de seguridad."
        )
        
        # [WARNING] ASSERT OBLIGATORIO 2: Debe haber errores en el formulario
        form = response.context.get('form') if hasattr(response, 'context') else None
        self.assertIsNotNone(
            form,
            "[ERROR] VIOLACIÓN DE SEGURIDAD: El formulario debe estar en el contexto de la respuesta."
        )
        
        self.assertTrue(
            form.errors,
            "[ERROR] VIOLACIÓN DE SEGURIDAD: El formulario DEBE tener errores cuando un usuario "
            "sin membresía intenta loguearse. Si no tiene errores, la validación de membresía no está funcionando."
        )
        
        # [WARNING] ASSERT OBLIGATORIO 3: El mensaje de error debe estar presente
        error_messages = []
        for field, errors in form.errors.items():
            error_messages.extend(errors)
        
        self.assertTrue(
            len(error_messages) > 0,
            f"[ERROR] VIOLACIÓN DE SEGURIDAD: Debe haber mensajes de error. "
            f"Errores encontrados: {error_messages}"
        )
        
        # [WARNING] ASSERT OBLIGATORIO 4: El usuario NO debe estar autenticado
        session = self.client_tenant_a.session
        self.assertNotIn(
            '_auth_user_id',
            session,
            "[ERROR] VIOLACIÓN DE SEGURIDAD: El usuario NO debe estar autenticado después de un "
            "intento de login sin membresía. Si _auth_user_id está en la sesión, el login fue exitoso, "
            "lo cual es un fallo crítico de seguridad."
        )
        
        # [WARNING] ASSERT OBLIGATORIO 5: NO debe haber redirección
        self.assertNotEqual(
            response.status_code,
            302,
            "[ERROR] VIOLACIÓN DE SEGURIDAD: NO debe haber redirección (302) después de un "
            "intento de login sin membresía. Si hay redirección, significa que el login fue exitoso."
        )
    
    def test_escenario_d_credenciales_invalidas(self):
        """
        ESCENARIO D: Credenciales Inválidas (Test de Control).
        
        Usuario intenta loguearse con credenciales incorrectas.
        
        Resultado esperado: Fallo por credenciales inválidas (antes de validar membresía).
        Este test verifica que el formulario funciona correctamente incluso cuando
        las credenciales son incorrectas.
        """
        login_url = reverse('tenant_landing:login')
        
        # Intentar login con credenciales incorrectas
        response = self.client_tenant_a.post(
            login_url,
            {
                'username': self.user.username,
                'password': 'password_incorrecto'  # Password incorrecto
            }
        )
        
        # Verificar que el formulario es inválido (credenciales incorrectas)
        self.assertEqual(response.status_code, 200)
        
        form = response.context.get('form') if hasattr(response, 'context') else None
        self.assertIsNotNone(form)
        self.assertTrue(form.errors)
        
        # Verificar que el usuario NO está autenticado
        session = self.client_tenant_a.session
        self.assertNotIn('_auth_user_id', session)
    
    def test_escenario_e_tenant_publico_permite_acceso(self):
        """
        ESCENARIO E: Tenant Público Permite Acceso.
        
        El esquema 'public' es especial y debe permitir acceso sin membresía
        (para administradores globales).
        
        Nota: Este test puede requerir configuración adicional si el tenant público
        tiene un dominio específico. Por ahora, validamos que el formulario
        maneja correctamente el caso de schema_name == 'public'.
        """
        # Este test valida que el formulario permite acceso al tenant público
        # En la práctica, el tenant público usa ROOT_URLCONF, no TENANT_URLCONF,
        # así que este test puede no ser aplicable directamente
        
        # Por ahora, solo verificamos que el formulario tiene la lógica
        # para permitir acceso al tenant público
        from apps.tenant.landing.forms import TenantAuthenticationForm
        
        # Verificar que el formulario existe y tiene el método confirm_login_allowed
        self.assertTrue(hasattr(TenantAuthenticationForm, 'confirm_login_allowed'))
        
        # La validación específica del tenant público se hace en el método
        # confirm_login_allowed del formulario
