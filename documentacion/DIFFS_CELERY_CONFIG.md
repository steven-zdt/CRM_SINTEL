# CELERY: CONFIG + RUTAS + COMPATIBILIDAD

**Fecha:** 2026-02-10  
**Estado:** ✅ Validado con Cambios Necesarios

---

## 🔍 VALIDACIÓN REALIZADA

### 1. config/celery.py

**Estado actual:**
- ✅ `app = Celery('config')` está correcto
- ✅ `autodiscover_tasks(lambda: settings.INSTALLED_APPS)` apunta correctamente a apps
- ❌ `autodiscover_tasks(packages=["apps.services.xml_ingest"])` apunta a módulo legacy
- ❌ `__import__("apps.services.xml_ingest.tasks")` importa módulo legacy
- ❌ `app.conf.imports` incluye `"apps.services.xml_ingest.tasks"` (legacy)

**Cambios necesarios:** ✅ SÍ

### 2. config/settings.py

**Estado actual:**
- ✅ `CELERY_TASK_DEFAULT_QUEUE = 'default'` está configurado
- ✅ `CELERY_TASK_ROUTES` existe con rutas para otras tareas
- ❌ `CELERY_IMPORTS` incluye `"apps.services.xml_ingest.tasks"` (legacy)
- ❌ `CELERY_TASK_ROUTES` NO incluye ruta para `document_ingest_task`
- ✅ `CELERY_TASK_ALWAYS_EAGER` NO está en settings (correcto - se configura solo en tests)

**Cambios necesarios:** ✅ SÍ

### 3. Tests y CI

**Estado actual:**
- ✅ `CELERY_TASK_ALWAYS_EAGER` está configurado en fixtures de tests (`tests/public/impuestos/conftest.py`, `tests/public/tenants/conftest.py`)
- ✅ Se usa `override_settings` para tests individuales cuando es necesario
- ✅ No requiere cambios en settings.py para tests

**Cambios necesarios:** ❌ NO

---

## 📋 DIFFS NECESARIOS

### Diff 1: config/celery.py

```diff
--- a/config/celery.py
+++ b/config/celery.py
@@ -27,13 +27,13 @@ app.config_from_object('django.conf:settings', namespace='CELERY')
 # 1) Descubre tasks en apps instaladas
 app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
 
 # 2) Descubre tasks en paquetes de "services" que NO son Django apps
 #    (services no siempre están en INSTALLED_APPS)
-app.autodiscover_tasks(packages=["apps.services.xml_ingest"])
+app.autodiscover_tasks(packages=["apps.services.document_ingest"])
 
 # 3) Refuerzo: añade import explícito (evita "unregistered task" en ciertos arranques)
 try:
-    __import__("apps.services.xml_ingest.tasks")
+    __import__("apps.services.document_ingest.tasks")
 except Exception:
     # No hacer fail del arranque si falta; el worker lo intentará más tarde.
     pass
 
 # ⚠️ IMPORT EXPLÍCITO: Módulos fuera de INSTALLED_APPS (apps/services)
 # Esto asegura que las tareas se registren aunque no estén en una app Django
 app.conf.imports = (
     "apps.services.maildigester.tasks",  # Tarea crítica de ingesta de correo
-    "apps.services.xml_ingest.tasks",  # Tarea de ingesta XML (tenant-aware)
+    "apps.services.document_ingest.tasks",  # Tarea de ingesta universal (tenant-aware)
 )
```

### Diff 2: config/settings.py

```diff
--- a/config/settings.py
+++ b/config/settings.py
@@ -801,7 +801,7 @@ CELERY_IMPORTS = (
     "apps.public.tenants.tasks",  # Tarea crítica de onboarding
     "apps.services.maildigester.tasks",  # Tarea de ingesta de facturas desde correo
-    "apps.services.xml_ingest.tasks",  # Tarea de ingesta XML (tenant-aware)
+    "apps.services.document_ingest.tasks",  # Tarea de ingesta universal (tenant-aware)
 )
 
 # ⚠️ CONFIGURACIÓN CRÍTICA: Colas Prioritarias
@@ -811,11 +811,14 @@ CELERY_TASK_DEFAULT_QUEUE = 'default'
 # Rutas explícitas de tareas a colas
 # IMPORTANTE: El orden importa. Las tareas críticas van a high_priority
 CELERY_TASK_ROUTES = {
     # Tarea crítica de onboarding: cola de alta prioridad
     'apps.public.tenants.tasks.onboard_tenant_task': {'queue': 'high_priority'},
     
     # Ingesta de facturas desde correo: cola de alta prioridad (crítica)
     'apps.services.maildigester.tasks.fetch_and_process_billing_mail': {'queue': 'high_priority'},
     'apps.services.maildigester.tasks.fetch_and_process_billing_mail': {'queue': 'high_priority'},
+    
+    # Pipeline universal de documentos: cola de alta prioridad (crítica)
+    'apps.services.document_ingest.tasks.document_ingest_task': {'queue': 'high_priority'},
     
     # Otras tareas pueden ir a sus colas específicas
     # 'apps.public.impuestos.tasks.*': {'queue': 'default'},
```

---

## ✅ VALIDACIÓN POST-APLICACIÓN

### Verificar que la tarea está registrada:

```bash
celery -A config inspect registered | grep document_ingest
```

**Resultado esperado:**
```
apps.services.document_ingest.tasks.document_ingest_task
```

### Verificar que la ruta está configurada:

```python
from django.conf import settings
print(settings.CELERY_TASK_ROUTES.get('apps.services.document_ingest.tasks.document_ingest_task'))
```

**Resultado esperado:**
```
{'queue': 'high_priority'}
```

### Verificar workers pueden procesar la tarea:

```bash
# Worker para cola high_priority
celery -A config worker -Q high_priority -n worker_high@%h

# En otro terminal, verificar que la tarea está disponible
celery -A config inspect active
```

---

## 📝 NOTAS

1. **Cola high_priority:** La tarea `document_ingest_task` se enruta a `high_priority` porque:
   - Es crítica para el negocio (ingesta de documentos)
   - Requiere procesamiento rápido
   - Debe tener prioridad sobre tareas generales

2. **Compatibilidad con infra existente:** 
   - Las colas `high_priority` y `default` ya existen en la infraestructura
   - No se requieren cambios en docker-compose o configuración de workers
   - Los workers existentes pueden procesar la nueva tarea

3. **Tests:**
   - `CELERY_TASK_ALWAYS_EAGER` está configurado en fixtures de tests
   - No requiere cambios en `settings.py` para tests
   - Los tests existentes seguirán funcionando

4. **Modo eager en dev/CI:**
   - **Dev:** Workers reales (no eager) - permite debugging de tareas asíncronas
   - **CI/Tests:** Eager mode via fixtures - ejecución síncrona para tests deterministas
   - **Prod:** Workers reales - procesamiento asíncrono con colas

---

## 🎯 RESUMEN

**Cambios necesarios:** ✅ SÍ (2 archivos)

1. ✅ `config/celery.py` - Actualizar autodiscover e imports
2. ✅ `config/settings.py` - Actualizar CELERY_IMPORTS y agregar ruta en CELERY_TASK_ROUTES

**Validaciones:**
- ✅ `app = Celery('config')` correcto
- ✅ `autodiscover_tasks` apunta correctamente
- ✅ Colas existentes se mantienen
- ✅ Tests usan eager mode via fixtures (correcto)
- ✅ Workers reales en dev/prod (correcto)

**Estado:** ✅ **VALIDADO CON CAMBIOS NECESARIOS**

---

**Última actualización:** 2026-02-10  
**Próxima acción:** Aplicar diffs 1 y 2
