"""
Fase F13 (proyecto OSF), "Resto de aplicaciones (una a la vez)" - primer app:
gastos. Hallazgo colateral de F12: `GastoViewSet` heredaba el mismo gap que
F11 encontro y corrigio en Facturas - `get_qs_detail()` (usado por retrieve/
update/partial_update/destroy/anular via get_object()) solo filtraba por
empresa_id, nunca por sede (a diferencia de get_qs_list(), ya migrado en F7).
Ademas, `render_offcanvas_editar`/`render_offcanvas_detalle` resolvian su
`DocumentoSoporte` objetivo con `get_object_or_404(..., empresa_id=...)`
directo, bypaseando get_queryset() por completo. Y `DocumentoSoporteTableView`
(la grilla HTML real) no aplicaba ningun filtro de sede en absoluto.
"""
from rest_framework import status

from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.gastos.models import DocumentoSoporte, ResolucionDIAN
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class GastoObjectLevelScopeF13Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F13 Gastos", nit="900000787", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F13 Gastos")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F13 Gastos")
        self.resolucion = ResolucionDIAN.objects.create(
            empresa=self.empresa, numero_resolucion="RESF13", prefijo="GF13",
            rango_desde=1, rango_hasta=1000,
            fecha_resolucion="2026-01-01", fecha_fin="2027-01-01", vigente=True,
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor F13 Gastos", numero_documento="F13-654", tipo_documento="NIT",
        )

    def _crear(self, consecutivo, sede=None):
        return DocumentoSoporte.objects.create(
            empresa=self.empresa, resolucion_dian=self.resolucion, consecutivo=consecutivo,
            fecha="2026-05-01", proveedor=self.proveedor, subtotal=1000, total=1000,
            descripcion="Gasto F13", categoria_contable="ARRENDAMIENTOS", sede=sede,
        )

    def _asignar_perfil_sede(self, sedes):
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set(sedes)
        return perfil

    def test_alcance_sede_no_puede_ver_documento_de_otra_sede_por_uuid_directo(self):
        doc_b = self._crear(1, sede=self.sede_b)
        self._asignar_perfil_sede([self.sede_a])

        resp = self.api_client.get(f"/api/v1/gastos/{doc_b.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND, resp.content)

    def test_alcance_sede_puede_ver_documento_sin_sede_null_safe(self):
        doc_sin = self._crear(2)
        self._asignar_perfil_sede([self.sede_a])

        resp = self.api_client.get(f"/api/v1/gastos/{doc_sin.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

    def test_alcance_sede_no_puede_ver_offcanvas_editar_de_otra_sede(self):
        doc_b = self._crear(3, sede=self.sede_b)
        self._asignar_perfil_sede([self.sede_a])

        resp = self.api_client.get(f"/api/v1/gastos/render-offcanvas/editar/?uuid={doc_b.uuid}")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND, resp.content)

    def test_alcance_sede_no_puede_ver_offcanvas_detalle_de_otra_sede(self):
        doc_b = self._crear(4, sede=self.sede_b)
        self._asignar_perfil_sede([self.sede_a])

        resp = self.api_client.get(f"/api/v1/gastos/render-offcanvas/detalle/?uuid={doc_b.uuid}")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND, resp.content)

    def test_alcance_empresa_puede_ver_cualquier_sede(self):
        doc_b = self._crear(5, sede=self.sede_b)
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        resp = self.api_client.get(f"/api/v1/gastos/{doc_b.uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

        resp2 = self.api_client.get(f"/api/v1/gastos/render-offcanvas/detalle/?uuid={doc_b.uuid}")
        self.assertEqual(resp2.status_code, status.HTTP_200_OK, resp2.content)
