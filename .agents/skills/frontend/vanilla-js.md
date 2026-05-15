# Skill: Vanilla JS & Feature-Sliced Design — SINTEL v2.62

**Carga cuando:** Modificar o crear scripts de frontend, interacciones del DOM, validaciones de formularios y módulos JS.

---

## 1. Estructura FSD y Namespaces

Todo código JavaScript debe estar encapsulado en el namespace `window.Sintel.<App_Name>`. 
Prohibido usar scripts globales sin encapsular.

**Estructura de archivos FSD:**
*   `<app_name>.api.js`: Única fuente de verdad para endpoints de la app.
*   `features/<modelo>_list.js`: Controla la grilla (Tabulator) y el listado.
*   `features/<modelo>_editor.js`: Controla modales (Offcanvas) y validación de formularios.

```javascript
// Estructura base
window.Sintel = window.Sintel || {};
window.Sintel.MiApp = window.Sintel.MiApp || {};

window.Sintel.MiApp.Editor = (function() {
    function init() {
        // Inicialización de eventos
    }
    
    return { init };
})();
```

## 2. DOM Shield (Protección de Formularios)

Antes de enviar un formulario, asegurar de que solo los `<input type="hidden">` envíen datos críticos (como ForeignKeys), removiendo el atributo `name` de los selectores visibles.

```javascript
function prepareFormData(formElement) {
    // DOM Shield: Remover temporalmente los nombres de los selects visibles
    const visibleSelects = formElement.querySelectorAll('select.visible-selector');
    visibleSelects.forEach(select => select.removeAttribute('name'));
    
    const formData = new FormData(formElement);
    
    // Restaurar atributos si es necesario...
    return formData;
}
```

## 3. Manejo Centralizado de Errores UI

Toda petición asíncrona que falle debe ser manejada por `UIManager`.

```javascript
try {
    // operacion asincrona
} catch (error) {
    window.UIManager.handleError(error, {
        contexto: '[MiApp:Editor]',
        formElement: miFormulario
    });
}
```

## 4. Reglas Estrictas de Eliminación (UI)

Ver patrón completo en [crud-fsd.md § C. Eliminar (Bloqueo Estricto)](crud-fsd.md).

Regla: si `activo === true`, bloquear DELETE y mostrar error — nunca auto-inactivar.
