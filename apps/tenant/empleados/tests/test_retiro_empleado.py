"""
Tests del flujo controlado de retiro de empleado (mision auditoria nomina
FASE 21/22, 2026-09-10).

Cubre las brechas detectadas en la auditoria:
- Retirar un empleado exige motivo_retiro + fecha_retiro (ya no basta con
  PATCH estado=RETIRADO).
- Indemnizacion por despido sin justa causa (CST art. 64) se calcula
  automaticamente segun tipo de contrato y tiempo de servicio -- nunca es
  un numero manual inventado por el caller.
- No se puede generar una LIQUIDACION_DEFINITIVA para un empleado que
  sigue ACTIVO.
"""
from decimal import Decimal

from django.test import override_settings
from django_tenants.utils import schema_context
from rest_framework import status

from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.empleados.models import Contrato, Devengo, Empleado
from apps.tenant.empleados.services.business_service import (
    EmpleadoBusinessService,
    NominaCalculationService,
)
from apps.tenant.empresa.models import Empresa


@override_settings(ALLOWED_HOSTS=['*'], SMLMV_VIGENTE='1423500')
class TestRetiroEmpleado(TenantAPITestCase):

    def setUp(self):
        super().setUp()
        self.url_list = '/api/v1/empleados/'
        self.valid_payload = {
            'tipo_documento': 'CC',
            'numero_documento': '900111222',
            'primer_nombre': 'Maria',
            'primer_apellido': 'Lopez',
            'email': 'maria.lopez@example.com',
            'eps': 'EPS001',
            'afp': 'AFP001',
            'arl': 'ARL001',
            'nivel_riesgo_arl': 'I',
            'fecha_ingreso': '2020-01-01',
            'estado': 'ACTIVO',
        }

    def _crear_empleado_con_contrato_y_nomina(self, fecha_inicio_contrato='2020-01-01', salario='2000000.00', tipo='INDEF'):
        res_post = self.tpost(self.url_list, data=self.valid_payload)
        self.assertJSONResponse(res_post, status.HTTP_201_CREATED)
        emp_uuid = res_post.data['uuid']

        with schema_context(self.tenant.schema_name):
            empresa = Empresa.objects.first()
            empleado = Empleado.objects.get(uuid=emp_uuid)
            contrato = Contrato.objects.create(
                empresa=empresa,
                empleado=empleado,
                tipo=tipo,
                fecha_inicio=fecha_inicio_contrato,
                salario_mensual=Decimal(salario),
                estado='ACTIVO',
                activo=True,
            )
            Devengo.objects.create(
                empresa=empresa,
                empleado=empleado,
                contrato=contrato,
                periodo_mes='2023-12',
                fecha_pago='2023-12-30',
                salario_base=Decimal(salario),
                salud_empleado=Decimal('80000.00'),
                pension_empleado=Decimal('80000.00'),
                neto_pagar=Decimal('1840000.00'),
                anulado=False,
            )
        return emp_uuid, f"{self.url_list}{emp_uuid}/"

    # -- Validaciones de entrada (FASE 22) -----------------------------------

    def test_retiro_sin_motivo_falla(self):
        emp_uuid, url_detail = self._crear_empleado_con_contrato_y_nomina()
        res = self.tpatch(url_detail, data={'estado': 'RETIRADO', 'fecha_retiro': '2024-01-01'})
        self.assertJSONResponse(res, status.HTTP_400_BAD_REQUEST)
        self.assertIn('motivo_retiro', res.data)

    def test_retiro_sin_fecha_falla(self):
        emp_uuid, url_detail = self._crear_empleado_con_contrato_y_nomina()
        res = self.tpatch(url_detail, data={'estado': 'RETIRADO', 'motivo_retiro': 'RENUNCIA'})
        self.assertJSONResponse(res, status.HTTP_400_BAD_REQUEST)
        self.assertIn('fecha_retiro', res.data)

    def test_no_se_puede_retirar_dos_veces(self):
        emp_uuid, url_detail = self._crear_empleado_con_contrato_y_nomina()
        res1 = self.tpatch(url_detail, data={'estado': 'RETIRADO', 'fecha_retiro': '2024-01-01', 'motivo_retiro': 'RENUNCIA'})
        self.assertJSONResponse(res1, status.HTTP_200_OK)

        with schema_context(self.tenant.schema_name):
            empleado = Empleado.objects.get(uuid=emp_uuid)
            with self.assertRaises(Exception):
                EmpleadoBusinessService.retirar_empleado(
                    empleado=empleado, motivo_retiro='RENUNCIA',
                    fecha_retiro='2024-02-01', empresa_id=empleado.empresa_id,
                )

    # -- Flujo controlado de extremo a extremo -------------------------------

    def test_retiro_renuncia_no_genera_indemnizacion_y_cierra_contrato(self):
        emp_uuid, url_detail = self._crear_empleado_con_contrato_y_nomina()
        res = self.tpatch(url_detail, data={
            'estado': 'RETIRADO', 'fecha_retiro': '2024-01-15', 'motivo_retiro': 'RENUNCIA',
        })
        self.assertJSONResponse(res, status.HTTP_200_OK)

        with schema_context(self.tenant.schema_name):
            empleado = Empleado.objects.get(uuid=emp_uuid)
            self.assertEqual(empleado.estado, 'RETIRADO')
            self.assertEqual(str(empleado.fecha_retiro), '2024-01-15')
            self.assertEqual(empleado.motivo_retiro, 'RENUNCIA')

            contrato = Contrato.objects.get(empleado=empleado)
            self.assertEqual(contrato.estado, 'INACTIVO')
            self.assertFalse(contrato.activo)
            self.assertEqual(str(contrato.fecha_fin), '2024-01-15')

            liquidacion = empleado.liquidaciones.filter(tipo_liquidacion='LIQUIDACION_DEFINITIVA').first()
            self.assertIsNotNone(liquidacion, "Debe generarse una liquidacion definitiva automatica")
            self.assertEqual(liquidacion.desglose_conceptos['indemnizacion_detalle']['aplica'], False)
            self.assertEqual(Decimal(liquidacion.desglose_conceptos['indemnizacion']), Decimal('0.00'))

    def test_retiro_sin_justa_causa_indefinido_menos_de_un_anio(self):
        """Salario < 10 SMLMV, < 1 año de servicio -> 30 dias de salario diario."""
        emp_uuid, url_detail = self._crear_empleado_con_contrato_y_nomina(
            fecha_inicio_contrato='2023-06-01', salario='2000000.00',
        )
        res = self.tpatch(url_detail, data={
            'estado': 'RETIRADO', 'fecha_retiro': '2024-01-01', 'motivo_retiro': 'SIN_JUSTA_CAUSA',
        })
        self.assertJSONResponse(res, status.HTTP_200_OK)

        with schema_context(self.tenant.schema_name):
            empleado = Empleado.objects.get(uuid=emp_uuid)
            liquidacion = empleado.liquidaciones.filter(tipo_liquidacion='LIQUIDACION_DEFINITIVA').first()
            detalle = liquidacion.desglose_conceptos['indemnizacion_detalle']
            self.assertTrue(detalle['aplica'])
            # 30 dias * (2.000.000 / 30) = 2.000.000 exactos
            self.assertEqual(Decimal(detalle['valor']), Decimal('2000000.00'))

    def test_retiro_sin_justa_causa_indefinido_mas_de_un_anio_prorratea(self):
        """> 1 año de servicio: 30 dias + 20 dias/año adicional (prorrateado)."""
        contrato_inicio = '2019-01-01'
        fecha_retiro = '2022-01-01'  # ~3 años
        emp_uuid, url_detail = self._crear_empleado_con_contrato_y_nomina(
            fecha_inicio_contrato=contrato_inicio, salario='2000000.00',
        )

        with schema_context(self.tenant.schema_name):
            from datetime import date
            contrato = Contrato.objects.get(empleado__uuid=emp_uuid)
            dias_servicio = NominaCalculationService.calcular_dias_360(
                date(2019, 1, 1), date(2022, 1, 1)
            )
            anios_adicionales = (Decimal(dias_servicio) - Decimal('360')) / Decimal('360')
            dias_esperados = Decimal('30') + (anios_adicionales * Decimal('20'))
            valor_esperado = (dias_esperados * (Decimal('2000000.00') / Decimal('30'))).quantize(Decimal('0.01'))

        res = self.tpatch(url_detail, data={
            'estado': 'RETIRADO', 'fecha_retiro': fecha_retiro, 'motivo_retiro': 'SIN_JUSTA_CAUSA',
        })
        self.assertJSONResponse(res, status.HTTP_200_OK)

        with schema_context(self.tenant.schema_name):
            empleado = Empleado.objects.get(uuid=emp_uuid)
            liquidacion = empleado.liquidaciones.filter(tipo_liquidacion='LIQUIDACION_DEFINITIVA').first()
            detalle = liquidacion.desglose_conceptos['indemnizacion_detalle']
            self.assertTrue(detalle['aplica'])
            self.assertEqual(Decimal(detalle['valor']), valor_esperado)

    def test_retiro_sin_justa_causa_prestacion_no_indemniza(self):
        emp_uuid, url_detail = self._crear_empleado_con_contrato_y_nomina(tipo='PRESTACION')
        res = self.tpatch(url_detail, data={
            'estado': 'RETIRADO', 'fecha_retiro': '2024-01-01', 'motivo_retiro': 'SIN_JUSTA_CAUSA',
        })
        self.assertJSONResponse(res, status.HTTP_200_OK)

        with schema_context(self.tenant.schema_name):
            empleado = Empleado.objects.get(uuid=emp_uuid)
            liquidacion = empleado.liquidaciones.filter(tipo_liquidacion='LIQUIDACION_DEFINITIVA').first()
            self.assertIsNotNone(liquidacion)
            self.assertEqual(Decimal(liquidacion.desglose_conceptos['indemnizacion']), Decimal('0.00'))

    # -- Guard de liquidacion definitiva sin retiro (FASE 20) ----------------

    def test_liquidacion_definitiva_requiere_empleado_retirado(self):
        emp_uuid, url_detail = self._crear_empleado_con_contrato_y_nomina()

        with schema_context(self.tenant.schema_name):
            empleado = Empleado.objects.get(uuid=emp_uuid)
            contrato = Contrato.objects.get(empleado=empleado)
            empleado_id, contrato_id = empleado.id, contrato.id

        res = self.tpost('/api/v1/empleados/liquidaciones-prestaciones/', data={
            'empleado_id': empleado_id,
            'contrato_id': contrato_id,
            'tipo_liquidacion': 'LIQUIDACION_DEFINITIVA',
            'fecha_corte': '2024-01-01',
        })
        self.assertJSONResponse(res, status.HTTP_400_BAD_REQUEST)
        self.assertIn('fecha de retiro', str(res.data.get('detail', '')).lower())
