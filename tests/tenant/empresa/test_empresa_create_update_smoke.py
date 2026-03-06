"""
Tests de smoke para crear y actualizar Empresa (API-First).

Verifica que:
- GET /api/v1/empresas/mi-empresa/ retorna {} cuando no existe
- POST /api/v1/empresas/ crea empresa con payload mínimo
- PATCH /api/v1/empresas/{id}/ actualiza empresa (incl. segmento_dian)
"""
import pytest
from rest_framework import status
from apps.tenant.api.tests.base import SintelTenantTestCase
from apps.tenant.empresa.models import Empresa


@pytest.mark.django_db(transaction=True)
class EmpresaCreateUpdateSmokeTest(SintelTenantTestCase):
    """
    Tests de smoke para crear y actualizar Empresa.
    """
    
    def setUp(self):
        super().setUp()
        self.api_base = '/api/v1/empresas/'
        self.mi_empresa_url = f'{self.api_base}mi-empresa/'
    
    def test_mi_empresa_returns_empty_when_not_exists(self):
        """
        Verifica que GET /api/v1/empresas/mi-empresa/ retorna {} cuando no existe empresa.
        """
        # Asegurar que no hay empresa
        Empresa.objects.all().delete()
        
        response = self.client.get(self.mi_empresa_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # Debe retornar {} (objeto vacío) para indicar Create mode
        self.assertEqual(data, {})
    
    def test_create_empresa_with_minimal_payload(self):
        """
        Verifica que POST /api/v1/empresas/ crea empresa con payload mínimo.
        """
        # Asegurar que no hay empresa
        Empresa.objects.all().delete()
        
        payload = {
            'razon_social': 'Empresa Test S.A.S.',
            'nit': '900123456',
            'direccion': 'Calle 123 #45-67',
            'telefono': '3001234567',
        }
        
        response = self.client.post(self.api_base, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertIn('id', data)
        self.assertEqual(data['razon_social'], payload['razon_social'])
        self.assertEqual(data['nit'], payload['nit'])
        
        # Verificar que se creó en la BD
        empresa = Empresa.objects.first()
        self.assertIsNotNone(empresa)
        self.assertEqual(empresa.razon_social, payload['razon_social'])
    
    def test_create_then_update_empresa(self):
        """
        Verifica flujo completo: crear empresa, luego actualizar con segmento_dian y CIIU.
        """
        # Asegurar que no hay empresa
        Empresa.objects.all().delete()
        
        # 1. Crear empresa
        create_payload = {
            'razon_social': 'Empresa Test S.A.S.',
            'nit': '900123456',
            'direccion': 'Calle 123 #45-67',
            'telefono': '3001234567',
        }
        
        create_response = self.client.post(self.api_base, create_payload, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        empresa_id = create_response.json()['id']
        
        # 2. Actualizar con segmento_dian y actividad_economica
        update_payload = {
            'tipo_contribuyente_segmento': 'MEDIANO',
            'actividad_economica': '6201',  # Código CIIU válido (si existe en catálogo)
        }
        
        update_response = self.client.patch(
            f'{self.api_base}{empresa_id}/',
            update_payload,
            format='json'
        )
        
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        data = update_response.json()
        self.assertEqual(data['tipo_contribuyente_segmento'], 'MEDIANO')
        if 'actividad_economica' in data:
            self.assertEqual(data['actividad_economica'], '6201')
        
        # 3. Verificar que los cambios se reflejan en GET mi-empresa
        get_response = self.client.get(self.mi_empresa_url)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        get_data = get_response.json()
        self.assertEqual(get_data['tipo_contribuyente_segmento'], 'MEDIANO')
    
    def test_update_existing_empresa(self):
        """
        Verifica que PATCH funciona cuando la empresa ya existe.
        """
        # Crear empresa existente
        empresa = Empresa.objects.create(
            razon_social='Empresa Existente S.A.S.',
            nit='800123456',
            dv='1',
            direccion='Calle Principal 100',
            telefono='3007654321',
        )
        
        # Actualizar
        update_payload = {
            'tipo_contribuyente_segmento': 'GRAN_CONTRIBUYENTE',
            'regimen_renta_codigo': 'ORDINARIO',
        }
        
        response = self.client.patch(
            f'{self.api_base}{empresa.id}/',
            update_payload,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['tipo_contribuyente_segmento'], 'GRAN_CONTRIBUYENTE')
        self.assertEqual(data['regimen_renta_codigo'], 'ORDINARIO')
        
        # Verificar en BD
        empresa.refresh_from_db()
        self.assertEqual(empresa.tipo_contribuyente_segmento, 'GRAN_CONTRIBUYENTE')
        self.assertEqual(empresa.regimen_renta_codigo, 'ORDINARIO')
    
    def test_create_returns_409_if_already_exists(self):
        """
        Verifica que POST retorna 409 si ya existe una empresa (singleton rule).
        """
        # Crear empresa existente
        Empresa.objects.create(
            razon_social='Empresa Existente S.A.S.',
            nit='800123456',
            dv='1',
            direccion='Calle Principal 100',
            telefono='3007654321',
        )
        
        # Intentar crear otra
        payload = {
            'razon_social': 'Nueva Empresa S.A.S.',
            'nit': '900999999',
            'direccion': 'Calle Nueva 200',
            'telefono': '3008888888',
        }
        
        response = self.client.post(self.api_base, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        data = response.json()
        self.assertIn('detail', data)
        self.assertIn('Ya existe', data['detail'])
