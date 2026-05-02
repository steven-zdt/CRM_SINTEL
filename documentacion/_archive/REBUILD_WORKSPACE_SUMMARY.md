# Rebuild Total del Workspace - Resumen de Cambios

## Arquitectura Modular Implementada

### 1. Estructura de Archivos Creada

```
apps/tenant/core/
├── static/core/js/
│   ├── lib/
│   │   └── http.js                    # Helper HTTP con SessionAuth+CSRF
│   ├── router.js                      # Router hash-based
│   ├── empresa/
│   │   ├── empresa.api.js            # API wrapper para Empresa
│   │   ├── empresa.ui.js             # UI y renderizado
│   │   └── empresa.page.js           # Entry point
│   ├── facturas/
│   │   └── facturas.page.js          # Entry point wrapper
│   └── mail/
│       ├── mail.api.js               # API wrapper para MailDigester
│       ├── mail.ui.js                # UI del panel
│       └── mail.page.js              # Entry point
└── templates/tenant/core/partials/
    ├── empresa/
    │   └── assets_empresas.html      # Assets del módulo
    ├── facturas/
    │   └── assets_facturas.html      # Assets del módulo
    └── mail/
        └── assets_mail.html          # Assets del módulo
```

### 2. Módulos Implementados

#### ✅ Empresa (SSoT)
- **API**: `empresa.api.js` - Wrapper para endpoints DRF
  - `getMiEmpresa()` → GET /api/v1/core/empresa/
  - `listEmpresas()` → GET /api/v1/empresas/
  - `createEmpresa()` → POST /api/v1/empresas/
  - `updateEmpresa()` → PATCH /api/v1/core/empresa/
  - `deleteEmpresa()` → DELETE /api/v1/empresas/{id}/

- **UI**: `empresa.ui.js` - Renderizado y eventos
  - `renderEmpresaList()` - Lista (singleton: 0-1 elementos)
  - `renderEmpresaDetail()` - Detalle (modo lectura)
  - `renderEmpresaForm()` - Formulario create/edit
  - `handleSaveEmpresa()` - Guardado
  - `handleDeleteEmpresa()` - Eliminación

- **Page**: `empresa.page.js` - Entry point `initEmpresaPage()`

#### ✅ Facturas (Alineado)
- **Page**: `facturas.page.js` - Wrapper que llama a `initFacturas()` de `facturas.ui.js`
- Ya usa endpoints universales:
  - `POST /api/v1/core/documentos/upload/?preview=true|false`
  - `GET /api/v1/core/documentos/{id}/xml/`
  - `DELETE /api/v1/core/documentos/{id}/`

#### ⚠️ MailDigester (Pendiente)
- Estructura creada, pendiente implementación completa

### 3. Router Hash-Based

**Archivo**: `router.js`

- Maneja navegación por hash (`#empresa`, `#facturas`, `#mail`)
- Inyecta partials en `#workspace-router-outlet`
- Llama a funciones `init*Page()` de cada módulo
- Escucha `hashchange` y clicks en `a[data-view]`

### 4. HTTP Helper

**Archivo**: `lib/http.js`

- Función `http(method, url, body)` con:
  - SessionAuth (`credentials: "same-origin"`)
  - CSRF automático (`X-CSRFToken` header)
  - Manejo de FormData y JSON
  - Manejo inteligente de 401 (no críticos vs críticos)
  - Diagnóstico de 403

### 5. Cambios en workspace.html

**ANTES**: 2319 líneas con JS inline masivo

**DESPUÉS**: Shell mínimo con:
- Estructura base (sidebar, main, outlet)
- Inclusión de libs compartidas (http.js, router.js)
- Inclusión de assets por módulo (opcional, puede ser lazy)
- Sin JS inline

## Próximos Pasos

1. **Reemplazar workspace.html** con shell mínimo
2. **Completar módulo MailDigester** (mail.api.js, mail.ui.js, mail.page.js)
3. **Crear partials HTML** para cada módulo (opcional, pueden renderizarse desde JS)
4. **Probar navegación** entre módulos
5. **Validar CRUD** de cada módulo

## Notas de Implementación

- **API-First**: Todos los módulos consumen exclusivamente APIs DRF (JSON-only)
- **SessionAuth + CSRF**: Manejo automático en `http.js`
- **Multi-tenant**: Aislamiento por esquema (django-tenants)
- **CRUD Aislado**: Cada app persiste vía sus propios endpoints
- **document_ingest**: Solo parsea, no persiste (v2.37)
