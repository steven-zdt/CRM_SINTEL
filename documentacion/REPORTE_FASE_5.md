# REPORTE FASE 5 — Frontend (FE-A1..A9, FE-M1..M6)

**Fecha:** 2026-08-03
**Alcance:** Los 9 hallazgos ALTO (FE-A1..A9) y los 6 MEDIO (FE-M1..M6) de Frontend definidos en `PLAN_UNICO_CORRECCIONES.md` §"FASE 5". No se tocó Fase 6/7/8/9 ni se avanzó más la expansión de Fase 5-BIS (Tabulator) en esta sesión.

---

## 0. Limitación de entorno (misma de todas las fases anteriores)

Sin Docker/venv funcional en este host. Verificación aplicada: `python -m py_compile` y `node --check` sobre **todos** los archivos `.py`/`.js` tocados (sweep completo al final de la fase, 0 fallos en archivos de esta sesión — los únicos `py_compile` fallidos detectados en el sweep pertenecen a `tests/tenant/core/smoke/*.py`, que ya estaban rotos en el árbol antes de esta sesión, per `git log`, y no se tocaron aquí), más lectura completa de cada archivo modificado y sus consumidores/call sites.

---

## 1. FE-A1 — Guard `data-editor-initialized` en `*_editor.js`

**Inventario real:** 35 archivos `*_editor.js` en el árbol (2 ya tenían el guard correcto: `facturas/facturas_editor.js`, `inventario/categorias_editor.js` — usados como plantilla).

**Metodología aplicada por archivo (no un find/replace ciego):** para cada uno de los 33 restantes se leyó la función de inicialización real y su(s) punto(s) de entrada (DOMContentLoaded, `MutationObserver`, `htmx:afterSettle`, `htmx:afterSwap`, llamada externa) para decidir dónde anclar el guard y sobre qué elemento (el `<form>`, el offcanvas, o `document.body` cuando el problema real eran listeners delegados sobre `document`, no sobre un form).

**Resultado:**
- **19 archivos corregidos** — sin guard, o con un guard roto que se resetea en cada recarga del script (variable de módulo `let x = false`, que nace en `false` en cada ejecución del `<script>` y por lo tanto nunca protege contra recargas HTMX del módulo, solo contra llamadas duplicadas *dentro* de la misma ejecución).
- **12 archivos ya eran seguros** por un patrón distinto pero correcto (`form.cloneNode(true)` + `replaceChild` — elimina cualquier listener previo al reemplazar el nodo; o `data-init`/similar ya bien implementado) — no se tocaron, documentados aquí para que una futura pasada no los re-touchee sin necesidad.
- **1 archivo excluido explícitamente** (`cotizaciones/item_editor.js`) por ser un editor basado en Tabulator, no en un formulario con submit — pertenece a la superficie de Fase 5-BIS, no a FE-A1.
- **1 archivo revisado sin cambios** (`proveedores/representante_editor.js`) — su inicialización depende de `DOMContentLoaded`, que en un contexto SPA/HTMX probablemente nunca se re-dispara tras la carga inicial de la página; no se encontró evidencia de doble-init (el riesgo real, si existe, sería "nunca se inicializa tras un swap HTMX", un problema distinto a FE-A1). Se deja documentado para revisión futura, no se tocó a ciegas.

**Bug de mayor severidad encontrado durante esta fase (no en la lista original de 5 archivos "más graves" del audit, pero de la misma clase):** en `contabilidad/{asiento,cuenta,periodo,plantilla}_editor.js`, `empleados/{contrato,devengo,empleado,liquidacion,resolucion}_editor.js`, `proveedores/cuentas_pagar_editor.js` y `proyectos/nueva_tarea_editor.js`, la función `init()` registra listeners **delegados en `document`/`document.body`** (no en un `<form>` de vida corta). Cada vez que el script se recarga (navegación HTMX al módulo), se registra un listener global adicional — sin el guard, abrir el módulo Contabilidad 3 veces produce 3 `POST` por cada clic en "Guardar Asiento". Se corrigió anclando el guard a `document.body.dataset.<modulo>EditorInitialized` en vez de a una variable de módulo.

**Caso especial — `proyectos_editor.js` (FE-A2 explícito del audit):** el flag `editorEventsInitialized` se resetea intencionalmente en `hidden.bs.offcanvas` para permitir reinicializar en la siguiente apertura — pero si el offcanvas/form no se recrea (mismo nodo DOM reutilizado, no reemplazado), ese reset permite volver a registrar el `submit` sobre el mismo `<form>`, duplicando el POST. Se agregó un guard adicional atado al nodo `<form>` real (`form.dataset.submitBound`) que no depende del flag de módulo — la causa raíz queda cerrada sin tocar el resto de la lógica de reset (que sigue siendo necesaria para otros efectos del `initEditorEvents()`).

---

## 2. FE-A4 + FE-A5 — Helper centralizado `mostrarOffcanvasSeguro`

**FE-A5 — Nuevo archivo SSoT:** `apps/tenant/core/static/core/js/common/offcanvas.helper.js`, expone `window.Sintel.Core.mostrarOffcanvasSeguro(elOrId)`. Cargado globalmente desde `assets_core.html` (antes de cualquier módulo), mismo patrón ya usado para `tabulator.factory.js`.

**Estrategia de consolidación (más segura que reescribir los 16 call sites):** en cada uno de los 16 archivos, el **cuerpo** de la función local `mostrarOffcanvasSeguro`/`_mostrarOffcanvasSeguro` se reemplazó por una delegación de una línea al helper global, **conservando el nombre de la función local**. Esto significa que ningún call site dentro de esos 16 archivos tuvo que tocarse — siguen llamando a su función local de siempre, que ahora delega en vez de duplicar la lógica.

- **14 de 16 archivos consolidados:** `empleados/{contrato,empleado}_editor.js`, `empresa/{area,empresa,mailinboxconfig,sede}_list.js`, `inventario/{activos,categorias,inventario,movimientos,productos,servicios}_list.js`, `ventas/{orden,resolucion}_editor.js`, `ventas/venta_editor.js`.
- **1 archivo excluido a propósito:** `empleados/devengo_editor.js` — su implementación local tiene un `setTimeout(...,0)` adicional antes de crear la instancia, con un comentario explícito documentando que evita un error real (`null.scroll` en `offcanvas.js`) observado en ese módulo específico. Forzar la delegación genérica habría eliminado esa mitigación puntual; se dejó la implementación local intacta (ya corregida para FE-A4, ver abajo).

**FE-A4 — Instancias sin `dispose()` previo (`getOrCreateInstance` crudo), barrido completo del árbol (no solo los 5 archivos nombrados en el hallazgo original):**
- `empleados/contrato_editor.js`, `empleados/empleado_editor.js` — reimplementaciones locales de `mostrarOffcanvasSeguro` que usaban `getOrCreateInstance` sin dispose; corregidas antes de consolidarlas al helper (§ arriba).
- `empleados/liquidacion_list.js`, `empleados/nomina_historial.js`, `proveedores/proveedores_form.js` — los 3 archivos nombrados explícitamente en el hallazgo original; corregidos con el patrón dispose-then-create inline (no se delegaron al helper porque no exponen una función `mostrarOffcanvasSeguro` reutilizable, son casos puntuales de un único call site).
- Grep de verificación final sobre **todo** `apps/tenant/**/*.js`: 0 usos restantes de `bootstrap.Offcanvas.getOrCreateInstance` (los usos de `Modal.getOrCreateInstance`/`Tab.getOrCreateInstance` encontrados en el mismo grep son componentes distintos, sin el bug de acumulación de backdrops que tiene específicamente Offcanvas, y fuera del alcance literal del hallazgo — no se tocaron).

---

## 3. FE-A3 — Patrón anti-backdrop crudo en templates

`perfil/templates/tenant/perfil/partials/list.html:17` y `inventario/templates/inventario/list_categorias.html:15` — el `hx-on::after-request` inline que llamaba `bootstrap.Offcanvas.getOrCreateInstance(el).show()` directamente se reemplazó por una llamada al helper: `window.Sintel?.Core?.mostrarOffcanvasSeguro('offcanvas-id')`. Grep de verificación: 0 ocurrencias de `Offcanvas.getOrCreateInstance` en todo `apps/tenant/**/*.html`.

---

## 4. FE-A6 — `setData()` → `replaceData()`

Los 7 archivos nombrados en el hallazgo original, todos corregidos: `cotizaciones/{producto,servicio}_editor.js` (durante el pase de FE-A1, mismo archivo), `dashboard/dashboard_main.js` (2 ocurrencias), `empleados/{empleado,contrato}_list.js`, `proveedores/cuentas_pagar_list.js`. Grep de verificación adicional sobre todo el árbol encontró 2 usos más de `.setData(` (`contabilidad/libro_diario_list.js`, `contabilidad/reporte.ui.js`) — **no se tocaron**: ambos pasan un array de datos ya calculado localmente (no recargan desde el servidor), un uso legítimo de `setData()` distinto al patrón "recargar desde el mismo endpoint" que el hallazgo señala como obligatorio usar `replaceData()`.

---

## 5. FE-A9 — `getHeaders()`/CSRF centralizado

`compras/compras.api.js`, `gastos/gastos.api.js`, `ventas/ventas.api.js` — las 3 implementaciones divergentes de CSRF (una reimplementaba `getCookie()` localmente; dos leían `document.querySelector('[name=csrfmiddlewaretoken]')`, un input de formulario tradicional no garantizado en páginas API-first) se reemplazaron por `window.getCookie('csrftoken')` — la función SSoT ya expuesta globalmente desde `core/js/lib/http.js` (confirmada su existencia y uso ya establecido por 2 archivos más, per `REPORTE_FASE_1.md` FE-C3 §3). Las 3 quedan con `X-CSRFToken` funcionando incluso si la página no renderiza el input tradicional.

---

## 6. FE-A7 — Ruta de estáticos de `facturas`

Movidos con `git mv` (preserva historial) los 7 archivos de `apps/tenant/facturas/static/js/facturas/` a `apps/tenant/facturas/static/facturas/js/` (estructura estándar `static/<app>/js/`). Referencias actualizadas en los 2 templates que los cargaban (`partials/assets_facturas.html`, `offcanvas_editar_factura.html`). Verificación: 0 referencias residuales a `static/js/facturas`/`'js/facturas` en todo `apps/`/`config/` (excluyendo 3 archivos de documentación `.agent/*.md`, no actualizados por estar fuera del alcance de código).

---

## 7. FE-A8 — Prefijo `tenant/` en templates de `inventario`

Movidos con `git mv` los 13 templates de `apps/tenant/inventario/templates/inventario/` a `apps/tenant/inventario/templates/tenant/inventario/` (el audit contó 12; el árbol actual tiene 13 — probablemente un archivo se agregó después de la auditoría original, mismo criterio de conformidad aplica). Referencias actualizadas en:
- `core/templates/tenant/core/workspace.html` (2 `{% include %}`)
- `inventario/api/viewsets.py` (6 `template_name=` en `Response()` de acciones DRF que renderizan HTML)
- `inventario/templates/tenant/inventario/list_inventario.html` (5 `{% include %}` internos)

Verificación: 0 referencias residuales a `'inventario/list_`/`'inventario/offcanvas_`/`'inventario/assets_inventario` en todo `apps/` (`.py`/`.html`), `python -m py_compile` limpio en `viewsets.py`.

---

## 8. FE-M1/M2/M3 — Investigación (código muerto, diferido a Fase 6)

Los 3 hallazgos apuntan al mismo tipo de problema en 2 archivos distintos, ambos ya sin ninguna referencia real desde ningún template:

- **`apps/tenant/core/static/tenant/core/workspace.js`** (111 líneas, ES module con `import`, expone `window.cargarResumen`/`window.initInventario`/`window.initActivosCRUD` como globales sin namespace — el bug literal que describe FE-M1). Grep exhaustivo de `<script...src="...workspace.js">`/`type="module"` apuntando a este archivo en **todo** `apps/`: **0 resultados**. Es un prototipo de "hydrateView" que importa su propio `./inventario/ui.js`/`catalogo.crud.js`/`activos.crud.js`, aparentemente superado por el patrón `workspace/*.page.js` que sí está en uso (`facturas.page.js`, `inventario.page.js`). El otro `workspace.js` real y sí referenciado (`core/static/core/js/workspace.js`, cargado desde `workspace.html`) **ya está correctamente envuelto en un único IIFE** — no tiene el bug de FE-M1 tal como está escrito hoy.
- **`apps/tenant/landing/static/tenant/landing/workspace/facturas.js`** (458 líneas) + **`facturas.page.js`** (1.218 líneas) — suman exactamente las 1.676 líneas que describe FE-M3. `facturas.js`: 0 referencias en todo el árbol. `facturas.page.js`: 0 referencias desde ningún template real (el único "uso" encontrado es un falso positivo de grep en un archivo no relacionado de `inventario`), **pero sí está referenciado por 4 archivos de test** (`apps/tenant/core/tests/test_workspace_facturas_*.py`) que hacen `GET` real al workspace y assertan que el HTML de respuesta contiene `'/static/tenant/landing/workspace/facturas.page.js'` — assertion que, dado que ningún template real incluye ese script, muy probablemente ya está fallando o cayendo en el `self.skipTest()` que esos mismos tests tienen como fallback ante un workspace que no responde como esperan.

**Por qué no se eliminó en esta fase (decisión deliberada, no un olvido):** confirmar "0 referencias" en templates no es suficiente para borrar con seguridad cuando hay tests que sí referencian el archivo — borrarlo sin saber si esos 4 tests están hoy en verde, rojo o skip podría convertir un test ya-fallando-silenciosamente en un error distinto, o (menos probable pero posible) revelar una ruta de carga dinámica no capturada por el grep estático. El criterio de la propia Fase 6 (código muerto) exige justo este tipo de verificación adicional antes de un `git rm`. Se deja documentado aquí como hallazgo listo para que Fase 6 lo cierre, idealmente coordinado con Fase 7 (decidir qué hacer con los 4 tests dependientes) en el mismo entorno donde se pueda correr `pytest` real.

---

## 9. FE-M4 — Estado dual de `http.js` (documentado)

Agregada una sección nueva a `documentacion/arquitectura_general.md` §5.2 explicando por qué existen 2 versiones de `http.js` cargadas en el shell (la legacy gana por orden de carga y es la única que maneja `FormData`/expone `window.getCookie`, per `REPORTE_FASE_1.md` FE-C3) — cierra el hallazgo tal como pedía su criterio de aceptación ("referencia explícita en `arquitectura_general.md`"), sin fusionar los 2 archivos (esa consolidación sigue pendiente, marcada explícitamente como Fase 6/7 en la nota agregada).

## 10. FE-M5 — No localizado

El hallazgo original describe una ruta hardcoded `/static/core/js/lib/http.js` en un template de `dashboard`. Búsqueda exhaustiva (`grep -rn "core/js/lib/http"` sobre `apps/tenant/dashboard/`) no encontró ninguna coincidencia en el estado actual del árbol. No se modificó nada — no hay evidencia de qué archivo tocar, y forzar un cambio especulativo sobre un archivo no identificado no es seguro. Se documenta como "no reproducible en el estado actual" en vez de darlo por cerrado o inventar una corrección.

## 11. FE-M6 — Ya resuelto

Verificado por grep: `contabilidad/api/viewsets.py` no tiene ningún `lookup_field='id'`/`lookup_url_kwarg='id'` remanente — el único ViewSet con `lookup_field` explícito ya usa `'uuid'`, con un comentario `[ARQ-A1]` que confirma que este hallazgo específico ya se cerró durante la Fase 2. No se requirió ninguna acción.

---

## 12. Archivos tocados (agregado, ~60 archivos)

```
# Nuevo
?? apps/tenant/core/static/core/js/common/offcanvas.helper.js
?? documentacion/REPORTE_FASE_5.md

# Movidos (git mv, historial preservado)
R  apps/tenant/facturas/static/js/facturas/*.js (7 archivos) -> apps/tenant/facturas/static/facturas/js/...
R  apps/tenant/inventario/templates/inventario/*.html (13 archivos) -> apps/tenant/inventario/templates/tenant/inventario/...

# Modificados — guard FE-A1 (19), helper FE-A5 (14), dispose FE-A4 (3 adicionales),
# setData->replaceData FE-A6 (5 adicionales), CSRF FE-A9 (3), referencias FE-A7/A8 (4)
M  apps/tenant/{bancos,compras,contabilidad,cotizaciones,dashboard,empleados,empresa,
     inventario,proveedores,proyectos,ventas}/static/**/*.js  (~35 archivos)
M  apps/tenant/{perfil,inventario}/templates/.../*.html  (2 archivos)
M  apps/tenant/inventario/api/viewsets.py
M  apps/tenant/core/templates/tenant/core/workspace.html
M  apps/tenant/core/templates/tenant/core/partials/assets_core.html
M  apps/tenant/facturas/templates/tenant/facturas/{offcanvas_editar_factura,partials/assets_facturas}.html
M  documentacion/arquitectura_general.md
M  documentacion/PLAN_UNICO_CORRECCIONES.md
```

No se ejecutó ningún `git add`/`git commit`.

## 13. Checklist de cierre

- [x] `py_compile` limpio en todos los `.py` tocados (1 archivo: `inventario/api/viewsets.py`).
- [x] `node --check` limpio en todos los `.js` tocados/nuevos (sweep completo, 0 fallos).
- [x] Ningún hallazgo se "arregló" moviendo el problema a otro archivo sin verificar — cada consolidación (FE-A5) y cada movimiento de ruta (FE-A7/A8) se verificó con grep exhaustivo de referencias antes y después.
- [x] Los 2 archivos ya-correctos usados como plantilla de FE-A1 no se tocaron.
- [x] Las decisiones de "no tocar" (12 archivos ya seguros de FE-A1, 2 de FE-A6, FE-M1/M2/M3 diferidos, FE-M5 no localizado) están documentadas con su razón concreta, no omitidas en silencio.
- [ ] **Pendiente (bloqueado por entorno):** confirmación en navegador de que ningún flujo de guardado quedó roto por los cambios de guard/dispose — se hace en la validación final de Fase 5-BIS (`PLAN_UNICO_CORRECCIONES.md` §"Validación final"), no antes.

## 14. Siguiente paso

Fase 6 (Simplificación/Dedup/Código muerto) es la siguiente en el plan — debe empezar retomando los 2 hallazgos de código muerto que esta fase dejó identificados y listos (`core/static/tenant/core/workspace.js`, `landing/workspace/facturas.js` + `facturas.page.js`), coordinando con Fase 7 la decisión sobre los 4 tests dependientes del segundo. Fase 7 (Testing) queda explícitamente para el final, según instrucción del usuario.
