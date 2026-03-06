# REFACTOR — AISLAMIENTO COMPLETO DE CRUD

**Fecha:** 2026-02-10  
**Objetivo:** Aislar completamente el CRUD de las apps del servicio universal `document_ingest`

---

## ✅ CAMBIOS APLICADOS

### 1. `apps/services/document_ingest/ingest_service.py`

**Cambios:**
- ✅ Eliminado import de `materialize_document` del router de dominio
- ✅ Eliminado bloque completo de persistencia (líneas 268-428)
- ✅ Cambiado return para que SIEMPRE devuelva DTO sin persistir
- ✅ Actualizado docstring para reflejar que SOLO parsea

**Resultado:**
```python
# Antes: Persistía cuando preview=False
if not preview:
    persist_result, persist_code = materialize_document(dto_dict)
    return {"persisted": True, "id": ..., ...}, persist_code

# Después: SIEMPRE devuelve DTO sin persistir
return {
    "success": True,
    "persisted": False,  # Siempre False
    "dto": dto_dict,
    "sha256": sha256_hash,
    "metadata": metadata,
    "tipo": dto_dict.get("type") or dto_dict.get("document_type", ""),
}, 200
```

---

### 2. `apps/tenant/core/api/viewsets_documentos.py`

**Cambios:**
- ✅ Cambiado `preview=preview` a `preview=True` (siempre True)
- ✅ Eliminada construcción de `redirect_url` basada en persistencia
- ✅ Agregado `create_endpoint` en respuesta para indicar dónde persistir

**Resultado:**
```python
# Antes: Podía persistir si preview=False
result, status_code = ingest_document(..., preview=preview, ...)
if result.get("persisted"):
    response_data["id"] = result.get("id")
    response_data["redirect_url"] = f"/api/v1/facturas/{doc_id}/"

# Después: Siempre devuelve DTO con sugerencia de endpoint
result, status_code = ingest_document(..., preview=True, ...)
response_data = {
    "success": True,
    "persisted": False,  # Siempre False
    "dto": result.get("dto", {}),
    "create_endpoint": "/api/v1/facturas/create-from-dto/",  # Sugerencia
}
```

---

### 3. `apps/tenant/facturas/api/viewsets.py`

**Cambios:**
- ✅ Creado nuevo endpoint `@action` `create_from_dto` (línea 640)
- ✅ Endpoint recibe DTO y lo persiste usando `materializar_factura_desde_result`
- ✅ Endpoint `materialize` marcado como DEPRECATED

**Nuevo Endpoint:**
```python
@action(detail=False, methods=["post"], url_path="create-from-dto")
def create_from_dto(self, request: Request) -> Response:
    """
    Crea una factura o nota crédito desde DTO parseado por document_ingest.
    
    POST /api/v1/facturas/create-from-dto/
    
    Body: {"dto": {...}, "persist_anexos": true|false}
    
    Returns: 201 Created | 200 OK | 409 Conflict | 422 Unprocessable Entity
    """
    dto = request.data.get("dto")
    persist_anexos = bool(request.data.get("persist_anexos", True))
    
    if not dto:
        return Response({"error": "missing_dto", ...}, status=400)
    
    payload, code = materializar_factura_desde_result(dto, persist_anexos=persist_anexos)
    return Response(payload, status=code)
```

---

### 4. `apps/tenant/core/static/core/js/facturas.ui.js`

**Cambios:**
- ✅ Actualizado `uploadDocumentoXML()` para siempre usar `preview=true`
- ✅ Creada nueva función `createFacturaFromDTO()` para persistir DTO
- ✅ Actualizado `importarFacturaDesdeXML()` para flujo separado:
  1. Llama a endpoint universal para parsear
  2. Si `preview=false`, llama a endpoint de app para persistir

**Nuevo Flujo:**
```javascript
// Paso 1: Parsear (siempre preview=true)
const parseResult = await uploadDocumentoXML(formData, true);

// Paso 2: Si preview=false, persistir
if (!preview) {
  const persistResult = await createFacturaFromDTO(parseResult.dto, true);
  // Recargar tabla si exitoso
  if (persistResult.id) {
    await loadTable();
  }
}
```

---

## 📋 FLUJO ACTUALIZADO

### Antes (NO deseado):
```
Usuario sube XML
  ↓
document_ingest parsea
  ↓
document_router materializa (crea Factura)
  ↓
Factura creada automáticamente
```

### Después (Deseado):
```
Usuario sube XML
  ↓
document_ingest parsea → devuelve DTO
  ↓
App (JS) recibe DTO
  ↓
App llama a /api/v1/facturas/create-from-dto/ con DTO
  ↓
App persiste Factura bajo su propia lógica
```

---

## ✅ VALIDACIONES

### 1. `document_ingest` NO persiste modelos
- ✅ Eliminado import de `materialize_document`
- ✅ Eliminado bloque de persistencia
- ✅ Siempre devuelve `persisted: false`

### 2. Endpoint universal solo devuelve DTO
- ✅ Siempre usa `preview=True`
- ✅ No construye `redirect_url` basado en persistencia
- ✅ Incluye `create_endpoint` como sugerencia

### 3. Apps tienen endpoints propios para persistir
- ✅ Creado `/api/v1/facturas/create-from-dto/`
- ✅ Endpoint usa servicios propios de la app

### 4. JS llama a endpoint universal y luego a endpoint de app
- ✅ `uploadDocumentoXML()` siempre parsea
- ✅ `createFacturaFromDTO()` persiste
- ✅ `importarFacturaDesdeXML()` orquesta ambos pasos

---

## 🔧 PENDIENTES

### 1. Desactivar Router de Dominio (Opcional)
- `apps/tenant/core/document_router.py` ya no se usa
- Puede mantenerse como stub o eliminarse

### 2. Actualizar Documentación
- Actualizar `arquitectura_general.md` con nuevo flujo
- Documentar endpoints nuevos

### 3. Pruebas
- Probar CRUD manual sin `document_ingest`
- Probar upload XML → DTO sin persistencia
- Probar consumir DTO → crear factura local

---

## 📊 RESUMEN

| Componente | Estado | Cambios |
|------------|--------|---------|
| `document_ingest` | ✅ Refactorizado | Eliminada persistencia |
| `viewsets_documentos` | ✅ Refactorizado | Solo devuelve DTO |
| `facturas/api/viewsets` | ✅ Actualizado | Nuevo endpoint `create_from_dto` |
| `facturas.ui.js` | ✅ Actualizado | Flujo separado parseo → persistencia |

---

**Última actualización:** 2026-02-10  
**Estado:** ✅ Refactorización completa aplicada
