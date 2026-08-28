"""
REM P0-02 (docs/remediation/REM-P0-02.md): PeriodoContable.__doc__ afirma
"Bloquea edicion/anulacion de Facturas y Gastos en periodos cerrados", pero
verificar_periodo_cerrado() nunca se invocaba desde `facturas` -- una factura
podia editarse (PATCH) o anularse (cambiar-estado -> ANULADA) libremente con
fecha_emision dentro de un periodo contable ya cerrado.
"""
from datetime import date

from rest_framework import status

from apps.tenant.contabilidad.models import PeriodoContable
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class FacturaPeriodoCerradoP0_02Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test P0-02", nit="900000791", direccion="Calle 1",
        )
        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )

    def _crear_factura(self, numero, fecha_emision, estado=Factura.Estado.ACEPTADA):
        return Factura.objects.create(
            empresa=self.empresa, numero=numero, consecutivo=1,
            fecha_emision=fecha_emision,
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit="123", receptor_razon_social="Cliente P0-02",
            estado=estado,
        )

    def _cerrar_periodo(self, fecha_inicio, fecha_fin, periodo="2026-01"):
        return PeriodoContable.objects.create(
            empresa=self.empresa, periodo=periodo,
            fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, estado="CERRADO",
        )

    def test_patch_factura_en_periodo_abierto_es_permitido(self):
        factura = self._crear_factura("FA-P002-ABIERTO", "2026-06-15T00:00:00Z")
        resp = self.api_client.patch(
            f"/api/v1/facturas/{factura.uuid}/", {"observaciones": "nota"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

    def test_patch_factura_en_periodo_cerrado_es_rechazado(self):
        self._cerrar_periodo(date(2026, 1, 1), date(2026, 1, 31))
        factura = self._crear_factura("FA-P002-CERRADO", "2026-01-15T00:00:00Z")
        resp = self.api_client.patch(
            f"/api/v1/facturas/{factura.uuid}/", {"observaciones": "nota"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

    def test_anular_factura_en_periodo_abierto_es_permitido(self):
        factura = self._crear_factura("FA-P002-ANULA-OK", "2026-06-15T00:00:00Z")
        resp = self.api_client.post(
            f"/api/v1/facturas/{factura.uuid}/cambiar-estado/", {"estado": "ANULADA"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

    def test_anular_factura_en_periodo_cerrado_es_rechazado(self):
        self._cerrar_periodo(date(2026, 1, 1), date(2026, 1, 31))
        factura = self._crear_factura("FA-P002-ANULA-BLOQ", "2026-01-15T00:00:00Z")
        resp = self.api_client.post(
            f"/api/v1/facturas/{factura.uuid}/cambiar-estado/", {"estado": "ANULADA"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        factura.refresh_from_db()
        self.assertNotEqual(factura.estado, Factura.Estado.ANULADA)
