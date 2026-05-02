"""
Pruebas de humo para el shell estático del dashboard (API-First).

[WARNING] POLÍTICA:
- Verifica que el shell use módulos ES
- Verifica que consuma exclusivamente Core API
- Verifica ausencia de URLs absolutas y llamadas directas a apps
"""
import os
from pathlib import Path
from django.test import TestCase
from django.conf import settings

PROJECT_ROOT = Path(settings.BASE_DIR)


class TestDashboardShellAPIFirst(TestCase):
    """
    Pruebas de cumplimiento API-First para el dashboard shell.
    """
    
    def test_shell_exists(self):
        """Verifica que el shell estático existe."""
        shell_path = PROJECT_ROOT / 'apps' / 'tenant' / 'dashboard' / 'static' / 'tenant' / 'dashboard' / 'index.html'
        self.assertTrue(shell_path.exists(), "Dashboard shell debe existir")
    
    def test_shell_uses_module_script(self):
        """Verifica que el shell use <script type='module'>."""
        shell_path = PROJECT_ROOT / 'apps' / 'tenant' / 'dashboard' / 'static' / 'tenant' / 'dashboard' / 'index.html'
        content = shell_path.read_text(encoding='utf-8')
        
        # Debe tener type="module"
        self.assertIn('type="module"', content, "Dashboard shell debe usar módulos ES")
        
        # Debe importar el módulo dashboard.js
        self.assertIn('/static/tenant/dashboard/js/dashboard.js', content,
                     "Dashboard shell debe importar dashboard.js como módulo")
    
    def test_shell_consumes_core_api(self):
        """Verifica que el shell consuma Core API."""
        shell_path = PROJECT_ROOT / 'apps' / 'tenant' / 'dashboard' / 'static' / 'tenant' / 'dashboard' / 'index.html'
        content = shell_path.read_text(encoding='utf-8')
        
        # Debe consumir Core API
        self.assertIn('/api/v1/core/dashboard/sections/', content,
                     "Dashboard shell debe consumir /api/v1/core/dashboard/sections/")
    
    def test_shell_no_absolute_urls(self):
        """Verifica que no haya URLs absolutas (excepto CDN)."""
        shell_path = PROJECT_ROOT / 'apps' / 'tenant' / 'dashboard' / 'static' / 'tenant' / 'dashboard' / 'index.html'
        content = shell_path.read_text(encoding='utf-8')
        
        # Buscar URLs absolutas (permitir CDN)
        import re
        absolute_urls = re.findall(r'https?://[^\s"\'<>]+', content)
        
        for url in absolute_urls:
            # Permitir CDN (tailwindcss, font-awesome, w3.org)
            if 'cdn' in url.lower() or 'cdnjs' in url.lower() or 'w3.org' in url:
                continue
            self.fail(f"URL absoluta encontrada (no CDN): {url}")
    
    def test_shell_no_direct_app_endpoints(self):
        """Verifica que no haya llamadas directas a endpoints de apps (para agregación)."""
        shell_path = PROJECT_ROOT / 'apps' / 'tenant' / 'dashboard' / 'static' / 'tenant' / 'dashboard' / 'index.html'
        content = shell_path.read_text(encoding='utf-8')
        
        # No debe tener fetch directo a /api/v1/empresas/, /api/v1/facturas/, etc.
        # (para agregación; CRUD específico de app está permitido)
        prohibited_patterns = [
            r"fetch\(['\"]/api/v1/empresas/",
            r"fetch\(['\"]/api/v1/facturas/",
            r"fetch\(['\"]/api/v1/contabilidad/",
            r"fetch\(['\"]/api/v1/perfil/",
        ]
        
        for pattern in prohibited_patterns:
            import re
            matches = re.findall(pattern, content)
            if matches:
                self.fail(f"Llamada directa a endpoint no Core encontrada: {matches[0]}")
    
    def test_shell_no_inline_scripts(self):
        """Verifica que no haya scripts inline grandes (deben ser módulos ES)."""
        shell_path = PROJECT_ROOT / 'apps' / 'tenant' / 'dashboard' / 'static' / 'tenant' / 'dashboard' / 'index.html'
        content = shell_path.read_text(encoding='utf-8')
        
        # Buscar scripts inline (no módulos)
        import re
        inline_scripts = re.findall(r'<script[^>]*>(?!.*type=["\']module["\']).*?</script>', content, re.DOTALL)
        
        for script in inline_scripts:
            # Permitir scripts pequeños (configuración, etc.)
            if len(script) > 200:
                self.fail(f"Script inline grande encontrado (debe ser módulo ES): {script[:100]}...")
