"""
Regresion (2026-09-12): "Ver" en Ventas devolvia 500 silencioso -- el
template offcanvas_detalle_venta.html hacia {% load humanize %} pero
django.contrib.humanize nunca estuvo registrado en INSTALLED_APPS
(config/settings.py). HTMX no hace swap en respuestas no-2xx, asi que el
usuario hacia clic en "Ver" y no pasaba nada, sin ningun error visible.

Fix: reemplazar humanize/intcomma por el filtro currency_cop/format_cop
que ya usa el resto del repo (apps.tenant.core.templatetags.currency_filters).
"""
from decimal import Decimal

from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.ventas.models import ItemVenta, Venta
from tests.tenant.base_test import SintelTenantTestCase


class DetalleVentaOffcanvasTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Detalle Venta SAS", nit="900000961", direccion="Calle DV",
        )
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="DV-CLI-1", razon_social="Cliente DV SAS",
            regimen_tributario="ORDINARIO",
        )
        self.venta = Venta.objects.create(
            empresa=self.empresa, cliente=self.cliente, fecha_emision="2026-06-01",
            numero_factura="DET-VENTA-1", subtotal=Decimal("1250000.00"),
            impuestos=Decimal("237500.00"), total_neto=Decimal("1487500.00"),
        )
        ItemVenta.objects.create(
            venta=self.venta, empresa=self.empresa,
            descripcion="Servicio de consultoria", cantidad=Decimal("1.0000"),
            precio_unitario=Decimal("1250000.00"), porcentaje_iva=Decimal("19.00"),
        )

    def test_ver_detalle_venta_no_devuelve_500(self):
        """
        Antes del fix: 500 (TemplateSyntaxError: 'humanize' is not a
        registered tag library). Despues del fix: 200, con los montos
        formateados y sin fuga de tags de Django sin resolver.
        """
        resp = self.client.get(
            f"/api/v1/ventas/render-offcanvas/detalle/?uuid={self.venta.uuid}"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertNotIn(b"{#", resp.content)
        self.assertNotIn(b"{%", resp.content)
        # format_cop: separador de miles con punto, sin decimales (mismo
        # estilo que ya usa el resto del repo para esta clase de tabla).
        self.assertIn("1.250.000".encode(), resp.content)
        self.assertIn("1.487.500".encode(), resp.content)
