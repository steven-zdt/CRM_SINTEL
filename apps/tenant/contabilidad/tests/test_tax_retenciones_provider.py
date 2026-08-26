"""
ContabilidadReportProvider (dataset tax.retenciones) -- regresion real
(mision Tax Service, FASE 38/39).

Datos reales via RetencionesService (el SSoT real, no fabricados a mano
saltandose el servicio): RETEFUENTE + RETEICA en una COMPRA (practicada),
mas una reversa real de la RETEFUENTE. Verifica que el dataset da el NETO
correcto (bruto - reversado), mismo criterio que
RetencionesService.total_retenciones_por_documento().
"""
from decimal import Decimal

from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from apps.services.reporting.contracts import ReportRequest
from apps.services.reporting.query_engine import ReportQueryEngine
from apps.services.reporting.registry import registry
from apps.tenant.contabilidad.services.retenciones_service import RetencionesService
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class TaxRetencionesProviderTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Tax Retenciones", nit="900000933", direccion="Calle Tax Ret",
        )
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        self.retefuente = RetencionesService.crear_retencion(
            tipo="RETEFUENTE", porcentaje=Decimal("4.00"), base=Decimal("1000000.00"),
            documento_origen_app="gastos", documento_origen_modelo="DocumentoSoporte", documento_origen_id=1,
            naturaleza="COMPRA", empresa=self.empresa,
        )
        RetencionesService.crear_retencion(
            tipo="RETEICA", porcentaje=Decimal("1.00"), base=Decimal("1000000.00"),
            documento_origen_app="gastos", documento_origen_modelo="DocumentoSoporte", documento_origen_id=1,
            naturaleza="COMPRA", empresa=self.empresa,
        )
        RetencionesService.crear_retencion(
            tipo="RETEFUENTE", porcentaje=Decimal("3.50"), base=Decimal("500000.00"),
            documento_origen_app="facturas", documento_origen_modelo="Factura", documento_origen_id=99,
            naturaleza="VENTA", empresa=self.empresa,
        )
        # Reversa real de la primera RETEFUENTE (ej. nota credito).
        RetencionesService.reversar_retencion(
            self.retefuente, documento_reversada_app="gastos",
            documento_reversada_modelo="DocumentoSoporte", documento_reversada_id=1,
            empresa=self.empresa,
        )

    def _authenticated_request(self):
        factory = APIRequestFactory()
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.post("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        request.tenant = self.tenant
        request.user, _ = JWTAuthentication().authenticate(request)
        return request

    def test_provider_registrado(self):
        dataset = registry.get_dataset("tax.retenciones")
        self.assertIsNotNone(dataset)
        self.assertEqual(dataset.owner_app, "contabilidad")

    def test_retefuente_neta_de_reversa(self):
        """La RETEFUENTE original ($40,000) fue reversada -- el neto debe
        ser $0 (bruto) + la VENTA de $17,500 = $17,500 total, no $57,500."""
        request = self._authenticated_request()
        report_request = ReportRequest(dataset_id="tax.retenciones", filters={"tipo": "RETEFUENTE"})
        result = ReportQueryEngine().execute(report_request, request)
        total_retefuente = sum(row["monto"] for row in result.rows)
        self.assertEqual(total_retefuente, 17500.0)  # solo la VENTA, la COMPRA reversada neteo a 0

    def test_reteica_no_afectada_por_la_reversa(self):
        request = self._authenticated_request()
        report_request = ReportRequest(dataset_id="tax.retenciones", filters={"tipo": "RETEICA"})
        result = ReportQueryEngine().execute(report_request, request)
        total_reteica = sum(row["monto"] for row in result.rows)
        self.assertEqual(total_reteica, 10000.0)  # 1% de 1,000,000, sin reversa

    def test_agrupado_por_naturaleza(self):
        request = self._authenticated_request()
        report_request = ReportRequest(dataset_id="tax.retenciones", group_by=("naturaleza",), measures=("monto",))
        result = ReportQueryEngine().execute(report_request, request)
        rows_by_naturaleza = {row["naturaleza"]: row["monto"] for row in result.rows}
        # COMPRA (practicada): RETEICA 10,000 + RETEFUENTE neta 0 = 10,000
        self.assertEqual(rows_by_naturaleza["COMPRA"], 10000.0)
        # VENTA (sufrida): RETEFUENTE 17,500
        self.assertEqual(rows_by_naturaleza["VENTA"], 17500.0)
