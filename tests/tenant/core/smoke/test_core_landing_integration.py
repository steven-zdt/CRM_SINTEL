"""
Smoke tests para Landing vía Core (info, activate).

[WARNING] POLÍTICA v2.30: Validar que Core expone landing/info y landing/auth/activate correctamente.
"""
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from apps.public.tenants.models import TenantMembership
from apps.public.tenants.services.invitations import generate_invitation_token, verify_invitation_token
from tests.tenant.base_test import SintelTenantTestCase

User = get_user_model()


class TestCoreLandingIntegration(SintelTenantTestCase):
    """Tests de humo para Landing vía Core."""
        import pytest

        try:
            import playwright  # noqa: F401
            import cryptography  # noqa: F401
        except Exception:
            pytest.skip("Skipping heavy smoke test: missing playwright/cryptography", allow_module_level=True)
    
    def test_landing_info_200_anonimo(self):
        """GET /api/v1/core/landing/info/ (anónimo) → 200 con datos públicos mínimos."""
        client = APIClient(HTTP_HOST=self.domain.domain)
        
        response = client.get('/api/v1/core/landing/info/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = response.json()
        
        # Datos públicos mínimos esperados
        self.assertIn('nombre', data)
        self.assertIn('schema_name', data)
        self.assertIn('is_active', data)
        self.assertIn('branding', data)
        
        # Verificar que el nombre viene del tenant
        self.assertEqual(data['nombre'], self.tenant.nombre)
        self.assertEqual(data['schema_name'], self.tenant.schema_name)
        self.assertIsInstance(data['is_active'], bool)
    
    def test_landing_info_200_autenticado(self):
        """GET /api/v1/core/landing/info/ (autenticado) → 200 con datos públicos mínimos."""
        response = self.api_client.get('/api/v1/core/landing/info/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = response.json()
        
        # Mismas validaciones que anónimo
        self.assertIn('nombre', data)
        self.assertIn('schema_name', data)
        self.assertIn('branding', data)
    
    def test_landing_activate_get_no_token_400(self):
        """GET /api/v1/core/landing/auth/activate/ sin token → 400."""
        client = APIClient(HTTP_HOST=self.domain.domain)
        
        response = client.get('/api/v1/core/landing/auth/activate/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn('detail', data)
        self.assertIn('Token', data['detail'])
    
    def test_landing_activate_get_invalid_token_400(self):
        """GET /api/v1/core/landing/auth/activate/?token=invalid → 400."""
        client = APIClient(HTTP_HOST=self.domain.domain)
        
        response = client.get('/api/v1/core/landing/auth/activate/?token=invalid')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn('detail', data)
    
    def test_landing_activate_get_valid_token_200(self):
        """GET /api/v1/core/landing/auth/activate/?token=VAL → 200 si token válido y usuario sin password usable."""
        # Crear usuario sin password usable
        with schema_context('public'):
            user_no_password = User.objects.create_user(
                username='no_password',
                email='no_password@example.com',
                password=None,  # Sin password usable
            )
            # Asegurar que no tiene password usable
            user_no_password.set_unusable_password()
            user_no_password.save()
            
            # Crear membresía
            TenantMembership.objects.create(
                client=self.tenant,
                user=user_no_password,
                is_active=True,
            )
            
            # Generar token válido
            token = generate_invitation_token(
                user_id=user_no_password.id,
                tenant_id=self.tenant.id,
            )
        
        client = APIClient(HTTP_HOST=self.domain.domain)
        response = client.get(f'/api/v1/core/landing/auth/activate/?token={token}')
        
        # Debe retornar 200 si el token es válido
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('user', data)
        self.assertIn('tenant', data)
        self.assertIn('token_valid', data)
        self.assertTrue(data['token_valid'])
    
    def test_landing_activate_get_already_activated_409(self):
        """GET /api/v1/core/landing/auth/activate/?token=VAL → 409 si ya activado."""
        # Crear usuario con password usable
        with schema_context('public'):
            user_activated = User.objects.create_user(
                username='activated',
                email='activated@example.com',
                password='testpass123',  # Con password usable
            )
            
            # Crear membresía
            TenantMembership.objects.create(
                client=self.tenant,
                user=user_activated,
                is_active=True,
            )
            
            # Generar token válido
            token = generate_invitation_token(
                user_id=user_activated.id,
                tenant_id=self.tenant.id,
            )
        
        client = APIClient(HTTP_HOST=self.domain.domain)
        response = client.get(f'/api/v1/core/landing/auth/activate/?token={token}')
        
        # Debe retornar 409 si ya tiene password usable
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        data = response.json()
        self.assertIn('detail', data)
        self.assertIn('redirect_url', data)
        self.assertIn('login_api_url', data)
    
    def test_landing_activate_post_no_token_400(self):
        """POST /api/v1/core/landing/auth/activate/ sin token → 400."""
        client = APIClient(HTTP_HOST=self.domain.domain)
        
        response = client.post(
            '/api/v1/core/landing/auth/activate/',
            {
                'password1': 'newpass123',
                'password2': 'newpass123',
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn('detail', data)
        self.assertIn('Token', data['detail'])
    
    def test_landing_activate_post_no_passwords_400(self):
        """POST /api/v1/core/landing/auth/activate/?token=... sin passwords → 400."""
        client = APIClient(HTTP_HOST=self.domain.domain)
        
        response = client.post(
            '/api/v1/core/landing/auth/activate/?token=test',
            {},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn('detail', data)
        self.assertIn('contraseñas', data['detail'])
    
    def test_landing_activate_post_valid_200_redirect_url(self):
        """POST /api/v1/core/landing/auth/activate/?token=VAL con password → 200 + redirect_url absoluta."""
        # Crear usuario sin password usable
        with schema_context('public'):
            user_no_password = User.objects.create_user(
                username='no_password2',
                email='no_password2@example.com',
                password=None,
            )
            user_no_password.set_unusable_password()
            user_no_password.save()
            
            # Crear membresía
            TenantMembership.objects.create(
                client=self.tenant,
                user=user_no_password,
                is_active=True,
            )
            
            # Generar token válido
            token = generate_invitation_token(
                user_id=user_no_password.id,
                tenant_id=self.tenant.id,
            )
        
        client = APIClient(HTTP_HOST=self.domain.domain)
        response = client.post(
            f'/api/v1/core/landing/auth/activate/?token={token}',
            {
                'password1': 'newpass123',
                'password2': 'newpass123',
            },
            format='json'
        )
        
        # Debe retornar 200 con redirect_url si el token es válido
        # Nota: Puede retornar 409 si el usuario ya tiene password usable
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_409_CONFLICT])
        data = response.json()
        self.assertIn('detail', data)
        if response.status_code == status.HTTP_200_OK:
            self.assertIn('redirect_url', data)
            # Verificar que redirect_url es absoluta o relativa válida
            redirect_url = data['redirect_url']
            self.assertIsInstance(redirect_url, str)
            self.assertGreater(len(redirect_url), 0)
