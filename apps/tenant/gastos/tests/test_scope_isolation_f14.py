"""
Fase F14 (proyecto OSF), "Pruebas de aislamiento organizacional" - ver
docstring completo en apps/tenant/facturas/tests/test_scope_isolation_f14.py
para el contexto transversal. Este archivo cierra el gap para `gastos`:
(1) alcance=SEDE sin sedes asignadas -> frozenset(), ve solo sin-sede; (2)
alcance=SEDE con DOS sedes asignadas -> ve registros de ambas.
"""
from rest_framework import status

from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.gastos.models import DocumentoSoporte, ResolucionDIAN
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class GastoIsolationF14Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F14 Gastos", nit="900000794", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F14 Gastos")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F14 Gastos")
        self.resolucion = ResolucionDIAN.objects.create(
            empresa=self.empresa, numero_resolucion="RESF14", prefijo="GF14",
            rango_desde=1, rango_hasta=1000,
            fecha_resolucion="2026-01-01", fecha_fin="2027-01-01", vigente=True,
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor F14 Gastos", numero_documento="F14-654", tipo_documento="NIT",
        )

    def _crear(self, consecutivo, sede=None):
        return DocumentoSoporte.objects.create(
            empresa=self.empresa, resolucion_dian=self.resolucion, consecutivo=consecutivo,
            fecha="2026-05-01", proveedor=self.proveedor, subtotal=1000, total=1000,
            descripcion="Gasto F14", categoria_contable="ARRENDAMIENTOS", sede=sede,
        )

    def test_alcance_sede_sin_asignaciones_no_ve_ninguna_sede_solo_null_safe(self):
        d_sin = self._crear(1)
        d_a = self._crear(2, sede=self.sede_a)

        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )

        resp = self.api_client.get("/api/v1/gastos/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        ids = {row["id"] for row in resp.json().get("results", resp.json())}
        self.assertIn(d_sin.id, ids)
        self.assertNotIn(d_a.id, ids)

    def test_alcance_sede_con_dos_sedes_asignadas_ve_ambas(self):
        d_a = self._crear(3, sede=self.sede_a)
        d_b = self._crear(4, sede=self.sede_b)
        sede_c = Sede.objects.create(empresa=self.empresa, nombre="Sede C F14 Gastos")
        d_c = self._crear(5, sede=sede_c)

        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.sede_a, self.sede_b])

        resp = self.api_client.get("/api/v1/gastos/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        ids = {row["id"] for row in resp.json().get("results", resp.json())}
        self.assertIn(d_a.id, ids)
        self.assertIn(d_b.id, ids)
        self.assertNotIn(d_c.id, ids)
