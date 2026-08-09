"""
Tests de Aislamiento Organizacional (FASE 7, plan de consolidacion OCF/OSF —
ver documentacion/ORGANIZATIONAL_SCOPE_MIGRATION_STATUS.md).

Escenario fijo pedido por el plan maestro:

    Empresa A
     |-- Sede Bogota
     |    |-- Area Comercial
     |    `-- Area Tecnica
     |
     `-- Sede Barranquilla
          |-- Area Comercial
          `-- Area Tecnica

Cierra especificamente el gap critico encontrado en FASE 2/6
(documentacion/OSF_TECHNICAL_AUDIT.md, documentacion/COMPRAS_PILOT_VALIDATION.md):
`HasOrganizationalScope.has_object_permission()` -- el unico mecanismo de
enforcement a nivel de objeto individual del piloto oficial (`compras`) --
nunca habia tenido un test que confirmara GET/PATCH/DELETE por UUID directo
cross-sede/area.

`Area` es un modelo hijo de `Sede` (cada Area pertenece a una sola Sede) --
"Area Comercial" como concepto de negocio existe aqui como DOS registros
distintos (`area_comercial_bog`, `area_comercial_bar`), uno por sede. El
Caso 3 (alcance=AREA) requiere que el perfil tenga AMBAS sedes en
`sedes_asignadas` (no solo una) para que `OrganizationalScope.filter()`
--que aplica `sede_id__in` Y `area_id__in`-- no descarte las ordenes de la
otra sede antes de llegar al filtro de area. Esto es una demostracion viva
del Riesgo #3 de FASE 2 (documentacion/OSF_TECHNICAL_AUDIT.md): nada en el
modelo obliga a que `areas_asignadas` sea consistente con `sedes_asignadas`
-- aqui se construyen consistentes a proposito, para que el Caso 3 funcione
como el plan maestro lo describe.
"""
from rest_framework import status

from apps.tenant.compras.models import OrdenCompra, PlantillaOrdenCompra
from apps.tenant.empresa.models import Area, Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class OrganizationalIsolationEmpresaATests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa A F7", nit="900000777", direccion="Calle 1",
        )
        self.bogota = Sede.objects.create(empresa=self.empresa, nombre="Bogota F7")
        self.barranquilla = Sede.objects.create(empresa=self.empresa, nombre="Barranquilla F7")

        self.comercial_bog = Area.objects.create(
            empresa=self.empresa, sede=self.bogota, nombre="Comercial F7", codigo_funcionamiento="COM-BOG-F7",
        )
        self.tecnica_bog = Area.objects.create(
            empresa=self.empresa, sede=self.bogota, nombre="Tecnica F7", codigo_funcionamiento="TEC-BOG-F7",
        )
        self.comercial_bar = Area.objects.create(
            empresa=self.empresa, sede=self.barranquilla, nombre="Comercial F7", codigo_funcionamiento="COM-BAR-F7",
        )
        self.tecnica_bar = Area.objects.create(
            empresa=self.empresa, sede=self.barranquilla, nombre="Tecnica F7", codigo_funcionamiento="TEC-BAR-F7",
        )

        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor F7", numero_documento="F7-1", tipo_documento="NIT",
        )
        self.plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa, nombre="Plantilla F7", prefijo="F7",
            rango_desde=1, rango_hasta=1000, consecutivo_actual=1, vigente=True,
        )

        self.orden_bog_com = self._crear_orden(self.bogota, self.comercial_bog, consecutivo=1)
        self.orden_bog_tec = self._crear_orden(self.bogota, self.tecnica_bog, consecutivo=2)
        self.orden_bar_com = self._crear_orden(self.barranquilla, self.comercial_bar, consecutivo=3)
        self.orden_bar_tec = self._crear_orden(self.barranquilla, self.tecnica_bar, consecutivo=4)

    def _crear_orden(self, sede, area, consecutivo):
        return OrdenCompra.objects.create(
            empresa=self.empresa, sede=sede, area=area, proveedor=self.proveedor,
            plantilla=self.plantilla, fecha="2026-06-01", consecutivo=consecutivo,
        )

    def _consecutivos(self, resp):
        return {row["consecutivo"] for row in resp.json().get("results", resp.json())}

    # ------------------------------------------------------------------
    # Caso 1: alcance=EMPRESA -> ve/opera sobre toda la empresa
    # ------------------------------------------------------------------

    def test_caso1_empresa_list_ve_las_4_ordenes(self):
        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )
        resp = self.api_client.get("/api/v1/compras/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(self._consecutivos(resp), {1, 2, 3, 4})

    def test_caso1_empresa_retrieve_cualquier_orden_permitido(self):
        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="EMPRESA",
        )
        for orden in (self.orden_bog_com, self.orden_bog_tec, self.orden_bar_com, self.orden_bar_tec):
            resp = self.api_client.get(f"/api/v1/compras/{orden.uuid}/")
            self.assertEqual(resp.status_code, status.HTTP_200_OK, f"orden {orden.consecutivo}: {resp.content}")

    # ------------------------------------------------------------------
    # Caso 2: alcance=SEDE, sede=Bogota -> ve/opera solo Bogota
    # ------------------------------------------------------------------

    def test_caso2_sede_bogota_list_ve_solo_bogota(self):
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.bogota])

        resp = self.api_client.get("/api/v1/compras/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(self._consecutivos(resp), {1, 2})

    def test_caso2_sede_bogota_retrieve_orden_bogota_permitido(self):
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.bogota])

        resp = self.api_client.get(f"/api/v1/compras/{self.orden_bog_com.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

    def test_caso2_sede_bogota_retrieve_orden_barranquilla_denegado(self):
        """[CIERRA EL GAP CRITICO DE FASE 2/6] Primera verificacion real de
        HasOrganizationalScope.has_object_permission() en GET por UUID
        directo. Sin este test, este mecanismo llevaba desde ADR-003
        (2026-08-07) sin ninguna cobertura."""
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.bogota])

        resp = self.api_client.get(f"/api/v1/compras/{self.orden_bar_com.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN, resp.content)

    def test_caso2_sede_bogota_update_orden_barranquilla_denegado(self):
        """[Bug de FASE 7, corregido] `HasOrganizationalScope` deniega el
        update via self.get_object() -> check_object_permissions(). Hasta
        el fix de handle_service_error() (apps/tenant/api/mixins.py, ver
        documentacion/FASE7_AISLAMIENTO_ORGANIZACIONAL.md), la denegacion
        real (PermissionDenied) caia al branch generico de esa funcion y
        respondia 500 en vez de 403 -- el bloqueo SI funcionaba incluso
        antes del fix (verificado con el assert de `observaciones` sin
        cambiar), solo el codigo de estado era incorrecto."""
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.bogota])

        resp = self.api_client.patch(
            f"/api/v1/compras/{self.orden_bar_com.uuid}/",
            data={"observaciones": "intento cross-sede"},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN, resp.content)
        self.orden_bar_com.refresh_from_db()
        # Lo que SI importa para aislamiento: la escritura no se aplico.
        self.assertNotEqual(self.orden_bar_com.observaciones, "intento cross-sede")

    def test_caso2_sede_bogota_delete_orden_barranquilla_denegado(self):
        """[Bug de FASE 7, corregido] Mismo caso que el test anterior para
        `OrdenCompraViewSet.destroy()`. La orden NO se elimina."""
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.bogota])

        resp = self.api_client.delete(f"/api/v1/compras/{self.orden_bar_com.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN, resp.content)
        self.assertTrue(OrdenCompra.objects.filter(id=self.orden_bar_com.id).exists())

    def test_caso2_sede_bogota_delete_orden_bogota_permitido(self):
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.bogota])

        resp = self.api_client.delete(f"/api/v1/compras/{self.orden_bog_com.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT, resp.content)
        self.assertFalse(OrdenCompra.objects.filter(id=self.orden_bog_com.id).exists())

    # ------------------------------------------------------------------
    # Caso 3: alcance=AREA, area=Comercial (ambas sedes) -> ve/opera solo
    # Comercial, en cualquiera de las 2 sedes donde el perfil la tiene
    # ------------------------------------------------------------------

    def test_caso3_area_comercial_list_ve_las_2_ordenes_comercial_de_ambas_sedes(self):
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="AREA",
        )
        perfil.sedes_asignadas.set([self.bogota, self.barranquilla])
        perfil.areas_asignadas.set([self.comercial_bog, self.comercial_bar])

        resp = self.api_client.get("/api/v1/compras/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(self._consecutivos(resp), {1, 3})

    def test_caso3_area_comercial_retrieve_tecnica_bogota_denegado(self):
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="AREA",
        )
        perfil.sedes_asignadas.set([self.bogota, self.barranquilla])
        perfil.areas_asignadas.set([self.comercial_bog, self.comercial_bar])

        resp = self.api_client.get(f"/api/v1/compras/{self.orden_bog_tec.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN, resp.content)

    def test_caso3_area_comercial_retrieve_comercial_barranquilla_permitido(self):
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="AREA",
        )
        perfil.sedes_asignadas.set([self.bogota, self.barranquilla])
        perfil.areas_asignadas.set([self.comercial_bog, self.comercial_bar])

        resp = self.api_client.get(f"/api/v1/compras/{self.orden_bar_com.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

    # ------------------------------------------------------------------
    # [Bug de FASE 7, corregido] Las acciones HTMX de offcanvas
    # (render_offcanvas_detalle/render_offcanvas_editar) usaban
    # get_object_or_404() sin check_object_permissions() -- bypaseaban
    # HasOrganizationalScope por completo. Corregido agregando la llamada
    # explicita a self.check_object_permissions() (ver
    # apps/tenant/compras/api/viewsets.py y
    # documentacion/FASE7_AISLAMIENTO_ORGANIZACIONAL.md).
    # ------------------------------------------------------------------

    def test_render_offcanvas_detalle_respeta_has_organizational_scope(self):
        """La API JSON y la accion HTMX de offcanvas ahora coinciden: ambas
        deniegan (403) el mismo recurso fuera del alcance del perfil."""
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.bogota])

        resp_api = self.api_client.get(f"/api/v1/compras/{self.orden_bar_com.uuid}/")
        self.assertEqual(resp_api.status_code, status.HTTP_403_FORBIDDEN, resp_api.content)

        resp_htmx = self.api_client.get(
            f"/api/v1/compras/render-offcanvas/detalle/?uuid={self.orden_bar_com.uuid}"
        )
        self.assertEqual(resp_htmx.status_code, status.HTTP_403_FORBIDDEN, resp_htmx.content)
