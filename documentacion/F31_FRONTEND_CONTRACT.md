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

4. **`ajax-setup-csrf.js` tiene doble responsabilidad -- una vestigial, una crítica.**
   Ademas del `$.ajaxSetup(...)` para jQuery (vestigial -- F31.0 encontró
   solo 2 archivos con sintaxis jQuery en todo `apps/tenant/`, uno de ellos
   este mismo), el archivo tambien registra el listener global
   `htmx:configRequest` que inyecta el header CSRF en **toda peticion HTMX
   de mutacion de las 14 apps que usan HTMX**. Esa segunda mitad es
   infraestructura de seguridad activa, no vestigial -- ver correccion en
   §4.2.

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
| `Sintel.Core.Http` | Transporte fetch + CSRF (capa única) | 3 archivos en conflicto real (`static/js/http.js` x2 copias + `lib/http.js`), NO solo `lib/http.js`+`lib/api-helpers.js` como se creía | **DIFERIDA a micro-fase dedicada con pruebas de navegador** -- hay divergencia real de comportamiento, no solo duplicación de nombre. Ver §4.1 (corregido). |
| `Sintel.Core.Routes` | Descubrimiento/cache de URLs backend | `helpers/routes.js` | Ninguna -- ya es SSoT único, mantiene su rol. |
| `Sintel.Core.Crud` | Operaciones CRUD estándar sobre `Http` + `Routes` | `helpers/crud.js` | Ninguna en diseño -- su dependencia de "Http" se vuelve inambigua una vez resuelta §4.1. |
| `Sintel.Core.Dom` | Utilidades DOM (visibilidad, espera de elementos) | `lib/dom-utils.js` | Ninguna -- ya es SSoT único. |
| `Sintel.Core.Errors` | Error Boundary global (HTMX 400/409/422/500) | `lib/ui-manager.js` + `error_injector.js` | Ninguna en diseño -- ambos ya cooperan por diseño (UI Manager global + injector modular), mantienen roles distintos y complementarios. |
| `Sintel.Core.Errors.LegacyDataTables` (a eliminar) | Manejo de errores DataTables | `helpers/error-service.js` | **Abierta** -- confirmar que no hay consumidores activos de `dt-error.dt`, luego eliminar (no migrar). Ver §4.2. |
| `Sintel.Core.Notifications` | Toasts/alerts (SweetAlert2) | `utils/feedback.js` | Ninguna -- ya es SSoT único. |
| `Sintel.Core.Modal` | Modales Bootstrap | `helpers/modal-service.js` | Ninguna en diseño -- separado de Offcanvas por diseño correcto (son componentes Bootstrap distintos). |
| `Sintel.Core.Offcanvas` | Offcanvas seguro (anti-backdrop-leak) | `common/offcanvas.helper.js` | Ninguna en diseño -- ya es el SSoT correcto; el trabajo pendiente es de **adopción** (14 sites), no de diseño. Ver §4.3. |
| `Sintel.Core.Tables` | Factory de grillas Tabulator | `common/tabulator.factory.js` | Ninguna en diseño para el factory en sí -- el trabajo pendiente es decidir el Grupo 1 de migración (dashboard + inventario, corregido en F31.0). |
| `Sintel.Core.Auth` | JWT/Session helpers | `jwt-auth.js` (funcional, cargado en tenant vía `{% static 'js/jwt-auth.js' %}`) | **DIFERIDA junto con §4.1** -- funciona hoy, pero vive fisicamente en `apps/public/console/static/js/`. Reubicar requiere la misma decisión de "dónde vive JS compartido" que §4.1. Ver §4.5. |
| `Sintel.Core.Csrf` | Lectura de cookie CSRF | función `getCookie()` duplicada dentro de `lib/http.js` | Se resuelve como parte de la micro-fase diferida de §4.1. |
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

### 4.1 `Sintel.Core.Http`: CORRECCIÓN MAYOR -- el problema real es mucho más profundo que "dos archivos duplicados"

**Retracto la recomendación original de "fusionar" -- verificado durante
F31.2 que este NO es un merge simple.** Hay en realidad **3 archivos**
involucrados, no 2, y una divergencia de comportamiento real, no solo de
nombre:

1. **`apps/tenant/core/static/js/http.js`** ("v3.4 unificado", doble
   contrato función+objeto, `credentials: 'include'`, CSRF desde
   `meta[name="csrf-token"]`) -- cargado en `tenant/base.html:129`, al
   final de `<body>`, ANTES del bloque `extra_js` del hijo.
2. **`apps/tenant/core/static/core/js/lib/http.js`** (contrato solo
   función, `credentials: 'same-origin'`, CSRF desde cookie
   `document.cookie`, allowlist de módulos "no críticos" para 401,
   manejo especial de `FormData`, y **lógica de negocio ad-hoc para un
   campo `cliente`** que no debería vivir en un cliente HTTP genérico) --
   cargado vía `assets_core.html`, incluido dentro de
   `{% block extra_js %}` de `workspace.html`, es decir **DESPUÉS** del
   anterior en el DOM final. **Gana** -- confirmado por un comentario ya
   existente en el propio archivo (tag `[FE-C3]`): *"este cliente (el que
   efectivamente se carga al final en assets_core.html y gana sobre
   window.http)..."* -- alguien ya diagnosticó este mismo problema antes
   y parcheó JWT ahí en vez de corregir el orden de carga.
3. **`apps/public/console/static/js/http.js`** -- **byte-idéntico** al
   #1 (`diff` confirma 0 diferencias). Es el mismo archivo v3.4 duplicado
   físicamente para poder servirse también en páginas de la consola
   pública bajo la misma ruta estática sin prefijo de app (`js/http.js`).

**Implicación real:** en toda página `workspace.html` (el shell de casi
todas las apps de negocio), el cliente HTTP que realmente gobierna el
comportamiento en producción es el #2 (`core/js/lib/http.js`), NO el
"v3.4 unificado" que parece ser el más maduro por diseño. El contrato de
objeto (`window.http.get/post/...`) del #1 SOLO funciona en páginas de
consola pública (donde #2 no se carga) -- confirmado que
`apps/public/console/static/js/tenants_manager.js` sí depende de ese
contrato de objeto. **Ningún JS de tenant usa el contrato de objeto**
(verificado por grep), así que el "ganador" real (#2) no rompe nada
visible hoy -- pero #2 tiene comportamientos reales (allowlist de 401,
manejo de FormData, diagnóstico 403) que el #1 no replica, así que
literalmente invertir el orden de carga (hacer que el #1 gane) SÍ
rompería esos comportamientos si algo los necesita.

**Decisión revisada:** esto no es un "fusionar y listo" de F31.2. Requiere
una micro-fase dedicada, posterior a F31.2, con **pruebas de regresión de
navegador reales** (formularios, uploads con FormData, flujos que
disparan 401/403) antes de tocar cualquiera de los 3 archivos -- el riesgo
de romper CSRF/auth/uploads en todas las apps tenant simultáneamente es
demasiado alto para resolverlo sin esa verificación. **No se modifica
ningún archivo de este cluster en F31.2.** Se documenta como hallazgo
crítico, no se ejecuta el fix.

### 4.2 `error-service.js`: código muerto confirmado -- RESUELTO. `ajax-setup-csrf.js`: CORRECCIÓN, NO es vestigial

Verificado leyendo el cuerpo completo de ambos archivos (no solo el
encabezado, que es donde F31.1 se quedó originalmente):

- **`error-service.js`**: su `init()` retorna inmediatamente si
  `!w.jQuery || !w.jQuery.fn.dataTable` -- en tenant (sin jQuery/DataTables
  reales) es un no-op puro. No expone nada que otro módulo consuma más
  allá de `w.ErrorService.init`, que nadie más llama. **Código muerto
  confirmado, seguro eliminar.**
- **`ajax-setup-csrf.js` -- CORRECCIÓN a la recomendación original de
  F31.1**: el archivo tiene DOS responsabilidades, no una. Además del
  `$.ajaxSetup(...)` para jQuery (ese sí vestigial), contiene un listener
  global **`document.body.addEventListener('htmx:configRequest', ...)`**
  que inyecta el header CSRF en **toda petición HTMX de mutación
  (POST/PUT/PATCH/DELETE) de las 14 apps que usan HTMX**. Esto es
  infraestructura de seguridad activa y crítica, no vestigial. **Eliminar
  este archivo completo habría roto CSRF en HTMX en todo el frontend
  tenant.** Decisión corregida: **NO eliminar el archivo**; en una fase
  futura de limpieza más fina se podría separar la parte jQuery (borrar)
  de la parte HTMX (mover a `Sintel.Core.Http` o su propio módulo), pero
  eso es una refactorización quirúrgica, no una eliminación, y queda fuera
  del alcance de F31.2.

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
de reescritura. **Diferencia con el caso de `http.js` (§4.1): `jwt-auth.js`
tiene un único archivo físico** (no está duplicado byte-a-byte como
`http.js`), así que reubicarlo es más simple -- pero comparte la misma
causa raíz (no existe hoy un lugar neutral para JS compartido entre
tenant y consola pública). **Diferida a la misma micro-fase futura que
§4.1**, para resolver ambos con una sola decisión de ubicación
compartida en vez de dos soluciones ad-hoc distintas.

### 4.6 `Sintel.Core.Events`: contrato de nombres de evento

F31.0 no auditó los nombres de evento (`CustomEvent`) realmente usados por
cada app hoy. Antes de imponer el contrato `<modelo>-created/updated/deleted`
del plan original, se necesita un grep dedicado de
`dispatchEvent\(new CustomEvent` y `addEventListener\(['"]` en
`apps/tenant/*/static/*/js/` para saber cuántos nombres distintos existen
hoy y si ya coinciden con esa convención o hay que normalizar.

---

## 5. Siguiente paso -- actualizado tras la ejecución de F31.2

De las 6 decisiones originalmente abiertas en §4:
- **§4.2 resuelta y ejecutada**: `error-service.js` era código muerto
  confirmado -- eliminado en F31.2, junto con su `<script>` tag en
  `assets_core.html`.
- **§4.1 y §4.5 investigadas a fondo y DIFERIDAS**, no ejecutadas: lo que
  parecía una duplicación simple resultó ser 3 archivos con divergencia
  real de comportamiento (`static/js/http.js` x2 copias byte-idénticas +
  `core/js/lib/http.js`, este último con lógica de negocio y manejo de
  401/FormData que el "v3.4" no replica) más un problema estructural
  compartido (no existe un lugar neutral para JS compartido entre tenant
  y consola pública, lo que también afecta a `jwt-auth.js`). Corregir
  esto sin pruebas de navegador reales tiene demasiado riesgo de romper
  CSRF/auth/uploads en todo el frontend tenant simultáneamente -- se
  documenta como hallazgo crítico para una micro-fase futura dedicada,
  no se ejecuta en F31.2.
- **§4.3 (Offcanvas), §4.4 (contabilidad), §4.6 (eventos)**: ver
  ejecución en F31.2 (código y hallazgos documentados por separado).
