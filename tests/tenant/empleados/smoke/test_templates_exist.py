"""
Smoke test: Verifica que los templates de empleados existen y son accesibles.

Test no invasivo que solo verifica la estructura de archivos.
"""
from pathlib import Path
from django.test import SimpleTestCase
from django.template.loader import get_template


class EmpleadosTemplatesSmokeTest(SimpleTestCase):
    """Verifica que los templates de empleados existen y son cargables."""

    def test_list_template_exists(self):
        """Verifica que empleados_list.html existe y es cargable."""
        template = get_template("tenant/empleados/empleados_list.html")
        self.assertIsNotNone(template)

    def test_create_template_exists(self):
        """Verifica que offcanvas_crear_empleado.html existe y es cargable."""
        template = get_template("tenant/empleados/offcanvas_crear_empleado.html")
        self.assertIsNotNone(template)

    def test_edit_template_exists(self):
        """Verifica que offcanvas_editar_empleado.html existe y es cargable."""
        template = get_template("tenant/empleados/offcanvas_editar_empleado.html")
        self.assertIsNotNone(template)

    def test_assets_template_exists(self):
        """Verifica que assets_empleados.html existe y es cargable."""
        template = get_template("tenant/empleados/assets_empleados.html")
        self.assertIsNotNone(template)

    def test_templates_directory_structure(self):
        """Verifica que la estructura de directorios y archivos FSD es correcta."""
        base_path = Path("apps/tenant/empleados/templates/tenant/empleados")
        self.assertTrue(base_path.exists(), f"El directorio {base_path} no existe")
        
        required_files = [
            "empleados_list.html",
            "offcanvas_crear_empleado.html",
            "offcanvas_editar_empleado.html",
            "assets_empleados.html"
        ]
        for filename in required_files:
            file_path = base_path / filename
            self.assertTrue(
                file_path.exists(),
                f"El archivo {file_path} no existe"
            )

