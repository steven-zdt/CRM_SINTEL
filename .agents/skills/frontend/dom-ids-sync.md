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
