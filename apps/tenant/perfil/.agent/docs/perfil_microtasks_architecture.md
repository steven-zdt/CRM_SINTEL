# 🏗️ Arquitectura de Microtareas (MT-PRF): Módulo Perfil

Sistema de trazabilidad técnica para la evolución del módulo de gestión de usuarios.

---

## 🛠️ Fase 1: Capa de Datos e Integridad (Data Layer)

- `[ ]` **MT-PRF-001**: Migración de `lookup_field` a `uuid` en `PerfilViewSet`.
- `[ ]` **MT-PRF-002**: Refactorizar `PerfilSelector` para usar `.only()` en consultas de listado de colaboradores.
- `[ ]` **MT-PRF-003**: Implementar constraint de unicidad `(user, empresa)` a nivel de base de datos para prevenir perfiles duplicados.
- `[ ]` **MT-PRF-004**: Auditoría de índices en `TenantProfile`: `[empresa, rol]` para reportes rápidos de jerarquía.

---

## 🧠 Fase 2: Lógica de Negocio y Seguridad (Service Layer)

- `[ ]` **MT-PRF-010**: Implementar `Double Semantic Verification (DSV)` en el método de actualización de roles.
- `[ ]` **MT-PRF-011**: Desarrollar validador `is_last_admin(perfil_id)` en `PerfilBusinessService`.
- `[ ]` **MT-PRF-012**: Integrar flujo de auto-elevación de privilegios para `owner_email` en el Fast Path de `/me/`.
- `[ ]` **MT-PRF-013**: Crear `PerfilServiceMixin` para estandarizar el acceso a servicios desde el ViewSet.

---

## 🌐 Fase 3: API y Contratos (API Layer)

- `[ ]` **MT-PRF-020**: Exponer endpoint `/api/v1/perfil/perfiles/me/` con caché de sesión para optimizar carga inicial del workspace.
- `[ ]` **MT-PRF-021**: Implementar `HX-Trigger` en todas las respuestas POST/PATCH para actualización reactiva del menú de navegación.
- `[ ]` **MT-PRF-022**: Documentación Swagger/OpenAPI para el flujo de invitación a terceros.

---

## 🎨 Fase 4: Interfaz de Usuario (UI/UX)

- `[ ]` **MT-PRF-030**: Migrar gestión de colaboradores a Tabulator con soporte para cambio de rol in-line (solo para ADMIN).
- `[ ]` **MT-PRF-031**: Crear `offcanvas_detalle_perfil.html` con vista de actividad reciente del colaborador.
- `[ ]` **MT-PRF-032**: Implementar UI Shield en formularios de edición para proteger campos inmutables como el email.
- `[ ]` **MT-PRF-033**: Namespace JS `window.Sintel.Perfil` con submódulos `list` y `editor`.
