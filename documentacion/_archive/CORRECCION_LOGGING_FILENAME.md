# CORRECCIÓN DE ERROR 500 — KeyError: "Attempt to overwrite 'filename' in LogRecord"

**Fecha:** 2026-02-10  
**Estado:** ✅ **CORREGIDO**  
**Problema:** Error 500 en `POST /api/v1/core/documentos/upload/` causado por uso de clave reservada `"filename"` en logging.

---

## 🔍 CAUSA TÉCNICA

El error `KeyError: "Attempt to overwrite 'filename' in LogRecord"` ocurre cuando se intenta usar una clave reservada del `LogRecord` de Python en el dict `extra` de logging.

**Claves reservadas de LogRecord:**
- `filename`, `lineno`, `funcName`, `module`, `pathname`
- `process`, `processName`, `thread`, `threadName`
- `created`, `msecs`, `relativeCreated`
- `levelname`, `levelno`, `message`, `name`

En este caso, se estaba usando `"filename"` en el dict `extra`, que colisiona con el atributo `filename` del `LogRecord` (que contiene la ruta del archivo Python donde se ejecuta el logging).

---

## ✅ CORRECCIONES APLICADAS

### 1. `apps/tenant/core/api/viewsets_documentos.py`

**Cambios:**
- `"filename"` → `"upload_filename"` en todas las llamadas a logging

**Líneas corregidas:**
- Línea 103: `logger.exception("documento_upload_read_error", ...)`
- Línea 124: `logger.info("documento_upload_start", ...)`
- Línea 210: `logger.info("documento_upload_complete", ...)`
- Línea 225: `logger.exception("documento_upload_error", ...)`

### 2. `apps/services/document_ingest/ingest_service.py`

**Cambios:**
- `"filename"` → `"upload_filename"` en todas las llamadas a logging

**Líneas corregidas:**
- Línea 113: `logger.info("document_ingest_start", ...)`
- Línea 127: `logger.info("document_ingest_normalization_ok", ...)`
- Línea 136: `logger.warning("document_ingest_normalization_error", ...)`
- Línea 161: `logger.info("document_ingest_routing_ok", ...)`
- Línea 170: `logger.warning("document_ingest_routing_failed", ...)`
- Línea 189: `logger.exception("document_ingest_parse_error", ...)`

### 3. `apps/services/document_ingest/tasks.py`

**Cambios:**
- `"filename"` → `"upload_filename"` en logging

**Líneas corregidas:**
- Línea 57: `log_task.info("document_ingest_task start", ...)`

### 4. `apps/tenant/facturas/api/viewsets.py`

**Cambios:**
- `"filename"` → `"upload_filename"` en logging (dentro de `safe_extra()`)

**Líneas corregidas:**
- Línea 564: `log_up.warning("upload_document read error", ...)`
- Línea 588: `log_up.info("upload_document success", ...)`
- Línea 605: `log_up.exception("upload_document error", ...)`

---

## 📋 RESUMEN DE CLAVES RENOMBRADAS

| Archivo | Antes | Después | Cantidad |
|---------|-------|---------|----------|
| `apps/tenant/core/api/viewsets_documentos.py` | `"filename"` | `"upload_filename"` | 4 |
| `apps/services/document_ingest/ingest_service.py` | `"filename"` | `"upload_filename"` | 6 |
| `apps/services/document_ingest/tasks.py` | `"filename"` | `"upload_filename"` | 1 |
| `apps/tenant/facturas/api/viewsets.py` | `"filename"` | `"upload_filename"` | 3 |
| **TOTAL** | | | **14** |

---

## ✅ VERIFICACIÓN DEL MODAL DEL WORKSPACE

### Estado: ✅ **ALINEADO CORRECTAMENTE**

**Archivo:** `apps/tenant/core/static/core/js/facturas.ui.js`

**Función `uploadDocumentoXML`:**
- ✅ Usa endpoint universal: `/api/v1/core/documentos/upload/`
- ✅ Soporta `?preview=true|false` como query param
- ✅ Envía archivo vía `FormData` con `file=<archivo.xml>`
- ✅ NO establece `Content-Type` manualmente (navegador añade boundary)
- ✅ Usa `credentials: 'include'` para cookies
- ✅ Maneja errores 409/422/415/400 con mensajes canónicos

**Función `importarFacturaDesdeXML`:**
- ✅ Llama a `uploadDocumentoXML` con `FormData` correcto
- ✅ Recarga tabla después de persistencia exitosa
- ✅ Maneja errores correctamente

**Botón del workspace:**
- ✅ `#btn-importar-ubl` abre modal correcto
- ✅ `#btn-confirm-import` llama a `importarFacturaDesdeXML`

---

## 🧪 COMANDOS DE VERIFICACIÓN

### 1. Probar subida con preview (200 OK)

```bash
curl -X POST "http://localhost:8000/api/v1/core/documentos/upload/?preview=true" \
  -H "Authorization: Bearer <token>" \
  -H "X-CSRFToken: <csrf_token>" \
  -F "file=@factura.xml" \
  -v
```

**Resultado esperado:**
- Status: `200 OK`
- Body: `{"persisted": false, "dto": {...}, "sha256": "...", ...}`
- **Sin errores en logs**

### 2. Probar subida con persistencia (201 Created)

```bash
curl -X POST "http://localhost:8000/api/v1/core/documentos/upload/?preview=false" \
  -H "Authorization: Bearer <token>" \
  -H "X-CSRFToken: <csrf_token>" \
  -F "file=@factura.xml" \
  -v
```

**Resultado esperado:**
- Status: `201 Created` o `200 OK` (si ya existe)
- Body: `{"persisted": true, "dto": {...}, "id": 123, ...}`
- **Sin errores en logs**

### 3. Verificar logs (sin KeyError)

```bash
docker compose -f infra/compose/docker-compose.yml logs app | grep -i "keyerror\|filename\|documento_upload"
```

**Resultado esperado:**
- ✅ No debe aparecer `KeyError: "Attempt to overwrite 'filename'"`
- ✅ Debe aparecer `documento_upload_start` con `upload_filename` en logs estructurados
- ✅ No debe haber tracebacks relacionados con logging

### 4. Verificar logs de Celery (si se usa async)

```bash
docker compose -f infra/compose/docker-compose.yml logs celery | grep -i "keyerror\|filename\|document_ingest_task"
```

**Resultado esperado:**
- ✅ No debe aparecer `KeyError`
- ✅ Debe aparecer `document_ingest_task start` con `upload_filename`

---

## 📊 DIFFS APLICADOS

### Diff 1: `apps/tenant/core/api/viewsets_documentos.py`

```diff
--- a/apps/tenant/core/api/viewsets_documentos.py
+++ b/apps/tenant/core/api/viewsets_documentos.py
@@ -100,7 +100,7 @@ def upload(self, request: Request) -> Response:
                 extra={
                     "request_id": request_id,
                     "schema_name": schema,
-                    "filename": filename,
+                    "upload_filename": filename,
                 }
             )
@@ -121,7 +121,7 @@ def upload(self, request: Request) -> Response:
             extra={
                 "request_id": request_id,
                 "schema_name": schema,
-                "filename": filename,
+                "upload_filename": filename,
                 "size_bytes": len(file_content),
                 "mime_type": mime_type,
                 "preview": preview,
@@ -207,7 +207,7 @@ def upload(self, request: Request) -> Response:
                 extra={
                     "request_id": request_id,
                     "schema_name": schema,
-                    "filename": filename,
+                    "upload_filename": filename,
                     "status_code": http_status,
                     "persisted": result.get("persisted", False),
                     "tipo": response_data.get("tipo"),
@@ -222,7 +222,7 @@ def upload(self, request: Request) -> Response:
                 extra={
                     "request_id": request_id,
                     "schema_name": schema,
-                    "filename": filename,
+                    "upload_filename": filename,
                 }
             )
```

### Diff 2: `apps/services/document_ingest/ingest_service.py`

```diff
--- a/apps/services/document_ingest/ingest_service.py
+++ b/apps/services/document_ingest/ingest_service.py
@@ -110,7 +110,7 @@ def ingest_document(
         extra={
             "request_id": request_id,
             "schema_name": schema,
-            "filename": filename,
+            "upload_filename": filename,
             "size_bytes": len(content),
             "sha256": sha256_hash,
         }
@@ -124,7 +124,7 @@ def ingest_document(
             extra={
                 "request_id": request_id,
                 "schema_name": schema,
-                "filename": filename,
+                "upload_filename": filename,
             }
         )
@@ -133,7 +133,7 @@ def ingest_document(
             extra={
                 "request_id": request_id,
                 "schema_name": schema,
-                "filename": filename,
+                "upload_filename": filename,
                 "error": str(e)[:200],
             }
         )
@@ -158,7 +158,7 @@ def ingest_document(
                 "request_id": request_id,
                 "schema_name": schema,
                 "document_type": document_type,
-                "filename": filename,
+                "upload_filename": filename,
             }
         )
@@ -167,7 +167,7 @@ def ingest_document(
             extra={
                 "request_id": request_id,
                 "schema_name": schema,
-                "filename": filename,
+                "upload_filename": filename,
                 "kind_hint": kind_hint,
                 "error": str(e)[:200],
             }
@@ -186,7 +186,7 @@ def ingest_document(
             extra={
                 "request_id": request_id,
                 "schema_name": schema,
-                "filename": filename,
+                "upload_filename": filename,
             }
         )
```

### Diff 3: `apps/services/document_ingest/tasks.py`

```diff
--- a/apps/services/document_ingest/tasks.py
+++ b/apps/services/document_ingest/tasks.py
@@ -54,7 +54,7 @@ def document_ingest_task(schema_name: str, file_b64: str, filename: Optional[s
             log_task.info(
                 "document_ingest_task start",
-                extra={"schema_name": schema_name, "size_b64": size_b64, "filename": filename}
+                extra={"schema_name": schema_name, "size_b64": size_b64, "upload_filename": filename}
             )
```

### Diff 4: `apps/tenant/facturas/api/viewsets.py`

```diff
--- a/apps/tenant/facturas/api/viewsets.py
+++ b/apps/tenant/facturas/api/viewsets.py
@@ -561,7 +561,7 @@ def upload_document(self, request: Request) -> Response:
                 extra=safe_extra({
                     "request_id": request.META.get("REQUEST_ID", "-"),
                     "schema_name": getattr(connection, "schema_name", "-"),
-                    "filename": file.name,
+                    "upload_filename": file.name,
                     "error": str(e)[:200],
                 })
@@ -585,7 +585,7 @@ def upload_document(self, request: Request) -> Response:
                 extra=safe_extra({
                     "request_id": request.META.get("REQUEST_ID", "-"),
                     "schema_name": getattr(connection, "schema_name", "-"),
-                    "filename": file.name,
+                    "upload_filename": file.name,
                     "size": len(file_content),
                     "preview": preview,
                     "async_mode": async_mode,
@@ -602,7 +602,7 @@ def upload_document(self, request: Request) -> Response:
                 extra=safe_extra({
                     "request_id": request.META.get("REQUEST_ID", "-"),
                     "schema_name": getattr(connection, "schema_name", "-"),
-                    "filename": file.name,
+                    "upload_filename": file.name,
                 })
             )
```

---

## ✅ CHECKLIST DE VALIDACIÓN

- [x] Todas las referencias a `"filename"` en logging renombradas a `"upload_filename"`
- [x] Sin errores de linting
- [x] Modal del workspace alineado al endpoint universal
- [x] Manejo de errores 409/422/415/400 implementado
- [x] FormData correcto (sin Content-Type manual)
- [x] CSRF y cookies configurados correctamente

---

## 🚀 PRÓXIMOS PASOS

1. **Probar en Docker:**
   ```bash
   docker compose -f infra/compose/docker-compose.yml up -d --build
   docker compose -f infra/compose/docker-compose.yml logs -f app
   ```

2. **Ejecutar pruebas E2E:**
   - Subir XML con preview → 200 OK
   - Subir XML sin preview → 201 Created
   - Verificar que NO aparece `KeyError` en logs

3. **Verificar modal del workspace:**
   - Abrir workspace → Click "Importar UBL XML"
   - Seleccionar archivo → Click "Confirmar"
   - Verificar que funciona sin errores 500

---

**Última actualización:** 2026-02-10  
**Estado:** ✅ **CORRECCIÓN COMPLETA**
