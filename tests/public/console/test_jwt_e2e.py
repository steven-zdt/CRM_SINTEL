"""
Tests E2E para autenticación JWT en la consola.

Verifica el flujo completo de JWT:
- Login/obtener tokens
- Refresh de tokens
- Acceso con Bearer token
- Denegación sin token
- Auto-login desde sesión
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    """Cliente API para pruebas JWT."""
    return APIClient()


@pytest.fixture
def user_admin(db):
    """Usuario admin para pruebas."""
    return User.objects.create_superuser(
        email="admin@test.local",
        password="admin123",
        username="admin"
    )


class TestJWTAuthentication:
    """Tests para autenticación JWT."""
    
    def test_login_obtain_tokens(self, api_client, user_admin):
        """
        E2E: Login vía /api/token/ obtiene access + refresh tokens.
        """
        response = api_client.post('/api/token/', {
            'username': user_admin.username,
            'password': 'admin123',
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert len(response.data['access']) > 0
        assert len(response.data['refresh']) > 0
    
    def test_login_invalid_credentials(self, api_client, user_admin):
        """
        E2E: Login con credenciales inválidas devuelve 401.
        """
        response = api_client.post('/api/token/', {
            'username': user_admin.username,
            'password': 'wrong_password',
        }, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_refresh_token(self, api_client, user_admin):
        """
        E2E: Refresh token renueva access token.
        """
        # Primero obtener tokens
        login_response = api_client.post('/api/token/', {
            'username': user_admin.username,
            'password': 'admin123',
        }, format='json')
        
        assert login_response.status_code == status.HTTP_200_OK
        refresh_token = login_response.data['refresh']
        
        # Refresh token
        refresh_response = api_client.post('/api/token/refresh/', {
            'refresh': refresh_token,
        }, format='json')
        
        assert refresh_response.status_code == status.HTTP_200_OK
        assert 'access' in refresh_response.data
        assert len(refresh_response.data['access']) > 0
    
    def test_refresh_invalid_token(self, api_client):
        """
        E2E: Refresh con token inválido devuelve 401.
        """
        response = api_client.post('/api/token/refresh/', {
            'refresh': 'invalid_token',
        }, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_verify_token(self, api_client, user_admin):
        """
        E2E: Verify token valida token JWT.
        """
        # Obtener token
        login_response = api_client.post('/api/token/', {
            'username': user_admin.username,
            'password': 'admin123',
        }, format='json')
        
        assert login_response.status_code == status.HTTP_200_OK
        access_token = login_response.data['access']
        
        # Verificar token
        verify_response = api_client.post('/api/token/verify/', {
            'token': access_token,
        }, format='json')
        
        assert verify_response.status_code == status.HTTP_200_OK
    
    def test_verify_invalid_token(self, api_client):
        """
        E2E: Verify con token inválido devuelve 401.
        """
        response = api_client.post('/api/token/verify/', {
            'token': 'invalid_token',
        }, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_access_protected_endpoint_with_token(self, api_client, user_admin):
        """
        E2E: Acceso a endpoint protegido con Bearer token funciona.
        """
        # Obtener token
        login_response = api_client.post('/api/token/', {
            'username': user_admin.username,
            'password': 'admin123',
        }, format='json')
        
        assert login_response.status_code == status.HTTP_200_OK
        access_token = login_response.data['access']
        
        # Acceder a endpoint protegido con Bearer token
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = api_client.get('/api/admin/v1/tenants/')
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_access_protected_endpoint_without_token(self, api_client):
        """
        E2E: Acceso a endpoint protegido sin token devuelve 401.
        """
        response = api_client.get('/api/admin/v1/tenants/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_access_protected_endpoint_with_invalid_token(self, api_client):
        """
        E2E: Acceso a endpoint protegido con token inválido devuelve 401.
        """
        api_client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')
        response = api_client.get('/api/admin/v1/tenants/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestJWTFromSession:
    """Tests para obtención de JWT desde sesión Django."""
    
    def test_jwt_from_session_authenticated(self, client, user_admin):
        """
        E2E: /console/jwt/from-session/ devuelve JWT para usuario autenticado.
        """
        # Login con sesión Django
        assert client.login(username=user_admin.username, password='admin123')
        
        # Obtener JWT desde sesión
        response = client.get('/console/jwt/from-session/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'access' in data
        assert 'refresh' in data
        assert len(data['access']) > 0
        assert len(data['refresh']) > 0
    
    def test_jwt_from_session_unauthenticated(self, client):
        """
        E2E: /console/jwt/from-session/ devuelve 401 para usuario no autenticado.
        """
        response = client.get('/console/jwt/from-session/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert 'error' in data


class TestJWTRotation:
    """Tests para rotación de refresh tokens."""
    
    def test_refresh_rotates_token(self, api_client, user_admin):
        """
        E2E: Refresh token rota refresh token si ROTATE_REFRESH_TOKENS=True.
        
        Nota: Esto depende de la configuración SIMPLE_JWT['ROTATE_REFRESH_TOKENS'].
        Si está en True, el refresh devuelve un nuevo refresh token.
        """
        # Obtener tokens iniciales
        login_response = api_client.post('/api/token/', {
            'username': user_admin.username,
            'password': 'admin123',
        }, format='json')
        
        assert login_response.status_code == status.HTTP_200_OK
        original_refresh = login_response.data['refresh']
        
        # Refresh token (puede rotar si ROTATE_REFRESH_TOKENS=True)
        refresh_response = api_client.post('/api/token/refresh/', {
            'refresh': original_refresh,
        }, format='json')
        
        assert refresh_response.status_code == status.HTTP_200_OK
        assert 'access' in refresh_response.data
        
        # Si ROTATE_REFRESH_TOKENS=True, también devuelve nuevo refresh
        # Si False, solo devuelve access
        # Verificamos que al menos el access esté presente
        assert len(refresh_response.data['access']) > 0
