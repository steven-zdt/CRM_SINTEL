"""
Tests de humo para Fase 3: Workspace Facturas UI (Upload asíncrono + Polling + Materialización).

# WARNING: VALIDACIONES ESTRICTAS:
- Rutas relativas (nunca http(s)://host)
- Sin duplicación de assets
- Columna Naturaleza presente
- Orden correcto de scripts
"""
import re
from pathlib import Path

from django.test import SimpleTestCase

TEMPLATE_PATH = Path("apps/tenant/core/templates/tenant/core/workspace.html")
FACTURAS_JS_PATH = Path("apps/tenant/landing/static/tenant/landing/workspace/facturas.page.js")


_OBSOLETE_REASON = (
    "Hallazgo real: facturas.page.js (apps/tenant/landing/static/tenant/"
    "landing/workspace/facturas.page.js) ya no existe en el repo -- la "
    "logica de renderizado de filas/badge de naturaleza que probaba este "
    "archivo (rowHTML, naturalezaBadge) se movio al servidor durante la "
    "migracion FASE 5-BIS (Tabulator -> django-tables2+HTMX, "
    "documentacion/plan_refactorizacion.md seccion 2.1; "
    "F33_14E_BADGES_ESTADO_INVENTORY.md confirma que el renderizado de "
    "badges vive hoy en django-tables2). El template workspace.html "
    "tampoco referencia facturas.page.js ni <th>Naturaleza</th> inline. "
    "Reescribir estos tests requiere el contrato real del nuevo "
    "endpoint HTMX de facturas, fuera de alcance de saneamiento de "
    "tests -- queda documentado para rediseno dedicado."
)


class WorkspaceFacturasUIPhase3Tests(SimpleTestCase):
    """Tests de humo para validar estructura HTML/JS de Fase 3 (OBSOLETO, ver _OBSOLETE_REASON)."""

    maxDiff = None

    def test_template_exists(self):
        """Verificar que el template existe."""
        self.assertTrue(TEMPLATE_PATH.exists(), f"Template no encontrado: {TEMPLATE_PATH}")

    def test_facturas_js_exists(self):
        """Verificar que el JS de facturas existe."""
        self.skipTest(_OBSOLETE_REASON)
        self.assertTrue(FACTURAS_JS_PATH.exists(), f"JS no encontrado: {FACTURAS_JS_PATH}")
    
    def test_tabla_tiene_columna_naturaleza(self):
        """Verificar que la tabla tiene columna Naturaleza."""
        self.skipTest(_OBSOLETE_REASON)
        content = TEMPLATE_PATH.read_text(encoding="utf-8", errors="ignore")
        
        # Buscar la tabla de facturas
        self.assertIn('id="tbl-facturas"', content, "Tabla de facturas no encontrada")
        
        # Verificar columna Naturaleza en thead
        self.assertIn('<th>Naturaleza</th>', content, "Columna Naturaleza no encontrada en thead")
        
        # Verificar tbody con id
        self.assertIn('id="facturas-tbody"', content, "tbody de facturas sin id")
    
    def test_rutas_relativas_sin_hosts(self):
        """Verificar que no hay rutas absolutas con protocolo/host."""
        self.skipTest(_OBSOLETE_REASON)
        content = TEMPLATE_PATH.read_text(encoding="utf-8", errors="ignore")
        
        # Buscar patrones de URLs absolutas (http:// o https://)
        absolute_urls = re.findall(r'https?://[^\s"\'<>]+', content, re.IGNORECASE)
        
        # Filtrar URLs permitidas (comentarios, ejemplos, etc.)
        forbidden = [u for u in absolute_urls if not any(
            skip in u.lower() for skip in ['example.com', 'localhost', '127.0.0.1', 'comment', 'todo']
        )]
        
        self.assertEqual(
            len(forbidden), 0,
            f"Se encontraron URLs absolutas con protocolo/host: {forbidden}"
        )
    
    def test_scripts_sin_duplicacion(self):
        """Verificar que facturas.page.js no está duplicado en tags <script>."""
        self.skipTest(_OBSOLETE_REASON)
        content = TEMPLATE_PATH.read_text(encoding="utf-8", errors="ignore")
        
        # Buscar solo en tags <script> con src que contenga facturas.page.js
        # El template usa {% static %} que se renderiza en tiempo de ejecución
        # Buscar el patrón de Django template tag o el nombre del archivo
        script_matches = re.findall(
            r'<script[^>]*src\s*=\s*["\'][^"\']*facturas\.page\.js[^"\']*["\']', 
            content, 
            re.IGNORECASE
        )
        
        # También buscar el patrón de Django template tag
        django_static_matches = re.findall(
            r'{%\s*static\s+[\'"]tenant/landing/workspace/facturas\.page\.js[\'"]\s*%}',
            content,
            re.IGNORECASE
        )
        
        total_matches = len(script_matches) + len(django_static_matches)
        
        self.assertGreaterEqual(
            total_matches, 1,
            "facturas.page.js debe aparecer al menos 1 vez en tags <script> o {% static %}"
        )
        
        self.assertLessEqual(
            total_matches, 1,
            f"facturas.page.js aparece {total_matches} veces (debe aparecer máximo 1 vez)"
        )
    
    def test_js_tiene_helpers_fase3(self):
        """Verificar que el JS tiene helpers de Fase 3."""
        self.skipTest(_OBSOLETE_REASON)
        content = FACTURAS_JS_PATH.read_text(encoding="utf-8", errors="ignore")
        
        # Verificar funciones clave de Fase 3
        self.assertIn('subirUblAsync', content, "Función subirUblAsync no encontrada")
        self.assertIn('pollYMaterializa', content, "Función pollYMaterializa no encontrada")
        self.assertIn('disableWhileRunning', content, "Función disableWhileRunning no encontrada")
        self.assertIn('eliminarFactura', content, "Función eliminarFactura no encontrada")
    
    def test_js_rutas_relativas(self):
        """Verificar que el JS usa rutas relativas."""
        self.skipTest(_OBSOLETE_REASON)
        content = FACTURAS_JS_PATH.read_text(encoding="utf-8", errors="ignore")
        
        # Buscar URLs absolutas con protocolo
        absolute_urls = re.findall(r'["\']https?://[^"\']+["\']', content, re.IGNORECASE)
        
        # Filtrar URLs permitidas
        forbidden = [u for u in absolute_urls if not any(
            skip in u.lower() for skip in ['example.com', 'localhost', '127.0.0.1', 'comment', 'todo']
        )]
        
        self.assertEqual(
            len(forbidden), 0,
            f"Se encontraron URLs absolutas en JS: {forbidden}"
        )
    
    def test_js_usa_credentials_same_origin(self):
        """Verificar que las peticiones fetch usan credentials: 'same-origin'."""
        self.skipTest(_OBSOLETE_REASON)
        content = FACTURAS_JS_PATH.read_text(encoding="utf-8", errors="ignore")
        
        # Buscar fetch calls
        fetch_calls = re.findall(r'fetch\([^)]+\)', content, re.DOTALL)
        
        # Verificar que al menos una tiene credentials
        has_credentials = any("credentials" in call for call in fetch_calls)
        
        # Verificar que las llamadas a facturas tienen credentials
        facturas_fetches = [
            call for call in fetch_calls 
            if '/api/v1/facturas' in call
        ]
        
        if facturas_fetches:
            # Al menos una debe tener credentials
            has_credentials = any("credentials" in call for call in facturas_fetches)
            self.assertTrue(
                has_credentials,
                f"Las llamadas fetch a APIs de facturas deben incluir credentials: 'same-origin'. Encontradas: {len(facturas_fetches)} llamadas"
            )
    
    def test_js_usa_csrf_token(self):
        """Verificar que las peticiones mutantes usan CSRF token."""
        self.skipTest(_OBSOLETE_REASON)
        content = FACTURAS_JS_PATH.read_text(encoding="utf-8", errors="ignore")
        
        # Buscar llamadas POST/DELETE
        post_delete = re.findall(r"method:\s*['\"](POST|DELETE)['\"]", content, re.IGNORECASE)
        
        if post_delete:
            # Debe haber referencias a CSRF
            self.assertIn('X-CSRFToken', content, "Las peticiones mutantes deben incluir X-CSRFToken")
            self.assertIn('getCsrf', content, "Debe existir función getCsrf()")
    
    def test_naturaleza_badge_funciona(self):
        """Verificar que naturalezaBadge está implementado correctamente."""
        self.skipTest(_OBSOLETE_REASON)
        content = FACTURAS_JS_PATH.read_text(encoding="utf-8", errors="ignore")
        
        # Verificar función naturalezaBadge
        self.assertIn('naturalezaBadge', content, "Función naturalezaBadge no encontrada")
        
        # Verificar que usa row.naturaleza (no calcula en UI)
        self.assertIn('row.naturaleza', content, "Debe usar row.naturaleza del backend")
    
    def test_rowhtml_usa_naturaleza_backend(self):
        """Verificar que rowHTML consume row.naturaleza del backend."""
        self.skipTest(_OBSOLETE_REASON)
        content = FACTURAS_JS_PATH.read_text(encoding="utf-8", errors="ignore")
        
        # Buscar función rowHTML (puede tener múltiples líneas, buscar hasta el cierre de función)
        # Buscar desde "function rowHTML" hasta encontrar el cierre correspondiente
        start_idx = content.find('function rowHTML')
        self.assertNotEqual(start_idx, -1, "Función rowHTML no encontrada")
        
        # Buscar el cierre de la función (buscar el } que cierra la función)
        brace_count = 0
        in_function = False
        end_idx = start_idx
        
        for i in range(start_idx, len(content)):
            if content[i] == '{':
                brace_count += 1
                in_function = True
            elif content[i] == '}':
                brace_count -= 1
                if in_function and brace_count == 0:
                    end_idx = i + 1
                    break
        
        rowhtml_body = content[start_idx:end_idx]
        
        # Verificar que usa naturalezaBadge con row.naturaleza
        has_naturaleza_badge = 'naturalezaBadge' in rowhtml_body and 'row.naturaleza' in rowhtml_body
        self.assertTrue(has_naturaleza_badge, 
                     f"rowHTML debe usar naturalezaBadge con row.naturaleza del backend. Cuerpo: {rowhtml_body[:200]}")
        
        # Verificar que NO calcula naturaleza en UI (no debe comparar NITs para determinar naturaleza)
        # Nota: Puede mostrar emisor_nit/receptor_nit en el HTML, pero no debe compararlos
        self.assertNotIn('if', rowhtml_body.lower()[:500], 
                        "rowHTML no debe tener lógica condicional para calcular naturaleza")
        self.assertNotIn('empresa_nit', rowhtml_body.lower(),
                        "rowHTML no debe calcular naturaleza usando empresa_nit en UI")
        # Verificar que no compara NITs para determinar naturaleza
        self.assertNotIn('==', rowhtml_body[:500], 
                        "rowHTML no debe comparar NITs para determinar naturaleza")
