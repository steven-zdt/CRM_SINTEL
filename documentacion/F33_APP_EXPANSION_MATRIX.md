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

**Total: 13 archivos, 6 apps** (perfil, compras, gastos, facturas,
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
  ejercita `cuenta_list.js` (uno de los 13 archivos editados) en un flujo
  real crear→editar→eliminar con navegador. El único fallo
  (`40-tenant-edit.spec.js`) es **ambiental, no una regresión**: apunta a
  `sintel.net.co` (consola pública), un host distinto de
  `qaisotest.sintel.net.co` -- el único mapeado en este contenedor efímero
  -- y ejercita gestión de tenants en la consola pública, código no tocado
  por este batch (ninguno de los 13 archivos editados pertenece a
  `apps/public/`). Clasificación: `FALSE_POSITIVE` / `ENVIRONMENTAL`, no
  `REGRESSION`.
- Los 13 archivos se releyeron completos tras cada edición para confirmar
  estructura de llaves intacta (sin `node --check` disponible en este
  entorno, mismo entorno reportado en F31.2).

## Batches pendientes (NO ejecutados en esta pasada — con evidencia, no omisión)

| # | Alcance | Apps afectadas | Por qué no en este batch |
|---|---|---|---|
| 2 | OBSOLETE: modals muertos `confirmarEliminarModal` | compras, gastos | Requiere confirmar 0 referencias JS por archivo antes de borrar (regla F33.24) — no ejecutado aún en esta sesión |
| 3 | OBSOLETE: 2 prototipos Tailwind huérfanos | dashboard, contabilidad, empresa, facturas, perfil (`core/static/tenant/core/*/index.html`) | Mismo motivo — pendiente de confirmar 0 referencias |
| 4 | `ModalService` (`core/js/helpers/modal-service.js`) | global (cargado en `assets_core.html`) | 0 consumidores reales confirmados por grep (solo se referencia a sí mismo + 1 doc archivado), pero es infraestructura cargada globalmente — mayor blast radius que Offcanvas, requiere su propio ciclo de verificación antes de eliminar |
| 5 | Confirmaciones nativas → `UIManager.confirm()` | ~12 apps, ~30 sitios | Escala comparable a F32.7 (46 archivos) — expansión masiva explícitamente prohibida en una sola operación. Requiere su propio batch app-por-app |
| 6 | Card KPI → `sintel_kpi_card` | clientes, gastos, proyectos, cotizaciones, facturas, ventas (7 sitios) | Primitiva ya existe (F33.6-9) pero adopción = 0 verificado. Cambio visual, requiere spot-check en navegador por app, no solo grep |
| 7 | Empty state hand-rolled → `empty_state.html` | clientes, bancos, facturas, proveedores (6 sitios) | Igual — primitiva existe, adopción pendiente |
| 8 | Badges de estado (17 métodos, 7 apps) | inventario, clientes, contabilidad, gastos, ventas, empresa | Mayor divergencia visual real, requiere decisión de wording unificado antes de tocar código (no solo consolidación mecánica) |
| 9 | Filtro/búsqueda wrapper → `filter_bar.html` | bancos, compras, gastos, proveedores, clientes, facturas, ventas, cotizaciones | Cambio visual en 8 apps, requiere spot-check navegador |
| 10 | `routes.js`/`crud.js` (`core/js/helpers/`) | global | Investigado en este batch: **NO están muertos** — `routes.js` tiene un consumidor real y guardado (`inventario.api.js:getApiBase()`, con fallback si no está disponible). Fuera del alcance de F33 (Shared UI) — es capa de datos ("Aislamiento Gradual"), no UI. Se deja documentado, no se toca. |

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
