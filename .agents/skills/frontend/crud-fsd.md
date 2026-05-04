---
name: crud-fsd-frontend
description: Estándar arquitectónico para módulos CRUD Frontend (HTMX + Tabulator + Vanilla JS) de propósito general.
---

# Skill: Arquitectura CRUD Frontend (Feature-Sliced Design)

**Carga cuando:** Construyas o refactorices interfaces de gestión (CRUD) para modelos en el entorno del Workspace (ej. cualquier entidad de negocio, catálogos, registros operacionales).

## 1. Stack y Patrón Arquitectónico (Corrección del Estándar)

> [!WARNING]
> **Corrección Arquitectónica:** A diferencia de las SPA tradicionales o aplicaciones 100% HTMX, SINTEL v2.62 utiliza un modelo híbrido estricto:
> - **HTMX (`hx-get`):** Se utiliza EXCLUSIVAMENTE para *Server-Driven UI* (ej. solicitar el HTML de los modales/offcanvas al servidor).
> - **Vanilla JS (Fetch/JSON):** Se utiliza para TODAS las mutaciones de datos (POST, PATCH, DELETE). **NO uses `hx-post` o `hx-put`** para enviar formularios, ya que el backend DRF requiere payloads JSON estructurados y JWT en los headers.
> - **Tabulator:** Grilla reactiva para lectura y renderizado.

## 2. Estructura de Archivos (Feature-Sliced)

Cada módulo debe dividirse en los siguientes namespaces dentro de `static/<app_name>/js/`:

- `<app_name>.api.js`: SSoT para peticiones HTTP al DRF API.
- `<app_name>.list.js`: Inicialización de Tabulator y delegación de eventos globales.
- `<app_name>.editor.js`: Captura de formularios (Offcanvas) y envío de datos.
- `<app_name>.utils.js` (Opcional): Validaciones y helpers puros.

---

## 3. Implementación de Funciones Core

### A. Listar (Tabulator + Event Delegation)
El renderizado se delega a `TabulatorFactory`. Las acciones por fila se gestionan mediante eventos, no funciones en línea.

```javascript
// <app_name>.list.js
const DOM = { grid: '#grid-entidad', search: '#search-entidad' };

// 1. Inicialización
state.table = window.TabulatorFactory.create(
    DOM.grid,
    '/api/v1/<app_name>/',
    getColumnas(),
    { searchInputSelector: DOM.search }
);

// 2. Columnas con Event Delegation
function getColumnas() {
    return [
        { title: 'Nombre', field: 'nombre', widthGrow: 2 },
        { title: 'Estado', field: 'activo', formatter: TabulatorFactory.formatters.badgeStatus },
        {
            title: 'Acciones',
            formatter: () => `
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" data-action="edit"><i class="bi bi-pencil"></i></button>
                    <button class="btn btn-outline-danger" data-action="delete"><i class="bi bi-trash"></i></button>
                </div>`,
            cellClick: handleCellAction
        }
    ];
}

function handleCellAction(e, cell) {
    const action = e.target.closest('button')?.dataset.action;
    const id = cell.getRow().getData().id;
    
    if (action === 'edit') abrirOffcanvasEdicion(id);
    if (action === 'delete') w.<AppName>Utils.eliminar(id);
}
```

### B. Crear / Editar (HTMX + Vanilla JS)

**1. Solicitud de UI (HTMX en el HTML):**
```html
<!-- Botón de Creación en list.html -->
<button hx-get="/api/v1/<app_name>/render-offcanvas/crear/"
        hx-target="#offcanvas-container-<app_name>"
        hx-swap="innerHTML">
    Nuevo Registro
</button>
```

**2. Captura y Envío (Vanilla JS en editor.js):**
> [!IMPORTANT]
> El Offcanvas no envía datos por sí solo. `editor.js` escucha su aparición e inyecta la lógica.

```javascript
// <app_name>.editor.js
d.addEventListener('shown.bs.offcanvas', (e) => {
    if (e.target.id === 'offcanvas-<app_name>') {
        const form = d.querySelector('#form-<app_name>');
        
        form.addEventListener('submit', async (ev) => {
            ev.preventDefault();
            const data = Object.fromEntries(new FormData(form).entries());
            const id = d.querySelector('#<app_name>-id').value;
            
            // Mutación vía API directa (JSON)
            const method = id ? 'PATCH' : 'POST';
            const url = id ? `/api/v1/<app_name>/${id}/` : `/api/v1/<app_name>/`;
            
            const response = await w.http(method, url, data);
            
            if (response.ok) {
                // ⚠️ v2.62.3: Cerrar offcanvas usando UIManager
                if (w.UIManager?.handleOffcanvas) {
                    w.UIManager.handleOffcanvas(e.target, 'hide');
                } else {
                    bootstrap.Offcanvas.getInstance(e.target)?.hide();
                }
                // Notificar éxito al ecosistema
                d.dispatchEvent(new CustomEvent('entidadGuardada'));
            } else {
                w.UIManager.handleError(response);
            }
        });
    }
});
```

### C. Eliminar (Bloqueo Estricto)

> [!CAUTION]
> **Regla Cero-Automatización:** Si un registro está `activo=true`, NO se debe auto-inactivar. El frontend debe rechazar la eliminación e instar al usuario a editar manualmente el registro.

```javascript
// <app_name>.utils.js
async function eliminar(id, activo) {
    if (activo) {
        w.UIManager.notifyError({ 
            data: { detail: 'No se puede eliminar un registro activo. Inactívelo editando el registro primero.' }
        });
        return;
    }

    // Confirmación SweetAlert
    const confirm = await Swal.fire({ title: '¿Eliminar registro?', icon: 'warning', showCancelButton: true });
    
    if (confirm.isConfirmed) {
        const res = await w.http('DELETE', `/api/v1/<app_name>/${id}/`);
        if (res.ok) {
            d.dispatchEvent(new CustomEvent('entidadEliminada'));
        }
    }
}
```

### D. Actualizar (Sincronización Reactiva)

El módulo principal (`list.js`) simplemente escucha los eventos del DOM emitidos por otros submódulos y actualiza la tabla en memoria sin recargar la página:

```javascript
// <app_name>.list.js
d.addEventListener('entidadGuardada', () => state.table.replaceData());
d.addEventListener('entidadEliminada', () => state.table.replaceData());
```

---

## 4. Checklist de Validación FSD

- [ ] ¿La lógica de creación reside en `editor.js` y no en el HTML?
- [ ] ¿Los botones de creación usan `hx-get` inyectando el Offcanvas en un contenedor vacío?
- [ ] ¿Las mutaciones (POST/PATCH) se envían como JSON vía `w.http`?
- [ ] ¿Se disparan CustomEvents (`entidadGuardada`) tras operaciones exitosas para desacoplar el recargo de la tabla?
- [ ] ¿El borrado valida el estado activo del registro antes de enviar la petición?
