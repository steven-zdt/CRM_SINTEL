"""
Ciclo de Vida Controlado v4.0 - Checklist documental (informativo, NO bloqueante).

Decision de producto (2026-09-18): los documentos por transicion pasaron de
gate duro a checklist opcional -- un documento faltante YA NO impide avanzar
de fase (antes dejaba el proyecto atascado con 400 "Faltan documentos
obligatorios"). Estos tests fijan el comportamiento nuevo:

- Avanzar de fase SIEMPRE funciona aunque no haya ningun documento cargado.
- El checklist (`resolver_requisitos_transicion`) sigue reportando con
  exactitud que falta y que no, para que la UI lo muestre.
- `documentos_obligatorios_faltantes` (el unico que puede bloquear) esta
  vacio para todas las transiciones, porque hoy ningun requisito esta
  marcado como obligatorio.
"""
import pytest
from django_tenants.utils import schema_context

from apps.tenant.proyectos.models import Proyecto, DocumentoProyecto
from apps.tenant.proyectos.services.business_service import cambiar_fase_proyecto
from apps.tenant.proyectos.services.documentos_service import (
    REQUISITOS_TRANSICION,
    documentos_faltantes,
    documentos_obligatorios_faltantes,
    resolver_requisitos_transicion,
)
from apps.tenant.empresa.models import Empresa


def _crear_proyecto(empresa, fase_actual):
    return Proyecto.objects.create(
        nombre=f'Proyecto Gate {fase_actual}', empresa=empresa, fase_actual=fase_actual,
    )


def _doc(proyecto, tipo, fase):
    return DocumentoProyecto.objects.create(
        proyecto=proyecto, empresa_id=proyecto.empresa_id, fase=fase,
        tipo_documento=tipo, activo=True,
    )


@pytest.mark.django_db
class TestDocumentosNoBloqueanElAvance:
    """El corazon del cambio: ninguna transicion se bloquea por falta de documentos."""

    @pytest.mark.parametrize('fase_actual,nueva_fase', [
        ('BORRADOR', 'INICIO'),
        ('INICIO', 'PLANEACION'),
        ('PLANEACION', 'EJECUCION'),
        ('EJECUCION', 'CIERRE'),
    ])
    def test_avanza_sin_ningun_documento(self, tenant1, fase_actual, nueva_fase):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa, fase_actual)

            resultado = cambiar_fase_proyecto(proyecto, nueva_fase)

            assert resultado.fase_actual == nueva_fase
            proyecto.refresh_from_db()
            assert proyecto.fase_actual == nueva_fase

    def test_recorrido_completo_del_ciclo_sin_documentos(self, tenant1):
        """BORRADOR -> INICIO -> PLANEACION -> EJECUCION -> CIERRE, expediente vacio."""
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa, 'BORRADOR')

            for nueva_fase in ('INICIO', 'PLANEACION', 'EJECUCION', 'CIERRE'):
                cambiar_fase_proyecto(proyecto, nueva_fase)
                proyecto.refresh_from_db()
                assert proyecto.fase_actual == nueva_fase

    def test_ningun_requisito_esta_marcado_como_obligatorio(self, tenant1):
        """Guard-rail: si alguien marca un requisito como obligatorio, este
        test falla y obliga a decidirlo conscientemente."""
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa, 'INICIO')

            for (fase_actual, nueva_fase) in REQUISITOS_TRANSICION:
                assert documentos_obligatorios_faltantes(proyecto, fase_actual, nueva_fase) == []


@pytest.mark.django_db
class TestChecklistSigueSiendoExacto:
    """El checklist informativo no perdio precision al dejar de bloquear."""

    def test_sin_ningun_documento_reporta_los_tres_faltantes(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa, 'INICIO')

            assert documentos_faltantes(proyecto, 'INICIO', 'PLANEACION') == [
                'Orden de Compra / Orden de Pedido',
                'Autorizacion',
                'Cotizacion aprobada',
            ]

    def test_reporta_solo_la_autorizacion_faltante(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa, 'INICIO')
            _doc(proyecto, 'ORDEN_COMPRA', 'INICIO')
            _doc(proyecto, 'COTIZACION_APROBADA', 'INICIO')

            assert documentos_faltantes(proyecto, 'INICIO', 'PLANEACION') == ['Autorizacion']

    def test_reporta_solo_el_cronograma_faltante(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa, 'PLANEACION')
            _doc(proyecto, 'ACTA_INICIO', 'PLANEACION')

            assert documentos_faltantes(proyecto, 'PLANEACION', 'EJECUCION') == ['Cronograma']

    def test_reporta_solo_el_informe_final_faltante(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa, 'EJECUCION')
            _doc(proyecto, 'ACTA_ENTREGA', 'EJECUCION')

            assert documentos_faltantes(proyecto, 'EJECUCION', 'CIERRE') == ['Informe final']

    def test_orden_de_compra_o_pedido_cualquiera_satisface_el_requisito(self, tenant1):
        """No debe pedir AMBAS: con una de las dos ese item queda cumplido."""
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()

            proyecto_a = _crear_proyecto(empresa, 'INICIO')
            _doc(proyecto_a, 'ORDEN_COMPRA', 'INICIO')
            orden_a = next(r for r in resolver_requisitos_transicion(proyecto_a, 'INICIO', 'PLANEACION')
                           if 'Orden' in r['label'])
            assert orden_a['cumplido'] is True

            proyecto_b = _crear_proyecto(empresa, 'INICIO')
            _doc(proyecto_b, 'ORDEN_PEDIDO', 'INICIO')
            orden_b = next(r for r in resolver_requisitos_transicion(proyecto_b, 'INICIO', 'PLANEACION')
                           if 'Orden' in r['label'])
            assert orden_b['cumplido'] is True

    def test_documento_inactivo_no_cuenta_como_cumplido(self, tenant1):
        """Un documento desactivado (reemplazado) no satisface el item."""
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa, 'EJECUCION')
            _doc(proyecto, 'INFORME_FINAL', 'EJECUCION')
            doc_acta = _doc(proyecto, 'ACTA_ENTREGA', 'EJECUCION')
            doc_acta.activo = False
            doc_acta.save(update_fields=['activo'])

            assert documentos_faltantes(proyecto, 'EJECUCION', 'CIERRE') == ['Acta de entrega']

    def test_checklist_expone_obligatorio_false_en_cada_item(self, tenant1):
        """La UI necesita este flag para rotular los documentos como opcionales."""
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa, 'INICIO')

            requisitos = resolver_requisitos_transicion(proyecto, 'INICIO', 'PLANEACION')
            assert requisitos, 'la transicion INICIO->PLANEACION debe tener checklist'
            for item in requisitos:
                assert item['obligatorio'] is False
                assert set(item) == {'label', 'cumplido', 'obligatorio'}
