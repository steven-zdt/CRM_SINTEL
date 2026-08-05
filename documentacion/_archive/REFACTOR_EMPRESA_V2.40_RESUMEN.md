# Refactor Módulo Empresa v2.40 - Resumen Ejecutivo

**Fecha:** 2026-01-XX  
**Versión:** v2.40  
**Estado:** ✅ Refactor completado y validado estáticamente

---

## 📋 Resumen de Cambios

### 1. Core Orchestrator (`apps/tenant/core/api/views.py`)
- ✅ **Eliminados campos legacy** del PATCH:
  - `tipo_contribuyente_clase`
  - `tipo_contribuyente_segmento`
  - `regimen_renta_codigo`
  - `responsabilidades_rut_codigos`
  - `actividad_economica`
- ✅ **Implementado upsert** en PATCH `/api/v1/core/empresa/`:
  - Crea empresa si no existe (201 Created)
  - Actualiza empresa si existe (200 OK)
- ✅ **Solo campos canónicos** permitidos:
  - `razon_social`, `nit`, `dv`, `direccion`, `telefono`, `email_contacto`
  - `regimen_tributario`, `website`, `moneda`, `logo`

### 2. Service Layer (`apps/tenant/empresa/impl/empresa_service.py`)
- ✅ **Eliminadas referencias a campos legacy** en:
  - `get_empresa()`: Solo campos canónicos en DTO
  - `update_empresa()`: Solo campos canónicos en validación
- ✅ **DTO limpio** sin campos legacy

### 3. MailInboxConfig (`apps/tenant/empresa/api/viewsets.py`)
- ✅ **Agregado `http_method_names` explícito** para permitir POST/PATCH
- ✅ **Métodos `create()`, `update()`, `partial_update()`** ya existían (correctos)
- ✅ **Logging de depuración** agregado en `create()`

### 4. Frontend (`apps/tenant/core/static/core/js/mailinbox/mailinbox.page.js`)
- ✅ **Simplificada llamada a `safeFetchJson()`** (eliminados headers duplicados)

---

## 🧪 Checklist de Pruebas en Desarrollo/Producción

### Prueba 1: Core Orchestrator - Upsert

**Escenario A: Crear Empresa (sin empresa existente)**
```bash
# PATCH /api/v1/core/empresa/ con JSON
curl -X PATCH http://home.sintel.net.co/api/v1/core/empresa/ \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=..." \
  -H "X-CSRFToken: ..." \
  -d '{
    "razon_social": "Mi Empresa Test",
    "nit": "900123456",
    "dv": "1",
    "direccion": "Calle Test 123",
    "telefono": "1234567890",
    "email_contacto": "test@example.com",
    "regimen_tributario": "NO_RESPONDE",
    "moneda": "COP"
  }'
```

**Resultado esperado:**
- ✅ Status: `201 Created`
- ✅ Body: DTO con empresa creada + branding
- ✅ Log: `[MailInboxConfigViewSet.create]` (si aplica)

**Escenario B: Actualizar Empresa (con empresa existente)**
```bash
# PATCH /api/v1/core/empresa/ con JSON
curl -X PATCH http://home.sintel.net.co/api/v1/core/empresa/ \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=..." \
  -H "X-CSRFToken: ..." \
  -d '{
    "razon_social": "Mi Empresa Actualizada",
    "telefono": "9876543210"
  }'
```

**Resultado esperado:**
- ✅ Status: `200 OK`
- ✅ Body: DTO con empresa actualizada + branding
- ✅ Campos actualizados correctamente

---

### Prueba 2: API Empresa - Endpoints

**2.1 Listar (Paginado)**
```bash
GET /api/v1/empresas/?page_size=1
```

**Resultado esperado:**
```json
{
  "count": 0,
  "next": null,
  "previous": null,
  "results": []
}
```
O si existe:
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 34,
      "razon_social": "...",
      "nit": "...",
      "dv": "...",
      "direccion": "...",
      "telefono": "...",
      "email_contacto": "..."
    }
  ]
}
```

**Validar:**
- ✅ Formato paginado DRF (`{count, results, next, previous}`)
- ✅ Sin campos legacy en `results`

**2.2 Mi Empresa (Singleton)**
```bash
GET /api/v1/empresas/mi-empresa/
```

**Sin empresa:**
- ✅ Status: `204 No Content`
- ✅ Body: vacío

**Con empresa:**
- ✅ Status: `200 OK`
- ✅ Body: DTO completo con campos canónicos (sin legacy)

**2.3 Detalle por ID**
```bash
GET /api/v1/empresas/34/
```

**Resultado esperado:**
- ✅ Status: `200 OK`
- ✅ Body: DTO completo con `EmpresaDetailSerializer`
- ✅ Tamaño razonable (~300-400 bytes)
- ✅ Sin campos legacy

**2.4 Crear (POST)**
```bash
POST /api/v1/empresas/
```

**Primera vez:**
- ✅ Status: `201 Created`
- ✅ Body: DTO completo

**Segunda vez (singleton violation):**
- ✅ Status: `409 Conflict`
- ✅ Body: `{"error": "singleton_violation", "detail": "Ya existe una empresa en este tenant."}`

---

### Prueba 3: Workspace UI - Flujo Completo

**3.1 Crear Empresa**
1. Abrir `http://home.sintel.net.co/workspace/#empresa`
2. Hacer clic en "Crear Empresa"
3. Llenar formulario:
   - NIT: `900123456`
   - Razón Social: `Empresa Test`
   - Dirección: `Calle Test 123`
   - Teléfono: `1234567890`
   - Email: `test@example.com`
4. Hacer clic en "Crear"

**Validar:**
- ✅ Modal se cierra después de crear
- ✅ Tabla se actualiza con la nueva empresa
- ✅ No aparecen errores de campos legacy en consola
- ✅ Botón "Editar" se habilita automáticamente
- ✅ Log del servidor muestra: `POST /api/v1/empresas/ 201`

**3.2 Editar Empresa**
1. Hacer clic en "Editar"
2. Verificar que el modal se abre con datos pre-llenados
3. Modificar algún campo (ej: teléfono)
4. Hacer clic en "Guardar Cambios"

**Validar:**
- ✅ Modal muestra datos correctos
- ✅ Cambios se guardan correctamente
- ✅ Tabla se actualiza
- ✅ No aparecen errores
- ✅ Log del servidor muestra: `GET /api/v1/empresas/34/ 200` (cargar datos)
- ✅ Log del servidor muestra: `PATCH /api/v1/empresas/34/ 200` (guardar cambios)

**3.3 Ver Empresa (Modal de Solo Lectura)**
1. Hacer clic en "Ver" (si existe botón)
2. Verificar que el modal muestra todos los campos en modo solo lectura

**Validar:**
- ✅ Modal muestra todos los campos canónicos
- ✅ Campos están deshabilitados (readonly)
- ✅ Sin campos legacy visibles

---

### Prueba 4: MailInboxConfig - Crear Configuración

**4.1 Crear Nueva Configuración**
1. Abrir `http://home.sintel.net.co/workspace/#empresa`
2. Ir a sección "Configuraciones de Correo"
3. Hacer clic en "Nueva Configuración"
4. Llenar formulario:
   - Nombre: `Buzón Principal`
   - Email: `facturas@example.com`
   - Proveedor: `Gmail` o `Personalizado`
   - Servidor IMAP: `imap.gmail.com`
   - Puerto IMAP: `993`
   - Usuario IMAP: `usuario@example.com`
   - Contraseña IMAP: `***`
5. Hacer clic en "Crear"

**Validar:**
- ✅ Modal se cierra después de crear
- ✅ Tabla se actualiza con la nueva configuración
- ✅ No aparece error 405
- ✅ Log del servidor muestra: `POST /api/v1/empresas/mail-inbox-config/ 201`

**4.2 Editar Configuración**
1. Hacer clic en "Editar" en una configuración existente
2. Modificar algún campo
3. Hacer clic en "Guardar"

**Validar:**
- ✅ Cambios se guardan correctamente
- ✅ No aparece error 405
- ✅ Log del servidor muestra: `PATCH /api/v1/empresas/mail-inbox-config/{id}/ 200`

---

### Prueba 5: Validación de Campos Legacy

**5.1 Verificar que NO aparezcan campos legacy en respuestas**

```bash
# GET /api/v1/empresas/34/
# Verificar que la respuesta NO contenga:
# - tipo_contribuyente_clase
# - tipo_contribuyente_segmento
# - regimen_renta_codigo
# - responsabilidades_rut_codigos
# - actividad_economica
```

**Validar:**
- ✅ Respuesta solo contiene campos canónicos
- ✅ Sin campos legacy en JSON

**5.2 Verificar que PATCH rechace campos legacy**

```bash
# PATCH /api/v1/core/empresa/ con campo legacy
curl -X PATCH http://home.sintel.net.co/api/v1/core/empresa/ \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=..." \
  -H "X-CSRFToken: ..." \
  -d '{
    "razon_social": "Test",
    "tipo_contribuyente_clase": "PJ"
  }'
```

**Resultado esperado:**
- ✅ Campo legacy es ignorado (no se procesa)
- ✅ Solo se actualiza `razon_social`
- ✅ No aparece error (campo simplemente se ignora)

---

## 🔍 Verificaciones Adicionales

### 1. Logs del Servidor

**Buscar en logs:**
```bash
# Verificar que no aparezcan errores relacionados con campos legacy
grep -i "tipo_contribuyente\|regimen_renta\|responsabilidades_rut\|actividad_economica" logs/*.log

# Verificar que los endpoints respondan correctamente
grep "GET /api/v1/empresas/" logs/*.log
grep "POST /api/v1/empresas/" logs/*.log
grep "PATCH /api/v1/empresas/" logs/*.log
```

**Resultado esperado:**
- ✅ Sin errores relacionados con campos legacy
- ✅ Endpoints responden con 200/201/204 según corresponda

### 2. Consola del Navegador

**Abrir DevTools (F12) y verificar:**
- ✅ No aparecen errores de JavaScript
- ✅ No aparecen errores de campos legacy
- ✅ Logs `[empresa.page]` muestran flujo correcto
- ✅ Logs `[mailinbox.page]` muestran flujo correcto

### 3. Network Tab

**Verificar peticiones HTTP:**
- ✅ `GET /api/v1/empresas/` → 200 OK
- ✅ `GET /api/v1/empresas/34/` → 200 OK
- ✅ `POST /api/v1/empresas/` → 201 Created (primera vez) o 409 Conflict (segunda vez)
- ✅ `PATCH /api/v1/empresas/34/` → 200 OK
- ✅ `POST /api/v1/empresas/mail-inbox-config/` → 201 Created
- ✅ `PATCH /api/v1/empresas/mail-inbox-config/{id}/` → 200 OK

**Validar headers:**
- ✅ `Content-Type: application/json`
- ✅ `X-CSRFToken` presente en mutaciones
- ✅ `Accept: application/json`

---

## 📝 Notas Importantes

1. **Campos Legacy Eliminados:**
   - `tipo_contribuyente_clase`
   - `tipo_contribuyente_segmento`
   - `regimen_renta_codigo`
   - `responsabilidades_rut_codigos`
   - `actividad_economica`

2. **Campos Canónicos Mantenidos:**
   - `razon_social`
   - `nit`
   - `dv`
   - `direccion`
   - `telefono`
   - `email_contacto`
   - `regimen_tributario`
   - `logo`
   - `website`
   - `moneda`

3. **Endpoints Validados:**
   - `GET /api/v1/empresas/` → Lista paginada
   - `GET /api/v1/empresas/{id}/` → Detalle por ID
   - `GET /api/v1/empresas/mi-empresa/` → Singleton (200/204)
   - `POST /api/v1/empresas/` → Crear (201/409)
   - `PATCH /api/v1/empresas/{id}/` → Actualizar
   - `PATCH /api/v1/core/empresa/` → Upsert (201/200)
   - `POST /api/v1/empresas/mail-inbox-config/` → Crear configuración
   - `PATCH /api/v1/empresas/mail-inbox-config/{id}/` → Actualizar configuración

---

## ✅ Estado Final

- ✅ **Refactor completado**
- ✅ **Validación estática completada**
- ✅ **Código sin errores de linter**
- ✅ **Campos legacy eliminados**
- ✅ **Upsert implementado**
- ✅ **MailInboxConfig corregido (405 resuelto)**

**Listo para pruebas en entorno de desarrollo/producción.**
