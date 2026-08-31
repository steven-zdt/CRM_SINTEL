# CONSOLE_TENANTS_CRUD — Fase 1, 33

Matriz real de CRUD (código verificado, no asumido) por entidad.

## Matriz (Fase 1)

| Entidad | CREATE | READ | UPDATE | DELETE | Acciones especiales | Permisos | Audit |
|---|---|---|---|---|---|---|---|
| `Client`/Tenant | ✅ `POST .../onboard/` (+ `POST .../` estándar DRF) | ✅ list/retrieve | ✅ `PATCH`/`PUT` estándar DRF | ⚠️ Soportado por el modelo (`Client.delete()`, con candado anti-borrado del schema `public`), **sin endpoint/UI que lo dispare desde consola** — decisión correcta per Fase 5 del plan ("no implementar hard-delete automáticamente... si no existe política formal, usar DESACTIVAR") | `toggle-active`, `extend-trial` (**nueva**), `resend-invitation`, `manual-activate` (⚠️ roto, ver E2E-06), `admin-set-password` | `IsAdminUser` + `SessionAuthentication` en todas | ✅ `TENANT_CREATE` y `TENANT_UPDATE`/`EXTEND_TRIAL` **ahora auditados** (antes: gap E2E-05, cerrado en esta misión para estas 3 acciones) |
| `Domain` | ❌ Sin endpoint de API dedicado — solo se crea indirectamente vía el flujo de onboarding (`crear_tenant_con_owner()`) | ✅ `DomainViewSet` (`ReadOnlyModelViewSet`) | ❌ Sin endpoint | ❌ Sin endpoint | Ninguna | `IsAdminUser` (lectura) | ❌ Sin auditoría |
| `TenantMembership` | ❌ Sin API REST dedicada (se crea indirectamente en el onboarding) | ❌ Sin ViewSet propio | ❌ Sin endpoint (cambiar rol, activar/desactivar membresía) | ❌ Sin endpoint | Ninguna | N/A | ❌ Sin auditoría |

## Gaps reales identificados (Fase 6-7) — DEFERRED, no corregidos en esta pasada

**Domain CRUD (más allá de lectura) y Membership CRUD completo NO
existen como API dedicada.** Esto es una brecha real frente al objetivo
de la misión ("gestionar dominio", "gestionar membresías" desde
consola). Se documenta explícitamente en vez de improvisar una
implementación apresurada, por las siguientes razones:

1. **Riesgo real si se hace mal:** Domain tiene una regla de negocio
   dura (`unique_primary_domain_per_tenant`, "no permitir que un
   dominio activo apunte simultáneamente a dos tenants") que requiere
   diseño cuidadoso de validación + tests de concurrencia (Fase 34) —
   exactamente el tipo de trabajo que esta sesión, por norma, no
   apresura.
2. **TenantMembership CRUD** requiere decisiones de permisos no
   triviales (¿puede un ADMIN de tenant gestionar sus propias
   membresías, o es exclusivo de staff global?) que no estaban resueltas
   en el código existente y que esta misión no debía inventar sin
   evidencia de la política real de negocio.
3. El objetivo de **mayor valor y riesgo real de seguridad** de esta
   misión — el trial REAL y efectivo — ya consumió el tiempo disponible
   con la profundidad que merece (implementación + verificación en vivo
   + tests). Ampliar el alcance a un CRUD completo de 2 entidades más
   habría diluido esa calidad.

**Recomendación para una sesión dedicada futura:** implementar
`DomainViewSet` con `create`/`update`/`destroy` (validando unicidad de
`is_primary` y de `domain` global), y un `TenantMembershipViewSet`
(crear/cambiar rol/activar/desactivar, con `unique_together` ya
existente en el modelo como guardarraíl), ambos con auditoría en
`ConsoleActionLog`, reutilizando el helper `_log_console_action()` ya
creado en `ClientViewSet` en esta misión (mover a un mixin compartido
si se implementa).

## API — códigos de estado reales (Fase 33)

| Endpoint | Método | 200/201 | 400 | 403 | 404 | 409 |
|---|---|---|---|---|---|---|
| `.../onboard/` | POST | 201 | Validación (schema_name, dominio, email) | No staff | — | — (duplicado de schema_name da 500, ver `E2E-04`, no corregido — mismo punto de código que `task_6ea17ebf`) |
| `.../{id}/toggle-active/` | POST | 200 | — | No staff | Tenant no existe | — |
| `.../{id}/extend-trial/` | POST | 200 (**nuevo**) | Sin `days`/`paid_until`, fecha inválida, fecha no futura | No staff | Tenant no existe | — |
| `.../{id}/manual-activate/` | POST | 200 | Sin admin primario, sin dominio | No staff | Tenant no existe | 409 si ya activó |
| `.../{id}/admin-set-password/` | POST | 200 | Password < 8 chars o débil | No staff | Tenant no existe | — |
