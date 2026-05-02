# Reporte de Alineación de Endpoints

## Resumen

Este documento lista los reemplazos de endpoints legacy por endpoints universales (parse-only) y endpoints específicos de cada app, siguiendo la arquitectura API-First y el principio parse-only del pipeline universal.

---

## Endpoints Universales (Parse-Only)

### Upload (Parse-Only)
**Endpoint**: `POST /api/v1/core/documentos/upload/?preview=true|false`

**Parámetros**:
- `preview=true` → Solo parsea y devuelve DTO (no persiste)
- `preview=false` → Parse-only también (no persiste, solo retorna DTO)
- `tipo=<app>` → Opcional, para apps que consumen el pipeline (ej: `?tipo=gasto&preview=true`)

**Body**: `FormData` con `file=<archivo>`

**Respuesta**: `{ dto: {...}, document_type: "...", ... }`

**Reemplazos**:
- ❌ `POST /api/v1/facturas/upload-ubl/` → ✅ `POST /api/v1/core/documentos/upload/?preview=true`
- ❌ `POST /api/v1/facturas/importar-ubl/` → ✅ `POST /api/v1/core/documentos/upload/?preview=true` + `POST /api/v1/facturas/create-from-dto/`
- ❌ `POST /api/v1/gastos/upload/` → ✅ `POST /api/v1/core/documentos/upload/?tipo=gasto&preview=true`
- ❌ `POST /api/v1/inventario/upload/` → ✅ `POST /api/v1/core/documentos/upload/?tipo=inventario&preview=true` (si aplica)

### XML
**Endpoint**: `GET /api/v1/core/documentos/{id}/xml/`

**Respuesta**: `{ xml: "<xml>..." }` o texto plano

**Reemplazos**:
- ❌ `GET /api/v1/facturas/{id}/xml/` → ✅ `GET /api/v1/core/documentos/{id}/xml/`

### DELETE Documento
**Endpoint**: `DELETE /api/v1/core/documentos/{id}/`

**Respuesta**: `204 No Content` o `200 OK`

**Reemplazos**:
- ❌ `DELETE /api/v1/facturas/{id}/` (solo para documentos) → ✅ `DELETE /api/v1/core/documentos/{id}/`

---

## Endpoints Específicos de Apps (Persistencia)

### Facturas
- ✅ `POST /api/v1/facturas/create-from-dto/` — Materializa DTO en Factura/NotaCredito
- ✅ `GET /api/v1/facturas/` — Lista facturas
- ✅ `GET /api/v1/facturas/{id}/` — Detalle de factura
- ✅ `DELETE /api/v1/facturas/{id}/` — Elimina factura (si aplica, fuera del pipeline universal)

### Gastos
- ✅ `POST /api/v1/gastos/create-from-dto/` — Materializa DTO en Gasto
- ✅ `GET /api/v1/gastos/` — Lista gastos
- ✅ `POST /api/v1/gastos/` — Crea gasto manual
- ✅ `GET /api/v1/gastos/{id}/` — Detalle de gasto
- ✅ `PATCH /api/v1/gastos/{id}/` — Actualiza gasto
- ✅ `DELETE /api/v1/gastos/{id}/` — Elimina gasto

### Inventario
- ✅ `POST /api/v1/core/inventario/entrada/` — Entrada de inventario
- ✅ `GET /api/v1/core/inventario/catalogo/` — Catálogo
- ✅ `GET /api/v1/core/inventario/resumen/` — Resumen
- ✅ `POST /api/v1/inventario/create-from-dto/` — Materializa DTO (si aplica)

### Empresa
- ✅ `GET /api/v1/core/empresa/` — Mi empresa (singleton)
- ✅ `PATCH /api/v1/core/empresa/` — Actualiza mi empresa
- ✅ `GET /api/v1/empresas/` — Lista empresas (singleton: 0-1)
- ✅ `POST /api/v1/empresas/` — Crea empresa
- ✅ `GET /api/v1/empresas/{id}/` — Detalle de empresa
- ✅ `DELETE /api/v1/empresas/{id}/` — Elimina empresa

### Proveedores
- ✅ `GET /api/v1/proveedores/` — Lista proveedores
- ✅ `POST /api/v1/proveedores/` — Crea proveedor
- ✅ `GET /api/v1/proveedores/{id}/` — Detalle de proveedor
- ✅ `PATCH /api/v1/proveedores/{id}/` — Actualiza proveedor
- ✅ `DELETE /api/v1/proveedores/{id}/` — Elimina proveedor

### Empleados
- ✅ `GET /api/v1/empleados/` — Lista empleados
- ✅ `POST /api/v1/empleados/` — Crea empleado
- ✅ `GET /api/v1/empleados/{id}/` — Detalle de empleado
- ✅ `PATCH /api/v1/empleados/{id}/` — Actualiza empleado
- ✅ `DELETE /api/v1/empleados/{id}/` — Elimina empleado

### Contabilidad
- ✅ `GET /api/v1/contabilidad/` — Lista (endpoints específicos según sub-módulos)
- ✅ `POST /api/v1/contabilidad/` — Crea (endpoints específicos según sub-módulos)
- ✅ `GET /api/v1/contabilidad/{id}/` — Detalle
- ✅ `PATCH /api/v1/contabilidad/{id}/` — Actualiza
- ✅ `DELETE /api/v1/contabilidad/{id}/` — Elimina

### Perfil
- ✅ `GET /api/v1/core/perfil/me/` — Mi perfil
- ✅ `PATCH /api/v1/core/perfil/me/` — Actualiza mi perfil

### MailDigester
- ✅ `POST /api/v1/core/maildigester/run/` — Inicia ingesta
- ✅ `GET /api/v1/core/maildigester/runs/` — Lista ejecuciones
- ✅ `GET /api/v1/core/maildigester/run/{id}/details/` — Detalles de ejecución
- ✅ `POST /api/v1/core/maildigester/run/{id}/stop/` — Detiene ejecución
- ✅ `DELETE /api/v1/core/maildigester/run/{id}/` — Elimina ejecución

---

## Endpoints Legacy Eliminados

### Facturas
- ❌ `POST /api/v1/facturas/upload-ubl/` — Reemplazado por universal
- ❌ `POST /api/v1/facturas/importar-ubl/` — Reemplazado por universal + create-from-dto
- ❌ `GET /api/v1/facturas/{id}/xml/` — Reemplazado por universal
- ❌ `POST /api/v1/facturas/materialize/` — DEPRECATED (usar create-from-dto)

### Otros
- ❌ `POST /api/v1/gastos/upload/` — Reemplazado por universal (si existía)
- ❌ `POST /api/v1/inventario/upload/` — Reemplazado por universal (si existía)

---

## Flujo Parse-Only (Dos Pasos)

### Paso 1: Parsear (Universal)
```
POST /api/v1/core/documentos/upload/?preview=true
Body: FormData(file=<archivo>)
→ Respuesta: { dto: {...}, document_type: "...", ... }
```

### Paso 2: Persistir (App-Specific)
```
POST /api/v1/<app>/create-from-dto/
Body: { dto: {...}, persist_anexos: true }
→ Respuesta: { id: ..., ... } (objeto materializado)
```

**Apps con este flujo**:
- ✅ Facturas: `POST /api/v1/facturas/create-from-dto/`
- ✅ Gastos: `POST /api/v1/gastos/create-from-dto/`
- ✅ Inventario: `POST /api/v1/inventario/create-from-dto/` (si aplica)

---

## Verificación de Alineación

### JavaScript (Frontend)
- [x] `facturas.api.js` — Usa endpoints universales
- [x] `gastos.api.js` — Usa endpoints universales
- [ ] `inventario.api.js` — Verificar si usa endpoints universales
- [ ] Otros `<app>.api.js` — Verificar que no usen endpoints legacy

### Búsqueda de Referencias Legacy
```bash
# Buscar referencias a endpoints legacy
grep -r "upload-ubl" apps/tenant/core/static/core/js/
grep -r "importar-ubl" apps/tenant/core/static/core/js/
grep -r "/api/v1/facturas/upload" apps/tenant/core/static/core/js/
grep -r "?async=true" apps/tenant/core/static/core/js/
```

---

## Principios de Alineación

### 1. Parse-Only Universal
- ✅ `document_ingest` **solo parsea** (devuelve DTO)
- ✅ **No persiste** datos directamente
- ✅ Endpoint universal: `/api/v1/core/documentos/upload/`

### 2. Persistencia por App
- ✅ Cada app persiste con su **service layer**
- ✅ Endpoints específicos: `/api/v1/<app>/create-from-dto/` (donde aplique)
- ✅ CRUD estándar: `/api/v1/<app>/` (GET, POST, PATCH, DELETE)

### 3. API-First
- ✅ Backend no renderiza datos (solo JSON)
- ✅ UI consume DRF APIs exclusivamente
- ✅ SessionAuth + CSRF en mutaciones

### 4. Multi-tenant
- ✅ Todas las llamadas API son tenant-aware (schema context)
- ✅ CSRF y SessionAuth garantizan aislamiento

---

**Última actualización**: 2024-12-19  
**Versión**: 1.0
