"""
Fase F7 (proyecto OSF), "Migrar Selectors a scope-aware" - DocumentoSoporte,
3/6 apps candidatas fuertes (F6): el campo `sede` ya existia (DT-SEDE-01)
pero nunca se usaba para filtrar. NULL-safe: el 100% de los DocumentoSoporte
reales tiene sede=NULL hoy.
"""
from rest_framework import status

from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.gastos.models import DocumentoSoporte, ResolucionDIAN
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class GastosScopeSelectorsF7Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F7 Gastos", nit="900000778", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F7 Gastos")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F7 Gastos")
        self.resolucion = ResolucionDIAN.objects.create(
            empresa=self.empresa, numero_resolucion="RESF7", prefijo="GF7",
            rango_desde=1, rango_hasta=1000,
            fecha_resolucion="2026-01-01", fecha_fin="2027-01-01", vigente=True,
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor F7 Gastos", numero_documento="F7-654", tipo_documento="NIT",
        )

    def _crear(self, consecutivo, sede=None):
        return DocumentoSoporte.objects.create(
            empresa=self.empresa, resolucion_dian=self.resolucion, consecutivo=consecutivo,
            fecha="2026-05-01", proveedor=self.proveedor, subtotal=1000, total=1000,
            descripcion="Gasto F7", categoria_contable="ARRENDAMIENTOS", sede=sede,
        )

    def test_alcance_sede_ve_sin_sede_y_su_sede_pero_no_la_de_otra(self):
        d_sin = self._crear(1)
        d_a = self._crear(2, sede=self.sede_a)
        d_b = self._crear(3, sede=self.sede_b)

        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.sede_a])

        resp = self.api_client.get("/api/v1/gastos/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        ids = {row["id"] for row in resp.json().get("results", resp.json())}
        self.assertIn(d_sin.id, ids)
        self.assertIn(d_a.id, ids)
        self.assertNotIn(d_b.id, ids)

    def test_alcance_empresa_sigue_viendo_todo(self):
        self._crear(1, sede=self.sede_a)
        self._crear(2, sede=self.sede_b)
        self._crear(3)

        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        resp = self.api_client.get("/api/v1/gastos/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(len(resp.json().get("results", resp.json())), 3)
