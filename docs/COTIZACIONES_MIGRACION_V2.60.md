# Migración y Correcciones del Módulo Cotizaciones v2.60

## Resumen Ejecutivo

Este documento describe la migración completa del módulo de Cotizaciones a la arquitectura SINTEL v2.60, incluyendo la implementación del Patrón Wizard, correcciones de errores de Tabulator, y la alineación con los principios de Feature-Sliced Design, API-First, y Zero Trust.

**Fecha de Documentación:** 2024
**Versión:** 2.60.3
**Estado:** Completado

---

## 1. Arquitectura y Principios Aplicados

### 1.1 Principios SINTEL v2.60

- **API-First**: Toda la lógica de negocio está en DRF (Django Rest Framework)
- **Feature-Sliced Design**: Módulos dedicados por funcionalidad (`features/`)
- **Zero Trust**: Validaciones estrictas en serializers y servicios
- **SSoT (Single Source of Truth)**: Un solo punto de verdad para datos y URLs
- **Wizard Pattern**: Flujo de dos fases (Fase A: Creación inicial, Fase B: Editor completo)

### 1.2 Estructura de Archivos

```
apps/tenant/cotizaciones/
├── api/
│   ├── urls.py              # SSoT para todas las URLs (API + UI)
│   ├── viewsets.py          # ViewSets DRF (CRUD)
│   └── serializers.py       # Serializers con validación Zero Trust
├── ui_views.py              # Solo TemplateView (sin lógica de negocio)
├── services.py              # Lógica de negocio (cálculos, generación de códigos)
├── models.py               # Modelos de dominio
└── configuracion/
    ├── models.py           # Modelo de plantillas/base
    └── viewsets.py         # ViewSet para configuraciones

apps/tenant/core/
├── templates/tenant/core/partials/cotizaciones/
│   ├── list.html                           # Workspace principal
│   ├── offcanvas_crear.htm                 # Fase A del Wizard
│   ├── editor_cotizacion.html              # Fase B del Wizard
│   ├── offcanvas_list_plantillas.html      # Lista de plantillas
│   ├── offcanvas_plantilla_crear.html      # Crear plantilla
│   ├── offcanvas_plantilla_editar.html     # Editar plantilla
│   └── offcanvas_ver_detalle.html          # Ver detalles (solo lectura)
└── static/core/js/cotizaciones/
    ├── cotizaciones.api.js                 # Wrapper de API
    ├── cotizaciones.page.js                # Tabulator principal
    ├── cotizaciones.helpers.js             # Funciones utilitarias
    ├── cotizacion_columns.js                # Definición de columnas
    ├── htmx-handlers.js                    # Handlers globales HTMX
    └── features/
        ├── cotizacion_crear.js             # Fase A del Wizard
        ├── cotizacion_editor.js            # Fase B del Wizard
        ├── plantillas_list.js               # Lista de plantillas (Tabulator nativo)
        ├── plantilla_crear.js               # Crear plantilla
        ├── plantilla_editar.js              # Editar plantilla
        └── plantilla_ver.js                 # Ver detalles de plantilla
```

---

## 2. Migración de Arquitectura

### 2.1 Eliminación de Código Legacy

**Archivos Eliminados:**
- `apps/tenant/cotizaciones/views.py` (migrado a `api/viewsets.py` y `ui_views.py`)
- `apps/tenant/cotizaciones/urls_ui.py` (consolidado en `api/urls.py`)
- `apps/tenant/cotizaciones/templates/` (migrado a `apps/tenant/core/templates/`)
- `apps/tenant/cotizaciones/static/` (migrado a `apps/tenant/core/static/`)
- `apps/tenant/core/static/core/js/cotizaciones/cotizacion_modals.js` (reemplazado por módulos Feature-Sliced)

### 2.2 Consolidación de URLs

**Antes:**
- URLs API en `api/urls.py`
- URLs UI en `urls_ui.py` (separado)

**Después:**
- **SSoT**: `api/urls.py` contiene tanto `api_urlpatterns` (DRF) como `ui_urlpatterns` (TemplateView)
- Todas las rutas se importan desde un solo archivo en `config/urls_tenant.py`

### 2.3 Separación de Responsabilidades

**Backend:**
- `api/viewsets.py`: CRUD vía DRF
- `api/serializers.py`: Validación Zero Trust
- `services.py`: Lógica de negocio (cálculos, generación de códigos)
- `ui_views.py`: Solo renderiza HTML (TemplateView)

**Frontend:**
- `cotizaciones.api.js`: Comunicación con API
- `cotizaciones.page.js`: Inicialización de Tabulator principal
- `features/*.js`: Módulos dedicados por funcionalidad

---

## 3. Implementación del Patrón Wizard

### 3.1 Fase A: Creación Inicial (`offcanvas_crear.htm` + `cotizacion_crear.js`)

**Flujo:**
1. Usuario completa formulario básico (cliente, plantilla, fecha vencimiento)
2. JavaScript valida y aplica DOM Shield (protección del ID del cliente)
3. Datos se guardan en `sessionStorage` como `sintel_draft_cotizacion`
4. Click en "Siguiente Paso" → cierra offcanvas y carga editor vía HTMX
5. Se abre el editor en modo borrador

**Características:**
- DOM Shield: Input oculto con `name="cliente"` que contiene el ID numérico
- Validación client-side antes de guardar en sessionStorage
- No hace POST a la API (se hace en Fase B)
- **Delegación de Eventos**: Listener en `body` con capture phase para evitar colisiones con HTMX
- **Tipo Automático**: El tipo de cotización se asigna automáticamente desde el perfil seleccionado (no se solicita al usuario)

### 3.2 Fase B: Editor Completo (`editor_cotizacion.html` + `cotizacion_editor.js`)

**Flujo:**
1. Editor lee `sessionStorage` al inicializar
2. Si es borrador: tablas Tabulator en modo local (sin AJAX)
3. Si es edición: tablas cargan items desde API
4. Usuario agrega/edita items en las tablas
5. Al guardar: POST único con cabecera + items anidados
6. `sessionStorage` se limpia automáticamente después de guardar exitosamente

**Características:**
- State-Aware: Detecta modo borrador vs edición
- Tablas locales en borrador (evita errores de UUID inexistente)
- POST unificado: Cabecera + items en una sola petición
- Cálculo de totales en tiempo real
- **Consulta de Tipo**: El tipo de cotización se consulta desde el perfil seleccionado cuando es borrador
- **Limpieza Automática**: `sessionStorage` se limpia después de guardar para evitar conflictos

---

## 4. Correcciones de Errores Críticos

### 4.1 Error: "Cannot read properties of undefined (reading 'slice')"

**Causa:**
- `plantillas_list.js` usaba `TabulatorFactory.create()` que corrompía el objeto de configuración
- El Factory transformaba `ajaxURL` en un objeto, causando que Tabulator nativo fallara

**Solución:**
- Cambio a `new w.Tabulator()` directamente (Tabulator nativo)
- Decodificador DRF manual con `ajaxResponse`
- Endpoint correcto: `/api/v1/cotizaciones/configuracion/` (singular)

**Archivo:** `apps/tenant/core/static/core/js/cotizaciones/features/plantillas_list.js`

### 4.2 Error: "Cannot build header filter, No such editor found: undefined"

**Causa:**
- Columnas con `headerFilter: true` o variables que evaluaban a `undefined`
- Tabulator intentaba inferir el tipo de editor y fallaba

**Solución:**
- Todas las columnas tienen `headerFilter` explícito:
  - `"input"` para filtros de texto
  - `"select"` para filtros de selección
  - `false` para columnas sin filtro

**Archivos Corregidos:**
- `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.page.js`
  - Columna "Fecha": `headerFilter: false`
  - Columna "Total": `headerFilter: false`
  - Columna "Vencimiento": `headerFilter: false`
  - Columna "Acciones": `headerFilter: false`
  - **Función `sanitizeColumns()`**: Sanitiza todas las columnas antes de pasarlas al Factory
    - Convierte `headerFilter: true` → `"input"`
    - Convierte `headerFilter: undefined` → `false`
    - Valida strings de headerFilter
    - Sanitiza editores para evitar `undefined`
  - **Tabla de Configuraciones**: Todas las columnas tienen `headerFilter: false` explícito

### 4.3 Error: Caché del Navegador

**Causa:**
- Navegador retenía versiones antiguas de scripts JS

**Solución:**
- Cache-Busting implementado: `?v=2.60.1` en todos los scripts
- Archivos actualizados:
  - `assets_cotizaciones.html`
  - `offcanvas_list_plantillas.html`
  - `offcanvas_plantilla_crear.html`
  - `offcanvas_plantilla_editar.html`

### 4.4 Error: Formatters Undefined

**Causa:**
- Referencias a `w.TabulatorFactory.formatters.valueOrFallback` sin validación

**Solución:**
- Validación defensiva con fallback:
```javascript
formatter: (w.TabulatorFactory && w.TabulatorFactory.formatters && w.TabulatorFactory.formatters.valueOrFallback) 
  ? w.TabulatorFactory.formatters.valueOrFallback 
  : function(cell) { return cell.getValue() || ''; }
```

### 4.5 Error: "w is not defined" en onclick

**Causa:**
- Referencias a `w.` en atributos `onclick` del HTML generado por formatters
- El alias `w` solo existe dentro del scope del IIFE

**Solución:**
- Cambio de `w.SintelPlantillas` a `window.SintelPlantillas` en todos los `onclick`
- Exposición explícita: `window.SintelPlantillas = w.SintelPlantillas`

**Archivo:** `apps/tenant/core/static/core/js/cotizaciones/features/plantillas_list.js`

### 4.6 Error: "w.SintelFeedback.confirm is not a function"

**Causa:**
- Llamada a `w.SintelFeedback.confirm()` sin verificar existencia del método

**Solución:**
- Implementación de Graceful Degradation con múltiples fallbacks:
  1. SintelFeedback (preferido)
  2. SweetAlert2 (fallback)
  3. `confirm()` nativo (último recurso)

**Archivo:** `apps/tenant/core/static/core/js/cotizaciones/features/plantillas_list.js`

---

## 5. Mejoras de Backend

### 5.1 Generación de Código Único

**Implementación:**
- `CotizacionService.generar_codigo_unico(perfil_id, empresa_id)`
- Usa `select_for_update()` y `F()` expressions para atomicidad
- Formato: `prefijo + numero_formateado + sufijo` (ej: "STS. 0422-2026")

**Características:**
- Thread-safe: Previene race conditions
- Histórico: Mantiene integridad si el perfil cambia
- Configurable: Prefijo, sufijo y semilla por perfil

### 5.2 Cálculo de Totales

**Implementación:**
- `CotizacionService.calcular_totales(cotizacion_id)`
- SSoT para todos los cálculos financieros

**Lógica:**
1. Suma subtotales de items
2. Calcula AIU (si está activo) sobre subtotal
3. Calcula IVA sobre (subtotal + AIU)
4. Total = subtotal + AIU + IVA

### 5.3 DNA Inheritance (Herencia de Plantilla)

**Concepto:**
- Al crear una cotización, se copian los valores actuales del perfil
- Si el perfil cambia en el futuro, las cotizaciones viejas mantienen sus valores históricos

**Campos Copiados:**
- `iva_porcentaje_default` → `iva_porcentaje`
- `aiu_admin_default` → `porcentaje_aiu_admin`
- `aiu_imprevistos_default` → `porcentaje_aiu_imprevistos`
- `aiu_utilidad_default` → `porcentaje_aiu_utilidad`
- `tipo_cotizacion_default` → `tipo_cotizacion`

---

## 6. Mejoras de Frontend

### 6.1 DOM Shield Pattern

**Problema:**
- El backend recibía texto descriptivo en lugar del ID numérico del cliente

**Solución:**
- Input oculto: `<input type="hidden" id="hidden-cliente-id" name="cliente">`
- Select visible: `<select id="select-cliente">` (sin `name`)
- JavaScript sincroniza el select con el input oculto

**Archivo:** `offcanvas_crear.htm` + `cotizacion_crear.js`

### 6.2 State-Aware Editor

**Características:**
- Detecta modo borrador: `!inputUuid.value`
- Modo borrador: Tablas locales, no hacen AJAX
- Modo edición: Tablas cargan desde API, autoguardado habilitado

**Archivo:** `cotizacion_editor.js`

### 6.3 Inicialización Resiliente

**Problema:**
- Scripts se ejecutaban antes de que HTMX inyectara el HTML

**Solución:**
- Múltiples estrategias de inicialización:
  1. Inmediata si DOM está listo
  2. `htmx:afterSwap` con delay
  3. Polling fallback si es necesario

**Patrón:**
```javascript
function safeInit() {
    if (!Module.table) Module.init();
}

if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', safeInit);
} else {
    safeInit();
}

d.body.addEventListener('htmx:afterSwap', function(event) {
    if (event.detail.target.querySelector(selector)) {
        setTimeout(safeInit, 50);
    }
});
```

---

## 7. Configuración de Plantillas (CRUD Completo)

### 7.1 Lista de Plantillas

**Archivo:** `offcanvas_list_plantillas.html` + `plantillas_list.js`

**Características:**
- Tabulator nativo (evita bug del Factory)
- Endpoint: `/api/v1/cotizaciones/configuracion/`
- Acciones: Ver, Editar, Eliminar
- Decodificador DRF manual

### 7.2 Crear/Editar Plantilla

**Archivos:**
- `offcanvas_plantilla_crear.html` + `plantilla_crear.js`
- `offcanvas_plantilla_editar.html` + `plantilla_editar.js`

**Características:**
- Formularios HTMX
- Validación client-side
- Integración con API DRF

### 7.3 Ver Detalles de Plantilla

**Archivos:**
- `offcanvas_ver_detalle.html` + `plantilla_ver.js`

**Características:**
- Vista de solo lectura
- Carga datos dinámicamente desde API
- Secciones organizadas:
  - Información General (nombre, tipo, IVA)
  - Configuración de Código (prefijo, sufijo, secuencia actual)
  - Desglose AIU (condicional, solo si `usa_aiu` es true)
- Obtiene ID desde `window.lastViewedPlantillaId` o desde URL
- Abre offcanvas automáticamente después de cargar datos

**Ruta UI:**
- `GET /cotizaciones/partials/configuracion/ver/{id}/` - Vista de detalles

---

## 8. Validaciones Zero Trust

### 8.1 Serializer Validations

**Cliente:**
- Obligatorio: `required=True, allow_null=False`
- Validación de existencia y pertenencia a empresa
- Conversión segura de tipos (string → int)

**Configuración (Perfil):**
- Obligatorio: `required=True, allow_null=False`
- Validación de existencia y pertenencia a empresa
- Validación de unicidad de `numero_cotizacion` por empresa y perfil

**Items:**
- Validación de tipo_item vs producto/servicio
- Cálculo automático de `precio_unitario_venta` y `subtotal_linea`

### 8.2 Service Layer Validations

**Empresa:**
- SSoT: Se obtiene del tenant, nunca del payload
- Validación de existencia antes de crear cotización

**Perfil:**
- Validación de existencia y pertenencia a empresa
- Validación de campos requeridos para generación de código

---

## 9. Endpoints API

### 9.1 Cotizaciones

- `GET /api/v1/cotizaciones/` - Lista paginada
- `POST /api/v1/cotizaciones/` - Crear (acepta items anidados)
- `GET /api/v1/cotizaciones/{uuid}/` - Detalle
- `PATCH /api/v1/cotizaciones/{uuid}/` - Actualizar
- `DELETE /api/v1/cotizaciones/{uuid}/` - Eliminar
- `POST /api/v1/cotizaciones/{uuid}/recalcular/` - Recalcular totales

### 9.2 Items

- `GET /api/v1/cotizaciones/items/` - Lista
- `POST /api/v1/cotizaciones/items/` - Crear
- `PATCH /api/v1/cotizaciones/items/{id}/` - Actualizar
- `DELETE /api/v1/cotizaciones/items/{id}/` - Eliminar

### 9.3 Configuraciones

- `GET /api/v1/cotizaciones/configuracion/` - Lista
- `POST /api/v1/cotizaciones/configuracion/` - Crear
- `GET /api/v1/cotizaciones/configuracion/{id}/` - Detalle
- `PATCH /api/v1/cotizaciones/configuracion/{id}/` - Actualizar
- `DELETE /api/v1/cotizaciones/configuracion/{id}/` - Eliminar

### 9.4 UI (HTMX)

- `GET /cotizaciones/partials/crear/` - Offcanvas de creación
- `GET /cotizaciones/editor/draft/` - Editor en modo borrador
- `GET /cotizaciones/editor/{uuid}/` - Editor de cotización existente
- `GET /cotizaciones/partials/configuracion/lista/` - Lista de plantillas
- `GET /cotizaciones/partials/configuracion/crear/` - Crear plantilla
- `GET /cotizaciones/partials/configuracion/editar/{id}/` - Editar plantilla
- `GET /cotizaciones/partials/configuracion/ver/{id}/` - Ver detalles de plantilla

---

## 10. Checklist de Verificación

### 10.1 Backend
- [x] Eliminado `views.py` legacy
- [x] Eliminado `urls_ui.py` legacy
- [x] URLs consolidadas en `api/urls.py`
- [x] `ui_views.py` solo contiene TemplateView
- [x] Validaciones Zero Trust en serializers
- [x] Lógica de negocio en `services.py`
- [x] Generación de código único implementada
- [x] Cálculo de totales implementado

### 10.2 Frontend
- [x] Eliminado `cotizacion_modals.js` legacy
- [x] Módulos Feature-Sliced en `features/`
- [x] DOM Shield implementado
- [x] Wizard Pattern implementado (Fase A + Fase B)
- [x] Cache-Busting implementado (versión dinámica con timestamp)
- [x] Delegación de eventos implementada para evitar colisiones con HTMX
- [x] Asignación automática de tipo desde perfil
- [x] HeaderFilters corregidos
- [x] Tabulator nativo en `plantillas_list.js`
- [x] Inicialización resiliente

### 10.3 Errores Corregidos
- [x] Error `.slice()` en plantillas_list.js
- [x] Error headerFilter undefined
- [x] Error formatters undefined
- [x] Error caché del navegador
- [x] Error cliente ID vs texto descriptivo
- [x] Error "w is not defined" en onclick
- [x] Error "SintelFeedback.confirm is not a function"
- [x] Sanitización de columnas implementada
- [x] Módulo "Ver Detalles" implementado
- [x] Campo "Tipo de Cotización" eliminado (asignación automática desde perfil)
- [x] Botón "Siguiente Paso" implementado con delegación de eventos
- [x] Colisiones de eventos con HTMX resueltas
- [x] Limpieza automática de sessionStorage implementada
- [x] Error Offcanvas "backdrop undefined" corregido (solo creación de plantillas)

---

## 11. Próximos Pasos Recomendados

### 11.1 Mejoras Futuras
- [ ] Implementar autoguardado en editor (debounce)
- [ ] Agregar validación de items duplicados
- [ ] Implementar exportación a PDF
- [ ] Agregar historial de cambios
- [ ] Implementar notificaciones de vencimiento

### 11.2 Optimizaciones
- [ ] Lazy loading de items en tablas grandes
- [ ] Virtual scrolling en Tabulator
- [ ] Compresión de respuestas API
- [ ] Cache de plantillas frecuentes

---

## 12. Referencias

### 12.1 Documentación Técnica
- SINTEL v2.60 Architecture Rules
- Tabulator Factory v2.40 Documentation
- HTMX Best Practices
- Django REST Framework Serializers

### 12.2 Archivos Clave
- `apps/tenant/cotizaciones/api/urls.py` - SSoT de URLs
- `apps/tenant/cotizaciones/services.py` - Lógica de negocio
- `apps/tenant/core/static/core/js/cotizaciones/features/cotizacion_editor.js` - Wizard Fase B
- `apps/tenant/core/templates/tenant/core/partials/cotizaciones/editor_cotizacion.html` - Template del editor

---

## 13. Notas de Versión

### v2.60.3 (Actual)
- **Eliminación del campo "Tipo de Cotización"**: Se asigna automáticamente desde el perfil seleccionado
- **Botón "Siguiente Paso"**: Implementado con delegación de eventos para evitar colisiones con HTMX
- **Delegación de Eventos**: Listener en `body` con capture phase para garantizar funcionamiento con contenido dinámico
- **Limpieza de sessionStorage**: Se limpia automáticamente después de guardar exitosamente
- **Cache-Busting Dinámico**: Uso de timestamp (`{% now 'U' %}`) para forzar recarga de scripts
- **Consulta de Tipo desde Perfil**: El editor consulta el tipo del perfil cuando es borrador

### v2.60.2
- Implementación del módulo "Ver Detalles" para plantillas
- Corrección de referencias globales (w vs window) en onclick
- Implementación de Graceful Degradation en función eliminar
- Sanitización de columnas antes de pasar al TabulatorFactory
- Corrección de headerFilter en tabla de configuraciones

### v2.60.1
- Corrección de error `.slice()` en plantillas_list.js
- Corrección de headerFilter undefined
- Implementación de cache-busting
- Migración completa a Tabulator nativo para plantillas

### v2.60.0
- Migración inicial a arquitectura SINTEL v2.60
- Implementación del Patrón Wizard
- Eliminación de código legacy
- Consolidación de URLs

---

---

## 14. Correcciones Adicionales Implementadas

### 14.1 Sanitización de Columnas

**Problema:**
- Columnas con `headerFilter: true` o `undefined` causaban errores en Tabulator
- El TabulatorFactory no sanitizaba las columnas antes de pasarlas a Tabulator nativo

**Solución:**
- Función `sanitizeColumns()` implementada en `cotizaciones.page.js`
- Aplicada a ambas tablas: principal y configuraciones
- Convierte valores inválidos a valores seguros antes de inicializar

**Código:**
```javascript
function sanitizeColumns(columns) {
    return columns.map(col => {
        const sanitized = { ...col };
        
        // Sanitizar headerFilter
        if (sanitized.headerFilter === true) {
            sanitized.headerFilter = "input";
        } else if (sanitized.headerFilter === undefined || sanitized.headerFilter === null) {
            sanitized.headerFilter = false;
        }
        
        // Sanitizar editor
        if (sanitized.editor === undefined || sanitized.editor === null) {
            sanitized.editor = false;
        } else if (sanitized.editor === true) {
            sanitized.editor = "input";
        }
        
        return sanitized;
    });
}
```

### 14.2 Graceful Degradation en Confirmaciones

**Problema:**
- Dependencia estricta de `SintelFeedback.confirm()` causaba errores si no estaba disponible

**Solución:**
- Múltiples niveles de fallback:
  1. SintelFeedback (preferido)
  2. SweetAlert2 (fallback intermedio)
  3. `confirm()` nativo (último recurso)

**Beneficios:**
- Nunca falla: siempre hay un método de confirmación disponible
- Mejor UX: usa la mejor opción disponible
- Resiliente: funciona en cualquier entorno

### 14.3 Referencias Globales Corregidas

**Problema:**
- `onclick="w.SintelPlantillas.ver(${id})"` fallaba porque `w` no existe en scope global

**Solución:**
- Cambio a `onclick="window.SintelPlantillas.ver(${id})"`
- Exposición explícita: `window.SintelPlantillas = w.SintelPlantillas`
- Consistencia: todas las referencias usan `window.` en handlers inline

### 14.4 Módulo "Ver Detalles" Implementado

**Características:**
- Offcanvas dedicado para vista de solo lectura
- Carga datos dinámicamente desde API
- Secciones organizadas y condicionales (AIU solo si está activo)
- Obtiene ID desde múltiples fuentes (window.lastViewedPlantillaId o URL)
- Abre automáticamente después de cargar datos

**Archivos:**
- `offcanvas_ver_detalle.html` - Template HTML
- `plantilla_ver.js` - Script de carga de datos
- `ConfiguracionVerOffcanvasView` - Vista Django
- Ruta: `/cotizaciones/partials/configuracion/ver/{id}/`

---

## 15. Patrones de Código Implementados

### 15.1 DOM Shield Pattern

**Uso:** Protección de IDs numéricos en formularios

**Implementación:**
```html
<input type="hidden" id="hidden-cliente-id" name="cliente" value="">
<select id="select-cliente">
  <!-- options sin name attribute -->
</select>
```

**JavaScript:**
```javascript
selectCliente.addEventListener('change', function() {
    hiddenClienteId.value = parseInt(this.value, 10);
});
```

### 15.2 Graceful Degradation Pattern

**Uso:** Funciones que requieren librerías externas

**Implementación:**
```javascript
if (window.SintelFeedback && typeof window.SintelFeedback.confirm === 'function') {
    confirmar = await window.SintelFeedback.confirm(...);
} else if (window.Swal) {
    const result = await window.Swal.fire({...});
    confirmar = result.isConfirmed;
} else {
    confirmar = confirm(...);
}
```

### 15.3 State-Aware Pattern

**Uso:** Detección de modo borrador vs edición

**Implementación:**
```javascript
const esBorrador = !inputUuid || !inputUuid.value || inputUuid.value.trim() === '';

if (esBorrador) {
    // Modo borrador: tablas locales
    tableConfig.data = [];
} else {
    // Modo edición: carga desde API
    tableConfig.ajaxURL = `/api/v1/cotizaciones/items/?cotizacion=${uuid}`;
}
```

### 15.4 Inicialización Resiliente Pattern

**Uso:** Scripts que se cargan vía HTMX

**Implementación:**
```javascript
function safeInit() {
    if (!Module.table) Module.init();
}

if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', safeInit);
} else {
    safeInit();
}

d.body.addEventListener('htmx:afterSwap', function(event) {
    if (event.detail.target.querySelector(selector)) {
        setTimeout(safeInit, 50);
    }
});
```

---

## 16. Mejoras del Wizard Pattern (v2.60.3)

### 16.1 Eliminación del Campo "Tipo de Cotización"

**Problema:**
- El campo "Tipo de Cotización" era redundante, ya que el tipo debe heredarse del perfil seleccionado
- El usuario tenía que seleccionar manualmente un tipo que ya estaba definido en el perfil

**Solución:**
- **Frontend**: Eliminado el campo `select-tipo` del formulario de creación
- **Backend**: El servicio `crear_preforma()` siempre asigna el tipo desde `plantilla.tipo_cotizacion_default`
- **Serializer**: Campo `tipo_cotizacion` es opcional (usa default del modelo)
- **Editor**: Consulta el tipo del perfil desde la API cuando es borrador

**Archivos Modificados:**
- `offcanvas_crear.htm`: Eliminado div con select de tipo
- `cotizacion_crear.js`: Eliminada referencia a `select-tipo` en payload
- `services.py`: Asignación automática desde perfil, eliminado fallback a datos del frontend
- `serializers.py`: Comentarios actualizados, campo opcional
- `cotizacion_editor.js`: Consulta tipo desde perfil cuando es borrador

### 16.2 Botón "Siguiente Paso" con Delegación de Eventos

**Problema:**
- El botón "Siguiente Paso" no funcionaba debido a colisiones de eventos con HTMX
- El listener se perdía cuando HTMX inyectaba contenido dinámicamente
- Posibles conflictos con otros handlers globales

**Solución:**
- **Delegación de Eventos**: Listener en `d.body` con capture phase (`true`)
- **Prioridad**: Capture phase ejecuta antes que otros handlers
- **Aislamiento**: `stopPropagation()` evita interferencias
- **Resiliente**: Funciona incluso cuando HTMX inyecta el formulario después

**Implementación:**
```javascript
d.body.addEventListener('submit', function(e) {
    if (e.target && e.target.id === 'form-crear-cotizacion') {
        e.preventDefault();
        e.stopPropagation();
        ejecutarSiguientePaso(e.target);
    }
}, true); // Capture phase para ganar prioridad
```

**Archivos Modificados:**
- `offcanvas_crear.htm`: Botón `type="submit"` sin atributo `form` redundante
- `cotizacion_crear.js`: Refactorizado con delegación de eventos y función centralizada
- `htmx-handlers.js`: Verificado que no tiene listeners de submit que interfieran

### 16.3 Limpieza Automática de sessionStorage

**Implementación:**
- Después de guardar exitosamente una cotización desde borrador, se limpia `sessionStorage`
- Evita conflictos en futuras creaciones
- Se ejecuta solo si la respuesta es exitosa (`res.ok`)

**Código:**
```javascript
if (esBorrador) {
    sessionStorage.removeItem('sintel_draft_cotizacion');
    console.log('[cotizacion_editor] ✅ sessionStorage limpiado después de guardar');
}
```

### 16.4 Cache-Busting Dinámico

**Implementación:**
- Cambio de versión estática (`?v=2.60.wizard`) a timestamp dinámico (`?t={% now 'U' %}`)
- Fuerza la recarga del script en cada carga de página
- Garantiza que siempre se use la versión más reciente

**Archivo:** `assets_cotizaciones.html`

---

## 17. Flujo Completo del Wizard Pattern (v2.60.3)

### 17.1 Fase A: Creación Inicial

1. **Usuario hace clic en "Nueva Cotización"**
   - Se abre `offcanvas_crear.htm` en `#offcanvas-container`
   - Se cargan clientes y plantillas usando `CotizacionesHelpers`

2. **Usuario completa el formulario**
   - Selecciona Cliente (con DOM Shield)
   - Selecciona Perfil de Configuración
   - Ingresa Fecha de Vencimiento
   - **NO selecciona tipo** (se asigna automáticamente desde el perfil)

3. **Usuario hace clic en "Siguiente Paso"**
   - Delegación de eventos captura el `submit` en `body`
   - Se valida el formulario
   - Se aplica DOM Shield (sincroniza cliente ID)
   - Se guarda payload en `sessionStorage`:
     ```javascript
     {
         cliente: <id>,
         configuracion: <id>,
         fecha_vencimiento: "YYYY-MM-DD"
     }
     ```
   - Se cierra el offcanvas actual
   - Se carga el editor vía HTMX en `#offcanvas-container`

### 17.2 Fase B: Editor Completo

1. **Editor se carga en modo borrador**
   - `CotizacionEditorDraftView` establece `is_draft=True`
   - El template muestra badge "Borrador"

2. **Editor lee sessionStorage**
   - `cotizacion_editor.js` detecta que `editor-uuid` está vacío
   - Lee `sintel_draft_cotizacion` de `sessionStorage`
   - Pobla campos ocultos: `editor-cliente-id`, `editor-configuracion-id`
   - Pobla campos visibles: `editor-fecha-vencimiento`
   - Consulta tipo desde perfil: `cotizacionesAPI.getConfiguracion()`

3. **Tablas en modo local**
   - Tablas Tabulator se inicializan con `data: []` (sin `ajaxURL`)
   - Usuario puede agregar/editar items sin conexión a BD
   - Todo queda en memoria local

4. **Usuario hace clic en "Guardar Cotización"**
   - Se recolectan items de todas las tablas (`accesorios`, `mano-obra`)
   - Se construye payload unificado:
     ```javascript
     {
         cliente: <id>,
         configuracion: <id>,
         fecha_vencimiento: "YYYY-MM-DD",
         items: [...]
     }
     ```
   - Se envía POST único a `/api/v1/cotizaciones/`
   - Backend asigna tipo automáticamente desde perfil
   - Se limpia `sessionStorage` después de guardar exitosamente
   - Se cierra el offcanvas del editor
   - Se actualiza la tabla principal de cotizaciones

---

## 18. Corrección de Error Offcanvas (v2.60.3)

### 18.1 Error: "Cannot read properties of undefined (reading 'backdrop')"

**Problema:**
- Error en `offcanvas.js:178` al intentar crear instancia de Offcanvas
- Ocurría específicamente en el flujo de "Nueva Plantilla"
- Bootstrap intentaba inicializar automáticamente el offcanvas cuando HTMX inyectaba contenido
- El elemento no estaba completamente listo o faltaban atributos necesarios

**Causa Raíz:**
- Uso de `data-bs-toggle="offcanvas"` y `data-bs-target` en botones con HTMX
- Bootstrap intentaba inicializar antes de que HTMX terminara de inyectar el contenido
- El elemento `#offcanvas-container-secundario` podía no existir o estar incompleto

**Solución Implementada:**
- **Eliminación de inicialización automática**: Removidos `data-bs-toggle` y `data-bs-target` del botón
- **Inicialización manual controlada**: Función JavaScript específica que espera a que HTMX cargue el contenido
- **Contenedor garantizado**: Agregado `#offcanvas-container-secundario` directamente en el template
- **Opciones explícitas**: Configuración explícita de `backdrop`, `keyboard`, `scroll` al crear instancia
- **Manejo seguro**: Try-catch y verificación de atributos antes de inicializar

**Archivos Modificados:**
- `offcanvas_list_plantillas.html`: 
  - Contenedor secundario agregado
  - Botón actualizado sin atributos Bootstrap automáticos
  - Función `window.abrirOffcanvasSecundario()` agregada
- `plantilla_crear.js`:
  - Manejo seguro de offcanvas con try-catch
  - Verificación de atributos antes de inicializar
  - Opciones explícitas al crear instancia

**Código de la Solución:**
```javascript
// Función específica para abrir offcanvas secundario después de carga HTMX
window.abrirOffcanvasSecundario = function() {
    const handler = function(event) {
        if (event.detail.target && event.detail.target.id === 'offcanvas-container-secundario') {
            document.body.removeEventListener('htmx:afterSwap', handler);
            
            setTimeout(() => {
                const offcanvasEl = document.getElementById('offcanvas-container-secundario');
                if (offcanvasEl && window.bootstrap) {
                    try {
                        if (!offcanvasEl.hasAttribute('tabindex')) {
                            offcanvasEl.setAttribute('tabindex', '-1');
                        }
                        
                        const instance = window.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl, {
                            backdrop: true,
                            keyboard: true,
                            scroll: false
                        });
                        instance.show();
                    } catch (error) {
                        console.error('[offcanvas_list_plantillas] Error al abrir offcanvas secundario:', error);
                    }
                }
            }, 50);
        }
    };
    
    document.body.addEventListener('htmx:afterSwap', handler);
};
```

**Alcance:**
- ✅ Solo afecta la creación de plantillas
- ✅ No modifica otras vistas ni lógica de cotizaciones
- ✅ No afecta el flujo del Wizard Pattern
- ✅ Solución aislada y específica

---

**Documento generado automáticamente - Última actualización: 2024**
