"""
Tests de API para la app contabilidad.

Verifica:
- CRUD de CuentaContable, AsientoContable, MovimientoContable
- POST /api/v1/asientos-contables/{id}/aprobar/
- Paginación y filtros
"""
from decimal import Decimal

from rest_framework import status

from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.empresa.models import Empresa
from apps.tenant.contabilidad.models import (
    AsientoContable,
    CuentaContable,
    MovimientoContable,
)


class CuentaContableViewSetTests(TenantAPITestCase):
    """Tests para CuentaContableViewSet."""
    
    def setUp(self):
        """Configuración inicial."""
        super().setUp()
        self.empresa = Empresa.objects.first()
        if not self.empresa:
            self.empresa = Empresa.objects.create(
                razon_social='Empresa Test',
                nit='123456789',
                dv='0',
                direccion='Calle Test'
            )
        
        self.cuenta = CuentaContable.objects.create(
            empresa=self.empresa,
            codigo='110505',
            nombre='Caja',
            tipo='ACTIVO',
            activa=True,
        )
    
    def test_list_cuentas(self):
        """Test: GET /api/v1/cuentas-contables/ devuelve lista paginada."""
        response = self.tget('/api/v1/contabilidad/cuentas-contables/')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        data = response.json()
        self.assertPaginationFormat(data)
    
    def test_create_cuenta(self):
        """Test: POST /api/v1/cuentas-contables/ crea nueva cuenta."""
        data = {
            'codigo': '110510',
            'nombre': 'Bancos',
            'tipo': 'ACTIVO',
            'activa': True,
        }
        response = self.tpost('/api/v1/contabilidad/cuentas-contables/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()
        self.assertEqual(response_data['codigo'], '110510')


class AsientoContableViewSetTests(TenantAPITestCase):
    """Tests para AsientoContableViewSet."""
    
    def setUp(self):
        """Configuración inicial."""
        super().setUp()
        self.empresa = Empresa.objects.first()
        if not self.empresa:
            self.empresa = Empresa.objects.create(
                razon_social='Empresa Test',
                nit='123456789',
                dv='0',
                direccion='Calle Test'
            )
        
        self.cuenta_debe = CuentaContable.objects.create(
            empresa=self.empresa,
            codigo='110505',
            nombre='Caja',
            tipo='ACTIVO',
            activa=True,
        )
        
        self.cuenta_haber = CuentaContable.objects.create(
            empresa=self.empresa,
            codigo='240805',
            nombre='Ingresos',
            tipo='INGRESO',
            activa=True,
        )
        
        self.asiento = AsientoContable.objects.create(
            empresa=self.empresa,
            numero='AS-001',
            fecha='2024-01-15',
            descripcion='Asiento de prueba',
            estado='BORRADOR',
        )
        
        # Crear movimientos balanceados
        MovimientoContable.objects.create(
            empresa=self.empresa,
            asiento=self.asiento,
            cuenta=self.cuenta_debe,
            debe=Decimal('100000.00'),
            haber=Decimal('0.00'),
            descripcion='Debe',
            orden=1,
        )
        
        MovimientoContable.objects.create(
            empresa=self.empresa,
            asiento=self.asiento,
            cuenta=self.cuenta_haber,
            debe=Decimal('0.00'),
            haber=Decimal('100000.00'),
            descripcion='Haber',
            orden=2,
        )
        
        # Recalcular totales
        self.asiento.refresh_from_db()
    
    def test_list_asientos(self):
        """Test: GET /api/v1/asientos-contables/ devuelve lista paginada."""
        response = self.tget('/api/v1/contabilidad/asientos-contables/')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        data = response.json()
        self.assertPaginationFormat(data)
    
    def test_create_asiento(self):
        """Test: POST /api/v1/asientos-contables/ crea nuevo asiento."""
        data = {
            'numero': 'AS-002',
            'fecha': '2024-01-16',
            'descripcion': 'Nuevo asiento',
            'estado': 'BORRADOR',
        }
        response = self.tpost('/api/v1/contabilidad/asientos-contables/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()
        self.assertEqual(response_data['numero'], 'AS-002')
    
    def test_aprobar_action(self):
        """Test: POST /api/v1/asientos-contables/{id}/aprobar/ aprueba asiento balanceado."""
        response = self.tpost(f'/api/v1/contabilidad/asientos-contables/{self.asiento.id}/aprobar/', {})
        self.assertJSONResponse(response, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data['estado'], 'APROBADO')
        
        # Verificar en BD
        self.asiento.refresh_from_db()
        self.assertEqual(self.asiento.estado, 'APROBADO')
    
    def test_aprobar_desbalanceado(self):
        """Test: No se puede aprobar asiento desbalanceado."""
        # Crear asiento desbalanceado
        asiento_desbalanceado = AsientoContable.objects.create(
            empresa=self.empresa,
            numero='AS-003',
            fecha='2024-01-17',
            descripcion='Asiento desbalanceado',
            estado='BORRADOR',
        )
        
        MovimientoContable.objects.create(
            empresa=self.empresa,
            asiento=asiento_desbalanceado,
            cuenta=self.cuenta_debe,
            debe=Decimal('100000.00'),
            haber=Decimal('0.00'),
            descripcion='Solo debe',
            orden=1,
        )
        
        # Intentar aprobar
        response = self.tpost(f'/api/v1/contabilidad/asientos-contables/{asiento_desbalanceado.id}/aprobar/', {})
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
    
    def test_filter_by_estado(self):
        """Test: Filtrar por estado."""
        response = self.tget('/api/v1/contabilidad/asientos-contables/?estado=BORRADOR')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        data = response.json()
        for result in data['results']:
            self.assertEqual(result['estado'], 'BORRADOR')


class MovimientoContableViewSetTests(TenantAPITestCase):
    """Tests para MovimientoContableViewSet."""
    
    def setUp(self):
        """Configuración inicial."""
        super().setUp()
        self.empresa = Empresa.objects.first()
        if not self.empresa:
            self.empresa = Empresa.objects.create(
                razon_social='Empresa Test',
                nit='123456789',
                dv='0',
                direccion='Calle Test'
            )
        
        self.cuenta = CuentaContable.objects.create(
            empresa=self.empresa,
            codigo='110505',
            nombre='Caja',
            tipo='ACTIVO',
            activa=True,
        )
        
        self.asiento = AsientoContable.objects.create(
            empresa=self.empresa,
            numero='AS-001',
            fecha='2024-01-15',
            descripcion='Asiento de prueba',
            estado='BORRADOR',
        )
        
        self.movimiento = MovimientoContable.objects.create(
            empresa=self.empresa,
            asiento=self.asiento,
            cuenta=self.cuenta,
            debe=Decimal('100000.00'),
            haber=Decimal('0.00'),
            descripcion='Movimiento test',
            orden=1,
        )
    
    def test_list_movimientos(self):
        """Test: GET /api/v1/movimientos-contables/ devuelve lista paginada."""
        response = self.tget('/api/v1/contabilidad/movimientos-contables/')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        data = response.json()
        self.assertPaginationFormat(data)
    
    def test_create_movimiento(self):
        """Test: POST /api/v1/movimientos-contables/ crea nuevo movimiento."""
        data = {
            'asiento': self.asiento.id,
            'cuenta': self.cuenta.id,
            'debe': '50000.00',
            'haber': '0.00',
            'descripcion': 'Nuevo movimiento',
            'orden': 2,
        }
        response = self.tpost('/api/v1/contabilidad/movimientos-contables/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()
        self.assertEqual(response_data['descripcion'], 'Nuevo movimiento')
