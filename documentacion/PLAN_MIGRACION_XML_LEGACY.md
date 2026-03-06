# Plan de Migración: xml_ingest / xml_parser → Pipeline Universal

**Fecha:** 2026-02-10  
**Estado:** 📋 Plan de Migración  
**Basado en:** Auditoría Legado (xml_ingest / xml_parser)

## 🎯 Objetivo

Migrar todas las dependencias de `apps/services/xml_ingest` y `apps/services/xml_parser` al pipeline universal (`apps/services/document_parser` + `apps/services/document_ingest`), manteniendo compatibilidad retroactiva durante la transición.

## 📊 Resumen Ejecutivo

### Dependencias Identificadas

- **Código de Producción:** 6 imports condicionales (fallback legacy)
- **Endpoints DRF:** 2 endpoints activos (`/upload-ubl/`, `/importar-ubl/`)
- **Tareas Celery:** 1 tarea registrada (`xml_ingest_task`)
- **Tests:** ~10 archivos de test
- **Dependencias Cruzadas:** `document_parser/xml_parser` y `maildigester`
- **Lógica Especializada:** ~15 archivos con lógica AttachedDocument/ApplicationResponse

### Estrategia General

1. **Fase 1:** Migrar dependencias directas de bajo riesgo (facturas/services.py)
2. **Fase 2:** Migrar endpoints DRF con deprecación gradual
3. **Fase 3:** Migrar tareas Celery y configuración
4. **Fase 4:** Migrar dependencias cruzadas (maildigester, document_parser)
5. **Fase 5:** Migrar lógica especializada (AttachedDocument/ApplicationResponse)
6. **Fase 6:** Deprecar y eliminar módulos legacy

---

## 📋 FASE 1: Migración de Dependencias Directas (BAJO RIESGO)

### 1.1 Migrar `facturas/services.py`

**Objetivo:** Eliminar imports condicionales de `xml_ingest` y usar exclusivamente el pipeline universal.

**Archivos afectados:**
- `apps/tenant/facturas/services.py` (líneas 102, 465, 471, 650, 807)

**Pasos:**

1. **Eliminar import de normalizers (línea 102):**
   ```python
   # ANTES:
   from apps.services.xml_ingest.normalizers import norm_nit
   
   # DESPUÉS:
   from apps.services.document_parser.normalizers import normalize_nit
   # O usar directamente desde el DTO normalizado
   ```

2. **Eliminar fallback legacy en `importar_documento` (líneas 465, 471):**
   - Remover el bloque `if not use_universal:`
   - Asegurar que `FEATURE_DOCUMENT_PIPELINE=True` por defecto
   - Eliminar imports condicionales de `ingest_ubl_async` y `ingest_ubl_sync`

3. **Eliminar fallback legacy en `importar_ubl_async` (línea 650):**
   - Remover el bloque `else: # Pipeline legacy`
   - Usar exclusivamente el pipeline universal

4. **Eliminar fallback legacy en `importar_factura_desde_ubl` (línea 807):**
   - Remover el bloque de preview que usa `ingest_ubl_sync`
   - Usar `ingest_document` con `preview=True`

**Criterios de validación:**
- ✅ Todos los tests de `facturas/tests/` pasan
- ✅ No hay imports de `xml_ingest` en `facturas/services.py`
- ✅ Feature flag `FEATURE_DOCUMENT_PIPELINE` puede ser `True` sin fallback

**Riesgo:** 🟢 BAJO (ya hay feature flags y fallback condicional)

---

### 1.2 Migrar `facturas/api/viewsets.py`

**Objetivo:** Eliminar dependencia de `task_status` y usar sistema de tareas del pipeline universal.

**Archivos afectados:**
- `apps/tenant/facturas/api/viewsets.py` (línea 673)

**Pasos:**

1. **Reemplazar `task_status` (línea 673):**
   ```python
   # ANTES:
   from apps.services.xml_ingest.service import task_status
   payload, code = task_status(task_id, request=request)
   
   # DESPUÉS:
   # Si el pipeline universal tiene sistema de tareas:
   from apps.services.document_ingest.tasks import get_task_status
   payload, code = get_task_status(task_id, request=request)
   # O implementar endpoint de estado de tareas en el pipeline universal
   ```

2. **Crear endpoint de estado de tareas en pipeline universal (si no existe):**
   - Agregar `get_task_status` en `apps/services/document_ingest/tasks.py`
   - O usar sistema de tareas de Celery directamente

**Criterios de validación:**
- ✅ Endpoint `/api/v1/facturas/task-status/{task_id}/` funciona
- ✅ Retorna formato compatible con el anterior
- ✅ No hay imports de `xml_ingest` en `viewsets.py`

**Riesgo:** 🟡 MEDIO (requiere implementar sistema de tareas en pipeline universal)

---

## 📋 FASE 2: Migración de Endpoints DRF (MEDIO RIESGO)

### 2.1 Deprecar `/upload-ubl/` y `/importar-ubl/`

**Objetivo:** Marcar endpoints como deprecados y redirigir a `/api/v1/core/documentos/upload/`.

**Archivos afectados:**
- `apps/tenant/facturas/api/viewsets.py` (líneas 357, 382)

**Pasos:**

1. **Agregar headers de deprecación:**
   ```python
   @action(detail=False, methods=["post"], url_path="upload-ubl", parser_classes=[MultiPartParser, FormParser])
   def upload_ubl(self, request: Request) -> Response:
       """
       ⚠️ DEPRECATED: Este endpoint está deprecado.
       Use POST /api/v1/core/documentos/upload/ en su lugar.
       Este endpoint será removido en v2.40.
       """
       response = Response(...)
       response['Deprecation'] = 'true'
       response['Link'] = '</api/v1/core/documentos/upload/>; rel="successor-version"'
       response['Sunset'] = 'Mon, 01 Jan 2027 00:00:00 GMT'  # 1 año desde ahora
       return response
   ```

2. **Redirigir internamente a pipeline universal:**
   - Mantener lógica actual que ya usa `importar_documento`
   - Agregar log de advertencia cuando se use endpoint deprecado

3. **Actualizar documentación OpenAPI/Swagger:**
   - Marcar endpoints como `deprecated: true`
   - Agregar nota sobre endpoint de reemplazo

**Criterios de validación:**
- ✅ Endpoints legacy retornan headers de deprecación
- ✅ Endpoints legacy redirigen internamente a pipeline universal
- ✅ Logs de advertencia se generan cuando se usan endpoints deprecados
- ✅ Documentación OpenAPI actualizada

**Riesgo:** 🟢 BAJO (endpoints ya usan pipeline universal internamente)

**Timeline:** 2-3 semanas (incluye período de aviso a usuarios)

---

## 📋 FASE 3: Migración de Tareas Celery (MEDIO RIESGO)

### 3.1 Migrar `xml_ingest_task` a pipeline universal

**Objetivo:** Reemplazar tarea Celery legacy por tarea del pipeline universal.

**Archivos afectados:**
- `apps/services/xml_ingest/tasks.py`
- `config/celery.py` (líneas 29, 33, 42)
- `config/settings.py` (líneas 804, 951-957, 1022-1023)

**Pasos:**

1. **Crear tarea equivalente en pipeline universal:**
   ```python
   # apps/services/document_ingest/tasks.py
   @shared_task(name="apps.services.document_ingest.tasks.document_ingest_task")
   def document_ingest_task(schema_name: str, file_b64: str, filename: str = None) -> Dict[str, Any]:
       """Tarea Celery para procesamiento asíncrono de documentos."""
       from django_tenants.utils import schema_context
       from apps.services.document_ingest.ingest_service import ingest_document
       import base64
       
       with schema_context(schema_name):
           file_bytes = base64.b64decode(file_b64)
           result, status_code = ingest_document(
               content=file_bytes,
               filename=filename,
               preview=False,
               async_mode=False
           )
           return result
   ```

2. **Actualizar configuración de Celery:**
   ```python
   # config/celery.py
   # Reemplazar:
   app.autodiscover_tasks(packages=["apps.services.xml_ingest"])
   # Por:
   app.autodiscover_tasks(packages=["apps.services.document_ingest"])
   
   # Reemplazar en app.conf.imports:
   "apps.services.document_ingest.tasks",  # Tarea de ingesta universal
   ```

3. **Actualizar configuración de logging:**
   ```python
   # config/settings.py
   # Reemplazar loggers de xml_ingest por document_ingest
   "services.document_ingest.task": {
       "handlers": ["console", "file"],
       "level": "INFO",
   },
   "services.document_ingest.parse": {
       "handlers": ["console", "file"],
       "level": "DEBUG",
   },
   ```

4. **Mantener compatibilidad durante transición:**
   - Registrar ambas tareas durante período de migración
   - Redirigir llamadas a `xml_ingest_task` hacia `document_ingest_task`

**Criterios de validación:**
- ✅ Tarea `document_ingest_task` está registrada en Celery
- ✅ Workers pueden procesar tareas del pipeline universal
- ✅ Logs se generan correctamente
- ✅ No hay tareas huérfanas en cola

**Riesgo:** 🟡 MEDIO (requiere actualizar workers y configuración)

**Timeline:** 3-4 semanas (incluye actualización de workers en producción)

---

## 📋 FASE 4: Migración de Dependencias Cruzadas (ALTO RIESGO)

### 4.1 Migrar `document_parser/xml_parser/parser.py`

**Objetivo:** Eliminar dependencia de `xml_parser/core` y usar solo helpers de `document_parser`.

**Archivos afectados:**
- `apps/services/document_parser/xml_parser/parser.py` (línea 14)

**Pasos:**

1. **Crear helpers equivalentes en `document_parser`:**
   ```python
   # apps/services/document_parser/xml_parser/helpers.py
   from lxml import etree
   
   def parse_xml_bytes(xml_bytes: bytes) -> etree._Element:
       """Parsea bytes XML a Element."""
       # Implementación equivalente a xml_parser/core
       pass
   
   def local_name(element) -> str:
       """Obtiene el nombre local del elemento sin namespace."""
       # Implementación equivalente
       pass
   
   # ... otros helpers necesarios
   ```

2. **Actualizar imports en `document_parser/xml_parser/parser.py`:**
   ```python
   # ANTES:
   from apps.services.xml_parser.core import parse_xml_bytes, local_name, xpath, first, text, attr
   
   # DESPUÉS:
   from apps.services.document_parser.xml_parser.helpers import parse_xml_bytes, local_name, xpath, first, text, attr
   ```

3. **Migrar lógica de helpers:**
   - Copiar funciones necesarias de `xml_parser/core.py` a `document_parser/xml_parser/helpers.py`
   - Asegurar que la funcionalidad es equivalente

**Criterios de validación:**
- ✅ No hay imports de `xml_parser` en `document_parser`
- ✅ Todos los tests de `document_parser` pasan
- ✅ Funcionalidad equivalente a la anterior

**Riesgo:** 🟡 MEDIO (requiere refactorización de helpers)

---

### 4.2 Migrar `maildigester/mail_service.py`

**Objetivo:** Reemplazar `xml_parser/xml_service` por pipeline universal.

**Archivos afectados:**
- `apps/services/maildigester/mail_service.py` (línea 14)

**Pasos:**

1. **Reemplazar llamada a `procesar_factura_xml`:**
   ```python
   # ANTES:
   from apps.services.xml_parser.xml_service import procesar_factura_xml
   procesar_factura_xml(xml_content)
   
   # DESPUÉS:
   from apps.services.document_ingest.ingest_service import ingest_document
   result, status_code = ingest_document(
       content=xml_content.encode('utf-8'),
       filename="factura.xml",
       preview=False
   )
   ```

2. **Adaptar lógica de procesamiento:**
   - Adaptar manejo de resultados del pipeline universal
   - Mantener compatibilidad con flujo de maildigester

**Criterios de validación:**
- ✅ Maildigester puede procesar XMLs correctamente
- ✅ No hay imports de `xml_parser` en `maildigester`
- ✅ Tests de maildigester pasan

**Riesgo:** 🟡 MEDIO (requiere adaptar lógica de procesamiento)

---

### 4.3 Migrar `facturas/ubl_parser.py`

**Objetivo:** Eliminar dependencia de `xml_parser` y usar helpers de `document_parser`.

**Archivos afectados:**
- `apps/tenant/facturas/ubl_parser.py` (línea 23)

**Pasos:**

1. **Actualizar imports:**
   ```python
   # ANTES:
   from apps.services.xml_parser import xpath, text, parse_xml_bytes
   
   # DESPUÉS:
   from apps.services.document_parser.xml_parser.helpers import xpath, text, parse_xml_bytes
   ```

2. **Verificar compatibilidad:**
   - Asegurar que helpers de `document_parser` tienen misma API
   - Actualizar llamadas si es necesario

**Criterios de validación:**
- ✅ No hay imports de `xml_parser` en `ubl_parser.py`
- ✅ Funcionalidad de parsing UBL funciona correctamente
- ✅ Tests de `ubl_parser` pasan

**Riesgo:** 🟢 BAJO (solo cambio de imports si helpers son equivalentes)

---

## 📋 FASE 5: Migración de Lógica Especializada (ALTO RIESGO)

### 5.1 Migrar lógica de AttachedDocument/ApplicationResponse

**Objetivo:** Migrar toda la lógica de manejo de AttachedDocument y ApplicationResponse al pipeline universal.

**Archivos afectados:**
- `apps/services/xml_parser/core.py` (funciones de extracción)
- `apps/services/xml_ingest/service.py` (orquestación)
- `apps/services/xml_ingest/tasks.py` (tareas)
- `apps/services/maildigester/detectors.py` (detección)
- Múltiples archivos de parsers UBL

**Pasos:**

1. **Migrar funciones de extracción a `document_parser`:**
   ```python
   # apps/services/document_parser/xml_parser/attached_document.py
   def extract_embedded_invoice(root: etree._Element) -> etree._Element:
       """Extrae Invoice embebido desde AttachedDocument."""
       # Migrar lógica de xml_parser/core.py
       pass
   
   def extract_application_response(root: etree._Element) -> Optional[etree._Element]:
       """Extrae ApplicationResponse desde AttachedDocument."""
       # Migrar lógica de xml_parser/core.py
       pass
   ```

2. **Actualizar parser XML del pipeline universal:**
   - Integrar detección de AttachedDocument en `document_parser/xml_parser/parser.py`
   - Manejar extracción de documentos embebidos
   - Procesar ApplicationResponse si está presente

3. **Actualizar maildigester:**
   - Migrar `extract_xml_from_attacheddocument` a usar helpers de `document_parser`
   - Actualizar pipeline de maildigester para usar pipeline universal

4. **Validar casos de uso reales:**
   - Probar con XMLs reales que contengan AttachedDocument
   - Verificar que ApplicationResponse se procesa correctamente
   - Asegurar compatibilidad con casos de uso existentes

**Criterios de validación:**
- ✅ Pipeline universal puede procesar AttachedDocument
- ✅ ApplicationResponse se extrae y procesa correctamente
- ✅ Todos los tests de casos especiales pasan
- ✅ No hay regresiones en funcionalidad existente

**Riesgo:** 🔴 ALTO (lógica compleja, casos de uso críticos)

**Timeline:** 6-8 semanas (requiere testing exhaustivo)

---

## 📋 FASE 6: Deprecación y Eliminación (BAJO RIESGO)

### 6.1 Deprecar módulos legacy

**Objetivo:** Marcar módulos como deprecados y preparar para eliminación.

**Pasos:**

1. **Agregar warnings de deprecación:**
   ```python
   # apps/services/xml_ingest/__init__.py
   import warnings
   
   warnings.warn(
       "apps.services.xml_ingest está deprecado. "
       "Use apps.services.document_ingest en su lugar. "
       "Este módulo será removido en v2.40.",
       DeprecationWarning,
       stacklevel=2
   )
   ```

2. **Agregar comentarios de deprecación en código:**
   - Marcar todas las funciones públicas como deprecadas
   - Agregar notas sobre alternativas

3. **Actualizar documentación:**
   - Marcar módulos como deprecados en documentación
   - Proporcionar guías de migración

**Timeline:** 2 semanas

---

### 6.2 Eliminar módulos legacy

**Objetivo:** Remover completamente `xml_ingest` y `xml_parser` del código base.

**Pasos:**

1. **Verificar que no hay dependencias:**
   ```bash
   # Buscar cualquier referencia restante
   grep -r "xml_ingest\|xml_parser" apps/ config/ tasks/
   ```

2. **Eliminar directorios:**
   - `apps/services/xml_ingest/`
   - `apps/services/xml_parser/`

3. **Limpiar configuración:**
   - Remover de `config/celery.py`
   - Remover de `config/settings.py`
   - Remover de `INSTALLED_APPS` si están listados

4. **Actualizar documentación:**
   - Remover referencias a módulos legacy
   - Actualizar guías de desarrollo

**Criterios de validación:**
- ✅ No hay referencias a `xml_ingest` o `xml_parser` en código
- ✅ Todos los tests pasan
- ✅ Build y deployment funcionan correctamente

**Riesgo:** 🟢 BAJO (solo si todas las fases anteriores están completas)

**Timeline:** 1 semana

---

## 📊 Timeline General

| Fase | Duración | Dependencias | Riesgo |
|------|----------|--------------|--------|
| FASE 1: Dependencias Directas | 2-3 semanas | Ninguna | 🟢 BAJO |
| FASE 2: Endpoints DRF | 2-3 semanas | FASE 1 | 🟢 BAJO |
| FASE 3: Tareas Celery | 3-4 semanas | FASE 1 | 🟡 MEDIO |
| FASE 4: Dependencias Cruzadas | 4-5 semanas | FASE 1 | 🟡 MEDIO |
| FASE 5: Lógica Especializada | 6-8 semanas | FASE 4 | 🔴 ALTO |
| FASE 6: Deprecación/Eliminación | 2-3 semanas | Todas anteriores | 🟢 BAJO |
| **TOTAL** | **19-26 semanas** | - | - |

---

## ✅ Checklist de Validación por Fase

### FASE 1 ✅
- [ ] `facturas/services.py` no tiene imports de `xml_ingest`
- [ ] `facturas/api/viewsets.py` no tiene imports de `xml_ingest`
- [ ] Todos los tests de `facturas/tests/` pasan
- [ ] Feature flag `FEATURE_DOCUMENT_PIPELINE` puede ser `True` sin fallback

### FASE 2 ✅
- [ ] Endpoints `/upload-ubl/` y `/importar-ubl/` tienen headers de deprecación
- [ ] Endpoints redirigen internamente a pipeline universal
- [ ] Documentación OpenAPI actualizada
- [ ] Logs de advertencia se generan

### FASE 3 ✅
- [ ] Tarea `document_ingest_task` está registrada en Celery
- [ ] Workers pueden procesar tareas del pipeline universal
- [ ] Configuración de logging actualizada
- [ ] No hay tareas huérfanas

### FASE 4 ✅
- [ ] `document_parser` no tiene imports de `xml_parser`
- [ ] `maildigester` no tiene imports de `xml_parser`
- [ ] `facturas/ubl_parser.py` no tiene imports de `xml_parser`
- [ ] Todos los tests pasan

### FASE 5 ✅
- [ ] Pipeline universal procesa AttachedDocument
- [ ] ApplicationResponse se extrae correctamente
- [ ] Tests de casos especiales pasan
- [ ] No hay regresiones

### FASE 6 ✅
- [ ] Módulos marcados como deprecados
- [ ] No hay referencias a `xml_ingest` o `xml_parser`
- [ ] Documentación actualizada
- [ ] Módulos eliminados del código base

---

## 🚨 Estrategia de Rollback

### Por Fase

**FASE 1-2:** Rollback inmediato mediante feature flags
- `FEATURE_DOCUMENT_PIPELINE=False` restaura comportamiento legacy

**FASE 3:** Rollback requiere actualizar workers
- Mantener ambas tareas registradas durante transición
- Redirigir llamadas según necesidad

**FASE 4-5:** Rollback complejo
- Requiere mantener código legacy durante período de transición
- Migración gradual con co-existencia

**FASE 6:** Rollback imposible (eliminación)
- Solo proceder si todas las fases anteriores están validadas

---

## 📝 Notas de Implementación

### Feature Flags

Mantener durante toda la migración:
- `FEATURE_DOCUMENT_PIPELINE`: Controla uso del pipeline universal
- `FEATURE_XML_PIPELINE`: Controla uso del pipeline XML legacy (deprecado)

### Testing

- **Unit Tests:** Migrar tests críticos a pipeline universal
- **Integration Tests:** Validar flujos completos con ambos pipelines
- **E2E Tests:** Validar casos de uso reales con pipeline universal

### Monitoreo

- Agregar métricas de uso de endpoints legacy
- Monitorear errores durante migración
- Alertar cuando uso de legacy sea < 5%

---

## 🎯 Criterios de Éxito

1. ✅ **Cero dependencias** de `xml_ingest`/`xml_parser` en código de producción
2. ✅ **100% de funcionalidad** migrada al pipeline universal
3. ✅ **Todos los tests** pasan con pipeline universal
4. ✅ **Cero regresiones** en funcionalidad existente
5. ✅ **Documentación** actualizada y completa
6. ✅ **Módulos legacy** eliminados del código base

---

**Última actualización:** 2026-02-10  
**Próxima revisión:** Después de completar FASE 1
