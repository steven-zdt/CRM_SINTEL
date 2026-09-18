"""COTIZACIONES-01/02: conversion Cotizacion -> Venta.

Gap de cobertura real: la conversion no existia en absoluto (confirmado con
evidencia negativa en 3 auditorias previas -- ver docs/cotizaciones/
COTIZACIONES_INTEGRATIONS.md). Este archivo cubre CotizacionService.
convertir_a_venta(). COTIZACIONES-02 (mismo dia): la condicion de entrada
cambio de ACEPTADA a APROBADA (rename de estados, 0 filas reales
afectadas).
"""
import datetime
from decimal import Decimal

import pytest
from django_tenants.utils import schema_context
from rest_framework.exceptions import ValidationError

from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.cotizaciones.services import CotizacionService
from apps.tenant.ventas.models import Venta


def _crear_cotizacion_aprobada(empresa, cliente, con_items=True):
    from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion

    ConfiguracionCotizacion.objects.get_or_create(
        empresa=empresa,
        defaults={
            'dias_validez': 15, 'nombre_configuracion': 'Perfil General', 'es_activo': True,
        },
    )
    payload = {
        'cliente': cliente.id,
        'fecha_emision': datetime.date(2026, 3, 30),
        'items': [{
            'tipo_item': 'PRODUCTO', 'descripcion': 'Router empresarial',
            'cantidad': 2, 'costo_unitario': 500, 'porcentaje_utilidad': 20,
            'unidad': 'UND', 'orden': 1,
        }] if con_items else [],
    }
    cotizacion = CotizacionService.crear_preforma(empresa, payload)
    CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.ENVIADA)
    return CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.APROBADA)


@pytest.mark.django_db
def test_convertir_cotizacion_aprobada_crea_venta(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion_aprobada(empresa, cliente)

        venta = CotizacionService.convertir_a_venta(cotizacion)

        assert venta.cotizacion_uuid == cotizacion.uuid
        assert venta.cliente_id == cliente.id
        assert venta.empresa_id == empresa.id
        assert venta.estado == Venta.Estado.BORRADOR
        assert venta.items.count() == 1
        item = venta.items.first()
        assert item.descripcion == "Router empresarial"
        assert item.cantidad == Decimal("2")
        # precio_unitario_venta calculado por CotizacionItemBusinessService:
        # 500 * (1 + 20/100) = 600.00
        assert item.precio_unitario == Decimal("600.00")
        assert venta.subtotal == Decimal("1200.00")  # 2 * 600


@pytest.mark.django_db
def test_convertir_es_idempotente_no_duplica_venta(tenant, factory_empresa, factory_cliente):
    """Mandato §14: click 1 / click 2 / retry no deben crear Venta A, B, C
    -- una sola Venta por Cotizacion (constraint unique en
    Venta.cotizacion_uuid + guard explicito en el service)."""
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion_aprobada(empresa, cliente)

        venta1 = CotizacionService.convertir_a_venta(cotizacion)
        venta2 = CotizacionService.convertir_a_venta(cotizacion)
        venta3 = CotizacionService.convertir_a_venta(cotizacion)

        assert venta1.id == venta2.id == venta3.id
        assert Venta.objects.filter(cotizacion_uuid=cotizacion.uuid).count() == 1


@pytest.mark.django_db
def test_no_se_puede_convertir_desde_borrador(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion

        ConfiguracionCotizacion.objects.get_or_create(
            empresa=empresa,
            defaults={'dias_validez': 15, 'nombre_configuracion': 'Perfil General', 'es_activo': True},
        )
        cotizacion = CotizacionService.crear_preforma(empresa, {
            'cliente': cliente.id, 'fecha_emision': datetime.date(2026, 3, 30),
            'items': [{'tipo_item': 'PRODUCTO', 'descripcion': 'X', 'cantidad': 1,
                       'costo_unitario': 10, 'porcentaje_utilidad': 0, 'unidad': 'UND', 'orden': 1}],
        })
        assert cotizacion.estado == Cotizacion.Estado.BORRADOR

        with pytest.raises(ValidationError):
            CotizacionService.convertir_a_venta(cotizacion)
        assert Venta.objects.filter(cotizacion_uuid=cotizacion.uuid).count() == 0


@pytest.mark.django_db
def test_no_se_puede_convertir_desde_enviada(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion

        ConfiguracionCotizacion.objects.get_or_create(
            empresa=empresa,
            defaults={'dias_validez': 15, 'nombre_configuracion': 'Perfil General', 'es_activo': True},
        )
        cotizacion = CotizacionService.crear_preforma(empresa, {
            'cliente': cliente.id, 'fecha_emision': datetime.date(2026, 3, 30),
            'items': [{'tipo_item': 'PRODUCTO', 'descripcion': 'X', 'cantidad': 1,
                       'costo_unitario': 10, 'porcentaje_utilidad': 0, 'unidad': 'UND', 'orden': 1}],
        })
        CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.ENVIADA)

        with pytest.raises(ValidationError):
            CotizacionService.convertir_a_venta(cotizacion)


@pytest.mark.django_db
def test_no_se_puede_convertir_sin_cliente(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion_aprobada(empresa, cliente)
        cotizacion.cliente = None
        cotizacion.save(update_fields=["cliente"])

        with pytest.raises(ValidationError):
            CotizacionService.convertir_a_venta(cotizacion)


@pytest.mark.django_db
def test_no_se_puede_convertir_sin_items(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion_aprobada(empresa, cliente, con_items=False)
        assert cotizacion.items.count() == 0

        with pytest.raises(ValidationError):
            CotizacionService.convertir_a_venta(cotizacion)


@pytest.mark.django_db
def test_venta_no_cruza_tenants(tenant, tenant_b, factory_empresa, factory_cliente):
    """Aislamiento multi-tenant: una Venta creada en el schema de un tenant
    no es visible desde otro (aislamiento real de PostgreSQL por schema).
    """
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion_aprobada(empresa, cliente)
        venta = CotizacionService.convertir_a_venta(cotizacion)
        venta_uuid = venta.uuid

    with schema_context(tenant_b.schema_name):
        assert not Venta.objects.filter(uuid=venta_uuid).exists()
