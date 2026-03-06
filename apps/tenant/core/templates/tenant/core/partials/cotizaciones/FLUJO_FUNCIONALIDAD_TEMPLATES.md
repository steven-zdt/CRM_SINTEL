# 📋 Flujo Completo de Funcionalidad - Templates de Cotizaciones

**Versión:** 2.60  
**Fecha:** 2026-01-XX  
**Ubicación:** `apps/tenant/core/templates/tenant/core/partials/cotizaciones/`

---

## 📑 Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura General](#arquitectura-general)
3. [Templates y sus Funcionalidades](#templates-y-sus-funcionalidades)
4. [Flujo Completo de Usuario](#flujo-completo-de-usuario)
5. [Integración con JavaScript](#integración-con-javascript)
6. [Endpoints y APIs](#endpoints-y-apis)
7. [Diagramas de Flujo](#diagramas-de-flujo)

---

## 🎯 Resumen Ejecutivo

El módulo de **Cotizaciones** implementa un sistema completo de gestión de cotizaciones siguiendo una arquitectura **API-First** con **Tabulator** como motor de tablas. Los templates están organizados en 7 archivos principales que cubren:

- **Listado y visualización** de cotizaciones
- **Editor de cotizaciones** estilo Excel con cálculo en tiempo real
- **Gestión de plantillas/configuraciones** (CRUD completo)
- **Visualización de detalles** de plantillas

### Características Principales

- ✅ **API-First Architecture**: Backend DRF + Frontend Tabulator
- ✅ **Cálculo en tiempo real** de subtotales e impuestos
- ✅ **Gestión de plantillas** configurables (IVA, AIU, secuencias)
- ✅ **Offcanvas Navigation**: Navegación moderna sin modales
- ✅ **HTMX Integration**: Carga dinámica de formularios
- ✅ **Error Boundary v2.60**: Manejo centralizado de errores

---

## 🏗️ Arquitectura General

### Estructura de Templates

```
cotizaciones/
├── list.html                          # Vista principal de listado
├── editor_cotizacion.html            # Editor de cotizaciones
├── assets_cotizaciones.html          # Carga de scripts (orden crítico)
├── offcanvas_list_plantillas.html     # Lista de plantillas/configuraciones
├── offcanvas_plantilla_crear.html    # Formulario crear plantilla
├── offcanvas_plantilla_editar.html    # Formulario editar plantilla
└── offcanvas_ver_detalle.html        # Vista detalle de plantilla
```

### Dependencias JavaScript (Orden Crítico)

El orden de carga de scripts es **CRÍTICO** y está definido en `assets_cotizaciones.html`:

1. **assets_core.html** (incluye DOMUtils, TabulatorFactory, etc.)
2. **cotizaciones.api.js** → Define `window.cotizacionesAPI`
3. **cotizaciones.helpers.js** → Define `window.CotizacionesHelpers`
4. **cotizaciones.page.js** → Workspace principal (depende de Helpers y TabulatorFactory)
5. **cotizacion_columns.js** → Define `window.getCotizacionColumns()` ⚠️ **DEBE cargarse ANTES del Editor**
6. **cotizacion_editor.js** → Editor de cotizaciones (depende de `getCotizacionColumns`)

---

## 📄 Templates y sus Funcionalidades

### 1. `list.html` - Vista Principal de Cotizaciones

**Propósito:** Vista principal que muestra el listado de cotizaciones con resumen estadístico.

#### Componentes Principales

##### Panel de Resumen (Líneas 10-52)
- **Total Neto**: Suma total de todas las cotizaciones
- **Aceptadas**: Contador de cotizaciones aceptadas
- **Enviadas**: Contador de cotizaciones enviadas
- **Borrador**: Contador de cotizaciones en borrador

**Selectores:**
- `#total-cotizaciones-neto`
- `#cantidad-aceptadas`
- `#cantidad-enviadas`
- `#cantidad-borrador`
- `#cantidad-cotizaciones`

##### Toolbar (Líneas 55-86)
- **Botón "Nueva Cotización"**: Abre editor vía HTMX
  - `hx-get="{% url 'cotizaciones_ui:ui_editor_draft' %}"`
  - `hx-target="#offcanvas-container"`
- **Botón "Refrescar"**: Actualiza la tabla
- **Botón "Ver Parámetros"**: Abre lista de plantillas

##### Búsqueda (Líneas 89-91)
- Input de búsqueda con selector: `#search-cotizacion`
- Búsqueda en tiempo real sobre número, cliente, etc.

##### Tabla Principal (Líneas 94-98)
- Contenedor Tabulator: `#grid-cotizaciones`
- Inicializada por `cotizaciones.page.js`
- Columnas: Número, Cliente, Fecha, Estado, Total, Acciones

##### Sección Colapsable - Perfiles de Configuración (Líneas 101-116)
- Panel colapsable para gestionar plantillas
- Búsqueda de configuraciones: `#search-configuracion`
- Tabla de configuraciones: `#grid-configuraciones-parametros`

##### Offcanvas Containers (Líneas 122-129)
- `#offcanvas-container`: Offcanvas superior para formularios generales
- `#offcanvas-editor-container`: Offcanvas lateral derecho para editor (90% ancho, max 1200px)

#### Flujo de Interacción

1. **Carga inicial**: `cotizaciones.page.js` inicializa tabla y carga datos
2. **Click "Nueva Cotización"**: HTMX carga `editor_cotizacion.html` en offcanvas
3. **Click "Ver Parámetros"**: HTMX carga `offcanvas_list_plantillas.html`
4. **Búsqueda**: Filtra tabla en tiempo real
5. **Acciones en fila**: Editar, Ver, Eliminar, Convertir a Factura

---

### 2. `editor_cotizacion.html` - Editor de Cotizaciones

**Propósito:** Editor estilo Excel para crear/editar cotizaciones con cálculo en tiempo real.

#### Componentes Principales

##### Header (Líneas 5-10)
- Título: "Editor de Cotización"
- Botón cerrar offcanvas
- Data attribute: `data-cotizacion-uuid` para identificar cotización existente

##### Configuración Inicial (Líneas 15-33)
- **Cliente** (select): `#editor-select-cliente` - Campo requerido
- **Perfil/Plantilla** (select): `#editor-select-perfil` - Campo requerido
- **Vencimiento** (date): `#editor-fecha-vencimiento` - Campo requerido

##### Secciones de Items (Líneas 35-48)
Tres secciones modulares que se muestran según el tipo de plantilla:

1. **Equipos y Suministros** (`#section-equipos`)
   - Grid: `#grid-editor-equipos`
   - Clase: `editor-module d-none` (oculta por defecto)

2. **Materiales de Instalación** (`#section-materiales`)
   - Grid: `#grid-editor-materiales`
   - Clase: `editor-module d-none`

3. **Servicios Profesionales** (`#section-servicios`)
   - Grid: `#grid-editor-servicios`
   - Clase: `editor-module d-none`

**Nota:** Las secciones se muestran dinámicamente según el tipo de plantilla seleccionada.

##### Panel de Totales (Líneas 50-68)
- **Subtotal**: `#total-subtotal` - Suma de todos los items
- **IVA Aplicado**: `#total-iva` - IVA calculado según porcentaje de plantilla
- **Total Cotización**: `#total-con-impuestos` - Subtotal + IVA

##### Botones de Acción (Líneas 70-75)
- **Cancelar**: Cierra offcanvas sin guardar
- **Guardar Cotización**: `#btn-guardar-maestro` - Guarda cotización completa

##### Scripts (Líneas 79-82)
⚠️ **ORDEN CRÍTICO:**
1. `cotizacion_columns.js` - DEBE cargarse PRIMERO
2. `cotizacion_editor.js` - Depende de `getCotizacionColumns()`

#### Flujo de Funcionamiento

1. **Carga del Editor**: HTMX carga template en `#offcanvas-editor-container`
2. **Inicialización**: `cotizacion_editor.js` detecta carga y inicializa
3. **Carga de Datos**:
   - Si `data-cotizacion-uuid` existe → Carga cotización existente
   - Si no → Crea nueva cotización en borrador
4. **Selección de Perfil**: Al seleccionar perfil, se muestran secciones correspondientes
5. **Edición de Items**: 
   - Cálculo en tiempo real de subtotales
   - Función `recalcularFila()` actualiza `subtotal_linea = cantidad × costo_unitario`
6. **Actualización de Totales**: `actualizarPanelTotales()` recalcula IVA y total
7. **Guardado**: `#btn-guardar-maestro` envía datos completos al backend

#### Características Técnicas

- **Cálculo en tiempo real**: Al editar cantidad o precio unitario, se recalcula subtotal
- **dataType: "number"**: Asegura que valores se guarden como números (no strings)
- **Error Boundary**: Manejo de errores mediante `UIManager.notifyError()`
- **Sincronización**: Actualiza panel de totales automáticamente

---

### 3. `assets_cotizaciones.html` - Gestor de Assets

**Propósito:** Carga ordenada de todos los scripts del módulo de cotizaciones.

#### Estructura de Carga

##### Bloque 1: API Wrapper (Líneas 19-22)
```html
<script src="{% static 'core/js/cotizaciones/cotizaciones.api.js' %}?v=2.60.2"></script>
```
- Define `window.cotizacionesAPI`
- Wrapper de endpoints DRF
- **DEBE cargarse PRIMERO**

##### Bloque 2: HTMX Handlers (Líneas 24-25)
```html
<script src="{% static 'core/js/cotizaciones/htmx-handlers.js' %}?v=2.60.2"></script>
```
- Manejo de errores y eventos HTMX
- Intercepta respuestas y muestra errores

##### Bloque 2.5: Helpers (Líneas 27-28)
```html
<script src="{% static 'core/js/cotizaciones/cotizaciones.helpers.js' %}?v=2.60.2"></script>
```
- Funciones utilitarias compartidas
- Define `window.CotizacionesHelpers`

##### Bloque 3: Página Principal (Líneas 30-31)
```html
<script src="{% static 'core/js/cotizaciones/cotizaciones.page.js' %}?v=2.60.2"></script>
```
- Workspace principal
- Inicializa tablas y eventos
- **DEBE cargarse ÚLTIMO** (después de dependencias)

##### Bloque 5: Columnas de Tabulator (Líneas 37-39)
```html
<script src="{% static 'core/js/cotizaciones/cotizacion_columns.js' %}?v=2.60"></script>
```
- Define `window.getCotizacionColumns()`
- **CRÍTICO**: Requerido por el editor

##### Bloque 6: Editor de Cotizaciones (Líneas 41-45)
```html
<script src="{% static 'core/js/cotizaciones/features/cotizacion_editor.js' %}?v=2.60.wizard"></script>
```
- Editor estilo Excel
- Depende de `getCotizacionColumns()`

#### Cache-Busting

Todos los scripts usan versionado (`?v=X.X.X`) para forzar recarga en actualizaciones.

---

### 4. `offcanvas_list_plantillas.html` - Lista de Plantillas

**Propósito:** Muestra lista de plantillas/configuraciones disponibles en un offcanvas.

#### Componentes Principales

##### Header (Líneas 2-7)
- Título: "Parámetros y Plantillas"
- Botón cerrar

##### Body (Líneas 8-23)
- **Descripción**: Texto informativo
- **Botón "Nueva Plantilla"**: 
  - `hx-get="{% url 'cotizaciones_ui:ui_crear_configuracion' %}"`
  - `hx-target="#offcanvas-container-secundario"`
  - Abre offcanvas secundario en cascada
- **Tabla de Plantillas**: `#grid-plantillas-offcanvas`
  - Inicializada por `plantillas_list.js`

##### Offcanvas Secundario (Línea 26)
- `#offcanvas-container-secundario`: Offcanvas anidado para creación
- Z-index: 1056 (por encima del principal)

##### Función JavaScript (Líneas 29-64)
- `window.abrirOffcanvasSecundario()`: Maneja apertura del offcanvas secundario
- Espera a que HTMX cargue contenido antes de abrir
- Usa `htmx:afterSwap` event listener

#### Flujo de Interacción

1. **Click "Ver Parámetros"** en `list.html` → Carga este template
2. **Tabla se inicializa**: `plantillas_list.js` carga datos y crea tabla
3. **Click "Nueva Plantilla"**: Abre offcanvas secundario con formulario de creación
4. **Acciones en fila**: Ver detalle, Editar, Eliminar

---

### 5. `offcanvas_plantilla_crear.html` - Crear Plantilla

**Propósito:** Formulario para crear nueva plantilla/configuración de cotización.

#### Campos del Formulario

##### Información General
- **Nombre del Perfil** (`nombre_configuracion`): Texto, requerido
- **Tipo de Plantilla** (`tipo_plantilla`): Select
  - Opciones: Mixto, Equipos, Materiales, Servicios
- **Tipo de Cotización por Defecto** (`tipo_cotizacion_default`): Select
  - Opciones: Mixto, Productos, Servicios, Materiales

##### Configuración Fiscal
- **IVA por defecto (%)** (`iva_porcentaje_default`): Number, requerido, default 19.00
- **Utilidad por defecto (%)** (`porcentaje_utilidad_default`): Number, default 10.00

##### Configuración AIU (Opcional)
- **Checkbox "Habilitar Cálculos AIU"** (`usa_aiu`): Muestra/oculta campos AIU
- **Container AIU** (`#container-aiu-crear`): Oculto por defecto (`d-none`)
  - Admin (%): `aiu_admin_default`
  - Imprevistos (%): `aiu_imprevistos_default`
  - Utilidad (%): `aiu_utilidad_default`

##### Configuración de Secuencia
- **Prefijo de Secuencia** (`prefijo_secuencia`): Ej: "STS. "
- **Sufijo de Secuencia** (`sufijo_secuencia`): Ej: "-2026"
- **Semilla Inicial** (`semilla_inicial`): Number, default 1, min 1

##### Estado
- **Plantilla Activa** (`es_activo`): Checkbox, checked por defecto

#### Botones
- **Cancelar**: Cierra offcanvas
- **Crear Plantilla** (`#btn-submit-plantilla-crear`): Submit del formulario

#### Script
- `plantilla_crear.js`: Maneja validación y envío del formulario

#### Flujo de Funcionamiento

1. **Carga**: HTMX carga template en offcanvas secundario
2. **Inicialización**: `plantilla_crear.js` adjunta event listeners
3. **Toggle AIU**: Checkbox muestra/oculta campos AIU
4. **Validación**: Validación HTML5 + validación JavaScript
5. **Submit**: POST a `/api/v1/cotizaciones/configuracion/`
6. **Éxito**: Cierra offcanvas y refresca tabla de plantillas

---

### 6. `offcanvas_plantilla_editar.html` - Editar Plantilla

**Propósito:** Formulario para editar plantilla/configuración existente.

#### Diferencias con Crear

- **Header**: Color warning (amarillo) vs primary (azul)
- **Campo oculto**: `#edit-plantilla-id` con ID de plantilla
- **Valores precargados**: Todos los campos tienen valores desde `{{ configuracion.* }}`
- **Container AIU**: Visible si `configuracion.usa_aiu` es True
- **Botón Submit**: "Guardar Cambios" (warning) vs "Crear Plantilla" (primary)

#### Campos (Idénticos a Crear)

Mismos campos que `offcanvas_plantilla_crear.html` pero con valores precargados desde el contexto Django.

#### Script
- `plantilla_editar.js`: Maneja validación y envío (PATCH)

#### Flujo de Funcionamiento

1. **Carga**: HTMX carga template con contexto `{{ configuracion }}`
2. **Inicialización**: `plantilla_editar.js` adjunta event listeners
3. **Toggle AIU**: Checkbox muestra/oculta campos AIU según estado actual
4. **Validación**: Validación HTML5 + validación JavaScript
5. **Submit**: PATCH a `/api/v1/cotizaciones/configuracion/{id}/`
6. **Éxito**: Cierra offcanvas y refresca tabla de plantillas

---

### 7. `offcanvas_ver_detalle.html` - Ver Detalle de Plantilla

**Propósito:** Vista de solo lectura para ver detalles completos de una plantilla.

#### Secciones de Información

##### Información General (Líneas 9-21)
- **Nombre**: `#view-nombre`
- **Tipo Base**: `#view-tipo`
- **IVA aplicado**: `#view-iva` (con %)

##### Configuración de Código (Líneas 23-35)
- **Prefijo**: `#view-prefijo`
- **Sufijo**: `#view-sufijo`
- **Secuencia Actual**: `#view-secuencia` (text-success)

##### Desglose AIU (Líneas 37-49)
- **Container**: `#view-section-aiu` (oculto por defecto, `d-none`)
- **Administración**: `#view-aiu-admin` (con %)
- **Imprevistos**: `#view-aiu-imprev` (con %)
- **Utilidad**: `#view-aiu-util` (con %)

#### Botón
- **Cerrar Vista**: Cierra offcanvas

#### Script
- `plantilla_ver.js`: Carga datos y popula campos

#### Flujo de Funcionamiento

1. **Carga**: HTMX carga template (sin contexto inicial)
2. **Inicialización**: `plantilla_ver.js` hace GET a API para obtener datos
3. **Poblado**: Script popula todos los campos `#view-*`
4. **Toggle AIU**: Muestra sección AIU si `usa_aiu` es True

---

## 🔄 Flujo Completo de Usuario

### Escenario 1: Crear Nueva Cotización

```
1. Usuario en list.html
   ↓
2. Click "Nueva Cotización"
   ↓
3. HTMX carga editor_cotizacion.html en #offcanvas-editor-container
   ↓
4. cotizacion_editor.js se inicializa
   ↓
5. Usuario selecciona Cliente, Perfil y Fecha de Vencimiento
   ↓
6. Al seleccionar Perfil, se muestran secciones correspondientes (equipos/materiales/servicios)
   ↓
7. Usuario hace click en botón "+" en columna ACCIONES para añadir fila
   ↓
8. Usuario edita cantidad o precio unitario
   ↓
9. recalcularFila() calcula subtotal en tiempo real
   ↓
10. actualizarPanelTotales() actualiza IVA y total
   ↓
11. Usuario click "Guardar Cotización"
   ↓
12. cotizacion_editor.js envía datos al backend
   ↓
13. Éxito: Cierra offcanvas y refresca tabla en list.html
```

### Escenario 2: Editar Cotización Existente

```
1. Usuario en list.html
   ↓
2. Click botón "Editar" en fila de cotización
   ↓
3. HTMX carga editor_cotizacion.html con data-cotizacion-uuid
   ↓
4. cotizacion_editor.js detecta UUID y carga datos existentes
   ↓
5. Se muestran secciones con items precargados
   ↓
6. Usuario modifica items (añadir/editar/eliminar)
   ↓
7. Cálculos se actualizan en tiempo real
   ↓
8. Usuario click "Guardar Cotización"
   ↓
9. PATCH al backend con datos actualizados
   ↓
10. Éxito: Cierra offcanvas y refresca tabla
```

### Escenario 3: Gestionar Plantillas

```
1. Usuario en list.html
   ↓
2. Click "Ver Parámetros"
   ↓
3. HTMX carga offcanvas_list_plantillas.html
   ↓
4. plantillas_list.js inicializa tabla con plantillas existentes
   ↓
5a. CREAR: Click "Nueva Plantilla"
     ↓
     5a.1. HTMX carga offcanvas_plantilla_crear.html en offcanvas secundario
     ↓
     5a.2. Usuario completa formulario
     ↓
     5a.3. plantilla_crear.js envía POST
     ↓
     5a.4. Éxito: Cierra offcanvas y refresca tabla
   ↓
5b. EDITAR: Click "Editar" en fila
     ↓
     5b.1. HTMX carga offcanvas_plantilla_editar.html con contexto
     ↓
     5b.2. Usuario modifica campos
     ↓
     5b.3. plantilla_editar.js envía PATCH
     ↓
     5b.4. Éxito: Cierra offcanvas y refresca tabla
   ↓
5c. VER: Click "Ver" en fila
     ↓
     5c.1. HTMX carga offcanvas_ver_detalle.html
     ↓
     5c.2. plantilla_ver.js carga datos y popula campos
     ↓
     5c.3. Usuario ve información completa (solo lectura)
```

---

## 🔌 Integración con JavaScript

### Módulos JavaScript Principales

#### 1. `cotizaciones.page.js`
- **Responsabilidad**: Inicializa tabla principal y maneja eventos de listado
- **Dependencias**: TabulatorFactory, cotizacionesAPI, CotizacionesHelpers
- **Selectores críticos**:
  - `#grid-cotizaciones`: Tabla principal
  - `#search-cotizacion`: Búsqueda
  - `#grid-configuraciones-parametros`: Tabla de configuraciones

#### 2. `cotizacion_editor.js`
- **Responsabilidad**: Lógica del editor de cotizaciones
- **Dependencias**: `getCotizacionColumns()` (de `cotizacion_columns.js`)
- **Funciones principales**:
  - `CotizacionEditorModule.init()`: Inicializa editor
  - `CotizacionEditorModule.actualizarPanelTotales()`: Recalcula totales
  - `CotizacionEditorModule.reindexarFilas()`: Reindexa números de item

#### 3. `cotizacion_columns.js`
- **Responsabilidad**: Define columnas de Tabulator para items
- **Función principal**: `getCotizacionColumns(seccion, isEditable)`
- **Características**:
  - Cálculo en tiempo real mediante `recalcularFila()`
  - `dataType: "number"` para evitar problemas con strings
  - Validadores para cantidad y precio unitario

#### 4. `plantillas_list.js`
- **Responsabilidad**: Inicializa tabla de plantillas en offcanvas
- **Selector**: `#grid-plantillas-offcanvas`

#### 5. `plantilla_crear.js` / `plantilla_editar.js`
- **Responsabilidad**: Manejo de formularios de plantillas
- **Validación**: HTML5 + JavaScript
- **Envío**: POST (crear) / PATCH (editar)

#### 6. `plantilla_ver.js`
- **Responsabilidad**: Carga y muestra detalles de plantilla
- **Método**: GET a API y populado de campos

### Comunicación entre Módulos

```
list.html
  └─ cotizaciones.page.js
      ├─ Inicializa tabla principal
      ├─ Maneja click "Nueva Cotización" → HTMX carga editor_cotizacion.html
      └─ Maneja click "Ver Parámetros" → HTMX carga offcanvas_list_plantillas.html

editor_cotizacion.html
  └─ cotizacion_editor.js
      ├─ Depende de: cotizacion_columns.js (getCotizacionColumns)
      ├─ Usa: CotizacionEditorModule
      └─ Llama a: actualizarPanelTotales(), reindexarFilas()

offcanvas_list_plantillas.html
  └─ plantillas_list.js
      ├─ Inicializa tabla de plantillas
      └─ Maneja acciones: Ver, Editar, Eliminar

offcanvas_plantilla_crear.html
  └─ plantilla_crear.js
      └─ Maneja submit del formulario

offcanvas_plantilla_editar.html
  └─ plantilla_editar.js
      └─ Maneja submit del formulario (PATCH)

offcanvas_ver_detalle.html
  └─ plantilla_ver.js
      └─ Carga datos y popula campos
```

---

## 🌐 Endpoints y APIs

### Endpoints de Cotizaciones

#### Listado y CRUD
- `GET /api/v1/cotizaciones/` - Lista cotizaciones
- `POST /api/v1/cotizaciones/` - Crea cotización
- `GET /api/v1/cotizaciones/{id}/` - Obtiene cotización
- `PATCH /api/v1/cotizaciones/{id}/` - Actualiza cotización
- `DELETE /api/v1/cotizaciones/{id}/` - Elimina cotización

#### Acciones Especiales
- `POST /api/v1/cotizaciones/{id}/convertir_a_factura/` - Convierte cotización aceptada a factura
- `POST /api/v1/cotizaciones/{id}/marcar_enviada/` - Marca como enviada
- `POST /api/v1/cotizaciones/{id}/marcar_aceptada/` - Marca como aceptada

### Endpoints de Configuraciones/Plantillas

#### CRUD
- `GET /api/v1/cotizaciones/configuracion/` - Lista plantillas
- `POST /api/v1/cotizaciones/configuracion/` - Crea plantilla
- `GET /api/v1/cotizaciones/configuracion/{id}/` - Obtiene plantilla
- `PATCH /api/v1/cotizaciones/configuracion/{id}/` - Actualiza plantilla
- `DELETE /api/v1/cotizaciones/configuracion/{id}/` - Elimina plantilla

### Endpoints UI (HTMX)

#### Vistas de Templates
- `GET /cotizaciones/ui/editor/draft/` → Renderiza `editor_cotizacion.html`
- `GET /cotizaciones/ui/list/configuracion/` → Renderiza `offcanvas_list_plantillas.html`
- `GET /cotizaciones/ui/crear/configuracion/` → Renderiza `offcanvas_plantilla_crear.html`
- `GET /cotizaciones/ui/editar/configuracion/{id}/` → Renderiza `offcanvas_plantilla_editar.html` con contexto
- `GET /cotizaciones/ui/ver/configuracion/{id}/` → Renderiza `offcanvas_ver_detalle.html`

---

## 📊 Diagramas de Flujo

### Flujo de Creación de Cotización

```
[Usuario] → Click "Nueva Cotización"
    ↓
[HTMX] → GET /cotizaciones/ui/editor/draft/
    ↓
[Backend] → Renderiza editor_cotizacion.html
    ↓
[Frontend] → Carga en #offcanvas-editor-container
    ↓
[cotizacion_editor.js] → Inicializa editor
    ↓
[Usuario] → Selecciona Cliente, Perfil, Fecha
    ↓
[Frontend] → Muestra secciones según tipo de plantilla
    ↓
[Usuario] → Añade items (click "+")
    ↓
[Usuario] → Edita cantidad/precio
    ↓
[recalcularFila()] → Calcula subtotal en tiempo real
    ↓
[actualizarPanelTotales()] → Actualiza IVA y total
    ↓
[Usuario] → Click "Guardar Cotización"
    ↓
[cotizacion_editor.js] → POST /api/v1/cotizaciones/
    ↓
[Backend] → Crea cotización y items
    ↓
[Frontend] → Cierra offcanvas y refresca tabla
```

### Flujo de Gestión de Plantillas

```
[Usuario] → Click "Ver Parámetros"
    ↓
[HTMX] → GET /cotizaciones/ui/list/configuracion/
    ↓
[Backend] → Renderiza offcanvas_list_plantillas.html
    ↓
[Frontend] → Carga en #offcanvas-container
    ↓
[plantillas_list.js] → Inicializa tabla
    ↓
[plantillas_list.js] → GET /api/v1/cotizaciones/configuracion/
    ↓
[Backend] → Retorna lista de plantillas
    ↓
[Frontend] → Muestra tabla con plantillas
    ↓
[Usuario] → Click "Nueva Plantilla" / "Editar" / "Ver"
    ↓
[HTMX] → Carga template correspondiente
    ↓
[JavaScript específico] → Maneja formulario/vista
    ↓
[Submit] → POST/PATCH a API
    ↓
[Backend] → Guarda cambios
    ↓
[Frontend] → Cierra offcanvas y refresca tabla
```

---

## 🔍 Puntos Críticos y Consideraciones

### Orden de Carga de Scripts

⚠️ **CRÍTICO**: El orden de carga en `assets_cotizaciones.html` y `editor_cotizacion.html` es **OBLIGATORIO**:

1. `cotizacion_columns.js` **DEBE** cargarse antes de `cotizacion_editor.js`
2. `cotizaciones.api.js` **DEBE** cargarse antes de `cotizaciones.page.js`
3. `assets_core.html` **DEBE** cargarse primero (incluye TabulatorFactory)

### Selectores HTML

⚠️ Los selectores en templates **DEBEN** coincidir exactamente con los definidos en JavaScript:

- `#grid-cotizaciones` en `list.html` → `TABLE_SELECTOR` en `cotizaciones.page.js`
- `#search-cotizacion` en `list.html` → `SEARCH_SELECTOR` en `cotizaciones.page.js`
- `#grid-editor-equipos` en `editor_cotizacion.html` → Usado por `cotizacion_editor.js`

### Cálculo en Tiempo Real

⚠️ La función `recalcularFila()` en `cotizacion_columns.js` es crítica:

- Se dispara automáticamente al editar `cantidad` o `costo_unitario`
- Usa `dataType: "number"` para evitar problemas con strings
- Actualiza `subtotal_linea` sin disparar eventos adicionales (`row.update(..., false)`)
- Notifica a `CotizacionEditorModule.actualizarPanelTotales()` para recalcular totales

### Offcanvas en Cascada

⚠️ `offcanvas_list_plantillas.html` usa offcanvas secundario:

- Z-index: 1056 (por encima del principal)
- Función `window.abrirOffcanvasSecundario()` maneja apertura después de carga HTMX
- Usa event listener `htmx:afterSwap` para detectar cuando el contenido está listo

### Inmutabilidad de Cotizaciones Aceptadas

⚠️ Las cotizaciones con estado "ACEPTADA" **NO pueden ser editadas**:

- Validación en backend
- Botón "Editar" se oculta en frontend para cotizaciones aceptadas
- Solo pueden convertirse a factura

---

## 📝 Notas de Versión

### v2.60
- ✅ Cálculo en tiempo real de subtotales
- ✅ `dataType: "number"` para evitar problemas con strings
- ✅ Error Boundary v2.60 para manejo centralizado de errores
- ✅ Arquitectura modular con Feature-Sliced
- ✅ Offcanvas navigation (sin modales)

### v2.40
- ✅ Editor integrado en `cotizacion_editor.js`
- ✅ DNA Dinámico para secciones modulares
- ✅ Inmutabilidad de cotizaciones aceptadas

---

## 🔗 Referencias

- **Arquitectura General**: `documentacion/arquitectura_general.md`
- **API Core**: `documentacion/ARQUITECTURA_CORE_API_v2.30.md`
- **Tabulator Factory**: `apps/tenant/core/static/core/js/tabulator.factory.js`
- **UI Manager**: `apps/tenant/core/static/core/js/ui-manager.js`

---

**Documento generado automáticamente**  
**Última actualización**: 2026-01-XX
