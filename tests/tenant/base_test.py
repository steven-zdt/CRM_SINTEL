"""
Clase base reutilizable para tests de tenants.

[WARNING] IMPORTANTE: Todas las pruebas que involucren modelos dentro de TENANT_APPS
deben heredar de SintelTenantTestCase en lugar de django.test.TestCase.

Arquitectura:
- Hereda de TenantTestCase de django-tenants
- Configura automáticamente un tenant de prueba
- Crea un usuario admin con TenantMembership
- Proporciona un APIClient autenticado listo para usar

Uso:
    from tests.tenant.base_test import SintelTenantTestCase

    class MyTest(SintelTenantTestCase):
        def test_something(self):
            # self.tenant está disponible
            # self.user está disponible (admin del tenant)
            # self.api_client está disponible (autenticado)
            response = self.api_client.get('/api/v1/empresa/empresas/')
            self.assertEqual(response.status_code, 200)
"""

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework.test import APIClient

from apps.public.tenants.models import Client as TenantClient
from apps.public.tenants.models import Domain, TenantMembership

User = get_user_model()


class SintelTenantTestCase(TenantTestCase):
    """
    Clase base para tests de tenants en SINTEL.

    Configura automáticamente:
    - Un tenant de prueba (Client)
    - Un dominio asociado (test.sintel.local)
    - Un usuario admin con TenantMembership
    - Un APIClient autenticado

    [WARNING] IMPORTANTE: TenantTestCase maneja automáticamente:
    - La creación y destrucción del esquema del tenant
    - El cambio de esquema antes y después de cada test
    - La limpieza de datos al finalizar
    """

    @classmethod
    def setup_tenant(cls, tenant_user=None):
        """
        Crea un tenant de prueba.

        [WARNING] IMPORTANTE: Este método es llamado automáticamente por TenantTestCase como método de clase.
        Debe retornar una instancia de Client (modelo de tenant).

        Args:
            tenant_user: Parámetro opcional (no usado en esta implementación)

        Returns:
            Client: Objeto tenant creado
        """
        # TenantTestCase ya está en el esquema 'public' por defecto
        # Crear tenant de prueba
        # Usar un schema_name único basado en el nombre de la clase
        schema_name = (
            f"test_{cls.__name__.lower().replace('test', '').replace('case', '')}"
        )
        if not schema_name or schema_name == "test_":
            schema_name = "test_tenant"

        # Delete any existing tenant with this schema name to avoid UniqueViolation
        TenantClient.objects.filter(schema_name=schema_name).delete()

        tenant = TenantClient.objects.create(
            schema_name=schema_name,
            nombre=f"Test Tenant - {cls.__name__}",
            is_active=True,
            on_trial=True,
        )

        return tenant

    @classmethod
    def setup_domain(cls, domain):
        """
        Configura el dominio asociado al tenant de prueba.

        [WARNING] IMPORTANTE: Este método es llamado automáticamente por TenantTestCase como método de clase.
        El parámetro 'domain' es el objeto Domain ya creado por TenantTestCase.
        Podemos modificarlo o simplemente retornarlo.

        Args:
            domain: Objeto Domain ya creado por TenantTestCase

        Returns:
            Domain: Objeto dominio (modificado o sin cambios)
        """
        # TenantTestCase ya crea el domain automáticamente
        # Solo necesitamos configurarlo o retornarlo tal cual
        # Si necesitamos modificarlo, lo hacemos aquí
        domain.domain = f"{domain.tenant.schema_name}.sintel.local"
        domain.is_primary = True
        domain.save()

        return domain

    def setUp(self):
        """
        Configuración inicial para cada test.

        Crea:
        - Usuario admin global (self.user)
        - TenantMembership (relación usuario-tenant)
        - APIClient autenticado (self.api_client)
        - Cliente HTTP estándar con HTTP_HOST configurado (self.client)
        """
        # Llamar al setUp del padre (TenantTestCase)
        # Esto crea automáticamente self.tenant y self.domain mediante setup_tenant y setup_domain
        super().setUp()

        # [WARNING] IMPORTANTE: Configurar ROOT_URLCONF para usar TENANT_URLCONF
        # TenantTestCase no lo hace automáticamente, necesitamos hacerlo manualmente
        from django.conf import settings
        from django.test import override_settings
        from django.urls import clear_url_caches, set_urlconf

        # Configurar el ROOT_URLCONF para usar las URLs del tenant
        # Esto es necesario para que las URLs se resuelvan correctamente
        self.urlconf_override = override_settings(ROOT_URLCONF=settings.TENANT_URLCONF)
        self.urlconf_override.enable()
        clear_url_caches()
        set_urlconf(settings.TENANT_URLCONF)

        # Crear usuario admin global (en el esquema public)
        # Necesitamos cambiar al esquema public para crear el usuario
        from django.db import connection
        from django_tenants.utils import get_public_schema_name

        connection.set_schema_to_public()

        self.user = self.setup_user()

        # Crear TenantMembership (relación usuario-tenant)
        # Esto debe hacerse en el esquema public
        self.membership = self.setup_membership()

        # Restaurar el esquema del tenant
        connection.set_schema(self.tenant.schema_name)

        # Crear APIClient autenticado con HTTP_HOST configurado
        # [WARNING] VITAL: Configurar HTTP_HOST para que el middleware de routing funcione
        self.api_client = APIClient(HTTP_HOST=self.domain.domain)
        self.api_client.force_authenticate(user=self.user)

        # Crear cliente HTTP estándar con HTTP_HOST configurado
        # [WARNING] VITAL: Configurar HTTP_HOST para que el middleware de routing funcione
        from django.test import Client

        self.client = Client(HTTP_HOST=self.domain.domain)
        self.client.force_login(self.user)

    def tearDown(self):
        """
        Limpieza después de cada test.
        """
        # Restaurar el ROOT_URLCONF original
        if hasattr(self, "urlconf_override"):
            self.urlconf_override.disable()

        # Llamar al tearDown del padre
        super().tearDown()

    def setup_user(self):
        """
        Crea un usuario admin para el tenant de prueba.

        [WARNING] IMPORTANTE: Este método debe ejecutarse en el esquema public.

        Returns:
            User: Objeto usuario creado
        """
        # Crear usuario admin
        # Nota: User está en el esquema public, así que debe estar en public para crearlo
        user = User.objects.create_user(
            email=self.get_user_email(),
            username=self.get_username(),
            password=self.get_user_password(),
            is_active=True,
            is_staff=True,
        )

        return user

    def setup_membership(self):
        """
        Crea la relación TenantMembership entre el usuario y el tenant.

        [WARNING] IMPORTANTE: Este método debe ejecutarse en el esquema public.

        Returns:
            TenantMembership: Objeto membresía creado
        """
        membership = TenantMembership.objects.create(
            client=self.tenant, user=self.user, rol="ADMIN", is_primary_admin=True
        )

        return membership

    def get_tenant_schema_name(self):
        """
        Retorna el nombre del esquema para el tenant de prueba.

        Puede ser sobrescrito en clases hijas para personalizar.

        Returns:
            str: Nombre del esquema (ej: 'test_tenant')
        """
        # Usar el nombre de la clase de test como base para el schema_name
        class_name = (
            self.__class__.__name__.lower().replace("test", "").replace("case", "")
        )
        return f"test_{class_name}" if class_name else "test_tenant"

    def get_tenant_name(self):
        """
        Retorna el nombre del tenant de prueba.

        Puede ser sobrescrito en clases hijas para personalizar.

        Returns:
            str: Nombre del tenant (ej: 'Test Tenant')
        """
        return f"Test Tenant - {self.__class__.__name__}"

    def get_tenant_domain(self):
        """
        Retorna el dominio para el tenant de prueba.

        Puede ser sobrescrito en clases hijas para personalizar.

        Returns:
            str: Dominio (ej: 'test.sintel.local')
        """
        schema_name = self.get_tenant_schema_name()
        return f"{schema_name}.sintel.local"

    def get_user_email(self):
        """
        Retorna el email del usuario admin de prueba.

        Puede ser sobrescrito en clases hijas para personalizar.

        Returns:
            str: Email (ej: 'admin@test.sintel.local')
        """
        return f"admin@{self.get_tenant_domain()}"

    def get_username(self):
        """
        Retorna el username del usuario admin de prueba.

        Puede ser sobrescrito en clases hijas para personalizar.

        Returns:
            str: Username (ej: 'admin')
        """
        return "admin"

    def get_user_password(self):
        """
        Retorna la contraseña del usuario admin de prueba.

        Puede ser sobrescrito en clases hijas para personalizar.

        Returns:
            str: Contraseña (ej: 'testpass123')
        """
        return "testpass123"
