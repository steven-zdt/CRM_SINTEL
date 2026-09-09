"""COTIZACIONES-01: maquina de estados de Cotizacion.

Gap de cobertura real: ninguna auditoria previa del modulo (.agent/,
docs/cotizaciones/) tenia tests de transicion de estado porque la maquina
de estados nunca existio -- 'estado' era editable via PATCH generico sin
ninguna validacion (documentado en MATRIZ_ESTADOS_COTIZACION.md,
COTIZACIONES_RELEASE_GATE.md). Este archivo cubre la implementacion nueva:
CotizacionService.cambiar_estado() (TRANSICIONES_VALIDAS).

Estados reales del modelo: BORRADOR/ENVIADA/ACEPTADA/CANCELADA -- no
BORRADOR/ENVIADA/APROBADA/ARCHIVADA (esos nombres no existen en este
dominio, confirmado en 3 auditorias independientes antes de implementar).
"""
import datetime

import pytest
from django_tenants.utils import schema_context
from rest_framework.exceptions import ValidationError

from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.cotizaciones.services import CotizacionService


def _crear_cotizacion(tenant, empresa, cliente):
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
            'tipo_item': 'PRODUCTO', 'descripcion': 'Item de prueba',
            'cantidad': 1, 'costo_unitario': 100, 'porcentaje_utilidad': 10,
            'unidad': 'UND', 'orden': 1,
        }],
    }
    return CotizacionService.crear_preforma(empresa, payload)


@pytest.mark.django_db
def test_cotizacion_nace_en_borrador(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        assert cotizacion.estado == Cotizacion.Estado.BORRADOR


@pytest.mark.django_db
def test_borrador_a_enviada_ok(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        actualizada = CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.ENVIADA)
        assert actualizada.estado == Cotizacion.Estado.ENVIADA


@pytest.mark.django_db
def test_enviada_a_borrador_ok(tenant, factory_empresa, factory_cliente):
    """ENVIADA -> BORRADOR: correcciones antes de que el cliente la acepte."""
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.ENVIADA)
        vuelta = CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.BORRADOR)
        assert vuelta.estado == Cotizacion.Estado.BORRADOR


@pytest.mark.django_db
def test_enviada_a_aceptada_ok(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.ENVIADA)
        aceptada = CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.ACEPTADA)
        assert aceptada.estado == Cotizacion.Estado.ACEPTADA


@pytest.mark.django_db
def test_borrador_a_cancelada_ok(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        cancelada = CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.CANCELADA)
        assert cancelada.estado == Cotizacion.Estado.CANCELADA


@pytest.mark.django_db
def test_enviada_a_cancelada_ok(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.ENVIADA)
        cancelada = CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.CANCELADA)
        assert cancelada.estado == Cotizacion.Estado.CANCELADA


@pytest.mark.django_db
def test_borrador_a_aceptada_rechazado(tenant, factory_empresa, factory_cliente):
    """No se puede saltar ENVIADA -- debe pasar primero por revision/envio."""
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        with pytest.raises(ValidationError):
            CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.ACEPTADA)


@pytest.mark.django_db
def test_aceptada_es_terminal(tenant, factory_empresa, factory_cliente):
    """ACEPTADA no admite ninguna transicion -- evita alterar en silencio
    una propuesta ya aprobada por el cliente."""
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.ENVIADA)
        CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.ACEPTADA)

        with pytest.raises(ValidationError):
            CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.CANCELADA)
        with pytest.raises(ValidationError):
            CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.BORRADOR)


@pytest.mark.django_db
def test_cancelada_es_terminal(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.CANCELADA)
        with pytest.raises(ValidationError):
            CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.BORRADOR)


@pytest.mark.django_db
def test_transicion_idempotente_mismo_estado_no_es_error(tenant, factory_empresa, factory_cliente):
    """Mandato §10: doble click / retry sobre la misma transicion no debe
    fallar. Enviar 2 veces seguidas una cotizacion ya ENVIADA es un no-op,
    no un error."""
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.ENVIADA)
        # repetir la misma transicion no lanza excepcion
        de_nuevo = CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.ENVIADA)
        assert de_nuevo.estado == Cotizacion.Estado.ENVIADA


@pytest.mark.django_db
def test_estado_invalido_es_rechazado(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        with pytest.raises(ValidationError):
            CotizacionService.cambiar_estado(cotizacion, "ESTADO_INVENTADO")


@pytest.mark.django_db
def test_patch_generico_ya_no_puede_cambiar_estado(tenant, factory_empresa, factory_cliente):
    """Mandato §7-8: 'estado' quedo fuera de allowed_fields de
    actualizar_cotizacion() -- un PATCH que intente incluir 'estado' lo
    ignora en silencio (no lo aplica), el estado real solo cambia via
    cambiar_estado()."""
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        assert cotizacion.estado == Cotizacion.Estado.BORRADOR

        actualizada = CotizacionService.actualizar_cotizacion(
            cotizacion, {"estado": Cotizacion.Estado.ACEPTADA}
        )
        assert actualizada.estado == Cotizacion.Estado.BORRADOR
