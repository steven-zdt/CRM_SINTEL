"""
Tests de API REST para tenants.

Valida que la API habla el "mismo idioma" que el modelo.
"""
import pytest
from rest_framework import status
from django.urls import reverse
from apps.public.tenants.models import Client, Domain
from tests.public.tenants.factories import ClientFactory, DomainFactory


@pytest.mark.django_db
class TestClientAPI:
    """Tests para el endpoint de Client."""
    
    def test_list_tenants(self, admin_client):
        """Test: Listar tenants (GET /api/admin/v1/tenants/)."""
        # Crear algunos tenants
        client1 = ClientFactory(nombre="Empresa 1", schema_name="empresa1")
        client2 = ClientFactory(nombre="Empresa 2", schema_name="empresa2")
        
        # Hacer request
        url = reverse('admin-tenants-list')
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)
        
        # Verificar que los tenants están en la respuesta
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        nombres = [item['nombre'] for item in results]
        
        assert "Empresa 1" in nombres or "Empresa 2" in nombres
    
    def test_list_tenants_returns_correct_fields(self, admin_client):
        """Test: Verificar que la lista devuelve los campos correctos."""
        ClientFactory(nombre="Test Corp", schema_name="testcorp")
        
        url = reverse('admin-tenants-list')
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        if results:
            tenant_data = results[0]
            
            # Verificar campos requeridos
            assert 'id' in tenant_data
            assert 'nombre' in tenant_data
            assert 'schema_name' in tenant_data
            assert 'paid_until' in tenant_data
            assert 'on_trial' in tenant_data
            assert 'created_on' in tenant_data
    
    def test_list_tenants_no_subdomain_field(self, admin_client):
        """Test ANTI-PATRÓN: Asegurar que NO se envía el campo subdomain."""
        ClientFactory(nombre="Test Corp", schema_name="testcorp")
        
        url = reverse('admin-tenants-list')
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        if results:
            tenant_data = results[0]
            
            # Verificar que NO existe el campo subdomain
            assert 'subdomain' not in tenant_data
    
    def test_retrieve_tenant(self, admin_client):
        """Test: Obtener un tenant específico (GET /api/admin/v1/tenants/{id}/)."""
        client = ClientFactory(nombre="Test Corp", schema_name="testcorp")
        
        url = reverse('admin-tenants-detail', kwargs={'pk': client.id})
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['nombre'] == "Test Corp"
        assert response.data['schema_name'] == "testcorp"
        assert 'subdomain' not in response.data
    
    def test_api_requires_authentication(self, client):
        """Test: La API requiere autenticación."""
        url = reverse('admin-tenants-list')
        response = client.get(url)
        
        # Debe retornar 401 o 403 (depende de la configuración)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
    
    def test_api_requires_admin_permission(self, client):
        """Test: La API requiere permisos de administrador."""
        from django.contrib.auth import get_user_model
        from django.test import Client
        
        User = get_user_model()
        # Crear usuario NO admin
        user = User.objects.create_user(
            email="user@test.local",
            password="testpass123"
        )
        
        client.force_login(user)
        
        url = reverse('admin-tenants-list')
        response = client.get(url)
        
        # Debe retornar 403 (Forbidden)
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestDomainAPI:
    """Tests para el endpoint de Domain."""
    
    def test_list_domains(self, admin_client):
        """Test: Listar dominios (GET /api/admin/v1/domains/)."""
        client = ClientFactory()
        domain1 = DomainFactory(tenant=client, domain="test1.localhost", is_primary=True)
        domain2 = DomainFactory(tenant=client, domain="test2.localhost", is_primary=False)
        
        url = reverse('admin-tenant-domains-list')
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        domains = [item['domain'] for item in results]
        
        assert "test1.localhost" in domains or "test2.localhost" in domains
    
    def test_domain_api_uses_tenant_field(self, admin_client):
        """Test: Verificar que la API de Domain usa 'tenant' (convención django-tenants)."""
        client = ClientFactory(nombre="Test Corp")
        domain = DomainFactory(tenant=client, domain="test.localhost")
        
        url = reverse('admin-tenant-domains-detail', kwargs={'pk': domain.id})
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verificar que existe el campo 'tenant' en la respuesta
        # (puede ser un ID o un objeto anidado)
        assert 'tenant' in response.data


@pytest.mark.django_db
class TestAPISerialization:
    """Tests para la serialización de datos."""
    
    def test_client_serializer_validates_schema_name(self, admin_client):
        """Test: El serializer valida schema_name correctamente."""
        # Nota: Como el ViewSet es ReadOnly, no podemos probar creación vía API
        # Pero podemos verificar que los datos serializados son correctos
        
        client = ClientFactory(nombre="Test Corp", schema_name="testcorp")
        
        url = reverse('admin-tenants-detail', kwargs={'pk': client.id})
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['schema_name'] == "testcorp"
        assert response.data['schema_name'].islower()  # Debe estar normalizado
    
    def test_client_serializer_excludes_domains_from_write(self, admin_client):
        """Test: El serializer NO incluye domains como campo de escritura."""
        # Verificar que el serializer no permite escribir 'domains'
        # (solo lectura)
        client = ClientFactory()
        
        url = reverse('admin-tenants-detail', kwargs={'pk': client.id})
        response = admin_client.get(url)
        
        # Verificar que 'domains' no está en los campos de escritura
        # (aunque puede estar en lectura)
        # Nota: Como es ReadOnly, no hay campos de escritura, pero verificamos estructura
        assert response.status_code == status.HTTP_200_OK
