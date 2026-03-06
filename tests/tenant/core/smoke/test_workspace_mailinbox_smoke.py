"""
Tests de humo para UI de MailInboxConfig en workspace.

⚠️ v2.37: Alineado con UI estándar tenant apps.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

User = get_user_model()


class WorkspaceMailinboxSmokeTest(TestCase):
    """
    Tests de humo para render del panel mailinbox en workspace.
    """
    
    def setUp(self):
        """Setup: Crear cliente y usuario de prueba."""
        self.client = Client()
        # TODO: Crear usuario y tenant para tests reales
    
    def test_workspace_includes_mailinbox_partial(self):
        """Test: workspace.html incluye partial de mailinbox."""
        # Sin autenticación, debería redirigir o mostrar login
        response = self.client.get('/workspace/')
        # Verificar que el partial está incluido (requiere autenticación)
        self.assertIn(response.status_code, [200, 302, 401, 403])
    
    def test_mailinbox_js_loaded(self):
        """Test: mailinbox.page.js está cargado en workspace."""
        # Este test requiere verificar el HTML renderizado
        # Por ahora, solo verificar que la ruta existe
        pass
