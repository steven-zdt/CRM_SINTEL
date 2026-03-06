"""
Smoke test: Verifica que los templates de empleados existen y son accesibles.

Test no invasivo que solo verifica la estructura de archivos.
"""
from pathlib import Path
from django.test import SimpleTestCase
from django.template.loader import get_template


class EmpleadosTemplatesSmokeTest(SimpleTestCase):
    """Verifica que los partials de empleados existen y son cargables."""

    def test_list_template_exists(self):
        """Verifica que list.html existe y es cargable."""
        template = get_template("tenant/empleados/partials/list.html")
        self.assertIsNotNone(template)

    def test_create_template_exists(self):
        """Verifica que create.html existe y es cargable."""
        template = get_template("tenant/empleados/partials/create.html")
        self.assertIsNotNone(template)

    def test_edit_template_exists(self):
        """Verifica que edit.html existe y es cargable."""
        template = get_template("tenant/empleados/partials/edit.html")
        self.assertIsNotNone(template)

    def test_delete_template_exists(self):
        """Verifica que delete.html existe y es cargable."""
        template = get_template("tenant/empleados/partials/delete.html")
        self.assertIsNotNone(template)

    def test_partials_directory_structure(self):
        """Verifica que la estructura de directorios es correcta."""
        base_path = Path("apps/tenant/empleados/templates/tenant/empleados/partials")
        self.assertTrue(base_path.exists(), f"El directorio {base_path} no existe")
        
        required_files = ["list.html", "create.html", "edit.html", "delete.html"]
        for filename in required_files:
            file_path = base_path / filename
            self.assertTrue(
                file_path.exists(),
                f"El archivo {file_path} no existe"
            )
