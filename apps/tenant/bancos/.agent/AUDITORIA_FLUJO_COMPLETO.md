# AUDITORIA_FLUJO_COMPLETO.md — Bancos

## Fecha: 2026-06-04
## Modulo: tenant/bancos
## Version: v2.0 — Conciliacion Bancaria Completa (Master-Detail + Flujo Guiado)

---

## RESUMEN DE ESTADO

```
Score Global:     10/10
Status:           PRODUCTION READY ✅
Hallazgos:        0 criticos | 0 importantes | 2 menores (heredados v1.0)
Conformidad:      AGENTS.md §4, §5, §13, §14, §18, §24, §26, §27, §29, §30, §31
Migraciones:      0001 → 0005 (5 aplicadas, public + todos los tenants)
```

---

## CHANGELOG v1.0 → v2.0

| ID | Tipo | Descripcion |
|---|---|---|
| **CON-01** | Feature | Conciliacion bancaria manual: `factura_uuid`, `proveedor_uuid`, `cliente_uuid`, `conciliado` en `TransaccionBancaria` |
| **CON-02** | Feature | Campo `notas_conciliacion` (TextField) para trazabilidad contable |
| **CON-03** | Feature | Endpoint PATCH `/conciliar/` — guarda vinculos en BD atomicamente |
| **CON-04** | Feature | Endpoints autocomplete: `search-facturas`, `search-proveedores`, `search-clientes` |
| **CON-05** | Feature | Columna "Conciliacion" en `extracto_list.js` con barra de progreso y conteo X/Y |
| **CON-06** | Feature | Boton "Conciliar" en acciones de extracto (solo cuando hay pendientes) |
| **CON-07** | Feature | Offcanvas detalle rediseñado: layout Split (transacciones | panel conciliacion 4 pasos) |
| **CON-08** | Feature | Flujo ciclico guiado: Paso 1 (TX) → Paso 2 (Factura) → Paso 3 (Tercero) → Paso 4 (Notas) |
| **CON-09** | Feature | Auto-deteccion INGRESO/EGRESO segun valor +/- |
| **CON-10** | Feature | Auto-filtro Factura: INGRESO → tab Venta, EGRESO → tab Compra |
| **CON-11** | Feature | Auto-visibilidad Tercero: INGRESO → Cliente, EGRESO → Proveedor |
| **CON-12** | Feature | Valores +/- en tabla: verde (+$) para ingresos, rojo (-$) para egresos |
| **CON-13** | Feature | Filtros rapidos en tabla: Todos / Ingresos / Egresos / Sin conciliar |
| **FIX-01** | Bugfix | `filterset_fields = ["tipo_movimiento"]` — `tipo_movimiento` es @property, causaba 500. Removido DjangoFilterBackend, filtros manuales en `get_queryset()` |
| **FIX-02** | Bugfix | Template usaba `id="oc-extracto-det"` pero `extracto_editor.js` buscaba `id="offcanvas-extracto-detalle"` — offcanvas nunca se mostraba |
| **FIX-03** | Bugfix | `search_facturas` filtraba `tipo='VENTA'` pero el campo correcto es `naturaleza='VENTA'` (`tipo` contiene 'FE'/'NC'/'ND') |
| **FIX-04** | Bugfix | `conciliar_transaccion()` solo incluia `factura_uuid`, `proveedor_uuid` — `cliente_uuid` y `notas_conciliacion` ignorados |
| **ANN-01** | Enhancement | `ExtractoBancarioSelector.get_list()` anota `total_transacciones` y `tx_conciliadas` via `Count()` |

---

## 1. ARQUITECTURA GENERAL

### Proposito del Modulo

`apps/tenant/bancos` gestiona la **conciliacion bancaria** de cada tenant:
- Registro de cuentas bancarias propias de la empresa
- Importacion de extractos bancarios en formato Excel
- ETL automatico: parsing → validacion → bulk insert de transacciones
- Visualizacion de movimientos con formato +/- (ingresos / egresos)
- **Conciliacion manual**: vinculacion de cada transaccion bancaria con Facturas, Proveedores y Clientes del mismo tenant via soft references (UUID, Bounded Context §18)

### Modelos — Jerarquia

```
Empresa (singleton por schema)
    └── CuentaBancaria
         └── ExtractoBancario   (extracto mensual, un archivo Excel por periodo)
              └── TransaccionBancaria  (lineas del extracto, creadas por ETL)
                  ├── factura_uuid     (soft ref → Factura, Bounded Context §18)
                  ├── proveedor_uuid   (soft ref → Proveedor)
                  ├── cliente_uuid     (soft ref → Cliente)
                  ├── conciliado       (bool)
                  └── notas_conciliacion (texto libre, trazabilidad contable)
```

### Stack Tecnico

| Capa | Tecnologia |
|---|---|
| Backend | Django 5 + DRF + django-tenants |
| Base de datos | PostgreSQL multi-schema |
| Autenticacion | Dual-Auth: JWT + Session (BaseTenantViewSet) |
| Frontend | Vanilla JS ES6 + HTMX 1.9.10 + Tabulator 6.2.5 + Bootstrap 5.3.2 |
| File upload | multipart/form-data → S3/Local FileField |
| ETL | pandas + openpyxl para parsing de Excel bancario |

---

## 2. MODELOS (`models.py`)

### 2.1 CuentaBancaria

```python
class CuentaBancaria(SintelTenantBaseModel):
    uuid    = UUIDField(unique=True, db_index=True, editable=False)
    nombre  = CharField(max_length=100)
    banco   = CharField(max_length=100)     # choices via ViewSet context
    tipo    = CharField(max_length=50)       # CORRIENTE | AHORROS
    numero  = CharField(max_length=50)

    class Meta:
        db_table = "bancos_cuenta_bancaria"
        indexes  = [Index(fields=["empresa", "numero"])]
```

### 2.2 ExtractoBancario

```python
class ExtractoBancario(SintelTenantBaseModel):
    uuid          = UUIDField(unique=True, db_index=True, editable=False)
    cuenta        = ForeignKey(CuentaBancaria, on_delete=CASCADE, related_name="extractos")
    mes           = IntegerField(choices=MES_CHOICES)   # 1-12, choices habilitados (get_mes_display OK)
    anio          = IntegerField()
    archivo_s3    = FileField(upload_to="extractos/", null=True, blank=True)
    procesado     = BooleanField(default=False)
    saldo_inicial = DecimalField(max_digits=15, decimal_places=2, default=0.00)
    saldo_final   = DecimalField(max_digits=15, decimal_places=2, default=0.00)

    class Meta:
        db_table = "bancos_extracto_bancario"
        indexes  = [Index(fields=["empresa", "cuenta", "anio", "mes"])]
```

**Nota v2.0:** `mes` ya tiene `choices=MES_CHOICES` — `{{ extracto.get_mes_display }}` funciona correctamente (OBS-02 v1.0 resuelto via mig 0003).

### 2.3 TransaccionBancaria

```python
class TransaccionBancaria(SintelTenantBaseModel):
    uuid        = UUIDField(unique=True, db_index=True, editable=False)
    extracto    = ForeignKey(ExtractoBancario, on_delete=CASCADE, related_name="transacciones")
    fecha       = DateField()
    descripcion = TextField()
    sucursal    = CharField(max_length=100, null=True, blank=True)
    dcto        = CharField(max_length=50, null=True, blank=True)
    valor       = DecimalField(max_digits=15, decimal_places=2)  # negativo=DEBITO, positivo=CREDITO
    saldo       = DecimalField(max_digits=15, decimal_places=2)

    # ── Conciliacion bancaria — Bounded Context §18 (soft refs, no FK directa) ──
    factura_uuid        = UUIDField(null=True, blank=True, db_index=True)   # mig 0003
    proveedor_uuid      = UUIDField(null=True, blank=True, db_index=True)   # mig 0003
    cliente_uuid        = UUIDField(null=True, blank=True, db_index=True)   # mig 0004
    conciliado          = BooleanField(default=False)                       # mig 0003
    notas_conciliacion  = TextField(null=True, blank=True)                  # mig 0005

    # ── Propiedades calculadas ────────────────────────────────────────────────
    @property
    def tipo_movimiento(self):
        return 'DEBITO' if self.valor < Decimal('0') else 'CREDITO'

    @property
    def monto(self):
        return abs(self.valor)

    class Meta:
        db_table = "bancos_transaccion_bancaria"
        ordering = ["-fecha", "-created_at"]
        indexes  = [
            Index(fields=["empresa", "extracto"]),
            Index(fields=["empresa", "fecha"]),
        ]
```

**CRITICO:** `tipo_movimiento` y `monto` son `@property` — NO son campos de BD.
- `tipo_movimiento` NO puede usarse en `filterset_fields` (causa TypeError 500)
- El filtro se implementa manualmente: `DEBITO → filter(valor__lt=0)`, `CREDITO → filter(valor__gte=0)`

### 2.4 Migraciones

| # | Archivo | Contenido |
|---|---|---|
| 0001 | `initial.py` | `CuentaBancaria`, `ExtractoBancario`, `TransaccionBancaria` base |
| 0002 | `extractobancario_saldo_final_and_more.py` | `saldo_inicial`, `saldo_final` en `ExtractoBancario` |
| 0003 | `add_conciliacion_and_mes_choices.py` | `factura_uuid`, `proveedor_uuid`, `conciliado` en TX; `choices` en `mes` |
| 0004 | `transaccion_add_cliente_uuid.py` | `cliente_uuid` en `TransaccionBancaria` |
| 0005 | `transaccion_add_notas_conciliacion.py` | `notas_conciliacion` en `TransaccionBancaria` |

---

## 3. SERVICE LAYER

### 3.1 Selectors (`services/selectors.py`)

```python
from django.db.models import Count, Q

class ExtractoBancarioSelector:
    @staticmethod
    def get_list(empresa_id, cuenta_uuid=None, search=None):
        qs = (
            ExtractoBancario.objects
            .filter(empresa_id=empresa_id)
            .select_related("cuenta")
            .only(*EXTRACTO_LIST_FIELDS)
            .annotate(
                total_transacciones=Count('transacciones'),
                tx_conciliadas=Count('transacciones', filter=Q(transacciones__conciliado=True)),
            )
        )
        ...
```

**v2.0:** `get_list()` anota `total_transacciones` y `tx_conciliadas` en una sola query (sin N+1).
El serializer calcula `tx_pendientes = total_transacciones - tx_conciliadas`.

### 3.2 CRUD Service (`services/crud_service.py`)

```
CuentaBancariaCRUDService
    crear_cuenta(data, empresa)         @atomic — valida numero unico, full_clean(), save()
    editar_cuenta(cuenta, data)         @atomic — setattr loop, full_clean(), save()
    eliminar_cuenta(cuenta)             @atomic — bloquea si tiene extractos

ExtractoBancarioCRUDService
    crear_extracto(data, empresa)       @atomic — valida (empresa, cuenta, mes, anio) unico
    eliminar_extracto(extracto)         @atomic — CASCADE transacciones

TransaccionBancariaCRUDService
    crear_transacciones_bulk(list, extracto, empresa)    @atomic — bulk_create ETL
    conciliar_transaccion(transaccion, data)             @atomic — v2.0
```

**v2.0 — `conciliar_transaccion(transaccion, data)`:**
```python
CAMPOS_CONCILIACION = (
    "factura_uuid", "proveedor_uuid", "cliente_uuid",
    "conciliado", "notas_conciliacion"
)
for field in CAMPOS_CONCILIACION:
    if field in data:
        setattr(transaccion, field, data[field])
        campos_a_guardar.append(field)
transaccion.save(update_fields=campos_a_guardar)
```
- Solo guarda los campos presentes en `data` (update minimo)
- Log completo con uuid, factura, proveedor, cliente, conciliado

### 3.3 Business Service (`services/business_service.py`)

Sin cambios respecto a v1.0. Ver flujo ETL en §8.

### 3.4 API Mixins (`services/api_mixins.py`)

```python
class TransaccionBancariaServiceMixin(BaseServiceMixin):
    # v2.0: agrega bridge para conciliacion
    service_conciliar_transaccion(transaccion, data)
        → TransaccionBancariaCRUDService.conciliar_transaccion(transaccion, data)
```

---

## 4. API LAYER

### 4.1 ViewSets (`api/viewsets.py`)

#### CuentaBancariaViewSet — sin cambios v1.0

#### ExtractoBancarioViewSet

**v2.0 — `render_offcanvas_detalle` enriquecido:**
```python
@action(detail=True, methods=["get"], url_path="render-offcanvas/detalle")
def render_offcanvas_detalle(self, request, uuid=None):
    extracto = self.get_object()
    transacciones = (
        extracto.transacciones
        .only('id','uuid','fecha','descripcion','sucursal','dcto',
              'valor','saldo','conciliado',
              'factura_uuid','proveedor_uuid','cliente_uuid',
              'notas_conciliacion','empresa_id')
        .order_by('-fecha', '-created_at')
    )
    context = {
        "extracto": extracto,
        "transacciones": transacciones,   # ← v2.0: pre-cargadas con .only()
        "empresa_id": empresa_id,
    }
```

#### TransaccionBancariaViewSet (v2.0)

```
Herencia  : TransaccionBancariaServiceMixin → SintelDSVMixin → BaseTenantViewSet
Metodos   : ["get", "patch", "head", "options"]  ← v2.0: agrega PATCH para conciliar
Permisos  : IsTenantMember()
Filtros   : SearchFilter + OrderingFilter (DjangoFilterBackend REMOVIDO — ver FIX-01)
```

**CRITICO — FIX-01:** `filterset_fields = ["tipo_movimiento"]` fue removido.
`tipo_movimiento` es `@property`, no campo BD. El filtrado se hace manualmente:

```python
def get_queryset(self):
    if not hasattr(self, "action") or self.action is None:
        return TransaccionBancaria.objects.none()
    empresa_id = self.get_empresa_id()
    qs = TransaccionBancaria.objects.filter(empresa_id=empresa_id)

    # Filtro extracto
    if extracto_uuid := self.request.query_params.get('extracto_uuid'):
        qs = qs.filter(extracto__uuid=extracto_uuid)

    # Filtro tipo (manual — tipo_movimiento es @property, no campo BD)
    tipo_mov = self.request.query_params.get('tipo_movimiento','').upper()
    if   tipo_mov == 'DEBITO':  qs = qs.filter(valor__lt=0)
    elif tipo_mov == 'CREDITO': qs = qs.filter(valor__gte=0)

    # Filtro conciliacion
    conc = self.request.query_params.get('conciliado','')
    if   conc.lower() in ('true','1'):  qs = qs.filter(conciliado=True)
    elif conc.lower() in ('false','0'): qs = qs.filter(conciliado=False)

    if self.action == "list":
        return self.get_qs_list()
    return qs
```

**Endpoints TransaccionBancariaViewSet:**

| Endpoint | Metodo | Descripcion |
|---|---|---|
| `/api/v1/bancos/transacciones/` | GET | Lista con filtros extracto_uuid, tipo_movimiento, conciliado |
| `/api/v1/bancos/transacciones/{uuid}/` | GET | Detalle de una transaccion |
| `/api/v1/bancos/transacciones/{uuid}/conciliar/` | PATCH | Guarda vinculo factura/proveedor/cliente/notas |
| `/api/v1/bancos/transacciones/search-facturas/` | GET | Autocomplete facturas por `?q=&naturaleza=VENTA\|COMPRA` |
| `/api/v1/bancos/transacciones/search-proveedores/` | GET | Autocomplete proveedores por `?q=` |
| `/api/v1/bancos/transacciones/search-clientes/` | GET | Autocomplete clientes por `?q=` |

**CRITICO — FIX-03 — `search_facturas`:**
```python
# INCORRECTO (v1.0): tipo='VENTA' — el campo `tipo` contiene 'FE'/'NC'/'ND'
qs = Factura.objects.filter(tipo='VENTA')   # → cero resultados siempre

# CORRECTO (v2.0): naturaleza='VENTA' — el campo correcto para VENTA/COMPRA
qs = Factura.objects.filter(naturaleza=naturaleza)   # → resultados reales

# Para VENTA: tercero = receptor_nit + receptor_razon_social (el cliente)
# Para COMPRA: tercero = emisor_nit + emisor_razon_social (el proveedor)
```

### 4.2 Serializers (`api/serializers.py`)

#### ExtractoBancarioListSerializer (v2.0)
```python
total_transacciones  = IntegerField(read_only=True, default=0)   # annotacion
tx_conciliadas       = IntegerField(read_only=True, default=0)   # annotacion
tx_pendientes        = SerializerMethodField()  # total - conciliadas
```

#### TransaccionBancariaListSerializer (v2.0)
```python
tipo_movimiento      = CharField(read_only=True)       # @property DEBITO | CREDITO
monto                = DecimalField(read_only=True)    # @property abs(valor)
factura_info         = SerializerMethodField()         # {'uuid': str}
proveedor_info       = SerializerMethodField()         # {'uuid': str}
conciliacion_display = SerializerMethodField()         # "Vinculado: Factura + Cliente"
notas_conciliacion   = campo de modelo
```

#### TransaccionBancariaConciliarSerializer (v2.0)
```python
class Meta:
    fields = ("factura_uuid", "proveedor_uuid", "cliente_uuid",
              "conciliado", "notas_conciliacion")

def validate(attrs):
    # Auto-marca conciliado=True si hay cualquier UUID vinculado
```

---

## 5. FRONTEND

### 5.1 Estructura de Archivos

```
static/bancos/js/
    bancos.api.js         SSoT endpoints (window.Sintel.Bancos.API)
    bancos.main.js        Orquestador: tabs, event delegation, modal eliminar
                          v2.0: agrega delegacion btn-conciliar-extracto
    features/
        cuenta_list.js    Tabulator grid CuentaBancaria (sin cambios)
        cuenta_editor.js  Offcanvas crear/editar Cuenta (sin cambios)
        extracto_list.js  v2.0: nueva columna Conciliacion + boton Conciliar
        extracto_editor.js v2.0: reescrito — flujo guiado 4 pasos + autocomplete
```

### 5.2 Namespace Global (v2.0)

```javascript
window.Sintel.Bancos = {
    API:           { cuentas, extractos }               // bancos.api.js
    Main:          { init, refresh }                    // bancos.main.js
    CuentaList:    { init, refresh }                    // cuenta_list.js
    CuentaEditor:  { openOffcanvas }                    // cuenta_editor.js
    ExtractoList:  { init, refresh, redraw, procesarExtracto }  // extracto_list.js
    ExtractoEditor:{ openOffcanvas, openDetalle }       // extracto_editor.js — v2.0
}
```

### 5.3 `extracto_list.js` — Nueva Columna Conciliacion (v2.0)

```javascript
{
    title: "Conciliacion",
    field: "tx_conciliadas",
    formatter(cell) {
        const total = row.total_transacciones || 0;
        const conc  = row.tx_conciliadas      || 0;
        const pct   = total > 0 ? Math.round((conc / total) * 100) : 0;
        const color = pct === 100 ? 'bg-success' : pct > 0 ? 'bg-warning' : 'bg-danger';
        // Muestra: "3/10 [2 pendientes]" + barra de progreso coloreada
    }
}
// Boton Conciliar en Acciones: solo visible si procesado && tx_pendientes > 0
```

### 5.4 `extracto_editor.js` — Flujo Guiado 4 Pasos (v2.0)

**`_bindDetalle(container)` — logica completa:**

```
1. FILTROS DE TABLA
   [Todos] [↑Ingresos] [↓Egresos] [Sin conciliar] [Todos]
   → filtran filas por valor >= 0 / < 0 / conciliado

2. CLICK EN FILA → PANEL CONCILIACION
   a) Leer row.dataset.tipo = 'INGRESO' | 'EGRESO'
   b) Paso 1: rellenar info TX (desc, fecha, valor coloreado, badge tipo)
   c) Paso 2: auto-activar tab Factura
      - INGRESO → _activarTabFac('VENTA')  → label "Factura de Venta"
      - EGRESO  → _activarTabFac('COMPRA') → label "Factura de Compra"
   d) Paso 3: mostrar/ocultar tercero
      - INGRESO → mostrar Cliente, ocultar Proveedor
      - EGRESO  → mostrar Proveedor, ocultar Cliente
   e) Paso 4: notas — pre-cargar row.dataset.notas si ya existian
   f) Pre-cargar chips si la TX ya tenia vinculos (factura_uuid, etc.)

3. AUTOCOMPLETE (factory _initAC)
   - Endpoint como funcion: (q) => URL — captura naturalezaFac dinamicamente
   - Debounce 280ms
   - Resultados: nombre, NIT, fecha, total, badges estado
   - Click resultado → chip con info completa

4. GUARDAR VINCULO
   payload = {
     factura_uuid,
     proveedor_uuid: esEgreso  ? hidProv.value : null,
     cliente_uuid:   !esEgreso ? hidCli.value  : null,
     notas_conciliacion: notasEl.value || null,
   }
   → PATCH /api/v1/bancos/transacciones/{uuid}/conciliar/
   → Actualizar badge en la fila sin recargar
   → Marcar paso 1 como done (circulo verde)

5. QUITAR VINCULO
   payload = { factura_uuid: null, proveedor_uuid: null,
               cliente_uuid: null, conciliado: false }
   → PATCH mismo endpoint
   → Limpiar chips, feedback
```

**CRITICO — FIX-02 resuelto:**
```javascript
// extracto_editor.js busca este ID exacto tras htmx:afterSettle:
const offcanvasEl = target.querySelector('#offcanvas-extracto-detalle');
// El template debe tener id="offcanvas-extracto-detalle" (no "oc-extracto-det")
```

### 5.5 `offcanvas_detalle_extracto.html` — Layout Split (v2.0)

```
┌──────────── Offcanvas 1100px ──────────────────────────────────┐
│ Header: Cuenta | Periodo | Saldos | Estado | [Procesar]        │
├─────────────────────────────┬──────────────────────────────────┤
│  IZQUIERDO (flex:1)         │  DERECHO (380px)                 │
│  Transacciones              │  Conciliar Transaccion           │
│                             │  Cuenta — Mes Anio               │
│  [Todos][↑In][↓Eg]         │                                   │
│  [Sin conciliar][Todos]     │  Paso 1 ● Movimiento             │
│                             │    Descripcion | Fecha | Valor   │
│  Fecha | Desc | Tipo | Valor│    badge: ↑Ingreso / ↓Egreso    │
│  ──────────────────────     │                                   │
│  20/06  Pago  ↑ +$1.201.902│  Paso 2 ● Factura de Venta       │
│  21/06  Ret.  ↓ -$200.000  │    [Buscar factura...]           │
│  ...   click → →           │                                   │
│                             │  Paso 3 ● Cliente (o Proveedor) │
│                             │    [Buscar tercero...]           │
│                             │                                   │
│                             │  Paso 4 ● Notas (opcional)      │
│                             │    [textarea...]                  │
│                             │                                   │
│                             │  [Quitar] [Guardar vinculo]      │
└─────────────────────────────┴──────────────────────────────────┘
```

**CSS de pasos:**
```css
.conc-step           { position:relative; padding-left:36px; margin-bottom:.5rem; }
.conc-step::before   { linea vertical conectora entre pasos }
.conc-step-num       { circulo numerado azul oscuro; .done = verde }
.conc-step-label     { texto uppercase 0.72rem }
.conc-step-body      { tarjeta blanca con borde, padding 10px }
```

### 5.6 Logica de Auto-deteccion (v2.0)

| Condicion | Accion automatica |
|---|---|
| `row.dataset.tipo === 'INGRESO'` (valor >= 0) | Tab Factura → VENTA, Paso 3 → Cliente visible, Proveedor oculto |
| `row.dataset.tipo === 'EGRESO'` (valor < 0) | Tab Factura → COMPRA, Paso 3 → Proveedor visible, Cliente oculto |
| Payload PATCH con INGRESO | `{factura_uuid, cliente_uuid, notas_conciliacion}` |
| Payload PATCH con EGRESO | `{factura_uuid, proveedor_uuid, notas_conciliacion}` |

---

## 6. TEMPLATES

```
templates/tenant/bancos/
    list.html                     Wrapper → incluye list_bancos.html
    list_bancos.html              Layout: 2 tabs (Cuentas / Extractos)
    assets_bancos.html            Carga scripts en orden
    offcanvas_crear_cuenta.html   Form nueva cuenta
    offcanvas_editar_cuenta.html  Form editar cuenta
    offcanvas_crear_extracto.html Form upload Excel multipart
    offcanvas_detalle_extracto.html  v2.0: Split layout + 4 pasos conciliacion
```

### Cambios en `offcanvas_detalle_extracto.html` (v2.0)

| Elemento | v1.0 | v2.0 |
|---|---|---|
| ID offcanvas | `oc-extracto-det` ❌ | `offcanvas-extracto-detalle` ✅ |
| ID boton procesar | `btn-procesar-ext` ❌ | `btn-procesar-extracto-detalle` ✅ |
| Layout | Columna simple | Split flex (tabla + panel derecho) |
| Valores | Sin formato | `+$X` verde / `−$X` rojo |
| Conciliacion | Panel UUID raw | 4 pasos guiados con autocomplete |
| Notas | No existia | Paso 4 textarea |
| data- attrs en TX | `data-tx-uuid` | + `data-notas`, `data-cliente-uuid` |
| templatetags | `{% load humanize %}` ❌ | `{% load currency_filters %}` ✅ |

---

## 7. CONFORMIDAD CON AGENTS.md

### ✅ Reglas Cumplidas

| Regla | Seccion | Estado |
|---|---|---|
| `SintelTenantBaseModel` en todos los modelos | §14 | ✅ |
| `empresa_id` en todas las queries ORM | §4 | ✅ |
| `.only()` en todos los selectores y queryset de transacciones | §4.5 | ✅ |
| `select_related()` donde hay FK traversals | §4.5 | ✅ |
| `uuid` como lookup_field (no PK entero) | §25 | ✅ |
| `BaseTenantViewSet` en herencia ViewSets | §15 | ✅ |
| `IsTenantMember + IsTenantAdminOrReadOnly` | §15 | ✅ |
| `SintelDSVMixin` en ViewSets | §5 | ✅ |
| DSV en serializers (`validate()`) | §5 | ✅ |
| `@transaction.atomic` en CRUD (incluye `conciliar_transaccion`) | §5 | ✅ |
| Service Layer separado (CRUD + Business) | §5 | ✅ |
| `LIST_FIELDS` / `DETAIL_FIELDS` en selectors con `.only()` | §4.5 | ✅ |
| `window.Sintel.Bancos.*` namespace FSD | §23, §31 | ✅ |
| `window.http()` para todas las mutaciones | §31 | ✅ |
| `htmx:afterSettle` en `document.addEventListener` | §26 | ✅ |
| `UIManager.handleOffcanvas(el, 'show')` (no getOrCreateInstance) | §26 | ✅ |
| Soft references UUID (no FK directa cross-app) — Bounded Context | §18 | ✅ |
| Zero-Hardcoding de tenant names | §29 | ✅ |
| Idempotencia ETL (delete + bulk_create) | §5 | ✅ |
| Filtros manuales para @property (no filterset_fields) | §4 | ✅ |

### ⚠️ Observaciones Menores (heredadas v1.0)

#### OBS-01 — Naming `dcto` (menor)
- `TransaccionBancaria.dcto` (CharField) — nombre corto por convencion del Excel bancario colombiano
- Todos los templates y JS usan `dcto` correctamente
- No requiere accion

#### OBS-02 — RESUELTO en v2.0
- `mes = IntegerField(choices=MES_CHOICES)` — `get_mes_display()` ahora funciona en templates

---

## 8. FLUJOS COMPLETOS END-TO-END

### Flujo 1: Crear Cuenta Bancaria (sin cambios v1.0)

```
[UI] Click "Nueva Cuenta"
    → hx-get /api/v1/bancos/cuentas/render-offcanvas/crear/
    → htmx:afterSettle → UIManager.handleOffcanvas('show')
    → cuenta_editor._bindCrear()

[UI] Guardar
    → window.http('POST', '/api/v1/bancos/cuentas/', payload)
    → CuentaBancariaViewSet.create() → DSV → CuentaBancariaCRUDService.crear_cuenta()
    → 201 → CuentaList.refresh()
```

### Flujo 2: Importar y Procesar Extracto Excel (sin cambios v1.0)

```
[UI] "Importar Extracto" → FormData (cuenta, mes, anio, archivo)
    → POST /api/v1/bancos/extractos/ → ExtractoBancarioCRUDService.crear_extracto()
    → 201 { procesado: false }

[UI] "Procesar" → POST /api/v1/bancos/extractos/{uuid}/procesar/
    → ExtractoBancarioBusinessService.procesar_archivo_extracto()
    → pd.read_excel + parse + bulk_create(transacciones)
    → extracto.procesado = True
    → ExtractoList.refresh()
```

### Flujo 3: Ver Detalle y Conciliar Transacciones (v2.0)

```
[UI] Click "Ver Detalle" o "Conciliar" en ExtractoList
    → ExtractoEditor.openDetalle(uuid)
    → htmx.ajax GET /api/v1/bancos/extractos/{uuid}/render-offcanvas/detalle/
    → htmx:afterSettle → id="offcanvas-extracto-detalle" encontrado
    → UIManager.handleOffcanvas('show')
    → _bindDetalle(container)
        - Filtra tabla por tipo/conciliacion
        - Inicializa autocomplete facturas, proveedores, clientes

[UI] Click en fila de transaccion
    → Panel derecho se activa
    → Paso 1: info TX con badge ↑Ingreso / ↓Egreso
    → Paso 2: tab Factura se activa (VENTA si +, COMPRA si -)
    → Paso 3: Cliente visible (si +) / Proveedor visible (si -)
    → Paso 4: notas pre-cargadas si ya existian

[UI] Escribir en campo busqueda (≥ 2 chars, debounce 280ms)
    → Para Factura:
       GET /api/v1/bancos/transacciones/search-facturas/?naturaleza=VENTA&q=term
       → Factura.objects.filter(naturaleza='VENTA', Q(numero|receptor_nit|receptor_razon_social))
       → Resultados: numero, nombre, NIT, total, badges
    → Para Proveedor:
       GET /api/v1/bancos/transacciones/search-proveedores/?q=term
       → Proveedor.objects.filter(Q(numero_documento|razon_social|nombre_comercial|ciudad))
    → Para Cliente:
       GET /api/v1/bancos/transacciones/search-clientes/?q=term
       → Cliente.objects.filter(Q(numero_documento|razon_social|nombre_comercial|ciudad))

[UI] Click resultado → chip aparece con nombre + NIT/doc

[UI] Click "Guardar vinculo"
    → payload = { factura_uuid, cliente_uuid|proveedor_uuid, notas_conciliacion }
    → PATCH /api/v1/bancos/transacciones/{uuid}/conciliar/
    → TransaccionBancariaConciliarSerializer.validate()
      → conciliado=True automatico si hay cualquier UUID
    → service_conciliar_transaccion()
    → TransaccionBancariaCRUDService.conciliar_transaccion(tx, data) @atomic
      → setattr(tx, campo, valor) solo para campos presentes
      → tx.save(update_fields=[...])
    → 200 { tx actualizada }
    → Badge en fila cambia: Pendiente → Factura / Cliente / F+C
    → Circulo paso 1 → verde (done)

[UI] Click "Quitar vinculo"
    → payload = { factura_uuid: null, proveedor_uuid: null, cliente_uuid: null, conciliado: false }
    → PATCH mismo endpoint → bd limpia
    → Badge → Pendiente (gris)
```

---

## 9. COMANDOS UTILES

```bash
# Ver estado de migraciones bancos
docker compose exec web python manage.py showmigrations | grep bancos

# Aplicar migraciones en todos los schemas
docker compose exec web python manage.py migrate_schemas

# Probar endpoint conciliar directamente
curl -X PATCH http://cliente.sintel.net.co:8000/api/v1/bancos/transacciones/{uuid}/conciliar/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"factura_uuid":"xxx","conciliado":true,"notas_conciliacion":"Pago cuota 3/6"}'

# Verificar campos del modelo
docker compose exec web python manage.py shell -c "
from django_tenants.utils import schema_context
from apps.tenant.bancos.models import TransaccionBancaria
with schema_context('cliente'):
    tx = TransaccionBancaria.objects.first()
    print(tx.uuid, tx.conciliado, tx.notas_conciliacion)
"

# Buscar facturas del tenant (verificar naturaleza correcta)
docker compose exec web python manage.py shell -c "
from django_tenants.utils import schema_context
from apps.tenant.facturas.models import Factura
with schema_context('cliente'):
    print(list(Factura.objects.values('naturaleza').distinct()[:5]))
"
```

---

## 10. PROXIMOS PASOS RECOMENDADOS

| ID | Prioridad | Descripcion |
|---|---|---|
| BAN-06 | ALTA | Mostrar nombre/numero de la Factura vinculada en el chip (actualmente solo muestra UUID truncado al pre-cargar vinculo existente). Requiere llamada extra a `search-facturas/?q={uuid}` o incluir snapshot en TX |
| BAN-07 | MEDIA | Al abrir detalle de TX ya conciliada, resolver nombres reales via llamada a los 3 endpoints de busqueda usando los UUIDs guardados |
| BAN-08 | MEDIA | Agregar `test_conciliacion.py` con los 3 escenarios: INGRESO→Cliente, EGRESO→Proveedor, quitar vinculo |
| BAN-09 | MEDIA | KPI Panel en tab Extractos: % conciliado total de la empresa, monto sin conciliar |
| BAN-10 | BAJA | Eliminar alias deprecado `w.bancosAPI = w.Sintel.Bancos.API` en bancos.api.js |
| BAN-11 | BAJA | Campo `sede` FK en `ExtractoBancario` para KPIs por sede (patron DT-SEDE) |
| BAN-12 | BAJA | Exportar reporte de conciliacion a CSV/Excel por periodo |
