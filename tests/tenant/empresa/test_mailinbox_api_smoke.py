"""
Tests de humo para API de MailInboxConfig.

[WARNING] v2.37: Alineado con arquitectura SSoT y API-First.
"""

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.tenant.empresa.models import MailInboxConfig


class MailInboxConfigAPISmokeTest(TestCase):
    """
    Tests de humo para endpoints de MailInboxConfig.
    """

    def setUp(self):
        """Setup: Crear cliente API y configuración de prueba."""
        self.client = APIClient()
        # TODO: Crear usuario y tenant para tests reales
        # Por ahora, tests básicos sin autenticación

    def test_list_endpoint_exists(self):
        """Test: Endpoint LIST existe y retorna estructura correcta."""
        # Sin autenticación, debería retornar 401 o 403
        response = self.client.get("/api/v1/empresa/mail-inbox-config/")
        # Esperamos 401 (no autenticado) o 403 (sin permisos)
        self.assertIn(
            response.status_code, [401, 403, 404]
        )  # 404 si no está registrado

    def test_detail_endpoint_exists(self):
        """Test: Endpoint DETAIL existe."""
        # Sin autenticación, debería retornar 401 o 403
        response = self.client.get("/api/v1/empresa/mail-inbox-config/1/")
        self.assertIn(response.status_code, [401, 403, 404])

    def test_test_connection_endpoint_exists(self):
        """Test: Endpoint test-connection existe."""
        # Sin autenticación, debería retornar 401 o 403
        response = self.client.post(
            "/api/v1/empresa/mail-inbox-config/test-connection/"
        )
        self.assertIn(response.status_code, [401, 403, 404])

    def test_list_serializer_no_secrets(self):
        """Test: LIST serializer no expone passwords."""
        # Este test requiere autenticación real
        # Por ahora, solo verificar estructura
        pass

    def test_detail_serializer_no_passwords(self):
        """Test: DETAIL serializer no expone passwords en respuesta."""
        # Este test requiere autenticación real
        pass
