# Auditoría de Flujo - Templates Inventario v2.60

**Fecha de Auditoría:** 2026-02-10  
**Versión del Módulo:** v2.60  
**Ubicación:** `apps/tenant/core/templates/tenant/core/partials/inventario/`

---

## 📋 Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Estructura de Templates](#estructura-de-templates)
3. [Flujos de Interacción](#flujos-de-interacción)
4. [HTMX y Eventos](#htmx-y-eventos)
5. [Integración con JavaScript](#integración-con-javascript)
6. [Patrones de Diseño](#patrones-de-diseño)
7. [Dependencias y Orden de Carga](#dependencias-y-orden-de-carga)
8. [Puntos de Atención](#puntos-de-atención)

---

## 1. Resumen Ejecutivo

### 1.1. Propósito

Los templates del módulo **Inventario** implementan la capa de presentación usando:
- **HTMX**: Para carga dinámica de contenido (Offcanvas)
- **Bootstrap 5**: Para componentes UI (Tabs, Offcanvas, Forms)
- **Tabulator Factory**: Para tablas interactivas (JavaScript)
- **API-First Architecture**: Sin datos server-side, solo estructura HTML

### 1.2. Arquitectura de Templates

```
┌─────────────────────────────────────────┐
│   Template Principal (list.html)        │
│   - Tabs: Existencias | Movimientos    │
│   - Contenedores para Tabulator         │
│   - Contenedor HTMX para Offcanvas      │
└──────────────┬──────────────────────────┘
               │
               ├─── list_productos.html (Tab Existencias)
               ├─── list_movimientos.html (Tab Movimientos)
               ├─── list_servicios.html (Módulo independiente)
               ├─── list_activos.html (Módulo independiente)
               ├─── list_categorias.html (Módulo independiente)
               │
               └─── offcanvas_form.html (HTMX)
                    ├─── Formulario Producto
                    └─── Formulario Ajuste Inventario
```

### 1.3. Principios de Diseño

- ✅ **API-First**: Sin datos server-side, solo estructura HTML
- ✅ **HTMX Progressive Enhancement**: Carga dinámica sin recargar página
- ✅ **Error Boundary Pattern**: Contenedores de errores en cada formulario
- ✅ **Zero Trust**: Validación en backend, frontend solo UI
- ✅ **Feature-Sliced Architecture**: Templates modulares e independientes

---

## 2. Estructura de Templates

### 2.1. Template Principal: `list.html`

**Propósito**: Vista principal con navegación por Tabs

**Estructura**:
```html
<div id="tab-inventario-content">
  <!-- Tabs Navigation -->
  <ul class="nav nav-tabs" id="inventario-tabs">
    <li>Tab: Existencias</li>
    <li>Tab: Movimientos Recientes</li>
  </ul>
  
  <!-- Tab Content -->
  <div class="tab-content">
    <!-- Tab: Existencias (Productos) -->
    <div id="pane-existencias">
      - Toolbar (Entrada/Salida, Nuevo Producto, Refrescar)
      - Input de búsqueda
      - Contenedor Tabulator (#grid-inventario)
    </div>
    
    <!-- Tab: Movimientos Recientes (Kardex) -->
    <div id="pane-movimientos">
      - Toolbar (Registrar Movimiento, Refrescar)
      - Input de búsqueda
      - Contenedor Tabulator (#grid-movimientos)
    </div>
  </div>
  
  <!-- Contenedor HTMX para Offcanvas -->
  <div id="offcanvas-container-inventario"></div>
</div>
```

**Características**:
- **Tabs Bootstrap 5**: Navegación entre Existencias y Movimientos
- **Botones HTMX**: Carga dinámica de Offcanvas sin recargar página
- **Contenedores Tabulator**: `#grid-inventario` y `#grid-movimientos`
- **Sin datos server-side**: Solo estructura HTML, datos vía API

**IDs Críticos**:
- `#tab-inventario-content` - Contenedor principal
- `#inventario-tabs` - Navegación de tabs
- `#pane-existencias` - Tab de productos
- `#pane-movimientos` - Tab de movimientos
- `#grid-inventario` - Tabla Tabulator de productos
- `#grid-movimientos` - Tabla Tabulator de movimientos
- `#offcanvas-container-inventario` - Contenedor HTMX para Offcanvas

### 2.2. Template Offcanvas: `offcanvas_form.html`

**Propósito**: Formulario dinámico (Producto o Ajuste de Inventario)

**Estructura**:
```html
<div class="offcanvas offcanvas-end" id="offcanvas-inventario">
  <div class="offcanvas-header">
    <h5 id="offcanvas-inventario-label">Título dinámico</h5>
    <button class="btn-close" data-bs-dismiss="offcanvas"></button>
  </div>
  
  <div class="offcanvas-body">
    <!-- Contenedor de errores -->
    <div id="form-inventario-feedback" class="alert alert-danger d-none"></div>
    
    {% if tipo_formulario == 'ajuste' %}
      <!-- FORMULARIO DE AJUSTE DE INVENTARIO -->
      <form id="form-ajuste-inventario">
        - Selección de Producto (si no viene pre-seleccionado)
        - Tipo de Movimiento (Entradas/Salidas)
        - Cantidad
        - Costo Unitario
        - Referencia Externa
        - Cliente Referencia (solo para salidas)
        - Observaciones
      </form>
    {% else %}
      <!-- FORMULARIO DE PRODUCTO -->
      <form id="form-producto">
        - Datos Básicos (Código, Nombre, Categoría, Unidad, Descripción)
        - Precios y Costos (Precio Venta, Costo Promedio)
        - Gestión de Stock (Stock Actual, Stock Mínimo)
        - Estado (Activo/Inactivo)
      </form>
    {% endif %}
  </div>
</div>
```

**Características**:
- **Formulario dinámico**: Cambia según `tipo_formulario` (producto/ajuste)
- **Modo creación/edición**: Detecta si hay `producto` en contexto
- **Validación HTML5**: Campos requeridos con `required`
- **Script inline**: Lógica para mostrar/ocultar campo Cliente según tipo de movimiento

**IDs Críticos**:
- `#offcanvas-inventario` - Instancia de Offcanvas Bootstrap
- `#form-inventario-feedback` - Contenedor de errores (Error Boundary)
- `#form-ajuste-inventario` - Formulario de ajuste
- `#form-producto` - Formulario de producto
- `#ajuste-producto-select` - Select de producto (ajuste)
- `#ajuste-tipo-movimiento` - Select de tipo de movimiento
- `#producto-codigo`, `#producto-nombre`, etc. - Campos del formulario de producto

**Contexto Django**:
- `tipo_formulario`: `'producto'` o `'ajuste'`
- `producto`: Instancia de `Producto` (opcional, para edición)
- `categorias`: QuerySet de `CategoriaItem` (para select de categoría)
- `tipos_movimiento`: Lista de choices de `MovimientoInventario.TipoMovimiento`

### 2.3. Templates de Listado

#### 2.3.1. `list_productos.html`

**Propósito**: Tab de productos (usado dentro de `list.html` o independiente)

**Estructura**:
```html
<div class="ui-module">
  <div id="feedback-productos-list" class="alert d-none"></div>
  
  <div class="d-flex justify-content-between">
    <h5>Productos</h5>
    <div class="btn-group">
      <button id="btn-nuevo-producto">Nuevo Producto</button>
      <button onclick="window.InventarioProductosModule?.refresh()">Refrescar</button>
    </div>
  </div>
  
  <input id="search-producto" placeholder="Buscar...">
  <div id="grid-productos"></div>
</div>
```

**IDs Críticos**:
- `#grid-productos` - Contenedor Tabulator
- `#search-producto` - Input de búsqueda
- `#btn-nuevo-producto` - Botón crear producto
- `#feedback-productos-list` - Contenedor de errores

#### 2.3.2. `list_movimientos.html`

**Propósito**: Tab de movimientos/Kardex (usado dentro de `list.html` o independiente)

**Estructura**:
```html
<div class="ui-module">
  <div id="feedback-movimientos-list" class="alert d-none"></div>
  
  <div class="d-flex justify-content-between">
    <h5>Kardex</h5>
    <div class="btn-group">
      <button id="btn-nuevo-movimiento">Registrar Movimiento</button>
      <button onclick="window.InventarioMovimientosModule?.refresh()">Refrescar</button>
    </div>
  </div>
  
  <input id="search-movimiento" placeholder="Buscar...">
  <div id="grid-movimientos"></div>
</div>
```

**IDs Críticos**:
- `#grid-movimientos` - Contenedor Tabulator
- `#search-movimiento` - Input de búsqueda
- `#btn-nuevo-movimiento` - Botón crear movimiento
- `#feedback-movimientos-list` - Contenedor de errores

#### 2.3.3. `list_servicios.html`

**Propósito**: Módulo independiente de servicios

**Estructura**: Similar a `list_productos.html`

**IDs Críticos**:
- `#grid-servicios` - Contenedor Tabulator
- `#search-servicio` - Input de búsqueda
- `#btn-nuevo-servicio` - Botón crear servicio
- `#feedback-servicios-list` - Contenedor de errores

#### 2.3.4. `list_activos.html`

**Propósito**: Módulo independiente de activos fijos

**Estructura**: Similar a `list_productos.html`

**IDs Críticos**:
- `#grid-activos` - Contenedor Tabulator
- `#search-activo` - Input de búsqueda
- `#btn-nuevo-activo` - Botón crear activo
- `#feedback-activos-list` - Contenedor de errores

#### 2.3.5. `list_categorias.html`

**Propósito**: Módulo independiente de categorías

**Estructura**: Similar a `list_productos.html`

**IDs Críticos**:
- `#grid-categorias` - Contenedor Tabulator
- `#search-categoria` - Input de búsqueda
- `#btn-nuevo-categoria` - Botón crear categoría
- `#feedback-categorias-list` - Contenedor de errores

### 2.4. Template Assets: `assets_inventario.html`

**Propósito**: Carga de scripts JavaScript y eventos HTMX

**Estructura**:
```html
{# BLOQUE 1: API Wrapper #}
<script src="inventario.api.js"></script>

{# BLOQUE 2: Features Feature-Sliced #}
<script src="features/inventario_list.js"></script>
<script src="features/inventario_editor.js"></script>

{# HTMX: Reinicializar listeners #}
<script>
  document.addEventListener('htmx:afterSwap', function(event) {
    if (event.detail.target.id === 'offcanvas-container-inventario') {
      // Reinicializar listeners
    }
  });
</script>
```

**Características**:
- **Orden crítico**: Scripts deben cargarse en este orden exacto
- **HTMX Integration**: Reinicializa listeners cuando se carga Offcanvas
- **Sin async/defer**: Scripts bloqueantes para garantizar orden

---

## 3. Flujos de Interacción

### 3.1. Flujo: Crear Producto

```
1. Usuario hace clic en "Nuevo Producto"
   ↓
2. HTMX intercepta el clic (atributo hx-get)
   hx-get="/api/v1/inventario/productos/gestor-offcanvas/"
   hx-target="#offcanvas-container-inventario"
   hx-swap="innerHTML"
   ↓
3. Backend renderiza offcanvas_form.html
   - tipo_formulario = 'producto'
   - producto = None (modo creación)
   - categorias = QuerySet de categorías activas
   ↓
4. HTMX inserta HTML en #offcanvas-container-inventario
   ↓
5. Evento htmx:afterSwap dispara
   - assets_inventario.html detecta el evento
   - Reinicializa listeners (si es necesario)
   ↓
6. JavaScript muestra Offcanvas
   bootstrap.Offcanvas.getOrCreateInstance(el).show()
   ↓
7. Usuario completa formulario y hace clic en "Guardar"
   ↓
8. inventario_editor.js intercepta el submit
   - Recolecta datos del formulario
   - Envía POST /api/v1/inventario/productos/
   ↓
9. Backend procesa y retorna respuesta
   ↓
10. Frontend cierra Offcanvas y muestra notificación
    ↓
11. Frontend dispara evento 'productoGuardado' para refrescar tabla
```

### 3.2. Flujo: Editar Producto

```
1. Usuario hace clic en "Editar" en tabla Tabulator
   ↓
2. inventario_list.js intercepta el clic
   - Obtiene ID del producto
   ↓
3. HTMX carga formulario Offcanvas
   hx-get="/api/v1/inventario/productos/gestor-offcanvas/?id={id}"
   ↓
4. Backend renderiza offcanvas_form.html
   - tipo_formulario = 'producto'
   - producto = Instancia de Producto (modo edición)
   - categorias = QuerySet de categorías activas
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

### 3.3. Flujo: Registrar Entrada/Salida de Stock

```
1. Usuario hace clic en "Entrada/Salida"
   ↓
2. HTMX carga formulario Offcanvas
   hx-get="/api/v1/inventario/productos/gestor-offcanvas/?tipo=ajuste"
   ↓
3. Backend renderiza offcanvas_form.html
   - tipo_formulario = 'ajuste'
   - producto = None (selección manual)
   - tipos_movimiento = Choices de MovimientoInventario.TipoMovimiento
   ↓
4. HTMX inserta HTML y muestra Offcanvas
   ↓
5. Script inline muestra/oculta campo Cliente según tipo de movimiento
   - Si tipo empieza con "SALIDA_": muestra campo Cliente
   - Si no: oculta campo Cliente
   ↓
6. Usuario selecciona producto, tipo, cantidad, etc.
   ↓
7. inventario_editor.js intercepta el submit
   - Recolecta datos del formulario
   - Envía POST /api/v1/inventario/movimientos/
   ↓
8. Backend crea MovimientoInventario y recalcula stock
   ↓
9. Frontend cierra Offcanvas y refresca tabla de productos (stock actualizado)
```

### 3.4. Flujo: Búsqueda en Tiempo Real

```
1. Usuario escribe en input de búsqueda
   <input id="search-producto" placeholder="Buscar...">
   ↓
2. inventario_list.js escucha evento 'input'
   - Debounce (espera 300ms después de dejar de escribir)
   ↓
3. Tabulator actualiza filtro
   table.setFilter('nombre', 'like', searchTerm)
   ↓
4. Tabulator re-renderiza tabla con resultados filtrados
```

### 3.5. Flujo: Cambio de Tab

```
1. Usuario hace clic en tab "Movimientos Recientes"
   ↓
2. Bootstrap 5 activa el tab
   - Muestra #pane-movimientos
   - Oculta #pane-existencias
   ↓
3. Evento 'shown.bs.tab' dispara
   ↓
4. inventario_list.js detecta el cambio
   - Inicializa tabla Tabulator de movimientos (si no está inicializada)
   - Carga datos desde API
```

---

## 4. HTMX y Eventos

### 4.1. Atributos HTMX en Templates

#### 4.1.1. Botón "Nuevo Producto"
```html
<button hx-get="/api/v1/inventario/productos/gestor-offcanvas/" 
        hx-target="#offcanvas-container-inventario" 
        hx-swap="innerHTML"
        hx-on::after-request="if(event.detail.successful){ 
          const el = document.getElementById('offcanvas-inventario'); 
          if(el) bootstrap.Offcanvas.getOrCreateInstance(el).show(); 
        }">
```

**Explicación**:
- `hx-get`: Endpoint que renderiza el formulario
- `hx-target`: Contenedor donde se inserta el HTML
- `hx-swap`: Reemplaza contenido interno (`innerHTML`)
- `hx-on::after-request`: Callback después de la petición (muestra Offcanvas)

#### 4.1.2. Botón "Entrada/Salida"
```html
<button hx-get="/api/v1/inventario/productos/gestor-offcanvas/?tipo=ajuste" 
        hx-target="#offcanvas-container-inventario" 
        hx-swap="innerHTML"
        hx-on::after-request="...">
```

**Diferencia**: Incluye query param `?tipo=ajuste` para cargar formulario de ajuste

### 4.2. Eventos HTMX

#### 4.2.1. `htmx:afterSwap`
**Ubicación**: `assets_inventario.html`

**Propósito**: Reinicializar listeners cuando se carga Offcanvas

```javascript
document.addEventListener('htmx:afterSwap', function(event) {
    if (event.detail.target.id === 'offcanvas-container-inventario') {
        setTimeout(function() {
            console.log('[inventario.assets] Offcanvas cargado vía HTMX');
            // Los event listeners se reinicializan automáticamente en inventario_editor.js
        }, 50);
    }
});
```

**Características**:
- **Delay de 50ms**: Asegura que el DOM esté completamente renderizado
- **Target específico**: Solo actúa cuando el target es `#offcanvas-container-inventario`
- **Reinicialización automática**: `inventario_editor.js` detecta el nuevo formulario

### 4.3. Contenedor HTMX

**ID**: `#offcanvas-container-inventario`

**Ubicación**: `list.html` (fuera del contenedor de tabs)

**Propósito**: Contenedor donde HTMX inserta el HTML del Offcanvas

**Características**:
- **Vacío inicialmente**: Se llena dinámicamente vía HTMX
- **Fuera de tabs**: Evita que se oculte al cambiar de tab
- **Reutilizable**: Se reutiliza para todos los formularios (producto, ajuste)

---

## 5. Integración con JavaScript

### 5.1. Módulos JavaScript

#### 5.1.1. `inventario_list.js`
**Responsabilidades**:
- Inicializar tablas Tabulator (`#grid-inventario`, `#grid-movimientos`)
- Manejar búsqueda en tiempo real
- Escuchar eventos de tabs
- Refrescar tablas cuando se guarda un producto

**Integración con Templates**:
- **IDs esperados**: `#grid-inventario`, `#grid-movimientos`, `#search-producto`, `#search-movimiento`
- **Eventos**: `shown.bs.tab` (cambio de tab), `productoGuardado` (refrescar tabla)

#### 5.1.2. `inventario_editor.js`
**Responsabilidades**:
- Manejar formularios (producto, ajuste)
- Recolectar datos del formulario
- Enviar peticiones a API
- Mostrar errores (Error Boundary Pattern)
- Cerrar Offcanvas después de guardar

**Integración con Templates**:
- **IDs esperados**: `#form-producto`, `#form-ajuste-inventario`, `#btn-guardar-producto`, `#btn-guardar-ajuste`
- **Eventos**: `submit` (formulario), `click` (botones guardar)

### 5.2. Event Delegation

**Patrón**: Event delegation para elementos cargados dinámicamente

**Ejemplo**:
```javascript
// En inventario_editor.js
document.addEventListener('submit', function(e) {
    if (e.target.id === 'form-producto') {
        e.preventDefault();
        guardarProducto();
    }
});
```

**Ventajas**:
- Funciona con elementos cargados dinámicamente (HTMX)
- No requiere reinicializar listeners después de cada carga

### 5.3. APIs Globales

**Módulos expuestos en `window`**:
- `window.inventarioAPI` - Wrapper de API (definido en `inventario.api.js`)
- `window.SintelInventarioTables` - Referencia a tablas Tabulator (opcional)
- `window.InventarioProductosModule` - Módulo de productos (opcional)
- `window.InventarioMovimientosModule` - Módulo de movimientos (opcional)

**Uso en Templates**:
```html
<button onclick="window.InventarioProductosModule?.refresh()">
```

---

## 6. Patrones de Diseño

### 6.1. Error Boundary Pattern

**Implementación**: Contenedor de errores en cada formulario

**Ejemplo**:
```html
<div id="form-inventario-feedback" class="alert alert-danger d-none mb-3" role="alert"></div>
```

**Características**:
- **Clase `d-none`**: Oculto inicialmente
- **Clase `alert-danger`**: Estilo de error de Bootstrap
- **ID único**: `form-inventario-feedback`

**Uso en JavaScript**:
```javascript
if (!res.ok) {
    const errorContainer = document.querySelector('#form-inventario-feedback');
    if (errorContainer) {
        errorContainer.textContent = 'Error: ' + res.data.detail;
        errorContainer.classList.remove('d-none');
    }
}
```

### 6.2. API-First Architecture

**Principio**: Templates no incluyen datos server-side, solo estructura HTML

**Implementación**:
- **Sin datos en contexto**: Templates solo reciben estructura mínima (categorías para select)
- **Datos vía API**: JavaScript carga datos desde API REST
- **HTMX para formularios**: Backend renderiza formularios, pero datos se envían vía API

**Ventajas**:
- **Separación de concerns**: Templates solo UI, lógica en JavaScript
- **Reutilización**: Templates pueden usarse en diferentes contextos
- **Testing**: Fácil testear templates sin datos reales

### 6.3. Progressive Enhancement

**Principio**: Funcionalidad básica sin JavaScript, mejorada con JavaScript

**Implementación**:
- **Formularios HTML5**: Validación nativa del navegador
- **HTMX**: Mejora la experiencia sin recargar página
- **Tabulator**: Mejora tablas con funcionalidades avanzadas

**Fallback**:
- Si JavaScript falla, formularios siguen funcionando (submit tradicional)
- Si HTMX falla, se puede cargar formulario vía link normal

### 6.4. Feature-Sliced Architecture

**Principio**: Templates modulares e independientes

**Implementación**:
- **Templates independientes**: `list_productos.html`, `list_servicios.html`, etc.
- **Reutilización**: Cada template puede usarse solo o dentro de `list.html`
- **Separación de concerns**: Cada template tiene su propio contenedor y IDs

---

## 7. Dependencias y Orden de Carga

### 7.1. Orden de Carga de Scripts

**Archivo**: `assets_inventario.html`

**Orden crítico**:
```
1. inventario.api.js
   ↓ (define window.inventarioAPI)
2. features/inventario_list.js
   ↓ (usa window.inventarioAPI)
3. features/inventario_editor.js
   ↓ (usa window.inventarioAPI)
4. HTMX listeners
   ↓ (reinicializa después de cargar Offcanvas)
```

**⚠️ CRÍTICO**: Scripts NO deben tener `async` o `defer` para garantizar orden

### 7.2. Dependencias de Templates

**Jerarquía**:
```
workspace.html (template base)
  └── Incluye assets_inventario.html
      └── Carga scripts en orden
  └── Incluye list.html (o template específico)
      └── list.html incluye contenedor HTMX
          └── HTMX carga offcanvas_form.html dinámicamente
```

### 7.3. Dependencias de Bootstrap

**Componentes usados**:
- **Bootstrap 5 Tabs**: `nav nav-tabs`, `tab-pane`
- **Bootstrap 5 Offcanvas**: `offcanvas offcanvas-end`
- **Bootstrap 5 Forms**: `form-control`, `form-select`, `form-check`
- **Bootstrap 5 Alerts**: `alert alert-danger`

**Versión**: Bootstrap 5.x (requerido)

### 7.4. Dependencias de HTMX

**Versión**: HTMX 1.x (requerido)

**Atributos usados**:
- `hx-get`: Petición GET
- `hx-target`: Target para insertar HTML
- `hx-swap`: Modo de inserción (`innerHTML`)
- `hx-on::after-request`: Callback después de petición

---

## 8. Puntos de Atención

### 8.1. IDs Únicos

⚠️ **CRÍTICO**: Todos los IDs deben ser únicos en la página

**IDs principales**:
- `#tab-inventario-content` - Contenedor principal
- `#grid-inventario` - Tabla de productos
- `#grid-movimientos` - Tabla de movimientos
- `#offcanvas-inventario` - Instancia de Offcanvas
- `#offcanvas-container-inventario` - Contenedor HTMX
- `#form-inventario-feedback` - Contenedor de errores

**Riesgo**: Si hay IDs duplicados, JavaScript puede seleccionar el elemento incorrecto

### 8.2. Orden de Scripts

⚠️ **CRÍTICO**: Scripts deben cargarse en orden exacto

**Orden correcto**:
1. `inventario.api.js` (define APIs)
2. `inventario_list.js` (usa APIs)
3. `inventario_editor.js` (usa APIs)

**Riesgo**: Si se invierte el orden, puede haber errores de `undefined`

### 8.3. HTMX y Bootstrap Offcanvas

⚠️ **ATENCIÓN**: Offcanvas debe mostrarse después de que HTMX inserte el HTML

**Solución**: Usar `hx-on::after-request` para mostrar Offcanvas

```html
hx-on::after-request="if(event.detail.successful){ 
  const el = document.getElementById('offcanvas-inventario'); 
  if(el) bootstrap.Offcanvas.getOrCreateInstance(el).show(); 
}"
```

**Riesgo**: Si se intenta mostrar Offcanvas antes de que HTMX inserte HTML, fallará

### 8.4. Formularios y Validación

⚠️ **ATENCIÓN**: Validación HTML5 es solo UI, validación real está en backend

**Implementación**:
- **Frontend**: Validación HTML5 (`required`, `min`, `max`, `step`)
- **Backend**: Validación estricta en serializers y services

**Riesgo**: Usuario puede deshabilitar validación HTML5, pero backend siempre valida

### 8.5. Contenedor HTMX

⚠️ **ATENCIÓN**: Contenedor HTMX debe estar fuera de tabs

**Razón**: Si está dentro de un tab, se ocultará al cambiar de tab

**Solución**: Colocar `#offcanvas-container-inventario` fuera de `#inventario-tab-content`

### 8.6. Script Inline en Offcanvas

⚠️ **ATENCIÓN**: Script inline en `offcanvas_form.html` solo se ejecuta cuando `tipo_formulario == 'ajuste'`

**Ubicación**: Al final de `offcanvas_form.html`

**Propósito**: Mostrar/ocultar campo Cliente según tipo de movimiento

**Riesgo**: Si se modifica la estructura del formulario, el script puede fallar

### 8.7. Event Delegation

⚠️ **ATENCIÓN**: Usar event delegation para elementos cargados dinámicamente

**Razón**: Elementos cargados vía HTMX no tienen listeners directos

**Solución**: Escuchar eventos en `document` y filtrar por `target.id`

---

## 9. Mejores Prácticas

### 9.1. Naming Conventions

**IDs de contenedores**: `#grid-{modulo}`, `#search-{modulo}`, `#feedback-{modulo}-list`

**IDs de formularios**: `#form-{tipo}`, `#btn-guardar-{tipo}`

**Clases CSS**: Usar clases de Bootstrap 5, evitar clases personalizadas innecesarias

### 9.2. Accesibilidad

**Implementación**:
- **ARIA labels**: `role="region"`, `aria-label`, `aria-labelledby`
- **Semántica HTML**: Usar elementos semánticos (`<form>`, `<button>`, `<input>`)
- **Navegación por teclado**: Bootstrap maneja esto automáticamente

### 9.3. Performance

**Optimizaciones**:
- **Lazy loading**: Tablas Tabulator solo se inicializan cuando se muestra el tab
- **Debounce en búsqueda**: Esperar 300ms después de dejar de escribir
- **HTMX caching**: HTMX cachea respuestas automáticamente

### 9.4. Mantenibilidad

**Recomendaciones**:
- **Comentarios en templates**: Explicar secciones complejas
- **IDs descriptivos**: Usar nombres claros y consistentes
- **Separación de concerns**: Templates solo UI, lógica en JavaScript

---

## 10. Conclusión

Los templates del módulo **Inventario v2.60** implementan una arquitectura moderna y robusta:

✅ **HTMX Progressive Enhancement**: Carga dinámica sin recargar página  
✅ **Bootstrap 5 Components**: UI consistente y accesible  
✅ **API-First Architecture**: Separación clara entre UI y datos  
✅ **Error Boundary Pattern**: Manejo centralizado de errores  
✅ **Feature-Sliced Architecture**: Templates modulares e independientes  
✅ **Event Delegation**: Funciona con elementos cargados dinámicamente  

**Próximos pasos recomendados**:
1. Agregar tests de templates (Django template tests)
2. Documentar casos de uso específicos
3. Crear guía de estilos para nuevos templates
4. Implementar loading states en formularios HTMX

---

**Fin del Documento**
