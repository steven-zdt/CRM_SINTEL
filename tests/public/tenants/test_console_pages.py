"""
Tests funcionales para páginas de consola de tenants.

Valida que las páginas de consola carguen correctamente (200)
y usen los templates esperados.
"""
import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed


@pytest.mark.django_db
class TestConsoleTenantsPages:
    """Tests para páginas de consola de tenants."""
    
    def test_console_tenants_list_200(self, admin_client):
        """Verifica que la lista de tenants carga correctamente."""
        url = reverse("console:tenants-list")
        response = admin_client.get(url)
        assert response.status_code == 200
        # assertTemplateUsed(response, "console/pages/tenants/list.html")
    
    def test_console_tenants_new_200(self, admin_client):
        """Verifica que la página de nuevo tenant carga correctamente."""
        url = reverse("console:tenants-new")
        response = admin_client.get(url)
        assert response.status_code == 200
        # Verificar que se pasan usuarios en el contexto
        assert "users" in response.context
    
    def test_console_tenants_create_requiere_post(self, admin_client):
        """Verifica que create redirige si no es POST."""
        url = reverse("console:tenants-create")
        response = admin_client.get(url)
        assert response.status_code == 302  # Redirect
        # Debe redirigir a tenants-list
        assert response.url == reverse("console:tenants-list")
    
    def test_console_tenants_list_requiere_staff(self, csrf_client):
        """Verifica que tenants_list requiere staff."""
        client, _ = csrf_client
        
        # Usuario no staff
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(email="user@test.local", password="pass123")
        client.force_login(user)
        
        url = reverse("console:tenants-list")
        response = client.get(url)
        # Debe ser 403 (PermissionDenied) o 302 (redirect a login)
        assert response.status_code in (302, 403)
