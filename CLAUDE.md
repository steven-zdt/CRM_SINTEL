# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**`AGENTS.md` (root) is the canonical, exhaustive source for architecture and rules.** This file is a short, Claude-Code-specific operational reference (commands + quick-lookup pointers) — kept intentionally small to avoid drifting out of sync with `AGENTS.md` (DOC-M3, `PLAN_UNICO_CORRECCIONES.md` Fase 9). If anything below conflicts with `AGENTS.md`, `AGENTS.md` wins — update this file to match, not the other way around.

> **Before any change:** read `AGENTS.md` and the app's `.agent/` audit doc (exact filename varies per app — see `documentacion/arquitectura_general.md` §10.2). Read `MEMORY.md` for current project state and active ADRs. Check `docs/ADR-*.md` for architectural decisions (**ADR-001-retention-pull-model.md**, **ADR-002-public-schema-api-dual-registration.md**).

---

## Commands

### Docker (development)
```bash
make up          # Start all services (web:8000, db:5432, redis:6379, celery)
make down        # Stop containers (keeps data volumes)
make down-full   # Stop AND wipe data volumes — asks for confirmation
make logs        # Tail web container logs
make shell       # Shell into web container
```

### Database migrations (multi-tenant)
```bash
make migrate-shared    # Public schema
make migrate-tenants   # All tenant schemas
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
**Testing Progresivo por Alcance (norma permanente, AGENTS.md §24.0):** escalar
`test específico → componente → app → integración → suite global`. NUNCA correr `make test`
(suite completa) por defecto tras un cambio pequeño — reservarlo para cierres de fase, cambios
transversales (`apps/tenant/api/`, `apps/tenant/core/`, mixins heredados por 3+ apps) o releases.
Correr varias suites acotadas en paralelo dentro del contenedor está permitido cuando conviene.
Nota técnica real (no una preferencia): todas las corridas de `pytest` comparten la misma base
de datos de test (`test_sintel`, alias `default`) — pytest-django la crea/destruye al arrancar,
así que dos corridas simultáneas SÍ chocan ahí ("database test_sintel is being accessed by other
users"), sin importar en qué schema/tenant trabaje cada una. Si conviene paralelismo real, usar
`--reuse-db`/`--keepdb` o serializar; si no, ejecutar una corrida a la vez.

### Code quality
```bash
make audit      # Full audit: ruff + bandit + pip-audit + django check + static check
make ruff       # Lint + autofix (line-length 100, target py3.12)
make bandit     # Security scan (static)
make pip-audit  # Dependency vulnerability scan
make dj-check   # Django system check
```

### One-off management commands (inside container)
```bash
docker compose exec web python manage.py migrate_schemas --shared
docker compose exec web python manage.py createsuperuser
make crear-empresa NOMBRE="Acme" DOMINIO="acme" EMAIL="admin@acme.com"
```

---

## Architecture — quick map (full detail lives in AGENTS.md)

### Multi-tenant via PostgreSQL schemas (django-tenants)

- **Public schema** — `apps/public/`: shared accounts, tenant registry, DIAN catalog, admin console.
- **Tenant schemas** — `apps/tenant/`: one isolated PostgreSQL schema per company.
- **Tenant resolution:** middleware maps hostname → schema. `config/urls_public.py` (public) / `config/urls_tenant.py` (tenant). API routes in `config/api_urls.py`.
- **`home.sintel.net.co` vs `acme.sintel.net.co` dual-registration rule (ADR-002):** any endpoint reachable from a static page on the public domain must be registered in both URL confs, with tenant resolved from the JWT/session payload on the public side. See `docs/ADR-002-public-schema-api-dual-registration.md` for the full checklist — do not re-derive it from memory.

### Feature-Sliced Design (FSD) — one ecosystem per model

```
apps/tenant/<app>/
  models.py
  services/
    __init__.py          # re-exports main classes
    crud_service.py      # DB persistence only, @transaction.atomic
    business_service.py  # business rules + Double Semantic Verification (IDOR)
    selectors.py         # read-only QuerySets with .only(), LIST_FIELDS/DETAIL_FIELDS
    api_mixins.py         # <Model>ServiceMixin injected into ViewSet
  api/
    viewsets.py          # inherits BaseTenantViewSet + ServiceMixin
    serializers.py
    urls.py
  templates/tenant/<app>/          # prefix 'tenant/' is mandatory
    offcanvas_crear_<model>.html
    offcanvas_editar_<model>.html
    list_<model>.html
    partials/
  static/<app>/js/
    <app>.api.js         # SSoT for all endpoint URLs
    features/<model>_list.js
    features/<model>_editor.js
```

Service Layer flow (unidirectional): `ViewSet` → `ServiceMixin` → `business_service.py` (rules + DSV) → `crud_service.py` (DB write) → response. Full detail: AGENTS.md §5 (CRUD-E2E), §7 (FSD).

### Authentication — Dual-Auth (JWT + Session)

- `BaseTenantViewSet` sets `[JWTAuthentication, SessionAuthentication]` — **never override in child ViewSets**.
- Permissions: import **only** from `apps.tenant.api.permissions`.
- JWT in frontend: `window.jwtAuth?.getAccessToken?.()` — `window.jwtAuth.token` does **not** exist.
- Full detail: AGENTS.md §15 (SECURITY).

### Cross-schema bridge

Tenant apps **must not** import from `apps.public.*` directly (except `apps.tenant.core`/`apps.tenant.api`). Use `apps.tenant.core.services.membership`. Full detail: AGENTS.md §17 (BRIDGE).

### Accounting integration (Pull Model)

Never create `AsientoContable`/`MovimientoContable`/retention amounts directly from source apps. Contabilidad owns the ledger and the Chart of Accounts (`APP_ORIGEN_PREFIJOS` in `contabilidad/services/selectors.py`); source apps read via `RetencionesService`/extractors, never write directly. Full detail, code examples, and the retenciones-selectores UI pattern: AGENTS.md §18 (CONTAB), `docs/ADR-001-retention-pull-model.md`.

### Frontend

- **No build step.** CDN libraries: Bootstrap 5.3.2, HTMX 1.9.10, Bootstrap Icons, Font Awesome. Alpine.js 3.x available via CDN but **not part of the approved standard** — prefer Vanilla JS ES6+ namespaced modules (`window.Sintel.<App>`).
- **Grids:** migrating from Tabulator to server-rendered `django-tables2` + HTMX (`PLAN_UNICO_CORRECCIONES.md` Fase 5-BIS) — check `documentacion/PLAN_UNICO_CORRECCIONES.md` §"FASE 5-BIS" for which apps have migrated before assuming either pattern for a given app.
- **Offcanvas:** always via `window.Sintel.Core.mostrarOffcanvasSeguro(el)` (`core/js/common/offcanvas.helper.js`) — never `bootstrap.Offcanvas.getOrCreateInstance()`. Full detail: AGENTS.md §26 (HTMX-OFFCANVAS).
- **Console (public):** HTMX for server-driven fragments.
- Static files served by WhiteNoise in production; `collectstatic` runs automatically on container start.

---

## Non-negotiable rules — quick lookup

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
| **`parseInt()` on UUID** | PROHIBITED — corrupts the UUID to a partial integer. |
| **`getOrCreateInstance().show()` on Offcanvas** | PROHIBITED — accumulates backdrops. Use `mostrarOffcanvasSeguro(el)`. |
| **`py_compile` hook** | A PostToolUse hook runs `python -m py_compile` after every `.py` edit. Fix `SyntaxError` before continuing. |

### Karpathy Principles (Caution over Speed)

- **Think Before Coding**: Don't assume. Ask if uncertain. Surface tradeoffs.
- **Simplicity First**: Minimum code. No speculative abstractions. If 200 lines can be 50, rewrite.
- **Surgical Changes**: Touch only what you must. Match existing style. Don't "improve" adjacent code.
- **Goal-Driven Execution**: Define success criteria. Use loops with verification: `Step → verify`.

Full rules and patterns: **`AGENTS.md`** (canonical source) — sections are tagged (`[SECURITY]`, `[CONTAB]`, etc.) and cross-referenced from `documentacion/arquitectura_general.md`.
