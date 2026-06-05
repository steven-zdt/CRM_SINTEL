# Logica de Negocio: Modulo Perfil (SSoT)

Este documento centraliza las reglas de identidad, jerarquia de roles, seguridad de acceso y la sincronizacion de datos organizacionales en SINTEL v3.10.2.

---

## 1. Identidad Unificada (User vs TenantProfile)

- **Unicidad**: Cada combinacion de `(User, Empresa)` debe ser unica. Un usuario puede tener multiples perfiles en diferentes tenants, pero solo uno por empresa inquilina.
- **SSoT de Atributos**: Los datos globales (email, nombres) residen en el modelo `User` (esquema publico), mientras que los datos operativos (cargo, departamento, rol interno) residen en `TenantProfile` (esquema tenant).

---

## 2. Jerarquia de Roles y Privilegios (RBAC)

- **ADMIN**: Acceso total a la configuracion de la empresa, gestion de otros perfiles y operaciones CRUD criticas.
- **OPERADOR**: Permisos de creacion y edicion en modulos operativos, restringido de configuraciones administrativas.
- **VISOR**: Acceso de solo lectura a los modulos autorizados.

> El rol es especifico del tenant. Un usuario puede ser `ADMIN` en la Empresa A y `VISOR` en la Empresa B.

---

## 3. Reglas de Auto-Elevacion Administrativa

- **Owner Persistence**: El usuario cuyo email coincide con `Empresa.owner_email` es considerado el administrador principal.
- **Sincronizacion Silenciosa**: Al iniciar sesion, si el perfil del propietario no tiene el rol `ADMIN`, el sistema lo eleva automaticamente para garantizar que nunca pierda el acceso al control de su empresa.
- **Tier-1 (fast path)**: verificacion intra-schema via `Empresa.owner_email`.
- **Tier-2 (fallback)**: verificacion cross-schema via `TenantMembership.is_primary_admin`.

---

## 4. Gestion de Invitaciones y Usuarios

- **Provision Idempotente**: Si se intenta crear un perfil para un email que ya existe en el sistema global, se vincula el usuario existente al tenant en lugar de crear un duplicado.
- **Estado de Invitacion**: Los usuarios nuevos creados desde este modulo no tienen contrasena activa (`unusable_password`). Debe pasar por el flujo de activacion/recuperacion de contrasena para acceder por primera vez.

---

## 5. Integridad del Acceso Administrativo y SaaS-Defense

### 5a. Proteccion del Ultimo Admin
El sistema bloquea cualquier operacion de borrado o cambio de rol que resulte en un tenant sin administradores activos. Esta validacion se realiza a nivel de `BusinessService` antes de cualquier transaccion.

### 5b. [SEG-5] Guard Anti-Auto-Eliminacion (v3.10.2)

**Regla:** Ningun usuario puede eliminar su propio `TenantProfile`, independientemente de su rol. Tampoco puede eliminarse el perfil del administrador primario del tenant.

**Implementacion en 3 capas:**

**Capa 1 — ViewSet `destroy()`** (`apps/tenant/perfil/api/viewsets.py`):
```python
# Antes de llamar al service, resuelve el perfil destino:
if target_profile.user_id == request.user.id:
    return Response({"error": "No puedes eliminar tu propio perfil de usuario."}, status=400)

if self.perfil_service._is_tenant_primary_admin(target_profile.user):
    return Response({"error": "No se puede eliminar al administrador primario del tenant."}, status=400)
```

**Capa 2 — `permissions_context`** (`apps/tenant/perfil/api/permissions.py`):  
`get_permissions_context()` retorna `'user_id': perfil.user_id`. El endpoint `/me/` expone este valor para que el frontend pueda comparar sin llamada extra.

**Capa 3 — Frontend formatter** (`perfil.page.js`):
```javascript
var isSelf = requestorContext.user_id != null && data.user_id != null
  && Number(data.user_id) === Number(requestorContext.user_id);
var canDelete = actions.includes('delete') && !isSelf;
```
El boton "Eliminar" no se renderiza para la propia fila del usuario autenticado.

### 5c. Double Semantic Verification (DSV)
Toda mutacion de perfiles debe validar que el `id` del perfil pertenezca a la `empresa_id` del tenant autenticado para prevenir ataques de desplazamiento horizontal (IDOR).

---

## 6. Sincronizacion Perfil <-> Empresa (Sedes, Areas y Departamentos)

Para evitar asignaciones invalidas en el sistema SaaS, se aplican las siguientes reglas de negocio y consistencia:

- **Validacion de Pertenencia (DSV en Mutaciones)**:
  - Todas las sedes en `sedes_asignadas` deben pertenecer a la empresa del perfil.
  - Todas las areas en `areas_asignadas` deben pertenecer a las sedes que pertenecen a la empresa del perfil.
  - El `departamento` del perfil debe pertenecer a la empresa del perfil.
- **Zero Waste ORM**: Las consultas en viewsets y selectors filtran estrictamente por el `empresa_id` del tenant y usan `.only()` o `.defer()` para evitar recuperar campos innecesarios y prevenir la sobrecarga de consultas N+1 en las tablas organizacionales.
- **DOM Shield**: La UI remueve el atributo `name` de los selectores visibles de Sedes, Areas y Departamentos para evitar la manipulacion y sobreescritura maliciosa de datos en el cliente. El envio al backend se realiza exclusivamente por `hidden inputs` vinculados a UUIDs.

---

## 7. `permissions_context` — Contrato de la API

El endpoint `GET /api/v1/perfil/perfiles/me/` retorna `permissions_context` como campo de solo lectura calculado. Es el SSoT para la UI respecto a lo que el usuario autenticado puede hacer.

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `can_edit_users` | bool | Puede editar perfiles de otros usuarios |
| `can_delete_users` | bool | Puede eliminar perfiles (sujeto a guards SEG-5) |
| `can_assign_roles` | bool | Puede asignar roles via `/assign-rol/` |
| `can_create_profiles` | bool | Puede crear nuevos perfiles de usuario |
| `is_owner` | bool | Es el administrador primario del tenant |
| `rol` | str | Rol activo: `ADMIN`, `OPERADOR` o `VISOR` |
| `user_id` | int | ID del `User` global del solicitante (para guards per-fila en frontend) |
