"""
Fase 12 (autorizada por el usuario 2026-09-25): integracion OrdenCompra <->
RequisicionCompra.

**[2026-09-26] FASE C activada, luego evolucionada a N:N el mismo dia**
(PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md #3): el FK unico
`OrdenCompra.requisicion` + escape `es_excepcional` que se implementaron
primero se retiraron el mismo dia -- "No resolver esto con un FK unico" y
"La excepcion es_excepcional no debe seguir funcionando para nuevas OC".
Reemplazados por `OrdenCompraRequisicion` (N:N real, con `monto_asignado`
para el control financiero, ver `budget_control_service.py`).

Estos tests verifican:
1. Crear una orden SIN ninguna requisicion es rechazado (422) -- ya no
   existe ninguna via de excepcion.
2. Cuando SI hay requisicion(es) vinculada(s), la orden solo puede
   aprobarse si TODAS estan APROBADA.
"""

from datetime import date
from decimal import Decimal

from apps.tenant.compras.models import OrdenCompra, OrdenCompraRequisicion, PlantillaOrdenCompra
from apps.tenant.compras.requisiciones.services.business_service import (
    RequisicionCompraBusinessService,
)
from apps.tenant.compras.services.business_service import OrdenCompraBusinessService
from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class OrdenCompraRequisicionIntegracionTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Integ Req-OC",
            nit="900700500",
            direccion="Calle Integ",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede Integ Req-OC")
        self.solicitante = TenantProfile.objects.get_or_create(
            user=self.user,
            empresa=self.empresa,
            defaults={"rol": "ADMIN", "alcance": "EMPRESA", "cargo": "Comprador"},
        )[0]
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa,
            razon_social="Proveedor Integ Req-OC",
            tipo_documento="NIT",
            numero_documento="900700600",
            activo=True,
        )
        self.plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa,
            nombre="Plantilla Integ Req-OC",
            prefijo="INTEGOC",
            rango_desde=1,
            rango_hasta=1000,
            consecutivo_actual=1,
            vigente=True,
        )
        # Cotizacion de origen -- OBLIGATORIA al crear RequisicionCompra
        # desde 2026-09-26.
        self.cotizacion = Cotizacion.objects.create(
            empresa=self.empresa,
            numero_cotizacion="COT-INTEG-REQ-OC",
            fecha_vencimiento=date.today(),
        )

    def _items_oc(self):
        return [
            {
                "descripcion": "Item OC sin requisicion",
                "cantidad": "1",
                "valor_unitario": "10000",
                "porcentaje_iva": "0",
            }
        ]

    def test_crear_orden_sin_requisicion_es_rechazada(self):
        """Sin ninguna requisicion, la creacion debe rechazarse (422) -- no
        se crea nada. Ya no existe ninguna via de excepcion."""
        data = {
            "plantilla": str(self.plantilla.uuid),
            "proveedor": str(self.proveedor.uuid),
            "fecha": date.today(),
            "observaciones": "Sin requisicion",
        }
        ok, result, code = OrdenCompraBusinessService.crear_orden_compra(
            data, self._items_oc(), self.empresa, self.sede
        )
        self.assertFalse(ok)
        self.assertEqual(code, 422)
        self.assertEqual(result["error"], "requisicion_requerida")
        self.assertEqual(OrdenCompra.objects.filter(empresa=self.empresa).count(), 0)

    def _crear_requisicion_aprobada(self, valor_unitario_estimado="10000", numero_cotizacion=None):
        cotizacion = self.cotizacion
        if numero_cotizacion:
            cotizacion = Cotizacion.objects.create(
                empresa=self.empresa,
                numero_cotizacion=numero_cotizacion,
                fecha_vencimiento=date.today(),
            )
        ok, req, code = RequisicionCompraBusinessService.crear_requisicion(
            {
                "fecha_necesidad": date.today(),
                "tipo": "BIEN",
                "prioridad": "MEDIA",
                "justificacion": "Integracion Req-OC",
                "observaciones": "",
                "proyecto": None,
                "responsable_aprobacion": None,
                "cotizacion": cotizacion,
            },
            [
                {
                    "tipo_item": "BIEN",
                    "descripcion": "Item req",
                    "cantidad_solicitada": "1",
                    "valor_unitario_estimado": valor_unitario_estimado,
                    "porcentaje_iva": "0",
                    "unidad_medida": "UND",
                }
            ],
            self.empresa,
            self.sede,
            self.solicitante,
        )
        self.assertTrue(ok, req)
        RequisicionCompraBusinessService.enviar_a_aprobacion(str(req.uuid), self.empresa.id)
        ok, req, code = RequisicionCompraBusinessService.aprobar_requisicion(
            str(req.uuid), self.empresa.id
        )
        self.assertTrue(ok, req)
        return req

    def test_orden_con_requisicion_no_aprobada_no_puede_aprobarse(self):
        """N:N (PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md #3): a
        diferencia del FK unico original, `crear_orden_compra()` ya exige
        que CADA Requisicion este en `ESTADOS_DISPONIBLES_PARA_COMPRA`
        (APROBADA/EN_PROCESO_COMPRA/PARCIALMENTE_ATENDIDA) desde el momento
        de la CREACION -- una Requisicion en BORRADOR ya no puede ni
        siquiera vincularse a una OC nueva (rechazo temprano, `422
        requisicion_no_disponible`), no solo al intentar aprobar la orden
        despues."""
        ok, req, code = RequisicionCompraBusinessService.crear_requisicion(
            {
                "fecha_necesidad": date.today(),
                "tipo": "BIEN",
                "prioridad": "MEDIA",
                "justificacion": "Sin aprobar aun",
                "observaciones": "",
                "proyecto": None,
                "responsable_aprobacion": None,
                "cotizacion": self.cotizacion,
            },
            [
                {
                    "tipo_item": "BIEN",
                    "descripcion": "Item req",
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
        self.assertTrue(ok, req)  # req sigue en BORRADOR

        data = {
            "plantilla": str(self.plantilla.uuid),
            "proveedor": str(self.proveedor.uuid),
            "fecha": date.today(),
            "requisiciones": [str(req.uuid)],
        }
        ok, result, code = OrdenCompraBusinessService.crear_orden_compra(
            data, self._items_oc(), self.empresa, self.sede
        )
        self.assertFalse(ok, result)
        self.assertEqual(code, 422)
        self.assertEqual(result["error"], "requisicion_no_disponible")
        self.assertEqual(OrdenCompra.objects.filter(empresa=self.empresa).count(), 0)

    def test_orden_con_requisicion_aprobada_si_puede_aprobarse(self):
        req = self._crear_requisicion_aprobada()
        data = {
            "plantilla": str(self.plantilla.uuid),
            "proveedor": str(self.proveedor.uuid),
            "fecha": date.today(),
            "requisiciones": [str(req.uuid)],
        }
        ok, orden, code = OrdenCompraBusinessService.crear_orden_compra(
            data, self._items_oc(), self.empresa, self.sede
        )
        self.assertTrue(ok, orden)

        ok, orden, code = OrdenCompraBusinessService.cambiar_estado_orden_compra(
            str(orden.uuid), "APROBADA", self.empresa.id
        )
        self.assertTrue(ok, orden)
        self.assertEqual(orden.estado, "APROBADA")

    def test_crear_orden_con_dos_requisiciones_consolida_ambas(self):
        """N:N real (PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md #3): una
        OC puede consolidar varias requisiciones -- el monto se reparte
        proporcional al total_estimado de cada una (sin montos explicitos)."""
        req1 = self._crear_requisicion_aprobada(
            valor_unitario_estimado="10000", numero_cotizacion="COT-NN-1"
        )
        req2 = self._crear_requisicion_aprobada(
            valor_unitario_estimado="30000", numero_cotizacion="COT-NN-2"
        )

        data = {
            "plantilla": str(self.plantilla.uuid),
            "proveedor": str(self.proveedor.uuid),
            "fecha": date.today(),
            "requisiciones": [str(req1.uuid), str(req2.uuid)],
        }
        items = [
            {
                "descripcion": "Item consolidado",
                "cantidad": "1",
                "valor_unitario": "4000",
                "porcentaje_iva": "0",
            }
        ]
        ok, orden, code = OrdenCompraBusinessService.crear_orden_compra(
            data, items, self.empresa, self.sede
        )
        self.assertTrue(ok, orden)

        vinculos = OrdenCompraRequisicion.objects.filter(orden_compra=orden)
        self.assertEqual(vinculos.count(), 2)
        self.assertEqual(sum((v.monto_asignado for v in vinculos), Decimal("0.00")), orden.total)
        # Reparto proporcional: req2 tiene 3x el total_estimado de req1.
        monto_req1 = vinculos.get(requisicion=req1).monto_asignado
        monto_req2 = vinculos.get(requisicion=req2).monto_asignado
        self.assertEqual(monto_req1, Decimal("1000.00"))
        self.assertEqual(monto_req2, Decimal("3000.00"))

    def test_crear_orden_excede_saldo_de_requisicion_es_rechazada(self):
        """Control financiero (#23/#24 del plan): la orden no puede consumir
        mas saldo del que tiene la requisicion. No se crea nada (rollback
        completo, incluida la OrdenCompra que ya se habia insertado antes
        de la validacion de presupuesto)."""
        req = self._crear_requisicion_aprobada(valor_unitario_estimado="10000")  # saldo = 10000

        data = {
            "plantilla": str(self.plantilla.uuid),
            "proveedor": str(self.proveedor.uuid),
            "fecha": date.today(),
            "requisiciones": [str(req.uuid)],
        }
        items = [
            {
                "descripcion": "Excede saldo",
                "cantidad": "1",
                "valor_unitario": "20000",
                "porcentaje_iva": "0",
            }
        ]
        ok, result, code = OrdenCompraBusinessService.crear_orden_compra(
            data, items, self.empresa, self.sede
        )
        self.assertFalse(ok)
        self.assertEqual(code, 400)
        self.assertIn("presupuesto", result)
        self.assertEqual(OrdenCompra.objects.filter(empresa=self.empresa).count(), 0)
        self.assertEqual(OrdenCompraRequisicion.objects.filter(empresa=self.empresa).count(), 0)
