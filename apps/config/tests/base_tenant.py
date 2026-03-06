"""
Clase base para tests de apps tenant.

Hereda de TenantTestCase y proporciona helpers para tests multi-tenant.
"""
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from django_tenants.utils import schema_context
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.public.tenants.models import Client, Domain

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
        # Crear cliente con el dominio del tenant (propaga HTTP_HOST correcto)
        self.client = TenantClient(self.tenant)
        
        # Crear usuario global en el esquema public
        with schema_context('public'):
            self.user = User.objects.create_user(
                username='testuser',
                email='testuser@example.com',
                password='testpass123',
            )
        
        # Autenticar como usuario en el tenant
        self.client.force_login(self.user)
    
    def tget(self, url, **kwargs):
        """
        GET request con tenant client.
        
        Args:
            url: URL del endpoint
            **kwargs: Argumentos adicionales
        
        Returns:
            Response
        """
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
            kwargs['data'] = data
            kwargs['format'] = 'json'
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
            kwargs['data'] = data
            kwargs['format'] = 'json'
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
            kwargs['data'] = data
            kwargs['format'] = 'json'
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
