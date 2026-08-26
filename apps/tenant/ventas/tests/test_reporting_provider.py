"""
VentasReportProvider -- regresion real (mision Reporting Hub, FASE 33/34).

Prueba con datos reales (no mocks) que:
1. El provider queda registrado en el ReportRegistry real via
   VentasConfig.ready() -- sin re-registrar nada aqui.
2. ReportQueryEngine.execute() contra una Venta real produce agregados
   correctos.
3. El Scope Engine (FASE 10/11) bloquea un filtro `sede` fuera del alcance
   de un perfil SEDE-scoped, y permite uno dentro de su alcance -- probado
   sobre un dataset (`ventas.resumen`) cuyo modelo NO tiene campo `sede`,
   para demostrar que la interseccion ocurre en el Scope Engine, no
   depende de que el Provider filtre por sede.
"""
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from apps.services.reporting.contracts import ReportRequest
from apps.services.reporting.query_engine import ReportQueryEngine
from apps.services.reporting.registry import registry
from apps.services.reporting.scope import ScopeViolationError
from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.ventas.models import Venta
from tests.tenant.base_test import SintelTenantTestCase


class VentasReportProviderTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Reporting Test", nit="900000930", direccion="Calle Reporting",
        )
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="RPT-1", razon_social="Cliente Reporting", regimen_tributario="ORDINARIO",
        )
        Venta.objects.create(
            empresa=self.empresa, cliente=self.cliente, fecha_emision="2026-06-01",
            estado="BORRADOR", numero_factura="RPT-V-1", subtotal="100.00", impuestos="19.00", total_neto="119.00",
        )
        Venta.objects.create(
            empresa=self.empresa, cliente=self.cliente, fecha_emision="2026-06-02",
            estado="BORRADOR", numero_factura="RPT-V-2", subtotal="200.00", impuestos="38.00", total_neto="238.00",
        )

    def _authenticated_request(self, alcance="EMPRESA", sedes_asignadas=None):
        TenantProfile.objects.filter(user=self.user).delete()
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance=alcance,
        )
        if sedes_asignadas:
            perfil.sedes_asignadas.set(sedes_asignadas)

        factory = APIRequestFactory()
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.post("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        request.tenant = self.tenant
        request.user, _ = JWTAuthentication().authenticate(request)
        return request

    def test_provider_queda_registrado_via_appconfig_ready(self):
        """No re-registra nada -- confirma que VentasConfig.ready() ya lo hizo."""
        dataset = registry.get_dataset("ventas.resumen")
        self.assertIsNotNone(dataset)
        self.assertEqual(dataset.owner_app, "ventas")
        self.assertIsNotNone(registry.get_provider("ventas.resumen"))

    def test_query_real_agrega_correctamente(self):
        request = self._authenticated_request(alcance="EMPRESA")
        report_request = ReportRequest(
            dataset_id="ventas.resumen",
            group_by=("estado",),
            measures=("cantidad_ventas", "subtotal", "impuestos", "total"),
        )
        result = ReportQueryEngine().execute(report_request, request)

        self.assertEqual(len(result.rows), 1)
        row = result.rows[0]
        self.assertEqual(row["estado"], "BORRADOR")
        self.assertEqual(row["cantidad_ventas"], 2)
        self.assertEqual(row["subtotal"], 300.0)
        self.assertEqual(row["impuestos"], 57.0)
        self.assertEqual(row["total"], 357.0)
        self.assertEqual(result.totals["total"], 357.0)

    def test_sede_scope_bloquea_filtro_fuera_de_alcance(self):
        sede_propia = Sede.objects.create(empresa=self.empresa, nombre="Sede Propia RPT")
        sede_ajena = Sede.objects.create(empresa=self.empresa, nombre="Sede Ajena RPT")
        request = self._authenticated_request(alcance="SEDE", sedes_asignadas=[sede_propia])

        report_request = ReportRequest(dataset_id="ventas.resumen", filters={"sede": sede_ajena.id})
        with self.assertRaises(ScopeViolationError):
            ReportQueryEngine().execute(report_request, request)

    def test_sede_scope_permite_filtro_dentro_de_alcance(self):
        sede_propia = Sede.objects.create(empresa=self.empresa, nombre="Sede Propia RPT 2")
        request = self._authenticated_request(alcance="SEDE", sedes_asignadas=[sede_propia])

        report_request = ReportRequest(dataset_id="ventas.resumen", filters={"sede": sede_propia.id})
        # No debe lanzar ScopeViolationError -- Venta no tiene campo `sede`
        # asi que los datos no se filtran por sede, pero el Scope Engine
        # debe permitir la solicitud (esta dentro del alcance del perfil).
        result = ReportQueryEngine().execute(report_request, request)
        self.assertGreaterEqual(result.count, 0)
