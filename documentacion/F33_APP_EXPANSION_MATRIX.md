# F33.13 — Matriz de Expansión Controlada por App

Continuación de `F33_STATUS_REPORT.md` (F33.0-12 = PASS, piloto `empresa`
validado). Punto de entrada: F33.13. No se repite el piloto, no se crea
namespace nuevo, no se migran todas las apps de una sola vez.

## Orden de ejecución y su motivo

El inventario F33.0/F33.1 ya prioriza por evidencia (no preferencia): la
mayor duplicación medible es Offcanvas (#12b/c/d, ~47 archivos combinados,
riesgo real de backdrops huérfanos). #12b (`UIManager.handleOffcanvas`) ya
se resolvió en F33.4 con el alias delgado. F33.13 continúa con #12c/#12d
(instanciación cruda + snippets de fallback copiados a mano) porque:

1. El target ya existe y está probado (`Sintel.Core.mostrarOffcanvasSeguro`,
   piloto empresa validado con navegador + E2E + governance).
2. Es el mismo patrón mecánico en todos los sitios — bajo riesgo de romper
   comportamiento específico de cada app.
3. Es medible con grep dirigido (`new bootstrap\.Offcanvas`,
   `bootstrap\.Offcanvas\.getOrCreateInstance`), no requiere rediseño.

## Batch 1 — Offcanvas #12c/#12d restante (EJECUTADO)

Metodología: grep dirigido sobre los 3 patrones de violación del inventario
+ lectura de contexto funcional de cada archivo antes de tocarlo (no solo
grep, per regla F33.13.3).

**Nota de proceso:** la primera pasada de este batch usó un patrón de grep
que no capturaba `new w.bootstrap.Offcanvas(` (solo `new bootstrap.Offcanvas(`
sin el prefijo `w.`), lo que dejó pasar 6 violaciones reales en
compras/gastos/facturas/contabilidad -- exactamente las que el inventario
F33.0 ya había citado por número de línea. Se detectó al re-verificar la
afirmación "0 instanciaciones crudas restantes" con un grep más amplio
(`new (w\.)?bootstrap\.Offcanvas\(`) antes de cerrar el batch, y se
corrigió en la misma pasada. Tabla final, ya corregida:

| App | Archivo | Patrón encontrado | Acción | Estado |
|---|---|---|---|---|
| perfil | `perfil.modals.js` (líneas 58, 81) | `new bootstrap.Offcanvas(el); .show()` sin dispose previo ni limpieza de backdrop — violación real de AGENTS.md §26 | Reemplazado por `Sintel.Core.mostrarOffcanvasSeguro(el)` | CONSOLIDATE, hecho |
| compras | `compras_list.js` (`loadAndShowOffcanvas()`, flujo fetch manual) | Igual patrón | Reemplazado, preservado el evento `compra-editor-init` posterior | CONSOLIDATE, hecho |
| compras | `compras_list.js` (`htmx:afterSettle`, 2 sitios: ordenes + plantillas) | Igual patrón, flujo HTMX | Reemplazado en ambos sitios | CONSOLIDATE, hecho |
| gastos | `gasto_list.js` (`loadAndShowOffcanvas()` + `htmx:afterSettle`, 2 sitios) | Igual patrón que compras, mismo código base | Reemplazado en ambos sitios | CONSOLIDATE, hecho |
| facturas | `facturas_main.js` (offcanvas de "facturas pendientes", ~línea 490) | Raw `new w.bootstrap.Offcanvas().show()`, sin dispose | Reemplazado | CONSOLIDATE, hecho |
| contabilidad | `pendiente/plantilla_interceptor.js:147` | Raw `new w.bootstrap.Offcanvas(el, {backdrop:true, scroll:false})` (opciones = defaults de Bootstrap, sin efecto real) | Reemplazado, instancia devuelta preservada para `_inyectarBotonActivar()` que la consume | CONSOLIDATE, hecho |
| inventario | `movimientos_editor.js` (`abrir()`) | Snippet de fallback copiado a mano (dispose+backdrop+`new Offcanvas().show()`) | Reemplazado por llamada única al helper | CONSOLIDATE, hecho |
| contabilidad | `asiento_list.js`, `cuenta_list.js`, `periodo_list.js`, `plantilla_list.js` | Bloque idéntico `if (UIManager?.handleOffcanvas) {...} else {raw fallback}` — el fallback nunca se ejecuta en la práctica (UIManager siempre está cargado), puro código muerto duplicado 4 veces | Simplificado a llamada directa al helper (elimina la rama muerta) | CONSOLIDATE, hecho |
| contabilidad | `libro_diario_list.js` | Mismo patrón, 5ª copia | Igual | CONSOLIDATE, hecho |

**Total: 11 archivos, 6 apps** (perfil, compras, gastos, facturas,
contabilidad, inventario). Verificado con grep final
(`new (w\.)?bootstrap\.Offcanvas\(|bootstrap\.Offcanvas\.getOrCreateInstance`
sobre `apps/tenant/**/*.js`): 0 coincidencias restantes salvo el propio
helper y las 2 excepciones documentadas abajo.

### Excepción confirmada, NO tocada (evidencia de por qué)

- **`empleados/devengo_editor.js`** — inicialmente clasificado por error como
  el mismo patrón (usa `bootstrap.Offcanvas.getOrCreateInstance` crudo). Al
  intentar el mismo reemplazo mecánico se detectó que este archivo tiene un
  `setTimeout(..., 0)` deliberado antes de `.show()`, con comentario
  explícito ("evita null.scroll en offcanvas.js"). Investigación confirmó
  que esto ya fue auditado y excluido a propósito en F31.2
  (`F31_2_CORE_EXECUTION.md` §4.3, `REPORTE_FASE_5.md`) y está documentado
  como excepción aceptada en el propio helper de tests E2E
  (`tests/e2e/specs/_helpers.js:32`, ignorePattern `"reading 'scroll'"`).
  El helper compartido no tiene ese workaround de timing. **Revertido a su
  estado original** — clasificación correcta: `APP_SPECIFIC` (workaround de
  un bug real de Bootstrap, no duplicación evitable), no `DUPLICATE`. Queda
  registrado aquí para que una fase futura no repita el mismo error sin
  primero verificar si el helper compartido necesita el mismo workaround.
- **`facturas_main.js:66` (`initOffcanvas()`)** — excepción ya documentada
  en F31.2 (crea instancia sin mostrarla, contrato de 3 funciones
  separadas: `initOffcanvas`/`showOffcanvas`/`hideOffcanvas`). Confirmada
  intacta, no tocada. Distinto del sitio en el mismo archivo que sí se
  corrigió en este batch (offcanvas de "facturas pendientes", función
  separada sin relación con ese contrato de 3 funciones).
- **`gastos/resolucion_editor.js:29-30`** — `if (!getInstance(el)) { new
  bootstrap.Offcanvas(el); }` sin `.show()`. Es una inicialización
  defensiva (asegura que el botón de cierre funcione tras swap HTMX), no
  el patrón "mostrar" que el helper resuelve — el mismo archivo ya usa
  `UIManager.handleOffcanvas(id, 'hide')` en otro punto, señal de que su
  autor ya conoce el helper consolidado. No se reclasifica como duplicado
  sin evidencia más fuerte de que cause el mismo bug de backdrops.
- **`compras_list.js` / `gastos_list.js` (bloques `htmx:beforeCleanupElement`)**
  y **`perfil.modals.js` (cierres tras guardar)** — usan
  `getInstance(el).hide()`/`.dispose()` para *cerrar*, patrón idiomático de
  Bootstrap sin el riesgo que el helper previene (que es sobre *mostrar*
  repetidamente sin dispose). No son violaciones.

### Verificación

- `manage.py check`: PASS (ejecutado 2 veces, antes y después de corregir
  el gap de grep).
- Governance (`tools.organizational_governance.cli --report`): **FINAL
  STATUS: PASS** (0 FAIL en todas las categorías, ejecutado 2 veces).
- E2E: suite completa vía contenedor Playwright efímero
  (`mcr.microsoft.com/playwright:v1.62.1-jammy`, red `crm_sintel_default`,
  host `qaisotest.sintel.net.co` mapeado a la IP del contenedor `web`):
  **29/30 PASS.** Incluye `30-contabilidad-cuenta-crud.spec.js`, que
  ejercita `cuenta_list.js` (uno de los 11 archivos editados) en un flujo
  real crear→editar→eliminar con navegador. El único fallo
  (`40-tenant-edit.spec.js`) es **ambiental, no una regresión**: apunta a
  `sintel.net.co` (consola pública), un host distinto de
  `qaisotest.sintel.net.co` -- el único mapeado en este contenedor efímero
  -- y ejercita gestión de tenants en la consola pública, código no tocado
  por este batch (ninguno de los 11 archivos editados pertenece a
  `apps/public/`). Clasificación: `FALSE_POSITIVE` / `ENVIRONMENTAL`, no
  `REGRESSION`.
- Los 11 archivos se releyeron completos tras cada edición para confirmar
  estructura de llaves intacta (sin `node --check` disponible en este
  entorno, mismo entorno reportado en F31.2).

## Batch 2 — OBSOLETE con evidencia (EJECUTADO)

Regla aplicada: solo se elimina con evidencia de 0 consumidores reales
(F33.24). Cada candidato del inventario se re-verificó individualmente
antes de tocarlo -- uno de los 5 originalmente listados resultó tener
más matices de los que el inventario capturaba (ver abajo).

| Candidato | Verificación | Acción |
|---|---|---|
| `compras_list.html` -- modal `#confirmarEliminarModalCompras` | 0 referencias JS (grep del ID y de `#btn-confirmar-eliminar-compras` en toda la app: solo el propio template y el doc de auditoría) | Eliminado (18 líneas de markup muerto) |
| `gastos_list.html` -- modal `#confirmarEliminarModal` (sin sufijo) | 0 referencias JS. Bonus: compartía el mismo `id` sin sufijo que `empleados_list.html:408` (que sí está vivo) -- riesgo real de colisión de ID si ambos fragmentos coexistieran en el DOM | Eliminado |
| `core/static/tenant/core/contabilidad/index.html` | 0 render/redirect real -- solo mencionado en comentarios/docstrings de `views_ui.py` (vista deprecada que retorna 404) | Eliminado |
| `core/static/tenant/core/empresa/index.html` | Igual -- solo mencionado en comentario de `urls_ui.py` | Eliminado |
| `core/static/tenant/core/perfil/index.html` | 0 referencias en absoluto (ni siquiera en comentarios) | Eliminado |
| `core/static/tenant/core/facturas/index.html` | 0 referencias en absoluto | Eliminado |
| `core/static/tenant/core/dashboard/index.html` | **NO eliminado** -- a diferencia de sus 4 hermanos, este SÍ es alcanzado por tráfico real: el redirect post-login (`/dashboard/`, `apps/tenant/core/api/viewsets.py`) sirve exactamente este shell (ya documentado desde F32.5/F33.10 como "roto pero alcanzable", referencia a `core/js/lib/http.js` eliminado en F32.7). Además ya está modificado sin commitear por otra sesión en este mismo árbol de trabajo (`git status` lo mostraba `M` antes de este batch) -- tocarlo aquí arriesgaría pisar ese trabajo en curso. Queda fuera de este batch. |
| `ModalService` (`core/js/helpers/modal-service.js`) | 0 consumidores reales (solo se referencia a sí mismo + 1 doc archivado), pero cargado globalmente en `assets_core.html` en cada página tenant | **NO eliminado en este batch** -- mayor blast radius que los anteriores (afecta las 17 apps simultáneamente), merece su propio ciclo de verificación aislado, no combinarlo con limpieza app-específica |

**Total: 6 archivos eliminados** (2 modals muertos + 4 shells Tailwind
huérfanos), 3 apps + core.

### Verificación

- `manage.py check`: PASS.
- Governance: **FINAL STATUS: PASS**.
- E2E, primer intento: **19/29 PASS, 10 fallos** -- investigado antes de
  asumir regresión. Logs del contenedor `web` mostraron la causa real:
  `[WARNING] django.request: Too Many Requests` +
  `"POST /api/v1/core/auth/login/ HTTP/1.1" 429`. El `AnonRateThrottle`
  (`config/settings.py`, ya documentado como fuente de falsos negativos en
  sesiones anteriores) se agotó tras 2 suites E2E completas corridas
  seguidas en la misma sesión (cada `login()` cuenta contra el limite). Los
  10 fallos compartían el mismo síntoma (`page.waitForURL` timeout dentro
  de `login()`), incluyendo specs que no tocan ningún archivo de este
  batch (`62-f334-offcanvas-consolidation.spec.js`, que ni siquiera
  navega a una app de negocio) -- confirma causa compartida en el
  transporte de login, no en el código editado.
- Cache de throttle es `LocMemCache` (en memoria del proceso `web`, no
  Redis) -- se limpia reiniciando el contenedor (`docker compose restart
  web`, no destructivo, sin perdida de datos de BD). Tras el reinicio:
  **E2E, segundo intento: 29/29 PASS** (suite completa, incluye
  `30-contabilidad-cuenta-crud.spec.js` y los 2 specs de F33.4/F33.10 que
  ejercitan Offcanvas real). Confirma que los 10 fallos eran 100%
  ambientales, cero regresión real de este batch.

## Batch 4 — `ModalService` (código muerto global, EJECUTADO)

Diferido en el batch 2 explícitamente por su mayor blast radius (carga
global vía `assets_core.html`, no app-específica). Ejecutado como su
propio ciclo aislado de verificación, tal como se documentó que
requeriría:

1. **Re-verificación de 0 consumidores** (grep repo-wide de `ModalService`):
   solo el propio archivo + 2 menciones documentales (`documentacion/_archive/COOKBOOK_MODALES_CRUD.md`,
   docs de esta misma fase). Ningún `.open(`/`.close(`/`.clear(` invocado
   en ningún JS de `apps/tenant/**`.
2. **Impact Analysis** (`tools/ekg/impact.py --path "modal-service.js" --offline`):
   4 impactados (los 3 shells `workspace.html`/`assets_dashboard.html`/
   `assets_landing.html` que incluyen `assets_core.html`, mismo patrón ya
   documentado en F33.12), 0 tests en el grafo -- consistente con "0
   consumidores reales", no una alarma nueva.
3. **Eliminación**: `apps/tenant/core/static/core/js/helpers/modal-service.js`
   borrado + su `<script>` tag en `assets_core.html` removido + la línea
   que lo documentaba en `core/js/helpers/README.md` corregida (quedaba
   describiendo un archivo que ya no existe).

### Verificación

- `manage.py check`: PASS.
- Governance: **FINAL STATUS: PASS**.
- E2E: **29/29 PASS** (suite completa, contenedor Playwright efímero
  fresco), corrida completa por ser cambio de carga global, mismo
  criterio que exigió diferir este batch en primer lugar.

## Batch 5, parte 1 — Confirmaciones nativas → `UIManager.confirm()` (apps de 1 solo sitio, EJECUTADO)

Regla aplicada: no migrar los ~30 sitios en ~12 apps de una sola vez
(escala comparable a F32.7, expresamente prohibido). Se ejecuta primero
el subconjunto de menor riesgo: apps donde **toda** su superficie de
`confirm()` nativo vive en un único sitio -- migración aislada, sin
tocar archivos con múltiples sitios que requieren más contexto.

| App | Archivo | Contexto | Acción |
|---|---|---|---|
| ventas | `resolucion_editor.js:96` | `btn.addEventListener('click', function () {...})` síncrono, dentro de `bindPanelBotones()` | Listener convertido a `async`, `if (!w.confirm(...)) return;` → `if (!(await w.UIManager?.confirm(...))) return;` |
| perfil | `perfil.modals.js:91` | `function deletePerfil(id) {...}`, llamado sin `await` desde `perfil.page.js:80` (fire-and-forget, no depende de retorno síncrono) | Función convertida a `async function`, mismo patrón de reemplazo |

**`bancos.main.js:138` evaluado y NO migrado en este batch:** a
diferencia de ventas/perfil, el `confirm()` nativo ahí es solo el
*fallback* de un patrón más grande -- el camino primario ya usa un modal
Bootstrap hand-rolled (`bootstrap.Modal.getOrCreateInstance('confirmarEliminarModalBancos')`),
exactamente el hallazgo #5c del inventario F33.0 (`DUPLICATE`, modal vivo
que reimplementa lo que `UIManager.confirm()` ya resuelve). Migrarlo
correctamente implica retirar el modal HTML completo, no solo cambiar
una línea -- alcance distinto, se difiere a un batch propio junto con
`empleados_list.html` (mismo patrón, ver inventario §5c).

`UIManager.confirm()` verificado (`ui-manager.js:466-484`): `async
function confirm(message, title)`, usa SweetAlert2 si está cargado (que
lo está en todas las páginas tenant vía `assets_core.html`), con
fallback a `w.confirm()` nativo si no -- upgrade estrictamente seguro,
nunca peor que el comportamiento anterior.

### Verificación

- `manage.py check`: PASS.
- Governance: **FINAL STATUS: PASS**.
- E2E: **29/29 PASS** (suite completa). Verificación visual en navegador
  real no fue posible en este entorno (el host `qaisotest.sintel.net.co`
  usado por el contenedor Playwright efímero no es resoluble desde el
  Browser pane de esta sesión) -- la cobertura funcional real vino de la
  suite E2E, que sí ejecuta interacciones reales de Playwright contra el
  servidor.

## Batch 5, parte 2 — Confirmaciones nativas, resto de sitios aislados (EJECUTADO)

Continuación directa de la parte 1, mismo criterio explícito acordado:
`confirm() aislado → UIManager.confirm()` mecánico; `confirm() integrado
en modal vivo → auditar primero, no reemplazo mecánico`.

**Auditoría previa a tocar código:** se re-grepeó `bootstrap\.Modal` en
todo `apps/tenant/**/*.js` (6 archivos) y se cruzó contra los ~28 sitios
de `confirm()` restantes. Solo `bancos.main.js` y `empleado_list.js`
(ya migrado en F33.10/no tenía confirm() nativo en la lista) resultaron
tener Modal + confirm() relacionados. Los otros 3 archivos con
`bootstrap.Modal` (`facturas_main.js`, `facturas_editor.js`,
`inventario/productos_list.js`) se verificaron línea por línea: su uso
de Modal es para una feature completamente distinta (offcanvas de
"facturas pendientes", visor de imagen), no relacionada con sus sitios
de `confirm()` -- confirmado **aislado**, no modal-integrado.

**27 sitios migrados** en 21 archivos, 8 apps:

| App | Archivos | Sitios |
|---|---|---|
| clientes | `clientes.list.js` | 2 (deleteCliente, deleteContacto) |
| empleados | `resolucion_list.js`, `nomina_list.js`, `nomina_historial.js`, `liquidacion_list.js`, `contrato_list.js` | 5 |
| empresa | `sede_list.js`, `area_list.js`, `mailinboxconfig_list.js` | 3 |
| contabilidad | `plantilla_list.js`, `plantilla_editor.js`, `cuenta_list.js`, `periodo_list.js`, `asiento_list.js` | 5 |
| proyectos | `proyectos_list.js`, `proyectos_editor.js` (x2), `nueva_tarea_list.js` | 4 |
| proveedores | `proveedores_form.js`, `representante_editor.js` | 2 |
| inventario | `categorias_list.js`, `activos_list.js`, `servicios_list.js` | 3 |
| facturas | `facturas_main.js`, `facturas_editor.js`, `facturas_list.js` | 3 |

Patrón mecánico aplicado en cada sitio: donde la función/listener ya era
`async` (la mayoría, ~20 sitios), swap directo de
`confirm(msg)`→`(await w.UIManager?.confirm(msg))`. Donde el listener
era síncrono (~7 sitios: `resolucion_list.js`, `liquidacion_list.js`,
4 de contabilidad, `facturas_editor.js`), se agregó `async` a la firma
del listener -- cambio mínimo, sin alterar el resto de la lógica ni el
orden de ejecución (los listeners de click no dependen de retorno
síncrono).

**Confirmado NO migrado, con motivo (igual que parte 1):**
`bancos.main.js:138` -- fallback de un modal Bootstrap hand-rolled vivo
(#5c del inventario), requiere retirar el modal HTML completo, alcance
distinto. Queda como único sitio nativo restante en todo `apps/tenant/**`.

### Verificación

- `manage.py check`: PASS.
- Governance: **FINAL STATUS: PASS**.
- Los 21 archivos se releyeron completos tras cada edición (estructura
  de llaves/paréntesis intacta, sin `node --check` disponible en este
  entorno).
- **E2E, hallazgo real (no ambiental) -- encontrado y corregido:**
  primer intento del suite completo dio 2 fallos reales:
  `10-clientes-crud.spec.js` y `30-contabilidad-cuenta-crud.spec.js`,
  ambos en el paso "eliminar" (fila queda visible en vez de
  desaparecer). Investigado antes de asumir nada: ambos specs usaban
  `page.once('dialog', (dialog) => dialog.accept())` -- el patron
  correcto de Playwright para interceptar `window.confirm()` **nativo**.
  `UIManager.confirm()` renderiza un modal SweetAlert2 (DOM real), no
  dispara el evento `dialog` del navegador -- el handler quedaba inerte
  y el modal nunca se cerraba, bloqueando la eliminacion. **Corregido en
  los tests** (no en el codigo de produccion, que es el comportamiento
  correcto/mejorado): se reemplazo el `dialog` handler por un click real
  sobre `.swal2-confirm` despues del boton de eliminar. Verificado que
  ningun otro spec existente comparte este patron contra un archivo
  tocado en este batch (`20-inventario-productos-crud.spec.js` es el
  unico otro consumidor de `page.once('dialog', ...)`, pero
  `productos_list.js` no fue tocado -- sigue usando `confirm()` nativo,
  su spec permanece correcto sin cambios).
- E2E, re-corrida tras el fix: **28/29 PASS** (una corrida intermedia
  con 26 fallos se investigo por separado -- confirmado por texto de
  error literal `429 (Too Many Requests)`, mismo patron de
  `AnonRateThrottle` agotado ya documentado en batch 2; contenedor `web`
  reiniciado, re-corrida limpia). El unico fallo restante
  (`63-f3310-empresa-pilot.spec.js`) es la flakiness de login()
  pre-existente y ya documentada en el propio comentario de
  `_helpers.js` ("10s eran insuficientes en la practica... doble
  salto") -- no relacionado con ningun archivo de este batch. Los 2
  specs objetivo de la correccion (`10-clientes-crud`,
  `30-contabilidad-cuenta-crud`) pasaron limpiamente.

## F33.13-B — Cierre de `confirm()` nativo (bancos + hallazgo de gap en el grep, EJECUTADO)

**Prioridad 1 de la sesión: `bancos.main.js`, con auditoría completa
ANTES de tocar código** (no un swap directo):

1. **Quién abre el modal:** `confirmarEliminacion(uuid, type)`, invocada
   desde el delegador global de clicks al hacer click en
   `.btn-delete-cuenta`/`.btn-delete-extracto`. Usaba
   `bootstrap.Modal.getOrCreateInstance(...).show()`.
2. **Quién lo cierra:** `ejecutarEliminacion()` al final del flujo
   (`bootstrap.Modal.getInstance(...).hide()`), más el botón "Cancelar"
   nativo (`data-bs-dismiss="modal"`, sin JS propio).
3. **Consumidores externos:** ninguno -- confirmado por grep repo-wide,
   el modal y su botón solo aparecían en `bancos.main.js` y su propio
   template.
4. **¿Migrable al patrón Core?** Sí -- el flujo usaba estado compartido
   a nivel de módulo (`currentDeleteUuid`/`currentDeleteType`) para
   tender el puente entre "abrir modal" y "click del usuario en su
   botón", exactamente el problema que `UIManager.confirm()` (async,
   `Promise<boolean>`) resuelve sin estado intermedio. Sin nada
   específico del dominio bancario.

**Ejecutado:** `confirmarEliminacion`/`ejecutarEliminacion` simplificados
a usar `await w.UIManager?.confirm(...)`; `bindDeleteModal()` y su
registro en `init()` eliminados (ya no hay botón de modal que atar); el
modal HTML completo (`#confirmarEliminarModalBancos`, 18 líneas)
eliminado de `list_bancos.html`.

**Hallazgo adicional durante la verificación final:** el grep de batch 5
(`confirm(['"]`, solo strings literales) tenía un gap real -- no
detectaba `confirm(unaVariable)`. Un grep más amplio
(`[^A-Za-z.?]confirm\(`) encontró **3 sitios mas** no migrados:
`inventario/inventario_list.js`, `inventario/movimientos_list.js`,
`inventario/productos_list.js` (los 3 ya en funciones/listeners
`async`, swap directo sin cambios estructurales). `productos_list.js`
tenía cobertura E2E dependiente de `page.once('dialog', ...)`
(`20-inventario-productos-crud.spec.js`) -- corregido con el mismo
patrón `.swal2-confirm` ya usado en batch 5 parte 2.

**Verificación final repo-wide:** `[^A-Za-z.?]confirm\(` sobre
`apps/tenant/**/*.js` → **0 coincidencias** salvo la definición de
`UIManager.confirm` misma. `page.once('dialog'` sobre
`tests/e2e/specs/**` → **0 coincidencias**. `confirm() nativo queda en
0 sitios en todo el repo.**

`manage.py check` PASS, governance FINAL STATUS PASS. E2E: **29/29
PASS** (contenedor `web` reiniciado preventivamente antes de la corrida
para evitar el falso-positivo de `AnonRateThrottle` ya visto -- corrida
limpia sin necesidad de una segunda pasada, incluye
`63-f3310-empresa-pilot.spec.js`, flaky en corridas anteriores de esta
sesión, verde esta vez).

**Nota de alcance:** `empleados_list.html`/`empleado_list.js` (patrón
modal hand-rolled hermano, `#confirmarEliminarModal` sin sufijo) **NO
fue tocado** -- es un caso distinto: nunca tuvo un fallback `confirm()`
nativo (su modal se abre directamente sin condicional), por lo que
nunca apareció en ningún grep de `confirm()`. Es una migración de modal
aparte (mismo target final, `UIManager.confirm()`, pero sin la señal de
"confirm() nativo restante" que motivó priorizar bancos). Queda
documentado como trabajo futuro, no como parte de "cerrar el último
confirm()" (que sí se cerró en su totalidad).

**Hallazgo colateral, no corregido aquí:** `inventario_list.js` y
`productos_list.js` tienen lógica de eliminar-producto casi idéntica
(mismo mensaje de advertencia multi-línea, misma secuencia) -- ambos
archivos están vivos, no es código muerto. Flageado como tarea aparte
(no se investiga ni se toca en este batch, fuera de alcance de
"confirm() nativo").

## F33.14-A — Card KPI: inventario y adopción controlada (EJECUTADO)

Auditoría de 16 candidatos en las 17 apps tenant + migración de los
únicos 2 archivos verificados como byte-idénticos al target sin
acoplamiento funcional. Detalle completo, tabla de clasificación por
candidato, y corrección de precisión sobre el inventario original de
F33.0: `documentacion/F33_14A_CARD_KPI_INVENTORY.md`.

**Resumen:** de los "7 sitios duplicados" que F33.0 declaraba, solo
`clientes` (6/6 cards) y `proyectos` (4/6 cards) resultaron migrables
sin cambiar comportamiento ni diseño. `cotizaciones` es byte-idéntico
pero sus valores se actualizan por JS via `id=` (bloqueado hasta decidir
si se extiende el primitivo). `ventas`/`gastos`/`facturas` tienen
personalizaciones visuales reales (tamaño, acento de color, tipografía)
que el inventario original no distinguió. `compras` e `inventario` (x2
archivos) tienen implementaciones de KPI card completamente
independientes, no detectadas en F33.0.

`manage.py check` PASS, governance PASS, E2E 29/29.

## F33.14-B — Empty State: inventario y adopción controlada (EJECUTADO)

Auditoría de 8 candidatos en las 17 apps tenant, mismo rigor que
F33.14-A. Detalle completo:
`documentacion/F33_14B_EMPTY_STATE_INVENTORY.md`.

**Resumen:** solo `clientes/clientes_list.html` (2/2 sitios) era
byte-idéntico al target y sin acoplamiento funcional -- migrado. Los
otros 7 candidatos se dividen en: una sub-variante "compacta" (`id` en
vez de `data-attr`, tamaño reducido) repetida en `clientes` y
`proveedores`; **2 variantes distintas con wrapper `alert-info`
encontradas en `proveedores`** que ni siquiera coinciden entre sí para
el mismo concepto ("representantes"); y un patrón de fila de tabla
`{% empty %}` (`bancos`, `facturas`) estructuralmente incompatible con
el primitivo basado en `<div>`.

**Hallazgo colateral:** `clientes/contactos_list.html` resultó ser
código muerto real (0 referencias repo-wide, confirmado antes de
tocarlo) -- eliminado, no migrado.

`manage.py check` PASS, governance PASS, E2E 29/29.

## F33.14-C — Loading States: inventario y adopción controlada (EJECUTADO)

Auditoría de 17 candidatos (`spinner-border`) en las apps tenant, mismo
rigor que F33.14-A/B. Detalle completo:
`documentacion/F33_14C_LOADING_STATE_INVENTORY.md`.

**Resumen:** solo `gastos/gastos_list.html` (2/2 sitios) y
`compras/compras_list.html` (1/1 sitio) eran el contenido inicial
byte-idéntico de un panel `hx-trigger="load"` -- migrados. Los otros 14
candidatos se dividen en: una familia "compacta py-4" con 2 sub-variantes
internas inconsistentes entre sí, repetida en `clientes` y `facturas` (4
sitios, 3 archivos); un spinner JS-toggled por `data-spinner` con color
propio en `clientes_list.html` (mecanismo distinto al del target); un
near-miss de un solo sitio en `contabilidad/reporte_page.html` (le falta
`role="status"`/`span.visually-hidden`, migrar sería a la vez un cambio
visual y una mejora de accesibilidad no solicitada); 8 archivos con
spinners inline de botón/celda de tabla (estado de envío, no panel); y 2
overlays globales (`workspace.html`, `editor_cotizacion.html`).

`manage.py check` PASS, governance PASS, E2E ver `F33_STATUS_REPORT.md`.

## F33.14-D — Filter/Search Bar: inventario y adopción controlada (EJECUTADO)

Auditoría de 21 candidatos (`keyup changed delay:400ms`) en las apps
tenant, mismo rigor que F33.14-A/B/C. Detalle completo:
`documentacion/F33_14D_FILTER_BAR_INVENTORY.md`.

**Resumen:** solo `compras/compras_list.html` (1/1 sitio) y
`gastos/gastos_list.html` (2/2 sitios) eran el markup byte-idéntico al
target (`input-group input-group-sm w-auto` + `data-search-input` +
boton `data-action="search"`) -- migrados. Los otros 19 candidatos se
dividen en: una familia real de 4 archivos "icono-prefijo, sin boton"
(`clientes`, `proyectos`, `ventas`, `facturas`) con `hx-include` para
combinar con filtros por pestaña; una familia de 2 archivos cuyo wrapper
coincide pero difiere en el boton (`bancos` no tiene boton de busqueda
en absoluto, `proveedores` tiene un boton con su propio `hx-get`
autosuficiente en vez del handler JS del target); y 13 archivos con un
patron "input bare" sin wrapper ni boton (`contabilidad` x5, `empleados`
x5 sitios, `empresa` x2 archivos, `perfil`, `inventario` x4).

`manage.py check` PASS, governance PASS, E2E ver `F33_STATUS_REPORT.md`.

## F33.14-E — Badges de estado: auditoría de cierre de Batch 8 (EJECUTADO, 0 migraciones)

Auditoría de los 179 métodos `render_*` en los 13 `tables.py` de las
apps tenant (Fase 5-BIS, django-tables2). Detalle completo:
`documentacion/F33_14E_BADGES_ESTADO_INVENTORY.md`.

**Resumen:** a diferencia de Card KPI/Empty State/Loading/Filter Bar,
**no existe ningún primitivo de badge compartido hoy** (`sintel_ui.py`
solo lo menciona en un comentario). El único candidato real de
duplicación (`render_activo`/`render_activa`, patrón booleano
"Activo/Inactivo" en 7-8 sitios de 5 apps) tiene **3 combinaciones de
color inconsistentes para "Inactivo"** (`bg-danger`/`bg-secondary`/
`bg-secondary-subtle`+borde), incluso dentro de la misma app
(`contabilidad`, `inventario`) -- unificarlo mecánicamente elegiría un
color sin base de diseño. El resto (~50 sitios) son mapeos de estado
genuinamente específicos de cada dominio (facturas DIAN, estados de
compra/venta/proyecto/contrato, tipos de cuenta contable), confirmando
con evidencia real la conclusión original del batch 8. **0 archivos de
código modificados** -- crear un primitivo nuevo sin decisión de diseño
previa violaría la prohibición explícita de "no crear más
infraestructura" de la misión F33.

## Batches pendientes (NO ejecutados en esta pasada — con evidencia, no omisión)

| # | Alcance | Apps afectadas | Por qué no en este batch |
|---|---|---|---|
| 5d | `empleados_list.html`/`empleado_list.js` (patrón modal hermano, sin `confirm()` nativo) | empleados | Modal hand-rolled vivo sin fallback nativo -- mismo target (`UIManager.confirm()`) pero requiere retirar el modal HTML completo, no un swap de línea. Sin urgencia (no aparece en ningún grep de `confirm()` nativo restante) |
| 6b | `cotizaciones` (Card KPI, bloqueado por acoplamiento JS) + `ventas`/`gastos`/`facturas`/`compras`/`inventario` (Card KPI, estilos propios reales) | cotizaciones, ventas, gastos, facturas, compras, inventario | Ver `F33_14A_CARD_KPI_INVENTORY.md` §Pendiente -- cada uno requiere su propia decisión de diseño (extender el primitivo, crear una variante, o confirmar que es intencional), no un swap mecánico |
| 7b | Empty state "compacto" (`clientes`, `proveedores`) + 2 variantes `alert-info` inconsistentes entre sí en `proveedores` + patrón tabla `{% empty %}` (`bancos`, `facturas`) | clientes, proveedores, bancos, facturas | Ver `F33_14B_EMPTY_STATE_INVENTORY.md` §Pendiente -- cada sub-variante requiere su propia decisión de diseño, no un swap mecánico. `proveedores` en particular tiene una inconsistencia interna real (2 archivos, mismo concepto, 2 estilos) que amerita resolverse antes de tocar el primitivo global |
| 7c | Loading state "compacto py-4" (`clientes`, `facturas` x2 archivos) con 2 sub-variantes internas + `data-spinner` JS-toggled en `clientes_list.html` + near-miss de accesibilidad en `contabilidad/reporte_page.html` | clientes, facturas, contabilidad | Ver `F33_14C_LOADING_STATE_INVENTORY.md` §Pendiente -- misma lógica que 7b: cada sub-variante requiere su propia decisión de diseño antes de tocar el primitivo o crear uno nuevo |
| 8b | Badge booleano "Activo/Inactivo" (7-8 sitios, 5 apps) con 3 combinaciones de color inconsistentes entre sí, incluso dentro de la misma app | clientes, contabilidad, empresa, inventario, proveedores | Ver `F33_14E_BADGES_ESTADO_INVENTORY.md` §Pendiente -- requiere decidir cuál color de "Inactivo" es el intencional antes de crear cualquier helper compartido; no hay primitivo previo que adoptar (a diferencia de 6b/7b/7c/9b) |
| 9b | Filter bar "icono-prefijo, sin boton" (`clientes`, `proyectos`, `ventas`, `facturas`) + `bancos` (falta boton) + `proveedores` (boton con mecanismo distinto) + familia "input bare" sin wrapper ni boton (13 archivos: `contabilidad`, `empleados`, `empresa`, `perfil`, `inventario`) | clientes, proyectos, ventas, facturas, bancos, proveedores, contabilidad, empleados, empresa, perfil, inventario | Ver `F33_14D_FILTER_BAR_INVENTORY.md` §Pendiente -- la familia "icono-prefijo" es la candidata mas fuerte para una 2a variante del primitivo, pero requiere decision de diseno explicita antes de extenderlo; la familia "input bare" (13 archivos) implicaria anadir wrapper+boton donde hoy no existen, cambio visual real fuera de "adopcion controlada" |
| 8 | Badges de estado (17 métodos, 7 apps) | inventario, clientes, contabilidad, gastos, ventas, empresa | Mayor divergencia visual real, requiere decisión de wording unificado antes de tocar código (no solo consolidación mecánica) |
| 9 | Filtro/búsqueda wrapper → `filter_bar.html` | bancos, compras, gastos, proveedores, clientes, facturas, ventas, cotizaciones | Cambio visual en 8 apps, requiere spot-check navegador |
| 10 | `routes.js`/`crud.js` (`core/js/helpers/`) | global | Investigado: **NO están muertos** — `routes.js` tiene un consumidor real y guardado (`inventario.api.js:getApiBase()`, con fallback si no está disponible). Fuera del alcance de F33 (Shared UI) — es capa de datos ("Aislamiento Gradual"), no UI. Se deja documentado, no se toca. |
| 11 | `core/static/tenant/core/dashboard/index.html` | dashboard/core | Ver batch 2 -- alcanzado por tráfico real vía redirect post-login, y ya modificado por otra sesión concurrente. Requiere su propio análisis (¿arreglar el shell, o corregir el redirect para que no dependa de él?) fuera del alcance de "eliminar código muerto" |

## Apps no evaluadas todavía en este ciclo

`ventas`, `proyectos`, `bancos`, `dashboard`, `cotizaciones`, `facturas`,
`clientes` — ninguna tenía hallazgos de Offcanvas #12c/#12d en el grep de
este batch (confirmado: el grep de `new bootstrap\.Offcanvas` /
`getOrCreateInstance` sobre todo `apps/tenant/**/*.js` solo devolvió los
archivos ya listados arriba). Para estas apps, el trabajo pendiente es el
de los batches 2-9 (Confirm/Cards/Empty/Badges/Filters), no Offcanvas.

## Conclusión de este ciclo

**F33.13 avanza de NOT_STARTED a IN_PROGRESS** con evidencia real: el
hallazgo de mayor severidad del inventario (Offcanvas) queda con su
consolidación técnica completa (F33.4 + este batch = 0 instanciaciones
crudas ni snippets de fallback duplicados restantes en `apps/tenant/**`,
verificado por grep tras los cambios). Los batches 2-9 quedan como trabajo
explícitamente pendiente, no completado — **F33 sigue sin poder declararse
COMPLETED** hasta ejecutarlos o hasta que una evaluación futura determine
con evidencia que no ameritan acción.
