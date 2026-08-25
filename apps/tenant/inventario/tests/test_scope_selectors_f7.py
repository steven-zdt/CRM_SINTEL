"""
Fase F7 (proyecto OSF), "Migrar Selectors a scope-aware" - MovimientoInventario,
4/6 apps candidatas fuertes (F6): el campo `sede` ya existia (DT-SEDE-05)
pero nunca se usaba para filtrar. NULL-safe: el 100% de los
MovimientoInventario reales tiene sede=NULL hoy.
"""
from rest_framework import status

from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.inventario.models import MovimientoInventario, Producto
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class InventarioScopeSelectorsF7Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F7 Inventario", nit="900000779", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F7 Inv")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F7 Inv")
        self.producto = Producto.objects.create(
            empresa=self.empresa, codigo="SKU-F7", nombre="Producto F7",
        )

    def _crear(self, sede=None):
        return MovimientoInventario.objects.create(
            empresa=self.empresa, tipo="ENTRADA_AJUSTE", cantidad=1, sede=sede,
            producto=self.producto,
        )

    def test_alcance_sede_ve_sin_sede_y_su_sede_pero_no_la_de_otra(self):
        m_sin = self._crear()
        m_a = self._crear(sede=self.sede_a)
        m_b = self._crear(sede=self.sede_b)

        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.sede_a])

        resp = self.api_client.get("/api/v1/inventario/movimientos/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        # [MovimientoInventarioListSerializer] "id" expone el UUID (convencion
        # del proyecto), el PK entero se expone aparte como "pk".
        ids = {row["pk"] for row in resp.json().get("results", resp.json())}
        self.assertIn(m_sin.id, ids)
        self.assertIn(m_a.id, ids)
        self.assertNotIn(m_b.id, ids)

    def test_alcance_empresa_sigue_viendo_todo(self):
        self._crear(sede=self.sede_a)
        self._crear(sede=self.sede_b)
        self._crear()

        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        resp = self.api_client.get("/api/v1/inventario/movimientos/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(len(resp.json().get("results", resp.json())), 3)
