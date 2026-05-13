# 🧠 Lógica de Negocio: Módulo Perfil (SSoT)

Este documento centraliza las reglas de identidad, jerarquía de roles y seguridad de acceso.

---

## 1. Identidad Unificada (User vs TenantProfile)

- **Unicidad**: Cada combinación de `(User, Empresa)` debe ser única. Un usuario puede tener múltiples perfiles en diferentes tenants, pero solo uno por empresa.
- **SSoT de Atributos**: Los datos globales (email, nombres) residen en el modelo `User` (esquema público), mientras que los datos operativos (cargo, departamento, rol interno) residen en `TenantProfile`.

---

## 2. Jerarquía de Roles y Privilegios (RBAC)

- **ADMIN**: Acceso total a la configuración de la empresa, gestión de otros perfiles y operaciones CRUD críticas.
- **OPERADOR**: Permisos de creación y edición en módulos operativos, restringido de configuraciones administrativas.
- **VISOR**: Acceso de solo lectura a los módulos autorizados.

> [!IMPORTANT]
> El rol es específico del tenant. Un usuario puede ser `ADMIN` en la Empresa A y `VISOR` en la Empresa B.

---

## 3. Reglas de Auto-Elevación Administrativa

- **Owner Persistence**: El usuario cuyo email coincide con `Empresa.owner_email` es considerado el administrador principal.
- **Sincronización Silenciosa**: Al iniciar sesión, si el perfil del propietario no tiene el rol `ADMIN`, el sistema lo eleva automáticamente para garantizar que nunca pierda el acceso al control de su empresa.

---

## 4. Gestión de Invitaciones y Usuarios

- **Provisión Idempotente**: Si se intenta crear un perfil para un email que ya existe en el sistema global, se vincula el usuario existente al tenant en lugar de crear un duplicado.
- **Estado de Invitación**: Los usuarios nuevos creados desde este módulo no tienen contraseña activa (`unusable_password`). Deben pasar por el flujo de activación/recuperación de contraseña para acceder por primera vez.

---

## 5. Integridad del Acceso Administrativo

- **Protección del Último Admin**: El sistema bloquea cualquier operación de borrado o cambio de rol que resulte en un tenant sin administradores activos. Esta validación se realiza a nivel de `BusinessService` antes de cualquier transacción.
- **Double Semantic Verification (DSV)**: Toda mutación de perfiles debe validar que el `id` del perfil pertenezca a la `empresa_id` del tenant autenticado para prevenir ataques de desplazamiento horizontal (IDOR).
