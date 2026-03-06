"""
Tests de API para la app empresa.

Verifica:
- CRUD completo
- GET /api/v1/empresas/activas/
- Paginación y filtros
- Aislamiento por tenant
"""
from rest_framework import status
from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.empresa.models import Empresa


class EmpresaViewSetTests(TenantAPITestCase):
    """Tests para EmpresaViewSet."""
    
    def setUp(self):
        """Configuración inicial."""
        super().setUp()
        
        # Crear empresas de prueba en el tenant actual
        # Incluir todos los campos requeridos: razon_social, nit, dv, direccion, ciudad, departamento
        self.empresa1 = Empresa.objects.create(
            razon_social='Empresa Activa S.A.S.',
            nit='900123456',
            dv='1',
            direccion='Calle 123 #45-67',
            ciudad='Bogotá',
            departamento='Cundinamarca',
            email='empresa1@example.com',
            activa=True,
        )
        self.empresa2 = Empresa.objects.create(
            razon_social='Empresa Inactiva S.A.S.',
            nit='900654321',
            dv='1',
            direccion='Carrera 78 #90-12',
            ciudad='Medellín',
            departamento='Antioquia',
            email='empresa2@example.com',
            activa=False,
        )
    
    def test_list_empresas(self):
        """Test: GET /api/v1/empresas/ devuelve lista paginada."""
        response = self.tget('/api/v1/empresas/')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        data = response.json()
        self.assertPaginationFormat(data)
        self.assertGreaterEqual(len(data['results']), 2)
    
    def test_detail_empresa(self):
        """Test: GET /api/v1/empresas/{id}/ devuelve detalle."""
        response = self.tget(f'/api/v1/empresas/{self.empresa1.id}/')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['id'], self.empresa1.id)
        self.assertEqual(data['razon_social'], 'Empresa Activa S.A.S.')
    
    def test_create_empresa(self):
        """Test: POST /api/v1/empresas/ crea nueva empresa."""
        # Incluir todos los campos requeridos del modelo
        data = {
            'razon_social': 'Nueva Empresa S.A.S.',
            'nit': '900999999-1',  # El serializer acepta formato con guión
            'direccion': 'Avenida Principal 123',
            'ciudad': 'Cali',
            'departamento': 'Valle del Cauca',
            'email': 'nueva@example.com',
            'activa': True,
        }
        response = self.tpost('/api/v1/empresas/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()
        self.assertEqual(response_data['razon_social'], 'Nueva Empresa S.A.S.')
        
        # Verificar que se creó en la BD (el modelo separa nit y dv)
        self.assertTrue(Empresa.objects.filter(nit='900999999').exists())
    
    def test_update_empresa(self):
        """Test: PUT /api/v1/empresas/{id}/ actualiza empresa."""
        # Incluir todos los campos requeridos para PUT
        data = {
            'razon_social': 'Empresa Actualizada S.A.S.',
            'nit': f'{self.empresa1.nit}-{self.empresa1.dv}',  # Formato completo
            'direccion': self.empresa1.direccion,
            'ciudad': self.empresa1.ciudad,
            'departamento': self.empresa1.departamento,
            'email': self.empresa1.email,
            'activa': True,
        }
        response = self.tput(f'/api/v1/empresas/{self.empresa1.id}/', data)
        self.assertJSONResponse(response, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data['razon_social'], 'Empresa Actualizada S.A.S.')
    
    def test_delete_empresa(self):
        """Test: DELETE /api/v1/empresas/{id}/ elimina empresa."""
        empresa_id = self.empresa2.id
        response = self.tdelete(f'/api/v1/empresas/{empresa_id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Empresa.objects.filter(id=empresa_id).exists())
    
    def test_activas_action(self):
        """Test: GET /api/v1/empresas/activas/ devuelve solo empresas activas."""
        response = self.tget('/api/v1/empresas/activas/')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        data = response.json()
        # Verificar que todas las empresas devueltas están activas
        for empresa in data.get('results', []):
            self.assertTrue(empresa['activa'])
    
    def test_filter_by_activa(self):
        """Test: Filtrar por activa."""
        response = self.tget('/api/v1/empresas/?activa=true')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        data = response.json()
        for result in data['results']:
            self.assertTrue(result['activa'])
    
    def test_filter_by_ciudad(self):
        """Test: Filtrar por ciudad."""
        response = self.tget('/api/v1/empresas/?ciudad=Bogotá')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        data = response.json()
        for result in data['results']:
            self.assertEqual(result['ciudad'], 'Bogotá')
    
    def test_search_by_razon_social(self):
        """Test: Búsqueda por razón social."""
        response = self.tget('/api/v1/empresas/?search=Activa')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        data = response.json()
        self.assertGreater(len(data['results']), 0)
        self.assertIn('Activa', data['results'][0]['razon_social'])
    
    def test_tenant_isolation(self):
        """Test: Verificar aislamiento entre tenants."""
        # Crear otro tenant
        from apps.public.tenants.models import Client, Domain
        from django_tenants.utils import schema_context
        from unittest.mock import patch
        
        with schema_context('public'):
            with patch('apps.public.tenants.models.Client.create_schema', return_value=None):
                tenant2 = Client.objects.create(
                    nombre='Tenant 2',
                    schema_name='tenant2',  # Schema name válido (sin guiones)
                    on_trial=True,
                )
                Domain.objects.create(
                    domain='tenant2.localhost',
                    tenant=tenant2,
                    is_primary=True,
                )
        
        # Crear empresa en tenant2 (con todos los campos requeridos)
        with schema_context('tenant2'):
            empresa_tenant2 = Empresa.objects.create(
                razon_social='Empresa Tenant 2',
                nit='800111111',
                dv='1',
                direccion='Calle Test 456',
                ciudad='Bogotá',
                departamento='Cundinamarca',
                email='tenant2@example.com',
                activa=True,
            )
        
        # Verificar que el tenant actual no ve la empresa del otro tenant
        response = self.tget('/api/v1/empresas/')
        data = response.json()
        nit_ids = [e.get('nit', '') for e in data['results']]
        # El serializer puede devolver nit con o sin formato, verificar ambos
        self.assertNotIn('800111111', nit_ids)
        self.assertNotIn('800111111-1', nit_ids)
        
        # Verificar que tenant2 sí ve su empresa (el modelo separa nit y dv)
        with schema_context('tenant2'):
            self.assertTrue(Empresa.objects.filter(nit='800111111').exists())
