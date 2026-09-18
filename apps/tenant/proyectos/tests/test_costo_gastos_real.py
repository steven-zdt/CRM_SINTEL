"""
GASTOS_PROYECTOS_01 - Tests de calculo de costo_gastos_real en Proyectos.

Cubre calcular_costo_gastos() y su integracion en
calcular_indicadores_financieros() (P&L completo con mano de obra +
materiales + gastos).
"""
import datetime
import uuid as uuid_module
from decimal import Decimal

from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.empresa.models import Empresa
from apps.tenant.gastos.models import DocumentoSoporte, ResolucionDIAN
from apps.tenant.proveedores.models import Proveedor
from apps.tenant.proyectos.models import AsignacionPersonal, Proyecto
from apps.tenant.proyectos.services.business_service import (
    calcular_costo_gastos,
    calcular_indicadores_financieros,
)


class CostoGastosRealTests(TenantAPITestCase):

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first()

        self.proyecto = Proyecto.objects.create(
            empresa=self.empresa,
            nombre='Proyecto Costos',
            codigo='PRJ-2026-COST',
            tipo_servicio='PROYECTO_INTEGRAL',
            valor_contrato_proyectado=Decimal('10000000.00'),
        )
        self.otro_proyecto = Proyecto.objects.create(
            empresa=self.empresa,
            nombre='Otro Proyecto',
            codigo='PRJ-2026-OTRO',
            tipo_servicio='PROYECTO_INTEGRAL',
            valor_contrato_proyectado=Decimal('1000000.00'),
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa,
            numero_documento='900333444',
            razon_social='Proveedor Costos SAS',
            tipo_persona='JURIDICA',
            tipo_documento='NIT',
            regimen_tributario='ORDINARIO',
            activo=True,
        )
        self.resolucion = ResolucionDIAN.objects.create(
            empresa=self.empresa,
            numero_resolucion='RES-COST',
            prefijo='DS',
            rango_desde=1,
            rango_hasta=1000,
            fecha_resolucion=datetime.date(2026, 1, 1),
            fecha_inicio=datetime.date(2026, 1, 1),
            fecha_fin=datetime.date(2027, 1, 1),
        )
        self._consecutivo = 0

    def _crear_documento(self, subtotal, proyecto_uuid=None, activo=True, anulado=False):
        self._consecutivo += 1
        return DocumentoSoporte.objects.create(
            empresa=self.empresa,
            resolucion_dian=self.resolucion,
            consecutivo=self._consecutivo,
            fecha=datetime.date(2026, 6, 1),
            proveedor=self.proveedor,
            subtotal=Decimal(subtotal),
            total=Decimal(subtotal),
            proyecto_uuid=proyecto_uuid,
            activo=activo,
            anulado=anulado,
        )

    def test_costo_gastos_real_cero_sin_gastos(self):
        self.assertEqual(calcular_costo_gastos(self.proyecto), Decimal('0.00'))

    def test_costo_gastos_real_suma_multiples_gastos(self):
        self._crear_documento('100000.00', proyecto_uuid=self.proyecto.uuid)
        self._crear_documento('200000.00', proyecto_uuid=self.proyecto.uuid)

        self.assertEqual(calcular_costo_gastos(self.proyecto), Decimal('300000.00'))

    def test_costo_gastos_real_excluye_anulados(self):
        self._crear_documento('100000.00', proyecto_uuid=self.proyecto.uuid)
        self._crear_documento('999999.00', proyecto_uuid=self.proyecto.uuid, anulado=True, activo=False)

        self.assertEqual(calcular_costo_gastos(self.proyecto), Decimal('100000.00'))

    def test_costo_gastos_real_excluye_inactivos(self):
        self._crear_documento('150000.00', proyecto_uuid=self.proyecto.uuid)
        self._crear_documento('999999.00', proyecto_uuid=self.proyecto.uuid, activo=False)

        self.assertEqual(calcular_costo_gastos(self.proyecto), Decimal('150000.00'))

    def test_costo_gastos_real_excluye_gastos_sin_proyecto(self):
        self._crear_documento('500000.00', proyecto_uuid=None)

        self.assertEqual(calcular_costo_gastos(self.proyecto), Decimal('0.00'))

    def test_costo_gastos_real_excluye_gastos_de_otro_proyecto(self):
        self._crear_documento('500000.00', proyecto_uuid=self.otro_proyecto.uuid)

        self.assertEqual(calcular_costo_gastos(self.proyecto), Decimal('0.00'))
        self.assertEqual(calcular_costo_gastos(self.otro_proyecto), Decimal('500000.00'))

    def test_indicadores_financieros_incluyen_costo_gastos(self):
        AsignacionPersonal.objects.create(
            empresa=self.empresa,
            proyecto=self.proyecto,
            nombre_colaborador='Tecnico',
            rol='TECNICO',
            fecha_asignacion=datetime.date.today(),
            activo=True,
            costo_total_asignacion=Decimal('2000000.00'),
        )
        self._crear_documento('1000000.00', proyecto_uuid=self.proyecto.uuid)

        resultado = calcular_indicadores_financieros(self.proyecto)

        # contrato = 10_000_000; costo_total = 2_000_000 (MO) + 0 (mat) + 1_000_000 (gastos) = 3_000_000
        self.assertEqual(resultado['costo_mano_obra_real'], Decimal('2000000.00'))
        self.assertEqual(resultado['costo_gastos_real'], Decimal('1000000.00'))
        self.assertEqual(resultado['costo_total'], Decimal('3000000.00'))
        self.assertEqual(resultado['utilidad_estimada'], Decimal('7000000.00'))
        self.assertEqual(resultado['margen_rentabilidad'], Decimal('70.00'))

        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.costo_gastos_real, Decimal('1000000.00'))
