# SINTEL ERP — GitHub Copilot Instructions v2.62.0

These rules are STRICT and MANDATORY for all code suggestions in this project.

## ABSOLUTE PROHIBITIONS

- **NO emojis or Unicode special characters in any `.py` file** — causes Django 500 errors
- **NO `from apps.public.*` imports in any tenant app** except `apps.tenant.core` and `apps.tenant.api`
- **NO creating `AsientoContable` or `MovimientoContable` directly** — always via `Contabilizador`
- **NO Django Signals for business logic** — use Service Layer only
- **NO `.all()` or `.filter()` without `.only()` or `.defer()`** — Zero Waste ORM rule
- **NO querying models without `empresa_id` filter** in TENANT_APPS
- **NO `models.Model` inheritance** — always use `SintelTenantBaseModel`
- **NO new `.py` files outside the Service Layer structure** without explicit user authorization
- **NO modifying `apps/public/`** without RFC + Issue + `needs-admin-approval` label
- **NO `views.py` for business logic** — use ViewSet + ServiceMixin pattern

## STACK (no alternatives allowed without authorization)

Backend: Python + Django + DRF + django-tenants + PostgreSQL + Celery
Frontend: HTMX + Vanilla JS ES6+ (namespace `window.Sintel.<App>`) + Bootstrap 5 + Tabulator

## ARCHITECTURE — Service Layer Pattern

Every tenant app MUST follow this structure:

```
apps/tenant/<app_name>/
├── services/
│   ├── __init__.py          # Re-exports main classes
│   ├── crud_service.py      # Pure DB persistence (@transaction.atomic). NO business logic.
│   ├── business_service.py  # Business rules + Double Semantic Verification (IDOR prevention)
│   ├── selectors.py         # Read-only QuerySets with .only(). Defines LIST_FIELDS, DETAIL_FIELDS.
│   ├── api_mixins.py        # <Model>ServiceMixin injected into ViewSet
│   └── services.py          # Facade re-exporting from business_service.py
├── api/
│   └── viewsets.py          # ViewSet inherits BaseTenantViewSet + <Model>ServiceMixin
├── templates/tenant/<app_name>/   # prefix 'tenant/' is MANDATORY
│   ├── list_<model>.html
│   ├── offcanvas_crear_<model>.html
│   ├── offcanvas_editar_<model>.html
│   └── offcanvas_detalle_<model>.html
└── static/<app_name>/js/
    ├── <app>.api.js         # SSoT for all endpoint URLs
    └── features/
        ├── <model>_list.js
        └── <model>_editor.js
```

## MODELS

```python
# CORRECT
from apps.tenant.core.models import SintelTenantBaseModel

class MyModel(SintelTenantBaseModel):
    # empresa, created_at, updated_at injected automatically
    ...

# WRONG — NEVER do this
class MyModel(models.Model): ...
```

## VIEWSET PATTERN

```python
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.permissions import IsTenantMember, IsTenantAdminOrReadOnly

class MyModelViewSet(MyModelServiceMixin, BaseTenantViewSet):
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    lookup_field = "uuid"
    queryset = MyModel.objects.none()  # always none() at class level

    def get_queryset(self):
        return self.get_qs_list()  # via ServiceMixin
```

## QUERYSET PATTERN

```python
# CORRECT
MyModel.objects.filter(empresa_id=empresa_id).only('id', 'uuid', 'nombre')

# WRONG — NEVER
MyModel.objects.all()
MyModel.objects.filter(empresa_id=empresa_id)  # missing .only()
```

## ACCOUNTING INTEGRATION

```python
# CORRECT — always via Contabilizador
from apps.tenant.contabilidad.services.asientos_service import materializar_asiento_desde_gasto
asiento = materializar_asiento_desde_gasto(gasto)  # accepts object, not ID

# WRONG — NEVER create directly
AsientoContable.objects.create(...)
```

## SECURITY — Double Semantic Verification (DSV)

All mutation endpoints MUST validate that FK entities belong to the current tenant:
```python
# In business_service.py
def crear_modelo(self, empresa_id, data):
    # Validate FKs belong to this tenant
    if not RelatedModel.objects.filter(empresa_id=empresa_id, id=data['related_id']).exists():
        raise ValidationError("IDOR: entity does not belong to tenant")
```

## JWT AUTHENTICATION (Frontend)

```javascript
// CORRECT
const token = window.jwtAuth?.getAccessToken?.();
if (token) { headers['Authorization'] = `Bearer ${token}`; }

// WRONG — .token property does NOT exist
window.jwtAuth.token
```

## CROSS-SCHEMA ACCESS (Bridge Pattern)

```python
# CORRECT — use the bridge
from apps.tenant.core.services.membership import check_membership

# WRONG — direct import from public schema
from apps.public.tenants.models import TenantMembership  # BLOCKED
```
