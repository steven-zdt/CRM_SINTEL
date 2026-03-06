# RESUMEN — REFACTOR AISLAMIENTO CRUD

**Fecha:** 2026-02-10  
**Estado:** ✅ **REFACTORIZACIÓN COMPLETA**

---

## ✅ CAMBIOS APLICADOS

### 1. `apps/services/document_ingest/ingest_service.py`
- ✅ Eliminado import de `materialize_document`
- ✅ Eliminado bloque completo de persistencia
- ✅ Siempre devuelve DTO sin persistir (`persisted: false`)

### 2. `apps/tenant/core/api/viewsets_documentos.py`
- ✅ Siempre usa `preview=True` al llamar `ingest_document`
- ✅ Eliminada construcción de `redirect_url` basada en persistencia
- ✅ Agregado `create_endpoint` en respuesta

### 3. `apps/tenant/facturas/api/viewsets.py`
- ✅ Creado endpoint `create_from_dto` (`POST /api/v1/facturas/create-from-dto/`)
- ✅ Endpoint `materialize` marcado como DEPRECATED

### 4. `apps/tenant/core/static/core/js/facturas.ui.js`
- ✅ Creada función `createFacturaFromDTO()` para persistir DTO
- ✅ Actualizado `importarFacturaDesdeXML()` para flujo separado:
  - Paso 1: Parsear (endpoint universal)
  - Paso 2: Persistir (endpoint de app)

---

## 📋 FLUJO ACTUALIZADO

### Antes (NO deseado):
```
XML → document_ingest → document_router → Factura creada automáticamente
```

### Después (Deseado):
```
XML → document_ingest → DTO
DTO → App endpoint → Factura creada bajo lógica propia
```

---

## ✅ VALIDACIONES

- [x] `document_ingest` NO persiste modelos
- [x] Endpoint universal solo devuelve DTO
- [x] Apps tienen endpoints propios para persistir
- [x] JS llama a endpoint universal y luego a endpoint de app

---

**Última actualización:** 2026-02-10
