# F31.1 — Contrato Frontend (diseño, sin código nuevo)

**Fecha:** 2026-08-12 · Insumo directo: `F31_FRONTEND_INVENTORY.md` (F31.0).
**Alcance:** solo diseño/decisión. **0 archivos de código creados o
modificados en este documento.** F31.2 (implementación de Core) requiere
que las decisiones abiertas de §4 se resuelvan primero.

---

## 1. Lo que la auditoría de assets_core.html revela (nuevo, no visible en F31.0)

F31.0 auditó por patrón (grep agregado). Leer el bootstrap real de
`apps/tenant/core/templates/tenant/core/partials/assets_core.html` --
el include que TODA página de tenant carga -- cambia la imagen: los 9
archivos de `core/js/lib/` + `core/js/helpers/` **no son candidatos a
"posible duplicado"**, son **13 scripts obligatorios cargados en cadena en
cada página**, con dependencias de orden ya documentadas explícitamente
en comentarios (`routes.js` DEBE ir antes de `crud.js`; `ui-manager.js`
DEBE ir después de HTMX; `error_injector.js` después de `ui-manager.js`).
Cualquier consolidación de Core (F31.2) **debe preservar ese grafo de
dependencias real**, no reorganizar a ciegas.

**Hallazgos nuevos, confirmados leyendo el cuerpo de los archivos (no solo
el nombre):**

1. **`http.js` y `api-helpers.js` son dos capas de transporte HTTP
   independientes y solapadas**, ambas con su propio manejo de CSRF:
   - `http.js` expone `window.http(method, url, body)` -- fetch de bajo
     nivel con CSRF/SessionAuth.
   - `api-helpers.js` expone `window.API_HELPERS` -- URL-building con
     trailing-slash, CSRF, "fetch seguro" con manejo de 403/405/409/422.
   El propio `crud.js` documenta la ambigüedad en su encabezado:
   *"Transport: usa API_HELPERS.safeFetchJson o http.js"* -- ni el codigo
   existente tiene claro cual es el SSoT de transporte.

2. **`error-service.js` maneja errores de DataTables** ("Manejo unificado
   de errores DataTables... Fuerza `DataTable.ext.errMode='none'`"), pero
   el propio `assets_core.html` documenta: *"v3.3: DataTables eliminado -
   Migrado completamente a Tabulator"*. Esto hace a `error-service.js` un
   **candidato fuerte a código muerto** -- su razón de ser (DataTables) ya
   no existe en el proyecto. Requiere confirmación (buscar si algo aun
   dispara el evento `dt-error.dt` que escucha) antes de eliminarlo, no
   asumirlo sin evidencia.

3. **La consolidación de Offcanvas de F31.0 (14 violaciones en 6 apps) NO
   es un hallazgo nuevo** -- el propio `offcanvas.helper.js` se cargó como
   parte de un esfuerzo de consolidación *anterior*, fechado
   explícitamente: *"SSoT: window.Sintel.Core.mostrarOffcanvasSeguro --
   consolida las 16 reimplementaciones locales detectadas en la auditoria
   2026-07-26"*. Es decir: **ya hubo una FASE previa de consolidación de
   Offcanvas que redujo 16 reimplementaciones a un helper compartido, y
   14 siguen sin convertir**. F31 no inicia este trabajo -- lo continúa y
   lo cierra.

4. **`ajax-setup-csrf.js` es infraestructura jQuery** ("Red de seguridad
   global para jQuery... para cualquier llamada jQuery que no pase por
   DataTables o por nuestros helpers centralizados") en un proyecto donde
   F31.0 encontró **solo 2 archivos** con sintaxis jQuery en todo
   `apps/tenant/` (uno de ellos es este mismo archivo). Candidato a
   verificar si sigue siendo necesario o es vestigial junto con
   DataTables.

---

## 2. Contrato Core Frontend propuesto (`window.Sintel.Core.*`)

Manteniendo el principio del usuario -- **sin framework nuevo, Vanilla JS
ES6+, SSoT por responsabilidad** -- el contrato agrupa los archivos
*existentes* en módulos con una única responsabilidad cada uno. Esto es
una propuesta de **mapeo**, no una reescritura: la mayoría de los archivos
actuales ya tienen contenido correcto, solo están fragmentados o
duplicados a nivel de archivo.

| Módulo objetivo | Responsabilidad | Archivo(s) actuales que mapean | Decisión requerida |
|---|---|---|---|
| `Sintel.Core.Http` | Transporte fetch + CSRF (capa única) | `lib/http.js` + `lib/api-helpers.js` | **Abierta** -- fusionar en 1 solo archivo/API, o declarar explícitamente cuál es el SSoT y el otro pasa a ser un shim de compatibilidad temporal. Ver §4.1. |
| `Sintel.Core.Routes` | Descubrimiento/cache de URLs backend | `helpers/routes.js` | Ninguna -- ya es SSoT único, mantiene su rol. |
| `Sintel.Core.Crud` | Operaciones CRUD estándar sobre `Http` + `Routes` | `helpers/crud.js` | Ninguna en diseño -- su dependencia de "Http" se vuelve inambigua una vez resuelta §4.1. |
| `Sintel.Core.Dom` | Utilidades DOM (visibilidad, espera de elementos) | `lib/dom-utils.js` | Ninguna -- ya es SSoT único. |
| `Sintel.Core.Errors` | Error Boundary global (HTMX 400/409/422/500) | `lib/ui-manager.js` + `error_injector.js` | Ninguna en diseño -- ambos ya cooperan por diseño (UI Manager global + injector modular), mantienen roles distintos y complementarios. |
| `Sintel.Core.Errors.LegacyDataTables` (a eliminar) | Manejo de errores DataTables | `helpers/error-service.js` | **Abierta** -- confirmar que no hay consumidores activos de `dt-error.dt`, luego eliminar (no migrar). Ver §4.2. |
| `Sintel.Core.Notifications` | Toasts/alerts (SweetAlert2) | `utils/feedback.js` | Ninguna -- ya es SSoT único. |
| `Sintel.Core.Modal` | Modales Bootstrap | `helpers/modal-service.js` | Ninguna en diseño -- separado de Offcanvas por diseño correcto (son componentes Bootstrap distintos). |
| `Sintel.Core.Offcanvas` | Offcanvas seguro (anti-backdrop-leak) | `common/offcanvas.helper.js` | Ninguna en diseño -- ya es el SSoT correcto; el trabajo pendiente es de **adopción** (14 sites), no de diseño. Ver §4.3. |
| `Sintel.Core.Tables` | Factory de grillas Tabulator | `common/tabulator.factory.js` | Ninguna en diseño para el factory en sí -- el trabajo pendiente es decidir el Grupo 1 de migración (dashboard + inventario, corregido en F31.0). |
| `Sintel.Core.Auth` | JWT/Session helpers | `jwt-auth.js` (funcional, cargado en tenant vía `{% static 'js/jwt-auth.js' %}`) | **Resuelta, requiere accion menor** -- el archivo funciona pero vive fisicamente en `apps/public/console/static/js/`, no en `core`. Ver §4.5. |
| `Sintel.Core.Csrf` | Lectura de cookie CSRF | función `getCookie()` duplicada dentro de `http.js` (y posiblemente `ajax-setup-csrf.js`) | Se resuelve como efecto colateral de §4.1 (fusionar transporte). |
| `Sintel.Core.Events` | Contrato de eventos `<modelo>-created/updated/deleted` | *no existe hoy como módulo -- son `CustomEvent` dispersos por feature* | **Abierta** -- F31.0 no auditó el uso real de nombres de evento por app (fuera de su alcance). Requiere una pasada dedicada antes de F31.9. |

**Lo que el contrato explícitamente NO toca:** `sede_selector.js`
(selector organizacional, ya es SSoT propio), `notyf.init.js` (init de
librería externa, no necesita modularización), `workspace.js` (orquestador
de la página workspace, no un módulo Core reusable por otras apps).

---

## 3. Prioridad de migración de grillas (corregida per F31.0)

```
Grupo 1 (Tabulator puro, sin django-tables2 en absoluto):
  dashboard, inventario
       ↓
Grupo 2 (coexistencia con 1 uso residual, ya mayormente HTMX+django-tables2):
  empleados, proveedores, proyectos, ventas
       ↓
Grupo 3 (coexistencia deliberada, candidatos a NO migrar por F31.7):
  contabilidad (reportes/pendientes/libro diario)
  cotizaciones (grid principal -- verificar si aplica la misma excepcion de F31.7
                antes de forzar la migracion)
       ↓
Ya migrado (sin accion):
  bancos, compras, empresa, facturas, gastos, perfil
       ↓
Fuera de alcance:
  landing, core (infraestructura, no una app de listado)
```

**App piloto propuesta:** el usuario propuso `compras` como piloto en su
plan original -- pero F31.0 confirma que `compras` **ya está migrada**
(django-tables2 + HTMX, 0 Tabulator). No hay trabajo de migración de
grilla que pilotar ahí. La app piloto real para F31.6 (dado que el
objetivo es probar el patrón de migración Tabulator -> HTMX +
django-tables2) debe ser una del **Grupo 1**: se recomienda **`dashboard`**
antes que `inventario` -- tiene menos superficie (3 archivos JS, 5
plantillas) y 0 usos de HTMX que proteger/preservar durante la migración,
mientras que `inventario` ya mezcla HTMX (offcanvas) con Tabulator (grid),
lo que añade riesgo a un primer piloto.

---

## 4. Decisiones abiertas -- requieren respuesta antes de F31.2

### 4.1 `Sintel.Core.Http`: ¿fusionar `http.js` + `api-helpers.js`, o declarar uno SSoT?

Dos capas de transporte HTTP coexisten hoy, ambas con CSRF propio. Opciones:
- **(a) Fusionar** en un único `http.js` que absorba las capacidades de
  `api-helpers.js` (URL-building con trailing slash, manejo de
  403/405/409/422) -- más trabajo, resultado más limpio.
  - **(recomendado)**
- **(b) Declarar `api-helpers.js` como SSoT** (es el más completo,
  maneja más códigos de error) y convertir `http.js` en un alias delgado
  para no romper los consumidores existentes que llaman `window.http(...)`
  directamente.
- **(c) Dejar ambos, documentar cuál usar para qué caso** -- no
  recomendado, perpetúa la ambigüedad que ya causó que `crud.js` no supiera
  cuál transporte usar.

### 4.2 `error-service.js`: código muerto confirmado -- RESUELTO

Verificado: `dt-error.dt`/`jQuery.fn.dataTable` solo aparecen en 2 archivos
mas, ambos en `apps/public/console/static/js/` (`users_manager.js`,
`tenants_manager.js`) -- **fuera del scope tenant** que carga
`error-service.js` via `assets_core.html`. Esos 2 archivos SÍ usan
DataTables activamente (`jQuery('#dt-users').DataTable({...})`), pero
pertenecen a la consola de administración pública, un árbol de assets
completamente separado que nunca incluye `assets_core.html` de tenant.
**Decisión:** `error-service.js` es código muerto confirmado dentro de su
propio scope (tenant) -- seguro eliminar junto con `ajax-setup-csrf.js`
(§1.4) en el mismo cambio de F31.2, documentando la razón (deuda de una
migración ya completada en el lado tenant, no relacionada a F31). **Nota
de alcance:** la consola pública (`apps/public/console/`) SÍ sigue en
jQuery DataTables real y con uso activo -- queda fuera del alcance de F31
(que audita solo las 17 apps tenant), pero es una deuda técnica real que
merece su propio hallazgo si alguna fase futura audita el frontend
público.

### 4.3 Offcanvas: ¿corregir los 14 sites en bloque o por app durante F31.6?

- **(a) Corregir las 14 violaciones en un commit dedicado**, antes de
  empezar la migración de grillas por app -- cierra deuda conocida de
  2026-07-26 de una vez.
  - **(recomendado)**, porque ya está fuera de alcance de cualquier app
    específica y no bloquea la migración de grillas.
- **(b) Corregir cada violación al migrar su app correspondiente** en
  F31.6 -- diluye el trabajo pero puede introducir inconsistencia (algunas
  apps corregidas antes que otras sin razón aparente).

### 4.4 `contabilidad`: ¿aceptar "1 api.js por sub-dominio" como patrón válido?

`contabilidad` es la única app con 8 archivos `*.api.js` en vez de 1. Es
también la app con más sub-dominios reales (asientos, cuentas, libro
diario, períodos, plantillas, reportes, retenciones, tipos de comprobante).
Recomendación: **aceptar el patrón como variante válida para apps con 5+
sub-dominios reales**, documentarlo explícitamente en el contrato (no
como excepción silenciosa) en vez de forzar una consolidación artificial
en un solo archivo gigante.

### 4.5 `Sintel.Core.Auth`: RESUELTO -- `jwt-auth.js` sí carga en tenant, pero está mal ubicado

Verificado en dos pasos: `window.jwtAuth` se **define** en un único
archivo físico de todo el repo, `apps/public/console/static/js/jwt-auth.js`,
y **sí se carga en páginas tenant** -- `apps/tenant/core/templates/tenant/base.html:125`
y `tenant/core/base.html:125` tienen
`<script src="{% static 'js/jwt-auth.js' %}"></script>`. Funciona porque
Django's `collectstatic` fusiona el `static/` de todas las apps en un
namespace global, asi que `js/jwt-auth.js` (ruta SIN prefijo de app) se
resuelve al unico archivo fisico que existe en esa ruta relativa, sin
importar que viva dentro de `apps/public/console/`.

**Es funcionalmente correcto hoy, pero es una violacion de facto del
patron "Aislamiento de JavaScript por Aplicacion"** (`AGENTS.md`) -- un
archivo compartido entre tenant y consola publica esta fisicamente alojado
dentro de una sola app (`console`) en vez de un lugar neutral (p.ej.
`apps/tenant/core/static/js/` o una app `shared`/`common` dedicada).
Explica ademas, incidentalmente, por que existe
`apps/tenant/core/static/js/http.js` (el duplicado huerfano de F31.0 §3):
**la convencion de rutas sin prefijo de app (`static/js/...`, no
`static/<app>/js/...`) ya se usa deliberadamente para al menos un archivo
real (`jwt-auth.js`)** -- no es un patron inventado por error, es
precedente existente, aunque no documentado como tal. Decision para
F31.2: mover `jwt-auth.js` a una ubicacion neutral compartida (definir
cual) es la correccion correcta, no simplemente eliminar el patron de
ruta sin prefijo -- pero el `http.js` huerfano de `core/static/js/` sigue
siendo codigo muerto real (0 referencias), a diferencia de `jwt-auth.js`
(activamente cargado).

`Sintel.Core.Auth` como modulo: mapea a `jwt-auth.js` (funcional, ya
consumido defensivamente por `tabulator.factory.js:166` con
`typeof window.jwtAuth === 'object'`), pendiente solo de reubicacion, no
de reescritura.

### 4.6 `Sintel.Core.Events`: contrato de nombres de evento

F31.0 no auditó los nombres de evento (`CustomEvent`) realmente usados por
cada app hoy. Antes de imponer el contrato `<modelo>-created/updated/deleted`
del plan original, se necesita un grep dedicado de
`dispatchEvent\(new CustomEvent` y `addEventListener\(['"]` en
`apps/tenant/*/static/*/js/` para saber cuántos nombres distintos existen
hoy y si ya coinciden con esa convención o hay que normalizar.

---

## 5. Siguiente paso

Este documento es una propuesta de contrato. De las 6 decisiones
originalmente abiertas en §4, **2 quedaron resueltas con evidencia durante
este mismo pase** (4.2 `error-service.js` = código muerto confirmado,
eliminar; 4.5 `jwt-auth.js` = funcional, solo requiere reubicación).
Quedan genuinamente abiertas y requieren una decisión del usuario antes de
F31.2:

- **§4.1** -- fusionar `http.js`+`api-helpers.js` o declarar uno SSoT
  (recomendación: fusionar).
- **§4.3** -- corregir las 14 violaciones de Offcanvas en un solo commit
  dedicado antes de migrar grillas, o diluir por app durante F31.6
  (recomendación: commit dedicado).
- **§4.4** -- aceptar "1 api.js por sub-dominio" como patrón válido para
  `contabilidad` (recomendación: sí, documentarlo explícitamente).
- **§4.6** -- auditar el contrato real de nombres de evento
  (`CustomEvent`) antes de imponer la convención `<modelo>-created/updated/deleted`.

No se ha tocado ningún archivo de código en F31.0 ni F31.1.
