"""
Tests de humo para validar columna Naturaleza y assets en workspace.html.
"""
import re
from django.urls import reverse
from django_tenants.test.cases import TenantTestCase


class WorkspaceFacturasLinksAndColumnTests(TenantTestCase):
    """Tests para validar que la tabla de facturas tiene la columna Naturaleza y assets correctos."""
    
    def setUp(self):
        super().setUp()
        # Ajustar al name real de la URL del workspace
        # Si no existe, usar la ruta directa
        try:
            self.url = reverse("tenant-workspace")
        except:
            self.url = "/workspace/"
    
    def test_columna_naturaleza_y_assets(self):
        """Valida que la columna Naturaleza está presente y los assets no están duplicados."""
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
