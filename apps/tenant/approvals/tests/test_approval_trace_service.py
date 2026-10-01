"""
Fase 6 de PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md (#16):
ApprovalTraceService -- servicio de solo lectura, sin API/UI todavia.
"""

from datetime import date, timedelta
from decimal import Decimal

from apps.tenant.approvals.models import SolicitudAprobacion
from apps.tenant.approvals.services.trace_service import ApprovalTraceService
from apps.tenant.compras.models import PlantillaOrdenCompra
from apps.tenant.compras.requisiciones.services.business_service import (
    RequisicionCompraBusinessService,
)
from apps.tenant.compras.services.business_service import OrdenCompraBusinessService
from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from apps.tenant.proyectos.models import Proyecto
from tests.tenant.base_test import SintelTenantTestCase


class ApprovalTraceServiceTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Trace Test",
            nit="900800200",
            direccion="Calle Trace",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede Trace")
        self.solicitante = TenantProfile.objects.get_or_create(
            user=self.user,
            empresa=self.empresa,
            defaults={"rol": "ADMIN", "alcance": "EMPRESA", "cargo": "Analista"},
        )[0]
        self.cotizacion = Cotizacion.objects.create(
            empresa=self.empresa,
            numero_cotizacion="COT-TRACE-1",
            fecha_vencimiento=date.today() + timedelta(days=30),
            total_con_impuestos=Decimal("100000.00"),
        )
        self.proyecto = Proyecto.objects.create(empresa=self.empresa, nombre="Proyecto Trace")
        self.requisicion = self._crear_y_enviar_requisicion()

    def _crear_y_enviar_requisicion(self):
        ok, req, code = RequisicionCompraBusinessService.crear_requisicion(
            {
                "fecha_necesidad": date.today() + timedelta(days=5),
                "tipo": "BIEN",
                "prioridad": "MEDIA",
                "justificacion": "Requisicion de prueba para trazabilidad",
                "observaciones": "",
                "proyecto": self.proyecto,
                "responsable_aprobacion": None,
                "cotizacion": self.cotizacion,
            },
            [
                {
                    "tipo_item": "BIEN",
                    "descripcion": "Item trace",
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
        RequisicionCompraBusinessService.enviar_a_aprobacion(
            str(req.uuid), self.empresa.id, usuario=self.solicitante
        )
        return req

    def _solicitud(self):
        return SolicitudAprobacion.objects.get(
            objeto_uuid=self.requisicion.uuid,
            tipo_documento=SolicitudAprobacion.TipoDocumento.REQUISICION,
        )

    def test_construir_trazabilidad_incluye_requisicion_cotizacion_y_proyecto(self):
        dto = ApprovalTraceService.construir_trazabilidad(self._solicitud(), self.empresa.id)

        self.assertEqual(dto["request"]["tipo_documento"], "REQUISICION")
        self.assertEqual(dto["request"]["estado"], "PENDIENTE")
        self.assertEqual(dto["origin"]["uuid"], str(self.requisicion.uuid))

        tipos_nodos = {n["tipo"] for n in dto["nodes"]}
        self.assertEqual(tipos_nodos, {"REQUISICION", "COTIZACION", "PROYECTO"})

        tipos_relaciones = {r["tipo"] for r in dto["relations"]}
        self.assertEqual(tipos_relaciones, {"ORIGEN", "CONTEXTO"})

        self.assertEqual(dto["financial_summary"]["valor_requisicion"], "10000.00")
        self.assertEqual(dto["financial_summary"]["saldo_requisicion"], "10000.00")
        self.assertEqual(dto["financial_summary"]["valor_cotizacion"], "100000.00")
        self.assertEqual(dto["alerts"], [])

    def test_construir_trazabilidad_incluye_timeline_de_ambas_fuentes_ordenado(self):
        dto = ApprovalTraceService.construir_trazabilidad(self._solicitud(), self.empresa.id)
        fuentes = {e["fuente"] for e in dto["timeline"]}
        self.assertEqual(fuentes, {"SOLICITUD", "REQUISICION"})
        self.assertEqual(len(dto["timeline"]), 2)
        fechas = [e["fecha"] for e in dto["timeline"]]
        self.assertEqual(fechas, sorted(fechas))
        # enviar_a_aprobacion() transiciona la Requisicion (BORRADOR ->
        # PENDIENTE_APROBACION) ANTES de crear la SolicitudAprobacion --
        # dentro de la misma transaccion, ese orden real debe reflejarse.
        self.assertEqual(dto["timeline"][0]["fuente"], "REQUISICION")
        self.assertEqual(dto["timeline"][0]["estado_nuevo"], "PENDIENTE_APROBACION")
        self.assertEqual(dto["timeline"][1]["fuente"], "SOLICITUD")
        self.assertEqual(dto["timeline"][1]["evento"], "CREADA")

    def test_construir_trazabilidad_incluye_ordenes_de_compra_generadas(self):
        proveedor = Proveedor.objects.create(
            empresa=self.empresa,
            razon_social="Proveedor Trace",
            tipo_documento="NIT",
            numero_documento="900800300",
            activo=True,
        )
        plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa,
            nombre="Plantilla Trace",
            prefijo="TRACE",
            rango_desde=1,
            rango_hasta=1000,
            consecutivo_actual=1,
            vigente=True,
        )
        RequisicionCompraBusinessService.aprobar_requisicion(
            str(self.requisicion.uuid), self.empresa.id, usuario=self.solicitante
        )
        ok, orden, code = OrdenCompraBusinessService.crear_orden_compra(
            {
                "plantilla": str(plantilla.uuid),
                "proveedor": str(proveedor.uuid),
                "fecha": date.today(),
                "requisiciones": [str(self.requisicion.uuid)],
            },
            [
                {
                    "descripcion": "Item OC trace",
                    "cantidad": "1",
                    "valor_unitario": "10000",
                    "porcentaje_iva": "0",
                }
            ],
            self.empresa,
            self.sede,
        )
        self.assertTrue(ok, orden)

        dto = ApprovalTraceService.construir_trazabilidad(self._solicitud(), self.empresa.id)
        nodos_oc = [n for n in dto["nodes"] if n["tipo"] == "ORDEN_COMPRA"]
        self.assertEqual(len(nodos_oc), 1)
        self.assertEqual(nodos_oc[0]["uuid"], str(orden.uuid))
        self.assertEqual(dto["financial_summary"]["saldo_requisicion"], "0.00")

    def test_construir_trazabilidad_alerta_si_ordenes_exceden_saldo(self):
        """Caso sintetico -- fuerza un OrdenCompraRequisicion con monto_asignado
        mayor al saldo real (bypass del Service Layer, solo para probar que
        el DTO refleja lo que haya en BD, sin recalcular de mas)."""
        from apps.tenant.compras.models import OrdenCompra, OrdenCompraRequisicion

        proveedor = Proveedor.objects.create(
            empresa=self.empresa,
            razon_social="Proveedor Trace 2",
            tipo_documento="NIT",
            numero_documento="900800400",
            activo=True,
        )
        plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa,
            nombre="Plantilla Trace 2",
            prefijo="TRACE2",
            rango_desde=1,
            rango_hasta=1000,
            consecutivo_actual=1,
            vigente=True,
        )
        orden = OrdenCompra.objects.create(
            empresa=self.empresa,
            sede=self.sede,
            plantilla=plantilla,
            proveedor=proveedor,
            numero_documento="TRACE2-1",
            consecutivo=1,
            fecha=date.today(),
            total=Decimal("99999.00"),
        )
        OrdenCompraRequisicion.objects.create(
            empresa=self.empresa,
            orden_compra=orden,
            requisicion=self.requisicion,
            monto_asignado=Decimal("99999.00"),
        )

        dto = ApprovalTraceService.construir_trazabilidad(self._solicitud(), self.empresa.id)
        self.assertTrue(any(a["nivel"] == "ROJO" for a in dto["alerts"]))

    def test_construir_trazabilidad_tipo_documento_no_soportado_retorna_dto_vacio(self):
        solicitud = self._solicitud()
        solicitud.tipo_documento = "TIPO_INEXISTENTE"
        dto = ApprovalTraceService.construir_trazabilidad(solicitud, self.empresa.id)
        self.assertIsNone(dto["origin"])
        self.assertEqual(dto["nodes"], [])
