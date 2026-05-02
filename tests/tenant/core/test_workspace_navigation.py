"""
Tests de navegación del workspace: verifica que los links de empleados y gastos funcionen.

Verifica:
1. Que los links existan en el sidebar
2. Que las secciones existan en el DOM
3. Que el hash navigation funcione correctamente
"""
import re
from pathlib import Path
from django.test import SimpleTestCase

TEMPLATE_PATH = Path("apps/tenant/core/templates/tenant/core/workspace.html")


class WorkspaceNavigationTest(SimpleTestCase):
    """Tests de navegación del workspace."""

    def test_template_exists(self):
        """Verifica que el template existe."""
        self.assertTrue(TEMPLATE_PATH.exists(), "workspace.html no existe")

    def test_empleados_link_in_sidebar(self):
        """Verifica que el link de empleados esté en el sidebar."""
        content = TEMPLATE_PATH.read_text(encoding="utf-8", errors="ignore")
        # Buscar el link en el sidebar
        self.assertIn('href="#empleados"', content, "Link de empleados no encontrado en sidebar")
        self.assertIn('data-view="empleados"', content, "Atributo data-view de empleados no encontrado")
        self.assertIn("👥 Empleados", content, "Texto del link de empleados no encontrado")

    def test_gastos_link_in_sidebar(self):
        """Verifica que el link de gastos esté en el sidebar."""
        content = TEMPLATE_PATH.read_text(encoding="utf-8", errors="ignore")
        # Buscar el link en el sidebar
        self.assertIn('href="#gastos"', content, "Link de gastos no encontrado en sidebar")
        self.assertIn('data-view="gastos"', content, "Atributo data-view de gastos no encontrado")
        self.assertIn("💰 Gastos", content, "Texto del link de gastos no encontrado")

    def test_empleados_section_exists(self):
        """Verifica que la sección view-empleados exista."""
        content = TEMPLATE_PATH.read_text(encoding="utf-8", errors="ignore")
        self.assertIn('id="view-empleados"', content, "Sección view-empleados no encontrada")
        self.assertIn("tenant/empleados/partials/list.html", content, "Partial de list de empleados no incluido")

    def test_gastos_section_exists(self):
        """Verifica que la sección view-gastos exista."""
        content = TEMPLATE_PATH.read_text(encoding="utf-8", errors="ignore")
        self.assertIn('id="view-gastos"', content, "Sección view-gastos no encontrada")
        self.assertIn("tenant/gastos/partials/list.html", content, "Partial de list de gastos no incluido")

    def test_setActiveView_includes_empleados_and_gastos(self):
        """Verifica que setActiveView incluya empleados y gastos."""
        content = TEMPLATE_PATH.read_text(encoding="utf-8", errors="ignore")
        # Buscar la función setActiveView
        pattern = r'setActiveView\(view\)\s*\{[^}]*sections\s*=\s*\[([^\]]+)\]'
        match = re.search(pattern, content, re.DOTALL)
        self.assertIsNotNone(match, "Función setActiveView no encontrada")
        sections_str = match.group(1)
        self.assertIn('"empleados"', sections_str, "empleados no está en la lista de secciones")
        self.assertIn('"gastos"', sections_str, "gastos no está en la lista de secciones")

    def test_currentViewFromHash_includes_empleados_and_gastos(self):
        """Verifica que currentViewFromHash incluya empleados y gastos."""
        content = TEMPLATE_PATH.read_text(encoding="utf-8", errors="ignore")
        # Buscar la función currentViewFromHash
        pattern = r'currentViewFromHash\(\)\s*\{[^}]*return\s*\[([^\]]+)\]'
        match = re.search(pattern, content, re.DOTALL)
        self.assertIsNotNone(match, "Función currentViewFromHash no encontrada")
        views_str = match.group(1)
        self.assertIn('"empleados"', views_str, "empleados no está en la lista de views válidas")
        self.assertIn('"gastos"', views_str, "gastos no está en la lista de views válidas")

    def test_js_files_included(self):
        """Verifica que los archivos JS estén incluidos."""
        content = TEMPLATE_PATH.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("tenant/empleados/devengos.page.js", content, "JS de devengos no incluido")
        self.assertIn("tenant/gastos/gastos.page.js", content, "JS de gastos no incluido")
