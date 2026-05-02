"""
Tests unitarios para modelo MailInboxConfig.

[WARNING] v2.37: Alineado con arquitectura SSoT.
"""
from django.test import TestCase
from apps.tenant.empresa.models import MailInboxConfig


class MailInboxConfigModelTest(TestCase):
    """
    Tests del modelo MailInboxConfig.
    """
    
    def test_create_mailinbox_config(self):
        """Test: Crear configuración básica."""
        config = MailInboxConfig.objects.create(
            nombre="Test Config",
            email_address="test@example.com",
            provider="custom",
            imap_host="imap.example.com",
            imap_port=993,
            imap_ssl=True,
            imap_username="test@example.com",
            imap_password="test_password",
        )
        self.assertIsNotNone(config.id)
        self.assertEqual(config.nombre, "Test Config")
        self.assertEqual(config.provider, "custom")
        self.assertTrue(config.is_active)
    
    def test_password_not_in_repr(self):
        """Test: Password no debe estar en __str__ ni __repr__."""
        config = MailInboxConfig.objects.create(
            nombre="Test Config",
            imap_password="secret_password",
        )
        str_repr = str(config)
        self.assertNotIn("secret_password", str_repr)
        self.assertNotIn("password", str_repr.lower())
    
    def test_indexes_exist(self):
        """Test: Verificar que los índices existen."""
        from django.db import connection
        indexes = connection.introspection.get_indexes(connection.cursor(), MailInboxConfig._meta.db_table)
        index_fields = [idx['columns'][0] for idx in indexes.values()]
        # Verificar índices esperados
        self.assertIn('provider', index_fields or [])
    
    def test_gmail_preset(self):
        """Test: Configuración Gmail con presets."""
        config = MailInboxConfig.objects.create(
            nombre="Gmail Test",
            provider="gmail",
            email_address="test@gmail.com",
        )
        # Los presets se aplican en el serializer, no en el modelo
        # Este test solo verifica que se puede crear
        self.assertEqual(config.provider, "gmail")
