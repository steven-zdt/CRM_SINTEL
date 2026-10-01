"""
Fase 12 (autorizada por el usuario 2026-09-25): Service Layer de
RequisicionCompra -- numeracion, maquina de estados, DSV/multitenant, y
crear_orden_desde_requisicion (que delega en OrdenCompraBusinessService sin
duplicar su logica DSV, ver docs/compras/REQUISICIONES_DESIGN.md).
"""

from datetime import date, timedelta
from decimal import Decimal

from apps.tenant.compras.models import OrdenCompra, PlantillaOrdenCompra
from apps.tenant.compras.requisiciones.models import RequisicionCompra
from apps.tenant.compras.requisiciones.services.business_service import (
    RequisicionCompraBusinessService,
)
from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.facturas.models import Factura
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class RequisicionCompraServiceTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Req Service",
            nit="900700100",
            direccion="Calle Req 1",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede Req Service")
        self.solicitante = TenantProfile.objects.get_or_create(
            user=self.user,
            empresa=self.empresa,
            defaults={"rol": "ADMIN", "alcance": "EMPRESA", "cargo": "Analista de Compras"},
        )[0]
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa,
            razon_social="Proveedor Req Service",
            tipo_documento="NIT",
            numero_documento="900700200",
            activo=True,
        )
        self.plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa,
            nombre="Plantilla Req Service",
            prefijo="REQOC",
            rango_desde=1,
            rango_hasta=1000,
            consecutivo_actual=1,
            vigente=True,
        )
        # La Cotizacion de origen es OBLIGATORIA al crear una RequisicionCompra
        # desde 2026-09-26 (decision del usuario) -- ver
        # RequisicionCompraBusinessService.crear_requisicion().
        self.cotizacion = Cotizacion.objects.create(
            empresa=self.empresa,
            numero_cotizacion="COT-REQ-SERVICE-001",
            fecha_vencimiento="2026-12-31",
        )

    def _items_data(self, cantidad="3", valor_unitario="50000"):
        return [
            {
                "tipo_item": "BIEN",
                "descripcion": "Item de prueba servicio",
                "cantidad_solicitada": cantidad,
                "valor_unitario_estimado": valor_unitario,
                "porcentaje_iva": "0",
                "unidad_medida": "UND",
            }
        ]

    def _crear_requisicion(self, **overrides):
        data = {
            "fecha_necesidad": date.today() + timedelta(days=7),
            "tipo": "BIEN",
            "prioridad": "MEDIA",
            "justificacion": "Necesidad real de prueba",
            "observaciones": "",
            "proyecto": None,
            "responsable_aprobacion": None,
            "cotizacion": self.cotizacion,
        }
        data.update(overrides)
        ok, result, code = RequisicionCompraBusinessService.crear_requisicion(
            data,
            self._items_data(),
            self.empresa,
            self.sede,
            self.solicitante,
        )
        self.assertTrue(ok, result)
        self.assertEqual(code, 201)
        return result

    # ── Numeracion ────────────────────────────────────────────────────

    def test_numeracion_secuencial_por_empresa(self):
        r1 = self._crear_requisicion()
        r2 = self._crear_requisicion()
        self.assertEqual(r1.numero_documento, "REQ-000001")
        self.assertEqual(r2.numero_documento, "REQ-000002")
        self.assertEqual(r1.consecutivo, 1)
        self.assertEqual(r2.consecutivo, 2)

    # NOTA: no existe un test de "numeracion aislada entre 2 empresas del
    # mismo schema" -- Empresa es SINGLETON por tenant schema a nivel de BD
    # (UniqueConstraint 'unique_singleton_empresa_per_schema',
    # apps/tenant/empresa/models.py:168-171, "Solo se permite una empresa
    # por tenant"). El aislamiento real entre tenants es a nivel de SCHEMA
    # de PostgreSQL (django-tenants), no de multiples filas Empresa dentro
    # del mismo schema -- ya cubierto por la infraestructura compartida de
    # tenant, no algo que este submodulo deba re-probar por separado.

    # ── Creacion: validaciones ──────────────────────────────────────────

    def test_crear_sin_items_es_rechazado(self):
        ok, result, code = RequisicionCompraBusinessService.crear_requisicion(
            {
                "fecha_necesidad": date.today() + timedelta(days=1),
                "tipo": "BIEN",
                "prioridad": "MEDIA",
                "justificacion": "x",
                "observaciones": "",
                "proyecto": None,
                "responsable_aprobacion": None,
                "cotizacion": self.cotizacion,
            },
            [],
            self.empresa,
            self.sede,
            self.solicitante,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 400)

    def test_crear_sin_sede_es_rechazado(self):
        ok, result, code = RequisicionCompraBusinessService.crear_requisicion(
            {
                "fecha_necesidad": date.today() + timedelta(days=1),
                "tipo": "BIEN",
                "prioridad": "MEDIA",
                "justificacion": "x",
                "observaciones": "",
                "proyecto": None,
                "responsable_aprobacion": None,
                "cotizacion": self.cotizacion,
            },
            self._items_data(),
            self.empresa,
            None,
            self.solicitante,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 422)

    def test_crear_sin_cotizacion_es_rechazado(self):
        ok, result, code = RequisicionCompraBusinessService.crear_requisicion(
            {
                "fecha_necesidad": date.today() + timedelta(days=1),
                "tipo": "BIEN",
                "prioridad": "MEDIA",
                "justificacion": "x",
                "observaciones": "",
                "proyecto": None,
                "responsable_aprobacion": None,
            },
            self._items_data(),
            self.empresa,
            self.sede,
            self.solicitante,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 422)
        self.assertEqual(result.get("error"), "cotizacion_requerida")

    def test_crear_con_cotizacion_inexistente_es_rechazado(self):
        ok, result, code = RequisicionCompraBusinessService.crear_requisicion(
            {
                "fecha_necesidad": date.today() + timedelta(days=1),
                "tipo": "BIEN",
                "prioridad": "MEDIA",
                "justificacion": "x",
                "observaciones": "",
                "proyecto": None,
                "responsable_aprobacion": None,
                "cotizacion": "00000000-0000-0000-0000-000000000000",
            },
            self._items_data(),
            self.empresa,
            self.sede,
            self.solicitante,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 400)
        self.assertEqual(result.get("error"), "cotizacion_invalida")

    def test_fecha_necesidad_anterior_a_solicitud_viola_constraint_db(self):
        req = self._crear_requisicion()
        req.fecha_necesidad = req.fecha_solicitud - timedelta(days=1)
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError), transaction.atomic():
            req.save()

    # ── Maquina de estados ──────────────────────────────────────────────

    def test_flujo_feliz_borrador_a_aprobada(self):
        req = self._crear_requisicion()
        self.assertEqual(req.estado, RequisicionCompra.Estado.BORRADOR)

        ok, req, code = RequisicionCompraBusinessService.enviar_a_aprobacion(
            str(req.uuid), self.empresa.id
        )
        self.assertTrue(ok, req)
        self.assertEqual(req.estado, RequisicionCompra.Estado.PENDIENTE_APROBACION)

        ok, req, code = RequisicionCompraBusinessService.aprobar_requisicion(
            str(req.uuid), self.empresa.id
        )
        self.assertTrue(ok, req)
        self.assertEqual(req.estado, RequisicionCompra.Estado.APROBADA)
        item = req.items.first()
        self.assertEqual(item.cantidad_aprobada, item.cantidad_solicitada)

    def test_enviar_a_aprobacion_sin_justificacion_es_rechazado(self):
        req = self._crear_requisicion(justificacion="")
        ok, result, code = RequisicionCompraBusinessService.enviar_a_aprobacion(
            str(req.uuid), self.empresa.id
        )
        self.assertFalse(ok)
        self.assertEqual(code, 422)

    def test_rechazar_sin_motivo_es_rechazado(self):
        req = self._crear_requisicion()
        RequisicionCompraBusinessService.enviar_a_aprobacion(str(req.uuid), self.empresa.id)
        ok, result, code = RequisicionCompraBusinessService.rechazar_requisicion(
            str(req.uuid), self.empresa.id, ""
        )
        self.assertFalse(ok)
        self.assertEqual(code, 422)

    def test_rechazar_con_motivo_queda_en_historial(self):
        req = self._crear_requisicion()
        RequisicionCompraBusinessService.enviar_a_aprobacion(str(req.uuid), self.empresa.id)
        ok, req, code = RequisicionCompraBusinessService.rechazar_requisicion(
            str(req.uuid),
            self.empresa.id,
            "No se aprueba por presupuesto insuficiente.",
        )
        self.assertTrue(ok, req)
        self.assertEqual(req.estado, RequisicionCompra.Estado.RECHAZADA)
        historial = req.historial_estados.order_by("-created_at").first()
        self.assertEqual(historial.estado_nuevo, "RECHAZADA")
        self.assertIn("presupuesto", historial.comentario)

    def test_transicion_invalida_es_rechazada(self):
        req = self._crear_requisicion()
        # BORRADOR -> APROBADA directo no esta permitido (debe pasar por PENDIENTE_APROBACION)
        ok, result, code = RequisicionCompraBusinessService._transicionar(
            str(req.uuid),
            self.empresa.id,
            RequisicionCompra.Estado.APROBADA,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 400)

    def test_transicion_idempotente_no_escribe_historial_duplicado(self):
        req = self._crear_requisicion()
        RequisicionCompraBusinessService.enviar_a_aprobacion(str(req.uuid), self.empresa.id)
        historial_antes = req.historial_estados.count()

        ok, req2, code = RequisicionCompraBusinessService._transicionar(
            str(req.uuid),
            self.empresa.id,
            RequisicionCompra.Estado.PENDIENTE_APROBACION,
        )
        self.assertTrue(ok)
        req.refresh_from_db()
        self.assertEqual(req.historial_estados.count(), historial_antes)

    def test_cancelar_desde_borrador(self):
        req = self._crear_requisicion()
        ok, req, code = RequisicionCompraBusinessService.cancelar_requisicion(
            str(req.uuid), self.empresa.id, "Ya no se necesita"
        )
        self.assertTrue(ok, req)
        self.assertEqual(req.estado, RequisicionCompra.Estado.CANCELADA)

    def test_cancelar_estado_terminal_no_permite_mas_transiciones(self):
        req = self._crear_requisicion()
        RequisicionCompraBusinessService.cancelar_requisicion(str(req.uuid), self.empresa.id)
        ok, result, code = RequisicionCompraBusinessService.enviar_a_aprobacion(
            str(req.uuid), self.empresa.id
        )
        self.assertFalse(ok)

    # ── Multitenant / DSV ────────────────────────────────────────────────

    def test_requisicion_con_empresa_id_incorrecto_no_es_visible(self):
        """DSV anti-IDOR: si el empresa_id resuelto en la request no
        coincide con el de la fila, el lookup debe fallar (404), sin
        importar que el UUID sea correcto. Empresa es singleton por schema
        (ver nota mas arriba) -- se simula el mismatch con un empresa_id
        que no existe, equivalente al efecto real de un IDOR bloqueado."""
        req = self._crear_requisicion()
        empresa_id_incorrecto = self.empresa.id + 999999
        ok, result, code = RequisicionCompraBusinessService.enviar_a_aprobacion(
            str(req.uuid), empresa_id_incorrecto
        )
        self.assertFalse(ok)
        self.assertEqual(code, 404)

    # ── Actualizar / Eliminar (§45 del plan: casos de rechazo obligatorios) ──

    def test_actualizar_requisicion_aprobada_es_rechazada(self):
        req = self._crear_requisicion()
        RequisicionCompraBusinessService.enviar_a_aprobacion(str(req.uuid), self.empresa.id)
        RequisicionCompraBusinessService.aprobar_requisicion(str(req.uuid), self.empresa.id)

        ok, result, code = RequisicionCompraBusinessService.actualizar_requisicion(
            str(req.uuid),
            {"observaciones": "Intento de edicion post-aprobacion"},
            None,
            self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 400)
        req.refresh_from_db()
        self.assertEqual(req.observaciones, "")

    def test_eliminar_requisicion_con_orden_generada_es_rechazada(self):
        req = self._requisicion_aprobada()
        item = req.items.first()
        oc_data = {
            "plantilla": str(self.plantilla.uuid),
            "proveedor": str(self.proveedor.uuid),
            "fecha": date.today().isoformat(),
        }
        RequisicionCompraBusinessService.crear_orden_desde_requisicion(
            str(req.uuid),
            oc_data,
            [{"requisicion_item_uuid": str(item.uuid), "cantidad": "1"}],
            self.empresa,
            self.sede,
            self.empresa.id,
        )

        ok, result, code = RequisicionCompraBusinessService.eliminar_requisicion(
            str(req.uuid), self.empresa.id
        )
        self.assertFalse(ok)
        self.assertEqual(code, 400)
        self.assertTrue(RequisicionCompra.objects.filter(uuid=req.uuid).exists())

    def test_eliminar_requisicion_borrador_sin_ordenes_permitido(self):
        req = self._crear_requisicion()
        ok, result, code = RequisicionCompraBusinessService.eliminar_requisicion(
            str(req.uuid), self.empresa.id
        )
        self.assertTrue(ok, result)
        self.assertEqual(code, 204)
        self.assertFalse(RequisicionCompra.objects.filter(uuid=req.uuid).exists())

    def test_eliminar_requisicion_con_cotizacion_adicional_es_rechazada(self):
        """§39 del plan: no destruir trazabilidad. La Cotizacion de ORIGEN
        (obligatoria, siempre presente) no bloquea el DELETE de un BORRADOR
        (ver test anterior) -- pero una cotizacion ADICIONAL vinculada
        despues si debe bloquearlo."""
        req = self._crear_requisicion()
        otra_cotizacion = Cotizacion.objects.create(
            empresa=self.empresa,
            numero_cotizacion="COT-REQ-ADICIONAL",
            fecha_vencimiento=date.today() + timedelta(days=30),
        )
        RequisicionCompraBusinessService.vincular_cotizacion(
            str(req.uuid),
            str(otra_cotizacion.uuid),
            self.empresa.id,
        )
        ok, result, code = RequisicionCompraBusinessService.eliminar_requisicion(
            str(req.uuid), self.empresa.id
        )
        self.assertFalse(ok)
        self.assertEqual(code, 400)
        self.assertTrue(RequisicionCompra.objects.filter(uuid=req.uuid).exists())

    def test_eliminar_requisicion_con_factura_vinculada_es_rechazada(self):
        req = self._crear_requisicion()
        factura = Factura.objects.create(
            empresa=self.empresa,
            numero="FAC-REQ-DEL-1",
            prefijo="FAC",
            consecutivo=1,
            tipo="FE",
            estado="BORRADOR",
            fecha_emision=date.today(),
            emisor_nit="900111222",
            emisor_razon_social="Emisor Test",
            receptor_nit="800222333",
            receptor_razon_social="Receptor Test",
            subtotal=Decimal("100000.00"),
            impuestos=Decimal("19000.00"),
            total=Decimal("119000.00"),
        )
        RequisicionCompraBusinessService.vincular_factura(
            str(req.uuid), str(factura.uuid), self.empresa.id
        )
        ok, result, code = RequisicionCompraBusinessService.eliminar_requisicion(
            str(req.uuid), self.empresa.id
        )
        self.assertFalse(ok)
        self.assertEqual(code, 400)
        self.assertTrue(RequisicionCompra.objects.filter(uuid=req.uuid).exists())

    # ── crear_orden_desde_requisicion ────────────────────────────────────

    def _requisicion_aprobada(self, cantidad="3"):
        req = self._crear_requisicion(**{})
        RequisicionCompraBusinessService.enviar_a_aprobacion(str(req.uuid), self.empresa.id)
        ok, req, code = RequisicionCompraBusinessService.aprobar_requisicion(
            str(req.uuid), self.empresa.id
        )
        self.assertTrue(ok, req)
        return req

    def test_crear_orden_desde_requisicion_marca_atendida_si_se_ordena_todo(self):
        req = self._requisicion_aprobada()
        item = req.items.first()
        oc_data = {
            "plantilla": str(self.plantilla.uuid),
            "proveedor": str(self.proveedor.uuid),
            "fecha": date.today().isoformat(),
        }
        items_ordenados = [{"requisicion_item_uuid": str(item.uuid), "cantidad": "3"}]

        ok, orden, code = RequisicionCompraBusinessService.crear_orden_desde_requisicion(
            str(req.uuid),
            oc_data,
            items_ordenados,
            self.empresa,
            self.sede,
            self.empresa.id,
        )
        self.assertTrue(ok, orden)
        self.assertEqual(code, 201)
        self.assertIsInstance(orden, OrdenCompra)
        self.assertEqual(
            list(orden.requisiciones_vinculadas.values_list("requisicion_id", flat=True)),
            [req.id],
        )

        req.refresh_from_db()
        self.assertEqual(req.estado, RequisicionCompra.Estado.ATENDIDA)
        item.refresh_from_db()
        self.assertEqual(item.cantidad_ordenada, Decimal("3.00"))
        self.assertEqual(item.cantidad_pendiente, Decimal("0.00"))

    def test_crear_orden_desde_requisicion_parcial_queda_parcialmente_atendida(self):
        req = self._requisicion_aprobada()
        item = req.items.first()
        oc_data = {
            "plantilla": str(self.plantilla.uuid),
            "proveedor": str(self.proveedor.uuid),
            "fecha": date.today().isoformat(),
        }
        items_ordenados = [{"requisicion_item_uuid": str(item.uuid), "cantidad": "1"}]

        ok, orden, code = RequisicionCompraBusinessService.crear_orden_desde_requisicion(
            str(req.uuid),
            oc_data,
            items_ordenados,
            self.empresa,
            self.sede,
            self.empresa.id,
        )
        self.assertTrue(ok, orden)

        req.refresh_from_db()
        self.assertEqual(req.estado, RequisicionCompra.Estado.PARCIALMENTE_ATENDIDA)
        item.refresh_from_db()
        self.assertEqual(item.cantidad_ordenada, Decimal("1.00"))
        self.assertEqual(item.cantidad_pendiente, Decimal("2.00"))

    def test_crear_orden_desde_requisicion_dos_ordenes_completa_atendida(self):
        req = self._requisicion_aprobada()
        item = req.items.first()
        oc_data = {
            "plantilla": str(self.plantilla.uuid),
            "proveedor": str(self.proveedor.uuid),
            "fecha": date.today().isoformat(),
        }

        RequisicionCompraBusinessService.crear_orden_desde_requisicion(
            str(req.uuid),
            oc_data,
            [{"requisicion_item_uuid": str(item.uuid), "cantidad": "1"}],
            self.empresa,
            self.sede,
            self.empresa.id,
        )
        req.refresh_from_db()
        self.assertEqual(req.estado, RequisicionCompra.Estado.PARCIALMENTE_ATENDIDA)

        RequisicionCompraBusinessService.crear_orden_desde_requisicion(
            str(req.uuid),
            oc_data,
            [{"requisicion_item_uuid": str(item.uuid), "cantidad": "2"}],
            self.empresa,
            self.sede,
            self.empresa.id,
        )
        req.refresh_from_db()
        self.assertEqual(req.estado, RequisicionCompra.Estado.ATENDIDA)
        self.assertEqual(
            OrdenCompra.objects.filter(requisiciones_vinculadas__requisicion=req)
            .distinct()
            .count(),
            2,
        )

    def test_crear_orden_no_permite_ordenar_mas_de_lo_pendiente(self):
        req = self._requisicion_aprobada()
        item = req.items.first()
        oc_data = {
            "plantilla": str(self.plantilla.uuid),
            "proveedor": str(self.proveedor.uuid),
            "fecha": date.today().isoformat(),
        }

        ok, result, code = RequisicionCompraBusinessService.crear_orden_desde_requisicion(
            str(req.uuid),
            oc_data,
            [{"requisicion_item_uuid": str(item.uuid), "cantidad": "999"}],
            self.empresa,
            self.sede,
            self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 422)
        self.assertFalse(
            OrdenCompra.objects.filter(requisiciones_vinculadas__requisicion=req).exists()
        )

    def test_crear_orden_desde_requisicion_no_aprobada_es_rechazado(self):
        req = self._crear_requisicion()  # BORRADOR
        item = req.items.first()
        oc_data = {
            "plantilla": str(self.plantilla.uuid),
            "proveedor": str(self.proveedor.uuid),
            "fecha": date.today().isoformat(),
        }

        ok, result, code = RequisicionCompraBusinessService.crear_orden_desde_requisicion(
            str(req.uuid),
            oc_data,
            [{"requisicion_item_uuid": str(item.uuid), "cantidad": "1"}],
            self.empresa,
            self.sede,
            self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 422)

    def test_crear_orden_item_de_otra_requisicion_es_rechazado(self):
        req1 = self._requisicion_aprobada()
        req2 = self._requisicion_aprobada()
        item_de_req2 = req2.items.first()
        oc_data = {
            "plantilla": str(self.plantilla.uuid),
            "proveedor": str(self.proveedor.uuid),
            "fecha": date.today().isoformat(),
        }

        ok, result, code = RequisicionCompraBusinessService.crear_orden_desde_requisicion(
            str(req1.uuid),
            oc_data,
            [{"requisicion_item_uuid": str(item_de_req2.uuid), "cantidad": "1"}],
            self.empresa,
            self.sede,
            self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 400)
