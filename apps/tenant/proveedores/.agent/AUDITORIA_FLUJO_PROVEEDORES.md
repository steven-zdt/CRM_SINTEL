# [PORTAL] Auditoría y SSoT: Módulo Proveedores

**Versión:** 3.16.1 (CuentasPagar unificado + Cartera → CuentasPagar rename)
**Estado:** PRODUCTION READY
**Ubicación:** `apps/tenant/proveedores/`
**Última Auditoría:** 2026-06-03
**Última Actualización:** 2026-06-03

---

## Responsabilidades del Módulo

1. **Gestión de Directorio:** Catálogo de acreedores bajo conformidad fiscal colombiana (NIT, régimen, CIIU)
2. **Normativa Tributaria:** Retenciones (retefuente, reteica, reteiva), gran contribuyente, autoretenedor
3. **Aislamiento Multi-tenant:** empresa_id en todas las queries, IDOR prevention via DSV
4. **Cuentas por Pagar:** Registro y seguimiento de deudas a proveedores por factura
5. **UUID Lookup Field (AGENTS.md §25):** Prevención de enumeration attacks
6. **Double Semantic Verification (AGENTS.md §13):** Protección IDOR en mutaciones

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

### CuentasPagar ⭐ NUEVO (v3.16.0 — Unifica CuentaPorPagar + Cartera)

```
CuentasPagar(SintelTenantBaseModel)
├── uuid              UUIDField unique, db_index
├── empresa           FK → Empresa (PROTECT, related_name="carteras")
├── proveedor         FK → Proveedor (CASCADE, related_name="carteras")
├── numero_factura    CharField — número de factura de compra
├── factura_uuid      UUIDField null/blank — soft reference Factura (sin FK directa)
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

# CuentasPagar (unificado)
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
```

### CRUD Service (`services/crud_service.py`)

```python
class ProveedorCRUDService:
    create(empresa_id, data)          @atomic
    update(proveedor, data)           @atomic
    delete(proveedor)                 @atomic  # hard delete + CASCADE gastos
    update_or_create(empresa_id, data) @atomic
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

class CuentasPagarBusinessService:         # NUEVO v3.16.0
    registrar_cartera(proveedor, numero_factura, fecha_emision,
                      fecha_vencimiento, valor_total, ...)
        → get_or_create idempotente por (empresa, proveedor, numero_factura)
    registrar_abono(cartera_uuid, monto, observaciones, empresa_id)
        → select_for_update() + cartera.valor_pagado += monto + save()
        → save() auto-recalcula saldo y estado_pago
```

### API Mixins (`services/api_mixins.py`)

```python
class ProveedorServiceMixin(BaseServiceMixin):
    selector_class     = ProveedorSelector
    business_service_class = ProveedorBusinessService
    crud_service_class = ProveedorCRUDService
    # métodos: service_crear_proveedor, service_actualizar_proveedor,
    #           service_obtener_snapshot, get_qs_list, get_qs_detail

class CuentasPagarServiceMixin:            # NUEVO v3.16.0
    @property cuentas_pagar_selector → CuentasPagarSelector()
    @property cuentas_pagar_service  → CuentasPagarBusinessService()
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
| `/api/v1/proveedores/{uuid}/render-offcanvas/crear/` | GET | HTML crear | TemplateHTML |
| `/api/v1/proveedores/{uuid}/render-offcanvas/editar/` | GET | HTML editar | TemplateHTML |
| **`/api/v1/proveedores/cuentas-pagar/`** | GET | Listar CuentasPagar | CuentasPagarListSerializer |
| **`/api/v1/proveedores/cuentas-pagar/`** | POST | Registrar obligación | — |
| **`/api/v1/proveedores/cuentas-pagar/{uuid}/`** | GET | Detalle CxP | CuentasPagarDetailSerializer |
| **`/api/v1/proveedores/cuentas-pagar/{uuid}/registrar-abono/`** | POST | Registrar pago | CuentasPagarAbonoSerializer |
| **`/api/v1/proveedores/cuentas-pagar/render-offcanvas/`** | GET | HTML gestión | TemplateHTML |

**Orden crítico en urls.py:** `cuentas-pagar` y cualquier prefijo con nombre ANTES del prefijo vacío `""` de ProveedorViewSet. Si el prefijo vacío va primero, interpreta `cuentas-pagar` como UUID del Proveedor → ValidationError.

### Serializers

```python
ProveedorListSerializer          → lista Tabulator (cartera_resumen inline)
ProveedorDetailSerializer        → crear/editar proveedor
CuentasPagarListSerializer       → Tabulator CxP (proveedor_razon_social denormalizado)
CuentasPagarDetailSerializer     → detalle + factura_detalle via FacturaInterAppAPI
CuentasPagarAbonoSerializer      → entrada para POST registrar-abono (monto, observaciones)
```

---

## Frontend

### Templates

```
templates/tenant/proveedores/
├── proveedores_list.html     Tabs: Directorio | Cuentas por Pagar / Cartera
├── assets_proveedores.html   Carga scripts en orden correcto
├── offcanvas_form.html       Crear/editar Proveedor (premium, flexbox footer)
├── offcanvas_cuentas_por_pagar.html   Gestión CxP (abono)
└── offcanvas_cartera.html    (legacy — puede eliminarse)
```

### JavaScript (`static/proveedores/js/`)

```
proveedores.api.js           SSoT de endpoints REST
proveedores.utils.js         Utilidades comunes
proveedores_form.js          Editor Proveedor (HTMX + retenciones)
proveedores_main.js          Orquestador: Tabulator + tab switching + event delegation
features/
    cartera_list.js          Tabulator CuentasPagar
                             Namespace: window.Sintel.Proveedores.CuentasPagarList
                             API_URL: /api/v1/proveedores/cuentas-pagar/
                             init() SOLO desde shown.bs.tab (no auto-init en page-load)
    cartera_editor.js        Editor abono/crear CxP
```

**Patrón de inicialización de tabs (skill: tabulator.md §6):**
```javascript
// proveedores_main.js — shown.bs.tab
tabCartera.addEventListener('shown.bs.tab', () => {
    const list = w.Sintel?.Proveedores?.CuentasPagarList;
    if (list?.init) list.init();         // crea tabla si no existe
    requestAnimationFrame(() => {
        w.SintelProveedoresTables?.cartera?.redraw(true);  // recalcula anchos
    });
});
```

**Regla anti-spinner:** Spinners de tabs inactivos arrancan con `style="display:none;"`. El JS los muestra al init. Si se arrancan visibles y el init falla, el spinner queda congelado.

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

POST /api/v1/proveedores/cuentas-pagar/
    ↓ CuentasPagarViewSet.create()
    ↓ DSV: proveedor.empresa_id == empresa_id
    ↓ CuentasPagarBusinessService.registrar_cartera()
       → get_or_create(empresa, proveedor, numero_factura)  ← idempotente
    ↓ 201 Created

POST /api/v1/proveedores/cuentas-pagar/{uuid}/registrar-abono/
    ↓ CuentasPagarViewSet.registrar_abono()
    ↓ CuentasPagarBusinessService.registrar_abono()
       → select_for_update()
       → cxp.valor_pagado += monto
       → cxp.save()  ← auto-recalcula saldo y estado_pago
    ↓ 200 OK + CuentasPagarDetailSerializer
```

---

## Conformidad AGENTS.md (v3.16.1)

| Regla | Estado |
|---|---|
| §4 Zero Waste `.only()` | ✅ LIST_FIELDS/DETAIL_FIELDS en todos los selectores |
| §5 Service Layer unidireccional | ✅ ViewSet → Mixin → BusinessService → CRUDService |
| §13 IDOR Prevention DSV | ✅ empresa_id en todas las queries + DSV en mutations |
| §14/§25 UUID Lookup | ✅ `lookup_field="uuid"` en ambos ViewSets |
| §17 Bridge Isolation | ✅ Sin imports directos de apps.public |
| §18 Bounded Context Facturas | ✅ factura_uuid soft reference, FacturaInterAppAPI para leer |
| §22 CSS Isolation | ✅ Templates sin CSS cross-app |
| §23 JS Isolation | ✅ `window.Sintel.Proveedores` namespace |
| §26 Anti-Backdrop Offcanvas | ✅ UIManager.handleOffcanvas() + dispose() en fallback |
| §27 UUID sin parseInt | ✅ No hay parseInt sobre UUIDs de FK |
| §30 Zero-Collision selectors | ✅ Traversals en _*_TRAVERSALS, no en FIELD constants |
| §31 SSoT Frontend skills | ✅ Consultar .agents/skills/frontend/ antes de UI changes |

---

## Estructura Física

```
apps/tenant/proveedores/
├── models.py
│   ├── Proveedor          (directorio acreedores, normativa colombiana)
│   └── CuentasPagar       (v3.16.0 — unificación CuentaPorPagar + Cartera)
├── api/
│   ├── viewsets.py        (ProveedorViewSet + CuentasPagarViewSet)
│   ├── serializers.py     (Proveedor* + CuentasPagar* serializers)
│   └── urls.py            (cuentas-pagar ANTES del prefijo vacío "")
├── services/
│   ├── __init__.py
│   ├── selectors.py       (ProveedorSelector + CuentasPagarSelector)
│   ├── crud_service.py    (ProveedorCRUDService)
│   ├── business_service.py (ProveedorBusinessService + CuentasPagarBusinessService)
│   └── api_mixins.py      (ProveedorServiceMixin + CuentasPagarServiceMixin)
├── choices/
│   └── niif_proveedores_choices.py
├── migrations/
│   ├── 0001–0010  (historia Proveedor + CuentaPorPagar legacy)
│   ├── 0011       recreate_cuentaporpagar
│   ├── 0012       add_cartera_model (modelo unificado)
│   ├── 0013       remove_cuentaporpagar_unify_cartera
│   ├── 0014       rename_cartera_cuentaspagar_and_more ← rename model
│   └── 0015       update_cuentaspagar_verbose_name
├── templates/tenant/proveedores/
│   ├── proveedores_list.html  (tabs: Directorio | CxP/Cartera)
│   ├── assets_proveedores.html
│   ├── offcanvas_form.html    (proveedor crear/editar)
│   └── offcanvas_cuentas_por_pagar.html
└── static/proveedores/js/
    ├── proveedores.api.js
    ├── proveedores.utils.js
    ├── proveedores_main.js
    ├── proveedores_form.js
    └── features/
        ├── cartera_list.js    (CuentasPagarList namespace, API /cuentas-pagar/)
        └── cartera_editor.js
```

---

## Cambios Históricos Resumidos

| Versión | Fecha | Cambio |
|---|---|---|
| v3.5.0 | 2026-04-xx | UUID Lookup, DSV, Service Layer, Retenciones |
| v3.6.0 | 2026-05-11 | UI Premium redesign, flexbox footer |
| v3.6.1 | 2026-05-11 | Hard delete + CASCADE DocumentoSoporte |
| v3.10.3 | 2026-05-25 | Imports globales consolidados |
| **v3.16.0** | **2026-06-03** | **CuentasPagar unificado (CuentaPorPagar + Cartera fusionados)** |
| **v3.16.1** | **2026-06-03** | **Rename Cartera → CuentasPagar en cascada (14 archivos)** |

---

**Última Actualización:** 2026-06-03
**Auditor:** Claude Code
**Status:** PRODUCTION READY v3.16.1
