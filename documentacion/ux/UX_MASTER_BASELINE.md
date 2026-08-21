# UX_MASTER_BASELINE — Transformacion UX/UI de SINTEL

Mision: transformar progresivamente la interfaz y experiencia de
usuario del ERP, presentando las 16 apps independientes como un unico
sistema empresarial coherente -- sin alterar la arquitectura tecnica
(Service Layer, DSV, OCF, multitenant) ni las reglas de negocio.

**Fecha:** 2026-08-21. **Rama:** `feat/onboarding-cookie`.

---

## FASE 0 — Baseline frontend

### Stack tecnico confirmado

- **Sin build step.** Bootstrap 5.3.2 (CDN), Bootstrap Icons 1.11.1
  (CDN), Font Awesome 6.4.0 (CDN), HTMX 1.9.10, Tabulator 6.2.5
  (legacy, en migracion a django-tables2+HTMX segun
  `PLAN_UNICO_CORRECCIONES.md` FASE 5-BIS), Notyf (notificaciones
  toast).
- **JS:** modulos vanilla ES6 namespaced bajo `window.Sintel.*`, sin
  framework SPA. `apps/tenant/core/static/core/js/workspace.js` es el
  orquestador del shell (tabs, nav, logout).
- **Layout actual:** `workspace.html` (342 lineas) es un SPA-like
  shell -- las 16 apps se inyectan como `<section id="tab-X"
  style="display:none">` dentro de una sola pagina, alternadas por
  JS via `data-tab`/hash de URL (`#empresa`, `#facturas`, etc.), no
  hay navegacion real de pagina (sin recarga completa al cambiar de
  app).
- **CSS:** `workspace.css` con custom properties (`--brand`, `--muted`,
  `--border`, etc.) ya establecidas -- sistema de color coherente
  reutilizable, no hace falta crear uno nuevo.

### Componentes UI compartidos YA EXISTENTES (reutilizar, no duplicar)

`apps/tenant/core/templates/tenant/core/partials/ui/`:
- `empty_state.html` -- estado vacio estandar
- `filter_bar.html` -- barra de filtros estandar
- `kpi_card.html` -- tarjeta de KPI estandar
- `loading_state.html` -- estado de carga estandar

Mas `_base_offcanvas.html` (offcanvas base) y
`window.Sintel.Core.mostrarOffcanvasSeguro()` (helper JS obligatorio
para abrir offcanvas, ver `AGENTS.md` §26). Estos ya son el resultado
de un trabajo previo de "Shared UI / Design System" (FASE 33 de la
mision anterior, ver `arquitectura_general.md` DOC-M25 en adelante).

### Contexto organizacional -- YA existe un selector parcial

El navbar superior YA tiene un boton "Cambiar de sede" con menu
desplegable (confirmado renderizado: "Sede Principal QA" / "centro"
como opciones), y un menu de cuenta mostrando el email del usuario
(`admin@home.com`) con acceso a "Perfil" y "Cerrar sesion". Esto
cubre parcialmente la FASE 4 de la mision (contexto visual
Empresa/Sede/Area/Usuario) -- falta mostrar Empresa y Area de forma
explicita junto a Sede, pero el patron de selector desplegable ya
esta establecido y debe reutilizarse, no reinventarse.

### Navegacion -- ANTES de esta pasada

`<ul id="nav">` era una lista plana de 15 items (14 apps + Mi Perfil)
sin agrupacion conceptual, en el orden en que historicamente se fue
agregando cada modulo (Dashboard, Empresa, Proyectos, Facturas,
Contabilidad, Inventario, Clientes, Ventas, Proveedores, Compras,
Empleados, Cotizaciones, Gastos, Bancos, [separador], Mi Perfil) --
sin relacion con el flujo de negocio real ni con categorias que un
usuario nuevo pueda reconocer.

### Hallazgo real encontrado durante el baseline: resaltado de item activo roto

`workspace.js` alternaba la clase CSS `.active` en el link de
navegacion clickeado (`classList.add('active')`/`remove('active')`),
pero `workspace.css` **nunca definio ninguna regla para `.active`**
-- solo estiliza `[aria-current="page"]`. Resultado: el usuario nunca
veia resaltado visualmente en que seccion estaba parado dentro del
sidebar, viola directamente el principio UX central de la mision
("¿Donde estoy?"). Corregido en esta misma pasada (ver FASE 3).

### `.agent/` docs de cada app (fuente de negocio real)

Cada app tiene su propio `.agent/AUDITORIA_FLUJO_*.md` -- ya usados
extensivamente en las 2 misiones de auditoria de codigo previas de
esta sesion. Son la fuente primaria de "que hace cada app" para el
mapa de experiencia (FASE 1), evitando re-descubrir reglas de negocio
ya documentadas.

### Registro / Home publico (`home.sintel.net.co` en este entorno de desarrollo)

Confirmado: en este entorno de desarrollo local, `home.sintel.net.co`
es literalmente el dominio de un TENANT real (schema `home`), no solo
el dominio publico generico -- resuelto via `/etc/hosts` local. El
flujo real de entrada:
1. `apps/public/core.PublicIndexView` (`public/core/index.html`) --
   landing page de marketing en el dominio raiz `sintel.net.co`.
2. Registro/activacion via `apps.public.tenants` (OTT, One-Time
   Token) -- consumido en `apps/tenant/core/api/viewsets.py`.
3. Tras activacion, el usuario entra directo al `workspace.html` de
   su tenant -- **no existe hoy ninguna pantalla de onboarding
   guiado con checklist de progreso** (el ejemplo de la mision
   "✅ Cuenta 🟡 Empresa ⚪ Equipo..." es una funcionalidad nueva a
   construir, no algo que ya exista y haya que mejorar).

**Hallazgo secundario (no corregido en esta pasada, informativo):**
`config/urls_public.py` registra `path('', PublicIndexView...)` en la
linea 70 Y `include('apps.public.tenants.urls')` en la linea 98
(que a su vez define su propio `path("", LandingPageView...)`) --
dado que Django resuelve el primer patron que matchea, la
`LandingPageView` de `apps.public.tenants` para la ruta raiz nunca es
alcanzable (queda shadowed). Los sub-paths (`/select/`, `/activate/`)
de ese mismo modulo SI funcionan. Candidato a limpieza en una fase
posterior de FASE 12 (codigo muerto de rutas) -- no se toca aqui por
no ser parte del alcance actual (nav restructuring).

---

## FASE 3 — Navegacion empresarial (IMPLEMENTADO en esta pasada)

Se reagrupo `<ul id="nav">` en 5 secciones conceptuales, siguiendo el
ejemplo literal de la mision, adaptado a los 15 items reales del
sistema:

| Grupo | Items |
|---|---|
| 🏠 Inicio | Dashboard |
| 🚀 Configuración | Mi perfil, Mi empresa, Equipo (Empleados) |
| 🤝 Relaciones | Clientes, Proveedores |
| 📦 Operación | Inventario, Cotizaciones, Proyectos, Gastos, Compras, Ventas |
| 💳 Finanzas | Facturas, Bancos, Contabilidad |

**Archivos tocados:**
- `apps/tenant/core/templates/tenant/core/workspace.html` --
  reestructuracion del `<ul id="nav">`. **Ningun `data-tab`/`href` se
  modifico** -- mismos 15 items, mismo `data-tab` exacto en cada uno,
  solo se agregaron 5 `<li class="nav-section-header">` como
  separadores visuales y se reordenaron los items dentro de sus
  nuevos grupos. Cero riesgo de romper el JS existente (que busca
  `#nav a[data-tab]` como descendiente, sin importar el anidamiento).
- `apps/tenant/core/static/tenant/core/css/workspace.css` -- agregada
  la regla `.nav-section-header` (11px, mayusculas, color
  `var(--muted)`, mismo lenguaje visual que `.brand h2` ya
  establecido) -- 2 reglas nuevas, ~14 lineas.
- `apps/tenant/core/static/core/js/workspace.js` -- **corregido el
  bug de resaltado de item activo**: las 3 llamadas a
  `classList.add/remove('active')` se cambiaron a
  `setAttribute('aria-current','page')`/`removeAttribute('aria-current')`,
  reutilizando la regla CSS `[aria-current="page"]` que YA existia
  pero nunca se activaba. Mejora de accesibilidad (semantica ARIA
  correcta) Y de UX (el resaltado ahora si funciona) en el mismo
  cambio, sin agregar CSS nuevo.

### Verificacion realizada

- **`manage.py shell`:** el template `tenant/core/workspace.html`
  parsea sin `TemplateSyntaxError`.
- **`django.test.Client(SERVER_NAME='home.sintel.net.co')` +
  `force_login()`** (tecnica estandar de Django, sin conocer ni
  ingresar ninguna contraseña real) sobre un usuario staff existente
  del tenant `home`: `GET /workspace/` responde `200`, y el HTML
  renderizado contiene exactamente la estructura de navegacion
  agrupada esperada, con los 15 `data-tab`/`href` intactos.
- **Contenido de `workspace.css` servido** (verificado 2 veces, antes
  y despues de `collectstatic` + reinicio del contenedor `web`):
  contiene la regla `.nav-section-header` con los valores correctos.
- **Verificacion visual en el Browser pane de esta sesion: NO
  concluyente.** La consola del navegador muestra
  `net::ERR_BLOCKED_BY_CLIENT` en las peticiones a los recursos
  estaticos de `home.sintel.net.co:8000` -- el propio sandbox del
  navegador de esta herramienta bloquea esas peticiones (comportamiento
  tipo ad-blocker), y esto se confirmo que **afecta a TODO
  `workspace.css`, incluyendo reglas preexistentes nunca tocadas**
  (`.brand h2`, `.ws-shell{display:grid}` tampoco se aplican en este
  navegador sandboxeado) -- no es un efecto de este cambio especifico.
  **Se recomienda verificacion visual manual en un navegador real**
  (Chrome/Edge normal del usuario) antes de considerar este cambio
  desplegado con confianza visual completa -- la evidencia estatica
  (contenido servido correcto, HTML renderizado correcto, JS sin
  errores de sintaxis en ejecucion) es solida, pero no reemplaza un
  vistazo visual humano.
- **Descartado explicitamente: cache de nginx.** Se confirmo via
  `curl` directo (fuera del navegador sandbox) que tanto
  `http://home.sintel.net.co:8000/static/.../workspace.css` (contenedor
  `web` directo) como `http://home.sintel.net.co/static/.../workspace.css`
  y `https://home.sintel.net.co/static/.../workspace.css` (a traves de
  `nginx`, contenedor `crm_sintel-nginx-1`) devuelven el contenido
  actualizado con la regla `.nav-section-header`. El bloqueo es 100%
  atribuible al sandbox del navegador de esta herramienta
  (`net::ERR_BLOCKED_BY_CLIENT` en la propia peticion `GET
  .../workspace.css`, confirmado via `read_network_requests`), no a
  ningun problema de infraestructura. Nota aparte (no relacionada, no
  corregida aqui): el contenedor `nginx` reporta healthcheck
  `unhealthy` en `docker compose ps`, aunque sirve trafico
  correctamente -- candidato a revisar en otra sesion, fuera del
  alcance de esta mision UX.

---

## FASE 2 — Onboarding / primeros pasos (IMPLEMENTADO)

Construida la pantalla de progreso de configuracion inicial que el
baseline (FASE 0) identifico como inexistente. Vive dentro de
`#workspace-welcome` (la pantalla que ya se mostraba al entrar al
workspace sin ningun tab activo) -- no es una pantalla nueva separada,
sino que enriquece la ya existente.

**Diseño de datos: 100% API-First, cero informacion inventada.** El
checklist consulta en paralelo los endpoints REST YA EXISTENTES de
cada app (no se creo ningun endpoint nuevo, cero backend nuevo):

| Paso | Señal real | Endpoint reutilizado |
|---|---|---|
| Cuenta | Siempre true (llegar a `/workspace/` ya exige `LoginRequiredMixin` + membresia activa) | -- |
| Empresa | `razon_social`, `nit`, `direccion` y `ciudad` todos no vacios | `GET /api/v1/empresas/mi-empresa/` |
| Equipo | Al menos 1 empleado registrado | `GET /api/v1/empleados/?page_size=1` (campo `count`) |
| Clientes | Al menos 1 cliente registrado | `GET /api/v1/clientes/?page_size=1` |
| Proveedores | Al menos 1 proveedor registrado | `GET /api/v1/proveedores/?page_size=1` |
| Inventario | Al menos 1 producto O 1 servicio (una empresa de puros servicios legitimamente tiene 0 productos) | `GET /api/v1/inventario/productos/?page_size=1` + `.../servicios/?page_size=1` |

Cada paso pendiente muestra un boton "Configurar" que simplemente
dispara `.click()` sobre el link real de navegacion
(`#nav a[data-tab="X"]`) -- reutiliza 100% la logica de navegacion ya
existente en `workspace.js` (mismo `showTab()`/`pushState()` de
siempre), cero duplicacion de routing.

**Se oculta sola cuando ya no aplica** (FASE 2 exige no insistir con
lo que el sistema ya sabe): si los 6 pasos estan completos, el
componente simplemente no se muestra -- queda solo el mensaje generico
"Selecciona un modulo para comenzar la gestion" que ya existia.

**Archivos nuevos:**
- `apps/tenant/core/templates/tenant/core/partials/onboarding_checklist.html`
  -- markup del card (Bootstrap `.card`, mismo lenguaje visual que
  `kpi_card.html`/`empty_state.html` ya existentes en
  `partials/ui/`, sin depender de ellos porque ninguno cubre un
  checklist de progreso).
- `apps/tenant/core/static/core/js/common/onboarding_checklist.js`
  -- IIFE vanilla JS, mismo patron exacto que `common/sede_selector.js`
  (namespaced en `window.Sintel.Core.OnboardingChecklist`). Sin
  dependencias nuevas, sin frameworks.

**Archivos editados:**
- `apps/tenant/core/templates/tenant/core/workspace.html` -- 1 linea
  `{% include %}` dentro de `#workspace-welcome`, 1 linea `<script>`
  en `extra_js`. Cero cambios a la logica de tabs existente.

### Verificacion realizada

- **Render del template:** confirmado via Django test Client +
  `force_login()` (mismo patron ya usado en FASE 3) que
  `GET /workspace/` (200) incluye el markup del checklist y el
  `<script>` del nuevo JS.
- **Endpoints reales, con datos reales del tenant `home`:** se
  consultaron los 6 endpoints con el mismo test Client. Resultado real
  observado: `mi-empresa` existe pero `ciudad=""` (Empresa incompleta,
  correctamente detectado como pendiente); `empleados.count=1`,
  `clientes.count=1`, `proveedores.count=2` (completos);
  `productos.count=0` y `servicios.count=0` (Inventario
  correctamente detectado como pendiente). Ningun dato fue inventado
  ni asumido -- se leyo el estado real de esta empresa de prueba.
- **Logica del widget (calculo de progreso + render del DOM):**
  dado que el navegador sandbox de esta herramienta bloquea
  **absolutamente todas** las peticiones de subrecursos a
  `home.sintel.net.co:8000` (confirmado exhaustivamente: no solo
  `workspace.css`, sino tambien el propio `onboarding_checklist.js`,
  y de hecho los ~60 archivos JS/HTMX de TODAS las apps del
  workspace -- incluso `workspace.js` mismo nunca llega a ejecutarse
  en este navegador, por lo que ni siquiera el click en un link del
  nav dispara `showTab()`), se verifico la logica inyectando el
  codigo identico del archivo directamente en el contexto de la
  pagina ya cargada, con `window.fetch` interceptado para devolver
  las respuestas REALES capturadas del test Client (no inventadas).
  Resultado: el checklist calcula correctamente 4/6 pasos completos,
  barra de progreso al 67%, los 4 pasos completos muestran el icono
  de check y los 2 pendientes (Empresa, Inventario) muestran el
  boton "Configurar" -- exactamente el comportamiento esperado dado
  el estado real de datos del tenant.
- **Conclusion sobre la herramienta de navegador de esta sesion:**
  esta confirmado que el bloqueo (`net::ERR_BLOCKED_BY_CLIENT`) es
  total para este dominio local personalizado (`home.sintel.net.co`),
  no parcial ni especifico de un archivo -- afecta a TODOS los JS/CSS
  del workspace, no solo a los tocados en esta mision. **Es un limite
  pre-existente de esta herramienta especifica, no un defecto de la
  aplicacion ni de este cambio.** Se recomienda de nuevo verificacion
  visual e interactiva (probar el boton "Configurar") en un navegador
  real antes de dar este incremento por validado visualmente.

---

## FASE 3.1 — Correccion de uniformidad del sidebar (IMPLEMENTADO)

**Hallazgo del usuario:** el grupo original "Operación" (FASE 3) no
era logicamente uniforme con el resto de grupos -- mezclaba en un
solo cajon 6 modulos de naturaleza distinta (Inventario, Cotizaciones,
Proyectos, Gastos, Compras, Ventas), mientras que "Finanzas" (Facturas,
Bancos, Contabilidad) si tenia un criterio claro y unico ("registro
fiscal/contable"). La agrupacion original de FASE 3 se hizo copiando
literalmente el ejemplo de la mision sin definir explicitamente un
criterio de clasificacion aplicado por igual a los 15 modulos --
resultado: 4 grupos con criterio claro (Inicio, Configuración,
Relaciones, Finanzas) y 1 grupo ("Operación") que era en realidad la
bolsa de "todo lo que sobraba".

**Criterio unico aplicado ahora, explicito y verificable, a las 6
categorias:**

| Grupo | Criterio | Modulos |
|---|---|---|
| Inicio | Vista general, no transaccional | Dashboard |
| Configuración | Administracion del tenant en si (acceso, datos de la empresa, personal) | Usuarios y roles, Mi empresa, Equipo |
| Relaciones | Contrapartes externas con las que se hacen negocios | Clientes, Proveedores |
| **Comercial** | Documentos de negociacion/transaccion con esas contrapartes | Cotizaciones, Ventas, Compras |
| **Operación** | Gestion de recursos internos de ejecucion (no son documentos de negociacion con un tercero) | Inventario, Proyectos, Gastos |
| Finanzas | Registro fiscal/contable formal (documento legal, caja, libro contable) | Facturas, Bancos, Contabilidad |

"Comercial" y "Operación" reemplazan al antiguo cajon unico
"Operación" de FASE 3 -- mismo total de modulos (6), pero ahora cada
uno de los 2 grupos resultantes tiene un criterio tan preciso como
"Finanzas" ya lo tenia. Se paso de 5 a 6 grupos.

**Cambio aplicado:** solo reordenamiento de `<li>` dentro de
`apps/tenant/core/templates/tenant/core/workspace.html` + 1 nuevo
`<li class="nav-section-header">Comercial</li>`. Cero `href`/`data-tab`
modificados o eliminados -- verificado que los 15 tabs y su orden
interno de atributos siguen exactamente iguales, solo reagrupados.

### Verificacion realizada

- Template parsea sin error.
- Render real via Django test Client + `force_login()`: se extrajeron
  los 6 encabezados (`Inicio, Configuración, Relaciones, Comercial,
  Operación, Finanzas`) y los 15 `data-tab` en su nuevo orden -- se
  confirmo que son exactamente los mismos 15 modulos que antes de
  este cambio, ninguno perdido ni duplicado.

---

## FASE Empleados/Dashboard — Revision (SIN CAMBIOS DE CODIGO)

**Empleados y Dashboard:** sin jerga tecnica user-facing. Buen
ejemplo de traduccion correcta ya presente en el codigo: el tab de
Nominas se titula **"Nóminas (Devengos)"** -- combina el termino de
negocio ("Nóminas") con el termino contable tecnico entre parentesis
("Devengos"), exactamente el patron que la mision pide (lenguaje de
negocio primero, tecnico solo como aclaracion opcional). Sin cambios
necesarios en ninguno de los 2 modulos.

**Hallazgo revisado y descartado deliberadamente (no es una
violacion real):**
`apps/tenant/empleados/static/empleados/js/features/devengo_editor.js`
tiene una funcion local `_mostrarOffcanvasSeguro()` (linea 139) que a
primera vista coincide con el patron prohibido
(`bootstrap.Offcanvas.getOrCreateInstance(el).show()`, linea 152).
Al leer el contexto completo se confirma que **no es una duplicacion
descuidada**:
- Limpia exactamente el mismo conjunto de backdrops/clases/estilos
  que el helper central (`.offcanvas-backdrop`, `overflow-hidden`,
  `modal-open`, `offcanvas-open`, `overflow`, `paddingRight`) --
  igual de completa, no una version debil como los casos de
  Inventario/Proyectos.
- Envuelve la creacion de la instancia en `setTimeout(() => ..., 0)`,
  con un comentario explicito: *"Tick minimo para que Bootstrap
  complete cualquier ciclo interno pendiente antes de crear la nueva
  instancia (evita null.scroll en offcanvas.js)"* -- es decir, es un
  workaround deliberado para un bug real y especifico de timing de
  Bootstrap en este componente. El helper central
  (`mostrarOffcanvasSeguro`) NO tiene este delay -- dispone y crea de
  forma sincronica.

Migrar esta funcion al helper central eliminaria el `setTimeout` y
podria **reintroducir el bug de `null.scroll` que este codigo existe
especificamente para evitar**. Se descarta como hallazgo -- coincidir
superficialmente con un patron de grep no es lo mismo que ser una
violacion real; la lectura completa del contexto es lo que decide.

---

## FASE Facturas/Contabilidad/Bancos — Revision (SIN CAMBIOS DE CODIGO)

**Contabilidad y Bancos:** sin jerga tecnica user-facing, sin
reimplementaciones de Offcanvas (las unicas menciones a
`bootstrap.Offcanvas` en estas 2 apps estan en comentarios de
documentacion `.agent/*.md`, no en codigo real). Rotulos como
"Asientos Contables", "Libro Diario", "Retenciones", "Extractos
Bancarios" son terminologia contable/bancaria estandar, no jerga de
arquitectura interna. Sin cambios.

**Facturas -- hallazgo detectado pero NO corregido (decision
deliberada):** `apps/tenant/facturas/static/facturas/js/facturas_main.js`
(`initOffcanvas()`, linea 49) reimplementa manualmente
`bootstrap.Offcanvas.getInstance()` + `dispose()` + limpieza de
backdrops + `new bootstrap.Offcanvas()`, el mismo patron ya
consolidado en `mostrarOffcanvasSeguro` (mismo tipo de hallazgo que
en Inventario/Proyectos). A diferencia de esos 2 casos, aqui se
decidio **no tocarlo en esta pasada**, por 3 razones concretas:

1. **Ya hace `dispose()` antes de crear** -- a diferencia del bug real
   que la regla de `CLAUDE.md` describe (`getOrCreateInstance()` SIN
   dispose previo), este codigo no tiene el bug de acumulacion de
   backdrops; la diferencia con el helper central es de amplitud de
   limpieza (le falta limpiar `.modal-backdrop` y algunos estilos),
   no una falla activa.
2. **Tiene un modo de uso real que el helper central no soporta**:
   `initOffcanvas()` se llama en 3 sitios (via `htmx:afterSettle`)
   *sin* mostrar el panel inmediatamente despues -- solo re-crea la
   instancia de Bootstrap tras un swap de HTMX. `mostrarOffcanvasSeguro`
   siempre llama `.show()` de inmediato; no existe hoy un modo
   "preparar sin mostrar". Migrar esto exigiria o bien extender el
   helper central (cambio con impacto en TODOS sus ~25 llamadores
   existentes) o reescribir la logica de re-inicializacion de
   Facturas -- ninguna de las dos es un cambio de UI de bajo riesgo.
3. **Alto radio de impacto**: la funcion se usa en mas de 10 sitios
   dentro de un archivo de 2000+ lineas, y ademas expone
   `AppFacturas.getOffcanvasInstance()` publicamente (otros modulos
   podrian depender de la instancia cruda). Facturas es, segun toda
   la documentacion de auditorias previas de esta sesion, el modulo
   mas critico y fragil del sistema (pipeline de importacion XML
   DIAN, Kardex, Contabilidad Pull Model). El mandato explicito de la
   mision es "si una duda de bajo riesgo existe, no tocar" -- aqui la
   duda es real.

Se documenta como hallazgo abierto para una fase futura dedicada
exclusivamente a Facturas, con presupuesto de tiempo para leer el
archivo completo y probar cada uno de los 10+ call-sites, en vez de
una correccion apurada dentro de esta pasada de UX general.

---

## FASE Inventario/Cotizaciones/Proyectos — Consolidacion de offcanvas duplicados (IMPLEMENTADO)

**Revision realizada:** se busco jerga tecnica (`schema_name`,
`TenantProfile`, `singleton`, `OCF`, `DSV`, `IDOR`) en las 3 apps --
sin ocurrencias user-facing. Cotizaciones no presento hallazgos.

**Hallazgo real en Inventario y Proyectos:** violacion directa de la
regla no-negociable de `CLAUDE.md` ("`getOrCreateInstance().show()`
en Offcanvas -- PROHIBIDO -- acumula backdrops. Usar
`mostrarOffcanvasSeguro(el)`") -- 2 reimplementaciones locales,
crudas, del manejo de Offcanvas que la consolidacion F33.4 ya habia
resuelto para otras apps (Empresa, ver FASE Empresa arriba) pero que
nunca llegaron a Inventario ni a Proyectos:

- `apps/tenant/inventario/templates/tenant/inventario/list_inventario.html`
  -- `window.sintelAbrirOffcanvas` reimplementaba manualmente
  `bootstrap.Offcanvas.getInstance()` + `dispose()` +
  `new bootstrap.Offcanvas().show()`, limpiando solo
  `.offcanvas-backdrop` y 2 clases de `body` (menos que el helper
  central, que tambien limpia `.modal-backdrop`, `offcanvas-open` y
  estilos de overflow/padding). Usado en 5 sitios del modulo
  (`list_activos.html`, `list_movimientos.html`, `list_productos.html`,
  `list_servicios.html` x2).
- `apps/tenant/proyectos/templates/tenant/proyectos/proyectos_list.html`
  -- el boton "Nuevo Proyecto" tenia una cadena `hx-on::after-request`
  con un fallback manual identico (`bootstrap.Offcanvas.getInstance` +
  `dispose` + backdrop removal + `new bootstrap.Offcanvas().show()`)
  para el caso en que `window.UIManager?.handleOffcanvas` no
  estuviera disponible -- caso que en la practica nunca ocurre, porque
  `UIManager` es un asset core cargado siempre (`assets_core.html`) y
  `UIManager.handleOffcanvas` ya es el mismo alias delgado hacia
  `mostrarOffcanvasSeguro` (confirmado leyendo `ui-manager.js:327-335`).

**Cambio aplicado (ambos casos, sin cambio de comportamiento):**
reemplazado por una llamada directa a
`window.Sintel?.Core?.mostrarOffcanvasSeguro(...)` -- mismo patron
"alias delgado" ya usado en Empresa. Cero logica de negocio tocada:
es exclusivamente codigo de infraestructura de UI (como se abre un
panel lateral), no reglas de negocio, calculos ni permisos.

### Verificacion realizada

- Ambos templates parsean sin error.
- Render real via Django test Client + `force_login()`: confirmado
  que el codigo nuevo esta presente y que el codigo crudo anterior
  (`bootstrap.Offcanvas.getInstance(el); if (prev) prev.dispose`) ya
  no aparece en ninguno de los 2 archivos.
- Se confirmo que ningun test del repositorio depende del markup
  crudo reemplazado (`sintelAbrirOffcanvas(` / `handleOffcanvas(el` /
  `bootstrap.Offcanvas.getInstance(el)` -- 0 coincidencias en archivos
  de test).

---

## FASE Empresa — Eliminado el badge "SSoT" del sidebar (IMPLEMENTADO)

**Hallazgo:** el link "Mi empresa" del sidebar tenia un badge literal
`<span class="badge bg-info">SSoT</span>` -- jerga de arquitectura
interna (Single Source of Truth) expuesta directamente al usuario
final, exactamente lo que `CLAUDE.md` prohibe explicitamente
("Conceptos tecnicos... NUNCA deben aparecer como lenguaje
user-facing"). Se reviso el resto de la app Empresa (templates,
JS de features, tablas) buscando `schema_name`, `TenantProfile`,
`singleton`, `OCF`, `DSV`, `tenant_id`, `empresa_id`, `SSoT` -- las
unicas ocurrencias de `SINGLETON`/`SSoT` encontradas estan en
comentarios de template (invisibles al usuario) o en codigo backend,
no en texto renderizado.

**Cambio aplicado:** se elimino el badge por completo (no se
reemplazo por otro texto) -- el dato "Empresa es singleton" no aporta
nada util a un usuario de negocio (nunca vera mas de una empresa, no
hay ambiguedad que aclarar), asi que quitarlo es mas simple y correcto
que inventar una traduccion de un concepto que el usuario no
necesita (principio "Simplicity First").

### Verificacion realizada

- Template parsea sin error.
- Render real via Django test Client + `force_login()`: confirmado
  que "SSoT" ya no aparece en ningun texto visible de la pagina (la
  unica ocurrencia restante es un comentario HTML `<!-- SSoT: ... -->`
  invisible para el usuario) y que el link "Mi empresa" sigue
  apuntando exactamente igual a `#empresa`.

---

## FASE Perfil — Renombrado de "Mi perfil" a "Usuarios y roles" (IMPLEMENTADO)

**Hallazgo real:** el tab `#perfil` (enlazado tanto desde el sidebar
como desde el dropdown de cuenta, ambos con el rotulo "Perfil"/"Mi
perfil") **no muestra un formulario de "editar mis propios datos"**
-- muestra una tabla completa de TODOS los perfiles del tenant
(columnas reales confirmadas en `apps/tenant/perfil/tables.py`:
Usuario, Cargo, Departamento, Telefono, Rol, Avatar, Acciones), con
permiso `IsTenantMember` (cualquier miembro puede verla, no solo
administradores). Es decir: es una pantalla de **gestion de usuarios
y roles del equipo** (ADMIN/OPERADOR/VISOR), no un perfil personal --
y no existe en todo el codebase ninguna pantalla separada de "editar
mi propio perfil". El rotulo "Mi perfil"/"Perfil" prometia una cosa
(mis datos personales) y entregaba otra (gestion de todo el equipo) --
viola directamente el principio "¿Donde estoy? ¿Que es esto?" de la
mision, para cualquier usuario, no solo los nuevos.

**Cambio aplicado (solo texto de navegacion, cero logica tocada):**
"Mi perfil" -> **"Usuarios y roles"** en los 3 lugares donde aparecia
el rotulo:
- `apps/tenant/core/templates/tenant/core/workspace.html` (link del
  sidebar).
- `apps/tenant/core/templates/tenant/partials/_header.html` (link del
  dropdown de cuenta).
- `apps/tenant/core/static/core/js/workspace.js` (mapa de titulos de
  `viewTitle`, usado por `showTab()`).

**Deliberadamente NO tocado en este incremento** (fuera de alcance,
para mantener el cambio acotado y revisable): el texto interno del
modulo ("Nuevo Perfil", tooltips, columnas de la tabla) y la pregunta
mas profunda de si deberia existir una pantalla separada de "editar mi
propio perfil" (hoy no existe ninguna) -- ambas cosas quedan anotadas
para una pasada futura de esta misma fase si el usuario lo confirma.

**Hallazgo secundario (no corregido, informativo):**
`tests/tenant/core/test_workspace_account_dropdown.py::test_perfil_removed_from_sidebar`
busca el sidebar con el string literal `'<ul class="nav" id="nav">'`,
pero el markup real siempre ha sido `<ul class="nav flex-column"
id="nav">` (incluso antes de esta mision) -- el `.find()` nunca
encuentra el marcador, `sidebar_start` queda en `-1`, y el bloque
`if sidebar_start != -1 and sidebar_end != -1:` que contiene las
aserciones reales nunca se ejecuta. El test pasa en verde de forma
vacia (no verifica nada) independientemente de si `#perfil` esta o no
en el sidebar -- confirmado por lectura de codigo, es un gap de
cobertura pre-existente, no introducido por este cambio. No se
corrige aqui (fuera del alcance de la mision UX; requeriria decidir
si la intencion original -- sacar Perfil del sidebar -- sigue vigente,
lo cual es una decision de producto, no de UI).

**Confirmado por ejecucion real** (`pytest tests/tenant/core/test_workspace_account_dropdown.py`,
5 passed / 2 failed): `test_perfil_removed_from_sidebar` esta entre
los 5 que pasan -- confirma la lectura de codigo de arriba (pasa de
forma vacia). Los 2 que fallan (`test_hash_routing_still_works`,
`test_workspace_contains_all_view_sections`) son de una arquitectura
anterior por completo: buscan `hydrateView`/`currentViewFromHash` (JS)
e `id="view-perfil"`/`id="view-empresa"`/etc. (HTML), ninguno de los
cuales existe en el codigo actual (que usa `showTab()`/`popstate` e
`id="tab-*"`) -- confirmado que **no tienen relacion con el rotulo
renombrado en este cambio**, son staleness pre-existente de un
refactor de arquitectura anterior que nunca actualizo este archivo de
test. No se corrigen aqui (mismo criterio que arriba: fuera de
alcance de la mision UX).

### Verificacion realizada

- **Render de ambos templates:** confirmado que
  `tenant/core/workspace.html` y `tenant/partials/_header.html`
  parsean sin error.
- **Render real via Django test Client + `force_login()`:** el
  sidebar contiene "Usuarios y roles" (ya no "Mi perfil") y el
  dropdown de cuenta contiene "Usuarios y roles" (ya no "Perfil"),
  ambos enlazando igual que antes a `#perfil` -- cero cambio de
  destino/comportamiento, solo el rotulo visible.

---

## Estado de la mision UX

Esta es la PRIMERA pasada de una mision de transformacion de gran
escala (37 fases segun el prompt original, cubriendo Home/Onboarding,
las 16 apps, sistema visual, iconografia, formularios, tablas,
responsive, accesibilidad). Dado el alcance y que este es un cambio
**visible en produccion** (a diferencia de las 2 misiones de auditoria
de codigo backend anteriores en esta sesion, que eran solo eliminacion
de codigo muerto sin riesgo visual), se entrega este primer incremento
concreto y verificable (navegacion agrupada + fix de resaltado activo)
y se documenta el hallazgo real (ruta shadowed en `urls_public.py`,
ausencia de onboarding guiado) antes de continuar con mas fases, para
que el usuario pueda revisar el resultado visualmente.

**Primera pasada completa sobre las 16 apps, en el orden fijo exacto
de la mision, cerrada:** Home/Onboarding -> Perfil -> Empresa ->
Clientes/Proveedores -> Inventario/Cotizaciones/Proyectos ->
Gastos/Compras/Ventas -> Facturas/Contabilidad/Bancos ->
Empleados/Dashboard. 9 commits en total. Resumen por bloque:

| Bloque | Resultado |
|---|---|
| Home/Onboarding | Navegacion agrupada (FASE 3) + fix aria-current + checklist de primeros pasos (FASE 2) |
| Perfil | Rotulo "Mi perfil" -> "Usuarios y roles" (mismatch real de contenido) |
| Empresa | Badge "SSoT" eliminado del sidebar |
| Sidebar (correccion transversal) | "Operacion" dividido en "Comercial"+"Operacion" con criterio uniforme |
| Clientes/Proveedores | Sin hallazgos -- ya en buen estado |
| Inventario/Cotizaciones/Proyectos | Offcanvas duplicado consolidado en Inventario y Proyectos (Cotizaciones sin hallazgos) |
| Gastos/Compras/Ventas | Sin hallazgos -- ya en buen estado |
| Facturas/Contabilidad/Bancos | Contabilidad/Bancos sin hallazgos; Facturas: hallazgo de offcanvas detectado pero **no corregido** (alto riesgo, documentado para fase futura dedicada) |
| Empleados/Dashboard | Sin hallazgos -- caso de offcanvas revisado y descartado (workaround deliberado de un bug real de Bootstrap, no una duplicacion descuidada) |

**Patron consistente en toda la revision:** de las 16 apps, solo 6
requirieron cambios de codigo (todos de bajo riesgo: rotulos,
agrupacion de navegacion, consolidacion de infraestructura de UI ya
existente). Las otras 10 ya estaban en buen estado o el hallazgo
encontrado se determino, tras leer el contexto completo, que no era
una violacion real o que corregirlo era mas riesgoso que dejarlo --
consistente con el mandato de la mision de cautela sobre velocidad y
"cambios quirurgicos, solo tocar lo necesario".

**Pendiente para una proxima fase (no iniciado):** FASE 1 (mapa de
experiencia completo, documento dedicado), revision mas profunda de
formularios/offcanvas de creacion-edicion (esta pasada se centro en
listados/navegacion, no en los formularios individuales de cada
modulo), y la fase dedicada a Facturas mencionada arriba.
