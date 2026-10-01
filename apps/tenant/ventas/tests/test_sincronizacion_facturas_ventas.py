"""
PLAN_SINCRONIZACION_FACTURAS_VENTAS_FASES (apps/tenant/ventas/.agent/):
tests de `FacturaVentaSyncService` -- sincronizacion unitaria/masiva de
Facturas VENTA (FE) sin Venta comercial vinculada.

Cobertura: FASE 15 (idempotencia), FASE 16 (concurrencia real), FASE 17
(seguridad/aislamiento por tenant), mas los casos base ya cubiertos
parcialmente por `migrar_facturas_a_ventas` (test_fst375_migracion_y_autorrelleno.py)
pero ahora contra el servicio unitario que consume la UI ("Sincronizar y
validar facturas").
"""

import threading
from decimal import Decimal

import pytest
from django.db import connection
from django_tenants.utils import schema_context

from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, ItemFactura
from apps.tenant.ventas.models import Venta
from apps.tenant.ventas.services.business_service import (
    FacturaVentaSyncService,
    VentaBusinessService,
)
from tests.tenant.base_test import SintelTenantTestCase


def _crear_factura_venta(
    empresa, numero, consecutivo, receptor_nit="900860947", con_item=True, cotizacion_uuid=None
):
    factura = Factura.objects.create(
        empresa=empresa,
        numero=numero,
        consecutivo=consecutivo,
        tipo=Factura.TipoFactura.FE,
        naturaleza=Factura.Naturaleza.VENTA,
        estado=Factura.Estado.ACEPTADA,
        fecha_emision="2026-06-20",
        emisor_nit=empresa.nit,
        emisor_razon_social=empresa.razon_social,
        receptor_nit=receptor_nit,
        receptor_razon_social="Cliente Sync SAS",
        subtotal=Decimal("100000.00"),
        impuestos=Decimal("19000.00"),
        total=Decimal("119000.00"),
        cotizacion_uuid=cotizacion_uuid,
    )
    if con_item:
        ItemFactura.objects.create(
            empresa=empresa,
            factura=factura,
            descripcion="Servicio sync",
            cantidad=Decimal("1.00"),
            valor_unitario=Decimal("100000.00"),
            porcentaje_iva=Decimal("19.00"),
            valor_iva=Decimal("19000.00"),
            subtotal=Decimal("100000.00"),
            total=Decimal("119000.00"),
        )
    return factura


class SincronizarFacturasSelectorTests(SintelTenantTestCase):
    """FASE 4/17: `listar_pendientes` -- DSV, filtros y exclusion de ya vinculadas."""

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Sync",
            nit="900000970",
            direccion="Calle Sync",
        )
        self.pendiente = _crear_factura_venta(self.empresa, "SYNC-01", 1001)
        self.compra = Factura.objects.create(
            empresa=self.empresa,
            numero="SYNC-COMPRA-01",
            consecutivo=1002,
            tipo=Factura.TipoFactura.FE,
            naturaleza=Factura.Naturaleza.COMPRA,
            estado=Factura.Estado.ACEPTADA,
            fecha_emision="2026-06-20",
            emisor_nit="900999888",
            emisor_razon_social="Proveedor Sync",
            receptor_nit=self.empresa.nit,
            receptor_razon_social=self.empresa.razon_social,
        )

    def test_no_incluye_facturas_de_naturaleza_compra(self):
        pendientes = FacturaVentaSyncService.listar_pendientes(self.empresa.id)
        self.assertIn(self.pendiente, list(pendientes))
        self.assertNotIn(self.compra, list(pendientes))

    def test_no_incluye_facturas_ya_vinculadas(self):
        FacturaVentaSyncService.sincronizar_una(
            str(self.pendiente.uuid), self.empresa.id, self.empresa
        )
        pendientes = FacturaVentaSyncService.listar_pendientes(self.empresa.id)
        self.assertNotIn(self.pendiente, list(pendientes))

    def test_dsv_no_expone_facturas_de_otra_empresa(self):
        otra_empresa = Empresa.objects.exclude(id=self.empresa.id).first()
        if otra_empresa is None:
            self.skipTest("Requiere una segunda Empresa en el mismo schema.")
        pendientes = FacturaVentaSyncService.listar_pendientes(otra_empresa.id)
        self.assertNotIn(self.pendiente, list(pendientes))

    def test_search_filtra_por_numero(self):
        pendientes = FacturaVentaSyncService.listar_pendientes(self.empresa.id, search="SYNC-01")
        self.assertIn(self.pendiente, list(pendientes))
        pendientes_vacio = FacturaVentaSyncService.listar_pendientes(
            self.empresa.id, search="NO-EXISTE"
        )
        self.assertNotIn(self.pendiente, list(pendientes_vacio))


class SincronizarUnaTests(SintelTenantTestCase):
    """FASE 8/9/15: sincronizacion unitaria + idempotencia."""

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Sync Unitaria",
            nit="900000971",
            direccion="Calle Sync",
        )
        self.factura = _crear_factura_venta(self.empresa, "SYNC-U-01", 2001)

    def test_sincroniza_crea_venta_nueva(self):
        resultado = FacturaVentaSyncService.sincronizar_una(
            str(self.factura.uuid),
            self.empresa.id,
            self.empresa,
        )
        self.assertEqual(resultado["estado"], "VINCULADA")
        venta = Venta.objects.get(uuid=resultado["venta_uuid"])
        self.assertEqual(venta.factura_asociada_id, self.factura.id)

    def test_sincroniza_crea_venta_nueva_propaga_cotizacion_uuid_de_la_factura(self):
        """Bug real encontrado en auditoria (2026-09-26): `crear_venta_desde_
        factura()` no propagaba `Factura.cotizacion_uuid` (soft-reference ya
        backfileada en la Factura) hacia la Venta nueva, dejando roto el
        vinculo Cotizacion<->Venta que usa `Cotizacion.convertir_a_venta()`
        para su idempotencia. cotizacion_uuid sigue siendo opcional -- no se
        exige ni bloquea nada, solo se propaga si ya existe."""
        cot_uuid = "11111111-1111-1111-1111-111111111111"
        factura = _crear_factura_venta(
            self.empresa, "SYNC-U-COT-01", 2010, cotizacion_uuid=cot_uuid
        )
        resultado = FacturaVentaSyncService.sincronizar_una(
            str(factura.uuid),
            self.empresa.id,
            self.empresa,
        )
        self.assertEqual(resultado["estado"], "VINCULADA")
        venta = Venta.objects.get(uuid=resultado["venta_uuid"])
        self.assertEqual(str(venta.cotizacion_uuid), cot_uuid)

    def test_sincroniza_venta_manual_existente_hereda_cotizacion_uuid_de_la_factura(self):
        """Mismo bug, otro camino: cuando la Venta candidata ya existia
        (creada manualmente, sin cotizacion) y se vincula a una Factura que
        SI tiene `cotizacion_uuid`, la Venta debe heredarlo."""
        cliente = Cliente.objects.create(
            empresa=self.empresa,
            tipo_persona="JURIDICA",
            tipo_documento="NIT",
            numero_documento="SYNC-CLI-COT",
            razon_social="Cliente Sync SAS",
            regimen_tributario="ORDINARIO",
        )
        venta_previa = Venta.objects.create(
            empresa=self.empresa,
            cliente=cliente,
            fecha_emision="2026-06-20",
            numero_factura="SYNC-U-01",
            subtotal=Decimal("100000.00"),
            total_neto=Decimal("119000.00"),
        )
        self.assertIsNone(venta_previa.cotizacion_uuid)
        cot_uuid = "22222222-2222-2222-2222-222222222222"
        self.factura.cotizacion_uuid = cot_uuid
        self.factura.save(update_fields=["cotizacion_uuid"])

        resultado = FacturaVentaSyncService.sincronizar_una(
            str(self.factura.uuid),
            self.empresa.id,
            self.empresa,
        )
        self.assertEqual(resultado["estado"], "VINCULADA")
        venta_previa.refresh_from_db()
        self.assertEqual(str(venta_previa.cotizacion_uuid), cot_uuid)

    def test_sincroniza_vincula_venta_manual_existente_por_numero_factura(self):
        cliente = Cliente.objects.create(
            empresa=self.empresa,
            tipo_persona="JURIDICA",
            tipo_documento="NIT",
            numero_documento="SYNC-CLI-1",
            razon_social="Cliente Sync SAS",
            regimen_tributario="ORDINARIO",
        )
        venta_previa = Venta.objects.create(
            empresa=self.empresa,
            cliente=cliente,
            fecha_emision="2026-06-20",
            numero_factura="SYNC-U-01",
            subtotal=Decimal("100000.00"),
            total_neto=Decimal("119000.00"),
        )
        resultado = FacturaVentaSyncService.sincronizar_una(
            str(self.factura.uuid),
            self.empresa.id,
            self.empresa,
        )
        self.assertEqual(resultado["estado"], "VINCULADA")
        venta_previa.refresh_from_db()
        self.assertEqual(resultado["venta_uuid"], str(venta_previa.uuid))

    def test_idempotente_segunda_llamada_reporta_ya_vinculada(self):
        primero = FacturaVentaSyncService.sincronizar_una(
            str(self.factura.uuid),
            self.empresa.id,
            self.empresa,
        )
        segundo = FacturaVentaSyncService.sincronizar_una(
            str(self.factura.uuid),
            self.empresa.id,
            self.empresa,
        )
        self.assertEqual(segundo["estado"], "YA_VINCULADA")
        self.assertEqual(segundo["venta_uuid"], primero["venta_uuid"])
        self.assertEqual(Venta.objects.filter(factura_asociada=self.factura).count(), 1)

    def test_rechaza_factura_de_otra_naturaleza(self):
        factura_compra = Factura.objects.create(
            empresa=self.empresa,
            numero="SYNC-COMPRA-U",
            consecutivo=2002,
            tipo=Factura.TipoFactura.FE,
            naturaleza=Factura.Naturaleza.COMPRA,
            estado=Factura.Estado.ACEPTADA,
            fecha_emision="2026-06-20",
            emisor_nit="900999888",
            emisor_razon_social="Proveedor Sync",
            receptor_nit=self.empresa.nit,
            receptor_razon_social=self.empresa.razon_social,
        )
        resultado = FacturaVentaSyncService.sincronizar_una(
            str(factura_compra.uuid),
            self.empresa.id,
            self.empresa,
        )
        self.assertEqual(resultado["estado"], "INVALIDA")

    def test_rechaza_uuid_inexistente(self):
        resultado = FacturaVentaSyncService.sincronizar_una(
            "00000000-0000-0000-0000-000000000000",
            self.empresa.id,
            self.empresa,
        )
        self.assertEqual(resultado["estado"], "INVALIDA")

    def test_dsv_factura_de_otra_empresa_no_se_puede_sincronizar(self):
        """Anti-IDOR: un UUID valido de Factura de OTRA empresa (manipulado
        en el request) no debe resolverse ni con el empresa_id correcto del
        atacante."""
        otra_empresa = Empresa.objects.exclude(id=self.empresa.id).first()
        if otra_empresa is None:
            self.skipTest("Requiere una segunda Empresa en el mismo schema.")
        resultado = FacturaVentaSyncService.sincronizar_una(
            str(self.factura.uuid),
            otra_empresa.id,
            otra_empresa,
        )
        self.assertEqual(resultado["estado"], "INVALIDA")
        self.factura.refresh_from_db()
        self.assertFalse(hasattr(self.factura, "venta_origen"))

    def test_error_si_factura_sin_items(self):
        factura_sin_items = _crear_factura_venta(
            self.empresa,
            "SYNC-SIN-ITEMS",
            2003,
            con_item=False,
        )
        resultado = FacturaVentaSyncService.sincronizar_una(
            str(factura_sin_items.uuid),
            self.empresa.id,
            self.empresa,
        )
        self.assertEqual(resultado["estado"], "ERROR")
        self.assertFalse(Venta.objects.filter(numero_factura="SYNC-SIN-ITEMS").exists())

    def test_ambigua_si_hay_mas_de_una_venta_candidata(self):
        cliente = Cliente.objects.create(
            empresa=self.empresa,
            tipo_persona="JURIDICA",
            tipo_documento="NIT",
            numero_documento="SYNC-CLI-DUP",
            razon_social="Cliente Sync SAS",
            regimen_tributario="ORDINARIO",
        )
        Venta.objects.create(
            empresa=self.empresa,
            cliente=cliente,
            fecha_emision="2026-06-20",
            numero_factura="SYNC-U-01",
            subtotal=Decimal("1.00"),
            total_neto=Decimal("1.00"),
        )
        Venta.objects.create(
            empresa=self.empresa,
            cliente=cliente,
            fecha_emision="2026-06-20",
            numero_factura="SYNC-U-01",
            subtotal=Decimal("2.00"),
            total_neto=Decimal("2.00"),
        )
        resultado = FacturaVentaSyncService.sincronizar_una(
            str(self.factura.uuid),
            self.empresa.id,
            self.empresa,
        )
        self.assertEqual(resultado["estado"], "AMBIGUA")
        self.factura.refresh_from_db()
        self.assertFalse(hasattr(self.factura, "venta_origen"))


class SincronizarMasivoTests(SintelTenantTestCase):
    """FASE 11/14: sincronizacion en bloque -- clasificacion y resumen."""

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Sync Masiva",
            nit="900000972",
            direccion="Calle Sync",
        )
        self.f1 = _crear_factura_venta(self.empresa, "SYNC-M-01", 3001)
        self.f2 = _crear_factura_venta(self.empresa, "SYNC-M-02", 3002)
        self.f3_invalida = Factura.objects.create(
            empresa=self.empresa,
            numero="SYNC-M-COMPRA",
            consecutivo=3003,
            tipo=Factura.TipoFactura.FE,
            naturaleza=Factura.Naturaleza.COMPRA,
            estado=Factura.Estado.ACEPTADA,
            fecha_emision="2026-06-20",
            emisor_nit="900999888",
            emisor_razon_social="Proveedor Sync",
            receptor_nit=self.empresa.nit,
            receptor_razon_social=self.empresa.razon_social,
        )

    def test_clasifica_resultados_y_resumen(self):
        resp = FacturaVentaSyncService.sincronizar_masivo(
            [str(self.f1.uuid), str(self.f2.uuid), str(self.f3_invalida.uuid)],
            self.empresa.id,
            self.empresa,
        )
        self.assertEqual(resp["resumen"]["VINCULADA"], 2)
        self.assertEqual(resp["resumen"]["INVALIDA"], 1)
        self.assertEqual(len(resp["resultados"]), 3)
        self.assertEqual(Venta.objects.filter(empresa=self.empresa).count(), 2)

    def test_corrida_repetida_no_duplica_ventas(self):
        FacturaVentaSyncService.sincronizar_masivo(
            [str(self.f1.uuid), str(self.f2.uuid)],
            self.empresa.id,
            self.empresa,
        )
        resp2 = FacturaVentaSyncService.sincronizar_masivo(
            [str(self.f1.uuid), str(self.f2.uuid)],
            self.empresa.id,
            self.empresa,
        )
        self.assertEqual(resp2["resumen"]["YA_VINCULADA"], 2)
        self.assertEqual(Venta.objects.filter(empresa=self.empresa).count(), 2)


class EliminarVentaSincronizadaTests(SintelTenantTestCase):
    """Bug report (2026-09-18): permitir eliminar desde Ventas una Venta
    creada/vinculada por sincronizacion, sin tocar la Factura origen --
    `anular_venta()` la rechaza (esta en FACTURADA_DIAN, pensado para una
    emision fiscal real que aqui nunca ocurre)."""

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Eliminar Sync",
            nit="900000973",
            direccion="Calle Sync",
        )
        self.factura = _crear_factura_venta(self.empresa, "SYNC-DEL-01", 4001)
        resultado = FacturaVentaSyncService.sincronizar_una(
            str(self.factura.uuid),
            self.empresa.id,
            self.empresa,
        )
        self.venta_sincronizada = Venta.objects.get(uuid=resultado["venta_uuid"])

    def test_elimina_venta_sincronizada_sin_tocar_la_factura(self):
        ok, result, code = VentaBusinessService.eliminar_venta_sincronizada(
            str(self.venta_sincronizada.uuid),
            self.empresa.id,
        )
        self.assertTrue(ok, result)
        self.assertEqual(code, 200)
        self.assertFalse(Venta.objects.filter(uuid=self.venta_sincronizada.uuid).exists())
        self.factura.refresh_from_db()
        self.assertEqual(self.factura.numero, "SYNC-DEL-01")
        self.assertFalse(hasattr(self.factura, "venta_origen"))

    def test_factura_vuelve_a_quedar_pendiente_tras_eliminar(self):
        VentaBusinessService.eliminar_venta_sincronizada(
            str(self.venta_sincronizada.uuid),
            self.empresa.id,
        )
        pendientes = FacturaVentaSyncService.listar_pendientes(self.empresa.id)
        self.assertIn(self.factura, list(pendientes))

    def test_rechaza_eliminar_venta_manual_sin_factura_asociada(self):
        cliente = Cliente.objects.create(
            empresa=self.empresa,
            tipo_persona="JURIDICA",
            tipo_documento="NIT",
            numero_documento="SYNC-DEL-CLI",
            razon_social="Cliente Manual SAS",
            regimen_tributario="ORDINARIO",
        )
        venta_manual = Venta.objects.create(
            empresa=self.empresa,
            cliente=cliente,
            fecha_emision="2026-06-20",
            subtotal=Decimal("1.00"),
            total_neto=Decimal("1.00"),
        )
        ok, result, code = VentaBusinessService.eliminar_venta_sincronizada(
            str(venta_manual.uuid),
            self.empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 400)
        self.assertTrue(Venta.objects.filter(uuid=venta_manual.uuid).exists())

    def test_dsv_no_permite_eliminar_venta_de_otra_empresa(self):
        otra_empresa = Empresa.objects.exclude(id=self.empresa.id).first()
        if otra_empresa is None:
            self.skipTest("Requiere una segunda Empresa en el mismo schema.")
        ok, result, code = VentaBusinessService.eliminar_venta_sincronizada(
            str(self.venta_sincronizada.uuid),
            otra_empresa.id,
        )
        self.assertFalse(ok)
        self.assertEqual(code, 404)
        self.assertTrue(Venta.objects.filter(uuid=self.venta_sincronizada.uuid).exists())


class FormatoNumericoSinTruncarCentavosTests(SintelTenantTestCase):
    """Bug report (2026-09-18): "estas omitiendo cifras despues de la coma"
    -- el listado de Facturas y de Ventas truncaba los centavos en pantalla
    (",.0f"/floatformat:0) aunque el valor real en BD si los tenia. Ambos
    listados deben mostrar el valor COMPLETO (2 decimales), igual que
    currency_cop en el detalle."""

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Formato Numerico",
            nit="900000974",
            direccion="Calle Fmt",
        )

    def test_dt_facturas_no_trunca_centavos(self):
        # Facturas ya no tiene tabla django-tables2 propia (retirada al
        # migrar a DataTables, ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md).
        # El dato crudo lo sirve FacturaListSerializer/POST /api/v1/facturas/dt/
        # y el formato de moneda lo aplica DOMUtils.formatCurrency en el
        # navegador -- este test protege que el dato no pierda los centavos
        # antes de llegar al JS (mismo criterio que test_dt_ventas_no_trunca_centavos).
        from apps.tenant.facturas.api.serializers import FacturaListSerializer

        factura = _crear_factura_venta(self.empresa, "FMT-01", 5001)
        factura.total = Decimal("693760.48")
        factura.save(update_fields=["total"])
        data = FacturaListSerializer(factura).data
        self.assertEqual(Decimal(data["total"]), Decimal("693760.48"))

    def test_dt_ventas_no_trunca_centavos(self):
        # Ventas ya no tiene una tabla django-tables2 propia (retirada tras
        # cerrar el gate visual del piloto DataTables -- ver
        # docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md). El listado
        # vivo sirve el valor crudo via VentaListSerializer/POST
        # /api/v1/ventas/dt/ y el formato de moneda (2 decimales) lo aplica
        # DOMUtils.formatCurrency en el navegador (venta_list.js:renderTotal) --
        # lo que este test protege es que el dato que llega al frontend no
        # pierda los centavos ANTES de que el JS los formatee.
        from apps.tenant.ventas.api.serializers import VentaListSerializer

        cliente = Cliente.objects.create(
            empresa=self.empresa,
            tipo_persona="JURIDICA",
            tipo_documento="NIT",
            numero_documento="FMT-CLI-1",
            razon_social="Cliente Fmt SAS",
            regimen_tributario="ORDINARIO",
        )
        venta = Venta.objects.create(
            empresa=self.empresa,
            cliente=cliente,
            fecha_emision="2026-06-20",
            subtotal=Decimal("100000.00"),
            total_neto=Decimal("119000.48"),
        )
        data = VentaListSerializer(venta).data
        self.assertEqual(Decimal(data["total_neto"]), Decimal("119000.48"))


@pytest.mark.django_db(transaction=True)
def test_dos_sincronizaciones_concurrentes_de_la_misma_factura_no_duplican_venta(tenant):
    """FASE 16: concurrencia real -- dos usuarios pulsan "Vincular" sobre la
    misma Factura al mismo tiempo. `select_for_update()` sobre Factura en
    `sincronizar_una()` debe serializar el acceso: exactamente una
    ejecucion crea la Venta, la otra debe encontrarla YA_VINCULADA -- nunca
    dos Ventas para la misma Factura."""
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        factura = _crear_factura_venta(empresa, "SYNC-CONC-01", 9001)
        factura_uuid = str(factura.uuid)
        empresa_id = empresa.id

    resultados = {}
    barrera = threading.Barrier(2)

    def _sincronizar(nombre):
        try:
            with schema_context(tenant.schema_name):
                empresa_local = Empresa.objects.get(id=empresa_id)
                barrera.wait(timeout=5)
                resultado = FacturaVentaSyncService.sincronizar_una(
                    factura_uuid,
                    empresa_id,
                    empresa_local,
                )
                resultados[nombre] = resultado["estado"]
        except Exception as exc:
            resultados[nombre] = f"EXCEPCION: {exc}"
        finally:
            connection.close()

    hilo_a = threading.Thread(target=_sincronizar, args=("A",))
    hilo_b = threading.Thread(target=_sincronizar, args=("B",))
    hilo_a.start()
    hilo_b.start()
    hilo_a.join(timeout=10)
    hilo_b.join(timeout=10)

    estados = sorted(resultados.values())
    assert estados == ["VINCULADA", "YA_VINCULADA"], f"Resultados inesperados: {resultados}"

    with schema_context(tenant.schema_name):
        assert Venta.objects.filter(numero_factura="SYNC-CONC-01").count() == 1
