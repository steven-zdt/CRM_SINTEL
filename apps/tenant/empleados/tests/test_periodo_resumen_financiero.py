"""
Tests del Resumen Financiero de PeriodoNomina (mision "Periodos de Nomina"
seccion 15-19, 2026-09-11): la pantalla de "Periodos de Nomina" debe
convertirse en un centro de control del gasto -- no solo el neto pagado al
empleado, sino tambien los aportes patronales (EPS/AFP/ARL/parafiscales) y
el costo total real para la empresa. Todo el calculo vive en Backend
(PeriodoNominaSelector.get_resumen() + NominaCalculationService.
calcular_aportes_patronales()) -- el frontend solo presenta.
"""
from decimal import Decimal

from django.test import override_settings
from django_tenants.utils import schema_context
from rest_framework import status

from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.empleados.models import Contrato, Empleado, ResolucionDIAN
from apps.tenant.empresa.models import Empresa


@override_settings(ALLOWED_HOSTS=['*'])
class TestPeriodoResumenFinanciero(TenantAPITestCase):

    URL_PERIODOS = '/api/v1/empleados/periodos-nomina/'
    URL_DEVENGOS = '/api/v1/empleados/devengos/'

    def setUp(self):
        super().setUp()
        with schema_context(self.tenant.schema_name):
            self.empresa = Empresa.objects.first()
            ResolucionDIAN.objects.create(
                empresa=self.empresa, numero_resolucion='18760000003', prefijo='NE',
                rango_desde=1, rango_hasta=100000,
                fecha_resolucion='2024-01-01', fecha_inicio='2024-01-01',
                fecha_fin='2030-12-31', vigente=True,
            )

        res = self.tpost(self.URL_PERIODOS, data={
            'periodo_mes': '2024-07',
            'fecha_inicio': '2024-07-01',
            'fecha_fin': '2024-07-31',
            'fecha_pago': '2024-07-31',
        })
        self.assertJSONResponse(res, status.HTTP_201_CREATED)
        self.periodo_uuid = res.data['uuid']

    def _crear_empleado_con_contrato(self, doc, nombre, salario='2000000.00', nivel_riesgo_arl='I'):
        with schema_context(self.tenant.schema_name):
            empleado = Empleado.objects.create(
                empresa=self.empresa, tipo_documento='CC', numero_documento=doc,
                primer_nombre=nombre, primer_apellido='Test', email=f'{doc}@example.com',
                eps='EPS001', afp='AFP001', arl='ARL001', nivel_riesgo_arl=nivel_riesgo_arl,
                estado='ACTIVO', fecha_ingreso='2020-01-01',
            )
            contrato = Contrato.objects.create(
                empresa=self.empresa, empleado=empleado, tipo='INDEF',
                fecha_inicio='2020-01-01', salario_mensual=Decimal(salario),
                estado='ACTIVO', activo=True,
            )
            return empleado.id, contrato.id

    def test_resumen_incluye_aportes_patronales_y_costo_total_empresa(self):
        emp_id, contrato_id = self._crear_empleado_con_contrato('800222001', 'Ana')

        res_liq = self.tpost(self.URL_DEVENGOS, data={
            'empleado': emp_id,
            'contrato': contrato_id,
            'periodo': self.periodo_uuid,
            'periodo_mes': '2024-07',
            'dias_laborados': '30',
            'fecha_pago': '2024-07-31',
        })
        self.assertJSONResponse(res_liq, status.HTTP_201_CREATED)

        res = self.tget(f'{self.URL_PERIODOS}{self.periodo_uuid}/resumen/')
        self.assertJSONResponse(res, status.HTTP_200_OK)
        data = res.data

        # Salario 2.000.000 x 30/30 dias = 2.000.000 (sin auxilio -- contrato
        # de prueba no lo pacta), IBC = salario_base (nunca + auxilio).
        self.assertEqual(Decimal(data['total_devengado']), Decimal('2000000.00'))

        aportes = data['aportes_patronales']
        self.assertEqual(Decimal(aportes['eps_patronal']), Decimal('170000.00'))       # 8.5%
        self.assertEqual(Decimal(aportes['pension_patronal']), Decimal('240000.00'))   # 12%
        self.assertEqual(Decimal(aportes['arl_patronal']), Decimal('10440.00'))        # 0.522% (clase I)
        self.assertEqual(Decimal(aportes['caja_compensacion']), Decimal('80000.00'))   # 4%
        self.assertEqual(Decimal(aportes['icbf']), Decimal('60000.00'))                # 3%
        self.assertEqual(Decimal(aportes['sena']), Decimal('40000.00'))                # 2%

        self.assertEqual(Decimal(data['total_aportes_patronales']), Decimal('600440.00'))
        self.assertEqual(Decimal(data['costo_total_empresa']), Decimal('2600440.00'))

    def test_resumen_sin_devengos_reporta_ceros(self):
        res = self.tget(f'{self.URL_PERIODOS}{self.periodo_uuid}/resumen/')
        self.assertJSONResponse(res, status.HTTP_200_OK)
        data = res.data
        self.assertEqual(Decimal(data['total_devengado']), Decimal('0.00'))
        self.assertEqual(Decimal(data['total_aportes_patronales']), Decimal('0.00'))
        self.assertEqual(Decimal(data['costo_total_empresa']), Decimal('0.00'))

    def test_arl_varia_por_nivel_de_riesgo(self):
        """Clase V (riesgo maximo, 6.96%) debe aportar mas ARL que Clase I (0.522%)."""
        emp_id, contrato_id = self._crear_empleado_con_contrato(
            '800222002', 'Pedro', nivel_riesgo_arl='V'
        )
        res_liq = self.tpost(self.URL_DEVENGOS, data={
            'empleado': emp_id,
            'contrato': contrato_id,
            'periodo': self.periodo_uuid,
            'periodo_mes': '2024-07',
            'dias_laborados': '30',
            'fecha_pago': '2024-07-31',
        })
        self.assertJSONResponse(res_liq, status.HTTP_201_CREATED)

        res = self.tget(f'{self.URL_PERIODOS}{self.periodo_uuid}/resumen/')
        self.assertJSONResponse(res, status.HTTP_200_OK)
        self.assertEqual(
            Decimal(res.data['aportes_patronales']['arl_patronal']), Decimal('139200.00')
        )  # 2.000.000 x 6.96%

    def test_contrato_prestacion_no_genera_aportes_patronales(self):
        with schema_context(self.tenant.schema_name):
            empleado = Empleado.objects.create(
                empresa=self.empresa, tipo_documento='CC', numero_documento='800222003',
                primer_nombre='Contratista', primer_apellido='Independiente',
                email='contratista@example.com', eps='EPS001', afp='AFP001', arl='ARL001',
                estado='ACTIVO', fecha_ingreso='2020-01-01',
            )
            contrato = Contrato.objects.create(
                empresa=self.empresa, empleado=empleado, tipo='PRESTACION',
                fecha_inicio='2020-01-01', salario_mensual=Decimal('3000000.00'),
                estado='ACTIVO', activo=True,
            )
            emp_id, contrato_id = empleado.id, contrato.id

        res_liq = self.tpost(self.URL_DEVENGOS, data={
            'empleado': emp_id,
            'contrato': contrato_id,
            'periodo': self.periodo_uuid,
            'periodo_mes': '2024-07',
            'dias_laborados': '30',
            'fecha_pago': '2024-07-31',
        })
        self.assertJSONResponse(res_liq, status.HTTP_201_CREATED)

        res = self.tget(f'{self.URL_PERIODOS}{self.periodo_uuid}/resumen/')
        self.assertJSONResponse(res, status.HTTP_200_OK)
        self.assertEqual(Decimal(res.data['total_aportes_patronales']), Decimal('0.00'))
        # El devengado si se cuenta (el contratista si cobra) -- solo los
        # aportes patronales son cero.
        self.assertEqual(Decimal(res.data['total_devengado']), Decimal('3000000.00'))
