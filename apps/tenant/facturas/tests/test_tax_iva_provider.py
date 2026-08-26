"""
FacturasTaxReportProvider -- regresion real (mision Tax Service, FASE 38/39).

Datos reales controlados: una Factura VENTA (IVA generado) y una Factura
COMPRA (IVA descontable), cada una con su FacturaImpuesto real (tipo='IVA').
Verifica que el dataset tax.iva separa generado/descontable correctamente
y que el SALDO_FISCAL_CALCULADO (generado - descontable) es correcto -- no
se afirma "valor a pagar" en ningun lado (ver docs/tax/TAX_BASELINE.md §6).
"""
from decimal import Decimal

from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from apps.services.reporting.contracts import ReportRequest
from apps.services.reporting.query_engine import ReportQueryEngine
from apps.services.reporting.registry import registry
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, FacturaImpuesto
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class TaxIvaProviderTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Tax IVA", nit="900000932", direccion="Calle Tax IVA",
        )
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        factura_venta = Factura.objects.create(
            empresa=self.empresa, numero="FV-TAX-1", prefijo="FV", consecutivo=1,
            tipo=Factura.TipoFactura.FE, estado=Factura.Estado.ACEPTADA, naturaleza=Factura.Naturaleza.VENTA,
            fecha_emision="2026-06-01T10:00:00Z",
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit="900111222", receptor_razon_social="Cliente Tax IVA SAS",
            subtotal=Decimal("1000000.00"), impuestos=Decimal("190000.00"), total=Decimal("1190000.00"),
            cufe="CUFE-TAX-VENTA-1",
        )
        FacturaImpuesto.objects.create(
            factura=factura_venta, empresa=self.empresa, tipo_impuesto=FacturaImpuesto.TipoImpuesto.IVA,
            porcentaje=Decimal("19.00"), base_imponible=Decimal("1000000.00"), valor_impuesto=Decimal("190000.00"),
        )

        factura_compra = Factura.objects.create(
            empresa=self.empresa, numero="FC-TAX-1", prefijo="FC", consecutivo=1,
            tipo=Factura.TipoFactura.FE, estado=Factura.Estado.ACEPTADA, naturaleza=Factura.Naturaleza.COMPRA,
            fecha_emision="2026-06-02T10:00:00Z",
            emisor_nit="900333444", emisor_razon_social="Proveedor Tax IVA SAS",
            receptor_nit=self.empresa.nit, receptor_razon_social=self.empresa.razon_social,
            subtotal=Decimal("400000.00"), impuestos=Decimal("76000.00"), total=Decimal("476000.00"),
            cufe="CUFE-TAX-COMPRA-1",
        )
        FacturaImpuesto.objects.create(
            factura=factura_compra, empresa=self.empresa, tipo_impuesto=FacturaImpuesto.TipoImpuesto.IVA,
            porcentaje=Decimal("19.00"), base_imponible=Decimal("400000.00"), valor_impuesto=Decimal("76000.00"),
        )

        # Factura rechazada con IVA -- NO debe contar (estado != ACEPTADA).
        factura_rechazada = Factura.objects.create(
            empresa=self.empresa, numero="FV-TAX-2", prefijo="FV", consecutivo=2,
            tipo=Factura.TipoFactura.FE, estado=Factura.Estado.RECHAZADA, naturaleza=Factura.Naturaleza.VENTA,
            fecha_emision="2026-06-03T10:00:00Z",
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit="900111222", receptor_razon_social="Cliente Tax IVA SAS",
            subtotal=Decimal("500000.00"), impuestos=Decimal("95000.00"), total=Decimal("595000.00"),
            cufe="CUFE-TAX-RECHAZADA-1",
        )
        FacturaImpuesto.objects.create(
            factura=factura_rechazada, empresa=self.empresa, tipo_impuesto=FacturaImpuesto.TipoImpuesto.IVA,
            porcentaje=Decimal("19.00"), base_imponible=Decimal("500000.00"), valor_impuesto=Decimal("95000.00"),
        )

    def _authenticated_request(self):
        factory = APIRequestFactory()
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.post("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        request.tenant = self.tenant
        request.user, _ = JWTAuthentication().authenticate(request)
        return request

    def test_provider_registrado(self):
        dataset = registry.get_dataset("tax.iva")
        self.assertIsNotNone(dataset)
        self.assertEqual(dataset.owner_app, "facturas")

    def test_iva_generado_y_descontable_separados_correctamente(self):
        request = self._authenticated_request()
        report_request = ReportRequest(dataset_id="tax.iva", group_by=("naturaleza",), measures=("base_imponible", "valor_iva"))
        result = ReportQueryEngine().execute(report_request, request)

        rows_by_naturaleza = {row["naturaleza"]: row for row in result.rows}
        self.assertEqual(set(rows_by_naturaleza.keys()), {"VENTA", "COMPRA"})
        self.assertEqual(rows_by_naturaleza["VENTA"]["valor_iva"], 190000.0)
        self.assertEqual(rows_by_naturaleza["COMPRA"]["valor_iva"], 76000.0)

    def test_factura_rechazada_no_cuenta(self):
        request = self._authenticated_request()
        report_request = ReportRequest(dataset_id="tax.iva", filters={"naturaleza": "VENTA"})
        result = ReportQueryEngine().execute(report_request, request)
        total_iva_venta = sum(row["valor_iva"] for row in result.rows)
        self.assertEqual(total_iva_venta, 190000.0)  # NO incluye los 95000 de la rechazada

    def test_saldo_fiscal_calculado_sin_group_by(self):
        request = self._authenticated_request()
        report_request = ReportRequest(dataset_id="tax.iva", group_by=(), measures=("valor_iva",))
        result = ReportQueryEngine().execute(report_request, request)

        self.assertEqual(result.totals["iva_generado"], 190000.0)
        self.assertEqual(result.totals["iva_descontable"], 76000.0)
        self.assertEqual(result.totals["saldo_fiscal_calculado"], 114000.0)
