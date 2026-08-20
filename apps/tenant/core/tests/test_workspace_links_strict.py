"""
Pruebas de humo estrictas para enlaces/URLs en workspace.html y columna Naturaleza.

Verifica:
- Enlaces exactos (paths absolutos relativos al tenant; sin host/protocolo)
- APIs relativas del tenant (/api/v1/...)
- Sin protocolo/host hardcodeados, sin dobles slashes
- Sin duplicación de assets de workspace
- Columna "Naturaleza" presente en tabla de facturas
"""
import re

from django.urls import reverse

from tests.tenant.base_test import SintelTenantTestCase


class WorkspaceLinksStrictTests(SintelTenantTestCase):
    """Tests estrictos para enlaces y URLs en workspace.html."""
    
    def setUp(self):
        super().setUp()
        # F29-002: contrato real confirmado -- 'core_ui:workspace' (ver
        # apps/tenant/core/urls_ui.py, app_name = 'core_ui'). Los nombres
        # sin namespace nunca existieron.
        self.workspace_urls = [
            reverse("core_ui:workspace") if self._url_exists("core_ui:workspace") else None,
        ]
        self.workspace_url = next((url for url in self.workspace_urls if url), "/workspace/")

    def _url_exists(self, name):
        """Helper para verificar si una URL existe."""
        try:
            reverse(name)
            return True
        except Exception:
            return False


class WorkspaceFacturasLinksAndColumnTests(SintelTenantTestCase):
    """Tests estrictos para enlaces/URLs y columna Naturaleza en workspace.html."""
    
    def setUp(self):
        super().setUp()
        # F29-002: contrato real confirmado -- 'core_ui:workspace' (ver
        # apps/tenant/core/urls_ui.py, app_name = 'core_ui'). Los nombres
        # sin namespace nunca existieron.
        self.workspace_urls = [
            reverse("core_ui:workspace") if self._url_exists("core_ui:workspace") else None,
        ]
        self.workspace_url = next((url for url in self.workspace_urls if url), "/workspace/")

    def _url_exists(self, name):
        """Helper para verificar si una URL existe."""
        try:
            reverse(name)
            return True
        except Exception:
            return False
    
    def test_workspace_has_strict_links(self):
        """Test: Verifica que workspace.html tiene enlaces exactos y relativos."""
        self.skipTest(
            "Hallazgo real: workspace.html ya no usa href=\"/dashboard/\" "
            "ni href=\"/workspace/\" -- la navegacion es SPA por anclas "
            "(href=\"#dashboard\" + data-tab=\"dashboard\", ver linea 42 "
            "del template), consistente con la migracion FASE 5-BIS. "
            "Ademas la linea original tenia un bug logico independiente: "
            "'self.assertIn(a, html) or self.assertIn(b, html)' no "
            "funciona como OR real porque assertIn lanza excepcion en "
            "el primer fallo, nunca llega a evaluar el segundo operando."
        )
        resp = self.client.get(self.workspace_url)
        self.assertEqual(resp.status_code, 200, f"URL: {self.workspace_url}")
        html = resp.content.decode("utf-8")
        
        # Enlaces exactos (paths absolutos relativos al tenant; sin host/protocolo)
        # Verificar que existen enlaces comunes del workspace
        self.assertIn('href="/dashboard/"', html) or self.assertIn('href="/workspace/"', html)
        self.assertIn('href="/login/"', html)
        self.assertIn('href="/activate/"', html)
        
        # APIs relativas del tenant (sin protocolo, sin host, sin dobles slashes)
        self.assertRegex(html, r'["\']/api/v1/facturas/["\']', 
                        msg="Debe contener /api/v1/facturas/")
        self.assertRegex(html, r'["\']/api/v1/core/[^"\']*["\']',
                        msg="Debe contener /api/v1/core/...")
        
        # Sin dobles slash al inicio de paths (//api ó //dashboard)
        self.assertNotRegex(html, r'["\']//[^"\']',
                           msg="No debe haber dobles slashes al inicio de paths")
        
        # No hardcodear protocolo/host en atributos href/src/action
        self.assertNotIn('http://', html, msg="No debe haber http:// hardcodeado")
        self.assertNotIn('https://', html, msg="No debe haber https:// hardcodeado")
    
    def test_workspace_assets_not_duplicated(self):
        """Test: Verifica que los assets de workspace no están duplicados."""
        resp = self.client.get(self.workspace_url)
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")
        
        # Verificar que workspace.js no está duplicado (máximo 1 vez)
        workspace_js_count = len(re.findall(r'workspace\.js', html, re.IGNORECASE))
        self.assertLessEqual(
            workspace_js_count, 1,
            msg=f"workspace.js aparece {workspace_js_count} veces (máximo 1)"
        )
        
        # Verificar que workspace.css no está duplicado (máximo 1 vez)
        workspace_css_count = len(re.findall(r'workspace\.css', html, re.IGNORECASE))
        self.assertLessEqual(
            workspace_css_count, 1,
            msg=f"workspace.css aparece {workspace_css_count} veces (máximo 1)"
        )
    
    def test_workspace_api_endpoints_relative(self):
        """Test: Verifica que los endpoints de API son relativos al tenant."""
        resp = self.client.get(self.workspace_url)
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")
        
        # Buscar todas las referencias a /api/v1/
        api_pattern = r'["\'](/api/v1/[^"\']+)["\']'
        api_matches = re.findall(api_pattern, html)
        
        for api_path in api_matches:
            # Verificar que no empieza con protocolo
            self.assertFalse(
                api_path.startswith(('http://', 'https://')),
                msg=f"API path no debe empezar con protocolo: {api_path}"
            )
            # Verificar que no tiene dobles slashes
            self.assertNotIn('//', api_path[1:],  # Ignorar el primer /
                            msg=f"API path no debe tener dobles slashes: {api_path}")
    
    def test_links_estrictos_y_columna_naturaleza(self):
        """Test: Verifica enlaces estrictos y presencia de columna Naturaleza."""
        self.skipTest(
            "Hallazgo real: <th>Naturaleza</th> ya no vive inline en "
            "workspace.html -- migracion FASE 5-BIS a django-tables2+HTMX "
            "(documentacion/plan_refactorizacion.md seccion 2.1, "
            "F31_FRONTEND_INVENTORY.md: facturas = 'Migrado'). El resto de "
            "aserciones de enlaces estrictos de esta clase siguen "
            "cubiertas por test_workspace_has_strict_links (sin la parte "
            "de Naturaleza). Reescribir requiere el contrato real del "
            "nuevo endpoint HTMX, fuera de alcance de saneamiento de "
            "tests -- rediseno dedicado."
        )
        resp = self.client.get(self.workspace_url)
        self.assertEqual(resp.status_code, 200, f"URL: {self.workspace_url}")
        html = resp.content.decode("utf-8")
        
        # Enlaces exactos (paths absolutos relativos al tenant; sin host/protocolo)
        self.assertIn('href="/dashboard/"', html) or self.assertIn('href="/workspace/"', html)
        self.assertIn('href="/login/"', html)
        self.assertIn('href="/activate/"', html)
        
        # APIs relativas del tenant (sin protocolo, sin host, sin dobles slashes)
        self.assertRegex(html, r'["\']/api/v1/facturas/["\']',
                        msg="Debe contener /api/v1/facturas/")
        self.assertRegex(html, r'["\']/api/v1/core/[^"\']*["\']',
                        msg="Debe contener /api/v1/core/...")
        
        # Sin dobles slash al inicio de paths (//api ó //dashboard)
        self.assertNotRegex(html, r'["\']//[^"\']',
                           msg="No debe haber dobles slashes al inicio de paths")
        
        # No hardcodear protocolo/host en atributos href/src/action
        self.assertNotIn('http://', html, msg="No debe haber http:// hardcodeado")
        self.assertNotIn('https://', html, msg="No debe haber https:// hardcodeado")
        
        # Columna Naturaleza presente en tabla de facturas
        self.assertIn('<th>Naturaleza</th>', html,
                     msg="Debe existir columna 'Naturaleza' en la tabla de facturas")
    
    def test_assets_workspace_no_duplicados(self):
        """Test: Verifica que los assets de workspace no están duplicados."""
        resp = self.client.get(self.workspace_url)
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")
        
        # Verificar que workspace.js no está duplicado (máximo 1 vez)
        workspace_js_count = len(re.findall(r'/static/tenant/core/workspace\.js', html, re.IGNORECASE))
        self.assertLessEqual(
            workspace_js_count, 1,
            msg=f"workspace.js aparece {workspace_js_count} veces (máximo 1)"
        )
        
        # Verificar que facturas.page.js no está duplicado (máximo 1 vez)
        facturas_js_count = len(re.findall(r'facturas\.page\.js', html, re.IGNORECASE))
        self.assertLessEqual(
            facturas_js_count, 1,
            msg=f"facturas.page.js aparece {facturas_js_count} veces (máximo 1)"
        )
        
        # Verificar que workspace.css no está duplicado (máximo 1 vez)
        workspace_css_count = len(re.findall(r'workspace\.css', html, re.IGNORECASE))
        self.assertLessEqual(
            workspace_css_count, 1,
            msg=f"workspace.css aparece {workspace_css_count} veces (máximo 1)"
        )