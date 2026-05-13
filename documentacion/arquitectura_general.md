# Arquitectura General — SINTEL ERP

**Version:** 3.5.0
**Ultima actualizacion:** 2026-05-09
**Fuente canonica:** `documentacion/arquitectura_general.md`
**Reglas de desarrollo:** `AGENTS.md` (raiz del proyecto)
**Estado actual del proyecto:** `MEMORY.md` (raiz del proyecto)
**Modo de Proyecto:** 🚧 EN DESARROLLO (Development Mode)

---

## 1. Vision General

SINTEL es un ERP SaaS multi-tenant para gestion contable y facturacion electronica en Colombia. Cada empresa (tenant) opera en un esquema PostgreSQL aislado compartiendo la misma infraestructura. El sistema sigue una arquitectura Feature-Sliced Design (FSD) con Service Layer estricto, autenticacion Dual-Auth (JWT + Session) y frontend sin build step.

**Dominio de negocio:** gestion de facturas electronicas DIAN, contabilidad NIIF PYMES, nomina, inventario, gastos, cotizaciones y CRM basico.

---

## 2. Stack Tecnologico

### Backend

| Tecnologia | Version | Rol |
|---|---|---|
| Python | 3.12 | Lenguaje principal |
| Django | 4.x | Framework web |
| Django REST Framework | 3.x | APIs JSON |
| django-tenants | 3.x | Aislamiento multi-tenant por esquemas PostgreSQL |
| PostgreSQL | 15+ | Base de datos relacional |
| Celery | 5.x | Tareas asincronas y procesamiento en segundo plano |
| Redis | 7.x | Broker de Celery y cache |
| WhiteNoise | 6.x | Servicio de archivos estaticos en produccion |
| djangorestframework-simplejwt | 5.3+ | Tokens JWT (access 15 min, refresh 7 dias) |

### Frontend

| Tecnologia | Version | Rol |
|---|---|---|
| HTMX | 1.9.10 | Server-driven UI, carga dinamica de fragmentos HTML |
| Bootstrap | 5.3.2 | Sistema de diseno UI, Offcanvas para modales |
| Tabulator | 6.2.5 | Grillas de datos reactivas con paginacion remota |
| Vanilla JS ES6+ | — | Modulos por namespace `window.Sintel.<App>` |
| Bootstrap Icons + Font Awesome | — | Iconografia |

**No hay build step.** Todas las librerias se cargan via CDN. No hay Webpack, Vite ni compilacion de frontend.

### Infraestructura

| Componente | Tecnologia |
|---|---|
| Contenedores | Docker + Docker Compose |
| Servidor WSGI | Gunicorn |
| Proxy inverso | Nginx (produccion) |
| Autenticacion asimetrica | HS256 JWT via `JWT_SECRET_KEY` env var |

---

## 3. Centralidad del Directorio `config/`

El directorio `config/` es el nucleo de configuracion del proyecto. Toda la orquestacion de URLs, settings y tareas asincronas pasa por aqui.

```
config/
  settings.py          # SSoT de toda la configuracion Django
  urls.py              # Root URL (redirige segun dominio)
  urls_public.py       # ROOT_URLCONF — dominio admin → esquema public
  urls_tenant.py       # TENANT_URLCONF — subdominios → esquema tenant
  api_urls.py          # SSoT de TODAS las rutas API REST (/api/v1/...)
  celery.py            # Configuracion Celery + autodiscovery de tasks
  asgi.py              # Entry point ASGI
  wsgi.py              # Entry point WSGI
  public_api_urls.py   # Rutas API del esquema publico
  well_known.py        # Endpoints .well-known (DIAN, OAuth)
```

### settings.py — Configuracion central

- `SHARED_APPS`: apps del esquema public (accounts, tenants, impuestos, console)
- `TENANT_APPS`: apps del esquema tenant (empresa, facturas, contabilidad, etc.)
- `INSTALLED_APPS = SHARED_APPS + TENANT_APPS`
- `ROOT_URLCONF = 'config.urls_public'`
- `TENANT_URLCONF = 'config.urls_tenant'`
- `DEFAULT_AUTHENTICATION_CLASSES`: JWT + Session (heredado por todos los ViewSets)
- `SIMPLE_JWT`: access 15 min, refresh 7 dias, ROTATE=True, BLACKLIST=True, HS256
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`: configurados via env vars

### api_urls.py — SSoT de rutas API

Todas las rutas `/api/v1/<app>/` estan registradas aqui. Es la unica fuente de verdad para endpoints REST. Ningun ViewSet se registra fuera de este archivo.

### Resolucion de tenant por hostname

```
request → TenantMiddleware → hostname match → set schema PostgreSQL
admin.sintel.co  →  public schema  →  urls_public.py
empresa.sintel.co  →  tenant schema  →  urls_tenant.py
```

---

## 4. Arquitectura Multi-Tenant (django-tenants)

- **Esquema `public`**: usuarios globales (`accounts.User`), registro de tenants (`tenants.Client`), catalogo DIAN (`impuestos`), consola admin (`console`).
- **Esquemas tenant**: un esquema PostgreSQL por empresa. Completamente aislados a nivel de base de datos.
- **Modelo base obligatorio**: todos los modelos tenant heredan de `SintelTenantBaseModel` (`apps/tenant/core/models.py`), que inyecta `empresa (FK)`, `created_at`, `updated_at` e indices `[empresa]`, `[empresa, -created_at]`.
- **Cross-schema bridge**: las apps tenant NO importan de `apps.public.*` directamente. Usan `apps.tenant.core.services.membership` como unico puente autorizado.

---

## 5. Service Layer — Feature-Sliced Design (FSD)

Cada app tenant sigue esta estructura exacta. Un ecosistema completo por modelo.

```
apps/tenant/<app>/
  models.py
  services/
    __init__.py          # Re-exporta clases principales
    crud_service.py      # SOLO persistencia DB, @transaction.atomic
    business_service.py  # Reglas de negocio + Double Semantic Verification (IDOR)
    selectors.py         # QuerySets read-only con .only(), LIST_FIELDS/DETAIL_FIELDS
    api_mixins.py        # <Modelo>ServiceMixin inyectado en ViewSet
    services.py          # Facade estable (re-exporta desde business_service)
  api/
    viewsets.py          # Hereda BaseTenantViewSet + ServiceMixin
    serializers.py
    urls.py
  templates/tenant/<app>/
    offcanvas_crear_<modelo>.html
    offcanvas_editar_<modelo>.html
    offcanvas_detalle_<modelo>.html
    list_<modelo>.html
    partials/
  static/<app>/js/
    <app>.api.js         # SSoT de todas las URLs de endpoint
    features/
      <modelo>_list.js   # Grilla Tabulator
      <modelo>_editor.js # Formularios Offcanvas
  AUDITORIA_FLUJO_COMPLETO.md   # Flujo especifico de la app (leer antes de modificar)
```

### Flujo unidireccional (obligatorio)

```
ViewSet → ServiceMixin → BusinessService (DSV + reglas) → CRUDService (DB) → Response JSON/HTMX OOB
```

El ViewSet solo enruta HTTP. Toda logica vive en el Service Layer. Los modelos no tienen logica de negocio.

### Double Semantic Verification (DSV)

Toda mutacion en `business_service.py` valida que los FKs del payload pertenezcan al tenant actual (`empresa_id`). Previene IDOR a nivel de aplicacion.

---

## 6. Seguridad y Autenticacion (Dual-Auth)

### Dual-Auth JWT + Session

`BaseTenantViewSet` (`apps/tenant/api/base.py`) define:
```python
authentication_classes = [JWTAuthentication, SessionAuthentication]
```
Todos los ViewSets tenant lo heredan. Prohibido sobrescribir en ViewSets hijos.

- DRF evalua JWT primero (header `Authorization: Bearer`). Si falla, usa Session (cookie).
- Bridge Session→JWT: `GET /api/v1/core/auth/from-session/`

### Roles (SSoT: `TenantProfile.rol`)

| Rol | Capacidades |
|---|---|
| `ADMIN` | CRUD completo, asignar roles, configuracion empresa |
| `OPERADOR` | Lectura + escritura segun app |
| `VISOR` | Solo lectura |

### Permisos (SSoT: `apps/tenant/api/permissions.py`)

```python
permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
```

`IsTenantMember` es obligatorio en todo ViewSet. Verifica membresia activa via el bridge cross-schema.

### Frontend JWT

```javascript
const token = window.jwtAuth?.getAccessToken?.();   // CORRECTO
// window.jwtAuth.token  ← NO EXISTE, prohibido
```

---

## 7. Frontend

### Patron de modulos JS

```javascript
// Namespace por app: window.Sintel.<App>
window.Sintel = window.Sintel || {};
window.Sintel.Clientes = (function() {
    const state = {};
    // ...
    return { init };
})();
```

### Tabulator (grillas)

Todas las grillas usan `TabulatorFactory.create()` (`core/static/core/js/common/tabulator.factory.js`). Inyecta JWT automaticamente, maneja busqueda y paginacion remota.

```javascript
state.table = window.TabulatorFactory.create(
    '#grid-clientes',
    '/api/v1/clientes/',
    getColumnas(),
    { searchInputSelector: '#search-clientes' }
);
```

La tabla espera respuesta DRF paginada: `{ count, next, previous, results: [] }`.

### HTMX (Offcanvas y fragmentos)

Los Offcanvas (crear/editar/detalle) se cargan via `hx-get` apuntando a `render-offcanvas/crear/`. El backend retorna HTML parcial. El JS lo muestra con `UIManager.handleOffcanvas(el, 'show')`.

```html
<button hx-get="/api/v1/<app>/render-offcanvas/crear/"
        hx-target="#offcanvas-container-<app>"
        hx-swap="innerHTML">Nuevo</button>
```

### DOM Shield

Los formularios Maestro-Detalle remueven temporalmente el atributo `name` de los selectores visibles y capturan valores desde `<input type="hidden">`. Envia JSON puro al backend.

---

## 8. Integracion Contable (Modelo Pull)

Las apps fuente nunca importan de `contabilidad`. El `Contabilizador` extrae activamente via extractores en `contabilidad/integracion/extractores/`.

```
ExtractorGastos / ExtractorFacturas / ExtractorInventario / ExtractorNomina
    → Contabilizador(empresa_id).contabilizar(TransaccionEconomica DTO)
    → AsientoContable + MovimientoContable (atomico)
```

- DTOs inmutables (`@dataclass(frozen=True)`)
- Idempotencia via constraint UNIQUE en `documento_origen`
- Numero de asiento: `ASI-{YYYYMMDD}-{UUID8}`
- Activacion: `python manage.py backfill_asientos_gastos [--dry-run]` o Celery

---

## 9. Aplicaciones y Documentacion por App

### Esquema Public (`SHARED_APPS`)

Documento de referencia unico para todo el esquema public: [`FLUJO_APLICACION_PUBLIC_v3.3.md`](../apps/public/FLUJO_APLICACION_PUBLIC_v3.3.md)

| App | Ruta | Responsabilidad |
|---|---|---|
| `accounts` | `apps/public/accounts/` | Modelo `User` global (AbstractUser), creacion y actualizacion de usuarios |
| `tenants` | `apps/public/tenants/` | `Client` (django-tenants), `TenantMembership`, invitaciones OTT |
| `impuestos` | `apps/public/impuestos/` | Catalogo DIAN: tarifas IVA, retenciones, RetencionICA |
| `console` | `apps/public/console/` | Consola admin: crear tenants, gestionar membresias, JWT bridge |
| `core` (public) | `apps/public/core/` | Middleware de resolucion de tenant, infraestructura compartida |

### Esquema Tenant (`TENANT_APPS`)

| App | Ruta | Responsabilidad | Documento de auditoria |
|---|---|---|---|
| `core` | `apps/tenant/core/` | UI Shell, bridge cross-schema, onboarding, auth JWT | [`AUDITORIA_FLUJO_CORE.md`](../apps/tenant/core/AUDITORIA_FLUJO_CORE.md) |
| `empresa` | `apps/tenant/empresa/` | Datos fiscales, logo, configuracion del tenant | [`AUDITORIA_EMPRESA.md`](../apps/tenant/empresa/AUDITORIA_EMPRESA.md) |
| `perfil` | `apps/tenant/perfil/` | `TenantProfile` — rol del usuario dentro del tenant | [`AUDITORIA_FLUJO_COMPLETO.md`](../apps/tenant/perfil/AUDITORIA_FLUJO_COMPLETO.md) |
| `facturas` | `apps/tenant/facturas/` | Facturacion electronica DIAN (XML, envio, estados) | [`AUDITORIA_FLUJO_COMPLETO_FACTUR.md`](../apps/tenant/facturas/AUDITORIA_FLUJO_COMPLETO_FACTUR.md) |
| `contabilidad` | `apps/tenant/contabilidad/` | PUC NIIF, asientos, movimientos, extractores Pull | [`AUDITORIA_COMPLETA_CONTABILIDAD.md`](../apps/tenant/contabilidad/AUDITORIA_COMPLETA_CONTABILIDAD.md) · [`AUDITORIA_FLUJO_COMPLETO.md`](../apps/tenant/contabilidad/AUDITORIA_FLUJO_COMPLETO.md) |
| `gastos` | `apps/tenant/gastos/` | DocumentoSoporte, gastos operativos | [`AUDITORIA_FLUJO_COMPLETO_GASTOS.md`](../apps/tenant/gastos/AUDITORIA_FLUJO_COMPLETO_GASTOS.md) |
| `inventario` | `apps/tenant/inventario/` | Productos, servicios, kardex, movimientos | [`AUDITORIA_INVENTARIO.md`](../apps/tenant/inventario/AUDITORIA_INVENTARIO.md) |
| `empleados` | `apps/tenant/empleados/` | Nomina, devengos, empleados | [`AUDITORIA_COMPLETA_EMPLEADOS.md`](../apps/tenant/empleados/AUDITORIA_COMPLETA_EMPLEADOS.md) |
| `cotizaciones` | `apps/tenant/cotizaciones/` | Cotizaciones comerciales, items | [`AUDITORIA_FLUJO_COMPLETO.md`](../apps/tenant/cotizaciones/AUDITORIA_FLUJO_COMPLETO.md) |
| `clientes` | `apps/tenant/clientes/` | CRM basico, terceros clientes | [`AUDITORIA_FLUJO_CLIENTES.md`](../apps/tenant/clientes/AUDITORIA_FLUJO_CLIENTES.md) |
| `proveedores` | `apps/tenant/proveedores/` | Terceros proveedores | [`AUDITORIA_FLUJO_COMPLETO_PROVE.md`](../apps/tenant/proveedores/AUDITORIA_FLUJO_COMPLETO_PROVE.md) |
| `proyectos` | `apps/tenant/proyectos/` | Gestion de proyectos | [`AUDITORIA_FLUJO_COMPLETO.md`](../apps/tenant/proyectos/AUDITORIA_FLUJO_COMPLETO.md) |
| `landing` | `apps/tenant/landing/` | Pagina publica estatica del tenant | [`AUDITORIA_FLUJO_COMPLETO.md`](../apps/tenant/landing/AUDITORIA_FLUJO_COMPLETO.md) |

> **Regla obligatoria (AGENTS.md §16):** antes de modificar cualquier app, leer su documento de auditoria listado arriba. Si no existe documento, solicitar autorizacion explicita al usuario antes de proceder.

---

## 10. Comandos Esenciales

```bash
# Docker
make up                  # Levantar servicios (web:8000, db:5432, redis:6379, celery)
make down                # Detener
make logs                # Tail logs del contenedor web
make shell               # Shell en el contenedor web

# Migraciones multi-tenant
make migrate-tenants     # Todos los esquemas tenant
make migrate-shared      # Esquema public
make makemigrations      # Crear migraciones
make check-migrations    # Verificar pendientes

# Calidad de codigo
make audit               # ruff + bandit + django check
make ruff                # Lint + autofix (line-length 100, py3.12)
make bandit              # Escaneo de seguridad

# Tests
make test                # Todos los tests (pytest)
make smoke               # Suite de smoke tests

# Contabilidad
python manage.py seed_reglas_contables
python manage.py poblar_catalogo_niif
python manage.py backfill_asientos_gastos [--dry-run] [--empresa-id N]

# Tenant
make crear-empresa NOMBRE="Acme" DOMINIO="acme" EMAIL="admin@acme.com"
docker compose exec web python manage.py createsuperuser

# Validacion pre-PR (obligatorio)
python -m py_compile <archivo.py>
```

---

## 11. Principios No Negociables

Ver `AGENTS.md` para el detalle completo. Resumen:

| Regla | Detalle |
|---|---|
| Sin emojis en `.py` | Causan `SyntaxError` → Django 500 |
| `SintelTenantBaseModel` | Todos los modelos tenant heredan de este, nunca de `models.Model` |
| `empresa_id` en toda query | Sin `.all()` ni `.filter()` sin `empresa_id` |
| `.only()` obligatorio | Toda queryset especifica campos. `queryset = Model.objects.none()` en clase |
| Sin Signals para logica de negocio | Todo en Service Layer |
| Sin `.py` nuevos fuera del Service Layer | Requiere autorizacion explicita |
| `apps/public/` bloqueado | Requiere RFC + `needs-admin-approval` |
| UUID como lookup field | `BaseTenantViewSet` expone UUID, nunca PK entero |
| FK a `perfil.TenantProfile` | Nunca FK a `settings.AUTH_USER_MODEL` desde modelos tenant |
| Karpathy: cambios quirurgicos | Tocar solo lo necesario. Pensar antes de codificar. Objetivos verificables |
