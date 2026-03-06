# Auditoría: Mail Inbox Config → Core Orchestrator v2.40

**Fecha:** 2026-01-XX  
**Versión:** v2.40  
**Estado:** ✅ Auditoría completada

---

## AUDIT SUMMARY

### A) Modelo Empresa
- ✓ **OK**: `Empresa` no tiene campo `mail_inbox_config` (JSONField)
- ✎ **CAMBIO**: No se requiere agregar campo JSON a `Empresa` porque `MailInboxConfig` es un modelo separado
- ✓ **OK**: `MailInboxConfig` es modelo independiente (sin FK a `Empresa`)

### B) Serializer EmpresaUpsertSerializer
- ✎ **CAMBIO**: Agregar soporte para aceptar `mail_inbox_config` como objeto anidado opcional
- ✎ **CAMBIO**: Validar estructura de `mail_inbox_config` si está presente
- ✓ **OK**: Password ya es `write_only` en `MailInboxConfigDetailSerializer`

### C) Core Orchestrator (MiEmpresaView.patch)
- ✎ **CAMBIO**: Agregar lógica para detectar `mail_inbox_config` en `request.data`
- ✎ **CAMBIO**: Si existe `mail_inbox_config`, usar `core_mailbox_create` o `core_mailbox_update`
- ✓ **OK**: Ya soporta upsert (create si no existe, update si existe)

### D) Ruta Legacy
- ✎ **CAMBIO**: Agregar `@action` en `MailInboxConfigViewSet` para deprecar POST con 405

### E) Frontend (mailinbox.page.js)
- ✎ **CAMBIO**: Reemplazar `POST /api/v1/empresas/mail-inbox-config/` por `PATCH /api/v1/core/empresa/`
- ✎ **CAMBIO**: Envolver payload en `{ mail_inbox_config: {...} }`
- ✓ **OK**: `safeFetchJson` ya maneja CSRF y JSON correctamente

### F) Tests
- ✎ **CAMBIO**: Crear `tests/tenant/core/test_orchestrator_mail_inbox.py`

---

## DIFFS

### D.1) Actualizar Core Orchestrator para aceptar mail_inbox_config

```diff
--- a/apps/tenant/core/api/views.py
+++ b/apps/tenant/core/api/views.py
@@ -302,6 +302,7 @@ class MiEmpresaView(APIView):
             # Extraer campos editables del request.data (solo campos canónicos)
             campos_editables = [
                 'razon_social', 'nit', 'dv', 'direccion', 'telefono', 'email_contacto',
                 'regimen_tributario', 'website', 'moneda'
             ]
             for campo in campos_editables:
                 if campo in request.data:
                     data[campo] = request.data[campo]
+            
+            # ⚠️ v2.40: Soporte para mail_inbox_config a través del orchestrator
+            mail_inbox_config_data = None
+            if 'mail_inbox_config' in request.data:
+                mail_inbox_config_data = request.data['mail_inbox_config']
+                if not isinstance(mail_inbox_config_data, dict):
+                    return Response(
+                        {"error": "mail_inbox_config debe ser un objeto JSON válido."},
+                        status=status.HTTP_400_BAD_REQUEST
+                    )
             
             # Extraer archivos si hay multipart
             if request.FILES and 'logo' in request.FILES:
@@ -329,6 +340,30 @@ class MiEmpresaView(APIView):
                 empresa_dto = core_empresa_update(data, files=files)
                 status_code = status.HTTP_200_OK
             
+            # ⚠️ v2.40: Procesar mail_inbox_config si está presente
+            if mail_inbox_config_data:
+                from apps.tenant.core.services.empresa_adapter import (
+                    core_mailbox_create,
+                    core_mailbox_update
+                )
+                from apps.tenant.empresa.models import MailInboxConfig
+                
+                # Determinar si es creación o actualización
+                config_id = mail_inbox_config_data.get('id')
+                if config_id:
+                    # Actualizar configuración existente
+                    try:
+                        mailbox_dto = core_mailbox_update(config_id, mail_inbox_config_data)
+                        empresa_dto['mail_inbox_config'] = mailbox_dto
+                    except MailInboxConfig.DoesNotExist:
+                        return Response(
+                            {"error": f"Configuración de buzón con ID {config_id} no encontrada."},
+                            status=status.HTTP_404_NOT_FOUND
+                        )
+                else:
+                    # Crear nueva configuración
+                    mailbox_dto = core_mailbox_create(mail_inbox_config_data)
+                    empresa_dto['mail_inbox_config'] = mailbox_dto
+            
             # Construir URL absoluta del logo si existe
             if empresa_dto.get('logo') and not empresa_dto.get('logo_url'):
```

### D.2) Actualizar mailinbox.page.js para usar Core Orchestrator

```diff
--- a/apps/tenant/core/static/core/js/mailinbox/mailinbox.page.js
+++ b/apps/tenant/core/static/core/js/mailinbox/mailinbox.page.js
@@ -510,24 +510,30 @@
   async function handleGuardarMailInbox() {
     try {
       // Recolectar datos del formulario
       const payload = collectMailInboxPayload();
       log('Payload recolectado:', { ...payload, imap_password: '***' });
 
-      // Determinar método y URL según existencia
+      // ⚠️ v2.40: Usar Core Orchestrator en lugar de endpoint directo
       const idEl = d.getElementById('mailinbox-id');
       const configId = idEl?.value ? parseInt(idEl.value) : null;
       const exists = configId !== null && !isNaN(configId);
-      const method = exists ? 'PATCH' : 'POST';
-      const API_BASE = '/api/v1/empresas/mail-inbox-config/';
-      const url = exists ? `${API_BASE}${configId}/` : API_BASE;
+      
+      // Envolver payload en mail_inbox_config para el orchestrator
+      const orchestratorPayload = {
+        mail_inbox_config: {
+          ...payload,
+          ...(exists ? { id: configId } : {})
+        }
+      };
+      
+      const url = '/api/v1/core/empresa/';
 
-      log(`${exists ? 'Actualizando' : 'Creando'} configuración con ${method} a ${url}`);
+      log(`${exists ? 'Actualizando' : 'Creando'} configuración vía Core Orchestrator: ${url}`);
 
       // Mostrar feedback de carga
       const feedback = d.getElementById('mailinbox-form-feedback');
       if (feedback) {
         feedback.className = 'alert alert-info';
         feedback.textContent = `${exists ? 'Actualizando' : 'Creando'} configuración...`;
         feedback.classList.remove('d-none');
       }
 
       // Realizar petición
-      // ⚠️ IMPORTANTE: safeFetchJson maneja automáticamente Content-Type y X-CSRFToken
-      // ⚠️ CRÍTICO: No pasar headers duplicados, safeFetchJson ya los maneja
-      const data = await w.API_HELPERS.safeFetchJson(url, {
-        method: method,
-        body: JSON.stringify(payload)
+      const data = await w.API_HELPERS.safeFetchJson(url, {
+        method: 'PATCH',
+        body: orchestratorPayload
       });
 
       log('Configuración guardada:', data);
+      
+      // Extraer mail_inbox_config de la respuesta si está presente
+      const mailboxData = data.mail_inbox_config || data;
```

### D.3) Deprecar ruta legacy con 405

```diff
--- a/apps/tenant/empresa/api/viewsets.py
+++ b/apps/tenant/empresa/api/viewsets.py
@@ -530,6 +530,25 @@ class MailInboxConfigViewSet(viewsets.ModelViewSet):
         return MailInboxConfigDetailSerializer
     
+    @action(detail=False, methods=["post"], url_path="deprecated-create")
+    def deprecated_create(self, request: Request, *args, **kwargs) -> Response:
+        """
+        ⚠️ DEPRECATED v2.40: Esta ruta está deprecada.
+        
+        Usa PATCH /api/v1/core/empresa/ con mail_inbox_config en el payload.
+        
+        Returns:
+            405 Method Not Allowed con mensaje claro
+        """
+        return Response(
+            {
+                "error": "deprecated_route",
+                "detail": "Esta ruta está deprecada. Usa PATCH /api/v1/core/empresa/ con 'mail_inbox_config' en el payload para crear/actualizar configuraciones de buzón."
+            },
+            status=status.HTTP_405_METHOD_NOT_ALLOWED
+        )
+    
     def get_queryset(self):
```

---

## IMPLEMENTACIÓN

Voy a implementar los cambios necesarios:
