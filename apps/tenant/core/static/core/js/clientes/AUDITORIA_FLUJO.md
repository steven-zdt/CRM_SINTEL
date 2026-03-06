# 🔍 Auditoría de Flujo - Módulo Clientes v2.60

## 📋 Resumen Ejecutivo

**Fecha de Auditoría:** 2026-01-XX  
**Última Actualización:** 2026-01-XX  
**Versión:** 2.60  
**Objetivo:** Documentar flujo completo, arquitectura, dependencias y patrones del módulo de Clientes  
**Estado:** ✅ **DOCUMENTADO Y VALIDADO**

---

## 📁 Estructura de Archivos

### Frontend (JavaScript)

```
apps/tenant/core/static/core/js/clientes/
├── clientes.api.js          # Capa de Datos - Wrapper de API (Aislamiento Gradual)
└── clientes.page.js         # Capa de Presentación - Lógica de UI y Tabulator
```

### Templates (HTML)

```
apps/tenant/core/templates/tenant/core/partials/clientes/
├── list.html                # Vista principal con tabla Tabulator
├── modals.html              # Modal de Crear/Editar Cliente
└── assets_clientes.html      # Carga de scripts y estilos
```

### Backend (Django/DRF)

```
apps/tenant/clientes/
├── api/
│   ├── viewsets.py          # ClienteViewSet (CRUD completo)
│   ├── serializers.py       # ClienteListSerializer, ClienteDetailSerializer
│   └── urls.py              # Router DRF
├── models.py                # Modelo Cliente
└── services.py              # Servicios de negocio (qs_list, crear_cliente, etc.)
```

---

## 🏗️ Arquitectura

### Principios de Diseño

1. **API-First**: Frontend consume exclusivamente endpoints RESTful DRF
2. **Aislamiento Gradual v2.60**: Separación clara entre Capa de Datos y Capa de Presentación
3. **Tabulator Factory v2.40**: Uso de `TabulatorFactory` para evitar código repetido
4. **Error Boundary Pattern**: Manejo centralizado de errores mediante `UIManager`
5. **SSoT (Single Source of Truth)**: Empresa se inyecta automáticamente desde el tenant

### Capas de la Aplicación

```
┌─────────────────────────────────────────────────────────┐
│  CAPA DE PRESENTACIÓN (clientes.page.js)                │
│  - Inicialización de Tabulator                          │
│  - Eventos y listeners                                  │
│  - Validaciones de UI                                   │
│  - Manejo de modales                                    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  CAPA DE DATOS (clientes.api.js)                        │
│  - Wrapper de API (w.clientesAPI)                       │
│  - Retorna siempre {ok, status, data}                  │
│  - Sin lógica de negocio                                │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  BACKEND (Django REST Framework)                        │
│  - ClienteViewSet (CRUD)                                │
│  - Serializers (List/Detail)                           │
│  - Services (Lógica de negocio)                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔄 Flujo de Inicialización

### 1. Carga de Dependencias

**Orden de carga (en `assets_clientes.html` o similar):**

```html
1. lib/api.js              → w.http() (función base para llamadas HTTP)
2. ui-manager.js           → w.UIManager (Error Boundary)
3. tabulator.factory.js    → w.TabulatorFactory (The Engine)
4. clientes.api.js         → w.clientesAPI (Capa de Datos)
5. clientes.page.js        → w.ClientesModule (Capa de Presentación)
```

### 2. Inicialización Lazy Loading

**Archivo:** `clientes.page.js` (líneas 544-577)

```javascript
// ⚠️ v2.40: Inicializar solo cuando el contenedor sea visible
let initialized = false;

function tryInit() {
    if (initialized) return;
    const hasGrid = d.querySelector('#grid-clientes');
    if (hasGrid) {
        init();
        initialized = true;
    }
}

// Usar DOMUtils.onVisibleOnce si está disponible
if (w.DOMUtils && w.DOMUtils.onVisibleOnce) {
    w.DOMUtils.onVisibleOnce('#tab-clientes', tryInit);
    w.DOMUtils.onVisibleOnce('#clientes', tryInit);
}

// Fallback: inicializar en DOMContentLoaded
if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', tryInit);
} else {
    tryInit();
}

// Escuchar eventos de tabs de Bootstrap
d.addEventListener('shown.bs.tab', function(e) {
    if (e.target && (e.target.getAttribute('data-tab') === 'clientes' || 
                     e.target.getAttribute('href') === '#clientes' ||
                     e.target.getAttribute('data-bs-target') === '#clientes')) {
        tryInit();
    }
});
```

### 3. Función `init()`

**Archivo:** `clientes.page.js` (líneas 522-541)

```javascript
function init() {
    // Validar dependencias
    if (!w.Tabulator) {
        console.error('[clientes.page] Tabulator no está disponible');
        return;
    }
    
    if (!w.TabulatorFactory) {
        console.error('[clientes.page] TabulatorFactory no está disponible');
        return;
    }
    
    if (!w.clientesAPI) {
        console.error('[clientes.page] ❌ CRÍTICO: window.clientesAPI no está disponible.');
        return;
    }
    
    // Inicializar componentes
    initTabulator();  // Crear tabla Tabulator
    initEvents();     // Configurar eventos
}
```

---

## 📊 Flujo de Operaciones CRUD

### CREATE (Crear Cliente)

**Flujo completo:**

1. **Usuario hace clic en "Nuevo"** → `ClientesModule.abrirModalCrear()`
2. **Modal se abre** → Formulario se resetea, título cambia a "Nuevo Cliente"
3. **Usuario completa formulario** → Campos validados por HTML5 (`required`)
4. **Usuario hace clic en "Guardar"** → `guardarCliente()` se ejecuta
5. **Validación de datos** → FormData se convierte a objeto JavaScript
6. **Llamada a API** → `w.clientesAPI.create(data)`
7. **Backend procesa** → `ClienteViewSet.create()` → `crear_cliente()` service
8. **Respuesta** → `{ok: true/false, status: 200/400, data: {...}}`
9. **Manejo de respuesta:**
   - ✅ **Éxito (200)**: Modal se cierra, notificación de éxito, tabla se recarga
   - ❌ **Error 400 (Validación)**: Modal permanece abierto, errores se muestran en `#form-cliente-feedback`
   - ❌ **Error 500/403**: Modal se cierra, notificación de error

**Código relevante:**

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
    
    // Manejo de errores (Error Boundary Pattern)
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

### READ (Listar Clientes)

**Flujo completo:**

1. **Página se carga** → `initTabulator()` se ejecuta
2. **Tabulator se inicializa** → `TabulatorFactory.create()` configura tabla
3. **Primera carga** → Tabulator hace GET `/api/v1/clientes/?page=1&page_size=10`
4. **Backend procesa** → `ClienteViewSet.list()` → `qs_list()` service
5. **Respuesta paginada** → `{count: N, next: "...", previous: null, results: [...]}`
6. **Tabulator renderiza** → Columnas se muestran según `getColumns()`

**Búsqueda con debounce:**

```javascript
// clientes.page.js - líneas 121-133
const searchInput = d.querySelector('#search-cliente');
if (searchInput && table) {
    let timeout = null;
    searchInput.addEventListener('keyup', function(e) {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            if (table) {
                table.setPage(1);      // Resetear a primera página
                table.replaceData();   // Recargar datos (Server-Side)
            }
        }, 300);  // Debounce de 300ms
    });
}
```

**Configuración de Tabulator:**

```javascript
// clientes.page.js - líneas 101-116
function initTabulator() {
    table = w.TabulatorFactory.create(
        '#grid-clientes',              // Selector del contenedor
        '/api/v1/clientes/',           // URL base de la API
        getColumns(),                  // Columnas personalizadas
        {
            searchInputSelector: '#search-cliente'  // Input de búsqueda
        }
    );
}
```

### UPDATE (Editar Cliente)

**Flujo completo:**

1. **Usuario hace clic en botón "Editar"** → `ClientesModule.editar(id)`
2. **Llamada a API** → `w.clientesAPI.get(id)`
3. **Backend procesa** → `ClienteViewSet.retrieve()` → `qs_detail()` service
4. **Respuesta** → `{ok: true, status: 200, data: {...}}`
5. **Formulario se llena** → Campos se poblan con datos del cliente
6. **Modal se abre** → Título cambia a "Editar Cliente"
7. **Usuario modifica datos** → Validación HTML5
8. **Usuario guarda** → `guardarCliente()` detecta `id` y llama `w.clientesAPI.update(id, data)`

**Código relevante:**

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
        // ... resto de campos
        d.querySelector('#cliente-activo').checked = data.activo !== false;
    }
    
    // Actualizar título del modal
    d.querySelector('#modal-cliente-label').textContent = 'Editar Cliente';
    
    // Abrir modal usando Bootstrap Modal API
    const modalEl = d.querySelector('#modal-cliente');
    if (modalEl) {
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
    }
}
```

### DELETE (Eliminar Cliente)

**Flujo completo:**

1. **Usuario hace clic en botón "Eliminar"** → `ClientesModule.eliminar(id)`
2. **Validación de seguridad** → Se verifica que el cliente NO esté activo
3. **Confirmación** → `confirm()` pregunta al usuario
4. **Llamada a API** → `w.clientesAPI.delete(id)`
5. **Backend procesa** → `ClienteViewSet.destroy()` → Elimina registro
6. **Respuesta** → `{ok: true, status: 204, data: null}`
7. **Notificación de éxito** → `SintelFeedback.success()`
8. **Tabla se recarga** → `table.replaceData()`

**Código relevante:**

```javascript
// clientes.page.js - líneas 414-473
async function eliminar(id) {
    // ⚠️ REGLA DE SEGURIDAD: Validar estado activo antes de proceder
    const resGet = await w.clientesAPI.get(id);
    
    if (!resGet.ok || !resGet.data) {
        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
            w.UIManager.handleError(resGet, '[clientes.page]');
        }
        return;
    }
    
    const data = resGet.data;
    
    // Validar que el cliente no esté activo
    if (data.activo) {
        if (w.SintelFeedback) {
            w.SintelFeedback.error('El ítem está activo. Desactívelo primero.');
        }
        return;
    }
    
    // Confirmar eliminación
    const confirmar = confirm('¿Está seguro de que desea eliminar este cliente? Esta acción es irreversible.');
    if (!confirmar) {
        return;
    }
    
    // Llamada a API
    const res = await w.clientesAPI.delete(id);
    
    if (!res.ok) {
        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
            w.UIManager.handleError(res, '[clientes.page]');
        }
        return;
    }
    
    // Éxito
    if (w.SintelFeedback) {
        w.SintelFeedback.success('Cliente eliminado exitosamente');
    }
    
    // Recargar tabla
    if (table) {
        table.setPage(1).then(() => {
            table.replaceData();
        });
    }
}
```

---

## 🔌 Endpoints de API

### Base URL

```
/api/v1/clientes/
```

### Endpoints Disponibles

| Método | Endpoint | Descripción | Parámetros |
|--------|----------|-------------|------------|
| `GET` | `/api/v1/clientes/` | Lista paginada de clientes | `?page=1&page_size=10&search=...` |
| `GET` | `/api/v1/clientes/{id}/` | Detalle de un cliente | `{id}` (path parameter) |
| `POST` | `/api/v1/clientes/` | Crear nuevo cliente | Body: JSON con datos del cliente |
| `PATCH` | `/api/v1/clientes/{id}/` | Actualizar cliente parcialmente | `{id}` + Body: JSON |
| `PUT` | `/api/v1/clientes/{id}/` | Actualizar cliente completamente | `{id}` + Body: JSON |
| `DELETE` | `/api/v1/clientes/{id}/` | Eliminar cliente | `{id}` (path parameter) |

### Formato de Respuesta

**Lista (GET /api/v1/clientes/):**

```json
{
  "count": 150,
  "next": "http://example.com/api/v1/clientes/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "tipo_persona": "JURIDICA",
      "tipo_documento": "NIT",
      "numero_documento": "900123456-1",
      "razon_social": "Empresa Ejemplo S.A.S.",
      "email": "contacto@ejemplo.com",
      "telefono": "+57 300 123 4567",
      "activo": true
    }
  ]
}
```

**Detalle (GET /api/v1/clientes/{id}/):**

```json
{
  "id": 1,
  "tipo_persona": "JURIDICA",
  "tipo_documento": "NIT",
  "numero_documento": "900123456-1",
  "razon_social": "Empresa Ejemplo S.A.S.",
  "nombre_comercial": "Ejemplo",
  "regimen_tributario": "ORDINARIO",
  "email": "contacto@ejemplo.com",
  "telefono": "+57 300 123 4567",
  "direccion": "Calle 123 #45-67",
  "ciudad": "Bogotá",
  "activo": true,
  "observaciones": "Cliente preferencial"
}
```

---

## 🎨 Columnas de Tabulator

**Archivo:** `clientes.page.js` (líneas 30-98)

```javascript
function getColumns() {
    return [
        {
            title: "ID",
            field: "id",
            width: 60,
            headerSort: false
        },
        {
            title: "Documento",
            field: "numero_documento",
            formatter: function(cell) {
                const data = cell.getRow().getData();
                const badge = data.tipo_documento_display 
                    ? `<span class="badge bg-secondary me-1">${data.tipo_documento_display}</span>` 
                    : '';
                return `${badge}${data.numero_documento || '-'}`;
            }
        },
        {
            title: "Razón Social",
            field: "razon_social",
            headerFilter: "input",
            headerFilterPlaceholder: "Buscar..."
        },
        {
            title: "Email",
            field: "email",
            formatter: w.TabulatorFactory.formatters.valueOrFallback
        },
        {
            title: "Teléfono",
            field: "telefono",
            formatter: w.TabulatorFactory.formatters.valueOrFallback
        },
        {
            title: "Estado",
            field: "activo",
            formatter: w.TabulatorFactory.formatters.statusBadge,
            headerSort: false
        },
        {
            title: "Acciones",
            formatter: function(cell) {
                const rowData = cell.getRow().getData();
                const id = rowData.id;
                const isActive = rowData.activo === true;
                
                const deleteDisabled = isActive ? 'disabled' : '';
                const deleteClass = isActive ? 'opacity-50' : '';
                
                return `
                    <div class="btn-group btn-group-sm" role="group">
                        <button type="button" class="btn btn-outline-primary btn-edit" data-id="${id}" title="Editar Cliente">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button type="button" class="btn btn-outline-danger btn-delete ${deleteClass}" data-id="${id}" ${deleteDisabled} title="${isActive ? 'Desactive primero para eliminar' : 'Eliminar Cliente'}">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                `;
            },
            headerSort: false,
            hozAlign: "center",
            width: 120
        }
    ];
}
```

---

## 🛡️ Manejo de Errores (Error Boundary Pattern)

### Principios

1. **Aislamiento Gradual v2.60**: Sin bloques `try/catch` en funciones principales
2. **UIManager.handleError()**: Manejo centralizado de errores
3. **Diferencia entre errores 400 y otros**: Errores 400 mantienen modal abierto, otros lo cierran

### Flujo de Manejo de Errores

```javascript
// Ejemplo: guardarCliente()
if (!res.ok) {
    if (res.status === 400) {
        // Errores de validación: mantener modal abierto
        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
            w.UIManager.handleError(res, '[clientes.page]', {
                modalSelector: '#modal-cliente',
                errorContainerSelector: '#form-cliente-feedback'
            });
        }
        return;  // ⚠️ CRÍTICO: No cerrar modal
    }
    
    // Otros errores (500, 403, etc.): cerrar modal
    if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, '[clientes.page]');
    }
    return;
}
```

### Contenedor de Errores en HTML

```html
<!-- modals.html - línea 16 -->
<div id="form-cliente-feedback" class="alert alert-danger d-none mb-3" role="alert"></div>
```

---

## 🎯 Eventos y Listeners

### Event Delegation para Botones de Acciones

**Archivo:** `clientes.page.js` (líneas 160-186)

```javascript
const tableContainer = d.querySelector('#grid-clientes');
if (tableContainer) {
    tableContainer.addEventListener('click', function(e) {
        const btn = e.target.closest('button');
        if (!btn) return;
        
        const id = parseInt(btn.getAttribute('data-id'), 10);
        if (!id || isNaN(id)) return;
        
        if (btn.classList.contains('btn-edit')) {
            e.preventDefault();
            e.stopPropagation();
            ClientesModule.editar(id);
        } else if (btn.classList.contains('btn-delete')) {
            e.preventDefault();
            e.stopPropagation();
            if (btn.disabled) {
                if (w.SintelFeedback) {
                    w.SintelFeedback.error('No se puede eliminar un cliente activo. Desactívelo primero.');
                }
                return;
            }
            ClientesModule.eliminar(id);
        }
    });
}
```

### Submit del Formulario

**Archivo:** `clientes.page.js` (líneas 136-157)

```javascript
const form = d.querySelector('#form-cliente');
if (form) {
    // Prevenir envío tradicional (GET)
    form.setAttribute('method', 'POST');
    form.setAttribute('onsubmit', 'return false;');
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        e.stopPropagation();
        await guardarCliente();
    });
    
    // También interceptar el botón de submit directamente
    const submitBtn = d.querySelector('#btn-guardar-cliente');
    if (submitBtn) {
        submitBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            e.stopPropagation();
            await guardarCliente();
        });
    }
}
```

---

## 🔧 Dependencias Globales

### Requeridas

| Variable Global | Archivo Origen | Propósito |
|----------------|----------------|-----------|
| `w.Tabulator` | `tabulator.min.js` | Biblioteca Tabulator |
| `w.TabulatorFactory` | `tabulator.factory.js` | Factory para crear tablas |
| `w.http()` | `lib/api.js` | Función base para llamadas HTTP |
| `w.clientesAPI` | `clientes.api.js` | Wrapper de API de clientes |
| `w.UIManager` | `ui-manager.js` | Manejo de errores y modales |
| `w.SintelFeedback` | `sintel-feedback.js` | Notificaciones de éxito/error |
| `w.DOMUtils` | `dom-utils.js` | Utilidades DOM (opcional) |

### Verificación de Dependencias

```javascript
// clientes.page.js - líneas 522-537
function init() {
    if (!w.Tabulator) {
        console.error('[clientes.page] Tabulator no está disponible');
        return;
    }
    
    if (!w.TabulatorFactory) {
        console.error('[clientes.page] TabulatorFactory no está disponible');
        return;
    }
    
    if (!w.clientesAPI) {
        console.error('[clientes.page] ❌ CRÍTICO: window.clientesAPI no está disponible.');
        return;
    }
    
    initTabulator();
    initEvents();
}
```

---

## 📝 API Pública (w.ClientesModule)

**Archivo:** `clientes.page.js` (líneas 580-602)

```javascript
w.ClientesModule = {
    editar: editar,                    // Editar cliente por ID
    eliminar: eliminar,                // Eliminar cliente por ID
    abrirModalCrear: abrirModalCrear, // Abrir modal para crear nuevo cliente
    refresh: function() {              // Refrescar tabla manualmente
        if (table) {
            table.setPage(1).then(() => {
                table.replaceData();
            });
        }
    }
};
```

### Uso desde HTML

```html
<!-- list.html - línea 9 -->
<button class="btn btn-primary btn-sm" onclick="ClientesModule.abrirModalCrear()">
    <i class="bi bi-plus-lg me-1"></i>Nuevo
</button>
```

---

## 🔐 Reglas de Seguridad

### Eliminación de Clientes

1. **Validación de Estado Activo**: No se puede eliminar un cliente activo
2. **Confirmación del Usuario**: Se requiere confirmación explícita antes de eliminar
3. **Validación en Backend**: El backend también valida el estado antes de eliminar

**Código:**

```javascript
// clientes.page.js - líneas 431-437
if (data.activo) {
    if (w.SintelFeedback) {
        w.SintelFeedback.error('El ítem está activo. Desactívelo primero.');
    }
    return;
}
```

### Validación de Formulario

1. **HTML5 Validation**: Campos requeridos marcados con `required`
2. **Validación en Backend**: DRF Serializer valida datos antes de guardar
3. **Manejo de Errores 400**: Errores de validación se muestran en el modal sin cerrarlo

---

## 🎨 Patrones de UI/UX

### Modal Bootstrap

**Uso de `getOrCreateInstance()`:**

```javascript
// clientes.page.js - líneas 391-407
const modalEl = d.querySelector('#modal-cliente');
if (modalEl) {
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    
    // Usar evento shown.bs.modal para dar foco
    modalEl.addEventListener('shown.bs.modal', function focusFirstInput() {
        const firstInput = modalEl.querySelector('input:not([type="hidden"]), select, textarea');
        if (firstInput) {
            firstInput.focus();
        }
        modalEl.removeEventListener('shown.bs.modal', focusFirstInput);
    }, { once: true });
    
    modal.show();
}
```

### Estados de Loading

```javascript
// clientes.page.js - líneas 222-225
if (btnGuardar) {
    btnGuardar.disabled = true;
    btnGuardar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
}
```

### Notificaciones de Éxito/Error

```javascript
// clientes.page.js - líneas 330-332
if (w.SintelFeedback) {
    w.SintelFeedback.success(id ? 'Cliente actualizado exitosamente' : 'Cliente creado exitosamente');
}
```

---

## 🔄 Recarga de Tabla

### Después de Crear/Actualizar/Eliminar

**Archivo:** `clientes.page.js` (líneas 334-345, 462-472)

```javascript
// ⚠️ CRÍTICO: Recargar tabla con paginación remota
if (table) {
    table.setPage(1).then(() => {
        table.replaceData();
    }).catch(err => {
        console.error('[clientes.page] Error al recargar tabla:', err);
        // Fallback: intentar recargar directamente
        if (table) {
            table.replaceData();
        }
    });
}
```

### Método `refresh()` Público

```javascript
// clientes.page.js - líneas 584-600
refresh: function() {
    if (table) {
        table.setPage(1).then(() => {
            table.replaceData();
        }).catch(err => {
            console.error('[clientes.page] Error al refrescar tabla:', err);
            try {
                table.replaceData();
            } catch (fallbackErr) {
                console.error('[clientes.page] Error en fallback de refresh:', fallbackErr);
            }
        });
    }
}
```

---

## 📊 Estructura de Datos

### Modelo Cliente (Backend)

```python
# apps/tenant/clientes/models.py
class Cliente(models.Model):
    empresa = models.ForeignKey(Empresa, ...)  # SSoT
    tipo_persona = models.CharField(...)       # NATURAL, JURIDICA
    tipo_documento = models.CharField(...)      # CC, CE, NIT, PA
    numero_documento = models.CharField(...)
    razon_social = models.CharField(...)
    nombre_comercial = models.CharField(...)
    regimen_tributario = models.CharField(...) # SIMPLE, ORDINARIO, NO_RESP
    email = models.EmailField(...)
    telefono = models.CharField(...)
    direccion = models.TextField(...)
    ciudad = models.CharField(...)
    activo = models.BooleanField(default=True)
    observaciones = models.TextField(...)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Payload de Creación/Actualización

```javascript
{
    tipo_persona: "JURIDICA",
    tipo_documento: "NIT",
    numero_documento: "900123456-1",
    razon_social: "Empresa Ejemplo S.A.S.",
    nombre_comercial: "Ejemplo",
    regimen_tributario: "ORDINARIO",
    email: "contacto@ejemplo.com",
    telefono: "+57 300 123 4567",
    direccion: "Calle 123 #45-67",
    ciudad: "Bogotá",
    activo: true,
    observaciones: "Cliente preferencial"
}
```

---

## 🐛 Debugging y Logs

### Logs de Consola

**Prefijo:** `[clientes.page]` o `[clientes.api]`

**Ejemplos:**

```javascript
console.error('[clientes.page] ❌ CRÍTICO: window.clientesAPI no está disponible.');
console.error('[clientes.page] Error al guardar cliente');
console.error('[clientes.page] Status:', res.status);
console.error('[clientes.page] Payload enviado:', JSON.stringify(data, null, 2));
console.error('[clientes.page] Respuesta del servidor:', JSON.stringify(res.data, null, 2));
```

### Debug de Errores 400

**Archivo:** `clientes.page.js` (líneas 241-248)

```javascript
if (!res.ok) {
    console.error('[clientes.page] ❌ Error al guardar cliente');
    console.error('[clientes.page] Status:', res.status);
    console.error('[clientes.page] Payload enviado:', JSON.stringify(data, null, 2));
    console.error('[clientes.page] Respuesta del servidor:', JSON.stringify(res.data, null, 2));
    console.error('[clientes.page] Objeto completo de respuesta:', res);
}
```

---

## ✅ Checklist de Validación

### Inicialización

- [ ] Tabulator se carga correctamente
- [ ] TabulatorFactory está disponible
- [ ] clientesAPI está disponible
- [ ] Tabla se inicializa solo cuando el contenedor es visible
- [ ] Eventos se configuran correctamente

### Operaciones CRUD

- [ ] **CREATE**: Modal se abre, formulario se resetea, datos se guardan correctamente
- [ ] **READ**: Tabla se carga con datos paginados, búsqueda funciona con debounce
- [ ] **UPDATE**: Modal se abre con datos, formulario se llena, cambios se guardan
- [ ] **DELETE**: Validación de estado activo funciona, confirmación se muestra, eliminación exitosa

### Manejo de Errores

- [ ] Errores 400 mantienen modal abierto y muestran errores en `#form-cliente-feedback`
- [ ] Errores 500/403 cierran modal y muestran notificación
- [ ] UIManager.handleError() se llama correctamente

### UI/UX

- [ ] Botones de acciones funcionan (Editar/Eliminar)
- [ ] Botón Eliminar se deshabilita para clientes activos
- [ ] Estados de loading se muestran durante guardado
- [ ] Notificaciones de éxito/error se muestran correctamente
- [ ] Tabla se recarga después de operaciones CRUD

---

## 📚 Referencias

### Archivos Relacionados

- `apps/tenant/core/static/core/js/clientes/clientes.api.js` - Capa de Datos
- `apps/tenant/core/static/core/js/clientes/clientes.page.js` - Capa de Presentación
- `apps/tenant/core/templates/tenant/core/partials/clientes/list.html` - Vista principal
- `apps/tenant/core/templates/tenant/core/partials/clientes/modals.html` - Modal de formulario
- `apps/tenant/clientes/api/viewsets.py` - ViewSet DRF
- `apps/tenant/clientes/api/serializers.py` - Serializers DRF
- `apps/tenant/clientes/services.py` - Servicios de negocio

### Documentación Relacionada

- `AUDITORIA_FLUJO.md` (Módulo Cotizaciones) - Referencia de formato
- Tabulator Documentation: https://tabulator.info/
- Django REST Framework: https://www.django-rest-framework.org/

---

## 🔄 Historial de Cambios

### v2.60 (2026-01-XX)

- ✅ Implementación de Aislamiento Gradual
- ✅ Error Boundary Pattern con UIManager
- ✅ Lazy Loading de inicialización
- ✅ Validación de seguridad para eliminación
- ✅ Mejoras en manejo de modales Bootstrap

### v2.40 (2024-XX-XX)

- ✅ Migración a Tabulator Factory
- ✅ API-First Architecture
- ✅ Separación de Capa de Datos y Presentación

---

**Fin del Documento**
