# Skill: DOM ID Sync & Selectors (Hotfix v2.62.1)

**Carga cuando:** Escribir o modificar templates HTML (Offcanvas, Modals, Formularios, Tablas) y enlazar eventos o instancias UI en módulos JavaScript.

---

## 1. Prevención de Desincronización (Regla Principal)

**Raíz de Bug Histórico:** Desincronización entre los nombres de `id="..."` en los templates HTML y los selectores usados en `document.getElementById()` o librerías de UI (ej. Bootstrap Offcanvas) en JavaScript.

**Acción Obligatoria:** 
CADA VEZ que modifiques el `id` de un elemento en un template `.html` (ej. `offcanvas_crear_empleado.html`), ESTÁS OBLIGADO a realizar una búsqueda en el archivo `.js` correspondiente (`empleado_editor.js`) para actualizar el selector. Lo mismo aplica a la inversa.

## 2. Convención de Nomenclatura Estricta (Namespacing)

Para evitar colisiones entre distintos módulos y garantizar que el JS encuentre el DOM correcto, los IDs DEBEN incluir el nombre del modelo.

```html
<!-- MALA PRÁCTICA (Causa colisiones si hay múltiples offcanvas en el DOM) -->
<div class="offcanvas" id="offcanvasCrear">...</div>
<form id="formularioPrincipal">...</form>

<!-- BUENA PRÁCTICA (SINTEL Standard) -->
<div class="offcanvas" id="offcanvasCrear<Modelo>">...</div>
<form id="formCrear<Modelo>">...</form>
```

## 3. Centralización de Selectores en JavaScript

**PROHIBIDO:** Usar strings mágicos (`'#miFormulario'`) esparcidos por múltiples funciones en JavaScript.
**OBLIGATORIO:** Definir los selectores del DOM como constantes en la parte superior del módulo o en un objeto de configuración (`DOM_ELEMENTS`).

```javascript
// features/<modelo>_editor.js
window.Sintel.<Modulo>.Editor = (function() {
    // 1. Centralización (SSoT de selectores en el JS)
    const DOM = {
        offcanvasCrear: 'offcanvasCrear<Modelo>',
        formCrear: 'formCrear<Modelo>',
        btnSubmit: 'btnGuardar<Modelo>'
    };

    let offcanvasInstance = null;

    function init() {
        const el = document.getElementById(DOM.offcanvasCrear);
        if (!el) {
            console.error(`[EmpleadoEditor] CRITICAL: No se encontró el ID '${DOM.offcanvasCrear}' en el DOM.`);
            return;
        }
        offcanvasInstance = new bootstrap.Offcanvas(el);
    }
    
    return { init };
})();
```

## 4. Uso de Atributos Data (Data-Attributes) para Eventos

Cuando sea posible, prefiere usar `data-*` attributes en lugar de clases CSS o IDs para atar comportamiento JavaScript a botones de tablas o listas.

```html
<!-- HTML -->
<button data-action="editar-<modelo>" data-uuid="{{ <modelo>.uuid }}">Editar</button>
```

```javascript
// JS
document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-action="editar-<modelo>"]');
    if (btn) {
        const uuid = btn.dataset.uuid;
        // ...
    }
});
```

## 5. Prevención de Condiciones de Carrera (HTMX Swap)

**Raíz de Bug Histórico:** Intentar instanciar y activar componentes de la UI (ej. `bootstrap.Offcanvas(...).show()`) inmediatamente después de llamar a `htmx.ajax()`, antes de que HTMX termine de inyectar el nuevo HTML en el DOM. Esto genera un fallo de renderizado o que el componente no se muestre ("silenciosamente").

**Acción Obligatoria:** 
NUNCA actives un Offcanvas o Modal de manera síncrona justo debajo de la llamada a `htmx.ajax`. 
DEBES delegar la activación escuchando el evento `htmx:afterSettle` a nivel del contenedor o del `document.body`.

```javascript
// MALA PRÁCTICA (Condición de carrera)
async function openOffcanvas() {
    await htmx.ajax('GET', url, { target: '#container' });
    // ❌ ERROR: El DOM podría no estar procesado completamente aquí
    bootstrap.Offcanvas.getOrCreateInstance(document.querySelector('.offcanvas')).show();
}

// BUENA PRÁCTICA (SINTEL Standard - Resiliente)
async function openOffcanvas() {
    // Solo hacemos la petición, sin activar la UI aquí
    return htmx.ajax('GET', url, { target: '#container', swap: 'innerHTML' });
}

// Listener centralizado en el módulo (fuera de la función openOffcanvas):
document.body.addEventListener('htmx:afterSettle', (e) => {
    const target = e.detail.target;
    // Verificamos que el swap ocurrió en nuestro contenedor
    if (target && target.id === 'container') {
        const offcanvasEl = target.querySelector('.offcanvas');
        if (offcanvasEl) {
            // ✅ SEGURO: El DOM ya ha sido inyectado y procesado
            if (window.UIManager?.handleOffcanvas) {
                window.UIManager.handleOffcanvas(offcanvasEl, 'show');
            } else {
                bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
            }
        }
    }
});
```
