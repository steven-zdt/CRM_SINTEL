# 📋 Informe de Estructura - Módulo Empresa JavaScript

**Fecha:** 2024-12-19  
**Versión:** v2.40 (Alineado a Campos Canónicos)  
**Directorio:** `apps/tenant/core/static/core/js/empresa/`  
**Estado:** ✅ **ALINEADO CON BACKEND**

---

## 📊 Resumen Ejecutivo

| Archivo | Estado | Líneas | Propósito | Uso Actual |
|---------|--------|--------|-----------|------------|
| `empresa.page.js` | ✅ Activo | ~1,378 | Módulo principal completo | ✅ En producción |
| `empresa.api.js` | ⚠️ Legacy | 120 | API wrapper (legacy) | ❌ No se carga |
| `empresa.modals.js` | ⚠️ Legacy | 393 | Modales (legacy) | ❌ No se carga |
| `empresa.ui.js` | ⚠️ Legacy | 339 | UI helpers (legacy) | ❌ No se carga |

**Estado General:** ✅ **ALINEADO Y FUNCIONAL**

---

## 📁 Estructura de Archivos

```
apps/tenant/core/static/core/js/empresa/
├── empresa.page.js          ✅ Módulo principal (activo)
├── empresa.api.js           ⚠️ Legacy (no se carga)
├── empresa.modals.js        ⚠️ Legacy (no se carga)
├── empresa.ui.js            ⚠️ Legacy (no se carga)
└── INFORME_ESTRUCTURA.md     📋 Este documento
```

---

## 🎯 Archivo Principal: `empresa.page.js`

### Propósito
Módulo completo que maneja toda la funcionalidad del módulo Empresa en el workspace:
- Inicialización y estado del módulo
- Fetching de datos desde API
- Renderizado de DataTables
- Manejo de modales (Ver, Editar, Crear)
- Validación y envío de formularios
- Manejo de errores y feedback

### Arquitectura

#### Patrón de Diseño
- **IIFE (Immediately Invoked Function Expression)**: Encapsula el código
- **Estado del módulo**: Objeto `state` para tracking de inicialización
- **Helpers globales**: Depende de `w.API_HELPERS`, `w.Routes`, `w.CRUD`, `w.DOMUtils`, `w.DataTablesUtils`

#### Campos Canónicos (v2.40)
El módulo está alineado con los campos canónicos del modelo `Empresa`:

**LIST_FIELDS (para listado):**
- `id`
- `razon_social`
- `nit`
- `dv`
- `direccion`
- `telefono`
- `email_contacto`
- `regimen_tributario`
- `moneda`
- `created_at`
- `updated_at`

**DETAIL_FIELDS (para detalle):**
- Todos los campos de LIST_FIELDS +
- `logo` (URL absoluta)
- `website`

**Campos Eliminados (obsoletos):**
- ❌ `tipo_contribuyente_clase`
- ❌ `tipo_contribuyente_segmento`
- ❌ `regimen_renta_codigo` (reemplazado por `regimen_tributario`)
- ❌ `responsabilidades_rut_codigos`
- ❌ `actividad_economica`

### Funciones Principales

#### 1. Helpers de Utilidad
```javascript
computeNitCompleto(row)          // Calcula "nit-dv" o "nit"
parseNitToNitAndDv(raw)          // Parsea NIT con/sin DV
renderRegimenBadge(code)         // Renderiza badge de régimen
formatDateTime(isoStr)           // Formatea fecha/hora
getEl(id)                        // Helper para getElementById
getValueOrNull(id)               // Obtiene valor o null
```

#### 2. Helpers HTTP
```javascript
httpJSON(method, url, payloadOrNull)  // Helper robusto para fetch JSON
  - Headers: Accept, Content-Type, X-CSRFToken
  - credentials: "same-origin"
  - Manejo robusto de Content-Type (JSON vs HTML)
  - Retorna: { ok, status, headers, data }
```

#### 3. Normalización de Datos
```javascript
normalizeEmpresaListPayload(payload)  // Extrae 'results' de paginación DRF
collectEmpresaPayload(formId)         // Recolecta datos del formulario (solo campos canónicos)
collectCreatePayload()                // Recolecta datos del modal crear
```

#### 4. Fetching de Datos
```javascript
fetchEmpresaList()      // GET /api/v1/empresas/ (paginado)
fetchEmpresaDetail(id)  // GET /api/v1/empresas/{id}/ o singleton
loadEmpresa()           // Carga empresa singleton al iniciar
```

#### 5. Handlers de UI
```javascript
handleVerEmpresa(id)        // Abre modal de visualización
handleEditarEmpresa(id)     // Abre modal de edición
handleGuardarEmpresa(ev)    // Guarda cambios (PATCH singleton)
handleCrearEmpresa(ev)      // Crea empresa (PATCH singleton con verificación)
```

#### 6. Helpers de UI
```javascript
showEmpresaError(msg)           // Muestra error en #empresa-feedback
showEmpresaSuccess(msg)          // Muestra éxito (toast)
closeEmpresaModalIfOpen()        // Cierra modales abiertos
refreshEmpresaPanel()            // Refresca DataTable
renderFieldErrors(errors, formId) // Renderiza errores de validación
limpiarModales()                 // Limpia campos de modales
```

#### 7. DataTables
```javascript
initDataTableEmpresa()  // Inicializa DataTable con columnas canónicas
```

**Columnas DataTables (alineadas a LIST_FIELDS):**
1. NIT (calculado: `nit-dv`)
2. Razón Social
3. Dirección
4. Teléfono
5. Email
6. Régimen Tributario (badge)
7. Moneda
8. Actualizado (fecha/hora)
9. Acciones (Ver, Editar)

### Flujo de Datos

#### Crear Empresa
1. Usuario completa formulario en modal `#modal-crear-empresa`
2. `handleCrearEmpresa()` recolecta datos con `collectCreatePayload()`
3. Verifica existencia: `GET /api/v1/empresas/?page_size=1`
4. Si no existe: `PATCH /api/v1/core/empresa/` (upsert)
5. Si 405: Lee `Allow` header o `OPTIONS`, retry con `PUT`
6. Éxito: Cierra modal, refresca tabla, muestra toast

#### Editar Empresa
1. Usuario hace clic en "Editar" en DataTable
2. `handleEditarEmpresa()` carga datos: `GET /api/v1/empresas/{id}/`
3. Llena formulario en modal `#modal-editar-empresa`
4. `handleGuardarEmpresa()` recolecta datos con `collectEmpresaPayload()`
5. Verifica existencia: `GET /api/v1/empresas/?page_size=1`
6. `PATCH /api/v1/core/empresa/` (upsert)
7. Éxito: Cierra modal, refresca tabla

#### Ver Empresa
1. Usuario hace clic en "Ver" en DataTable
2. `handleVerEmpresa()` carga datos: `GET /api/v1/empresas/{id}/`
3. Llena campos readonly en modal `#modal-ver-empresa`
4. Muestra logo si existe

### Endpoints Utilizados

| Método | Endpoint | Propósito |
|--------|----------|-----------|
| `GET` | `/api/v1/empresas/` | Listar empresas (singleton: 0-1 elementos) |
| `GET` | `/api/v1/empresas/{id}/` | Obtener empresa por ID |
| `GET` | `/api/v1/core/empresa/` | Obtener empresa singleton (fallback) |
| `PATCH` | `/api/v1/core/empresa/` | Crear/Actualizar empresa (upsert) |
| `PUT` | `/api/v1/core/empresa/` | Fallback si PATCH retorna 405 |

### Manejo de Errores

#### Errores HTTP
- **400 (Bad Request)**: Validación de campos → `renderFieldErrors()`
- **405 (Method Not Allowed)**: Retry con método permitido (PUT)
- **409 (Conflict)**: Singleton violation → Mensaje claro
- **401/403**: Sesión expirada → Mensaje de recarga

#### Errores de Parsing
- **JSON parse error**: Detecta HTML/no-JSON → Muestra snippet en error
- **Content-Type check**: Verifica `application/json` antes de `res.json()`

### Logging

Todos los logs usan prefijo `[empresa.page]`:
- `console.info()`: Operaciones normales
- `console.error()`: Errores
- `console.warn()`: Advertencias
- `console.debug()`: Solo si `DEBUG === true`

---

## ⚠️ Archivos Legacy

### `empresa.api.js`
- **Estado**: ⚠️ Legacy, no se carga en assets
- **Propósito**: API wrapper con funciones `getMiEmpresa()`, `listEmpresas()`, etc.
- **Razón de Legacy**: Funcionalidad migrada a `empresa.page.js` con helpers globales

### `empresa.modals.js`
- **Estado**: ⚠️ Legacy, no se carga en assets
- **Propósito**: Manejo de modales independiente
- **Razón de Legacy**: Funcionalidad integrada en `empresa.page.js`

### `empresa.ui.js`
- **Estado**: ⚠️ Legacy, no se carga en assets
- **Propósito**: Helpers de renderizado UI
- **Razón de Legacy**: Funcionalidad integrada en `empresa.page.js`

**Nota**: Estos archivos se mantienen como referencia histórica pero **NO deben usarse** en desarrollo nuevo.

---

## 🔄 Orquestación Actual

### Dependencias Globales Requeridas

El módulo requiere que estén disponibles en `window`:

```javascript
w.API_HELPERS      // Helpers de API (safeFetchJson, etc.)
w.Routes           // Router para URLs dinámicas
w.CRUD             // Helpers CRUD (updateSingleton, etc.)
w.DOMUtils         // Helpers DOM (waitForVisible, awaitVisibleAny, etc.)
w.DataTablesUtils  // Helpers DataTables (canUseDataTables, etc.)
```

### Inicialización

```javascript
// Auto-inicialización al cargar
if (d.readyState === 'loading') {
  d.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
```

### Flujo de Inicialización

1. `init()` verifica dependencias (`requireCore()`)
2. Carga empresa singleton (`loadEmpresa()`)
3. Bind eventos (`bindEvents()`)
4. Carga rutas (`w.Routes.get('empresa')`)
5. Adjunta listeners (`attachListenersOnce()`)
6. Inicializa DataTable si existe (`initDataTableEmpresa()`)

---

## ✅ Alineación con Backend

### Serializers
- **`EmpresaListSerializer`**: Campos mínimos para listado
- **`EmpresaDetailSerializer`**: Campos extendidos + logo URL
- **`EmpresaUpsertSerializer`**: Campos para create/update

### Services
- **`LIST_FIELDS`**: Alineado con `EmpresaListSerializer`
- **`DETAIL_FIELDS`**: Alineado con `EmpresaDetailSerializer`

### Modelo
- Campos canónicos: `razon_social`, `nit`, `dv`, `direccion`, `telefono`, `email_contacto`, `regimen_tributario`, `logo`, `website`, `moneda`
- Singleton: `UniqueConstraint` sobre `singleton_key`

---

## 📝 Notas de Desarrollo

### Reglas de Modificación

1. **NO eliminar campos canónicos** sin actualizar backend primero
2. **NO agregar campos obsoletos** (tipo_contribuyente_clase, etc.)
3. **Siempre usar `httpJSON()`** para fetch (no `fetch()` directo)
4. **Siempre verificar existencia** antes de crear (GET list)
5. **Siempre usar PATCH singleton** para upsert (no POST)
6. **Siempre filtrar campos canónicos** en `collectEmpresaPayload()`

### Testing

Para probar el módulo:
1. Abrir workspace: `http://home.sintel.com/workspace/#empresa`
2. Verificar que DataTable carga correctamente
3. Probar "Crear Empresa" (debe usar PATCH singleton)
4. Probar "Editar Empresa" (debe usar PATCH singleton)
5. Verificar logs en consola: `[empresa.page]`

---

## 🔗 Referencias

- **Backend Models**: `apps/tenant/empresa/models.py`
- **Backend Serializers**: `apps/tenant/empresa/api/serializers.py`
- **Backend Services**: `apps/tenant/empresa/services.py`
- **Backend ViewSets**: `apps/tenant/empresa/api/viewsets.py`
- **Templates**: `apps/tenant/core/templates/tenant/core/partials/empresa/`
- **Documentación Arquitectura**: `documentacion/arquitectura_general.md`
- **Documentación Workspace Empresa**: `documentacion/WORKSPACE_MODULO_EMPRESA_v2.37.md`

---

**Última actualización**: 2024-12-19  
**Versión del informe**: 1.0
