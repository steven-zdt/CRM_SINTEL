---
name: sintel-add-association
description: Add or update optional cross-app associations in the SINTEL Django tenant codebase from model to dashboard UI. Use when a task asks to link one tenant model to another, expose a new relationship in DRF serializers/viewsets/services, validate tenant ownership, add list/detail/editor UI controls, or replicate the Factura-Cotizacion style association pattern for any app.
---

# SINTEL Add Association

Use this skill to implement an association between two tenant app models end to end. Follow the local `AGENTS.md` rules first, then use this workflow as the operational checklist.

## Quick Pattern

For an optional non-strict relation like `Factura -> Cotizacion`:

```python
target = models.ForeignKey(
    'target_app_label.TargetModel',
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name='source_items',
)
```

Use Django's installed app label for lazy references, not the Python package name when the app overrides `AppConfig.label`. Example: cotizaciones uses `tenant_cotizaciones.Cotizacion`.

## Required First Steps

1. Read the app SSoT document in `apps/tenant/<source_app>/.agent/` before editing.
2. Inspect the source app service layer, serializer, viewset, templates, and JS modules.
3. Confirm whether the relation is optional (`SET_NULL`) or strict (`PROTECT`/`CASCADE`). Prefer optional `SET_NULL` for operational links that should not destroy historical records.
4. Check `apps/tenant/<target_app>/apps.py` for the real app label.
5. Avoid direct `apps.public` imports and keep all tenant mutations filtered by `empresa_id`.

## Backend Workflow

### 1. Model

Add the relation in the source model with a lazy string reference:

```python
association_field = models.ForeignKey(
    'target_app_label.TargetModel',
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name='source_model_plural',
    verbose_name=_('Target label'),
)
```

Do not import the target model at module import time unless the codebase already requires it. Generate migrations after the edit.

### 2. Selectors

Keep serializer fields and ORM optimization fields separate.

```python
LIST_FIELDS = (
    "id",
    "uuid",
    "association_field_id",
)

DETAIL_FIELDS = (
    "id",
    "uuid",
    "association_field_id",
)

ASSOCIATION_ONLY_FIELDS = (
    "association_field__id",
    "association_field__uuid",
    "association_field__display_code",
)
```

Use related fields only inside `.only()`, never inside serializer `Meta.fields`.

```python
qs = SourceModel.objects.select_related("association_field").only(
    *LIST_FIELDS,
    *ASSOCIATION_ONLY_FIELDS,
)
```

If using `select_related("other_relation")`, include minimal `other_relation__...` fields too. Django raises `FieldError` if a traversed relation is deferred.

### 3. CRUD Service

Add a transactional persistence method:

```python
@staticmethod
@transaction.atomic
def vincular_target(source: SourceModel, target) -> SourceModel:
    source.association_field = target
    source.save(update_fields=['association_field'])
    return source
```

Use the real field name in `update_fields`. Add `updated_at` only if the product expects this link to count as a normal edit.

### 4. Business Service

Resolve the target lazily and apply DSV:

```python
@staticmethod
def vincular_target(source: SourceModel, target_uuid: str | None, empresa_id: int) -> SourceModel:
    from rest_framework.exceptions import ValidationError
    from apps.tenant.target_app.models import TargetModel

    if source.empresa_id != empresa_id:
        raise ValidationError({"detail": "El registro no pertenece a la empresa activa."})

    if target_uuid in (None, ""):
        return SourceCRUDService.vincular_target(source, None)

    target = TargetModel.objects.filter(
        uuid=target_uuid,
        empresa_id=empresa_id,
    ).only("id", "uuid", "empresa_id", "display_code").first()

    if not target or target.empresa_id != source.empresa_id:
        raise ValidationError({
            "target_uuid": "El registro vinculado no existe o no pertenece a la empresa activa."
        })

    return SourceCRUDService.vincular_target(source, target)
```

### 5. API Mixin

Expose the service through the app service mixin:

```python
def service_vincular_target(self, source, target_uuid, empresa_id):
    return SourceBusinessService.vincular_target(source, target_uuid, empresa_id)
```

### 6. Serializers

Expose read info and optional write UUID.

```python
target_vinculado_info = serializers.SerializerMethodField()
target_uuid = serializers.UUIDField(required=False, allow_null=True, write_only=True)
```

For list serializers, add only read info:

```python
def get_target_vinculado_info(self, obj):
    target = getattr(obj, "association_field", None)
    if not target:
        return None
    return {
        "uuid": str(target.uuid),
        "codigo": target.display_code,
        "label": target.display_code,
    }
```

Add the read field to `fields` and `read_only_fields`. Do not include ORM paths like `association_field__uuid` in serializer fields.

### 7. ViewSet Action

Add a detail PATCH action dedicated to the link:

```python
@action(detail=True, methods=['patch'], url_path='vincular-target')
def vincular_target(self, request, *args, **kwargs):
    source = self.get_object()
    from apps.tenant.perfil.services.perfil_service import get_or_create_profile
    empresa_id = get_or_create_profile(request.user).empresa_id

    target_uuid = request.data.get('target_uuid', None)
    source = self.service_vincular_target(source, target_uuid, empresa_id)
    serializer = SourceDetailSerializer(source, context={'request': request})
    resp = Response(serializer.data, status=status.HTTP_200_OK)
    resp["HX-Trigger"] = "sourceTargetChanged"
    return resp
```

Make `get_queryset()` use the detail selector for the custom action so `get_object()` remains optimized and tenant-filtered.

## Frontend Workflow

### API JS

Add a small API wrapper in the source app API module:

```javascript
async function vincularTarget(sourceUuid, targetUuid = null) {
  return await window.http('PATCH', `${SOURCE_API_BASE}/${sourceUuid}/vincular-target/`, {
    target_uuid: targetUuid || null,
  });
}
```

Export it through the app namespace.

### Detail UI

Add a conditional control:

- If linked: badge/card with target label and an X button to unlink.
- If unlinked: select/dropdown and a subtle link button.

Keep DOM updates partial. After PATCH, re-render only the association block from returned JSON.

### Editor UI

Add the association selector to the edit modal/offcanvas. Do not send the association UUID through the normal limited-edit PATCH if the backend keeps association mutation in a dedicated action. Instead:

1. Send existing manual fields to `PATCH /api/v1/source/<uuid>/`.
2. Send association to `PATCH /api/v1/source/<uuid>/vincular-target/`.
3. If the select is empty, send `target_uuid: null`.

### List/Dashboard UI

Expose a control column so users can see link state without opening the record:

```javascript
{
  title: "Target",
  field: "target_vinculado_info",
  formatter: function(cell) {
    const info = cell.getValue();
    if (!info) {
      return '<span class="badge text-bg-light border text-muted">Sin vínculo</span>';
    }
    const label = info.label || info.codigo || 'Vinculado';
    return `<span class="badge text-bg-success" title="${label}">${label}</span>`;
  },
  headerSort: false,
  minWidth: 160
}
```

## Validation Checklist

Run targeted checks after implementation:

```bash
python -m py_compile <changed_python_files>
python manage.py check
node --check <changed_js_files>
```

If a model field was added:

```bash
make makemigrations
make migrate-tenants
```

If available, serialize one real object from a tenant schema and confirm the list/detail serializers return the new `*_vinculado_info` object.

## Common Failure Modes

- Wrong lazy label: inspect `apps.py`; use `AppConfig.label`.
- DRF `ImproperlyConfigured` for `field__name`: remove ORM paths from serializer fields.
- Django `FieldError` about deferred fields with `select_related`: include minimal `related__field` entries in `.only()`.
- UUID vs PK mismatch: public API URLs use `uuid` via `BaseTenantViewSet`; UI hidden IDs and JS endpoints should use UUID.
- Association leaked into limited edit serializer: keep link mutations in the dedicated action unless the app explicitly allows it.
- Missing tenant DSV: always verify both source and target `empresa_id`.
