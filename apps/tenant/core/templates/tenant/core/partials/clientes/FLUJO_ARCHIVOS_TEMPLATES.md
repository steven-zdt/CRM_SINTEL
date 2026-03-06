# 📄 Flujo Completo de Archivos Templates - Módulo Clientes v2.60

## 📋 Resumen Ejecutivo

**Fecha de Documentación:** 2026-01-XX  
**Versión:** 2.60  
**Objetivo:** Documentar estructura, orden de carga, dependencias y flujo completo de los archivos templates del módulo Clientes  
**Estado:** ✅ **DOCUMENTADO**

---

## 📁 Estructura de Archivos

```
apps/tenant/core/templates/tenant/core/partials/clientes/
├── list.html              # Vista principal con tabla Tabulator
├── modals.html            # Modal de Crear/Editar Cliente
└── assets_clientes.html  # Carga de scripts JavaScript
```

---

## 🔄 Flujo de Carga e Integración

### 1. Punto de Entrada: `workspace.html`

**Ubicación:** `apps/tenant/core/templates/tenant/core/workspace.html`

**Inclusión de Templates:**

```django
{# Módulo Clientes #}
<section id="tab-clientes" class="workspace-tab" style="display: none;">
  {% include 'tenant/core/partials/clientes/list.html' %}
  {% include 'tenant/core/partials/clientes/modals.html' %}
</section>
```

**Líneas:** 85-88

**Orden de Inclusión:**
1. `list.html` se incluye primero (estructura principal)
2. `modals.html` se incluye después (modales)

**Carga de Assets:**

```django
{% block extra_js %}
  {# 1. LIBRERÍAS CORE - v2.95 #}
  {% include 'tenant/core/partials/assets_core.html' %}
  
  {# 2. NAVEGACIÓN Y ORQUESTACIÓN #}
  <script src="{% static 'core/js/workspace.js' %}"></script>
  
  {# 3. ASSETS MODULARES #}
  ...
  {% include 'tenant/core/partials/clientes/assets_clientes.html' %}
  ...
{% endblock extra_js %}
```

**Línea:** 181

**Orden de Carga de Scripts:**
1. `assets_core.html` (DOMUtils, TabulatorFactory, http(), UIManager, etc.)
2. `workspace.js` (navegación y orquestación)
3. `assets_clientes.html` (scripts específicos del módulo)

---

## 📄 Archivo 1: `list.html`

### Propósito

Vista principal del módulo de Clientes. Contiene la estructura HTML para la tabla Tabulator y los controles de búsqueda y creación.

### Estructura HTML

```html
<div class="card shadow-sm">
  <!-- Header con título y controles -->
  <div class="card-header bg-white d-flex justify-content-between align-items-center py-3">
    <h5 class="mb-0 text-secondary">
      <i class="bi bi-people me-2"></i>Directorio de Clientes
    </h5>
    <div>
      <!-- Input de búsqueda -->
      <div class="input-group input-group-sm d-inline-flex w-auto me-2">
        <input type="text" id="search-cliente" class="form-control" placeholder="Buscar cliente...">
        <button class="btn btn-outline-secondary" type="button">
          <i class="bi bi-search"></i>
        </button>
      </div>
      <!-- Botón crear nuevo cliente -->
      <button class="btn btn-primary btn-sm" onclick="ClientesModule.abrirModalCrear()">
        <i class="bi bi-plus-lg me-1"></i>Nuevo
      </button>
    </div>
  </div>
  
  <!-- Contenedor de la tabla Tabulator -->
  <div class="card-body p-0">
    <div id="grid-clientes"></div>
  </div>
</div>
```

### Elementos Críticos

| ID/Selector | Tipo | Propósito | Referencia JS |
|-------------|------|-----------|---------------|
| `#search-cliente` | `<input>` | Input de búsqueda con debounce | `clientes.page.js` línea 121 |
| `#grid-clientes` | `<div>` | Contenedor de tabla Tabulator | `clientes.page.js` línea 109 |
| `ClientesModule.abrirModalCrear()` | `onclick` | Abre modal para crear cliente | `clientes.page.js` línea 476 |

### Integración con JavaScript

**Inicialización de Tabulator:**

```javascript
// clientes.page.js - líneas 101-116
function initTabulator() {
    table = w.TabulatorFactory.create(
        '#grid-clientes',              // ← Selector del contenedor
        '/api/v1/clientes/',           // URL base de la API
        getColumns(),                  // Columnas personalizadas
        {
            searchInputSelector: '#search-cliente'  // ← Input de búsqueda
        }
    );
}
```

**Búsqueda con Debounce:**

```javascript
// clientes.page.js - líneas 121-133
const searchInput = d.querySelector('#search-cliente');
if (searchInput && table) {
    let timeout = null;
    searchInput.addEventListener('keyup', function(e) {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            if (table) {
                table.setPage(1);
                table.replaceData();
            }
        }, 300);
    });
}
```

### Notas Importantes

- ⚠️ **v2.40**: El comentario en la línea 18 indica que `modals.html` se incluye en `workspace.html`, no aquí, para evitar duplicación.
- El contenedor `#grid-clientes` debe estar vacío inicialmente; Tabulator lo poblará dinámicamente.
- El botón "Nuevo" usa `onclick` directo para mantener compatibilidad con lazy loading.

---

## 📄 Archivo 2: `modals.html`

### Propósito

Contiene el modal Bootstrap para crear y editar clientes. Incluye el formulario completo con todos los campos del modelo Cliente.

### Estructura HTML

```html
{% load static %}
<!-- Modal: Crear/Editar Cliente -->
<div class="modal fade" id="modal-cliente" tabindex="-1" aria-labelledby="modal-cliente-label" aria-hidden="true">
  <div class="modal-dialog modal-lg">
    <div class="modal-content">
      <!-- Header del Modal -->
      <div class="modal-header">
        <h5 class="modal-title" id="modal-cliente-label">Cliente</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
      </div>
      
      <!-- Body del Modal -->
      <div class="modal-body">
        <!-- Contenedor de errores (Error Boundary Pattern) -->
        <div id="form-cliente-feedback" class="alert alert-danger d-none mb-3" role="alert"></div>
        <div id="cliente-feedback" class="alert d-none" role="alert" aria-live="polite"></div>
        
        <!-- Formulario -->
        <form id="form-cliente" method="POST" onsubmit="return false;">
          <input type="hidden" id="cliente-id" name="id">
          
          <!-- Campos del formulario -->
          <div class="row">
            <!-- Tipo Persona -->
            <div class="col-md-6 mb-3">
              <label for="cliente-tipo_persona" class="form-label">Tipo Persona *</label>
              <select class="form-select" id="cliente-tipo_persona" name="tipo_persona" required>
                <option value="">Seleccionar...</option>
                <option value="NATURAL">Persona natural</option>
                <option value="JURIDICA">Persona jurídica</option>
              </select>
            </div>
            
            <!-- ... resto de campos ... -->
          </div>
        </form>
      </div>
      
      <!-- Footer del Modal -->
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
        <button type="submit" form="form-cliente" class="btn btn-primary" id="btn-guardar-cliente">Guardar</button>
      </div>
    </div>
  </div>
</div>
```

### Elementos Críticos

| ID/Selector | Tipo | Propósito | Referencia JS |
|-------------|------|-----------|---------------|
| `#modal-cliente` | `<div>` | Contenedor del modal Bootstrap | `clientes.page.js` línea 214, 391, 502 |
| `#modal-cliente-label` | `<h5>` | Título del modal (cambia dinámicamente) | `clientes.page.js` línea 387, 485 |
| `#form-cliente-feedback` | `<div>` | Contenedor de errores (Error Boundary) | `clientes.page.js` línea 255, 494 |
| `#form-cliente` | `<form>` | Formulario principal | `clientes.page.js` línea 136, 194, 369 |
| `#cliente-id` | `<input type="hidden">` | ID del cliente (para edición) | `clientes.page.js` línea 213, 371 |
| `#btn-guardar-cliente` | `<button>` | Botón de guardar | `clientes.page.js` línea 149, 217 |

### Campos del Formulario

#### Campos Obligatorios (required)

| Campo | ID | Tipo | Valores Posibles |
|-------|-----|------|------------------|
| Tipo Persona | `#cliente-tipo_persona` | `<select>` | `NATURAL`, `JURIDICA` |
| Tipo Documento | `#cliente-tipo_documento` | `<select>` | `CC`, `CE`, `NIT`, `PA` |
| Número Documento | `#cliente-numero_documento` | `<input type="text">` | Texto libre |
| Razón Social | `#cliente-razon_social` | `<input type="text">` | Texto libre |
| Régimen Tributario | `#cliente-regimen_tributario` | `<select>` | `SIMPLE`, `ORDINARIO`, `NO_RESP` |

#### Campos Opcionales

| Campo | ID | Tipo | Valor por Defecto |
|-------|-----|------|-------------------|
| Nombre Comercial | `#cliente-nombre_comercial` | `<input type="text">` | Vacío |
| Email | `#cliente-email` | `<input type="email">` | Vacío |
| Teléfono | `#cliente-telefono` | `<input type="text">` | Vacío |
| Dirección | `#cliente-direccion` | `<input type="text">` | Vacío |
| Ciudad | `#cliente-ciudad` | `<input type="text">` | Vacío |
| Activo | `#cliente-activo` | `<input type="checkbox">` | `checked` (true) |
| Observaciones | `#cliente-observaciones` | `<textarea>` | Vacío |

### Integración con JavaScript

**Abrir Modal (Crear):**

```javascript
// clientes.page.js - líneas 476-519
function abrirModalCrear() {
    const form = d.querySelector('#form-cliente');
    if (form) {
        form.reset();
        d.querySelector('#cliente-id').value = '';
        d.querySelector('#cliente-activo').checked = true;
    }
    
    d.querySelector('#modal-cliente-label').textContent = 'Nuevo Cliente';
    
    // Ocultar feedback
    const errorContainer = d.querySelector('#form-cliente-feedback');
    if (errorContainer) {
        errorContainer.classList.add('d-none');
        errorContainer.textContent = '';
    }
    
    // Abrir modal
    const modalEl = d.querySelector('#modal-cliente');
    if (modalEl) {
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
    }
}
```

**Abrir Modal (Editar):**

```javascript
// clientes.page.js - líneas 352-408
async function editar(id) {
    const res = await w.clientesAPI.get(id);
    
    if (!res.ok || !res.data) {
        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
            w.UIManager.handleError(res, '[clientes.page]');
        }
        return;
    }
    
    const data = res.data;
    
    // Llenar formulario
    const form = d.querySelector('#form-cliente');
    if (form) {
        d.querySelector('#cliente-id').value = data.id || '';
        d.querySelector('#cliente-tipo_persona').value = data.tipo_persona || '';
        d.querySelector('#cliente-tipo_documento').value = data.tipo_documento || '';
        d.querySelector('#cliente-numero_documento').value = data.numero_documento || '';
        d.querySelector('#cliente-razon_social').value = data.razon_social || '';
        // ... resto de campos ...
        d.querySelector('#cliente-activo').checked = data.activo !== false;
    }
    
    d.querySelector('#modal-cliente-label').textContent = 'Editar Cliente';
    
    const modalEl = d.querySelector('#modal-cliente');
    if (modalEl) {
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
    }
}
```

**Guardar Cliente:**

```javascript
// clientes.page.js - líneas 193-346
async function guardarCliente() {
    const form = d.querySelector('#form-cliente');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    // Convertir checkbox activo
    data.activo = d.querySelector('#cliente-activo').checked;
    
    // Remover campos vacíos
    Object.keys(data).forEach(key => {
        if (data[key] === '' || data[key] === null) {
            delete data[key];
        }
    });
    
    const id = d.querySelector('#cliente-id').value;
    
    // Mostrar loading
    const btnGuardar = d.querySelector('#btn-guardar-cliente');
    if (btnGuardar) {
        btnGuardar.disabled = true;
        btnGuardar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
    }
    
    // Llamada a API
    let res;
    if (id) {
        res = await w.clientesAPI.update(id, data);
    } else {
        res = await w.clientesAPI.create(data);
    }
    
    // Restaurar botón
    if (btnGuardar) {
        btnGuardar.disabled = false;
        btnGuardar.innerHTML = btnOriginalText;
    }
    
    // Manejo de errores
    if (!res.ok) {
        if (res.status === 400) {
            // Errores de validación: mantener modal abierto
            if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                w.UIManager.handleError(res, '[clientes.page]', {
                    modalSelector: '#modal-cliente',
                    errorContainerSelector: '#form-cliente-feedback'
                });
            }
            return;
        }
        // Otros errores
        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
            w.UIManager.handleError(res, '[clientes.page]');
        }
        return;
    }
    
    // Éxito: cerrar modal, notificar, recargar tabla
    if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
        w.UIManager.handleModal('#modal-cliente', 'hide');
    }
    
    if (w.SintelFeedback) {
        w.SintelFeedback.success(id ? 'Cliente actualizado exitosamente' : 'Cliente creado exitosamente');
    }
    
    // Recargar tabla
    if (table) {
        table.setPage(1).then(() => {
            table.replaceData();
        });
    }
}
```

### Error Boundary Pattern

**Contenedor de Errores:**

```html
<!-- modals.html - línea 16 -->
<div id="form-cliente-feedback" class="alert alert-danger d-none mb-3" role="alert"></div>
```

**Uso en JavaScript:**

```javascript
// clientes.page.js - líneas 255-304
if (res.status === 400) {
    const errorContainer = modalEl?.querySelector('#form-cliente-feedback');
    
    if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, '[clientes.page]', {
            modalSelector: '#modal-cliente',
            errorContainerSelector: '#form-cliente-feedback'
        });
    }
    return;  // ⚠️ CRÍTICO: No cerrar modal
}
```

### Notas Importantes

- ⚠️ **v2.60**: El contenedor `#form-cliente-feedback` es parte del Error Boundary Pattern.
- El formulario tiene `onsubmit="return false;"` para prevenir envío tradicional.
- El botón de guardar usa `form="form-cliente"` para asociarlo al formulario.
- El modal usa `bootstrap.Modal.getOrCreateInstance()` para evitar conflictos de aria-hidden.

---

## 📄 Archivo 3: `assets_clientes.html`

### Propósito

Carga los scripts JavaScript específicos del módulo de Clientes en el orden correcto.

### Estructura HTML

```django
{% load static %}
{# Assets del módulo Clientes v2.60 - Tabulator Implementation #}
{# ⚠️ v2.60: Aislamiento Gradual - API Wrapper + Error Boundary Pattern #}
{# ⚠️ CRÍTICO: Cargar Factory ANTES del módulo específico #}
{# ⚠️ ORDEN CRÍTICO: Los scripts DEBEN cargarse en este orden exacto (sin async/defer) #}
{# 1. assets_core.html (incluye DOMUtils, TabulatorFactory, http(), UIManager, etc.) - ya cargado en workspace.html #}
{# 2. clientes.api.js (define window.clientesAPI) - REQUERIDO por clientes.page.js #}
{# 3. clientes.page.js (depende de clientesAPI, TabulatorFactory, UIManager) - DEBE cargarse ÚLTIMO #}

{# BLOQUE 1: API Wrapper - DEBE cargarse PRIMERO (requerido por page.js) #}
<script src="{% static 'core/js/clientes/clientes.api.js' %}"></script>

{# BLOQUE 2: Page Script - DEBE cargarse DESPUÉS de api.js #}
<script src="{% static 'core/js/clientes/clientes.page.js' %}"></script>
```

### Orden de Carga

```
1. assets_core.html (cargado en workspace.html antes)
   ├── DOMUtils
   ├── TabulatorFactory
   ├── http()
   ├── UIManager
   └── SintelFeedback

2. clientes.api.js
   └── window.clientesAPI

3. clientes.page.js
   ├── Depende de: clientesAPI
   ├── Depende de: TabulatorFactory
   ├── Depende de: UIManager
   └── Expone: window.ClientesModule
```

### Dependencias

**clientes.api.js requiere:**
- `w.http()` (de `lib/api.js`)

**clientes.page.js requiere:**
- `w.Tabulator` (de `tabulator.min.js`)
- `w.TabulatorFactory` (de `tabulator.factory.js`)
- `w.clientesAPI` (de `clientes.api.js`)
- `w.UIManager` (de `ui-manager.js`)
- `w.SintelFeedback` (de `sintel-feedback.js`)
- `w.DOMUtils` (opcional, de `dom-utils.js`)

### Notas Importantes

- ⚠️ **CRÍTICO**: Los scripts NO deben usar `async` o `defer` para mantener el orden de ejecución.
- `clientes.api.js` DEBE cargarse antes de `clientes.page.js`.
- `assets_core.html` DEBE estar cargado antes que `assets_clientes.html`.

---

## 🔄 Flujo Completo de Renderizado

### 1. Carga Inicial de la Página

```
1. Usuario accede a /workspace/
   ↓
2. Django renderiza workspace.html
   ↓
3. Se incluyen templates:
   - list.html (línea 86)
   - modals.html (línea 87)
   ↓
4. HTML se renderiza en el navegador
   - #tab-clientes está oculto (display: none)
   - #grid-clientes está vacío
   - #modal-cliente está en el DOM pero oculto
```

### 2. Carga de Scripts

```
1. assets_core.html se carga (en workspace.html)
   ↓
2. workspace.js se carga
   ↓
3. assets_clientes.html se carga (línea 181)
   ├── clientes.api.js se carga
   │   └── window.clientesAPI se define
   └── clientes.page.js se carga
       └── window.ClientesModule se define
```

### 3. Inicialización Lazy Loading

```
1. Usuario hace clic en tab "Clientes"
   ↓
2. workspace.js muestra #tab-clientes
   ↓
3. clientes.page.js detecta visibilidad
   ├── DOMUtils.onVisibleOnce('#tab-clientes', tryInit)
   └── O evento 'shown.bs.tab'
   ↓
4. tryInit() se ejecuta
   ├── Verifica que #grid-clientes existe
   ├── Verifica dependencias (Tabulator, TabulatorFactory, clientesAPI)
   └── Llama a init()
   ↓
5. init() se ejecuta
   ├── initTabulator() → Crea tabla Tabulator
   └── initEvents() → Configura eventos
```

### 4. Operación: Crear Cliente

```
1. Usuario hace clic en "Nuevo"
   ↓
2. onclick="ClientesModule.abrirModalCrear()"
   ↓
3. abrirModalCrear() se ejecuta
   ├── Resetea formulario
   ├── Limpia #cliente-id
   ├── Cambia título a "Nuevo Cliente"
   ├── Oculta #form-cliente-feedback
   └── Abre modal con bootstrap.Modal.getOrCreateInstance()
   ↓
4. Usuario completa formulario
   ↓
5. Usuario hace clic en "Guardar"
   ↓
6. Event listener intercepta submit
   ├── e.preventDefault()
   └── Llama a guardarCliente()
   ↓
7. guardarCliente() se ejecuta
   ├── Extrae datos del formulario
   ├── Muestra loading en botón
   ├── Llama a w.clientesAPI.create(data)
   ├── Backend procesa y responde
   └── Maneja respuesta:
       ├── Éxito: Cierra modal, notifica, recarga tabla
       └── Error 400: Mantiene modal abierto, muestra errores
```

### 5. Operación: Editar Cliente

```
1. Usuario hace clic en botón "Editar" en la tabla
   ↓
2. Event delegation captura click
   ├── Detecta .btn-edit
   ├── Extrae data-id
   └── Llama a ClientesModule.editar(id)
   ↓
3. editar(id) se ejecuta
   ├── Llama a w.clientesAPI.get(id)
   ├── Backend responde con datos
   ├── Llena formulario con datos
   ├── Cambia título a "Editar Cliente"
   └── Abre modal
   ↓
4. Usuario modifica datos
   ↓
5. Usuario guarda
   ↓
6. guardarCliente() detecta #cliente-id con valor
   └── Llama a w.clientesAPI.update(id, data)
```

### 6. Operación: Eliminar Cliente

```
1. Usuario hace clic en botón "Eliminar" en la tabla
   ↓
2. Event delegation captura click
   ├── Detecta .btn-delete
   ├── Valida que no esté disabled
   ├── Extrae data-id
   └── Llama a ClientesModule.eliminar(id)
   ↓
3. eliminar(id) se ejecuta
   ├── Llama a w.clientesAPI.get(id) para validar estado
   ├── Valida que activo === false
   ├── Muestra confirmación
   ├── Llama a w.clientesAPI.delete(id)
   └── Recarga tabla
```

---

## 🎯 IDs y Selectores Críticos

### Vista Principal (list.html)

| Selector | Propósito | Uso en JS |
|----------|-----------|-----------|
| `#search-cliente` | Input de búsqueda | `clientes.page.js:121` |
| `#grid-clientes` | Contenedor de tabla Tabulator | `clientes.page.js:109` |

### Modal (modals.html)

| Selector | Propósito | Uso en JS |
|----------|-----------|-----------|
| `#modal-cliente` | Contenedor del modal | `clientes.page.js:214,391,502` |
| `#modal-cliente-label` | Título del modal | `clientes.page.js:387,485` |
| `#form-cliente-feedback` | Contenedor de errores | `clientes.page.js:255,494` |
| `#form-cliente` | Formulario principal | `clientes.page.js:136,194,369` |
| `#cliente-id` | ID oculto del cliente | `clientes.page.js:213,371` |
| `#btn-guardar-cliente` | Botón de guardar | `clientes.page.js:149,217` |

### Campos del Formulario

| Selector | Campo | Tipo |
|----------|-------|------|
| `#cliente-tipo_persona` | Tipo Persona | `<select>` |
| `#cliente-tipo_documento` | Tipo Documento | `<select>` |
| `#cliente-numero_documento` | Número Documento | `<input>` |
| `#cliente-razon_social` | Razón Social | `<input>` |
| `#cliente-nombre_comercial` | Nombre Comercial | `<input>` |
| `#cliente-regimen_tributario` | Régimen Tributario | `<select>` |
| `#cliente-email` | Email | `<input type="email">` |
| `#cliente-telefono` | Teléfono | `<input>` |
| `#cliente-direccion` | Dirección | `<input>` |
| `#cliente-ciudad` | Ciudad | `<input>` |
| `#cliente-activo` | Activo | `<input type="checkbox">` |
| `#cliente-observaciones` | Observaciones | `<textarea>` |

---

## 🔗 Integración con Workspace

### Tab de Navegación

```html
<!-- workspace.html - línea 46 -->
<li class="nav-item">
  <a href="#clientes" data-tab="clientes" class="nav-link">
    <i class="bi bi-person-badge me-2"></i>Clientes
  </a>
</li>
```

### Sección de Contenido

```html
<!-- workspace.html - líneas 85-88 -->
<section id="tab-clientes" class="workspace-tab" style="display: none;">
  {% include 'tenant/core/partials/clientes/list.html' %}
  {% include 'tenant/core/partials/clientes/modals.html' %}
</section>
```

### Carga de Assets

```html
<!-- workspace.html - línea 181 -->
{% include 'tenant/core/partials/clientes/assets_clientes.html' %}
```

---

## 🛡️ Validaciones y Reglas

### Validación HTML5

- Campos marcados con `required` se validan automáticamente antes del submit.
- `#cliente-email` usa `type="email"` para validación de formato.

### Validación en JavaScript

- `guardarCliente()` remueve campos vacíos antes de enviar.
- `eliminar()` valida que el cliente no esté activo antes de eliminar.

### Validación en Backend

- DRF Serializer valida todos los campos antes de guardar.
- Errores 400 se muestran en `#form-cliente-feedback` sin cerrar el modal.

---

## 📊 Mapeo de Campos Modelo → HTML

| Campo Modelo | ID HTML | Tipo HTML | Requerido |
|--------------|---------|-----------|-----------|
| `tipo_persona` | `#cliente-tipo_persona` | `<select>` | ✅ |
| `tipo_documento` | `#cliente-tipo_documento` | `<select>` | ✅ |
| `numero_documento` | `#cliente-numero_documento` | `<input>` | ✅ |
| `razon_social` | `#cliente-razon_social` | `<input>` | ✅ |
| `nombre_comercial` | `#cliente-nombre_comercial` | `<input>` | ❌ |
| `regimen_tributario` | `#cliente-regimen_tributario` | `<select>` | ✅ |
| `email` | `#cliente-email` | `<input type="email">` | ❌ |
| `telefono` | `#cliente-telefono` | `<input>` | ❌ |
| `direccion` | `#cliente-direccion` | `<input>` | ❌ |
| `ciudad` | `#cliente-ciudad` | `<input>` | ❌ |
| `activo` | `#cliente-activo` | `<input type="checkbox">` | ❌ (default: true) |
| `observaciones` | `#cliente-observaciones` | `<textarea>` | ❌ |

---

## ✅ Checklist de Validación

### Estructura HTML

- [ ] `list.html` incluye `#grid-clientes` vacío
- [ ] `list.html` incluye `#search-cliente` para búsqueda
- [ ] `list.html` incluye botón "Nuevo" con `onclick` correcto
- [ ] `modals.html` incluye `#modal-cliente` con estructura Bootstrap
- [ ] `modals.html` incluye `#form-cliente-feedback` para errores
- [ ] `modals.html` incluye todos los campos del modelo
- [ ] Campos requeridos tienen atributo `required`
- [ ] `assets_clientes.html` carga scripts en orden correcto

### Integración JavaScript

- [ ] `#grid-clientes` se inicializa con TabulatorFactory
- [ ] `#search-cliente` tiene listener con debounce
- [ ] `#form-cliente` tiene listener de submit
- [ ] `#btn-guardar-cliente` tiene listener de click
- [ ] Botones de acciones en tabla usan event delegation
- [ ] Modal se abre con `bootstrap.Modal.getOrCreateInstance()`

### Funcionalidad

- [ ] Crear cliente funciona correctamente
- [ ] Editar cliente llena formulario correctamente
- [ ] Eliminar cliente valida estado activo
- [ ] Búsqueda funciona con debounce
- [ ] Errores 400 se muestran en modal sin cerrarlo
- [ ] Tabla se recarga después de operaciones CRUD

---

## 📚 Referencias

### Archivos Relacionados

- `apps/tenant/core/templates/tenant/core/workspace.html` - Punto de entrada
- `apps/tenant/core/static/core/js/clientes/clientes.api.js` - Capa de Datos
- `apps/tenant/core/static/core/js/clientes/clientes.page.js` - Capa de Presentación
- `apps/tenant/core/static/core/js/clientes/AUDITORIA_FLUJO.md` - Documentación técnica

### Documentación Externa

- Bootstrap 5 Modals: https://getbootstrap.com/docs/5.0/components/modal/
- Tabulator Documentation: https://tabulator.info/
- Django Templates: https://docs.djangoproject.com/en/stable/topics/templates/

---

## 🔄 Historial de Cambios

### v2.60 (2026-01-XX)

- ✅ Error Boundary Pattern implementado (`#form-cliente-feedback`)
- ✅ Mejoras en manejo de modales Bootstrap
- ✅ Documentación completa de flujo de archivos

### v2.40 (2024-XX-XX)

- ✅ Separación de templates (list.html, modals.html, assets_clientes.html)
- ✅ API-First Architecture
- ✅ Integración con Tabulator Factory

---

**Fin del Documento**
