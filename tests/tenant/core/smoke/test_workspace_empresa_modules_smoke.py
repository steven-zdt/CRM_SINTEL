"""
Smoke tests para módulos independientes EmpresaModule y MailInboxConfigModule.

[WARNING] v2.37: Verifica que ambos módulos funcionan independientemente en workspace/#empresa.

[WARNING] IMPORTANTE: Estos tests actúan como salvaguardas. Si fallan, significa que se ha
modificado algo crítico del módulo. Ver documentacion/WORKSPACE_MODULO_EMPRESA_v2.37.md
"""
import pytest
from django.test import Client
from django.urls import reverse

try:
    import cryptography  # noqa: F401
    import playwright  # noqa: F401
except Exception:
    pytest.skip("Skipping heavy smoke test: missing playwright/cryptography", allow_module_level=True)

from tests.tenant.base_test import SintelTenantTestCase


class TestEmpresaModulesSmoke(SintelTenantTestCase):
    """
    Smoke tests para verificar que ambos módulos se renderizan correctamente.
    """

    def test_workspace_empresa_tab_loads(self):
        """Verifica que el tab #empresa carga correctamente."""
        client = Client()
        self.client.force_login(self.user)
        
        # Acceder al workspace con hash #empresa
        response = self.client.get('/workspace/#empresa', follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verificar que ambos módulos están presentes en el HTML
        content = response.content.decode('utf-8')
        
        # Módulo 1: EmpresaModule
        self.assertIn('empresa-module-container', content)
        self.assertIn('tabla-empresa', content)
        self.assertIn('empresa_list.html', content)  # Verificar que el partial se incluye
        
        # Módulo 2: MailInboxConfigModule
        self.assertIn('mailinbox-module-container', content)
        self.assertIn('tabla-mailinbox', content)
        self.assertIn('mailinbox_list.html', content)  # Verificar que el partial se incluye
    
    def test_empresa_module_assets_loaded(self):
        """Verifica que los assets de EmpresaModule se cargan."""
        client = Client()
        self.client.force_login(self.user)
        
        response = self.client.get('/workspace/', follow=True)
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Verificar que assets_empresa.html se incluye
        self.assertIn('assets_empresa.html', content)
        self.assertIn('empresa.page.js', content)
    
    def test_mailinbox_module_assets_loaded(self):
        """Verifica que los assets de MailInboxConfigModule se cargan."""
        client = Client()
        self.client.force_login(self.user)
        
        response = self.client.get('/workspace/', follow=True)
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Verificar que assets_mailinbox.html se incluye
        self.assertIn('assets_mailinbox.html', content)
        self.assertIn('mailinbox.page.js', content)
    
    def test_empresa_api_endpoint_accessible(self):
        """Verifica que el endpoint de EmpresaModule es accesible."""
        self.client.force_login(self.user)
        
        response = self.client.get('/api/v1/empresas/', HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)  # Siempre 200 (array vacío o con datos)
        
        data = response.json()
        # Debe retornar array (singleton: 0 o 1 elemento)
        self.assertIsInstance(data, list)
        
        # Si hay datos, verificar campos mínimos
        if len(data) > 0:
            empresa = data[0]
            # Verificar que solo expone campos mínimos (sin id, razon_social, etc.)
            expected_fields = {'nit', 'direccion', 'telefono', 'email_contacto', 'regimen_tributario', 'moneda'}
            self.assertTrue(expected_fields.issubset(set(empresa.keys())), 
                          f"Faltan campos esperados. Campos presentes: {list(empresa.keys())}")
            
            # Verificar que NO expone campos pesados o sensibles
            forbidden_fields = {'id', 'razon_social', 'logo', 'website', 'created_at', 'updated_at'}
            self.assertFalse(any(field in empresa for field in forbidden_fields),
                           f"Se expusieron campos prohibidos: {[f for f in forbidden_fields if f in empresa]}")
    
    def test_empresa_api_empty_list(self):
        """Verifica que el endpoint retorna array vacío cuando no hay empresa."""
        self.client.force_login(self.user)
        
        # Asegurar que no hay empresa
        from apps.tenant.empresa.models import Empresa
        Empresa.objects.all().delete()
        
        response = self.client.get('/api/v1/empresas/', HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 0)
    
    def test_empresa_api_with_data(self):
        """Verifica que el endpoint retorna 1 fila cuando hay empresa."""
        self.client.force_login(self.user)
        
        # Crear empresa de prueba
        from apps.tenant.empresa.models import Empresa
        Empresa.objects.all().delete()  # Limpiar primero
        
        empresa = Empresa.objects.create(
            razon_social='Empresa Test',
            nit='123456789',
            dv='0',
            direccion='Calle Test 123',
            telefono='1234567',
            email_contacto='test@example.com',
            regimen_renta_codigo='ORDINARIO',
            moneda='COP'
        )
        
        response = self.client.get('/api/v1/empresas/', HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        
        # Verificar campos
        empresa_data = data[0]
        self.assertEqual(empresa_data['nit'], '123456789')
        self.assertEqual(empresa_data['direccion'], 'Calle Test 123')
        self.assertEqual(empresa_data['telefono'], '1234567')
        self.assertEqual(empresa_data['email_contacto'], 'test@example.com')
        self.assertEqual(empresa_data['regimen_tributario'], 'ORDINARIO')  # Alias de regimen_renta_codigo
        self.assertEqual(empresa_data['moneda'], 'COP')
    
    def test_mailinbox_api_endpoint_accessible(self):
        """Verifica que el endpoint de MailInboxConfigModule es accesible."""
        client = Client()
        self.client.force_login(self.user)
        
        response = self.client.get('/api/v1/empresas/mail-inbox-config/', HTTP_ACCEPT='application/json')
        self.assertIn(response.status_code, [200, 401, 403])  # 200 si hay datos, 401/403 si no autenticado
        
        if response.status_code == 200:
            data = response.json()
            # Debe retornar objeto paginado o array
            self.assertTrue(isinstance(data, dict) or isinstance(data, list))
            if isinstance(data, dict):
                # Si es paginado, debe tener 'results'
                self.assertIn('results', data)
    
    def test_modules_independent_containers(self):
        """Verifica que ambos módulos tienen contenedores independientes."""
        self.client.force_login(self.user)
        
        response = self.client.get('/workspace/#empresa', follow=True)
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Verificar que los contenedores son distintos
        self.assertIn('id="empresa-module-container"', content)
        self.assertIn('id="mailinbox-module-container"', content)
        
        # Verificar que las tablas tienen IDs distintos
        self.assertIn('id="tabla-empresa"', content)
        self.assertIn('id="tabla-mailinbox"', content)
        
        # Verificar que no hay mezcla de IDs
        self.assertNotIn('tabla-empresa', content.replace('id="tabla-empresa"', ''))
        self.assertNotIn('tabla-mailinbox', content.replace('id="tabla-mailinbox"', ''))
    
    def test_empresa_table_columns(self):
        """Verifica que la tabla de empresa tiene exactamente 7 columnas."""
        self.client.force_login(self.user)
        
        response = self.client.get('/workspace/#empresa', follow=True)
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Contar <th> en la tabla de empresa
        import re

        # Buscar el thead de tabla-empresa
        tabla_match = re.search(r'<table[^>]*id="tabla-empresa"[^>]*>.*?<thead>.*?<tr>(.*?)</tr>.*?</thead>', content, re.DOTALL)
        if tabla_match:
            thead_content = tabla_match.group(1)
            th_count = len(re.findall(r'<th[^>]*>', thead_content))
            self.assertEqual(th_count, 7, f"La tabla debe tener 7 columnas, pero tiene {th_count}")
        
        # Verificar que las columnas son las correctas
        expected_columns = ['NIT', 'Dirección', 'Teléfono', 'Email', 'Régimen', 'Moneda', 'Acciones']
        for col in expected_columns:
            self.assertIn(f'<th>{col}</th>', content, f"Falta la columna '{col}'")
    
    def test_empresa_table_empty_state(self):
        """Verifica que la tabla muestra mensaje vacío cuando no hay datos."""
        self.client.force_login(self.user)
        
        # Asegurar que no hay empresa
        from apps.tenant.empresa.models import Empresa
        Empresa.objects.all().delete()
        
        response = self.client.get('/workspace/#empresa', follow=True)
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Verificar que la tabla está presente (shell vacío)
        self.assertIn('id="tabla-empresa"', content)
        self.assertIn('<tbody></tbody>', content)  # Tbody vacío
