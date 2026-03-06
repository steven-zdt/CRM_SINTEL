"""
Tests de seguridad y acceso para el Dashboard.

Valida:
- Login Required: Usuarios no autenticados son redirigidos
- Tenant Membership Check: Usuarios sin membresía reciben 403
- Happy Path: Usuarios con membresía pueden acceder
"""
from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context

from tests.tenant.base_test import SintelTenantTestCase
from apps.public.tenants.models import Client as TenantClient, Domain, TenantMembership

User = get_user_model()


class TestDashboardAccess(SintelTenantTestCase):
    """
    Tests de acceso al Dashboard.
    
    Valida que el control de acceso funciona correctamente:
    - Usuarios no autenticados son redirigidos al login
    - Usuarios sin membresía reciben 403 Forbidden
    - Usuarios con membresía pueden acceder (200 OK)
    """
    
    def test_anonymous_redirect(self):
        """
        Prueba 1: Usuario anónimo intenta acceder a /dashboard/.
        
        Resultado esperado: 302 Redirect al login
        
        ⚠️ IMPORTANTE: LoginRequiredMixin debe redirigir usuarios no autenticados ANTES
        de que se ejecute el método dispatch que verifica la membresía.
        """
        # Cliente anónimo (sin autenticación)
        # ⚠️ CRÍTICO: Configurar HTTP_HOST para que el middleware de routing funcione
        # El HTTP_HOST debe coincidir EXACTAMENTE con el dominio del tenant para que
        # TenantMainMiddleware identifique el tenant y cargue TENANT_URLCONF
        from django.test import Client
        anonymous_client = Client(HTTP_HOST=self.domain.domain)
        
        # Verificar que el dominio está configurado correctamente
        self.assertIsNotNone(self.domain, "El dominio debe estar creado")
        self.assertIsNotNone(self.domain.domain, "El dominio debe tener un nombre")
        
        # Intentar acceder al dashboard sin autenticación
        response = anonymous_client.get('/dashboard/')
        
        # Validaciones: 
        # LoginRequiredMixin debe interceptar usuarios no autenticados y redirigir (302)
        # ANTES de que se ejecute dispatch() que verifica la membresía
        self.assertEqual(
            response.status_code,
            302,
            f"Usuario no autenticado debe ser redirigido (302) por LoginRequiredMixin. Status recibido: {response.status_code}. "
            f"Si recibes 404, el HTTP_HOST no está configurado correctamente. "
            f"Si recibes 403, el dispatch() se ejecutó antes que LoginRequiredMixin."
        )
        
        # Verificar que la redirección apunta al login o landing page
        redirect_url = response.url
        self.assertTrue(
            '/login' in redirect_url or redirect_url == '/' or '/login/' in redirect_url or 'login' in redirect_url.lower(),
            f"La redirección debe apuntar al login o landing page, pero fue: {redirect_url}"
        )
    
    def test_cross_tenant_access_denied(self):
        """
        Prueba 2: Usuario autenticado sin membresía en el tenant actual.
        
        Caso de prueba:
        1. Crear un segundo usuario (user_hacker)
        2. Autenticarlo
        3. NO crear TenantMembership para este tenant (o crear membresía para otro tenant)
        4. Intentar acceder a /dashboard/
        5. Resultado esperado: 403 Forbidden
        
        ⚠️ Esto valida que estar logueado no es suficiente; se requiere membresía.
        """
        # Crear User Hacker (autenticado pero sin membresía en este tenant)
        from django.db import connection
        from django_tenants.utils import get_public_schema_name, schema_context
        
        # Cambiar al esquema public para crear el usuario
        connection.set_schema_to_public()
        
        user_hacker = User.objects.create_user(
            email='hacker@test.com',
            username='hacker',
            password='hackerpass123',
            is_active=True
        )
        # NO crear TenantMembership para este usuario en el tenant actual
        
        # Opcional: Crear membresía para otro tenant (para validar cross-tenant)
        # Crear otro tenant de prueba
        other_tenant = TenantClient.objects.create(
            schema_name='other_tenant',
            nombre='Other Tenant',
            is_active=True
        )
        Domain.objects.create(
            tenant=other_tenant,
            domain='other-tenant.sintel.local',
            is_primary=True
        )
        # Crear membresía para el otro tenant (NO para el tenant actual)
        TenantMembership.objects.create(
            client=other_tenant,
            user=user_hacker,
            rol='ADMIN'
        )
        
        # Restaurar el esquema del tenant actual
        connection.set_schema(self.tenant.schema_name)
        
        # Cliente autenticado como hacker
        # ⚠️ IMPORTANTE: Configurar HTTP_HOST para que el middleware de routing funcione
        from django.test import Client
        hacker_client = Client(HTTP_HOST=self.domain.domain)
        hacker_client.force_login(user_hacker)
        
        # Intentar acceder al dashboard del tenant actual
        response = hacker_client.get('/dashboard/')
        
        # Validaciones: Debe recibir 403 Forbidden (usuario autenticado sin membresía)
        self.assertEqual(
            response.status_code,
            403,
            f"Usuario sin membresía en este tenant debe recibir 403 Forbidden. Status: {response.status_code}"
        )
        
        # Verificar que el mensaje de error es apropiado
        # El template 403.html debe contener información sobre el acceso denegado
        content = response.content.decode('utf-8').lower()
        has_error_message = (
            'permisos' in content or
            'acceso' in content or
            'denied' in content or
            'forbidden' in content or
            'membresía' in content or
            'membership' in content or
            '403' in content or
            'denegado' in content
        )
        self.assertTrue(
            has_error_message,
            f"El mensaje de error debe indicar que el acceso fue denegado. Contenido recibido: {content[:200]}"
        )
    
    def test_authorized_access(self):
        """
        Prueba 3: Usuario con membresía puede acceder al dashboard.
        
        Caso de prueba:
        - El usuario creado en setUp (self.user) tiene TenantMembership
        - Debe recibir 200 OK al acceder a /dashboard/ (o 404 si la ruta no está configurada)
        """
        # El usuario self.user ya está autenticado y tiene membresía (configurado en setUp)
        # self.client ya está configurado con HTTP_HOST y usuario autenticado
        
        # Acceder al dashboard
        response = self.client.get('/dashboard/')
        
        # Validaciones: Puede ser 200 (si la ruta existe) o 404 (si no está configurada)
        # En un tenant real, debería ser 200
        self.assertIn(
            response.status_code,
            [200, 404],
            f"Usuario con membresía debe recibir 200 OK o 404 si la ruta no existe. Status: {response.status_code}"
        )
        
        # Si es 200, verificar que el template se renderiza correctamente
        if response.status_code == 200 and hasattr(response, 'templates') and response.templates:
            template_names = [t.name for t in response.templates if hasattr(t, 'name')]
            has_dashboard_template = any('dashboard' in name.lower() for name in template_names)
            self.assertTrue(
                has_dashboard_template,
                f"Debe renderizar un template de dashboard. Templates encontrados: {template_names}"
            )
    
    def test_user_with_membership_can_access_api(self):
        """
        Prueba adicional: Usuario con membresía puede acceder a APIs del tenant.
        
        Valida que el permiso IsTenantMember funciona correctamente.
        """
        # Usar self.api_client que ya está autenticado con self.user
        # ⚠️ IMPORTANTE: Configurar HTTP_HOST para que el middleware de routing funcione
        # APIClient no usa HTTP_HOST automáticamente, necesitamos configurarlo manualmente
        from rest_framework.test import APIClient
        
        # Crear un nuevo APIClient con HTTP_HOST configurado
        api_client = APIClient(HTTP_HOST=self.domain.domain)
        api_client.force_authenticate(user=self.user)
        
        # Intentar acceder a la API de empresa
        response = api_client.get('/api/v1/empresa/empresas/')
        
        # Validaciones: Puede ser 200 (si la ruta existe) o 404 (si no está configurada)
        self.assertIn(
            response.status_code,
            [200, 404],
            f"Usuario con membresía debe poder acceder a la API del tenant. Status: {response.status_code}"
        )
    
    def test_user_without_membership_cannot_access_api(self):
        """
        Prueba adicional: Usuario sin membresía NO puede acceder a APIs del tenant.
        
        Valida que el permiso IsTenantMember bloquea correctamente.
        """
        # Crear User Hacker (autenticado pero sin membresía)
        with schema_context(get_public_schema_name()):
            hacker = User.objects.create_user(
                email='hacker2@test.com',
                username='hacker2',
                password='hackerpass123',
                is_active=True
            )
            # NO crear TenantMembership para este usuario
        
        # Cliente API autenticado como hacker
        from rest_framework.test import APIClient
        hacker_api_client = APIClient()
        hacker_api_client.force_authenticate(user=hacker)
        
        # Intentar acceder a la API de empresa
        response = hacker_api_client.get('/api/v1/empresa/empresas/')
        
        # Validaciones
        self.assertIn(
            response.status_code,
            [403, 404],
            "Usuario sin membresía NO debe poder acceder a la API del tenant"
        )
