# 🧠 Lógica de Negocio: Módulo Accounts (SSoT)

Este documento centraliza las reglas de identidad y seguridad de usuarios globales.

---

## 1. Identidad Unívoca (Email-First)

- **Email como PK Lógica**: El email es el identificador único en todo el sistema. No se permiten dos registros con el mismo email en el esquema público.
- **Normalización**: Todos los emails se convierten a minúsculas antes de la validación y persistencia.

---

## 2. Aislamiento Cross-Schema (Unidireccionalidad)

- **Independencia de Esquema**: El modelo `User` en `public` no debe tener llaves foráneas (`ForeignKey`) hacia ningún modelo que pertenezca al esquema `tenant` (ej. `Factura`, `Producto`).
- **Referencia Inversa**: Los modelos de tenant referencian al `User` global. Al borrar un `User`, se debe asegurar que las referencias en los tenants se manejen mediante `on_delete=PROTECT` o limpieza orquestada para evitar inconsistencias.

---

## 3. Seguridad de Contraseñas e Invitaciones

- **Unusable Passwords**: Los usuarios creados automáticamente durante invitaciones no tienen contraseña. Deben usar el flujo de recuperación de contraseña (o activación) para establecer una inicial.
- **Validación de Complejidad**: El sistema aplica los validadores estándar de Django para asegurar contraseñas robustas.

---

## 4. Política de Eliminación y Auditoría

- **Borrado Físico vs Lógico**: Por defecto, la eliminación de un usuario es física en la tabla `User`, pero se genera un registro inmutable en `DeletionAudit` con el ID original y el timestamp para propósitos forenses y legales.
- **Integridad de Datos**: El `DeleteUserService` es el único encargado de garantizar que no queden registros huérfanos en los esquemas de inquilinos.

---

## 5. Roles Administrativos Globales (is_staff / is_superuser)

- **is_superuser**: Acceso total a la base de datos vía admin de Django. Solo para personal técnico de infraestructura.
- **is_staff**: Acceso a la consola administrativa global (`/console/`) para gestión de inquilinos y soporte a usuarios.
