# F33 — Shared UI / Design System — STATUS REPORT

**Estado global: IN_PROGRESS** (no COMPLETED -- ver razonamiento al final)

**Actualizacion:** F33.13 (expansion controlada) avanzo de NOT_STARTED a
IN_PROGRESS con 2 batches reales ejecutados y verificados (commits
`a39fa8f`, `22373dd` -- 17 archivos tocados/eliminados en 7 apps (perfil,
compras, gastos, facturas, contabilidad, inventario, core),
ver seccion F33.13 abajo y `F33_APP_EXPANSION_MATRIX.md` para el detalle
completo).

## F33.0 — Inventario Shared UI: PASS

Escaneo real de las 17 apps tenant via agente de exploracion dedicado.
Detalle: `documentacion/F33_SHARED_UI_INVENTORY.md`. Hallazgo principal:
Offcanvas tenia 2 helpers "safe" independientes con adopcion comparable
(~25 vs ~22 archivos); Confirmaciones tenia 3 mecanismos coexistiendo;
Card KPI duplicada 7 veces; Badges de estado con 4+ convenciones para el
mismo semantico en 7 apps.

## F33.1 — Clasificar duplicados: PASS

`SHARED_EXISTING` / `DUPLICATE` / `APP_SPECIFIC` / `CANDIDATE_SHARED` /
`OBSOLETE` aplicado a los 12 hallazgos del inventario (mismo documento,
segunda mitad). Conclusion: Offcanvas y Confirmaciones no necesitaban
componente nuevo, solo consolidar el duplicado sobre el target ya
existente.

## F33.2-9 — Core UI Contract, Table, Offcanvas, Form, Estados,
Notificaciones, Filtros, Cards: PASS

`documentacion/F33_CORE_UI_CONTRACT.md`. De las 10 piezas conceptuales de
la mision original, 6 ya existian (Table=django-tables2, Notificaciones/
Confirm=UIManager, Offcanvas=mostrarOffcanvasSeguro) o no tenian evidencia
de duplicacion que las justificara (Form, ErrorState). Las 4 restantes se
implementaron como primitivas Django server-side minimas (no JS):
`sintel_kpi_card`, `sintel_empty_state` (templatetags), mas 2 partials
(`loading_state.html`, `filter_bar.html`) y un helper de wording
(`tables_i18n.empty_text`). Deliberadamente no se creo
`window.Sintel.Core.UI` como namespace nuevo.

## F33.4 — Offcanvas Contract: PASS (consolidacion real ejecutada)

`Sintel.Core.mostrarOffcanvasSeguro` extendido con `{action:'show'|'hide'}`
(retrocompatible, default `'show'`). `UIManager.handleOffcanvas` -- la
segunda implementacion independiente que el inventario encontro -- ahora
es un alias delgado que delega ahi. Verificado con spec E2E dedicado
(`62-f334-offcanvas-consolidation.spec.js`, show/hide via ambos puntos de
entrada) mas las 3 specs CRUD existentes que ya ejercitan offcanvas real.

## F33.10 — Migracion piloto: PASS

App elegida por evidencia (no preferencia): `empresa`, que tenia el
hallazgo mas completo y accionable del inventario -- 2 templates de modal
confirmados muertos (`modals.html`, `mailinbox_modals.html`) mas su propia
copia del snippet de fallback de offcanvas (`sintelAbrirOffcanvasEmpresa`).

Ejecutado: ambos modals muertos eliminados (una investigacion mas profunda
que la del inventario original confirmo que `mailinbox_modals.html`
tampoco estaba "vivo pero sin migrar" como decia el inventario -- el flujo
real ya usa un offcanvas server-rendered completamente distinto via
`MailInboxConfigViewSet.render_offcanvas`, corrigiendo la clasificacion a
`OBSOLETE`). El snippet local se redujo a un alias de una linea sobre el
helper ya consolidado.

## F33.11 — Validacion piloto: PASS

- `manage.py check`: PASS.
- Governance (`tools.organizational_governance.cli --report`): **FINAL
  STATUS: PASS** (0 WARN, 0 FAIL).
- Playwright, suite completa (29 specs, incluye los 2 nuevos de F33):
  **29/29 PASS.**
- Flujo real verificado con navegador: click en "Nueva Sede" abre el
  offcanvas correctamente via el helper consolidado.

## F33.12 — Impact Analysis: PASS (con hallazgo de cobertura del grafo)

`python -m tools.ekg.impact --path "offcanvas.helper.js" --offline`:

```
Total impacted (excluding target): 4
  assets_core.html -> workspace.html, assets_dashboard.html, assets_landing.html

Tests covering target or any impacted node: NONE FOUND
Aplicaciones tocadas: core, dashboard, landing
```

**Hallazgo, no bloqueante:** el grafo EKG no detecta cobertura de test
para este cambio, pero SI existe (specs 62/63, mas las 3 specs CRUD
existentes que ejercitan offcanvas real) -- el grafo solo indexa
referencias `{% static %}`/imports estaticos, no llamadas JS a funciones
cross-archivo (`mostrarOffcanvasSeguro()` invocado desde ~25 archivos de
features no aparece como arista). Gap de completitud del grafo, documentado
para una fase futura de EKG, no una falta real de cobertura.

## F33.13 — Expansion controlada: **IN_PROGRESS** (2 batches ejecutados con evidencia)

Detalle completo: `documentacion/F33_APP_EXPANSION_MATRIX.md`.

**Batch 1 (Offcanvas #12c/#12d, commit `a39fa8f`):** 11 archivos en 6 apps
(perfil, compras, gastos, facturas, contabilidad x6, inventario)
consolidados sobre `Sintel.Core.mostrarOffcanvasSeguro`, mismo patron ya
probado en el piloto empresa. Verificado con grep repo-wide (0
instanciaciones crudas de `bootstrap.Offcanvas` restantes salvo el propio
helper y 2 excepciones deliberadamente preservadas -- `devengo_editor.js`
por un workaround real de timing de Bootstrap ya documentado en F31.2, y
`facturas_main.js:66` por su contrato de 3 funciones separadas, tambien
documentado en F31.2). `manage.py check` PASS, governance PASS, E2E 29/29.

**Batch 2 (OBSOLETE con evidencia, commit `22373dd`):** 6 archivos
eliminados -- 2 modals de confirmar-eliminar sin consumidores JS
(compras, gastos) + 4 de los 5 prototipos Tailwind huerfanos (el 5o,
`dashboard/index.html`, se dejo intacto por estar alcanzado por trafico
real via el redirect post-login y por estar ya modificado por otra sesion
concurrente). `manage.py check` PASS, governance PASS, E2E 29/29 (una
corrida intermedia con 10 fallos se investigo y se confirmo ambiental --
`AnonRateThrottle` agotado tras 2 suites seguidas, no una regresion; ver
matriz para el detalle completo con evidencia de logs).

**Batch 4 (ModalService, commits `6feccaa`+`68bfacd`):** eliminado
`core/js/helpers/modal-service.js` (0 consumidores confirmados por grep
+ Impact Analysis), su `<script>` tag en `assets_core.html`, y la
entrada obsoleta en `helpers/README.md`. Diferido en el batch 2 por su
carga global (mayor blast radius); ejecutado ahora con su propio ciclo
de verificacion completo. `manage.py check` PASS, governance PASS, E2E
29/29 (corrida completa, contenedor Playwright fresco).

**Batch 5, parte 1 (Confirm nativo->UIManager, subconjunto de 1 sitio):**
migrados `ventas/resolucion_editor.js` y `perfil/perfil.modals.js` (los
2 unicos sitios donde toda la superficie de `confirm()` nativo de la app
vive en un solo archivo/funcion). `bancos.main.js` evaluado y diferido
-- su `confirm()` es solo el fallback de un modal Bootstrap hand-rolled
vivo (hallazgo #5c del inventario, DUPLICATE), migracion de mayor
alcance que un simple swap. `manage.py check` PASS, governance PASS,
E2E 29/29.

**Batch 5, parte 2 (resto de Confirm nativo->UIManager, 27 sitios en 21
archivos, 8 apps):** migrados todos los sitios de `confirm()` nativo
confirmados aislados (auditados uno por uno contra Modal usage antes de
tocar codigo -- clientes, empleados, empresa, contabilidad, proyectos,
proveedores, inventario, facturas). Solo `bancos.main.js` queda como
`confirm()` nativo en todo `apps/tenant/**` (modal-integrado, #5c del
inventario, diferido).

**Hallazgo real durante la verificacion (no ambiental):** 2 specs E2E
existentes (`10-clientes-crud.spec.js`, `30-contabilidad-cuenta-crud.spec.js`)
usaban `page.once('dialog', ...)` para el flujo de eliminar -- el patron
de Playwright para `window.confirm()` nativo, que deja de dispararse con
`UIManager.confirm()` (SweetAlert2, un modal DOM real). Corregidos ambos
specs para clickear `.swal2-confirm`. Verificado en ese momento que
ningun otro spec compartia el patron contra un archivo tocado
(`20-inventario-productos-crud.spec.js` usaba el mismo `dialog` handler
pero contra `productos_list.js`, no tocado en ese batch -- **luego si
se toco en F33.13-B, ver abajo**).

`manage.py check` PASS, governance PASS. E2E: 28/29 tras el fix (2
corridas intermedias con fallos masivos se investigaron y confirmaron
`AnonRateThrottle` -- error 429 literal en el texto de fallo, mismo
patron ya documentado en batch 2; contenedor `web` reiniciado 2 veces
mas en el proceso). El unico fallo restante en la corrida final es la
flakiness de login() pre-existente y ya documentada en
`tests/e2e/specs/_helpers.js`, no relacionada con este batch.

**F33.13-B (cierre completo de `confirm()` nativo -- bancos + gap de
grep):** Prioridad explicita: `bancos.main.js` auditado por completo
ANTES de tocar codigo (quien abre el modal, quien lo cierra, 0
consumidores externos confirmados, migrable al patron Core sin
comportamiento especifico de dominio) -- migrado a `UIManager.confirm()`,
modal HTML completo eliminado de `list_bancos.html`. Durante la
verificacion final se encontro que el grep de batch 5
(`confirm(['"]`, solo strings literales) tenia un gap real: no detectaba
`confirm(unaVariable)`. Un grep mas amplio encontro **3 sitios mas**:
`inventario_list.js`, `movimientos_list.js`, `productos_list.js` --
migrados, y el spec `20-inventario-productos-crud.spec.js` corregido con
el mismo patron `.swal2-confirm`.

**Verificacion final repo-wide: 0 confirm() nativo restante en todo
`apps/tenant/**`, 0 specs E2E dependientes de `page.once('dialog'`.**
`manage.py check` PASS, governance PASS, E2E **29/29 PASS** (contenedor
`web` reiniciado preventivamente antes de correr, sin necesidad de
segunda pasada -- incluye `63-f3310-empresa-pilot.spec.js`, verde esta
vez tras ser flaky en corridas anteriores).

`empleados_list.html`/`empleado_list.js` (patron modal hermano, sin
fallback `confirm()` nativo) queda fuera de este cierre -- nunca aparecio
en ningun grep de `confirm()` porque su modal se abre directamente sin
condicional. Documentado como trabajo futuro aparte.

**F33.14-A (Card KPI, inventario + adopcion controlada):** auditoria de
16 candidatos en las 17 apps tenant (detalle completo:
`documentacion/F33_14A_CARD_KPI_INVENTORY.md`). Corrige el inventario
original de F33.0 -- de los "7 sitios duplicados" declarados, solo 2 se
migraron sin cambiar comportamiento ni diseno (`clientes` 6/6 cards,
`proyectos` 4/6 cards; las otras 2 cards de proyectos tienen un color no
estandar y un font-size custom, personalizacion real no descuido).
`cotizaciones` es byte-identico al target pero sus valores se actualizan
por JS via `id=` (bloqueado hasta decidir si se extiende el primitivo).
`ventas`/`gastos`/`facturas` tienen estilos propios reales (tamano,
acento de color, tipografia) que el inventario original no distinguio.
Se encontraron ademas 2 implementaciones de KPI card completamente
independientes no detectadas en F33.0 (`compras`, `inventario` x2
archivos). `manage.py check` PASS, governance PASS, E2E 29/29.

**F33.14-B (Empty State, inventario + adopcion controlada):** auditoria
de 8 candidatos en las 17 apps tenant (detalle:
`documentacion/F33_14B_EMPTY_STATE_INVENTORY.md`). Solo
`clientes/clientes_list.html` (2/2 sitios) era byte-identico al target
sin acoplamiento funcional -- migrado. Los otros 7 se dividen en una
sub-variante "compacta" (`id` en vez de `data-attr`, repetida en
`clientes` y `proveedores`), 2 variantes `alert-info` en `proveedores`
que ni siquiera coinciden entre si para el mismo concepto, y un patron
de fila de tabla `{% empty %}` estructuralmente incompatible (`bancos`,
`facturas`). Hallazgo colateral: `contactos_list.html` resulto ser
codigo muerto real (0 referencias repo-wide) -- eliminado, no migrado.
`manage.py check` PASS, governance PASS, E2E 29/29.

**F33.14-C (Loading states, inventario + adopcion controlada):**
auditoria de 17 candidatos (`spinner-border`) en las apps tenant
(detalle: `documentacion/F33_14C_LOADING_STATE_INVENTORY.md`). Solo
`gastos/gastos_list.html` (2/2 sitios) y `compras/compras_list.html`
(1/1 sitio) eran el contenido inicial byte-identico de un panel
`hx-trigger="load"` -- migrados. Los otros 14 se dividen en: una familia
"compacta py-4" con 2 sub-variantes internas inconsistentes entre si,
repetida en `clientes` y `facturas` (4 sitios, 3 archivos); un spinner
JS-toggled por `data-spinner` con color propio en `clientes_list.html`
(mecanismo distinto al del target, mismo patron que el hallazgo
`data-empty-state` de F33.14-B); un near-miss de un solo sitio en
`contabilidad/reporte_page.html` (le falta `role="status"` +
`span.visually-hidden`, migrarlo seria a la vez un cambio visual y una
mejora de accesibilidad no solicitada); 8 archivos con spinners inline
de boton/celda de tabla (estado de envio de formulario, no panel); y 2
overlays globales (`workspace.html`, `editor_cotizacion.html`).
`manage.py check` PASS, governance PASS. E2E: primera corrida post-
restart del contenedor `web` arrojo 18 fallos `ERR_CONNECTION_REFUSED`
(el puerto 8000 aun no aceptaba conexiones pese a que `manage.py check`
via `docker compose exec` ya pasaba -- ese comando no prueba que el
servidor este escuchando en red) -- confirmado como carrera de arranque
del contenedor, no una regresion del cambio, verificando que los 11
tests que si corrieron pasaron. Re-corrida completa tras confirmar el
puerto activo (`curl` 200 en `/static/tenant/core/auth/login.html`):
**29/29 PASS** (4.4m).

**F33.14-D (Filter/search bar, inventario + adopcion controlada):**
auditoria de 21 candidatos (`keyup changed delay:400ms`) en las apps
tenant (detalle: `documentacion/F33_14D_FILTER_BAR_INVENTORY.md`). Solo
`compras/compras_list.html` (1/1 sitio) y `gastos/gastos_list.html`
(2/2 sitios) eran el markup byte-identico al target (`input-group
input-group-sm w-auto` + `data-search-input` + boton
`data-action="search"`) -- migrados. Los otros 19 se dividen en: una
familia real de 4 archivos "icono-prefijo, sin boton" (`clientes`,
`proyectos`, `ventas`, `facturas`), casi siempre con `hx-include` para
combinar con filtros por pestaña/estado; 2 archivos cuyo wrapper
coincide pero el boton difiere (`bancos` no tiene boton de busqueda en
absoluto, `proveedores` tiene un boton con su propio `hx-get`
autosuficiente en vez del handler JS del target); y 13 archivos con un
patron "input bare" sin wrapper ni boton (`contabilidad` x5, `empleados`
x5 sitios, `empresa` x2 archivos, `perfil`, `inventario` x4). `manage.py
check` PASS, governance PASS, E2E **29/29 PASS** (4.7m, contenedor `web`
verificado activo -- `curl` 200 -- antes de correr, tras el mismo
hallazgo de carrera de arranque que F33.14-C).

**F33.14-E (Badges de estado, auditoria de cierre de Batch 8):**
auditoria de 179 metodos `render_*` en los 13 `tables.py` de las apps
tenant (detalle: `documentacion/F33_14E_BADGES_ESTADO_INVENTORY.md`).
A diferencia de A-D, **no existe primitivo de badge compartido hoy**
(`sintel_ui.py` solo lo menciona en un comentario) -- el unico
candidato real (`render_activo`/`render_activa`, patron booleano en
7-8 sitios de 5 apps) tiene **3 combinaciones de color inconsistentes
para "Inactivo"**, incluso dentro de la misma app (`contabilidad`,
`inventario`). El resto (~50 sitios) son mapeos de estado genuinamente
especificos de cada dominio, confirmando con evidencia real la
conclusion original del batch 8. **0 archivos de codigo modificados**
-- crear un primitivo sin decision de diseno previa violaria la
prohibicion explicita de "no crear mas infraestructura". Sin cambios
de codigo, no aplica ciclo `manage.py check`/governance/E2E.

**Batches 6b-7b-7c-8b-9b (resto de Card KPI, Empty state, Loading
states, Badges booleanos, Filtros) — pendientes**, documentados con
evidencia en la matriz junto con su motivo de diferimiento (requieren
spot-check visual en navegador por app, o decisiones de diseno sobre
el primitivo, no solo grep mecanico). No son omision silenciosa -- son
decisiones de alcance explicitas para no violar la regla "nunca
refactor masivo + migracion masiva en la misma operacion".

**Batches 6-9 (Shared UI adoption) quedan asi formalmente cerrados**
con evidencia (F33.14-A a F33.14-E): 4 sub-fases con migraciones reales
(8 archivos, 12 sitios migrados en total) + 1 sub-fase de auditoria pura
que confirma por que no corresponde crear un primitivo nuevo sin
decision de diseno adicional. Roadmap original: "Una vez terminados
Batches 6-9, hacemos F33.15 -> F33.19 como cierre formal" -- siguiente
paso: F33.15 (Testing).

## F33.15 — Testing (consolidacion de la suite existente): **PARCIAL, con hallazgos reales, bloqueada por inestabilidad del entorno Docker local**

**Ejecutado y verificado:**
- `pytest --collect-only`: **2064 tests, 0 errores de coleccion** -- confirma
  que ninguno de los cambios de F33.13/F33.14 (frontend puro) rompio la
  coleccion de tests, mismo baseline que la validacion F33-R previa.
- Registrado el marker `pytest.mark.e2e` en `pytest.ini` (estaba en uso
  en `tests/e2e/test_workspace_facturas_forensics.py` sin declarar,
  generaba `PytestUnknownMarkWarning` en cada coleccion). Verificado:
  2064 tests siguen coleccionando, 0 errores, antes y despues del
  cambio. Commit aislado.

**Bloqueado -- corrida completa de `pytest` (2064 tests) no se pudo
completar de forma confiable en este entorno:**

El motor de Docker Desktop (backend WSL2) colapso repetidamente
(`500 Internal Server Error` en la API, contenedores forzados a
reiniciar) durante intentos sucesivos de correr la suite completa y,
tras dividirla, incluso el subconjunto `apps/public` (mas pequeno).
Diagnostico real, no descartado a la primera:

1. **No fue falta de memoria** -- se detuvieron `neo4j`/`cloudflared`
   para liberar RAM (la VM de Docker tiene 5.7GiB, uso en reposo ~1.4GB)
   y el patron de corte persistio identico.
2. **No fue acumulacion de schemas huerfanos** -- verificado con SQL
   directo (`information_schema.schemata`): solo 3 schemas no-publicos
   en la base, sin residuos `test_*`/`empresa*` de corridas previas.
   `TenantTestCase` limpia correctamente.
3. **Causa real identificada:** una corrida en modo verbose (`-v
   --tb=no`, matada manualmente tras confirmar que el buffer de
   `docker compose exec -T` no se vacia hasta el final del proceso)
   revelo que el corte real ocurre en
   `apps/public/console/tests/test_legacy_public_tenants_api.py`, en la
   clase `ConsoleAPIConsumptionTests` -- su `setUp()` crea 2 tenants
   reales (`TenantClient.objects.create(schema_name=...)`) por cada
   test, lo cual dispara `CREATE SCHEMA` + migraciones completas de
   tenant en PostgreSQL, una operacion DDL pesada que se vuelve
   progresivamente mas lenta bajo la degradacion de I/O que el propio
   entorno Docker Desktop ya arrastraba tras los reinicios forzados
   anteriores -- probablemente entrando en una espiral: timeout del
   comando -> proceso pytest no finaliza limpio dentro del contenedor
   -> conexiones/transacciones Postgres no liberadas -> siguiente
   corrida arranca en peor estado -> nuevo colapso.
4. **Hallazgo colateral, tambien real, verificado por ejecucion
   completa (no interrumpida) de la clase mas corta:** 5 tests de
   `ConsoleIsolationAndPermissionsTests` en el mismo archivo **fallan**
   (no se cuelgan): `test_console_only_accessible_from_public_schema`,
   `test_dashboard_requires_staff`, `test_impuestos_catalogo_requires_staff`,
   `test_tenants_list_requires_staff`, `test_users_list_requires_staff`.
   Lectura de codigo (`config/urls_public.py` lineas 107-108) muestra
   un candidato de causa: `path('console/', include('apps.public.console.urls'))`
   se registra ANTES que `path('console/impuestos/', include('apps.public.impuestos.dashboard.urls_dashboard'))`,
   y `console/urls.py` linea 26 ya define su propia ruta
   `impuestos/` (`ImpuestosIndexView`) -- un posible conflicto de
   enrutamiento donde la vista de `console/urls.py` shadowea a la de
   `impuestos.dashboard` en `console/impuestos/`. **No verificado por
   ejecucion** (el entorno no lo permitio de forma confiable) -- es una
   hipotesis fundamentada por lectura de codigo, no una causa
   confirmada.

**No se sigue reintentando la ejecucion masiva** -- instruccion
explicita del usuario tras observar el patron de cuelgues repetidos:
identificar el bug, documentarlo, y continuar con el resto de tareas en
vez de esperar indefinidamente una respuesta que no llega. El archivo
`apps/public/console/tests/test_legacy_public_tenants_api.py` (700
lineas, nombre "legacy") queda senalado como el punto de partida real
para quien retome esta investigacion: aislar `ConsoleAPIConsumptionTests`
en un entorno Docker sano y en reposo, con timeout largo (>10 min) y
`-x` (parar en el primer fallo) para confirmar si el cuelgue es del
`setUp()` (creacion de tenant) o de un test especifico posterior.

**F33.15 no se declara COMPLETED** -- coleccion y marker quedan
resueltos con evidencia; la corrida completa/regresion queda como
pendiente real, bloqueada por el entorno, con el diagnostico de causa
mas probable ya documentado para no repetir el mismo ciclo de
diagnostico en el proximo intento.

## F33.17 — Accesibilidad (componentes modificados): **PARCIAL**

Auditoria enfocada, no un WCAG audit completo -- solo los componentes
tocados por F33.13/F33.14 (modal/confirm, offcanvas, forms, tables,
labels/ARIA), por lectura de codigo (sin depender de ejecucion pesada
de Docker, dado el hallazgo de F33.15).

**Hallazgos reales, corregidos** (solo atributos ARIA, 0 cambio visual
o funcional, verificado con `Template().render()`):
- `kpi_card.html` / `empty_state.html`: icono decorativo (`<i
  class="bi bi-...">`) sin `aria-hidden="true"` -- puede ser anunciado
  como ruido por algunos lectores de pantalla. Corregido en ambos.
- `filter_bar.html`: el boton de busqueda es icon-only (sin texto
  visible), dependia solo de `title="Buscar"` -- no es un sustituto
  confiable de un nombre accesible (WCAG 4.1.2 Name, Role, Value).
  Se agrego `aria-label="Buscar"` explicito.

Los 3 fixes se propagan automaticamente a las adopciones ya hechas
(Card KPI: `clientes` 6 sitios + `proyectos` 4 sitios; Empty State:
`clientes` 2 sitios; Filter Bar: `compras` 1 sitio + `gastos` 2
sitios). `manage.py check` + governance PASS.

**Revisado sin hallazgos** (ya siguen buenas practicas, sin cambios
necesarios): `UIManager.confirm()` (delega en SweetAlert2, que maneja
foco/ARIA nativamente); `mostrarOffcanvasSeguro` (delega en
`bootstrap.Offcanvas` nativo, que maneja `aria-hidden`/foco/restauracion);
formulario muestreado (`offcanvas_crear_cliente.html`, 12/12 inputs con
`<label for="id">` correctamente asociado).

**No cubierto en esta pasada** (fuera del foco "componentes
modificados", o requiere herramientas de contraste/lectura de pantalla
real no disponibles por lectura de codigo): contraste de color real
(solo inspeccion de clases Bootstrap, no medicion), navegacion por
teclado end-to-end en flujos completos, tablas django-tables2 (headers
`<th>` -- la libreria los genera automaticamente, no auditado a fondo).

## F33.16, F33.18, F33.19 — E2E (clean 29/29 baseline), Responsive,
Performance, Release Gate: **NOT_STARTED**

Responsive y Performance (F33.18-19) requieren su propia auditoria real
(pruebas de `resize_window` en mobile/tablet, deteccion de
listeners/requests duplicados) -- no se hicieron pasadas superficiales
para "marcar la casilla"; genuinamente no se ejecutaron. F33.16 (E2E)
tiene evidencia parcial acumulada: cada batch de F33.13/F33.14 corrio la
suite E2E completa (29/29 PASS en cada cierre exitoso), pero el objetivo
explicito de F33.16 -- resolver definitivamente la flakiness historica de
`login()` y declarar un baseline limpio como parte del Release Gate, no
solo "paso en la ultima corrida de un batch" -- no se ha ejecutado como
sub-fase propia todavia.

**Esto NO es un bloqueo (`BLOCKED_SAFE`)** -- no hay ningun impedimento
tecnico, de permisos, ni de credenciales. Es una decision de alcance y,
para F33.15/16, tambien una limitacion real del entorno Docker local en
esta maquina (ver seccion F33.15 arriba) que debe resolverse o
investigarse mas antes de correr regresiones masivas con confianza.

## Conclusion

**F33 no se declara COMPLETED.** Los criterios de exito de la mision
("componentes realmente compartidos consolidados" en plural, "testing
consolidado", "responsive validado", "accessibility validado")
genuinamente no se cumplen todavia. Lo que SI esta completo y verificado
con evidencia real (no solo documentado): inventario, clasificacion,
contrato, la consolidacion tecnica de Offcanvas (el hallazgo de mayor
severidad) extendida a las 6 apps con violaciones reales, 4 primitivas
UI nuevas todas con al menos 1 adopcion real verificada (Card KPI, Empty
State, Loading State, Filter Bar), 1 auditoria de Badges que confirma
con evidencia por que no crear una 5a primitiva sin decision de diseno,
6+ archivos de codigo muerto eliminados con evidencia, coleccion de
tests establecida en 2064/0 errores, y cada batch de codigo validado
individualmente con `manage.py check` + governance + E2E 29/29. F33.17
(accesibilidad de componentes modificados) tiene una primera pasada
real ejecutada con 3 hallazgos corregidos.

**Siguiente paso recomendado:** retomar F33.15 resolviendo primero el
hallazgo de causa raiz documentado arriba (aislar
`ConsoleAPIConsumptionTests` en un entorno Docker sano), luego F33.16
(E2E baseline limpio como cierre formal, no solo re-uso de corridas de
batch), completar F33.17 (contraste real, navegacion por teclado
end-to-end, tablas django-tables2 -- no cubierto en la primera pasada),
y F33.18-19 (responsive, performance -- auditorias reales, no listas de
verificacion superficiales).
