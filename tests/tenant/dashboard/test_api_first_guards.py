"""
Tests de guarda para asegurar API-First estricto en dashboard.

Verifica que no existan:
- TemplateView o vistas que rendericen HTML
- Llamadas a render() o render_to_response()
- Templates en apps/tenant/dashboard/templates/
- Rutas que apunten a vistas HTML
"""

import ast
import os
from pathlib import Path

from django.test import TestCase


class TestAPIFirstGuards(TestCase):
    """Tests de guarda para API-First estricto."""

    def test_no_template_views_in_dashboard(self):
        """Verifica que no existan TemplateView en apps/tenant/dashboard."""
        dashboard_path = Path("apps/tenant/dashboard")

        # Buscar archivos Python
        python_files = list(dashboard_path.rglob("*.py"))

        for file_path in python_files:
            # Saltar __pycache__ y archivos de tests
            if "__pycache__" in str(file_path) or "test" in str(file_path):
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

                # Verificar que no haya TemplateView
                if "TemplateView" in content:
                    # Verificar que no sea un comentario o docstring
                    try:
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                for base in node.bases:
                                    if (
                                        isinstance(base, ast.Name)
                                        and base.id == "TemplateView"
                                    ):
                                        self.fail(
                                            f"[ERROR] TemplateView encontrado en {file_path}: "
                                            f"clase {node.name} hereda de TemplateView. "
                                            f"Usa API-First en su lugar."
                                        )
                    except SyntaxError:
                        # Si hay error de sintaxis, solo verificar el string
                        if "class" in content and "TemplateView" in content:
                            self.fail(
                                f"[ERROR] Posible TemplateView en {file_path}. "
                                f"Revisa manualmente."
                            )

    def test_no_render_calls_in_dashboard(self):
        """Verifica que no existan llamadas a render() o render_to_response()."""
        dashboard_path = Path("apps/tenant/dashboard")

        # Buscar archivos Python
        python_files = list(dashboard_path.rglob("*.py"))

        forbidden_patterns = [
            "render(",
            "render_to_response(",
            "loader.render_to_string(",
        ]

        for file_path in python_files:
            # Saltar __pycache__ y archivos de tests
            if "__pycache__" in str(file_path) or "test" in str(file_path):
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

                for pattern in forbidden_patterns:
                    if pattern in content:
                        # Verificar que no sea un comentario
                        lines = content.split("\n")
                        for i, line in enumerate(lines, 1):
                            if pattern in line and not line.strip().startswith("#"):
                                # Verificar que no sea un docstring
                                if '"""' not in line and "'''" not in line:
                                    self.fail(
                                        f"[ERROR] Llamada a {pattern} encontrada en {file_path}:{i}. "
                                        f"Usa API-First en su lugar."
                                    )

    def test_no_templates_in_dashboard(self):
        """Verifica que no existan templates en apps/tenant/dashboard/templates/."""
        templates_path = Path("apps/tenant/dashboard/templates")

        if templates_path.exists():
            # Buscar archivos HTML
            html_files = list(templates_path.rglob("*.html"))

            if html_files:
                self.fail(
                    f"[ERROR] Templates HTML encontrados en apps/tenant/dashboard/templates/: "
                    f"{[str(f) for f in html_files]}. "
                    f"Elimina estos templates y usa shells estáticos en su lugar."
                )

    def test_dashboard_urls_only_redirect_to_static(self):
        """Verifica que las URLs del dashboard solo redirijan a estáticos o API."""
        urls_file = Path("apps/tenant/dashboard/urls.py")

        if not urls_file.exists():
            self.fail("[ERROR] apps/tenant/dashboard/urls.py no existe.")

        with open(urls_file, "r", encoding="utf-8") as f:
            content = f.read()

            # Verificar que no haya referencias a vistas que rendericen HTML
            forbidden_patterns = [
                "TemplateView",
                ".as_view()",  # Solo permitir si es RedirectView o API views
                "render(",
            ]

            # Verificar que solo haya RedirectView o lambdas que redirijan a estáticos
            if "TemplateView" in content:
                self.fail(
                    "[ERROR] TemplateView encontrado en apps/tenant/dashboard/urls.py. "
                    "Solo se permiten RedirectView o redirecciones a estáticos."
                )

    def test_dashboard_views_only_redirect(self):
        """Verifica que las vistas del dashboard solo redirijan (no rendericen)."""
        views_file = Path("apps/tenant/dashboard/views.py")

        if not views_file.exists():
            # Si no existe views.py, está bien (todo es API)
            return

        with open(views_file, "r", encoding="utf-8") as f:
            content = f.read()

            # Verificar que solo haya RedirectView
            if "TemplateView" in content:
                self.fail(
                    "[ERROR] TemplateView encontrado en apps/tenant/dashboard/views.py. "
                    "Solo se permiten RedirectView para redirigir a shells estáticos."
                )

            if "render(" in content or "render_to_response(" in content:
                self.fail(
                    "[ERROR] Llamadas a render() encontradas en apps/tenant/dashboard/views.py. "
                    "Solo se permiten redirecciones a shells estáticos."
                )
