# [PORTAL] Auditoría y SSoT: Módulo Proveedores

**Versión:** 3.17.1 (Representante redesign + CRUD garantizado)
**Estado:** PRODUCTION READY
**Ubicación:** `apps/tenant/proveedores/`
**Última Auditoría:** 2026-06-10
**Última Actualización:** 2026-06-10

---

## Responsabilidades del Módulo

1. **Gestión de Directorio:** Catálogo de acreedores bajo conformidad fiscal colombiana (NIT, régimen, CIIU)
2. **Normativa Tributaria:** Retenciones (retefuente, reteica, reteiva), gran contribuyente, autoretenedor
3. **Aislamiento Multi-tenant:** empresa_id en todas las queries, IDOR prevention via DSV
4. **Cuentas por Pagar:** Registro y seguimiento de deudas a proveedores por factura
5. **Representantes:** Directorio de encargados/contactos autorizados por proveedor
6. **UUID Lookup Field (AGENTS.md §25):** Prevención de enumeration attacks
7. **Double Semantic Verification (AGENTS.md §13):** Protección IDOR en mutaciones

---

## Modelos (`models.py`)

### Proveedor

```
Proveedor(SintelTenantBaseModel)
├── uuid              UUIDField unique, db_index
├── empresa           FK → Empresa (PROTECT, related_name="proveedores")
├── tipo_persona      NATURAL | JURIDICA
├── tipo_documento    NIT | CC | CE | PA
├── numero_documento  sin dígito verificador
├── digito_verificacion (opcional)
├── razon_social      Nombre legal
├── nombre_comercial  (opcional)
├── regimen_tributario SIMPLE | ORDINARIO | NO_RESP
├── actividad_economica_ciiu  Código CIIU
├── responsable_iva   Boolean
├── gran_contribuyente Boolean
├── autoretenedor     Boolean
├── es_retenedor      Boolean
├── aplica_retefuente + retefuente_porcentaje
├── aplica_reteica    + reteica_porcentaje
├── aplica_reteiva    + reteiva_porcentaje
├── email_contacto, telefono_contacto, direccion, ciudad, departamento
├── plazo_pago_dias   default=30
├── banco, tipo_cuenta (AHORROS|CORRIENTE), numero_cuenta
├── activo            Boolean
└── observaciones     TextField

Meta: UniqueConstraint(empresa, tipo_documento, numero_documento)
      Index(empresa, activo), Index(numero_documento), Index(razon_social)
```

### CuentasPagar ⭐ v3.16.0 — Unifica CuentaPorPagar + Cartera

```
CuentasPagar(SintelTenantBaseModel)
├── uuid              UUIDField unique, db_index
├── empresa           FK → Empresa (PROTECT, related_name="carteras")
├── proveedor         FK → Proveedor (CASCADE, related_name="carteras")
├── numero_factura    CharField — número de factura de compra
├── factura_uuid      UUIDField null/blank — soft reference Factura (sin FK directa)
├── orden_compra_uuid UUIDField null/blank — soft reference OrdenCompra (v3.18.0, sin FK directa)
├── fecha_emision     DateField
├── fecha_vencimiento DateField db_index
├── valor_total       DecimalField(18,2) — monto original
├── valor_pagado      DecimalField(18,2) default=0 — acumulado
├── saldo             DecimalField(18,2) default=0 editable=False — calculado por save()
├── estado_pago       SIN_PAGO | PARCIAL | PAGADA  db_index
├── fecha_ultimo_pago DateField null/blank
├── referencia_pago   CharField blank — comprobante
└── observaciones     TextField blank

Reglas de negocio en save():
  1. Sanitiza valor_pagado < 0 → 0
  2. saldo = valor_total - valor_pagado
  3. estado SIN_PAGO  → valor_pagado == 0
  4. estado PARCIAL   → 0 < valor_pagado < valor_total
  5. estado PAGADA    → valor_pagado >= valor_total

Meta: UniqueConstraint(empresa, proveedor, numero_factura)
      Index(empresa, estado_pago), Index(empresa, proveedor, estado_pago)
      Index(numero_factura), Index(fecha_vencimiento), Index(factura_uuid)

Bounded Context: factura_uuid es soft reference — nunca FK directa a app facturas.
Lectura de factura via FacturaInterAppAPI. (AGENTS.md §18)
```

### Representante ⭐ v3.17.0 — Encargado/Contacto Autorizado por Proveedor

```
Representante(SintelTenantBaseModel)
├── uuid              UUIDField unique, db_index
├── empresa           FK → Empresa (PROTECT, related_name="representantes_proveedor")
├── proveedor         FK → Proveedor (CASCADE, related_name="representantes")
├── tipo_documento    CC | CE | PA | NIT
├── numero_documento  CharField max_length=32
├── nombre_completo   CharField max_length=255
├── email_contacto    EmailField blank
├── telefono_contacto CharField blank
├── cargo             CharField default="Representante Legal"
└── es_principal      Boolean default=True — representante para correspondencia oficial

Concepto: Un "representante" es el encargado (persona) de un proveedor.
Relación: Proveedor 1:N Representante.

Reglas de negocio:
  1. DSV: proveedor.empresa_id debe == empresa_id del request
  2. UniqueConstraint(empresa, proveedor, numero_documento)
  3. es_principal: marcador de contacto principal (validación en UI)

Meta: UniqueConstraint(empresa, proveedor, numero_documento)
      Index(empresa, proveedor), Index(empresa, es_principal)
      Index(numero_documento), Index(email_contacto)
```

---

## Historial de Migraciones

| # | Archivo | Contenido |
|---|---|---|
| 0001 | `initial.py` | Proveedor base |
| 0002 | `add_uuid_to_proveedor.py` | UUID field |
| 0003 | `add_retenciones_fields.py` | Retenciones v3.5 |
| 0004–0008 | varios | Campos adicionales |
| 0009 | `alter_proveedor_created_at_and_more` | SintelTenantBaseModel sync + CreateModel CuentaPorPagar (legacy) |
| 0010 | `delete_cuentaporpagar` | Eliminado CuentaPorPagar (primer intento legacy) |
| 0011 | `recreate_cuentaporpagar` | Re-crea CuentaPorPagar (segundo intento, ya unificado en Cartera) |
| 0012 | `add_cartera_model` | Crea modelo Cartera (v3.16.0 — modelo unificado completo) |
| 0013 | `remove_cuentaporpagar_unify_cartera` | Elimina CuentaPorPagar definitivamente |
| **0014** | `rename_cartera_cuentaspagar_and_more` | **RenameModel Cartera → CuentasPagar** |
| **0015** | `update_cuentaspagar_verbose_name` | verbose_name = "Cuentas por Pagar" |
| 0016–0017 | (gap) | Migraciones de otros módulos |
| **0018** | `representante_and_more` | **CreateModel Representante (v3.17.0) + constraint** |
| **0019** | `cuentaspagar_orden_compra_uuid_and_more` | **Agrega `orden_compra_uuid` (v3.18.0) — soft reference para la sincronizacion automatica desde Compras** |

---

## Service Layer

### Selectors (`services/selectors.py`)

```python
# Proveedor
LIST_FIELDS   = (id, uuid, tipo_*, numero_documento, razon_social, ...)
DETAIL_FIELDS = LIST_FIELDS + (plazo_pago_dias, banco, tipo_cuenta, ...)

class ProveedorSelector:
    get_list(empresa_id, search)        → .only(LIST_FIELDS)
    get_by_id(empresa_id, pk)           → .only(DETAIL_FIELDS)
    get_by_uuid(empresa_id, uuid_val)   → .only(DETAIL_FIELDS)
    get_cartera_resumen(empresa_id, uuids) → query agrupada Facturas COMPRA (N=1 query)
    get_by_documento(empresa_id, tipo, numero) → lookup por documento legal

# CuentasPagar
LIST_FIELDS_CARTERA   = (id, uuid, empresa_id, proveedor_id, numero_factura,
                          factura_uuid, fecha_*, valor_total, valor_pagado,
                          saldo, estado_pago, fecha_ultimo_pago, referencia_pago,
                          created_at)
DETAIL_FIELDS_CARTERA = LIST_FIELDS_CARTERA + (observaciones, updated_at)

class CuentasPagarSelector:
    qs_list(empresa_id, proveedor_id, estado_pago, vencidas)
        → .select_related("proveedor").only(LIST_FIELDS_CARTERA + proveedor traversals)
    get_by_uuid(empresa_id, uuid_val)
        → .select_related("proveedor").only(DETAIL_FIELDS_CARTERA + traversals)
    resumen_por_empresa(empresa_id) → dict KPIs (deuda_total, deuda_vencida, ...)

# Representante
LIST_FIELDS_REPRESENTANTE = (id, uuid, empresa_id, proveedor_id, tipo_documento,
                              numero_documento, nombre_completo, email_contacto,
                              telefono_contacto, cargo, es_principal)

class RepresentanteSelector:
    get_list_por_proveedor(empresa_id, proveedor_uuid)
        → filter(empresa_id, proveedor__uuid).only(LIST_FIELDS).order_by(-es_principal)
    get_list_por_empresa(empresa_id)            ← NUEVO v3.17.1
        → filter(empresa_id).only(LIST_FIELDS).order_by(-es_principal, nombre_completo)
        → Usado por DirectorioRepresentantes (sin filtro de proveedor)
    get_by_uuid(empresa_id, uuid_val)
        → .select_related("proveedor").only(LIST_FIELDS + proveedor traversals)
    get_principal_por_proveedor(empresa_id, proveedor_id) → representante principal o None
```

### CRUD Service (`services/crud_service.py`)

```python
class ProveedorCRUDService:
    create(empresa_id, data)          @atomic
    update(proveedor, data)           @atomic
    delete(proveedor)                 @atomic  # hard delete + CASCADE gastos
    update_or_create(empresa_id, data) @atomic

class RepresentanteCRUDService:
    create(empresa_id, proveedor_id, data)    @atomic
    update(representante, data)               @atomic
    delete(representante)                     @atomic
```

### Business Service (`services/business_service.py`)

```python
class ProveedorBusinessService:
    crear_proveedor(empresa_id, data)        → DSV + CRUD
    actualizar_proveedor(proveedor, data)    → DSV + CRUD
    eliminar_proveedor(proveedor)
        — Validar activo==False antes de eliminar
        — Hard delete + CASCADE a DocumentoSoporte
    obtener_snapshot_proveedor(empresa, uuid, tipo_documento)
    obtener_o_crear_proveedor(empresa_id, data)

class CuentasPagarBusinessService:
    registrar_cuenta_pagar(proveedor, empresa_id, datos_cuenta_pagar)
        → get_or_create idempotente por (empresa, proveedor, numero_factura)
        → datos_cuenta_pagar acepta orden_compra_uuid opcional (v3.18.0)
    registrar_abono(cuenta_pagar_uuid, monto, observaciones, empresa_id)
        → select_for_update() + cuenta_pagar.valor_pagado += monto + save()
        → save() auto-recalcula saldo y estado_pago

class RepresentanteBusinessService:
    crear_representante(empresa_id, proveedor_uuid, data)
        → DSV: proveedor.empresa_id == empresa_id
        → RepresentanteCRUDService.create()
    actualizar_representante(empresa_id, representante_uuid, data)
        → DSV: representante.empresa_id == empresa_id
        → RepresentanteCRUDService.update()
    eliminar_representante(empresa_id, representante_uuid)
        → DSV: representante.empresa_id == empresa_id
        → RepresentanteCRUDService.delete()
```

### API Mixins (`services/api_mixins.py`)

```python
class ProveedorServiceMixin(BaseServiceMixin):
    selector_class         = ProveedorSelector
    business_service_class = ProveedorBusinessService
    crud_service_class     = ProveedorCRUDService

class CuentasPagarServiceMixin:
    @property cuentas_pagar_selector → CuentasPagarSelector()
    @property cuentas_pagar_service  → CuentasPagarBusinessService()

class RepresentanteServiceMixin:
    @property representante_selector → RepresentanteSelector()
    @property representante_service  → RepresentanteBusinessService()
```

---

## API Layer

### Endpoints

| Endpoint | Método | Acción | Serializer |
|---|---|---|---|
| `/api/v1/proveedores/` | GET | Listar proveedores + cartera inline | ProveedorListSerializer |
| `/api/v1/proveedores/` | POST | Crear proveedor | ProveedorDetailSerializer |
| `/api/v1/proveedores/{uuid}/` | GET | Detalle proveedor | ProveedorDetailSerializer |
| `/api/v1/proveedores/{uuid}/` | PATCH | Actualizar proveedor | ProveedorDetailSerializer |
| `/api/v1/proveedores/{uuid}/` | DELETE | Eliminar + CASCADE | — |
| `/api/v1/proveedores/cuentas-pagar/` | GET | Listar CuentasPagar | CuentasPagarListSerializer |
| `/api/v1/proveedores/cuentas-pagar/` | POST | Registrar obligación | — |
| `/api/v1/proveedores/cuentas-pagar/{uuid}/` | GET | Detalle CxP | CuentasPagarDetailSerializer |
| `/api/v1/proveedores/cuentas-pagar/{uuid}/registrar-abono/` | POST | Registrar pago | CuentasPagarAbonoSerializer |
| **`/api/v1/proveedores/representantes/`** | GET | Listar todos (empresa) o filtrar por `?proveedor_uuid=` | RepresentanteListSerializer |
| **`/api/v1/proveedores/representantes/`** | POST | Crear representante (`proveedor_uuid` en body) | RepresentanteDetailSerializer |
| **`/api/v1/proveedores/representantes/{uuid}/`** | GET | Detalle representante | RepresentanteDetailSerializer |
| **`/api/v1/proveedores/representantes/{uuid}/`** | PATCH | Actualizar representante | RepresentanteDetailSerializer |
| **`/api/v1/proveedores/representantes/{uuid}/`** | DELETE | Eliminar representante | — |

**Orden crítico en urls.py:** `cuentas-pagar` y `representantes` ANTES del prefijo vacío `""` de ProveedorViewSet. Si el prefijo vacío va primero, Django interpreta `cuentas-pagar` o `representantes` como UUID → ValidationError.

**Router plano (NO anidado):** `RepresentanteViewSet` usa `DefaultRouter` plano. El `proveedor_uuid` NO llega como kwarg de URL — viene de `request.query_params` (GET) o `request.data` (POST). El `uuid` del representante viene de `self.kwargs.get('uuid')`.

### RepresentanteViewSet — Arquitectura DSV Correcta

```python
class RepresentanteViewSet(RepresentanteServiceMixin, BaseTenantViewSet):
    lookup_field    = 'uuid'
    lookup_url_kwarg = 'uuid'
    queryset        = Representante.objects.none()

    def get_queryset(self):
        empresa = self.get_empresa()
        return Representante.objects.filter(empresa=empresa)

    def get_object(self):
        """DSV empresa + uuid. Router plano: proveedor_uuid NO en kwargs."""
        empresa = self.get_empresa()
        representante_uuid = self.kwargs.get('uuid')   # ← self.kwargs, NO param
        obj = Representante.objects.filter(
            empresa=empresa, uuid=representante_uuid
        ).first()
        if not obj:
            raise NotFound("Representante no encontrado.")
        return obj

    def list(self, request, *args, **kwargs):
        empresa = self.get_empresa()
        proveedor_uuid = request.query_params.get('proveedor_uuid')  # ← query_params
        if proveedor_uuid:
            qs = self.representante_selector.get_list_por_proveedor(empresa.id, proveedor_uuid)
        else:
            qs = self.representante_selector.get_list_por_empresa(empresa.id)
        ...

    def create(self, request, *args, **kwargs):
        empresa = self.get_empresa()
        proveedor_uuid = request.data.get('proveedor_uuid')  # ← request.data
        if not proveedor_uuid:
            return Response({"error": "proveedor_uuid es obligatorio."}, status=400)
        ...

    def update(self, request, *args, **kwargs):
        empresa = self.get_empresa()
        representante_uuid = self.kwargs.get('uuid')   # ← self.kwargs
        ...

    def destroy(self, request, *args, **kwargs):
        empresa = self.get_empresa()
        representante_uuid = self.kwargs.get('uuid')   # ← self.kwargs
        ...
```

**Bugs críticos corregidos en v3.17.1 (5 fixes):**

| Bug | Causa | Fix |
|---|---|---|
| `list()` siempre 0 resultados | `def list(self, req, proveedor_uuid=None)` — DRF no inyecta query params | Leer `request.query_params.get('proveedor_uuid')` |
| `get_object()` siempre NotFound | `filter(proveedor__uuid=None)` — router plano, no hay kwarg `proveedor_uuid` | Filtrar solo `empresa + uuid`, sin `proveedor__uuid` |
| `update()` uuid siempre None | `def update(self, req, uuid=None)` — DRF no inyecta URL capture groups | Leer `self.kwargs.get('uuid')` |
| `destroy()` uuid siempre None | Ídem | Ídem |
| `create()` proveedor_uuid None | `def create(self, req, proveedor_uuid=None)` | Leer `request.data.get('proveedor_uuid')` |

### Serializers

```python
ProveedorListSerializer          → lista Tabulator (cartera_resumen inline)
ProveedorDetailSerializer        → crear/editar proveedor
CuentasPagarListSerializer       → Tabulator CxP (proveedor_razon_social denormalizado)
CuentasPagarDetailSerializer     → detalle + factura_detalle via FacturaInterAppAPI
CuentasPagarAbonoSerializer      → entrada para POST registrar-abono (monto, observaciones)
RepresentanteListSerializer      → lista Tabulator (tipo_documento_display denormalizado)
RepresentanteDetailSerializer    → crear/editar representante
```

---

## Frontend

### Arquitectura de Templates (v3.17.1)

```
workspace.html
└── (include) proveedores_list.html   ← tabs propios internos
    ├── Tab: Directorio              → contenido del proveedor
    ├── Tab: Cuentas por Pagar       → cartera_list.js
    └── Tab: Representantes          → representantes_directory.html
                                       (directorio global consolidado)

    (include permanente al fondo del body)
    └── offcanvas_representante_form.html  ← SIEMPRE en DOM
```

**Regla crítica de DOM:** El offcanvas `#offcanvas-representante` debe estar en el DOM al cargar `proveedores_list.html`, independientemente del tab activo. Se incluye via `{% include %}` al final de `proveedores_list.html`. NO incluir dentro de offcanvas de proveedor ni en assets condicionales.

**workspace.html (v3.17.1 — sin outer nav-pills):**
```html
{# Módulo Proveedores v3.17.0 - Feature-Sliced Architecture + Representantes #}
<section id="tab-proveedores" class="workspace-tab" style="display: none;">
  {% include 'tenant/proveedores/proveedores_list.html' %}
</section>
```

El outer wrapper de nav-pills (Directorio / Cuentas / Representantes) fue eliminado de `workspace.html` — era duplicado del inner nav-pills de `proveedores_list.html`.

### Templates

```
templates/tenant/proveedores/
├── proveedores_list.html
│   ├── 3 subtabs: #subtab-directorio | #subtab-cuentas-pagar | #subtab-representantes
│   ├── IDs de botones: #subtab-directorio-btn | #subtab-cuentas-pagar-btn | #subtab-representantes-btn
│   └── (include al final) offcanvas_representante_form.html
├── assets_proveedores.html     Carga TODOS los scripts del módulo en orden
├── offcanvas_form.html         Crear/editar Proveedor (premium, flexbox footer)
├── offcanvas_cuentas_por_pagar.html
├── offcanvas_representante_form.html  (v3.17.1 — redesign 560px, dos paneles)
└── partials/
    ├── representantes_directory.html  (Tabulator global, "Nuevo Representante")
    ├── list_representantes.html       (tabla simple por proveedor, con data-attrs)
    └── assets_representantes.html     (vacío — scripts en assets_proveedores.html)
```

### Offcanvas Representante (v3.17.1 — Redesign)

`offcanvas_representante_form.html` — dos modos de apertura:

| Modo | Condición | Panel visible | Comportamiento |
|---|---|---|---|
| **Directorio** | `representanteUuid=null, proveedorUuid=null` | `#proveedor-selector-container` | Carga lista de proveedores via `GET /api/v1/proveedores/` y muestra `<select>` |
| **Detalle Proveedor** | `proveedorUuid != null` | `#proveedor-info-container` | Muestra badge azul con nombre del proveedor (no editable) |
| **Editar** | `representanteUuid != null` | badge (si hay nombre) | Carga datos del representante, muestra badge si hay nombre |

```html
<!-- Panel 1: Solo visible en modo directorio -->
<div id="proveedor-selector-container" class="mb-4 d-none">
  <select class="form-select" id="proveedor_select">...</select>
</div>

<!-- Panel 2: Solo visible con proveedor pre-seleccionado -->
<div id="proveedor-info-container" class="mb-4 d-none">
  <div class="proveedor-badge">
    <span id="proveedor-nombre-display">—</span>
  </div>
</div>
```

### JavaScript (`static/proveedores/js/`)

```
representante.api.js           SSoT endpoints REST representantes
                               CRÍTICO: const w = window; al inicio del IIFE
                               BASE_URL = '/api/v1/proveedores/representantes'
                               Métodos: listar(proveedorUuid?), obtener(uuid),
                                        crear(data, proveedorUuid), actualizar(uuid, data),
                                        eliminar(uuid), getTipoDocumentoDisplay(code)

features/
    representante_list.js      Tabla HTML simple (proveedor detalle tab)
                               Namespace: window.Sintel.Proveedores.Representante
                               cargarTabla(proveedorUuid):
                                 → lee container.dataset.proveedorNombre
                                 → pasa a renderizarTabla(data, proveedorUuid, proveedorNombre)
                               renderizarTabla(representantes, proveedorUuid='', proveedorNombre=''):
                                 → botón edit: abrirFormRepresentante(uuid, proveedorUuid, proveedorNombre)
                                 → botón delete: eliminarRepresentante(uuid, proveedorUuid)

    representante_editor.js    Form editor (modo directorio + modo detalle)
                               Namespace: window.Sintel.Proveedores (funciones globales del módulo)

                               abrirFormRepresentante(representanteUuid, proveedorUuid, proveedorNombre=''):
                                 → determina modoDirectorio = !representanteUuid && !proveedorUuid
                                 → si modoDirectorio: muestra #proveedor-selector-container
                                                      carga proveedores via _cargarProveedores()
                                 → si proveedorUuid: muestra #proveedor-info-container con nombre
                                 → guarda en form.dataset: representanteUuid, proveedorUuid, modoDirectorio
                                 → new bootstrap.Offcanvas(el).show()

                               guardarRepresentante():
                                 → si modoDirectorio: lee proveedorUuid desde #proveedor_select
                                 → valida, construye data, llama api.crear() o api.actualizar()
                                 → _recargarTabla(modoDirectorio ? '' : proveedorUuid)

                               eliminarRepresentante(uuid, proveedorUuid):
                                 → confirm() → api.eliminar()
                                 → _recargarTabla(proveedorUuid)

                               _recargarTabla(proveedorUuid):
                                 → proveedorUuid presente: Representante.cargarTabla(proveedorUuid)
                                 → sin proveedorUuid: DirectorioRepresentantes.reload()
```

### Propagación de proveedorNombre (cadena completa)

```
Server (Django):
  {{ proveedor.razon_social|escapejs }}
  → data-proveedor-nombre en #representantes-container
  → data-proveedor-uuid en #representantes-container

JS cargarTabla(proveedorUuid):
  → container.dataset.proveedorNombre
  → renderizarTabla(data, proveedorUuid, proveedorNombre)

JS renderizarTabla(reps, proveedorUuid, proveedorNombre):
  → onclick: abrirFormRepresentante(uuid, proveedorUuid, proveedorNombre)

JS abrirFormRepresentante(uuid, proveedorUuid, proveedorNombre):
  → proveedor-nombre-display.textContent = proveedorNombre
```

### Namespace Global y Cross-Module Communication

```javascript
// Expuesto por representante_editor.js
window.Sintel.Proveedores.abrirFormRepresentante(uuid, proveedorUuid, proveedorNombre)
window.Sintel.Proveedores.guardarRepresentante()
window.Sintel.Proveedores.eliminarRepresentante(uuid, proveedorUuid)

// Expuesto por representantes_directory.html (inline script)
window.Sintel.DirectorioRepresentantes = { reload: reloadDirectorio }
// Llamado por _recargarTabla('') después de CRUD desde modo directorio

// Expuesto por representante_list.js
window.Sintel.Proveedores.Representante.cargarTabla(proveedorUuid)
window.Sintel.Proveedores.Representante.renderizarTabla(reps, proveedorUuid, proveedorNombre)
```

### Patrón de inicialización de tabs

```javascript
// proveedores_main.js — initSubtabRedraws()
// IDs de INNER tabs (de proveedores_list.html, no de workspace.html)
const tabDirectorio     = d.querySelector('#subtab-directorio-btn');
const tabCuentasPagar   = d.querySelector('#subtab-cuentas-pagar-btn');
const tabRepresentantes = d.querySelector('#subtab-representantes-btn');

tabRepresentantes.addEventListener('shown.bs.tab', () => {
    // El directorio se auto-inicializa internamente (inline script en representantes_directory.html)
});
```

**Tabulator directory — regla destroy-before-recreate:**
```javascript
async function reloadDirectorio() {
    if (table) { table.destroy(); table = null; }  // OBLIGATORIO antes de re-crear
    initialized = false;
    await initTable();
}
```

---

## Flujo End-to-End

### Directorio de Proveedores

```
GET /api/v1/proveedores/
    ↓ ProveedorViewSet.list()
    ↓ ProveedorSelector.get_list(empresa_id, search)
    ↓ get_cartera_resumen() — una sola query agrupada (N=1)
    ↓ ProveedorListSerializer (cartera_resumen inline)
    ↓ Tabulator grid con columna Cartera

HTMX → render-offcanvas/crear → offcanvas_form.html
    ↓ htmx:afterSettle → UIManager.handleOffcanvas(el, 'show')
    ↓ proveedores_form.js: guardar() → POST /api/v1/proveedores/
    ↓ ProveedorBusinessService.crear_proveedor() → DSV → @atomic → 201
    ↓ Tabulator.replaceData()
```

### Cuentas por Pagar

```
GET /api/v1/proveedores/cuentas-pagar/
    ↓ CuentasPagarViewSet.list()
    ↓ CuentasPagarSelector.qs_list(empresa_id, estado_pago)
    ↓ CuentasPagarListSerializer (proveedor_razon_social denormalizado)
    ↓ Tabulator grid

POST /api/v1/proveedores/cuentas-pagar/{uuid}/registrar-abono/
    ↓ CuentasPagarViewSet.registrar_abono()
    ↓ CuentasPagarBusinessService.registrar_abono()
       → select_for_update()
       → cxp.valor_pagado += monto
       → cxp.save()  ← auto-recalcula saldo y estado_pago
    ↓ 200 OK + CuentasPagarDetailSerializer
```

### Sincronizacion automatica desde Compras (v3.18.0)

**Hallazgo real (2026-08-26):** `CuentasPagar` tenia 0 registros en el tenant
`home` pese a existir una OrdenCompra real, porque `registrar_cuenta_pagar()`
solo se llamaba desde el endpoint manual — ningun flujo de Compras/Facturas/
Gastos lo disparaba. Confirmado que el mismo patron (100% manual, sin
trigger) existe simetricamente en `clientes.Cartera` (cuentas por cobrar).

Decision explicita del usuario: el punto de reconocimiento de la obligacion
es la transicion de la Orden de Compra a **APROBADA** (no RECIBIDA, no la
existencia de una Factura DIAN — muchas compras de este ERP nunca generan
una factura electronica).

```
POST /api/v1/compras/{uuid}/cambiar-estado/  {"estado": "APROBADA"}
    ↓ OrdenCompraBusinessService.cambiar_estado_orden_compra()
    ↓ OrdenCompraCRUDService.cambiar_estado(orden, 'APROBADA')
    ↓ si nuevo_estado == 'APROBADA':
        OrdenCompraBusinessService._sincronizar_cuenta_por_pagar(orden)
            ↓ numero_factura = orden.numero_documento (o "OC-{consecutivo}")
            ↓ fecha_vencimiento = orden.fecha + proveedor.plazo_pago_dias
            ↓ CuentasPagarBusinessService.registrar_cuenta_pagar(
                  proveedor=orden.proveedor, empresa_id=orden.empresa_id,
                  datos_cuenta_pagar={..., "orden_compra_uuid": orden.uuid})
                  ↓ get_or_create(empresa, proveedor, numero_factura) — idempotente
```

**Alcance deliberado:** si la orden se anula despues de aprobada, la CxP ya
generada NO se reversa automaticamente (mismo criterio que
`RecepcionCompraBusinessService.anular_recepcion()`, que tampoco reversa
`MovimientoInventario` de una recepcion CONFIRMADA).

Ver `apps/tenant/compras/.agent/AUDITORIA_FLUJO_COMPRAS.md` para el lado
Compras del bridge.

### Representantes — Directorio Global

```
Tab "Representantes" mostrado
    ↓ representantes_directory.html inline script: shown.bs.tab → initTable()
    ↓ GET /api/v1/proveedores/representantes/  (sin proveedor_uuid)
    ↓ RepresentanteViewSet.list() → RepresentanteSelector.get_list_por_empresa(empresa.id)
    ↓ RepresentanteListSerializer → Tabulator grid

"Nuevo Representante" button click → abrirFormRepresentante(null, null)
    ↓ modoDirectorio = true
    ↓ muestra #proveedor-selector-container
    ↓ GET /api/v1/proveedores/?page_size=200 → pobla <select>

Guardar
    ↓ proveedorUuid = document.getElementById('proveedor_select').value
    ↓ POST /api/v1/proveedores/representantes/ con {proveedor_uuid, ...data}
    ↓ RepresentanteViewSet.create() → DSV proveedor → @atomic → 201
    ↓ _recargarTabla('') → DirectorioRepresentantes.reload()
       → table.destroy() + initTable()  ← evita Tabulator doble instancia
```

### Representantes — Detalle de Proveedor

```
Proveedor detalle offcanvas abierto → tab "Representantes" → cargarTabla(proveedorUuid)
    ↓ GET /api/v1/proveedores/representantes/?proveedor_uuid=<uuid>
    ↓ RepresentanteViewSet.list() → RepresentanteSelector.get_list_por_proveedor(empresa.id, uuid)
    ↓ renderizarTabla(data, proveedorUuid, proveedorNombre)  ← nombre del data-attr

"Agregar Encargado" → abrirFormRepresentante(null, proveedorUuid, proveedorNombre)
    ↓ modoDirectorio = false
    ↓ muestra #proveedor-info-container con badge del nombre

Edit button → abrirFormRepresentante(rep.uuid, proveedorUuid, proveedorNombre)
    ↓ carga datos del representante, muestra badge

Guardar (editar o crear)
    ↓ POST o PATCH /api/v1/proveedores/representantes/{uuid}/
    ↓ _recargarTabla(proveedorUuid) → Representante.cargarTabla(proveedorUuid)
```

---

## Conformidad AGENTS.md (v3.17.1)

| Regla | Estado |
|---|---|
| §4 Zero Waste `.only()` | ✅ LIST_FIELDS/DETAIL_FIELDS en todos los selectores |
| §5 Service Layer unidireccional | ✅ ViewSet → Mixin → BusinessService → CRUDService |
| §13 IDOR Prevention DSV | ✅ empresa_id en todas las queries + DSV en mutations |
| §14/§25 UUID Lookup | ✅ `lookup_field="uuid"` en todos los ViewSets |
| §17 Bridge Isolation | ✅ Sin imports directos de apps.public |
| §18 Bounded Context Facturas | ✅ factura_uuid soft reference, FacturaInterAppAPI para leer |
| §22 CSS Isolation | ✅ Templates sin CSS cross-app |
| §23 JS Isolation | ✅ `window.Sintel.Proveedores` namespace |
| §26 Anti-Backdrop Offcanvas | ✅ `new bootstrap.Offcanvas(el).show()` — no `getOrCreateInstance` |
| §27 UUID sin parseInt | ✅ No hay parseInt sobre UUIDs de FK |
| §30 Zero-Collision selectors | ✅ Traversals en _*_TRAVERSALS, no en FIELD constants |
| §31 SSoT Frontend skills | ✅ Consultar .agents/skills/frontend/ antes de UI changes |
| Router plano vs anidado | ✅ Parámetros leídos de request.query_params / request.data / self.kwargs |

---

## Estructura Física

```
apps/tenant/proveedores/
├── models.py
│   ├── Proveedor          (directorio acreedores, normativa colombiana)
│   ├── CuentasPagar       (v3.16.0 — unificación CuentaPorPagar + Cartera)
│   └── Representante      (v3.17.0 — encargados/contactos por proveedor)
├── api/
│   ├── viewsets.py        (ProveedorViewSet + CuentasPagarViewSet + RepresentanteViewSet)
│   ├── serializers.py     (Proveedor* + CuentasPagar* + Representante* serializers)
│   └── urls.py            (cuentas-pagar y representantes ANTES del prefijo vacío "")
├── services/
│   ├── __init__.py
│   ├── selectors.py       (ProveedorSelector + CuentasPagarSelector + RepresentanteSelector)
│   ├── crud_service.py    (ProveedorCRUDService + RepresentanteCRUDService)
│   ├── business_service.py (ProveedorBS + CuentasPagarBS + RepresentanteBS)
│   └── api_mixins.py      (ProveedorMixin + CuentasPagarMixin + RepresentanteMixin)
├── choices/
│   └── niif_proveedores_choices.py
├── migrations/
│   ├── 0001–0013  (historia Proveedor + CuentaPorPagar + Cartera)
│   ├── 0014       rename_cartera_cuentaspagar_and_more
│   ├── 0015       update_cuentaspagar_verbose_name
│   └── 0018       representante_and_more (v3.17.0)
├── templates/tenant/proveedores/
│   ├── proveedores_list.html
│   │   ├── Subtabs: #subtab-directorio | #subtab-cuentas-pagar | #subtab-representantes
│   │   └── (include) offcanvas_representante_form.html  ← PERMANENTE en DOM
│   ├── assets_proveedores.html    (carga todos los scripts del módulo)
│   ├── offcanvas_form.html        (proveedor crear/editar)
│   ├── offcanvas_cuentas_por_pagar.html
│   ├── offcanvas_representante_form.html  (v3.17.1 — 560px, dos paneles)
│   └── partials/
│       ├── representantes_directory.html  (Tabulator global + "Nuevo Representante")
│       ├── list_representantes.html       (tabla HTML por proveedor, data-attrs)
│       └── assets_representantes.html     (vacío — scripts en assets_proveedores.html)
└── static/proveedores/js/
    ├── proveedores.api.js         (SSoT endpoints proveedor)
    ├── proveedores.utils.js
    ├── proveedores_main.js        (orquestador + initSubtabRedraws con IDs internos)
    ├── proveedores_form.js
    ├── representante.api.js       (SSoT endpoints representante; const w = window CRÍTICO)
    └── features/
        ├── cartera_list.js        (CuentasPagarList namespace, /cuentas-pagar/)
        ├── cartera_editor.js
        ├── representante_list.js  (tabla HTML simple, renderizarTabla con proveedorNombre)
        └── representante_editor.js (abrirFormRepresentante 3 params, modoDirectorio flag)
```

---

## Cambios Históricos

| Versión | Fecha | Cambio |
|---|---|---|
| v3.5.0 | 2026-04-xx | UUID Lookup, DSV, Service Layer, Retenciones |
| v3.6.0 | 2026-05-11 | UI Premium redesign, flexbox footer |
| v3.6.1 | 2026-05-11 | Hard delete + CASCADE DocumentoSoporte |
| v3.10.3 | 2026-05-25 | Imports globales consolidados |
| v3.16.0 | 2026-06-03 | CuentasPagar unificado (CuentaPorPagar + Cartera) |
| v3.16.1 | 2026-06-03 | Rename Cartera → CuentasPagar en cascada (14 archivos) |
| v3.17.0 | 2026-06-10 | Representante model + full CRUD (5 FASES): Modelos + Services + API + Frontend + Docs |
| v3.17.1 | 2026-06-10 | 5 bugs críticos ViewSet + redesign offcanvas + directorio representantes + propagación proveedorNombre |
| **v3.18.0** | **2026-08-26** | **Sincronizacion automatica CuentasPagar al aprobar OrdenCompra (bug real: 0 CxP pese a compras existentes) — campo `orden_compra_uuid` + `OrdenCompraBusinessService._sincronizar_cuenta_por_pagar()`** |

---

## Resumen v3.17.1 (2026-06-10)

### Bugs Corregidos

1. **Double menu en workspace/#proveedores** — `workspace.html` envolvía `proveedores_list.html` en un outer nav-pills duplicado. Eliminado; ahora simple `{% include %}`.

2. **RepresentanteViewSet — 5 bugs de parámetros** — Router plano: DRF no inyecta query params ni URL kwargs como parámetros de método. Todos corregidos leyendo de `request.query_params`, `request.data` y `self.kwargs`.

3. **`representante.api.js` — ReferenceError `w is not defined`** — El IIFE usaba `w.http(...)` sin definir `w`. Fix: `const w = window;` al inicio del closure.

4. **`#offcanvas-representante` no en DOM desde tab Representantes** — El form solo existía dentro del offcanvas de proveedor. Fix: incluido permanentemente en `proveedores_list.html`.

5. **Tabulator doble instancia al recargar desde delete** — `initTable()` creaba segunda instancia sin destruir la primera. Fix: `reloadDirectorio()` llama `table.destroy()` primero.

### Features Completadas

- **Directorio Global Representantes:** Tab "Representantes" en `proveedores_list.html`, Tabulator consolidado, filtro de búsqueda, botón "Nuevo Representante".

- **Offcanvas Redesign (v3.17.1):** 560px, dos paneles de proveedor (select en modo directorio / badge en modo detalle), secciones por categoría, toggle "Encargado Principal", terminología "Encargado".

- **RepresentanteSelector.get_list_por_empresa():** Método nuevo para directorio sin filtro de proveedor.

- **Propagación de proveedorNombre (cadena completa):** `data-proveedor-nombre` → `cargarTabla()` → `renderizarTabla()` → botón edit onclick 3 args → `abrirFormRepresentante()` → badge display.

- **Cross-module reload:** `window.Sintel.DirectorioRepresentantes.reload` expuesto por el inline script del directorio; invocado por `_recargarTabla('')` en el editor.

---

**Última Actualización:** 2026-06-10
**Auditor:** Claude Code
**Status:** PRODUCTION READY v3.17.1
