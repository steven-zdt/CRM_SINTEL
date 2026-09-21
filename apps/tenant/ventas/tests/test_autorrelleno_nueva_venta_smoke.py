"""
Prueba de humo (HTTP real) del autorrelleno de "Nueva Venta" al vincular una
Factura existente ANTES de guardar (FST-375 secc. 21).

Bug reportado: al seleccionar una Factura en el buscador del formulario de
creacion, los campos (cliente, fechas, items) no se autorrellenaban -- solo
se guardaba el UUID pendiente para vincular despues de crear la Venta
(venta_editor.js::confirmarSeleccion, rama "modo creacion").

Fix: `venta_editor.js::autorrellenarDesdeFactura()` (nuevo) llama a
`Sintel.Ventas.API.obtenerFacturaParaAutorrelleno()` (nuevo, en
ventas.api.js), que compone dos llamadas ya existentes:
    1. GET /api/v1/facturas/{uuid}/       -- cabecera (cliente_uuid,
       receptor_nit, fecha_emision, fecha_vencimiento, forma_pago,
       medio_pago_codigo, id)
    2. GET /api/v1/facturas/items-factura/?factura=<id> -- items (descripcion,
       cantidad, valor_unitario, porcentaje_iva)

Esta suite no puede ejecutar el JS en un navegador (sin entorno grafico en
esta sesion) -- es una prueba de humo del CONTRATO HTTP real que ese JS
consume: si estos dos endpoints no devuelven exactamente estos campos con
estos valores, el autorrelleno no puede funcionar sin importar el JS.

De paso cubre un segundo bug encontrado en la misma revision:
`ver_detalle_factura.js` construia la URL de items con
`FACTURAS_API_BASE.replace('/facturas', '/items-factura')` ->
'/api/v1/items-factura' (404 real, ruta inexistente) en vez de
'/api/v1/facturas/items-factura' (la ruta real, ver
apps/tenant/facturas/api/urls.py). Este test verifica la ruta REAL que
ambos JS (venta_editor.js y ver_detalle_factura.js, ya corregido) deben usar.
"""
from decimal import Decimal

from rest_framework import status

from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, ItemFactura
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class AutorrellenoNuevaVentaSmokeTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Autorrelleno", nit="900555111", direccion="Calle AR",
        )
        TenantProfile.objects.get_or_create(
            user=self.user, empresa=self.empresa,
            defaults={"rol": "ADMIN", "alcance": "EMPRESA", "cargo": "Admin"},
        )
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900860947", razon_social="Focus electronic security sistem S.A.S",
            regimen_tributario="ORDINARIO",
        )
        self.factura = Factura.objects.create(
            empresa=self.empresa, numero="FST 375", prefijo="FST", consecutivo=375,
            fecha_emision="2026-06-20T10:18:00Z", fecha_vencimiento="2026-07-20",
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit="900860947", receptor_razon_social="Focus electronic security sistem S.A.S",
            cliente_uuid=self.cliente.uuid,
            naturaleza=Factura.Naturaleza.VENTA, estado=Factura.Estado.ACEPTADA,
            forma_pago="Credito", medio_pago_codigo="42",
        )
        ItemFactura.objects.create(
            empresa=self.empresa, factura=self.factura,
            descripcion="SERVICIO MANO OBRA INSTALACION PP241173",
            cantidad=Decimal("1.00"), valor_unitario=Decimal("4319257.00"),
            porcentaje_iva=Decimal("19.00"), valor_iva=Decimal("820658.83"),
            subtotal=Decimal("4319257.00"), total=Decimal("5139915.83"),
        )

    def test_smoke_detalle_factura_trae_los_campos_que_el_autorrelleno_necesita(self):
        resp = self.api_client.get(f"/api/v1/facturas/{self.factura.uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        data = resp.json()

        self.assertEqual(data["id"], self.factura.id)
        self.assertEqual(data["cliente_uuid"], str(self.cliente.uuid))
        self.assertEqual(data["receptor_nit"], "900860947")
        self.assertEqual(str(data["fecha_emision"])[:10], "2026-06-20")
        self.assertEqual(data["fecha_vencimiento"], "2026-07-20")
        self.assertEqual(data["forma_pago"], "Credito")
        self.assertEqual(data["medio_pago_codigo"], "42")

    def test_smoke_ruta_real_de_items_factura_es_la_anidada_bajo_facturas(self):
        """Confirma la ruta que ambos JS (venta_editor.js y
        ver_detalle_factura.js) deben usar -- la version rota
        ('/api/v1/items-factura/') debe dar 404."""
        resp_correcta = self.api_client.get(
            f"/api/v1/facturas/items-factura/?factura={self.factura.id}"
        )
        self.assertEqual(resp_correcta.status_code, status.HTTP_200_OK, resp_correcta.content)

        resp_rota = self.api_client.get(f"/api/v1/items-factura/?factura={self.factura.id}")
        self.assertEqual(resp_rota.status_code, status.HTTP_404_NOT_FOUND)

    def test_smoke_items_factura_trae_los_campos_que_el_autorrelleno_necesita(self):
        resp = self.api_client.get(f"/api/v1/facturas/items-factura/?factura={self.factura.id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        body = resp.json()
        items = body.get("results", body)
        self.assertEqual(len(items), 1)

        item = items[0]
        self.assertEqual(item["descripcion"], "SERVICIO MANO OBRA INSTALACION PP241173")
        self.assertEqual(Decimal(str(item["cantidad"])), Decimal("1.00"))
        self.assertEqual(Decimal(str(item["valor_unitario"])), Decimal("4319257.00"))
        self.assertEqual(Decimal(str(item["porcentaje_iva"])), Decimal("19.00"))

    def test_smoke_porcentaje_iva_viaja_como_string_decimal_no_entero(self):
        """
        Bug real reportado (2026-09-18): venta_editor.js::crearFilaItem()
        comparaba `porcentaje_iva` con '=== "19"' (string exacto) contra las
        3 opciones fijas del <select> ('0'/'5'/'19'). DRF serializa
        DecimalField como STRING CON DECIMALES ("19.00", no "19" ni 19.0) --
        ninguna comparacion coincidia nunca, el <select> caia silenciosamente
        en la PRIMERA opcion (0%), perdiendo el IVA real y descuadrando el
        total de la Venta contra la factura.

        Este test fija el contrato exacto que rompia esa comparacion: si
        algun dia DRF deja de serializar como string ("19.00" -> 19.0), este
        test debe fallar y recordar revisar crearFilaItem() en
        venta_editor.js (que ahora normaliza con parseFloat() antes de
        comparar, sea cual sea el tipo que llegue).
        """
        resp = self.api_client.get(f"/api/v1/facturas/items-factura/?factura={self.factura.id}")
        item = resp.json().get("results", resp.json())[0]
        self.assertEqual(item["porcentaje_iva"], "19.00")
        self.assertNotEqual(item["porcentaje_iva"], "19")
        self.assertNotEqual(item["porcentaje_iva"], 19)

    def test_smoke_cliente_resoluble_por_nit_para_el_autofill_sin_cliente_uuid(self):
        """Caso factura sin cliente_uuid backfileado: el autorrelleno del JS
        cae a matching por NIT contra las <option data-doc> del select --
        este test confirma que el Cliente real es encontrable por ese NIT
        (mismo criterio que ClienteSelector.get_cliente_by_documento)."""
        factura_sin_cliente_uuid = Factura.objects.create(
            empresa=self.empresa, numero="FST-SIN-UUID", consecutivo=376,
            fecha_emision="2026-06-20T10:18:00Z",
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit="900860947", receptor_razon_social="Focus electronic security sistem S.A.S",
            naturaleza=Factura.Naturaleza.VENTA, estado=Factura.Estado.ACEPTADA,
        )
        resp = self.api_client.get(f"/api/v1/facturas/{factura_sin_cliente_uuid.uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        data = resp.json()
        self.assertIsNone(data.get("cliente_uuid"))
        self.assertEqual(data["receptor_nit"], "900860947")

        # El formulario de creacion de Venta trae TODOS los clientes activos
        # de la empresa como <option data-doc="...">  -- confirmamos que
        # el Cliente real esta en ese universo y su NIT coincide.
        resp_clientes = self.api_client.get(
            "/api/v1/ventas/render-offcanvas/crear/", HTTP_ACCEPT="text/html"
        )
        self.assertEqual(resp_clientes.status_code, status.HTTP_200_OK)
        self.assertIn(b"900860947", resp_clientes.content)
