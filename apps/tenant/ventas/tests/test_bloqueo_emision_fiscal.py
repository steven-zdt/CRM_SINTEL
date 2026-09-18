"""
VENTAS-COMPRAS-FACTURAS-01 (Fase 8/13, 2026-09-09): barrera de emision
fiscal. SINTEL todavia NO esta autorizada por la DIAN para crear/emitir/
transmitir Facturas electronicas -- `facturas` es el dueño fiscal
exclusivo (recibe XML ya generado/firmado externamente via
FacturaBusinessService.guardar_desde_dto()).

Este archivo prueba el comportamiento REAL de produccion (el flag
`EMISION_FISCAL_VENTA_AUTORIZADA` en su valor por defecto, False) -- no
duplica los tests existentes de COMERCIAL-04/F23 que mockean el flag a
True para seguir probando que el pipeline DIAN interno no se rompio (ver
docstrings de esos archivos).
"""
from decimal import Decimal

from django.utils import timezone
from rest_framework import status

from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from apps.tenant.inventario.models import MovimientoInventario, Producto
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.ventas.models import Venta
from apps.tenant.ventas.services.business_service import (
    EMISION_FISCAL_VENTA_AUTORIZADA,
    VentaBusinessService,
)
from apps.tenant.ventas.services.crud_service import VentaCRUDService
from tests.tenant.base_test import SintelTenantTestCase


def test_flag_por_defecto_es_false():
    """Documenta el estado real (no un mock): el valor con el que corre
    produccion hoy. Si esto cambia a True algun dia, debe ser un cambio de
    codigo explicito y revisado (ver comentario junto a la constante)."""
    assert EMISION_FISCAL_VENTA_AUTORIZADA is False


class BloqueoEmisionFiscalTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Bloqueo Fiscal", nit="900000950", direccion="Calle BF",
        )
        TenantProfile.objects.create(user=self.user, empresa=self.empresa)
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="BF-CLI-1", razon_social="Cliente Bloqueo Fiscal SAS",
            regimen_tributario="ORDINARIO",
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa, codigo="PROD-BF", nombre="Producto BF",
            stock_actual=Decimal("50"), costo_promedio=Decimal("10.00"), precio_venta=Decimal("40.00"),
        )

    def _payload(self):
        return {
            "cliente": str(self.cliente.uuid),
            "fecha_emision": "2026-06-10",
            "items": [{
                "descripcion": "Producto BF", "cantidad": "2", "precio_unitario": "40.00",
                "porcentaje_iva": "19", "producto_id": str(self.producto.uuid),
            }],
        }

    def test_procesar_y_facturar_venta_rechaza_con_403_por_defecto(self):
        ok, result, code = VentaBusinessService.procesar_y_facturar_venta(
            empresa=self.empresa, payload=self._payload(),
        )

        assert ok is False
        assert code == 403
        assert "detail" in result
        assert "no esta habilitada" in result["detail"].lower() or "no esta autorizada" in result["detail"].lower()

    def test_rechazo_no_crea_venta_ni_factura(self):
        """Cero datos parciales -- la barrera corta antes de cualquier
        escritura (DSV, consecutivo, Venta, DTO, CUFE, XML, firma)."""
        ventas_antes = Venta.objects.filter(empresa=self.empresa).count()
        facturas_antes = Factura.objects.filter(empresa=self.empresa).count()

        ok, result, code = VentaBusinessService.procesar_y_facturar_venta(
            empresa=self.empresa, payload=self._payload(),
        )

        assert ok is False
        assert Venta.objects.filter(empresa=self.empresa).count() == ventas_antes
        assert Factura.objects.filter(empresa=self.empresa).count() == facturas_antes

    def test_venta_borrador_via_crear_venta_borrador_sigue_funcionando(self):
        """crear_venta_borrador() (POST /ventas/, sin `procesar-facturar`)
        nunca toco Facturas -- no le aplica la barrera, sigue creando la
        Venta en BORRADOR con normalidad."""
        ok, venta, code = VentaBusinessService.crear_venta_borrador(
            empresa=self.empresa, payload=self._payload(),
        )

        assert ok is True
        assert code == 201
        assert venta.estado == Venta.Estado.BORRADOR
        assert venta.factura_asociada_id is None

    def test_venta_ya_facturada_previamente_sigue_siendo_consultable_idempotente(self):
        """El caso de una Venta que YA estaba FACTURADA_DIAN (dato
        historico previo a esta mision, o facturada legitimamente en un
        entorno con el flag en True) no debe romperse: es una lectura pura,
        no emite nada nuevo. La barrera solo bloquea la CREACION."""
        venta = VentaCRUDService.crear_venta(
            empresa=self.empresa, cliente=self.cliente,
            data={"fecha_emision": "2026-06-10"},
            items_data=[{
                "descripcion": "Producto BF", "cantidad": "1", "precio_unitario": "40.00",
                "porcentaje_iva": "19", "producto_id": self.producto.id,
            }],
        )
        factura_historica = Factura.objects.create(
            empresa=self.empresa, numero="HIST-001", consecutivo=1,
            naturaleza=Factura.Naturaleza.VENTA, estado="ACEPTADA",
            fecha_emision=timezone.now(),
        )
        venta.estado = Venta.Estado.FACTURADA_DIAN
        venta.factura_asociada = factura_historica
        venta.save(update_fields=["estado", "factura_asociada"])

        ok, resultado, code = VentaBusinessService.procesar_y_facturar_venta(
            empresa=self.empresa, payload=self._payload(), venta_existente=venta,
        )

        assert ok is True
        assert code == 200
        assert resultado.id == venta.id
        assert Factura.objects.filter(empresa=self.empresa).count() == 1

    def test_http_procesar_facturar_no_crea_factura_nueva(self):
        """Fase 8, prueba explicita pedida por la mision: POST Venta -> NO
        aparece nueva Factura, via el endpoint HTTP real."""
        venta = VentaCRUDService.crear_venta(
            empresa=self.empresa, cliente=self.cliente,
            data={"fecha_emision": "2026-06-10"},
            items_data=[{
                "descripcion": "Producto BF", "cantidad": "1", "precio_unitario": "40.00",
                "porcentaje_iva": "19", "producto_id": self.producto.id,
            }],
        )
        facturas_antes = Factura.objects.filter(empresa=self.empresa).count()

        resp = self.api_client.post(
            f"/api/v1/ventas/{venta.uuid}/procesar-facturar/", data={}, format="json",
        )

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert Factura.objects.filter(empresa=self.empresa).count() == facturas_antes
        venta.refresh_from_db()
        assert venta.estado == Venta.Estado.BORRADOR
