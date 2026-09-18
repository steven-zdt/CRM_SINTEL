"""
Ciclo de Vida Controlado v4.0 - Maquina de estados (Fase 44/46 de la mision).

Unidad: valida el mapa TRANSICIONES_VALIDAS_FASE de
services/business_service.py::cambiar_fase_proyecto() de forma aislada.
Los documentos requeridos se pre-cargan en cada test (via DocumentoProyecto)
para que la unica variable bajo prueba sea la adyacencia de fases, no el
gate documental (eso vive en test_lifecycle_gates_documentales.py).
"""
import pytest
from django_tenants.utils import schema_context
from rest_framework.exceptions import ValidationError

from apps.tenant.proyectos.models import Proyecto, DocumentoProyecto, HistorialFaseProyecto
from apps.tenant.proyectos.services.business_service import cambiar_fase_proyecto
from apps.tenant.empresa.models import Empresa


def _crear_proyecto(empresa, fase_actual='BORRADOR', **extra):
    return Proyecto.objects.create(
        nombre=f'Proyecto Transicion {fase_actual}', empresa=empresa, fase_actual=fase_actual, **extra
    )


def _satisfacer_documentos_inicio_planeacion(proyecto):
    for tipo in ('ORDEN_COMPRA', 'AUTORIZACION', 'COTIZACION_APROBADA'):
        DocumentoProyecto.objects.create(
            proyecto=proyecto, empresa_id=proyecto.empresa_id, fase='INICIO',
            tipo_documento=tipo, activo=True,
        )


def _satisfacer_documentos_planeacion_ejecucion(proyecto):
    for tipo in ('ACTA_INICIO', 'CRONOGRAMA'):
        DocumentoProyecto.objects.create(
            proyecto=proyecto, empresa_id=proyecto.empresa_id, fase='PLANEACION',
            tipo_documento=tipo, activo=True,
        )


def _satisfacer_documentos_ejecucion_cierre(proyecto):
    for tipo in ('ACTA_ENTREGA', 'INFORME_FINAL'):
        DocumentoProyecto.objects.create(
            proyecto=proyecto, empresa_id=proyecto.empresa_id, fase='EJECUCION',
            tipo_documento=tipo, activo=True,
        )


@pytest.mark.django_db
class TestTransicionesValidas:

    def test_borrador_a_inicio_no_requiere_documentos(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa, 'BORRADOR')

            resultado = cambiar_fase_proyecto(proyecto, 'INICIO')

            assert resultado.fase_actual == 'INICIO'
            assert HistorialFaseProyecto.objects.filter(proyecto=proyecto).count() == 1

    def test_inicio_a_planeacion_con_documentos_completos(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa, 'INICIO')
            _satisfacer_documentos_inicio_planeacion(proyecto)

            resultado = cambiar_fase_proyecto(proyecto, 'PLANEACION')

            assert resultado.fase_actual == 'PLANEACION'

    def test_planeacion_a_ejecucion_con_documentos_completos(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa, 'PLANEACION')
            _satisfacer_documentos_planeacion_ejecucion(proyecto)

            resultado = cambiar_fase_proyecto(proyecto, 'EJECUCION')

            assert resultado.fase_actual == 'EJECUCION'

    def test_ejecucion_a_cierre_con_documentos_completos(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa, 'EJECUCION')
            _satisfacer_documentos_ejecucion_cierre(proyecto)

            resultado = cambiar_fase_proyecto(proyecto, 'CIERRE')

            assert resultado.fase_actual == 'CIERRE'

    def test_misma_fase_es_idempotente_y_no_crea_historial(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa, 'INICIO')

            cambiar_fase_proyecto(proyecto, 'INICIO')

            proyecto.refresh_from_db()
            assert proyecto.fase_actual == 'INICIO'
            assert HistorialFaseProyecto.objects.filter(proyecto=proyecto).count() == 0


@pytest.mark.django_db
class TestSaltosDeFaseProhibidos:
    """
    Ejemplos explicitamente prohibidos por la mision (seccion 3):
    BORRADOR -> EJECUCION, BORRADOR -> CIERRE, INICIO -> EJECUCION,
    PLANEACION -> CIERRE.
    """

    @pytest.mark.parametrize('fase_origen,fase_destino', [
        ('BORRADOR', 'EJECUCION'),
        ('BORRADOR', 'CIERRE'),
        ('BORRADOR', 'PLANEACION'),
        ('INICIO', 'EJECUCION'),
        ('INICIO', 'CIERRE'),
        ('INICIO', 'BORRADOR'),
        ('PLANEACION', 'CIERRE'),
        ('PLANEACION', 'INICIO'),
        ('EJECUCION', 'BORRADOR'),
        ('EJECUCION', 'PLANEACION'),
        ('CIERRE', 'EJECUCION'),
        ('CIERRE', 'BORRADOR'),
    ])
    def test_salto_de_fase_rechazado(self, tenant1, fase_origen, fase_destino):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa, fase_origen)

            with pytest.raises(ValidationError) as exc_info:
                cambiar_fase_proyecto(proyecto, fase_destino)

            assert 'no permitida' in str(exc_info.value.detail).lower()

            proyecto.refresh_from_db()
            assert proyecto.fase_actual == fase_origen, (
                'El proyecto no debe quedar mutado en BD tras una transicion rechazada.'
            )
            assert HistorialFaseProyecto.objects.filter(proyecto=proyecto).count() == 0

    def test_fase_invalida_es_rechazada(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa, 'BORRADOR')

            with pytest.raises(ValidationError):
                cambiar_fase_proyecto(proyecto, 'FASE_QUE_NO_EXISTE')

            proyecto.refresh_from_db()
            assert proyecto.fase_actual == 'BORRADOR'
