"""
Ciclo de Vida Controlado v4.0 - Bitacora de Ejecucion extendida (Fase 16/17/50).

TareaDiariaProyecto ya cubria fecha/responsable/descripcion/estado; esta
mision le agrego avance/bloqueos/incidencias (Fase 17). Estos tests cubren
solo lo NUEVO -- el resto del comportamiento (rango de fechas, DSV) ya esta
cubierto en test_tareas_diarias.py y no se repite aqui.
"""
import pytest
from django_tenants.utils import schema_context
from rest_framework.exceptions import ValidationError

from apps.tenant.proyectos.models import Proyecto, TareaDiariaProyecto
from apps.tenant.proyectos.services.tareas_service import TareasDiariasBusinessService
from apps.tenant.empresa.models import Empresa


@pytest.mark.django_db
class TestBitacoraExtendida:

    def test_crear_tarea_con_avance_bloqueos_incidencias(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = Proyecto.objects.create(
                nombre='Proyecto Bitacora', empresa=empresa, fase_actual='EJECUCION',
                fecha_inicio='2026-01-01', fecha_fin_estimada='2026-12-31',
            )

            tarea = TareasDiariasBusinessService.crear_tarea(
                empresa=empresa, proyecto=proyecto,
                fecha_inicio='2026-06-01', fecha_fin='2026-06-01',
                titulo='Instalacion de cableado', asignado_a='Tecnico Juan',
                avance=40, bloqueos='Falta autorizacion de acceso al site',
                incidencias='Corte de energia de 2 horas',
            )

            tarea.refresh_from_db()
            assert tarea.avance == 40
            assert tarea.bloqueos == 'Falta autorizacion de acceso al site'
            assert tarea.incidencias == 'Corte de energia de 2 horas'

    def test_avance_es_opcional(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = Proyecto.objects.create(
                nombre='Proyecto Bitacora Sin Avance', empresa=empresa, fase_actual='EJECUCION',
            )

            tarea = TareasDiariasBusinessService.crear_tarea(
                empresa=empresa, proyecto=proyecto,
                fecha_inicio='2026-06-02', fecha_fin='2026-06-02', titulo='Tarea sin avance reportado',
            )

            assert tarea.avance is None
            assert tarea.bloqueos == ''
            assert tarea.incidencias == ''

    def test_avance_mayor_a_100_es_rechazado_a_nivel_bd(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = Proyecto.objects.create(
                nombre='Proyecto Avance Invalido', empresa=empresa, fase_actual='EJECUCION',
            )
            tarea = TareaDiariaProyecto(
                empresa=empresa, proyecto=proyecto, fecha_inicio='2026-06-03', fecha_fin='2026-06-03',
                titulo='Tarea avance invalido', avance=150,
            )
            with pytest.raises(Exception):
                tarea.full_clean()

    def test_actualizar_tarea_permite_editar_los_3_campos_nuevos(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = Proyecto.objects.create(
                nombre='Proyecto Bitacora Update', empresa=empresa, fase_actual='EJECUCION',
            )
            tarea = TareasDiariasBusinessService.crear_tarea(
                empresa=empresa, proyecto=proyecto,
                fecha_inicio='2026-06-04', fecha_fin='2026-06-04', titulo='Tarea a actualizar',
            )

            TareasDiariasBusinessService.actualizar_tarea(tarea, {
                'avance': 75, 'bloqueos': 'Ninguno', 'incidencias': 'Ninguna',
            })

            tarea.refresh_from_db()
            assert tarea.avance == 75
            assert tarea.bloqueos == 'Ninguno'
            assert tarea.incidencias == 'Ninguna'

    def test_bloqueo_en_cierre_sigue_aplicando_a_los_campos_nuevos(self, tenant1):
        """
        La regla de bloqueo en CIERRE ya existente (tareas_service.py) valida
        sobre proyecto.fase_actual, no sobre campos especificos -- confirma
        que sigue protegiendo incluso al intentar tocar solo los 3 campos
        nuevos de bitacora.
        """
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = Proyecto.objects.create(
                nombre='Proyecto Bitacora Cierre', empresa=empresa, fase_actual='EJECUCION',
            )
            tarea = TareasDiariasBusinessService.crear_tarea(
                empresa=empresa, proyecto=proyecto,
                fecha_inicio='2026-06-05', fecha_fin='2026-06-05', titulo='Tarea previa al cierre',
            )

            proyecto.fase_actual = 'CIERRE'
            proyecto.save(update_fields=['fase_actual'])

            with pytest.raises(ValidationError):
                TareasDiariasBusinessService.actualizar_tarea(tarea, {'avance': 100})
