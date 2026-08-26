"""
GastosReportProvider -- regresion real (mision Reporting Hub, loop de
expansion). Datos reales: 2 DocumentoSoporte activos (categorias distintas)
+ 1 anulado (no debe contar).
"""
from decimal import Decimal

from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from apps.services.reporting.contracts import ReportRequest
from apps.services.reporting.query_engine import ReportQueryEngine
from apps.services.reporting.registry import registry
from apps.tenant.empresa.models import Empresa
from apps.tenant.gastos.models import DocumentoSoporte, ResolucionDIAN
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class GastosReportProviderTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Reporting Gastos", nit="900000935", direccion="Calle Gastos",
        )
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")
        self.resolucion = ResolucionDIAN.objects.create(
            empresa=self.empresa, numero_resolucion="RES-RPT-1", prefijo="GRPT",
            rango_desde=1, rango_hasta=100,
            fecha_resolucion="2026-01-01", fecha_fin="2027-01-01", vigente=True,
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor Reporting Gastos", numero_documento="900555111", tipo_documento="NIT",
        )
        DocumentoSoporte.objects.create(
            empresa=self.empresa, resolucion_dian=self.resolucion, consecutivo=1,
            fecha="2026-06-01", proveedor=self.proveedor, subtotal=Decimal("500000"), total=Decimal("500000"),
            descripcion="Arriendo RPT", categoria_contable="ARRENDAMIENTOS",
        )
        DocumentoSoporte.objects.create(
            empresa=self.empresa, resolucion_dian=self.resolucion, consecutivo=2,
            fecha="2026-06-02", proveedor=self.proveedor, subtotal=Decimal("200000"), total=Decimal("200000"),
            descripcion="Servicios RPT", categoria_contable="SERVICIOS_PUBLICOS",
        )
        DocumentoSoporte.objects.create(
            empresa=self.empresa, resolucion_dian=self.resolucion, consecutivo=3,
            fecha="2026-06-03", proveedor=self.proveedor, subtotal=Decimal("999999"), total=Decimal("999999"),
            descripcion="Anulado RPT", categoria_contable="ARRENDAMIENTOS", anulado=True,
        )

    def _authenticated_request(self):
        factory = APIRequestFactory()
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.post("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        request.tenant = self.tenant
        request.user, _ = JWTAuthentication().authenticate(request)
        return request

    def test_provider_registrado(self):
        dataset = registry.get_dataset("gastos.resumen")
        self.assertIsNotNone(dataset)
        self.assertEqual(dataset.owner_app, "gastos")

    def test_agregado_por_categoria_excluye_anulado(self):
        request = self._authenticated_request()
        report_request = ReportRequest(dataset_id="gastos.resumen", group_by=("categoria_contable",))
        result = ReportQueryEngine().execute(report_request, request)

        rows_by_categoria = {row["categoria_contable"]: row for row in result.rows}
        self.assertEqual(set(rows_by_categoria.keys()), {"ARRENDAMIENTOS", "SERVICIOS_PUBLICOS"})
        # Solo el documento activo de ARRENDAMIENTOS (500000) -- el anulado (999999) no cuenta.
        self.assertEqual(rows_by_categoria["ARRENDAMIENTOS"]["total"], 500000.0)
        self.assertEqual(rows_by_categoria["SERVICIOS_PUBLICOS"]["total"], 200000.0)

    def test_total_general(self):
        request = self._authenticated_request()
        report_request = ReportRequest(dataset_id="gastos.resumen", group_by=())
        result = ReportQueryEngine().execute(report_request, request)
        self.assertEqual(result.totals["total"], 700000.0)
        self.assertEqual(result.totals["cantidad_documentos"], 2)
