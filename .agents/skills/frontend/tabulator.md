# Skill: Tabulator.js — SINTEL v3.16

**Carga cuando:** Crear o modificar tablas de datos con Tabulator.

---

## 1. Inicialización — TabulatorFactory (obligatorio)

```javascript
// TabulatorFactory: apps/tenant/core/static/core/js/common/tabulator.factory.js
// Inyecta JWT, maneja búsqueda, paginación remota y formato SINTEL

state.table = window.TabulatorFactory.create(
    '#grid-<modelo>',           // selector del container
    '/api/v1/<app>/',           // URL del API DRF paginado
    getColumnas(),              // definición de columnas
    { searchInputSelector: '#search-<modelo>' }
);
```

---

## 2. Formatters de Columnas — Catálogo SINTEL

```javascript
// Badge de estado activo/inactivo
formatter: (cell) => cell.getValue()
    ? '<span class="badge bg-success">Activo</span>'
    : '<span class="badge bg-secondary">Inactivo</span>'

// Sede (FK opcional)
formatter: (cell) => {
    const v = cell.getValue();
    return v
        ? `<span class="badge bg-light text-dark border small">${v}</span>`
        : '<span class="text-muted small">—</span>';
}

// Moneda COP
formatter: (cell) => {
    const v = parseFloat(cell.getValue());
    if (isNaN(v)) return '—';
    return '$' + v.toLocaleString('es-CO', { minimumFractionDigits: 0 });
}

// Fecha ISO a display legible
formatter: (cell) => {
    const v = cell.getValue();
    if (!v) return '—';
    return new Date(v).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' });
}

// UUID truncado (para referencias visibles)
formatter: (cell) => {
    const v = cell.getValue();
    return v ? `<code class="small text-muted">${String(v).slice(0, 8)}…</code>` : '—';
}

// Badge de vinculación (ej: cotización vinculada)
formatter: (cell) => {
    const info = cell.getValue();
    if (!info) return '<span class="badge text-bg-light border text-muted">Sin vínculo</span>';
    const label = info.label || info.codigo || info.uuid?.slice(0, 8) || 'Vinculado';
    return `<span class="badge text-bg-success">${label}</span>`;
}
```

---

## 3. Columna de Acciones — Patrón Estándar

```javascript
{
    title: 'Acciones',
    width: 130,
    hozAlign: 'center',
    headerSort: false,
    formatter: () => `
        <div class="btn-group btn-group-sm" role="group">
            <button class="btn btn-outline-primary" data-action="edit" title="Editar">
                <i class="bi bi-pencil"></i>
            </button>
            <button class="btn btn-outline-info" data-action="view" title="Ver detalle">
                <i class="bi bi-eye"></i>
            </button>
            <button class="btn btn-outline-danger" data-action="delete" title="Eliminar">
                <i class="bi bi-trash"></i>
            </button>
        </div>`,
    cellClick: handleCellAction
}

function handleCellAction(e, cell) {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;

    const row  = cell.getRow().getData();
    // IMPORTANTE: usar .uuid (UUID) para URLs de API — nunca .id (PK entero)
    const uuid = row.uuid;

    switch (btn.dataset.action) {
        case 'edit':   _abrirEditar(uuid);       break;
        case 'view':   _abrirDetalle(uuid);      break;
        case 'delete': _eliminar(row);           break;
    }
}

function _abrirEditar(uuid) {
    htmx.ajax('GET',
        `/api/v1/<app>/${uuid}/render-offcanvas/editar/`,
        { target: '#offcanvas-container-<app>', swap: 'innerHTML' }
    );
}
```

---

## 4. Recargar Datos

```javascript
// Preferido: replaceData() — no destruye la instancia
function recargarTabla() {
    if (state.table && typeof state.table.replaceData === 'function') {
        state.table.replaceData();
    }
}

// Con filtros activos preservados
function recargarConFiltros() {
    state.table?.replaceData();  // TabulatorFactory preserva los filtros
}
```

---

## 5. Anti-Zombie — Destruir antes de recrear

```javascript
function destruirTabla() {
    if (state.table && typeof state.table.destroy === 'function') {
        try { state.table.destroy(); } catch (e) { /* ignorar */ }
        state.table = null;
    }
}
```

---

## 6. Esperar TabulatorFactory

```javascript
async function waitForTabulatorFactory(maxMs = 5000) {
    if (window.TabulatorFactory) return;
    return new Promise((resolve, reject) => {
        const start = Date.now();
        const check = setInterval(() => {
            if (window.TabulatorFactory) {
                clearInterval(check);
                resolve();
            } else if (Date.now() - start > maxMs) {
                clearInterval(check);
                reject(new Error('[Tabulator] TabulatorFactory no disponible'));
            }
        }, 100);
    });
}
```

---

## 7. Container HTML

```html
{# Template lista #}
<div id="grid-<modelo>" data-grid="<app>"></div>

{# Spinner mientras carga #}
<div data-spinner="<app>" class="text-center py-5 d-none">
  <div class="spinner-border text-primary"></div>
  <p class="text-muted mt-2 small">Cargando...</p>
</div>

{# Empty state #}
<div data-empty-state="<app>" class="text-center py-5 d-none">
  <i class="bi bi-inbox fs-1 text-muted"></i>
  <p class="text-muted mt-2">No hay registros</p>
</div>
```

---

## 8. Esperar respuesta DRF paginada

Tabulator espera el formato DRF estándar:

```json
{
  "count": 42,
  "next": "http://.../api/v1/<app>/?page=2",
  "previous": null,
  "results": [{ "id": 1, "uuid": "...", "nombre": "..." }]
}
```

---

## 9. Reglas

| Regla | Detalle |
|---|---|
| `TabulatorFactory.create()` | Nunca `new Tabulator()` directamente |
| `replaceData()` | Para recargar — no destruir/recrear |
| `uuid` en URLs | `row.uuid` para endpoints API — nunca `row.id` |
| `data-action` en botones | Event delegation — no onclick inline ni `cellClick` global |
| `cellClick` en columna de acciones | Específico por columna — no en config global de la tabla |
| Container existe antes de init | `if (!document.querySelector('#grid-X')) return;` |
