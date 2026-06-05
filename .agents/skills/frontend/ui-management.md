# Skill: UI Stabilization & Offcanvas Management — SINTEL v3.16

**Carga cuando:** Offcanvas/modales con comportamiento inestable (abre y cierra solo), backdrops huérfanos, listeners duplicados tras swap HTMX.

---

## 1. Raíz del Problema — Ciclo de Vida HTMX + Bootstrap

HTMX reemplaza fragmentos del DOM dinámicamente. Si un elemento Bootstrap (Offcanvas/Modal) tiene una instancia en memoria y el DOM se reemplaza, la instancia queda huérfana y produce:
- Backdrop que no desaparece → pantalla negra / interacción bloqueada
- Offcanvas que se abre y cierra instantáneamente
- TypeError al intentar acceder a un elemento nulo

**Solución obligatoria:** usar `window.UIManager.handleOffcanvas()` — nunca `getOrCreateInstance().show()` directamente (AGENTS.md §26).

---

## 2. Apertura Segura — UIManager.handleOffcanvas

```javascript
// CORRECTO — UIManager gestiona el ciclo de vida completo
window.UIManager.handleOffcanvas(offcanvasEl, 'show');

// PROHIBIDO — acumula backdrops en el 2do intento (AGENTS.md §26)
bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
```

### Patrón completo post-HTMX swap

```javascript
document.body.addEventListener('htmx:afterSettle', function(e) {
    const target = e.detail.target;
    if (!target || target.id !== 'offcanvas-container-<app>') return;

    // requestAnimationFrame garantiza que Bootstrap encuentra el elemento en el DOM
    requestAnimationFrame(function() {
        const offcanvasEl = document.getElementById('offcanvas-<app>');
        if (!offcanvasEl) return;

        if (window.UIManager?.handleOffcanvas) {
            // handleOffcanvas: limpia backdrops + destruye instancia previa + crea nueva
            window.UIManager.handleOffcanvas(offcanvasEl, 'show');
        } else {
            // Fallback manual si UIManager no disponible
            _abrirOffcanvasSeguro(offcanvasEl);
        }
    });
});

// Fallback: apertura manual segura
function _abrirOffcanvasSeguro(el) {
    // 1. Destruir instancia previa si existe
    const prev = bootstrap.Offcanvas.getInstance(el);
    if (prev) { try { prev.dispose(); } catch(e) {} }

    // 2. Limpiar backdrops huérfanos
    document.querySelectorAll('.offcanvas-backdrop, .modal-backdrop')
        .forEach(b => b.remove());
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';

    // 3. Crear y mostrar nueva instancia
    new bootstrap.Offcanvas(el).show();
}
```

---

## 3. Cierre Seguro

```javascript
function cerrarOffcanvas(offcanvasEl) {
    if (window.UIManager?.handleOffcanvas) {
        window.UIManager.handleOffcanvas(offcanvasEl, 'hide');
    } else {
        const instance = bootstrap.Offcanvas.getInstance(offcanvasEl);
        if (instance) instance.hide();
    }
}
```

---

## 4. Destrucción antes del swap HTMX

Antes de que HTMX remueva el elemento del DOM, destruir la instancia Bootstrap para evitar TypeError en las transiciones.

```javascript
document.body.addEventListener('htmx:beforeCleanupElement', function(e) {
    const el = e.detail.el;
    const offcanvasEl = el.classList.contains('offcanvas')
        ? el
        : el.querySelector('.offcanvas');

    if (!offcanvasEl) return;

    if (window.UIManager?.destroyOffcanvas) {
        window.UIManager.destroyOffcanvas(offcanvasEl);
    } else {
        const instance = bootstrap.Offcanvas.getInstance(offcanvasEl);
        if (instance) { try { instance.dispose(); } catch(e) {} }
        // Limpiar backdrops en el mismo tick síncrono
        document.querySelectorAll('.offcanvas-backdrop').forEach(b => b.remove());
        document.body.style.overflow = '';
    }
});
```

---

## 5. Listeners Duplicados — Clonar Nodo

Cuando HTMX recarga el contenido del offcanvas y el `init()` se ejecuta de nuevo, los listeners se acumulan. Solución: clonar el botón antes de añadir el listener.

```javascript
function _initBtnGuardar() {
    const btn = document.getElementById('btn-guardar-<modelo>');
    if (!btn) return;

    // Clonar elimina todos los listeners previos adjuntos
    const fresh = btn.cloneNode(true);
    btn.parentNode.replaceChild(fresh, btn);

    fresh.addEventListener('click', _submitForm);
}
```

---

## 6. Limpieza Manual de Backdrops (helper)

```javascript
function limpiarBackdrops() {
    document.querySelectorAll('.offcanvas-backdrop, .modal-backdrop')
        .forEach(b => b.remove());
    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
}
```

---

## 7. Checklist

- [ ] `window.UIManager.handleOffcanvas(el, 'show')` — nunca `getOrCreateInstance().show()`
- [ ] `htmx:afterSettle` con `requestAnimationFrame` antes de abrir
- [ ] `htmx:beforeCleanupElement` destruye instancia Bootstrap antes de swap
- [ ] Listeners de botones clonados antes de añadir (evita duplicados)
- [ ] `bootstrap.Offcanvas.getInstance(el)?.dispose()` antes de crear nueva instancia manual
- [ ] Backdrops limpiados con `limpiarBackdrops()` si se detecta pantalla bloqueada
