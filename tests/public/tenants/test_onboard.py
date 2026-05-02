"""
Tests funcionales para onboarding de tenants.

Valida que el endpoint de onboarding crea correctamente
Client, Domain y TenantMembership.
"""
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.public.tenants.models import Client, Domain, TenantMembership

User = get_user_model()


@pytest.mark.django_db
class TestOnboard:
    """Tests para onboarding de tenants."""
    
    def test_onboard_crea_client_domain_membership(self, authenticated_client):
        """Verifica que onboard crea Client, Domain y TenantMembership correctamente."""
        # Crear usuario admin
        admin = User.objects.create_superuser(
            email="admin@test.local",
            password="admin123"
        )
        authenticated_client.force_authenticate(user=admin)
        
        url = reverse("admin-tenants-onboard")
        payload = {
            "nombre": "Acme SAS",
            "dominio": "acme.localhost:8000",
            "admin_user_id": admin.id
        }
        
        response = authenticated_client.post(url, data=payload, format="json")
        assert response.status_code in (200, 201), response.data
        
        data = response.json()
        c_id = data["client"]["id"]
        
        # Verificar que se creó el Client
        assert Client.objects.filter(id=c_id).exists()
        client = Client.objects.get(id=c_id)
        assert client.nombre == "Acme SAS"
        assert client.schema_name  # Debe tener schema_name
        
        # Verificar que se creó el Domain
        domain = Domain.objects.filter(tenant_id=c_id, is_primary=True).first()
        assert domain is not None
        assert domain.domain == "acme.localhost:8000"
        assert domain.is_primary is True
        
        # Verificar que se creó la TenantMembership
        membership = TenantMembership.objects.filter(
            client_id=c_id,
            user=admin,
            rol="ADMIN",
            is_primary_admin=True
        ).first()
        assert membership is not None
        assert membership.is_primary_admin is True
        
        # Verificar que login_url está en la respuesta y apunta a la raíz (/)
        assert "login_url" in data
        login_url = data["login_url"]
        assert "acme.localhost" in login_url
        # [WARNING] REGLA DE NEGOCIO: login_url debe apuntar a la raíz (/) - landing page
        assert login_url.endswith("/"), f"login_url debe terminar en '/', got '{login_url}'"
        assert "/login" not in login_url, f"login_url NO debe contener '/login', got '{login_url}'"
    
    def test_onboard_requiere_autenticacion(self, api_client):
        """Verifica que onboard requiere autenticación."""
        url = reverse("admin-tenants-onboard")
        payload = {
            "nombre": "Test",
            "dominio": "test.localhost",
            "admin_user_id": 1
        }
        
        response = api_client.post(url, data=payload, format="json")
        assert response.status_code == 401 or response.status_code == 403
    
    def test_onboard_valida_datos(self, authenticated_client, admin_user):
        """Verifica que onboard valida datos requeridos."""
        authenticated_client.force_authenticate(user=admin_user)
        
        url = reverse("admin-tenants-onboard")
        
        # Intentar crear sin nombre
        payload = {
            "dominio": "test.localhost",
            "admin_user_id": admin_user.id
        }
        response = authenticated_client.post(url, data=payload, format="json")
        assert response.status_code == 400
