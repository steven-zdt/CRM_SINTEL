# F31.2 — Ejecución: Consolidación Core Frontend

**Fecha:** 2026-08-12 · Ejecuta las 4 decisiones abiertas de
`F31_FRONTEND_CONTRACT.md` §4. Resultado real: 2 ejecutadas, 1 diferida
por riesgo (con evidencia nueva que cambia el diagnóstico), 2 completadas
como investigación de solo lectura (auditoría de eventos, decisión de
contabilidad).

---

## §4.2 -- `error-service.js`: eliminado

Confirmado código muerto en su scope (tenant): su `init()` retorna
inmediatamente si `!jQuery.fn.dataTable` (no existe en tenant desde la
migración a Tabulator), no expone nada que otro módulo consuma. Verificado
con grep dedicado que solo 2 referencias existían fuera del archivo mismo:
su propio `<script>` tag en `assets_core.html` y un comentario informativo
en `tests/workspace_ux_smoke.js` (no una dependencia funcional).

**Cambios:** `apps/tenant/core/static/core/js/helpers/error-service.js`
eliminado; su `<script>` tag removido de `assets_core.html`.

## §4.1 y §4.5 -- `http.js` / `jwt-auth.js`: DIFERIDOS tras investigación más profunda

Al intentar ejecutar la fusión recomendada en F31.1, la lectura completa
de los 3 archivos involucrados reveló un problema más serio que una simple
duplicación de nombre:

- **3 archivos**, no 2: `apps/tenant/core/static/js/http.js` ("v3.4
  unificado"), `apps/public/console/static/js/http.js` (byte-idéntico al
  anterior, confirmado con `diff`), y
  `apps/tenant/core/static/core/js/lib/http.js` (contrato distinto,
  con lógica de negocio ad-hoc para un campo `cliente` que no debería
  vivir en un cliente HTTP genérico).
- El tercero **gana en producción** sobre el "v3.4" en toda página
  `workspace.html` (la mayoría de las apps de negocio) -- confirmado leyendo
  el orden real de carga en `tenant/base.html` (línea 129) vs el bloque
  `extra_js` de `workspace.html` (línea 291, incluye `assets_core.html`
  después). Un comentario ya existente en el propio archivo perdedor
  (`[FE-C3]`) documenta que alguien ya diagnosticó este mismo problema
  antes y parcheó JWT ahí en vez de corregir el orden de carga -- no es un
  hallazgo nuevo, es deuda ya conocida con un workaround parcial aplicado.
- Verificado que ningún JS de tenant llama al contrato de objeto
  (`window.http.get/post/...`) del "v3.4" -- así que el "ganador" real no
  rompe nada visible en tenant hoy. Pero SÍ tiene comportamientos propios
  (allowlist de 401 para módulos no críticos, manejo de `FormData`,
  diagnóstico 403) que el "v3.4" no replica -- invertir el orden de carga
  sin más rompería esos comportamientos.
- `jwt-auth.js` comparte la causa raíz estructural: no existe hoy un lugar
  neutral para JS compartido entre tenant y consola pública, así que vive
  dentro de `apps/public/console/static/js/` aunque lo consume también
  tenant.

**Decisión:** no se modifica ninguno de estos archivos en F31.2. El riesgo
de romper CSRF/auth/uploads en todas las apps tenant simultáneamente sin
pruebas de navegador reales (no disponibles en este entorno -- ver
"Limitación de verificación" abajo) es demasiado alto para una corrección
apresurada. Se documenta como hallazgo crítico para una micro-fase futura
dedicada, con pruebas de regresión de navegador como prerrequisito
explícito antes de tocar código.

## §4.3 -- Offcanvas: 11 de 13 violaciones corregidas

**Archivos corregidos** (reemplazado el patrón manual
dispose+backdrop-cleanup+create+show por una llamada única a
`window.Sintel.Core.mostrarOffcanvasSeguro(el)`):

| App | Archivo |
|---|---|
| bancos | `cuenta_editor.js`, `extracto_editor.js` |
| empleados | `resolucion_editor.js`, `liquidacion_editor.js`, `liquidacion_list.js`, `nomina_historial.js` |
| facturas | `facturas_list.js` |
| proyectos | `proyectos_editor.js` |
| proveedores | `proveedores_form.js`, `representante_editor.js` |
| empresa | `mailinboxconfig_editor.js` |

En al menos 3 de estos sitios (`extracto_editor.js`, `nomina_historial.js`,
`representante_editor.js`) el patrón local **no disponía la instancia
previa antes de crear una nueva** -- exactamente el bug que
`offcanvas.helper.js` fue creado para prevenir (backdrops acumulados tras
aperturas repetidas). La conversión no es solo estilística: corrige un bug
latente real en esos 3 sitios.

**2 excepciones documentadas, NO corregidas (riesgo de romper
comportamiento específico):**
- `empleados/devengo_editor.js` -- tiene un `setTimeout(..., 0)`
  deliberado antes de crear la instancia, con un comentario explícito
  ("evita null.scroll en offcanvas.js") documentando un workaround a un
  bug de timing de Bootstrap que el helper compartido no tiene. Ya dispone
  correctamente antes del timeout (no es el bug de backdrops), así que no
  es urgente forzarlo al helper sin antes verificar si el helper necesita
  el mismo workaround.
- `facturas/facturas_main.js` -- su función `initOffcanvas()` crea la
  instancia **sin mostrarla** (usada para pre-inicializar tras
  reinyecciones de HTMX; `showOffcanvas()` la muestra por separado,
  `hideOffcanvas()`/`getOffcanvasInstance()` dependen del patrón de
  instancia guardada). Ya dispone correctamente antes de crear. El helper
  compartido no soporta "crear sin mostrar", así que forzar la
  sustitución rompería el contrato de 3 funciones separadas que otros
  callers de este archivo usan.

**Verificado:** `node --check` no disponible en este entorno (host ni
contenedor); los 11 archivos se revisaron manualmente línea por línea tras
cada edición (estructura de llaves/paréntesis intacta). No se pudo
verificar visualmente en navegador -- ver limitación abajo.

## §4.6 -- Contrato de eventos: auditado (solo lectura, sin normalizar)

Grep de `dispatchEvent(new CustomEvent(...))` en las 17 apps encontró **45
sitios**. Hallazgo principal: **el patrón dominante ya es `<modelo>-updated`
(kebab-case)** -- usado en ~23 de 45 sitios, cubriendo bancos, compras,
ventas, gastos, contabilidad (4 sub-dominios), perfil, proyectos, empleados
(5 modelos), empresa (4 modelos), proveedores (2). El contrato
`<modelo>-created/updated/deleted` (3 eventos separados) que proponía el
plan original de F31 **no es lo que existe hoy** -- la mayoría de las apps
disparan un único evento `-updated` sin distinguir create/update/delete.

**Outliers identificados (7 sitios, 3 apps) que rompen la convención
dominante con camelCase legacy:**
- `clientes`: `clienteGuardado`, `contactoGuardado`, `clienteEliminado`,
  `contactoEliminado` (4 sitios).
- `facturas/facturas_main.js`: `facturaEliminada` (1 sitio).
- `inventario/productos_editor.js`: `inventarioActualizado` (1 sitio).

**Otras categorías distintas, no comparables al contrato CRUD:**
`sintel:ventas:editor:ready`/`sintel:ventas:resolucion-editor:ready`
(namespaced, señales de "componente listo", no de dato cambiado);
`*-editor-init` (compras, gastos -- señales de inicialización de
componente); `tab-activated` (core/workspace.js, navegación de UI, no
CRUD).

**No se normaliza en F31.2** -- unificar estos 7 sitios requeriría
también encontrar y actualizar sus listeners correspondientes (fuera del
alcance de este grep de solo-escritura), y el contrato real ya
mayoritariamente vigente (`<modelo>-updated`) es una base más sólida para
documentar como estándar que reescribir todo a un esquema de 3 eventos
nunca adoptado. Recomendación para una fase futura de eventos: adoptar
`<modelo>-updated` como el contrato oficial (ya es el de facto), normalizar
solo los 7 outliers camelCase.

## §4.4 -- Patrón de `contabilidad` (8 `*.api.js`): aceptado, documentado

Decisión tomada per la recomendación de F31.1: `contabilidad` mantiene 8
archivos `*.api.js` (uno por sub-dominio: asiento, cuenta, libro, periodo,
plantilla, reporte, retencion, tipo_comprobante) como variante válida del
contrato SSoT-por-app, dado que tiene 8 sub-dominios reales distintos. No
requiere consolidación forzada en un archivo único. Documentado aquí como
la decisión oficial -- no se crea `contabilidad.api.js` raíz.

## F31.3 -- Auditoría del contrato API Client (solo lectura)

Verificado el principio de F31.1 ("`<app>.api.js` debe contener URLs +
métodos, NO CSRF/JWT/manejo genérico de errores") contra las 17 apps.

**Cumplen correctamente (delegan a `window.http()`/`w.http()`, sin lógica
propia de transporte):** inventario, bancos, empresa, facturas, clientes,
proyectos, proveedores (2 archivos), contabilidad (8 sub-archivos),
core/landing, perfil, área/mailinboxconfig de empresa. La mayoría del
proyecto ya sigue el contrato correcto.

**Violan el contrato -- 6 archivos con reimplementación completa de
`fetch()` + CSRF + JWT propios, en vez de delegar a Core:** `gastos.api.js`,
`compras.api.js`, `empleados.api.js`, `cotizaciones.api.js`,
`dashboard.api.js`, `ventas.api.js`. Peor aún: **cada uno tiene su propio
contrato de error distinto** -- `gastos`/`compras` hacen `throw error`
(objeto `Error` genérico o la `Response` cruda según el método),
`cotizaciones` hace `throw {ok:false, status, data}` (una forma custom
que imita pero no es idéntica a la de `window.http()`), `dashboard` hace
`throw new Error('Error ' + status + ...)` (mensaje plano, sin `status`/
`data` estructurados). Ninguno coincide exactamente entre sí ni con el
contrato `{ok, status, data}` sin `throw` de `window.http()`.

**Verificado el patrón prohibido `window.jwtAuth.token`** (CLAUDE.md exige
`window.jwtAuth?.getAccessToken?.()`): **0 ocurrencias** en todo el repo.
Ningún archivo usa el patrón incorrecto.

**Decisión:** no se corrige en este pase. Los consumidores (`*_list.js`/
`*_editor.js` de esas 6 apps) están escritos contra el contrato
`try/catch` + `throw` propio de cada api.js -- reemplazar el transporte
por `window.http()` sin auditar y actualizar cada consumidor rompería el
manejo de errores en 6 apps simultáneamente, sin forma de verificarlo en
navegador en este entorno (misma limitación que el cluster de `http.js`
de §4.1). Se documenta como el mismo tipo de hallazgo -- candidato a la
misma micro-fase futura dedicada con pruebas de navegador, no una
corrección aislada de F31.3.

## Limitación de verificación

**No fue posible verificar visualmente en navegador los 11 cambios de
Offcanvas.** El Browser pane no compuso frames (`preview_start` +
`screenshot` falló con timeout) y el único test E2E relevante
(`tests/e2e/test_workspace_facturas_forensics.py`, cubre el flujo de
detalle de facturas que usa `facturas_list.js`) requiere el plugin
`pytest-playwright`, **no instalado en este contenedor**
(`fixture 'page' not found`) -- limitación de entorno preexistente, no
introducida por este cambio. La verificación se apoyó en: (a) revisión
manual línea por línea de cada uno de los 11 archivos editados, (b) el
hecho de que `mostrarOffcanvasSeguro` es código ya probado y en uso activo
en el resto de la base de código (no es nueva), y (c) que las
transformaciones son sustituciones mecánicas de un patrón ya verificado
equivalente (o superior, al agregar el `dispose()` faltante en 3 casos).
**Recomendación:** validar manualmente en un navegador real (abrir cada
offcanvas afectado: cuentas/extractos de bancos, resoluciones/liquidaciones/
nómina de empleados, detalle de facturas, editor de proyectos, formulario
de proveedores/representantes, mailinbox de empresa) antes de dar por
cerrado este cambio en un entorno con acceso a un navegador funcional.
