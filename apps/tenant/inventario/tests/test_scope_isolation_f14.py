"""
Fase F14 (proyecto OSF), "Pruebas de aislamiento organizacional" - ver
docstring completo en apps/tenant/facturas/tests/test_scope_isolation_f14.py
para el contexto transversal. Este archivo cierra el gap para `inventario`
(Kardex, `MovimientoInventario`): (1) alcance=SEDE sin sedes asignadas ->
frozenset(), ve solo sin-sede; (2) alcance=SEDE con DOS sedes asignadas ->
ve movimientos de ambas.
"""
from rest_framework import status

from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.inventario.models import MovimientoInventario, Producto
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class MovimientoIsolationF14Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F14 Inventario", nit="900000795", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F14 Inv")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F14 Inv")
        self.producto = Producto.objects.create(
            empresa=self.empresa, codigo="SKU-F14", nombre="Producto F14",
        )

    def _crear(self, sede=None):
        return MovimientoInventario.objects.create(
            empresa=self.empresa, tipo="ENTRADA_AJUSTE", cantidad=1, sede=sede,
            producto=self.producto,
        )

    def test_alcance_sede_sin_asignaciones_no_ve_ninguna_sede_solo_null_safe(self):
        m_sin = self._crear()
        m_a = self._crear(sede=self.sede_a)

        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )

        resp = self.api_client.get("/api/v1/inventario/movimientos/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        # [MovimientoInventarioListSerializer] "id" expone el UUID, "pk" el entero.
        ids = {row["pk"] for row in resp.json().get("results", resp.json())}
        self.assertIn(m_sin.id, ids)
        self.assertNotIn(m_a.id, ids)

    def test_alcance_sede_con_dos_sedes_asignadas_ve_ambas(self):
        m_a = self._crear(sede=self.sede_a)
        m_b = self._crear(sede=self.sede_b)
        sede_c = Sede.objects.create(empresa=self.empresa, nombre="Sede C F14 Inv")
        m_c = self._crear(sede=sede_c)

        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.sede_a, self.sede_b])

        resp = self.api_client.get("/api/v1/inventario/movimientos/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        ids = {row["pk"] for row in resp.json().get("results", resp.json())}
        self.assertIn(m_a.id, ids)
        self.assertIn(m_b.id, ids)
        self.assertNotIn(m_c.id, ids)
