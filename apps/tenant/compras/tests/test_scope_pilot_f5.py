"""
Fase F5 (proyecto OSF), "compras como piloto oficial": pinea el fix del
hallazgo real encontrado en F4 y confirmado durante la auditoria de F5 -
tanto el listado DRF (`OrdenCompraViewSet.get_qs_list()`) como la grilla que
el usuario efectivamente ve (antes HTML/HTMX via `OrdenCompraTableView`,
migrada a DataTables -- `OrdenCompraViewSet.dt()`, que reutiliza el mismo
`get_qs_list()` -- ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md)
filtraban por una sola "sede activa" (la primera, o ninguna en absoluto en
el caso de la tabla HTML) en vez del conjunto COMPLETO de sedes/areas
permitidas (`OrganizationalScope`, Fase F2). Un perfil con alcance SEDE
asignado a 2 sedes solo veia ordenes de 1; un perfil con alcance AREA no
tenia ningun filtro de area en absoluto.
"""

from datetime import date

from rest_framework import status

from apps.tenant.compras.models import OrdenCompra, PlantillaOrdenCompra
from apps.tenant.compras.requisiciones.services.business_service import (
    RequisicionCompraBusinessService,
)
from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.empresa.models import Area, Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class ComprasScopePilotF5Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F5",
            nit="900000444",
            direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F5")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F5")
        self.sede_c = Sede.objects.create(empresa=self.empresa, nombre="Sede C F5")
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa,
            razon_social="Proveedor F5",
            numero_documento="F5-1",
            tipo_documento="NIT",
        )
        self.plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa,
            nombre="Plantilla F5",
            prefijo="OSF5",
            rango_desde=1,
            rango_hasta=1000,
            consecutivo_actual=1,
            vigente=True,
        )
        self.orden_a = self._crear_orden(self.sede_a, consecutivo=1)
        self.orden_b = self._crear_orden(self.sede_b, consecutivo=2)
        self.orden_c = self._crear_orden(self.sede_c, consecutivo=3)

    def _crear_orden(self, sede, consecutivo, area=None):
        return OrdenCompra.objects.create(
            empresa=self.empresa,
            sede=sede,
            area=area,
            proveedor=self.proveedor,
            plantilla=self.plantilla,
            fecha="2026-06-01",
            consecutivo=consecutivo,
        )

    def test_api_list_con_alcance_sede_ve_todas_las_sedes_asignadas_no_solo_una(self):
        perfil = TenantProfile.objects.create(
            user=self.user,
            empresa=self.empresa,
            rol="OPERADOR",
            alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.sede_a, self.sede_b])

        resp = self.api_client.get("/api/v1/compras/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        consecutivos = {row["consecutivo"] for row in resp.json().get("results", resp.json())}
        self.assertEqual(consecutivos, {1, 2})

    def test_api_list_con_alcance_area_filtra_por_area_no_solo_por_sede(self):
        area_x = Area.objects.create(
            empresa=self.empresa,
            sede=self.sede_a,
            nombre="Area X F5",
            codigo_funcionamiento="AX-F5",
        )
        area_y = Area.objects.create(
            empresa=self.empresa,
            sede=self.sede_a,
            nombre="Area Y F5",
            codigo_funcionamiento="AY-F5",
        )
        self._crear_orden(self.sede_a, consecutivo=10, area=area_x)
        self._crear_orden(self.sede_a, consecutivo=11, area=area_y)

        perfil = TenantProfile.objects.create(
            user=self.user,
            empresa=self.empresa,
            rol="OPERADOR",
            alcance="AREA",
        )
        perfil.sedes_asignadas.set([self.sede_a])
        perfil.areas_asignadas.set([area_x])

        resp = self.api_client.get("/api/v1/compras/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        consecutivos = {row["consecutivo"] for row in resp.json().get("results", resp.json())}
        self.assertIn(10, consecutivos)
        self.assertNotIn(11, consecutivos)
        # Las de sede_b/sede_c (sin area en absoluto) tampoco deben aparecer.
        self.assertNotIn(2, consecutivos)
        self.assertNotIn(3, consecutivos)

    def test_api_list_con_alcance_empresa_sigue_viendo_todo(self):
        TenantProfile.objects.create(
            user=self.user,
            empresa=self.empresa,
            rol="ADMIN",
            alcance="EMPRESA",
        )

        resp = self.api_client.get("/api/v1/compras/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        rows = resp.json().get("results", resp.json())
        consecutivos = {row["consecutivo"] for row in rows}
        self.assertEqual(consecutivos, {1, 2, 3})
        # [OSF Fase F5] hallazgo: con ordenes de 3 sedes distintas mezcladas
        # en el mismo listado (alcance EMPRESA ve todas), `sede_nombre` debe
        # distinguir cada fila - antes no existia en absoluto en el serializer.
        nombres_sede = {row["sede_nombre"] for row in rows}
        self.assertEqual(nombres_sede, {"Sede A F5", "Sede B F5", "Sede C F5"})

    def test_dt_con_alcance_sede_ve_todas_las_sedes_asignadas(self):
        """Hallazgo mas grave de F5: la grilla real (la que el usuario ve --
        antes HTML/HTMX via OrdenCompraTableView, ahora DataTables via
        OrdenCompraViewSet.dt()) no aplicaba NINGUN filtro de sede -- un
        perfil con alcance SEDE veia ordenes de TODAS las sedes, incluyendo
        las que no le pertenecen. dt() reutiliza get_qs_list() (mismo
        metodo ya corregido y cubierto por los tests de /api/v1/compras/
        arriba), asi que esto confirma que la grilla real hereda el fix."""
        perfil = TenantProfile.objects.create(
            user=self.user,
            empresa=self.empresa,
            rol="OPERADOR",
            alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.sede_a, self.sede_b])

        payload = {
            "draw": 1,
            "start": 0,
            "length": 10,
            "search": {"value": ""},
            "order": [],
            "columns": [],
        }
        resp = self.api_client.post("/api/v1/compras/dt/", data=payload, format="json")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        consecutivos = {row["consecutivo"] for row in resp.json()["data"]}
        self.assertEqual(consecutivos, {1, 2})

    def _crear_requisicion_aprobada_f5(self, perfil):
        """Requisicion real APROBADA, disponible para consolidar en una OC
        -- necesaria desde que Requisicion paso a obligatoria en toda OC
        nueva (PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md #3), sin
        relacion con lo que estos tests de "area" verifican."""
        cotizacion = Cotizacion.objects.create(
            empresa=self.empresa,
            numero_cotizacion=f"COT-F5-{OrdenCompra.objects.count()}",
            fecha_vencimiento=date.today(),
        )
        ok, req, code = RequisicionCompraBusinessService.crear_requisicion(
            {
                "fecha_necesidad": date.today(),
                "tipo": "BIEN",
                "prioridad": "MEDIA",
                "justificacion": "Requisicion F5",
                "observaciones": "",
                "proyecto": None,
                "responsable_aprobacion": None,
                "cotizacion": cotizacion,
            },
            [
                {
                    "tipo_item": "BIEN",
                    "descripcion": "Item F5",
                    "cantidad_solicitada": "2",
                    "valor_unitario_estimado": "100.00",
                    "porcentaje_iva": "19",
                    "unidad_medida": "UND",
                }
            ],
            self.empresa,
            self.sede_a,
            perfil,
        )
        assert ok, req
        RequisicionCompraBusinessService.enviar_a_aprobacion(str(req.uuid), self.empresa.id)
        ok, req, code = RequisicionCompraBusinessService.aprobar_requisicion(
            str(req.uuid), self.empresa.id
        )
        assert ok, req
        return req

    def _payload_crear_orden(self, area_uuid=None, requisicion_uuid=None):
        payload = {
            "plantilla": str(self.plantilla.uuid),
            "proveedor": str(self.proveedor.uuid),
            "fecha": "2026-06-15",
            "items": [
                {
                    "descripcion": "Item F5",
                    "cantidad": "2",
                    "valor_unitario": "100.00",
                    "porcentaje_iva": "19",
                },
            ],
            "requisiciones": [requisicion_uuid] if requisicion_uuid else [],
        }
        if area_uuid is not None:
            payload["area"] = area_uuid
        return payload

    def test_crear_orden_con_area_de_la_misma_sede_activa_funciona(self):
        """[OSF Fase F5] Hallazgo real: 'area' no existia como campo
        escribible en OrdenCompraCreateUpdateSerializer - el business
        service ya tenia DSV completa para area, pero DRF descartaba el
        valor antes de llegar ahi. Corregido; se confirma end-to-end que
        ahora SI se puede asignar."""
        perfil = TenantProfile.objects.create(
            user=self.user,
            empresa=self.empresa,
            rol="ADMIN",
            alcance="EMPRESA",
        )
        area_x = Area.objects.create(
            empresa=self.empresa,
            sede=self.sede_a,
            nombre="Area X Crear F5",
            codigo_funcionamiento="AXC-F5",
        )
        requisicion = self._crear_requisicion_aprobada_f5(perfil)

        resp = self.api_client.post(
            "/api/v1/compras/",
            data=self._payload_crear_orden(
                area_uuid=str(area_x.uuid), requisicion_uuid=str(requisicion.uuid)
            ),
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        orden_creada = OrdenCompra.objects.get(uuid=resp.json()["uuid"])
        self.assertEqual(orden_creada.area_id, area_x.id)
        # La sede activa (sin sesion/asignacion explicita) cae a la primera
        # Sede por nombre de la empresa - "Sede A F5" - que es la misma
        # sede de area_x, por eso la validacion de consistencia pasa.
        self.assertEqual(orden_creada.sede_id, self.sede_a.id)

    def test_crear_orden_con_area_de_otra_sede_falla_validacion(self):
        """[OSF Fase F5] Hallazgo real (encontrado al implementar el fix
        anterior): ni crear_orden_compra ni actualizar_orden_compra
        verificaban que el Area perteneciera a la MISMA Sede de la orden -
        solo que perteneciera a la misma empresa. Un Area de otra sede
        habria dejado la orden en un estado organizacionalmente
        inconsistente (sede X, area de sede Y)."""
        perfil = TenantProfile.objects.create(
            user=self.user,
            empresa=self.empresa,
            rol="ADMIN",
            alcance="EMPRESA",
        )
        area_de_sede_b = Area.objects.create(
            empresa=self.empresa,
            sede=self.sede_b,
            nombre="Area Sede B F5",
            codigo_funcionamiento="ASB-F5",
        )
        requisicion = self._crear_requisicion_aprobada_f5(perfil)

        resp = self.api_client.post(
            "/api/v1/compras/",
            data=self._payload_crear_orden(
                area_uuid=str(area_de_sede_b.uuid), requisicion_uuid=str(requisicion.uuid)
            ),
            format="json",
        )

        # La sede activa resuelta es sede_a (primera por nombre); el area
        # pertenece a sede_b - debe fallar, no crear una orden inconsistente.
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        self.assertEqual(resp.json().get("error"), "area_invalida")

    def test_actualizar_orden_con_area_de_otra_sede_falla_validacion(self):
        """Mismo hallazgo que el test anterior, pero en el flujo de
        actualizacion - antes de F5 esta validacion no existia en absoluto
        (el bloque DSV de 'area' en actualizar_orden_compra no existia)."""
        TenantProfile.objects.create(
            user=self.user,
            empresa=self.empresa,
            rol="ADMIN",
            alcance="EMPRESA",
        )
        area_de_sede_b = Area.objects.create(
            empresa=self.empresa,
            sede=self.sede_b,
            nombre="Area Sede B F5 Update",
            codigo_funcionamiento="ASBU-F5",
        )
        # self.orden_a esta en sede_a (BORRADOR por default, editable).
        resp = self.api_client.patch(
            f"/api/v1/compras/{self.orden_a.uuid}/",
            data={"area": str(area_de_sede_b.uuid)},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        self.assertEqual(resp.json().get("error"), "area_invalida")
        self.orden_a.refresh_from_db()
        self.assertIsNone(self.orden_a.area_id)
