"""
Tests para Core Orchestrator - Validación de Payloads v2.40

[WARNING] v2.40: Verifica que el Core Orchestrator maneja correctamente payloads inválidos
y retorna 400 en lugar de 500 (ParseError).
"""
from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.utils import schema_context, get_public_schema_name
from rest_framework import status
from rest_framework.test import APIClient
from django.urls import reverse
from tests.tenant.base_test import SintelTenantTestCase
from apps.tenant.empresa.models import Empresa
from apps.public.tenants.models import TenantMembership

User = get_user_model()


class TestOrchestratorEmpresaPayloads(SintelTenantTestCase):
    """Tests para validación de payloads en Core Orchestrator."""
    
    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        # Crear empresa para que los modelos puedan usar FK a Empresa
        self.empresa = Empresa.objects.create(
            razon_social="Empresa Test",
            nit="900123456",
            singleton_key=1
        )
        # Crear usuario con rol ADMIN
        with schema_context(get_public_schema_name()):
            self.admin_user = User.objects.create_user(
                username="admin_payload@test.com",
                email="admin_payload@test.com",
                password="testpass123"
            )
        
        # Crear membresía en el tenant
        public_schema = get_public_schema_name()
        with schema_context(public_schema):
            tenant = self.tenant
            TenantMembership.objects.create(
                client=tenant,
                user=self.admin_user,
                rol="ADMIN",
                is_active=True
            )
        
        # Re-autenticar el api_client con el admin_user
        self.api_client = APIClient(HTTP_HOST=self.domain.domain)
        self.api_client.force_authenticate(user=self.admin_user)
    
    def test_patch_with_valid_json_payload(self):
        """PATCH con payload JSON válido → 200 OK."""
        url = reverse('core-mi-empresa')
        
        payload = {
            "razon_social": "Empresa Actualizada",
            "nit": "900123456",
            "direccion": "Nueva Dirección 123"
        }
        
        response = self.api_client.patch(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('razon_social', response.data)
        self.assertEqual(response.data['razon_social'], "Empresa Actualizada")
    
    def test_patch_with_empty_body(self):
        """PATCH con Content-Type: application/json pero body vacío → 400 Bad Request."""
        url = reverse('core-mi-empresa')
        
        # Simular body vacío enviando un dict vacío
        response = self.api_client.patch(url, {}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'invalid_payload')
        self.assertIn('vacío', response.data['detail'].lower())
    
    def test_patch_with_invalid_json_string(self):
        """PATCH con Content-Type: application/json pero body no-JSON → 400 Bad Request."""
        url = reverse('core-mi-empresa')
        
        # Simular body inválido usando raw data
        response = self.api_client.patch(
            url,
            data='not valid json',
            content_type='application/json'
        )
        
        # DRF debería retornar 400 ParseError, no 500
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE])
        # Si es 400, debe tener un mensaje de error
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            self.assertIn('error', response.data or {})
    
    def test_patch_with_null_payload(self):
        """PATCH con payload null/None → 400 Bad Request."""
        url = reverse('core-mi-empresa')
        
        # Simular payload null enviando un dict vacío (lo más cercano a null en DRF)
        response = self.api_client.patch(url, {}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'invalid_payload')
    
    def test_patch_response_content_type_is_json(self):
        """Respuesta del Core Orchestrator debe tener Content-Type: application/json."""
        url = reverse('core-mi-empresa')
        
        payload = {
            "razon_social": "Empresa Test Content-Type"
        }
        
        response = self.api_client.patch(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar que la respuesta es JSON
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIsInstance(response.data, dict)
    
    def test_patch_with_valid_payload_creates_empresa_if_not_exists(self):
        """PATCH con payload válido crea Empresa si no existe → 201 Created."""
        # Eliminar empresa existente
        Empresa.objects.all().delete()
        
        url = reverse('core-mi-empresa')
        
        payload = {
            "razon_social": "Nueva Empresa",
            "nit": "900999999",
            "direccion": "Dirección Nueva"
        }
        
        response = self.api_client.patch(url, payload, format='json')
        
        # Debe crear nueva empresa (201) o actualizar si ya existe (200)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        
        # Verificar que la empresa fue creada/actualizada
        empresa = Empresa.objects.get(nit="900999999")
        self.assertEqual(empresa.razon_social, "Nueva Empresa")
    
    def test_patch_with_mail_inbox_config_valid(self):
        """PATCH con mail_inbox_config válido → 200 OK."""
        url = reverse('core-mi-empresa')
        
        payload = {
            "razon_social": "Empresa con Mail",
            "mail_inbox_config": {
                "nombre": "Buzón Test",
                "email_address": "test@example.com",
                "provider": "custom",
                "imap_host": "imap.example.com",
                "imap_port": 993,
                "imap_username": "test@example.com",
                "imap_password": "secret123",
                "imap_ssl": True,
                "imap_mailbox": "INBOX",
                "is_active": True
            }
        }
        
        response = self.api_client.patch(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('mail_inbox_config', response.data)
        mailbox_data = response.data['mail_inbox_config']
        self.assertEqual(mailbox_data['nombre'], "Buzón Test")
        # [WARNING] SEGURIDAD: Password NO debe estar en la respuesta
        self.assertNotIn('imap_password', mailbox_data)
    
    def test_patch_with_mail_inbox_config_invalid_type(self):
        """PATCH con mail_inbox_config que no es dict → 400 Bad Request."""
        url = reverse('core-mi-empresa')
        
        payload = {
            "razon_social": "Empresa Test",
            "mail_inbox_config": "invalid_string_not_dict"
        }
        
        response = self.api_client.patch(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('mail_inbox_config', str(response.data.get('error', '')).lower())
