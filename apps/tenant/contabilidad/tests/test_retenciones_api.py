"""
Tests para Retencion API endpoints (v3.7.1).

Cubre:
- GET /api/v1/contabilidad/retenciones/ (list, pagination, filters)
- GET /api/v1/contabilidad/retenciones/{uuid}/ (retrieve)
- POST /api/v1/contabilidad/retenciones/ (create)
- DELETE /api/v1/contabilidad/retenciones/{uuid}/ (destroy)
- GET .../obtener-por-tercero/ (custom action)
- GET .../obtener-por-documento/ (custom action)
- ConfiguracionRetenciones CRUD
"""

from decimal import Decimal
from rest_framework import status
from rest_framework.test import APIClient

from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.contabilidad.models import (
    Retencion, ConfiguracionRetenciones, CuentaContable
)
from apps.tenant.contabilidad.services.retenciones_service import RetencionesService
from apps.tenant.empresa.models import Empresa


class RetencionAPITestCase(TenantAPITestCase):
    """Tests para RetencionViewSet."""

    def setUp(self):
        super().setUp()

        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            nombre='API Test Corp',
            nit='800123456',
        )

        self.cuenta = CuentaContable.objects.create(
            empresa=self.empresa,
            codigo='2365',
            nombre='Retención en la Fuente',
            nivel=6,
            tipo='PASIVO',
            activa=True,
        )

        # Crear algunas retenciones para tests
        self.ret1 = RetencionesService.crear_retencion(
            empresa=self.empresa,
            tipo='RETEFUENTE',
            porcentaje=Decimal('2.50'),
            monto=Decimal('100.00'),
            documento_origen_app='facturas',
            documento_origen_modelo='Factura',
            documento_origen_id=1,
        )

        self.ret2 = RetencionesService.crear_retencion(
            empresa=self.empresa,
            tipo='RETEICA',
            porcentaje=Decimal('0.50'),
            monto=Decimal('50.00'),
            documento_origen_app='facturas',
            documento_origen_modelo='Factura',
            documento_origen_id=1,
        )

        self.api_url = '/api/v1/contabilidad/retenciones/'

    def test_list_retenciones(self):
        """Test: GET /api/v1/contabilidad/retenciones/ con paginación."""
        response = self.tget(self.api_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.json())
        self.assertGreaterEqual(len(response.json()['results']), 2)

    def test_list_retenciones_filter_by_tipo(self):
        """Test: Filtrar retenciones por tipo."""
        response = self.tget(f'{self.api_url}?tipo=RETEFUENTE')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()['results']
        self.assertTrue(all(r['tipo'] == 'RETEFUENTE' for r in results))

    def test_list_retenciones_filter_by_documento(self):
        """Test: Filtrar retenciones por documento origen."""
        response = self.tget(
            f'{self.api_url}?documento_origen_modelo=Factura'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()['results']
        self.assertTrue(
            all(r['documento_origen_modelo'] == 'Factura' for r in results)
        )

    def test_list_retenciones_search(self):
        """Test: Buscar retenciones por UUID."""
        response = self.tget(f'{self.api_url}?search={self.ret1.uuid}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_retencion(self):
        """Test: GET /api/v1/contabilidad/retenciones/{uuid}/"""
        url = f'{self.api_url}{self.ret1.uuid}/'
        response = self.tget(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['uuid'], str(self.ret1.uuid))
        self.assertEqual(data['tipo'], 'RETEFUENTE')
        self.assertEqual(data['monto'], '100.00')

    def test_create_retencion_api(self):
        """Test: POST /api/v1/contabilidad/retenciones/"""
        payload = {
            'tipo': 'RETEIVA',
            'porcentaje': '3.00',
            'base': '5000.00',
            'monto': '150.00',
            'documento_origen_app': 'facturas',
            'documento_origen_modelo': 'ItemFactura',
            'documento_origen_id': 42,
            'notas': 'Test API creation',
        }

        response = self.tpost(self.api_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data['tipo'], 'RETEIVA')
        self.assertEqual(data['monto'], '150.00')
        self.assertFalse(data['reversada'])

    def test_destroy_retencion(self):
        """Test: DELETE /api/v1/contabilidad/retenciones/{uuid}/"""
        url = f'{self.api_url}{self.ret1.uuid}/'
        response = self.tdelete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verificar que fue eliminado
        retencion = Retencion.objects.filter(uuid=self.ret1.uuid).exists()
        self.assertFalse(retencion)

    def test_obtener_por_tercero_action(self):
        """Test: GET .../obtener-por-tercero/?nit=&tipo_tercero=&naturaleza="""
        # Crear configuración
        ConfiguracionRetenciones.objects.create(
            empresa=self.empresa,
            tipo_tercero='CLIENTE',
            nit_tercero='123456789',
            tipo_retencion='RETEFUENTE',
            porcentaje_por_defecto=Decimal('2.50'),
            naturaleza='VENTA',
            cuenta_retencion=self.cuenta,
            activa=True,
        )

        url = (
            f'{self.api_url}obtener-por-tercero/'
            f'?nit=123456789&tipo_tercero=CLIENTE&naturaleza=VENTA'
        )
        response = self.tget(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertTrue(data['aplica_retefuente'])
        self.assertEqual(float(data['retefuente_porcentaje']), 2.50)

    def test_obtener_por_tercero_missing_nit(self):
        """Test: Error si falta parámetro nit."""
        url = f'{self.api_url}obtener-por-tercero/?tipo_tercero=CLIENTE'
        response = self.tget(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('missing_nit', response.json()['error'])

    def test_obtener_por_documento_action(self):
        """Test: GET .../obtener-por-documento/?app=&modelo=&id="""
        url = (
            f'{self.api_url}obtener-por-documento/'
            f'?app=facturas&modelo=Factura&id=1'
        )
        response = self.tget(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.json()
        self.assertEqual(len(results), 2)  # ret1 y ret2 tienen documento_origen_id=1
        tipos = {r['tipo'] for r in results}
        self.assertEqual(tipos, {'RETEFUENTE', 'RETEICA'})

    def test_obtener_por_documento_missing_params(self):
        """Test: Error si faltan parámetros."""
        url = f'{self.api_url}obtener-por-documento/?app=facturas'
        response = self.tget(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('missing_params', response.json()['error'])




class ConfiguracionRetencionesAPITestCase(TenantAPITestCase):
    """Tests para ConfiguracionRetencionesViewSet."""

    def setUp(self):
        super().setUp()

        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            nombre='Config Test Corp',
            nit='810123456',
        )

        self.cuenta = CuentaContable.objects.create(
            empresa=self.empresa,
            codigo='2365',
            nombre='Retención en la Fuente',
            nivel=6,
            tipo='PASIVO',
            activa=True,
        )

        self.config = ConfiguracionRetenciones.objects.create(
            empresa=self.empresa,
            tipo_tercero='CLIENTE',
            nit_tercero='111222333',
            tipo_retencion='RETEFUENTE',
            porcentaje_por_defecto=Decimal('2.50'),
            naturaleza='VENTA',
            cuenta_retencion=self.cuenta,
            activa=True,
        )

        self.api_url = '/api/v1/contabilidad/configuraciones-retenciones/'

    def test_list_configuraciones(self):
        """Test: GET /api/v1/contabilidad/configuraciones-retenciones/"""
        response = self.tget(self.api_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()['results']
        self.assertGreaterEqual(len(results), 1)

    def test_list_configuraciones_filter_by_tipo_tercero(self):
        """Test: Filtrar configuraciones por tipo_tercero."""
        response = self.tget(f'{self.api_url}?tipo_tercero=CLIENTE')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()['results']
        self.assertTrue(
            all(r['tipo_tercero'] == 'CLIENTE' for r in results)
        )

    def test_retrieve_configuracion(self):
        """Test: GET /api/v1/contabilidad/configuraciones-retenciones/{uuid}/"""
        url = f'{self.api_url}{self.config.uuid}/'
        response = self.tget(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['nit_tercero'], '111222333')
        self.assertEqual(float(data['porcentaje_por_defecto']), 2.50)

    def test_create_configuracion(self):
        """Test: POST /api/v1/contabilidad/configuraciones-retenciones/"""
        payload = {
            'tipo_tercero': 'PROVEEDOR',
            'nit_tercero': '999888777',
            'tipo_retencion': 'RETEICA',
            'porcentaje_por_defecto': '0.50',
            'naturaleza': 'COMPRA',
            'activa': True,
        }

        response = self.tpost(self.api_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data['nit_tercero'], '999888777')
        self.assertEqual(data['tipo_retencion'], 'RETEICA')

    def test_destroy_configuracion(self):
        """Test: DELETE /api/v1/contabilidad/configuraciones-retenciones/{uuid}/"""
        url = f'{self.api_url}{self.config.uuid}/'
        response = self.tdelete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        config_exists = ConfiguracionRetenciones.objects.filter(
            id=self.config.id
        ).exists()
        self.assertFalse(config_exists)


