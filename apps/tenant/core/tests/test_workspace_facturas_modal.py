"""
Tests de humo para Fase 4: Modal de detalle de factura con anexos.

⚠️ VALIDACIONES:
- Modal presente en HTML
- Rutas relativas (sin host/protocolo)
- Sin duplicación de assets
"""
import re
from django_tenants.test.cases import TenantTestCase
from django.urls import reverse


class WorkspaceFacturasModalTests(TenantTestCase):
    """Tests para validar modal de detalle de factura."""
    
    def setUp(self):
        super().setUp()
        # Intentar obtener la URL del workspace (ajustar según tu configuración)
        # Usar el mismo método que test_workspace_links_strict.py
        self.workspace_urls = [
            reverse("workspace") if self._url_exists("workspace") else None,
            reverse("tenant-workspace") if self._url_exists("tenant-workspace") else None,
            reverse("dashboard") if self._url_exists("dashboard") else None,
        ]
        self.url = next((url for url in self.workspace_urls if url), "/workspace/")
    
    def _url_exists(self, name):
        """Verifica si una URL name existe."""
        try:
            reverse(name)
            return True
        except:
            return False
    
    def test_modal_present_and_assets(self):
        """Test: Modal presente y assets sin duplicación."""
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        html = r.content.decode("utf-8")
        
        # Modal contenedor
        self.assertIn('id="factura-xml-modal"', html, "Modal de factura no encontrado")
        
        # Elementos del modal
        self.assertIn('id="fxm-numero"', html)
        self.assertIn('id="fxm-ubl"', html)
        self.assertIn('id="fxm-app"', html)
        self.assertIn('id="fxm-ubl-copy"', html)
        self.assertIn('id="fxm-app-copy"', html)
        self.assertIn('id="fxm-ubl-download"', html)
        self.assertIn('id="fxm-app-download"', html)
        
        # Pestañas
        self.assertIn('data-bs-target="#tab-ubl"', html)
        self.assertIn('data-bs-target="#tab-app"', html)
    
    def test_rutas_relativas_sin_hosts(self):
        """Test: Rutas estrictas (sin host/protocolo)."""
        r = self.client.get(self.url)
        html = r.content.decode("utf-8")
        
        # Buscar URLs absolutas con protocolo
        absolute_urls = re.findall(r'["\']https?://[^"\']+["\']', html, re.IGNORECASE)
        
        # Filtrar URLs permitidas (comentarios, ejemplos, etc.)
        forbidden = [u for u in absolute_urls if not any(
            skip in u.lower() for skip in ['example.com', 'localhost', '127.0.0.1', 'comment', 'todo']
        )]
        
        self.assertEqual(
            len(forbidden), 0,
            f"Se encontraron URLs absolutas con protocolo/host: {forbidden}"
        )
    
    def test_assets_sin_duplicacion(self):
        """Test: Assets del módulo sin duplicación."""
        r = self.client.get(self.url)
        html = r.content.decode("utf-8")
        
        # Contar ocurrencias de facturas.page.js en tags <script>
        script_matches = re.findall(
            r'<script[^>]*src\s*=\s*["\'][^"\']*facturas\.page\.js[^"\']*["\']',
            html,
            re.IGNORECASE
        )
        
        # También buscar el patrón de Django template tag
        django_static_matches = re.findall(
            r'{%\s*static\s+[\'"]tenant/landing/workspace/facturas\.page\.js[\'"]\s*%}',
            html,
            re.IGNORECASE
        )
        
        total_matches = len(script_matches) + len(django_static_matches)
        
        self.assertGreaterEqual(
            total_matches, 1,
            "facturas.page.js debe aparecer al menos 1 vez"
        )
        
        self.assertLessEqual(
            total_matches, 1,
            f"facturas.page.js aparece {total_matches} veces (debe aparecer máximo 1 vez)"
        )
