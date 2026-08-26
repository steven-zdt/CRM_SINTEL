"""
Frontend del Reporting Hub para Ventas -- regresion real (mision Reporting
Hub Frontend, FASE 34).

Cubre:
1. Las vistas HTML (VentaReportesContainerView, VentaReportesView) renderizan
   con datos reales, incluyendo los tres estados (datos, vacio, prohibido).
2. El endpoint GET /api/v1/reporting/export/ funciona con `export_format`
   (regresion del bug real encontrado en vivo: `?format=csv/xlsx` colisiona
   con la negociacion de contenido propia de DRF -- URL_FORMAT_OVERRIDE --
   y DefaultContentNegotiation.filter_renderers() levantaba Http404 ANTES
   de que la vista se ejecutara. Confirmado en vivo antes/despues del fix).
"""

from django.test import Client
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.ventas.models import Venta
from tests.tenant.base_test import SintelTenantTestCase


class VentaReportesFrontendTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Reportes FE", nit="900000931", direccion="Calle Reportes FE",
        )
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="RPTFE-1", razon_social="Cliente Reportes FE", regimen_tributario="ORDINARIO",
        )
        Venta.objects.create(
            empresa=self.empresa, cliente=self.cliente, fecha_emision="2026-06-01",
            estado="BORRADOR", numero_factura="RPTFE-V-1", subtotal="500.00", impuestos="95.00", total_neto="595.00",
        )

        # Cliente HTML con sesion real (LoginRequiredMixin).
        self.html_client = Client(HTTP_HOST=self.domain.domain)
        self.html_client.force_login(self.user)

        access = RefreshToken.for_user(self.user).access_token
        self.jwt_token = str(access)

    def test_container_view_responde_200_y_contiene_el_formulario(self):
        resp = self.html_client.get("/ui/ventas/reportes/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn(b'id="filtros-reportes-ventas"', resp.content)
        self.assertIn(b'id="reportes-ventas-panel"', resp.content)

    def test_tabla_view_con_datos_reales_muestra_kpi_y_fila(self):
        resp = self.html_client.get("/ui/ventas/reportes/tabla/?group_by=estado")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.content.decode()
        self.assertIn("BORRADOR", body)
        self.assertIn("595", body)  # total real (aparece en KPI y en la fila)
        self.assertNotIn("Sin permisos", body)
        self.assertNotIn("No hay datos", body)

    def test_tabla_view_sin_datos_muestra_estado_vacio(self):
        resp = self.html_client.get("/ui/ventas/reportes/tabla/?estado=ANULADA")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("No hay datos", resp.content.decode())

    def test_export_get_con_export_format_csv_funciona(self):
        """Regresion del bug real: ?format=csv colisionaba con DRF
        (URL_FORMAT_OVERRIDE) y devolvia 404 antes de ejecutar la vista."""
        resp = self.html_client.get(
            "/api/v1/reporting/export/",
            {"dataset_id": "ventas.resumen", "group_by": "estado", "export_format": "csv"},
            HTTP_AUTHORIZATION=f"Bearer {self.jwt_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp["Content-Type"], "text/csv")
        body = resp.content.decode("utf-8-sig")
        self.assertIn("BORRADOR", body)
        self.assertIn("TOTAL", body)

    def test_export_get_con_format_a_secas_ya_no_se_usa_pero_no_debe_dar_404_silencioso(self):
        """No-regresion inversa: si algun consumidor viejo todavia manda
        ?format=csv (nombre incorrecto), DRF lo interpreta como su propio
        parametro de negociacion de contenido y responde 404 -- esto es
        comportamiento de DRF, no un bug de esta vista, pero se deja
        documentado aqui para que no vuelva a sorprender a nadie."""
        resp = self.html_client.get(
            "/api/v1/reporting/export/",
            {"dataset_id": "ventas.resumen", "format": "csv"},
            HTTP_AUTHORIZATION=f"Bearer {self.jwt_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_export_get_xlsx_produce_un_archivo_excel_real(self):
        resp = self.html_client.get(
            "/api/v1/reporting/export/",
            {"dataset_id": "ventas.resumen", "export_format": "xlsx"},
            HTTP_AUTHORIZATION=f"Bearer {self.jwt_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(
            resp["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertGreater(len(resp.content), 0)
