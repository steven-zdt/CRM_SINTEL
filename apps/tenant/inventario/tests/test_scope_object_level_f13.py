"""
Fase F13 (proyecto OSF), "Resto de aplicaciones (una a la vez)" - sub-fase 3:
inventario. Mismo patron de auditoria objeto-por-accion: `MovimientoInventarioViewSet`
tenia un `get_object()` CUSTOM que resolvia `MovimientoInventarioSelector.get_detail()`
solo por empresa_id (afecta retrieve/update/partial_update/destroy). Tambien
`service_movimiento_get_offcanvas_context()` (accion gestor-offcanvas) bypaseaba
el scope de la misma forma.
"""
from rest_framework import status

from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.inventario.models import MovimientoInventario, Producto
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class MovimientoObjectLevelScopeF13Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F13 Inventario", nit="900000789", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F13 Inv")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F13 Inv")
        self.producto = Producto.objects.create(
            empresa=self.empresa, codigo="SKU-F13", nombre="Producto F13",
        )

    def _crear(self, sede=None):
        return MovimientoInventario.objects.create(
            empresa=self.empresa, tipo="ENTRADA_AJUSTE", cantidad=1, sede=sede,
            producto=self.producto,
        )

    def _asignar_perfil_sede(self, sedes):
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set(sedes)
        return perfil

    def test_alcance_sede_no_puede_ver_movimiento_de_otra_sede_por_uuid_directo(self):
        mov_b = self._crear(sede=self.sede_b)
        self._asignar_perfil_sede([self.sede_a])

        resp = self.api_client.get(f"/api/v1/inventario/movimientos/{mov_b.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND, resp.content)

    def test_alcance_sede_puede_ver_movimiento_sin_sede_null_safe(self):
        mov_sin = self._crear()
        self._asignar_perfil_sede([self.sede_a])

        resp = self.api_client.get(f"/api/v1/inventario/movimientos/{mov_sin.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

    def test_alcance_sede_no_puede_ver_offcanvas_de_movimiento_de_otra_sede(self):
        mov_b = self._crear(sede=self.sede_b)
        self._asignar_perfil_sede([self.sede_a])

        resp = self.api_client.get(
            f"/api/v1/inventario/movimientos/gestor-offcanvas/?id={mov_b.uuid}"
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertIsNone(resp.data.get("movimiento"))

    def test_alcance_empresa_puede_ver_cualquier_sede(self):
        mov_b = self._crear(sede=self.sede_b)
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        resp = self.api_client.get(f"/api/v1/inventario/movimientos/{mov_b.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
