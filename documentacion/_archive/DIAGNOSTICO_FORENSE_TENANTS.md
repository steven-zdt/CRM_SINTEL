# 🔬 Diagnóstico Forense: Creación de Tenants

## 📋 Resumen

Script de diagnóstico paso a paso para identificar exactamente dónde se rompe la cadena de creación de tenants cuando las tareas se quedan en estado `PENDING`.

## 🎯 Objetivo

Aislar si el fallo es de:
- **Lógica de Negocio**: El código Python falla silenciosamente
- **Infraestructura**: El worker de Celery no escucha la cola correcta

## 🚀 Cómo Ejecutar

### Opción 1: Dentro del Contenedor (Recomendado)

```bash
# 1. Entrar al contenedor web
docker-compose exec web bash

# 2. Ejecutar el diagnóstico
python scripts/debug_tenant_creation.py
```

### Opción 2: Desde el Host

```bash
# Ejecutar directamente en el contenedor
docker-compose exec web python scripts/debug_tenant_creation.py
```

## 📊 Pruebas que Ejecuta el Script

### PRUEBA 1: Validación de Configuración

**Qué verifica**:
- `CELERY_BROKER_URL` está configurado
- `CELERY_TASK_ROUTES` tiene la ruta para `onboard_tenant_task` → `high_priority`
- La app de Celery se inicializa correctamente

**Si falla**: Problema de configuración en `settings.py`

### PRUEBA 2: Creación Síncrona (Logic Check)

**Qué verifica**:
- El servicio `crear_tenant()` funciona correctamente
- Se crea el `Client` en la BD
- La señal `post_save` crea el `Domain` automáticamente
- Se crea el esquema PostgreSQL
- Se crea el `TenantMembership`

**Si falla**: El problema está en el código Python (servicio, señal, migraciones)

**Nota**: Hace rollback al final para no ensuciar la BD

### PRUEBA 3: Simulación Asíncrona Local (Eager Mode)

**Qué verifica**:
- La tarea Celery se puede importar y ejecutar
- La tarea funciona correctamente en modo eager (síncrono)
- No hay errores de sintaxis o importación en la tarea

**Si falla**: El problema está en `apps/public/tenants/tasks.py` (importación o sintaxis)

**Nota**: Limpia el tenant de prueba al finalizar

### PRUEBA 4: Inyección de Tarea Real (Queue Check)

**Qué verifica**:
- Hay workers de Celery activos
- Los workers están escuchando la cola `high_priority`
- La tarea se encola correctamente
- El worker toma la tarea y la procesa

**Si falla**: El problema está en la infraestructura (cola/worker)

**Nota**: Limpia el tenant de prueba al finalizar

## 📝 Interpretación de Resultados

### ✅ Todas las Pruebas Pasan

**Significado**: El sistema está funcionando correctamente.

**Acciones**:
- Si aún tienes problemas, revisa:
  1. Logs del worker: `docker-compose logs celery`
  2. Estado de Redis: `docker-compose ps redis`
  3. Configuración de red entre contenedores

### ❌ PRUEBA 1 Falla (Configuración)

**Diagnóstico**: Problema de configuración en `settings.py`

**Solución**:
1. Verificar que `CELERY_BROKER_URL` apunta a Redis
2. Verificar que `CELERY_TASK_ROUTES` tiene la ruta correcta
3. Verificar que `CELERY_TASK_DEFAULT_QUEUE` está configurado

### ❌ PRUEBA 2 Falla (Lógica de Negocio)

**Diagnóstico**: El problema está en el código Python

**Solución**:
1. Revisar el traceback mostrado por el script
2. Verificar `apps/services/onboarding/empresa_service.py`
3. Verificar `apps/public/tenants/signals.py`
4. Verificar que las migraciones están aplicadas

### ❌ PRUEBA 3 Falla (Tarea Celery)

**Diagnóstico**: El problema está en la tarea Celery

**Solución**:
1. Revisar el traceback mostrado por el script
2. Verificar `apps/public/tenants/tasks.py`
3. Verificar imports y sintaxis
4. Verificar que todas las dependencias están instaladas

### ❌ PRUEBA 4 Falla (Infraestructura)

**Diagnóstico**: El problema está en la infraestructura (cola/worker)

**Posibles Causas**:
1. El worker no está corriendo
2. El worker no está escuchando la cola `high_priority`
3. Hay un problema de conexión con Redis
4. La tarea no se encoló en la cola correcta

**Solución**:
1. Verificar que el worker está corriendo:
   ```bash
   docker-compose ps celery
   ```

2. Verificar que el worker escucha la cola correcta:
   ```bash
   docker-compose logs celery | grep -i "ready"
   ```
   
   Deberías ver algo como:
   ```
   celery@... ready.
   ```

3. Verificar el comando del worker en `docker-compose.yaml`:
   ```yaml
   command: celery -A config worker --loglevel=info --concurrency=4 -Q high_priority,default
   ```
   
   **IMPORTANTE**: El orden importa. `high_priority` debe ir primero.

4. Reiniciar el worker:
   ```bash
   docker-compose restart celery
   # o
   docker-compose down
   docker-compose up -d --build
   ```

## 🔍 Comandos de Verificación Adicionales

### Verificar Workers Activos

```bash
docker-compose exec web celery -A config inspect active
```

### Verificar Tareas en Cola

```bash
docker-compose exec redis redis-cli
> KEYS *
> LLEN celery  # Ver tareas en cola default
> LLEN high_priority  # Ver tareas en cola high_priority
```

### Verificar Logs del Worker

```bash
docker-compose logs celery | tail -50
docker-compose logs celery | grep -i "onboard_tenant_task"
docker-compose logs celery | grep -i "error"
```

### Verificar Estado de Redis

```bash
docker-compose exec redis redis-cli ping
# Debe responder: PONG
```

## 🐛 Troubleshooting Específico

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

### Tarea sigue en PENDING después de todas las pruebas

**Causa**: El worker no está escuchando la cola `high_priority`.

**Solución**:
1. Verificar logs: `docker-compose logs celery`
2. Verificar comando del worker: `docker-compose exec celery ps aux | grep celery`
3. Reiniciar completamente: `docker-compose down && docker-compose up -d`

## 📋 Checklist de Verificación

Antes de ejecutar el diagnóstico, verifica:

- [ ] Docker está corriendo
- [ ] Contenedores están levantados: `docker-compose ps`
- [ ] Redis está disponible: `docker-compose ps redis`
- [ ] Worker de Celery está corriendo: `docker-compose ps celery`
- [ ] Base de datos está accesible: `docker-compose ps db`

## 🎯 Resultado Esperado

Si todas las pruebas pasan:

```
✅ PRUEBA 1: Configuración válida
✅ PRUEBA 2: Creación síncrona exitosa (lógica de negocio correcta)
✅ PRUEBA 3: Celery eager mode exitoso (tarea se ejecuta correctamente)
✅ PRUEBA 4: Cola real verificada

✅ TODAS LAS PRUEBAS PASARON
El sistema está funcionando correctamente
```

Si alguna prueba falla, el script te indicará exactamente dónde está el problema y cómo solucionarlo.

## 📚 Referencias

- Documentación de Celery: https://docs.celeryproject.org/
- Configuración de Colas: `documentacion/CONFIGURACION_COLAS_PRIORITARIAS.md`
- Auditoría CRUD: `documentacion/AUDITORIA_CRUD_TENANTS.md`
