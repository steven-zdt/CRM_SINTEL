# Patrón Canónico de Modales — Facturas

## Resumen

Este documento define el patrón canónico de modales extraído del módulo **Facturas**, que debe ser replicado en todas las apps de `TENANT_APPS` para mantener consistencia en la UI modular.

---

## 1. Estructura de Archivos

### Templates (HTML)
- `apps/tenant/core/templates/tenant/core/partials/facturas/list.html` — Vista principal con toolbar, filtros y tabla
- `apps/tenant/core/templates/tenant/core/partials/facturas/modals.html` — Contenedor de todos los modales
- `apps/tenant/core/templates/tenant/core/partials/facturas/assets_facturas.html` — Inclusión de scripts JS en orden

### JavaScript Modular
- `apps/tenant/core/static/core/js/facturas/facturas.api.js` — Capa de datos (endpoints universales + CRUD)
- `apps/tenant/core/static/core/js/facturas/facturas.components.js` — Helpers (formato, badges, escapeHtml)
- `apps/tenant/core/static/core/js/facturas/facturas.table.js` — Lógica de tabla y filtros
- `apps/tenant/core/static/core/js/facturas/facturas.modals.js` — Lógica de modales (abrir, confirmar, cerrar)
- `apps/tenant/core/static/core/js/facturas/facturas.page.js` — Entry point (`window.initFacturasPage`)

---

## 2. Modales Implementados

### 2.1 Modal de Importar (`#modal-factura-importar`)
**ID canónico**: `modal-<app>-import` (para apps con parse-only)

**Estructura**:
- Input file: `<input type="file" id="input-ubl-file" accept=".xml,text/xml" required />`
- Checkbox preview: `<input type="checkbox" id="check-preview" checked>`
- Feedback: `<div id="import-feedback" class="alert d-none" role="alert" aria-live="polite"></div>`
- Botones:
  - Cancelar: `data-bs-dismiss="modal"`
  - Previsualizar: `id="btn-import-preview"` → `?preview=true`
  - Guardar desde DTO: `id="btn-import-save"` → endpoint app (`create-from-dto`)

**Comportamiento**:
- **Paso 1 (Preview)**: `POST /api/v1/core/documentos/upload/?preview=true` → muestra DTO en feedback
- **Paso 2 (Persistir)**: `POST /api/v1/facturas/create-from-dto/` → recarga tabla y cierra modal

### 2.2 Modal de Detalle (`#modal-factura-detalle`)
**ID canónico**: `modal-<app>-detail`

**Características**:
- **Creado dinámicamente desde JS** (no en `modals.html`)
- Read-only (inmutabilidad de documentos contables)
- Muestra alerta: "⚠️ Documento inmutable — solo lectura"
- Botón cerrar: `data-bs-dismiss="modal"`

### 2.3 Modal de XML (`#modal-factura-xml`)
**ID canónico**: `modal-<app>-xml` (para apps con documentos XML)

**Características**:
- **Creado dinámicamente desde JS**
- Endpoint: `GET /api/v1/core/documentos/{id}/xml/`
- Muestra XML en `<pre><code>` con scroll
- Botón cerrar: `data-bs-dismiss="modal"`

### 2.4 Modal de Eliminar (`confirmDeleteFactura`)
**ID canónico**: Confirmación nativa `confirm()` (no modal Bootstrap)

**Comportamiento**:
- Mensaje: "⚠️ Esta factura será eliminada solo del sistema SINTEL por error de carga.\n\nEsta acción es irreversible.\n\n¿Deseas continuar?"
- Endpoint: `DELETE /api/v1/core/documentos/{id}/`
- Recarga tabla tras éxito

---

## 3. Estructura de Botones y Feedback

### Botones Estándar
- **Confirmar acción**: `data-action="confirm"` (opcional, delegación global)
- **Cerrar modal**: `data-bs-dismiss="modal"` (Bootstrap 5)
- **Acciones de tabla**: `data-action="view|xml|delete"` + `data-id="{id}"`

### Feedback Accesible
- Contenedor: `<div class="alert d-none" id="<app>-modal-feedback" role="alert" aria-live="polite"></div>`
- Clases dinámicas: `alert-success`, `alert-danger`, `alert-warning`, `alert-info`
- Mostrar: `feedback.classList.remove('d-none')`
- Ocultar: `feedback.classList.add('d-none')` + `feedback.textContent = ''`

---

## 4. Eventos y Firma de Funciones en `*.modals.js`

### 4.1 Funciones Exportadas (Global)
```javascript
window.facturasModals = {
  showFacturaDetail,      // (facturaId) → crea modal dinámico
  showFacturaXML,         // (documentId) → crea modal dinámico
  handleImport,           // (file, preview, onSuccess, onError)
  confirmDeleteFactura,   // (documentId, onSuccess, onError)
};
```

### 4.2 Delegación de Eventos
- **Tabla**: `document.addEventListener('click', (ev) => { const btn = ev.target.closest('button[data-action]'); ... })`
- **Modales**: Eventos bindeados en `page.js` al crear modal dinámicamente

### 4.3 Flujo de Import (Parse-Only)
```javascript
async function handleImport(file, preview, onSuccess, onError) {
  // Paso 1: Parsear (siempre preview=true para obtener DTO)
  const parseR = await window.facturasAPI.uploadDocumento(file, true);
  if (!parseR.ok) {
    onError(getErrorMessage(parseR.status, parseR.data));
    return;
  }
  const dto = parseR.data?.dto || parseR.data;
  
  // Si es solo preview, retornar DTO
  if (preview) {
    onSuccess({ preview: true, dto, persisted: false });
    return;
  }
  
  // Paso 2: Persistir desde DTO
  const persistR = await window.facturasAPI.createFacturaFromDTO(dto, true);
  if (!persistR.ok) {
    onError(getErrorMessage(persistR.status, persistR.data));
    return;
  }
  
  onSuccess({ preview: false, dto, persisted: true, factura: persistR.data });
}
```

---

## 5. Errores Canónicos y Mensajes

### Función `getErrorMessage(status, data)`
```javascript
function getErrorMessage(status, data) {
  if (status === 409) {
    return data?.message || data?.detail || 'Documento duplicado (409). Ya existe una factura con el mismo CUFE.';
  } else if (status === 422) {
    return data?.message || data?.detail || 'Documento inválido (422). Verifique que el documento sea válido.';
  } else if (status === 415) {
    return 'Formato no soportado (415). Solo se aceptan archivos XML.';
  } else if (status === 400) {
    return data?.message || data?.detail || 'Error de parsing/detección (400).';
  } else if (status === 401 || status === 403) {
    return data?.detail || data?.message || 'No tienes permisos para realizar esta acción.';
  } else {
    return data?.detail || data?.message || `Error HTTP ${status}`;
  }
}
```

### Códigos HTTP y Significado
- **409 Conflict**: Documento duplicado (CUFE/CUDE ya existe)
- **422 Unprocessable Entity**: Documento inválido (validación de negocio)
- **415 Unsupported Media Type**: Formato no soportado
- **400 Bad Request**: Error de parsing/detección
- **401 Unauthorized**: No autenticado
- **403 Forbidden**: Sin permisos

---

## 6. Endpoints Universales (Parse-Only)

### Upload (Parse-Only)
- **Endpoint**: `POST /api/v1/core/documentos/upload/?preview=true|false`
- **Body**: `FormData` con `file=<archivo>`
- **Headers**: `X-CSRFToken` (automático vía `http.js`)
- **Respuesta**: `{ dto: {...}, document_type: "...", ... }`

### XML
- **Endpoint**: `GET /api/v1/core/documentos/{id}/xml/`
- **Respuesta**: `{ xml: "<xml>..." }` o texto plano

### DELETE
- **Endpoint**: `DELETE /api/v1/core/documentos/{id}/`
- **Respuesta**: `204 No Content` o `200 OK`

### Persistencia (App-Specific)
- **Endpoint**: `POST /api/v1/facturas/create-from-dto/`
- **Body**: `{ dto: {...}, persist_anexos: true }`
- **Respuesta**: `{ id: ..., ... }` (factura materializada)

---

## 7. Orden de Carga de Scripts (`assets_facturas.html`)

```html
{% load static %}
<script src="{% static 'core/js/lib/http.js' %}"></script>
<script src="{% static 'core/js/facturas/facturas.api.js' %}"></script>
<script src="{% static 'core/js/facturas/facturas.components.js' %}"></script>
<script src="{% static 'core/js/facturas/facturas.table.js' %}"></script>
<script src="{% static 'core/js/facturas/facturas.modals.js' %}"></script>
<script src="{% static 'core/js/facturas/facturas.page.js' %}"></script>
```

**Orden crítico**:
1. `lib/http.js` (helper HTTP con CSRF)
2. `<app>.api.js` (endpoints)
3. `<app>.components.js` (helpers)
4. `<app>.table.js` (si aplica)
5. `<app>.modals.js` (lógica de modales)
6. `<app>.page.js` (orquestación)

---

## 8. Entry Point (`page.js`)

### Función Global
```javascript
window.initFacturasPage = async function () {
  // 1. Inyectar HTML (list.html + modals.html)
  // 2. Inicializar componentes (filtros, tabla)
  // 3. Bind eventos (filtros, acciones, importar, refrescar)
  // 4. Cargar datos iniciales
};
```

### Inyección de Partials
- `list.html` → `#workspace-router-outlet`
- `modals.html` → puede estar en `list.html` o inyectarse por separado

---

## 9. Convenciones de IDs y Clases

### IDs de Modales
- `#modal-<app>-import` — Importar (parse-only)
- `#modal-<app>-detail` — Detalle (read-only)
- `#modal-<app>-xml` — Ver XML
- `#modal-<app>-create` — Crear (CRUD)
- `#modal-<app>-edit` — Editar (CRUD)
- `#modal-<app>-delete` — Eliminar (CRUD)

### Clases Bootstrap
- `modal fade` — Contenedor modal
- `modal-dialog` — Contenedor interno
- `modal-content` — Contenido
- `modal-header`, `modal-body`, `modal-footer` — Secciones
- `alert d-none` — Feedback oculto
- `btn-close` — Botón cerrar (Bootstrap 5)

---

## 10. Principios Arquitectónicos

### API-First
- ✅ Backend no renderiza datos (solo JSON)
- ✅ UI consume DRF APIs exclusivamente
- ✅ SessionAuth + CSRF en mutaciones

### Parse-Only Pipeline
- ✅ `document_ingest` **solo parsea** (devuelve DTO)
- ✅ Cada app persiste con su **service layer**
- ✅ Endpoint universal: `/api/v1/core/documentos/upload/`

### Inmutabilidad
- ✅ Facturas son documentos contables inmutables
- ✅ Correcciones vía Notas Crédito/Débito
- ✅ DELETE solo para errores de carga

### Multi-tenant
- ✅ Todas las llamadas API son tenant-aware (schema context)
- ✅ CSRF y SessionAuth garantizan aislamiento

---

## 11. Checklist de Aplicación a Otras Apps

Para cada app en `TENANT_APPS`:

- [ ] Crear `modals.html` con modales CRUD mínimos
- [ ] Crear `<app>.modals.js` con funciones canónicas
- [ ] Alinear `<app>.api.js` a endpoints universales (parse-only)
- [ ] Actualizar `<app>.page.js` para cargar `modals.html`
- [ ] Actualizar `assets_<app>.html` con orden correcto
- [ ] Verificar `router.js` tiene ruta `#<app>` → `init<App>Page`
- [ ] Implementar `getErrorMessage` canónico
- [ ] Probar flujo completo (preview + persistencia)

---

## 12. Notas de Implementación

### Modales Dinámicos vs Estáticos
- **Dinámicos** (creados desde JS): `detail`, `xml` (contenido variable)
- **Estáticos** (en `modals.html`): `import`, `create`, `edit`, `delete` (estructura fija)

### Compatibilidad con Bootstrap 5
- Usar `data-bs-dismiss="modal"` (no `data-dismiss`)
- Usar `new bootstrap.Modal(modal)` para control programático
- Eventos: `hidden.bs.modal` (no `hidden`)

### Manejo de FormData
- `http.js` maneja automáticamente `X-CSRFToken` header
- También agrega `csrfmiddlewaretoken` al `FormData` para compatibilidad Django tradicional

---

**Última actualización**: 2024-12-19  
**Versión del canon**: 1.0  
**App de referencia**: Facturas
