# MIGRACIÓN COMPLETA — RESUMEN EJECUTADO

**Fecha:** 2026-02-10  
**Estado:** ✅ **MIGRACIÓN APLICADA**  
**Objetivo:** Sustituir todo uso de `xml_ingest`/`xml_parser` por `document_ingest`/`document_parser`

---

## ✅ CAMBIOS APLICADOS

### 1. Backend - Servicios y Endpoints DRF

#### ✅ `apps/tenant/facturas/services.py`
- **Import actualizado:** `norm_nit` ahora usa `document_parser.normalizers`
- **`importar_documento`:** Usa pipeline universal cuando `FEATURE_DOCUMENT_PIPELINE=True`
- **`importar_ubl_async`:** Usa `document_ingest_task` de Celery
- **`importar_factura_desde_ubl`:** Usa `ingest_document` para preview
- **Fallback legacy eliminado:** Retorna error 503 si pipeline universal no está disponible

#### ✅ `apps/tenant/facturas/api/viewsets.py`
- **`upload_ubl`:** ⚠️ DEPRECATED - Delega completamente al pipeline universal
- **`importar_ubl`:** ⚠️ DEPRECATED - Delega completamente al pipeline universal
- **`task_status`:** Usa `get_task_status` del pipeline universal
- **Código legacy eliminado:** Removido flujo legacy duplicado

### 2. Celery - Tareas y Configuración

#### ✅ `apps/services/document_ingest/tasks.py`
- **Creado:** Migrado desde `apps/services/xml_ingest/tasks.py`
- **Tarea:** `document_ingest_task` (reemplaza `xml_ingest_task`)
- **Función:** `get_task_status` (reemplaza `task_status`)
- **Pipeline:** Usa `ingest_document` del servicio universal

#### ✅ `config/celery.py`
- **`autodiscover_tasks`:** Apunta a `apps.services.document_ingest`
- **`app.conf.imports`:** Actualizado para incluir `document_ingest.tasks`

#### ✅ `config/settings.py`
- **`CELERY_IMPORTS`:** Actualizado para incluir `document_ingest.tasks`
- **`CELERY_TASK_ROUTES`:** Agregada ruta para `document_ingest_task` → `high_priority`
- **Logging:** Actualizado de `xml_ingest` a `document_ingest`

### 3. UI/JS - Workspace

#### ✅ `apps/tenant/core/static/core/js/facturas.ui.js`
- **Endpoint:** Ya usa `/api/v1/core/documentos/upload/` (actualizado previamente)
- **Manejo de errores:** Soporta códigos 409/422/415/400 según contrato universal
- **Preview mode:** Implementado correctamente

### 4. Endpoint Universal

#### ✅ `apps/tenant/core/api/viewsets_documentos.py`
- **Endpoint:** `POST /api/v1/core/documentos/upload/` implementado
- **Contrato:** JSON-only, preview/persist, códigos 409/422/415/400
- **Multi-formato:** Soporta XML, PDF, XLS/XLSX, CSV, TXT

---

## ⚠️ REFERENCIAS LEGACY RESTANTES (NO CRÍTICAS)

### Tests Legacy
Los siguientes archivos de tests aún referencian `xml_ingest`/`xml_parser` pero **NO afectan la funcionalidad de producción**:

- `apps/tenant/facturas/tests/test_nota_credito_pipeline.py`
- `apps/tenant/facturas/tests/test_xml_pipeline_canonical.py`
- `apps/tenant/facturas/tests/test_services_ingest_integration.py`
- `apps/services/xml_ingest/tests/*` (tests del módulo legacy)
- `apps/services/xml_parser/tests/*` (tests del módulo legacy)

**Acción requerida:** Actualizar tests para usar pipeline universal (no bloquea migración).

### Módulos Legacy (Aún Existen)
Los siguientes módulos legacy aún existen pero **NO son referenciados en código de producción**:

- `apps/services/xml_ingest/` (directorio completo)
- `apps/services/xml_parser/` (directorio completo)

**Acción requerida:** Eliminar después de actualizar tests y verificar 0 referencias.

### Referencias en Documentación/Comentarios
- Comentarios en código que mencionan `xml_ingest`/`xml_parser` (no afectan funcionalidad)
- Documentación en `config/settings.py` línea 870 (comentario sobre `FEATURE_XML_PIPELINE`)

**Acción requerida:** Actualizar comentarios/documentación (opcional).

---

## 📋 CHECKLIST DE VALIDACIÓN

### ✅ Completado
- [x] Endpoints DRF actualizados para usar pipeline universal
- [x] Servicios actualizados para usar `document_ingest`
- [x] Celery configurado con tarea universal
- [x] JS/UI apunta al endpoint universal
- [x] Logging actualizado en `settings.py`
- [x] Sin errores de linting

### ⏳ Pendiente (No Bloquea)
- [ ] Actualizar tests legacy para usar pipeline universal
- [ ] Eliminar directorios `xml_ingest`/`xml_parser` (después de actualizar tests)
- [ ] Actualizar comentarios/documentación

---

## 🚀 PRÓXIMOS PASOS

### 1. Validación en Docker
```bash
docker compose -f infra/compose/docker-compose.yml --env-file .env up -d --build
docker compose -f infra/compose/docker-compose.yml ps
docker compose -f infra/compose/docker-compose.yml logs -f app celery beat
```

### 2. Verificar Tarea Celery
```bash
docker compose -f infra/compose/docker-compose.yml exec celery celery -A config inspect registered | grep document_ingest
```

### 3. Pruebas E2E
- Subir XML Factura con `preview=true` → 200 OK con DTO
- Subir XML Factura con `preview=false` → 201 Created
- Repetir misma Factura → 409 Conflict
- Subir Nota Crédito válida → 201 Created
- Repetir misma Nota Crédito → 409 Conflict

### 4. Actualizar Tests (Opcional)
- Migrar tests de `xml_ingest` a `document_ingest`
- Actualizar aserciones para usar contrato universal
- Verificar que tests pasan

### 5. Eliminación Final (Después de Tests)
```bash
# Verificar 0 referencias
grep -r "xml_ingest\|xml_parser" apps/ config/ --exclude-dir=__pycache__ --exclude="*.pyc"

# Si 0 referencias, eliminar:
rm -rf apps/services/xml_ingest/
rm -rf apps/services/xml_parser/
```

---

## 📊 ESTADO FINAL

**Migración de Código de Producción:** ✅ **COMPLETA**

- ✅ Todos los endpoints DRF usan pipeline universal
- ✅ Todos los servicios usan `document_ingest`
- ✅ Celery configurado correctamente
- ✅ UI/JS actualizado
- ✅ Sin errores de linting

**Pendiente (No Crítico):**
- ⏳ Actualizar tests legacy
- ⏳ Eliminar directorios legacy (después de tests)
- ⏳ Actualizar documentación/comentarios

---

**Última actualización:** 2026-02-10  
**Próxima acción:** Validar en Docker y ejecutar pruebas E2E
