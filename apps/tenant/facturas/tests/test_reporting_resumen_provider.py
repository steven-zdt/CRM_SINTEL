"""
FacturasResumenReportProvider -- regresion real (mision Reporting Hub, loop
de expansion). A diferencia de tax.iva (solo ACEPTADA), facturas.resumen
debe contar TODOS los estados -- por eso incluye a proposito una factura
RECHAZADA y verifica que SI aparece (comportamiento opuesto al de tax.iva,
cubierto en test_tax_iva_provider.py::test_factura_rechazada_no_cuenta).
"""
from decimal import Decimal

from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from apps.services.reporting.contracts import ReportRequest
from apps.services.reporting.query_engine import ReportQueryEngine
from apps.services.reporting.registry import registry
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class FacturasResumenProviderTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Reporting Facturas", nit="900000936", direccion="Calle Facturas RPT",
        )
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        Factura.objects.create(
            empresa=self.empresa, numero="FV-RPT-1", prefijo="FV", consecutivo=1,
            tipo=Factura.TipoFactura.FE, estado=Factura.Estado.ACEPTADA, naturaleza=Factura.Naturaleza.VENTA,
            fecha_emision="2026-06-01T10:00:00Z",
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit="900111222", receptor_razon_social="Cliente RPT SAS",
            subtotal=Decimal("1000000.00"), impuestos=Decimal("190000.00"), total=Decimal("1190000.00"),
            cufe="CUFE-RPT-VENTA-1",
        )
        Factura.objects.create(
            empresa=self.empresa, numero="FC-RPT-1", prefijo="FC", consecutivo=1,
            tipo=Factura.TipoFactura.FE, estado=Factura.Estado.ACEPTADA, naturaleza=Factura.Naturaleza.COMPRA,
            fecha_emision="2026-06-02T10:00:00Z",
            emisor_nit="900333444", emisor_razon_social="Proveedor RPT SAS",
            receptor_nit=self.empresa.nit, receptor_razon_social=self.empresa.razon_social,
            subtotal=Decimal("400000.00"), impuestos=Decimal("76000.00"), total=Decimal("476000.00"),
            cufe="CUFE-RPT-COMPRA-1",
        )
        # A diferencia de tax.iva: esta SI debe contar en facturas.resumen.
        Factura.objects.create(
            empresa=self.empresa, numero="FV-RPT-2", prefijo="FV", consecutivo=2,
            tipo=Factura.TipoFactura.FE, estado=Factura.Estado.RECHAZADA, naturaleza=Factura.Naturaleza.VENTA,
            fecha_emision="2026-06-03T10:00:00Z",
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit="900111222", receptor_razon_social="Cliente RPT SAS",
            subtotal=Decimal("500000.00"), impuestos=Decimal("95000.00"), total=Decimal("595000.00"),
            cufe="CUFE-RPT-RECHAZADA-1",
        )

    def _authenticated_request(self):
        factory = APIRequestFactory()
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.post("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        request.tenant = self.tenant
        request.user, _ = JWTAuthentication().authenticate(request)
        return request

    def test_provider_registrado(self):
        dataset = registry.get_dataset("facturas.resumen")
        self.assertIsNotNone(dataset)
        self.assertEqual(dataset.owner_app, "facturas")

    def test_agregado_por_estado_incluye_rechazada(self):
        request = self._authenticated_request()
        report_request = ReportRequest(dataset_id="facturas.resumen", group_by=("estado",))
        result = ReportQueryEngine().execute(report_request, request)

        rows_by_estado = {row["estado"]: row for row in result.rows}
        self.assertEqual(set(rows_by_estado.keys()), {"ACEPTADA", "RECHAZADA"})
        self.assertEqual(rows_by_estado["ACEPTADA"]["cantidad_documentos"], 2)
        self.assertEqual(rows_by_estado["RECHAZADA"]["cantidad_documentos"], 1)
        self.assertEqual(rows_by_estado["RECHAZADA"]["total"], 595000.0)

    def test_total_general_suma_las_tres(self):
        request = self._authenticated_request()
        report_request = ReportRequest(dataset_id="facturas.resumen", group_by=())
        result = ReportQueryEngine().execute(report_request, request)
        self.assertEqual(result.totals["cantidad_documentos"], 3)
        self.assertEqual(result.totals["total"], 1190000.0 + 476000.0 + 595000.0)

    def test_filtro_por_naturaleza(self):
        request = self._authenticated_request()
        report_request = ReportRequest(dataset_id="facturas.resumen", group_by=(), filters={"naturaleza": "COMPRA"})
        result = ReportQueryEngine().execute(report_request, request)
        self.assertEqual(result.totals["cantidad_documentos"], 1)
        self.assertEqual(result.totals["total"], 476000.0)
