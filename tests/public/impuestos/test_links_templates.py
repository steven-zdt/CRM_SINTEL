"""
Tests funcionales para verificar enlaces y templates en la consola.

Valida que todas las páginas de la consola se carguen correctamente (200)
y usen los templates esperados.
"""
import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed


@pytest.mark.django_db
class TestConsoleLinks:
    """Tests para enlaces de la consola de impuestos."""
    
    def test_console_impuestos_home_200(self, admin_client):
        """Verifica que la página home de impuestos carga correctamente."""
        url = reverse("console:impuestos-index")
        response = admin_client.get(url)
        assert response.status_code == 200
    
    def test_console_impuestos_ingesta_list_200(self, admin_client):
        """Verifica que la lista de ingesta carga correctamente."""
        url = reverse("console:impuestos-ingesta-list")
        response = admin_client.get(url)
        assert response.status_code == 200
        assertTemplateUsed(response, "console/pages/impuestos/ingesta_list.html")
    
    def test_console_impuestos_ingesta_create_200(self, admin_client):
        """Verifica que la página de crear ingesta carga correctamente."""
        url = reverse("console:impuestos-ingesta-create")
        response = admin_client.get(url)
        assert response.status_code == 200
        assertTemplateUsed(response, "console/pages/impuestos/ingesta_create.html")
    
    def test_console_impuestos_search_page_200(self, admin_client):
        """Verifica que la página de búsqueda carga correctamente."""
        url = reverse("console:impuestos-search-page")
        response = admin_client.get(url)
        assert response.status_code == 200
    
    def test_console_impuestos_search_health_200(self, admin_client):
        """Verifica que la página de salud de OpenSearch carga correctamente (solo staff)."""
        url = reverse("console:impuestos-search-health")
        response = admin_client.get(url)
        assert response.status_code == 200
    
    def test_console_impuestos_tipos_list_200(self, admin_client):
        """Verifica que la lista de tipos de impuesto carga correctamente."""
        url = reverse("console:console-impuestos-tipos")
        response = admin_client.get(url)
        assert response.status_code == 200
    
    def test_console_impuestos_ingesta_detail_404_if_not_exists(self, admin_client):
        """Verifica que el detalle devuelve 404 si el documento no existe."""
        url = reverse("console:impuestos-ingesta-detail", args=[99999])
        response = admin_client.get(url)
        assert response.status_code == 404
    
    def test_console_impuestos_tipo_form_new_200(self, admin_client):
        """Verifica que el formulario de nuevo tipo carga correctamente."""
        url = reverse("console:console-impuestos-tipo-form")
        response = admin_client.get(url)
        assert response.status_code == 200
