"""
Tests para EmailService de la aplicacion core.

[WARNING] REGLA 0: Cero caracteres especiales o emojis. Solo ASCII.
"""

from unittest.mock import patch
from django.test import TestCase
from django.core import mail
from django.contrib.auth import get_user_model
from django.conf import settings

from apps.public.tenants.models import Client
from apps.public.core.services.email_service import EmailService


class EmailServiceTestCase(TestCase):
    """
    Suite de pruebas para validar el envio de correos.
    """

    @patch("apps.public.tenants.models.Client.create_schema")
    def setUp(self, mock_create_schema):
        super().setUp()
        mock_create_schema.return_value = None

        User = get_user_model()
        self.user = User.objects.create_user(
            username="owner_test",
            email="owner@sintel.com",
            password="securepassword123",
        )

        self.tenant = Client.objects.create(
            schema_name="test_tenant",
            nombre="Test Company",
            on_trial=True,
        )

    @patch("apps.public.core.tasks.send_invitation_email_task.delay")
    def test_send_invitation_email_async_dispatches_task(self, mock_task_delay):
        """
        Verifica que send_invitation_email planifica correctamente la tarea asincrona.
        """
        url = "http://test_tenant.localhost/activate/abc"
        result = EmailService.send_invitation_email(self.user, self.tenant, url)
        
        self.assertTrue(result)
        mock_task_delay.assert_called_once_with(self.user.pk, self.tenant.pk, url)

    @patch("apps.public.core.tasks.send_password_reset_email_task.delay")
    def test_send_password_reset_email_async_dispatches_task(self, mock_task_delay):
        """
        Verifica que send_password_reset_email planifica la tarea de restablecimiento.
        """
        url = "http://test_tenant.localhost/reset/xyz"
        result = EmailService.send_password_reset_email(self.user, self.tenant, url)
        
        self.assertTrue(result)
        mock_task_delay.assert_called_once_with(self.user.pk, self.tenant.pk, url)

    def test_send_invitation_email_sync_sends_mail(self):
        """
        Verifica que el metodo sincrono envia correctamente el email y renderiza
        los templates con el contexto esperado.
        """
        mail.outbox = []
        url = "http://test_tenant.localhost/activate/abc"
        
        result = EmailService.send_invitation_email_sync(self.user, self.tenant, url)
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, [self.user.email])
        self.assertIn("Activa tu cuenta", sent_email.subject)
        
        # Verificar que el contenido renderiza datos del tenant y del usuario
        self.assertIn("Test Company", sent_email.body)
        self.assertIn(url, sent_email.body)

    def test_send_password_reset_email_sync_sends_mail(self):
        """
        Verifica que el metodo sincrono de reset envia correctamente el email.
        """
        mail.outbox = []
        url = "http://test_tenant.localhost/reset/xyz"
        
        result = EmailService.send_password_reset_email_sync(self.user, self.tenant, url)
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, [self.user.email])
        self.assertIn("Restablecer", sent_email.subject)
        self.assertIn(url, sent_email.body)
