# PLAN DE MIGRACIÓN — Universal Ingest + Celery

**Fecha:** 2026-02-10  
**Estado:** 📋 Plan de Migración Técnico  
**Objetivo:** Reemplazar `xml_ingest`/`xml_parser` por `document_ingest`/`document_parser` con Celery

---

## 🎯 Objetivo

Migrar completamente el sistema de ingesta XML legacy (`xml_ingest`/`xml_parser`) al pipeline universal (`document_ingest`/`document_parser`) con soporte asíncrono mediante Celery, manteniendo la regla de **"no crear archivos nuevos"** salvo que sea imprescindible.

---

## 📋 1. MAPA DE REEMPLAZO (Antes → Después)

### 1.1 Imports Directos

| Antes (Legacy) | Después (Universal) | Archivo Afectado |
|----------------|---------------------|------------------|
| `from apps.services.xml_ingest.normalizers import norm_nit` | `from apps.services.document_parser.normalizers import normalize_nit` | `facturas/services.py:102` |
| `from apps.services.xml_ingest.service import ingest_ubl_sync` | `from apps.services.document_ingest.ingest_service import ingest_document` | `facturas/services.py:471,807` |
| `from apps.services.xml_ingest.service import ingest_ubl_async` | `from apps.services.document_ingest.tasks import document_ingest_task` | `facturas/services.py:465,650` |
| `from apps.services.xml_ingest.service import task_status` | `from apps.services.document_ingest.tasks import get_task_status` | `facturas/api/viewsets.py:673` |
| `from apps.services.xml_parser import xpath, text, parse_xml_bytes` | `from apps.services.document_parser.xml_parser.helpers import xpath, text, parse_xml_bytes` | `facturas/ubl_parser.py:23` |
| `from apps.services.xml_parser.xml_service import procesar_factura_xml` | `from apps.services.document_ingest.ingest_service import ingest_document` | `maildigester/mail_service.py:14` |

### 1.2 Llamadas Síncronas

| Antes (Legacy) | Después (Universal) | Contexto |
|----------------|---------------------|----------|
| `ingest_ubl_sync(xml_bytes)` | `ingest_document(content=xml_bytes, preview=False)` | `facturas/services.py:472` |
| `ingest_ubl_sync(xml_bytes)` (preview) | `ingest_document(content=xml_bytes, preview=True)` | `facturas/services.py:808` |
| `enriched_payload, status_code = ingest_ubl_sync(...)` | `result, status_code = ingest_document(...)` | Flujo síncrono |

**Nota:** El formato de retorno cambia:
- **Antes:** `(enriched_payload, 200)` donde `enriched_payload = {"dto": {...}, "anexos": {...}, "meta": {...}}`
- **Después:** `(result, 200)` donde `result = {"persisted": bool, "dto": {...}, "id": int, "numero": str, ...}`

### 1.3 Llamadas Asíncronas

| Antes (Legacy) | Después (Universal) | Contexto |
|----------------|---------------------|----------|
| `ingest_ubl_async(xml_bytes, schema_name)` | `document_ingest_task.delay(schema_name=schema_name, file_b64=base64.b64encode(xml_bytes).decode("utf-8"), filename="document.xml")` | `facturas/services.py:469,651` |
| Retorna: `{"task_id": str, "status": "PENDING"}` | Retorna: `{"task_id": str, "status": "PENDING"}` | Mismo formato |

**Nota:** La tarea `document_ingest_task` debe aceptar los mismos parámetros que `xml_ingest_task` para mantener compatibilidad.

### 1.4 Endpoints DRF

| Antes (Legacy) | Después (Universal) | Estado |
|----------------|---------------------|--------|
| `POST /api/v1/facturas/upload-ubl/` | `POST /api/v1/core/documentos/upload/` | ✅ Ya implementado |
| `POST /api/v1/facturas/importar-ubl/` | `POST /api/v1/core/documentos/upload/` | ✅ Ya implementado |
| `GET /api/v1/facturas/task-status/{task_id}/` | `GET /api/v1/core/documentos/task-status/{task_id}/` | ⚠️ Crear si no existe |

### 1.5 Tasks Celery

| Antes (Legacy) | Después (Universal) | Acción |
|----------------|---------------------|--------|
| `apps.services.xml_ingest.tasks.xml_ingest_task` | `apps.services.document_ingest.tasks.document_ingest_task` | **MOVER/RENOMBRAR** `tasks.py` |
| Nombre canónico: `"apps.services.xml_ingest.tasks.xml_ingest_task"` | Nombre canónico: `"apps.services.document_ingest.tasks.document_ingest_task"` | Actualizar registro |

### 1.6 Tests

| Antes (Legacy) | Después (Universal) | Acción |
|----------------|---------------------|--------|
| `from apps.services.xml_ingest import ingest_ubl_sync` | `from apps.services.document_ingest.ingest_service import ingest_document` | Actualizar imports |
| `from apps.services.xml_parser import parse_xml_bytes` | `from apps.services.document_parser.xml_parser.helpers import parse_xml_bytes` | Actualizar imports |
| `reverse("factura-upload-ubl")` | `reverse("documentos-upload")` | Actualizar URLs |

### 1.7 JavaScript/UI

| Antes (Legacy) | Después (Universal) | Estado |
|----------------|---------------------|--------|
| `"/api/v1/facturas/upload-ubl/"` | `"/api/v1/core/documentos/upload/"` | ✅ Ya migrado |
| `API_UPLOAD = "/api/v1/facturas/upload-ubl/"` | `API_UPLOAD = "/api/v1/core/documentos/upload/"` | ✅ Ya migrado |

---

## 📋 2. COLAS Y RUTAS CELERY

### 2.1 Colas Necesarias

```python
# config/settings.py
CELERY_TASK_ROUTES = {
    # Pipeline universal de documentos (alta prioridad)
    "apps.services.document_ingest.tasks.document_ingest_task": {
        "queue": "high_priority",
        "routing_key": "document.ingest",
    },
    # Tareas de ingesta de correo (media prioridad)
    "apps.services.maildigester.tasks.*": {
        "queue": "default",
        "routing_key": "mail.ingest",
    },
    # Tareas generales (baja prioridad)
    "apps.*": {
        "queue": "default",
    },
}
```

### 2.2 Configuración de Colas

```python
# config/settings.py
CELERY_TASK_QUEUES = {
    "high_priority": {
        "exchange": "default",
        "exchange_type": "direct",
        "routing_key": "high_priority",
    },
    "default": {
        "exchange": "default",
        "exchange_type": "direct",
        "routing_key": "default",
    },
}

CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_DEFAULT_EXCHANGE = "default"
CELERY_TASK_DEFAULT_EXCHANGE_TYPE = "direct"
CELERY_TASK_DEFAULT_ROUTING_KEY = "default"
```

### 2.3 Workers Recomendados

- **Worker 1:** `celery -A config worker -Q high_priority -n worker_high@%h` (documentos críticos)
- **Worker 2:** `celery -A config worker -Q default -n worker_default@%h` (tareas generales)
- **Worker 3:** `celery -A config worker -Q high_priority,default -n worker_mixed@%h` (fallback)

### 2.4 Rutas por Tipo de Documento (Opcional)

Si se requiere priorización por tipo de documento:

```python
CELERY_TASK_ROUTES = {
    # Facturas/Notas Crédito (alta prioridad)
    "apps.services.document_ingest.tasks.document_ingest_task": {
        "queue": "high_priority",
        "routing_key": "document.ingest.invoice",
    },
    # Gastos/Inventario (media prioridad)
    "apps.services.document_ingest.tasks.document_ingest_task": {
        "queue": "default",
        "routing_key": "document.ingest.gasto",
    },
}
```

**Nota:** Esta priorización requiere pasar `document_type` como parámetro a la tarea y usar routing dinámico.

---

## 📋 3. REGLAS DE "NO CREAR ARCHIVOS"

### 3.1 Regla General

**NO crear archivos nuevos** salvo que sea imprescindible para la funcionalidad.

### 3.2 Casos Imprescindibles

#### ✅ IMPRESCINDIBLE: Mover/Renombrar `tasks.py`

**Razón:** `apps/services/document_ingest/tasks.py` NO existe, y es necesario para soporte asíncrono.

**Acción:**
1. **MOVER** `apps/services/xml_ingest/tasks.py` → `apps/services/document_ingest/tasks.py`
2. **RENOMBRAR** función `xml_ingest_task` → `document_ingest_task`
3. **ACTUALIZAR** imports internos:
   - `from apps.services.xml_parser import ...` → `from apps.services.document_parser.xml_parser.helpers import ...`
   - `from apps.tenant.facturas.ubl_parser import ...` → Usar `ingest_document` del pipeline universal
4. **ACTUALIZAR** nombre canónico: `"apps.services.document_ingest.tasks.document_ingest_task"`

**Código resultante (esquema):**
```python
# apps/services/document_ingest/tasks.py (MOVIDO desde xml_ingest/tasks.py)
from celery import shared_task
import base64
import logging
from typing import Dict, Any
from django_tenants.utils import schema_context
from apps.services.document_ingest.ingest_service import ingest_document

log_task = logging.getLogger("apps.services.document_ingest")

@shared_task(name="apps.services.document_ingest.tasks.document_ingest_task")
def document_ingest_task(schema_name: str, file_b64: str, filename: str = None) -> Dict[str, Any]:
    """Tarea tenant-aware para procesamiento asíncrono de documentos."""
    with schema_context(schema_name):
        file_bytes = base64.b64decode(file_b64.encode("utf-8"))
        result, status_code = ingest_document(
            content=file_bytes,
            filename=filename,
            preview=False,
            async_mode=False
        )
        return result
```

#### ✅ IMPRESCINDIBLE: Crear `get_task_status` si no existe

**Razón:** Endpoint `/task-status/` requiere función para consultar estado de tareas.

**Acción:**
- Si `task_status` existe en `xml_ingest/service.py`, **MOVER** a `document_ingest/tasks.py` o `document_ingest/ingest_service.py`
- Si no existe, **CREAR** función mínima que use `AsyncResult` de Celery

#### ❌ NO IMPRESCINDIBLE: Crear helpers en `document_parser/xml_parser/helpers.py`

**Razón:** Pueden reusarse helpers de `xml_parser/core.py` durante transición.

**Acción:** Mantener imports de `xml_parser/core` durante transición, migrar después.

#### ❌ NO IMPRESCINDIBLE: Crear endpoint nuevo `/task-status/`

**Razón:** Puede reusarse endpoint existente en `facturas/api/viewsets.py` durante transición.

**Acción:** Mantener endpoint legacy, actualizar internamente para usar nueva tarea.

### 3.3 Condiciones para Crear Archivo Nuevo

Un archivo nuevo **SOLO** se crea si:
1. ✅ Es imprescindible para funcionalidad crítica (ej: `tasks.py` para Celery)
2. ✅ No existe equivalente en el código base
3. ✅ No puede obtenerse moviendo/renombrando archivo existente
4. ✅ Está documentado en este plan con justificación

---

## 📋 4. ORDEN DE EJECUCIÓN

### FASE 1: Preparación (Sin cambios de código)

1. ✅ Verificar que `apps/services/document_ingest/tasks.py` NO existe
2. ✅ Documentar dependencias actuales de `xml_ingest`/`xml_parser`
3. ✅ Validar que pipeline universal funciona en modo síncrono
4. ✅ Configurar colas Celery en `config/settings.py` (sin activar aún)

**Criterios de validación:**
- [ ] Pipeline universal procesa XMLs correctamente
- [ ] Tests síncronos del pipeline universal pasan
- [ ] Colas Celery configuradas pero no en uso

---

### FASE 2: Migración de Tasks Celery (MOVER/RENOMBRAR)

1. **MOVER** `apps/services/xml_ingest/tasks.py` → `apps/services/document_ingest/tasks.py`
2. **ACTUALIZAR** función `xml_ingest_task` → `document_ingest_task`
3. **ACTUALIZAR** imports en `tasks.py`:
   - Reemplazar `from apps.services.xml_parser import ...` por helpers de `document_parser`
   - Reemplazar `from apps.tenant.facturas.ubl_parser import ...` por `ingest_document`
4. **ACTUALIZAR** `config/celery.py`:
   - Cambiar `app.autodiscover_tasks(packages=["apps.services.xml_ingest"])` → `["apps.services.document_ingest"]`
   - Cambiar `__import__("apps.services.xml_ingest.tasks")` → `__import__("apps.services.document_ingest.tasks")`
   - Cambiar `app.conf.imports` para incluir `"apps.services.document_ingest.tasks"`
5. **ACTUALIZAR** `config/settings.py`:
   - Cambiar `CELERY_IMPORTS` de `xml_ingest.tasks` → `document_ingest.tasks`
   - Agregar rutas de colas según sección 2.1
6. **CREAR** función `get_task_status` en `document_ingest/tasks.py` (mover desde `xml_ingest/service.py` si existe)

**Criterios de validación:**
- [ ] Tarea `document_ingest_task` está registrada en Celery
- [ ] Workers pueden descubrir la tarea
- [ ] Tarea procesa documentos correctamente en modo asíncrono
- [ ] `get_task_status` retorna estado correcto

**Rollback:** Revertir movimiento de `tasks.py` y actualizar `celery.py`/`settings.py`

---

### FASE 3: Migración de Llamadas Asíncronas

1. **ACTUALIZAR** `facturas/services.py`:
   - Línea 465: Reemplazar `ingest_ubl_async` por `document_ingest_task.delay(...)`
   - Línea 650: Reemplazar `ingest_ubl_async` por `document_ingest_task.delay(...)`
   - Adaptar formato de parámetros (schema_name, file_b64, filename)
2. **ACTUALIZAR** `facturas/api/viewsets.py`:
   - Línea 673: Reemplazar `task_status` por `get_task_status` de `document_ingest/tasks.py`
3. **VALIDAR** que formato de retorno es compatible:
   - `{"task_id": str, "status": "PENDING"}` debe mantenerse

**Criterios de validación:**
- [ ] Llamadas asíncronas usan nueva tarea
- [ ] Endpoint de estado de tareas funciona
- [ ] Tests de flujo asíncrono pasan
- [ ] No hay regresiones en funcionalidad

**Rollback:** Revertir cambios en `facturas/services.py` y `viewsets.py`

---

### FASE 4: Migración de Llamadas Síncronas

1. **ACTUALIZAR** `facturas/services.py`:
   - Línea 471: Reemplazar `ingest_ubl_sync` por `ingest_document` (fallback legacy)
   - Línea 807: Reemplazar `ingest_ubl_sync` (preview) por `ingest_document(preview=True)`
   - Adaptar manejo de formato de retorno (enriched_payload → result)
2. **ACTUALIZAR** `facturas/services.py`:
   - Línea 102: Reemplazar `norm_nit` por `normalize_nit` de `document_parser`
3. **ELIMINAR** bloques de fallback legacy:
   - Remover `if not use_universal:` en `importar_documento`
   - Remover `else: # Pipeline legacy` en `importar_ubl_async`

**Criterios de validación:**
- [ ] No hay imports de `xml_ingest` en `facturas/services.py`
- [ ] Llamadas síncronas usan pipeline universal
- [ ] Tests síncronos pasan
- [ ] Preview mode funciona correctamente

**Rollback:** Revertir cambios y reactivar fallback legacy

---

### FASE 5: Migración de Dependencias Cruzadas

1. **ACTUALIZAR** `facturas/ubl_parser.py`:
   - Línea 23: Reemplazar imports de `xml_parser` por helpers de `document_parser`
2. **ACTUALIZAR** `maildigester/mail_service.py`:
   - Línea 14: Reemplazar `procesar_factura_xml` por `ingest_document`
3. **ACTUALIZAR** `document_parser/xml_parser/parser.py`:
   - Línea 14: Crear helpers equivalentes o mantener imports de `xml_parser` durante transición

**Criterios de validación:**
- [ ] No hay imports de `xml_parser` en código de producción (excepto durante transición)
- [ ] Maildigester procesa XMLs correctamente
- [ ] Tests de dependencias cruzadas pasan

**Rollback:** Revertir cambios en dependencias cruzadas

---

### FASE 6: Actualización de Tests

1. **ACTUALIZAR** imports en tests:
   - `test_xml_pipeline_canonical.py`
   - `test_nota_credito_pipeline.py`
   - `test_services_ingest_integration.py`
   - Otros tests que usen `xml_ingest`/`xml_parser`
2. **ACTUALIZAR** URLs en tests:
   - `reverse("factura-upload-ubl")` → `reverse("documentos-upload")`
3. **VALIDAR** que tests pasan con pipeline universal

**Criterios de validación:**
- [ ] Todos los tests pasan
- [ ] No hay tests que fallen por imports legacy
- [ ] Cobertura de tests se mantiene

**Rollback:** Revertir cambios en tests

---

### FASE 7: Limpieza y Validación Final

1. **VERIFICAR** que no hay referencias a `xml_ingest`/`xml_parser`:
   ```bash
   grep -r "xml_ingest\|xml_parser" apps/ config/ tasks/ --exclude-dir=__pycache__
   ```
2. **ACTUALIZAR** documentación:
   - Marcar módulos legacy como deprecados
   - Actualizar guías de desarrollo
3. **VALIDAR** flujo completo:
   - Síncrono: `ingest_document` funciona
   - Asíncrono: `document_ingest_task` funciona
   - Estado: `get_task_status` funciona
   - Endpoints: `/upload/` funciona

**Criterios de validación:**
- [ ] Cero referencias a `xml_ingest`/`xml_parser` en código de producción
- [ ] Documentación actualizada
- [ ] Flujo completo validado
- [ ] Listo para deprecar módulos legacy

---

## 📊 Resumen de Archivos a Modificar

### Archivos a MOVER/RENOMBRAR
- ✅ `apps/services/xml_ingest/tasks.py` → `apps/services/document_ingest/tasks.py`

### Archivos a ACTUALIZAR
- `apps/tenant/facturas/services.py` (líneas 102, 465, 471, 650, 807)
- `apps/tenant/facturas/api/viewsets.py` (línea 673)
- `apps/tenant/facturas/ubl_parser.py` (línea 23)
- `apps/services/maildigester/mail_service.py` (línea 14)
- `apps/services/document_parser/xml_parser/parser.py` (línea 14)
- `config/celery.py` (líneas 29, 33, 42)
- `config/settings.py` (líneas 804, 951-957, 1022-1023)
- Tests: `test_xml_pipeline_canonical.py`, `test_nota_credito_pipeline.py`, etc.

### Archivos a CREAR (Solo si imprescindible)
- ❌ Ninguno (se mueve/renombra `tasks.py` existente)

---

## ✅ Checklist de Validación

### FASE 2: Tasks Celery
- [ ] `document_ingest_task` está registrada en Celery
- [ ] Workers pueden descubrir la tarea
- [ ] Tarea procesa documentos correctamente
- [ ] `get_task_status` funciona

### FASE 3: Llamadas Asíncronas
- [ ] Llamadas asíncronas usan nueva tarea
- [ ] Endpoint de estado funciona
- [ ] Tests asíncronos pasan

### FASE 4: Llamadas Síncronas
- [ ] No hay imports de `xml_ingest` en `facturas/services.py`
- [ ] Llamadas síncronas usan pipeline universal
- [ ] Preview mode funciona

### FASE 5: Dependencias Cruzadas
- [ ] Maildigester funciona
- [ ] `ubl_parser` funciona
- [ ] Tests pasan

### FASE 6: Tests
- [ ] Todos los tests pasan
- [ ] Cobertura se mantiene

### FASE 7: Limpieza
- [ ] Cero referencias a `xml_ingest`/`xml_parser`
- [ ] Documentación actualizada
- [ ] Flujo completo validado

---

## 🚨 Estrategia de Rollback

### Por Fase

**FASE 2:** Revertir movimiento de `tasks.py` y actualizar `celery.py`/`settings.py`
**FASE 3:** Revertir cambios en `facturas/services.py` y `viewsets.py`
**FASE 4:** Revertir cambios y reactivar fallback legacy
**FASE 5:** Revertir cambios en dependencias cruzadas
**FASE 6:** Revertir cambios en tests
**FASE 7:** No requiere rollback (solo validación)

---

## 📝 Notas Técnicas

### Compatibilidad de Formato

**Formato Legacy (xml_ingest):**
```python
{
    "dto": {...},
    "anexos": {
        "ubl_xml": "...",
        "application_response_xml": "...",
    },
    "meta": {"container": "AttachedDocument"},
}
```

**Formato Universal (document_ingest):**
```python
{
    "persisted": bool,
    "dto": {...},
    "id": int,
    "numero": str,
    "sha256": str,
    "metadata": {...},
}
```

**Adaptación necesaria:** La función `materializar_factura_desde_result` en `facturas/services.py` debe adaptarse al nuevo formato.

### Nombre Canónico de Tarea

**Legacy:**
```python
@shared_task(name="apps.services.xml_ingest.tasks.xml_ingest_task")
```

**Universal:**
```python
@shared_task(name="apps.services.document_ingest.tasks.document_ingest_task")
```

**Importante:** El nombre canónico debe ser único y no cambiar durante la migración para evitar tareas huérfanas.

---

**Última actualización:** 2026-02-10  
**Próxima acción:** Ejecutar FASE 1 (Preparación)
