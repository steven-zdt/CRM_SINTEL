# LIMPIEZA EJECUTADA — Verificación de Referencias Legacy

**Fecha:** 2026-02-10  
**Estado:** ⚠️ **NO EJECUTADA** — Referencias Activas Detectadas

---

## 🔍 VERIFICACIÓN DE REFERENCIAS

### Resultado: ❌ **NO SE PUEDE PROCEDER CON LIMPIEZA**

Se detectaron **múltiples referencias activas** a `xml_ingest` y `xml_parser` en el código base. Los módulos legacy **NO pueden ser eliminados** hasta que se hayan aplicado los diffs de migración del paso 3.

---

## 📊 REFERENCIAS DETECTADAS

### 1. Código de Producción (CRÍTICO)

#### `apps/tenant/facturas/services.py`
- **Línea 102:** `from apps.services.xml_ingest.normalizers import norm_nit`
- **Línea 465:** `from apps.services.xml_ingest.service import ingest_ubl_async`
- **Línea 471:** `from apps.services.xml_ingest.service import ingest_ubl_sync`
- **Línea 650:** `from apps.services.xml_ingest.service import ingest_ubl_async`
- **Línea 807:** `from apps.services.xml_ingest.service import ingest_ubl_sync`
- **Líneas 169, 326:** Comentarios que mencionan `xml_ingest/dto`

#### `apps/tenant/facturas/api/viewsets.py`
- **Línea 673:** `from apps.services.xml_ingest.service import task_status`
- **Líneas 100, 104, 115, 275, 283, 357, 382:** Referencias a endpoints `/upload-ubl/` y `/importar-ubl/` (comentarios y código)

#### `apps/tenant/facturas/ubl_parser.py`
- **Línea 23:** `from apps.services.xml_parser import xpath, text, parse_xml_bytes`
- **Líneas 5, 7, 74, 787:** Comentarios que mencionan `xml_parser`

#### `apps/services/maildigester/mail_service.py`
- **Línea 14:** `from apps.services.xml_parser.xml_service import procesar_factura_xml`
- **Línea 79:** Comentario que menciona `xml_parser`

#### `apps/services/document_parser/xml_parser/parser.py`
- **Línea 14:** `from apps.services.xml_parser.core import parse_xml_bytes, local_name, xpath, first, text, attr`

### 2. Módulos Legacy (Auto-referencias)

#### `apps/services/xml_ingest/`
- Múltiples archivos con imports internos de `xml_parser`
- `__init__.py` exporta funciones legacy
- `service.py`, `tasks.py`, `ingest_service.py` con lógica activa

#### `apps/services/xml_parser/`
- Múltiples archivos con imports internos de `xml_ingest`
- `ubl_invoice.py`, `ubl_credit_note.py` con lógica activa

### 3. Tests (NO CRÍTICO, pero deben migrarse)

#### `apps/tenant/facturas/tests/`
- `test_xml_pipeline_canonical.py`: Imports de `xml_ingest` y `xml_parser`
- `test_nota_credito_pipeline.py`: Imports de `xml_ingest`
- `test_services_ingest_integration.py`: Comentarios sobre `xml_ingest`
- `test_api_upload_ubl_contract.py`: Referencias a `upload-ubl`
- `test_upload_async_flow.py`: Referencias a `upload-ubl`
- `test_import_ubl_heavy_payload.py`: Referencias a `upload-ubl`
- `test_naturaleza_import_ubl.py`: Referencias a `upload-ubl`

#### `apps/services/xml_ingest/tests/`
- Múltiples archivos de test del módulo legacy

#### `apps/services/xml_parser/tests/`
- Múltiples archivos de test del módulo legacy

### 4. Configuración (CRÍTICO)

#### `config/celery.py`
- **Línea 29:** `app.autodiscover_tasks(packages=["apps.services.xml_ingest"])`
- **Línea 33:** `__import__("apps.services.xml_ingest.tasks")`
- **Línea 42:** `"apps.services.xml_ingest.tasks"` en `app.conf.imports`

#### `config/settings.py`
- **Línea 804:** `"apps.services.xml_ingest.tasks"` en `CELERY_IMPORTS`
- **Línea 868:** Comentario sobre `FEATURE_XML_PIPELINE`
- **Líneas 951-957:** Logging config para `services.xml_ingest.task` y `services.xml_ingest.parse`
- **Líneas 1022-1023:** Logger principal `apps.services.xml_ingest`

### 5. Documentación (NO CRÍTICO)

- `documentacion/DIFFS_MIGRACION_UNIVERSAL.md`: Referencias en diffs
- `documentacion/PLAN_MIGRACION_UNIVERSAL_CELERY.md`: Referencias en plan
- `documentacion/PLAN_MIGRACION_XML_LEGACY.md`: Referencias en plan
- `documentacion/arquitectura_general.md`: Referencias en documentación
- `documentacion/FASE_0_VALIDACION_ARQUITECTURA.md`: Referencias en documentación
- `documentacion/FASE_1_SERVICIO_XML_INGEST.md`: Referencias en documentación

### 6. Scripts y Otros (NO CRÍTICO)

- `scripts/audit_xml_pipeline_duplication.py`: Referencias en script de auditoría

### 7. Templates/UI (NO CRÍTICO)

- `apps/tenant/core/templates/tenant/core/workspace.html`: ID de botón `btn-importar-ubl` (solo ID, no funcionalidad)
- `apps/tenant/landing/static/tenant/landing/workspace/facturas.js`: ID de botón `btn-importar-ubl` (solo ID, no funcionalidad)

---

## 📋 RESUMEN DE REFERENCIAS POR TIPO

| Tipo | Cantidad | Crítico | Acción Requerida |
|------|----------|---------|------------------|
| **Imports en código de producción** | 8 | ✅ SÍ | Aplicar diffs del paso 3 |
| **Referencias en tests** | ~15 | ⚠️ NO | Migrar tests después |
| **Configuración (celery/settings)** | 6 | ✅ SÍ | Aplicar diffs del paso 3 |
| **Auto-referencias en módulos legacy** | ~20 | ⚠️ NO | Se eliminan con módulos |
| **Documentación** | ~10 | ⚠️ NO | Actualizar después |
| **Templates/UI (solo IDs)** | 2 | ⚠️ NO | No afecta funcionalidad |
| **Scripts** | 1 | ⚠️ NO | Actualizar después |

---

## ⚠️ PREREQUISITOS PARA LIMPIEZA

### 1. Aplicar Diffs de Migración (PASO 3)

**Archivos que DEBEN ser actualizados antes de eliminar módulos:**

1. ✅ `apps/tenant/facturas/services.py` (5 imports)
2. ✅ `apps/tenant/facturas/api/viewsets.py` (1 import)
3. ✅ `apps/tenant/facturas/ubl_parser.py` (1 import)
4. ✅ `apps/services/maildigester/mail_service.py` (1 import)
5. ✅ `apps/services/document_parser/xml_parser/parser.py` (1 import)
6. ✅ `config/celery.py` (3 referencias)
7. ✅ `config/settings.py` (4 referencias)

### 2. Mover/Renombrar tasks.py

- ✅ Mover `apps/services/xml_ingest/tasks.py` → `apps/services/document_ingest/tasks.py`
- ✅ Actualizar contenido según diffs del paso 3

### 3. Validar Funcionalidad

- ✅ Pipeline universal funciona correctamente
- ✅ Tests pasan con pipeline universal
- ✅ Endpoints funcionan correctamente
- ✅ Tareas Celery se registran correctamente

---

## 🚫 ACCIONES NO EJECUTADAS

### Eliminación de Directorios

**NO se eliminaron los siguientes directorios porque hay referencias activas:**

- ❌ `apps/services/xml_ingest/` (NO eliminado)
- ❌ `apps/services/xml_parser/` (NO eliminado)

### Sanitización

**NO se ejecutó sanitización porque los módulos aún están en uso:**

- ❌ Actualización de `__all__`/imports en paquetes superiores
- ❌ Corrección de imports rotos
- ❌ Actualización de tests

---

## ✅ PRÓXIMOS PASOS

### Paso 1: Aplicar Diffs de Migración

Aplicar los diffs documentados en `documentacion/DIFFS_MIGRACION_UNIVERSAL.md`:

1. Aplicar diff 1: `apps/tenant/facturas/services.py`
2. Aplicar diff 2: `apps/tenant/facturas/api/viewsets.py`
3. **MOVER** `apps/services/xml_ingest/tasks.py` → `apps/services/document_ingest/tasks.py`
4. Aplicar diff 3: Actualizar contenido de `tasks.py` movido
5. Aplicar diff 5: `config/celery.py`
6. Aplicar diff 6: `config/settings.py`

### Paso 2: Validar Migración

1. Ejecutar tests: `pytest apps/tenant/facturas/tests/`
2. Verificar tarea Celery: `celery -A config inspect registered`
3. Probar endpoints: `POST /api/v1/core/documentos/upload/`
4. Verificar que no hay imports rotos: `python manage.py check`

### Paso 3: Re-ejecutar Verificación

Una vez aplicados los diffs, re-ejecutar la búsqueda:

```bash
grep -r "xml_ingest\|xml_parser" apps/ config/ --exclude-dir=__pycache__ --exclude="*.md"
```

**Resultado esperado:** Solo referencias en:
- Tests legacy (que se migrarán después)
- Documentación (que se actualizará después)
- Módulos legacy mismos (que se eliminarán)

### Paso 4: Ejecutar Limpieza

Una vez que la verificación muestre 0 referencias críticas:

1. Eliminar `apps/services/xml_ingest/`
2. Eliminar `apps/services/xml_parser/`
3. Sanitizar imports y referencias
4. Actualizar documentación

---

## 📝 NOTAS

1. **Endpoints legacy:** Los endpoints `/upload-ubl/` y `/importar-ubl/` pueden mantenerse como wrappers deprecados que internamente usan el pipeline universal. No es crítico eliminarlos inmediatamente.

2. **Tests legacy:** Los tests que usan `xml_ingest`/`xml_parser` pueden mantenerse durante la transición para validar compatibilidad. Se migrarán gradualmente.

3. **Documentación:** Las referencias en documentación no impiden la eliminación de módulos, pero deben actualizarse para evitar confusión.

4. **IDs de botones:** Los IDs `btn-importar-ubl` en templates/JS no afectan la funcionalidad. Son solo identificadores del DOM.

---

## 🎯 CONCLUSIÓN

**Estado actual:** ⚠️ **NO SE PUEDE PROCEDER CON LIMPIEZA**

**Razón:** Existen **8 imports críticos** en código de producción y **6 referencias críticas** en configuración que deben ser migradas primero.

**Acción requerida:** Aplicar los diffs de migración documentados en `documentacion/DIFFS_MIGRACION_UNIVERSAL.md` antes de proceder con la eliminación de módulos legacy.

**Archivos removidos:** 0  
**Archivos modificados:** 0  
**Referencias críticas pendientes:** 14

---

**Última actualización:** 2026-02-10  
**Próxima acción:** Aplicar diffs de migración del paso 3
