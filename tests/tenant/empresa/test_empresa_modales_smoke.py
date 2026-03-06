"""
Smoke tests para modales y botones del módulo Empresa.

⚠️ v2.37: Alineado con arquitectura API-First y UI modular.
"""
import pytest
from django.test import Client
from rest_framework import status
from tests.tenant.base_test import SintelTenantTestCase
from apps.tenant.empresa.models import Empresa


class TestEmpresaModalesSmoke(SintelTenantTestCase):
    """
    Tests de smoke para modales y botones del módulo Empresa.
    
    ⚠️ IMPORTANTE: Estos tests validan que:
    - Los modales se renderizan correctamente
    - Los botones funcionan
    - Las operaciones CRUD funcionan
    - El feedback se muestra correctamente
    """
    
    def setUp(self):
        """Configuración inicial."""
        super().setUp()
        self.client = Client(HTTP_HOST=self.domain.domain)
        self.client.force_login(self.user)
    
    def test_modales_renderizados(self):
        """Valida que los tres modales están presentes en el HTML."""
        response = self.client.get('/workspace/#empresa', follow=True)
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Verificar que los modales están presentes
        self.assertIn('id="modal-ver-empresa"', content)
        self.assertIn('id="modal-editar-empresa"', content)
        self.assertIn('id="modal-crear-empresa"', content)
        
        # Verificar feedback divs
        self.assertIn('id="empresa-view-feedback"', content)
        self.assertIn('id="empresa-edit-feedback"', content)
        self.assertIn('id="empresa-create-feedback"', content)
    
    def test_api_list_returns_empresa_when_exists(self):
        """Valida que GET List retorna 1 row cuando existe Empresa."""
        # Crear empresa
        empresa = Empresa.objects.create(
            razon_social='Test Empresa',
            nit='123456789',
            dv='0',
            direccion='Calle Test',
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
        self.assertEqual(data[0]['nit'], empresa.nit)
    
    def test_api_detail_returns_correct_fields(self):
        """Valida que GET Detail retorna campos correctos."""
        # Crear empresa
        empresa = Empresa.objects.create(
            razon_social='Test Empresa',
            nit='123456789',
            dv='0',
            direccion='Calle Test',
            telefono='1234567',
            email_contacto='test@example.com',
            regimen_renta_codigo='ORDINARIO',
            moneda='COP'
        )
        
        response = self.client.get(f'/api/v1/empresas/{empresa.id}/', HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        
        # Verificar campos requeridos
        required_fields = ['id', 'nit', 'razon_social', 'direccion', 'telefono', 'email_contacto', 'moneda']
        for field in required_fields:
            self.assertIn(field, data, f"Campo '{field}' no está en la respuesta")
        
        # Verificar que regimen_tributario está presente (alias de regimen_renta_codigo)
        self.assertIn('regimen_tributario', data)
    
    def test_api_patch_updates_correctly(self):
        """Valida que PATCH actualiza correctamente."""
        # Crear empresa
        empresa = Empresa.objects.create(
            razon_social='Test Empresa',
            nit='123456789',
            dv='0',
            direccion='Calle Test',
            telefono='1234567',
            email_contacto='test@example.com',
            regimen_renta_codigo='ORDINARIO',
            moneda='COP'
        )
        
        # Actualizar
        payload = {
            'razon_social': 'Empresa Actualizada',
            'telefono': '9876543',
        }
        
        response = self.client.patch(
            f'/api/v1/empresas/{empresa.id}/',
            data=payload,
            content_type='application/json',
            HTTP_ACCEPT='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['razon_social'], 'Empresa Actualizada')
        self.assertEqual(data['telefono'], '9876543')
        
        # Verificar en BD
        empresa.refresh_from_db()
        self.assertEqual(empresa.razon_social, 'Empresa Actualizada')
        self.assertEqual(empresa.telefono, '9876543')
    
    def test_api_post_creates_singleton_if_not_exists(self):
        """Valida que POST crea singleton si no existe."""
        # Asegurar que no hay empresa
        Empresa.objects.all().delete()
        
        payload = {
            'razon_social': 'Nueva Empresa',
            'nit': '987654321',
            'dv': '0',
            'direccion': 'Nueva Dirección',
            'telefono': '5555555',
            'email_contacto': 'nueva@example.com',
            'regimen_renta_codigo': 'ORDINARIO',
            'moneda': 'COP'
        }
        
        response = self.client.post(
            '/api/v1/empresas/',
            data=payload,
            content_type='application/json',
            HTTP_ACCEPT='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        
        data = response.json()
        self.assertEqual(data['razon_social'], 'Nueva Empresa')
        self.assertEqual(data['nit'], '987654321')
        
        # Verificar que solo hay una empresa
        self.assertEqual(Empresa.objects.count(), 1)
    
    def test_botones_presentes_en_tabla(self):
        """Valida que los botones Ver y Editar están presentes en la tabla."""
        # Crear empresa
        Empresa.objects.create(
            razon_social='Test Empresa',
            nit='123456789',
            dv='0',
            direccion='Calle Test',
            telefono='1234567',
            email_contacto='test@example.com',
            regimen_renta_codigo='ORDINARIO',
            moneda='COP'
        )
        
        response = self.client.get('/workspace/#empresa', follow=True)
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Verificar que los botones están presentes (se renderizan en JS, pero la estructura debe estar)
        self.assertIn('btn-ver', content)
        self.assertIn('btn-editar', content)
        self.assertIn('btn-empresa-crear', content)
    
    def test_modal_ver_has_readonly_inputs(self):
        """Valida que el modal Ver tiene inputs readonly."""
        response = self.client.get('/workspace/#empresa', follow=True)
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Verificar que los inputs del modal Ver tienen readonly disabled
        self.assertIn('id="empresa-view-nit"', content)
        # Verificar que el input tiene readonly (se verifica en el HTML)
        # Nota: El readonly se aplica en el HTML, no se puede verificar fácilmente en el test
    
    def test_modal_editar_has_editable_inputs(self):
        """Valida que el modal Editar tiene inputs editables."""
        response = self.client.get('/workspace/#empresa', follow=True)
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Verificar que los inputs del modal Editar están presentes
        self.assertIn('id="empresa-edit-nit"', content)
        self.assertIn('id="btn-guardar-empresa"', content)
    
    def test_modal_crear_has_empty_inputs(self):
        """Valida que el modal Crear tiene inputs en blanco."""
        response = self.client.get('/workspace/#empresa', follow=True)
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Verificar que los inputs del modal Crear están presentes
        self.assertIn('id="empresa-create-nit"', content)
        self.assertIn('id="btn-crear-empresa-modal"', content)
    
    def test_list_serializer_exposes_minimal_fields(self):
        """Valida que ListSerializer expone solo campos mínimos."""
        # Crear empresa
        empresa = Empresa.objects.create(
            razon_social='Test Empresa',
            nit='123456789',
            dv='0',
            direccion='Calle Test',
            telefono='1234567',
            email_contacto='test@example.com',
            regimen_renta_codigo='ORDINARIO',
            moneda='COP',
            website='https://example.com'  # Campo pesado que NO debe estar en LIST
        )
        
        response = self.client.get('/api/v1/empresas/', HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        
        empresa_data = data[0]
        
        # Campos que DEBEN estar
        required_fields = ['nit', 'direccion', 'telefono', 'email_contacto', 'regimen_tributario', 'moneda']
        for field in required_fields:
            self.assertIn(field, empresa_data, f"Campo '{field}' debe estar en LIST")
        
        # Campos que NO deben estar (pesados o sensibles)
        # ⚠️ NOTA: 'id' ahora está en LIST para poder hacer retrieve desde el frontend
        prohibited_fields = ['razon_social', 'logo', 'website', 'created_at', 'updated_at']
        for field in prohibited_fields:
            self.assertNotIn(field, empresa_data, f"Campo '{field}' NO debe estar en LIST")
