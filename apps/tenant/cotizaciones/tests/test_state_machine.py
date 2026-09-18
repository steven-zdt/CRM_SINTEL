"""COTIZACIONES-01/02: maquina de estados de Cotizacion.

Gap de cobertura real: ninguna auditoria previa del modulo (.agent/,
docs/cotizaciones/) tenia tests de transicion de estado porque la maquina
de estados nunca existio -- 'estado' era editable via PATCH generico sin
ninguna validacion (documentado en MATRIZ_ESTADOS_COTIZACION.md,
COTIZACIONES_RELEASE_GATE.md). Este archivo cubre CotizacionService.
cambiar_estado() (TRANSICIONES_VALIDAS).

COTIZACIONES-02 (mismo dia): renombrado ACEPTADA->APROBADA,
CANCELADA->RECHAZADA, + ARCHIVADA nuevo (0 filas reales afectadas,
verificado en los 3 tenants antes del rename). BORRADOR->ENVIADA ya no es
una transicion manual -- solo ocurre gated por PDF exitoso
(generar_pdf_y_enviar, ver test_pdf_gating.py).
"""
import datetime

import pytest
from django_tenants.utils import schema_context
from rest_framework.exceptions import ValidationError

from apps.tenant.cotizaciones.models import Cotizacion, CotizacionHistorialEstado
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


def _forzar_enviada(cotizacion):
    """Salta el gating de PDF real (no es lo que se prueba en este archivo)
    -- usa cambiar_estado() directo, que es exactamente lo que
    generar_pdf_y_enviar() hace internamente tras confirmar el PDF."""
    return CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.ENVIADA)


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
        actualizada = _forzar_enviada(cotizacion)
        assert actualizada.estado == Cotizacion.Estado.ENVIADA


@pytest.mark.django_db
def test_enviada_a_borrador_ok(tenant, factory_empresa, factory_cliente):
    """ENVIADA -> BORRADOR: correcciones antes de la decision humana."""
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        _forzar_enviada(cotizacion)
        vuelta = CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.BORRADOR)
        assert vuelta.estado == Cotizacion.Estado.BORRADOR


@pytest.mark.django_db
def test_enviada_a_aprobada_ok(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        _forzar_enviada(cotizacion)
        aprobada = CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.APROBADA)
        assert aprobada.estado == Cotizacion.Estado.APROBADA


@pytest.mark.django_db
def test_enviada_a_rechazada_ok(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        _forzar_enviada(cotizacion)
        rechazada = CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.RECHAZADA)
        assert rechazada.estado == Cotizacion.Estado.RECHAZADA


@pytest.mark.django_db
def test_aprobada_a_archivada_ok(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        _forzar_enviada(cotizacion)
        CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.APROBADA)
        archivada = CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.ARCHIVADA)
        assert archivada.estado == Cotizacion.Estado.ARCHIVADA


@pytest.mark.django_db
def test_rechazada_a_archivada_ok(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        _forzar_enviada(cotizacion)
        CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.RECHAZADA)
        archivada = CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.ARCHIVADA)
        assert archivada.estado == Cotizacion.Estado.ARCHIVADA


@pytest.mark.django_db
def test_borrador_a_aprobada_rechazado(tenant, factory_empresa, factory_cliente):
    """No se puede saltar ENVIADA -- debe pasar primero por revision/envio."""
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        with pytest.raises(ValidationError):
            CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.APROBADA)


@pytest.mark.django_db
def test_borrador_a_archivada_rechazado(tenant, factory_empresa, factory_cliente):
    """No existe atajo BORRADOR->ARCHIVADA -- solo APROBADA/RECHAZADA llegan ahi."""
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        with pytest.raises(ValidationError):
            CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.ARCHIVADA)


@pytest.mark.django_db
def test_aprobada_es_terminal_salvo_archivar(tenant, factory_empresa, factory_cliente):
    """APROBADA solo admite ->ARCHIVADA -- evita alterar en silencio una
    propuesta ya aprobada (no se puede volver a BORRADOR ni RECHAZAR)."""
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        _forzar_enviada(cotizacion)
        CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.APROBADA)

        with pytest.raises(ValidationError):
            CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.RECHAZADA)
        with pytest.raises(ValidationError):
            CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.BORRADOR)


@pytest.mark.django_db
def test_archivada_es_terminal(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        _forzar_enviada(cotizacion)
        CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.APROBADA)
        CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.ARCHIVADA)
        with pytest.raises(ValidationError):
            CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.BORRADOR)


@pytest.mark.django_db
def test_transicion_idempotente_mismo_estado_no_es_error(tenant, factory_empresa, factory_cliente):
    """Mandato §10: doble click / retry sobre la misma transicion no debe
    fallar. Aprobar 2 veces seguidas una cotizacion ya APROBADA es un no-op,
    no un error -- y no duplica historial."""
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        _forzar_enviada(cotizacion)
        CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.APROBADA)
        filas_antes = CotizacionHistorialEstado.objects.filter(cotizacion=cotizacion).count()

        de_nuevo = CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.APROBADA)
        assert de_nuevo.estado == Cotizacion.Estado.APROBADA
        assert CotizacionHistorialEstado.objects.filter(cotizacion=cotizacion).count() == filas_antes


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
            cotizacion, {"estado": Cotizacion.Estado.APROBADA}
        )
        assert actualizada.estado == Cotizacion.Estado.BORRADOR


# --------------------------------------------------------------------- #
# Historial (COTIZACIONES-02 Fase 03)
# --------------------------------------------------------------------- #

@pytest.mark.django_db
def test_cada_transicion_real_escribe_historial(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        _forzar_enviada(cotizacion)
        CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.APROBADA, motivo="cliente confirmo por correo")

        filas = list(
            CotizacionHistorialEstado.objects.filter(cotizacion=cotizacion).order_by("created_at")
        )
        assert [f.estado_nuevo for f in filas] == [
            Cotizacion.Estado.ENVIADA, Cotizacion.Estado.APROBADA,
        ]
        assert filas[0].estado_anterior == Cotizacion.Estado.BORRADOR
        assert filas[1].estado_anterior == Cotizacion.Estado.ENVIADA
        assert filas[1].motivo == "cliente confirmo por correo"


@pytest.mark.django_db
def test_historial_es_append_only_no_se_puede_alterar_via_service_layer(tenant, factory_empresa, factory_cliente):
    """No existe ningun metodo de update/delete en el Service Layer para
    CotizacionHistorialEstado -- confirmado por ausencia (CotizacionService
    no expone nada que edite una fila de historial ya escrita)."""
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        _forzar_enviada(cotizacion)
        assert not hasattr(CotizacionService, "actualizar_historial")
        assert not hasattr(CotizacionService, "eliminar_historial")


# --------------------------------------------------------------------- #
# Proteccion de datos por estado (COTIZACIONES-02 Fase 12)
# --------------------------------------------------------------------- #

@pytest.mark.django_db
def test_no_se_puede_editar_cotizacion_fuera_de_borrador(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        cotizacion = _forzar_enviada(cotizacion)
        with pytest.raises(ValidationError):
            CotizacionService.actualizar_cotizacion(cotizacion, {"iva_porcentaje": "5.00"})


@pytest.mark.django_db
def test_no_se_puede_eliminar_cotizacion_aprobada(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        cotizacion = _forzar_enviada(cotizacion)
        cotizacion = CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.APROBADA)
        with pytest.raises(ValidationError):
            CotizacionService.eliminar_cotizacion(cotizacion)
        assert Cotizacion.objects.filter(pk=cotizacion.pk).exists()


@pytest.mark.django_db
def test_no_se_puede_eliminar_cotizacion_archivada(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        cotizacion = _forzar_enviada(cotizacion)
        cotizacion = CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.RECHAZADA)
        cotizacion = CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.ARCHIVADA)
        with pytest.raises(ValidationError):
            CotizacionService.eliminar_cotizacion(cotizacion)


@pytest.mark.django_db
def test_borrador_sigue_siendo_eliminable(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(tenant, empresa, cliente)
        CotizacionService.eliminar_cotizacion(cotizacion)
        assert not Cotizacion.objects.filter(pk=cotizacion.pk).exists()
