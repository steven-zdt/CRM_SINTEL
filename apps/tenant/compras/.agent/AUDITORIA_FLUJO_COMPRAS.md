# AUDITORIA DE FLUJO DE TRABAJO - MODULO DE COMPRAS

**Version auditada:** v3.10.5 → corregida 2026-06-18  
**Auditor:** Claude Code  
**Estado actual:** 6 bugs criticos/altos corregidos — 3 items de deuda tecnica pendientes

---

## 1. Descripcion General

El modulo de Compras gestiona el ciclo de vida de las Ordenes de Compra en un esquema SaaS multi-tenant estricto. Permite registrar solicitudes de compra de bienes/servicios a proveedores, con aprobacion, recepcion e integracion con Documentos Soporte o Gastos.

**Modelos:** `PlantillaOrdenCompra`, `OrdenCompra`, `ItemOrdenCompra`  
**URL base:** `/api/v1/compras/`  
**Tab workspace:** `#tab-compras` (`section#tab-compras` en workspace.html:110)

---

## 2. Modelos de Datos

### PlantillaOrdenCompra (`SintelTenantBaseModel`)
| Campo | Tipo | Notas |
|---|---|---|
| `uuid` | UUIDField | PK publica en API/URLs |
| `nombre` | CharField(100) | |
| `prefijo` | CharField(10) | Ej: OC, COM. Opcional. |
| `rango_desde` | IntegerField | Min 1 |
| `rango_hasta` | IntegerField | Min 1 |
| `consecutivo_actual` | IntegerField | Proximo numero a asignar |
| `vigente` | BooleanField | Filtro en selector de formulario |

**Metodos:** `formar_numero()`, `esta_en_rango()`  
**Validacion Python:** `clean()` verifica `rango_hasta >= rango_desde`  
**DT-COMPRAS-02:** Sin CheckConstraint DB — solo validacion Python.

**Indice:** `['empresa', 'vigente']`

### OrdenCompra (`SintelTenantBaseModel`)
| Campo | Tipo | Notas |
|---|---|---|
| `uuid` | UUIDField | PK publica |
| `plantilla` | FK PlantillaOrdenCompra | PROTECT, opcional |
| `consecutivo` | IntegerField | Autoasignado por plantilla |
| `numero_documento` | CharField(50) | Formado por plantilla: `prefijo-consecutivo` |
| `proveedor` | FK Proveedor | PROTECT, obligatorio |
| `proyecto` | FK Proyecto | SET_NULL, opcional |
| `documento_soporte` | FK DocumentoSoporte | SET_NULL, opcional |
| `fecha` | DateField | Emision |
| `fecha_entrega` | DateField | Opcional |
| `estado` | CharField | BORRADOR/PENDIENTE/APROBADA/RECIBIDA/ANULADA |
| `subtotal`, `impuestos`, `total` | DecimalField | Calculados desde items |
| `observaciones` | TextField | |

**Constraint:** `UniqueConstraint(['empresa', 'numero_documento'])` — unicidad por tenant  
**DT-COMPRAS-02:** Sin CheckConstraint para `fecha_entrega >= fecha`.  
**Indices:** `['empresa', 'fecha']`, `['empresa', 'estado']`

### ItemOrdenCompra (`SintelTenantBaseModel`)
| Campo | Tipo | Notas |
|---|---|---|
| `orden_compra` | FK OrdenCompra | CASCADE |
| `descripcion` | CharField(255) | |
| `item_inventario_uuid` | UUIDField | Soft ref a catalogo inventario, opcional |
| `cantidad`, `valor_unitario`, `porcentaje_iva` | DecimalField | Entradas del usuario |
| `valor_iva`, `subtotal`, `total` | DecimalField | Calculados en CRUDService |

---

## 3. Flujo de Estados

```
BORRADOR → PENDIENTE → APROBADA → RECIBIDA
    ↓           ↓          ↓
 ANULADA     ANULADA    ANULADA
```

| Estado | Edicion cabecera | Edicion items | Asociar DocSoporte |
|---|---|---|---|
| BORRADOR | Si | Si | No |
| PENDIENTE | Solo admin | No (bloqueado en CRUDService) | No |
| APROBADA | No | No | Si |
| RECIBIDA | No | No | No |
| ANULADA | No | No | No |

`CRUDService.actualizar_orden()` lanza `ValidationError` si `estado not in ['BORRADOR', 'PENDIENTE']`.

---

## 4. Arquitectura de Codigo (Service Layer FSD)

### 4.1 Selectors (`services/selectors.py`)

**`PlantillaOrdenCompraSelector`**
- `get_list(empresa_id, vigente_only=False)` → `.only(*PLANTILLA_LIST_FIELDS)`
- `get_detail(empresa_id, plantilla_uuid)` → `.only(*PLANTILLA_DETAIL_FIELDS)`
- `get_vigentes(empresa_id)` → solo plantillas con `vigente=True`

**`OrdenCompraSelector`**
- `get_list(empresa_id, search=None, estado=None)` → optimizado con:
  - `select_related('proveedor', 'proyecto', 'documento_soporte', 'plantilla')`
  - `.only(*ORDEN_COMPRA_LIST_FIELDS, *_PLANTILLA_TRAVERSALS, *_PROVEEDOR_TRAVERSALS, *_PROYECTO_TRAVERSALS, *_DOCUMENTO_SOPORTE_TRAVERSALS)`
  - **CORREGIDO 2026-06-18:** Se agregaron traversals de proveedor/proyecto/documento_soporte (antes causaban N+1 queries)
- `get_detail(empresa_id, orden_uuid)` → `select_related` + `prefetch_related('items')`
- `get_siguiente_consecutivo(empresa_id)` → `Max('consecutivo')` + 1

**Constantes SSoT (Zero-Collision):**
```python
ORDEN_COMPRA_LIST_FIELDS = ('id', 'uuid', 'consecutivo', 'numero_documento', 'plantilla_id',
    'fecha', 'fecha_entrega', 'estado', 'subtotal', 'impuestos', 'total',
    'empresa_id', 'proveedor_id', 'proyecto_id', 'documento_soporte_id')

_PLANTILLA_TRAVERSALS   = ('plantilla__uuid', 'plantilla__nombre', 'plantilla__prefijo')
_PROVEEDOR_TRAVERSALS   = ('proveedor__razon_social', 'proveedor__numero_documento')
_PROYECTO_TRAVERSALS    = ('proyecto__nombre',)
_DOCUMENTO_SOPORTE_TRAVERSALS = ('documento_soporte__numero_documento',)
```

### 4.2 CRUD Service (`services/crud_service.py`)

**`PlantillaOrdenCompraCRUDService`**
- `crear_plantilla(empresa, data)` — `full_clean()` + `save()`
- `actualizar_plantilla(plantilla, data)` — campos: nombre/prefijo/rango_desde/rango_hasta/consecutivo_actual/vigente
- `eliminar_plantilla(plantilla)` — bloquea si tiene ordenes asociadas

**`OrdenCompraCRUDService`**
- `crear_orden(data, items_data, empresa)` — crea cabecera, crea items con `bulk_create`, actualiza totales
- `actualizar_orden(orden, data, items_data)` — solo si estado BORRADOR/PENDIENTE; reemplaza items si se envian
- `cambiar_estado(orden, nuevo_estado)` — valida contra `ESTADO_CHOICES`
- `eliminar_orden(orden)` — solo si estado BORRADOR

### 4.3 Business Service (`services/business_service.py`)

**`_obtener_entidad_por_id_o_uuid(model_class, lookup_value, empresa_id)`**  
Helper DSV anti-IDOR. Soporta instancias del modelo (con verificacion `empresa_id`), objetos `uuid.UUID`, strings UUID, e integers.

**`_dsv_y_asignar_plantilla(empresa_id, plantilla_raw)`**  
- `select_for_update()` en PlantillaOrdenCompra para prevenir race conditions
- Valida: vigente=True, `esta_en_rango()`
- Asigna consecutivo y llama `formar_numero()`
- **DT-COMPRAS-01:** `consecutivo_actual += 1; save()` — seguro con `select_for_update`, pero patron no canonico (deberia usar `F('consecutivo_actual') + 1`)

**`crear_orden_compra(data, items_data, empresa)`**  
Flujo DSV 4 pasos:
1. DSV Plantilla (obligatorio) → asigna consecutivo
2. DSV Proveedor (obligatorio)
3. DSV Proyecto (opcional)
4. DSV DocumentoSoporte (opcional)
5. Delega a `OrdenCompraCRUDService.crear_orden()`

### 4.4 API Mixins (`services/api_mixins.py`)

- `PlantillaOrdenCompraServiceMixin` — CRUD simple sin business logic
- `OrdenCompraServiceMixin` — delega a `OrdenCompraBusinessService`; expone `service_crear_orden_compra`, `service_actualizar_orden_compra`, `service_cambiar_estado`, `service_eliminar_orden_compra`, `service_get_siguiente_consecutivo`

### 4.5 ViewSets (`api/viewsets.py`)

**`OrdenCompraViewSet`** (hereda `OrdenCompraServiceMixin`, `SintelDSVMixin`, `BaseTenantViewSet`)
- `lookup_field = "uuid"` (heredado de `BaseTenantViewSet`)
- `get_permissions()` → `[IsTenantMember(), IsTenantAdminOrReadOnly()]`  
  **CORREGIDO 2026-06-18:** Eliminado `if settings.DEBUG: return []` que bypasseaba toda autenticacion
- Acciones HTMX: `render_offcanvas/crear`, `render_offcanvas/editar`, `render_offcanvas/detalle`
- Accion extra: `cambiar-estado` (POST), `siguiente-consecutivo` (GET)

**`PlantillaOrdenCompraViewSet`** (hereda `PlantillaOrdenCompraServiceMixin`, `SintelDSVMixin`, `BaseTenantViewSet`)
- `get_permissions()` → `[IsTenantMember(), IsTenantAdminOrReadOnly()]`  
  **CORREGIDO 2026-06-18:** Mismo DEBUG bypass eliminado
- `get_object()` filtrado por `empresa_id` (anti-IDOR)

### 4.6 Serializers (`api/serializers.py`)

**`PlantillaOrdenCompraSerializer`** — fields: id, uuid, nombre, prefijo, `rango_desde`, `rango_hasta`, consecutivo_actual, vigente  
**`ItemOrdenCompraSerializer`** — fields: id, uuid, descripcion, item_inventario_uuid, cantidad, valor_unitario, porcentaje_iva, valor_iva, subtotal, total  
**`OrdenCompraListSerializer`** — fields aplanados: proveedor_nombre/nit, proyecto_nombre, plantilla_nombre, documento_soporte_numero  
**`OrdenCompraDetailSerializer`** — incluye items (many) + plantilla_uuid  
**`OrdenCompraCreateUpdateSerializer`** — `UUIDOrPKRelatedField` para plantilla/proveedor/proyecto/documento_soporte; valida `items` no vacio  
**`UUIDOrPKRelatedField`** — acepta UUID string o PK entero; DSV via `empresa_id` en context; retorna instancia del modelo

**DT-COMPRAS-03:** Sin validacion `fecha_entrega >= fecha` en `validate()` del serializer.

### 4.7 URLs (`api/urls.py`)

```python
router.register(r'plantillas', PlantillaOrdenCompraViewSet, basename='plantilla-orden-compra')
router.register(r'', OrdenCompraViewSet, basename='ordenes-compra')
```

Montado en `config/api_urls.py` bajo `compras/`.

---

## 5. UI y JavaScript

### 5.1 Template principal (`templates/tenant/compras/compras_list.html`)

Incluido en `workspace.html` bajo `<section id="tab-compras">`. Contiene:
- Toolbar con buscador (`#search-compra`) y boton "Nueva Orden" (HTMX GET)
- KPIs: `#kpi-total-ordenes`, `#kpi-monto-total`, `#kpi-aprobadas`, `#kpi-pendientes`
- Spinner: `[data-spinner="compras"]` (inicia oculto)
- Grid: `#grid-compras` (inicia oculto, revelado por JS)
- Container offcanvas: `#offcanvas-container-compras`
- Modal confirmacion eliminar: `#confirmarEliminarModalCompras`

**CORREGIDO 2026-06-18:** Eliminada doble inclusion de `assets_compras.html` que causaba ejecucion doble de los 4 scripts JS. Los assets se cargan solo desde `workspace.html extra_js` (linea 304).

### 5.2 Assets (`templates/tenant/compras/assets_compras.html`)

Cargado UNICAMENTE desde `workspace.html extra_js`:
1. `compras.api.js` — SSoT endpoints + `getHeaders()`
2. `compras.utils.js` — cache de proveedores/proyectos (5 min TTL)
3. `features/compras_list.js` — Tabulator grid + KPIs + event delegation
4. `features/compras_editor.js` — formulario dinamico de items

### 5.3 compras.api.js (`static/compras/js/compras.api.js`)

Namespace: `window.Sintel.Compras.API`

**Endpoints:**
```javascript
API.compras.list          // '/api/v1/compras/'
API.compras.detail(uuid)  // '/api/v1/compras/{uuid}/'
API.compras.cambiarEstado(uuid)  // '/api/v1/compras/{uuid}/cambiar-estado/'
API.compras.create(data)  // POST
API.compras.update(uuid, data)  // PATCH
API.cambiarEstado(uuid, estado) // POST con confirmacion
API.eliminar(uuid)        // DELETE
API.endpoints.renderCrear()
API.endpoints.renderEditar(uuid)
API.endpoints.renderDetalle(uuid)
```

`getHeaders()` — JWT via `window.jwtAuth.getValidAccessToken()`  
**CORREGIDO 2026-06-18:** CSRF ahora leido desde cookie (`getCookie('csrftoken')`) en lugar de `document.querySelector('[name=csrfmiddlewaretoken]')` que retornaba `null` antes de abrir el offcanvas.

### 5.4 compras.utils.js (`static/compras/js/compras.utils.js`)

Namespace: `window.Sintel.Compras.Utils`

- `loadProveedoresSelect(selector, selectedValue, placeholder)` — carga `/api/v1/proveedores/` con cache 5 min
- `loadProyectosSelect(selector, selectedValue, placeholder)` — carga `/api/v1/proyectos/` con cache 5 min
- `invalidateCache(which)` — limpia cache selectiva o total

### 5.5 compras_list.js (`static/compras/js/features/compras_list.js`)

Namespace: `window.Sintel.Compras.ComprasList` (alias: `window.Sintel.Compras.List`)

**Anti-zombie:** Destruye `w.SintelComprasTables` al inicio del modulo.

**`ComprasList.init(retryCount=0)`**
- Guarda: `_initializing = true` (previene doble init)
- 5 reintentos si TabulatorFactory no disponible (500ms cada uno)
- TabulatorFactory.create con `ajaxParams` NO es funcion (no hay filtro por estado, carga todo)
- `searchInputSelector: '#search-compra'` — debounce 300ms integrado en factory

**KPIs:** Calculados en `dataLoaded` y `dataFiltered` desde los datos del grid.

**Event delegation en `#grid-compras`:**
- `.btn-view-compra` → `ComprasList.verDetalle(uuid)` → HTMX GET `render-offcanvas/detalle/`
- `.btn-edit-compra` → `ComprasList.editarCompra(uuid)` → HTMX GET `render-offcanvas/editar/`
- `.btn-delete-compra` → `ComprasList.eliminarCompra(uuid)` → DELETE con confirmacion

**Event delegation en `#offcanvas-container-compras`:**
- `.btn-cambiar-estado` → `cambiarEstado(uuid, estado)` → cierra offcanvas + refresh

**HTMX hooks:**
- `htmx:afterSettle` en `document.body` → abre Bootstrap Offcanvas sobre el nuevo elemento HTML
- `htmx:beforeCleanupElement` → **CORREGIDO 2026-06-18:** `instance.dispose()` (eliminacion inmediata de backdrop) en lugar de `instance.hide()` (animacion que no completaba → backdrops acumulados)

**CORREGIDO 2026-06-18:** Agregado listener `tab-activated` para `redraw(true)` al volver al tab, o `init()` si la tabla aun no existe.

**Eventos reactivos:** Escucha `compra-created` y `compra-updated` en `document.body` → `refresh()`.

### 5.6 compras_editor.js (`static/compras/js/features/compras_editor.js`)

Inicializado via evento `compra-editor-init` disparado desde `htmx:afterSettle` (compras_list.js) o desde `loadAndShowOffcanvas()`.

**Ciclo de vida:**
1. `initializeEditor(form)` — lee `data-mode` y `data-uuid` del `<form>`
2. Carga proveedores y proyectos via `compras.utils.js` (con cache)
3. Bindea filas existentes (modo edicion) o agrega primera fila vacia (modo crear)
4. Configura selector de plantilla con info de rango disponible
5. `handleFormSubmit(e, form)` → `recolectarDatos(form)` → POST o PATCH

**Payload enviado al crear:**
```javascript
{
  plantilla: uuid,  // solo en create
  fecha, fecha_entrega, proveedor, proyecto, observaciones,
  items: [{ descripcion, item_inventario_uuid, cantidad, valor_unitario, porcentaje_iva }]
}
```

**Validacion frontend:** Al menos 1 item con descripcion; verificacion visual si plantilla agotada.

---

## 6. Flujo de Carga workspace/#compras

```
DOMContentLoaded
  ├─► workspace.js: showTab('compras') si hash=#compras
  │     → dispatchEvent('tab-activated', {tabName:'compras'})
  │         → compras_list.js: tab-activated handler
  │               → ComprasList.init() si tabla no existe
  │               → tabla.redraw(true) si ya existe [CORREGIDO]
  │
  ├─► compras_list.js DOMContentLoaded listener
  │     → setup() → ComprasList.init() [guard _initializing previene doble]
  │
  └─► Usuario click "Nueva Orden"
        → HTMX GET /api/v1/compras/render-offcanvas/crear/
        → hx-swap="innerHTML" en #offcanvas-container-compras
        → htmx:beforeCleanupElement → instance.dispose() [CORREGIDO]
        → htmx:afterSettle → new Offcanvas(el).show()
        → dispatchEvent('compra-editor-init', {form})
        → compras_editor.js: initializeEditor(form)
```

---

## 7. Migraciones

| Migracion | Contenido |
|---|---|
| `0001_init_compras.py` | OrdenCompra + ItemOrdenCompra inicial |
| `0002_plantillaordencompra_and_more.py` | PlantillaOrdenCompra + FK plantilla en OrdenCompra |

---

## 8. Registro de Correcciones (2026-06-18)

| ID | Severidad | Archivo | Descripcion | Estado |
|---|---|---|---|---|
| BUG-01 | CRITICO | `compras_list.html:122` | Doble carga de `assets_compras.html` — scripts ejecutaban 2 veces | CORREGIDO |
| BUG-02 | CRITICO | `compras.api.js:117` | CSRF leido de DOM (null antes de abrir offcanvas) → headers invalidos en DELETE/cambiar-estado | CORREGIDO |
| BUG-03 | CRITICO | `compras_list.js:491` | `instance.hide()` en `htmx:beforeCleanupElement` → backdrop no se limpiaba → pantalla negra en 2do open | CORREGIDO |
| BUG-04 | CRITICO | `viewsets.py:51,248` | `if settings.DEBUG: return []` bypasseaba toda autenticacion y aislamiento de tenant | CORREGIDO |
| BUG-05 | ALTO | `selectors.py:82-85` | `select_related` sin traversals en `.only()` → N+1 queries para proveedor/proyecto/documento_soporte | CORREGIDO |
| BUG-06 | ALTO | `compras_list.js` | Sin listener `tab-activated` → Tabulator no redibujaba al volver al tab | CORREGIDO |

---

## 9. Deuda Tecnica — RESUELTA 2026-06-18

| ID | Severidad | Descripcion | Archivo | Estado |
|---|---|---|---|---|
| DT-COMPRAS-01 | MEDIA | `plantilla.consecutivo_actual += 1; save()` → cambiado a `F('consecutivo_actual') + 1` con `.update()` | `business_service.py:121` | RESUELTO |
| DT-COMPRAS-02 | MEDIA | `CheckConstraint` DB agregado en `PlantillaOrdenCompra` (`rango_hasta >= rango_desde`, `consecutivo_actual >= rango_desde`) y en `OrdenCompra` (`fecha_entrega >= fecha`). Migracion `0003_add_check_constraints_compras.py` aplicada. | `models.py` | RESUELTO |
| DT-COMPRAS-03 | BAJA | `validate()` agregado a `OrdenCompraCreateUpdateSerializer` validando `fecha_entrega >= fecha` | `serializers.py` | RESUELTO |

---

## 10. Reglas de Mantenimiento

1. **Agregar traversal al selector** cuando se agregue un campo `source='fk__campo'` en un serializer list.
2. **Nunca `new bootstrap.Offcanvas(el)` mas de una vez** por elemento — el `htmx:beforeCleanupElement` llama `dispose()` antes de cada swap.
3. **No usar `if settings.DEBUG: return []`** en `get_permissions()` — rompe el aislamiento multi-tenant en desarrollo.
4. **Assets** cargados UNICAMENTE en `workspace.html extra_js` — no incluir `assets_compras.html` en templates de listado.
5. **`ajaxParams` como funcion** si se agrega filtro por estado al grid (ver patron en ventas: `function() { return _filtroEstado ? {estado: _filtroEstado} : {}; }`).
