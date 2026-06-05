---
name: crud-fsd-frontend
description: Arquitectura CRUD Frontend completa (HTMX + Tabulator + Vanilla JS) para módulos tenant. Usar al construir o refactorizar cualquier interfaz de gestión.
---

# Skill: Arquitectura CRUD Frontend (Feature-Sliced Design)

**Carga cuando:** Construyas o refactorices interfaces CRUD para modelos tenant (Workspace).

---

## 1. Modelo Híbrido SINTEL — Responsabilidades Separadas

> **Corrección arquitectónica crítica:**

| Tecnología | Uso correcto | Prohibido |
|---|---|---|
| **HTMX `hx-get`** | Cargar HTML de offcanvas/partials desde el servidor | Mutaciones (POST/PATCH/DELETE) |
| **Vanilla JS `window.http()`** | Todas las mutaciones de datos con JSON + JWT | Enviar formularios con `hx-post` |
| **Tabulator** | Grilla reactiva, lectura y renderizado | Mutar datos directamente |

---

## 2. Estructura de Archivos

```
static/<app>/js/
  <app>.api.js          SSoT de todos los endpoints
  features/
    <modelo>_list.js    Tabulator + delegación de eventos
    <modelo>_editor.js  Offcanvas + validación + submit
```

---

## 3. Namespace Obligatorio

```javascript
// Patrón base — SIEMPRE encapsular en window.Sintel.<App>
window.Sintel = window.Sintel || {};
window.Sintel.<App> = (function() {
    const state = { table: null };
    const DOM = {
        grid:         '#grid-<modelo>',
        search:       '#search-<modelo>',
        container:    '#offcanvas-container-<app>',
    };

    function init() {
        _initTable();
        _bindEvents();
    }

    return { init, state };
})();
```

---

## 4. A. Listar — Tabulator + Event Delegation

```javascript
// features/<modelo>_list.js
(function() {
    const state = window.Sintel.<App>.state;

    function _initTable() {
        state.table = window.TabulatorFactory.create(
            '#grid-<modelo>',
            '/api/v1/<app>/',
            _getColumnas(),
            { searchInputSelector: '#search-<modelo>' }
        );
    }

    function _getColumnas() {
        return [
            { title: 'Nombre',  field: 'nombre',  widthGrow: 2 },
            { title: 'Sede',    field: 'sede_nombre', width: 140,
              formatter: (cell) => cell.getValue()
                  ? `<span class="badge bg-light text-dark border">${cell.getValue()}</span>`
                  : '<span class="text-muted small">—</span>'
            },
            { title: 'Estado',  field: 'activo',  width: 90, hozAlign: 'center',
              formatter: (cell) => cell.getValue()
                  ? '<span class="badge bg-success">Activo</span>'
                  : '<span class="badge bg-secondary">Inactivo</span>'
            },
            {
                title: 'Acciones', width: 120, hozAlign: 'center', headerSort: false,
                formatter: () => `
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" data-action="edit" title="Editar">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-outline-danger" data-action="delete" title="Eliminar">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>`,
                cellClick: _handleCellAction
            }
        ];
    }

    function _handleCellAction(e, cell) {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        const row = cell.getRow().getData();
        if (btn.dataset.action === 'edit')   _abrirEditar(row.uuid);
        if (btn.dataset.action === 'delete') _eliminar(row);
    }

    function _abrirEditar(uuid) {
        htmx.ajax('GET',
            `/api/v1/<app>/${uuid}/render-offcanvas/editar/`,
            { target: '#offcanvas-container-<app>', swap: 'innerHTML' }
        );
    }

    // Escuchar eventos de mutacion — recarga sin destruir la tabla
    document.body.addEventListener('<modelo>Guardado',  () => state.table?.replaceData());
    document.body.addEventListener('<modelo>Eliminado', () => state.table?.replaceData());
    // HX-Trigger header del backend también puede dispararlo:
    document.body.addEventListener('lista<App>Changed', () => state.table?.replaceData());
})();
```

---

## 5. B. Crear / Editar — HTMX carga UI, Vanilla JS envía datos

**HTML (botón en list.html):**
```html
<button hx-get="/api/v1/<app>/render-offcanvas/crear/"
        hx-target="#offcanvas-container-<app>"
        hx-swap="innerHTML"
        class="btn btn-primary btn-sm">
    <i class="bi bi-plus-lg me-1"></i>Nuevo
</button>
<div id="offcanvas-container-<app>"></div>
```

**JS (editor.js) — el offcanvas envía datos cuando está visible:**
```javascript
// features/<modelo>_editor.js
document.body.addEventListener('htmx:afterSettle', function(e) {
    if (e.detail.target?.id !== 'offcanvas-container-<app>') return;

    const offcanvasEl = document.getElementById('offcanvas-<app>');
    if (!offcanvasEl) return;

    // Abrir con UIManager (limpia backdrops, destruye instancias previas)
    window.UIManager?.handleOffcanvas(offcanvasEl, 'show');

    // Inyectar listener de submit una sola vez (clonar evita duplicados)
    const btn = document.getElementById('btn-guardar-<modelo>');
    if (btn) {
        const fresh = btn.cloneNode(true);
        btn.parentNode.replaceChild(fresh, btn);
        fresh.addEventListener('click', _submitForm);
    }
});

async function _submitForm() {
    const form = document.getElementById('form-<modelo>');
    if (!form) return;

    const uuid = document.getElementById('<modelo>-uuid')?.value || null;
    const data = _collectData(form);

    if (!_validate(data)) return;

    const method = uuid ? 'PATCH' : 'POST';
    const url    = uuid
        ? `/api/v1/<app>/${uuid}/`
        : `/api/v1/<app>/`;

    try {
        const res = await window.http(method, url, data);
        if (res.ok) {
            window.UIManager?.handleOffcanvas(
                document.getElementById('offcanvas-<app>'), 'hide'
            );
            document.body.dispatchEvent(new CustomEvent('<modelo>Guardado'));
        } else {
            window.UIManager?.handleError(res, { contexto: '[<App>:Editor]' });
        }
    } catch (err) {
        window.UIManager?.handleError(err, { contexto: '[<App>:Editor]' });
    }
}

function _collectData(form) {
    const fd = new FormData(form);
    return {
        nombre:   fd.get('nombre') || '',
        // NUNCA: parseInt(fd.get('uuid_campo')) — ver AGENTS.md §27
        sede:     fd.get('sede_uuid') || null,  // UUID directo, sin parseInt
        // ... resto de campos
    };
}

function _validate(data) {
    if (!data.nombre?.trim()) {
        window.UIManager?.notifyError({ data: { detail: 'El nombre es obligatorio.' } });
        return false;
    }
    return true;
}
```

---

## 6. C. Eliminar — Bloqueo Estricto

> **Regla Cero-Automatización:** Si `activo === true`, NO eliminar ni auto-inactivar.

```javascript
async function _eliminar(row) {
    if (row.activo) {
        window.UIManager?.notifyError({
            data: { detail: 'No se puede eliminar un registro activo. Inactívelo primero editándolo.' }
        });
        return;
    }

    const confirm = await Swal.fire({
        title: '¿Eliminar registro?',
        text: `"${row.nombre}" será eliminado permanentemente.`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Sí, eliminar',
        cancelButtonText: 'Cancelar',
    });

    if (!confirm.isConfirmed) return;

    try {
        const res = await window.http('DELETE', `/api/v1/<app>/${row.uuid}/`);
        if (res.ok || res.status === 204) {
            document.body.dispatchEvent(new CustomEvent('<modelo>Eliminado'));
        } else {
            window.UIManager?.handleError(res, { contexto: '[<App>:Delete]' });
        }
    } catch (err) {
        window.UIManager?.handleError(err, { contexto: '[<App>:Delete]' });
    }
}
```

---

## 7. D. Respuesta del Backend — Ciclo Completo

```python
# ViewSet — POST crear / PATCH editar
def perform_create(self, serializer):
    instance = self.service_crear(serializer.validated_data, self.get_empresa_id())
    return instance

def create(self, request, *args, **kwargs):
    serializer = self.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    instance = self.perform_create(serializer)
    out = self.get_serializer(instance)
    headers = self.get_success_headers(out.data)
    resp = Response(out.data, status=status.HTTP_201_CREATED, headers=headers)
    resp['HX-Trigger'] = 'lista<App>Changed'   # notifica al frontend
    return resp
```

---

## 8. Checklist de Validación FSD

- [ ] Mutaciones (POST/PATCH/DELETE) van por `window.http()` — nunca `hx-post`
- [ ] Botones de creación usan `hx-get` + target a container vacío
- [ ] `htmx:afterSettle` inicializa JS post-swap (no hay race conditions)
- [ ] Listener de submit se clona antes de añadir (evita duplicados)
- [ ] UUID del objeto en `<input type="hidden" id="<modelo>-uuid">` — nunca `parseInt()`
- [ ] `_collectData` usa `fd.get('campo')` para UUIDs — nunca conversión numérica
- [ ] Delete valida `activo` antes de enviar petición
- [ ] Backend devuelve `HX-Trigger: lista<App>Changed` tras mutaciones exitosas
- [ ] `document.body.dispatchEvent(new CustomEvent('<modelo>Guardado'))` en éxito
- [ ] `state.table.replaceData()` en respuesta a eventos — no destruir/recrear
