"""
Ciclo de Vida Controlado v4.0 - Concurrencia (Fase 48 de la mision).

`@pytest.mark.django_db(transaction=True)` + threads reales -- igual que
test_cartera_concurrencia.py (patron ya establecido en este repo): un test
envuelto en la transaccion automatica de `django_db` normal NO detectaria un
`select_for_update()` mal usado, porque ambos "hilos" verian los mismos
datos no confirmados de la misma transaccion externa.

Escenario: proyecto en INICIO con el expediente ya completo. Dos hilos
intentan simultaneamente avanzar a PLANEACION. Sin select_for_update(),
ambos podrian leer fase_actual='INICIO' y crear DOS filas de historial para
la misma transicion. Con el lock, el segundo hilo espera, relee
fase_actual='PLANEACION' (ya aplicado por el primero) y su propia llamada
es idempotente (no crea una segunda fila) -- exactamente un historial, un
estado final consistente, ningun choque de escritura.
"""
import threading

import pytest
from django.db import connection
from django_tenants.utils import schema_context

from apps.tenant.proyectos.models import Proyecto, DocumentoProyecto, HistorialFaseProyecto
from apps.tenant.proyectos.services.business_service import cambiar_fase_proyecto
from apps.tenant.empresa.models import Empresa


@pytest.mark.django_db(transaction=True)
def test_dos_transiciones_simultaneas_a_la_misma_fase_no_duplican_historial(tenant1):
    with schema_context(tenant1.schema_name):
        empresa = Empresa.objects.first()
        proyecto = Proyecto.objects.create(
            nombre='Proyecto Concurrencia', empresa=empresa, fase_actual='INICIO',
        )
        for tipo in ('ORDEN_COMPRA', 'AUTORIZACION', 'COTIZACION_APROBADA'):
            DocumentoProyecto.objects.create(
                proyecto=proyecto, empresa_id=empresa.id, fase='INICIO',
                tipo_documento=tipo, activo=True,
            )
        proyecto_pk = proyecto.pk

    resultados = {}
    barrera = threading.Barrier(2)

    def _avanzar(nombre):
        try:
            with schema_context(tenant1.schema_name):
                proyecto_hilo = Proyecto.objects.get(pk=proyecto_pk)
                barrera.wait(timeout=5)  # maximiza la probabilidad de solape real
                cambiar_fase_proyecto(proyecto_hilo, 'PLANEACION')
                resultados[nombre] = 'OK'
        except Exception as exc:
            resultados[nombre] = f'ERROR: {exc}'
        finally:
            connection.close()

    hilo_a = threading.Thread(target=_avanzar, args=('A',))
    hilo_b = threading.Thread(target=_avanzar, args=('B',))
    hilo_a.start()
    hilo_b.start()
    hilo_a.join(timeout=10)
    hilo_b.join(timeout=10)

    # Ninguno de los dos hilos debe fallar: el que llega segundo encuentra
    # fase_actual ya en PLANEACION y su propia llamada es idempotente (no
    # es un salto de fase invalido, es la MISMA fase de destino).
    assert resultados == {'A': 'OK', 'B': 'OK'}, f'Resultados inesperados: {resultados}'

    with schema_context(tenant1.schema_name):
        proyecto_final = Proyecto.objects.get(pk=proyecto_pk)
        assert proyecto_final.fase_actual == 'PLANEACION'

        historial = HistorialFaseProyecto.objects.filter(proyecto_id=proyecto_pk)
        assert historial.count() == 1, (
            'select_for_update() debio serializar los dos hilos -- solo UNA '
            'transicion real ocurrio, la otra fue un no-op idempotente. '
            f'Filas de historial encontradas: {list(historial.values("fase_anterior", "fase_nueva"))}'
        )
