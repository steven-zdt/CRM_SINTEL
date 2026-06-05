# Plan de Accion — Cartera de Proveedores (UI completa)

**Fecha:** 2026-06-03
**Modelo:** `apps/tenant/proveedores/models.py::Cartera`
**Objetivo:** Estado de pagos de facturas de compra por proveedor

---

## Estado actual por capa

| Capa | Archivo | Estado | Bloquea |
|---|---|---|---|
| Model | `models.py::Cartera` | COMPLETO | — |
| Migración | `0012_add_cartera_model` | APLICADA | — |
| Business Service | `business_service::CarteraBusinessService` | COMPLETO (registrar/abonar) | — |
| Serializers | `serializers::Cartera*Serializer` x3 | COMPLETO | — |
| ViewSet | `viewsets::CarteraViewSet` | COMPLETO (código) | CarteraServiceMixin |
| URLs | `urls.py` router.register | COMPLETO | — |
| **Selector** | `selectors::CarteraSelector` | **FALTA** | ViewSet 500 |
| **API Mixin** | `api_mixins::CarteraServiceMixin` | **FALTA** | ViewSet 500 |
| **Import modelo** | `viewsets.py` import Cartera | **FALTA** | ImportError |
| **Template offcanvas** | `offcanvas_cartera.html` | **FALTA** | UI |
| **JS list** | `features/cartera_list.js` | **FALTA** | UI |
| **JS editor** | `features/cartera_editor.js` | **FALTA** | UI |
| **Tab en lista** | `proveedores_list.html` — tab Cartera | **FALTA** | UI |
| **API wrapper JS** | `proveedores.api.js` — endpoint cartera | **FALTA** | UI |

---

## Paso 1 — BACKEND (desbloquear 500) ✅ APLICAR PRIMERO

### 1.1 `selectors.py` — agregar `CarteraSelector`

```python
LIST_FIELDS_CARTERA = (
    "id", "uuid", "empresa_id", "proveedor_id",
    "numero_factura", "factura_uuid",
    "fecha_emision", "fecha_vencimiento",
    "valor_total", "valor_pagado", "saldo",
    "estado_pago", "fecha_ultimo_pago", "referencia_pago",
    "created_at",
)
DETAIL_FIELDS_CARTERA = LIST_FIELDS_CARTERA + ("observaciones", "updated_at")

class CarteraSelector:
    @staticmethod
    def qs_list(empresa_id, proveedor_id=None, estado_pago=None, vencidas=False):
        qs = Cartera.objects.filter(empresa_id=empresa_id).only(*LIST_FIELDS_CARTERA)
        if proveedor_id:
            qs = qs.filter(proveedor_id=proveedor_id)
        if estado_pago:
            qs = qs.filter(estado_pago=estado_pago)
        if vencidas:
            from django.utils import timezone
            qs = qs.filter(fecha_vencimiento__lt=timezone.now().date()).exclude(estado_pago="PAGADA")
        return qs.select_related("proveedor").order_by("fecha_vencimiento")

    @staticmethod
    def get_by_uuid(empresa_id, uuid_val):
        return (
            Cartera.objects
            .filter(empresa_id=empresa_id, uuid=uuid_val)
            .select_related("proveedor")
            .only(*DETAIL_FIELDS_CARTERA, "proveedor__razon_social", "proveedor__numero_documento")
            .first()
        )
```

### 1.2 `api_mixins.py` — agregar `CarteraServiceMixin`

```python
class CarteraServiceMixin:
    @property
    def cartera_selector(self):
        return CarteraSelector()

    @property
    def cartera_service(self):
        return CarteraBusinessService()
```

### 1.3 `viewsets.py` — fix import `Cartera`

```python
from apps.tenant.proveedores.models import Proveedor, CuentaPorPagar, Cartera
```

---

## Paso 2 — TEMPLATE `offcanvas_cartera.html`

**Ruta:** `apps/tenant/proveedores/templates/tenant/proveedores/offcanvas_cartera.html`

**Estructura:**

```html
<div class="offcanvas offcanvas-end" id="offcanvas-cartera" style="width:600px">
  <div class="offcanvas-header border-bottom">
    <h5><!-- Crear / Detalle de Cartera --></h5>
    <button type="button" class="btn-close" data-bs-dismiss="offcanvas"></button>
  </div>

  <div class="offcanvas-body">
    <!-- Modo CREAR: formulario nuevo registro -->
    {% if not cartera %}
      <form id="form-cartera" onsubmit="return false;">
        <!-- proveedor (select) -->
        <!-- numero_factura (input) -->
        <!-- factura_uuid (input hidden opcional) -->
        <!-- fecha_emision (date) -->
        <!-- fecha_vencimiento (date) -->
        <!-- valor_total (number) -->
        <!-- observaciones (textarea) -->
      </form>
    {% else %}
    <!-- Modo DETALLE: datos + panel de abono -->
      <div class="row g-3 mb-4">
        <!-- Proveedor, Factura, Fechas, Totales, Estado (badge), Saldo -->
      </div>
      {% if cartera.estado_pago != 'PAGADA' %}
      <div class="border rounded p-3 bg-light">
        <h6>Registrar Abono</h6>
        <form id="form-abono" onsubmit="return false;">
          <!-- monto -->
          <!-- referencia_pago -->
          <!-- fecha_ultimo_pago -->
          <!-- observaciones -->
        </form>
      </div>
      {% endif %}
    {% endif %}
  </div>

  <div class="offcanvas-footer border-top px-4 py-3">
    <button type="button" data-bs-dismiss="offcanvas" class="btn btn-secondary btn-sm">Cerrar</button>
    {% if not cartera %}
      <button id="btn-guardar-cartera" type="button" class="btn btn-primary btn-sm">Guardar</button>
    {% elif cartera.estado_pago != 'PAGADA' %}
      <button id="btn-registrar-abono" type="button" class="btn btn-success btn-sm">Registrar Abono</button>
    {% endif %}
  </div>
</div>
```

---

## Paso 3 — JS `features/cartera_list.js`

**Namespace:** `window.Sintel.Proveedores.CarteraList`

**Columnas Tabulator (skill: tabulator.md §2):**

```javascript
function getColumnas() {
  return [
    { title: 'Proveedor',       field: 'proveedor_nombre', widthGrow: 2, minWidth: 150 },
    { title: 'Factura',         field: 'numero_factura',   width: 120 },
    { title: 'Vencimiento',     field: 'fecha_vencimiento', width: 110,
      formatter: (cell) => new Date(cell.getValue()).toLocaleDateString('es-CO') },
    { title: 'Total',           field: 'valor_total',  width: 110, hozAlign: 'right',
      formatter: (cell) => '$' + parseFloat(cell.getValue()).toLocaleString('es-CO') },
    { title: 'Saldo',           field: 'saldo',        width: 110, hozAlign: 'right',
      formatter: (cell) => '$' + parseFloat(cell.getValue()).toLocaleString('es-CO') },
    { title: 'Estado',          field: 'estado_pago',  width: 110, hozAlign: 'center',
      formatter: fmtEstadoPago },
    { title: 'Acciones',        field: 'acciones',     width: 100, headerSort: false,
      hozAlign: 'center', formatter: fmtAcciones, cellClick: handleCellAction },
  ];
}
```

**Formatters:**
```javascript
function fmtEstadoPago(cell) {
  const map = {
    'SIN_PAGO': '<span class="badge bg-danger">Sin pago</span>',
    'PARCIAL':  '<span class="badge bg-warning text-dark">Parcial</span>',
    'PAGADA':   '<span class="badge bg-success">Pagada</span>',
  };
  return map[cell.getValue()] || cell.getValue();
}
```

**Flujo HTMX (skill: htmx.md §2):**
- Botón "Nueva Obligacion" → `hx-get /api/v1/proveedores/cartera/render-offcanvas/`
- Botón "Ver/Abonar" → `hx-get /api/v1/proveedores/cartera/render-offcanvas/?uuid={uuid}`
- `htmx:afterSettle` → `UIManager.handleOffcanvas(el, 'show')`

---

## Paso 4 — JS `features/cartera_editor.js`

**Namespace:** `window.Sintel.Proveedores.CarteraEditor`

```javascript
// Crear nueva obligacion
async function guardar(form) {
  const payload = collectData(form);
  const res = await w.http('POST', '/api/v1/proveedores/cartera/', payload);
  ...
}

// Registrar abono
async function registrarAbono(uuid, form) {
  const payload = collectData(form);
  const res = await w.http('POST', `/api/v1/proveedores/cartera/${uuid}/registrar-abono/`, payload);
  ...
}
```

---

## Paso 5 — `proveedores_list.html` — tab Cartera

Agregar tab nuevo junto a los existentes:

```html
<button class="nav-link" id="tab-cartera" data-bs-toggle="tab"
        data-bs-target="#tab-pane-cartera" type="button">
  <i class="bi bi-journal-check me-2"></i>Cartera
  <span class="badge bg-secondary ms-1" id="badge-cartera">0</span>
</button>

<!-- Tab pane -->
<div class="tab-pane fade" id="tab-pane-cartera">
  <div class="d-flex justify-content-between align-items-center mb-3">
    <input type="text" id="search-cartera" class="form-control w-auto"
           placeholder="Buscar por proveedor, factura...">
    <div class="d-flex gap-2">
      <button class="btn btn-outline-secondary btn-sm"
              id="btn-filtro-vencidas">
        <i class="bi bi-exclamation-triangle me-1"></i>Solo vencidas
      </button>
      <button class="btn btn-primary btn-sm"
              hx-get="/api/v1/proveedores/cartera/render-offcanvas/"
              hx-target="#offcanvas-container-proveedores"
              hx-swap="innerHTML"
              hx-on::after-request="if(event.detail.successful){ sintelAbrirOffcanvas('offcanvas-cartera'); }">
        <i class="bi bi-plus-lg me-2"></i>Nueva Obligacion
      </button>
    </div>
  </div>
  <div id="grid-cartera" style="width:100%;min-width:0;"></div>
  <div data-spinner="cartera" class="text-center py-4 d-none">
    <div class="spinner-border text-primary"></div>
  </div>
  <div data-empty-state="cartera" class="text-center py-4 d-none">
    <i class="bi bi-journal-check fs-2 text-muted d-block mb-2"></i>
    <span class="text-muted">Sin obligaciones registradas</span>
  </div>
</div>
```

---

## Paso 6 — `proveedores.api.js` — agregar endpoint cartera

```javascript
cartera: {
  list: (params = {}) => callHttp('GET', buildUrl('/api/v1/proveedores/cartera/', params)),
  get:  (uuid)        => callHttp('GET', `/api/v1/proveedores/cartera/${uuid}/`),
  create: (payload)   => callHttp('POST', '/api/v1/proveedores/cartera/', payload),
  abono: (uuid, data) => callHttp('POST', `/api/v1/proveedores/cartera/${uuid}/registrar-abono/`, data),
},
```

---

## Orden de ejecucion recomendado

```
Sprint 1 (desbloquear 500 — 30 min):
  ├── 1.1  selectors.py — CarteraSelector
  ├── 1.2  api_mixins.py — CarteraServiceMixin
  └── 1.3  viewsets.py — fix import Cartera

Sprint 2 (UI base — 2h):
  ├── 2.1  offcanvas_cartera.html — template crear + detalle/abono
  ├── 2.2  cartera_list.js — Tabulator con columnas y acciones
  └── 2.3  cartera_editor.js — guardar() + registrarAbono()

Sprint 3 (integracion — 1h):
  ├── 3.1  proveedores_list.html — tab Cartera + grid container
  ├── 3.2  proveedores.api.js — endpoint cartera
  └── 3.3  proveedores_main.js — orquestar CarteraList.init() en tab shown
```

---

## KPIs del modulo Cartera (indicadores expuestos por la API)

| KPI | Endpoint | Query |
|---|---|---|
| Total deuda empresa | `GET /cartera/?estado_pago=SIN_PAGO,PARCIAL` | SUM(saldo) |
| Deuda vencida | `GET /cartera/?vencidas=true` | fecha_vencimiento < hoy AND !PAGADA |
| Deuda por proveedor | `GET /cartera/?proveedor_id=X` | agrupado por proveedor |
| Facturas pendientes | `GET /cartera/` | COUNT donde !PAGADA |
