"""
Tests de humo para validar columna Naturaleza y assets en workspace.html.
"""
import re

from django.urls import reverse

from tests.tenant.base_test import SintelTenantTestCase


class WorkspaceFacturasLinksAndColumnTests(SintelTenantTestCase):
    """Tests para validar que la tabla de facturas tiene la columna Naturaleza y assets correctos."""
    
    def setUp(self):
        super().setUp()
        # F29-002: contrato real confirmado -- apps/tenant/core/urls_ui.py
        # declara app_name = 'core_ui' y registra path('workspace/', ...,
        # name='workspace'), incluido en config/urls_tenant.py sin
        # namespace= explicito (Django toma el app_name del modulo
        # incluido) -- el nombre reversible real es 'core_ui:workspace',
        # nunca 'tenant-workspace' (nunca existio) ni 'workspace' a secas
        # (NoReverseMatch: no esta namespaced). Confirmado:
        # reverse('core_ui:workspace') == '/workspace/'.
        try:
            self.url = reverse("core_ui:workspace")
        except Exception:
            self.url = "/workspace/"
    
    def test_columna_naturaleza_y_assets(self):
        """Valida que la columna Naturaleza está presente y los assets no están duplicados."""
        self.skipTest(
            "Hallazgo real: la tabla de facturas (<th>Naturaleza</th>, "
            "id=tbl-facturas) y facturas.page.js ya no viven inline en "
            "workspace.html -- migracion FASE 5-BIS a django-tables2+HTMX "
            "(documentacion/plan_refactorizacion.md seccion 2.1, "
            "F31_FRONTEND_INVENTORY.md: facturas = 'Migrado'). Reescribir "
            "requiere el contrato real del nuevo endpoint HTMX, fuera de "
            "alcance de saneamiento de tests -- rediseno dedicado."
        )
        resp = self.client.get(self.url)
        
        # Si la URL no existe o requiere autenticación, saltar el test
        if resp.status_code in (404, 302, 401):
            self.skipTest(f"Workspace URL no disponible o requiere autenticación: {resp.status_code}")
        
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")
        
        # Validar que la columna Naturaleza está presente en el thead
        self.assertIn("<th>Naturaleza</th>", html, 
                     "La columna 'Naturaleza' debe estar presente en el thead de la tabla")
        
        # Validar que el script de facturas está incluido
        self.assertIn('/static/tenant/landing/workspace/facturas.page.js', html,
                     "El script facturas.page.js debe estar incluido")
        
        # Validar que no hay duplicación del script
        matches = re.findall(r'/static/tenant/landing/workspace/facturas\.page\.js', html)
        self.assertLessEqual(len(matches), 1,
                            f"El script facturas.page.js no debe estar duplicado (encontrado {len(matches)} veces)")
        
        # Validar que la tabla tiene el ID correcto
        self.assertIn('id="tbl-facturas"', html,
                     "La tabla debe tener el ID 'tbl-facturas'")
        
        # Validar que el tbody existe
        self.assertIn('<tbody>', html,
                     "La tabla debe tener un tbody para renderizado dinámico")
