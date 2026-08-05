"""
Tests de smoke para verificar que el template se sirve correctamente.

Verifica que GET /empresa/ retorna 200 y usa el template correcto.
"""

import pytest
from django.urls import reverse

from apps.tenant.api.tests.base import SintelTenantTestCase


@pytest.mark.django_db(transaction=True)
class TemplateServedSmokeTest(SintelTenantTestCase):
    """
    Tests de smoke para verificar que el template se sirve correctamente.
    """

    def setUp(self):
        super().setUp()
        # Crear usuario autenticado
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.client.force_login(self.user)

        # Asegurar membresía en tenant
        self.tenant.add_member(self.user, "admin")

    def test_empresa_page_returns_200(self):
        """
        Verifica que GET /empresa/ retorna 200 OK.
        """
        response = self.client.get("/empresa/")

        self.assertEqual(response.status_code, 200)

    def test_empresa_page_uses_correct_template(self):
        """
        Verifica que GET /empresa/ usa el template correcto.
        """
        response = self.client.get("/empresa/")

        self.assertEqual(response.status_code, 200)
        # Verificar que el template se usó (verificar contenido)
        self.assertContains(response, "Datos de Mi Empresa", status_code=200)
        # Verificar que extiende tenant/base.html (verificar contenido común)
        self.assertContains(response, "tenant", status_code=200)

    def test_empresa_page_requires_authentication(self):
        """
        Verifica que GET /empresa/ requiere autenticación.
        """
        self.client.logout()

        response = self.client.get("/empresa/")

        # Debe redirigir a login o retornar 403
        self.assertIn(response.status_code, [302, 403])
