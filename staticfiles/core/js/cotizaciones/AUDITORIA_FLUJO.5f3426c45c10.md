# 🔍 Auditoría de Flujo - Módulo Cotizaciones v2.60

## 📋 Resumen Ejecutivo

**Fecha de Auditoría:** 2024-12-19  
**Última Actualización:** 2026-03-04 (Correcciones de validación y guardado aplicadas)  
**Versión:** 2.60  
**Objetivo:** Validar sincronía, coherencia de datos, duplicidad de llamados y flujo completo  
**Estado Final:** ✅ **VALIDADO Y ACTUALIZADO CON CORRECCIONES APLICADAS**

### 🔄 Refactorización Conservadora (2026-01-XX)

**Cambio Principal:** Estructura dinámica basada en banderas booleanas del perfil en lugar de tipos estáticos.

**Impacto:**
- ✅ Editor expone tablas dinámicamente según `usa_equipos`, `usa_materiales`, `usa_mano_obra`
- ✅ Eliminación de validaciones rígidas (como `if (tipo == 'MIXTO')`)
- ✅ Lógica matemática preservada intacta
- ✅ Compatibilidad total con Tabulator Factory v2.40

### 🎯 Transición "User-Driven" / Plantilla Maestra (2026-01-XX)

**Cambio Principal:** El editor de cotizaciones transiciona de un modelo basado en plantillas del backend a un modelo "User-Driven" donde el usuario controla directamente qué módulos activar y los parámetros financieros.

**Características Implementadas:**

1. **Panel de Configuración Dinámica** (`editor_cotizacion.html`):
   - Switches Bootstrap (`.dna-switch`) para activar/desactivar módulos:
     - Equipos (`#switch-equipos` → `#section-equipos`)
     - Materiales (`#switch-materiales` → `#section-materiales`)
     - Mano de Obra (`#switch-servicios` → `#section-servicios`)
   - Campos numéricos (`.dna-finance`) para parámetros financieros:
     - IVA (`#input-iva-porcentaje`)
     - AIU Admin (`#input-aiu-admin`)
     - AIU Imprevistos (`#input-aiu-imprevistos`)
     - AIU Utilidad (`#input-aiu-utilidad`)

2. **Control de Visibilidad y Tablas** (`cotizacion_editor.js`):
   - Listeners para switches: muestran/ocultan contenedores e inicializan/destruyen tablas Tabulator
   - Listeners para inputs financieros: recalculan totales en tiempo real
   - Prevención de fugas de memoria: clonado de elementos antes de agregar listeners (HTMX-safe)
   - Tabulator Factory v2.40: verificación de `d-none` antes de instanciar tablas

3. **Cálculo de Totales** (`actualizarPanelTotales()`):
   - Lee valores desde inputs `.dna-finance` (no desde perfil)
   - Suma solo subtotales de módulos activos (sin `d-none`)
   - Matemática preservada: `subtotal + AIU + IVA = total`

4. **Guardado de Cotización** (`guardarCotizaciónFinal()`) - Actualizado 2026-03-04:
   - ✅ Validación estricta del cliente (debe ser ID numérico)
   - ✅ Validación estricta de la configuración (debe ser ID numérico)
   - ✅ Incluye `fecha_emision` en el payload
   - ✅ Inyecta valores financieros en payload JSON
   - ✅ Incluye solo items de módulos activos
   - ✅ Manejo robusto de errores con UIManager
   - ✅ No requiere llamada a API de configuración para decidir renderizado

**Impacto:**
- ✅ **Independencia de API**: El editor funciona sin llamar obligatoriamente a `/api/v1/cotizaciones/configuracion/{id}/`
- ✅ **Control de Usuario**: El usuario decide qué módulos usar mediante switches
- ✅ **Parámetros Manuales**: IVA y AIU se capturan directamente desde inputs
- ✅ **QA Validado**: Cumplimiento de Tabulator Factory v2.40, prevención de fugas de memoria, matemática correcta

**Archivos Modificados:**
- `apps/tenant/core/templates/tenant/core/partials/cotizaciones/editor_cotizacion.html`
- `apps/tenant/core/static/core/js/cotizaciones/features/cotizacion_editor.js`

**Funciones Clave:**
- `configurarListenersDinamicos()`: Configura listeners para switches e inputs financieros
- `inicializarTablaModulo()`: Inicializa tablas solo si contenedor no tiene `d-none`
- `actualizarPanelTotales()`: Calcula totales desde inputs manuales y módulos activos
- `guardarCotizaciónFinal()`: Construye payload con valores manuales y solo módulos activos

---

## 🌐 URLs de API Identificadas

### 1. `/api/v1/clientes/`
**Propósito:** Obtener lista de clientes activos
**Parámetros Esperados:**
- `page_size=100` (para selects, obtener todos)
- `activo=true` (filtrar solo activos)
- `page=1` (opcional, para paginación)

**Llamadas Identificadas:**
- ✅ `cotizaciones.helpers.js::cargarClientesEnSelect()` → `/api/v1/clientes/?page_size=100&activo=true`
- ⚠️ `cotizaciones.page.js` (tabla principal) → `/api/v1/clientes/?page=1&page_size=10` (sin `activo=true`)

**Estado:** ⚠️ **REQUIERE CORRECCIÓN** - La tabla principal no filtra por activos

---

### 2. `/api/v1/cotizaciones/configuracion/`
**Propósito:** Obtener lista de perfiles de configuración
**Parámetros Esperados:**
- `es_activo=true` (filtrar solo activos)
- `page=1` (paginación)
- `page_size=10` (tamaño de página)

**Llamadas Identificadas:**
- ✅ `cotizaciones.helpers.js::cargarPerfilesEnSelect()` → Con `es_activo=true`
- ✅ `cotizaciones.helpers.js::cargarConfiguracionesEnSelect()` → Con `es_activo=true`
- ✅ `cotizaciones.helpers.js::recargarSelectoresPlantillas()` → Con `es_activo=true`
- ✅ `cotizaciones.page.js::fetchConfiguracionesList()` → Con `es_activo=true` (por defecto)
- ✅ `plantillas_list.js` (Tabulator) → Con `ajaxParams: { es_activo: true }`
- ✅ `cotizaciones.page.js::initConfiguracionesTable()` → Con `ajaxParams: { es_activo: true }`

**Estado:** ✅ **CORRECTO** - Todas las llamadas incluyen `es_activo=true`

### 2.1. `/api/v1/cotizaciones/configuracion/{id}/`
**Propósito:** Obtener detalle completo de un perfil de configuración (incluye banderas booleanas)
**Parámetros Esperados:**
- `id`: ID del perfil

**Respuesta Esperada:**
```json
{
  "id": 1,
  "nombre_configuracion": "Plantilla Industrial",
  "usa_equipos": true,
  "usa_materiales": true,
  "usa_mano_obra": false,
  "iva_porcentaje_default": "19.00",
  ...
}
```

**Llamadas Identificadas:**
- ⚠️ `cotizacion_editor.js::renderizarEditorDinamico()` → `/api/v1/cotizaciones/configuracion/${perfilId}/` (OPCIONAL, deprecated)

**Estado:** ⚠️ **OPCIONAL EN MODO USER-DRIVEN** - La función `renderizarEditorDinamico()` existe pero NO se llama obligatoriamente. El editor funciona en modo "User-Driven" sin depender de esta API. El usuario controla los módulos mediante switches y parámetros financieros mediante inputs manuales.

---

### 3. `/api/v1/cotizaciones/`
**Propósito:** Obtener lista de cotizaciones
**Parámetros Esperados:**
- `page=1` (paginación)
- `page_size=10` (tamaño de página)
- `search=` (búsqueda opcional)

**Llamadas Identificadas:**
- ✅ `cotizaciones.page.js` (Tabulator principal) → `/api/v1/cotizaciones/?page=1&page_size=10`

**Estado:** ✅ **CORRECTO**

---

## 📦 Archivos JavaScript Cargados

### Orden de Carga (assets_cotizaciones.html)

1. ✅ `assets_core.html` (incluye http.js, DOMUtils, TabulatorFactory)
2. ✅ `cotizaciones.api.js?v=2.60.2` (define `window.cotizacionesAPI`)
3. ✅ `htmx-handlers.js?v=2.60.2` (manejo de errores HTMX)
4. ✅ `cotizaciones.helpers.js?v=2.60.2` (define `window.CotizacionesHelpers`)
5. ✅ `cotizaciones.page.js?v=2.60.2` (página principal con Tabulator)
6. ✅ `features/cotizacion_editor.js?v=2.60.wizard` (editor de cotizaciones)

**Estado:** ✅ **ORDEN CORRECTO** - Las dependencias se cargan antes de los módulos que las usan

---

## 🔄 Análisis de Duplicidad

### Llamadas Potencialmente Duplicadas

#### Escenario 1: Editor Abierto + Tabla Principal Visible
**Cuando:** Usuario abre el editor de cotización en modo borrador

**Llamadas:**
1. `cargarClientesEnSelect()` → `/api/v1/clientes/?page_size=100&activo=true`
2. `cargarPerfilesEnSelect()` → `/api/v1/cotizaciones/configuracion/?es_activo=true`
3. Tabla principal (si está visible) → `/api/v1/cotizaciones/?page=1&page_size=10`
4. Tabla de configuraciones (si está visible) → `/api/v1/cotizaciones/configuracion/?es_activo=true&page=1&page_size=10`

**Análisis:** ✅ **NORMAL** - Cada componente necesita sus propios datos. No hay duplicación real.

#### Escenario 2: Múltiples Inicializaciones del Editor
**Cuando:** HTMX recarga el editor múltiples veces

**Protección:** ✅ `window.cotizacionEditorInitialized` previene inicializaciones duplicadas

**Estado:** ✅ **PROTEGIDO**

---

## 🔗 Sincronía Frontend-Backend

### Mapeo de Campos

#### Clientes API → Select
```javascript
// Backend retorna:
{
  id: 1,
  razon_social: "Cliente SAS",
  numero_documento: "10000000"
}

// Frontend mapea:
option.value = String(cliente.id)  // ✅ Correcto
option.textContent = `${cliente.razon_social} (${cliente.numero_documento})`  // ✅ Correcto
```

**Estado:** ✅ **SINCRONIZADO**

#### Configuraciones API → Select
```javascript
// Backend retorna:
{
  id: 40,
  nombre_configuracion: "Completo",
  tipo_plantilla: "MIXTO",
  tipo_plantilla_display: "Mixto",
  es_activo: true,
  iva_porcentaje_default: "19.00",
  usa_equipos: true,        // ⚠️ v2.60: Banderas booleanas
  usa_materiales: true,     // ⚠️ v2.60: Banderas booleanas
  usa_mano_obra: false      // ⚠️ v2.60: Banderas booleanas
}

// Frontend mapea:
option.value = String(perfil.id)  // ✅ Correcto
option.textContent = `${perfil.nombre_configuracion} (${perfil.tipo_plantilla_display || perfil.tipo_plantilla}) ✓`  // ✅ Correcto
option.setAttribute('data-iva', perfil.iva_porcentaje_default)  // ✅ Correcto
```

**Estado:** ✅ **SINCRONIZADO**

#### Configuraciones API → Editor Dinámico
```javascript
// Backend retorna (GET /api/v1/cotizaciones/configuracion/{id}/):
{
  id: 40,
  nombre_configuracion: "Plantilla Industrial",
  usa_equipos: true,        // ⚠️ v2.60: Banderas para renderizado dinámico
  usa_materiales: true,
  usa_mano_obra: false,
  iva_porcentaje_default: "19.00",
  ...
}

// Frontend usa directamente:
renderizarEditorDinamico(perfilId) {
  const perfil = res.data;
  // ⚠️ v2.60: Lectura directa de banderas (reemplaza validaciones rígidas)
  if (perfil.usa_equipos) { /* mostrar sección equipos */ }
  if (perfil.usa_materiales) { /* mostrar sección materiales */ }
  if (perfil.usa_mano_obra) { /* mostrar sección servicios */ }
}
```

**Estado:** ✅ **SINCRONIZADO** - Estructura dinámica basada en banderas booleanas

---

## ⚠️ Problemas Identificados

### 1. Tabla Principal de Clientes sin Filtro `activo=true`
**Archivo:** `cotizaciones.page.js`
**Problema:** La tabla principal de cotizaciones puede estar mostrando clientes inactivos si se usa para selección
**Impacto:** Bajo (solo afecta si hay búsqueda de clientes en la tabla)
**Prioridad:** Media
**Solución:** Agregar `activo=true` como parámetro por defecto si es necesario

### 2. Versiones de Cache-Busting Inconsistentes
**Archivos:**
- `cotizaciones.api.js?v=2.60.2`
- `cotizaciones.helpers.js?v=2.60.2`
- `cotizaciones.page.js?v=2.60.2`
- `features/cotizacion_editor.js?v=2.60.wizard`

**Problema:** El editor usa `v=2.60.wizard` mientras otros usan `v=2.60.2`
**Impacto:** Bajo (solo afecta cache del navegador)
**Prioridad:** Baja
**Solución:** Estandarizar a `v=2.60.2` o usar timestamps dinámicos

---

## ✅ Recomendaciones

1. **Estandarizar Versiones:** Usar la misma versión de cache-busting en todos los archivos
2. **Agregar Logs de Auditoría:** Implementar logs detallados en todas las llamadas API
3. **Validar Parámetros:** Asegurar que todas las llamadas incluyan filtros necesarios
4. **Documentar Flujos:** Mantener este documento actualizado con cada cambio

---

## 📊 Métricas de Flujo

### Tiempos Estimados de Carga
- `cotizaciones.api.js`: ~50ms
- `cotizaciones.helpers.js`: ~30ms
- `cotizaciones.page.js`: ~200ms (incluye inicialización de Tabulator)
- `features/cotizacion_editor.js`: ~100ms

**Total:** ~380ms (sin incluir carga de dependencias de `assets_core.html`)

### Llamadas API por Inicialización Completa
- Clientes: 1 llamada (solo si editor está abierto)
- Configuraciones: 1-2 llamadas (editor + tabla si está visible)
- Cotizaciones: 1 llamada (tabla principal)

**Total:** 2-4 llamadas API por carga completa de página

---

## 🔒 Seguridad y Validación

### Validaciones Implementadas
- ✅ Verificación de `window.http` antes de usar
- ✅ Verificación de `window.CotizacionesHelpers` antes de usar
- ✅ Try-catch en todas las llamadas async
- ✅ Validación de estructura de respuesta API
- ✅ Manejo de errores con `UIManager`

**Estado:** ✅ **SEGURO**

---

## 📝 Conclusión

**Estado General:** ✅ **FUNCIONAL** con mejoras menores recomendadas

**Puntos Fuertes:**
- Orden de carga correcto
- Sincronía frontend-backend correcta
- Protección contra inicializaciones duplicadas
- Manejo de errores robusto

**Áreas de Mejora:**
- Estandarizar versiones de cache-busting
- Agregar filtro `activo=true` a tabla principal de clientes (si es necesario)
- Implementar logs de auditoría más detallados

---

## 🔧 Correcciones Finales Aplicadas (2024-12-19)

### Eliminación Completa de sessionStorage
- ✅ **Verificado:** No hay referencias funcionales a `sessionStorage` en `cotizacion_editor.js`
- ✅ **Confirmado:** El editor se autoabastece directamente desde la base de datos
- ✅ **Resultado:** Independencia total del editor - no depende de acciones previas del usuario

### Lectura Dinámica del UUID
- ✅ **Antes:** UUID leído una vez al inicio del script (problema con HTMX)
- ✅ **Ahora:** UUID leído dinámicamente en cada inicialización mediante `getCotizacionUuid()`
- ✅ **Helper Functions:** `isBorrador()` y `getCotizacionUuid()` para acceso dinámico al estado

### Carga Automática de Catálogos
- ✅ **Implementado:** `initEditor()` detecta si `data-cotizacion-uuid` está vacío
- ✅ **Acción Inmediata:** Si es borrador, llama automáticamente a:
  - `window.CotizacionesHelpers.cargarClientesEnSelect(selectCliente)`
  - `window.CotizacionesHelpers.cargarPerfilesEnSelect(selectPerfil)`
- ✅ **Resultado:** Los datos aparecen instantáneamente al abrir el editor

### Alineación de IDs HTML-JS
- ✅ **Verificado:** Todos los IDs coinciden perfectamente:
  - `editor-select-cliente` → HTML línea 21, JS línea 141
  - `editor-select-perfil` → HTML línea 27, JS línea 142
  - `editor-fecha-vencimiento` → HTML línea 33, JS línea 143
  - `btn-guardar-maestro` → HTML línea 119, JS línea 144

### Prevención de Listeners Duplicados
- ✅ **Implementado:** `configurarBotonGuardar()` clona y reemplaza el botón antes de agregar listeners
- ✅ **Implementado:** Botones "Agregar Fila" se clonan antes de agregar listeners
- ✅ **Resultado:** Sin duplicación de eventos en reinicializaciones HTMX

### Parámetros de API Corregidos
- ✅ **Clientes:** `/api/v1/clientes/?page_size=100&activo=true` (correcto)
- ✅ **Configuraciones:** Todas las llamadas incluyen `es_activo=true` (corregido)
- ✅ **Paginación:** Parámetros estándar `page=1&page_size=10` aplicados correctamente

---

---

## 🔄 Refactorización Conservadora - Estructura Dinámica (2026-01-XX)

### Objetivo
Actualizar el editor de cotizaciones para que exponga tablas dinámicamente basándose en las banderas booleanas del perfil (`usa_equipos`, `usa_materiales`, `usa_mano_obra`) en lugar de usar tipos estáticos.

### Cambios Implementados

#### 1. HTML (`editor_cotizacion.html`)
- ✅ **Verificado:** Contenedores tienen IDs únicos (`#section-equipos`, `#section-materiales`, `#section-servicios`)
- ✅ **Verificado:** Todos tienen `d-none` por defecto para evitar saltos visuales
- ✅ **Agregado:** Comentario explicativo sobre secciones dinámicas

#### 2. JavaScript (`cotizacion_editor.js`)

##### Función `renderizarEditorDinamico()` Refactorizada:
- ❌ **Eliminado:** Validaciones rígidas (como `if (tipo == 'MIXTO')`)
- ✅ **Agregado:** Lectura directa de banderas booleanas del perfil:
  - `perfil.usa_equipos` → Muestra/oculta `#section-equipos`
  - `perfil.usa_materiales` → Muestra/oculta `#section-materiales`
  - `perfil.usa_mano_obra` → Muestra/oculta `#section-servicios`
- ✅ **Agregado:** Función `inicializarTablaModulo()` para inicialización dinámica
- ✅ **Agregado:** Error Boundary Pattern con `UIManager.handleError()`
- ✅ **Preservado:** Lógica matemática intacta (`subtotal = cantidad × precio`)

##### Mapeo de Módulos:
```javascript
const modulosUI = [
    { 
        activo: perfil.usa_equipos || false, 
        container: '#section-equipos', 
        grid: '#grid-editor-equipos',
        seccion: 'equipos'
    },
    { 
        activo: perfil.usa_materiales || false, 
        container: '#section-materiales', 
        grid: '#grid-editor-materiales',
        seccion: 'materiales'
    },
    { 
        activo: perfil.usa_mano_obra || false, 
        container: '#section-servicios', 
        grid: '#grid-editor-servicios',
        seccion: 'servicios'
    }
];
```

#### 3. Columnas (`cotizacion_columns.js`)
- ❌ **Eliminado:** `dataType: "number"` de las columnas `cantidad` y `costo_unitario`
- ✅ **Preservado:** Nombres de campos (`field`) sin cambios
- ✅ **Preservado:** Formateadores existentes sin cambios
- ✅ **Preservado:** Función `recalcularFila()` intacta
- ✅ **Actualizado:** Comentarios de documentación

---

## 🎯 Transición "User-Driven" / Plantilla Maestra - Detalles Técnicos (2026-01-XX)

### Arquitectura del Panel de Configuración Dinámica

#### HTML Structure (`editor_cotizacion.html`)

**Panel de Configuración Dinámica:**
```html
<div class="card mb-3 border-info shadow-sm">
  <div class="card-header bg-light fw-bold text-info">
    <i class="bi bi-sliders me-2"></i>Configuración Dinámica
  </div>
  <div class="card-body">
    <!-- Switches de Módulos -->
    <div class="form-check form-switch">
      <input class="form-check-input dna-switch" type="checkbox" 
             id="switch-equipos" 
             data-target="#section-equipos"
             data-seccion="equipos">
      <!-- ... más switches ... -->
    </div>
    
    <!-- Inputs Financieros -->
    <input type="number" 
           class="form-control form-control-sm dna-finance" 
           id="input-iva-porcentaje" 
           step="0.01" min="0" max="100" value="19.00">
    <!-- ... más inputs ... -->
  </div>
</div>
```

**Secciones de Tablas (todas con `d-none` por defecto):**
```html
<div id="section-equipos" class="editor-module d-none mb-4">
  <div id="grid-editor-equipos" class="border rounded"></div>
</div>
<!-- ... más secciones ... -->
```

#### JavaScript Implementation (`cotizacion_editor.js`)

##### 1. Función `configurarListenersDinamicos()`

**Propósito:** Configura listeners para switches e inputs financieros con prevención de fugas de memoria.

**Características:**
- Clonado de elementos antes de agregar listeners (HTMX-safe)
- Listeners para switches: muestran/ocultan contenedores e inicializan/destruyen tablas
- Listeners para inputs financieros: recalculan totales en tiempo real

**Código Clave:**
```javascript
function configurarListenersDinamicos() {
  // Switches: Clonar para prevenir duplicados
  const switches = d.querySelectorAll('.dna-switch');
  switches.forEach(switchEl => {
    const newSwitch = switchEl.cloneNode(true);
    switchEl.parentNode.replaceChild(newSwitch, switchEl);
    
    newSwitch.addEventListener('change', async function(e) {
      const isChecked = e.target.checked;
      const containerSelector = e.target.getAttribute('data-target');
      
      if (isChecked) {
        container.classList.remove('d-none');
        await inicializarTablaModulo(seccion, gridSelector, containerSelector);
      } else {
        container.classList.add('d-none');
        if (tables[seccion]) {
          tables[seccion].destroy();
          delete tables[seccion];
        }
        actualizarPanelTotales(); // Actualización inmediata
      }
    });
  });
  
  // Inputs financieros: Clonar y agregar listener
  const financeInputs = d.querySelectorAll('.dna-finance');
  financeInputs.forEach(input => {
    const newInput = input.cloneNode(true);
    input.parentNode.replaceChild(newInput, input);
    newInput.addEventListener('input', () => actualizarPanelTotales());
  });
}
```

##### 2. Función `inicializarTablaModulo()` - QA v2.60

**Mejora QA:** Verificación de `d-none` antes de instanciar tabla.

```javascript
async function inicializarTablaModulo(seccion, gridSelector, containerSelector) {
  const sectionEl = d.querySelector(containerSelector);
  
  // ⚠️ QA v2.60: Tabulator Factory - NO instanciar tablas en contenedores ocultos
  if (sectionEl.classList.contains('d-none')) {
    console.warn(`${context} Contenedor oculto (d-none), no se inicializará tabla`);
    return;
  }
  
  // ... resto de inicialización ...
}
```

##### 3. Función `actualizarPanelTotales()` - User-Driven

**Cambios Principales:**
- Lee valores desde inputs `.dna-finance` (no desde perfil)
- Suma solo subtotales de módulos activos (verifica `!d-none`)
- Matemática preservada: `subtotal + AIU + IVA = total`

**Código Clave:**
```javascript
function actualizarPanelTotales() {
  let subtotalGeneral = 0;
  
  // Iterar solo sobre módulos activos (sin d-none)
  Object.keys(tables).forEach(key => {
    const container = d.querySelector(seccionesMap[key]);
    if (container && container.classList.contains('d-none')) {
      return; // Módulo desactivado: No incluir
    }
    
    // Sumar subtotales de módulo activo
    const tableData = tables[key].getData();
    tableData.forEach(row => {
      subtotalGeneral += parseFloat(row.subtotal_linea) || 0;
    });
  });
  
  // Leer valores desde inputs manuales
  const ivaPorc = parseFloat(d.getElementById('input-iva-porcentaje').value || 0) / 100;
  const aiuAdminPorc = parseFloat(d.getElementById('input-aiu-admin').value || 0) / 100;
  // ... más inputs ...
  
  // Calcular con matemática preservada
  const aiuTotal = subtotalGeneral * (aiuAdminPorc + aiuImprevPorc + aiuUtilPorc);
  const baseParaIva = subtotalGeneral + aiuTotal;
  const ivaTotal = baseParaIva * ivaPorc;
  const totalConImpuestos = baseParaIva + ivaTotal;
  
  // Pintar en DOM
  d.getElementById('total-subtotal').textContent = fmtMoney(subtotalGeneral);
  d.getElementById('total-iva').textContent = fmtMoney(ivaTotal);
  d.getElementById('total-con-impuestos').textContent = fmtMoney(totalConImpuestos);
}
```

##### 4. Función `guardarCotizaciónFinal()` - User-Driven (Actualizado 2026-03-04)

**Cambios Principales:**
- ✅ Validación estricta del cliente (debe ser ID numérico)
- ✅ Validación estricta de la configuración (debe ser ID numérico)
- ✅ Incluye `fecha_emision` en el payload
- ✅ Inyecta valores financieros en payload JSON
- ✅ Incluye solo items de módulos activos
- ✅ Manejo robusto de errores con UIManager

**Código Clave (Actualizado):**
```javascript
async function guardarCotizaciónFinal() {
  // ⚠️ CRÍTICO: Validación estricta del cliente antes de construir payload
  const selectCliente = d.getElementById('editor-select-cliente');
  const clienteValue = selectCliente?.value;
  if (!clienteValue || isNaN(parseInt(clienteValue, 10))) {
    if (w.UIManager && typeof w.UIManager.showToast === 'function') {
      w.UIManager.showToast('Debe seleccionar un cliente válido de la lista', 'error');
    } else if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
      w.UIManager.notifyError({ 
        status: 400, 
        data: { detail: 'Debe seleccionar un cliente válido de la lista' } 
      }, `[${MOD}]`);
    }
    return;
  }
  const clienteId = parseInt(clienteValue, 10);
  
  // ⚠️ CRÍTICO: Validación estricta de la configuración
  const selectPerfil = d.getElementById('editor-select-perfil');
  const configuracionValue = selectPerfil?.value;
  if (!configuracionValue || isNaN(parseInt(configuracionValue, 10))) {
    if (w.UIManager && typeof w.UIManager.showToast === 'function') {
      w.UIManager.showToast('Debe seleccionar un perfil de configuración válido', 'error');
    }
    return;
  }
  const configuracionId = parseInt(configuracionValue, 10);
  
  // ⚠️ CRÍTICO: Obtener fecha_emision del usuario
  const fechaEmisionInput = d.getElementById('input-fecha-emision');
  const fechaEmision = fechaEmisionInput?.value || null;
  
  const payload = {
    // ⚠️ CRÍTICO: cliente DEBE ser un entero (ID numérico de la base de datos)
    cliente: clienteId,
    // ⚠️ CRÍTICO: configuracion DEBE ser un entero (ID numérico de la base de datos)
    configuracion: configuracionId,
    // ⚠️ v2.60: fecha_emision puede ser proporcionada por el usuario
    fecha_emision: fechaEmision,
    // ⚠️ v2.60: Valores desde inputs manuales (User-Driven)
    tipo_cotizacion: d.getElementById('editor-select-tipo-cotizacion')?.value || 'MIXTO',
    iva_porcentaje: parseFloat(d.getElementById('input-iva-porcentaje')?.value || 0),
    porcentaje_aiu_admin: parseFloat(d.getElementById('input-aiu-admin')?.value || 0),
    porcentaje_aiu_imprevistos: parseFloat(d.getElementById('input-aiu-imprevistos')?.value || 0),
    porcentaje_aiu_utilidad: parseFloat(d.getElementById('input-aiu-utilidad')?.value || 0),
    items: []
  };
  
  // Solo incluir items de módulos activos (sin d-none)
  Object.keys(w.SintelCotizacionTables).forEach(key => {
    const container = d.querySelector(seccionesMap[key]);
    if (container && container.classList.contains('d-none')) {
      return; // Módulo desactivado: No incluir
    }
    
    const table = w.SintelCotizacionTables[key];
    if (table && typeof table.getData === 'function') {
      const data = table.getData().map(item => ({
        ...item,
        tipo_item: key,
        seccion: key
      }));
      payload.items.push(...data);
    }
  });
  
  try {
    await w.cotizacionesAPI.create(payload);
    // Mensaje de éxito y cierre del editor
  } catch (error) {
    // Manejo de errores con UIManager
    if (w.UIManager && typeof w.UIManager.handleError === 'function') {
      w.UIManager.handleError(error);
    }
  }
}
```

**Validaciones Implementadas:**
- ✅ Cliente: Debe ser ID numérico válido (parseInt con validación)
- ✅ Configuración: Debe ser ID numérico válido (parseInt con validación)
- ✅ Fecha de Emisión: Opcional, se envía si el usuario la proporciona
- ✅ Items: Solo de módulos activos (verifica `!d-none`)
- ✅ Valores Financieros: Se capturan desde inputs manuales

**Correcciones Aplicadas (2026-03-04):**
- ✅ Validación estricta de cliente antes de construir payload
- ✅ Validación estricta de configuración antes de construir payload
- ✅ Uso de `parseInt()` explícito para garantizar IDs numéricos
- ✅ Inclusión de `fecha_emision` en el payload
- ✅ Uso de `w.SintelCotizacionTables` (Singleton) en lugar de `tables` local
- ✅ Manejo robusto de errores con UIManager

### Validaciones QA Aplicadas

#### ✅ 1. Tabulator Factory v2.40
- **Verificación:** `inicializarTablaModulo()` verifica `d-none` antes de instanciar
- **Resultado:** No se instancian tablas en contenedores ocultos

#### ✅ 2. Prevención de Fugas de Memoria
- **Verificación:** Clonado de elementos antes de agregar listeners
- **Aplicado a:** Switches (`.dna-switch`), inputs financieros (`.dna-finance`), botón guardar
- **Resultado:** Sin listeners duplicados en recargas HTMX

#### ✅ 3. Matemática de Recálculo
- **Verificación:** Al desactivar switch, se destruye tabla y se actualiza total inmediatamente
- **Resultado:** El total global resta correctamente el valor del módulo desactivado

#### ✅ 4. Independencia de API
- **Verificación:** `renderizarEditorDinamico()` marcada como `@deprecated` y no se llama obligatoriamente
- **Resultado:** El editor funciona sin depender de `/api/v1/cotizaciones/configuracion/{id}/`

### Flujo Completo User-Driven

```
1. Usuario abre editor → init()
   ↓
2. configurarListenersDinamicos() → Configura listeners (HTMX-safe)
   ↓
3. Usuario activa switch "Equipos"
   ↓
4. Listener detecta cambio → Quita d-none de #section-equipos
   ↓
5. inicializarTablaModulo() → Verifica que NO tenga d-none → Crea tabla Tabulator
   ↓
6. Usuario agrega items → Recalcula subtotales → actualizarPanelTotales()
   ↓
7. Usuario cambia IVA en input → Listener detecta input → actualizarPanelTotales()
   ↓
8. actualizarPanelTotales() → Lee IVA desde input → Suma solo módulos activos → Calcula total
   ↓
9. Usuario desactiva switch "Materiales"
   ↓
10. Listener detecta cambio → Añade d-none → Destruye tabla → actualizarPanelTotales() INMEDIATO
   ↓
11. actualizarPanelTotales() → Excluye módulo desactivado → Recalcula total
   ↓
12. Usuario guarda → guardarCotizaciónFinal()
   ↓
13. Construye payload con valores manuales y solo módulos activos
   ↓
14. POST /api/v1/cotizaciones/ → Backend recibe cotización completa
```

### Compatibilidad Legacy

**Función `renderizarEditorDinamico()`:**
- ✅ Mantenida para compatibilidad
- ⚠️ Marcada como `@deprecated`
- ⚠️ No se llama obligatoriamente en modo User-Driven
- ✅ Puede usarse opcionalmente si se necesita inicializar desde perfil

---

### Flujo Actualizado

```
1. Usuario selecciona perfil → renderizarEditorDinamico(perfilId)
   ↓
2. GET /api/v1/cotizaciones/configuracion/{id}/
   ↓
3. Lee banderas booleanas del perfil:
   - usa_equipos
   - usa_materiales
   - usa_mano_obra
   ↓
4. Muestra/oculta secciones dinámicamente:
   - Si usa_equipos = true → Muestra #section-equipos
   - Si usa_materiales = true → Muestra #section-materiales
   - Si usa_mano_obra = true → Muestra #section-servicios
   ↓
5. Inicializa tablas solo para módulos activos:
   - inicializarTablaModulo(seccion, gridSelector, containerSelector)
   ↓
6. Destruye tablas de módulos desactivados
   ↓
7. Actualiza panel de totales (suma solo módulos activos)
```

### Características Preservadas
- ✅ **Lógica Matemática:** Fórmulas intactas (`subtotal = cantidad × precio`)
- ✅ **Agregación de Totales:** Suma global preservada
- ✅ **Tabulator Factory v2.40:** Compatibilidad total
- ✅ **DOMUtils.onVisibleOnce:** Compatibilidad total
- ✅ **Error Boundary Pattern:** Aplicado correctamente
- ✅ **Funciones Existentes:** Reutilizadas (no se crearon funciones innecesarias)

### Estado de la Refactorización
- ✅ **HTML:** Actualizado y verificado
- ✅ **JavaScript Editor:** Refactorizado con banderas dinámicas
- ✅ **JavaScript Columnas:** Limpiado (eliminado dataType)
- ✅ **Lógica Matemática:** Preservada intacta
- ✅ **Compatibilidad:** Total con arquitectura v2.60

---

---

## 🛡️ Correcciones Anti-Zombi / Listeners Fantasma (2026-01-XX)

### Problema Identificado

**Síntoma:** La versión anterior del script (`v=2.60`) seguía viva en memoria después de swaps de HTMX, reaccionaba a eventos de Tabulator, no encontraba las tablas en el nuevo DOM, calculaba $0 y sobrescribía los valores correctos de la nueva instancia.

**Causa Raíz:**
- Variables locales (`tables`) encapsuladas en closures que persistían después de swaps HTMX
- Listeners de eventos acumulándose en cada recarga
- Ejecuciones fantasma en DOM desprendido sin verificación de conexión

### Soluciones Implementadas

#### 1. Patrón Singleton Global (`window.SintelCotizacionTables`)

**Cambio:** Convertir variable local `tables` a objeto global `window.SintelCotizacionTables`

**Implementación:**
```javascript
// Al inicio del archivo
if (!w.SintelCotizacionTables) {
  w.SintelCotizacionTables = {};
}

// En init() - Limpieza de instancias zombis
if (w.SintelCotizacionTables) {
  Object.keys(w.SintelCotizacionTables).forEach(key => {
    const tb = w.SintelCotizacionTables[key];
    if (tb && typeof tb.destroy === 'function') {
      try {
        console.log(`[${MOD}] Limpiando tabla zombie: ${key}`);
        tb.destroy();
      } catch (e) {
        console.warn(`[${MOD}] Error al destruir tabla zombie ${key}:`, e);
      }
    }
  });
}
w.SintelCotizacionTables = {}; // Reiniciar registro global
```

**Resultado:**
- ✅ Solo existe una instancia del objeto de tablas en toda la aplicación
- ✅ Las tablas zombis se destruyen antes de cada reinicialización
- ✅ Todas las referencias a `tables` fueron reemplazadas por `w.SintelCotizacionTables` (0 referencias restantes)

#### 2. Blindeje Anti-Zombi en Recálculo Global

**Cambio:** Verificación con `isConnected` para detectar DOM desconectado

**Implementación:**
```javascript
function recalcularTotalesGlobales() {
  // ⚠️ BLINDAJE ANTI-ZOMBI v2.60: Verificar que el elemento existe Y está conectado al DOM principal
  const elSubtotal = d.getElementById('total-subtotal');
  if (!elSubtotal || !elSubtotal.isConnected) {
    console.warn('[cotizacion-totales] ⚠️ Ejecución fantasma abortada. El DOM está desconectado o el elemento no existe.');
    return; // Abortar inmediatamente si el DOM no está disponible o está desconectado
  }
  
  // ... resto del código de cálculo usando w.SintelCotizacionTables ...
}
```

**Resultado:**
- ✅ Las ejecuciones fantasma se abortan si el DOM está desconectado
- ✅ Previene que closures viejos alteren el DOM nuevo después de un swap de HTMX

#### 3. Limpieza en Listener HTMX

**Cambio:** Limpieza adicional de tablas antes de reinicializar

**Implementación:**
```javascript
d.body.addEventListener('htmx:afterSwap', (e) => {
  if (e.detail.target && e.detail.target.id === 'offcanvas-container') {
    const editorDiv = d.getElementById('modal-cotizacion-editor');
    if (editorDiv) {
      // ⚠️ v2.60: Limpiar tablas existentes antes de reinicializar (ya se hace en init(), pero por seguridad)
      if (w.SintelCotizacionTables) {
        Object.keys(w.SintelCotizacionTables).forEach(key => {
          try {
            if (w.SintelCotizacionTables[key] && typeof w.SintelCotizacionTables[key].destroy === 'function') {
              w.SintelCotizacionTables[key].destroy();
            }
          } catch (error) {
            console.warn(`[cotizacion-editor] Error al destruir tabla ${key}:`, error);
          }
        });
      }
      w.SintelCotizacionTables = {};
      init();
    }
  }
});
```

**Resultado:**
- ✅ Las tablas zombis se destruyen antes de cada reinicialización
- ✅ Doble protección: limpieza en listener HTMX y en `init()`

#### 4. Delegación de Eventos en Columnas

**Estado:** Ya implementado correctamente en `cotizacion_columns.js`

**Implementación:**
```javascript
// En recalcularFila() - cotizacion_columns.js
row.update({ ... }, false).then(() => {
  // ⚠️ Este bloque garantiza el tiempo real exacto - Solo se ejecuta cuando Tabulator garantiza que los datos están asentados
  if (window.CotizacionEditorModule && typeof window.CotizacionEditorModule.recalcularTotalesGlobales === 'function') {
    window.CotizacionEditorModule.recalcularTotalesGlobales();
  }
}).catch(error => {
  console.error('[cotizacion-columns] Error al actualizar fila:', error);
});
```

**Resultado:**
- ✅ Los callbacks de Tabulator usan el objeto global con verificación de seguridad
- ✅ No hay referencias directas a funciones en closures

#### 5. Prevención de Listeners Duplicados

**Estado:** Ya implementado con patrón de clonado

**Implementación:**
```javascript
// En configurarListenersDinamicos()
const switches = d.querySelectorAll('.dna-switch');
switches.forEach(switchEl => {
  // Remover listeners previos si existen (prevención de duplicados)
  const newSwitch = switchEl.cloneNode(true);
  switchEl.parentNode.replaceChild(newSwitch, switchEl);
  newSwitch.addEventListener('change', async function(e) { ... });
});
```

**Resultado:**
- ✅ Los listeners se limpian antes de reasignarse, evitando duplicados
- ✅ Aplicado a switches, inputs financieros y botón guardar

### Validaciones QA Aplicadas

#### ✅ 1. Verificación de Referencias
- **Verificación:** Búsqueda de todas las referencias a `tables` local
- **Resultado:** 0 referencias restantes - Todas migradas a `window.SintelCotizacionTables`

#### ✅ 2. Verificación de Safeguard
- **Verificación:** `recalcularTotalesGlobales()` verifica `isConnected` antes de ejecutar
- **Resultado:** Ejecuciones fantasma abortadas correctamente

#### ✅ 3. Verificación de Limpieza
- **Verificación:** Tablas zombis se destruyen en `init()` y en listener HTMX
- **Resultado:** Sin instancias huérfanas de Tabulator

#### ✅ 4. Verificación de Delegación
- **Verificación:** Callbacks de Tabulator usan objeto global con verificación
- **Resultado:** Sin referencias directas a funciones en closures

### Impacto de las Correcciones

**Antes:**
- ❌ Variables locales en closures persistían después de swaps HTMX
- ❌ Listeners fantasma ejecutándose en DOM desprendido
- ❌ Valores correctos sobrescritos por cálculos de $0
- ❌ Múltiples instancias de tablas en memoria

**Después:**
- ✅ Objeto global único (`window.SintelCotizacionTables`)
- ✅ Safeguard con `isConnected` previene ejecuciones fantasma
- ✅ Limpieza automática de tablas zombis
- ✅ Delegación segura de eventos
- ✅ Prevención de listeners duplicados

### Archivos Modificados

- `apps/tenant/core/static/core/js/cotizaciones/features/cotizacion_editor.js`
  - Convertido `tables` local a `window.SintelCotizacionTables`
  - Agregado safeguard con `isConnected` en `recalcularTotalesGlobales()`
  - Mejorada limpieza en `init()` y listener HTMX
  - Actualizado `getTables()` y `debugTables()` para usar objeto global

- `apps/tenant/core/static/core/js/cotizaciones/cotizacion_columns.js`
  - Ya implementaba delegación correcta de eventos (sin cambios necesarios)

### Funciones Clave Modificadas

- `init()`: Limpieza de tablas zombis antes de inicializar
- `recalcularTotalesGlobales()`: Safeguard con `isConnected`
- `inicializarTablaModulo()`: Guarda tablas en `window.SintelCotizacionTables`
- `configurarListenersDinamicos()`: Ya implementaba clonado (sin cambios)
- Listener HTMX: Limpieza adicional de tablas antes de reinicializar

### Estado Final

- ✅ **Patrón Singleton:** Implementado y verificado
- ✅ **Blindeje Anti-Zombi:** Implementado y verificado
- ✅ **Limpieza de Tablas:** Implementado y verificado
- ✅ **Delegación de Eventos:** Verificado (ya estaba correcto)
- ✅ **Prevención de Duplicados:** Verificado (ya estaba correcto)

---

**Última Actualización:** 2026-01-27  
**Próxima Revisión:** Después de cambios significativos en el módulo  
**Estado:** ✅ **TODAS LAS CORRECCIONES APLICADAS Y VERIFICADAS**  
**Refactorización:** ✅ **ESTRUCTURA DINÁMICA IMPLEMENTADA Y DOCUMENTADA**  
**Anti-Zombi:** ✅ **LISTENERS FANTASMA ERADICADOS Y DOCUMENTADOS**  
**Flujo User-Driven:** ✅ **IMPLEMENTADO Y FUNCIONAL**

---

## ✅ Validación del Flujo Actual (2026-01-27)

### Estado de Validación

#### ✅ Estructura de Archivos
- [x] `cotizaciones.api.js`: Wrapper de API con métodos completos
- [x] `cotizaciones.helpers.js`: Funciones utilitarias compartidas
- [x] `cotizaciones.page.js`: Módulo principal con Tabulator
- [x] `cotizacion_columns.js`: Definición de columnas Tabulator
- [x] `htmx-handlers.js`: Handlers globales HTMX
- [x] `features/cotizacion_editor.js`: Editor principal (User-Driven)
- [x] `features/plantillas_*.js`: Gestión de plantillas (CRUD)

#### ✅ Patrón Singleton Global
- [x] `window.SintelCotizacionTables`: Objeto global único para tablas
- [x] Limpieza de tablas zombis en `init()`
- [x] Limpieza adicional en listener HTMX `afterSwap`
- [x] Todas las referencias migradas de `tables` local a objeto global

#### ✅ Blindeje Anti-Zombi
- [x] `recalcularTotalesGlobales()` verifica `isConnected` antes de ejecutar
- [x] Aborta ejecuciones fantasma en DOM desconectado
- [x] Prevención de listeners duplicados con clonado de elementos

#### ✅ Flujo User-Driven
- [x] Panel de Configuración Dinámica con switches (`.dna-switch`)
- [x] Inputs financieros (`.dna-finance`) para parámetros manuales
- [x] `configurarListenersDinamicos()`: Configura listeners HTMX-safe
- [x] `inicializarTablaModulo()`: Verifica `d-none` antes de instanciar
- [x] `actualizarPanelTotales()`: Alias de `recalcularTotalesGlobales()`
- [x] `guardarCotizaciónFinal()`: Construye payload con valores manuales

#### ✅ Funciones de Cálculo
- [x] `recalcularTotalesGlobales()`: Función principal de cálculo
- [x] `actualizarPanelTotales()`: Alias para compatibilidad
- [x] Matemática preservada: `subtotal + AIU + IVA = total`
- [x] Solo suma módulos activos (verifica `!d-none`)

#### ✅ Integración con Backend
- [x] `cotizacionesAPI.create()`: Crea cotización con payload completo
- [x] `cotizacionesAPI.update()`: Actualiza cotización existente
- [x] `cotizacionesAPI.listConfiguraciones()`: Lista perfiles activos
- [x] Validación de campos requeridos antes de guardar

#### ✅ Error Handling
- [x] Uso de `UIManager.handleError()` para errores de API
- [x] Uso de `UIManager.notifyError()` para errores generales
- [x] Handlers HTMX globales en `htmx-handlers.js`
- [x] Try-catch en funciones críticas con fallback a UIManager

#### ✅ Carga de Datos
- [x] `cargarClientesEnSelect()`: Carga clientes activos con filtro
- [x] `cargarPerfilesEnSelect()`: Carga perfiles activos
- [x] `cargarDatosEmisor()`: Carga datos del emisor desde SSoT
- [x] Carga paralela de catálogos en modo borrador

### Flujo Completo Validado

#### Flujo 1: Inicialización del Editor (Modo Borrador)
```
1. Usuario abre editor → HTMX carga template
   ↓
2. `init()` se ejecuta automáticamente
   ↓
3. Limpieza de tablas zombis (SintelCotizacionTables)
   ↓
4. `configurarFechasPorDefecto()`: Establece fechas automáticamente
   ↓
5. Carga paralela de catálogos:
   - cargarClientesEnSelect()
   - cargarPerfilesEnSelect()
   - cargarDatosEmisor()
   ↓
6. `configurarListenersDinamicos()`: Configura switches e inputs financieros
   ↓
7. Editor listo para uso (User-Driven)
```

#### Flujo 2: Activación de Módulos (User-Driven)
```
1. Usuario activa switch "Equipos"
   ↓
2. Listener detecta cambio → Quita `d-none` de `#section-equipos`
   ↓
3. `inicializarTablaModulo('equipos', ...)`:
   - Verifica que NO tenga `d-none`
   - Crea tabla Tabulator
   - Guarda en `window.SintelCotizacionTables['equipos']`
   ↓
4. Usuario agrega items → `recalcularFila()` calcula subtotal
   ↓
5. `actualizarPanelTotales()` → Suma solo módulos activos
```

#### Flujo 3: Cálculo de Totales
```
1. Usuario modifica cantidad/precio en cualquier fila
   ↓
2. `recalcularFila()` (cotizacion_columns.js) actualiza subtotal_linea
   ↓
3. Callback de Tabulator → `window.CotizacionEditorModule.recalcularTotalesGlobales()`
   ↓
4. `recalcularTotalesGlobales()`:
   - Verifica `isConnected` (safeguard anti-zombi)
   - Itera sobre `window.SintelCotizacionTables`
   - Suma solo módulos activos (verifica `!d-none`)
   - Lee valores financieros desde inputs `.dna-finance`
   - Calcula: subtotal + AIU + IVA = total
   - Actualiza DOM del panel de totales
```

#### Flujo 4: Guardado de Cotización (Actualizado 2026-03-04)
```
1. Usuario click "Guardar Cotización"
   ↓
2. `guardarCotizaciónFinal()`:
   - ✅ Valida cliente: Debe ser ID numérico válido (parseInt con validación)
   - ✅ Valida configuración: Debe ser ID numérico válido (parseInt con validación)
   - ✅ Obtiene fecha_emision del usuario (opcional)
   - ✅ Reindexa filas de tablas activas
   - ✅ Extrae items solo de módulos activos (verifica `!d-none`)
   - ✅ Construye payload con valores de inputs `.dna-finance`
   - ✅ Mapea secciones a tipo_item (equipos→PRODUCTO, materiales→MATERIAL, servicios→SERVICIO)
   ↓
3. `cotizacionesAPI.create(payload)` → POST /api/v1/cotizaciones/
   ↓
4. Backend (Serializer):
   - ✅ to_internal_value(): Normaliza strings a int si es necesario
   - ✅ PrimaryKeyRelatedField: Convierte ID → Objeto Cliente/ConfiguracionCotizacion
   - ✅ validate_cliente(): Valida pertenencia a empresa
   - ✅ validate(): Solo normalización, no conversión
   ↓
5. Backend (Service Layer):
   - ✅ Acepta objetos Cliente y ConfiguracionCotizacion directamente
   - ✅ Procesa fecha_emision del usuario
   - ✅ Guarda todos los datos financieros del usuario
   ↓
6. Backend valida y crea cotización con todos los datos del usuario
   ↓
7. Frontend muestra mensaje de éxito y cierra editor
```

### Puntos Críticos Validados

1. **Patrón Singleton**: `window.SintelCotizacionTables` es único y se limpia en cada `init()`
2. **Safeguard Anti-Zombi**: `isConnected` previene ejecuciones fantasma
3. **User-Driven**: El usuario controla módulos mediante switches, no mediante API
4. **Cálculos SSoT**: `recalcularTotalesGlobales()` es la única fuente de verdad
5. **HTMX-Safe**: Clonado de elementos previene listeners duplicados
6. **Error Boundary**: UIManager maneja todos los errores de forma centralizada

### Mejoras Implementadas

1. ✅ **Carga de Datos del Emisor**: Nueva función `cargarDatosEmisor()` consume `/api/v1/empresas/current-header/`
2. ✅ **Configuración de Fechas Automática**: `configurarFechasPorDefecto()` establece fechas por defecto
3. ✅ **Listener de Fecha de Emisión**: Actualiza automáticamente fecha de vencimiento (+15 días)
4. ✅ **Mapeo de Tipos de Item**: Conversión correcta de secciones a `tipo_item` del modelo
5. ✅ **Limpieza de Campos Temporales**: Elimina campos internos antes de enviar al backend

### Archivos Validados

- ✅ `cotizaciones.api.js`: Métodos completos y correctos
- ✅ `cotizaciones.helpers.js`: Funciones utilitarias validadas
- ✅ `cotizaciones.page.js`: Tabulator principal funcional
- ✅ `cotizacion_columns.js`: Columnas y cálculos correctos
- ✅ `features/cotizacion_editor.js`: Editor User-Driven completo
- ✅ `htmx-handlers.js`: Handlers globales implementados
- ✅ `assets_cotizaciones.html`: Orden de carga correcto

### Estado Final

- ✅ **Flujo Completo**: Validado y documentado
- ✅ **Patrones Anti-Zombi**: Implementados y verificados
- ✅ **User-Driven**: Funcional y documentado
- ✅ **Error Handling**: Centralizado con UIManager
- ✅ **Cálculos**: Matemática preservada y SSoT garantizado

---

## 📊 Resumen Ejecutivo del Flujo Actual

### Arquitectura JavaScript

**Patrón:** Feature-Sliced Architecture con módulos independientes

**Estructura:**
```
cotizaciones/
├── cotizaciones.api.js          # Capa de Datos (API Wrapper)
├── cotizaciones.helpers.js      # Funciones Utilitarias
├── cotizaciones.page.js         # Módulo Principal (Tabulator)
├── cotizacion_columns.js        # Definición de Columnas
├── htmx-handlers.js             # Handlers HTMX Globales
└── features/
    ├── cotizacion_editor.js     # Editor User-Driven
    ├── plantillas_list.js       # Lista de Plantillas
    ├── plantilla_crear.js       # Crear Plantilla
    ├── plantilla_editar.js      # Editar Plantilla
    └── plantilla_ver.js         # Ver Detalle Plantilla
```

### Flujo de Datos

```
Usuario → Switches/Inputs (User-Driven)
    ↓
Listeners Dinámicos (HTMX-Safe)
    ↓
Tablas Tabulator (window.SintelCotizacionTables)
    ↓
recalcularTotalesGlobales() (SSoT)
    ↓
Panel de Totales (DOM)
    ↓
guardarCotizaciónFinal()
    ↓
cotizacionesAPI.create()
    ↓
Backend (DRF ViewSet)
    ↓
Service Layer (CotizacionService)
    ↓
Database
```

### Características Clave

1. **User-Driven**: El usuario controla módulos mediante switches, no mediante API
2. **Patrón Singleton**: `window.SintelCotizacionTables` único y limpio
3. **Anti-Zombi**: Safeguard con `isConnected` previene ejecuciones fantasma
4. **HTMX-Safe**: Clonado de elementos previene listeners duplicados
5. **Error Boundary**: UIManager centraliza manejo de errores
6. **SSoT**: `recalcularTotalesGlobales()` es única fuente de verdad

### Dependencias Globales

- `window.http`: Función HTTP wrapper
- `window.cotizacionesAPI`: Wrapper de API de cotizaciones
- `window.CotizacionesHelpers`: Funciones utilitarias
- `window.UIManager`: Manejo de errores y feedback
- `window.Tabulator`: Librería de tablas
- `window.SintelCotizacionTables`: Objeto global de tablas (Singleton)
- `window.CotizacionEditorModule`: Módulo del editor (namespace)

### Orden de Carga (assets_cotizaciones.html)

1. `assets_core.html` (DOMUtils, TabulatorFactory, etc.)
2. `cotizaciones.api.js` (define `window.cotizacionesAPI`)
3. `htmx-handlers.js` (handlers globales HTMX)
4. `cotizaciones.helpers.js` (define `window.CotizacionesHelpers`)
5. `cotizaciones.page.js` (módulo principal)
6. `cotizacion_columns.js` (define `window.getCotizacionColumns`)
7. `features/cotizacion_editor.js` (editor User-Driven)

**Estado:** ✅ **ORDEN CORRECTO** - Dependencias cargadas antes de módulos que las usan

---

---

## 🔧 Correcciones Aplicadas al Flujo de Guardado (2026-03-04)

### Resumen de Correcciones Frontend

Se aplicaron correcciones críticas en el flujo de guardado para garantizar que los datos se envíen correctamente al backend y se validen adecuadamente.

---

### 1. Validación Estricta del Cliente

#### Problema Identificado
- El frontend podía enviar texto descriptivo en lugar del ID numérico
- El backend rechazaba el payload con error 400

#### Correcciones Aplicadas

**A. Validación en `guardarCotizaciónFinal()`**
- Validación estricta antes de construir el payload
- Verificación de que el valor sea un número válido con `isNaN(parseInt())`
- Uso explícito de `parseInt(clienteValue, 10)` para garantizar ID numérico
- Mensajes de error claros usando UIManager

**B. Helper `cargarClientesEnSelect()`**
- Asegura que `option.value` sea estrictamente el ID numérico (`cliente.id`)
- `option.textContent` muestra nombre y documento, pero `value` es solo el ID
- Validación adicional para omitir clientes con IDs inválidos

**Archivos Modificados:**
- `apps/tenant/core/static/core/js/cotizaciones/features/cotizacion_editor.js`
- `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.helpers.js`

---

### 2. Validación Estricta de Configuración

#### Correcciones Aplicadas
- Validación estricta de configuración antes de construir payload
- Verificación de que el valor sea un número válido
- Uso explícito de `parseInt()` para garantizar ID numérico

**Archivos Modificados:**
- `apps/tenant/core/static/core/js/cotizaciones/features/cotizacion_editor.js`

---

### 3. Inclusión de `fecha_emision` en Payload

#### Correcciones Aplicadas
- El payload ahora incluye `fecha_emision` si el usuario la proporciona
- Campo opcional: si no se proporciona, el backend usa `auto_now_add`
- Captura desde `input-fecha-emision` en el DOM

**Archivos Modificados:**
- `apps/tenant/core/static/core/js/cotizaciones/features/cotizacion_editor.js`

---

### 4. Uso de Singleton Global

#### Correcciones Aplicadas
- Reemplazo de variable local `tables` por `w.SintelCotizacionTables` (Singleton)
- Previene referencias a tablas zombis después de swaps HTMX
- Garantiza que se usen las tablas correctas del DOM actual

**Archivos Modificados:**
- `apps/tenant/core/static/core/js/cotizaciones/features/cotizacion_editor.js`

---

### 5. Manejo Robusto de Errores

#### Correcciones Aplicadas
- Try-catch en `guardarCotizaciónFinal()`
- Uso de `UIManager.handleError()` para errores de API
- Uso de `UIManager.showToast()` para validaciones locales
- Mensajes de error claros y específicos

**Archivos Modificados:**
- `apps/tenant/core/static/core/js/cotizaciones/features/cotizacion_editor.js`

---

## 📊 Flujo Corregido de Guardado (Frontend → Backend)

```
Frontend (JavaScript)
    ↓
    Usuario click "Guardar Cotización"
    ↓
guardarCotizaciónFinal()
    ↓
    ✅ Valida cliente: parseInt() con validación
    ✅ Valida configuración: parseInt() con validación
    ✅ Obtiene fecha_emision del usuario
    ✅ Construye payload con todos los datos
    ↓
    Payload: {
      cliente: 3,                    // ✅ ID numérico
      configuracion: 41,             // ✅ ID numérico
      fecha_emision: "2026-03-04",   // ✅ Fecha del usuario
      tipo_cotizacion: "MIXTO",      // ✅ Tipo del usuario
      iva_porcentaje: 19,            // ✅ Valor del usuario
      porcentaje_aiu_admin: 0,       // ✅ Valor del usuario
      porcentaje_aiu_imprevistos: 0, // ✅ Valor del usuario
      porcentaje_aiu_utilidad: 0,    // ✅ Valor del usuario
      items: [...]                   // ✅ Items de módulos activos
    }
    ↓
cotizacionesAPI.create(payload)
    ↓
POST /api/v1/cotizaciones/
    ↓
Backend (Serializer)
    ↓
    ✅ to_internal_value(): Normaliza strings
    ✅ PrimaryKeyRelatedField: Convierte ID → Objeto
    ✅ validate_cliente(): Valida pertenencia a empresa
    ✅ validate(): Solo normalización
    ↓
Backend (Service Layer)
    ↓
    ✅ Acepta objetos Cliente y ConfiguracionCotizacion
    ✅ Procesa fecha_emision del usuario
    ✅ Guarda todos los datos financieros
    ↓
✅ Cotización creada con todos los datos del usuario
```

---

## ✅ Estado Final del Flujo Frontend

### Validaciones Implementadas
- ✅ Cliente: Validación estricta de ID numérico
- ✅ Configuración: Validación estricta de ID numérico
- ✅ Fecha de Emisión: Captura opcional del usuario
- ✅ Items: Solo de módulos activos
- ✅ Valores Financieros: Captura desde inputs manuales

### Errores Resueltos
- ✅ Error 400: "ID de cliente inválido"
- ✅ Error: "tipo Cliente no soportado"
- ✅ Error: Datos del usuario no se guardaban
- ✅ Error: Referencias a tablas zombis

### Archivos Modificados
1. `apps/tenant/core/static/core/js/cotizaciones/features/cotizacion_editor.js`
2. `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.helpers.js`

---

## 🚀 Implementación de Edición de Cotizaciones - Frontend (2026-03-04)

### Resumen de Implementación

Se implementó el flujo completo de edición de cotizaciones desde el frontend, incluyendo:
1. **Fase 1**: Configuración de columna de acciones con HTMX
2. **Fase 2**: Lógica de carga de datos en el editor
3. **Eliminación de Inmutabilidad**: Remoción de restricciones de edición

### Fase 1: Configuración de Columna de Acciones con HTMX

#### Objetivo
Permitir que el botón "Editar" en la lista de cotizaciones use HTMX directamente para cargar el editor sin JavaScript adicional.

#### Cambios Aplicados

**Archivo**: `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.page.js`

1. **Columna de Acciones Actualizada**:
   ```javascript
   {
     title: "Acciones",
     formatter: function(cell) {
       const uuid = rowData.uuid || rowData.id;
       
       // Botón Editar con HTMX
       buttons += `
         <button class="btn btn-sm btn-outline-primary"
                 hx-get="/cotizaciones/editor/${uuid}/"
                 hx-target="#offcanvas-container"
                 hx-swap="innerHTML"
                 data-bs-toggle="offcanvas"
                 data-bs-target="#offcanvas-container">
           <i class="bi bi-pencil"></i> Editar
         </button>
       `;
       
       // Botón Ver PDF
       buttons += `
         <button class="btn btn-sm btn-outline-secondary" 
                 onclick="window.CotizacionesPage.verPDF('${uuid}')">
           <i class="bi bi-file-pdf"></i>
         </button>
       `;
       
       // Botón Eliminar (siempre visible)
       buttons += `
         <button class="btn btn-sm btn-link text-danger" 
                 data-action="eliminar" data-uuid="${uuid}">
           <i class="fas fa-trash"></i>
         </button>
       `;
       
       return `<div class="d-flex gap-1">${buttons}</div>`;
     }
   }
   ```

2. **Procesamiento HTMX Automático**:
   ```javascript
   // Eventos de Tabulator para procesar HTMX
   table.on('dataLoaded', function() {
     if (typeof htmx !== 'undefined' && typeof htmx.process === 'function') {
       const container = d.querySelector(TABLE_SELECTOR);
       if (container) {
         htmx.process(container);
       }
     }
   });
   
   table.on('dataProcessed', function() {
     if (typeof htmx !== 'undefined' && typeof htmx.process === 'function') {
       const container = d.querySelector(TABLE_SELECTOR);
       if (container) {
         htmx.process(container);
       }
     }
   });
   ```

#### Beneficios

- ✅ **HTMX Directo**: Sin JavaScript adicional para cargar el editor
- ✅ **Procesamiento Automático**: `htmx.process()` se ejecuta después de cada carga de datos
- ✅ **Compatibilidad**: Los botones con `data-action` siguen funcionando con event delegation
- ✅ **UX Mejorada**: Layout con `d-flex gap-1` y iconos Bootstrap Icons

### Fase 2: Lógica de Carga en el Editor

#### Objetivo
Cargar automáticamente los datos de una cotización existente cuando se abre el editor con un UUID válido.

#### Cambios Aplicados

**Archivo**: `apps/tenant/core/static/core/js/cotizaciones/features/cotizacion_editor.js`

1. **Detección de UUID y Modo**:
   ```javascript
   const editorDiv = d.getElementById('modal-cotizacion-editor');
   const uuid = editorDiv.getAttribute('data-cotizacion-uuid');
   const isDraft = !uuid || uuid === '' || uuid === 'None';
   ```

2. **Carga de Datos desde API**:
   ```javascript
   if (uuid && uuid !== '' && uuid !== 'None' && w.cotizacionesAPI) {
     // Cargar datos del emisor y catálogos
     await cargarDatosEmisor();
     await Promise.all([
       w.CotizacionesHelpers.cargarClientesEnSelect(selCliente),
       w.CotizacionesHelpers.cargarPerfilesEnSelect(selPerfil)
     ]);
     
     // Obtener datos de la cotización
     const response = await w.cotizacionesAPI.get(uuid);
     const cotizacion = response.data;
   }
   ```

3. **Relleno de Campos de Cabecera**:
   ```javascript
   // Cliente
   if (cotizacion.cliente) {
     const clienteId = typeof cotizacion.cliente === 'object' 
       ? cotizacion.cliente.id 
       : cotizacion.cliente;
     selCliente.value = String(clienteId);
     selCliente.dispatchEvent(new Event('change', { bubbles: true }));
   }
   
   // Perfil
   if (cotizacion.configuracion) {
     const configId = typeof cotizacion.configuracion === 'object' 
       ? cotizacion.configuracion.id 
       : cotizacion.configuracion;
     selPerfil.value = String(configId);
     selPerfil.dispatchEvent(new Event('change', { bubbles: true }));
   }
   
   // Fecha de Emisión
   if (cotizacion.fecha_emision) {
     const fecha = new Date(cotizacion.fecha_emision);
     inputFecha.value = fecha.toISOString().split('T')[0];
   }
   ```

4. **Relleno de Campos Financieros**:
   ```javascript
   // IVA
   if (inputIva && cotizacion.iva_porcentaje !== undefined) {
     inputIva.value = parseFloat(cotizacion.iva_porcentaje).toFixed(2);
   }
   
   // AIU Admin
   if (inputAiuAdmin && cotizacion.porcentaje_aiu_admin !== undefined) {
     inputAiuAdmin.value = parseFloat(cotizacion.porcentaje_aiu_admin).toFixed(2);
   }
   
   // AIU Imprevistos
   if (inputAiuImprevistos && cotizacion.porcentaje_aiu_imprevistos !== undefined) {
     inputAiuImprevistos.value = parseFloat(cotizacion.porcentaje_aiu_imprevistos).toFixed(2);
   }
   
   // AIU Utilidad
   if (inputAiuUtilidad && cotizacion.porcentaje_aiu_utilidad !== undefined) {
     inputAiuUtilidad.value = parseFloat(cotizacion.porcentaje_aiu_utilidad).toFixed(2);
   }
   ```

5. **Carga de Ítems en Tablas**:
   ```javascript
   // Distribuir ítems por tipo_item
   const equipos = cotizacion.items.filter(item => item.tipo_item === 'PRODUCTO');
   const materiales = cotizacion.items.filter(item => item.tipo_item === 'MATERIAL');
   const servicios = cotizacion.items.filter(item => item.tipo_item === 'SERVICIO');
   
   // Activar secciones automáticamente
   if (equipos.length > 0) {
     sectionEquipos.classList.remove('d-none');
     switchEquipos.checked = true;
   }
   
   // Inicializar tablas
   initVisibleGrids();
   
   // Cargar datos en las tablas
   setTimeout(() => {
     if (equipos.length > 0 && w.SintelCotizacionTables['equipos']) {
       const equiposData = equipos.map(item => ({
         descripcion: item.descripcion || '',
         cantidad: parseFloat(item.cantidad) || 0,
         costo_unitario: parseFloat(item.costo_unitario) || 0,
         porcentaje_utilidad: parseFloat(item.porcentaje_utilidad) || 0,
         precio_unitario_venta: parseFloat(item.precio_unitario_venta) || 0,
         subtotal_linea: parseFloat(item.subtotal_linea) || 0,
         marca: item.marca || '',
         referencia: item.referencia || '',
         unidad: item.unidad || 'UND',
         nro_item: item.orden || 0
       }));
       w.SintelCotizacionTables['equipos'].setData(equiposData);
     }
     // ... repetir para materiales y servicios
     
     // Actualizar panel de totales
     setTimeout(() => {
       actualizarPanelTotales();
     }, 100);
   }, 300);
   ```

#### Flujo de Carga

```
1. init() detecta UUID del template
   ↓
2. Si UUID válido → Cargar datos del emisor y catálogos
   ↓
3. Obtener cotización desde API (cotizacionesAPI.get(uuid))
   ↓
4. Rellenar campos de cabecera (cliente, perfil, fecha, tipo)
   ↓
5. Rellenar campos financieros (IVA, AIU)
   ↓
6. Distribuir ítems por tipo_item en tablas correspondientes
   ↓
7. Activar secciones automáticamente si tienen ítems
   ↓
8. Inicializar tablas Tabulator
   ↓
9. Cargar datos en las tablas
   ↓
10. Actualizar panel de totales
```

### Eliminación de Inmutabilidad

#### Cambios Aplicados

1. **Columna de Acciones** (`cotizaciones.page.js`):
   - ❌ Eliminada lógica que ocultaba botón "Editar" si está ACEPTADA
   - ❌ Eliminada lógica que ocultaba botón "Eliminar" si está ACEPTADA
   - ✅ Los botones ahora se muestran siempre, independientemente del estado

2. **API Wrapper** (`cotizaciones.api.js`):
   - ❌ Eliminados comentarios sobre inmutabilidad en `update()` y `delete()`

#### Resultado

- ✅ Las cotizaciones ACEPTADAS pueden editarse desde el frontend
- ✅ Los botones de acción se muestran siempre
- ✅ Sin restricciones de UI basadas en el estado

### Archivos Modificados

1. `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.page.js`
2. `apps/tenant/core/static/core/js/cotizaciones/features/cotizacion_editor.js`
3. `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.api.js`

### Flujo Completo de Edición - Frontend

```
1. Usuario hace clic en "Editar" en la lista de cotizaciones
   ↓
2. HTMX carga el template del editor con UUID
   ↓
3. cotizacion_editor.js detecta UUID en init()
   ↓
4. Carga datos del emisor y catálogos (clientes, perfiles)
   ↓
5. Obtiene cotización completa desde API (cotizacionesAPI.get(uuid))
   ↓
6. Rellena campos de cabecera (cliente, perfil, fecha, tipo)
   ↓
7. Rellena campos financieros (IVA, AIU admin/imprevistos/utilidad)
   ↓
8. Distribuye ítems por tipo_item (PRODUCTO → equipos, MATERIAL → materiales, SERVICIO → servicios)
   ↓
9. Activa secciones automáticamente si tienen ítems
   ↓
10. Inicializa tablas Tabulator (initVisibleGrids())
   ↓
11. Carga datos en las tablas (setData())
   ↓
12. Actualiza panel de totales (actualizarPanelTotales())
   ↓
13. Usuario modifica datos y hace clic en "Guardar"
   ↓
14. Frontend envía PATCH con datos actualizados (guardarCotizaciónFinal())
   ↓
15. Backend procesa actualización y retorna respuesta
   ↓
16. UI se actualiza con los cambios
```

### Beneficios Implementados

- ✅ **HTMX Directo**: Sin JavaScript adicional para cargar el editor
- ✅ **Carga Automática**: Los datos se cargan automáticamente al abrir el editor
- ✅ **UX Mejorada**: Secciones se activan automáticamente según ítems
- ✅ **Flexibilidad**: Sin restricciones de inmutabilidad en el frontend
- ✅ **User-Driven**: Los datos del usuario tienen prioridad absoluta

---

## 🔧 Sincronización de Tabla y Mejoras de UX (2026-03-04)

### Resumen de Mejoras

Se implementaron mejoras significativas en la sincronización de la tabla de cotizaciones con el modelo, redirección automática después de guardar, y refactorización del AIU como opcional. Todas las mejoras mejoran la experiencia del usuario y garantizan la integridad de los datos.

### Correcciones Aplicadas

#### 1. Sincronización de Tabla de Cotizaciones con Modelo

**Objetivo:** Sincronizar la tabla de listado de cotizaciones con los campos reales del modelo `Cotizacion` y el `CotizacionSerializer`.

**Archivos Modificados:**
- `apps/tenant/core/templates/tenant/core/partials/cotizaciones/list.html`
- `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.page.js`

**Cambios Aplicados:**

**A. Actualización del HTML:**
- Contenedor actualizado con ID único: `tabla-cotizaciones-principal`
- Agregados atributos de datos:
  - `data-url="/api/v1/cotizaciones/"` - URL de la API REST
  - `data-page-size="20"` - Tamaño de página para paginación
- Clases agregadas: `table-responsive tabulator-sintel flex-grow-1`

**B. Sincronización de Columnas:**

**Columna "NÚMERO":**
- **Antes**: `field: "numero"` (campo inexistente)
- **Ahora**: `field: "codigo_unico"` (campo del modelo)
- Muestra el código único generado (ej: "STS. 0422-2026")
- Formatter maneja valores nulos mostrando '-'

**Columna "CLIENTE":**
- **Antes**: `field: "cliente_nombre"` sin fallback
- **Ahora**: `field: "cliente_nombre"` con fallback a `cliente_display`
- Usa `cliente_nombre` del serializer (ReadOnlyField)
- Si `cliente_nombre` no está disponible, usa `cliente_display`

**Columna "TOTAL":**
- **Antes**: `field: "total_neto"` (campo inexistente)
- **Ahora**: `field: "total_con_impuestos"` (campo del modelo)
- Muestra el total con impuestos calculado
- Agregado `bottomCalc: "sum"` para calcular suma total en el pie
- Formatter maneja valores nulos mostrando `$0`

**Código de Columnas:**
```javascript
{
  title: "NÚMERO",
  field: "codigo_unico", // Campo del modelo
  width: 150,
  headerFilter: "input",
  formatter: function(cell) {
    const value = cell.getValue();
    return value || '-';
  }
},
{
  title: "CLIENTE",
  field: "cliente_nombre", // ReadOnlyField del serializer
  formatter: function(cell) {
    const value = cell.getValue();
    if (!value) {
      const rowData = cell.getRow().getData();
      return rowData.cliente_display || 'Sin cliente';
    }
    return value;
  },
  minWidth: 200,
  headerFilter: "input"
},
{
  title: "TOTAL",
  field: "total_con_impuestos", // Campo del modelo
  formatter: function(cell) {
    const value = cell.getValue();
    if (value === null || value === undefined) {
      return fmtMoney(0);
    }
    return fmtMoney(value);
  },
  width: 150,
  hozAlign: "right",
  sorter: "number",
  bottomCalc: "sum", // Suma total en el pie
  bottomCalcFormatter: function(cell) {
    const value = parseFloat(cell.getValue()) || 0;
    return fmtMoney(value);
  }
}
```

**C. Actualización de Selector JavaScript:**
- `TABLE_SELECTOR` actualizado de `#grid-cotizaciones` a `#tabla-cotizaciones-principal`
- Sincronizado con el nuevo ID del contenedor HTML

#### 2. Redirección Automática Después de Guardar

**Objetivo:** Redirigir automáticamente a la lista de cotizaciones después de guardar o actualizar una cotización.

**Archivo Modificado:**
- `apps/tenant/core/static/core/js/cotizaciones/features/cotizacion_editor.js`

**Cambios Aplicados:**

**A. Soporte para Creación y Actualización:**
- Detección automática de modo (creación POST vs actualización PATCH)
- Cálculo de `isUpdate` y `cotizacionUuid` antes del loop de items (optimización)
- Método HTTP dinámico: `PATCH` para actualización, `POST` para creación
- URL dinámica según el modo

**B. Redirección Automática:**
- Cierre automático del offcanvas después de guardar exitosamente
- Redirección a `workspace/#cotizaciones` usando `location.hash`
- Activación del tab de cotizaciones usando `showTab('cotizaciones')` si está disponible
- Refresco automático de la tabla usando `w.cotizacionesPage.refresh()`
- Delay de 500ms para mostrar mensaje de éxito antes de redirigir

**Código:**
```javascript
const res = await w.http(method, url, payload);
if (res.ok) {
  // Mostrar mensaje de éxito
  if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
    w.SintelFeedback.success(isUpdate ? 'Cotización actualizada exitosamente' : 'Cotización guardada exitosamente');
  }
  
  // Cerrar offcanvas si está abierto
  const offcanvasElement = d.getElementById('offcanvas-container');
  if (offcanvasElement) {
    const bsOffcanvas = w.bootstrap?.Offcanvas?.getInstance(offcanvasElement);
    if (bsOffcanvas) {
      bsOffcanvas.hide();
    }
  }
  
  // Redirigir a la lista de cotizaciones
  setTimeout(() => {
    w.location.hash = '#cotizaciones';
    if (w.showTab && typeof w.showTab === 'function') {
      w.showTab('cotizaciones');
    }
    if (w.cotizacionesPage && typeof w.cotizacionesPage.refresh === 'function') {
      w.cotizacionesPage.refresh();
    }
  }, 500);
}
```

**Flujo de Guardado:**
```
Usuario hace clic en "Guardar Cotización"
   ↓
Detectar si es creación o actualización
   ├─ Creación (sin UUID) → POST /api/v1/cotizaciones/
   └─ Actualización (con UUID) → PATCH /api/v1/cotizaciones/{uuid}/
   ↓
Enviar petición HTTP
   ↓
¿Respuesta exitosa?
   ├─ SÍ → Mostrar mensaje de éxito
   │        ↓
   │        Cerrar offcanvas
   │        ↓
   │        Esperar 500ms
   │        ↓
   │        Redirigir a workspace/#cotizaciones
   │        ↓
   │        Activar tab de cotizaciones
   │        ↓
   │        Refrescar tabla de cotizaciones
   └─ NO → Mostrar error
```

#### 3. Refactorización del AIU como Opcional

**Objetivo:** Hacer que la aplicación del esquema AIU sea opcional para cada cotización, controlada por un switch en el frontend.

**Archivos Modificados:**
- `apps/tenant/core/templates/tenant/core/partials/cotizaciones/editor_cotizacion.html`
- `apps/tenant/core/static/core/js/cotizaciones/features/cotizacion_editor.js`

**Cambios Aplicados:**

**A. Modificación del HTML:**
- Los tres campos de AIU encapsulados en un `div` con ID `container-aiu-fields` y clase `d-none`
- Agregado switch Bootstrap (`form-check form-switch`) con ID `switch-activar-aiu`
- Switch controla la visibilidad de `container-aiu-fields`

**B. Lógica de Interfaz:**
- Listener para `switch-activar-aiu` en `configurarListenersDinamicos()`
- Si el switch se activa: muestra campos AIU y llama a `actualizarPanelTotales()`
- Si el switch se desactiva: oculta campos AIU, resetea valores a "0.00", y llama a `actualizarPanelTotales()`

**C. Sincronía con Cotización Existente:**
- En `init()`, si la cotización cargada tiene valores de AIU > 0, activa automáticamente el switch
- Muestra los campos AIU y rellena los valores
- Si no hay valores de AIU, desactiva el switch y oculta los campos

**D. Ajuste del Payload de Guardado:**
- En `guardarCotizaciónFinal()`, si el switch está apagado, envía estrictamente `0.00` para todos los campos AIU
- Independiente de valores en inputs ocultos
- Solo captura valores si el switch está activado

**E. Cálculo de Totales:**
- En `recalcularTotalesGlobales()`, suma los tres porcentajes de AIU solo si el switch está activado
- Calcula `valorAiuGlobal` sobre el subtotal si el switch está activado
- Si el switch está desactivado, `valorAiuGlobal = 0`

**Código del Listener:**
```javascript
const switchActivarAiu = d.getElementById('switch-activar-aiu');
if (switchActivarAiu) {
  const newSwitch = switchActivarAiu.cloneNode(true);
  switchActivarAiu.parentNode.replaceChild(newSwitch, switchActivarAiu);
  
  newSwitch.addEventListener('change', function(e) {
    const container = d.getElementById('container-aiu-fields');
    
    if (e.target.checked) {
      // Switch activado: Mostrar campos AIU
      container.classList.remove('d-none');
      actualizarPanelTotales();
    } else {
      // Switch desactivado: Ocultar campos AIU y resetear valores
      container.classList.add('d-none');
      
      // Resetear valores a 0
      d.getElementById('input-aiu-admin').value = "0.00";
      d.getElementById('input-aiu-imprevistos').value = "0.00";
      d.getElementById('input-aiu-utilidad').value = "0.00";
      
      actualizarPanelTotales();
    }
  });
}
```

**Código del Payload:**
```javascript
// Capturar valores de AIU solo si el switch está activado
porcentaje_aiu_admin: (() => {
  const switchAiu = d.getElementById('switch-activar-aiu');
  if (!switchAiu || !switchAiu.checked) {
    return 0.00; // Enviar estrictamente 0 si está desactivado
  }
  const value = d.getElementById('input-aiu-admin')?.value;
  const parsed = parseFloat(value);
  return (!isNaN(parsed) && value !== '') ? parsed : 0.00;
})(),
// ... repetir para porcentaje_aiu_imprevistos y porcentaje_aiu_utilidad
```

### Mapeo de Campos Frontend ↔ Backend

| Columna Frontend | Campo Backend | Tipo | Origen |
|------------------|---------------|------|--------|
| NÚMERO | `codigo_unico` | CharField | Modelo Cotizacion |
| CLIENTE | `cliente_nombre` | ReadOnlyField | Serializer (source: `cliente.nombre_comercial`) |
| TOTAL | `total_con_impuestos` | DecimalField | Modelo Cotizacion |

### Beneficios Implementados

- ✅ **Sincronización Completa**: Tabla sincronizada con modelo y serializer
- ✅ **Redirección Automática**: Mejora UX al volver a la lista después de guardar
- ✅ **AIU Opcional**: Control granular del esquema AIU por cotización
- ✅ **Datos Reales**: Tabla muestra datos directamente desde la base de datos
- ✅ **Manejo de Errores**: Formatters manejan valores nulos correctamente
- ✅ **Cálculo de Totales**: Suma total automática en el pie de la tabla
- ✅ **Sincronía con Cotizaciones Existentes**: Switch AIU se activa automáticamente si hay valores

### Archivos Modificados

1. `apps/tenant/core/templates/tenant/core/partials/cotizaciones/list.html`
2. `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.page.js`
3. `apps/tenant/core/static/core/js/cotizaciones/features/cotizacion_editor.js`
4. `apps/tenant/core/templates/tenant/core/partials/cotizaciones/editor_cotizacion.html`
5. `apps/tenant/core/templates/tenant/core/workspace.html`

### Estado Final

- ✅ Tabla sincronizada con modelo `Cotizacion`
- ✅ Columnas usando campos reales del serializer
- ✅ Redirección automática después de guardar
- ✅ AIU opcional con switch de control
- ✅ Sincronía con cotizaciones existentes
- ✅ Manejo robusto de valores nulos
- ✅ Cálculo de suma total en el pie de la tabla

---

**Documento actualizado y validado**  
**Última validación:** 2026-03-04  
**Versión del Sistema:** 2.60  
**Estado:** ✅ Validado y Actualizado con Sincronización Completa de Tabla y Mejoras de UX  
**Estado:** ✅ **FLUJO COMPLETO DE EDICIÓN IMPLEMENTADO Y DOCUMENTADO**