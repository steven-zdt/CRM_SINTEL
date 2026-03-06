"""
Pruebas de humo para verificar la estructura de templates y estáticos.

Verifica que:
- Los templates base se pueden cargar
- Los partials se pueden incluir
- Los estáticos se resuelven correctamente
"""
from django.test import TestCase
from django.template.loader import get_template, TemplateDoesNotExist
from django.template import Context
from tests.tenant.base_test import SintelTenantTestCase


class TemplateStructureTests(SintelTenantTestCase):
    """Tests de estructura de templates para tenant."""
    
    def test_base_template_exists(self):
        """Test: El template base existe y se puede cargar."""
        try:
            template = get_template('tenant/base.html')
            self.assertIsNotNone(template)
        except TemplateDoesNotExist:
            self.fail("Template 'tenant/base.html' no existe")
    
    def test_header_partial_exists(self):
        """Test: El partial _header.html existe y se puede incluir."""
        try:
            template = get_template('tenant/partials/_header.html')
            self.assertIsNotNone(template)
        except TemplateDoesNotExist:
            self.fail("Template 'tenant/partials/_header.html' no existe")
    
    def test_footer_partial_exists(self):
        """Test: El partial _footer.html existe y se puede incluir."""
        try:
            template = get_template('tenant/partials/_footer.html')
            self.assertIsNotNone(template)
        except TemplateDoesNotExist:
            self.fail("Template 'tenant/partials/_footer.html' no existe")
    
    def test_messages_partial_exists(self):
        """Test: El partial _messages.html existe y se puede incluir."""
        try:
            template = get_template('tenant/partials/_messages.html')
            self.assertIsNotNone(template)
        except TemplateDoesNotExist:
            self.fail("Template 'tenant/partials/_messages.html' no existe")
    
    def test_base_template_renders(self):
        """Test: El template base se puede renderizar sin errores."""
        try:
            template = get_template('tenant/base.html')
            context = Context({
                'user': self.user,
                'csrf_token': 'test-token',
            })
            rendered = template.render(context)
            self.assertIn('SINTEL', rendered)
        except Exception as e:
            self.fail(f"Error renderizando template base: {e}")
    
    def test_error_templates_exist(self):
        """Test: Los templates de error existen."""
        try:
            template_404 = get_template('tenant/errors/404.html')
            template_403 = get_template('tenant/errors/403.html')
            self.assertIsNotNone(template_404)
            self.assertIsNotNone(template_403)
        except TemplateDoesNotExist as e:
            self.fail(f"Template de error no existe: {e}")


class StaticFilesStructureTests(SintelTenantTestCase):
    """Tests de estructura de archivos estáticos."""
    
    def test_landing_static_files_exist(self):
        """Test: Los archivos estáticos de landing están en la app."""
        import os
        from django.conf import settings
        
        # Verificar que los archivos están en la ubicación correcta
        landing_static_path = os.path.join(
            settings.BASE_DIR,
            'apps',
            'tenant',
            'landing',
            'static',
            'tenant',
            'landing'
        )
        
        self.assertTrue(
            os.path.exists(landing_static_path),
            f"Directorio de estáticos de landing no existe: {landing_static_path}"
        )
        
        # Verificar que index.html existe
        index_path = os.path.join(landing_static_path, 'index.html')
        self.assertTrue(
            os.path.exists(index_path),
            f"index.html no existe en: {index_path}"
        )
    
    def test_dashboard_static_files_exist(self):
        """Test: Los archivos estáticos de dashboard están en la app."""
        import os
        from django.conf import settings
        
        # Verificar que los archivos están en la ubicación correcta
        dashboard_static_path = os.path.join(
            settings.BASE_DIR,
            'apps',
            'tenant',
            'dashboard',
            'static',
            'tenant',
            'dashboard'
        )
        
        self.assertTrue(
            os.path.exists(dashboard_static_path),
            f"Directorio de estáticos de dashboard no existe: {dashboard_static_path}"
        )
        
        # Verificar que index.html existe
        index_path = os.path.join(dashboard_static_path, 'index.html')
        self.assertTrue(
            os.path.exists(index_path),
            f"index.html no existe en: {index_path}"
        )
