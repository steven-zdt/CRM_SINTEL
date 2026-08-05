# Skill: DOM ID Sync & Selectors — SINTEL v3.16

**Carga cuando:** Escribir o modificar templates HTML (Offcanvas, Modals, Formularios) y enlazar eventos o instancias Bootstrap en módulos JS.

---

## 1. Regla Principal — Sincronización HTML ↔ JS

**Raíz de bug histórico:** desincronización entre `id="..."` en template y selector en JS.

**Acción obligatoria:**
- Al cambiar un `id` en el template → buscar y actualizar en el `.js` correspondiente
- Al cambiar un selector en el `.js` → verificar que el `id` existe en el template
- Herramienta: `grep -rn "offcanvas-<modelo>" apps/tenant/<app>/`

---

## 2. Convención de Nomenclatura — Namespacing por Modelo

```html
<!-- PROHIBIDO — colisiona con otros módulos en el mismo DOM -->
<div class="offcanvas" id="offcanvasCrear">...</div>
<form id="formulario">...</form>
<input id="campo-nombre">

<!-- OBLIGATORIO — prefijo por modelo -->
<div class="offcanvas offcanvas-end" id="offcanvas-<modelo>-crear">...</div>
<form id="form-crear-<modelo>" onsubmit="return false;">...</form>
<input id="<modelo>-nombre" name="nombre">
<input type="hidden" id="<modelo>-uuid" name="uuid">
```

---

## 2.1. ⛔ Colisión de IDs ENTRE módulos en el Workspace SPA (bug recurrente)

**Causa raíz crítica:** `workspace.html` es una SPA — **TODOS los tabs se renderizan a la vez en el mismo DOM**, solo se ocultan con `display:none` (NO se eliminan). Por lo tanto un `id="..."` o `data-spinner="..."` repetido en dos módulos coexiste en el DOM simultáneamente.

`document.querySelector('#grid-X')` devuelve el **primer** elemento en orden de DOM. Si Facturas (que va antes) declara un `#grid-X` oculto, Tabulator del módulo nuevo construye su tabla **dentro del tab oculto de Facturas** → el tab real se ve **vacío** aunque la API devuelva 200 con datos.

**Casos reales (2026-06):** `facturas/list_factura.html` declara sub-grids `#grid-compras` (facturas de compra) y `#grid-ventas` (facturas de venta) para sus sub-pestañas. Colisionaban con los módulos **Compras** (órdenes de compra) y **Ventas** que también usaban `#grid-compras` / `#grid-ventas`. Síntoma: la tabla no listaba. Backend, serializer, scripts y orden de carga eran todos correctos — el bug era puramente la colisión de IDs en el DOM.

**Regla obligatoria:** el `id` del grid Tabulator, el `data-spinner`, `data-grid` y `data-empty-state` deben ser **únicos globalmente** entre TODOS los módulos del workspace, no solo dentro del módulo. Usar nombre específico del listado, no genérico:

```html
<!-- PROHIBIDO — 'compras'/'ventas' colisionan con sub-grids de facturas -->
<div id="grid-compras" data-grid="compras"></div>
<div id="grid-ventas"  data-spinner="ventas"></div>

<!-- OBLIGATORIO — nombre único del listado concreto -->
<div id="grid-ordenes-compra"  data-spinner="ordenes-compra"></div>
<div id="grid-listado-ventas"  data-spinner="listado-ventas"></div>
```

**Antes de crear/renombrar un grid o data-spinner, verificar unicidad en TODO el codebase:**

```bash
grep -rn 'id="grid-<nombre>"' apps/ --include=*.html      # debe haber 0 antes de crearlo
grep -rn 'data-spinner="<nombre>"' apps/ --include=*.html  # idem
```

**Verificar en el HTML renderizado** que el ID aparece exactamente 1 vez (no confiar solo en el conteo de archivos):

```python
# manage.py shell — Client autenticado, HTTP_HOST del tenant
html = c.get('/workspace/', HTTP_HOST=host).content.decode()
assert html.count('id="grid-<nombre>"') == 1   # >1 = colisión → tabla vacía
```

---

## 3. SSoT de Selectores en JS — Objeto DOM

```javascript
// features/<modelo>_editor.js
window.Sintel.<App>.Editor = (function() {

    // SSoT de IDs — cambiar aquí si cambia el template
    const DOM = {
        offcanvasCrear:  'offcanvas-<modelo>-crear',
        offcanvasEditar: 'offcanvas-<modelo>-editar',
        formCrear:       'form-crear-<modelo>',
        formEditar:      'form-editar-<modelo>',
        btnGuardar:      'btn-guardar-<modelo>',
        inputUuid:       '<modelo>-uuid',
        container:       'offcanvas-container-<app>',
    };

    function init() {
        const el = document.getElementById(DOM.offcanvasCrear);
        if (!el) {
            console.error(`[<App>Editor] CRITICAL: #${DOM.offcanvasCrear} no encontrado en el DOM`);
            return;
        }
    }

    return { init, DOM };
})();
```

---

## 4. Data-Attributes para Comportamiento JS

Preferir `data-*` sobre IDs para atar comportamiento a múltiples elementos.

```html
<!-- Template -->
<button data-action="editar-<modelo>"
        data-uuid="{{ obj.uuid }}"
        data-nombre="{{ obj.nombre }}">
  Editar
</button>
```

```javascript
// JS — event delegation en lugar de listener por elemento
document.addEventListener('click', function(e) {
    const btn = e.target.closest('[data-action="editar-<modelo>"]');
    if (!btn) return;

    const uuid   = btn.dataset.uuid;
    const nombre = btn.dataset.nombre;
    // uuid ya es string UUID — sin parseInt()
    _abrirEditar(uuid);
});
```

---

## 5. Condición de Carrera HTMX — Prohibición

```javascript
// PROHIBIDO — el DOM no está listo cuando se ejecuta .show()
async function abrirOffcanvas() {
    await htmx.ajax('GET', url, { target: '#container' });
    bootstrap.Offcanvas.getOrCreateInstance(document.querySelector('.offcanvas')).show(); // ERROR
}

// OBLIGATORIO — esperar htmx:afterSettle
document.body.addEventListener('htmx:afterSettle', function(e) {
    if (e.detail.target?.id !== 'offcanvas-container-<app>') return;
    requestAnimationFrame(function() {
        const el = document.getElementById('offcanvas-<modelo>-crear');
        if (el) window.UIManager?.handleOffcanvas(el, 'show');
    });
});
```

---

## 6. Prohibición — getOrCreateInstance().show() (AGENTS.md §26)

```javascript
// PROHIBIDO — acumula backdrops en el 2do intento → pantalla negra
bootstrap.Offcanvas.getOrCreateInstance(el).show();

// OBLIGATORIO — UIManager gestiona dispose + cleanup + show
window.UIManager.handleOffcanvas(el, 'show');

// Si UIManager no disponible — fallback manual
const prev = bootstrap.Offcanvas.getInstance(el);
if (prev) prev.dispose();
document.querySelectorAll('.offcanvas-backdrop').forEach(b => b.remove());
document.body.style.overflow = '';
new bootstrap.Offcanvas(el).show();
```

---

## 7. Verificación de IDs (comando)

```bash
# Verificar que los IDs del template existen en el JS
grep -n 'id="offcanvas-<modelo>' apps/tenant/<app>/templates/**/*.html
grep -n "'offcanvas-<modelo>" apps/tenant/<app>/static/**/*.js

# Verificar que los selectores del JS tienen match en el template
grep -n "getElementById\|querySelector" apps/tenant/<app>/static/**/*.js \
  | grep "<modelo>"
```

---

## 8. Checklist

- [ ] IDs en templates usan prefijo del modelo: `offcanvas-<modelo>`, `form-crear-<modelo>`
- [ ] Selectores en JS centralizados en objeto `DOM = { ... }` al inicio del módulo
- [ ] `data-uuid` en botones de tabla — no `data-id` (evitar confusión con PK entero)
- [ ] `htmx:afterSettle` con `requestAnimationFrame` — nunca abrir offcanvas síncronamente tras ajax
- [ ] `UIManager.handleOffcanvas(el, 'show')` — nunca `getOrCreateInstance().show()`
- [ ] Al cambiar ID en template: grep en JS. Al cambiar selector en JS: grep en template.
