"""
Smoke tests de templates para la app accounts.

Verifica que los endpoints API no renderizan templates HTML.
"""
from apps.config.tests.base_public import PublicAPITestCase


class AccountsTemplateTests(PublicAPITestCase):
    """Tests de templates para endpoints de accounts."""
    
    def setUp(self):
        """Configuración inicial."""
        super().setUp()
        from apps.public.accounts.models import User
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123',
        )
    
    def test_api_endpoints_no_render_templates(self):
        """Test: Los endpoints /api/public/v1/users/ no renderizan templates."""
        response = self.json('get', '/api/public/v1/users/')
        self.assertEqual(response['content-type'], 'application/json')
        self.assertNotIn('text/html', response['content-type'])
    
    def test_me_endpoint_no_render_templates(self):
        """Test: El endpoint me/ no renderiza templates."""
        self.client.force_authenticate(user=self.user)
        response = self.json('get', '/api/public/v1/users/me/')
        self.assertEqual(response['content-type'], 'application/json')
        self.assertNotIn('text/html', response['content-type'])
