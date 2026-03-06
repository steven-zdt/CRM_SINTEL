# AUDITORÍA — AISLAMIENTO DE CRUD

**Fecha:** 2026-02-10  
**Objetivo:** Aislar completamente el CRUD de las apps del servicio universal `document_ingest`

---

## 📋 HALLAZGOS DE AUDITORÍA

### 1. `apps/services/document_ingest/ingest_service.py`

**Líneas problemáticas:**
- **Línea 39:** Importa `materialize_document` del router de dominio
- **Línea 337:** Llama a `materialize_document(dto_dict, request_id=request_id)` que persiste modelos
- **Líneas 334-410:** Bloque completo que persiste cuando `FEATURE_XML_PIPELINE=True` y `preview=False`

**Acción requerida:**
- Eliminar import de `materialize_document`
- Eliminar bloque de persistencia (líneas 334-410)
- Cambiar return para que SOLO devuelva DTO sin persistir

---

### 2. `apps/tenant/core/document_router.py`

**Líneas problemáticas:**
- **Línea 66-205:** Función `materialize_document()` que llama a materializadores que crean modelos
- **Líneas 271-300:** Registro de materializadores que llaman a `guardar_factura_desde_dto` y `guardar_nota_credito_desde_dto`
- **Líneas 248-322:** `_ensure_materializers_registered()` que importa servicios de facturas y crea modelos

**Acción requerida:**
- Desactivar o eliminar función `materialize_document()`
- Cambiar para que solo devuelva `{"materializable": true, "dto": {...}}` sin persistir
- Eliminar registros de materializadores que crean modelos

---

### 3. `apps/tenant/core/api/viewsets_documentos.py`

**Líneas problemáticas:**
- **Línea 134:** Llama a `ingest_document()` con `preview=False` que puede persistir
- **Líneas 152-172:** Construye `redirect_url` asumiendo que se persistió

**Acción requerida:**
- Asegurar que `preview` siempre sea `True` o eliminar lógica de persistencia
- Cambiar respuesta para que solo devuelva DTO
- Eliminar construcción de `redirect_url` basada en persistencia

---

### 4. `apps/tenant/facturas/services.py`

**Líneas problemáticas:**
- **Líneas 113-128:** `materializar_factura_desde_dto()` que es llamada por el router
- **Líneas 131-159:** `materializar_nc_desde_dto()` que es llamada por el router
- **Líneas 160-310:** `guardar_factura_desde_dto()` que crea modelos (esta función está bien, pero no debe ser llamada por el router)
- **Líneas 311-425:** `guardar_nota_credito_desde_dto()` que crea modelos (esta función está bien, pero no debe ser llamada por el router)

**Acción requerida:**
- Mantener `guardar_factura_desde_dto()` y `guardar_nota_credito_desde_dto()` (son correctas)
- Eliminar o desactivar `materializar_factura_desde_dto()` y `materializar_nc_desde_dto()` del router
- Crear nuevos endpoints en `facturas/api/viewsets.py` que llamen a estas funciones directamente

---

### 5. `apps/tenant/facturas/api/viewsets.py`

**Líneas problemáticas:**
- **Línea 667:** Llama a `materializar_factura_desde_result()` que puede persistir

**Acción requerida:**
- Crear nuevo endpoint `@action` `create_from_dto` que reciba DTO y lo persista
- Mantener endpoints CRUD manual existentes

---

### 6. `apps/tenant/core/static/core/js/facturas.ui.js`

**Líneas problemáticas:**
- **Línea 509:** Llama a `uploadDocumentoXML()` que puede persistir automáticamente
- **Líneas 512-514:** Recarga tabla si `result.persisted` es true

**Acción requerida:**
- Cambiar flujo para que:
  1. Llame a endpoint universal para obtener DTO (siempre con `preview=true`)
  2. Luego llame a endpoint de la app `/api/v1/facturas/create-from-dto/` para persistir
- Actualizar manejo de errores

---

## 🔧 PLAN DE REFACTORIZACIÓN

### Fase 1: Eliminar Persistencia de `document_ingest`

1. Modificar `ingest_service.py`:
   - Eliminar import de `materialize_document`
   - Eliminar bloque de persistencia (líneas 334-410)
   - Cambiar return para que siempre devuelva DTO sin persistir

### Fase 2: Desactivar Router de Dominio

1. Modificar `document_router.py`:
   - Desactivar función `materialize_document()` o cambiar para que solo devuelva DTO
   - Eliminar registros de materializadores

### Fase 3: Asegurar Endpoint Universal Solo Devuelve DTO

1. Modificar `viewsets_documentos.py`:
   - Asegurar que `preview` siempre sea `True` o eliminar lógica de persistencia
   - Cambiar respuesta para que solo devuelva DTO

### Fase 4: Crear Endpoints de App para Persistir desde DTO

1. Modificar `facturas/api/viewsets.py`:
   - Crear endpoint `@action` `create_from_dto` que reciba DTO y lo persista
   - Usar `guardar_factura_desde_dto()` y `guardar_nota_credito_desde_dto()` directamente

### Fase 5: Actualizar JS para Flujo Separado

1. Modificar `facturas.ui.js`:
   - Cambiar `importarFacturaDesdeXML()` para que:
     - Llame a endpoint universal con `preview=true`
     - Luego llame a endpoint de app para persistir
   - Actualizar manejo de errores

---

## ✅ CHECKLIST DE VALIDACIÓN

- [ ] `document_ingest` NO persiste modelos
- [ ] `document_router` NO persiste modelos
- [ ] Endpoint universal solo devuelve DTO
- [ ] Apps tienen endpoints propios para persistir desde DTO
- [ ] JS llama a endpoint universal y luego a endpoint de app
- [ ] CRUD manual funciona sin `document_ingest`
- [ ] Upload XML → DTO sin persistencia automática
- [ ] Consumir DTO → crear factura local funciona

---

**Última actualización:** 2026-02-10
