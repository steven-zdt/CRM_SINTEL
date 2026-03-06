"""
Tests para validar que el onboarding NO acepta campos de password (v2.29).

⚠️ OBJETIVO: Garantizar que las contraseñas solo se establezcan en la activación.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


@pytest.mark.django_db
class TestOnboardingSinPassword:
    """Tests para validar que el onboarding rechaza campos de password."""
    
    def test_onboard_rechaza_password(self, api_client, staff_user):
        """Verifica que el onboarding rechaza campos de password con 400."""
        api_client.force_authenticate(user=staff_user)
        
        payload = {
            "nombre": "Empresa Test",
            "schema_name": "empresa_test",
            "owner_email": "owner@test.com",
            "password": "Test1234!",  # ⚠️ Campo rechazado
        }
        
        response = api_client.post('/api/public/v1/tenants/onboard/', payload)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "No se permite establecer contraseña" in str(response.data)
        assert "password" in str(response.data).lower()
    
    def test_onboard_rechaza_password1(self, api_client, staff_user):
        """Verifica que el onboarding rechaza password1."""
        api_client.force_authenticate(user=staff_user)
        
        payload = {
            "nombre": "Empresa Test",
            "schema_name": "empresa_test",
            "owner_email": "owner@test.com",
            "password1": "Test1234!",  # ⚠️ Campo rechazado
        }
        
        response = api_client.post('/api/public/v1/tenants/onboard/', payload)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "No se permite establecer contraseña" in str(response.data)
    
    def test_onboard_rechaza_password2(self, api_client, staff_user):
        """Verifica que el onboarding rechaza password2."""
        api_client.force_authenticate(user=staff_user)
        
        payload = {
            "nombre": "Empresa Test",
            "schema_name": "empresa_test",
            "owner_email": "owner@test.com",
            "password2": "Test1234!",  # ⚠️ Campo rechazado
        }
        
        response = api_client.post('/api/public/v1/tenants/onboard/', payload)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "No se permite establecer contraseña" in str(response.data)
    
    def test_onboard_rechaza_owner_password(self, api_client, staff_user):
        """Verifica que el onboarding rechaza owner_password."""
        api_client.force_authenticate(user=staff_user)
        
        payload = {
            "nombre": "Empresa Test",
            "schema_name": "empresa_test",
            "owner_email": "owner@test.com",
            "owner_password": "Test1234!",  # ⚠️ Campo rechazado
        }
        
        response = api_client.post('/api/public/v1/tenants/onboard/', payload)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "No se permite establecer contraseña" in str(response.data)
    
    def test_onboard_acepta_sin_password(self, api_client, staff_user):
        """Verifica que el onboarding acepta payload sin campos de password."""
        api_client.force_authenticate(user=staff_user)
        
        payload = {
            "nombre": "Empresa Test",
            "schema_name": "empresa_test",
            "owner_email": "owner@test.com",
            # Sin campos de password
        }
        
        response = api_client.post('/api/public/v1/tenants/onboard/', payload)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert "client_id" in response.data
        assert "domain" in response.data
        
        # Verificar que el usuario se creó sin password usable
        user = User.objects.filter(email="owner@test.com").first()
        assert user is not None
        assert not user.has_usable_password()  # ⚠️ CRÍTICO: Sin password usable
    
    def test_onboard_owner_sin_password_usable(self, api_client, staff_user):
        """Verifica que el owner creado NO tiene password usable."""
        api_client.force_authenticate(user=staff_user)
        
        payload = {
            "nombre": "Empresa Test",
            "schema_name": "empresa_test",
            "owner_email": "owner@test.com",
        }
        
        response = api_client.post('/api/public/v1/tenants/onboard/', payload)
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verificar que el usuario NO tiene password usable
        user = User.objects.filter(email="owner@test.com").first()
        assert user is not None
        assert not user.has_usable_password()  # ⚠️ CRÍTICO: Sin password usable
        
        # Verificar que el usuario NO puede loguearse antes de activar
        from django.test import Client
        from apps.public.tenants.models import Client as TenantClient, Domain
        
        tenant = TenantClient.objects.get(schema_name="empresa_test")
        domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
        
        client = Client(HTTP_HOST=domain.domain)
        login_response = client.post('/login/', {
            'username': user.email,
            'password': 'cualquier_password',
        })
        
        # El login debe fallar porque el usuario no tiene password usable
        assert login_response.status_code in [200, 302]  # Puede ser 200 con error o redirect
        # No debe estar autenticado
        assert not login_response.wsgi_request.user.is_authenticated
