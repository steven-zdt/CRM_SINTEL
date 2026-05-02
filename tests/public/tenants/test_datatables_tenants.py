"""
Tests funcionales para DataTables server-side de tenants.

Valida que el endpoint de DataTables retorne el formato correcto
y maneje correctamente parámetros de paginación, búsqueda y ordenamiento.
"""
import pytest
from django.urls import reverse
from apps.public.tenants.models import Client, Domain


@pytest.mark.django_db
class TestDataTablesTenants:
    """Tests para DataTables server-side de tenants."""
    
    def test_datatables_tenants_endpoint_basico(self, authenticated_client, admin_user):
        """Verifica que el endpoint de DataTables retorna formato correcto."""
        authenticated_client.force_authenticate(user=admin_user)
        
        # Crear tenant de prueba
        client = Client.objects.create(
            schema_name="test_tenant",
            nombre="Tenant de Prueba",
            auto_create_schema=True
        )
        Domain.objects.create(
            domain="test.localhost",
            tenant=client,
            is_primary=True
        )
        
        url = reverse("admin-dt-tenants")
        # DataTables envía draw/start/length (serverSide)
        params = {
            "draw": 1,
            "start": 0,
            "length": 10
        }
        response = authenticated_client.get(url, data=params)
        assert response.status_code == 200
        
        body = response.json()
        # Verificar estructura de respuesta DataTables
        assert "draw" in body
        assert "recordsTotal" in body
        assert "recordsFiltered" in body
        assert "data" in body
        assert isinstance(body["data"], list)
        
        # Verificar que draw se retorna correctamente
        assert body["draw"] == 1
    
    def test_datatables_tenants_busqueda(self, authenticated_client, admin_user):
        """Verifica que la búsqueda funciona correctamente."""
        authenticated_client.force_authenticate(user=admin_user)
        
        # Crear tenants de prueba
        Client.objects.create(
            schema_name="acme",
            nombre="Acme Corporation",
            auto_create_schema=True
        )
        Client.objects.create(
            schema_name="test_company",
            nombre="Test Company",
            auto_create_schema=True
        )
        
        url = reverse("admin-dt-tenants")
        
        # Búsqueda por "Acme"
        params = {
            "draw": 1,
            "start": 0,
            "length": 10,
            "search[value]": "Acme"
        }
        response = authenticated_client.get(url, data=params)
        assert response.status_code == 200
        body = response.json()
        assert body["recordsFiltered"] >= 1
        # Al menos un resultado debe contener "Acme"
        assert any("Acme" in str(row).upper() for row in body["data"])
    
    def test_datatables_tenants_requiere_autenticacion(self, api_client):
        """Verifica que DataTables requiere autenticación."""
        url = reverse("admin-dt-tenants")
        params = {"draw": 1, "start": 0, "length": 10}
        response = api_client.get(url, data=params)
        assert response.status_code == 401 or response.status_code == 403
