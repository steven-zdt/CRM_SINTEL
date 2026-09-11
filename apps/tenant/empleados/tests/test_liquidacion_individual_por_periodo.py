"""
Tests de la correccion arquitectonica de dominio (mision auditoria nomina
"correccion arquitectonica", 2026-09-10): PeriodoNomina es SOLO un
contenedor administrativo -- cada empleado se liquida individualmente
dentro del periodo, con SUS PROPIOS dias_laborados, sin que la duracion
administrativa del periodo los determine.

Antes de esta correccion, la UNICA forma de vincular un Devengo a un
PeriodoNomina era preliquidar_periodo() (forzaba dias_laborados=30 para
TODOS los empleados por igual). DevengoSerializer no tenia campo `periodo`
en absoluto -- la liquidacion individual (offcanvas "Liquidar") no podia
asociarse a ningun periodo. Este archivo prueba el escenario obligatorio
del PROMPT MAESTRO: Juan 8 dias, Pedro 15 dias, Maria 5 dias, los tres en
el MISMO PeriodoNomina.
"""
from decimal import Decimal, ROUND_HALF_UP

from django.test import override_settings
from django_tenants.utils import schema_context
from rest_framework import status

from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.empleados.models import Contrato, Devengo, Empleado, PeriodoNomina, ResolucionDIAN
from apps.tenant.empresa.models import Empresa


@override_settings(ALLOWED_HOSTS=['*'])
class TestLiquidacionIndividualPorPeriodo(TenantAPITestCase):

    URL_PERIODOS = '/api/v1/empleados/periodos-nomina/'
    URL_DEVENGOS = '/api/v1/empleados/devengos/'

    def setUp(self):
        super().setUp()
        with schema_context(self.tenant.schema_name):
            self.empresa = Empresa.objects.first()
            ResolucionDIAN.objects.create(
                empresa=self.empresa, numero_resolucion='18760000002', prefijo='NE',
                rango_desde=1, rango_hasta=100000,
                fecha_resolucion='2024-01-01', fecha_inicio='2024-01-01',
                fecha_fin='2030-12-31', vigente=True,
            )

        self.periodo_uuid = self._crear_periodo()

    def _crear_periodo(self, periodo_mes='2024-06'):
        res = self.tpost(self.URL_PERIODOS, data={
            'periodo_mes': periodo_mes,
            'fecha_inicio': f'{periodo_mes}-01',
            'fecha_fin': f'{periodo_mes}-15',
            'fecha_pago': f'{periodo_mes}-15',
        })
        self.assertJSONResponse(res, status.HTTP_201_CREATED)
        return res.data['uuid']

    def _crear_empleado_con_contrato(self, doc, nombre, salario='2000000.00'):
        with schema_context(self.tenant.schema_name):
            empleado = Empleado.objects.create(
                empresa=self.empresa, tipo_documento='CC', numero_documento=doc,
                primer_nombre=nombre, primer_apellido='Test', email=f'{doc}@example.com',
                eps='EPS001', afp='AFP001', arl='ARL001', estado='ACTIVO', fecha_ingreso='2020-01-01',
            )
            contrato = Contrato.objects.create(
                empresa=self.empresa, empleado=empleado, tipo='INDEF',
                fecha_inicio='2020-01-01', salario_mensual=Decimal(salario),
                estado='ACTIVO', activo=True,
            )
            return empleado.id, empleado.uuid, contrato.id

    def _liquidar(self, empleado_id, contrato_id, dias, fecha_pago='2024-06-15'):
        # periodo_mes es requerido de facto: DRF genera un UniqueTogetherValidator
        # desde el UniqueConstraint del modelo (empleado, periodo_mes, fecha_pago),
        # lo que fuerza esos 3 campos aunque el serializer los declare
        # required=False -- el formulario real siempre lo envia via un input
        # oculto derivado de fecha_inicio (devengo_editor.js).
        return self.tpost(self.URL_DEVENGOS, data={
            'empleado': empleado_id,
            'contrato': contrato_id,
            'periodo': self.periodo_uuid,
            'periodo_mes': fecha_pago[:7],
            'dias_laborados': str(dias),
            'fecha_pago': fecha_pago,
        })

    # -- Escenario obligatorio del PROMPT MAESTRO (FASE 7) -------------------

    def test_juan_8_pedro_15_maria_5_mismo_periodo(self):
        juan_id, juan_uuid, juan_contrato = self._crear_empleado_con_contrato('800111001', 'Juan')
        pedro_id, pedro_uuid, pedro_contrato = self._crear_empleado_con_contrato('800111002', 'Pedro')
        maria_id, maria_uuid, maria_contrato = self._crear_empleado_con_contrato('800111003', 'Maria')

        res_juan = self._liquidar(juan_id, juan_contrato, 8)
        self.assertJSONResponse(res_juan, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(res_juan.data['dias_laborados']), Decimal('8.00'))

        res_pedro = self._liquidar(pedro_id, pedro_contrato, 15)
        self.assertJSONResponse(res_pedro, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(res_pedro.data['dias_laborados']), Decimal('15.00'))

        res_maria = self._liquidar(maria_id, maria_contrato, 5)
        self.assertJSONResponse(res_maria, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(res_maria.data['dias_laborados']), Decimal('5.00'))

        # Los tres devengos pertenecen al MISMO periodo, con montos DISTINTOS
        # (proporcionales a sus propios dias, nunca forzados a coincidir).
        with schema_context(self.tenant.schema_name):
            periodo = PeriodoNomina.objects.get(uuid=self.periodo_uuid)
            devengos = {d.dias_laborados: d for d in Devengo.objects.filter(periodo=periodo, anulado=False)}
            self.assertEqual(len(devengos), 3)

            # Proporcional a salario_mensual * (dias/30) (base comercial,
            # NominaCalculationService.calcular_liquidacion()), NUNCA relativo
            # a los dias de otro empleado del mismo periodo.
            def _esperado(dias):
                return (Decimal('2000000.00') * Decimal(dias) / Decimal('30')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            self.assertEqual(devengos[Decimal('8.00')].salario_base, _esperado(8))
            self.assertEqual(devengos[Decimal('15.00')].salario_base, _esperado(15))
            self.assertEqual(devengos[Decimal('5.00')].salario_base, _esperado(5))
            self.assertLess(devengos[Decimal('5.00')].salario_base, devengos[Decimal('8.00')].salario_base)
            self.assertLess(devengos[Decimal('8.00')].salario_base, devengos[Decimal('15.00')].salario_base)

        # Los 3 ya NO deben aparecer en pendientes; los 3 deben aparecer en liquidados.
        res_pend = self.tget(f'{self.URL_PERIODOS}{self.periodo_uuid}/empleados-pendientes/')
        self.assertJSONResponse(res_pend, status.HTTP_200_OK)
        self.assertEqual(len(res_pend.data), 0)

        res_liq = self.tget(f'{self.URL_PERIODOS}{self.periodo_uuid}/empleados-liquidados/')
        self.assertJSONResponse(res_liq, status.HTTP_200_OK)
        self.assertEqual(len(res_liq.data), 3)
        dias_liquidados = sorted(Decimal(d['dias_laborados']) for d in res_liq.data)
        self.assertEqual(dias_liquidados, [Decimal('5.00'), Decimal('8.00'), Decimal('15.00')])

    # -- Regresion: UUID (no solo PK entero) debe funcionar para 'empleado' --
    #
    # mision auditoria "sincronizacion backend<->frontend" (2026-09-10):
    # encontrado auditando el contrato JSON real (POST directo, no via
    # pytest) -- service_validar_duplicado() asumia 'empleado' siempre como
    # PK entero y crasheaba (ValueError interno filtrado al usuario) si se
    # enviaba UUID, la forma preferida segun AGENTS.md Sec.14 y lo que
    # UUIDOrPKRelatedField acepta explicitamente. Los demas tests de este
    # archivo usan PK entero (asi coincide con como devengo_editor.js arma
    # el payload hoy) -- este prueba especificamente la otra mitad del
    # contrato del campo para que no vuelva a pasar desapercibido.
    def test_liquidar_con_uuid_de_empleado_y_contrato_no_solo_pk(self):
        with schema_context(self.tenant.schema_name):
            empresa = Empresa.objects.first()
            empleado = Empleado.objects.create(
                empresa=empresa, tipo_documento='CC', numero_documento='800111099',
                primer_nombre='ConUuid', primer_apellido='Test', email='conuuid@example.com',
                eps='EPS001', afp='AFP001', arl='ARL001', estado='ACTIVO', fecha_ingreso='2020-01-01',
            )
            contrato = Contrato.objects.create(
                empresa=empresa, empleado=empleado, tipo='INDEF',
                fecha_inicio='2020-01-01', salario_mensual=Decimal('2000000.00'),
                estado='ACTIVO', activo=True,
            )
            empleado_uuid, contrato_uuid = str(empleado.uuid), str(contrato.uuid)

        res = self.tpost(self.URL_DEVENGOS, data={
            'empleado': empleado_uuid,
            'contrato': contrato_uuid,
            'periodo': self.periodo_uuid,
            'periodo_mes': '2024-06',
            'dias_laborados': '10',
            'fecha_pago': '2024-06-15',
        })
        self.assertJSONResponse(res, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(res.data['dias_laborados']), Decimal('10.00'))

    # -- Pendientes refleja el estado real backend-driven --------------------

    def test_pendientes_antes_de_liquidar(self):
        juan_id, juan_uuid, juan_contrato = self._crear_empleado_con_contrato('800111004', 'Carlos')
        res = self.tget(f'{self.URL_PERIODOS}{self.periodo_uuid}/empleados-pendientes/')
        self.assertJSONResponse(res, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['uuid'], str(juan_uuid))
        self.assertNotIn('id', res.data[0])  # no exponer PK tecnico

    # -- Duplicado en el mismo periodo bloqueado ------------------------------

    def test_no_permite_doble_liquidacion_mismo_empleado_mismo_periodo(self):
        emp_id, emp_uuid, contrato_id = self._crear_empleado_con_contrato('800111005', 'Duplicado')
        res1 = self._liquidar(emp_id, contrato_id, 10)
        self.assertJSONResponse(res1, status.HTTP_201_CREATED)

        res2 = self._liquidar(emp_id, contrato_id, 12, fecha_pago='2024-06-16')
        self.assertJSONResponse(res2, status.HTTP_400_BAD_REQUEST)
        self.assertIn('periodo', res2.data)

    # -- Periodo en estado no editable bloquea nueva liquidacion --------------

    def test_no_permite_liquidar_en_periodo_cerrado(self):
        emp_id, emp_uuid, contrato_id = self._crear_empleado_con_contrato('800111006', 'Cerrado')

        with schema_context(self.tenant.schema_name):
            periodo = PeriodoNomina.objects.get(uuid=self.periodo_uuid)
            periodo.estado = 'CERRADO'
            periodo.save(update_fields=['estado'])

        res = self._liquidar(emp_id, contrato_id, 10)
        self.assertJSONResponse(res, status.HTTP_400_BAD_REQUEST)
        self.assertIn('periodo', res.data)

    # NOTA: no se prueba "periodo de otra empresa" con una segunda fila Empresa
    # en el mismo schema -- Empresa es SINGLETON por schema de tenant
    # (constraint `singleton_key`, ver apps/tenant/empresa/models.py), asi que
    # ese escenario es arquitectonicamente imposible dentro de un mismo schema.
    # El aislamiento cross-tenant real (DSV via empresa_id en el queryset de
    # UUIDOrPKRelatedField) ya esta cubierto por el patron tenant1/tenant2
    # existente en test_scope_isolation_f14.py -- no se duplica aqui.
