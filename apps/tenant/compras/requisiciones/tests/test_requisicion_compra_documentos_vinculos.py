"""
Fase 12 (autorizada por el usuario 2026-09-25): RequisicionDocumento,
vincular_cotizacion/vincular_factura (trazabilidad, sin efectos de
negocio), y permisos (VISOR no puede escribir).
"""

from datetime import date, timedelta
from decimal import Decimal

from rest_framework import status

from apps.tenant.compras.requisiciones.models import (
    RequisicionCotizacion,
    RequisicionDocumento,
    RequisicionFactura,
)
from apps.tenant.compras.requisiciones.services.business_service import (
    RequisicionCompraBusinessService,
)
from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.facturas.models import Factura
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class RequisicionDocumentosVinculosTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Req Docs",
            nit="900700700",
            direccion="Calle Req Docs",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede Req Docs")
        self.solicitante = TenantProfile.objects.get_or_create(
            user=self.user,
            empresa=self.empresa,
            defaults={"rol": "ADMIN", "alcance": "EMPRESA", "cargo": "Analista"},
        )[0]
        # Cotizacion de origen -- OBLIGATORIA al crear desde 2026-09-26.
        self.cotizacion_origen = Cotizacion.objects.create(
            empresa=self.empresa,
            numero_cotizacion="COT-REQ-ORIGEN",
            fecha_vencimiento=date.today() + timedelta(days=30),
        )

        ok, self.req, code = RequisicionCompraBusinessService.crear_requisicion(
            {
                "fecha_necesidad": date.today() + timedelta(days=3),
                "tipo": "SERVICIO",
                "prioridad": "MEDIA",
                "justificacion": "Docs y vinculos",
                "observaciones": "",
                "proyecto": None,
                "responsable_aprobacion": None,
                "cotizacion": self.cotizacion_origen,
            },
            [
                {
                    "tipo_item": "SERVICIO",
                    "descripcion": "Servicio X",
                    "cantidad_solicitada": "1",
                    "valor_unitario_estimado": "20000",
                    "porcentaje_iva": "0",
                    "unidad_medida": "UND",
                }
            ],
            self.empresa,
            self.sede,
            self.solicitante,
        )
        self.assertTrue(ok, self.req)

    # ── Documentos ────────────────────────────────────────────────────

    def test_adjuntar_documento_placeholder_externo(self):
        ok, doc, code = RequisicionCompraBusinessService.adjuntar_documento(
            str(self.req.uuid),
            self.empresa.id,
            {
                "tipo": "FACTURA",
                "nombre": "Factura proveedor pendiente",
                "numero_referencia": "FE-99999",
                "documento_uuid": None,
            },
        )
        self.assertTrue(ok, doc)
        self.assertEqual(code, 201)
        self.assertIsInstance(doc, RequisicionDocumento)
        self.assertIsNone(doc.documento_uuid)
        self.assertEqual(RequisicionDocumento.objects.filter(requisicion=self.req).count(), 1)

    def test_adjuntar_documento_requisicion_inexistente_falla(self):
        ok, result, code = RequisicionCompraBusinessService.adjuntar_documento(
            "00000000-0000-0000-0000-000000000000",
            self.empresa.id,
            {"tipo": "OTRO", "nombre": "x"},
        )
        self.assertFalse(ok)
        self.assertEqual(code, 404)

    # ── Vincular Cotizacion ──────────────────────────────────────────────

    def test_vincular_cotizacion_existente(self):
        cot = Cotizacion.objects.create(
            empresa=self.empresa,
            numero_cotizacion="COT-REQ-1",
            fecha_vencimiento=date.today() + timedelta(days=30),
        )
        ok, vinculo, code = RequisicionCompraBusinessService.vincular_cotizacion(
            str(self.req.uuid),
            str(cot.uuid),
            self.empresa.id,
            observacion="Compra para atender esta venta",
        )
        self.assertTrue(ok, vinculo)
        self.assertEqual(code, 201)
        self.assertEqual(
            RequisicionCotizacion.objects.filter(requisicion=self.req, cotizacion=cot).count(), 1
        )

    def test_vincular_cotizacion_es_idempotente_no_duplica(self):
        cot = Cotizacion.objects.create(
            empresa=self.empresa,
            numero_cotizacion="COT-REQ-2",
            fecha_vencimiento=date.today() + timedelta(days=30),
        )
        RequisicionCompraBusinessService.vincular_cotizacion(
            str(self.req.uuid), str(cot.uuid), self.empresa.id
        )
        RequisicionCompraBusinessService.vincular_cotizacion(
            str(self.req.uuid), str(cot.uuid), self.empresa.id
        )
        self.assertEqual(
            RequisicionCotizacion.objects.filter(requisicion=self.req, cotizacion=cot).count(), 1
        )

    def test_vincular_cotizacion_inexistente_falla(self):
        ok, result, code = RequisicionCompraBusinessService.vincular_cotizacion(
            str(self.req.uuid),
            "00000000-0000-0000-0000-000000000000",
            self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 400)

    # ── Vincular Factura ─────────────────────────────────────────────────

    def _crear_factura(self, numero="FAC-REQ-1"):
        return Factura.objects.create(
            empresa=self.empresa,
            numero=numero,
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

    def test_vincular_factura_existente(self):
        factura = self._crear_factura()
        ok, vinculo, code = RequisicionCompraBusinessService.vincular_factura(
            str(self.req.uuid),
            str(factura.uuid),
            self.empresa.id,
        )
        self.assertTrue(ok, vinculo)
        self.assertEqual(code, 201)
        self.assertEqual(
            RequisicionFactura.objects.filter(requisicion=self.req, factura=factura).count(), 1
        )

    def test_vincular_factura_via_api(self):
        factura = self._crear_factura(numero="FAC-REQ-API")
        resp = self.api_client.post(
            f"/api/v1/compras/requisiciones/{self.req.uuid}/vincular-factura/",
            data={"factura_uuid": str(factura.uuid)},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)


class RequisicionPermisosTests(SintelTenantTestCase):
    """VISOR (solo lectura) no puede crear/editar/transicionar requisiciones."""

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Req Permisos",
            nit="900700800",
            direccion="Calle Permisos",
        )
        Sede.objects.create(empresa=self.empresa, nombre="Sede Permisos")
        TenantProfile.objects.get_or_create(
            user=self.user,
            empresa=self.empresa,
            defaults={"rol": "VISOR", "alcance": "EMPRESA", "cargo": "Auditor"},
        )

    def _payload_valido(self):
        return {
            "fecha_necesidad": (date.today() + timedelta(days=5)).isoformat(),
            "tipo": "BIEN",
            "prioridad": "BAJA",
            "justificacion": "Intento de VISOR",
            "items": [
                {
                    "tipo_item": "BIEN",
                    "descripcion": "x",
                    "cantidad_solicitada": "1",
                    "valor_unitario_estimado": "1000",
                    "porcentaje_iva": "0",
                }
            ],
        }

    def test_visor_no_puede_crear_requisicion(self):
        resp = self.api_client.post(
            "/api/v1/compras/requisiciones/", data=self._payload_valido(), format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN, resp.content)

    def test_visor_si_puede_listar(self):
        resp = self.api_client.get("/api/v1/compras/requisiciones/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)


class RequisicionTrazabilidadDesdeProyectoTests(SintelTenantTestCase):
    """Pedido explicito del usuario (2026-09-25): al asignar un Proyecto a
    una requisicion, resolver y listar automaticamente su Cotizacion/Factura
    de origen -- usando unicamente el mecanismo real ya existente (Proyecto
    es Zero-Coupling, sin FK a Cotizaciones: el codigo "PRJ-COT-<codigo>"
    que genera CotizacionService.convertir_a_proyecto() es la unica forma
    real de encontrar la Cotizacion de origen; Proyecto.factura_costo y
    Venta.factura_asociada via Venta.cotizacion_uuid son las 2 formas
    reales de encontrar la Factura)."""

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Traza Proyecto",
            nit="900701000",
            direccion="Calle Traza",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede Traza")
        self.solicitante = TenantProfile.objects.get_or_create(
            user=self.user,
            empresa=self.empresa,
            defaults={"rol": "ADMIN", "alcance": "EMPRESA", "cargo": "Analista"},
        )[0]
        # Cotizacion de origen -- OBLIGATORIA al crear desde 2026-09-26.
        # Distinta de la que puedan resolver los tests de sincronizacion
        # automatica desde Proyecto, salvo que un test la pase explicita
        # (ver test_proyecto_con_codigo_prj_cot_vincula_cotizacion_automaticamente).
        self.cotizacion_origen = Cotizacion.objects.create(
            empresa=self.empresa,
            numero_cotizacion="COT-TRAZA-ORIGEN",
            fecha_vencimiento=date.today() + timedelta(days=30),
        )

    def _items(self):
        return [
            {
                "tipo_item": "BIEN",
                "descripcion": "Item traza",
                "cantidad_solicitada": "1",
                "valor_unitario_estimado": "1000",
                "porcentaje_iva": "0",
                "unidad_medida": "UND",
            }
        ]

    def _crear_con_proyecto(self, proyecto, cotizacion=None):
        return RequisicionCompraBusinessService.crear_requisicion(
            {
                "fecha_necesidad": date.today() + timedelta(days=5),
                "tipo": "BIEN",
                "prioridad": "MEDIA",
                "justificacion": "Traza desde proyecto",
                "observaciones": "",
                "proyecto": proyecto,
                "responsable_aprobacion": None,
                "cotizacion": cotizacion or self.cotizacion_origen,
            },
            self._items(),
            self.empresa,
            self.sede,
            self.solicitante,
        )

    def test_proyecto_con_codigo_prj_cot_vincula_cotizacion_automaticamente(self):
        from apps.tenant.proyectos.models import Proyecto

        cot = Cotizacion.objects.create(
            empresa=self.empresa,
            numero_cotizacion="COT-TRAZA-1",
            codigo_unico="TRAZA-UNICO-1",
            fecha_vencimiento=date.today() + timedelta(days=30),
        )
        proyecto = Proyecto.objects.create(
            empresa=self.empresa,
            nombre="Proyecto Traza 1",
            codigo=f"PRJ-COT-{cot.codigo_unico}",
        )

        # Cotizacion de origen (obligatoria) = la misma que resuelve el
        # proyecto -- la sincronizacion automatica hace get_or_create sobre
        # el mismo par (requisicion, cotizacion), asi que no duplica.
        ok, req, code = self._crear_con_proyecto(proyecto, cotizacion=cot)
        self.assertTrue(ok, req)
        self.assertEqual(
            RequisicionCotizacion.objects.filter(requisicion=req, cotizacion=cot).count(), 1
        )
        self.assertEqual(
            RequisicionFactura.objects.filter(requisicion=req).count(), 0
        )  # sin factura resoluble

    def test_proyecto_con_factura_costo_vincula_factura_directamente(self):
        from apps.tenant.proyectos.models import Proyecto

        factura = Factura.objects.create(
            empresa=self.empresa,
            numero="FAC-TRAZA-1",
            prefijo="FAC",
            consecutivo=1,
            tipo="FE",
            estado="BORRADOR",
            fecha_emision=date.today(),
            emisor_nit="900111222",
            emisor_razon_social="Emisor",
            receptor_nit="800222333",
            receptor_razon_social="Receptor",
            subtotal=Decimal("100000.00"),
            impuestos=Decimal("19000.00"),
            total=Decimal("119000.00"),
        )
        proyecto = Proyecto.objects.create(
            empresa=self.empresa,
            nombre="Proyecto Traza 2",
            factura_costo=factura,
        )

        ok, req, code = self._crear_con_proyecto(proyecto)
        self.assertTrue(ok, req)
        self.assertEqual(
            RequisicionFactura.objects.filter(requisicion=req, factura=factura).count(), 1
        )

    def test_proyecto_sin_codigo_prj_cot_ni_factura_costo_no_vincula_nada(self):
        from apps.tenant.proyectos.models import Proyecto

        proyecto = Proyecto.objects.create(
            empresa=self.empresa, nombre="Proyecto Sin Origen", codigo="PRJ-2026-999"
        )
        ok, req, code = self._crear_con_proyecto(proyecto)
        self.assertTrue(ok, req)
        # La sincronizacion automatica desde Proyecto no encuentra nada
        # resoluble -- el unico vinculo que debe existir es la Cotizacion de
        # origen OBLIGATORIA (self.cotizacion_origen), no una adicional.
        vinculos = RequisicionCotizacion.objects.filter(requisicion=req)
        self.assertEqual(vinculos.count(), 1)
        self.assertEqual(vinculos.first().cotizacion_id, self.cotizacion_origen.id)
        self.assertEqual(RequisicionFactura.objects.filter(requisicion=req).count(), 0)

    def test_requisicion_sin_proyecto_no_intenta_sincronizar(self):
        ok, req, code = RequisicionCompraBusinessService.crear_requisicion(
            {
                "fecha_necesidad": date.today() + timedelta(days=5),
                "tipo": "BIEN",
                "prioridad": "MEDIA",
                "justificacion": "Sin proyecto",
                "observaciones": "",
                "proyecto": None,
                "responsable_aprobacion": None,
                "cotizacion": self.cotizacion_origen,
            },
            self._items(),
            self.empresa,
            self.sede,
            self.solicitante,
        )
        self.assertTrue(ok, req)
        # Sin Proyecto no hay sincronizacion automatica -- solo debe existir
        # el vinculo de la Cotizacion de origen OBLIGATORIA.
        vinculos = RequisicionCotizacion.objects.filter(requisicion=req)
        self.assertEqual(vinculos.count(), 1)
        self.assertEqual(vinculos.first().cotizacion_id, self.cotizacion_origen.id)

    def test_sincronizar_trazabilidad_endpoint_manual(self):
        from apps.tenant.proyectos.models import Proyecto

        cot = Cotizacion.objects.create(
            empresa=self.empresa,
            numero_cotizacion="COT-TRAZA-2",
            codigo_unico="TRAZA-UNICO-2",
            fecha_vencimiento=date.today() + timedelta(days=30),
        )
        proyecto = Proyecto.objects.create(
            empresa=self.empresa,
            nombre="Proyecto Traza 3",
            codigo=f"PRJ-COT-{cot.codigo_unico}",
        )
        ok, req, code = self._crear_con_proyecto(proyecto, cotizacion=cot)
        self.assertTrue(ok, req)
        # ya deberia estar vinculada por la sincronizacion automatica en creacion
        self.assertEqual(RequisicionCotizacion.objects.filter(requisicion=req).count(), 1)

        # re-disparar manualmente es idempotente, no duplica
        ok2, resultado, code2 = RequisicionCompraBusinessService.sincronizar_trazabilidad_proyecto(
            str(req.uuid),
            self.empresa.id,
        )
        self.assertTrue(ok2, resultado)
        self.assertTrue(resultado["cotizacion"])
        self.assertEqual(RequisicionCotizacion.objects.filter(requisicion=req).count(), 1)

    def test_sincronizar_trazabilidad_sin_proyecto_falla(self):
        ok, req, code = RequisicionCompraBusinessService.crear_requisicion(
            {
                "fecha_necesidad": date.today() + timedelta(days=5),
                "tipo": "BIEN",
                "prioridad": "MEDIA",
                "justificacion": "x",
                "observaciones": "",
                "proyecto": None,
                "responsable_aprobacion": None,
                "cotizacion": self.cotizacion_origen,
            },
            self._items(),
            self.empresa,
            self.sede,
            self.solicitante,
        )
        ok2, result, code2 = RequisicionCompraBusinessService.sincronizar_trazabilidad_proyecto(
            str(req.uuid),
            self.empresa.id,
        )
        self.assertFalse(ok2)
        self.assertEqual(code2, 422)
