"""
Test especifico FST 375 (apps/tenant/ventas/.agent/PROMPT_IA_EDITORA_FACTURAS_VENTAS_FST375.md
secc. 40): valida, con los valores reales transcritos de esa factura (NO
hardcodeados en el codigo de produccion -- solo en el fixture de este test),
el recorrido completo:

    Factura (naturaleza VENTA, ya existente/importada)
        -> reconciliacion masiva (migrar_facturas_a_ventas)
        -> Venta creada y vinculada
        -> autorrelleno visible via VentaDetailSerializer (solo lectura)
        -> idempotencia (correr dos veces no duplica)

Y, del lado de Facturas, que el detalle expone correctamente los campos
nuevos (valor_en_letras, autorizacion DIAN, forma_pago/medio_pago) que la
UI de detalle (offcanvas_detalle_factura.html) ahora renderiza.

No se dispone del PDF/XML real de FST 375 -- el fixture reconstruye la
Factura via ORM con los valores tal como estan transcritos en el documento
de referencia, siguiendo la instruccion explicita del propio prompt: "no
convertir sus datos en constantes" (se usan solo como datos de un test, no
como literales en servicios/vistas).
"""
from decimal import Decimal
from io import StringIO

from django.core.management import call_command

from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.api.serializers import FacturaDetailSerializer
from apps.tenant.facturas.models import Factura, ItemFactura
from apps.tenant.ventas.api.serializers import VentaDetailSerializer
from apps.tenant.ventas.models import Venta
from apps.tenant.ventas.services.business_service import VentaBusinessService
from tests.tenant.base_test import SintelTenantTestCase


class FST375Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="SINTEL TECHNOLOGY SAS", nit="901123299", direccion="Calle 30 58 CD 20",
        )
        # FST 375 -- valores tal como los transcribe el documento de referencia.
        self.factura = Factura.objects.create(
            empresa=self.empresa,
            numero="FST 375", prefijo="FST", consecutivo=375,
            tipo=Factura.TipoFactura.FE,
            naturaleza=Factura.Naturaleza.VENTA,
            estado=Factura.Estado.ACEPTADA,
            fecha_emision="2026-06-20T10:18:00Z",
            fecha_vencimiento="2026-07-20",
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit="900860947",
            receptor_razon_social="Focus electronic security sistem S.A.S",
            receptor_telefono="(601) 7561406",
            receptor_direccion="CL 90 60 B 08 P4",
            moneda="COP",
            subtotal=Decimal("4319257.00"),
            impuestos=Decimal("820658.83"),
            total=Decimal("5139915.83"),
            forma_pago="Credito",
            medio_pago_codigo="42",
            payment_due_date="2026-07-20",
            cufe="fake-cufe-fst-375-test-only",
            qr_url="https://catalogo-vpfe-hab.dian.gov.co/document/fake-fst-375",
            qr_code="NumFac=FST375&NitFac=901123299",
            autorizacion_numero="18764101371367",
            autorizacion_prefijo="FST",
            autorizacion_rango_desde=343,
            autorizacion_rango_hasta=850,
            autorizacion_vigencia_inicio="2025-11-09",
            autorizacion_vigencia_fin="2027-11-09",
        )
        ItemFactura.objects.create(
            empresa=self.empresa, factura=self.factura,
            descripcion="SERVICIO MANO OBRA INSTALACION PP241173",
            cantidad=Decimal("1.00"),
            valor_unitario=Decimal("4319257.00"),
            porcentaje_iva=Decimal("19.00"),
            valor_iva=Decimal("820658.83"),
            subtotal=Decimal("4319257.00"),
            total=Decimal("5139915.83"),
            es_servicio=True,
        )

    # ------------------------------------------------------------------
    # Detalle de Factura (solo lectura) -- FST-375 secc. 4/6/7/11/13/41
    # ------------------------------------------------------------------

    def test_detalle_factura_expone_valor_en_letras_correcto(self):
        data = FacturaDetailSerializer(self.factura, context={"empresa_id": self.empresa.id}).data
        self.assertEqual(
            data["valor_en_letras"],
            "Cinco millones ciento treinta y nueve mil novecientos quince pesos M/CTE con ochenta y tres centavos",
        )

    def test_detalle_factura_expone_autorizacion_dian_solo_lectura(self):
        data = FacturaDetailSerializer(self.factura, context={"empresa_id": self.empresa.id}).data
        self.assertEqual(data["autorizacion_numero"], "18764101371367")
        self.assertEqual(data["autorizacion_prefijo"], "FST")
        self.assertEqual(data["autorizacion_rango_desde"], 343)
        self.assertEqual(data["autorizacion_rango_hasta"], 850)
        self.assertIn("autorizacion_numero", FacturaDetailSerializer.Meta.read_only_fields)
        self.assertIn("qr_code", FacturaDetailSerializer.Meta.read_only_fields)

    def test_detalle_factura_expone_forma_y_medio_de_pago(self):
        data = FacturaDetailSerializer(self.factura, context={"empresa_id": self.empresa.id}).data
        self.assertEqual(data["forma_pago"], "Credito")
        self.assertEqual(data["medio_pago_codigo"], "42")
        self.assertEqual(str(data["fecha_vencimiento"]), "2026-07-20")

    # ------------------------------------------------------------------
    # Reconciliacion masiva -- FST-375 secc. 16-18/21/35/40
    # ------------------------------------------------------------------

    def _run_migracion(self, apply=False):
        out = StringIO()
        call_command(
            "migrar_facturas_a_ventas",
            schema=self.tenant.schema_name,
            apply=apply,
            stdout=out,
        )
        return out.getvalue()

    def test_dry_run_no_escribe_nada(self):
        salida = self._run_migracion(apply=False)
        self.assertIn("ventas_creadas: 1", salida)
        self.assertFalse(Venta.objects.filter(numero_factura="FST 375").exists())
        self.factura.refresh_from_db()
        self.assertFalse(hasattr(self.factura, "venta_origen"))

    def test_apply_crea_venta_y_autorrellena_desde_la_factura(self):
        self._run_migracion(apply=True)

        venta = Venta.objects.get(numero_factura="FST 375")
        self.assertEqual(venta.estado, Venta.Estado.FACTURADA_DIAN)
        self.assertEqual(venta.factura_asociada_id, self.factura.id)
        self.assertEqual(venta.cliente.numero_documento, "900860947")
        self.assertEqual(str(venta.fecha_emision), "2026-06-20")
        self.assertEqual(str(venta.fecha_vencimiento), "2026-07-20")
        self.assertEqual(venta.subtotal, Decimal("4319257.00"))
        self.assertEqual(venta.impuestos, Decimal("820658.83"))
        self.assertEqual(venta.total_neto, Decimal("5139915.83"))

        item = venta.items.get()
        self.assertEqual(item.descripcion, "SERVICIO MANO OBRA INSTALACION PP241173")
        self.assertEqual(item.cantidad, Decimal("1.00"))
        self.assertEqual(item.precio_unitario, Decimal("4319257.00"))

        # Autorrelleno de solo lectura visible en el detalle de Venta
        # (VentaDetailSerializer ya expone estos campos desde
        # factura_asociada -- FACTURAS-VENTAS-COMPRAS-01).
        data = VentaDetailSerializer(venta).data
        self.assertEqual(data["forma_pago"], "Credito")
        self.assertEqual(data["medio_pago_codigo"], "42")
        self.assertEqual(data["factura_cufe"], "fake-cufe-fst-375-test-only")
        self.assertEqual(data["factura_numero"], "FST 375")

    def test_migracion_es_idempotente(self):
        """Correr la migracion dos veces no debe crear una segunda Venta."""
        self._run_migracion(apply=True)
        primera_venta_id = Venta.objects.get(numero_factura="FST 375").id

        salida_segunda = self._run_migracion(apply=True)

        self.assertEqual(Venta.objects.filter(numero_factura="FST 375").count(), 1)
        self.assertEqual(Venta.objects.get(numero_factura="FST 375").id, primera_venta_id)
        self.assertIn("ya_vinculadas: 1", salida_segunda)
        self.assertIn("ventas_creadas: 0", salida_segunda)

    def test_no_duplica_venta_si_ya_existe_una_con_el_mismo_numero_factura(self):
        """Si ya existe una Venta manual con numero_factura=FST 375 (creada
        antes de que existiera este comando), debe vincularse a ella en vez
        de crear una segunda."""
        cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900860947", razon_social="Focus electronic security sistem S.A.S",
            regimen_tributario="ORDINARIO",
        )
        venta_previa = Venta.objects.create(
            empresa=self.empresa, cliente=cliente, fecha_emision="2026-06-20",
            numero_factura="FST 375", subtotal=Decimal("4319257.00"), total_neto=Decimal("5139915.83"),
        )

        self._run_migracion(apply=True)

        self.assertEqual(Venta.objects.filter(numero_factura="FST 375").count(), 1)
        venta_previa.refresh_from_db()
        self.assertEqual(venta_previa.factura_asociada_id, self.factura.id)
        self.assertEqual(venta_previa.estado, Venta.Estado.FACTURADA_DIAN)

    def test_ambigua_si_hay_mas_de_una_venta_candidata(self):
        """Dos Ventas sin vincular con el mismo numero_factura: no debe
        vincular automaticamente con evidencia insuficiente (secc. 18)."""
        cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900860947-dup", razon_social="Focus electronic security sistem S.A.S",
            regimen_tributario="ORDINARIO",
        )
        Venta.objects.create(
            empresa=self.empresa, cliente=cliente, fecha_emision="2026-06-20",
            numero_factura="FST 375", subtotal=Decimal("1.00"), total_neto=Decimal("1.00"),
        )
        Venta.objects.create(
            empresa=self.empresa, cliente=cliente, fecha_emision="2026-06-20",
            numero_factura="FST 375", subtotal=Decimal("2.00"), total_neto=Decimal("2.00"),
        )

        salida = self._run_migracion(apply=True)

        self.assertIn("ambiguas: 1", salida)
        self.factura.refresh_from_db()
        self.assertFalse(hasattr(self.factura, "venta_origen"))

    def test_crear_venta_desde_factura_falla_sin_items(self):
        factura_sin_items = Factura.objects.create(
            empresa=self.empresa, numero="FST-SIN-ITEMS", consecutivo=999,
            fecha_emision="2026-06-20",
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit="900860947", receptor_razon_social="Focus electronic security sistem S.A.S",
            naturaleza=Factura.Naturaleza.VENTA, estado=Factura.Estado.ACEPTADA,
        )
        with self.assertRaises(ValueError):
            VentaBusinessService.crear_venta_desde_factura(factura_sin_items, self.empresa)
