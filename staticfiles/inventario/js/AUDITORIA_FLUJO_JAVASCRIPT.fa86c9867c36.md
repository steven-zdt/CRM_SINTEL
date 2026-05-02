# Auditoría de Flujo - JavaScript Inventario v2.60

**Fecha de Auditoría:** 2026-02-10  
**Versión del Módulo:** v2.60  
**Ubicación:** `apps/tenant/core/static/core/js/inventario/`

---

## 📋 Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Estructura de Archivos](#estructura-de-archivos)
3. [Arquitectura y Patrones](#arquitectura-y-patrones)
4. [Capa de Datos (API Wrapper)](#capa-de-datos-api-wrapper)
5. [Features (Lógica de Negocio)](#features-lógica-de-negocio)
6. [Módulos Standalone](#módulos-standalone)
7. [Flujos Principales](#flujos-principales)
8. [Eventos y Comunicación](#eventos-y-comunicación)
9. [Dependencias y Orden de Carga](#dependencias-y-orden-de-carga)
10. [Puntos de Atención](#puntos-de-atención)

---

## 1. Resumen Ejecutivo

### 1.1. Propósito

El código JavaScript del módulo **Inventario** implementa la capa de lógica y presentación del frontend usando:
- **Vanilla JavaScript**: Sin dependencias de jQuery
- **Feature-Sliced Architecture**: Separación clara de responsabilidades
- **API-First**: Consumo de APIs REST (DRF)
- **Tabulator Factory**: Motor de tablas interactivas
- **HTMX Integration**: Carga dinámica de contenido
- **Aislamiento Gradual**: Sin bloques try/catch, usa UIManager.handleError()

### 1.2. Arquitectura

```
┌─────────────────────────────────────────┐
│   Capa de Presentación                   │
│   (Tabulator, Bootstrap Offcanvas)       │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│   Features (Lógica de Negocio)          │
│   - inventario_list.js                   │
│   - inventario_editor.js                 │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│   Módulos Standalone (Páginas)          │
│   - productos.page.js                    │
│   - servicios.page.js                    │
│   - activos.page.js                      │
│   - movimientos.page.js                  │
│   - categorias.page.js                   │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│   Capa de Datos (API Wrapper)           │
│   - inventario.api.js                    │
│   Retorna: {ok, status, data}           │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│   HTTP Layer                            │
│   (w.http)                              │
└─────────────────────────────────────────┘
```

### 1.3. Principios de Diseño

- ✅ **Feature-Sliced Architecture**: Separación por features (list, editor)
- ✅ **Standalone Modules**: Módulos independientes (productos, servicios, activos, movimientos, categorias)
- ✅ **Aislamiento Gradual**: Sin bloques try/catch, solo verificar `ok`
- ✅ **Error Boundary Pattern**: Manejo centralizado con UIManager
- ✅ **Event Delegation**: Para elementos cargados dinámicamente (HTMX)
- ✅ **Anti-Zombies Pattern**: Prevenir instancias fantasma de Tabulator

---

## 2. Estructura de Archivos

### 2.1. Organización

```
apps/tenant/core/static/core/js/inventario/
├── inventario.api.js              # Capa de Datos (API Wrapper)
├── features/
│   ├── inventario_list.js         # Feature: Listado y Tabulator
│   └── inventario_editor.js       # Feature: Editor y Offcanvas
├── productos.page.js              # Módulo Standalone: Productos
├── servicios.page.js               # Módulo Standalone: Servicios
├── activos.page.js                # Módulo Standalone: Activos Fijos
├── movimientos.page.js             # Módulo Standalone: Movimientos (Kardex)
└── categorias.page.js             # Módulo Standalone: Categorías
```

### 2.2. Descripción de Archivos

#### 2.2.1. `inventario.api.js`
**Tipo**: Capa de Datos (API Wrapper)  
**Propósito**: Wrapper de API que retorna siempre `{ok, status, data}`

**Características**:
- Resuelve URL base dinámicamente usando `w.Routes` (si está disponible)
- Fallback a URL hardcodeada si `Routes` no está disponible
- Todos los métodos son `async`
- Expone `w.inventarioAPI` globalmente

**Métodos principales**:
```javascript
w.inventarioAPI = {
  productos: { list, get, save, update, delete, stock, kardex, dt },
  servicios: { list, get, save, update, delete, dt },
  activos: { list, get, save, update, delete, dt, list_all },
  movimientos: { list, get, save, dt },
  categorias: { list, get, save, update, delete, resumen, dt }
}
```

#### 2.2.2. `features/inventario_list.js`
**Tipo**: Feature (Lógica de Negocio)  
**Propósito**: Inicialización y gestión de tablas Tabulator

**Características**:
- Inicializa tabla de productos (`#grid-inventario`)
- Maneja búsqueda en tiempo real
- Event delegation para botones de acción
- Anti-Zombies: Destruye instancias previas de Tabulator
- Escucha eventos `inventarioActualizado` para refrescar tabla

**IDs esperados**:
- `#grid-inventario` - Contenedor Tabulator
- `#search-producto` - Input de búsqueda
- `#offcanvas-container-inventario` - Contenedor HTMX

#### 2.2.3. `features/inventario_editor.js`
**Tipo**: Feature (Lógica de Negocio)  
**Propósito**: Editor de productos y ajustes de inventario

**Características**:
- Recolecta datos de formularios (producto, ajuste)
- Validación frontend antes de enviar
- Manejo de errores con UIManager (Error Boundary)
- Cierra Offcanvas después de guardar
- Dispara evento `inventarioActualizado` para refrescar tabla

**IDs esperados**:
- `#form-producto` - Formulario de producto
- `#form-ajuste-inventario` - Formulario de ajuste
- `#btn-guardar-producto` - Botón guardar producto
- `#btn-guardar-ajuste` - Botón guardar ajuste
- `#form-inventario-feedback` - Contenedor de errores

#### 2.2.4. `productos.page.js`
**Tipo**: Módulo Standalone  
**Propósito**: Módulo independiente de productos

**Características**:
- **STANDALONE**: No depende de otros módulos
- Inicializa tabla Tabulator (`#grid-productos`)
- Event delegation para acciones (editar, ver kardex, eliminar)
- Expone API global: `window.InventarioProductosModule`

**IDs esperados**:
- `#grid-productos` - Contenedor Tabulator
- `#search-producto` - Input de búsqueda

#### 2.2.5. `servicios.page.js`
**Tipo**: Módulo Standalone  
**Propósito**: Módulo independiente de servicios

**Características**:
- **STANDALONE**: No depende de otros módulos
- Inicializa tabla Tabulator (`#grid-servicios`)
- Event delegation para acciones (editar, eliminar)
- Expone API global: `window.InventarioServiciosModule`

#### 2.2.6. `activos.page.js`
**Tipo**: Módulo Standalone  
**Propósito**: Módulo independiente de activos fijos

**Características**:
- **STANDALONE**: No depende de otros módulos
- Inicializa tabla Tabulator (`#grid-activos`)
- Event delegation para acciones (editar, eliminar)
- Expone API global: `window.InventarioActivosModule`

#### 2.2.7. `movimientos.page.js`
**Tipo**: Módulo Standalone  
**Propósito**: Módulo independiente de movimientos (Kardex)

**Características**:
- **STANDALONE**: No depende de otros módulos
- Inicializa tabla Tabulator (`#grid-movimientos`)
- Solo lectura: No permite editar/eliminar movimientos (integridad del Kardex)
- Expone API global: `window.InventarioMovimientosModule`

#### 2.2.8. `categorias.page.js`
**Tipo**: Módulo Standalone  
**Propósito**: Módulo independiente de categorías

**Características**:
- **STANDALONE**: No depende de otros módulos
- Inicializa tabla Tabulator (`#grid-categorias`)
- Event delegation para acciones (editar, eliminar)
- Expone API global: `window.categoriasPage`
- Notifica cambios mediante eventos: `'categorias:updated'`

---

## 3. Arquitectura y Patrones

### 3.1. Feature-Sliced Architecture

**Principio**: Separación por features (list, editor)

**Implementación**:
- **Features**: Lógica reutilizable (`inventario_list.js`, `inventario_editor.js`)
- **Pages**: Módulos standalone específicos (`productos.page.js`, etc.)

**Ventajas**:
- **Reutilización**: Features pueden usarse en diferentes contextos
- **Mantenibilidad**: Cambios en features afectan a todos los módulos
- **Testabilidad**: Features pueden testearse independientemente

### 3.2. Standalone Modules

**Principio**: Módulos completamente independientes

**Características**:
- No dependen de otros módulos del inventario
- Otros módulos pueden usarlos, pero ellos no los usan
- Solo exponen API global (`window.InventarioProductosModule`, etc.)

**Ventajas**:
- **Desacoplamiento**: Cambios en un módulo no afectan a otros
- **Carga selectiva**: Solo cargar módulos necesarios
- **Testing**: Testear módulos independientemente

### 3.3. Aislamiento Gradual

**Principio**: Sin bloques try/catch, solo verificar `ok`

**Implementación**:
```javascript
// ✅ CORRECTO
const res = await w.http('POST', '/api/v1/inventario/productos/', data);
if (!res.ok) {
    // Manejar error con UIManager
    if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, MOD, {
            errorContainerSelector: '#form-inventario-feedback'
        });
    }
    return;
}
// Continuar con éxito

// ❌ INCORRECTO
try {
    const res = await w.http('POST', '/api/v1/inventario/productos/', data);
    // ...
} catch (e) {
    // ...
}
```

**Ventajas**:
- **Código más limpio**: Sin anidación de try/catch
- **Manejo centralizado**: UIManager maneja todos los errores
- **Consistencia**: Mismo patrón en todo el código

### 3.4. Error Boundary Pattern

**Principio**: Manejo centralizado de errores

**Implementación**:
```javascript
if (!res.ok) {
    if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, MOD, {
            errorContainerSelector: '#form-inventario-feedback'
        });
    } else {
        // Fallback: Mostrar error básico
        const errorContainer = d.querySelector('#form-inventario-feedback');
        if (errorContainer) {
            errorContainer.classList.remove('d-none');
            errorContainer.innerHTML = `Error: ${res.data?.detail || 'Error desconocido'}`;
        }
    }
    return;
}
```

**Ventajas**:
- **Consistencia**: Mismo formato de errores en toda la app
- **UX mejorada**: Errores se muestran en contenedores específicos
- **Mantenibilidad**: Cambios en manejo de errores en un solo lugar

### 3.5. Event Delegation

**Principio**: Escuchar eventos en contenedores padre

**Implementación**:
```javascript
// Event Delegation para botones de acción
const gridEl = d.querySelector('#grid-inventario');
gridEl.addEventListener('click', async function(e) {
    const btn = e.target.closest('button');
    if (!btn) return;
    
    if (btn.classList.contains('btn-edit-producto')) {
        const id = btn.getAttribute('data-id');
        // ... manejar edición
    }
});
```

**Ventajas**:
- **Funciona con HTMX**: Elementos cargados dinámicamente tienen listeners
- **Performance**: Un solo listener en lugar de múltiples
- **Mantenibilidad**: No requiere reinicializar listeners después de cada carga

### 3.6. Anti-Zombies Pattern

**Principio**: Prevenir instancias fantasma de Tabulator

**Implementación**:
```javascript
// ⚠️ Anti-Zombies v2.60: Singleton global para instancias de Tabulator
if (window.SintelInventarioTables) {
    Object.values(window.SintelInventarioTables).forEach(tb => {
        if (tb && typeof tb.destroy === 'function') {
            try {
                tb.destroy();
            } catch (error) {
                console.warn(`${MOD} Error al destruir instancia zombie:`, error);
            }
        }
    });
}
window.SintelInventarioTables = {};
```

**Ventajas**:
- **Previene memory leaks**: Destruye instancias previas antes de crear nuevas
- **HTMX compatible**: Funciona con recargas dinámicas de contenido
- **Robustez**: Maneja errores al destruir instancias

---

## 4. Capa de Datos (API Wrapper)

### 4.1. `inventario.api.js`

**Propósito**: Wrapper de API que retorna siempre `{ok, status, data}`

#### 4.1.1. Resolución de URL Base

```javascript
async function getApiBase() {
    if (w.Routes && typeof w.Routes.get === 'function') {
        const routesRes = await w.Routes.get('inventario');
        if (routesRes && routesRes.ok && routesRes.data) {
            const routes = routesRes.data;
            // Intentar obtener la URL base desde diferentes estructuras
            if (routes.productos && routes.productos.collection) {
                const base = routes.productos.collection.replace(/\/productos\/?$/, '');
                if (base) return base;
            }
        }
    }
    return API_BASE_FALLBACK; // '/api/v1/inventario'
}
```

**Características**:
- **Dinámico**: Resuelve URL base usando `w.Routes` si está disponible
- **Fallback**: Usa URL hardcodeada si `Routes` no está disponible
- **Async**: Todos los métodos son `async` para resolver rutas dinámicamente

#### 4.1.2. Construcción de URLs con Parámetros

```javascript
function buildUrlWithParams(baseUrl, params = {}) {
    if (!params || Object.keys(params).length === 0) return baseUrl;
    
    const url = new URL(baseUrl, w.location.origin);
    Object.keys(params).forEach(key => {
        const value = params[key];
        if (value !== null && value !== undefined && value !== '') {
            url.searchParams.append(key, String(value));
        }
    });
    return url.pathname + url.search;
}
```

**Características**:
- **Filtrado**: Ignora valores `null`, `undefined` o vacíos
- **Seguridad**: Usa `URL` API para construir URLs seguras
- **GET requests**: NUNCA envía body en GET requests

#### 4.1.3. Estructura de API

```javascript
w.inventarioAPI = {
  productos: {
    list: async (params = {}) => {...},      // GET /productos/
    get: async (id) => {...},                // GET /productos/{id}/
    save: async (payload) => {...},          // POST /productos/
    update: async (id, payload) => {...},    // PATCH /productos/{id}/
    delete: async (id) => {...},             // DELETE /productos/{id}/
    stock: async (id) => {...},              // GET /productos/{id}/stock/
    kardex: async (id) => {...},             // GET /productos/{id}/kardex/
    dt: async () => {...}                    // DEPRECATED: DataTables endpoint
  },
  servicios: {...},
  activos: {...},
  movimientos: {...},
  categorias: {...}
}
```

**Formato de respuesta**:
```javascript
{
  ok: boolean,        // true si la petición fue exitosa
  status: number,     // Código HTTP (200, 400, 500, etc.)
  data: object       // Datos de respuesta o error
}
```

---

## 5. Features (Lógica de Negocio)

### 5.1. `features/inventario_list.js`

**Propósito**: Inicialización y gestión de tablas Tabulator

#### 5.1.1. Inicialización de Tabla

```javascript
function initTable() {
    const gridEl = d.querySelector('#grid-inventario');
    if (!gridEl) {
        console.warn(`${MOD} Contenedor #grid-inventario no encontrado`);
        return;
    }

    // ⚠️ Anti-Zombies: Destruir instancia previa si existe
    if (window.SintelInventarioTables.main) {
        try {
            window.SintelInventarioTables.main.destroy();
        } catch (error) {
            console.warn(`${MOD} Error al destruir tabla previa:`, error);
        }
    }

    // Crear tabla usando TabulatorFactory
    table = w.TabulatorFactory.create(
        '#grid-inventario',
        '/api/v1/inventario/productos/',
        getColumns(),
        tableConfig
    );

    // Guardar instancia en singleton global
    window.SintelInventarioTables.main = table;

    // Inicializar eventos
    initListEvents();
}
```

**Características**:
- **Anti-Zombies**: Destruye instancias previas antes de crear nuevas
- **TabulatorFactory**: Usa motor de tablas estándar
- **Singleton**: Guarda instancia en `window.SintelInventarioTables.main`

#### 5.1.2. Event Delegation

```javascript
function initListEvents() {
    const gridEl = d.querySelector('#grid-inventario');
    if (!gridEl) return;

    // Event Delegation para botones de acción
    gridEl.addEventListener('click', async function(e) {
        const btn = e.target.closest('button');
        if (!btn) return;

        // Botón Editar
        if (btn.classList.contains('btn-edit-producto')) {
            const id = btn.getAttribute('data-id');
            await htmx.ajax('GET', `/api/v1/inventario/productos/gestor-offcanvas/?id=${id}`, {
                target: '#offcanvas-container-inventario',
                swap: 'innerHTML'
            });
            // Mostrar Offcanvas
            const offcanvasEl = d.getElementById('offcanvas-inventario');
            if (offcanvasEl) {
                const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
                offcanvas.show();
            }
            return;
        }

        // Botón Ajustar Stock
        if (btn.classList.contains('btn-ajuste-producto')) {
            // Similar a editar, pero con tipo=ajuste
        }

        // Botón Eliminar
        if (btn.classList.contains('btn-delete-producto')) {
            // Confirmación y eliminación
        }
    });

    // Event Delegation: Clic en fila para editar
    if (table) {
        table.on('rowClick', async function(e, row) {
            const data = row.getData();
            // Cargar formulario de edición
        });
    }
}
```

**Características**:
- **Event Delegation**: Escucha eventos en contenedor padre
- **HTMX Integration**: Carga formularios dinámicamente
- **Bootstrap Offcanvas**: Muestra formularios en Offcanvas

#### 5.1.3. Eventos Personalizados

```javascript
// Escuchar evento de actualización para refrescar tabla
d.addEventListener('inventarioActualizado', function() {
    if (window.SintelInventarioTables.main) {
        window.SintelInventarioTables.main.replaceData();
    }
});
```

**Características**:
- **Comunicación entre módulos**: Eventos personalizados para sincronización
- **Refresco automático**: Tabla se actualiza cuando se guarda un producto

### 5.2. `features/inventario_editor.js`

**Propósito**: Editor de productos y ajustes de inventario

#### 5.2.1. Recolectar Datos de Formulario

```javascript
function recolectarDatosProducto() {
    const form = d.querySelector('#form-producto');
    if (!form) {
        console.error(`${MOD} Formulario #form-producto no encontrado`);
        return null;
    }

    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    // Remover campos vacíos
    Object.keys(data).forEach(key => {
        if (data[key] === '' || data[key] === null) {
            delete data[key];
        }
    });

    // ⚠️ Conversión de tipos numéricos
    if (data.id) data.id = parseInt(data.id);
    if (data.categoria) data.categoria = parseInt(data.categoria);
    if (data.precio_venta) data.precio_venta = parseFloat(data.precio_venta);
    // ... etc

    // ⚠️ Manejo del switch de activo
    const activoSwitch = form.querySelector('#producto-activo');
    if (activoSwitch) {
        data.activo = activoSwitch.checked;
    }

    return data;
}
```

**Características**:
- **FormData API**: Usa API nativa del navegador
- **Limpieza de datos**: Remueve campos vacíos
- **Conversión de tipos**: Convierte strings a números cuando es necesario
- **Manejo de checkboxes**: Convierte checked a boolean

#### 5.2.2. Validación Frontend

```javascript
async function validarMovimiento(data, producto) {
    // Validar que se haya seleccionado un producto
    if (!data.producto_id) {
        return { valid: false, error: 'Debe seleccionar un producto' };
    }

    // Validar que se haya seleccionado un tipo de movimiento
    if (!data.tipo_movimiento) {
        return { valid: false, error: 'Debe seleccionar un tipo de movimiento' };
    }

    // Validar que la cantidad sea positiva
    if (!data.cantidad || data.cantidad <= 0) {
        return { valid: false, error: 'La cantidad debe ser mayor a cero' };
    }

    // ⚠️ Validación crítica: No permitir salidas mayores al stock existente
    const esSalida = data.tipo_movimiento && data.tipo_movimiento.startsWith('SALIDA_');
    
    if (esSalida) {
        let stockActual = null;
        
        if (producto && producto.stock_actual !== undefined) {
            stockActual = parseFloat(producto.stock_actual);
        } else {
            // Si no tenemos el producto en el DOM, obtenerlo de la API
            const res = await w.http('GET', `/api/v1/inventario/productos/${data.producto_id}/`);
            if (res.ok && res.data) {
                stockActual = parseFloat(res.data.stock_actual || 0);
            }
        }

        if (stockActual !== null && data.cantidad > stockActual) {
            return {
                valid: false,
                error: `Stock insuficiente. Disponible: ${stockActual.toFixed(3)}, Solicitado: ${data.cantidad.toFixed(3)}`
            };
        }
    }

    return { valid: true, error: null };
}
```

**Características**:
- **Validación frontend**: Mejora UX al validar antes de enviar
- **Validación crítica**: Verifica stock suficiente para salidas
- **Async**: Puede obtener datos de API si es necesario

#### 5.2.3. Guardar Producto

```javascript
async function guardarProducto() {
    const data = recolectarDatosProducto();
    if (!data) return;

    const id = d.querySelector('#producto-id')?.value;
    const offcanvasEl = d.querySelector('#offcanvas-inventario');
    
    // ⚠️ Error Boundary: Guardar estado original del botón
    const btnGuardar = d.querySelector('#btn-guardar-producto');
    const btnOriginalText = btnGuardar?.innerHTML || '';
    const btnOriginalDisabled = btnGuardar?.disabled || false;
    
    // Mostrar estado de loading
    if (btnGuardar) {
        btnGuardar.disabled = true;
        btnGuardar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Guardando...';
    }

    // Limpiar errores previos
    const errorContainer = d.querySelector('#form-inventario-feedback');
    if (errorContainer) {
        errorContainer.classList.add('d-none');
        errorContainer.innerHTML = '';
    }

    // ⚠️ Aislamiento Gradual: Capa de Datos retorna {ok, status, data}
    let res;
    if (id) {
        res = await w.http('PATCH', `/api/v1/inventario/productos/${id}/`, data);
    } else {
        res = await w.http('POST', '/api/v1/inventario/productos/', data);
    }

    // Restaurar estado del botón
    if (btnGuardar) {
        btnGuardar.disabled = btnOriginalDisabled;
        btnGuardar.innerHTML = btnOriginalText;
    }

    // Manejo de errores con UIManager
    if (!res.ok) {
        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
            w.UIManager.handleError(res, MOD, {
                errorContainerSelector: '#form-inventario-feedback'
            });
        }
        return;
    }

    // Éxito: Cerrar Offcanvas, mostrar feedback y disparar evento
    if (offcanvasEl) {
        const offcanvas = bootstrap.Offcanvas.getInstance(offcanvasEl);
        if (offcanvas) {
            offcanvas.hide();
        }
    }

    if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
        w.SintelFeedback.success(id ? 'Producto actualizado correctamente' : 'Producto creado correctamente');
    }

    // Disparar evento personalizado para refrescar tabla
    d.dispatchEvent(new Event('inventarioActualizado'));
}
```

**Características**:
- **Aislamiento Gradual**: Sin try/catch, solo verificar `ok`
- **Error Boundary**: Manejo centralizado con UIManager
- **UX mejorada**: Loading state, feedback de éxito, cierre automático
- **Comunicación**: Dispara evento para refrescar tabla

---

## 6. Módulos Standalone

### 6.1. Características Comunes

Todos los módulos standalone comparten:

1. **Inicialización de Tabla Tabulator**
2. **Event Delegation para acciones**
3. **API Global expuesta en `window`**
4. **Búsqueda en tiempo real**
5. **Integración con HTMX para formularios**

### 6.2. `productos.page.js`

**API Global**: `window.InventarioProductosModule`

**Métodos expuestos**:
```javascript
window.InventarioProductosModule = {
  refresh: function() {
    if (table) table.replaceData();
  },
  abrirModalCrear: function() {
    // Cargar formulario de creación
  },
  editar: function(id) {
    // Cargar formulario de edición
  },
  verKardex: function(id) {
    // Mostrar Kardex del producto
  },
  eliminar: function(id) {
    // Eliminar producto (con confirmación)
  }
}
```

**Acciones**:
- **Editar**: Carga formulario de edición vía HTMX
- **Ver Kardex**: Muestra historial de movimientos
- **Eliminar**: Elimina producto (solo si está inactivo)

### 6.3. `servicios.page.js`

**API Global**: `window.InventarioServiciosModule`

**Similar a productos**, pero sin:
- Stock (servicios no tienen stock)
- Kardex (servicios no tienen movimientos)

### 6.4. `activos.page.js`

**API Global**: `window.InventarioActivosModule`

**Similar a productos**, pero con:
- **Estado**: Usa `estado` (ACTIVO, MANTENIMIENTO, BAJA, VENDIDO) en lugar de `activo`
- **Sin stock**: Activos fijos no tienen stock

### 6.5. `movimientos.page.js`

**API Global**: `window.InventarioMovimientosModule`

**Características especiales**:
- **Solo lectura**: No permite editar/eliminar movimientos (integridad del Kardex)
- **Solo ver detalles**: Botón de acción solo muestra detalles

### 6.6. `categorias.page.js`

**API Global**: `window.categoriasPage`

**Características especiales**:
- **Eventos personalizados**: Notifica cambios mediante `'categorias:updated'`
- **Resumen**: Puede obtener resumen de ítems asociados

---

## 7. Flujos Principales

### 7.1. Flujo: Crear Producto

```
1. Usuario hace clic en "Nuevo Producto"
   ↓
2. HTMX carga formulario Offcanvas
   hx-get="/api/v1/inventario/productos/gestor-offcanvas/"
   ↓
3. Backend renderiza offcanvas_form.html
   ↓
4. HTMX inserta HTML en #offcanvas-container-inventario
   ↓
5. Evento htmx:afterSwap dispara
   ↓
6. inventario_editor.js detecta nuevo formulario
   - initEditorEvents() configura listeners
   ↓
7. Usuario completa formulario y hace clic en "Guardar"
   ↓
8. inventario_editor.js intercepta el click
   - guardarProducto() recolecta datos
   - Muestra loading state
   ↓
9. Envía POST /api/v1/inventario/productos/
   ↓
10. Backend procesa y retorna respuesta
    ↓
11. Frontend verifica res.ok
    ↓
12. Si ok:
    - Cierra Offcanvas
    - Muestra feedback de éxito
    - Dispara evento 'inventarioActualizado'
    ↓
13. inventario_list.js escucha evento
    - Refresca tabla (replaceData())
```

### 7.2. Flujo: Registrar Entrada/Salida de Stock

```
1. Usuario hace clic en "Entrada/Salida"
   ↓
2. HTMX carga formulario Offcanvas
   hx-get="/api/v1/inventario/productos/gestor-offcanvas/?tipo=ajuste"
   ↓
3. Backend renderiza offcanvas_form.html (tipo=ajuste)
   ↓
4. HTMX inserta HTML y muestra Offcanvas
   ↓
5. Usuario selecciona producto, tipo, cantidad, etc.
   ↓
6. Usuario hace clic en "Registrar Movimiento"
   ↓
7. inventario_editor.js intercepta el click
   - procesarMovimiento() recolecta datos
   - validarMovimiento() valida frontend
   ↓
8. Si validación falla:
    - Muestra error en #form-inventario-feedback
    - Retorna sin enviar
   ↓
9. Si validación pasa:
    - Muestra loading state
    - Envía POST /api/v1/inventario/movimientos/
   ↓
10. Backend crea MovimientoInventario y recalcula stock
    ↓
11. Frontend verifica res.ok
    ↓
12. Si ok:
    - Cierra Offcanvas
    - Muestra feedback de éxito
    - Dispara evento 'inventarioActualizado'
    ↓
13. inventario_list.js escucha evento
    - Refresca tabla (stock actualizado)
```

### 7.3. Flujo: Editar Producto desde Tabla

```
1. Usuario hace clic en botón "Editar" en tabla
   ↓
2. inventario_list.js intercepta el click (Event Delegation)
   - Obtiene ID del producto (data-id)
   ↓
3. HTMX carga formulario Offcanvas
   hx.ajax('GET', `/api/v1/inventario/productos/gestor-offcanvas/?id=${id}`, ...)
   ↓
4. Backend renderiza offcanvas_form.html (con datos del producto)
   ↓
5. HTMX inserta HTML y muestra Offcanvas
   ↓
6. Formulario se pre-llena con datos del producto
   ↓
7. Usuario modifica y guarda
   ↓
8. inventario_editor.js envía PATCH /api/v1/inventario/productos/{id}/
   ↓
9. Backend actualiza y retorna respuesta
   ↓
10. Frontend cierra Offcanvas y refresca tabla
```

### 7.4. Flujo: Búsqueda en Tiempo Real

```
1. Usuario escribe en input de búsqueda
   <input id="search-producto">
   ↓
2. TabulatorFactory escucha evento 'input'
   - Debounce (espera 300ms después de dejar de escribir)
   ↓
3. Tabulator actualiza filtro
   table.setFilter('nombre', 'like', searchTerm)
   ↓
4. Tabulator re-renderiza tabla con resultados filtrados
```

---

## 8. Eventos y Comunicación

### 8.1. Eventos Personalizados

#### 8.1.1. `inventarioActualizado`
**Disparado por**: `inventario_editor.js`  
**Escuchado por**: `inventario_list.js`

**Propósito**: Refrescar tabla cuando se guarda un producto o movimiento

**Uso**:
```javascript
// Disparar evento
d.dispatchEvent(new Event('inventarioActualizado'));

// Escuchar evento
d.addEventListener('inventarioActualizado', function() {
    if (window.SintelInventarioTables.main) {
        window.SintelInventarioTables.main.replaceData();
    }
});
```

#### 8.1.2. `categorias:updated`
**Disparado por**: `categorias.page.js`  
**Escuchado por**: Módulos que usan categorías (opcional)

**Propósito**: Notificar cambios en categorías

### 8.2. Eventos HTMX

#### 8.2.1. `htmx:afterSwap`
**Disparado por**: HTMX cuando inserta HTML  
**Escuchado por**: `inventario_editor.js`, `inventario_list.js`

**Propósito**: Reinicializar listeners cuando se carga contenido dinámicamente

**Uso**:
```javascript
d.addEventListener('htmx:afterSwap', function(event) {
    if (event.detail.target.id === 'offcanvas-container-inventario') {
        setTimeout(init, 100); // Reinicializar listeners
    }
});
```

### 8.3. Eventos Bootstrap

#### 8.3.1. `hidden.bs.offcanvas`
**Disparado por**: Bootstrap cuando se cierra Offcanvas  
**Escuchado por**: `inventario_editor.js`

**Propósito**: Limpiar errores cuando se cierra Offcanvas

**Uso**:
```javascript
const offcanvasEl = d.querySelector('#offcanvas-inventario');
if (offcanvasEl) {
    offcanvasEl.addEventListener('hidden.bs.offcanvas', function() {
        const errorContainer = d.querySelector('#form-inventario-feedback');
        if (errorContainer) {
            errorContainer.classList.add('d-none');
            errorContainer.innerHTML = '';
        }
    });
}
```

---

## 9. Dependencias y Orden de Carga

### 9.1. Dependencias Globales

**Requeridas**:
- `w.http` - Capa HTTP (definido en `lib/http.js`)
- `w.TabulatorFactory` - Motor de tablas (definido en `tabulator.factory.js`)
- `w.UIManager` - Manejo de errores (definido en `ui-manager.js`)
- `w.SintelFeedback` - Feedback visual (definido en `sintel-feedback.js`)
- `w.Routes` - Resolución de rutas (opcional, definido en `routes.js`)
- `htmx` - HTMX library (opcional, para carga dinámica)
- `bootstrap` - Bootstrap 5 (opcional, para Offcanvas)

**Opcionales**:
- `w.inventarioAPI` - API wrapper (definido en `inventario.api.js`)

### 9.2. Orden de Carga

**Archivo**: `assets_inventario.html`

**Orden crítico**:
```
1. inventario.api.js
   ↓ (define window.inventarioAPI)
2. features/inventario_list.js
   ↓ (usa window.inventarioAPI, TabulatorFactory)
3. features/inventario_editor.js
   ↓ (usa window.inventarioAPI, UIManager, SintelFeedback)
4. HTMX listeners
   ↓ (reinicializa después de cargar Offcanvas)
```

**⚠️ CRÍTICO**: Scripts NO deben tener `async` o `defer` para garantizar orden

### 9.3. Dependencias entre Módulos

**Standalone Modules**: No dependen entre sí

**Features**: Pueden usarse por múltiples módulos

**API Wrapper**: Usado por todos los módulos

---

## 10. Puntos de Atención

### 10.1. IDs Únicos

⚠️ **CRÍTICO**: Todos los IDs deben ser únicos en la página

**IDs principales**:
- `#grid-inventario`, `#grid-productos`, `#grid-servicios`, etc.
- `#offcanvas-inventario`
- `#form-producto`, `#form-ajuste-inventario`
- `#form-inventario-feedback`

**Riesgo**: Si hay IDs duplicados, JavaScript puede seleccionar el elemento incorrecto

### 10.2. Orden de Scripts

⚠️ **CRÍTICO**: Scripts deben cargarse en orden exacto

**Orden correcto**:
1. `inventario.api.js` (define APIs)
2. `inventario_list.js` (usa APIs)
3. `inventario_editor.js` (usa APIs)

**Riesgo**: Si se invierte el orden, puede haber errores de `undefined`

### 10.3. Anti-Zombies Pattern

⚠️ **ATENCIÓN**: Siempre destruir instancias previas de Tabulator

**Implementación**:
```javascript
if (window.SintelInventarioTables.main) {
    try {
        window.SintelInventarioTables.main.destroy();
    } catch (error) {
        console.warn(`${MOD} Error al destruir tabla previa:`, error);
    }
}
```

**Riesgo**: Si no se destruyen, pueden quedar instancias fantasma (memory leaks)

### 10.4. Event Delegation

⚠️ **ATENCIÓN**: Usar event delegation para elementos cargados dinámicamente

**Razón**: Elementos cargados vía HTMX no tienen listeners directos

**Solución**: Escuchar eventos en contenedor padre y filtrar por `target`

### 10.5. Validación Frontend vs Backend

⚠️ **ATENCIÓN**: Validación frontend es solo UX, validación real está en backend

**Implementación**:
- **Frontend**: Validación básica (campos requeridos, tipos, stock suficiente)
- **Backend**: Validación estricta (permisos, integridad, reglas de negocio)

**Riesgo**: Usuario puede deshabilitar validación frontend, pero backend siempre valida

### 10.6. HTMX y Bootstrap Offcanvas

⚠️ **ATENCIÓN**: Offcanvas debe mostrarse después de que HTMX inserte el HTML

**Solución**: Usar `hx-on::after-request` para mostrar Offcanvas

**Riesgo**: Si se intenta mostrar Offcanvas antes de que HTMX inserte HTML, fallará

### 10.7. Conversión de Tipos

⚠️ **ATENCIÓN**: FormData retorna todos los valores como strings

**Solución**: Convertir explícitamente a números cuando sea necesario

**Ejemplo**:
```javascript
if (data.id) data.id = parseInt(data.id);
if (data.precio_venta) data.precio_venta = parseFloat(data.precio_venta);
```

### 10.8. Manejo de Checkboxes

⚠️ **ATENCIÓN**: FormData no incluye checkboxes no marcados

**Solución**: Obtener valor directamente del elemento

**Ejemplo**:
```javascript
const activoSwitch = form.querySelector('#producto-activo');
if (activoSwitch) {
    data.activo = activoSwitch.checked;
}
```

---

## 11. Mejores Prácticas

### 11.1. Naming Conventions

**Módulos**: `{modulo}.page.js` (ej: `productos.page.js`)  
**Features**: `inventario_{feature}.js` (ej: `inventario_list.js`)  
**APIs**: `{modulo}.api.js` (ej: `inventario.api.js`)

**Constantes**: `MOD = '[inventario.list]'` (para logging)

**IDs**: `#grid-{modulo}`, `#search-{modulo}`, `#form-{tipo}`

### 11.2. Logging

**Formato**: `console.log(\`${MOD} Mensaje\`)`

**Niveles**:
- `console.log()` - Información general
- `console.warn()` - Advertencias (elementos no encontrados, etc.)
- `console.error()` - Errores críticos (dependencias faltantes, etc.)

### 11.3. Error Handling

**Patrón**: Aislamiento Gradual + Error Boundary

**Implementación**:
```javascript
const res = await w.http('POST', '/api/v1/inventario/productos/', data);
if (!res.ok) {
    if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, MOD, {
            errorContainerSelector: '#form-inventario-feedback'
        });
    }
    return;
}
```

### 11.4. Performance

**Optimizaciones**:
- **Lazy loading**: Tablas Tabulator solo se inicializan cuando se muestra el tab
- **Debounce en búsqueda**: Esperar 300ms después de dejar de escribir
- **Event Delegation**: Un solo listener en lugar de múltiples
- **Anti-Zombies**: Destruir instancias previas antes de crear nuevas

---

## 12. Conclusión

El código JavaScript del módulo **Inventario v2.60** implementa una arquitectura moderna y robusta:

✅ **Feature-Sliced Architecture**: Separación clara de responsabilidades  
✅ **Standalone Modules**: Módulos independientes y reutilizables  
✅ **Aislamiento Gradual**: Sin bloques try/catch, manejo centralizado de errores  
✅ **Error Boundary Pattern**: Manejo consistente de errores  
✅ **Event Delegation**: Funciona con elementos cargados dinámicamente  
✅ **Anti-Zombies Pattern**: Previene memory leaks  
✅ **HTMX Integration**: Carga dinámica de contenido sin recargar página  
✅ **Tabulator Factory**: Motor de tablas estándar y optimizado  

**Próximos pasos recomendados**:
1. Agregar tests unitarios para features
2. Documentar casos de uso específicos
3. Implementar loading states más sofisticados
4. Agregar validación de formularios más robusta

---

**Fin del Documento**
