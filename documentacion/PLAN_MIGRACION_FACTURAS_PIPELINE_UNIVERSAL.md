# 📋 Plan de Migración: Facturas → Pipeline Universal de Documentos

**Versión:** 2.36  
**Fecha:** 2026-02-10  
**Estado:** FASE 0-2 Completadas ✅

## 🎯 Objetivo

Migrar la app `apps/tenant/facturas` desde su flujo actual centrado en XML/UBL, hacia un flujo universal de ingestión de documentos (XML, PDF, XLS/XLSX, CSV, TXT), consumiendo el nuevo servicio `document_ingest`, sin romper:

- ✅ El endpoint actual `/upload-ubl/`
- ✅ La inmutabilidad de facturas
- ✅ Los modelos existentes
- ✅ Las reglas SSoT / API-First / Service Layer
- ✅ Multitenancy
- ✅ Los ~60 tests actuales de facturas

## 📊 Estado del Pipeline Universal

**Pipeline Universal ya implementado (FASE 0-9):**
- ✅ `apps/services/document_parser/`: Parsing low-level genérico (XML, PDF, XLS/XLSX, CSV, TXT)
- ✅ `apps/services/document_ingest/`: Orquestación, routing, validación
- ✅ `apps/tenant/core/document_router.py`: Router de dominio para materialización
- ✅ `apps/tenant/core/api/viewsets_documentos.py`: Endpoint universal `/api/v1/core/documentos/upload/`
- ✅ Sistema de validadores plug-in por tipo de documento
- ✅ Tests completos (FASE 9)

**Pipeline Legacy (mantener durante transición):**
- ✅ `apps/services/xml_parser/`: Parsing XML legacy (mantenido por compatibilidad)
- ✅ `apps/services/xml_ingest/`: Orquestación XML legacy (mantenido por compatibilidad)
- ✅ `apps/tenant/facturas/services.py`: Servicios actuales (migrar gradualmente)

---

## 🔥 FASE 0 — Preparación ✅ COMPLETADA

### 1. Feature Flags Creados

**Ubicación:** `config/settings.py`

```python
# ⚠️ v2.36: Document Ingest Pipeline Universal (FASE 0)
# - FEATURE_DOCUMENT_PIPELINE=True: Activa el pipeline universal de documentos
# - FEATURE_DOCUMENT_PIPELINE=False: Mantiene comportamiento actual (solo XML/UBL)
# - FEATURE_UPLOAD_DOCUMENT_ENDPOINT=True: Activa endpoint universal
# - FEATURE_UPLOAD_DOCUMENT_ENDPOINT=False: Mantiene solo endpoints específicos por app
FEATURE_DOCUMENT_PIPELINE = os.getenv("FEATURE_DOCUMENT_PIPELINE", "false").lower() == "true"
FEATURE_UPLOAD_DOCUMENT_ENDPOINT = os.getenv("FEATURE_UPLOAD_DOCUMENT_ENDPOINT", "false").lower() == "true"
```

**Estado:** ✅ Implementado y verificado

### 2. Import Seguro en `apps/tenant/facturas/services.py`

**Ubicación:** `apps/tenant/facturas/services.py`

```python
# ⚠️ v2.36 FASE 0: Import seguro para Document Ingest Pipeline Universal
# Permite coexistencia con pipeline XML legacy durante migración
try:
    from apps.services.document_ingest.ingest_service import ingest_document
    HAS_DOCUMENT_INGEST = True
except (ImportError, Exception) as e:
    # Si document_ingest no está disponible, continuar con pipeline legacy
    ingest_document = None
    HAS_DOCUMENT_INGEST = False
    logger = logging.getLogger(__name__)
    logger.debug(f"document_ingest no disponible: {e}")
```

**Estado:** ✅ Implementado

### 3. NO se crean parsers

**Razón:** `apps/services/document_parser/*` ya existe y opera como SSoT del parsing universal.

**Parsers disponibles:**
- ✅ `xml_parser/parser.py`: UBL 2.1 Invoice/CreditNote
- ✅ `pdf_parser/parser.py`: Extracción de texto (placeholder)
- ✅ `excel_parser/parser.py`: XLS/XLSX a DataFrame (placeholder)
- ✅ `csv_parser/parser.py`: CSV a DataFrame (placeholder)
- ✅ `txt_parser/parser.py`: Heurísticas de texto (placeholder)

---

## 📋 Fases Siguientes

### FASE 2 — Actualizar flujo UBL para usar pipeline universal ✅ COMPLETADA

**Objetivo:** Reemplazar internamente `importar_ubl_sync` e `importar_ubl_async` para usar `importar_documento()` que consume el pipeline universal.

**Tareas completadas:**
1. ✅ Creada función `importar_documento()` que usa `ingest_document()` cuando `FEATURE_DOCUMENT_PIPELINE=True`
2. ✅ `importar_ubl_sync()` ahora llama a `importar_documento(file_bytes, filename="ubl.xml", preview=False, async_mode=False)`
3. ✅ `importar_ubl_async()` ahora llama a `importar_documento()` cuando el feature flag está activo
4. ✅ Mantiene compatibilidad retroactiva: fallback a pipeline legacy cuando `FEATURE_DOCUMENT_PIPELINE=False`
5. ✅ Maneja correctamente preview mode y persistencia
6. ✅ Soporta tanto Invoice como CreditNote
7. ✅ Materialización manual cuando `FEATURE_XML_PIPELINE=False` pero `FEATURE_DOCUMENT_PIPELINE=True`

**Archivos modificados:**
- `apps/tenant/facturas/services.py`

**Compatibilidad:**
- ✅ Misma firma de funciones (`importar_ubl_sync`, `importar_ubl_async`)
- ✅ Mismo formato de retorno
- ✅ Tests existentes deben seguir pasando

**Notas:**
- El pipeline universal requiere `FEATURE_XML_PIPELINE=True` para materialización automática
- Si `FEATURE_DOCUMENT_PIPELINE=True` pero `FEATURE_XML_PIPELINE=False`, se materializa manualmente desde el DTO usando `guardar_factura_desde_dto()` o `guardar_nota_credito_desde_dto()`
- El modo async actualmente se procesa de forma síncrona pero retorna formato compatible

### FASE 1 — Adaptar `upload_ubl` para usar `document_ingest` (Pendiente)

**Nota:** FASE 2 se completó antes de FASE 1 porque actualiza las funciones internas que `upload_ubl` usa.

### FASE 2 — Actualizar flujo UBL para usar pipeline universal ✅ COMPLETADA

**Objetivo:** Reemplazar internamente `importar_ubl_sync` e `importar_ubl_async` para usar `importar_documento()` que consume el pipeline universal.

**Tareas completadas:**
1. ✅ Creada función `importar_documento()` que usa `ingest_document()` cuando `FEATURE_DOCUMENT_PIPELINE=True`
2. ✅ `importar_ubl_sync()` ahora llama a `importar_documento(file_bytes, filename="ubl.xml", preview=False, async_mode=False)`
3. ✅ `importar_ubl_async()` ahora llama a `importar_documento()` cuando el feature flag está activo
4. ✅ Mantiene compatibilidad retroactiva: fallback a pipeline legacy cuando `FEATURE_DOCUMENT_PIPELINE=False`
5. ✅ Maneja correctamente preview mode y persistencia
6. ✅ Soporta tanto Invoice como CreditNote

**Archivos modificados:**
- `apps/tenant/facturas/services.py`

**Compatibilidad:**
- ✅ Misma firma de funciones (`importar_ubl_sync`, `importar_ubl_async`)
- ✅ Mismo formato de retorno
- ✅ Tests existentes deben seguir pasando

**Notas:**
- El pipeline universal requiere `FEATURE_XML_PIPELINE=True` para materialización automática
- Si `FEATURE_DOCUMENT_PIPELINE=True` pero `FEATURE_XML_PIPELINE=False`, se materializa manualmente desde el DTO
- El modo async actualmente se procesa de forma síncrona pero retorna formato compatible

### FASE 1 — Adaptar `upload_ubl` para usar `document_ingest` (Pendiente)

**Objetivo:** Modificar `apps/tenant/facturas/api/viewsets.py::upload_ubl` para usar `ingest_document()` cuando `FEATURE_DOCUMENT_PIPELINE=True`.

**Tareas:**
1. Modificar `upload_ubl` para detectar feature flag
2. Si `FEATURE_DOCUMENT_PIPELINE=True`:
   - Llamar `ingest_document()` con `kind_hint="invoice"` o `"creditnote"`
   - Mapear respuesta del pipeline universal a formato esperado por el ViewSet
3. Si `FEATURE_DOCUMENT_PIPELINE=False`:
   - Mantener flujo legacy actual
4. Mantener compatibilidad con parámetros existentes (`async`, `preview`)

**Archivos a modificar:**
- `apps/tenant/facturas/api/viewsets.py`

**Tests:**
- Verificar que tests existentes siguen pasando
- Agregar tests para feature flag activado/desactivado

### FASE 2 — Migrar `guardar_factura_desde_dto` (Pendiente)

**Objetivo:** Asegurar que `guardar_factura_desde_dto()` sea compatible con DTO del pipeline universal.

**Tareas:**
1. Verificar que DTO del pipeline universal es compatible con `guardar_factura_desde_dto()`
2. Si hay diferencias, crear función de adaptación o extender `guardar_factura_desde_dto()`
3. Mantener idempotencia por CUFE
4. Mantener inmutabilidad

**Archivos a modificar:**
- `apps/tenant/facturas/services.py`

**Tests:**
- Verificar que tests de idempotencia siguen pasando
- Agregar tests con DTO del pipeline universal

### FASE 3 — Migrar `guardar_nota_credito_desde_dto` (Pendiente)

**Objetivo:** Similar a FASE 2, pero para Notas Crédito.

**Tareas:**
1. Verificar compatibilidad de DTO
2. Asegurar idempotencia por CUDE
3. Mantener relación 1:1 con Factura

**Archivos a modificar:**
- `apps/tenant/facturas/services.py`

### FASE 4 — Deprecar Pipeline Legacy (Pendiente)

**Objetivo:** Una vez que el pipeline universal esté completamente probado, deprecar el pipeline legacy.

**Tareas:**
1. Marcar `apps/services/xml_ingest` y `apps/services/xml_parser` como deprecated
2. Actualizar documentación
3. Planificar eliminación en versión futura

---

## 🔄 Estrategia de Rollout

### Desarrollo
1. Activar `FEATURE_DOCUMENT_PIPELINE=True` en `.env` local
2. Probar endpoint `/upload-ubl/` con XML de facturas
3. Verificar que tests pasan

### Staging
1. Activar `FEATURE_DOCUMENT_PIPELINE=True` en staging
2. Probar con datos reales
3. Monitorear logs y errores

### Producción
1. Rollout gradual por tenant (feature flag por tenant si es necesario)
2. Monitorear métricas
3. Rollback inmediato si hay problemas (desactivar feature flag)

---

## ✅ Checklist de Migración

### FASE 0 — Preparación ✅
- [x] Crear feature flags en `config/settings.py`
- [x] Agregar import seguro en `apps/tenant/facturas/services.py`
- [x] Verificar que no hay errores de linting
- [x] Verificar que tests existentes siguen pasando

### FASE 1 — Adaptar `upload_ubl` (Pendiente)
- [ ] Modificar `upload_ubl` para usar `ingest_document()` cuando feature flag activo
- [ ] Mantener compatibilidad con flujo legacy
- [ ] Tests para feature flag activado
- [ ] Tests para feature flag desactivado

### FASE 2 — Actualizar flujo UBL ✅
- [x] Crear función `importar_documento()` que usa pipeline universal
- [x] Reemplazar `importar_ubl_sync()` para usar `importar_documento()`
- [x] Reemplazar `importar_ubl_async()` para usar `importar_documento()`
- [x] Mantener compatibilidad retroactiva con pipeline legacy
- [x] Verificar que funciones se importan correctamente

### FASE 3 — Migrar `guardar_factura_desde_dto` (Pendiente)
- [ ] Verificar compatibilidad de DTO
- [ ] Adaptar si es necesario
- [ ] Tests de idempotencia
- [ ] Tests con DTO del pipeline universal

### FASE 3 — Migrar `guardar_nota_credito_desde_dto` (Pendiente)
- [ ] Verificar compatibilidad de DTO
- [ ] Adaptar si es necesario
- [ ] Tests de idempotencia
- [ ] Tests con DTO del pipeline universal

### FASE 4 — Deprecar Pipeline Legacy (Pendiente)
- [ ] Marcar como deprecated
- [ ] Actualizar documentación
- [ ] Planificar eliminación

---

## 📝 Notas Importantes

1. **Backward Compatibility:** El pipeline legacy (`xml_ingest`, `xml_parser`) se mantiene durante toda la migración para permitir rollback inmediato.

2. **Feature Flags:** Los feature flags permiten activar/desactivar el nuevo pipeline sin deploy, facilitando el rollout gradual.

3. **Tests:** Todos los tests existentes deben seguir pasando durante la migración. Si un test falla, debe corregirse antes de continuar.

4. **SSoT:** El pipeline universal (`document_parser`, `document_ingest`) es la única fuente de verdad para parsing/normalización. El pipeline legacy se mantiene solo por compatibilidad.

5. **Inmutabilidad:** Las reglas de inmutabilidad de facturas (PUT/PATCH bloqueados) se mantienen intactas.

6. **Multitenancy:** El pipeline universal ya maneja multitenancy correctamente mediante `schema_context`.

---

## 🔗 Referencias

- **Documentación del Pipeline Universal:** `documentacion/arquitectura_general.md` (sección "Document Ingest Pipeline Universal")
- **Documentación de Validadores:** `documentacion/arquitectura_general.md` (sección "Validadores por Tipo de Documento")
- **Documentación de Integración:** `documentacion/arquitectura_general.md` (sección "Integración con Apps de Negocio")
- **Tests del Pipeline:** `tests/services/`, `tests/tenant/`, `tests/api/`, `tests/multitenant/`
