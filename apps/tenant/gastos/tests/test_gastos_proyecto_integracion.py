"""
GASTOS_PROYECTOS_01 - Tests de integracion Gastos <-> Proyectos.

Cubre (ver docs/remediation/GASTOS_PROYECTOS_IMPLEMENTATION_STATUS.md):
- Crear gasto sin proyecto / con proyecto (opcional, DSV).
- Editar gasto: asociar, mover entre proyectos, desasociar.
- Anular / desactivar un gasto asociado: sale del costo del proyecto.
- Recalculo automatico via calcular_indicadores_financieros() (sin Signals).
"""
import datetime
from decimal import Decimal

from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.empresa.models import Empresa
from apps.tenant.gastos.models import DocumentoSoporte, ResolucionDIAN
from apps.tenant.gastos.services.business_service import GastoBusinessService
from apps.tenant.proveedores.models import Proveedor
from apps.tenant.proyectos.models import Proyecto


class GastosProyectoIntegracionTests(TenantAPITestCase):

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first()

        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa,
            numero_documento='900111222',
            razon_social='Proveedor Test SAS',
            tipo_persona='JURIDICA',
            tipo_documento='NIT',
            regimen_tributario='ORDINARIO',
            activo=True,
        )
        self.resolucion = ResolucionDIAN.objects.create(
            empresa=self.empresa,
            numero_resolucion='RES-001',
            prefijo='DS',
            rango_desde=1,
            rango_hasta=1000,
            fecha_resolucion=datetime.date(2026, 1, 1),
            fecha_inicio=datetime.date(2026, 1, 1),
            fecha_fin=datetime.date(2027, 1, 1),
        )
        self.proyecto_a = Proyecto.objects.create(
            empresa=self.empresa,
            nombre='Proyecto A',
            codigo='PRJ-2026-A001',
            tipo_servicio='PROYECTO_INTEGRAL',
            valor_contrato_proyectado=Decimal('10000000.00'),
        )
        self.proyecto_b = Proyecto.objects.create(
            empresa=self.empresa,
            nombre='Proyecto B',
            codigo='PRJ-2026-B001',
            tipo_servicio='PROYECTO_INTEGRAL',
            valor_contrato_proyectado=Decimal('5000000.00'),
        )

    def _crear_gasto(self, subtotal='1000000.00', proyecto_uuid=None):
        data = {
            'resolucion_dian': self.resolucion.id,
            'proveedor': self.proveedor.id,
            'fecha': datetime.date(2026, 6, 1),
            'subtotal': subtotal,
            'numero_documento_proveedor': f'FAC-{DocumentoSoporte.objects.count() + 1}',
        }
        if proyecto_uuid is not None:
            data['proyecto_uuid'] = str(proyecto_uuid)
        success, result, status_code = GastoBusinessService.procesar_gasto(self.empresa, data)
        return success, result, status_code

    # ------------------------------------------------------------------
    # Creacion: proyecto opcional
    # ------------------------------------------------------------------
    def test_crear_gasto_sin_proyecto(self):
        success, documento, status_code = self._crear_gasto()
        self.assertTrue(success, documento)
        self.assertEqual(status_code, 201)
        self.assertIsNone(documento.proyecto_uuid)

    def test_crear_gasto_con_proyecto_valido_recalcula(self):
        success, documento, status_code = self._crear_gasto(
            subtotal='1000000.00', proyecto_uuid=self.proyecto_a.uuid
        )
        self.assertTrue(success, documento)
        self.assertEqual(documento.proyecto_uuid, self.proyecto_a.uuid)

        self.proyecto_a.refresh_from_db()
        self.assertEqual(self.proyecto_a.costo_gastos_real, Decimal('1000000.00'))

    def test_crear_gasto_con_proyecto_uuid_inexistente_rechazado(self):
        import uuid as uuid_module
        count_antes = DocumentoSoporte.objects.count()

        success, result, status_code = self._crear_gasto(proyecto_uuid=uuid_module.uuid4())

        self.assertFalse(success)
        self.assertEqual(status_code, 400)
        # Atomicidad: no debe haber creado el documento
        self.assertEqual(DocumentoSoporte.objects.count(), count_antes)

    def test_gasto_cost_amount_ssot_es_subtotal_no_total(self):
        """
        GASTO_COST_AMOUNT_SSoT = subtotal (confirmado en ExtractorGastos).
        Con retenciones > 0, total < subtotal -- el costo del proyecto debe
        reflejar subtotal, nunca el total neto post-retencion.
        """
        from apps.tenant.contabilidad.services import retenciones_service as _rs

        original = _rs.RetencionesService.obtener_retenciones_desde_tercero
        try:
            _rs.RetencionesService.obtener_retenciones_desde_tercero = staticmethod(
                lambda **kwargs: {
                    'retefuente_porcentaje': Decimal('0.11'),
                    'reteica_porcentaje': Decimal('0.00'),
                    'reteiva_porcentaje': Decimal('0.00'),
                }
            )
            success, documento, _ = self._crear_gasto(
                subtotal='1000000.00', proyecto_uuid=self.proyecto_a.uuid
            )
            self.assertTrue(success, documento)
            self.assertLess(documento.total, documento.subtotal)

            self.proyecto_a.refresh_from_db()
            self.assertEqual(self.proyecto_a.costo_gastos_real, documento.subtotal)
            self.assertNotEqual(self.proyecto_a.costo_gastos_real, documento.total)
        finally:
            _rs.RetencionesService.obtener_retenciones_desde_tercero = original

    # ------------------------------------------------------------------
    # Edicion: asociar / mover / desasociar (via PATCH -- perform_update)
    # ------------------------------------------------------------------
    def test_editar_gasto_asociar_proyecto_posteriormente(self):
        _, documento, _ = self._crear_gasto(subtotal='500000.00')
        self.assertIsNone(documento.proyecto_uuid)

        resp = self.tpatch(
            f'/api/v1/gastos/{documento.uuid}/',
            data={'proyecto_uuid': str(self.proyecto_a.uuid)},
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        self.proyecto_a.refresh_from_db()
        self.assertEqual(self.proyecto_a.costo_gastos_real, Decimal('500000.00'))

    def test_editar_gasto_mover_de_proyecto_a_a_b(self):
        _, documento, _ = self._crear_gasto(subtotal='700000.00', proyecto_uuid=self.proyecto_a.uuid)
        self.proyecto_a.refresh_from_db()
        self.assertEqual(self.proyecto_a.costo_gastos_real, Decimal('700000.00'))

        resp = self.tpatch(
            f'/api/v1/gastos/{documento.uuid}/',
            data={'proyecto_uuid': str(self.proyecto_b.uuid)},
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        self.proyecto_a.refresh_from_db()
        self.proyecto_b.refresh_from_db()
        self.assertEqual(self.proyecto_a.costo_gastos_real, Decimal('0.00'))
        self.assertEqual(self.proyecto_b.costo_gastos_real, Decimal('700000.00'))

    def test_editar_gasto_desasociar_proyecto(self):
        _, documento, _ = self._crear_gasto(subtotal='300000.00', proyecto_uuid=self.proyecto_a.uuid)

        resp = self.tpatch(
            f'/api/v1/gastos/{documento.uuid}/',
            data={'proyecto_uuid': None},
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        self.proyecto_a.refresh_from_db()
        documento.refresh_from_db()
        self.assertIsNone(documento.proyecto_uuid)
        self.assertEqual(self.proyecto_a.costo_gastos_real, Decimal('0.00'))

    def test_editar_gasto_proyecto_uuid_inexistente_rechazado(self):
        import uuid as uuid_module
        _, documento, _ = self._crear_gasto(subtotal='100000.00')

        resp = self.tpatch(
            f'/api/v1/gastos/{documento.uuid}/',
            data={'proyecto_uuid': str(uuid_module.uuid4())},
        )
        self.assertEqual(resp.status_code, 400, resp.content)

    # NOTA (FASE-18/Escenario 5 del plan): `subtotal` es read_only en
    # DocumentoSoporteDetailSerializer (dato fiscal, no editable via el PATCH
    # generico) -- verificado en este mismo ciclo de tests (un PATCH con
    # `subtotal` es silenciosamente ignorado por DRF). El recalculo SI
    # dispara correctamente ante cualquier perform_update() (ver
    # test_editar_gasto_asociar_proyecto_posteriormente), pero "editar el
    # importe de un gasto ya asociado" no es un camino alcanzable hoy via
    # API -- no se agrega un test para un escenario que el sistema no
    # permite, documentado en GASTOS_PROYECTOS_IMPLEMENTATION_STATUS.md.

    # ------------------------------------------------------------------
    # Anular / Desactivar: sale del costo
    # ------------------------------------------------------------------
    def test_anular_gasto_asociado_sale_del_costo(self):
        _, documento, _ = self._crear_gasto(subtotal='800000.00', proyecto_uuid=self.proyecto_a.uuid)
        self.proyecto_a.refresh_from_db()
        self.assertEqual(self.proyecto_a.costo_gastos_real, Decimal('800000.00'))

        success, result, status_code = GastoBusinessService.anular_gasto(
            documento.id, motivo='Prueba de anulacion', usuario=None, empresa_id=self.empresa.id
        )
        self.assertTrue(success, result)

        self.proyecto_a.refresh_from_db()
        self.assertEqual(self.proyecto_a.costo_gastos_real, Decimal('0.00'))

    def test_desactivar_gasto_asociado_sale_del_costo(self):
        _, documento, _ = self._crear_gasto(subtotal='250000.00', proyecto_uuid=self.proyecto_a.uuid)
        self.proyecto_a.refresh_from_db()
        self.assertEqual(self.proyecto_a.costo_gastos_real, Decimal('250000.00'))

        GastoBusinessService.desactivar_gasto(documento.id, empresa_id=self.empresa.id)

        self.proyecto_a.refresh_from_db()
        self.assertEqual(self.proyecto_a.costo_gastos_real, Decimal('0.00'))
