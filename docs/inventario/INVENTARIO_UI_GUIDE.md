# Inventario — Guía de UI real (FASE 31-42, consolidado)

**Fecha:** 2026-08-27. Describe el frontend TAL COMO ES tras los fixes de
esta misión — no un diseño aspiracional.

---

## Mapa de flujo real

```
workspace/#inventario
  │
  ├── Tab Categorías (list_categorias.html)
  │     └── Grilla django-tables2 + HTMX (#categorias-panel)
  │
  ├── Tab Productos (list_productos.html)
  │     └── Grilla django-tables2 + HTMX (#productos-panel)
  │           Acciones por fila: Editar / Ver Kardex / Eliminar (guard: solo si activo=False)
  │
  ├── Tab Servicios (list_servicios.html)
  │     └── Grilla django-tables2 + HTMX (#servicios-panel)
  │
  ├── Tab Activos Fijos (list_activos.html)
  │     └── Grilla django-tables2 + HTMX (#activos-panel)
  │           Acciones por fila: Editar / Eliminar (guard: solo si estado en {BAJA, VENDIDO} -- nuevo 2026-08-27)
  │
  └── Tab Movimientos / Kardex (list_movimientos.html)
        └── Tabulator (TabulatorFactory, remoto vía API) -- unico listado que
             sigue en Tabulator, deliberado (Kardex NO migró a Fase 5-BIS,
             ver docstring de tables.py)
```

**Nota de arquitectura confirmada**: 4 de las 5 grillas (Categorías,
Productos, Servicios, Activos) ya migraron a Fase 5-BIS (django-tables2 +
HTMX server-rendered) — solo el Kardex (Movimientos) sigue en Tabulator
puro, porque combina `MovimientoInventario` + `HistorialServicio` en una
vista agregada cross-model (`get_movimientos_timeline()`) que no encaja en
el patrón tabular simple de las otras 4. Documentado explícitamente en el
docstring de `tables.py`, no es deuda pendiente.

## Bugs reales corregidos hoy

1. **Ajustar Stock no refrescaba la grilla de Productos** (CRÍTICO) —
   `inventario_editor.js` disparaba un evento (`inventario-updated` en
   `document`) que no tenía ningún listener real. La grilla real escucha
   `producto-updated from:body`. Corregido para disparar el evento correcto
   — ahora el stock se ve actualizado sin recargar la página.
2. **Doble-submit sin protección en Activos y Categorías** (CRÍTICO) — un
   doble clic o red lenta podía crear registros duplicados. Corregido con
   el mismo patrón de flag + botón deshabilitado que ya usaban
   Productos/Servicios.
3. **Botón "Recargar" de Servicios era un no-op** — el `onclick` apuntaba a
   un namespace (`window.Sintel.Inventario.Servicios.List`) que nunca se
   creaba. Corregido agregando el alias.
4. **`inventario_list.js` (Tabulator legacy) era código muerto completo** —
   dependía de `#grid-productos`, que no existe en ningún template desde la
   migración a Fase 5-BIS. Eliminado (script tag + archivo).
5. **Borrado de Categoría con manejo de error manual** (bypaseaba
   `UIManager.handleError`) — corregido para delegar como el resto de las
   listas.
6. **Typo de namespace en `inventario.utils.js`** (`Sintel.Inventario.Api`
   en vez de `.API`) — la capa de abstracción de API quedaba muerta
   silenciosamente para la carga de categorías; corregido.
7. **Doble inicialización del editor de Movimientos** — se disparaba
   `MovimientosEditor.init()` dos veces por cada apertura del offcanvas
   (una vez por el `<script>` inline del template, otra por un listener
   genérico en `assets_inventario.html`), causando un doble `GET` de items
   en modo edición. Se dejó solo el trigger del template.
8. **Bloque muerto `window.Sintel.Inventario.Servicios.Editor`** en
   `assets_inventario.html` — nunca se ejecutaba (namespace que
   `servicios_editor.js` nunca crea); `servicios_editor.js` ya tenía su
   propio listener funcional. Eliminado el bloque redundante.

## Verificado y CORRECTO (no son bugs, confirmados con evidencia)

- `initCodigoPrefijo()`/`setupCuentaAutocomplete()` de la vinculación
  contable ya no existen en `activos_editor.js` — el código muerto que la
  auditoría v3.10.2 documentaba (DEUDA-08) ya había sido eliminado antes de
  esta misión; solo la entrada de la doc quedó desactualizada (corregida).
- Los campos `DecimalField` en offcanvas usan `stringformat` consistente —
  sin bug de locale (coma decimal es-CO).
- `bootstrap.Offcanvas.getOrCreateInstance()` NO se usa en ningún archivo
  del módulo — siempre `mostrarOffcanvasSeguro()`.
- Los 2 usos vivos de Tabulator (Movimientos) usan `TabulatorFactory`
  correctamente.
- Responsive: las 4 tablas migradas envuelven en `overflow-x:auto` sin
  anchos mínimos fijos.
- `productos_editor.js` nunca envía `stock_actual` en el payload de
  crear/editar — cumple la Regla #2 (todo cambio de stock pasa por Kardex).

## Accesibilidad

Se agregó `aria-label` explícito a los botones de icono en las 4 tablas
migradas (`tables.py`) — antes solo tenían `title`. El estado siempre se
muestra como badge (color + texto), nunca solo color.

## Deuda documentada, no corregida (menor, fuera de alcance de esta pasada)

- Campo `cliente_referencia: ''` hardcodeado en el payload de
  `movimientos_editor.js` sin campo de formulario correspondiente — ruido
  de contrato sin efecto funcional (el backend lo acepta como opcional).
- Sin campo de búsqueda dedicado en algunas grillas — mejora opcional, no
  un bug.
