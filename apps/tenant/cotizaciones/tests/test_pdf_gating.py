"""COTIZACIONES-02 Fase 04: BORRADOR -> generar PDF -> exito: ENVIADA / error: BORRADOR.

Gap de cobertura real: no existia ningun test de la transicion gated por
PDF -- el flujo previo (`_generar_pdf_sincronizado`, usado por
crear_preforma/actualizar_cotizacion) traga cualquier fallo en silencio y
nunca tocaba el estado. `CotizacionService.generar_pdf_y_enviar()` es la
implementacion nueva de esta fase.

El caso de exito usa el motor PDF real (xhtml2pdf), sin mocks -- ya sabemos
que funciona con datos reales (usado desde AI-VECTOR... no, desde
crear_preforma() en cada creacion de Cotizacion). Los casos de fallo
(controlado y excepcion) usan mock sobre generar_pdf_publico: inducir un
fallo real y deterministico de renderizado HTML->PDF no es practico ni
estable para un test automatizado.
"""
import datetime
from unittest.mock import patch

import pytest
from django_tenants.utils import schema_context
from rest_framework.exceptions import ValidationError

from apps.tenant.cotizaciones.models import Cotizacion, CotizacionHistorialEstado
from apps.tenant.cotizaciones.services import CotizacionService


def _crear_cotizacion_borrador(empresa, cliente):
    from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion

    ConfiguracionCotizacion.objects.get_or_create(
        empresa=empresa,
        defaults={'dias_validez': 15, 'nombre_configuracion': 'Perfil General', 'es_activo': True},
    )
    payload = {
        'cliente': cliente.id,
        'fecha_emision': datetime.date(2026, 3, 30),
        'items': [{
            'tipo_item': 'PRODUCTO', 'descripcion': 'Item PDF test',
            'cantidad': 1, 'costo_unitario': 100, 'porcentaje_utilidad': 10,
            'unidad': 'UND', 'orden': 1,
        }],
    }
    return CotizacionService.crear_preforma(empresa, payload)


@pytest.mark.django_db
def test_pdf_exitoso_pasa_de_borrador_a_enviada(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion_borrador(empresa, cliente)
        assert cotizacion.estado == Cotizacion.Estado.BORRADOR

        actualizada, pdf_bytes = CotizacionService.generar_pdf_y_enviar(cotizacion, empresa)

        assert actualizada.estado == Cotizacion.Estado.ENVIADA
        assert pdf_bytes  # bytes reales, no vacio
        assert pdf_bytes[:4] == b"%PDF"


@pytest.mark.django_db
def test_pdf_exitoso_escribe_historial(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion_borrador(empresa, cliente)
        CotizacionService.generar_pdf_y_enviar(cotizacion, empresa)

        fila = CotizacionHistorialEstado.objects.get(cotizacion=cotizacion)
        assert fila.estado_anterior == Cotizacion.Estado.BORRADOR
        assert fila.estado_nuevo == Cotizacion.Estado.ENVIADA
        assert "PDF" in fila.motivo


@pytest.mark.django_db
def test_pdf_fallo_controlado_permanece_borrador(tenant, factory_empresa, factory_cliente):
    """generar_pdf_publico() devuelve None (fallo controlado de xhtml2pdf,
    pisa_status.err) -- la cotizacion NUNCA debe pasar a ENVIADA."""
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion_borrador(empresa, cliente)

        with patch(
            "apps.tenant.cotizaciones.services.business_service.CotizacionPDFExportService.generar_pdf_publico",
            return_value=None,
        ):
            with pytest.raises(ValidationError):
                CotizacionService.generar_pdf_y_enviar(cotizacion, empresa)

        cotizacion.refresh_from_db()
        assert cotizacion.estado == Cotizacion.Estado.BORRADOR
        assert not CotizacionHistorialEstado.objects.filter(cotizacion=cotizacion).exists()


@pytest.mark.django_db
def test_pdf_excepcion_no_controlada_permanece_borrador(tenant, factory_empresa, factory_cliente):
    """generar_pdf_publico() lanza una excepcion (ImportError/error de
    template) -- se captura, se loguea, y la cotizacion permanece BORRADOR
    (nunca se propaga un 500 sin control ni se pasa a ENVIADA a ciegas)."""
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion_borrador(empresa, cliente)

        with patch(
            "apps.tenant.cotizaciones.services.business_service.CotizacionPDFExportService.generar_pdf_publico",
            side_effect=RuntimeError("fallo simulado de renderizado"),
        ):
            with pytest.raises(ValidationError):
                CotizacionService.generar_pdf_y_enviar(cotizacion, empresa)

        cotizacion.refresh_from_db()
        assert cotizacion.estado == Cotizacion.Estado.BORRADOR


@pytest.mark.django_db
def test_pdf_repetido_no_altera_estado_ya_enviada(tenant, factory_empresa, factory_cliente):
    """Cotizacion ya ENVIADA: generar/descargar PDF de nuevo no cambia el
    estado (no hay transicion ENVIADA->ENVIADA en TRANSICIONES_VALIDAS
    porque cambiar_estado() nunca se invoca aqui -- generar_pdf_y_enviar()
    solo transiciona si el estado actual es BORRADOR)."""
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion_borrador(empresa, cliente)
        cotizacion, _ = CotizacionService.generar_pdf_y_enviar(cotizacion, empresa)
        assert cotizacion.estado == Cotizacion.Estado.ENVIADA
        filas_antes = CotizacionHistorialEstado.objects.filter(cotizacion=cotizacion).count()

        actualizada, pdf_bytes = CotizacionService.generar_pdf_y_enviar(cotizacion, empresa)

        assert actualizada.estado == Cotizacion.Estado.ENVIADA
        assert pdf_bytes  # sigue generando el PDF para descarga
        assert CotizacionHistorialEstado.objects.filter(cotizacion=cotizacion).count() == filas_antes


@pytest.mark.django_db
def test_pdf_repetido_no_altera_estado_ya_aprobada(tenant, factory_empresa, factory_cliente):
    """Descargar PDF de una cotizacion APROBADA no la regresa a ningun otro
    estado -- exportar-pdf/generar-pdf nunca tocan el estado salvo el
    camino BORRADOR->ENVIADA."""
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion_borrador(empresa, cliente)
        CotizacionService.generar_pdf_y_enviar(cotizacion, empresa)
        CotizacionService.cambiar_estado(cotizacion, Cotizacion.Estado.APROBADA)

        actualizada, pdf_bytes = CotizacionService.generar_pdf_y_enviar(cotizacion, empresa)

        assert actualizada.estado == Cotizacion.Estado.APROBADA
        assert pdf_bytes
