# ADR-003: Contexto Organizacional (Empresa -> Sede -> Area) - Fundamentos + piloto `compras`

**Estado:** ACCEPTED (alcance parcial: fundamentos + 1 app piloto, ver "Rollout pendiente")
**Fecha:** 2026-08-07
**Autores:** Sintel Engineering
**Relacionado con:** ADR-001 (Pull Model), ADR-002 (dual-registration)

---

## Contexto

El pedido original ("Gobernanza mediante jerarquia organizacional") pide que SINTEL evolucione de
`Tenant -> Empresa` a `Tenant -> Empresa -> Sede -> Area -> Procesos`, con `request.tenant/.empresa/
.sede/.area` disponibles automaticamente en toda app privada, filtros `empresa_id AND sede_id
(AND area_id)` transparentes, y permisos con alcance organizacional (ADMIN GLOBAL > ADMIN EMPRESA >
ADMIN SEDE > JEFE AREA > OPERADOR > VISOR).

Antes de escribir codigo se audito el estado real del repositorio (no asumido):

- `Sede`/`Area` **ya existen** como modelos de primera clase en `apps/tenant/empresa/models.py`,
  con CRUD completo (`SedeService`/`AreaService`, ViewSets, UI de gestion).
- `TenantProfile` **ya tiene** `sedes_asignadas`/`areas_asignadas` (M2M con sync + DSV) - un
  concepto de "acceso concedido", no de "contexto activo".
- 5 apps (`cotizaciones`, `facturas`, `gastos`, `inventario`, `proyectos`) **ya tienen** un campo
  `sede` opcional (tag `DT-SEDE-0X`), pero solo para alimentar el reporte "KPI por sede" del
  dashboard - nunca se usa para scoping de queries ni reglas de negocio.
- **No existe** ningun `Proceso`, ninguna resolucion de "sede activa" (ni sesion ni middleware),
  ningun filtro automatico por sede, y `apps/tenant/api/permissions.py` solo conoce
  `TenantProfile.rol` (ADMIN/OPERADOR/VISOR) - nunca alcance organizacional.

Es decir: la mitad del vocabulario del pedido ya existe (dato), pero nada de la mitad activa
(contexto, filtros, permisos) - construir esto "desde cero" habria duplicado el modelo de datos ya
correcto; ignorar el estado real habria sido exactamente el tipo de suposicion que este proyecto
prohibe explicitamente en sus reglas de gobernanza.

Dado el tamano del cambio (toca esquema en vivo de cada tenant y el Service Layer completo), el
alcance de esta primera ejecucion se acoto explicitamente a: **fundamentos + una sola app piloto
(`compras`)**, con las otras 16 apps documentadas como rollout pendiente (mismo patron de
extension incremental ya usado para el piloto del Enterprise Knowledge Graph).

---

## Decision

### 1. `request.empresa`/`.sede`/`.area` vía mixin, no vía middleware

El pedido original especifica middleware. Pero `empresa` **ya no se resuelve asi hoy**: no hay
ningun middleware que setee `request.empresa`; se resuelve de forma perezosa, por request, dentro
de `SintelDSVMixin.get_empresa_id()` (`apps/tenant/api/mixins.py`), heredado por los ViewSets de
las 17 apps via su propio `api_mixins.py`.

Agregar ademas un middleware que mute `request.*` crearia dos mecanismos de resolucion en
paralelo que podrian desincronizarse. En su lugar, esta ejecucion **extiende el mismo mixin** con
`get_sede_id()` (mismo patron que `get_empresa_id()`) y `BaseServiceMixin._get_sede_id_seguro()`/
`_get_sede()` (mismo patron que `_get_empresa_id_seguro()`/`_get_empresa()`). El algoritmo de
resolucion en si vive en `apps/tenant/core/services/sede_context.py` (`resolve_sede_activa_id`),
compartido tambien por el context processor de UI (punto 5) para no duplicarlo.

Orden de resolucion de "sede activa":
1. `request.session['sede_activa_id']`, si sigue perteneciendo a la empresa activa.
2. La primera (por nombre) de `perfil.sedes_asignadas`.
3. La Sede "Principal" de la empresa (fallback para alcance EMPRESA / sin asignacion explicita).

### 2. Semilla organizacional automatica

`apps/tenant/empresa/services/business_service.py`'s `asegurar_estructura_organizacional_inicial(empresa)`
(idempotente: no hace nada si la empresa ya tiene alguna Sede) crea Sede "Principal" + Area
"General" reutilizando `SedeService`/`AreaService` ya existentes. Se invoca:
- Automaticamente desde el onboarding (`apps/services/onboarding/empresa_service.py`, en
  `crear_tenant_con_owner` y `onboard_tenant`, justo despues de crear la `Empresa`).
- Manualmente, una sola vez por tenant existente, via
  `python manage.py backfill_sede_area` (`apps/tenant/empresa/management/commands/backfill_sede_area.py`).

### 3. `SedeAwareModel`: mixin opt-in, no se toca `SintelTenantBaseModel`

`apps/tenant/core/models.py` gana `SedeAwareModel(SintelTenantBaseModel)` con `sede` (FK a
`empresa.Sede`, `on_delete=PROTECT`) y `area` (FK a `empresa.Area`, `on_delete=SET_NULL`,
opcional). Es opt-in: `SintelTenantBaseModel` no cambia, asi que las otras 16 apps no reciben
ninguna migracion nueva en esta ejecucion. `apps/tenant/compras/models.py`'s `OrdenCompra` es el
unico adoptante hoy.

**Advertencia para futuros adoptantes:** Django NO fusiona `Meta.indexes` de una clase abstracta
con el `Meta.indexes` propio del modelo concreto si este ultimo declara el suyo (verificado
empiricamente - ver comentario en `SedeAwareModel.Meta`). Cualquier modelo que adopte este mixin
y tambien declare su propio `Meta.indexes` debe repetir explicitamente
`models.Index(fields=['empresa', 'sede'])` ahi, como hace `OrdenCompra`.

### 4. Migracion controlada (nullable -> backfill -> harden), aplicada a `compras`

Tres migraciones separadas y verificables independientemente:
1. `0004_add_alcance_and_sede_area_context` - agrega `sede`/`area` nullable a `OrdenCompra`.
2. `0006_backfill_orden_compra_sede` (data migration) - asigna la Sede "Principal" de cada
   empresa a toda `OrdenCompra` existente sin `sede_id`. Requiere que `backfill_sede_area` ya haya
   corrido en ese tenant (si una empresa no tiene ninguna Sede, la orden queda con `sede_id` NULL
   a proposito, no se asume una sede).
3. `0007_harden_orden_compra_sede_not_null` - `AlterField` a `null=False`, con un `RunPython` que
   falla con un mensaje accionable si queda alguna fila sin `sede_id` (en vez del error generico
   de Postgres).

### 5. Alcance organizacional en permisos (ortogonal a `rol`)

`TenantProfile.alcance` (nuevo campo, `EMPRESA`/`SEDE`/`AREA`, default `EMPRESA`) es **ortogonal**
a `RolTenant.rol` (ADMIN/OPERADOR/VISOR) - no lo reemplaza, para no tocar los 9 archivos que hoy
comparan `rol == 'ADMIN'` literal. "ADMIN GLOBAL" del pedido original no es un valor de este campo:
es el staff/superuser de Django ya existente en el esquema publico, fuera de `TenantProfile` por
completo.

`apps/tenant/api/permissions.py`'s `HasOrganizationalScope` (nueva clase) verifica a nivel de
objeto que un perfil con `alcance=SEDE` solo opere sobre su(s) `sedes_asignadas`, y uno con
`alcance=AREA` solo sobre sus `areas_asignadas`; `alcance=EMPRESA` no tiene restriccion adicional
(comportamiento de hoy). Aplicada unicamente a `OrdenCompraViewSet` en esta ejecucion.

El filtrado de **listas** (no solo de objetos individuales) es prueba de concepto en
`OrdenCompraServiceMixin.get_qs_list()`: un perfil con alcance SEDE/AREA solo ve las ordenes de su
sede activa; alcance EMPRESA ve todas las sedes, igual que hoy.

### 6. Filtro reusable para las proximas apps

`apps/tenant/core/services/organizational_filters.py`'s `filter_by_context(queryset, empresa_id,
sede_id=None, area_id=None)` centraliza el patron `empresa_id AND sede_id (AND area_id)` para que
la proxima app que adopte `SedeAwareModel` lo reutilice en su selector en vez de reimplementar el
`.filter()` encadenado por su cuenta.

### 7. UI: selector de "Sede activa"

`apps/tenant/core/context_processors.py`'s `contexto_organizacional` inyecta `sede_activa`/
`sedes_disponibles` en todo template (registrado en `TEMPLATES['OPTIONS']['context_processors']`),
consumido por el dropdown nuevo en el header compartido
(`apps/tenant/core/templates/tenant/partials/_header.html`) - visible en cualquier pagina que
extienda `tenant/base.html`, no solo en `compras`. El cambio de sede activa se hace via
`POST /api/v1/core/contexto/sede/` (`apps/tenant/core/api/contexto.py`), el unico punto de
escritura de `request.session['sede_activa_id']`; el frontend vive en
`apps/tenant/core/static/core/js/common/sede_selector.js` (vanilla JS, mismo patron que
`tabulator.factory.js`).

---

## Rollout pendiente (no ejecutado en esta fase)

Para cada una de las otras 16 apps tenant, en el mismo orden que se probo en `compras`:
1. Cambiar el modelo transaccional relevante para heredar `SedeAwareModel` en vez de
   `SintelTenantBaseModel` (si ya tiene un campo `sede` tipo `DT-SEDE-0X`, decidir si se reemplaza
   por el del mixin o se documenta la coexistencia).
2. Migracion nullable -> backfill -> harden (repetir el patron de `0004`/`0006`/`0007` de compras).
3. Repetir el `models.Index(fields=['empresa', 'sede'])` explicito si el modelo declara su propio
   `Meta.indexes` (ver advertencia en el punto 3).
4. Pasar `sede`/`area` explicitos al Service Layer (nunca re-derivarlos ahi).
5. Adoptar `filter_by_context()` en el selector de la app.
6. Decidir, app por app, si aplica `HasOrganizationalScope` a su ViewSet.

Explicitamente diferido, sin fecha: el nivel `Proceso` (sin especificacion en el pedido original,
ningun campo/comportamiento definido), reemplazar `RolTenant` por un enum de 6 valores, el filtro
automatico del dashboard por sede/area (ya tiene un reporte KPI-por-sede separado, sin tocar), y
las reglas de gobernanza que requieren analisis de flujo de control (fuera del alcance de este
ADR, ver `tools/ekg/governance.py`).

---

## Checklist para adoptar `SedeAwareModel` en una nueva app

- [ ] El modelo hereda `SedeAwareModel` (no `SintelTenantBaseModel`) si necesita el contexto.
- [ ] Si el modelo declara su propio `Meta.indexes`, repite `Index(fields=['empresa', 'sede'])` ahi.
- [ ] Migracion nullable -> data migration de backfill -> harden `NOT NULL`, en 3 pasos separados.
- [ ] El Service Layer recibe `sede`/`area` como parametros explicitos (nunca los resuelve solo).
- [ ] El ViewSet resuelve `sede`/`area` via `self._get_sede()` (heredado de `BaseServiceMixin`),
      nunca directamente desde `request.session` o el modelo.
- [ ] El selector usa `filter_by_context()` en vez de un `.filter()` encadenado propio.
- [ ] Se corrio `backfill_sede_area` en todo tenant existente antes de aplicar la migracion de
      endurecimiento (`harden`) en produccion.

---

## Consecuencias

**Positivas:**
- Reutiliza integramente el modelo de datos Sede/Area ya construido y probado (CRUD, DSV, UI).
- Un solo mecanismo de resolucion de contexto (el mixin ya usado por las 17 apps), sin una segunda
  via paralela via middleware que pudiera desincronizarse.
- Migracion reversible y verificable paso a paso (nullable -> backfill -> harden), sin romper
  tenants existentes.
- `alcance` ortogonal a `rol` evita una migracion de datos riesgosa sobre el campo de rol existente.

**Negativas / riesgos aceptados:**
- Las otras 16 apps aun no tienen contexto organizacional activo - `sede`/`area` en esas apps
  (donde existen) siguen siendo campos de reporte, no de scoping, hasta que se ejecute el rollout.
- `HasOrganizationalScope`/`get_qs_list()` con alcance solo estan probados en `compras`; extender
  a otra app requiere repetir la verificacion (tests + prueba manual), no asumir que el patron
  generaliza sin revision.
- El mixin `SedeAwareModel` no fusiona `Meta.indexes` automaticamente (limitacion de Django, no de
  este diseno) - cada adoptante debe recordarlo explicitamente o perdera el indice compuesto en
  silencio (ver advertencia arriba, y test de regresion en `tools/ekg` no aplica aqui - la
  verificacion es manual, via `Model._meta.indexes`).

---

## Archivos modificados/creados en esta ejecucion

| Archivo | Cambio |
|---|---|
| `apps/tenant/core/models.py` | `SedeAwareModel` (nuevo mixin abstracto) |
| `apps/tenant/core/services/sede_context.py` | `resolve_sede_activa_id()` (nuevo, compartido) |
| `apps/tenant/core/services/organizational_filters.py` | `filter_by_context()` (nuevo) |
| `apps/tenant/core/context_processors.py` | `contexto_organizacional()` (nuevo) |
| `apps/tenant/core/api/contexto.py` | `ContextoSedeView` (nuevo endpoint) |
| `apps/tenant/core/api/urls.py` | Registro de `contexto/sede/` |
| `apps/tenant/core/templates/tenant/partials/_header.html` | Selector de Sede activa |
| `apps/tenant/core/static/core/js/common/sede_selector.js` | JS del selector (nuevo) |
| `apps/tenant/api/mixins.py` | `get_sede_id()`, `_get_sede_id_seguro()`, `_get_sede()` |
| `apps/tenant/api/permissions.py` | `HasOrganizationalScope` (nueva clase) |
| `apps/tenant/perfil/models.py` | `TenantProfile.alcance` (nuevo campo + migracion) |
| `apps/tenant/empresa/services/business_service.py` | `asegurar_estructura_organizacional_inicial()` |
| `apps/tenant/empresa/management/commands/backfill_sede_area.py` | Comando de backfill (nuevo) |
| `apps/services/onboarding/empresa_service.py` | Llama la semilla tras crear la Empresa |
| `apps/tenant/compras/models.py` | `OrdenCompra` hereda `SedeAwareModel`, endurece `sede` |
| `apps/tenant/compras/migrations/0004-0007` | Migracion controlada (nullable/indice/backfill/harden) |
| `apps/tenant/compras/services/{business_service,crud_service,api_mixins,selectors}.py` | `sede`/`area` explicitos, `get_qs_list()` con alcance |
| `apps/tenant/compras/api/viewsets.py` | `HasOrganizationalScope` en `OrdenCompraViewSet` |
| `apps/tenant/compras/tests/test_multitenant_isolation_tabla_html.py` | Fixture actualizado con `Sede` |
| `config/settings.py` | Registro del context processor |
