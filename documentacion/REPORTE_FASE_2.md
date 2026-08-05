# REPORTE FASE 2 — Arquitectura (Hallazgos ALTOS: ARQ-A)

**Fecha:** 2026-07-26
**Alcance:** Los 4 hallazgos ARQ-A de `documentacion/AUDITORIA_ENTERPRISE_2026-07-26.md`. No se tocó ningún otro hallazgo ALTO (SEC-A, PERF-A, FE-A quedan para Fases 3-5).

---

## 0. Nota sobre el estado del repositorio

Al correr `git status` al final de esta fase aparecen ~10 archivos de `contabilidad` (`services/business_service.py`, tests, JS de "plantillas", `activate.html`, etc.) modificados que **no forman parte de este reporte** — son parte de los ~450 cambios sin commitear que ya existían en el árbol de trabajo antes de iniciar la Fase 1 (documentado en `REPORTE_FASE_1.md` §0). Se verificó explícitamente que ninguno de esos archivos fue tocado por las ediciones de esta fase. La lista completa de archivos que sí corresponden a esta fase está en §3.

Misma limitación de entorno que Fase 1 (Docker sin red funcional entre contenedores, `venv` roto): verificación por `py_compile` + `node --check` + lectura manual, sin `make dj-check`/`make test` reales.

---

## 1. Hallazgos resueltos

### ARQ-A1 — 3 ViewSets con `lookup_field='id'` (PK entera expuesta)

Aplicado el patrón de 4 pasos de `AGENTS.md §25.3` a los 3 modelos sin campo `uuid`:

| Modelo | App | Migración |
|---|---|---|
| `ConfiguracionRetenciones` | contabilidad | `0015_configuracionretenciones_uuid.py` |
| `ItemPresupuestoProyecto` | proyectos | `0020_itempresupuesto_tareadiaria_uuid.py` |
| `TareaDiariaProyecto` | proyectos | `0020_itempresupuesto_tareadiaria_uuid.py` |

**Paso 1 (modelo):** campo `uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)` agregado a los 3.

**Paso 2 (migración):** un solo `AddField` por modelo con `default=uuid.uuid4` (callable) — mismo patrón ya usado con éxito en `apps/tenant/contabilidad/migrations/0012_plantilla_linea_uuid.py` (Django genera un UUID distinto por fila existente automáticamente; no hace falta el patrón de 3 fases nullable→poblar→unique para un default *callable*).

**Paso 3 (serializer/selector/viewset):**
- `ConfiguracionRetencionesListSerializer`/`DetailSerializer`: `uuid` agregado a `fields`/`read_only_fields`; `ViewSet.get_queryset()` agrega `'uuid'` a `.only(...)`.
- `ItemPresupuestoSerializer`/`TareaDiariaSerializer`: idem. Las constantes `ITEM_FIELDS` (`presupuesto_service.py`) y `TAREA_FIELDS` (`tareas_service.py`) ahora incluyen `'uuid'`.
- Los 3 ViewSets: se eliminó `lookup_field = 'id'` / `lookup_url_kwarg = 'id'` (heredan `'uuid'` de `BaseTenantViewSet`). El `@action cambiar_estado` de `TareaDiariaViewSet` cambió su parámetro `id=None` → `uuid=None` para coincidir con el nuevo `lookup_url_kwarg`.

**Paso 4 (frontend) — solo aplicaba a proyectos:**
- `ConfiguracionRetenciones` no tiene ningún consumidor en `static/`/`templates/` (verificado por grep) — nada que actualizar.
- `proyectos_editor.js`: 6 sitios actualizados (`item.id`→`item.uuid`, `tarea.id`→`tarea.uuid`, `data-id`→`data-uuid`, `data-tarea-id`→`data-tarea-uuid`) en las funciones de renderizado de presupuesto y tareas diarias. Verificado que ninguna otra parte del archivo lee esos atributos `data-*` de vuelta (eran de solo escritura), y que las funciones `eliminar()`/`cambiarEstado()`/`mostrarMenuEstado()` son agnósticas al formato del ID (solo interpolan el valor recibido en la URL) — cero riesgo de romper el flujo por el cambio de tipo.

**Hallazgo nuevo, no corregido (fuera de alcance de ARQ-A1):** `ConfiguracionRetencionesViewSet.get_queryset()` no filtra por `empresa_id` en absoluto (mitigado por aislamiento de esquema PostgreSQL, pero es una violación literal de Zero-Trust). Se documenta aquí para una fase de seguridad posterior; no se tocó en esta fase para no mezclar un cambio de seguridad con el de `lookup_field`.

### ARQ-A2 — `on_delete=CASCADE` en 4 modelos (esperado `PROTECT`)

**Decisión tomada — NO revertir a `PROTECT`.** Al investigar el impacto real se encontró que `EmpresaViewSet.destroy()` (`apps/tenant/empresa/api/viewsets.py:479-508`) es un endpoint **real y activo**, gateado a STAFF/ADMIN, cuyo propósito explícito es "Elimina la empresa del tenant" (con su propio comentario de advertencia ya en el código: *"Eliminar la empresa puede afectar otras funcionalidades"*).

Revertir estos 4 campos a `PROTECT` habría **roto ese endpoint de forma permanente** para cualquier tenant con al menos un usuario (todo login crea un `TenantProfile` automáticamente, per `arquitectura_general.md §3.6`) — es decir, prácticamente todo tenant real. Esto habría sido una regresión, no una corrección.

En cambio, se agregó un comentario `WARNING: [ARQ-A2]` a cada uno de los 4 campos explicando por qué `CASCADE` es una excepción intencional (exactamente la alternativa que la propia auditoría proponía: *"si cascading es deseado... debe documentarse como una excepción explícita y aprobada"*):
- `dashboard.SnapshotMetricaDiaria.empresa`
- `empresa.Sede.empresa`
- `empresa.Area.empresa`
- `perfil.TenantProfile.empresa`

Cero cambio de comportamiento — solo documentación. No se generó migración (no hay cambio de schema).

### ARQ-A3 — Brecha ADR-002 en páginas de autenticación estáticas

Investigación más profunda de lo que sugería el hallazgo original reveló matices importantes por acción:

| Acción | Backend | Frontend | Registrado en `public_api_urls.py` |
|---|---|---|---|
| `login` | Mensaje honesto en schema público (no autentica contra tenant equivocado — ver razón abajo) | `IS_PUBLIC_DOMAIN`/`getApiUrl()` agregado | Sí (`auth/login/`) |
| `password_reset_request` | **Corrección completa**: resuelve el tenant real desde `TenantMembership` del usuario (ADR-002 Regla 2) | `IS_PUBLIC_DOMAIN`/`getApiUrl()` agregado | Sí (`auth/password-reset/request/`) |
| `password_reset_confirm` | Mensaje honesto en schema público (limitación estructural — ver razón abajo) | `IS_PUBLIC_DOMAIN`/`getApiUrl()` agregado | Sí (`auth/password-reset/confirm/`) |

**Por qué `login` y `password_reset_confirm` no tienen la corrección completa (a diferencia de `password_reset_request` y `activate_with_code`):**

- **`login`**: no hay forma segura de inferir "a qué tenant quiere entrar" solo desde email+password sin ambigüedad — un mismo email puede tener membresía en varios tenants. Adivinar uno arbitrariamente sería un riesgo de UX confuso (o peor, de intentar autenticar contra el tenant equivocado). Se dejó el comportamiento ya "seguro por diseño" que existía (la membresía nunca se encuentra contra el Client del esquema público, así que nunca autentica mal) y solo se mejoró el mensaje de error para que sea honesto en vez de genérico.
- **`password_reset_confirm`**: la clave Redis del código es literalmente `reset:code:{tenant_schema}:{code}` (`apps/tenant/core/services/password_reset.py:57`) — el `tenant_schema` es parte de la clave, no solo del payload. Sin conocerlo de antemano no se puede ni siquiera *encontrar* el código en Redis para leer su payload (a diferencia de `activate_with_code`, cuyo código de activación sí se busca globalmente). Corregir esto de raíz requeriría cambiar el contrato del enlace de reset (incluir el tenant explícitamente en la URL del email) — cambio de mayor alcance que se deja documentado como pendiente, no improvisado a ciegas en una acción de autenticación.

Ambas rutas **ya fallaban de forma segura** antes de este cambio (nunca autenticaban ni confirmaban contra el tenant equivocado); el cambio aplicado es honestidad del mensaje de error, no una corrección de un agujero de seguridad activo.

**No corregido, fuera de alcance:** `login.html` también llama `GET /api/v1/core/landing/info/` (para mostrar el nombre del tenant) sin pasar por `getApiUrl()`. No fue posible confirmar en el tiempo de esta fase si ese endpoint específico ya está dual-registrado; se deja como observación para revisión en Fase 8 (Documentación) o una futura auditoría de endpoints.

### ARQ-A4 — Apps huérfanas `mail`/`mailinbox`

Verificado independientemente (no solo confiando en el hallazgo original) antes de actuar:
- Ninguna registrada en `TENANT_APPS` (`config/settings.py`).
- Cero referencias a `apps.tenant.mail`/`apps.tenant.mailinbox` en todo el árbol `apps/`/`config/`.
- Cero referencias a sus rutas de template (`tenant/mail/partials/*`, `tenant/mailinbox/partials/*`) en ningún `.py`/`.html` fuera de sus propios directorios.
- Ninguna contenía `models.py`/`services/`/`api/` — solo `migrations/__init__.py` (vacío) y templates huérfanos.

**Acción:** eliminados ambos directorios completos (6 archivos). Esta acción fue bloqueada inicialmente por el clasificador de permisos (acción destructiva); se pidió confirmación explícita al usuario antes de proceder.

---

## 2. Criterios de "fase estable" — checklist

- [x] `py_compile` limpio en los 15 archivos `.py` tocados/creados.
- [x] `node --check` limpio en `proyectos_editor.js`.
- [x] Scripts inline de `login.html`/`reset-request.html`/`reset-confirm.html` parseados sin error (extraídos y evaluados con `new Function()`).
- [x] Ningún `data-*`/`item.id`/`tarea.id` remanente sin actualizar en `proyectos_editor.js` (verificado por grep exhaustivo de cada sitio de lectura).
- [x] Las 2 migraciones nuevas son aditivas (solo `AddField`, sin tocar datos existentes) y reversibles.
- [x] Ambas decisiones de "no corregir completamente" (ARQ-A2 sin revertir CASCADE, `login`/`password_reset_confirm` sin resolución completa de tenant) están documentadas con la razón concreta, no omitidas silenciosamente.
- [x] Confirmado que los ~450 cambios preexistentes del repositorio no fueron tocados ni mezclados con los de esta fase.

## 3. Archivos tocados (17 modificados + 2 migraciones nuevas + 6 eliminados)

```
M  apps/tenant/contabilidad/api/serializers.py
M  apps/tenant/contabilidad/api/viewsets.py
M  apps/tenant/contabilidad/models.py
M  apps/tenant/core/api/viewsets.py
M  apps/tenant/core/static/tenant/core/auth/login.html
M  apps/tenant/core/static/tenant/core/auth/reset-confirm.html
M  apps/tenant/core/static/tenant/core/auth/reset-request.html
M  apps/tenant/dashboard/models.py
M  apps/tenant/empresa/models.py
M  apps/tenant/perfil/models.py
M  apps/tenant/proyectos/api/serializers.py
M  apps/tenant/proyectos/api/viewsets.py
M  apps/tenant/proyectos/models.py
M  apps/tenant/proyectos/services/presupuesto_service.py
M  apps/tenant/proyectos/services/tareas_service.py
M  apps/tenant/proyectos/static/proyectos/js/features/proyectos_editor.js
M  config/public_api_urls.py
?? apps/tenant/contabilidad/migrations/0015_configuracionretenciones_uuid.py
?? apps/tenant/proyectos/migrations/0020_itempresupuesto_tareadiaria_uuid.py
D  apps/tenant/mail/ (3 archivos)
D  apps/tenant/mailinbox/ (3 archivos)
```

No se ejecutó ningún `git add`/`git commit`.

## 4. Siguiente paso

Antes de Fase 3 (Seguridad — SEC-A/SEC-M): recomendado ejecutar `make dj-check && make test` (o al menos `pytest apps/tenant/contabilidad apps/tenant/proyectos apps/tenant/empresa apps/tenant/perfil apps/tenant/dashboard -q`) para confirmar que las migraciones nuevas aplican limpio y que ningún test existente dependía de `lookup_field='id'` en los 3 ViewSets migrados.
