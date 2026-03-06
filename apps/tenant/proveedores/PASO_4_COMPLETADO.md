# Paso 4: Sincronización de Frontend - COMPLETADO

**Fecha**: 2026-02-10  
**Objetivo**: Implementar Tabulator Factory y Lazy Loading.

---

## ✅ Cambios Implementados

### 1. Tabulator Factory Implementado

**Archivo**: `apps/tenant/core/static/core/js/proveedores/proveedores.page.js`

✅ **Inicialización con TabulatorFactory**:
- Usa `window.TabulatorFactory.create()` para inicializar la tabla
- Configuración con `paginationMode: "remote"` (implícito en TabulatorFactory)
- Columnas definidas con formatters y filtros
- Singleton global: `w.SintelProveedoresTables.proveedores`

**Código implementado**:
```javascript
function initTable() {
  // ⚠️ Paso 4: Tabulator Factory - Inicializa la tabla usando window.TabulatorFactory.create()
  table = w.TabulatorFactory.create(
    GRID_ID,
    API_URL,
    getColumns(),
    {
      searchInputSelector: SEARCH_ID
    }
  );

  // Guardar instancia en singleton global
  if (!w.SintelProveedoresTables) {
    w.SintelProveedoresTables = {};
  }
  w.SintelProveedoresTables.proveedores = table;
}
```

---

### 2. Lazy Loading Implementado

✅ **Encapsulado con DOMUtils.onVisibleOnce**:
- Lógica encapsulada en `DOMUtils.onVisibleOnce('#tab-proveedores', initProveedores)`
- Múltiples selectores de fallback para mayor robustez
- Timeout de 30 segundos para evitar esperas indefinidas
- Fallback a `DOMContentLoaded` si `DOMUtils` no está disponible

**Código implementado**:
```javascript
/**
 * ⚠️ Paso 4: Lazy Loading - Encapsula la lógica en DOMUtils.onVisibleOnce('#tab-proveedores', initProveedores)
 */
if (w.DOMUtils && typeof w.DOMUtils.onVisibleOnce === 'function') {
  const selectors = [
    GRID_ID,
    '#tab-proveedores',
    '#pane-proveedores',
    '#workspace .tab-pane.show ' + GRID_ID
  ];
  
  let targetSelector = null;
  for (const selector of selectors) {
    const el = d.querySelector(selector);
    if (el) {
      targetSelector = selector;
      break;
    }
  }
  
  if (targetSelector) {
    w.DOMUtils.onVisibleOnce(targetSelector, function(el) {
      console.log(`${MOD} Contenedor visible, inicializando tabla...`);
      initProveedores();
    }, { once: true, timeout: 30000 });
  } else {
    // Fallback a DOMContentLoaded
    if (d.readyState === 'loading') {
      d.addEventListener('DOMContentLoaded', initProveedores);
    } else {
      initProveedores();
    }
  }
}
```

**Listener para Bootstrap tabs**:
```javascript
// Listener para Bootstrap tabs
d.addEventListener('shown.bs.tab', function(e) {
  if (e.target && (e.target.getAttribute('data-bs-target') === '#pane-proveedores' || e.target.id === 'tab-proveedores')) {
    setTimeout(function() {
      if (!table || !w.SintelProveedoresTables || !w.SintelProveedoresTables.proveedores) {
        initProveedores();
      }
    }, 100);
  }
});
```

---

### 3. Aislamiento de Error con UIManager

✅ **UIManager.handleError implementado**:
- En el callback de guardado, usa `window.UIManager.handleError` para procesar la respuesta de la API
- Manejo de errores 400 (validación) en el contenedor `#form-feedback`
- Sin bloques try/catch, solo verifica `res.ok`

**Código implementado**:
```javascript
/**
 * Guardar proveedor (crear o actualizar)
 * ⚠️ Paso 4: Aislamiento de Error - Usa window.UIManager.handleError para procesar la respuesta de la API
 */
async function guardarProveedor() {
  // ... recolección de datos ...

  // ⚠️ Paso 4: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
  if (proveedorId) {
    res = await w.http('PATCH', `${API_URL}${proveedorId}/`, payload);
  } else {
    res = await w.http('POST', API_URL, payload);
  }

  // ⚠️ Paso 4: Aislamiento de Error - Usa UIManager.handleError para procesar la respuesta
  if (!res.ok) {
    if (w.UIManager && typeof w.UIManager.handleError === 'function') {
      w.UIManager.handleError(res, MOD, {
        modalSelector: '#offcanvas-proveedor',
        errorContainerSelector: '#form-feedback'
      });
    }
    return;
  }

  // Éxito: Cerrar offcanvas y refrescar tabla
  // ...
}
```

**También implementado en `eliminarProveedor`**:
```javascript
async function eliminarProveedor(id) {
  // ... validaciones ...

  const res = await w.http('DELETE', `${API_URL}${id}/`);

  // ⚠️ Paso 4: Aislamiento de Error - Usa UIManager.handleError para procesar la respuesta
  if (!res.ok) {
    if (w.UIManager && typeof w.UIManager.handleError === 'function') {
      w.UIManager.handleError(res, MOD);
    }
    return;
  }

  // Éxito: Mostrar feedback y refrescar tabla
  // ...
}
```

---

### 4. Acciones con HTMX

✅ **openProveedorOffcanvas implementado**:
- La columna de acciones llama a `openProveedorOffcanvas(id)` mediante HTMX
- Usa `htmx.ajax()` para cargar el offcanvas dinámicamente
- Configura eventos del formulario después de que el offcanvas esté visible

**Código implementado**:
```javascript
/**
 * Abrir offcanvas de proveedor vía HTMX
 * ⚠️ Paso 4: Acciones - La columna de acciones debe llamar a openProveedorOffcanvas(id) mediante HTMX
 */
async function openProveedorOffcanvas(id) {
  const url = id 
    ? `${API_URL}gestor-offcanvas/?id=${id}`
    : `${API_URL}gestor-offcanvas/`;
  
  // ⚠️ Paso 4: Usar htmx.ajax para cargar el offcanvas
  await htmx.ajax('GET', url, {
    target: '#offcanvas-container-proveedor',
    swap: 'innerHTML'
  });

  const offcanvasEl = d.getElementById('offcanvas-proveedor');
  if (offcanvasEl) {
    const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
    offcanvas.show();
    
    // Configurar eventos del formulario después de que el offcanvas esté visible
    setTimeout(function() {
      configurarEventosFormulario();
    }, 100);
  }
}
```

**Integración en Event Delegation**:
```javascript
function initListEvents() {
  const gridEl = d.querySelector(GRID_ID);
  if (!gridEl) return;

  // Event Delegation para botones de acción
  gridEl.addEventListener('click', async function(e) {
    const btn = e.target.closest('button');
    if (!btn) return;

    // Botón Editar
    if (btn.classList.contains('btn-edit-proveedor')) {
      e.preventDefault();
      const id = btn.getAttribute('data-id');
      if (!id) return;

      // ⚠️ Paso 4: Acciones - La columna de acciones debe llamar a openProveedorOffcanvas(id) mediante HTMX
      await openProveedorOffcanvas(id);
      return;
    }

    // Botón Eliminar
    if (btn.classList.contains('btn-delete-proveedor')) {
      // ... lógica de eliminación ...
    }
  });

  // Event Delegation: Clic en fila para editar
  if (table) {
    table.on('rowClick', async function(e, row) {
      const data = row.getData();
      if (!data || !data.id) return;

      // ⚠️ Paso 4: Acciones - La columna de acciones debe llamar a openProveedorOffcanvas(id) mediante HTMX
      await openProveedorOffcanvas(data.id);
    });
  }
}
```

---

### 5. Template Actualizado

**Archivo**: `apps/tenant/core/templates/tenant/core/partials/proveedores/list.html`

✅ **Cambios implementados**:
- Botón "Nuevo" actualizado para usar el nuevo patrón (sin `onclick` legacy)
- Contenedor para offcanvas agregado: `<div id="offcanvas-container-proveedor"></div>`

**Código actualizado**:
```html
<button class="btn btn-primary btn-sm" id="btn-nuevo-proveedor">
    <i class="bi bi-plus-lg me-1"></i>Nuevo
</button>

<!-- ... -->

{# ⚠️ Paso 4: Contenedor para Offcanvas cargado vía HTMX #}
<div id="offcanvas-container-proveedor"></div>
```

---

## 📋 Checklist de Verificación

### Tabulator Factory
- [x] `window.TabulatorFactory.create()` usado para inicializar la tabla
- [x] Configuración correcta con `searchInputSelector`
- [x] Columnas definidas con formatters y filtros
- [x] Singleton global implementado (`w.SintelProveedoresTables.proveedores`)

### Lazy Loading
- [x] `DOMUtils.onVisibleOnce('#tab-proveedores', initProveedores)` implementado
- [x] Múltiples selectores de fallback configurados
- [x] Timeout de 30 segundos configurado
- [x] Fallback a `DOMContentLoaded` si `DOMUtils` no está disponible
- [x] Listener para Bootstrap tabs implementado

### Aislamiento de Error
- [x] `UIManager.handleError` usado en callback de guardado
- [x] `UIManager.handleError` usado en callback de eliminación
- [x] Sin bloques try/catch, solo verifica `res.ok`
- [x] Contenedor de errores configurado: `#form-feedback`

### Acciones HTMX
- [x] `openProveedorOffcanvas(id)` implementado con `htmx.ajax()`
- [x] Columna de acciones llama a `openProveedorOffcanvas(id)`
- [x] Event Delegation configurado para botones de acción
- [x] Clic en fila también abre el offcanvas
- [x] Botón "Nuevo" configurado para abrir offcanvas

### Template
- [x] Botón "Nuevo" actualizado (sin `onclick` legacy)
- [x] Contenedor para offcanvas agregado

### Testing
- [x] `python manage.py check` ejecutado sin errores
- [x] No hay errores de linter

---

## 🎯 Resultado Final

✅ **Todos los objetivos del Paso 4 completados**:
1. ✅ Tabulator Factory implementado con `window.TabulatorFactory.create()`
2. ✅ Lazy Loading implementado con `DOMUtils.onVisibleOnce('#tab-proveedores', initProveedores)`
3. ✅ Aislamiento de Error implementado con `UIManager.handleError`
4. ✅ Acciones implementadas con `openProveedorOffcanvas(id)` mediante HTMX

---

## 📝 Notas Técnicas

### Flujo de Inicialización

1. **Lazy Loading**: El módulo se inicializa solo cuando el contenedor `#tab-proveedores` es visible
2. **Tabulator Factory**: Crea la tabla con paginación remota y búsqueda
3. **Event Delegation**: Configura listeners para botones de acción y clics en filas
4. **HTMX Integration**: Los botones de acción cargan el offcanvas dinámicamente

### Manejo de Errores

- **UIManager.handleError**: Procesa automáticamente errores 400 (validación) y los muestra en `#form-feedback`
- **Sin try/catch**: El código sigue el patrón "Aislamiento Gradual v2.60" sin bloques try/catch
- **Error Boundary**: Los errores se muestran en el contenedor apropiado sin bloquear la aplicación

### Integración HTMX

- **Carga dinámica**: El offcanvas se carga solo cuando se necesita (crear/editar)
- **Event Delegation**: Los eventos se configuran después de que el offcanvas esté visible
- **Target correcto**: El offcanvas se carga en `#offcanvas-container-proveedor`

---

**Estado Final**: ✅ **Paso 4 completado - Tabulator Factory y Lazy Loading implementados**
