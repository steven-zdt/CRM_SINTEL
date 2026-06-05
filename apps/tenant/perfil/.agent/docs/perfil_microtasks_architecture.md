# Arquitectura de Microtareas (MT-PRF): Modulo Perfil

Sistema de trazabilidad tecnica para la evolucion del modulo de gestion de usuarios en SINTEL v3.10.2.

---

## Fase 1: Capa de Datos e Integridad (Data Layer)

- `[x]` **MT-PRF-001**: Migracion de `lookup_field` a `uuid` en `PerfilViewSet`.
- `[x]` **MT-PRF-002**: Refactorizar `PerfilSelector` para usar `.only()` en consultas de listado de colaboradores.
- `[ ]` **MT-PRF-003**: Implementar constraint de unicidad `(user, empresa)` a nivel de base de datos para prevenir perfiles duplicados.
- `[ ]` **MT-PRF-004**: Auditoria de indices en `TenantProfile`: `[empresa, rol]` para reportes rapidos de jerarquia.

---

## Fase 2: Logica de Negocio y Seguridad (Service Layer)

- `[x]` **MT-PRF-010**: Implementar `Double Semantic Verification (DSV)` en el metodo de actualizacion de roles y asignaciones organizacionales.
- `[ ]` **MT-PRF-011**: Desarrollar validador `is_last_admin(perfil_id)` en `PerfilBusinessService`.
- `[x]` **MT-PRF-012**: Integrar flujo de auto-elevacion de privilegios para `owner_email` en el Fast Path de `/me/`.
- `[x]` **MT-PRF-013**: Crear `PerfilServiceMixin` para estandarizar el acceso a servicios desde el ViewSet.
- `[x]` **MT-PRF-014**: [SEG-5] Guard anti-auto-eliminacion en `destroy()` — bloquea borrado del propio perfil y del admin primario (2 guards en ViewSet + 1 en frontend). Implementado 2026-05-25.

---

## Fase 3: API y Contratos (API Layer)

- `[x]` **MT-PRF-020**: Exponer endpoint `/api/v1/perfil/perfiles/me/` con cache de sesion para optimizar carga inicial del workspace.
- `[x]` **MT-PRF-021**: Implementar `HX-Trigger` en todas las respuestas POST/PATCH para actualizacion reactiva del menu de navegacion ("perfilesChanged").
- `[x]` **MT-PRF-023**: Agregar campo `user_id` a `permissions_context` (retornado por `/me/`) para que el frontend pueda identificar la fila propia del usuario autenticado sin llamada extra.
- `[ ]` **MT-PRF-022**: Documentacion Swagger/OpenAPI para el flujo de invitacion a terceros.

---

## Fase 4: Interfaz de Usuario (UI/UX)

- `[x]` **MT-PRF-030**: Migrar gestion de colaboradores a Tabulator con soporte para cambio de rol in-line (solo para ADMIN).
- `[x]` **MT-PRF-031**: Crear `offcanvas_detalle_perfil.html` con vista de actividad reciente del colaborador.
- `[x]` **MT-PRF-032**: Implementar UI Shield en formularios de edicion para proteger campos inmutables como el email.
- `[x]` **MT-PRF-033**: Namespace JS `window.Sintel.Perfil` con submodulos `list` y `editor`.
- `[x]` **MT-PRF-034**: [SEG-5] Ocultar boton "Eliminar" en la fila propia del usuario autenticado via comparacion `data.user_id === requestorContext.user_id`. Implementado 2026-05-25.

---

## Fase 5: Sincronizacion Organizacional (v3.9.1)

- `[x]` **MT-PRF-040**: Sincronizacion dinamica de Sedes y Areas en Offcanvas Crear/Editar.
- `[x]` **MT-PRF-041**: Sincronizacion dinamica de Departamentos en Offcanvas Crear/Editar.
- `[x]` **MT-PRF-042**: Implementacion de DOM Shield para remover atributos `name` de selectores visibles en formularios organizacionales.
- `[x]` **MT-PRF-043**: Optimizacion Zero-Waste para consultas de Sedes, Areas y Departamentos con `.only()` en endpoints.
