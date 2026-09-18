"""COTIZACIONES-02 Fase 11: items SERVICIO de una Cotizacion APROBADA -> Proyecto.

Reutiliza el orquestador YA EXISTENTE de Proyectos (orchestrate_create_proyecto,
apps/tenant/proyectos/services/business_service.py) -- no se crea un
segundo modelo Proyecto ni un service paralelo. Antes de esta mision no
existia ningun bridge Cotizacion->Proyecto en el codigo (confirmado con
evidencia negativa).
"""
import datetime
from decimal import Decimal

import pytest
from django_tenants.utils import schema_context
from rest_framework.exceptions import ValidationError

from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.cotizaciones.services import CotizacionService
from apps.tenant.proyectos.models import Proyecto


def _crear_cotizacion_aprobada(empresa, cliente, items):
    from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion

    ConfiguracionCotizacion.objects.get_or_create(
        empresa=empresa,
        defaults={'dias_validez': 15, 'nombre_configuracion': 'Perfil General', 'es_activo': True},
    )
    payload = {
        'cliente': cliente.id,
        'fecha_emision': datetime.date(2026, 3, 30),
        'items': items,
    }
    cotizacion = CotizacionService.crear_preforma(empresa, payload)
    CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.ENVIADA)
    return CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.APROBADA)


_ITEM_SERVICIO = {
    'tipo_item': 'SERVICIO', 'descripcion': 'Instalacion y configuracion',
    'cantidad': 1, 'costo_unitario': 1000, 'porcentaje_utilidad': 30,
    'unidad': 'UND', 'orden': 1,
}
_ITEM_PRODUCTO = {
    'tipo_item': 'PRODUCTO', 'descripcion': 'Router',
    'cantidad': 1, 'costo_unitario': 200, 'porcentaje_utilidad': 20,
    'unidad': 'UND', 'orden': 2,
}


@pytest.mark.django_db
def test_convertir_a_proyecto_crea_proyecto_con_valor_de_servicios(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion_aprobada(empresa, cliente, [_ITEM_SERVICIO, _ITEM_PRODUCTO])

        proyecto = CotizacionService.convertir_a_proyecto(cotizacion)

        assert proyecto.empresa_id == empresa.id
        assert proyecto.cliente_id == cliente.id
        # 1000 * 1.30 = 1300.00 (solo el item SERVICIO, no el PRODUCTO)
        assert proyecto.valor_contrato_proyectado == Decimal("1300.00")


@pytest.mark.django_db
def test_convertir_a_proyecto_es_idempotente(tenant, factory_empresa, factory_cliente):
    """Doble click no crea un Proyecto hermano -- busca por codigo derivado
    deterministicamente de la Cotizacion antes de crear uno nuevo."""
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion_aprobada(empresa, cliente, [_ITEM_SERVICIO])

        p1 = CotizacionService.convertir_a_proyecto(cotizacion)
        p2 = CotizacionService.convertir_a_proyecto(cotizacion)

        assert p1.id == p2.id
        assert Proyecto.objects.filter(empresa_id=empresa.id).count() == 1


@pytest.mark.django_db
def test_convertir_a_proyecto_sin_items_servicio_falla(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion_aprobada(empresa, cliente, [_ITEM_PRODUCTO])
        with pytest.raises(ValidationError):
            CotizacionService.convertir_a_proyecto(cotizacion)
        assert Proyecto.objects.filter(empresa_id=empresa.id).count() == 0


@pytest.mark.django_db
def test_convertir_a_proyecto_requiere_aprobada(tenant, factory_empresa, factory_cliente):
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
            'items': [_ITEM_SERVICIO],
        })
        assert cotizacion.estado == Cotizacion.Estado.BORRADOR
        with pytest.raises(ValidationError):
            CotizacionService.convertir_a_proyecto(cotizacion)
