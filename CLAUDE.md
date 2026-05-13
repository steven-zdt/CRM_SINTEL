# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Before any change:** read `AGENTS.md` (root) and the app's `AUDITORIA_FLUJO_COMPLETO.md` if it exists. Read `MEMORY.md` for current project state and active ADRs.

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
