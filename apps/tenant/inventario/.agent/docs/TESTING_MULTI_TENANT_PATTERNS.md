# Testing Multi-Tenant: Patrones Obligatorios y Anti-Patrones

**Versión:** 3.5.1
**Fecha:** 2026-05-15
**Aplicable a:** Todos los tests bajo `tests/tenant/<app>/`

---

## Causa Raíz del Bug (Sesión 2026-05-15)

### El Problema

Los tests de permisos CRUD en `tests/tenant/inventario/test_crud_permissions.py`
fallaban con `405 != 201` y `405 != 200` para el usuario `admin_user`, incluso
en modo `DEBUG=True`.

**Síntomas:**
- `test_admin_can_create` → `AssertionError: 405 != 201`
- `test_admin_can_update` → `AssertionError: 405 != 200`
- Rol `STAFF` inexistente en el sistema

**Cadena de fallo:**

```
BaseViewSet.create()
  → _check_enforced_mode(request)
    → request.user.is_authenticated  # False / AnonymousUser
  → retorna (False, "Usuario no autenticado")
  → Response(status=405)
```

### Causa Raíz 1: Esquema Incorrecto para Creación de Usuarios

`User` vive en el esquema **public** (SHARED_APPS).
`TenantProfile` vive en el esquema **tenant**.

El setUp de los tests creaba `User.objects.create_user(...)` **sin** cambiar
el esquema de la conexión explícitamente. En el contexto del test de tenant,
la conexión apunta al esquema del tenant, y aunque Django maneja `User` en
público, la mezcla de contextos causaba inconsistencias.

**Anti-patrón (PROHIBIDO):**
```python
def setUp(self):
    super().setUp()  # conexión está en tenant schema
    # INCORRECTO: crear usuario sin context explicito
    self.admin_user = User.objects.create_user(username="admin@test.com", ...)
    # TenantMembership con rol STAFF (NO EXISTE en SINTEL)
    TenantMembership.objects.create(client=self.tenant, user=self.admin_user, rol="STAFF")
```

### Causa Raíz 2: Confusión entre TenantMembership.rol y TenantProfile.rol

La capa de permisos `IsTenantAdmin` (y `_check_enforced_mode`) verifica
**`TenantProfile.rol`** (SSoT de permisos), NO `TenantMembership.rol`.

Si el `admin_user` tiene `TenantMembership(rol='ADMIN')` pero NO tiene
`TenantProfile` en el esquema del tenant, `IsTenantProfileAdmin.has_permission()`
retorna `False` en producción (y `True` en DEBUG gracias al fallback).

Sin embargo, cuando el usuario no está correctamente autenticado en el request
(`request.user.is_authenticated == False`), `_check_enforced_mode` retorna
`False` antes de llegar a `IsTenantAdmin`.

### Causa Raíz 3: Rol `STAFF` Inexistente

`RolTenant` (SSoT en `apps/tenant/perfil/models.py`) define exactamente 3 roles:
- `ADMIN`
- `OPERADOR`
- `VISOR`

El rol `STAFF` no existe. Crearlo en `TenantMembership` no rompe la DB (es
CharField libre), pero nunca coincide con ningún permiso real.

---

## Patrón Correcto Obligatorio para Tests Multi-Tenant

### 1. Crear Usuarios en el Esquema Public

```python
from django_tenants.utils import get_public_schema_name, schema_context
from django.contrib.auth import get_user_model

User = get_user_model()

def _create_user_in_public(self, username, email, password='testpass123'):
    """
    OBLIGATORIO: User siempre se crea en esquema public.
    """
    public_schema = get_public_schema_name()
    with schema_context(public_schema):
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=True,
        )
    return user
```

### 2. Crear TenantProfile en el Esquema del Tenant

```python
def _create_tenant_profile(self, user, empresa, rol):
    """
    OBLIGATORIO: TenantProfile se crea en el esquema del tenant (conexión activa).
    El rol debe ser uno de: 'ADMIN', 'OPERADOR', 'VISOR'.
    """
    from apps.tenant.perfil.models import TenantProfile
    return TenantProfile.objects.create(
        user=user,
        empresa=empresa,
        rol=rol,  # SOLO: 'ADMIN' | 'OPERADOR' | 'VISOR'
    )
```

### 3. Crear TenantMembership en el Esquema Public

```python
public_schema = get_public_schema_name()
with schema_context(public_schema):
    from apps.public.tenants.models import TenantMembership
    TenantMembership.objects.create(
        client=self.tenant,
        user=self.admin_user,
        rol='ADMIN',     # SOLO: 'ADMIN' | 'OPERADOR' | 'VISOR' (NO 'STAFF')
        is_active=True
    )
```

### 4. Crear APIClient Independiente por Rol

```python
def _make_client_for(self, user, domain):
    """Un cliente por usuario. NO reutilizar self.api_client entre roles."""
    client = APIClient(HTTP_HOST=domain)
    client.force_authenticate(user=user)
    return client

# En setUp():
domain = self.domain.domain
self.admin_client = self._make_client_for(self.admin_user, domain)
self.visor_client = self._make_client_for(self.visor_user, domain)
```

### 5. Secuencia Correcta de setUp

```python
def setUp(self):
    super().setUp()  # Crea tenant, dominio, DB schema

    # 1. Crear empresa singleton PRIMERO
    self.empresa = Empresa.objects.create(
        razon_social="Test Empresa",
        nit="900123456",
        singleton_key=1
    )

    # 2. Crear usuarios EN ESQUEMA PUBLIC
    self.admin_user = self._create_user_in_public("admin@test.com", "admin@test.com")
    self.visor_user = self._create_user_in_public("visor@test.com", "visor@test.com")

    # 3. Crear TenantProfile EN ESQUEMA TENANT (conexión ya activa)
    self._create_tenant_profile(self.admin_user, self.empresa, 'ADMIN')
    self._create_tenant_profile(self.visor_user, self.empresa, 'VISOR')

    # 4. Crear TenantMembership EN ESQUEMA PUBLIC
    public_schema = get_public_schema_name()
    with schema_context(public_schema):
        from apps.public.tenants.models import TenantMembership
        TenantMembership.objects.create(client=self.tenant, user=self.admin_user, rol='ADMIN', is_active=True)
        TenantMembership.objects.create(client=self.tenant, user=self.visor_user, rol='VISOR', is_active=True)

    # 5. Crear clientes API por rol
    domain = self.domain.domain
    self.admin_client = self._make_client_for(self.admin_user, domain)
    self.visor_client = self._make_client_for(self.visor_user, domain)
```

---

## Reglas de Verificación Rápida (Checklist)

Antes de ejecutar cualquier test de permisos, verificar:

- [ ] `User.objects.create_user()` está dentro de `schema_context(get_public_schema_name())`
- [ ] `TenantProfile.objects.create()` está FUERA de `schema_context` (usa el esquema activo del tenant)
- [ ] `TenantMembership.objects.create()` está dentro de `schema_context(get_public_schema_name())`
- [ ] El rol en `TenantProfile` y `TenantMembership` es exactamente `'ADMIN'`, `'OPERADOR'` o `'VISOR'`
- [ ] Cada rol tiene su propio `APIClient` (NO compartir `self.api_client`)
- [ ] La `Empresa` tiene `singleton_key=1` para que `get_empresa_singleton()` la encuentre

---

## Arquitectura de Permisos en _check_enforced_mode

```
request.user.is_authenticated ?
  │
  No → return (False, "Usuario no autenticado") → HTTP 405
  │
  Sí
  │
  request.method in SAFE_METHODS (GET, HEAD, OPTIONS) ?
  │
  Sí → return (True, None) → Permitido (lectura)
  │
  No (POST, PUT, PATCH, DELETE)
  │
  IsTenantAdmin().has_permission(request, view) ?
  │  ↳ En DEBUG: return True (fallback de desarrollo)
  │  ↳ En PROD: verifica TenantProfile.rol == 'ADMIN' + empresa del tenant
  │
  True → return (True, None) → Permitido (escritura)
  No   → return (False, "...") → HTTP 405
```

**Implicación crítica:** Si `request.user.is_authenticated == False`,
el 405 ocurre ANTES de verificar el rol. Un usuario mal configurado
en el test (creado en esquema equivocado) puede resultar en
`AnonymousUser` en el request, causando falsos 405.

---

## Referencia de Roles SINTEL (SSoT)

**Archivo:** `apps/tenant/perfil/models.py` — clase `RolTenant`

| Rol       | Lectura | Escritura | Admin | Válido en Tests |
|-----------|---------|-----------|-------|-----------------|
| `ADMIN`   | Sí      | Sí        | Sí    | Sí              |
| `OPERADOR`| Sí      | No*       | No    | Sí              |
| `VISOR`   | Sí      | No        | No    | Sí              |
| `STAFF`   | —       | —         | —     | **NO EXISTE**   |
| `USER`    | —       | —         | —     | **NO EXISTE**   |

\* OPERADOR puede escribir en algunas apps según configuración del ViewSet.
En inventario, el `BaseViewSet._check_enforced_mode` requiere `ADMIN` para
cualquier mutación.
