"""COTIZACIONES-02 Fase 07: Venta -> Factura VENTA.

CotizacionService.facturar_venta_de_cotizacion() reutiliza el flujo oficial
ya existente (VentaBusinessService.procesar_y_facturar_venta, COMERCIAL-04)
-- no reimplementa DTO ni calculo de impuestos. Mismo patron de fixtures que
apps/tenant/ventas/tests/test_comercial_04_idempotencia.py (sin mocks de la
parte DIAN -- el flujo real ya funciona sin ResolucionFacturacion explicita
en el payload, confirmado leyendo ese test antes de escribir este).

VENTAS-COMPRAS-FACTURAS-01 (2026-09-09): `procesar_y_facturar_venta()`
rechaza por defecto desde hoy (Fase 8, SINTEL no autorizada por la DIAN).
Los 3 tests que dependen del camino exitoso mockean el flag a True --
siguen probando que `facturar_venta_de_cotizacion()` delega correctamente
al flujo oficial de Ventas (el objetivo real de esta suite), no el bloqueo
de produccion en si (eso vive en
apps/tenant/ventas/tests/test_bloqueo_emision_fiscal.py).
"""
import datetime
from decimal import Decimal
from unittest import mock

import pytest
from django_tenants.utils import schema_context
from rest_framework.exceptions import ValidationError

from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.cotizaciones.services import CotizacionService
from apps.tenant.facturas.models import Factura
from apps.tenant.ventas.models import Venta

_EMISION_HABILITADA = mock.patch(
    "apps.tenant.ventas.services.business_service.EMISION_FISCAL_VENTA_AUTORIZADA", True,
)


def _crear_cotizacion_aprobada(empresa, cliente):
    from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion

    ConfiguracionCotizacion.objects.get_or_create(
        empresa=empresa,
        defaults={'dias_validez': 15, 'nombre_configuracion': 'Perfil General', 'es_activo': True},
    )
    payload = {
        'cliente': cliente.id,
        'fecha_emision': datetime.date(2026, 3, 30),
        'items': [{
            'tipo_item': 'PRODUCTO', 'descripcion': 'Switch 24 puertos',
            'cantidad': 1, 'costo_unitario': 300, 'porcentaje_utilidad': 25,
            'unidad': 'UND', 'orden': 1,
        }],
    }
    cotizacion = CotizacionService.crear_preforma(empresa, payload)
    CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.ENVIADA)
    return CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.APROBADA)


@pytest.mark.django_db
def test_facturar_venta_sin_venta_asociada_falla(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion_aprobada(empresa, cliente)
        with pytest.raises(ValidationError):
            CotizacionService.facturar_venta_de_cotizacion(cotizacion)


@pytest.mark.django_db
@_EMISION_HABILITADA
def test_facturar_venta_crea_factura_venta_vinculada(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion_aprobada(empresa, cliente)
        venta = CotizacionService.convertir_a_venta(cotizacion)

        resultado, status_code = CotizacionService.facturar_venta_de_cotizacion(cotizacion)

        assert status_code == 201
        venta.refresh_from_db()
        assert venta.estado == Venta.Estado.FACTURADA_DIAN
        assert venta.factura_asociada_id is not None

        factura = Factura.objects.get(pk=venta.factura_asociada_id)
        assert factura.naturaleza == Factura.Naturaleza.VENTA
        assert factura.empresa_id == empresa.id


@pytest.mark.django_db
@_EMISION_HABILITADA
def test_facturar_venta_es_idempotente_no_duplica_factura(tenant, factory_empresa, factory_cliente):
    """Mandato §7/24: doble click no duplica Factura. Hereda la proteccion
    real de VentaBusinessService.procesar_y_facturar_venta (COMERCIAL-04):
    la 2a llamada ve Venta.estado==FACTURADA_DIAN y devuelve la misma sin
    volver a ejecutar nada (200, no 201)."""
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion_aprobada(empresa, cliente)
        venta = CotizacionService.convertir_a_venta(cotizacion)

        _, status1 = CotizacionService.facturar_venta_de_cotizacion(cotizacion)
        assert status1 == 201
        venta.refresh_from_db()
        factura_id_1 = venta.factura_asociada_id

        resultado2, status2 = CotizacionService.facturar_venta_de_cotizacion(cotizacion)
        assert status2 == 200
        assert resultado2.id == venta.id
        assert resultado2.factura_asociada_id == factura_id_1

        assert Factura.objects.filter(empresa_id=empresa.id).count() == 1


@pytest.mark.django_db
@_EMISION_HABILITADA
def test_factura_no_reescribe_totales_manualmente(tenant, factory_empresa, factory_cliente):
    """Mandato §7: no se escribe manualmente Factura.total = Cotizacion.total
    -- los montos vienen de la Venta (calculados por VentaCRUDService.
    crear_venta, no copiados a mano por CotizacionService)."""
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion_aprobada(empresa, cliente)
        venta = CotizacionService.convertir_a_venta(cotizacion)
        # 300 * 1.25 = 375.00 * 1 unidad, + 19% IVA (default de la cotizacion)
        assert venta.subtotal == Decimal("375.00")

        CotizacionService.facturar_venta_de_cotizacion(cotizacion)
        venta.refresh_from_db()
        factura = Factura.objects.get(pk=venta.factura_asociada_id)
        assert factura.total == venta.total_neto
