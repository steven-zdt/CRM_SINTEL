# CAMBIOS DE CÓDIGO (DIFFS) — REFÁCTOR A UNIVERSAL

**Fecha:** 2026-02-10  
**Estado:** 📋 Diffs Listos para Aplicar  
**Objetivo:** Sustituir xml_ingest/xml_parser por document_ingest/document_parser

---

## 📋 1. apps/tenant/facturas/services.py

### 1.1 Reemplazar import de normalizers (línea 102)

```diff
--- a/apps/tenant/facturas/services.py
+++ b/apps/tenant/facturas/services.py
@@ -99,7 +99,7 @@ def determinar_naturaleza_desde_emisor(emisor_nit: str, empresa_nit: str) ->
     Returns:
         Factura.Naturaleza.VENTA si emisor == empresa, Factura.Naturaleza.COMPRA si difiere
     """
-    from apps.services.xml_ingest.normalizers import norm_nit
+    from apps.services.document_parser.normalizers import normalize_nit as norm_nit
     
     emisor_norm = norm_nit(emisor_nit)
     empresa_norm = norm_nit(empresa_nit)
```

### 1.2 Eliminar fallback legacy y usar pipeline universal (líneas 462-476)

```diff
--- a/apps/tenant/facturas/services.py
+++ b/apps/tenant/facturas/services.py
@@ -459,20 +459,6 @@ def importar_documento(
         async_mode: bool = False, # Actualmente no usado, pero mantiene compatibilidad de firma
         kind_hint: Optional[str] = None, # Sugerencia de tipo para el pipeline universal
     ) -> Union[Tuple[Dict[str, Any], int], Dict[str, Any]]:
-        """
-        Función unificada para importar cualquier documento usando el pipeline universal.
-        
-        Args:
-            file_bytes: Contenido del archivo en bytes.
-            filename: Nombre del archivo (para detección de tipo).
-            preview: Si True, solo parsear y validar, no persistir.
-            async_mode: Si True, encolar tarea asíncrona (actualmente no implementado, procesa síncrono).
-            kind_hint: Sugerencia de tipo de documento (ej: "invoice", "creditnote", "gasto").
-            
-        Returns:
-            Tuple (payload, status_code) si es síncrono, o Dict con task_id si es asíncrono.
-        """
         log = logging.getLogger("tenant.facturas.import")
         schema = getattr(connection, "schema_name", "-")
         request_id = getattr(settings, 'REQUEST_ID', '-')
@@ -480,7 +466,7 @@ def importar_documento(
         if not HAS_DOCUMENT_INGEST:
             log.warning(
                 "document_ingest_not_available_fallback_legacy",
                 extra={"request_id": request_id, "schema_name": schema}
             )
-            # Fallback al pipeline legacy si el universal no está disponible
+            # TODO: Deprecar fallback legacy una vez que document_ingest esté estable
             if async_mode:
                 # TODO: Implementar ingest_ubl_async si es necesario para el fallback
                 log.warning("async_mode_not_supported_in_legacy", extra={"request_id": request_id, "schema_name": schema})
@@ -490,7 +476,7 @@ def importar_documento(
                 return enriched_payload, status_code
 
         # Usar el pipeline universal
-        # El pipeline universal ya maneja async_mode internamente si está configurado
-        # Para esta fase, lo pasamos como False y el pipeline lo procesa síncronamente
+        # TODO: Revisar FEATURE_XML_PIPELINE una vez que la migración esté completa
         result, status_code = ingest_document(
             content=file_bytes,
             filename=filename,
@@ -500,7 +486,7 @@ def importar_documento(
             async_mode=False # Por ahora, el pipeline universal se ejecuta síncrono
         )
 
-        # Si es modo asíncrono, el pipeline universal debería retornar un task_id
+        # Si es modo asíncrono, usar tarea Celery del pipeline universal
         if async_mode:
-            # TODO: Si el pipeline universal soporta async real, esto debería retornar el task_id
-            # Por ahora, simulamos el retorno de una tarea pendiente
+            from apps.services.document_ingest.tasks import document_ingest_task
+            import base64
+            task = document_ingest_task.delay(
+                schema_name=schema or connection.schema_name,
+                file_b64=base64.b64encode(file_bytes).decode("utf-8"),
+                filename=filename
+            )
             log.info("document_ingest_async_simulated", extra={"request_id": request_id, "schema_name": schema})
-            return {"task_id": "simulated_task_id", "status": "PENDING"}, 202
+            return {"task_id": task.id, "status": "PENDING"}, 202
 
         # Si es preview, el pipeline universal ya retorna el DTO sin persistir
         if preview:
@@ -520,7 +506,7 @@ def importar_documento(
             # Si no se persistió pero no hay error explícito, puede ser que FEATURE_XML_PIPELINE=False
             # En ese caso, el pipeline universal solo parseó pero no materializó
             # Necesitamos materializar manualmente desde el DTO
-            if not result.get("persisted") and not result.get("error"):
+            if not result.get("persisted") and not result.get("error") and not preview:
                 dto = result.get("dto", {})
                 if dto:
                     # Extraer XML del resultado si está disponible
@@ -528,7 +514,7 @@ def importar_documento(
                     if "metadata" in result:
                         # El XML original podría estar en metadata o necesitamos reconstruirlo
                         # Por ahora, intentamos obtenerlo del DTO o usar vacío
-                        xml_text = dto.get("xml_content", "") or "" # TODO: Asegurar que el DTO universal contenga el XML si es necesario
+                        xml_text = dto.get("xml_content", "") or ""
                     
                     # Materializar usando guardar_factura_desde_dto o guardar_nota_credito_desde_dto
                     doc_type = dto.get("type") or dto.get("document_type", "")
@@ -550,7 +536,7 @@ def importar_documento(
                     return {
                         "persisted": False,
                         "dto": {},
                         "sha256": result.get("sha256"),
                         "metadata": result.get("metadata"),
                         "error": "materialization_skipped",
                         "message": "El documento fue parseado pero no se pudo materializar manualmente.",
                     }, 200 # O 422 si se considera un error de negocio
```

### 1.3 Actualizar importar_ubl_async para usar pipeline universal (línea 650)

```diff
--- a/apps/tenant/facturas/services.py
+++ b/apps/tenant/facturas/services.py
@@ -647,7 +647,7 @@ def importar_ubl_async(file_bytes: bytes, schema_name: Optional[str] = None) ->
             }
     else:
-        # Pipeline legacy
-        from apps.services.xml_ingest.service import ingest_ubl_async
-        return ingest_ubl_async(file_bytes, schema_name)
+        # Pipeline universal con Celery
+        from apps.services.document_ingest.tasks import document_ingest_task
+        import base64
+        task = document_ingest_task.delay(
+            schema_name=schema_name or connection.schema_name,
+            file_b64=base64.b64encode(file_bytes).decode("utf-8"),
+            filename="ubl.xml"
+        )
+        return {"task_id": task.id, "status": "PENDING"}
```

### 1.4 Actualizar importar_factura_desde_ubl para usar pipeline universal (línea 807)

```diff
--- a/apps/tenant/facturas/services.py
+++ b/apps/tenant/facturas/services.py
@@ -804,9 +804,9 @@ def importar_factura_desde_ubl(xml_content: str | bytes, preview: bool = False)
     if preview:
-        # Solo parsear, no persistir
-        from apps.services.xml_ingest.service import ingest_ubl_sync
-        enriched_payload, _ = ingest_ubl_sync(xml_bytes)
-        return None  # Preview no retorna factura
+        # Solo parsear, no persistir usando pipeline universal
+        from apps.services.document_ingest.ingest_service import ingest_document
+        result, _ = ingest_document(content=xml_bytes, filename="ubl.xml", preview=True)
+        return None  # Preview no retorna factura
     
     # Importar y persistir
```

---

## 📋 2. apps/tenant/facturas/api/viewsets.py

### 2.1 Actualizar task_status para usar pipeline universal (línea 673)

```diff
--- a/apps/tenant/facturas/api/viewsets.py
+++ b/apps/tenant/facturas/api/viewsets.py
@@ -670,7 +670,7 @@ class FacturaViewSet(viewsets.ReadOnlyModelViewSet):
               - error_code/message/hint cuando hay problemas
         """
         # ⚠️ NORMALIZACIÓN: Pasar request para contexto de logging
-        from apps.services.xml_ingest.service import task_status
+        from apps.services.document_ingest.tasks import get_task_status
-        payload, code = task_status(task_id, request=request)
+        payload, code = get_task_status(task_id, request=request)
         return Response(payload, status=code)
```

---

## 📋 3. Mover/Renombrar tasks.py (IMPRESCINDIBLE)

### 3.1 Crear apps/services/document_ingest/tasks.py (mover desde xml_ingest/tasks.py)

**Acción:** Mover `apps/services/xml_ingest/tasks.py` → `apps/services/document_ingest/tasks.py` y actualizar contenido.

```diff
--- a/apps/services/xml_ingest/tasks.py
+++ b/apps/services/document_ingest/tasks.py
@@ -1,25 +1,25 @@
 """
-Tareas Celery para procesamiento asíncrono de XML (tenant-aware).
+Tareas Celery para procesamiento asíncrono de documentos (tenant-aware).
 
 ⚠️ PRINCIPIOS:
 - Tenant-aware: Usa schema_context para aislamiento por esquema
 - Agnóstico: Retorna DTO serializable (sin acoplar a modelos de negocio)
-- Supports AttachedDocument with embedded Invoice and ApplicationResponse
+- Soporta múltiples formatos: XML, PDF, XLS/XLSX, CSV, TXT
 - Nombre canónico (dotted path) para evitar "unregistered task"
 """
 from celery import shared_task
+from celery.result import AsyncResult
 import base64
 import time
 import logging
-from typing import Dict, Any
+from typing import Dict, Any, Tuple, Optional
 from django_tenants.utils import schema_context
+from django.conf import settings
 
-from apps.services.xml_parser import parse_xml_bytes, ensure_invoice_root_and_artifacts
-from apps.tenant.facturas.ubl_parser import parse_ubl_to_dict
+from apps.services.document_ingest.ingest_service import ingest_document
 
-log_task = logging.getLogger("apps.services.xml_ingest")
+log_task = logging.getLogger("apps.services.document_ingest")
 
 def _safe_len(v):
     """Helper para obtener longitud segura."""
     try:
         return len(v) if v else 0
     except (TypeError, AttributeError):
         return 0
 
-@shared_task(name="apps.services.xml_ingest.tasks.xml_ingest_task")
-def xml_ingest_task(schema_name: str, xml_b64: str) -> Dict[str, Any]:
+@shared_task(name="apps.services.document_ingest.tasks.document_ingest_task")
+def document_ingest_task(schema_name: str, file_b64: str, filename: Optional[str] = None) -> Dict[str, Any]:
     """
     Tarea tenant-aware: abre schema_context(schema_name) antes de cualquier acceso.
     Nombre canónico (dotted path) para evitar 'unregistered task'.
     
     ⚠️ NORMALIZACIÓN: Logging estructurado con inicio, duración y resultado.
     
     Args:
         schema_name: Nombre del esquema del tenant (ej: "tenant1", "cliente_acme")
-        xml_b64: XML codificado en base64
+        file_b64: Archivo codificado en base64
+        filename: Nombre del archivo (opcional, para detección de tipo)
         
     Returns:
-        Dict serializable con estructura: {"dto": {...}, "anexos": {...}, "meta": {...}}
+        Dict serializable con estructura del pipeline universal: {"persisted": bool, "dto": {...}, "id": int, ...}
     """
     t0 = time.monotonic()
-    size_b64 = _safe_len(xml_b64)
+    size_b64 = _safe_len(file_b64)
     
     try:
         with schema_context(schema_name):
             log_task.info(
                 "document_ingest_task start",
                 extra={"schema_name": schema_name, "size_b64": size_b64, "filename": filename}
             )
             
-            xml_bytes = base64.b64decode(xml_b64.encode("utf-8"))
-            root = parse_xml_bytes(xml_bytes)
-            bundle = ensure_invoice_root_and_artifacts(root)   # AttachedDocument o Invoice cruda
-            dto = parse_ubl_to_dict(bundle["invoice_root"], xml_bytes=None, naturaleza=None)    # mapeo UBL -> DTO (dominio Facturas)
+            file_bytes = base64.b64decode(file_b64.encode("utf-8"))
+            result, status_code = ingest_document(
+                content=file_bytes,
+                filename=filename,
+                preview=False,
+                async_mode=False
+            )
             
-            out = {
-                "dto": dto,
-                "anexos": {
-                    "ubl_xml": bundle["invoice_xml"],
-                    "application_response_xml": bundle["app_response_xml"],
-                },
-                "meta": {"container": bundle["container"]},
-            }
+            # Adaptar formato de retorno para compatibilidad con llamadas legacy
+            # El pipeline universal retorna {"persisted": bool, "dto": {...}, "id": int, ...}
+            # Mantenemos este formato para consistencia
             
             dt = time.monotonic() - t0
             log_task.info(
                 "document_ingest_task done",
                 extra={
                     "schema_name": schema_name,
-                    "elapsed_s": round(dt, 3)
+                    "elapsed_s": round(dt, 3),
+                    "persisted": result.get("persisted", False),
+                    "status_code": status_code
                 }
             )
-            return out
+            return result
     except Exception as e:
         dt = time.monotonic() - t0
         log_task.exception(
-            "ingest_task error",
+            "document_ingest_task error",
             extra={
                 "schema_name": schema_name,
                 "elapsed_s": round(dt, 3)
             }
         )
         raise
+
+
+def get_task_status(task_id: str, request=None) -> Tuple[Dict[str, Any], int]:
+    """
+    Devuelve un JSON apto para UI:
+      - state: PENDING | STARTED | SUCCESS | FAILURE | UNKNOWN
+      - result: payload si SUCCESS
+      - error_code/message/hint cuando hay problemas
+    Nunca levanta excepción; siempre retorna (payload, 200).
+    
+    ⚠️ NORMALIZACIÓN: Acepta request opcional para extraer contexto (request_id, schema_name).
+    
+    Args:
+        task_id: ID de la tarea Celery
+        request: Request opcional para contexto de logging
+        
+    Returns:
+        Tuple (payload, status_code) donde payload tiene estructura:
+        {
+            "state": "PENDING" | "STARTED" | "SUCCESS" | "FAILURE" | "UNKNOWN",
+            "result": {...} si SUCCESS,
+            "error_code": str si FAILURE,
+            "message": str si hay error,
+            "hint": str opcional
+        }
+    """
+    from celery.result import AsyncResult
+    from django.db import connection
+    import logging
+    
+    log = logging.getLogger("apps.services.document_ingest")
+    schema = getattr(connection, "schema_name", "-")
+    request_id = getattr(settings, 'REQUEST_ID', '-')
+    
+    try:
+        task_result = AsyncResult(task_id)
+        state = task_result.state
+        
+        payload = {
+            "state": state,
+        }
+        
+        if state == "SUCCESS":
+            payload["result"] = task_result.result
+        elif state == "FAILURE":
+            payload["error_code"] = "task_failed"
+            payload["message"] = str(task_result.info) if task_result.info else "Tarea falló"
+            payload["hint"] = "Revisar logs del worker para más detalles"
+        elif state in ("PENDING", "STARTED"):
+            payload["message"] = f"Tarea en estado: {state}"
+        else:
+            payload["state"] = "UNKNOWN"
+            payload["message"] = f"Estado desconocido: {state}"
+        
+        log.info(
+            "task_status_queried",
+            extra={
+                "request_id": request_id,
+                "schema_name": schema,
+                "task_id": task_id,
+                "state": state
+            }
+        )
+        
+        return payload, 200
+    except Exception as e:
+        log.exception(
+            "task_status_error",
+            extra={
+                "request_id": request_id,
+                "schema_name": schema,
+                "task_id": task_id
+            }
+        )
+        return {
+            "state": "UNKNOWN",
+            "error_code": "query_error",
+            "message": f"Error al consultar estado de tarea: {str(e)}"
+        }, 200
```

---

## 📋 4. Thin-wrapper para ingest_ubl_async (opcional, mantener compatibilidad)

### 4.1 Crear wrapper en apps/services/xml_ingest/service.py (si se necesita mantener compatibilidad)

```diff
--- a/apps/services/xml_ingest/service.py
+++ b/apps/services/xml_ingest/service.py
@@ -62,6 +62,13 @@ def ingest_ubl_async(xml_bytes: bytes, schema_name: str) -> Dict[str, Any]:
     Returns:
         Dict with task_id and status: {"task_id": str, "status": "PENDING"}
     """
+    # TODO: Deprecar esta función una vez que todos los callers migren a document_ingest
+    # Thin-wrapper que delega al pipeline universal
+    import warnings
+    warnings.warn(
+        "ingest_ubl_async está deprecado. Use apps.services.document_ingest.tasks.document_ingest_task en su lugar.",
+        DeprecationWarning,
+        stacklevel=2
+    )
+    
     from .tasks import xml_ingest_task
+    # Delegar a pipeline universal
+    from apps.services.document_ingest.tasks import document_ingest_task
+    import base64
+    task = document_ingest_task.delay(
+        schema_name=schema_name,
+        file_b64=base64.b64encode(xml_bytes).decode("utf-8"),
+        filename="ubl.xml"
+    )
-    task = xml_ingest_task.delay(
-        schema_name=schema_name,
-        xml_b64=base64.b64encode(xml_bytes).decode("utf-8"),
-    )
     return {"task_id": task.id, "status": "PENDING"}
```

---

## 📋 5. config/celery.py

### 5.1 Actualizar autodiscover y imports

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

---

## 📋 6. config/settings.py

### 6.1 Actualizar CELERY_IMPORTS

```diff
--- a/config/settings.py
+++ b/config/settings.py
@@ -801,7 +801,7 @@ CELERY_IMPORTS = (
     "apps.public.tenants.tasks",  # Tarea crítica de onboarding
     "apps.services.maildigester.tasks",  # Tarea de ingesta de facturas desde correo
-    "apps.services.xml_ingest.tasks",  # Tarea de ingesta XML (tenant-aware)
+    "apps.services.document_ingest.tasks",  # Tarea de ingesta universal (tenant-aware)
 )
```

### 6.2 Actualizar CELERY_TASK_ROUTES para enrutar a cola high_priority

```diff
--- a/config/settings.py
+++ b/config/settings.py
@@ -811,7 +811,10 @@ CELERY_TASK_ROUTES = {
     # Tarea crítica de onboarding: cola de alta prioridad
     'apps.public.tenants.tasks.onboard_tenant_task': {'queue': 'high_priority'},
     
     # Ingesta de facturas desde correo: cola de alta prioridad (crítica)
     'apps.services.maildigester.tasks.fetch_and_process_billing_mail': {'queue': 'high_priority'},
     'apps.services.maildigester.tasks.fetch_and_process_billing_mail': {'queue': 'high_priority'},
+    
+    # Pipeline universal de documentos: cola de alta prioridad
+    'apps.services.document_ingest.tasks.document_ingest_task': {'queue': 'high_priority'},
 }
```

### 6.3 Actualizar configuración de logging

```diff
--- a/config/settings.py
+++ b/config/settings.py
@@ -950,13 +950,13 @@ LOGGING = {
             "propagate": False,
         },
-        # ⚠️ FASE 5: Tarea Celery de ingesta XML
-        "services.xml_ingest.task": {
+        # ⚠️ Pipeline universal: Tarea Celery de ingesta de documentos
+        "services.document_ingest.task": {
             "handlers": ["console"],
             "level": "INFO",
             "propagate": False,
         },
-        # ⚠️ FASE 5: Router/parsers XML
-        "services.xml_ingest.parse": {
+        # ⚠️ Pipeline universal: Router/parsers de documentos
+        "services.document_ingest.parse": {
             "handlers": ["console"],
             "level": "INFO",
             "propagate": False,
         },
@@ -1022,7 +1022,7 @@ LOGGING = {
             "propagate": False,
         },
-        # ⚠️ NORMALIZACIÓN: Logger principal de xml_ingest
-        "apps.services.xml_ingest": {
+        # ⚠️ NORMALIZACIÓN: Logger principal de document_ingest
+        "apps.services.document_ingest": {
             "handlers": ["console"],
             "level": "INFO",
             "propagate": False,
```

---

## 📋 7. JavaScript (solo si hay referencias legacy)

### 7.1 Verificar que no hay referencias legacy en JS

**Nota:** Según la auditoría, los archivos JS ya fueron migrados en la FASE 5 (Limpieza y Coherencia). No se requieren cambios adicionales.

Si se detectan referencias legacy en otros archivos JS:

```diff
--- a/path/to/file.js
+++ b/path/to/file.js
@@ -X, Y +X, Y @@
-const API_UPLOAD = "/api/v1/facturas/upload-ubl/";
+const API_UPLOAD = "/api/v1/core/documentos/upload/";
```

---

## 📋 8. Endpoints DRF (ya migrados)

### 8.1 Verificar endpoints

**Nota:** Los endpoints `/upload-ubl/` y `/importar-ubl/` ya usan internamente el pipeline universal según FASE 5. No se requieren cambios adicionales en este diff.

Si se requiere deprecar explícitamente:

```diff
--- a/apps/tenant/facturas/api/viewsets.py
+++ b/apps/tenant/facturas/api/viewsets.py
@@ -382,6 +382,10 @@ class FacturaViewSet(viewsets.ReadOnlyModelViewSet):
     @action(detail=False, methods=["post"], url_path="upload-ubl", parser_classes=[MultiPartParser, FormParser])
     def upload_ubl(self, request: Request) -> Response:
         """
+        ⚠️ DEPRECATED: Este endpoint está deprecado.
+        Use POST /api/v1/core/documentos/upload/ en su lugar.
+        Este endpoint será removido en v2.40.
         Sube un archivo XML UBL 2.1 y lo importa (async o sync).
         
         ⚠️ FASE 5: Mantiene compatibilidad retroactiva.
```

---

## ✅ Checklist de Aplicación

### Pre-aplicación
- [ ] Backup del código actual
- [ ] Verificar que `apps/services/document_ingest/tasks.py` NO existe
- [ ] Validar que pipeline universal funciona en modo síncrono

### Aplicación
- [ ] Aplicar diff 1 (facturas/services.py)
- [ ] Aplicar diff 2 (facturas/api/viewsets.py)
- [ ] **MOVER** `apps/services/xml_ingest/tasks.py` → `apps/services/document_ingest/tasks.py`
- [ ] Aplicar diff 3 (actualizar contenido de tasks.py movido)
- [ ] Aplicar diff 4 (thin-wrapper opcional)
- [ ] Aplicar diff 5 (config/celery.py)
- [ ] Aplicar diff 6 (config/settings.py)

### Post-aplicación
- [ ] Verificar que tarea `document_ingest_task` está registrada: `celery -A config inspect registered`
- [ ] Probar llamada asíncrona: `importar_ubl_async(file_bytes, schema_name)`
- [ ] Probar endpoint de estado: `GET /api/v1/facturas/task-status/{task_id}/`
- [ ] Validar que workers pueden procesar tareas
- [ ] Ejecutar tests: `pytest apps/tenant/facturas/tests/`

---

## 🚨 Notas Importantes

1. **Mover tasks.py:** Este es el único archivo que se MUEVE/RENOMBRA. No se crea nuevo.
2. **Compatibilidad:** El formato de retorno de `document_ingest_task` es diferente al de `xml_ingest_task`. Asegurar que los consumidores se adapten.
3. **Feature Flags:** Revisar `FEATURE_XML_PIPELINE` y `FEATURE_DOCUMENT_PIPELINE` después de aplicar cambios.
4. **Rollback:** Si hay problemas, revertir movimientos de archivos y cambios en `celery.py`/`settings.py` primero.

---

**Última actualización:** 2026-02-10  
**Próxima acción:** Aplicar diffs en orden secuencial
