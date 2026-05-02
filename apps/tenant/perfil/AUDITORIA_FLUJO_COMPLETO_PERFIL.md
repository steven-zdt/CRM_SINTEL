# AUDITORIA_FLUJO_COMPLETO_PERFIL.md

## Resumen de la App: `perfil` (apps/tenant/perfil)

### 1. Propósito y Alcance

La app `perfil` gestiona el `TenantProfile` — el perfil privado del colaborador dentro de un tenant. Proporciona datos específicos por empresa (cargo, departamento, teléfono corporativo, avatar y preferencias) mientras mantiene el `User` global en el esquema `public`.

Desde **v2.61.8**, el módulo "Nuevo Perfil" también **crea usuarios nuevos** en el esquema `public` cuando el email no existe aún, usando el patrón de invitación (`set_unusable_password`). Sólo usuarios con rol `ADMIN` pueden acceder a esta operación.

---

### 2. Principios de Diseño Obligatorios (alineado a AGENTS.md)

- Herencia: `TenantProfile` hereda de `SintelTenantBaseModel` (implementado).
- Aislamiento tenant: todas las mutaciones validan `empresa_id` (Double Semantic Verification).
- Service Layer: lógica en `services/`. ViewSets actúan sólo como enrutadores HTTP.
- Atomicidad: operaciones compuestas envueltas en `@transaction.atomic`.
- Query Efficiency: `.only()` en todos los QuerySets. Patrón `queryset = Model.objects.none()` + override en `get_queryset()`.
- Cero Signals: lógica de negocio orquestada explícitamente desde servicios.
- Regla 17 (Bridge): no hay imports directos de `apps.public` desde esta app. Se usa `get_user_model()` (API estándar Django) para acceder al User.

---

### 3. Inventario de Archivos

```
apps/tenant/perfil/
├── models.py                        # TenantProfile, RolTenant(ADMIN/OPERADOR/VISOR)
├── admin.py
├── apps.py
├── api/
│   ├── mixins.py                    # PerfilServiceMixin (inyecta perfil_service)
│   ├── permissions.py               # IsTenantProfileAdmin, IsTenantProfileOperadorOrAdmin
│   ├── serializers.py               # TenantProfileSerializer, TenantProfileRolSerializer
│   ├── urls.py                      # router.register('perfiles', PerfilViewSet)
│   └── viewsets.py                  # PerfilViewSet (enrutador puro)
├── services/
│   ├── __init__.py                  # Exporta PerfilBusinessService, PerfilCRUDService
│   ├── api_mixins.py                # Vacio (evita circular import)
│   ├── business_service.py          # Logica de negocio (create user+profile, roles, DSV)
│   ├── crud_service.py              # Persistencia transaccional (list, get, create, update, delete)
│   ├── perfil_service.py            # Fachada legacy (compatibilidad de imports)
│   └── selectors.py                 # Consultas GET optimizadas con .only()
├── static/perfil/js/
│   ├── perfil.api.js                # URLs/endpoints SSoT
│   ├── perfil.modals.js             # Offcanvas handlers (create, edit, detail)
│   ├── perfil.page.js               # Inicializacion de pagina y tabla Tabulator
│   └── perfil.ui.js                 # DOM lifecycle, HTMX, feedback UI
├── templates/tenant/perfil/
│   ├── list_tenantprofile.html      # Vista principal con tabla Tabulator
│   ├── offcanvas_crear_perfil.html  # Formulario crear usuario+perfil (ADMIN)
│   ├── offcanvas_editar_perfil.html # Formulario editar perfil existente
│   ├── offcanvas_detalle_perfil.html# Vista de detalle (readonly)
│   └── partials/
│       ├── assets_perfil.html       # Inclusion de scripts JS de la app
│       ├── list.html                # Partial de tabla
│       └── modals.html              # Partial de contenedores de offcanvas
├── migrations/
│   ├── 0001_initial.py
│   ├── 0002_alter_tenantprofile_*.py
│   ├── 0003_alter_tenantprofile_user.py
│   ├── 0004_alter_tenantprofile_user_cascade.py
│   └── 0005_tenantprofile_rol.py
└── tests/
    └── test_models.py
```

---

### 4. Modelo: `TenantProfile`

```python
class TenantProfile(SintelTenantBaseModel):
    user          = OneToOneField(AUTH_USER_MODEL, related_name='tenant_profile', on_delete=CASCADE)
    empresa       = ForeignKey('empresa.Empresa', ...)    # heredado de SintelTenantBaseModel
    cargo         = CharField(max_length=120, blank=True)
    departamento  = CharField(max_length=120, blank=True)
    telefono_corporativo = CharField(max_length=30, blank=True)
    avatar        = ImageField(upload_to='avatars/', blank=True, null=True)
    configuracion = JSONField(default=dict, blank=True)
    rol           = CharField(choices=RolTenant.choices, default=RolTenant.OPERADOR)
    created_at    = DateTimeField(auto_now_add=True)    # heredado
    updated_at    = DateTimeField(auto_now=True)        # heredado
```

**Constraint de unicidad:** `unique_together = ('user', 'empresa')`.

**`RolTenant`:** `ADMIN`, `OPERADOR`, `VISOR`.

---

### 5. Endpoints Registrados

| Método | URL | Permiso | Acción |
|--------|-----|---------|--------|
| `GET` | `/api/v1/perfil/perfiles/` | `IsTenantMember` | Lista paginada de perfiles |
| `POST` | `/api/v1/perfil/perfiles/` | `IsTenantMember` + `IsTenantProfileAdmin` | Crea usuario + perfil |
| `GET` | `/api/v1/perfil/perfiles/<id>/` | `IsTenantMember` | Detalle de perfil |
| `PATCH` | `/api/v1/perfil/perfiles/<id>/` | `IsTenantMember` + `IsTenantProfileAdmin` | Actualiza perfil por ID |
| `DELETE` | `/api/v1/perfil/perfiles/<id>/` | `IsTenantMember` + `IsTenantProfileAdmin` | Elimina perfil |
| `GET/PATCH` | `/api/v1/perfil/perfiles/me/` | `IsTenantMember` | Perfil del usuario autenticado |
| `PATCH` | `/api/v1/perfil/perfiles/<id>/assign-rol/` | `IsTenantMember` + `IsTenantProfileAdmin` | Asigna rol |
| `GET` | `/api/v1/perfil/perfiles/render-offcanvas/crear/` | `IsTenantMember` | HTML offcanvas crear (HTMX) |
| `GET` | `/api/v1/perfil/perfiles/<id>/render-offcanvas/editar/` | `IsTenantMember` | HTML offcanvas editar (HTMX) |
| `GET` | `/api/v1/perfil/perfiles/<id>/render-offcanvas/detalle/` | `IsTenantMember` | HTML offcanvas detalle (HTMX) |

---

### 6. Flujo Operacional Completo (secuencia)

#### 6.1 Acceso al módulo (workspace#perfil)
1. `workspace.js` invoca `showTab('perfil')` → `DOMUtils.onVisibleOnce` lazy-init.
2. `perfil.page.js` inicializa `TabulatorFactory` con JWT inyectado vía `window.jwtAuth`.
3. Tabulator hace `GET /api/v1/perfil/perfiles/?page=1&page_size=10`.
4. `PerfilViewSet.list()` → `Empresa.objects.only("id").first()` → `perfil_service.list_profiles(empresa)` → `PerfilCRUDService.list_profiles(empresa_id)` con `.order_by('-created_at')`.
5. Respuesta paginada `{count, next, previous, results}` → Tabulator renderiza filas.

#### 6.2 Crear usuario + perfil (POST)
1. Admin abre offcanvas via `GET /api/v1/perfil/perfiles/render-offcanvas/crear/`.
2. Backend inyecta `empresas` y `rol_choices` en el template.
3. Form fields: `empresa_id` (hidden, DOM Shield), `first_name` (requerido), `last_name`, `email` (requerido), `username` (opcional), `cargo`, `departamento`, `telefono_corporativo`, `rol`.
4. `perfil.modals.js` valida frontend: `email` y `first_name` obligatorios.
5. POST a `/api/v1/perfil/perfiles/` con payload JSON.
6. `PerfilViewSet.create()`:
   - Guard: `IsTenantProfileAdmin` (sólo ADMIN).
   - DSV: resuelve `Empresa` desde schema activo via `empresa_id` del payload.
   - Llama `perfil_service.create_profile_for_user(empresa, data)`.
7. `PerfilBusinessService.create_profile_for_user()`:
   - Busca `User` por `email`, luego por `username`.
   - **Si no existe → crea User nuevo** con `set_unusable_password()` (invitación).
   - Username generado automáticamente desde `email` si no se provee.
   - Idempotencia: si ya existe TenantProfile para ese `user+empresa` → `ValidationError`.
   - Crea `TenantProfile` con defaults (cargo, departamento, telefono, rol).
8. Respuesta `201 Created` con datos del perfil serializado.
9. Frontend: `replaceData()` en Tabulator + `UIManager.notifySuccess`.

#### 6.3 Resolución de perfil propio (me/)
1. `GET /api/v1/perfil/perfiles/me/` → `PerfilViewSet.me()`.
2. `Empresa.objects.only("id").first()` (anti-IDOR: singleton del schema activo).
3. `perfil_service.get_or_initialize_profile(user, empresa)`:
   - **Auto-Admin Elevation:** si es el owner del tenant (`Empresa.owner_email`) y su perfil no tiene rol ADMIN → corrige automáticamente.
   - **Tier 1 (fast path):** compara `user.email` con `Empresa.owner_email` en el schema activo.
   - **Tier 2 (fallback cross-schema):** `check_primary_admin` via Core Membership Bridge.
4. Respuesta con datos del perfil.

#### 6.4 Asignación de rol (assign-rol)
1. `PATCH /api/v1/perfil/perfiles/<id>/assign-rol/` solo para ADMIN.
2. `PerfilBusinessService.assign_rol(profile_id, empresa, new_rol)`:
   - DSV: valida que `new_rol` sea un valor válido de `RolTenant`.
   - Valida que el perfil exista y pertenezca al tenant.
   - Protección: no permite retirar rol ADMIN al último administrador del tenant.

---

### 7. Service Layer

#### `PerfilCRUDService` (crud_service.py)
- `list_profiles(empresa_id)` → QuerySet con `.only()` + `.order_by('-created_at')`.
- `get_profile_by_user_and_tenant(user_id, empresa_id)` → perfil o `None`.
- `get_profile_by_id_and_tenant(profile_id, empresa_id)` → perfil o `None`.
- `create_profile(user, empresa, defaults)` → crea `TenantProfile` (idempotente).
- `update_profile(profile, data)` → actualiza campos parcialmente.
- `delete_profile(profile)` → elimina perfil.

#### `PerfilBusinessService` (business_service.py)
- `get_or_initialize_profile(user, empresa)` → perfil con Auto-Admin Elevation.
- `create_profile_for_user(empresa, data)` → crea User (si no existe) + TenantProfile.
- `update_user_profile(user, empresa, data)` → DSV + actualiza perfil propio.
- `update_profile_by_id(profile_id, empresa, data)` → para admins.
- `get_profile(profile_id, empresa)` → con validación de pertenencia al tenant.
- `delete_profile(profile_id, empresa)` → con validación.
- `assign_rol(profile_id, empresa, new_rol)` → con protección de último ADMIN.
- `_is_tenant_primary_admin(user)` → Tier 1 (owner_email) + Tier 2 (bridge).

#### `PerfilSelectors` (selectors.py)
- `LIST_FIELDS` / `DETAIL_FIELDS` como SSoT de campos expuestos.
- Métodos `@staticmethod` con `.only(LIST_FIELDS)` y filtro por `empresa_id`.

---

### 8. Frontend (JS Modules)

| Archivo | Responsabilidad |
|---------|-----------------|
| `perfil.api.js` | SSoT de URLs de la app. `getApiBase()`, `getOffcanvasCrearUrl()`, etc. |
| `perfil.page.js` | Inicialización de tabla Tabulator, columnas, eventos de fila. |
| `perfil.modals.js` | Handlers de offcanvas: `handleSaveCreate()`, `handleSaveEdit()`, `showDetail()`. DOM Shield para empresa_id. Validación frontend. |
| `perfil.ui.js` | Lifecycle de BS5 Offcanvas, integración HTMX, feedback (`UIManager`). |

**DOM Shield en crear:** el select de empresa visible **no tiene `name`**. El valor real se sincroniza vía JS al `<input type="hidden" name="empresa_id">`.

**`collectFormData('form-perfil-crear')`** itera todos los `form.elements` con atributo `name`. Los campos `first_name`, `last_name`, `email`, `username`, `rol`, etc. se recolectan automáticamente sin cambios en JS.

---

### 9. Seguridad y Anti-IDOR

- Todo endpoint de mutación valida `empresa_id` via `Empresa.objects.get(pk=...)` en el schema activo.
- `IsTenantProfileAdmin` verifica `request.user.tenant_profile.rol == 'ADMIN'`.
- `create_profile_for_user` valida que el perfil no exista antes de crear (idempotencia).
- Creación de usuarios: nunca se expone password en respuesta. `set_unusable_password()` garantiza que el usuario no puede autenticarse hasta activar cuenta.
- `assign_rol` protege el último ADMIN del tenant (no permite degradarlo).

---

### 10. Issues Resueltos (historial de correcciones)

| # | Severidad | Problema | Solución aplicada |
|---|-----------|----------|-------------------|
| P0-1 | Crítico | `/me/` usaba `Empresa.objects.only("id").first()` incorrectamente | Corregido - patrón singleton del schema activo |
| P0-2 | Crítico | `from django.db.models import Q` faltaba en `selectors.py` | Import añadido |
| P1-1 | Alto | Templates en `templates/perfil/` (ruta incorrecta) | Movidos a `templates/tenant/perfil/` |
| P1-2 | Alto | Archivos JS muertos (`perfil.form.js`, `perfil.table.js`) | Eliminados |
| P1-3 | Medio | IIFE duplicada en `perfil.ui.js` | Unificada |
| P1-4 | Medio | `PerfilServiceMixin` duplicado en `api/mixins.py` y `services/api_mixins.py` | Unificado en `api/mixins.py`; `services/api_mixins.py` vaciado |
| P2-1 | Menor | Seed de onboarding usaba `get_or_create` con campos mutables | Lookup corregido |
| FIX-1 | Crítico | `ImportError` circular `services/__init__.py` → `services/api_mixins.py` → `api/mixins.py` | `api_mixins.py` vaciado; `PerfilServiceMixin` eliminado de `services/__init__.py` |
| FIX-2 | Crítico | `RecursionError` en `/workspace/` por templates relay auto-referenciadas en `core/templates/tenant/perfil/partials/` | Tres templates eliminados: `list.html`, `modals.html`, `assets_perfil.html` |
| FIX-3 | Menor | `UnorderedObjectListWarning` en paginación | `order_by('-created_at')` añadido a `list_profiles()` |
| FIX-4 | Feature | `POST /perfiles/` rechazaba con "No se encontro un usuario..." | `create_profile_for_user()` ahora crea User nuevo si no existe (invitación) |

---

### 11. Checklist de Conformidad

- [x] Hereda `SintelTenantBaseModel`.
- [x] OneToOne a `settings.AUTH_USER_MODEL` con `related_name='tenant_profile'`.
- [x] `unique_together=('user','empresa')` presente.
- [x] Lógica completamente delegada a `services/`.
- [x] ViewSets actúan sólo como enrutadores HTTP.
- [x] Templates en ruta canónica `templates/tenant/perfil/`.
- [x] JS bajo namespace `window.Sintel.Perfil` con módulos FSD.
- [x] DOM Shield implementado para `empresa_id`.
- [x] Cero imports directos de `apps.public` (cumple Regla 17 Bridge).
- [x] Auto-Admin Elevation en `get_or_initialize_profile`.
- [x] Creación de usuario nuevo desde Admin (invitación con `unusable_password`).
- [x] Protección del último ADMIN del tenant en `assign_rol`.
- [x] `IsTenantMember` en `permission_classes` de `PerfilViewSet`.
- [ ] Tests unitarios completos para `PerfilBusinessService` (pendiente).
- [ ] Tests de integración para endpoints de creación (pendiente).

---

### 12. Integración con Workspace

- Incluido en `workspace.html` mediante `include` modular del partial `assets_perfil.html`.
- Tab `#perfil` lazy-init via `DOMUtils.onVisibleOnce`.
- JWT inyectado automáticamente en `TabulatorFactory` via `window.jwtAuth`.
- HTMX configurado globalmente (`ajax-setup-csrf.js`) para CSRF en todas las requests.

---

**Última actualización:** 2026-04-04

**Cambios (2026-04-04):** Reestructuración completa del documento. Añadidos: inventario de archivos, tabla de endpoints, flujo detallado de create-user+profile, historial de correcciones FIX-1 a FIX-4, checklist de conformidad actualizado. Refleja estado post-refactorización v2.61.8.
