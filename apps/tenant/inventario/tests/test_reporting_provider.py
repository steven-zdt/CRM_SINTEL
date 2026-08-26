"""
InventarioReportProvider -- regresion real (mision Reporting Hub, loop de
expansion). Datos reales via KardexService.registrar_movimiento() (el SSoT
real de escritura, no creacion directa de MovimientoInventario) -- una
ENTRADA_COMPRA y una SALIDA_VENTA reales, verifica que el dataset
`inventario.movimientos` agrega correctamente por tipo.
"""
from decimal import Decimal

from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from apps.services.reporting.contracts import ReportRequest
from apps.services.reporting.query_engine import ReportQueryEngine
from apps.services.reporting.registry import registry
from apps.tenant.empresa.models import Empresa
from apps.tenant.inventario.models import Producto
from apps.tenant.inventario.services.business_service import KardexService
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class InventarioReportProviderTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Reporting Inventario", nit="900000934", direccion="Calle Kardex",
        )
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")
        self.producto = Producto.objects.create(
            empresa=self.empresa, codigo="RPT-INV-1", nombre="Producto Reporting Inventario", stock_actual=Decimal("0"),
        )

        KardexService.registrar_movimiento(
            empresa_id=self.empresa.id, producto_id=self.producto.id, tipo="ENTRADA_COMPRA",
            cantidad=Decimal("10"), costo_unitario=Decimal("100.00"),
        )
        KardexService.registrar_movimiento(
            empresa_id=self.empresa.id, producto_id=self.producto.id, tipo="SALIDA_VENTA",
            cantidad=Decimal("3"), costo_unitario=Decimal("100.00"),
        )

    def _authenticated_request(self):
        factory = APIRequestFactory()
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.post("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        request.tenant = self.tenant
        request.user, _ = JWTAuthentication().authenticate(request)
        return request

    def test_provider_registrado(self):
        dataset = registry.get_dataset("inventario.movimientos")
        self.assertIsNotNone(dataset)
        self.assertEqual(dataset.owner_app, "inventario")

    def test_movimientos_reales_agregados_por_tipo(self):
        request = self._authenticated_request()
        report_request = ReportRequest(dataset_id="inventario.movimientos", group_by=("tipo",))
        result = ReportQueryEngine().execute(report_request, request)

        rows_by_tipo = {row["tipo"]: row for row in result.rows}
        self.assertEqual(set(rows_by_tipo.keys()), {"ENTRADA_COMPRA", "SALIDA_VENTA"})
        self.assertEqual(rows_by_tipo["ENTRADA_COMPRA"]["cantidad"], 10.0)
        self.assertEqual(rows_by_tipo["ENTRADA_COMPRA"]["costo_total"], 1000.0)
        self.assertEqual(rows_by_tipo["SALIDA_VENTA"]["cantidad"], 3.0)
        self.assertEqual(rows_by_tipo["SALIDA_VENTA"]["costo_total"], 300.0)

    def test_filtro_por_tipo(self):
        request = self._authenticated_request()
        report_request = ReportRequest(dataset_id="inventario.movimientos", filters={"tipo": "ENTRADA_COMPRA"})
        result = ReportQueryEngine().execute(report_request, request)
        self.assertEqual(result.count, 1)
        self.assertEqual(result.rows[0]["cantidad"], 10.0)
