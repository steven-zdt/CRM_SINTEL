"""
Clase base para tests de apps públicas (SHARED_APPS).

Hereda de APITestCase (DRF) y proporciona helpers para tests de APIs públicas.
"""
from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

User = get_user_model()


class PublicAPITestCase(APITestCase):
    """
    Clase base para tests de APIs públicas.

    Proporciona:
    - APIClient configurado
    - Helpers para requests JSON
    - Usuario admin por defecto
    """

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        # WARNING: AISLAMIENTO: connection.schema_name es una sesion Postgres
        # (SET search_path), no una transaccion -- el rollback automatico de
        # TestCase NO lo revierte. Un test previo que enruta requests hacia un
        # host de tenant (TenantMainMiddleware) puede dejar la conexion apuntando
        # a ese schema para el resto del proceso pytest. Forzar 'public' aqui
        # evita que ese leak rompa el ORM de tests publicos (SHARED_APPS).
        connection.set_schema_to_public()
        self.client = APIClient()
        # Forzar host válido para django-tenants / ALLOWED_HOSTS
        # En tests, el host por defecto es 'testserver', que no existe en Domain.
        # Usamos 'localhost', que está permitido y resuelve al esquema público.
        self.client.defaults.setdefault("HTTP_HOST", "localhost")
        
        # Crear usuario admin por defecto
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True,
        )
        
        # Autenticar como admin por defecto
        self.client.force_authenticate(user=self.admin_user)
    
    def json(self, method, url, data=None, **kwargs):
        """
        Helper para realizar requests JSON.
        
        Args:
            method: 'get', 'post', 'put', 'patch', 'delete'
            url: URL del endpoint
            data: Datos a enviar (dict)
            **kwargs: Argumentos adicionales para el método del cliente
        
        Returns:
            Response de DRF
        """
        method_func = getattr(self.client, method.lower())
        if data is not None:
            kwargs['data'] = data
            kwargs['format'] = 'json'
        return method_func(url, **kwargs)
    
    def assertJSONResponse(self, response, expected_status=status.HTTP_200_OK):
        """
        Assert que la respuesta es JSON con el status esperado.
        
        Args:
            response: Response de DRF
            expected_status: Status HTTP esperado
        """
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(response['content-type'], 'application/json')
    
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
