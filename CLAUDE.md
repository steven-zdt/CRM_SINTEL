# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Before any change:** read `AGENTS.md` (root) and the app's `AUDITORIA_FLUJO_COMPLETO.md` if it exists. Read `MEMORY.md` for current project state and active ADRs. Check `docs/ADR-*.md` for architectural decisions (e.g., **ADR-001-retention-pull-model.md** for Retencion Pull Model).

---

## Commands

### Docker (development)
```bash
make up          # Start all services (web:8000, db:5432, redis:6379, celery)
make down        # Stop and remove containers
make logs        # Tail web container logs
make shell       # Shell into web container
```

### Database migrations (multi-tenant)
```bash
make migrate-shared    # Public schema (--fake-initial)
make migrate-tenants   # All tenant schemas (--fake-initial)
make makemigrations    # Create migration files
make check-migrations  # Verify no pending migrations
```

### Tests
```bash
make test                        # All tests (pytest inside Docker)
make test-file FILE="path/to/test_file.py"   # Single file
make test-ingesta / test-etl / test-api      # Phase-specific
make smoke                       # Smoke test suite
```

### Code quality
```bash
make audit    # Full audit: ruff + bandit + django check + static check
make ruff     # Lint + autofix (line-length 100, target py3.12)
make bandit   # Security scan
make dj-check # Django system check
```

### One-off management commands (inside container)
```bash
docker compose exec web python manage.py migrate_schemas --shared
docker compose exec web python manage.py createsuperuser
make crear-empresa NOMBRE="Acme" DOMINIO="acme" EMAIL="admin@acme.com"
```

---

## Architecture

### Multi-tenant via PostgreSQL schemas (django-tenants)

- **Public schema** — `apps/public/`: shared user accounts (`accounts.User`), tenant registry (`tenants.Client`), DIAN catalog (`impuestos`), admin console (`console`).
- **Tenant schemas** — `apps/tenant/`: one isolated PostgreSQL schema per company. Main apps: `empresa`, `facturas`, `contabilidad`, `inventario`, `empleados`, `gastos`, `cotizaciones`, `proveedores`, `clientes`, `proyectos`, `dashboard`, `perfil`, `core`.
- **Tenant resolution:** middleware maps hostname → schema. Admin domain → public; subdomains → tenant.
- **URL configs:** `config/urls_public.py` (ROOT_URLCONF) and `config/urls_tenant.py` (TENANT_URLCONF). API routes in `config/api_urls.py`.

### Feature-Sliced Design (FSD) — one ecosystem per model

Each tenant app is structured as:
```
apps/tenant/<app>/
  models.py
  services/
    __init__.py          # re-exports main classes
    crud_service.py      # DB persistence only, @transaction.atomic
    business_service.py  # business rules + Double Semantic Verification (IDOR)
    selectors.py         # read-only QuerySets with .only(), LIST_FIELDS/DETAIL_FIELDS
    api_mixins.py        # <Model>ServiceMixin injected into ViewSet
    services.py          # stable facade re-exporting business_service
  api/
    viewsets.py          # inherits BaseTenantViewSet + ServiceMixin
    serializers.py
    urls.py
  templates/tenant/<app>/          # prefix 'tenant/' is mandatory
    offcanvas_crear_<model>.html
    offcanvas_editar_<model>.html
    offcanvas_detalle_<model>.html
    list_<model>.html
    partials/
  static/<app>/js/
    <app>.api.js         # SSoT for all endpoint URLs
    features/<model>_list.js
    features/<model>_editor.js
```

### Service Layer flow (unidirectional)

`ViewSet` → `ServiceMixin.service_crear_*()` → `business_service.py` (rules + DSV) → `crud_service.py` (DB write) → JSON / HTMX OOB response → frontend Tabulator `.replaceData()`.

### Authentication — Dual-Auth (JWT + Session)

- `BaseTenantViewSet` sets `[JWTAuthentication, SessionAuthentication]` — **never override in child ViewSets**.
- JWT endpoints: `POST /api/token/`, `/api/token/refresh/`, `/api/token/verify/`.
- Bridge session→JWT: `GET /api/v1/core/auth/from-session/`.
- Roles SSoT: `TenantProfile.rol` (`ADMIN` / `OPERADOR` / `VISOR`) in `apps/tenant/perfil/`.
- Permissions: import **only** from `apps.tenant.api.permissions` (`IsTenantMember`, `IsTenantAdminOrReadOnly`, etc.).

### Cross-schema bridge

Tenant apps **must not** import from `apps.public.*` directly (except `apps.tenant.core` and `apps.tenant.api`). Use the bridge:
```python
from apps.tenant.core.services.membership import check_membership  # correct
from apps.public.tenants.models import TenantMembership            # BLOCKED
```

### Accounting integration

Never create `AsientoContable` or `MovimientoContable` directly from source apps. Contabilidad uses a **Pull Model**: extractors inside `contabilidad/integracion/extractores/` read source apps — source apps never import from `contabilidad`.

#### Asientos (General Ledger)

Trigger extraction via management command or Celery task:
```bash
python manage.py backfill_asientos_gastos [--dry-run] [--empresa-id N]
```

If you need to contabilize programmatically within `contabilidad` itself:
```python
from apps.tenant.contabilidad.integracion.contabilizador import Contabilizador
from apps.tenant.contabilidad.integracion.dtos import TransaccionEconomica
contabilizador = Contabilizador(empresa_id)
asiento = contabilizador.contabilizar(dto)  # TransaccionEconomica DTO
```

#### Retenciones (Tax Withholdings) — v3.7.1+

**Contabilidad owns Retencion model** (see **ADR-001**). Never store retention amounts in source apps (Facturas, Gastos, etc.). Use Pull Model:

**From Source Apps (Facturas, Gastos):**
```python
# Delegate to Contabilidad API
from apps.tenant.contabilidad.services.retenciones_service import RetencionesService

# 1. Get retention config for a client/vendor
retenciones = RetencionesService.obtener_retenciones_desde_tercero(
    nit='123456789',
    tipo_tercero='CLIENTE',  # or 'PROVEEDOR'
    naturaleza='VENTA',      # or 'COMPRA'
)
# Returns dict: {'aplica_retefuente': True, 'retefuente_porcentaje': Decimal('2.50'), ...}

# 2. Create retention records (auto-generated when you call this)
retencion = RetencionesService.crear_retencion(
    empresa=empresa,
    tipo='RETEFUENTE',          # or 'RETEICA', 'RETEIVA'
    porcentaje=Decimal('2.50'),
    monto=Decimal('125.00'),
    documento_origen_app='facturas',
    documento_origen_modelo='Factura',
    documento_origen_id=factura.id,
)

# 3. Query existing retentions for a document
retenciones = RetencionesService.listar_retenciones_por_documento(
    documento_origen_app='facturas',
    documento_origen_modelo='Factura',
    documento_origen_id=factura.id,
)
```

**Backward Compatibility (v3.7.1 only):**
```python
# Old code still works via @property (reads Retencion table)
factura.total_retencion_fuente        # Returns Decimal('125.00') via @property
factura.retefuente                    # DEPRECATED — marked editable=False

# Serializers auto-compute from @property, so API unchanged
# {
#   "id": 1,
#   "retefuente": "125.00",      # Reads from Retencion records
#   "reteica": "0.00",
#   ...
# }
```

**API Endpoints:**
- `GET /api/v1/contabilidad/retenciones/obtener-por-tercero/?nit=&tipo_tercero=&naturaleza=`
- `GET /api/v1/contabilidad/retenciones/obtener-por-documento/?app=&modelo=&id=`
- `GET /api/v1/contabilidad/retenciones/` (list with filters)
- `POST /api/v1/contabilidad/retenciones/` (create)

**Deprecation Timeline:**
- **v3.7.1 (NOW):** Fields marked `editable=False`, use RetencionesService
- **v3.8.x (2026-06/07):** Users upgrade, @property methods read from Retencion
- **v3.9.0 (2026-08):** Fields removed (see FASE_10_CLEANUP_PLAN.md)

#### Selectores de Retenciones en Gastos — v3.7.3+

**New Feature (v3.7.3):** User selects retention type (Retefuente, ReteICA) via dropdown in "Nuevo Gasto" / "Editar Gasto" forms. Amounts calculated automatically.

**Architecture:**
- **SSoT (Single Source of Truth):** `DocumentoSoporte.RETEFUENTE_CHOICES` and `RETEICA_CHOICES` in `apps/tenant/gastos/models.py`
- **Frontend:** Options replicated in both templates (for rendering, not persistence)
  - `apps/tenant/gastos/templates/tenant/gastos/offcanvas_crear_gasto.html` (lines ~154-170)
  - `apps/tenant/gastos/templates/tenant/gastos/offcanvas_editar_gasto.html` (lines ~144-160)
- **JavaScript:** Listeners on `#retefuente_select` and `#reteica_select`, store value in hidden inputs (`#retefuente_porcentaje`, `#reteica_porcentaje`)

**Critical Rule — Keep CHOICES Synchronized:**
```
If you modify RETEFUENTE_CHOICES or RETEICA_CHOICES in models.py,
you MUST update the <option> elements in BOTH templates to match exactly.

models.py:
    ('0.11', '11% - Honorarios y Consultoria (Declarante)')
    ↓
offcanvas_crear_gasto.html:
    <option value="0.11">11% - Honorarios y Consultoria (Declarante)</option>
    ↓
offcanvas_editar_gasto.html:
    <option value="0.11">11% - Honorarios y Consultoria (Declarante)</option>
```

**How It Works:**
1. User selects Retefuente type from dropdown (value = percentage like `0.11`)
2. JavaScript listener updates hidden input `#retefuente_porcentaje` = `0.11`
3. `calcularTotales()` runs: `monto = subtotal × porcentaje / 100`
4. Display updates (readonly): `#retefuente_display` → `$55,000`
5. On save: backend receives `subtotal`, `total`, and creates `Retencion` records via Pull Model

**For Full Details & Maintenance Guide:** See `RETENCIONES_SELECTORES_GUIDE.md` (root) and memory file `retenciones_selectores_v373.md`.

#### Editar Empleado — Guardar Cambios (v3.7.4)

**Fixed (v3.7.4):** Editar Empleado now saves changes correctly. Previously, the form button had no listener and form had `onsubmit="return false;"` blocking submission.

**How It Works:**
1. User opens edit form → `offcanvas-empleado` has `data-empleado-uuid`
2. User modifies fields and clicks "Actualizar Empleado"
3. JavaScript `submitEmpleado()` function:
   - Validates required fields
   - Collects form data
   - Sends PATCH request to `/api/v1/empleados/{uuid}/` with CSRF token
   - On success: closes offcanvas, shows notification, reloads table
   - On error: shows error message, allows retry
4. Backend processes PATCH and returns updated employee

**For Guarantee & Testing Guide:** See `EMPLEADO_EDIT_FIX_GUARANTEE.md` (root) with:
- Complete testing checklist
- Troubleshooting guide
- Files modified and what changed
- Technical stack explanation

#### PUC Code Linking — APP_ORIGEN_PREFIJOS (Single Source of Truth)

**Critical Rule:** All accounting code prefixes (Plan de Cuentas) for **ALL business apps** must come ONLY from:
```
apps/tenant/contabilidad/services/selectors.py:APP_ORIGEN_PREFIJOS
```

**Why:** Contabilidad owns the Chart of Accounts. Other apps read from it (Pull Model). Never hardcode prefixes in source apps.

**Correct Usage — Backend:**
```python
from apps.tenant.contabilidad.services.selectors import (
    APP_ORIGEN_PREFIJOS,
    filtrar_cuentas_por_app_origen
)

# Get prefixes for an app
prefijos = APP_ORIGEN_PREFIJOS['inventario']  # ['143505', '143510', ..., '51', '15']

# Filter cuentas by app origin (automatic at ViewSet level)
qs = filtrar_cuentas_por_app_origen(queryset, 'gastos')  # Only '233505', '2365', '51', '6', etc.
```

**Correct Usage — Frontend:**
```javascript
// inventario.api.js
searchCuentas: async (query, options = {}) => {
  const params = {
    search: query,
    app_origen: 'inventario',  // Backend resolves allowed prefixes
    codigo_prefix: options.codigoPrefix  // e.g., '51' for depreciation
  };
  return w.http('GET', '/api/v1/contabilidad/cuentas-contables/', params);
}
```

**Forbidden — Never Hardcode:**
```python
# ❌ WRONG — Scattered hardcoded prefixes
GASTOS_PREFIJOS = ['51', '52', '53']  # In gastos/models.py
FACTURAS_PREFIJOS = ['4135', '4175']   # In facturas/api/viewsets.py

# ✅ RIGHT — Always centralized
from apps.tenant.contabilidad.services.selectors import APP_ORIGEN_PREFIJOS
```

See **AGENTS.md § 18.7** for full governance rules, audit procedures, and update workflow.

### Frontend

- **No build step.** CDN libraries: Bootstrap 5.3.2, HTMX 1.9.10, Tabulator 6.2.5, Bootstrap Icons, Font Awesome. Alpine.js 3.x is available via CDN but **not part of the approved standard** — prefer Vanilla JS ES6+ namespaced modules (`window.Sintel.<App>`).
- **Tenant apps:** Fetch API via unified `http.js` client → DRF JSON endpoints. Tabulator for grids.
- **Console (public):** HTMX for server-driven fragments.
- JWT in frontend: `window.jwtAuth?.getAccessToken?.()` — the property `window.jwtAuth.token` does **not** exist.
- Static files served by WhiteNoise in production; `collectstatic` runs automatically on container start.

---

## Non-negotiable rules

### 4.5. Karpathy Principles (Caution over Speed)

- **Think Before Coding**: Don't assume. Ask if uncertain. Surface tradeoffs.
- **Simplicity First**: Minimum code. No speculative abstractions. If 200 lines can be 50, rewrite.
- **Surgical Changes**: Touch only what you must. Match existing style. Don't "improve" adjacent code.
- **Goal-Driven Execution**: Define success criteria. Use loops with verification: `Step → verify`.

| Rule | Detail |
|---|---|
| **No emojis in `.py`** | Causes `SyntaxError` → Django 500. Plain ASCII only. |
| **`SintelTenantBaseModel`** | All tenant models inherit from `apps.tenant.core.models.SintelTenantBaseModel`, never `models.Model`. |
| **`empresa_id` in every query** | All tenant ORM queries must filter by `empresa_id`. No bare `.all()` or unguarded `.filter()`. |
| **`.only()` / `.defer()` required** | Every queryset must specify fields. `queryset = Model.objects.none()` at class level; populate in `get_queryset()`. |
| **No Signals for business logic** | Use Service Layer exclusively. |
| **No new `.py` outside Service Layer** | Requires explicit user authorization. |
| **`apps/public/` is blocked** | Requires RFC + `needs-admin-approval` label. Hooks enforce this automatically. |
| **UUID lookup, not PK** | `BaseTenantViewSet` sets `lookup_field = "uuid"`. Inherit it; don't expose integer PKs in URLs. |
| **FK to `perfil.TenantProfile`** | Never FK to `settings.AUTH_USER_MODEL` from tenant models. |
| **`py_compile` hook** | A PostToolUse hook runs `python -m py_compile` after every `.py` edit. Fix `SyntaxError` before continuing. |

Full rules and patterns: **`AGENTS.md`** (canonical source).
