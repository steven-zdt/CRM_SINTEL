"""
Pruebas de humo para verificar que el shell estático de empresas 
consume la API correctamente.

⚠️ POLÍTICA API-First: La presentación está en shells estáticos que consumen la API.
"""
from django.test import TestCase
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from pathlib import Path
import os


class TestEmpresasShellConsumesAPI(TestCase):
    """
    Pruebas para verificar que el shell estático de empresas consume la API.
    """

    def test_empresas_shell_exists(self):
        """
        Verifica que el shell estático existe en la ubicación correcta.
        """
        shell_path = Path(__file__).resolve().parent.parent.parent.parent / 'apps' / 'tenant' / 'empresa' / 'static' / 'tenant' / 'empresa' / 'index.html'
        
        self.assertTrue(
            shell_path.exists(),
            f"El shell estático no existe en: {shell_path}"
        )

    def test_empresas_shell_uses_es_modules(self):
        """
        Verifica que el shell estático usa módulos ES (type="module").
        """
        shell_path = Path(__file__).resolve().parent.parent.parent.parent / 'apps' / 'tenant' / 'empresa' / 'static' / 'tenant' / 'empresa' / 'index.html'
        
        if not shell_path.exists():
            self.skipTest("Shell estático no existe")
        
        content = shell_path.read_text(encoding='utf-8')
        
        # Verificar que usa módulos ES
        self.assertIn(
            'type="module"',
            content,
            "El shell estático debe usar módulos ES (type='module')"
        )

    def test_empresas_shell_consumes_api(self):
        """
        Verifica que el shell estático consume la API /api/v1/empresas/.
        """
        shell_path = Path(__file__).resolve().parent.parent.parent.parent / 'apps' / 'tenant' / 'empresa' / 'static' / 'tenant' / 'empresa' / 'index.html'
        
        if not shell_path.exists():
            self.skipTest("Shell estático no existe")
        
        content = shell_path.read_text(encoding='utf-8')
        
        # Verificar que consume la API (puede ser fetch, getJSON, o similar)
        api_patterns = [
            "/api/v1/empresas/",
            "fetch('/api/v1/empresas/",
            "getJSON('/api/v1/empresas/",
        ]
        
        found = False
        for pattern in api_patterns:
            if pattern in content:
                found = True
                break
        
        self.assertTrue(
            found,
            "El shell estático debe consumir la API /api/v1/empresas/"
        )

    def test_empresas_shell_no_absolute_urls(self):
        """
        Verifica que el shell estático NO contiene URLs absolutas (http://, https://).
        """
        shell_path = Path(__file__).resolve().parent.parent.parent.parent / 'apps' / 'tenant' / 'empresa' / 'static' / 'tenant' / 'empresa' / 'index.html'
        
        if not shell_path.exists():
            self.skipTest("Shell estático no existe")
        
        content = shell_path.read_text(encoding='utf-8')
        
        # Verificar que NO contiene URLs absolutas (excepto CDNs externos como tailwindcss)
        # Permitir CDNs conocidos
        allowed_absolute = ['https://cdn.tailwindcss.com', 'https://cdnjs.cloudflare.com']
        
        # Buscar URLs absolutas que NO sean CDNs permitidos
        import re
        absolute_url_pattern = re.compile(r'(http://|https://)(?!cdn\.tailwindcss\.com|cdnjs\.cloudflare\.com)[^\s"\'<>]+')
        matches = absolute_url_pattern.findall(content)
        
        # Filtrar matches que sean CDNs permitidos
        forbidden_matches = [m for m in matches if not any(cdn in str(m) for cdn in allowed_absolute)]
        
        self.assertEqual(
            len(forbidden_matches),
            0,
            f"El shell estático contiene URLs absolutas prohibidas: {forbidden_matches}. "
            "Debe usar URLs relativas para respetar el ruteo multi-tenant por hostname."
        )
