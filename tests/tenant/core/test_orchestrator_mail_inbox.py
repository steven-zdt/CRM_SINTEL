"""
Tests para Core Orchestrator - Mail Inbox Config v2.40

[WARNING] v2.40: Verifica que el Core Orchestrator puede crear/actualizar
configuraciones de buzón de correo a través de PATCH /api/v1/core/empresa/
"""
from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.utils import schema_context, get_public_schema_name
from rest_framework import status
from rest_framework.test import APIClient
from django.urls import reverse
from tests.tenant.base_test import SintelTenantTestCase
from apps.tenant.empresa.models import Empresa, MailInboxConfig
from apps.public.tenants.models import TenantMembership

User = get_user_model()


class TestOrchestratorMailInbox(SintelTenantTestCase):
    """Tests para Core Orchestrator con mail_inbox_config."""
    
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
                username="admin_mail@test.com",
                email="admin_mail@test.com",
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
    
    def test_create_mail_inbox_config_via_orchestrator(self):
        """El Core Orchestrator puede crear mail_inbox_config cuando Empresa existe."""
        url = reverse('core-mi-empresa')
        
        payload = {
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
        
        # Verificar que mail_inbox_config fue creado
        mailbox_data = response.data['mail_inbox_config']
        self.assertEqual(mailbox_data['nombre'], "Buzón Test")
        self.assertEqual(mailbox_data['imap_host'], "imap.example.com")
        self.assertEqual(mailbox_data['imap_port'], 993)
        
        # [WARNING] SEGURIDAD: Password NO debe estar en la respuesta (write_only)
        self.assertNotIn('imap_password', mailbox_data)
        self.assertNotIn('password', mailbox_data)
        
        # Verificar que el objeto fue persistido en la BD
        mailbox = MailInboxConfig.objects.get(id=mailbox_data['id'])
        self.assertEqual(mailbox.nombre, "Buzón Test")
        self.assertEqual(mailbox.imap_password, "secret123")  # Verificar que se guardó
    
    def test_create_mail_inbox_config_via_orchestrator_without_empresa(self):
        """El Core Orchestrator crea Empresa si no existe y luego crea mail_inbox_config."""
        # Eliminar empresa existente
        Empresa.objects.all().delete()
        
        url = reverse('core-mi-empresa')
        
        payload = {
            "razon_social": "Nueva Empresa",
            "nit": "900999999",
            "mail_inbox_config": {
                "nombre": "Buzón Nueva Empresa",
                "email_address": "nueva@example.com",
                "provider": "custom",
                "imap_host": "imap.example.com",
                "imap_port": 993,
                "imap_username": "nueva@example.com",
                "imap_password": "secret456",
                "imap_ssl": True,
                "imap_mailbox": "INBOX",
                "is_active": True
            }
        }
        
        response = self.api_client.patch(url, payload, format='json')
        
        # Debe crear Empresa (201) y mail_inbox_config
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertIn('mail_inbox_config', response.data)
        
        # Verificar que ambos fueron creados
        empresa = Empresa.objects.get(nit="900999999")
        self.assertEqual(empresa.razon_social, "Nueva Empresa")
        
        mailbox_data = response.data['mail_inbox_config']
        mailbox = MailInboxConfig.objects.get(id=mailbox_data['id'])
        self.assertEqual(mailbox.nombre, "Buzón Nueva Empresa")
    
    def test_update_mail_inbox_config_via_orchestrator(self):
        """El Core Orchestrator puede actualizar mail_inbox_config existente."""
        # Crear configuración existente
        mailbox = MailInboxConfig.objects.create(
            nombre="Buzón Original",
            email_address="original@example.com",
            provider="custom",
            imap_host="imap.original.com",
            imap_port=993,
            imap_username="original@example.com",
            imap_password="oldpass",
            imap_ssl=True,
            imap_mailbox="INBOX",
            is_active=True
        )
        
        url = reverse('core-mi-empresa')
        
        payload = {
            "mail_inbox_config": {
                "id": mailbox.id,
                "nombre": "Buzón Actualizado",
                "imap_host": "imap.updated.com",
                "imap_port": 143,
                "imap_ssl": False,
                "imap_starttls": True
            }
        }
        
        response = self.api_client.patch(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('mail_inbox_config', response.data)
        
        # Verificar que fue actualizado
        mailbox_data = response.data['mail_inbox_config']
        self.assertEqual(mailbox_data['nombre'], "Buzón Actualizado")
        self.assertEqual(mailbox_data['imap_host'], "imap.updated.com")
        self.assertEqual(mailbox_data['imap_port'], 143)
        
        # Verificar en BD
        mailbox.refresh_from_db()
        self.assertEqual(mailbox.nombre, "Buzón Actualizado")
        self.assertEqual(mailbox.imap_host, "imap.updated.com")
        self.assertEqual(mailbox.imap_port, 143)
        self.assertFalse(mailbox.imap_ssl)
        self.assertTrue(mailbox.imap_starttls)
        
        # [WARNING] SEGURIDAD: Password NO debe estar en la respuesta
        self.assertNotIn('imap_password', mailbox_data)
    
    def test_mail_inbox_config_password_write_only(self):
        """Password es write_only y no se expone en respuestas."""
        url = reverse('core-mi-empresa')
        
        payload = {
            "mail_inbox_config": {
                "nombre": "Buzón Secreto",
                "email_address": "secreto@example.com",
                "provider": "custom",
                "imap_host": "imap.secreto.com",
                "imap_port": 993,
                "imap_username": "secreto@example.com",
                "imap_password": "super_secret_password_123",
                "imap_ssl": True,
                "imap_mailbox": "INBOX",
                "is_active": True
            }
        }
        
        response = self.api_client.patch(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mailbox_data = response.data['mail_inbox_config']
        
        # [WARNING] CRÍTICO: Password NO debe estar en la respuesta
        self.assertNotIn('imap_password', mailbox_data)
        self.assertNotIn('password', mailbox_data)
        
        # Pero debe estar guardado en BD
        mailbox = MailInboxConfig.objects.get(id=mailbox_data['id'])
        self.assertEqual(mailbox.imap_password, "super_secret_password_123")
    
    def test_mail_inbox_config_invalid_payload(self):
        """El Core Orchestrator rechaza mail_inbox_config inválido."""
        url = reverse('core-mi-empresa')
        
        # mail_inbox_config debe ser un objeto, no un string
        payload = {
            "mail_inbox_config": "invalid_string"
        }
        
        response = self.api_client.patch(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_mail_inbox_config_update_nonexistent_id(self):
        """El Core Orchestrator retorna 404 si se intenta actualizar ID inexistente."""
        url = reverse('core-mi-empresa')
        
        payload = {
            "mail_inbox_config": {
                "id": 99999,  # ID que no existe
                "nombre": "Buzón Inexistente"
            }
        }
        
        response = self.api_client.patch(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
