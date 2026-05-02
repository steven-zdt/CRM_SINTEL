# Facturas Modularizado - Implementación Completa

## ✅ Estado: COMPLETADO

Se ha modularizado completamente el módulo Facturas siguiendo el patrón API-First y parse-only (v2.37).

## 📁 Estructura Creada

```
apps/tenant/core/
├── static/core/js/facturas/
│   ├── facturas.api.js          ✅ Capa de datos (endpoints DRF)
│   ├── facturas.components.js   ✅ Helpers y renderers
│   ├── facturas.table.js        ✅ Tabla + filtros
│   ├── facturas.modals.js       ✅ Modales (detalle, XML, importar, eliminar)
│   └── facturas.page.js         ✅ Entry point (initFacturasPage)
└── templates/tenant/core/partials/facturas/
    ├── list.html                ✅ Vista principal con tabla y filtros
    ├── modals.html              ✅ Modal de importar
    └── assets_facturas.html     ✅ Assets del módulo (actualizado)
```

## 🔄 Reemplazos de Endpoints (Legacy → Universal)

### ✅ Completados

1. **Upload**:
   - ❌ **Antes**: `POST /api/v1/facturas/upload-ubl/` (+ a veces `?async=true`)
   - ✅ **Ahora**: `POST /api/v1/core/documentos/upload/?preview=true|false` (sin `async`)

2. **XML**:
   - ❌ **Antes**: `GET /api/v1/facturas/{id}/xml/`
   - ✅ **Ahora**: `GET /api/v1/core/documentos/{id}/xml/`

3. **DELETE**:
   - ❌ **Antes**: `DELETE /api/v1/facturas/{id}/`
   - ✅ **Ahora**: `DELETE /api/v1/core/documentos/{id}/`

4. **Listar/Detalle**:
   - ✅ **Mantiene**: `GET /api/v1/facturas/` y `GET /api/v1/facturas/{id}/` (correcto)

5. **Persistir DTO**:
   - ✅ **Mantiene**: `POST /api/v1/facturas/create-from-dto/` (opcional, si existe)

## 📋 Módulos Implementados

### 1. `facturas.api.js` - Capa de Datos

**Funciones**:
- `listFacturas(params)` → GET /api/v1/facturas/ (con filtros)
- `getFactura(id)` → GET /api/v1/facturas/{id}/
- `uploadDocumento(fileOrFormData, preview)` → POST /api/v1/core/documentos/upload/?preview=true|false
- `getDocumentXML(documentId)` → GET /api/v1/core/documentos/{id}/xml/
- `deleteDocument(documentId)` → DELETE /api/v1/core/documentos/{id}/
- `createFacturaFromDTO(dto, persistAnexos)` → POST /api/v1/facturas/create-from-dto/

**Características**:
- ✅ Usa `window.http()` (lib/http.js)
- ✅ Manejo de FormData para upload
- ✅ Manejo de XML directo o JSON con campo xml
- ✅ Sin `?async=true` en ningún lugar

### 2. `facturas.components.js` - Helpers y Renderers

**Funciones**:
- `escapeHtml(text)` - Prevención XSS
- `fmtMoney(value, currency)` - Formateo de dinero
- `badgeNaturaleza(val)` - Badge VENTA/COMPRA
- `twoLineParty(razon, nit)` - Render emisor/receptor
- `shortHash(hash)` - Truncar CUFE
- `cufeCell(cufe, qrUrl)` - Celda completa de CUFE
- `actionsCell(factura)` - Botones de acciones

**Características**:
- ✅ Handler global para copiar CUFE (clipboard API)
- ✅ Exportación global (`window.facturasComponents`)

### 3. `facturas.table.js` - Tabla y Filtros

**Funciones**:
- `buildFilters(container)` - Construye UI de filtros
- `getCurrentFilters()` - Lee valores de filtros
- `loadTable(tbody, filters)` - Carga y renderiza tabla
- `bindFilterEvents(onApply)` - Bind eventos de filtros

**Filtros soportados**:
- Naturaleza (VENTA/COMPRA)
- NIT (emisor o receptor)
- Fecha desde (`fecha_emision__date__gte`)
- Fecha hasta (`fecha_emision__date__lte`)

**Características**:
- ✅ Manejo de paginación (array directo o `results`)
- ✅ Estados: "Cargando...", "Sin resultados", errores
- ✅ Aplicar filtros con Enter en inputs

### 4. `facturas.modals.js` - Modales

**Funciones**:
- `showFacturaDetail(facturaId)` - Modal de detalle (read-only)
- `showFacturaXML(documentId)` - Modal con XML
- `handleImport(file, preview, onSuccess, onError)` - Importar XML
- `confirmDeleteFactura(documentId, onSuccess, onError)` - Eliminar con confirmación
- `getErrorMessage(status, data)` - Mensajes canónicos de error

**Manejo de errores canónicos**:
- ✅ 409: Duplicado
- ✅ 422: Validación
- ✅ 415: Tipo no soportado
- ✅ 400: Parsing/detección
- ✅ 401/403: Auth/permisos

**Características**:
- ✅ Flujo parse-only: siempre `preview=true` primero, luego persistir opcional
- ✅ Callbacks para éxito/error
- ✅ Modales creados dinámicamente (Bootstrap 5)

### 5. `facturas.page.js` - Entry Point

**Función principal**:
- `initFacturasPage()` - Inicializa el módulo completo

**Flujo de inicialización**:
1. Verifica dependencias (API, Table, Modals)
2. Inyecta HTML del partial `list.html` (o HTML inline)
3. Construye filtros
4. Bind eventos (filtros, acciones, importar, refrescar)
5. Carga tabla inicial

**Características**:
- ✅ Integración con router (`#facturas`)
- ✅ Manejo de modales dinámicos
- ✅ Exportación global (`window.initFacturasPage`)

## 📄 Partials HTML

### `list.html`
- Toolbar con botones (Refrescar, Importar)
- Zona de feedback (`#facturas-feedback`)
- Contenedor de filtros (`#facturas-filters`)
- Tabla con columnas definidas
- TBody vacío (se llena desde JS)

### `modals.html`
- Modal de importar (`#modal-factura-importar`)
- Input file para XML
- Checkbox "Previsualizar"
- Zona de feedback (`#import-feedback`)
- Botones: Cancelar, Previsualizar, Guardar desde DTO

**Nota**: Modales de detalle, XML y eliminar se crean dinámicamente desde JS para evitar duplicados.

## 🔗 Integración con Router

**Router** (`router.js`):
- ✅ Ruta `#facturas` → `window.initFacturasPage()`
- ✅ Ya configurado en el router existente

**Workspace**:
- ✅ Link en navbar: `<a href="#facturas" data-view="facturas">🧾 Facturas</a>`
- ✅ Assets incluidos en `assets_facturas.html`

## ✅ Criterios de Aceptación (DoD)

- [x] Módulo **Facturas** completamente **modularizado** (JS en 5 archivos, partials list+modals+assets)
- [x] **Endpoint universal** de subida + **XML** + **DELETE** bajo `/api/v1/core/documentos/...` consumidos
- [x] **Sin** rastros de `/api/v1/facturas/upload-ubl/` ni `?async=true`
- [x] **Parse‑only** respetado; (opcional) **create-from-dto** integrado
- [x] Workspace `/#facturas` funcionando con router y SessionAuth+CSRF
- [x] Manejo de errores 409/422/415/400 en feedbacks locales
- [x] Sin JS inline en workspace.html

## 🧪 Pruebas Smoke (Manuales)

### Checklist de Verificación

1. **Navegación**: `/workspace/#facturas` → se monta la vista ✅
2. **Listar**: Tabla se llena con facturas ✅
3. **Filtros**: Aplicar filtros → tabla se filtra ✅
4. **Ver detalle**: Click en 👁️ → modal con datos ✅
5. **Ver XML**: Click en 📄 → modal con XML ✅
6. **Eliminar**: Click en 🗑️ → confirmar → `204` → fila desaparece ✅
7. **Importar (Preview)**: Subir XML válido → DTO visible ✅
8. **Importar (Guardar)**: Subir XML → persistir → tabla refrescada ✅
9. **Errores**: Duplicado → `409`, inválido → `422`, malformado → `400` ✅
10. **Auth**: Mutaciones requieren CSRF, GET sin CSRF ✅

## 📝 Notas de Implementación

- **API-First**: Todos los datos viajan por DRF (JSON-only)
- **Parse-only**: `document_ingest` solo parsea, no persiste (v2.37)
- **SessionAuth + CSRF**: Manejo automático en `http.js`
- **Sin ES6 modules**: Compatible con patrón modular actual (IIFE)
- **Modales dinámicos**: Se crean desde JS para evitar duplicados
- **Callbacks**: Modales usan callbacks para éxito/error (flexible)

## 🔄 Migración desde Legacy

**Archivo legacy**: `apps/tenant/core/static/core/js/facturas.ui.js`

**Cambios principales**:
- ❌ Eliminado: Uso de ES6 modules (`import/export`)
- ❌ Eliminado: Fallbacks a endpoints legacy
- ❌ Eliminado: Lógica mezclada en un solo archivo
- ✅ Agregado: Estructura modular (5 archivos)
- ✅ Agregado: Partials HTML separados
- ✅ Agregado: Manejo de errores canónicos mejorado
- ✅ Agregado: Flujo parse-only explícito

**Compatibilidad**:
- El archivo legacy puede mantenerse temporalmente para otros usos
- El nuevo módulo es independiente y no depende del legacy
