# 🏗️ Arquitectura de Microtareas (MT-ACC): Módulo Accounts

Sistema de trazabilidad técnica para la evolución de la gestión de usuarios globales.

---

## 🛠️ Fase 1: Integridad y Datos (Data Layer)

- `[ ]` **MT-ACC-001**: Implementar `DeletionAudit` para el registro de bajas de usuarios.
- `[ ]` **MT-ACC-002**: Refactorizar `UserManager` para mejorar la resolución de colisiones en usernames.
- `[ ]` **MT-ACC-003**: Auditoría de unicidad de email en migraciones de PostgreSQL.
- `[ ]` **MT-ACC-004**: Implementar validación de dominios de email permitidos (Blacklist/Whitelist).

---

## 🧠 Fase 2: Lógica de Servicios (Service Layer)

- `[ ]` **MT-ACC-010**: Desarrollar `DeleteUserService` con soporte para limpieza asíncrona en múltiples tenants.
- `[ ]` **MT-ACC-011**: Crear validador de complejidad de contraseña personalizado para el entorno SINTEL.
- `[ ]` **MT-ACC-012**: Implementar lógica de detección de cuentas inactivas para procesos de purga automática.

---

## 🌐 Fase 3: API y Autenticación (API Layer)

- `[ ]` **MT-ACC-020**: Migrar `AccountsViewSet` a `lookup_field='id'` (UUID no disponible en modelos base Django Auth, evaluar extensión).
- `[ ]` **MT-ACC-021**: Implementar filtrado por `is_active` y `date_joined` con optimización `.only()`.
- `[ ]` **MT-ACC-022**: Documentación OpenAPI para el endpoint de registro administrativo.

---

## 🎨 Fase 4: Consola Administrativa (UI Layer)

- `[ ]` **MT-ACC-030**: Crear vista de gestión de usuarios en la consola global con soporte para Tabulator.
- `[ ]` **MT-ACC-031**: Implementar búsqueda global de usuarios por email/nombre.
- `[ ]` **MT-ACC-032**: UI para bloqueo/desbloqueo masivo de usuarios desde la consola central.
