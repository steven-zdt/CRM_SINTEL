# Skill: Tabulator.js — SINTEL v2.62

**Carga cuando:** Crear o modificar tablas de datos con Tabulator.

---

## Inicialización con TabulatorFactory (Preferido)

```javascript
// TabulatorFactory está en: core/static/core/js/common/tabulator.factory.js
// Inyecta JWT automáticamente, maneja búsqueda, paginación remota

state.miTable = window.TabulatorFactory.create(
    '#grid-<modelo>',          // selector del contenedor
    '/api/v1/<app>/',          // URL del API REST
    getColumnas(),             // definición de columnas
    { searchInputSelector: '#search-<modelo>' }
);
```

## Definición de Columnas

```javascript
function getColumnas() {
    return [
        { title: 'Nombre', field: 'nombre', widthGrow: 2 },
        { title: 'Código', field: 'codigo', width: 150 },
        {
            title: 'Estado',
            field: 'activo',
            width: 80,
            hozAlign: 'center',
            formatter: (cell) => cell.getValue()
                ? '<span class="badge bg-success">Activo</span>'
                : '<span class="badge bg-danger">Inactivo</span>'
        },
        {
            title: 'Acciones',
            width: 140,
            hozAlign: 'center',
            headerSort: false,
            formatter: () => `
                <div class="btn-group btn-group-sm" role="group">
                    <button class="btn btn-outline-primary" data-action="edit" title="Editar">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-info" data-action="view" title="Ver">
                        <i class="bi bi-eye"></i>
                    </button>
                    <button class="btn btn-outline-danger" data-action="delete" title="Eliminar">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            `,
            cellClick: (e, cell) => handleCellAction(e, cell)
        }
    ];
}
```

## Event Delegation para Acciones

```javascript
function handleCellAction(e, cell) {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;

    const action = btn.dataset.action;
    const rowData = cell.getRow().getData();

    switch (action) {
        case 'edit':   editarObjeto(rowData.id);  break;
        case 'view':   verObjeto(rowData.id);     break;
        case 'delete': eliminarObjeto(rowData);   break;
    }
}
```

## Recargar Datos

```javascript
// Recargar sin destruir la instancia (preferido)
function recargarTabla() {
    if (state.miTable && typeof state.miTable.replaceData === 'function') {
        state.miTable.replaceData();
    }
}
```

## Anti-Zombie (destruir antes de crear)

```javascript
// Si existe instancia previa, destruirla
if (state.miTable && typeof state.miTable.destroy === 'function') {
    try { state.miTable.destroy(); } catch (e) { /* ignorar */ }
    state.miTable = null;
}
```

## Esperar a TabulatorFactory

```javascript
async function waitForTabulatorFactory() {
    if (window.TabulatorFactory) return;
    return new Promise((resolve, reject) => {
        let attempts = 0;
        const interval = setInterval(() => {
            if (window.TabulatorFactory) {
                clearInterval(interval);
                resolve();
            } else if (++attempts > 50) {
                clearInterval(interval);
                reject(new Error('TabulatorFactory timeout'));
            }
        }, 100);
    });
}
```

## Container HTML

```html
{# En el template de la lista #}
<div id="grid-<modelo>" data-grid="<app>"></div>
<div data-spinner="<app>" class="text-center py-5" style="display:none;">
  <div class="spinner-border"></div>
</div>
<div data-empty-state="<app>" class="text-center py-5" style="display:none;">
  <p class="text-muted">No hay registros</p>
</div>
```

## Reglas
- Siempre usar `TabulatorFactory.create()` — nunca `new Tabulator()` directamente
- `replaceData()` para recargar, no destruir/recrear
- **[CRITICAL]** Definir `cellClick` dentro de la columna de Acciones — evitar usar `cellClick` global en la configuración de la tabla si hay botones específicos.
- Usar delegación de eventos con `data-action` y `e.target.closest('[data-action]')` para manejar CRUD.
- Estilizar botones con `btn-group` y `btn-outline-*` para consistencia visual (SINTEL Standard).
- Verificar que el container `#grid-X` exista antes de inicializar
- La tabla espera respuesta DRF paginada: `{ count, next, previous, results: [] }`

