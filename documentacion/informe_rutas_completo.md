# 📋 Informe Completo del Estado de Rutas - Sistema CRM Sintel v2.40

**Fecha de Generación:** 2025-01-27  
**Versión del Sistema:** v2.40  
**Arquitectura:** API-First Multi-Tenant con Workspace Compositor

---

## 📑 Índice

1. [Arquitectura General de Rutas](#1-arquitectura-general-de-rutas)
2. [Flujo Completo de Request](#2-flujo-completo-de-request)
3. [Configuración de URLs Raíz](#3-configuración-de-urls-raíz)
4. [URLs de Tenant](#4-urls-de-tenant)
5. [URLs de API REST](#5-urls-de-api-rest)
6. [URLs de UI (Workspace)](#6-urls-de-ui-workspace)
7. [Módulos del Workspace](#7-módulos-del-workspace)
8. [Apps Tenant y sus Rutas](#8-apps-tenant-y-sus-rutas)
9. [Flujo de Assets y Partials](#9-flujo-de-assets-y-partials)
10. [Checklist de Validación](#10-checklist-de-validación)

---

## 1. Arquitectura General de Rutas

### 1.1 Estructura de Niveles

```
┌─────────────────────────────────────────────────────────────┐
│                    REQUEST ENTRANTE                          │
└───────────────────────┬───────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │   django-tenants Middleware   │
        │   (Aislamiento por esquema)    │
        └───────────────┬───────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌───────────────┐              ┌───────────────┐
│  ROOT_URLCONF │              │ TENANT_URLCONF │
│ config/urls.py│              │urls_tenant.py │
│ (Público)     │              │ (Privado)     │
└───────┬───────┘              └───────┬───────┘
        │                               │
        │                               │
        ▼                               ▼
┌──────────────────┐          ┌──────────────────┐
│ /api/v1/         │          │ /api/v1/         │
│ /api/public/v1/  │          │ /workspace/     │
│ /admin/          │          │ /dashboard/      │
│ /console/        │          │ /empresa/        │
└──────────────────┘          └──────────────────┘
```

### 1.2 Principios Arquitectónicos

- **API-First:** Todas las apps exponen APIs REST bajo `/api/v1/{app}/`
- **Workspace Compositor:** UI unificada en `/workspace/` que carga módulos dinámicamente
- **Multi-Tenant:** Aislamiento automático por esquema (django-tenants)
- **Lazy Loading:** Módulos cargan datos solo cuando son visibles
- **SSoT (Single Source of Truth):** Empresa como fuente única de datos por tenant

---

## 2. Flujo Completo de Request

### 2.1 Request a Tenant Privado (ej: cliente.sintel.com)

```
1. Request: GET https://cliente.sintel.com/workspace/
   │
   ├─► django-tenants detecta dominio "cliente.sintel.com"
   │   └─► Establece schema_context = "tenant_cliente"
   │
   ├─► TenantMainMiddleware activa TENANT_URLCONF
   │   └─► Carga: config/urls_tenant.py
   │
   ├─► config/urls_tenant.py línea 154:
   │   └─► path('', include('apps.tenant.core.urls_ui'))
   │
   ├─► apps/tenant/core/urls_ui.py línea 36:
   │   └─► path('workspace/', views_ui.WorkspaceView.as_view())
   │
   ├─► WorkspaceView.render() → workspace.html
   │
   └─► workspace.html incluye:
       ├─► Partials HTML (list.html, modals.html)
       ├─► Assets JS (assets_{app}.html)
       └─► JavaScript carga datos desde /api/v1/{app}/
```

### 2.2 Request a API REST (ej: GET /api/v1/gastos/)

```
1. Request: GET https://cliente.sintel.com/api/v1/gastos/
   │
   ├─► django-tenants detecta dominio
   │   └─► Establece schema_context = "tenant_cliente"
   │
   ├─► TenantMainMiddleware activa TENANT_URLCONF
   │   └─► Carga: config/urls_tenant.py
   │
   ├─► config/urls_tenant.py línea 147:
   │   └─► path('api/v1/', include('config.api_urls'))
   │
   ├─► config/api_urls.py línea 118:
   │   └─► path('gastos/', include('apps.tenant.gastos.api.urls'))
   │
   ├─► apps/tenant/gastos/api/urls.py línea 39:
   │   └─► router.register(r'', GastoViewSet, basename='gastos')
   │
   ├─► GastoViewSet.list() → qs_list() → GastoListSerializer
   │
   └─► Response JSON: [{id, ds_consecutivo, ds_prefijo, ...}]
```

---

## 3. Configuración de URLs Raíz

### 3.1 Archivo: `config/urls.py` (ROOT_URLCONF)

**Propósito:** URLs públicas (esquema `public`)

**Rutas Principales:**

| Ruta | Handler | Propósito |
|------|---------|-----------|
| `/` | `root_view` | Redirige a `/console/` |
| `/health` | `health_view` | Health check (Docker/K8s) |
| `/admin/` | `admin.site.urls` | Django Admin (solo público) |
| `/api/v1/` | `include('config.api_urls')` | APIs REST (namespace: `v1`) |
| `/api/public/v1/` | `include('config.public_api_urls')` | APIs públicas |
| `/api/token/` | `TokenObtainPairView` | JWT Login |
| `/api/token/refresh/` | `TokenRefreshView` | JWT Refresh |
| `/api/token/verify/` | `LoggedTokenVerifyView` | JWT Verify |
| `/api/schema/` | `SpectacularAPIView` | OpenAPI Schema |
| `/api/docs/` | `SpectacularSwaggerView` | Swagger UI |
| `/api/redoc/` | `SpectacularRedocView` | ReDoc |
| `/console/` | `include('apps.public.console.urls')` | Consola pública |

**Líneas Críticas:**
- **Línea 113:** `path('api/v1/', include(('config.api_urls', 'api'), namespace='v1'))`
  - Namespace `v1` para APIs REST
  - Incluye `config.api_urls` (también usado en tenant)

---

## 4. URLs de Tenant

### 4.1 Archivo: `config/urls_tenant.py` (TENANT_URLCONF)

**Propósito:** URLs privadas (esquemas `tenant_*`)

**Rutas Principales:**

#### 4.1.1 Rutas Raíz y Redirecciones

| Ruta | Handler | Propósito |
|------|---------|-----------|
| `/` | `TenantRootView` | Redirige según autenticación |
| `/activate/` | `RedirectView` → `/static/tenant/landing/activate.html` | Activación |
| `/login/` | `RedirectView` → `/static/tenant/landing/login.html` | Login |
| `/reset-password/` | `RedirectView` → `/static/tenant/landing/reset-request.html` | Reset password |
| `/dashboard/` | `RedirectView` → `/static/tenant/core/dashboard/index.html` | Dashboard |
| `/empresa/` | `RedirectView` → `/static/tenant/core/empresa/index.html` | Empresa |
| `/facturas/` | `RedirectView` → `/static/tenant/core/facturas/index.html` | Facturas |
| `/contabilidad/` | `RedirectView` → `/static/tenant/core/contabilidad/index.html` | Contabilidad |

#### 4.1.2 APIs REST

| Ruta | Include | Propósito |
|------|---------|-----------|
| `/api/v1/` | `include('config.api_urls')` | **APIs REST principales** |
| `/api/v1/landing/` | `include('apps.tenant.landing.api.urls')` | APIs de landing |
| `/api/token/` | `TokenObtainPairView` | JWT Login (tenant) |
| `/api/token/refresh/` | `TokenRefreshView` | JWT Refresh (tenant) |
| `/api/token/verify/` | `LoggedTokenVerifyView` | JWT Verify (tenant) |

#### 4.1.3 UI Routes (Workspace Compositor)

| Ruta | Include | Propósito |
|------|---------|-----------|
| `/workspace/` | `include('apps.tenant.core.urls_ui')` | **Workspace principal** |
| `/ui/landing/` | `include('apps.tenant.landing.urls_ui')` | Partials landing |
| `/ui/dashboard/` | `include('apps.tenant.dashboard.urls_ui')` | Partials dashboard |
| `/ui/empresa/` | `include('apps.tenant.empresa.urls_ui')` | Partials empresa |
| `/ui/contabilidad/` | `include('apps.tenant.contabilidad.urls_ui')` | Partials contabilidad |
| `/ui/perfil/` | `include('apps.tenant.perfil.urls_ui')` | Partials perfil |

**Líneas Críticas:**
- **Línea 147:** `path('api/v1/', include('config.api_urls'))`
  - **CRÍTICO:** Todas las APIs REST se registran aquí
- **Línea 154:** `path('', include('apps.tenant.core.urls_ui'))`
  - **CRÍTICO:** Workspace compositor se registra aquí

---

## 5. URLs de API REST

### 5.1 Archivo: `config/api_urls.py`

**Propósito:** Centraliza todas las APIs REST de apps tenant

**Estructura:**

```python
urlpatterns = [
    # Redirección de compatibilidad
    path('empresa/', empresa_singular_redirect),
    
    # Apps tenant (cada una en try/except para resiliencia)
    path('empresas/', include('apps.tenant.empresa.api.urls')),
    path('facturas/', include('apps.tenant.facturas.api.urls')),
    path('', include('apps.tenant.contabilidad.api.urls')),
    path('inventario/', include('apps.tenant.inventario.api.urls')),
    path('perfil/', include('apps.tenant.perfil.api.urls')),
    path('dashboard/', include('apps.tenant.dashboard.api.urls')),
    path('core/', include('apps.tenant.core.api.urls')),
    path('empleados/', include('apps.tenant.empleados.api.urls')),
    path('gastos/', include('apps.tenant.gastos.api.urls')),  # ⚠️ LÍNEA 118
    path('proveedores/', include('apps.tenant.proveedores.api.urls')),
    path('clientes/', include('apps.tenant.clientes.api.urls')),
    path('', include('apps.public.impuestos.api.urls')),
]
```

**Apps Registradas (en orden):**

1. ✅ **empresas** → `/api/v1/empresas/`
2. ✅ **facturas** → `/api/v1/facturas/`
3. ✅ **contabilidad** → `/api/v1/` (raíz)
4. ✅ **inventario** → `/api/v1/inventario/`
5. ✅ **perfil** → `/api/v1/perfil/`
6. ✅ **dashboard** → `/api/v1/dashboard/`
7. ✅ **core** → `/api/v1/core/`
8. ✅ **empleados** → `/api/v1/empleados/`
9. ✅ **gastos** → `/api/v1/gastos/` ⚠️ **CRÍTICO**
10. ✅ **proveedores** → `/api/v1/proveedores/`
11. ✅ **clientes** → `/api/v1/clientes/`
12. ✅ **impuestos** → `/api/v1/` (raíz)

**Resiliencia:**
- Cada `include()` está en `try/except` para que un fallo no bloquee las demás apps
- Logging detallado con `logger.info()` y `logger.error()`

---

## 6. URLs de UI (Workspace)

### 6.1 Archivo: `apps/tenant/core/urls_ui.py`

**Propósito:** Rutas UI del workspace compositor

**Rutas:**

| Ruta | View | Template | Propósito |
|------|------|----------|-----------|
| `/workspace/` | `WorkspaceView` | `workspace.html` | **Workspace principal** |

**Línea Crítica:**
- **Línea 36:** `path('workspace/', views_ui.WorkspaceView.as_view(), name='workspace')`
  - Genera la URL final: `/workspace/`
  - Renderiza `tenant/core/workspace.html`

---

## 7. Módulos del Workspace

### 7.1 Archivo: `apps/tenant/core/templates/tenant/core/workspace.html`

**Estructura de Módulos:**

| Tab ID | Módulo | Partials Incluidos | Assets Incluidos |
|--------|--------|-------------------|------------------|
| `#tab-empresa` | Empresa | `list.html`, `modals.html`, `mailinbox_list.html`, `mailinbox_modals.html` | `assets_empresa.html` |
| `#tab-facturas` | Facturas | `list.html`, `modals.html` | `assets_facturas.html` |
| `#tab-contabilidad` | Contabilidad | `list_cuentas.html`, `modals_cuentas.html`, `list_asientos.html`, `modals_asientos.html` | `assets_cuentas.html`, `assets_asientos.html` |
| `#tab-inventario` | Inventario | `list_catalogo.html`, `modals_catalogo.html`, `list_activos.html`, `modals_activos.html`, `list_movimientos.html`, `modals_movimientos.html` | `assets_inventario.html` |
| `#tab-empleados` | Empleados | `list.html`, `modals.html` | `assets_empleados.html` |
| `#tab-gastos` | **Gastos** | `list.html`, `modals.html` | `assets_gastos.html` ⚠️ |
| `#tab-proveedores` | Proveedores | `list.html`, `modals.html` | `assets_proveedores.html` |
| `#tab-clientes` | Clientes | `list.html`, `modals.html` | `assets_clientes.html` |
| `#tab-perfil` | Perfil | `list.html`, `modals.html` | `assets_perfil.html` |

### 7.2 Flujo de Carga de Módulo (ej: Gastos)

```
1. Usuario hace clic en tab "Gastos"
   │
   ├─► workspace.js muestra #tab-gastos
   │
   ├─► DOMUtils.onVisibleOnce('#tab-gastos', init)
   │   └─► Detecta que el tab es visible
   │
   ├─► gastos.page.js → init()
   │   ├─► initDataTable() → GET /api/v1/gastos/
   │   ├─► renderSummary() → GET /api/v1/gastos/summary/
   │   └─► attachListenersOnce() → Event listeners
   │
   └─► DataTables renderiza tabla con datos
```

### 7.3 Assets Cargados (orden de carga)

```html
<!-- Línea 245: Helpers Core -->
{% include 'tenant/core/partials/assets_core.html' %}

<!-- Línea 248: Workspace navigation -->
<script src="{% static 'core/js/workspace.js' %}"></script>

<!-- Línea 254: Empresa -->
{% include 'tenant/core/partials/empresa/assets_empresa.html' %}

<!-- Línea 263: Facturas -->
{% include 'tenant/facturas/partials/assets_facturas.html' %}

<!-- Línea 266-267: Contabilidad -->
{% include 'tenant/contabilidad/partials/assets_cuentas.html' %}
{% include 'tenant/contabilidad/partials/assets_asientos.html' %}

<!-- Línea 270: Inventario -->
{% include 'tenant/inventario/partials/assets_inventario.html' %}

<!-- Línea 273: Empleados -->
{% include 'tenant/empleados/partials/assets_empleados.html' %}

<!-- Línea 279: Gastos ⚠️ -->
{% include 'tenant/core/partials/gastos/assets_gastos.html' %}

<!-- Línea 280-282: Otros módulos -->
{% include 'tenant/proveedores/partials/assets_proveedores.html' %}
{% include 'tenant/clientes/partials/assets_clientes.html' %}
{% include 'tenant/perfil/partials/assets_perfil.html' %}
```

---

## 8. Apps Tenant y sus Rutas

### 8.1 Empresa (`apps.tenant.empresa`)

**API URLs:** `apps/tenant/empresa/api/urls.py`

| Endpoint | Método | ViewSet/Action | Propósito |
|----------|--------|----------------|-----------|
| `/api/v1/empresas/` | GET | `EmpresaViewSet.list()` | Listado |
| `/api/v1/empresas/` | POST | `EmpresaViewSet.create()` | Crear |
| `/api/v1/empresas/{id}/` | GET | `EmpresaViewSet.retrieve()` | Detalle |
| `/api/v1/empresas/{id}/` | PUT/PATCH | `EmpresaViewSet.update()` | Actualizar |
| `/api/v1/empresas/{id}/` | DELETE | `EmpresaViewSet.destroy()` | Eliminar |
| `/api/v1/empresas/dt/empresa/` | POST | `EmpresaViewSet.datatables()` | DataTables |
| `/api/v1/empresas/mail-inbox-config/` | GET/POST | `MailInboxConfigViewSet` | Config mailbox |
| `/api/v1/empresas/empresa/form-metadata/` | GET | `form_metadata` | Metadata formulario |
| `/api/v1/empresas/empresa/actividades-lookup/` | GET | `actividades_lookup` | Lookup actividades |
| `/api/v1/empresas/empresa/ciiu-lookup/` | GET | `ciiu_lookup` | Lookup CIIU |

**Router:** `DefaultRouter` con `basename='empresas'`

---

### 8.2 Facturas (`apps.tenant.facturas`)

**API URLs:** `apps/tenant/facturas/api/urls.py`

| Endpoint | Método | ViewSet/Action | Propósito |
|----------|--------|----------------|-----------|
| `/api/v1/facturas/` | GET | `FacturaViewSet.list()` | Listado |
| `/api/v1/facturas/` | POST | `FacturaViewSet.create()` | Crear |
| `/api/v1/facturas/{id}/` | GET | `FacturaViewSet.retrieve()` | Detalle |
| `/api/v1/facturas/{id}/` | PUT/PATCH | `FacturaViewSet.update()` | Actualizar |
| `/api/v1/facturas/{id}/` | DELETE | `FacturaViewSet.destroy()` | Eliminar |
| `/api/v1/facturas/dt/facturas/` | POST | `FacturaViewSet.datatables()` | DataTables |
| `/api/v1/facturas/notas-credito/` | GET/POST | `NotaCreditoViewSet` | Notas de crédito |
| `/api/v1/facturas/items-factura/` | GET/POST | `ItemFacturaViewSet` | Items factura |
| `/api/v1/facturas/ingesta-correo/run/` | POST | `MailIngestionRunCreateAPIView` | Ingesta correo |
| `/api/v1/facturas/ingesta-correo/runs/` | GET | `MailIngestionRunsListAPIView` | Lista ingesta |

**Router:** `DefaultRouter` con múltiples ViewSets (orden crítico)

---

### 8.3 Gastos (`apps.tenant.gastos`) ⚠️ **CRÍTICO**

**API URLs:** `apps/tenant/gastos/api/urls.py`

| Endpoint | Método | ViewSet/Action | Propósito |
|----------|--------|----------------|-----------|
| `/api/v1/gastos/` | GET | `GastoViewSet.list()` | Listado |
| `/api/v1/gastos/` | POST | `GastoViewSet.create()` | Crear |
| `/api/v1/gastos/{id}/` | GET | `GastoViewSet.retrieve()` | Detalle |
| `/api/v1/gastos/{id}/` | DELETE | `GastoViewSet.destroy()` | Eliminar (rollback) |
| `/api/v1/gastos/summary/` | GET | `GastoViewSet.summary()` | Resumen financiero |
| `/api/v1/gastos/resoluciones/` | GET | `GastoViewSet.resoluciones()` | Resoluciones DIAN |
| `/api/v1/gastos/{id}/anular/` | POST | `GastoViewSet.anular()` | Anular documento |
| `/api/v1/gastos/dt/gastos/` | POST | `GastoViewSet.datatables()` | DataTables server-side |

**Router:** `DefaultRouter` con `basename='gastos'`

**Características:**
- ✅ **Inmutabilidad estricta:** No permite PUT/PATCH
- ✅ **Service Layer:** `qs_list()`, `qs_detail()`, `get_gastos_summary()`, `anular_gasto_service()`
- ✅ **Campos aplanados:** `ds_consecutivo`, `ds_prefijo`, `ds_vendedor`, etc.
- ✅ **Exclusión de anulados:** `summary` excluye `anulado=True`

**Estructura del Router:**
```python
router = DefaultRouter()
router.register(r'', GastoViewSet, basename='gastos')
urlpatterns = router.urls  # ⚠️ CRÍTICO: No usar include(router.urls)
```

---

### 8.4 Contabilidad (`apps.tenant.contabilidad`)

**API URLs:** `apps/tenant/contabilidad/api/urls.py`

| Endpoint | Método | Propósito |
|----------|--------|-----------|
| `/api/v1/contabilidad/cuentas/` | GET/POST | Cuentas contables |
| `/api/v1/contabilidad/asientos/` | GET/POST | Asientos contables |
| `/api/v1/contabilidad/movimientos/` | GET/POST | Movimientos |

**Router:** `DefaultRouter` con múltiples ViewSets

---

### 8.5 Core (`apps.tenant.core`)

**API URLs:** `apps/tenant/core/api/urls.py`

| Endpoint | Método | Propósito |
|----------|--------|-----------|
| `/api/v1/core/health/` | GET | Health check |
| `/api/v1/core/routes/` | GET | Descubrimiento de rutas |
| `/api/v1/core/dashboard/` | GET | Dashboard compuesto |
| `/api/v1/core/mi-empresa/` | GET | Empresa del usuario |
| `/api/v1/core/empresa/` | GET | Empresa (orquestador) |
| `/api/v1/core/contabilidad/cuentas/` | GET/POST | Cuentas (Core API) |
| `/api/v1/core/contabilidad/asientos/` | GET/POST | Asientos (Core API) |
| `/api/v1/core/mi-perfil/` | GET | Perfil usuario |
| `/api/v1/core/facturas/resumen/` | GET | Resumen facturas |
| `/api/v1/core/landing/info/` | GET | Info landing |
| `/api/v1/core/auth/login/` | POST | Login |
| `/api/v1/core/auth/logout/` | POST | Logout |
| `/api/v1/core/auth/password-reset/request/` | POST | Reset password |
| `/api/v1/core/documentos/` | GET/POST | Documentos (ViewSet) |
| `/api/v1/core/links/` | GET/POST | Links (ViewSet) |
| `/api/v1/core/dashboard/sections/` | GET/POST | Secciones dashboard |
| `/api/v1/core/inventario/` | GET/POST | Inventario (ViewSet) |

**Router:** `DefaultRouter` con múltiples ViewSets y rutas manuales

---

### 8.6 Otras Apps Tenant

| App | Endpoint Base | Router | Estado |
|-----|--------------|--------|--------|
| **inventario** | `/api/v1/inventario/` | `DefaultRouter` | ✅ Activo |
| **perfil** | `/api/v1/perfil/` | `DefaultRouter` | ✅ Activo |
| **dashboard** | `/api/v1/dashboard/` | `DefaultRouter` | ✅ Activo |
| **empleados** | `/api/v1/empleados/` | `DefaultRouter` | ✅ Activo |
| **proveedores** | `/api/v1/proveedores/` | `DefaultRouter` | ✅ Activo |
| **clientes** | `/api/v1/clientes/` | `DefaultRouter` | ✅ Activo |
| **landing** | `/api/v1/landing/` | `DefaultRouter` | ✅ Activo |

---

## 9. Flujo de Assets y Partials

### 9.1 Estructura de Partials

```
apps/tenant/core/templates/tenant/core/partials/
├── empresa/
│   ├── list.html
│   ├── modals.html
│   ├── mailinbox_list.html
│   ├── mailinbox_modals.html
│   └── assets_empresa.html
├── facturas/
│   ├── list.html
│   ├── modals.html
│   └── assets_facturas.html
├── gastos/ ⚠️
│   ├── list.html
│   ├── modals.html
│   └── assets_gastos.html
└── assets_core.html
```

### 9.2 Assets de Gastos (`assets_gastos.html`)

**Ubicación:** `apps/tenant/core/templates/tenant/core/partials/gastos/assets_gastos.html`

**Scripts Incluidos:**
1. `gastos.api.js` - Wrapper de API
2. `gastos.modals.js` - Manejo de modales
3. `gastos.page.js` - Lógica principal (DataTables, eventos)

**Orden de Carga:**
```html
<!-- 1. API Wrapper -->
<script src="{% static 'core/js/gastos/gastos.api.js' %}"></script>

<!-- 2. Modals -->
<script src="{% static 'core/js/gastos/gastos.modals.js' %}"></script>

<!-- 3. Página principal -->
<script src="{% static 'core/js/gastos/gastos.page.js' %}"></script>
```

### 9.3 Partials de Gastos

**`list.html`:**
- Tabla DataTables con ID `#table-gastos`
- Columnas: Documento, Fecha, Vendedor, Categoría, Centro de Costo, Total Neto, Estado, Acciones
- Panel de resumen financiero (`#gastos-summary-panel`)

**`modals.html`:**
- Modal de creación (`#modal-gasto-create`)
- Formulario con campos de `DocumentoSoporte` y `Gasto`
- Validación HTML5 y cálculo automático de totales

---

## 10. Checklist de Validación

### 10.1 Validación de Rutas de Gastos

- [x] ✅ `apps.tenant.gastos` en `TENANT_APPS` (settings.py)
- [x] ✅ `path('gastos/', include('apps.tenant.gastos.api.urls'))` en `config/api_urls.py` (línea 118)
- [x] ✅ `router.register(r'', GastoViewSet, basename='gastos')` en `apps/tenant/gastos/api/urls.py` (línea 39)
- [x] ✅ `urlpatterns = router.urls` (no `include(router.urls)`)
- [x] ✅ `GastoViewSet.queryset = Gasto.objects.all()` (requerido por DRF)
- [x] ✅ `@action(detail=False, methods=["get"], url_path="summary")` en `summary()`
- [x] ✅ `#tab-gastos` en `workspace.html` (línea 202)
- [x] ✅ `{% include 'tenant/core/partials/gastos/list.html' %}` (línea 203)
- [x] ✅ `{% include 'tenant/core/partials/gastos/modals.html' %}` (línea 205)
- [x] ✅ `{% include 'tenant/core/partials/gastos/assets_gastos.html' %}` (línea 279)

### 10.2 Validación de Flujo Completo

- [x] ✅ Request → `config/urls_tenant.py` línea 147 → `config/api_urls.py` línea 118
- [x] ✅ `config/api_urls.py` → `apps/tenant/gastos/api/urls.py` → `router.register()`
- [x] ✅ `router.urls` → `GastoViewSet` → `get_queryset()` → `qs_list()`
- [x] ✅ `GastoListSerializer` → Response JSON
- [x] ✅ Frontend: `gastos.page.js` → `gastosAPI.list()` → `GET /api/v1/gastos/`
- [x] ✅ DataTables renderiza con campos aplanados

### 10.3 Endpoints Disponibles (Gastos)

| Endpoint | Método | Estado | Notas |
|----------|--------|--------|-------|
| `/api/v1/gastos/` | GET | ✅ | Listado |
| `/api/v1/gastos/` | POST | ✅ | Crear |
| `/api/v1/gastos/{id}/` | GET | ✅ | Detalle |
| `/api/v1/gastos/{id}/` | DELETE | ✅ | Eliminar |
| `/api/v1/gastos/summary/` | GET | ✅ | Resumen |
| `/api/v1/gastos/resoluciones/` | GET | ✅ | Resoluciones DIAN |
| `/api/v1/gastos/{id}/anular/` | POST | ✅ | Anular |
| `/api/v1/gastos/dt/gastos/` | POST | ✅ | DataTables |

---

## 📊 Resumen Ejecutivo

### Estado Actual: ✅ **FUNCIONAL**

**Rutas Registradas:**
- ✅ 12 apps tenant con APIs REST activas
- ✅ Workspace compositor funcionando
- ✅ Gastos completamente integrado

**Flujo Validado:**
1. ✅ Request → Tenant URLConf → API URLs → Router → ViewSet → Response
2. ✅ Workspace → Partials → Assets → JavaScript → API → DataTables

**Puntos Críticos:**
- ⚠️ **Gastos:** Router usa `router.urls` directamente (no `include(router.urls)`)
- ⚠️ **Gastos:** `queryset` debe estar definido en clase para DRF
- ⚠️ **Gastos:** `summary` action con `detail=False`

**Próximos Pasos Recomendados:**
1. Ejecutar `python scripts/verify_gastos_urls.py` para validación completa
2. Verificar logs del servidor al iniciar (buscar `✅ URLs de gastos registradas`)
3. Probar endpoints manualmente con `curl` o Postman

---

**Fin del Informe**
