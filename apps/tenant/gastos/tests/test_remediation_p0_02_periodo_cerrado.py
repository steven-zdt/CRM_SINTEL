"""
REM P0-02 (docs/remediation/REM-P0-02.md): PeriodoContable.__doc__ afirma
"Bloquea edicion/anulacion de Facturas y Gastos en periodos cerrados", pero
verificar_periodo_cerrado() nunca se invocaba desde `gastos` -- un
DocumentoSoporte podia editarse (PATCH) o anularse libremente con fecha
dentro de un periodo contable ya cerrado.
"""
from datetime import date
from decimal import Decimal

from rest_framework import status

from apps.tenant.contabilidad.models import PeriodoContable
from apps.tenant.empresa.models import Empresa
from apps.tenant.gastos.models import DocumentoSoporte, ResolucionDIAN
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class GastoPeriodoCerradoP0_02Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test Gasto P0-02", nit="900000792", direccion="Calle 1",
        )
        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )
        self.resolucion = ResolucionDIAN.objects.create(
            empresa=self.empresa, numero_resolucion="RES-P002-1", prefijo="GP002",
            rango_desde=1, rango_hasta=1000,
            fecha_resolucion="2026-01-01", fecha_fin="2027-01-01", vigente=True,
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor P0-02", numero_documento="P002-1",
            tipo_documento="NIT",
        )

    def _crear_documento(self, fecha):
        return DocumentoSoporte.objects.create(
            empresa=self.empresa, resolucion_dian=self.resolucion, consecutivo=1,
            fecha=fecha, proveedor=self.proveedor, subtotal=Decimal("1000000"),
            total=Decimal("1000000"), descripcion="Gasto P0-02", categoria_contable="ARRENDAMIENTOS",
        )

    def _cerrar_periodo(self, fecha_inicio, fecha_fin, periodo="2026-01"):
        return PeriodoContable.objects.create(
            empresa=self.empresa, periodo=periodo,
            fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, estado="CERRADO",
        )

    def test_patch_gasto_en_periodo_abierto_es_permitido(self):
        documento = self._crear_documento(date(2026, 6, 15))
        resp = self.api_client.patch(
            f"/api/v1/gastos/{documento.uuid}/", {"descripcion": "Gasto editado"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

    def test_patch_gasto_en_periodo_cerrado_es_rechazado(self):
        self._cerrar_periodo(date(2026, 1, 1), date(2026, 1, 31))
        documento = self._crear_documento(date(2026, 1, 15))
        resp = self.api_client.patch(
            f"/api/v1/gastos/{documento.uuid}/", {"descripcion": "Gasto editado"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

    def test_anular_gasto_en_periodo_abierto_es_permitido(self):
        documento = self._crear_documento(date(2026, 6, 15))
        resp = self.api_client.post(
            f"/api/v1/gastos/{documento.uuid}/anular/", {"motivo": "Error de captura"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

    def test_anular_gasto_en_periodo_cerrado_es_rechazado(self):
        self._cerrar_periodo(date(2026, 1, 1), date(2026, 1, 31))
        documento = self._crear_documento(date(2026, 1, 15))
        resp = self.api_client.post(
            f"/api/v1/gastos/{documento.uuid}/anular/", {"motivo": "Error de captura"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        documento.refresh_from_db()
        self.assertFalse(documento.anulado)
