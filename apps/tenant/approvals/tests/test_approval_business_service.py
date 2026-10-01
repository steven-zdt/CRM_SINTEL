"""
PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md Fases 1-4: motor generico de
Solicitudes de Aprobacion, sin enganche todavia al flujo real de
Requisiciones (RequisicionCompraBusinessService.enviar_a_aprobacion()
creando la solicitud es Fase 5, DEFERRED) -- estos tests llaman
ApprovalBusinessService directo, simulando lo que Fase 5 hara.
"""

from datetime import date, timedelta

from apps.tenant.approvals.models import SolicitudAprobacion, SolicitudAprobacionHistorial
from apps.tenant.approvals.services.business_service import ApprovalBusinessService
from apps.tenant.compras.requisiciones.services.business_service import (
    RequisicionCompraBusinessService,
)
from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class ApprovalBusinessServiceTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Approvals Test",
            nit="900800100",
            direccion="Calle Approvals",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede Approvals")
        self.solicitante = TenantProfile.objects.get_or_create(
            user=self.user,
            empresa=self.empresa,
            defaults={"rol": "ADMIN", "alcance": "EMPRESA", "cargo": "Analista"},
        )[0]
        self.cotizacion = Cotizacion.objects.create(
            empresa=self.empresa,
            numero_cotizacion="COT-APPROVALS-1",
            fecha_vencimiento=date.today() + timedelta(days=30),
        )
        self.requisicion = self._crear_requisicion_borrador()

    def _crear_requisicion_borrador(self):
        ok, req, code = RequisicionCompraBusinessService.crear_requisicion(
            {
                "fecha_necesidad": date.today() + timedelta(days=5),
                "tipo": "BIEN",
                "prioridad": "MEDIA",
                "justificacion": "Requisicion de prueba para el motor de aprobaciones",
                "observaciones": "",
                "proyecto": None,
                "responsable_aprobacion": None,
                "cotizacion": self.cotizacion,
            },
            [
                {
                    "tipo_item": "BIEN",
                    "descripcion": "Item aprobaciones",
                    "cantidad_solicitada": "1",
                    "valor_unitario_estimado": "10000",
                    "porcentaje_iva": "0",
                    "unidad_medida": "UND",
                }
            ],
            self.empresa,
            self.sede,
            self.solicitante,
        )
        self.assertTrue(ok, req)
        return req

    def _enviar_a_aprobacion(self):
        ok, req, code = RequisicionCompraBusinessService.enviar_a_aprobacion(
            str(self.requisicion.uuid), self.empresa.id
        )
        self.assertTrue(ok, req)
        return req

    # ── crear_solicitud ──────────────────────────────────────────────────

    def test_crear_solicitud_requisicion_valida(self):
        # NOTA (Fase 5, implementada mas tarde en la misma sesion que este
        # test): `RequisicionCompraBusinessService.enviar_a_aprobacion()`
        # ahora crea la SolicitudAprobacion como side-effect real -- llamarlo
        # aqui antes de `crear_solicitud()` ya no prueba el camino de
        # creacion fresca (201), sino el de idempotencia/reuso (200), que ya
        # cubre `test_crear_solicitud_es_idempotente_no_duplica_pendiente`
        # mas abajo. Se retira esa llamada para que este test siga probando
        # lo que su nombre promete: crear_solicitud() sobre una Requisicion
        # sin ninguna SolicitudAprobacion previa.
        ok, solicitud, code = ApprovalBusinessService.crear_solicitud(
            tipo_documento=SolicitudAprobacion.TipoDocumento.REQUISICION,
            objeto_uuid=self.requisicion.uuid,
            empresa_id=self.empresa.id,
            solicitante=self.solicitante,
            snapshot={"valor": "10000"},
        )
        self.assertTrue(ok, solicitud)
        self.assertEqual(code, 201)
        self.assertEqual(solicitud.estado, SolicitudAprobacion.Estado.PENDIENTE)
        self.assertEqual(
            SolicitudAprobacionHistorial.objects.filter(
                solicitud=solicitud, evento="CREADA"
            ).count(),
            1,
        )

    def test_crear_solicitud_documento_inexistente_es_rechazada(self):
        ok, result, code = ApprovalBusinessService.crear_solicitud(
            tipo_documento=SolicitudAprobacion.TipoDocumento.REQUISICION,
            objeto_uuid="00000000-0000-0000-0000-000000000000",
            empresa_id=self.empresa.id,
            solicitante=self.solicitante,
            snapshot={},
        )
        self.assertFalse(ok)
        self.assertEqual(code, 400)

    def test_crear_solicitud_tipo_documento_invalido_es_rechazada(self):
        ok, result, code = ApprovalBusinessService.crear_solicitud(
            tipo_documento="TIPO_NO_SOPORTADO",
            objeto_uuid=self.requisicion.uuid,
            empresa_id=self.empresa.id,
            solicitante=self.solicitante,
            snapshot={},
        )
        self.assertFalse(ok)
        self.assertEqual(code, 400)

    def test_crear_solicitud_es_idempotente_no_duplica_pendiente(self):
        self._enviar_a_aprobacion()
        ok1, sol1, _ = ApprovalBusinessService.crear_solicitud(
            tipo_documento=SolicitudAprobacion.TipoDocumento.REQUISICION,
            objeto_uuid=self.requisicion.uuid,
            empresa_id=self.empresa.id,
            solicitante=self.solicitante,
            snapshot={},
        )
        ok2, sol2, _ = ApprovalBusinessService.crear_solicitud(
            tipo_documento=SolicitudAprobacion.TipoDocumento.REQUISICION,
            objeto_uuid=self.requisicion.uuid,
            empresa_id=self.empresa.id,
            solicitante=self.solicitante,
            snapshot={},
        )
        self.assertTrue(ok1)
        self.assertTrue(ok2)
        self.assertEqual(sol1.id, sol2.id)
        self.assertEqual(
            SolicitudAprobacion.objects.filter(objeto_uuid=self.requisicion.uuid).count(), 1
        )

    def test_crear_solicitud_empresa_incorrecta_no_ve_el_documento(self):
        """DSV anti-IDOR: un empresa_id que no coincide con la fila real
        (Empresa es singleton por tenant schema, ver nota en otros archivos
        de esta mision) no debe poder crear una solicitud sobre ella."""
        ok, result, code = ApprovalBusinessService.crear_solicitud(
            tipo_documento=SolicitudAprobacion.TipoDocumento.REQUISICION,
            objeto_uuid=self.requisicion.uuid,
            empresa_id=self.empresa.id + 999999,
            solicitante=self.solicitante,
            snapshot={},
        )
        self.assertFalse(ok)
        self.assertEqual(code, 400)

    # ── aprobar / rechazar ───────────────────────────────────────────────

    def _crear_pendiente(self):
        self._enviar_a_aprobacion()
        ok, solicitud, _ = ApprovalBusinessService.crear_solicitud(
            tipo_documento=SolicitudAprobacion.TipoDocumento.REQUISICION,
            objeto_uuid=self.requisicion.uuid,
            empresa_id=self.empresa.id,
            solicitante=self.solicitante,
        )
        self.assertTrue(ok, solicitud)
        return solicitud

    def test_aprobar_delega_al_business_service_del_dominio(self):
        """#26 del plan: nunca `objeto.estado = 'APROBADA'` directo -- la
        aprobacion real de la Requisicion debe pasar por
        RequisicionCompraBusinessService.aprobar_requisicion()."""
        solicitud = self._crear_pendiente()
        ok, solicitud, code = ApprovalBusinessService.aprobar(
            str(solicitud.uuid),
            self.empresa.id,
            self.solicitante,
        )
        self.assertTrue(ok, solicitud)
        self.assertEqual(solicitud.estado, SolicitudAprobacion.Estado.APROBADA)
        self.requisicion.refresh_from_db()
        self.assertEqual(self.requisicion.estado, "APROBADA")
        self.assertEqual(
            SolicitudAprobacionHistorial.objects.filter(
                solicitud=solicitud, evento="APROBADA"
            ).count(),
            1,
        )

    def test_aprobar_dos_veces_es_idempotente(self):
        """#28 del plan: doble aprobacion (concurrencia o doble clic) nunca
        duplica efectos ni el historial de la segunda transicion real."""
        solicitud = self._crear_pendiente()
        ApprovalBusinessService.aprobar(str(solicitud.uuid), self.empresa.id, self.solicitante)
        ok2, solicitud2, code2 = ApprovalBusinessService.aprobar(
            str(solicitud.uuid), self.empresa.id, self.solicitante
        )
        self.assertTrue(ok2, solicitud2)
        self.assertEqual(solicitud2.estado, SolicitudAprobacion.Estado.APROBADA)
        self.assertEqual(
            SolicitudAprobacionHistorial.objects.filter(
                solicitud=solicitud, evento="APROBADA"
            ).count(),
            1,
        )

    def test_rechazar_sin_motivo_es_rechazado(self):
        solicitud = self._crear_pendiente()
        ok, result, code = ApprovalBusinessService.rechazar(
            str(solicitud.uuid), self.empresa.id, self.solicitante, ""
        )
        self.assertFalse(ok)
        self.assertEqual(code, 422)

    def test_rechazar_con_motivo_delega_al_business_service_del_dominio(self):
        solicitud = self._crear_pendiente()
        ok, solicitud, code = ApprovalBusinessService.rechazar(
            str(solicitud.uuid),
            self.empresa.id,
            self.solicitante,
            "No aplica para este periodo",
        )
        self.assertTrue(ok, solicitud)
        self.assertEqual(solicitud.estado, SolicitudAprobacion.Estado.RECHAZADA)
        self.assertEqual(solicitud.motivo_rechazo, "No aplica para este periodo")
        self.requisicion.refresh_from_db()
        self.assertEqual(self.requisicion.estado, "RECHAZADA")

    def test_aprobar_solicitud_inexistente_falla(self):
        ok, result, code = ApprovalBusinessService.aprobar(
            "00000000-0000-0000-0000-000000000000",
            self.empresa.id,
            self.solicitante,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 404)

    def test_aprobar_requisicion_directo_cierra_la_solicitud_sin_pasar_por_approvals(self):
        """El camino actual real (boton "Aprobar" de la UI de Requisiciones
        llama a RequisicionCompraBusinessService.aprobar_requisicion()
        directo, sin pasar por ApprovalBusinessService) debe dejar la
        SolicitudAprobacion correctamente cerrada de todos modos -- nunca
        debe quedar PENDIENTE para siempre solo porque no se uso el Centro
        de Aprobaciones (que todavia no existe, Fase 7/8)."""
        solicitud = self._crear_pendiente()
        ok, req, code = RequisicionCompraBusinessService.aprobar_requisicion(
            str(self.requisicion.uuid),
            self.empresa.id,
            usuario=self.solicitante,
        )
        self.assertTrue(ok, req)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, SolicitudAprobacion.Estado.APROBADA)
        self.assertEqual(
            SolicitudAprobacionHistorial.objects.filter(
                solicitud=solicitud, evento="APROBADA"
            ).count(),
            1,
        )

    def test_aprobar_bloqueado_si_el_documento_cambio_desde_el_envio(self):
        """#13 del plan: revalidar snapshot antes de aprobar. Si el
        documento cambio (simulado aqui forzando el snapshot guardado a un
        valor distinto -- en este codebase editar una requisicion
        PENDIENTE_APROBACION ya esta bloqueado por otra via, pero la
        revalidacion es defensa en profundidad, no la unica linea)."""
        solicitud = self._crear_pendiente()
        solicitud.snapshot_financiero["valor"] = "999999.00"
        solicitud.save(update_fields=["snapshot_financiero"])

        ok, result, code = ApprovalBusinessService.aprobar(
            str(solicitud.uuid), self.empresa.id, self.solicitante
        )
        self.assertFalse(ok)
        self.assertEqual(code, 409)
        self.assertEqual(result["error"], "documento_modificado")
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, SolicitudAprobacion.Estado.PENDIENTE)
        self.requisicion.refresh_from_db()
        self.assertEqual(self.requisicion.estado, "PENDIENTE_APROBACION")
