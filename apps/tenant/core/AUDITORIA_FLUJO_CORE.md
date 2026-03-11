# Auditoría de Flujo — Core (Workspace + Core API) — SINTEL

## 1) Propósito

`apps/tenant/core` es el **compositor** del tenant autenticado:

- Expone una **IU única** (workspace) para operar múltiples dominios (empresa, facturas, contabilidad, inventario, etc.).
- La IU es **shell HTML estructural** (sin lógica de negocio y sin render server-side de datos de negocio).
- Los datos y acciones del usuario se resuelven vía **APIs DRF** (SessionAuth + CSRF) por tenant.
- Core agrega **orquestación**: rutas canónicas, dashboard compuesto, y endpoints de “facade” (auth/landing) y adaptadores.

## 2) Entrada al sistema (ruteo tenant)

### 2.1 TENANT_URLCONF

En tenants privados, el ruteo se controla con `config/urls_tenant.py`.

Flujo base:

1. `GET /` (dominio tenant)
   - Redirige a shell estático según autenticación:
     - autenticado → `/static/tenant/core/dashboard/index.html`
     - anónimo → `/static/tenant/landing/index.html`

2. Shells estáticos de Core:
   - `/static/tenant/core/dashboard/index.html`
   - `/static/tenant/core/empresa/index.html`
   - `/static/tenant/core/contabilidad/index.html`
   - `/static/tenant/core/facturas/index.html`
   - `/static/tenant/core/perfil/index.html`

3. Workspace compositor (UI server-side estructural):
   - `GET /workspace/` → `apps/tenant/core/views_ui.py:WorkspaceView`

Notas:

- El ruteo de API vive bajo `path('api/v1/', include('config.api_urls'))`.
- La membresía tenant (cross-tenant guard) se asume en middleware (mencionado en `WorkspaceView`).

## 3) UI Core (workspace) — responsabilidades

### 3.1 WorkspaceView

Archivo:

- `apps/tenant/core/views_ui.py`

Características:

- `TemplateView` + `LoginRequiredMixin`.
- `ensure_csrf_cookie` para asegurar `csrftoken` en llamadas SessionAuth.
- Contexto mínimo: `STATIC_VERSION` (cache-busting).

Invariante:

- No debe inyectar datos de negocio; el JS consume APIs.

### 3.2 Template principal

Archivo:

- `apps/tenant/core/templates/tenant/core/workspace.html`

Observaciones:

- `workspace.html` incluye partials de Core y, en algunos módulos, partials de apps (ej. contabilidad `tenant/contabilidad/partials/list_cuentas.html`).
- Usa navegación por tabs (`#empresa`, `#facturas`, `#contabilidad`, etc.).
- Carga HTMX y utilidades JS; existe fallback de CDN.

Riesgos detectados:

- Mezcla de partials en Core y en apps específicas puede producir divergencias en contratos (IDs DOM, nombres de contenedor offcanvas) si no se gobierna como estándar.

## 4) Core API (DRF) — capa de composición

### 4.1 Registro de rutas

- `config/api_urls.py` registra cada app bajo `/api/v1/<app>/`.
- `apps/tenant/core/api/urls.py` registra `/api/v1/core/*`.

Puntos clave:

- `config/api_urls.py` es resiliente a `ImportError` por app (cada include está aislado).
- Core API no reemplaza CRUD de apps; actúa como **orquestador/facade**.

### 4.2 Endpoints Core principales

Definidos en `apps/tenant/core/api/views.py`:

- `GET /api/v1/core/routes/` → mapa canónico de rutas API.
- `GET /api/v1/core/dashboard/` → dashboard compuesto (empresa + facturas + contabilidad + perfil + branding).
- `GET/PATCH /api/v1/core/empresa/` → singleton/upsert de Empresa para UI.
- `GET/PATCH /api/v1/core/mi-perfil/` y `PATCH /api/v1/core/mi-perfil/configuracion/`.
- `POST /api/v1/core/auth/login/` y `POST /api/v1/core/auth/logout/`.
- Password reset (request/validate/confirm).
- Landing facade (`/api/v1/core/landing/info/`, `/api/v1/core/landing/auth/activate/`).

Otros módulos Core API:

- `apps/tenant/core/api/views_empresa.py`
  - mailbox configs CRUD (requiere `IsTenantAdmin`).

- `apps/tenant/core/api/views_contabilidad.py`
  - CRUD “facade” contabilidad por core adapters.

- `apps/tenant/core/api/viewsets_documentos.py`
  - endpoint universal de documentos (`/api/v1/core/documentos/*`).

- `apps/tenant/core/api/viewsets_inventario.py`
  - viewset de inventario a través de Core (facade).

### 4.3 Contrato y normalización de payload (JSON vs multipart)

Se estandarizó un helper funcional:

- `apps/tenant/core/api/utils.py`
  - `coerce_request_data(request)`
  - `get_pagination_params(request)`
  - `error_response(...)`

Objetivo:

- Normalizar `request.data` cuando venga como `QueryDict` (multipart/form-data).
- Ignorar `csrfmiddlewaretoken` como campo de negocio.
- Responder 400 claros cuando no hay campos editables.

## 5) Orquestación y adapters (consumo de lógica de apps)

### 5.1 Patrón

Core consume lógica de dominios por dos vías:

1. **Services de Core** (composición):
   - `apps/tenant/core/services/orchestration.py`
   - `apps/tenant/core/services/*` (snapshots/summary)

2. **Adapters** hacia apps dueñas (sin HTTP):
   - Ejemplos vistos en código:
     - `apps/tenant/core/services/empresa_adapter` (usado por Core Empresa + mailbox)
     - `apps/tenant/core/services/contabilidad_adapter` (usado por Core contabilidad)
     - `apps/tenant/core/services/landing_adapter` (landing facade)

Invariante:

- Los adapters deben mantener Core libre de lógica de dominio detallada (solo traducción/contrato y orquestación).

## 6) Seguridad, sesión y CSRF

- UI usa cookies de sesión (`SessionAuthentication`).
- `WorkspaceView` garantiza `csrftoken` con `ensure_csrf_cookie`.
- `apps/tenant/core/static/core/js/lib/http.js`:
  - añade header `X-CSRFToken` en mutaciones
  - maneja `FormData` sin setear `Content-Type`
  - agrega `csrfmiddlewaretoken` al FormData por compatibilidad

Puntos de control:

- Si el form no contiene campos con `name`, el request puede mandar solo CSRF; por eso Core API valida “campos editables reales”.

## 7) Error handling

- En tenants privados, handlers 404/403:
  - `apps/tenant/core/api/handlers.py`

Estado actual (API-first estricto):

- Devuelven **solo JSON** (`JsonResponse`) siempre.

## 8) Riesgos / deuda técnica observada

- **Doble registro conceptual de rutas**: `CoreRoutesView` y `CoreLinksViewSet` se solapan (ambos son “registry” de rutas). Esto puede generar divergencia.
- **Heterogeneidad de partials UI**: algunos módulos renderizan UI desde Core, otros desde la app específica. Si cambian selectores/IDs, la UI rompe.
- **Monolito en `core/api/views.py`**: concentra múltiples dominios (auth, landing, empresa, perfil, maildigester). Funciona pero dificulta mantenibilidad.

## 9) Recomendaciones (próximos pasos)

### 9.1 Unificar registro de rutas

- Elegir una fuente única:
  - o `GET /api/v1/core/routes/`
  - o `GET /api/v1/core/links/`

### 9.2 Separar Core API por submódulos (sin romper urls)

- Mantener `urls.py` igual, pero mover implementación a:
  - `views_auth.py`, `views_empresa_core.py`, `views_perfil_core.py`, etc.

### 9.3 Normalización estricta de payloads complejos

- Para campos JSON dentro de multipart (ej. `mail_inbox_config`), estandarizar:
  - enviar JSON real (application/json)
  - o serializar string y parsear controladamente (regla fija)

---

## Apéndice A — Mapa rápido de archivos Core relevantes

- UI
  - `apps/tenant/core/views_ui.py`
  - `apps/tenant/core/urls_ui.py`
  - `apps/tenant/core/templates/tenant/core/workspace.html`

- Core API
  - `apps/tenant/core/api/urls.py`
  - `apps/tenant/core/api/views.py`
  - `apps/tenant/core/api/views_empresa.py`
  - `apps/tenant/core/api/views_contabilidad.py`
  - `apps/tenant/core/api/viewsets_documentos.py`
  - `apps/tenant/core/api/viewsets_inventario.py`
  - `apps/tenant/core/api/utils.py`
  - `apps/tenant/core/api/handlers.py`

- Tenant URLs
  - `config/urls_tenant.py`
  - `config/api_urls.py`
