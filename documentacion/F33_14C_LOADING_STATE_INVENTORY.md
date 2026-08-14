# F33.14-C — Loading States: Inventario y Adopción Controlada

Mismo rigor que F33.14-A (Card KPI) y F33.14-B (Empty State): auditoría
completa ANTES de tocar código, lectura de cada candidato completo (no solo
grep de la firma superficial), ningún hallazgo `APP_SPECIFIC`/`KEEP`
convertido automáticamente en `SHARED`.

## Metodología

1. Grep de `spinner-border` sobre `apps/tenant/**/*.html` -- 17 archivos
   (excluyendo el propio partial `loading_state.html`).
2. Lectura completa de cada sitio con contexto (no solo la línea con match)
   para determinar: ¿es un panel de carga completo (HTMX "contenido inicial
   antes del primer swap") o un spinner inline dentro de un botón/celda de
   tabla ("estado de envío de formulario")? ¿Coincide el markup exacto
   (clases, `role`, `<span>` vs `<p>`, tamaño) con el target
   `loading_state.html`?
3. Verificación de mecanismo: `hx-trigger="load"` con contenido HTML inicial
   (mecanismo real del target) vs toggle JS por `data-attr`/`id`
   (mecanismo distinto, propio de `EmptyState`, no de `loading_state.html`)
   vs `innerHTML` inyectado por JS al hacer submit (estado de botón, no de
   panel).

## F33.14-C INVENTARIO

```
Candidatos encontrados: 17
├── SHARED_CANDIDATE: 2  (gastos_list.html, compras_list.html -- 3 sitios)
├── DUPLICATE:         5  (2 sub-familias reales -- 7 sitios)
├── KEEP (botón/celda inline, no es panel):  8  (15 sitios)
└── KEEP (overlay global, patrón distinto):  2  (2 sitios)

Migraciones ejecutadas: 2 archivos, 3 sitios
```

## Detalle por candidato

| # | Archivo | Clasificación | Evidencia | Acción |
|---|---|---|---|---|
| 1 | `gastos/gastos_list.html` (panel "gastos", panel "resoluciones") | **SHARED_CANDIDATE** | Markup byte-idéntico al target (`text-center py-5` + `spinner-border` con `role="status"` + `span.visually-hidden` + `p.mt-2.text-muted`), es el contenido inicial de un panel `hx-trigger="load"` -- coincide exactamente con el caso de uso del partial | **Migrado**, 2/2 sitios |
| 2 | `compras/compras_list.html` (panel "órdenes de compra") | **SHARED_CANDIDATE** | Mismo patrón exacto que #1 | **Migrado**, 1/1 sitio |
| 3 | `clientes/clientes_list.html` (`data-spinner="contactos"`, `data-spinner="cartera"`) | **DUPLICATE** (familia "JS-toggled por color") | `text-center py-5` coincide, pero `spinner-border` lleva `text-primary` (el target no tiene color) y el `<p>` lleva `text-muted small` (el target no tiene `small`) -- además el mecanismo de toggle es JS vía `[data-spinner="X"]`, no el contenido inicial de un swap HTMX. Es un patrón distinto (mismo problema estructural que el `data-empty-state` de F33.14-B, pero para spinners) | No migrado -- mecanismo y clases distintos, forzarlo cambiaría el color/tamaño visual actual |
| 4 | `clientes/offcanvas_detalle_cliente.html` (`id="historial-facturas-spinner"`) | **DUPLICATE** (familia "compacta py-4/sm") | `text-center py-4` (no `py-5`), `spinner-border-sm` (no el tamaño normal), `<span class="ms-2 small">` (no `<p class="mt-2">`), toggle por `id` no por `data-attr` -- tamaño reducido deliberado para un sub-panel dentro de offcanvas | No migrado -- mismo motivo que el hallazgo análogo de F33.14-B (offcanvas compactos) |
| 5 | `facturas/list_factura.html` (panel ventas, panel compras -- 2 sitios) | **DUPLICATE** (misma familia "compacta py-4/sm" que #4) | `text-center py-4` + `spinner-border-sm` + `<span class="ms-2 small">` -- idéntico patrón a #4, confirma que es una sub-variante real y repetida entre apps (`clientes` + `facturas`), no un caso aislado | No migrado -- mismo motivo que #4 |
| 6 | `facturas/offcanvas_pendientes_factura.html` | **DUPLICATE** (variante propia dentro de la misma familia compacta) | `text-center py-4` coincide con #4/#5, pero `spinner-border` SIN `-sm` y `<p class="text-muted small">` (no `<span>`) -- ni siquiera coincide exactamente con #4/#5 pese a estar en la familia "compacta" | No migrado -- inconsistencia real dentro del propio grupo "compacto" (3 archivos, mismo concepto, 2 variantes internas), documentado como hallazgo, no resuelto en esta pasada |
| 7 | `contabilidad/reporte_page.html` (`#container-estado-resultados`) | **DUPLICATE** (near-miss de un solo sitio) | `text-center py-5` coincide con el target, pero `spinner-border` lleva `text-primary opacity-50` y **no tiene** `role="status"` ni `span.visually-hidden` (regresión de accesibilidad si se dejara igual), y el `<p>` no lleva `mt-2` en el mismo orden de clases -- migrarlo implicaría un cambio visual real (quitar color/opacidad) y una mejora de accesibilidad no solicitada, no una migración neutra | No migrado -- candidato de bajo valor (1 solo sitio), requiere decisión de diseño explícita sobre si el color/opacidad es intencional |
| 8 | `contabilidad/cuenta_offcanvas_form.html` (botón "Guardando...", resultados de búsqueda) | **KEEP** (spinner inline, no panel) | `btnGuardar.innerHTML` y el contenedor de resultados se generan vía JS `innerHTML` como *estado de un botón/lista de resultados durante una request*, no como el contenido inicial de un panel `hx-trigger="load"` -- estructuralmente incompatible con `{% include %}` (el partial es server-side Django, esto es JS runtime) | Sin acción -- patrón "estado de envío", no "loading state de panel" |
| 9 | `contabilidad/pendiente_offcanvas_contabilizar.html` (7 sitios: celdas de tabla + botones) | **KEEP** (mismo motivo que #8, x7) | Todos los sitios son `innerHTML` de JS para botones (`btnAplicarPlantilla`, `btnRevisar`, `btn-ia-sugerir`, `btnGenerar`) o celdas `<td colspan="5">` dentro de `<tbody>` -- ninguno es un `<div>` standalone de panel | Sin acción -- mismo motivo que #8 |
| 10 | `empleados/offcanvas_crear_contrato.html` (botón "Guardando...") | **KEEP** (mismo motivo que #8) | `hx-on::htmx:before-request` inyecta el spinner en el `innerHTML` del propio botón de submit | Sin acción |
| 11 | `empleados/offcanvas_crear_devengo.html` (botón "Guardando...") | **KEEP** (mismo motivo que #8) | Idéntico patrón a #10 | Sin acción |
| 12 | `empleados/offcanvas_crear_resolucion.html` (botón "Guardando...") | **KEEP** (mismo motivo que #8) | Idéntico patrón a #10 | Sin acción |
| 13 | `empleados/offcanvas_detalle_liquidacion.html` (botón "Guardando...") | **KEEP** (mismo motivo que #8) | `this.innerHTML` en el handler de un botón de confirmación | Sin acción |
| 14 | `empleados/offcanvas_editar_contrato.html` (botón "Guardando...") | **KEEP** (mismo motivo que #8) | Idéntico patrón a #10 | Sin acción |
| 15 | `facturas/list_factura.html` (`#sync-spinner`, botón "Sincronizar Buzón") | **KEEP** (mismo motivo que #8) | `<span class="spinner-border spinner-border-sm d-none">` inline dentro de un botón, toggleado por JS -- no es panel | Sin acción (nota: este archivo también contiene los 2 sitios `DUPLICATE` de la fila #5, correctamente separados) |
| 16 | `core/workspace.html` (`#spinner` global HTMX) | **KEEP** (overlay global, patrón distinto) | `position-fixed top-50 start-50`, clase `htmx-indicator` -- es el indicador global de actividad HTMX de toda la aplicación, no el loading state de un panel específico | Sin acción -- patrón estructuralmente distinto (sin `entity`, sin contenedor de panel) |
| 17 | `cotizaciones/editor_cotizacion.html` (`#cot-editor-spinner`) | **KEEP** (overlay global, mismo motivo que #16) | `position-fixed top-0 start-0 w-100 h-100` con fondo semitransparente -- overlay de pantalla completa del editor, no un panel de lista | Sin acción -- mismo motivo que #16 |

## Verificación de la migración ejecutada

- Render directo del `{% include %}` vía `Template().render()`: output
  byte-idéntico al markup original (confirmado antes de aplicar).
- `manage.py check`: PASS.
- Governance (`tools.organizational_governance.cli --report`): **FINAL
  STATUS: PASS**.
- E2E: contenedor `web` reiniciado preventivamente antes de la corrida
  (ver resultado en `F33_STATUS_REPORT.md`).

## Pendiente, documentado con evidencia (no omisión)

| Candidato | Qué falta para decidir |
|---|---|
| Familia "compacta py-4" (`clientes/offcanvas_detalle_cliente.html`, `facturas/list_factura.html` x2, `facturas/offcanvas_pendientes_factura.html`) | 4 sitios en 3 archivos, 2 sub-variantes internas (`spinner-border-sm`+`<span>` vs `spinner-border` normal+`<p>`) -- antes de crear una 2ª primitiva "compacta", valdría la pena homologar estas 2 sub-variantes entre sí (mismo hallazgo de inconsistencia interna que F33.14-B encontró en `proveedores`) |
| `clientes_list.html` (`data-spinner`) | ¿Extender `loading_state.html` con un parámetro `id`/`data-attr` opcional para el caso "JS-toggled", o mantenerlo fuera del alcance del partial (que hoy solo cubre el caso "contenido inicial de swap HTMX")? Decisión de diseño, no solo técnica |
| `contabilidad/reporte_page.html` | Migrar implicaría decidir si el color/opacidad (`text-primary opacity-50`) es intencional o un accidente histórico, y si agregar `role="status"`+`span.visually-hidden` (mejora de accesibilidad) es deseable ahora o en F33.17 |

Ninguno se ejecuta en esta pasada -- cada uno requiere su propia decisión de
diseño con evidencia adicional, consistente con la regla "no sobrediseño" de
la misión.
