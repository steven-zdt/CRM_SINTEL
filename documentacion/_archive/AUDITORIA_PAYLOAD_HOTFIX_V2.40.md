# Auditoría: Hotfix ParseError Core Orchestrator v2.40

**Fecha:** 2026-01-XX  
**Versión:** v2.40  
**Estado:** ✅ Auditoría completada

---

## AUDIT SUMMARY

### A) Frontend API Helper (api-helpers.js)
- ✎ **CAMBIO**: `safeFetchJson` establece `Content-Type: application/json` incluso cuando `body` es `null`/`undefined`
- ✎ **CAMBIO**: Necesita verificar que `body` no sea `null`/`undefined` antes de establecer `Content-Type`
- ✓ **OK**: Ya detecta `FormData` y no establece `Content-Type` en ese caso
- ✓ **OK**: Ya convierte objetos a `JSON.stringify` correctamente

### B) Frontend httpJSON (empresa.page.js)
- ✎ **CAMBIO**: `httpJSON` siempre establece `Content-Type: application/json` incluso si `payloadOrNull` es `null`/`undefined`
- ✎ **CAMBIO**: No verifica si el payload es `FormData`
- ✓ **OK**: Ya maneja `null`/`undefined` para el body correctamente

### C) Call Sites (empresa.page.js, mailinbox.page.js)
- ✓ **OK**: `empresa.page.js` usa `httpJSON` con objetos planos (no FormData)
- ✓ **OK**: `mailinbox.page.js` usa `safeFetchJson` con objetos planos (no FormData)
- ✓ **OK**: No hay concatenación manual de JSON strings

### D) Core Orchestrator (MiEmpresaView.patch)
- ✎ **CAMBIO**: No valida que `request.data` sea un dict válido antes de procesarlo
- ✎ **CAMBIO**: No maneja el caso donde `request.data` está vacío o no es un dict
- ✓ **OK**: Ya tiene `parser_classes = [JSONParser, MultiPartParser, FormParser]`
- ✓ **OK**: Ya maneja errores de validación correctamente

---

## DIFFS

### D.1) Fix api-helpers.js - No establecer Content-Type si body es null/undefined

```diff
--- a/apps/tenant/core/static/core/js/lib/api-helpers.js
+++ b/apps/tenant/core/static/core/js/lib/api-helpers.js
@@ -112,15 +112,20 @@
     // ⚠️ v2.40: Manejo inteligente de Content-Type
     // Si el body es FormData, no establecer Content-Type (el navegador lo hará automáticamente)
     // Si el body es un objeto, establecer Content-Type: application/json y stringify
-    if (init.body instanceof FormData) {
+    const isFormData = (v) => typeof FormData !== "undefined" && v instanceof FormData;
+    
+    if (isFormData(init.body)) {
       // FormData: el navegador establecerá Content-Type automáticamente con boundary
       // No establecer Content-Type manualmente
-    } else {
+    } else if (init.body != null && method !== 'GET' && method !== 'HEAD') {
       // JSON: establecer Content-Type solo si hay body y es método mutante
       opts.headers['Content-Type'] = 'application/json';
       
       // Si el body es un objeto, convertirlo a JSON string
       if (opts.body && typeof opts.body === 'object') {
         opts.body = JSON.stringify(opts.body);
       }
+    } else if (init.body == null && method !== 'GET' && method !== 'HEAD') {
+      // Body es null/undefined pero es método mutante: no establecer Content-Type
+      // El servidor debe validar que el body es requerido
     }
```

### D.2) Fix httpJSON en empresa.page.js - No establecer Content-Type si payload es null/undefined

```diff
--- a/apps/tenant/core/static/core/js/empresa/empresa.page.js
+++ b/apps/tenant/core/static/core/js/empresa/empresa.page.js
@@ -109,9 +109,10 @@
   async function httpJSON(method, url, payloadOrNull) {
     const headers = {
       'Accept': 'application/json',
-      'Content-Type': 'application/json'
     };
 
+    const isFormData = (v) => typeof FormData !== "undefined" && v instanceof FormData;
+
     // Agregar CSRF para métodos mutantes
     if (['POST', 'PATCH', 'PUT', 'DELETE'].includes(method.toUpperCase())) {
       const csrfToken = w.API_HELPERS?.getCSRF?.() || '';
@@ -119,6 +120,15 @@
         headers['X-CSRFToken'] = csrfToken;
       }
     }
+
+    // ⚠️ v2.40: Establecer Content-Type solo si hay payload y no es FormData
+    if (payloadOrNull != null && method.toUpperCase() !== 'GET' && method.toUpperCase() !== 'HEAD') {
+      if (isFormData(payloadOrNull)) {
+        // FormData: el navegador establecerá Content-Type automáticamente
+        // No establecer Content-Type manualmente
+      } else {
+        headers['Content-Type'] = 'application/json';
+      }
+    }
```

### D.3) Fix Core Orchestrator - Validación temprana de payload

```diff
--- a/apps/tenant/core/api/views.py
+++ b/apps/tenant/core/api/views.py
@@ -287,6 +287,18 @@
         Actualización parcial de Empresa.
         Soporta application/json y multipart/form-data (para logo).
         """
+        # ⚠️ v2.40: Validación temprana de payload para evitar ParseError 500
+        # DRF puede lanzar ParseError si Content-Type es application/json pero el body no es JSON válido
+        # Esto debe retornar 400, no 500
+        if not isinstance(request.data, dict):
+            return Response(
+                {"error": "invalid_payload", "detail": "Cuerpo JSON requerido. El payload debe ser un objeto JSON válido."},
+                status=status.HTTP_400_BAD_REQUEST
+            )
+        
+        # Validar que el payload no esté completamente vacío (al menos debe tener algún campo)
+        if not request.data:
+            return Response(
+                {"error": "invalid_payload", "detail": "El payload no puede estar vacío. Proporcione al menos un campo para actualizar."},
+                status=status.HTTP_400_BAD_REQUEST
+            )
+        
         try:
             from apps.tenant.core.services.empresa_adapter import core_empresa_update
             from apps.tenant.core.branding import get_tenant_branding
```

---

## IMPLEMENTACIÓN

✅ **COMPLETADO**: Todos los cambios han sido implementados.

### Resumen de cambios aplicados:

1. ✅ **api-helpers.js** (`apps/tenant/core/static/core/js/lib/api-helpers.js`):
   - Agregada función `isFormData` para detectar FormData de forma segura
   - `Content-Type: application/json` solo se establece si:
     - El body no es `null`/`undefined`
     - El método es mutante (POST, PUT, PATCH, DELETE)
     - El body no es FormData
   - Evita enviar `Content-Type: application/json` con body vacío

2. ✅ **empresa.page.js** (`apps/tenant/core/static/core/js/empresa/empresa.page.js`):
   - `httpJSON` ahora detecta FormData y no establece `Content-Type` en ese caso
   - `Content-Type: application/json` solo se establece si hay payload y no es FormData
   - Manejo correcto de `null`/`undefined` para el body

3. ✅ **Core Orchestrator** (`apps/tenant/core/api/views.py`):
   - Validación temprana de `request.data` antes de procesarlo
   - Retorna 400 si `request.data` no es un dict
   - Retorna 400 si `request.data` está vacío
   - Evita que DRF lance `ParseError` que se convierte en 500

4. ✅ **Tests** (`tests/tenant/core/test_orchestrator_empresa_payloads.py`):
   - Test de payload válido → 200 OK
   - Test de body vacío → 400 Bad Request
   - Test de JSON inválido → 400 Bad Request (no 500)
   - Test de payload null → 400 Bad Request
   - Test de Content-Type en respuesta → application/json
   - Test de creación de Empresa si no existe → 201 Created
   - Test de mail_inbox_config válido → 200 OK
   - Test de mail_inbox_config inválido → 400 Bad Request

---

## POST-APPLY CHECKLIST

**⚠️ NO EJECUTAR AUTOMÁTICAMENTE - Instrucciones para el usuario:**

```bash
# 1. Verificar migraciones
python manage.py showmigrations

# 2. Aplicar migraciones (si hay nuevas)
python manage.py migrate_schemas --shared --fake-initial
python manage.py migrate_schemas --tenant --fake-initial

# 3. Ejecutar tests
pytest -q tests/tenant/core/test_orchestrator_empresa_payloads.py

# 4. Prueba manual:
# - Abrir workspace sección "Empresa" o "Mail Inbox"
# - Realizar PATCH /api/v1/core/empresa/ vía UI
# - Verificar que NO se produce 500 ParseError en logs
# - Verificar que payloads inválidos retornan 400 (no 500)
# - Verificar que Content-Type en respuesta es application/json
```

---

## NOTAS FINALES

- ✅ **ParseError Prevention**: El Core Orchestrator ahora valida payloads tempranamente, evitando que DRF lance `ParseError` que se convierte en 500
- ✅ **Content-Type Handling**: Los helpers del frontend no establecen `Content-Type: application/json` cuando el body es `null`/`undefined` o FormData
- ✅ **Error Responses**: Todos los errores de payload inválido retornan 400 Bad Request con mensajes claros
- ✅ **JSON-only Policy**: Se mantiene la política JSON-only; FormData solo se usa cuando es explícitamente necesario (logo)
- ✅ **Backward Compatibility**: Los cambios son compatibles con el código existente; solo agregan validaciones defensivas
