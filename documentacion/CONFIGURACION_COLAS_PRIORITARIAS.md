# 🔧 Configuración de Colas Prioritarias - Fix "Pending" State

## 📋 Resumen

Se ha implementado una arquitectura de **Colas Explícitas** para garantizar que la tarea crítica `onboard_tenant_task` sea procesada inmediatamente por un worker dedicado, solucionando el problema de tareas que se quedan en estado `PENDING`.

## ✅ Cambios Implementados

### 1. Configuración de Celery (`config/settings.py`)

**Rutas Explícitas de Tareas**:
```python
CELERY_TASK_DEFAULT_QUEUE = 'default'

CELERY_TASK_ROUTES = {
    # Tarea crítica de onboarding: cola de alta prioridad
    'apps.public.tenants.tasks.onboard_tenant_task': {'queue': 'high_priority'},
    
    # Todas las demás tareas van a default
    '*': {'queue': 'default'},
}
```

**Beneficios**:
- La tarea `onboard_tenant_task` va directamente a `high_priority`
- El worker procesa primero las tareas de alta prioridad
- Evita que tareas menos críticas bloqueen el onboarding

### 2. Servicio Celery Worker (`docker-compose.yaml`)

**Nuevo Servicio**:
```yaml
celery:
  build: .
  command: celery -A config worker --loglevel=info --concurrency=4 -Q high_priority,default
  volumes:
    - .:/app
  env_file:
    - .env
  depends_on:
    db:
      condition: service_healthy
    redis:
      condition: service_started
  environment:
    - C_FORCE_ROOT=1
```

**Características**:
- Escucha `high_priority` primero (orden importa)
- Luego escucha `default`
- Concurrencia de 4 workers
- Logs detallados para debugging

### 3. Tarea Mejorada (`apps/public/tenants/tasks.py`)

**Decorador Actualizado**:
```python
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    queue='high_priority'  # ⚠️ CRÍTICO: Forzar cola de alta prioridad
)
def onboard_tenant_task(...):
    logger.info("🚀 INICIANDO ONBOARDING TASK [ID: %s] ...", self.request.id)
    # ... resto del código ...
    logger.info("✅ ONBOARDING TASK COMPLETADA [ID: %s] ...", self.request.id)
```

**Mejoras**:
- Logs al inicio y fin de la tarea
- Cola explícita en el decorador (doble seguridad)
- Información detallada en logs para debugging

### 4. Vista Optimizada (`apps/public/console/views.py`)

**Encolado Directo**:
```python
# Encolar tarea directamente (no hay transacciones activas en este punto)
task = onboard_tenant_task.delay(**task_kwargs)
task_id = task.id
```

**Nota**: Se simplificó el código porque no hay transacciones activas en este punto (solo validaciones). Si en el futuro se necesita `transaction.on_commit`, se puede implementar con un modelo intermedio.

## 🚀 Pasos Críticos Post-Implementación

### ⚠️ IMPORTANTE: Reiniciar Contenedores

**El worker DEBE reiniciarse para reconocer la nueva cola `high_priority`.**

```bash
# Opción 1: Reinicio completo (recomendado)
docker-compose down
docker-compose up -d --build

# Opción 2: Solo reiniciar Celery
docker-compose restart celery

# Opción 3: Reconstruir solo Celery
docker-compose up -d --build celery
```

### Verificación

1. **Verificar que el worker está corriendo**:
   ```bash
   docker-compose ps celery
   ```

2. **Verificar que el worker escucha las colas correctas**:
   ```bash
   docker-compose logs celery | grep -i "ready"
   ```
   
   Deberías ver algo como:
   ```
   celery@... ready.
   ```

3. **Verificar que la tarea se encola correctamente**:
   ```bash
   docker-compose logs celery | grep -i "onboard_tenant_task"
   ```

4. **Crear un tenant de prueba**:
   - Ir a `http://localhost:8000/console/tenants/new/`
   - Crear un tenant
   - Verificar que el estado cambia de `PENDING` a `STARTED` y luego a `SUCCESS`

## 🔍 Diagnóstico

### Si la tarea sigue en PENDING

1. **Verificar que el worker está corriendo**:
   ```bash
   docker-compose ps celery
   ```

2. **Verificar logs del worker**:
   ```bash
   docker-compose logs celery | tail -50
   ```

3. **Verificar que Redis está disponible**:
   ```bash
   docker-compose exec redis redis-cli ping
   # Debe responder: PONG
   ```

4. **Verificar colas en Redis**:
   ```bash
   docker-compose exec redis redis-cli
   > KEYS *
   > LLEN celery  # Ver tareas en cola default
   > LLEN high_priority  # Ver tareas en cola high_priority
   ```

5. **Ejecutar diagnóstico**:
   ```bash
   python manage.py diagnostico_tenant <task_id>
   ```

### Comandos Útiles

```bash
# Ver workers activos
docker-compose exec web celery -A config inspect active

# Ver tareas programadas
docker-compose exec web celery -A config inspect scheduled

# Ver tareas reservadas
docker-compose exec web celery -A config inspect reserved

# Limpiar colas (si es necesario)
docker-compose exec web celery -A config purge

# Ver estadísticas
docker-compose exec web celery -A config inspect stats
```

## 📊 Arquitectura de Colas

```
┌─────────────────┐
│   Consola Web   │
│  (Django View)  │
└────────┬────────┘
         │
         │ onboard_tenant_task.delay()
         ▼
┌─────────────────┐
│      Redis      │
│  (Broker)       │
│                 │
│  high_priority  │ ← Tarea crítica
│  default        │ ← Otras tareas
└────────┬────────┘
         │
         │ Worker escucha ambas colas
         │ (high_priority primero)
         ▼
┌─────────────────┐
│ Celery Worker   │
│                 │
│ 1. Procesa      │
│    high_priority│
│ 2. Procesa      │
│    default      │
└─────────────────┘
```

## 🎯 Beneficios

1. **Procesamiento Inmediato**: Tareas críticas se procesan primero
2. **Fiabilidad**: Mismo nivel de confiabilidad que el Admin (síncrono)
3. **Escalabilidad**: Fácil agregar más workers o colas
4. **Debugging**: Logs detallados para identificar problemas
5. **Priorización**: Sistema claro de prioridades

## 🔄 Flujo Completo

1. Usuario crea tenant desde consola
2. Vista valida datos y encola tarea en `high_priority`
3. Worker toma la tarea inmediatamente (prioridad alta)
4. Tarea se ejecuta y crea tenant
5. Estado cambia de `PENDING` → `STARTED` → `SUCCESS`
6. HTMX actualiza la UI automáticamente

## 📝 Notas Importantes

- **El orden de las colas importa**: `-Q high_priority,default` significa que `high_priority` se procesa primero
- **La tarea tiene doble configuración**: En `CELERY_TASK_ROUTES` y en el decorador `@shared_task(queue='high_priority')`
- **Los logs son críticos**: Siempre revisa los logs si hay problemas
- **Reinicio obligatorio**: El worker debe reiniciarse después de cambios en configuración

## 🐛 Troubleshooting

### Error: "No module named 'config'"

**Causa**: El worker no puede importar el módulo de configuración.

**Solución**:
```bash
# Verificar que el PYTHONPATH está correcto
docker-compose exec celery env | grep PYTHONPATH

# Reconstruir el contenedor
docker-compose up -d --build celery
```

### Error: "Connection refused" a Redis

**Causa**: Redis no está disponible o no está en la red correcta.

**Solución**:
```bash
# Verificar que Redis está corriendo
docker-compose ps redis

# Verificar conectividad
docker-compose exec celery ping redis
```

### Tarea sigue en PENDING después de reiniciar

**Causa**: El worker no está escuchando la cola `high_priority`.

**Solución**:
1. Verificar logs: `docker-compose logs celery`
2. Verificar comando del worker: `docker-compose exec celery ps aux | grep celery`
3. Reiniciar completamente: `docker-compose down && docker-compose up -d`

## ✅ Checklist de Verificación

- [ ] `CELERY_TASK_ROUTES` configurado en `settings.py`
- [ ] Servicio `celery` agregado en `docker-compose.yaml`
- [ ] Tarea tiene `queue='high_priority'` en el decorador
- [ ] Tarea tiene logs al inicio y fin
- [ ] Worker reiniciado después de cambios
- [ ] Worker escucha `high_priority,default` (verificar logs)
- [ ] Redis está disponible y respondiendo
- [ ] Prueba de creación de tenant funciona

## 🎉 Resultado Esperado

Después de implementar estos cambios y reiniciar:

1. ✅ La tarea se encola inmediatamente
2. ✅ El worker la toma en menos de 1 segundo
3. ✅ El estado cambia de `PENDING` → `STARTED` → `SUCCESS`
4. ✅ La UI se actualiza automáticamente con HTMX
5. ✅ Los logs muestran el progreso completo

La creación de tenants desde la consola ahora tiene la misma fiabilidad que desde el Admin.
