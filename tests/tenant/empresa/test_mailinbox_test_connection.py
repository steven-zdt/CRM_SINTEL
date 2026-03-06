"""
Tests para endpoint test-connection de MailInboxConfig.

⚠️ v2.37: Alineado con arquitectura API-First y Service Layer.
"""
import pytest
from django.test import Client
from rest_framework import status
from tests.tenant.base_test import SintelTenantTestCase
from apps.tenant.empresa.models import MailInboxConfig


class TestMailInboxConfigTestConnection(SintelTenantTestCase):
    """
    Tests para el endpoint test-connection.
    
    ⚠️ IMPORTANTE: Estos tests validan que:
    - El endpoint acepta payload completo → 200
    - El endpoint rechaza payload incompleto → 400
    - Password nunca se expone en respuesta
    """
    
    def setUp(self):
        """Configuración inicial."""
        super().setUp()
        self.client = Client()
        self.client.force_login(self.user)
        self.endpoint = '/api/v1/empresas/mail-inbox-config/test-connection/'
    
    def test_test_connection_complete_payload_200(self):
        """Valida que payload completo retorna 200."""
        payload = {
            'host': 'imap.gmail.com',
            'port': 993,
            'protocol': 'imap',
            'username': 'test@gmail.com',
            'password': 'test_password',
            'use_ssl': True,
            'use_starttls': False,
        }
        
        response = self.client.post(
            self.endpoint,
            data=payload,
            content_type='application/json',
            HTTP_ACCEPT='application/json'
        )
        
        # El endpoint puede retornar 200 (éxito) o 400 (fallo de conexión real)
        # Lo importante es que NO retorna 400 por payload inválido
        self.assertIn(response.status_code, [200, 400], 
                     f"Status code inesperado: {response.status_code}")
        
        data = response.json()
        self.assertIn('ok', data)
        self.assertIn('message', data)
        self.assertIsInstance(data['ok'], bool)
        self.assertIsInstance(data['message'], str)
    
    def test_test_connection_incomplete_payload_400(self):
        """Valida que payload incompleto retorna 400."""
        # Falta 'password'
        payload = {
            'host': 'imap.gmail.com',
            'port': 993,
            'protocol': 'imap',
            'username': 'test@gmail.com',
            'use_ssl': True,
        }
        
        response = self.client.post(
            self.endpoint,
            data=payload,
            content_type='application/json',
            HTTP_ACCEPT='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        
        # Debe tener errores de validación
        self.assertIn('password', data or {})
    
    def test_test_connection_missing_required_fields_400(self):
        """Valida que faltan campos requeridos retorna 400."""
        # Falta 'host'
        payload = {
            'port': 993,
            'protocol': 'imap',
            'username': 'test@gmail.com',
            'password': 'test_password',
            'use_ssl': True,
        }
        
        response = self.client.post(
            self.endpoint,
            data=payload,
            content_type='application/json',
            HTTP_ACCEPT='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        
        # Debe tener errores de validación
        self.assertIn('host', data or {})
    
    def test_test_connection_password_not_exposed(self):
        """Valida que password nunca se expone en la respuesta."""
        payload = {
            'host': 'imap.gmail.com',
            'port': 993,
            'protocol': 'imap',
            'username': 'test@gmail.com',
            'password': 'secret_password_123',
            'use_ssl': True,
        }
        
        response = self.client.post(
            self.endpoint,
            data=payload,
            content_type='application/json',
            HTTP_ACCEPT='application/json'
        )
        
        # Cualquier respuesta válida (200 o 400)
        self.assertIn(response.status_code, [200, 400])
        
        data = response.json()
        response_text = response.content.decode('utf-8')
        
        # Verificar que password NO está en la respuesta
        self.assertNotIn('secret_password_123', response_text)
        self.assertNotIn('password', data)  # No debe estar en el JSON de respuesta
        
        # Verificar que el mensaje no contiene el password
        if 'message' in data:
            self.assertNotIn('secret_password_123', data['message'])
    
    def test_test_connection_invalid_protocol_400(self):
        """Valida que protocolo inválido retorna 400."""
        payload = {
            'host': 'imap.gmail.com',
            'port': 993,
            'protocol': 'invalid_protocol',  # Protocolo inválido
            'username': 'test@gmail.com',
            'password': 'test_password',
            'use_ssl': True,
        }
        
        response = self.client.post(
            self.endpoint,
            data=payload,
            content_type='application/json',
            HTTP_ACCEPT='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        
        # Debe tener error de validación en protocol
        self.assertIn('protocol', data or {})
    
    def test_test_connection_invalid_port_400(self):
        """Valida que puerto inválido retorna 400."""
        payload = {
            'host': 'imap.gmail.com',
            'port': 99999,  # Puerto inválido (> 65535)
            'protocol': 'imap',
            'username': 'test@gmail.com',
            'password': 'test_password',
            'use_ssl': True,
        }
        
        response = self.client.post(
            self.endpoint,
            data=payload,
            content_type='application/json',
            HTTP_ACCEPT='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        
        # Debe tener error de validación en port
        self.assertIn('port', data or {})
    
    def test_test_connection_ssl_and_starttls_conflict_400(self):
        """Valida que use_ssl=True y use_starttls=True retorna 400."""
        payload = {
            'host': 'imap.gmail.com',
            'port': 993,
            'protocol': 'imap',
            'username': 'test@gmail.com',
            'password': 'test_password',
            'use_ssl': True,
            'use_starttls': True,  # Conflicto: no se puede usar STARTTLS con SSL
        }
        
        response = self.client.post(
            self.endpoint,
            data=payload,
            content_type='application/json',
            HTTP_ACCEPT='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        
        # Debe tener error de validación cruzada
        self.assertIn('use_starttls', data or {})
