# 🧠 Lógica de Negocio: Módulo Console (SSoT)

Este documento centraliza las reglas de administración y auditoría global.

---

## 1. Control de Acceso (Staff Permissions)

- **Staff Enforcement**: Solo usuarios con `is_staff=True` o `is_superuser=True` pueden acceder a las vistas del módulo. El `StaffRequiredMixin` debe ser la primera clase de herencia en cada vista.
- **Contexto Public**: Todas las consultas deben ejecutarse contra el esquema `public`. El `PublicSchemaMixin` garantiza que el middleware no intente resolver un tenant basado en la URL durante las operaciones de consola.

---

## 2. Trazabilidad Inmutable (Action Logging)

- **Registro de Mutaciones**: Cualquier acción que cambie el estado del sistema (Crear, Editar, Eliminar) debe registrarse en `ConsoleActionLog`.
- **Campos de Auditoría**: El log debe capturar el usuario que realiza la acción, el tipo de acción (Enum), el ID del objeto afectado y un campo JSON con el estado previo y posterior (opcional).

---

## 3. Gestión de Recursos Globales

- **Visibilidad Multi-Tenant**: La consola tiene permiso para listar registros de `tenants.Client` independientemente del dominio desde el cual se acceda.
- **Integridad de Usuarios**: Las acciones de bloqueo de usuarios se aplican al `User` global, afectando su acceso a TODOS sus inquilinos vinculados simultáneamente.

---

## 4. Interfaz Basada en Estándares (FSD)

- **Modularidad de Templates**: Los templates deben estar divididos en Partials (ej. `tenants_list_partial.html`) para permitir la actualización parcial vía HTMX.
- **SSoT de JavaScript**: El archivo `jwt-auth.js` es la única fuente de verdad para la inyección de tokens de autorización en peticiones asíncronas desde la consola.

---

## 5. Visualización de la Salud del Sistema

- **Indicadores de Error (DLQ)**: El dashboard debe resaltar inmediatamente cualquier registro en `FailedTenantTask` para que el personal técnico intervenga en fallos de provisionamiento.
