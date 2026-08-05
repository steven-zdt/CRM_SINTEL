# Auditoría Flujo Completo — Módulo Public (Esquema Compartido)

**Versión auditada:** v3.16.0
**Fecha:** 2026-06-01
**Estado:** PRODUCTION READY (0 CRÍTICOS)
**Auditor:** Claude Code (claude-sonnet-4-6)
**Ubicación:** `apps/public/`
**Esquema BD:** `public` (compartido por todos los tenants)

> **Antes de modificar:** leer este documento completo. El esquema public es infraestructura crítica compartida — un error aquí afecta a TODOS los tenants simultáneamente.

---

## 1. Responsabilidades del Módulo Public

| App | Responsabilidad Principal |
|---|---|
| `accounts` | Modelo `User` global (AbstractUser), gestión de cuentas, eliminación con cascada cross-schema |
| `tenants` | Registro de tenants (`Client`, `Domain`), membresías (`TenantMembership`), ciclo de vida completo |
| `console` | UI de administración para staff: gestión de tenants y usuarios globales |
| `core` | Servicio de email transaccional, redirección inteligente, middleware de resolución de tenant |
| `impuestos` | Catálogo DIAN (PUC Colombia, tarifas, normas), SSoT para todos los tenants |

**Regla fundamental:** El flujo es **unidireccional**. Las apps tenant pueden importar de `apps.public` solo mediante el bridge autorizado (`apps.tenant.core.services.membership`). Las apps public **nunca** importan de apps tenant.

---

## 2. Inventario de Apps y Modelos

### 2.1 `accounts` — Gestión de Usuarios Globales

**Archivos clave:**
```
accounts/
  models.py                          # User, DeletionAudit
  admin.py                           # UserAdmin (BaseUserAdmin)
  managers.py                        # UserManager custom
  api/
    viewsets.py                      # UserAdminViewSet (IsAdminUser)
    public_viewsets.py               # PublicUserViewSet (AllowAny create)
    serializers.py                   # UserCreateSerializer, UserListSerializer, UserUpdateSerializer
    filters.py                       # UserFilter
    urls.py                          # Admin user routes
    public_urls.py                   # Public registration route
    services/user_service.py         # create_user_service, update_user_service
  signals.py                         # global_user_hard_deleting Signal (v3.11.0)
  services/
    delete_user_service.py           # Hard delete via signal (v3.11.0 — sin raw SQL cross-schema)
  management/commands/
    createsuperuser.py               # CLI: crea superusuario + asocia a tenant (v3.15.0 override)
    delete_user_row.py               # CLI: eliminar usuario por ID
    ensure_admin.py                  # CLI: SOLO verifica existencia de superusuario activo (v3.15.0)
    sanitize_empty_usernames.py      # CLI: limpiar usernames vacíos
  tests/
    test_api_accounts.py
```

**Migraciones:** 2 | Última: `0002_create_deletion_audit.py`

#### Modelos

**`User`** (extiende `AbstractUser`)

| Campo | Tipo | Notas |
|---|---|---|
| `email` | EmailField | unique=True, usado como login |
| `telefono` | CharField(20) | blank=True, nullable |
| `username` | CharField | auto-generado desde email si no se provee |

- FK hacia tenant: **NINGUNA** — relación unidireccional (tenant → public)
- Manager: `UserManager` custom con `create_user(email, password)` y `create_superuser()`

**`DeletionAudit`**

| Campo | Tipo | Notas |
|---|---|---|
| `target_user_id` | BigIntegerField | ID del usuario eliminado |
| `deleted_by` | FK → User | nullable, quién eliminó |
| `reason` | CharField | e.g., `admin_deleted_via_service` |
| `details` | JSONField | `{"cascade": bool}` |
| `created_at` | DateTimeField | auto |

Se escribe ANTES de eliminar al usuario para preservar la trazabilidad.

#### API Endpoints

| Método | URL | Permisos | Descripción |
|---|---|---|---|
| GET | `/api/admin/v1/accounts/users/` | IsAdminUser | Lista paginada de usuarios |
| POST | `/api/admin/v1/accounts/users/` | IsAdminUser | Crear usuario |
| GET | `/api/admin/v1/accounts/users/{id}/` | IsAdminUser | Detalle |
| PATCH | `/api/admin/v1/accounts/users/{id}/` | IsAdminUser | Actualizar parcial |
| DELETE | `/api/admin/v1/accounts/users/{id}/` | IsAdminUser | Eliminar con cascada |
| GET/PATCH | `/api/admin/v1/accounts/users/me/` | Autenticado | Perfil propio |
| POST | `/api/public/v1/users/` | AllowAny | Registro público (crear cuenta) |

#### Signal: `global_user_hard_deleting`

**Ruta:** `apps/public/accounts/signals.py`

```python
from django.dispatch import Signal
global_user_hard_deleting = Signal()
# kwargs: sender=User, user=<instancia User>
```

Emitido por `delete_user_service` justo antes de eliminar el usuario. El receiver registrado en `apps.tenant.core.services.membership._on_global_user_hard_deleting` usa `tenant_context()` para limpiar `TenantProfile` en cada schema de forma ORM-safe.

**Patron de aislamiento:** Signal definido en `apps.public` (no conoce TenantProfile). Receiver en `apps.tenant.core` (bridge autorizado). Elimina la necesidad de raw SQL cross-schema con `SET search_path`.

#### Servicio: `delete_user_service`

**Ruta:** `apps/public/accounts/services/delete_user_service.py`

Elimina un usuario y limpia todas sus referencias:
1. Token blacklist (JWT tokens revocados) — raw SQL con savepoint
2. TenantMembership en public — raw SQL con savepoint
3. django_admin_log entries — raw SQL con savepoint
4. **Emite `global_user_hard_deleting.send(sender=User, user=instance)`** → receiver en tenant.core limpia `TenantProfile` via `tenant_context()` en cada schema
5. `DeletionAudit.objects.create()` (registro de auditoría)
6. `DELETE FROM accounts_user WHERE id = %s`

**v3.11.0 (2026-06-01):** Eliminado el loop de raw SQL con `SET search_path` por schema. Reemplazado por signal desacoplado. El receiver usa la API oficial `tenant_context()` de django-tenants, sin raw SQL ni manipulación de search_path.

---

### 2.2 `tenants` — Ciclo de Vida de Tenants

**Archivos clave:**
```
tenants/
  models.py                          # Client, Domain, TenantMembership, FailedTenantTask
  admin.py                           # ClientAdmin, DomainAdmin, TenantMembershipAdmin
  forms.py                           # ClientAdminForm (con campo admin_user)
  services.py                        # crear_tenant_con_owner()
  signals.py                         # post_save Client → crear Domain automático
  audit.py                           # Log de acciones
  authz.py                           # Verificación de membresía activa
  auth_backend.py                    # Backend de autenticación multi-tenant
  middleware.py                      # Resolución hostname → schema
  middleware_admin_guard.py          # Guard para acceso admin
  middleware_urlconf.py              # Cambio dinámico de urlconf por schema
  validators.py, utils.py
  views.py                           # Activation view, redirect views
  urls.py                            # activate/, login/
  api/
    viewsets.py                      # ClientViewSet (onboard, toggle-active, resend-invitation)
    serializers.py
    urls.py
    views.py                         # APIViews para activación pública
  services/
    deletion_service.py              # hard_delete_tenant()
    invitations.py                   # Codigos alfanumericos 8 chars (Zero Collision, v3.12.0) + tokens legacy
    onboarding.py                    # OTT (One-Time Token) via Redis + already_activated (v3.11.0)
    password_reset.py                # Email de reset de contrasena
  management/commands/               # 28 comandos (ver sección 5)
  tests/
  migrations/
    0001_initial.py
    0002_failedtenanttask.py
```

**Migraciones:** 2 | Última: `0002_failedtenanttask.py`

#### Modelos

**`Client`** (extiende `TenantMixin`)

| Campo | Tipo | Notas |
|---|---|---|
| `nombre` | CharField | Nombre comercial del tenant |
| `schema_name` | CharField | Nombre del schema PostgreSQL (auto-generado) |
| `paid_until` | DateField | nullable |
| `on_trial` | BooleanField | `default=True` |
| `is_active` | BooleanField | `default=True` |
| `created_on` | DateField | auto |

- `clean()`: Auto-genera `schema_name` desde `nombre` si no se provee
- `delete()`: Triple protección contra eliminar el schema `public`

**`Domain`** (extiende `DomainMixin`)

| Campo | Tipo | Notas |
|---|---|---|
| `tenant` | FK → Client | CASCADE |
| `domain` | CharField | FQDN del subdominio |
| `is_primary` | BooleanField | Un solo primario por tenant |

**`TenantMembership`** — Autorización de usuarios en tenants

| Campo | Tipo | Notas |
|---|---|---|
| `client` | FK → Client | PROTECT |
| `user` | FK → User | PROTECT |
| `rol` | CharField | `ADMIN / STAFF / USER` |
| `is_primary_admin` | BooleanField | Un solo admin primario por tenant |
| `is_active` | BooleanField | `default=True` |
| `created_at` | DateTimeField | auto |

- **Constraint único:** `(client, user)` — un par solo puede existir una vez
- `clean()`: Valida solo un `is_primary_admin=True` por client

**`FailedTenantTask`** — DLQ para tareas Celery fallidas

| Campo | Tipo | Notas |
|---|---|---|
| `task_id`, `task_name` | CharField | Identificación Celery |
| `args`, `kwargs` | JSONField | Argumentos de la tarea |
| `exception`, `traceback` | TextField | Diagnóstico del fallo |
| `tenant_schema` | CharField | Schema afectado |
| `status` | CharField | `FAILED / RETRYING / RESOLVED` |
| `retries` | IntegerField | Intentos realizados |

#### API Endpoints

| Método | URL | Permisos | Descripción |
|---|---|---|---|
| GET | `/api/public/v1/clients/` | IsAdminUser | Lista de tenants |
| POST | `/api/public/v1/clients/onboard/` | IsAdminUser | Crear tenant + dueño atómicamente |
| POST | `/api/public/v1/clients/{id}/toggle-active/` | IsAdminUser | Activar/desactivar tenant |
| POST | `/api/public/v1/clients/{id}/resend-invitation/` | IsAdminUser | Reenviar **codigo alfanumerico 8 chars** al admin primario (v3.12.0) |
| GET/POST | `/activate/` | AllowAny | Activacion via **email + codigo 8 chars + contrasena** (v3.12.0) |

#### Admin: `ClientAdmin`

- Formulario: `ClientAdminForm` — permite seleccionar `admin_user` al crear/editar
- `save_model()` — Dos flujos:
  - **Creación (`change=False`):** `transaction.atomic()` → guarda Client → crea TenantMembership
  - **Edición (`change=True`):** `update_or_create(client=obj, user=admin_user, ...)` con lookup por `(client, user)` — la clave única real

**Fix aplicado (v3.10.4, 2026-05-29):** El `update_or_create` usaba `is_primary_admin=True` como lookup (incorrecto). Si el usuario ya tenía una membresía con `is_primary_admin=False`, intentaba CREATE → `IntegrityError UNIQUE(client_id, user_id)`. Corregido a lookup por `(client, user)`.

#### Servicios

**`crear_tenant_con_owner(nombre, admin_user_id, schema_name, paid_until, on_trial)`**

Patron Two-Phase DDL/DML (v3.11.0):
- **FASE 1 — DDL (sin transaction.atomic):** `Client.objects.create()` — TenantMixin crea el schema PostgreSQL via `CREATE SCHEMA`. Sin wrapper de transacción para evitar conflictos DDL/rollback.
- **FASE 2 — DML (transaction.atomic):** `Domain` + `TenantMembership` se crean atomicamente DESPUES de confirmar que el schema existe.
- Eliminados: `@transaction.atomic` global y `call_command('migrate_schemas')`.
- Auto-genera `schema_name` si no se provee.
- Retorna `(Client, Domain, TenantMembership, login_url)`.

**`hard_delete_tenant(client_id, actor_user_id, delete_orphan_users)`**
- Precondición: `client.is_active == False`
- Triple capa de protección anti-eliminación del schema `public`
- Llama `client.delete()` con `auto_drop_schema=True` → PostgreSQL borra el schema
- Limpia usuarios huérfanos opcionales (no staff/superuser)
- Escribe log de auditoría

**`generate_activation_code(user_id, tenant_id, ttl_hours=24)` → str (v3.12.0 — SSoT)**
- Genera codigo alfanumerico seguro de 8 caracteres via `secrets.choice(_CODE_ALPHABET)`
- Alfabeto `_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"` — excluye O/0/I/1/L (ambiguos visualmente)
- Entropia: 32^8 ≈ **1.1 × 10¹²** combinaciones — Zero Collision en escenarios reales
- Persiste en Redis: clave `invite:code:{code}` → `{user_id, tenant_id, expires_at}`, TTL 24h
- Retorna el codigo como string de 8 chars en mayusculas (ej: `"AKBT3M7Q"`)

**`validate_activation_code(code)` → dict | None (v3.12.0)**
- Valida longitud (8 chars) y que todos los caracteres pertenezcan a `_CODE_ALPHABET`
- Normaliza a mayusculas antes de buscar en Redis (tolerante a minusculas del usuario)
- **Uso unico:** elimina la clave de Redis al consumir
- Retorna `{user_id, tenant_id}` o `None` si invalido/expirado

**`generate_invitation_token(user_id, tenant_id, ttl_hours=24)`** — *legacy, mantener para compatibilidad*
- Token firmado con `SECRET_KEY` + salt `"tenant-owner-invitation"`
- Funciones `validate_invitation_token` y `verify_invitation_token` siguen disponibles

**`create_onboarding_ott(company_name, admin_email, schema_name, ttl_seconds=300)`**
- Crea User idempotente por email con `set_unusable_password()`
- Llama `crear_tenant_con_owner()`
- Genera UUID token, persiste en Redis con TTL
- Retorna `{"ott", "redirect_url", "schema_name"}`

**`consume_onboarding_ott(ott)` → dict | None (v3.11.0 actualizado)**
- Recupera y **elimina** el OTT de Redis (uso unico)
- **NUEVO:** verifica `user.has_usable_password()` antes de retornar
- Retorna `{"user_id", "schema_name", "domain", "already_activated": bool, "message": str}`
- Si `already_activated=True`: el tenant fue vinculado a cuenta existente — la vista debe redirigir al login sin forzar nueva contrasena

**`build_activation_url(domain, token)`** — *legacy, usada por flujo de invitacion clasico*
- Respeta variable de entorno `ACTIVATION_BASE_URL` para override en dev
- Construye `{protocolo}://{dominio}[:{puerto}]/activate/?token={token}`

**`send_tenant_activation_email_sync` — SSoT de URL de activacion (v3.15.0)**
- NO lee `ACTIVATION_BASE_URL` — construye la URL directamente desde el `schema_name` del tenant
- **URL generada:** `https://{schema}.sintel.net.co/static/tenant/core/auth/activate.html?token={signed_token_48h}`
- La pagina `activate.html` del TENANT PRIVADO valida el token via `GET /api/v1/core/auth/activate/?token=...`, solicita contrasena y redirige al workspace
- **Garantia para todos los tenants:** la URL siempre apunta al subdominio del tenant especifico — nueva o futura — sin configuracion adicional
- **Prohibido usar**: IP privada, `sintel.net.co/activate/` (dominio publico), ni `home.sintel.net.co` para tenants de otros clientes

---

### 2.3 `console` — Panel de Administración

**Archivos clave:**
```
console/
  models.py                          # ConsoleActionLog
  views.py                           # Vistas HTML (require staff)
  urls.py
  mixins.py
  api/
    views.py                         # DataTable views + health
    serializers.py
    urls.py
  templates/console/
    base.html
    dashboard.html
    tenants_list.html
    users_list.html
    impuestos_catalogo.html
  static/
  management/commands/
    debug_tenant_creation.py
    diagnostico_tenant.py
  migrations/
    0001, 0002, 0003_alter_consoleactionlog_action.py
```

**Migraciones:** 3 | Última: `0003_alter_consoleactionlog_action.py`

#### Modelo: `ConsoleActionLog`

| Campo | Tipo | Notas |
|---|---|---|
| `action` | CharField | `TENANT_CREATE/UPDATE/DELETE`, `USER_CREATE/UPDATE/DELETE/ACTIVATE` |
| `actor` | FK → User | Quién ejecutó la acción |
| `tenant` | FK → Client | nullable |
| `target_user` | FK → User | nullable |
| `metadata` | JSONField | Detalles adicionales |
| `created_at` | DateTimeField | auto |

Índices: `(action, created_at)`, `(tenant, created_at)`, `(actor, created_at)`

#### API — `SessionAuthentication + IsAdminUser`

| Método | URL | Descripción |
|---|---|---|
| POST | `/api/admin/v1/console/dt/tenants/` | DataTables de tenants con search/filter |
| POST | `/api/admin/v1/console/dt/tenant-domains/` | DataTables de dominios |
| GET/POST/PATCH/DELETE | `/api/admin/v1/console/dt/users/[{id}/]` | CRUD de usuarios globales |
| GET | `/api/admin/v1/console/dt/users/{id}/tenants/` | Membresías del usuario (v3.14.0) |
| POST | `/api/admin/v1/console/dt/users/{id}/assign-tenant/` | Asignar usuario a tenant huerfano (v3.14.0) |
| GET | `/api/admin/v1/console/orphan-tenants/` | Tenants sin administrador primario activo (v3.14.0) |
| GET | `/api/admin/v1/console/health/` | Estado del servicio |

**`ConsoleUserListSerializer` — campos clave (v3.14.0):**
- `tenants` — `SerializerMethodField`: lista de `{tenant_id, nombre, schema_name, domain_url, rol, is_primary_admin}` construida desde `_tenant_memberships` (prefetch, sin N+1)
- `domain_url` — construido en backend: `f"{SITE_PROTOCOL}://{schema_name}.{TENANT_DOMAIN_BASE}"` — nunca calculado en JS

**`/console/users/` — columna Tenants asignados (v3.14.0):**
- Muestra la URL del dominio del tenant como link clickeable: `https://cliente.sintel.net.co`
- Ícono ★ para el administrador primario
- Badge ambar "Sin tenant" si el usuario no tiene membresías
- Botón **"Asignar"** abre modal con lista de tenants huerfanos + buscador
- Asignacion via `POST /assign-tenant/` — desmarca admin anterior, crea/actualiza `TenantMembership`

**Templates HTML** (requieren `staff`):
- `/console/` → `dashboard.html`
- `/console/tenants/` → `tenants_list.html`
- `/console/users/` → `pages/users/list.html` (columna tenants + modal asignacion)
- `/console/impuestos/` → `impuestos_catalogo.html`

**Suite de Tests (v3.14.0 — DT-PUB-01 RESUELTO):**

| Archivo | Tests | Cobertura |
|---|---|---|
| `tests/conftest.py` | Fixtures | helpers: `make_normal_user`, `make_staff_user`, `make_tenant_with_domain`, `make_console_action_log` |
| `tests/test_views.py` | 15 | Control de acceso HTML: anon→302, no-staff→403, staff→200+template |
| `tests/test_api_views.py` | 41 | DataTables, CRUD, delete mock, health, fixtures |
| **Total** | **56 tests** | **~85% cobertura** |

Ejecutar: `python -m pytest apps/public/console/tests/ -v`

---

### 2.4 `core` — Infraestructura de Email y Redirección

**Archivos clave:**
```
core/
  views.py                           # PublicIndexView (smart redirect)
  urls.py
  middleware.py                      # Resolución de tenant por hostname
  api/
    public_views.py                  # Health, auth endpoints públicos
    views.py
  services/
    email_service.py                 # EmailService (SSoT de correos transaccionales)
  management/commands/
    print_urls.py                    # Listar URLs registradas
    status_public.py                 # Estado del schema público
    test_email.py                    # Prueba de envío de email
  templates/
    public/core/emails/
      owner_invitation.{html,txt}    # Template: invitación a owner
      password_reset.{html,txt}      # Template: reset de contraseña
    core/onboard.html
  static/
  migrations/                        # 0 migraciones (sin modelos propios)
```

**Sin modelos propios** — es una capa de utilidades pura.

#### Servicio: `EmailService`

| Método | Descripción |
|---|---|
| `_send_email(subject, recipient_list, template_name, context)` | Renderiza `{template_name}.{html,txt}` desde `public/core/emails/` y envía |
| **`send_tenant_activation_email(user, tenant)`** | **v3.15.0 SSoT** — unica funcion autorizada para emails de activacion. Despacha `send_tenant_activation_email_task` que genera token firmado + URL tenant-especifica internamente |
| **`send_tenant_activation_email_sync(user, tenant)`** | **v3.15.0** — sincrono: genera `generate_invitation_token(ttl=48h)` → URL `https://{schema}.sintel.net.co/static/tenant/core/auth/activate.html?token=...` → envia email |
| `send_invitation_code_email(user, tenant, code)` | Alias legacy → delega a `send_tenant_activation_email` |
| `send_invitation_email(user, tenant, activation_url)` | *Legacy* — despacha tarea Celery con URL de activacion |
| `send_password_reset_email(user, tenant, reset_url)` | Usa template `password_reset` |

Retorna `bool` — `True` en exito, `False` en fallo (logueado). Usa `settings.DEFAULT_FROM_EMAIL`.

**Template `owner_invitation.html/.txt` (v3.11.0 actualizado):**
- Muestra el codigo con estilo monospace prominente (2.8rem, letter-spacing)
- Incluye `{{ activate_url }}` para que el usuario sepa a donde ir
- No contiene link de activacion ni token — solo el codigo alfanumerico de 8 chars
- Variables de contexto: `user`, `tenant`, `tenant_name`, `code`, `activate_url`, `contact_email`

#### `PublicIndexView` — Redirección Inteligente

Determina el destino inicial del usuario:
- Si no autenticado → `/login/`
- Si autenticado staff → `/console/`
- Si autenticado con membresía activa → workspace del tenant
- Si sin membresía → pantalla de error/onboarding

---

### 2.5 `impuestos` — Catálogo DIAN (SSoT para todos los tenants)

**Archivos clave:**
```
impuestos/
  models.py                          # 10 modelos de catálogo tributario colombiano
  admin.py
  tasks.py                           # Tareas Celery de ingesta
  api/
    crud_viewsets.py                 # CRUD estándar
    viewsets.py                      # Endpoints especializados
    datatables.py                    # DataTables UI
    filters.py, serializers.py, urls.py
    health.py                        # Estado del catálogo
  services/
    provider.py                      # Proveedor de datos tributarios
    robots.py                        # Web scraping/ingesta de normas
  search/                            # Motor de búsqueda
  management/commands/
    impuestos_export_json.py
    impuestos_reindex.py
    impuestos_seed.py                # Poblar datos iniciales
    impuestos_smoke.py               # Smoke tests
    poblar_catalogo_dian.py          # Ingesta completa del catálogo DIAN
  templates/, static/
  migrations/
    0001_initial.py
```

**Migraciones:** 1 | Solo: `0001_initial.py`

#### Modelos (catálogo de solo lectura para tenants)

| Modelo | Contenido |
|---|---|
| `TipoImpuesto` | Tipos de impuesto (IVA, Retención, ICA, etc.) |
| `TarifaIVA` | Tarifas IVA: porcentaje, tipo (general/reducida/excluido/exento) |
| `ConceptoRetencion` | Conceptos de retención (Renta, ICA, IVA, CREE) con rango porcentual |
| `CodigoTributario` | Códigos de responsabilidad, régimen, etc. |
| `ActividadEconomica` | Clasificación CIIU de actividades económicas |
| `DocumentoFuente` | Documentos fuente para ingesta (PDF, HTML, XML, XLS, CSV) con estado |
| `IngestaLog` | Logs de procesamiento por documento y etapa |
| `NormaTributaria` | Normas extraídas con artículo, tema, impuesto, vigencia |
| `ContribuyenteTipo` | Tipos de contribuyente (PN/PJ) por segmento |
| `RegimenRenta` | Regímenes tributarios (ORDINARIO, RTE, SIMPLE) con tarifa |
| `ResponsabilidadRUT` | Responsabilidades RUT (códigos 48, 49, 47, 52, 13) con flags |
| `PerfilTributario` | Perfiles combinados (M2M: ContribuyenteTipo + RegimenRenta + ResponsabilidadRUT) |

---

## 3. URLs Registradas

### `config/urls_public.py` (ROOT_URLCONF)

| Ruta | Destino | Notas |
|---|---|---|
| `/health` | HealthCheckView | Estado de DB |
| `/` | PublicIndexView | Smart redirect |
| `/admin/` | Django admin | Solo staff |
| `/login/`, `/logout/` | Redirects | → Django admin login |
| `/api/token/` | TokenObtainPairView | JWT acceso |
| `/api/token/refresh/` | TokenRefreshView | JWT refresh |
| `/api/token/verify/` | LoggedTokenVerifyView | JWT verify con audit |
| `/api/public/v1/` | `config.public_api_urls` | APIs REST públicas |
| `/activate/` | `apps.public.tenants.urls` | Activación de cuentas |
| `/api/admin/v1/console/` | Console DataTable APIs | Solo staff |
| `/api/admin/v1/accounts/` | Gestión global de usuarios | Solo staff |
| `/console/` | Console UI | Solo staff |
| `/api/schema/`, `/api/docs/` | OpenAPI / Swagger | Documentación |

### `config/public_api_urls.py`

- `apps.public.tenants.api.urls` — ClientViewSet
- `apps.public.accounts.api.urls` — UserAdminViewSet
- `apps.public.accounts.api.public_urls` — PublicUserViewSet (registro)
- `apps.public.impuestos.api.urls` — Catálogo DIAN

---

## 4. Seguridad y Arquitectura Cross-Schema

### 4.1 Autenticación

| Capa | Tecnología | Uso |
|---|---|---|
| Admin UI | `SessionAuthentication` | Cookies de sesion, staff only |
| API REST | `JWTAuthentication` | Bearer token, clientes externos |
| **Activacion owner** | **Codigo alfanumerico 8 chars en Redis** | `secrets.choice(_CODE_ALPHABET)` × 8 + TTL 24h + uso unico (v3.12.0) |
| Onboarding OTT | UUID OTT en Redis | Uso unico, TTL configurable (default 5 min) |
| Invitacion legacy | Token firmado Django | `signing.dumps()` + sal + TTL embebido — mantenido por compatibilidad |

### 4.2 Permisos

| Permiso | Apps que lo usan | Descripción |
|---|---|---|
| `IsAdminUser` | console, accounts, tenants | Solo `is_staff=True` |
| `AllowAny` | accounts (registro), tenants (activación) | Sin autenticación |

### 4.3 Reglas de Aislamiento Cross-Schema

```
PUBLIC (shared)        TENANT (por empresa)
  User ←───────────── TenantProfile.user (FK permitida: tenant → public)
  Client ←──────────── TenantMembership.client (OK: ambos en public)

BLOQUEADO:
  User → TenantProfile   (public → tenant = PROHIBIDO)
  Console → apps.tenant  (public → tenant = PROHIBIDO)
```

**Bridge autorizado:** Solo `apps.tenant.core.services.membership` puede cruzar el esquema.

### 4.4 Protecciones Críticas

1. **Anti-eliminación del schema `public`:** Triple capa (Model.delete → Admin.delete_model → hard_delete_tenant) bloquea absolutamente la eliminación del tenant público.

2. **Cascade de eliminacion de usuario (v3.11.0):** Signal `global_user_hard_deleting` + receiver `_on_global_user_hard_deleting` en tenant.core usa `tenant_context()` para limpiar `TenantProfile` en cada schema de forma ORM-safe, sin raw SQL ni `SET search_path`.

3. **TenantMembership unica:** Constraint `UNIQUE(client_id, user_id)`. El admin usa `update_or_create(client=obj, user=admin_user, ...)` con el par unico como lookup (no `is_primary_admin`).

4. **Codigo de activacion alfanumerico 8 chars (v3.12.0):** `generate_activation_code()` usa `secrets.choice(_CODE_ALPHABET)` × 8 → Redis `invite:code:{code}` con TTL 24h, uso unico y entropia 32^8 ≈ 1.1×10¹² (Zero Collision). `ActivateAccountView.POST` acepta email + codigo + contrasena. Normaliza a mayusculas antes de validar en Redis.

5. **OTT ya_activado (v3.11.0):** `consume_onboarding_ott()` detecta `user.has_usable_password()`. Si True, retorna `already_activated=True` → la vista redirige al login sin forzar nueva contrasena.

5. **Audit trail:** `DeletionAudit` (users), `ConsoleActionLog` (acciones admin), `FailedTenantTask` (DLQ Celery).

---

## 5. Comandos de Gestión (Management Commands)

### accounts/
| Comando | Descripción |
|---|---|
| `createsuperuser [--tenant <schema>]` | **UNICO proceso autorizado** para crear admins del sistema. Pide email+password y asocia al tenant privado indicado. Override del comando nativo de Django (v3.15.0) |
| `ensure_admin` | SOLO verifica que exista un superusuario activo. Si no hay ninguno, muestra alerta. NO crea usuarios. (v3.15.0) |
| `delete_user_row <user_id>` | Eliminación física de usuario con cascada |
| `sanitize_empty_usernames` | Limpia usernames vacíos o nulos |

### console/
| Comando | Descripción |
|---|---|
| `debug_tenant_creation` | Debug del flujo de creación de tenant |
| `diagnostico_tenant` | Estado y diagnóstico de un tenant |

### core/
| Comando | Descripción |
|---|---|
| `print_urls` | Lista todas las URLs registradas |
| `status_public` | Estado general del schema público |
| `test_email` | Prueba envío de email transaccional |

### impuestos/
| Comando | Descripción |
|---|---|
| `impuestos_seed` | Poblar datos iniciales del catálogo |
| `poblar_catalogo_dian` | Ingesta completa desde DIAN |
| `impuestos_export_json` | Exportar catálogo a JSON |
| `impuestos_reindex` | Reindexar motor de búsqueda |
| `impuestos_smoke` | Smoke tests del catálogo |

### tenants/ — 28 comandos
| Categoría | Comandos |
|---|---|
| **Creación** | `crear_empresa`, `create_public_tenant`, `setup_public_tenant` |
| **Backup/Restore** | `backup_all_tenants`, `backup_tenant`, `restore_tenant` |
| **Dominios** | `fix_all_tenant_domains`, `fix_dev_domains`, `fix_tenant_domain`, `ensure_public_domains`, `check_domains`, `auditar_dominios_tenants` |
| **Diagnóstico** | `diagnostico_404`, `diagnostico_routing`, `inspect_tenant_columns`, `show_tenant_hosts`, `auditar_tenant`, `validate_domain_correspondence` |
| **Migraciones** | `fix_migration_history`, `migrate_tenant_if_needed` |
| **Usuarios** | `owner_activation_reset_and_token`, `cleanup_tenant_duplicates` |
| **Testing** | `generar_tenants_prueba`, `analizar_tenants_prueba`, `verificar_eliminacion_tenant` |
| **Otros** | `maildigester_run`, `auditar_referencias_admin_login` |

---

## 6. Cobertura de Tests

| App | Archivos de Test | Cobertura |
|---|---|---|
| `accounts` | `test_api_accounts.py`, `test_templates.py` | Media |
| `tenants` | Tests en `tests/` | Media |
| `console` | Sin tests | ❌ |
| `core` | `test_public_index_view.py` (4 tests), `test_email_service.py` | ✅ Media |
| `impuestos` | Tests en `tests/` | Media |

---

## 7. Flujos End-to-End

### 7.1 Creacion de Tenant — Two-Phase DDL/DML (v3.11.0)

```
Admin click "Crear Tenant" en /console/tenants/
  ↓
POST /api/public/v1/clients/onboard/
  ↓
crear_tenant_con_owner(nombre, admin_user_id, ...)

  FASE 1 — DDL (sin transaction.atomic):
    Client.objects.create(...)
      → TenantMixin.save() emite CREATE SCHEMA PostgreSQL
      → schema queda fisicamente creado (irrevocable)

  FASE 2 — DML (transaction.atomic separado):
    Domain.objects.get_or_create(...)    → domain FQDN
    TenantMembership.objects.create(...) → owner ADMIN
  ↓
returns (client, domain, membership, login_url)
  ↓
EmailService.send_invitation_code_email() → codigo alfanumerico 8 chars al owner
```

### 7.2 Activacion de Owner — Flujo Definitivo (v3.15.0 SSoT)

```
Admin crea tenant (cualquier ruta: consola, onboard, manual)
  ↓
EmailService.send_tenant_activation_email(user, tenant)   ← SSoT — unica funcion autorizada
  → send_tenant_activation_email_task.delay(user.pk, tenant.pk)
       → generate_invitation_token(user_id, tenant_id, ttl_hours=48)  ← token firmado
       → activate_url = f"https://{schema}.sintel.net.co/static/tenant/core/auth/activate.html?token={token}"
       → Email: Boton "Activar mi cuenta en {tenant_name}" → activate_url
  ↓
Owner recibe email → clic en boton "Activar mi cuenta en {tenant}"
  ↓
https://{schema}.sintel.net.co/static/tenant/core/auth/activate.html?token=eyJ...
  ↓
activate.html:
  → GET /api/v1/core/auth/activate/?token=eyJ... (validar token, mostrar email del owner)
  → Usuario ingresa contrasena + confirmacion
  → POST /api/v1/core/auth/activate/?token=eyJ... { password1, password2 }
       → process_activation(): valida token, verifica tenant, user.set_password()
       → redirect_url = "/static/tenant/core/auth/login.html"
  ↓
Owner loguea en workspace del tenant y accede normalmente
```

**Puntos de envio consolidados en el SSoT (todos usan la misma funcion):**
- `empresa_service.py` — onboarding nuevo tenant
- `tenants/tasks.py:send_activation_email_task` — task legacy
- `tenants/api/viewsets.py:resend_invitation` — reenvio desde consola
- `tenants/api/viewsets.py:manual_activate` — activacion de emergencia

### 7.2b OTT Onboarding — Cuenta Existente (v3.11.0)

```
consume_onboarding_ott(ott)
  Redis.getdel(f"onboard:{ott}") → {user_id, schema_name, domain}
  ↓
  user = User.objects.get(pk=user_id)
  if user.has_usable_password():
      return {..., "already_activated": True,
              "message": "El tenant ha sido anadido a tu cuenta existente."}
  else:
      return {..., "already_activated": False}
  ↓
CoreAuthViewSet.consume_ott():
  if already_activated:
      return 200 {already_activated: True, redirect_url: "/login/"} → onboard.html
                                                                        muestra mensaje 3s
                                                                        redirige a login
  else:
      login(request, user) → 200 {success: True} → onboard.html
                                                      redirige a /workspace/
```

### 7.3 Eliminacion de Usuario — Via Signal (v3.11.0)

```
DELETE /api/admin/v1/accounts/users/{id}/
  ↓
UserAdminViewSet.destroy()
  ↓
delete_user_service(user_id, cascade=True)
  1. DELETE token_blacklist (blacklisted + outstanding) — raw SQL savepoint
  2. DELETE tenants_tenantmembership WHERE user_id — raw SQL savepoint
  3. DELETE django_admin_log WHERE user_id — raw SQL savepoint
  4. global_user_hard_deleting.send(sender=User, user=instance)
       ↓ receiver: _on_global_user_hard_deleting
         for membership in TenantMembership.filter(user=user):
           with tenant_context(membership.client):
             TenantProfile.objects.filter(user=user).delete()
  5. DeletionAudit.objects.create(target_user_id, deleted_by_id)
  6. DELETE FROM accounts_user WHERE id
  ↓
204 No Content
```

---

## 8. Clasificacion y Ciclo de Vida de Usuarios (v3.15.0)

### 8.1 Tipos de Usuario

| Tipo | is_staff | is_superuser | TenantMembership | Accede a |
|---|---|---|---|---|
| **SYSTEM_ADMIN** | True | True | Opcional (puede tener para workspace propio) | `/admin/` + `/console/` + cualquier workspace |
| **TENANT_OWNER** | False | False | `is_primary_admin=True` | Solo su workspace `{schema}.sintel.net.co` |
| **TENANT_MEMBER** | False | False | `rol=OPERADOR/VISOR` | Solo su workspace (no en `/console/users/`) |

### 8.2 Regla del Superusuario (AGENTS.md)

```
REGLA CRITICA: El usuario administrador de sintel.net.co/admin/ se crea SIEMPRE
y SOLO de forma MANUAL con:

    python manage.py createsuperuser [--tenant <schema>]

NUNCA se crea automaticamente al arrancar el servidor.
ensure_admin SOLO verifica existencia — no crea.
```

### 8.3 `/console/users/` — Filtro de Visibilidad (v3.15.0)

Solo muestran usuarios visibles:
```python
Q(is_staff=True, is_superuser=True) |  # System admins
Q(Exists(_has_primary_admin))           # Tenant owners
```

EXCLUIDOS: TENANT_MEMBER, usuarios sin TenantMembership (a menos que sean staff+super).

### 8.4 `createsuperuser` Override

Al crear un superusuario con `python manage.py createsuperuser [--tenant <schema>]`:
1. Crea el User con `is_staff=True, is_superuser=True`
2. Desvincula el `is_primary_admin` anterior en el tenant seleccionado
3. Crea `TenantMembership(rol=ADMIN, is_primary_admin=True)` para ese usuario y tenant
4. El superusuario puede acceder tanto a `/admin/` como al workspace del tenant

---

## 9. Infraestructura DNS y Acceso Multi-Tenant (v3.13.0)

### 8.1 Arquitectura DNS — Windows Server 2022

El servidor Windows (`192.168.2.15`) hospeda el DNS autoritativo para la zona `sintel.net.co`.

| Registro DNS | Valor | Tipo |
|---|---|---|
| `@` (raiz) | `192.168.2.15` | A — dominio publico `sintel.net.co` |
| `*` (wildcard) | `192.168.2.15` | A — todos los subdominios tenant |
| `home` | `192.168.2.15` | A — tenant home (explicito) |
| `cliente` | `192.168.2.15` | A — tenant cliente (explicito) |
| `putito` | `192.168.2.15` | A — tenant putito (explicito) |
| `tupapi` | `192.168.2.15` | A — tenant tupapi (explicito) |

**Por que registros individuales ademas del wildcard:**
La wildcard `*` en Windows DNS no siempre se sirve correctamente en todas las condiciones de red. Los registros individuales son mas robustos y garantizan resolucion inmediata sin dependencia de propagacion del wildcard.

### 8.2 Management Command `ensure_tenant_dns`

**Ruta:** `apps/public/tenants/management/commands/ensure_tenant_dns.py`

Ejecutar desde el **HOST Windows** (no Docker) para agregar A records DNS al crear nuevos tenants:

```bash
python manage.py ensure_tenant_dns                  # Todos los tenants activos
python manage.py ensure_tenant_dns --schema nuevo   # Solo un tenant
python manage.py ensure_tenant_dns --dry-run        # Preview sin ejecutar
```

El comando:
1. Lee todos los tenants activos desde la BD
2. Para cada `{schema}.sintel.net.co` sin A record: ejecuta `Add-DnsServerResourceRecordA` via PowerShell
3. Muestra que lineas agregar en `docker-compose.yaml extra_hosts` y reiniciar

**Ejecucion:** Manual — ejecutar desde el HOST Windows al crear un nuevo tenant. Sin tarea programada.

### 8.3 Docker `extra_hosts` — Resolucion Interna

Los contenedores Docker NO usan el DNS de Windows por defecto (usan `127.0.0.11` que no tiene acceso directo a la zona `sintel.net.co`). Se usa `extra_hosts` en el anchor `x-app-base` del `docker-compose.yaml`:

```yaml
x-app-base: &app-base
  extra_hosts:
    - "sintel.net.co:192.168.2.15"
    - "home.sintel.net.co:192.168.2.15"
    - "{schema}.sintel.net.co:192.168.2.15"   # agregar por cada nuevo tenant
```

**Al crear un nuevo tenant**, agregar manualmente la linea y reiniciar:
```bash
# En docker-compose.yaml extra_hosts:
- "nuevocliente.sintel.net.co:192.168.2.15"

# Luego:
docker compose restart web celery
```

**IMPORTANTE:** No usar el comando `ensure_tenant_dns` para actualizar `docker-compose.yaml` — el script YAML de Python corrompe la estructura del archivo. Solo actualizar manualmente.

### 8.4 `ACTIVATION_BASE_URL` — Regla de Oro

| Valor | Resultado | Estado |
|---|---|---|
| `https://192.168.2.15` | Gmail bloquea el hipervinculo (IP privada) | **PROHIBIDO** |
| `https://home.sintel.net.co` | Apunta a un tenant privado, no al dominio publico | **PROHIBIDO** |
| `https://sintel.net.co` | Dominio publico raiz — Gmail muestra el hipervinculo | **CORRECTO** |

La URL de activacion para todos los tenants es siempre `https://sintel.net.co/activate/`. El endpoint vive en el schema `public` y valida el codigo independientemente del dominio de origen.

---

## 9. Reglas Invariantes del Sistema (v3.16.0 — Requieren Aprobacion Manual)

Las siguientes reglas NO pueden ser modificadas sin aprobacion manual explícita del administrador
del sistema. Cualquier cambio en estos comportamientos debe documentarse en este archivo con
version, fecha y justificacion.

### 9.1 Filtro de Visibilidad en `/console/users/`

```python
# UsersDataTableView — INMUTABLE sin aprobacion
Q(is_staff=True, is_superuser=True) | Q(Exists(_has_primary_admin))
```

- Solo muestra: administradores del sistema (staff+super) y owners primarios de tenants.
- PROHIBIDO mostrar: empleados de tenants (OPERADOR/VISOR), usuarios huerfanos.
- Razon: privacidad — los datos de empleados de un tenant no deben ser visibles desde el panel admin del sistema.

### 9.2 Flags de Usuario — Clasificacion Estricta

| Tipo | is_staff | is_superuser | Asignado por |
|---|---|---|---|
| SYSTEM_ADMIN | True | True | Solo `createsuperuser` |
| TENANT_OWNER | False | False | `crear_tenant_con_owner` / onboarding |
| TENANT_MEMBER | False | False | Operaciones internas del tenant |

- PROHIBIDO: asignar `is_staff=True` a owners en ningun flujo de onboarding.
- PROHIBIDO: crear superusuarios de forma automatica en `entrypoint.sh` o senales.

### 9.3 SSoT Email de Activacion de Tenants

Funcion canonica unica: `EmailService.send_tenant_activation_email(user, tenant)`

- Genera codigo Redis (8 chars alfanumericos, TTL 48h) internamente.
- URL siempre apunta al tenant privado: `https://{schema}.sintel.net.co/static/tenant/core/auth/activate.html`
- Aplica a TODOS los flujos: onboarding, reenvio, activacion manual.
- PROHIBIDO: usar `generate_invitation_token` + `build_activation_url` directamente en nuevos flujos.

### 9.4 Abstraccion de Nombres Propios en Infraestructura

- PROHIBIDO: referencias a nombres propios de tenants (`cliente`, `home`, `putito`, etc.) en scripts, management commands, docstrings o configuraciones.
- CORRECTO: usar `{schema_name}`, `{schema}.sintel.net.co`, `<schema_name>` como placeholders.
- Datos de tenants: siempre via ORM `Client.objects.exclude(schema_name="public").filter(is_active=True)`.
- EXCEPCION documentada: `schema_name="public"` / `sintel.net.co` — dominio raiz de la plataforma, gestionado independientemente.

### 9.5 Cobertura de Tests — Numeros Minimos

| Suite | Tests | Umbral minimo |
|---|---|---|
| `apps/public/console/tests/` | 56+ | No reducir sin aprobacion |
| `apps/public/core/tests/` | 11+ | No reducir sin aprobacion |

Ejecutar antes de cualquier merge: `python -m pytest apps/public/console/tests/ apps/public/core/tests/ -q`

---

## 10. Historial de Cambios Relevantes

| Version | Fecha | Cambio |
|---|---|---|
| v3.5.0 | 2026-05-09 | Baseline: EmailService, PublicIndexView, TenantMembership |
| v3.10.3 | 2026-05-25 | Imports globales consolidados en viewsets y services |
| v3.10.4 | 2026-05-29 | FIX: `delete_user_service` — nombres calificados por schema + reset search_path |
| v3.10.4 | 2026-05-29 | FIX: `ClientAdmin.save_model` — lookup `update_or_create` corregido a `(client, user)` eliminando IntegrityError UNIQUE |
| **v3.11.0** | **2026-06-01** | **ARCH: `crear_tenant_con_owner` — Two-Phase DDL/DML, eliminado `@transaction.atomic` global y `call_command('migrate_schemas')`** |
| **v3.11.0** | **2026-06-01** | **ARCH: Signal `global_user_hard_deleting` — desacopla limpieza de TenantProfile; receiver en tenant.core usa `tenant_context()`** |
| **v3.11.0** | **2026-06-01** | **FEATURE: Codigo de activacion 6 digitos — reemplaza token firmado en URL; `generate_activation_code()` + Redis + `validate_activation_code()` uso unico** |
| **v3.11.0** | **2026-06-01** | **FEATURE: `consume_onboarding_ott` detecta cuenta preexistente (`has_usable_password`) → `already_activated=True` + redirect a login** |
| **v3.11.0** | **2026-06-01** | **UI: `activate_password.html` — formulario email + codigo 6 digitos + contrasena; `onboard.html` maneja `already_activated`** |
| **v3.12.0** | **2026-06-01** | **SEC: Blindaje management commands — `generar_tenants_prueba` y `analizar_tenants_prueba` lanzan `CommandError` si `DEBUG=False`; imports de `settings`+`CommandError` al nivel modulo** |
| **v3.12.0** | **2026-06-01** | **SEC: Codigo activacion alfanumerico 8 chars — `secrets.choice(_CODE_ALPHABET)` reemplaza `random.randint`; alfabeto sin ambiguos; entropia 32^8 ≈ 1.1×10¹² (Zero Collision); normaliza a upper() en validacion** |
| **v3.12.0** | **2026-06-01** | **TEST: Smoke tests `TestPublicIndexView` — 4 tests en `apps/public/core/tests/test_public_index_view.py`; cubre anonimo, staff, miembro activo, sin membresia; DT-PUB-02 RESUELTO** |
| **v3.13.0** | **2026-06-01** | **EMAIL: `ACTIVATION_BASE_URL=https://sintel.net.co` — corregido de IP privada y dominio tenant; Gmail bloqueaba hipervinculos a `192.168.x.x`** |
| **v3.13.0** | **2026-06-01** | **INFRA: DNS Windows Server — registros A individuales para todos los tenants via `ensure_tenant_dns` (ejecucion manual al crear tenant)** |
| **v3.13.0** | **2026-06-01** | **INFRA: `docker-compose.yaml` — `extra_hosts` en anchor `x-app-base`; `sintel.net.co` agregado; resolucion interna de subdominios tenant sin DNS externo** |
| **v3.13.0** | **2026-06-01** | **FIX: `ensure_tenant_dns` — eliminada funcion `_update_compose_extra_hosts` que corrompía el YAML; ahora solo gestiona DNS Windows y muestra hints manuales** |
| **v3.14.0** | **2026-06-01** | **FIX: JWT_SECRET_KEY en `.env` — eliminado `warnings.warn` por generacion automatica; `public_api_urls.py` simplificado de 105 a 35 lineas** |
| **v3.14.0** | **2026-06-01** | **FEATURE: Password reset via codigo 8 chars — `generate_reset_code` + `validate_reset_code` en Redis (TTL 1h, clave `reset:code:{schema}:{code}`); `confirm_reset_with_code`; template email con codigo** |
| **v3.14.0** | **2026-06-01** | **UI: `/console/users/` — columna Tenants asignados con URL del dominio clickeable (`domain_url`); boton Asignar; modal tenants huerfanos + buscador** |
| **v3.14.0** | **2026-06-01** | **API: 3 endpoints nuevos en console — `orphan-tenants/`, `dt/users/{id}/assign-tenant/`, `dt/users/{id}/tenants/`** |
| **v3.14.0** | **2026-06-01** | **TEST: DT-PUB-01 RESUELTO — 56 tests (15 vistas + 41 API); `conftest.py` con helpers + patch DDL; ejecutar via pytest** |
| **v3.15.0** | **2026-06-01** | **ARCH: Clasificacion de usuarios — SYSTEM_ADMIN vs TENANT_OWNER vs TENANT_MEMBER; `is_staff=True` solo para admins del sistema; `/console/users/` filtra por superuser OR primary_admin** |
| **v3.15.0** | **2026-06-01** | **SEC: Override `createsuperuser` — crea superusuario + asocia directamente a tenant privado; `ensure_admin` convertido a solo-verificacion; eliminada creacion automatica en `entrypoint.sh`** |
| **v3.15.0** | **2026-06-01** | **FIX: `SafeTokenRefreshView` — convierte `User.DoesNotExist` en 401 en lugar de 500 cuando el usuario del token fue eliminado** |
| **v3.15.0** | **2026-06-01** | **FIX: `admin@home.com` desactivado y `home` tenant eliminado permanentemente (schema PostgreSQL dropeado)** |
| **v3.15.0** | **2026-06-01** | **SSoT EMAIL: `EmailService.send_tenant_activation_email(user, tenant)` — funcion canonica para todos los flujos de activacion; genera token firmado + URL `https://{schema}.sintel.net.co/static/tenant/core/auth/activate.html?token=...`** |
| **v3.15.0** | **2026-06-01** | **UNIFICACION: 5 puntos de envio de email actualizados al SSoT — empresa_service, tenants/tasks, resend-invitation, send_activation_email_task, send_invitation_code_email** |
| **v3.15.1** | **2026-06-01** | **FIX: Codigo canonico 8 chars Redis en `send_tenant_activation_email_sync`; `activate.html` tenant rediseñado con formulario email+codigo+password; endpoint `POST /api/v1/core/auth/activate-with-code/`** |
| **v3.15.1** | **2026-06-01** | **FIX: `send_invitation_email_sync` legacy agrega alias `activate_url` en contexto para compatibilidad con template actual** |
| **v3.15.1** | **2026-06-01** | **FIX: `perfil_tenantprofile` FK huerfano en schema `cliente` para user_id=2 eliminado via SQL calificado** |
| **v3.16.0** | **2026-06-01** | **ABSTRACCION: 6 archivos en apps/public/ — nombres propios de tenants reemplazados por placeholders `{schema_name}`, `{schema}.sintel.net.co`; default hardcodeado `home.localhost:8000` → `None` dinamico** |
| **v3.16.0** | **2026-06-01** | **REGLAS: Sección §9 agregada a AUDITORIA con 5 reglas invariantes (filtro console/users, flags de usuario, SSoT email, abstraccion nombres, cobertura tests mínima)** |
| **v3.16.0** | **2026-06-01** | **REGLAS: AGENTS.md — bloque "Nomenclatura y Abstraccion de Configuraciones" con 5 reglas CRITICAS que requieren aprobacion manual para ser modificadas** |
| **v3.16.0** | **2026-06-01** | **TEST: 67/67 passed — corregidos 3 tests: `test_records_total` (filtro visible), `test_search_by_email` (staff user), `test_send_invitation_email_sync` (alias activate_url)** |

---

## 9. Arquitectura de Signals Cross-Schema (v3.11.0)

### 9.1 Signal `global_user_hard_deleting`

Patron de comunicacion desacoplada entre el esquema public y los schemas tenant para la eliminacion de usuarios:

```
apps/public/accounts/signals.py
    global_user_hard_deleting = Signal()         ← definicion (public side)

apps/public/accounts/services/delete_user_service.py
    global_user_hard_deleting.send(sender=User, user=instance)  ← emision

apps/tenant/core/services/membership.py
    _on_global_user_hard_deleting(sender, user, **kwargs)       ← receiver
        for membership in TenantMembership.filter(user=user):
            with tenant_context(membership.client):
                TenantProfile.objects.filter(user=user).delete()

apps/tenant/core/apps.py (TenantCoreConfig.ready)
    global_user_hard_deleting.connect(_on_global_user_hard_deleting, weak=False)
```

**Principios aplicados:**
- Signal definido en `apps.public` — no conoce TenantProfile (aislamiento)
- Receiver en `apps.tenant.core` (bridge autorizado) — usa API oficial `tenant_context()`
- Conexion en `AppConfig.ready()` — garantiza registro al arranque
- `weak=False` — evita garbage collection del receiver

### 9.2 Codigos de Activacion — Redis Keys

| Clave | Valor | TTL | Patron |
|---|---|---|---|
| `invite:code:{8_alfanumericos}` | `{user_id, tenant_id, expires_at}` | 86400s (24h) | Uso unico — se elimina al validar |
| `onboard:{uuid}` | `{user_id, schema_name, domain}` | 300s (5 min) | Uso unico — se elimina al consumir |

**Entropia del codigo (v3.12.0):**
- Alfabeto: 32 simbolos (`ABCDEFGHJKMNPQRSTUVWXYZ23456789`, excluye O/0/I/1/L)
- Longitud: 8 caracteres
- Espacio total: **32^8 = 1,099,511,627,776 ≈ 1.1 × 10¹²** combinaciones
- Con 10.000 codigos activos simultaneos: P(colision) ≈ (10^4)^2 / (2 × 1.1×10^12) ≈ **4.5 × 10⁻⁵** (despreciable)
- Generacion via `secrets.choice()` — CSPRNG, no `random.randint`
- **Zero Collision** para volumenes de PYMES (cientos de tenants activos).

---

## 10. Deuda Técnica

| ID | App | Severidad | Estado | Descripción |
|---|---|---|---|---|
| DT-PUB-01 | `console` | MEDIA | **RESUELTO v3.14.0** | 56 tests: `test_views.py` (15) + `test_api_views.py` (41). Cubre acceso, DataTables, CRUD, delete mock, health, fixtures |
| DT-PUB-02 | `core` | BAJA | **RESUELTO v3.12.0** | `test_public_index_view.py` — 4 smoke tests (anonimo, staff, miembro, sin membresia); `test_email_service.py` existente |
| DT-PUB-03 | `tenants` | BAJA | **RESUELTO v3.10.5** | `delete_model` simplificado — delega 100% a `hard_delete_tenant()`. Imports globales. |
| DT-PUB-04 | `accounts/console` | BAJA | **RESUELTO v3.10.5** | `UsersDataTableView.delete()` ahora delega a `delete_user_service()` (DeletionAudit, JWT blacklist, cross-schema cleanup) |
| DT-PUB-05 | `tenants` | BAJA | Analizado — ver abajo | 30 management commands catalogados por categoría |

---

### DT-PUB-05 — Inventario y Clasificación de Management Commands (30 total)

**Clasificación por propósito y uso en producción:**

| Categoría | Commands | Acción recomendada |
|---|---|---|
| **Producción esencial** | `crear_empresa`, `setup_public_tenant`, `create_public_tenant`, `ensure_public_domain`, `ensure_public_domains`, `migrate_tenant_if_needed`, `backup_tenant`, `backup_all_tenants`, `restore_tenant`, `maildigester_run`, `owner_activation_reset_and_token` | Mantener activos |
| **Operaciones / fix puntual** | `fix_tenant_domain`, `fix_tenant_domains`, `fix_all_tenant_domains`, `fix_dev_domains`, `fix_migration_history`, `cleanup_tenant_duplicates` | Mantener — usar con precaución |
| **Diagnostico / audit** | `auditar_tenant`, `auditar_dominios_tenants`, `auditar_referencias_admin_login`, `check_domains`, `validate_domain_correspondence`, `show_tenant_hosts`, `inspect_tenant_columns`, `diagnostico_404`, `diagnostico_routing`, `verificar_eliminacion_tenant` | Mantener — considerar `DEBUG`-gate en prod |
| **Pruebas / desarrollo** | `generar_tenants_prueba`, `analizar_tenants_prueba` | **BLINDADOS v3.12.0** — guard `DEBUG=False` activo; imports globales limpios |

**v3.12.0 RESUELTO:** Guard aplicado en ambos comandos. Imports de `settings` y `CommandError` movidos al nivel de modulo. Mensaje estandar: `"PeligRO CRITICO: Este comando es destructivo y no puede ejecutarse en un entorno de produccion (DEBUG=False)."`

---

## 11. Historial de Cambios — v3.10.5 → v3.13.0

| Cambio | Archivo | Descripcion |
|---|---|---|
| DT-PUB-03 | `tenants/admin.py` | v3.10.5: `delete_model` simplificado — delega a `hard_delete_tenant()` |
| DT-PUB-04 | `console/api/views.py` | v3.10.5: `UsersDataTableView.delete()` delega a `delete_user_service()` |
| Celery tasks | `core/tasks.py` + `config/celery.py` | v3.11.0: `send_invitation_code_email_task` + registro explicito en `app.conf.imports` |
| Management commands | `tenants/management/commands/generar_tenants_prueba.py` | v3.12.0: imports globales; guard `DEBUG=False`; mensaje estandar |
| Management commands | `tenants/management/commands/analizar_tenants_prueba.py` | v3.12.0: `CommandError` + `settings` al nivel modulo; guard `DEBUG=False` |
| invitations.py | `tenants/services/invitations.py` | v3.12.0: `import secrets` reemplaza `import random`; `_CODE_ALPHABET`, `_CODE_LENGTH=8`; validacion + normalizacion upper() |
| activate view | `tenants/views.py:ActivateAccountView.post` | v3.12.0: validacion `len!=8` reemplaza `isdigit()+len!=6` |
| Template | `tenants/templates/public/activate_password.html` | v3.12.0: `maxlength=8`, `pattern=[A-Za-z0-9]{8}`, JS uppercase filter |
| Smoke tests | `core/tests/test_public_index_view.py` | v3.12.0: 4 tests completos — anonimo, staff, miembro activo, sin membresia |
| Email SMTP | `.env` | v3.13.0: `EMAIL_BACKEND=smtp`, `EMAIL_HOST=smtp.gmail.com`, `EMAIL_HOST_PASSWORD` App Password sin espacios |
| Activation URL | `.env` | v3.13.0: `ACTIVATION_BASE_URL=https://sintel.net.co` (dominio publico raiz) |
| DNS Windows | PowerShell manual | v3.13.0: A records individuales para cada tenant via `ensure_tenant_dns` (manual); tarea programada eliminada en v3.16.0 |
| Docker hosts | `docker-compose.yaml` | v3.13.0: `extra_hosts` en `x-app-base`; incluye `sintel.net.co` y todos los subdominios tenant activos |
| ensure_tenant_dns | `tenants/management/commands/ensure_tenant_dns.py` | v3.13.0: eliminada `_update_compose_extra_hosts`; solo DNS Windows + hints manuales |
| JWT config | `.env` + `config/settings.py` | v3.14.0: `JWT_SECRET_KEY` fija en `.env`; eliminado `warnings.warn` |
| public_api_urls.py | `config/public_api_urls.py` | v3.14.0: simplificado 105→35 lineas; eliminados logger.info, fallback routers, imports dinamicos |
| Password reset code | `tenant/core/services/password_reset.py` | v3.14.0: `generate_reset_code` + `validate_reset_code` Redis (TTL 1h, cross-tenant isolation) |
| Password reset endpoints | `tenant/core/api/viewsets.py` | v3.14.0: `password_reset_confirm` acepta `{code, new_password}`; `password_reset_request` acepta `email` O `email_or_username` |
| Console tests | `console/tests/` (3 archivos) | v3.14.0: 56 tests — DT-PUB-01 RESUELTO |
| ConsoleUserListSerializer | `console/api/serializers.py` | v3.14.0: campo `tenants` con `domain_url = f"{protocol}://{schema}.{TENANT_DOMAIN_BASE}"` |
| Console API endpoints | `console/api/views.py` + `urls.py` | v3.14.0: `OrphanTenantsView`, `AssignTenantView`, `UserTenantsView` |
| Console users UI | `console/templates/pages/users/list.html` | v3.14.0: columna URL dominio (link), boton Asignar, modal tenants huerfanos |
| users_manager.js | `console/static/js/users_manager.js` | v3.14.0: badge `domain_url` como `<a href>`, `openAssignTenantModal`, `assignTenantToUser` |
| Clasificacion usuarios | BD + `console/api/views.py` | v3.15.0: `is_staff=False` para owners de tenants; filtro `console/users/` por superuser OR primary_admin |
| createsuperuser override | `accounts/management/commands/createsuperuser.py` | v3.15.0: crea superusuario + TenantMembership al tenant indicado |
| ensure_admin | `accounts/management/commands/ensure_admin.py` | v3.15.0: SOLO verifica — no crea usuarios |
| entrypoint.sh | `entrypoint.sh` | v3.15.0: eliminada llamada a `ensure_admin` y mensaje `sintel_dev / admin123` |
| SafeTokenRefreshView | `core/api/views.py` + `config/urls_public.py` | v3.15.0: 401 en lugar de 500 cuando user del token fue eliminado |
| home tenant eliminado | BD + DNS + docker-compose | v3.15.0: `home` tenant dropeado permanentemente; `admin@home.com` desactivado |
| EmailService SSoT | `core/services/email_service.py` | v3.15.0: `send_tenant_activation_email(user, tenant)` — genera token + URL tenant especifica sin parametros externos |
| Celery task SSoT | `core/tasks.py` | v3.15.0: `send_tenant_activation_email_task` — generacion interna del token |
| Email template | `core/templates/owner_invitation.html/.txt` | v3.15.0: boton apunta a `{schema}.sintel.net.co/static/tenant/core/auth/activate.html?token=...` |
| empresa_service | `services/onboarding/empresa_service.py` | v3.15.0: usa `EmailService.send_tenant_activation_email` |
| tenants/tasks | `public/tenants/tasks.py` | v3.15.0: `send_activation_email_task` delega a `EmailService.send_tenant_activation_email_sync` |
| resend-invitation | `public/tenants/api/viewsets.py` | v3.15.0: usa `EmailService.send_tenant_activation_email` |
| activate.html (tenant) | `tenant/core/static/tenant/core/auth/activate.html` | v3.15.1: rediseñado — email + codigo 8 chars + password; llama `activate-with-code/` |
| activate-with-code endpoint | `tenant/core/api/viewsets.py` | v3.15.1: `POST /api/v1/core/auth/activate-with-code/` — valida codigo Redis + sets password |
| email_service legacy fix | `core/services/email_service.py` | v3.15.1: `send_invitation_email_sync` agrega `activate_url` alias en contexto |
| FK huerfano | BD PostgreSQL | v3.15.1: `DELETE FROM "cliente"."perfil_tenantprofile" WHERE user_id=2` |
| ensure_admin help | `accounts/commands/ensure_admin.py` | v3.16.0: ejemplo `--tenant home` → `--tenant <schema_name>` + instruccion ORM dinamica |
| createsuperuser help | `accounts/commands/createsuperuser.py` | v3.16.0: `(ej: home)` → `(ej: <schema_name>)` con instruccion ORM |
| diagnostico_404 | `tenants/commands/diagnostico_404.py` | v3.16.0: default `home.localhost:8000` → `None` dinamico; help usa `{schema}.sintel.net.co` |
| ensure_tenant_dns | `tenants/commands/ensure_tenant_dns.py` | v3.16.0: `--schema putito` → `--schema <schema_name>`; comentario excepcion dominio publico |
| owner_activation_reset | `tenants/commands/owner_activation_reset_and_token.py` | v3.16.0: ejemplos `cliente.sintel.net.co` → `{schema}.sintel.net.co` |
| middleware.py | `core/middleware.py` | v3.16.0: comentarios `cliente.localhost`, `tupapi.com` → `{schema}.localhost`, `{schema}.sintel.net.co` |
| test_api_views | `console/tests/test_api_views.py` | v3.16.0: `make_normal_user` → `make_staff_user` en list tests; import `make_staff_user`; `test_records_total` cuenta visibles |
| AGENTS.md | `AGENTS.md` | v3.16.0: bloque "Nomenclatura y Abstraccion" con 5 reglas CRITICAS INMUTABLES |
| AUDITORIA | `apps/public/.agent/AUDITORIA_FLUJO_CORE_PUBLIC.md` | v3.16.0: §9 Reglas Invariantes (5 reglas con aprobacion manual requerida) |
