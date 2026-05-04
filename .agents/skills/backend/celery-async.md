# Skill: Celery Async & Background Tasks — SINTEL v2.62

**Carga cuando:** Implementar procesamiento en segundo plano, tareas pesadas, envíos masivos o cálculos nocturnos.

---

## 1. Desacoplamiento de Carga Pesada

Toda operación que tome más de 2 segundos o dependa de APIs de terceros (ej. DIAN) DEBE despacharse asíncronamente.

```python
# MALA PRÁCTICA (Bloquea el request HTTP)
ejecutar_operacion_masiva(empresa_id) 

# BUENA PRÁCTICA
from apps.tenant.<app>.tasks import ejecutar_operacion_masiva_task
ejecutar_operacion_masiva_task.delay(empresa_id)
```

## 2. Dead Letter Queue (Tolerancia a Fallos)

Las tareas de Celery deben ser resilientes. Si fallan definitivamente tras agotar reintentos, deben registrarse en un log auditable o modelo de base de datos (`FailedTenantTask`).

```python
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def procesar_operacion_task(self, empresa_id, payload):
    try:
        # Lógica de procesamiento
        pass
    except TransientError as exc:
        # Reintento con backoff exponencial
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
    except Exception as exc:
        # Fallo duro: Enviar a DLQ (Dead Letter Queue)
        logger.error(f"[DLQ] Fallo en procesar_operacion_task para empresa {empresa_id}: {exc}")
        # Insertar registro de fallo en BD si es necesario
```

## 3. Eficiencia en Workers (Batching y Garbage Collection)

Evitar cargar queries completas en memoria RAM dentro de las tareas de Celery. Usar `.iterator()` y liberar memoria.

```python
@shared_task
def procesar_lote_masivo(empresa_id):
    qs = MiModelo.objects.filter(empresa_id=empresa_id).iterator(chunk_size=1000)
    
    for registro in qs:
        # Procesar de a 1 o en mini-batches
        pass
```
