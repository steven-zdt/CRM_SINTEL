"""
Fase 12 (autorizada por el usuario 2026-09-25): RequisicionCompraSelector --
cobertura directa de queryset (sin pasar por la API), incluida en el plan
original #58 como categoria explicita ("selectors").
"""

from datetime import date, timedelta

from apps.tenant.compras.requisiciones.services.business_service import (
    RequisicionCompraBusinessService,
)
from apps.tenant.compras.requisiciones.services.selectors import RequisicionCompraSelector
from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class RequisicionCompraSelectorTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Req Selectors",
            nit="900700900",
            direccion="Calle Selectors",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede Selectors")
        self.solicitante = TenantProfile.objects.get_or_create(
            user=self.user,
            empresa=self.empresa,
            defaults={"rol": "ADMIN", "alcance": "EMPRESA", "cargo": "Analista"},
        )[0]
        # Cotizacion de origen -- OBLIGATORIA al crear desde 2026-09-26.
        self.cotizacion = Cotizacion.objects.create(
            empresa=self.empresa,
            numero_cotizacion="COT-REQ-SELECTORS",
            fecha_vencimiento=date.today() + timedelta(days=30),
        )

    def _crear(self, justificacion="Justificacion selector"):
        ok, req, code = RequisicionCompraBusinessService.crear_requisicion(
            {
                "fecha_necesidad": date.today() + timedelta(days=2),
                "tipo": "BIEN",
                "prioridad": "MEDIA",
                "justificacion": justificacion,
                "observaciones": "",
                "proyecto": None,
                "responsable_aprobacion": None,
                "cotizacion": self.cotizacion,
            },
            [
                {
                    "tipo_item": "BIEN",
                    "descripcion": "Item selector",
                    "cantidad_solicitada": "1",
                    "valor_unitario_estimado": "1000",
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

    def test_get_list_filtra_por_empresa(self):
        self._crear()
        qs = RequisicionCompraSelector.get_list(self.empresa.id)
        self.assertEqual(qs.count(), 1)

    def test_get_list_search_por_numero_documento(self):
        req = self._crear()
        qs = RequisicionCompraSelector.get_list(self.empresa.id, search=req.numero_documento)
        self.assertEqual(qs.count(), 1)
        qs_vacio = RequisicionCompraSelector.get_list(self.empresa.id, search="NO-EXISTE-XYZ")
        self.assertEqual(qs_vacio.count(), 0)

    def test_get_list_filtra_por_estado(self):
        req = self._crear()
        RequisicionCompraBusinessService.enviar_a_aprobacion(str(req.uuid), self.empresa.id)
        qs_pendientes = RequisicionCompraSelector.get_list(
            self.empresa.id, estado="PENDIENTE_APROBACION"
        )
        self.assertEqual(qs_pendientes.count(), 1)
        qs_borrador = RequisicionCompraSelector.get_list(self.empresa.id, estado="BORRADOR")
        self.assertEqual(qs_borrador.count(), 0)

    def test_get_detail_incluye_items(self):
        req = self._crear()
        detail = RequisicionCompraSelector.get_detail(self.empresa.id, str(req.uuid)).first()
        self.assertIsNotNone(detail)
        self.assertEqual(detail.items.count(), 1)

    def test_get_pending_approval_solo_pendientes(self):
        req1 = self._crear("Req 1")
        self._crear("Req 2")  # queda en BORRADOR
        RequisicionCompraBusinessService.enviar_a_aprobacion(str(req1.uuid), self.empresa.id)

        pendientes = RequisicionCompraSelector.get_pending_approval(self.empresa.id)
        self.assertEqual(pendientes.count(), 1)
        self.assertEqual(pendientes.first().uuid, req1.uuid)

    def test_get_available_for_purchase_solo_aprobadas_o_en_proceso(self):
        req = self._crear()
        self.assertEqual(
            RequisicionCompraSelector.get_available_for_purchase(self.empresa.id).count(), 0
        )

        RequisicionCompraBusinessService.enviar_a_aprobacion(str(req.uuid), self.empresa.id)
        RequisicionCompraBusinessService.aprobar_requisicion(str(req.uuid), self.empresa.id)

        disponibles = RequisicionCompraSelector.get_available_for_purchase(self.empresa.id)
        self.assertEqual(disponibles.count(), 1)

    def test_get_siguiente_consecutivo(self):
        self.assertEqual(RequisicionCompraSelector.get_siguiente_consecutivo(self.empresa.id), 1)
        self._crear()
        self.assertEqual(RequisicionCompraSelector.get_siguiente_consecutivo(self.empresa.id), 2)
