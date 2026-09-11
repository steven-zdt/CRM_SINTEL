"""
Tests de la maquina de estados de PeriodoNomina (mision auditoria nomina
DEUDA-23, 2026-09-10).

Antes de este archivo, CERO tests en todo el repo cubrian PeriodoNomina --
la "verificacion end-to-end" documentada en NOMINA_FLUJO_EMPRESARIAL.md §6
fue manual (Django test Client ad-hoc durante esa sesion), nunca persistida.
Cubre: flujo feliz completo, transiciones invalidas, permisos por rol,
anulacion en cascada, bloqueo/desbloqueo, y el guard de "pendientes" en
cerrar_periodo() agregado en esta misma auditoria (DEUDA-22).
"""
from decimal import Decimal

from django.test import override_settings
from django_tenants.utils import schema_context
from rest_framework import status

from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.empleados.models import Contrato, Devengo, Empleado, PeriodoNomina, ResolucionDIAN
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile


@override_settings(ALLOWED_HOSTS=['*'])
class TestPeriodoNominaStateMachine(TenantAPITestCase):

    URL = '/api/v1/empleados/periodos-nomina/'

    def setUp(self):
        super().setUp()
        with schema_context(self.tenant.schema_name):
            empresa = Empresa.objects.first()
            self.empresa = empresa

            self.empleado = Empleado.objects.create(
                empresa=empresa, tipo_documento='CC', numero_documento='700111222',
                primer_nombre='Carlos', primer_apellido='Ramirez',
                email='carlos.ramirez@example.com', eps='EPS001', afp='AFP001', arl='ARL001',
                estado='ACTIVO', fecha_ingreso='2020-01-01',
            )
            self.contrato = Contrato.objects.create(
                empresa=empresa, empleado=self.empleado, tipo='INDEF',
                fecha_inicio='2020-01-01', salario_mensual=Decimal('2000000.00'),
                estado='ACTIVO', activo=True,
            )
            # Resolucion DIAN vigente -- procesar_devengo() la exige para
            # preliquidar (guard de consecutivo), sin ella el empleado cae
            # en 'fallidos' en vez de 'creados'.
            ResolucionDIAN.objects.create(
                empresa=empresa, numero_resolucion='18760000001', prefijo='NE',
                rango_desde=1, rango_hasta=100000,
                fecha_resolucion='2024-01-01', fecha_inicio='2024-01-01',
                fecha_fin='2030-12-31', vigente=True,
            )

    def _crear_periodo(self, periodo_mes='2024-06'):
        res = self.tpost(self.URL, data={
            'periodo_mes': periodo_mes,
            'fecha_inicio': f'{periodo_mes}-01',
            'fecha_fin': f'{periodo_mes}-30',
            'fecha_pago': f'{periodo_mes}-30',
        })
        self.assertJSONResponse(res, status.HTTP_201_CREATED)
        return res.data['uuid']

    def _set_rol(self, rol):
        with schema_context(self.tenant.schema_name):
            TenantProfile.objects.filter(user=self.user, empresa=self.empresa).update(rol=rol)

    # -- Flujo feliz completo -------------------------------------------------

    def test_flujo_completo_abierto_hasta_cerrado(self):
        periodo_uuid = self._crear_periodo()
        detail_url = f'{self.URL}{periodo_uuid}/'

        res_get = self.tpost(f'{detail_url}preliquidar/')
        self.assertJSONResponse(res_get, status.HTTP_200_OK)
        self.assertEqual(len(res_get.data['creados']), 1)
        self.assertEqual(len(res_get.data['fallidos']), 0)

        with schema_context(self.tenant.schema_name):
            periodo = PeriodoNomina.objects.get(uuid=periodo_uuid)
            self.assertEqual(periodo.estado, 'PRELIQUIDADO')
            self.assertEqual(Devengo.objects.filter(periodo=periodo, anulado=False).count(), 1)

        res_rev = self.tpost(f'{detail_url}enviar-revision/')
        self.assertJSONResponse(res_rev, status.HTTP_200_OK)
        self.assertEqual(res_rev.data['estado'], 'EN_REVISION')

        res_resumen = self.tget(f'{detail_url}resumen/')
        self.assertJSONResponse(res_resumen, status.HTTP_200_OK)
        self.assertEqual(res_resumen.data['pendientes'], 0)
        self.assertEqual(res_resumen.data['empleados_incluidos'], 1)

        res_aprob = self.tpost(f'{detail_url}aprobar/')
        self.assertJSONResponse(res_aprob, status.HTTP_200_OK)
        self.assertEqual(res_aprob.data['estado'], 'APROBADO')

        res_pago = self.tpost(f'{detail_url}marcar-pagado/')
        self.assertJSONResponse(res_pago, status.HTTP_200_OK)
        self.assertEqual(res_pago.data['estado'], 'PAGADO')

        res_cierre = self.tpost(f'{detail_url}cerrar/')
        self.assertJSONResponse(res_cierre, status.HTTP_200_OK)
        self.assertEqual(res_cierre.data['estado'], 'CERRADO')

    # -- Transiciones invalidas -------------------------------------------------

    def test_no_permite_aprobar_directo_desde_abierto(self):
        periodo_uuid = self._crear_periodo(periodo_mes='2024-07')
        res = self.tpost(f'{self.URL}{periodo_uuid}/aprobar/')
        self.assertJSONResponse(res, status.HTTP_400_BAD_REQUEST)

    def test_no_permite_periodo_duplicado_mismo_mes(self):
        self._crear_periodo(periodo_mes='2024-08')
        res2 = self.tpost(self.URL, data={
            'periodo_mes': '2024-08', 'fecha_inicio': '2024-08-01',
            'fecha_fin': '2024-08-30', 'fecha_pago': '2024-08-30',
        })
        self.assertJSONResponse(res2, status.HTTP_400_BAD_REQUEST)

    # -- DEUDA-22: cierre bloqueado con pendientes -------------------------------

    def test_cerrar_bloqueado_si_hay_empleados_pendientes(self):
        periodo_uuid = self._crear_periodo(periodo_mes='2024-09')
        detail_url = f'{self.URL}{periodo_uuid}/'
        self.assertJSONResponse(self.tpost(f'{detail_url}preliquidar/'), status.HTTP_200_OK)

        # Alta de un segundo empleado elegible DESPUES de preliquidar -> queda
        # pendiente (nunca tuvo devengo en este periodo).
        with schema_context(self.tenant.schema_name):
            empleado2 = Empleado.objects.create(
                empresa=self.empresa, tipo_documento='CC', numero_documento='700111333',
                primer_nombre='Ana', primer_apellido='Torres', email='ana.torres@example.com',
                eps='EPS001', afp='AFP001', arl='ARL001', estado='ACTIVO', fecha_ingreso='2024-08-01',
            )
            Contrato.objects.create(
                empresa=self.empresa, empleado=empleado2, tipo='INDEF',
                fecha_inicio='2024-08-01', salario_mensual=Decimal('1800000.00'),
                estado='ACTIVO', activo=True,
            )

        self.assertJSONResponse(self.tpost(f'{detail_url}enviar-revision/'), status.HTTP_200_OK)
        self.assertJSONResponse(self.tpost(f'{detail_url}aprobar/'), status.HTTP_200_OK)
        self.assertJSONResponse(self.tpost(f'{detail_url}marcar-pagado/'), status.HTTP_200_OK)

        res_cierre = self.tpost(f'{detail_url}cerrar/')
        self.assertJSONResponse(res_cierre, status.HTTP_400_BAD_REQUEST)
        self.assertIn('pendientes', res_cierre.data)

        with schema_context(self.tenant.schema_name):
            periodo = PeriodoNomina.objects.get(uuid=periodo_uuid)
            self.assertEqual(periodo.estado, 'PAGADO', "El periodo NO debe haber avanzado a CERRADO")

    # -- Anulacion en cascada -----------------------------------------------

    def test_anular_periodo_anula_devengos_en_cascada(self):
        periodo_uuid = self._crear_periodo(periodo_mes='2024-10')
        detail_url = f'{self.URL}{periodo_uuid}/'
        self.assertJSONResponse(self.tpost(f'{detail_url}preliquidar/'), status.HTTP_200_OK)

        res_anular = self.tpost(f'{detail_url}anular/')
        self.assertJSONResponse(res_anular, status.HTTP_200_OK)
        self.assertEqual(res_anular.data['estado'], 'ANULADO')

        with schema_context(self.tenant.schema_name):
            periodo = PeriodoNomina.objects.get(uuid=periodo_uuid)
            self.assertFalse(Devengo.objects.filter(periodo=periodo, anulado=False).exists())
            self.assertTrue(Devengo.objects.filter(periodo=periodo, anulado=True).exists())

    # -- Bloqueo / desbloqueo -------------------------------------------------

    def test_bloquear_y_desbloquear_periodo(self):
        periodo_uuid = self._crear_periodo(periodo_mes='2024-11')
        detail_url = f'{self.URL}{periodo_uuid}/'

        res_bloq = self.tpost(f'{detail_url}bloquear/')
        self.assertJSONResponse(res_bloq, status.HTTP_200_OK)
        self.assertEqual(res_bloq.data['estado'], 'BLOQUEADO')

        res_desbloq = self.tpost(f'{detail_url}desbloquear/', data={'estado_destino': 'ABIERTO'})
        self.assertJSONResponse(res_desbloq, status.HTTP_200_OK)
        self.assertEqual(res_desbloq.data['estado'], 'ABIERTO')

    # -- Permisos por rol (backend es la autoridad, no la UI) ----------------

    def test_visor_no_puede_preliquidar(self):
        periodo_uuid = self._crear_periodo(periodo_mes='2024-12')
        self._set_rol('VISOR')
        res = self.tpost(f'{self.URL}{periodo_uuid}/preliquidar/')
        self.assertJSONResponse(res, status.HTTP_403_FORBIDDEN)

    def test_operador_no_puede_aprobar(self):
        periodo_uuid = self._crear_periodo(periodo_mes='2025-01')
        detail_url = f'{self.URL}{periodo_uuid}/'
        self.assertJSONResponse(self.tpost(f'{detail_url}preliquidar/'), status.HTTP_200_OK)
        self.assertJSONResponse(self.tpost(f'{detail_url}enviar-revision/'), status.HTTP_200_OK)

        self._set_rol('OPERADOR')
        res = self.tpost(f'{detail_url}aprobar/')
        self.assertJSONResponse(res, status.HTTP_403_FORBIDDEN)
