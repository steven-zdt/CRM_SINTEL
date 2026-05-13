# Skill: UI Stabilization & Offcanvas Management — SINTEL v2.62.3

**Carga cuando:** El usuario reporta inestabilidad en modales u offcanvas (se abren y cierran solos), backdrops que no desaparecen, o eventos que se disparan múltiples veces tras un swap de HTMX.

---

## 1. Problema: Inestabilidad de Ciclo de Vida (Lifecycle)

En aplicaciones que usan **HTMX**, los fragmentos del DOM se reemplazan dinámicamente. Si un script intenta abrir un Offcanvas de Bootstrap sobre un elemento que acaba de ser reemplazado o que aún conserva una instancia previa en memoria, se producen errores de estado ("opens and closes instantly").

## 2. Solución: UIManager.handleOffcanvas

Todo el manejo de Offcanvas debe delegarse al orquestador central `window.UIManager`.

### Patrón de Uso (General):

```javascript
/**
 * Al recibir un fragmento vía HTMX (htmx:afterSettle)
 */
document.body.addEventListener('htmx:afterSettle', (e) => {
    const target = e.detail.target;
    
    // Si el target es el contenedor esperado
    if (target && target.id === 'mi-contenedor-offcanvas') {
        const offcanvasEl = document.getElementById('mi-offcanvas-id');
        
        if (offcanvasEl && window.UIManager?.handleOffcanvas) {
            // handleOffcanvas se encarga de:
            // 1. Limpiar backdrops huérfanos
            // 2. Destruir instancias previas (dispose)
            // 3. Crear y mostrar la nueva instancia
            window.UIManager.handleOffcanvas(offcanvasEl, 'show');
        }
    }
});
```

## 3. Limpieza Preventiva de Backdrops

Si no se usa el `UIManager`, se debe implementar manualmente la limpieza de backdrops huérfanos que bloquean la interacción:

```javascript
const cleanupBackdrops = () => {
    document.querySelectorAll('.offcanvas-backdrop, .modal-backdrop').forEach(b => b.remove());
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
};
```

## 4. Neutralización de Listeners Duplicados

Cuando HTMX reemplaza el contenido de un modal/offcanvas pero el script de inicialización se ejecuta nuevamente, los listeners de eventos (ej: botones de guardar) pueden duplicarse.

**Solución: Clonación de Nodos o Delegación.**

```javascript
function initFormulario() {
    const btnGuardar = document.querySelector('#btn-guardar');
    if (btnGuardar) {
        // Clonar el botón para eliminar cualquier listener previo adjunto
        const newBtn = btnGuardar.cloneNode(true);
        btnGuardar.parentNode.replaceChild(newBtn, btnGuardar);
        
        newBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            await guardarDatos();
        });
    }
}
```

## 5. Checklist de Implementación por App

- [ ] ¿La app usa `UIManager.handleOffcanvas`?
- [ ] ¿Se limpian los backdrops antes de cada `show()`?
- [ ] ¿Se usa `htmx:afterSettle` para asegurar que el DOM esté listo?
- [ ] ¿Los botones de acción limpian sus listeners previos (clonación)?
- [ ] ¿Se usa `instance.dispose()` si ya existe una instancia de Bootstrap?

## 6. Destrucción Segura de Componentes (Evitar TypeErrors)

Cuando HTMX va a remover un elemento del DOM que tiene una instancia de Bootstrap (Offcanvas/Modal), es **obligatorio** destruir la instancia manualmente para evitar que Bootstrap intente acceder a propiedades de un elemento nulo durante las transiciones.

### Implementación con htmx:beforeCleanupElement:

```javascript
document.body.addEventListener('htmx:beforeCleanupElement', (e) => {
    const el = e.detail.el;
    // Si el elemento que se va a limpiar es un offcanvas o contiene uno
    if (el.classList.contains('offcanvas') || el.querySelector('.offcanvas')) {
        const offcanvasEl = el.classList.contains('offcanvas') ? el : el.querySelector('.offcanvas');
        if (window.UIManager?.destroyOffcanvas) {
            window.UIManager.destroyOffcanvas(offcanvasEl);
        }
    }
});
```

### Método UIManager.destroyOffcanvas:
Este método debe realizar un `dispose()` de la instancia y remover backdrops de forma síncrona.

