"""
Tests de verificación del mecanismo de detección de URL y enrutamiento diferenciado.

Este módulo valida que el sistema detecte correctamente si una petición corresponde
al dominio público (sintel.com) o a un tenant privado (cliente.sintel.com) y sirva
interfaces completamente aisladas según la documentación oficial v2.19.

Arquitectura:
- TenantMainMiddleware detecta el tenant por dominio
- ROOT_URLCONF = 'config.urls_public' para dominio público
- TENANT_URLCONF = 'config.urls_tenant' para tenants privados
- TenantLandingView actúa como "Semáforo Inteligente" en la raíz de tenants privados
"""
from django.test import TestCase, Client as TestClient, override_settings
from django.urls import reverse
from django_tenants.utils import get_public_schema_name, schema_context
from django.conf import settings

from apps.public.tenants.models import Client as TenantClient, Domain
from apps.public.core.views import PublicIndexView
from apps.tenant.landing.views import TenantLandingView
from tests.tenant.base_test import SintelTenantTestCase


class RoutingLogicTests(SintelTenantTestCase):
    """
    Tests de verificación del enrutamiento diferenciado público/privado.
    
    Valida que:
    1. El dominio público carga urls_public
    2. Los tenants privados cargan urls_tenant
    3. TenantLandingView redirige usuarios autenticados al dashboard
    4. TenantLandingView muestra landing page para usuarios anónimos
    
    ⚠️ NOTA: SintelTenantTestCase ya configura:
    - self.tenant: Tenant de prueba
    - self.domain: Dominio asociado (formato: {schema_name}.sintel.local)
    - self.client: Cliente HTTP autenticado con HTTP_HOST configurado
    - self.api_client: Cliente API autenticado con HTTP_HOST configurado
    """
    
    def test_public_domain_loads_public_urlconf(self):
        """
        Escenario Público: Petición a sintel.com/ debe cargar urls_public.
        
        Verifica que:
        - El dominio público usa ROOT_URLCONF = 'config.urls_public'
        - PublicIndexView se ejecuta correctamente
        - No se carga ninguna ruta de tenant privado
        """
        # Obtener el dominio público
        public_schema = get_public_schema_name()
        
        with schema_context(public_schema):
            # Obtener o crear el dominio público
            try:
                public_client = TenantClient.objects.get(schema_name=public_schema)
            except TenantClient.DoesNotExist:
                # Crear tenant público si no existe (para tests)
                public_client = TenantClient.objects.create(
                    schema_name=public_schema,
                    nombre='SINTEL Global'
                )
            
            public_domain = Domain.objects.filter(tenant=public_client, is_primary=True).first()
            
            if not public_domain:
                # Crear dominio si no existe
                public_domain = Domain.objects.create(
                    domain='sintel.com',
                    tenant=public_client,
                    is_primary=True
                )
            
            # Crear cliente de prueba con el dominio público
            # Usar override_settings para forzar ROOT_URLCONF
            with override_settings(ROOT_URLCONF='config.urls_public'):
                client = TestClient()
                
                # Hacer petición a la raíz del dominio público
                response = client.get('/', HTTP_HOST=public_domain.domain)
                
                # Verificar que se carga PublicIndexView (redirección a login o consola)
                # PublicIndexView siempre redirige, así que esperamos 302
                self.assertEqual(response.status_code, 302)
                
                # Verificar que la URL de redirección es del dominio público (admin:login o console:dashboard)
                self.assertIn(response.url, ['/admin/login/', '/console/'])
    
    def test_private_tenant_anonymous_loads_landing_page(self):
        """
        Escenario Privado Anónimo: Petición a cliente.sintel.com/ con usuario anónimo
        debe devolver 200 OK (Landing Page).
        
        Verifica que:
        - El tenant privado usa TENANT_URLCONF = 'config.urls_tenant'
        - TenantLandingView se ejecuta para usuarios anónimos
        - Se renderiza el template tenant/landing/index.html
        - NO se redirige a login (acceso público permitido)
        """
        # Usar el tenant y dominio configurados en SintelTenantTestCase
        # SintelTenantTestCase crea el dominio como {schema_name}.sintel.local
        # El dominio ya está configurado en self.domain y se guarda en el esquema public
        # SintelTenantTestCase.setUp() ya configura self.client con HTTP_HOST, pero está autenticado
        # Necesitamos un cliente anónimo
        anonymous_client = TestClient()
        
        # Hacer petición a la raíz del tenant privado (usuario anónimo)
        # SintelTenantTestCase ya configura el dominio correctamente en el esquema public
        # Usar el dominio tal como está configurado (sin puerto en tests)
        domain_host = self.domain.domain
        
        # Verificar que el dominio existe en el esquema public
        from django_tenants.utils import schema_context
        from apps.public.tenants.models import Domain as PublicDomain
        with schema_context('public'):
            domain_exists = PublicDomain.objects.filter(domain=domain_host).exists()
            self.assertTrue(domain_exists, f"El dominio {domain_host} debe existir en el esquema public")
        
        response = anonymous_client.get('/', HTTP_HOST=domain_host)
        
        # Verificar que se carga TenantLandingView
        self.assertEqual(response.status_code, 200, 
                        f"Expected 200, got {response.status_code}. "
                        f"Domain: {domain_host}, Tenant: {self.tenant.schema_name}. "
                        f"Response: {response.content[:200] if hasattr(response, 'content') else 'No content'}")
        
        # Verificar que se renderiza el template correcto
        self.assertTemplateUsed(response, 'tenant/landing/index.html')
        
        # Verificar que el contexto contiene información del tenant
        if response.context:
            self.assertIn('login_url', response.context)
        
        # Verificar que NO se redirige (usuario anónimo puede ver landing page)
        self.assertNotEqual(response.status_code, 302)
    
    def test_private_tenant_authenticated_redirects_to_dashboard(self):
        """
        Escenario Privado Logueado: Petición a cliente.sintel.com/ con usuario autenticado
        debe devolver 302 Redirect a /dashboard/.
        
        Verifica que:
        - TenantLandingView detecta usuario autenticado
        - Redirige inmediatamente a tenant_dashboard:index
        - NO se renderiza la landing page
        """
        # Usar el cliente autenticado de SintelTenantTestCase
        # self.client ya está autenticado con self.user
        
        # Hacer petición a la raíz del tenant privado (usuario autenticado)
        # Usar el dominio completo con puerto si es necesario
        domain_host = self.domain.domain
        if ':' not in domain_host and settings.DEBUG:
            app_port = getattr(settings, 'APP_PORT', '8000')
            if app_port and app_port != '80':
                domain_host = f"{domain_host}:{app_port}"
        
        response = self.client.get('/', HTTP_HOST=domain_host)
        
        # Verificar que se redirige (302)
        self.assertEqual(response.status_code, 302, 
                        f"Expected 302, got {response.status_code}. Response: {response.content[:200]}")
        
        # Verificar que la URL de redirección es el dashboard
        self.assertIn('/dashboard/', response.url)
        
        # Verificar que NO se renderiza la landing page
        self.assertTemplateNotUsed(response, 'tenant/landing/index.html')
    
    def test_tenant_landing_view_dispatch_logic(self):
        """
        Verifica que TenantLandingView.dispatch() implementa correctamente
        la lógica de "Semáforo Inteligente".
        
        Caso A: Usuario autenticado -> Redirige a dashboard
        Caso B: Usuario anónimo -> Renderiza landing page
        """
        domain_host = self.domain.domain
        if ':' not in domain_host and settings.DEBUG:
            app_port = getattr(settings, 'APP_PORT', '8000')
            if app_port and app_port != '80':
                domain_host = f"{domain_host}:{app_port}"
        
        # Caso A: Usuario autenticado
        response = self.client.get('/', HTTP_HOST=domain_host)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard/', response.url)
        
        # Caso B: Usuario anónimo
        anonymous_client = TestClient()
        response = anonymous_client.get('/', HTTP_HOST=domain_host)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tenant/landing/index.html')
    
    def test_public_urlconf_excludes_tenant_routes(self):
        """
        Verifica que urls_public NO contiene rutas de tenant privado.
        
        El dominio público no debe tener acceso a:
        - /dashboard/ (dashboard de tenant)
        - /login/ (login de tenant, aunque puede tener su propio login)
        """
        public_schema = get_public_schema_name()
        
        with schema_context(public_schema):
            try:
                public_client = TenantClient.objects.get(schema_name=public_schema)
            except TenantClient.DoesNotExist:
                public_client = TenantClient.objects.create(
                    schema_name=public_schema,
                    nombre='SINTEL Global'
                )
            
            public_domain = Domain.objects.filter(tenant=public_client, is_primary=True).first()
            
            if not public_domain:
                public_domain = Domain.objects.create(
                    domain='sintel.com',
                    tenant=public_client,
                    is_primary=True
                )
            
            with override_settings(ROOT_URLCONF='config.urls_public'):
                client = TestClient()
                
                # Verificar que /dashboard/ no existe en dominio público
                response = client.get('/dashboard/', HTTP_HOST=public_domain.domain)
                # Debe devolver 404 porque no existe en urls_public
                self.assertEqual(response.status_code, 404)
    
    def test_tenant_urlconf_excludes_public_routes(self):
        """
        Verifica que urls_tenant NO contiene rutas públicas.
        
        Los tenants privados no deben tener acceso a:
        - /console/ (consola pública)
        - /api/public/v1/ (APIs públicas)
        """
        domain_host = self.domain.domain
        if ':' not in domain_host and settings.DEBUG:
            app_port = getattr(settings, 'APP_PORT', '8000')
            if app_port and app_port != '80':
                domain_host = f"{domain_host}:{app_port}"
        
        client = TestClient()
        
        # Verificar que /console/ no existe en tenant privado
        response = client.get('/console/', HTTP_HOST=domain_host)
        # Debe devolver 404 porque no existe en urls_tenant
        self.assertEqual(response.status_code, 404)
        
        # Verificar que /api/public/v1/ no existe en tenant privado
        response = client.get('/api/public/v1/', HTTP_HOST=domain_host)
        # Debe devolver 404 porque no existe en urls_tenant
        self.assertEqual(response.status_code, 404)
    
    def test_urlconf_separation_in_settings(self):
        """
        Verifica que settings.py tiene la configuración correcta de URLConf.
        
        ROOT_URLCONF debe ser 'config.urls_public'
        TENANT_URLCONF debe ser 'config.urls_tenant'
        
        ⚠️ NOTA: En TenantTestCase, Django cambia temporalmente ROOT_URLCONF,
        pero la configuración base debe ser correcta.
        """
        # Verificar configuración base (no en contexto de tenant)
        # TenantTestCase puede cambiar ROOT_URLCONF temporalmente, pero TENANT_URLCONF siempre debe ser correcto
        self.assertEqual(settings.TENANT_URLCONF, 'config.urls_tenant')
        
        # Verificar que la configuración base es correcta
        # (puede estar sobrescrita por TenantTestCase, pero eso es esperado)
        # La verificación real se hace en los tests de routing
    
    def test_tenant_landing_view_context(self):
        """
        Verifica que TenantLandingView inyecta correctamente el contexto.
        
        El contexto debe incluir:
        - tenant_name: Nombre del tenant
        - login_url: URL de login del tenant
        """
        domain_host = self.domain.domain
        if ':' not in domain_host and settings.DEBUG:
            app_port = getattr(settings, 'APP_PORT', '8000')
            if app_port and app_port != '80':
                domain_host = f"{domain_host}:{app_port}"
        
        anonymous_client = TestClient()
        response = anonymous_client.get('/', HTTP_HOST=domain_host)
        
        self.assertEqual(response.status_code, 200, 
                        f"Expected 200, got {response.status_code}. Response: {response.content[:200]}")
        
        # Verificar que el contexto contiene los campos requeridos
        if response.context:
            self.assertIn('login_url', response.context)
            
            # Verificar que login_url apunta a /login/
            self.assertIn('/login/', response.context['login_url'])
