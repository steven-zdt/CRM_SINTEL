"""
Smoke test para validar que la sección de Activos Fijos se movió de #inventario a #empresa.

Este test solo valida la estructura HTML del template, sin tocar endpoints ni modelos.
"""
import re
from pathlib import Path
from django.test import SimpleTestCase

# Ruta del template del workspace (según arquitectura)
# apps/tenant/core/templates/tenant/core/workspace.html
# Fuente: arquitectura_general.md (UI del workspace en core/tenant).
TEMPLATE_PATH = Path("apps/tenant/core/templates/tenant/core/workspace.html")


class WorkspaceActivosFijosMoveSmokeTest(SimpleTestCase):
    maxDiff = None

    def test_template_exists(self):
        """Verifica que el template workspace.html existe."""
        self.assertTrue(TEMPLATE_PATH.exists(), "workspace.html no existe en la ruta esperada")

    def test_block_markers_present(self):
        """Verifica que los marcadores BEGIN/END están presentes en el template."""
        content = TEMPLATE_PATH.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("BEGIN:AF-TABLE-AND-MODAL", content)
        self.assertIn("END:AF-TABLE-AND-MODAL", content)

    def test_block_is_under_empresa_not_inventario(self):
        """Verifica que el bloque de Activos Fijos está dentro de #empresa y no en #inventario."""
        content = TEMPLATE_PATH.read_text(encoding="utf-8", errors="ignore")
        # Normaliza espacios para evitar falsos negativos
        norm = re.sub(r"\s+", " ", content)
        
        # Posiciones de anclas/secciones
        pos_empresa = norm.find('id="view-empresa"')
        pos_inventario = norm.find('id="view-inventario"')
        pos_begin = norm.find("BEGIN:AF-TABLE-AND-MODAL")
        pos_end = norm.find("END:AF-TABLE-AND-MODAL")
        
        self.assertNotEqual(pos_begin, -1, "No se encontró el marcador BEGIN:AF-TABLE-AND-MODAL")
        self.assertNotEqual(pos_end, -1, "No se encontró el marcador END:AF-TABLE-AND-MODAL")
        self.assertNotEqual(pos_empresa, -1, "No se encontró la sección #view-empresa")
        
        # Asegura que el bloque está DESPUÉS de #view-empresa
        self.assertTrue(
            pos_begin > pos_empresa,
            "El bloque de Activos fijos no se encuentra dentro/después de #view-empresa",
        )
        
        # Si existe #view-inventario, aseguramos que el bloque NO esté dentro de ese rango
        if pos_inventario != -1:
            # Buscar el cierre de la sección inventario (buscamos el siguiente </section> después de view-inventario)
            # Para simplificar, verificamos que el bloque no esté entre inventario y su cierre
            # Buscamos el patrón: id="view-inventario" ... BEGIN:AF-TABLE-AND-MODAL
            inventario_section = norm[pos_inventario:pos_inventario + 5000]  # Buscar en los siguientes 5000 caracteres
            if "BEGIN:AF-TABLE-AND-MODAL" in inventario_section:
                # Si encontramos el bloque dentro de la sección inventario, fallar
                self.fail("El bloque de Activos fijos sigue dentro de #view-inventario")

    def test_activos_table_included(self):
        """Verifica que el include de la tabla de activos está presente."""
        content = TEMPLATE_PATH.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("_activos_table.html", content, "El include de la tabla de activos no está presente")

    def test_activos_modals_included(self):
        """Verifica que el include del modal de activos está presente."""
        content = TEMPLATE_PATH.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("_activos_modals.html", content, "El include del modal de activos no está presente")
