"""
Regresion (2026-09-12, hallazgo V-2): PATCH/PUT /api/v1/ventas/{uuid}/
respondia 200 sin persistir ningun cambio -- VentaDetailSerializer
marcaba todos los campos read-only, asi que el UpdateModelMixin por
defecto de ModelViewSet no tenia nada que escribir.
VentaCRUDService.actualizar_venta() ya existia (con guarda de estado
BORRADOR) pero nadie lo invocaba. Tampoco existia ningun boton/flujo
"Editar" en la UI.

Fix: VentaViewSet.partial_update()/update() ahora orquestan explicitamente
via VentaBusinessService.actualizar_venta_borrador() (mismo patron que
ResolucionFacturacionViewSet), y el offcanvas de "Crear" se reutiliza en
modo edicion (render-offcanvas/editar).

Ver docs/remediation/AUDIT_BASELINE_20260912.md hallazgo V-2.
"""
from decimal import Decimal

from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.ventas.models import ItemVenta, Venta
from tests.tenant.base_test import SintelTenantTestCase


class EditarVentaTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Editar Venta SAS", nit="900000962", direccion="Calle EV",
        )
        # SintelTenantTestCase.setup_membership() solo crea TenantMembership
        # (esquema public); IsTenantAdminOrReadOnly exige TenantProfile.rol
        # (esquema tenant) para metodos de escritura (PATCH/PUT/POST/DELETE).
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="EV-CLI-1", razon_social="Cliente EV SAS",
            regimen_tributario="ORDINARIO",
        )
        self.venta = Venta.objects.create(
            empresa=self.empresa, cliente=self.cliente, fecha_emision="2026-06-01",
            numero_factura="EV-VENTA-1", observaciones="Observacion original",
            subtotal=Decimal("100.00"), total_neto=Decimal("100.00"),
            estado=Venta.Estado.BORRADOR,
        )
        ItemVenta.objects.create(
            venta=self.venta, empresa=self.empresa, descripcion="Item original",
            cantidad=Decimal("1.0000"), precio_unitario=Decimal("100.00"),
        )

    def test_patch_persiste_cambios_reales(self):
        """
        Antes del fix: 200 OK pero observaciones/items no cambiaban en BD.
        """
        resp = self.api_client.patch(
            f"/api/v1/ventas/{self.venta.uuid}/",
            {
                "observaciones": "Observacion editada",
                "fecha_vencimiento": "2026-07-15",
                "items": [
                    {"descripcion": "Item editado", "cantidad": "2", "precio_unitario": "150.00", "porcentaje_iva": "19"},
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        self.venta.refresh_from_db()
        self.assertEqual(self.venta.observaciones, "Observacion editada")
        self.assertEqual(str(self.venta.fecha_vencimiento), "2026-07-15")

        items = list(self.venta.items.all())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].descripcion, "Item editado")
        self.assertEqual(items[0].cantidad, Decimal("2.0000"))
        # subtotal/total_neto deben reflejar los items nuevos (2 * 150 = 300,
        # + 19% iva = 357), no seguir en 100 (valor original).
        self.assertEqual(self.venta.subtotal, Decimal("300.00"))
        self.assertEqual(self.venta.total_neto, Decimal("357.00"))

    def test_no_permite_editar_venta_ya_facturada(self):
        self.venta.estado = Venta.Estado.FACTURADA_DIAN
        self.venta.save(update_fields=["estado"])

        resp = self.api_client.patch(
            f"/api/v1/ventas/{self.venta.uuid}/",
            {"observaciones": "No deberia aplicar"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content)

        self.venta.refresh_from_db()
        self.assertEqual(self.venta.observaciones, "Observacion original")

    def test_render_offcanvas_editar_precarga_datos(self):
        resp = self.client.get(
            f"/api/v1/ventas/render-offcanvas/editar/?uuid={self.venta.uuid}"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertNotIn(b"{#", resp.content)
        self.assertNotIn(b"{%", resp.content)
        self.assertIn(b"Editar Venta", resp.content)
        self.assertIn(b"Item original", resp.content)
        # Cliente bloqueado (no editable), mostrado como texto, no <select>.
        self.assertIn(self.cliente.razon_social.encode(), resp.content)
