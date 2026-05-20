"""
Clase base para tests de apps tenant.

Hereda de TenantTestCase y proporciona helpers para tests multi-tenant.
"""
from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from django_tenants.utils import schema_context
import json
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


class TenantAPITestCase(TenantTestCase):
    """
    Clase base para tests de APIs tenant.
    
    Proporciona:
    - TenantClient configurado con dominio
    - Helpers para requests JSON con tenant
    - Usuario autenticado por defecto
    - Aislamiento automático por esquema
    """
    
    @classmethod
    def setup_tenant(cls, tenant):
        """
        Configuración del tenant antes de crear el esquema.
        
        Si tu Client tiene campos obligatorios adicionales, completarlos aquí.
        """
        # TenantTestCase ya crea el tenant con campos básicos
        # Si necesitas campos adicionales, configúralos aquí
        return tenant
    """
    Clase base para tests de APIs tenant.
    
    Proporciona:
    - TenantClient configurado con dominio
    - Helpers para requests JSON con tenant
    - Usuario autenticado por defecto
    - Aislamiento automático por esquema
    """
    
    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        
        # TenantTestCase ya crea self.tenant y self.domain automáticamente
        # Asegurar que el dominio primario del tenant use un sufijo de desarrollo
        # permitido (ej: '.localhost') para que la middleware de seguridad acepte
        # solicitudes en el entorno de pruebas.
        try:
            from apps.public.tenants.models import Domain
            primary_domain_qs = Domain.objects.filter(tenant=self.tenant, is_primary=True)
            if primary_domain_qs.exists():
                primary_domain = primary_domain_qs.first()
                primary_domain.domain = f"{self.tenant.schema_name}.localhost"
                primary_domain.save()
        except Exception:
            # Best-effort: si no existe o falla, continuar (TenantClient puede aún resolver)
            pass

        # Crear cliente con el dominio del tenant (propaga HTTP_HOST correcto)
        self.client = TenantClient(self.tenant)
        
        # Crear usuario global en el esquema public
        with schema_context('public'):
            self.user = User.objects.create_user(
                username='testuser',
                email='testuser@example.com',
                password='testpass123',
            )
            # Crear TenantMembership para el tenant actual con rol ADMIN (permite mutaciones en tests)
            try:
                from apps.public.tenants.models import TenantMembership
                TenantMembership.objects.update_or_create(
                    client=self.tenant,
                    user=self.user,
                    defaults={'rol': 'ADMIN', 'is_active': True, 'is_primary_admin': True},
                )
            except Exception:
                # Si falla por cualquier razón, continuar (tests pueden ajustar permisos manualmente)
                pass
        
        # Crear TenantProfile para el usuario en el esquema tenant
        with schema_context(self.tenant.schema_name):
            try:
                from apps.tenant.perfil.models import TenantProfile
                from apps.tenant.empresa.models import Empresa
                empresa = Empresa.objects.first()
                if not empresa:
                    empresa = Empresa.objects.create(
                        razon_social='Empresa Test Base',
                        nit='999999999',
                        dv='9',
                        direccion='Calle Base 123'
                    )
                TenantProfile.objects.update_or_create(
                    user=self.user,
                    defaults={'empresa': empresa, 'rol': 'ADMIN', 'cargo': 'Administrador Test'}
                )
            except Exception:
                pass

        # Autenticar como usuario en el tenant (session) y preparar JWT
        self.client.force_login(self.user)
        try:
            # Crear token de acceso JWT para el usuario (stateless)
            access = AccessToken.for_user(self.user)
            # Guardar como string para incluir en headers de prueba
            self.jwt_token = str(access)
        except Exception:
            # Si no está disponible simplejwt, seguir sin JWT
            self.jwt_token = None
    
    def tget(self, url, **kwargs):
        """
        GET request con tenant client.
        
        Args:
            url: URL del endpoint
            **kwargs: Argumentos adicionales
        
        Returns:
            Response
        """
        # Ensure tests use an allowed host to bypass Tenant domain restrictions
        if 'HTTP_HOST' not in kwargs:
            # Usar el dominio del tenant para que django-tenants seleccione el esquema correcto
            try:
                kwargs['HTTP_HOST'] = f"{self.tenant.schema_name}.localhost"
            except Exception:
                kwargs['HTTP_HOST'] = 'testserver'
        # Incluir JWT Authorization por defecto si existe y no fue proporcionada
        if getattr(self, 'jwt_token', None) and 'HTTP_AUTHORIZATION' not in kwargs:
            kwargs['HTTP_AUTHORIZATION'] = f'Bearer {self.jwt_token}'
        return self.client.get(url, **kwargs)
    
    def tpost(self, url, data=None, **kwargs):
        """
        POST request con tenant client (JSON).
        
        Args:
            url: URL del endpoint
            data: Datos a enviar (dict)
            **kwargs: Argumentos adicionales
        
        Returns:
            Response
        """
        if data is not None:
            kwargs['data'] = json.dumps(data)
            kwargs['content_type'] = 'application/json'
        if 'HTTP_HOST' not in kwargs:
            try:
                kwargs['HTTP_HOST'] = f"{self.tenant.schema_name}.localhost"
            except Exception:
                kwargs['HTTP_HOST'] = 'testserver'
        if getattr(self, 'jwt_token', None) and 'HTTP_AUTHORIZATION' not in kwargs:
            kwargs['HTTP_AUTHORIZATION'] = f'Bearer {self.jwt_token}'
        return self.client.post(url, **kwargs)
    
    def tput(self, url, data=None, **kwargs):
        """
        PUT request con tenant client (JSON).
        
        Args:
            url: URL del endpoint
            data: Datos a enviar (dict)
            **kwargs: Argumentos adicionales
        
        Returns:
            Response
        """
        if data is not None:
            kwargs['data'] = json.dumps(data)
            kwargs['content_type'] = 'application/json'
        if 'HTTP_HOST' not in kwargs:
            try:
                kwargs['HTTP_HOST'] = f"{self.tenant.schema_name}.localhost"
            except Exception:
                kwargs['HTTP_HOST'] = 'testserver'
        if getattr(self, 'jwt_token', None) and 'HTTP_AUTHORIZATION' not in kwargs:
            kwargs['HTTP_AUTHORIZATION'] = f'Bearer {self.jwt_token}'
        return self.client.put(url, **kwargs)
    
    def tpatch(self, url, data=None, **kwargs):
        """
        PATCH request con tenant client (JSON).
        
        Args:
            url: URL del endpoint
            data: Datos a enviar (dict)
            **kwargs: Argumentos adicionales
        
        Returns:
            Response
        """
        if data is not None:
            kwargs['data'] = json.dumps(data)
            kwargs['content_type'] = 'application/json'
        if 'HTTP_HOST' not in kwargs:
            try:
                kwargs['HTTP_HOST'] = f"{self.tenant.schema_name}.localhost"
            except Exception:
                kwargs['HTTP_HOST'] = 'testserver'
        if getattr(self, 'jwt_token', None) and 'HTTP_AUTHORIZATION' not in kwargs:
            kwargs['HTTP_AUTHORIZATION'] = f'Bearer {self.jwt_token}'
        return self.client.patch(url, **kwargs)
    
    def tdelete(self, url, **kwargs):
        """
        DELETE request con tenant client.
        
        Args:
            url: URL del endpoint
            **kwargs: Argumentos adicionales
        
        Returns:
            Response
        """
        if 'HTTP_HOST' not in kwargs:
            try:
                kwargs['HTTP_HOST'] = f"{self.tenant.schema_name}.localhost"
            except Exception:
                kwargs['HTTP_HOST'] = 'testserver'
        if getattr(self, 'jwt_token', None) and 'HTTP_AUTHORIZATION' not in kwargs:
            kwargs['HTTP_AUTHORIZATION'] = f'Bearer {self.jwt_token}'
        return self.client.delete(url, **kwargs)
    
    def assertJSONResponse(self, response, expected_status=status.HTTP_200_OK):
        """
        Assert que la respuesta es JSON con el status esperado.
        
        Args:
            response: Response
            expected_status: Status HTTP esperado
        """
        self.assertEqual(response.status_code, expected_status)
        self.assertIn('application/json', response['content-type'])
    
    def assertPaginationFormat(self, response_data):
        """
        Assert que la respuesta tiene el formato de paginación estándar.
        
        Args:
            response_data: Datos de la respuesta (dict)
        """
        self.assertIn('count', response_data)
        self.assertIn('next', response_data)
        self.assertIn('previous', response_data)
        self.assertIn('results', response_data)
        self.assertIsInstance(response_data['results'], list)
    
    def assertTenantIsolation(self, tenant1, tenant2, model_class, create_func):
        """
        Verifica que los datos están aislados entre tenants.
        
        Args:
            tenant1: Primer tenant
            tenant2: Segundo tenant
            model_class: Clase del modelo a verificar
            create_func: Función que crea una instancia del modelo
        """
        # Crear instancia en tenant1
        with schema_context(tenant1.schema_name):
            obj1 = create_func()
            count1 = model_class.objects.count()
        
        # Crear instancia en tenant2
        with schema_context(tenant2.schema_name):
            obj2 = create_func()
            count2 = model_class.objects.count()
        
        # Verificar que cada tenant solo ve sus propios datos
        with schema_context(tenant1.schema_name):
            self.assertEqual(model_class.objects.count(), count1)
            self.assertTrue(model_class.objects.filter(id=obj1.id).exists())
            self.assertFalse(model_class.objects.filter(id=obj2.id).exists())
        
        with schema_context(tenant2.schema_name):
            self.assertEqual(model_class.objects.count(), count2)
            self.assertTrue(model_class.objects.filter(id=obj2.id).exists())
            self.assertFalse(model_class.objects.filter(id=obj1.id).exists())
