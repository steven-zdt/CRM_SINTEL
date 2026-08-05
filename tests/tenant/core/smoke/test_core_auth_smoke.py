"""
Smoke tests para Auth centralizada en Core (login, logout, password-reset).

[WARNING] POLÍTICA v2.30: Validar que Core es la única fuente de autenticación.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django_tenants.utils import schema_context
from rest_framework import status
from rest_framework.test import APIClient

from apps.public.tenants.models import TenantMembership
from tests.tenant.base_test import SintelTenantTestCase

User = get_user_model()


class TestCoreAuthSmoke(SintelTenantTestCase):
    """Tests de humo para Auth centralizada en Core."""
    
    def test_login_valid_credentials_membership_200(self):
        """POST /api/v1/core/auth/login/ (credenciales válidas + membresía) → 200 + redirect_url."""
        # Asegurar que el usuario tiene password usable
        if not self.user.has_usable_password():
            self.user.set_password('testpass123')
            self.user.save()
        
        client = APIClient(HTTP_HOST=self.domain.domain)
        response = client.post(
            '/api/v1/core/auth/login/',
            {
                'email': self.user.email,
                'password': 'testpass123',
            import pytest

            try:
                import cryptography  # noqa: F401
                import playwright  # noqa: F401
            except Exception:
                pytest.skip("Skipping heavy smoke test: missing playwright/cryptography", allow_module_level=True)
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('detail', data)
        self.assertIn('redirect_url', data)
        # Verificar que redirect_url apunta al dashboard
        redirect_url = data['redirect_url']
        self.assertIsInstance(redirect_url, str)
        # Puede ser absoluta o relativa, pero debe existir
        self.assertGreater(len(redirect_url), 0)
    
    def test_login_valid_no_membership_error(self):
        """POST /api/v1/core/auth/login/ (válidas sin membresía) → error controlado."""
        # Crear usuario sin membresía
        with schema_context('public'):
            user_no_membership = User.objects.create_user(
                username='no_member_auth',
                email='no_member_auth@example.com',
                password='testpass123',
            )
        
        client = APIClient(HTTP_HOST=self.domain.domain)
        response = client.post(
            '/api/v1/core/auth/login/',
            {
                'email': user_no_membership.email,
                'password': 'testpass123',
            },
            format='json'
        )
        
        # Debe retornar error (401 o 403) porque no tiene membresía
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        data = response.json()
        self.assertIn('detail', data)
    
    def test_login_invalid_credentials_401(self):
        """POST /api/v1/core/auth/login/ (credenciales inválidas) → 401."""
        client = APIClient(HTTP_HOST=self.domain.domain)
        response = client.post(
            '/api/v1/core/auth/login/',
            {
                'email': 'nonexistent@example.com',
                'password': 'wrongpassword',
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertIn('detail', data)
    
    def test_logout_200_redirect_url(self):
        """POST /api/v1/core/auth/logout/ → 200 + redirect_url="/"."""
        # Primero hacer login
        if not self.user.has_usable_password():
            self.user.set_password('testpass123')
            self.user.save()
        
        client = APIClient(HTTP_HOST=self.domain.domain)
        # Login
        client.post(
            '/api/v1/core/auth/login/',
            {
                'email': self.user.email,
                'password': 'testpass123',
            },
            format='json'
        )
        
        # Logout
        response = client.post('/api/v1/core/auth/logout/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('detail', data)
        self.assertIn('redirect_url', data)
        # Verificar que redirect_url es "/" o similar
        redirect_url = data['redirect_url']
        self.assertIsInstance(redirect_url, str)
        # Puede ser "/" o una URL absoluta
        self.assertGreater(len(redirect_url), 0)
    
    def test_password_reset_request_200_idempotent(self):
        """POST /api/v1/core/auth/password-reset/request/ → 200 (idempotente)."""
        client = APIClient(HTTP_HOST=self.domain.domain)
        
        # Debe retornar 200 incluso si el email no existe (idempotente)
        response = client.post(
            '/api/v1/core/auth/password-reset/request/',
            {
                'email': 'nonexistent@example.com',
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('detail', data)
        
        # Con email válido también debe retornar 200
        response2 = client.post(
            '/api/v1/core/auth/password-reset/request/',
            {
                'email': self.user.email,
            },
            format='json'
        )
        
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
    
    def test_password_reset_validate_invalid_400(self):
        """POST /api/v1/core/auth/password-reset/validate/ con token inválido → 400."""
        client = APIClient(HTTP_HOST=self.domain.domain)
        
        response = client.post(
            '/api/v1/core/auth/password-reset/validate/',
            {
                'uid': 'invalid',
                'token': 'invalid',
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn('detail', data)
    
    def test_password_reset_confirm_invalid_400(self):
        """POST /api/v1/core/auth/password-reset/confirm/ con token inválido → 400."""
        client = APIClient(HTTP_HOST=self.domain.domain)
        
        response = client.post(
            '/api/v1/core/auth/password-reset/confirm/',
            {
                'uid': 'invalid',
                'token': 'invalid',
                'password1': 'newpass123',
                'password2': 'newpass123',
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn('detail', data)
    
    def test_password_reset_confirm_valid_200_redirect_url(self):
        """POST /api/v1/core/auth/password-reset/confirm/ con token válido → 200 + redirect_url."""
        # Asegurar que el usuario tiene password usable
        if not self.user.has_usable_password():
            self.user.set_password('oldpass123')
            self.user.save()
        
        # Generar token válido
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        
        client = APIClient(HTTP_HOST=self.domain.domain)
        response = client.post(
            '/api/v1/core/auth/password-reset/confirm/',
            {
                'uid': uid,
                'token': token,
                'password1': 'newpass123',
                'password2': 'newpass123',
            },
            format='json'
        )
        
        # Debe retornar 200 con redirect_url
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('detail', data)
        self.assertIn('redirect_url', data)
        redirect_url = data['redirect_url']
        self.assertIsInstance(redirect_url, str)
        self.assertGreater(len(redirect_url), 0)
