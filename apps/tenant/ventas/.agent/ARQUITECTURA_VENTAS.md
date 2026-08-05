# Auditoria Flujo Completo — Modulo Ventas

**Version auditada:** v3.17.0
**Fecha:** 2026-06-18
**Estado:** PRODUCTION READY (0 criticos)
**Ubicacion:** `apps/tenant/ventas/`
**App Label:** `tenant_ventas`
**Auditor:** Claude Sonnet 4.6

---

## 1. Responsabilidades del Modulo

| # | Responsabilidad | Estado |
|---|----------------|--------|
| 1 | **Registro Comercial** — `Venta` como master record antes y despues de la emision DIAN | OK |
| 2 | **Resolucion DIAN** — `ResolucionFacturacion` gestiona rangos autorizados; asignacion atomica de consecutivos via `select_for_update()` | OK |
| 3 | **Maquina de Estados** — `BORRADOR → FACTURADA_DIAN → ANULADA` con transiciones controladas | OK |
| 4 | **Integracion DIAN UBL 2.1** — `procesar_y_facturar_venta()` genera DTO canonico, CUFE, XML, firma XAdES y delega creacion de `Factura` a `FacturaBusinessService` | OK |
| 5 | **Desacoplamiento Contable** — Ventas nunca toca `AsientoContable` ni `MovimientoContable`; Contabilidad extrae via Pull Model desde `Factura` | OK |
| 6 | **Double Semantic Verification (DSV)** — Cada FK a `Cliente`, `Proyecto`, `Producto`, `Servicio`, `ResolucionFacturacion` verificada contra `empresa_id` antes de persistir | OK |
| 7 | **Items dinamicos** — `ItemVenta` con subtotales calculados en tiempo real (JS) y al persistir (`ItemVenta.save()`) | OK |
| 8 | **UUID Lookup** — `lookup_field = 'uuid'` en `VentaViewSet` y `ResolucionFacturacionViewSet`; nunca se exponen PKs enteros en URLs | OK |
| 9 | **Anti-Zombie Tabulator** — `venta_list.js` destruye instancia previa al re-montar via HTMX | OK |
| 10 | **Anti-Backdrop Bootstrap** — `mostrarOffcanvasSeguro()` elimina backdrops huerfanos antes de abrir offcanvas | OK |
| 11 | **Zero parseInt() sobre UUIDs** — `capturarClienteUUID()` usa `getAttribute('data-uuid')` del `<option>` | OK |

---

## 2. Modelos (`models.py`)

**App Label:** `tenant_ventas`
**Migraciones:** `0001_init_ventas.py`, `0002_rewrite_venta_v2.py`, `0003_venta_numero_factura_resolucionfacturacion_and_more.py`

---

### 2.1 `ResolucionFacturacion` (nuevo en v3.17.0)

**Herencia:** `SintelTenantBaseModel` ✅
**Tabla:** `tenant_ventas_resolucionfacturacion`
**Ordering:** `['-vigente', '-fecha_resolucion']`

Controla el rango de consecutivos autorizados por la DIAN para emitir facturas.

#### Campos

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `default=uuid4, unique=True, db_index=True, editable=False` |
| `numero_resolucion` | CharField(50) | `db_index=True` — numero oficial DIAN |
| `prefijo` | CharField(10) | `blank=True` — Ej: `SETP`, `FE`, `PV` |
| `tipo` | CharField(10) | `TipoDocumento.choices`: `FE / POS / PAPEL`, `default=FE`, `db_index=True` |
| `fecha_resolucion` | DateField | Fecha de emision de la resolucion por la DIAN |
| `fecha_desde` | DateField | `default=date.today` — inicio de vigencia |
| `fecha_hasta` | DateField | Vencimiento de la resolucion |
| `rango_desde` | IntegerField | `MinValueValidator(1)` |
| `rango_hasta` | IntegerField | `MinValueValidator(1)` |
| `consecutivo_actual` | IntegerField | `db_index=True, default=1` — proximo a asignar |
| `vigente` | BooleanField | `db_index=True, default=True` |

#### Indices BD

```python
indexes = [
    Index(fields=['empresa', 'vigente']),
    Index(fields=['empresa', 'tipo']),
]
```

#### Metodos del modelo

| Metodo | Descripcion |
|--------|-------------|
| `formar_numero()` | Retorna `"{prefijo}{consecutivo_actual}"` o solo el consecutivo si no hay prefijo |
| `esta_en_rango()` | `consecutivo_actual <= rango_hasta` |
| `esta_vigente_en_fecha(fecha_ref=None)` | `fecha_desde <= fecha_ref <= fecha_hasta` |
| `clean()` | Valida `rango_desde <= rango_hasta` — solo nivel Python (sin `CheckConstraint` DB) |

> **Atencion:** `clean()` no se ejecuta automaticamente en `bulk_create()` o inserciones ORM directas. Se recomienda agregar `CheckConstraint(Q(rango_hasta__gte=F('rango_desde')))` en una futura migracion.

---

### 2.2 `Venta`

**Herencia:** `SintelTenantBaseModel` ✅
**Tabla:** `tenant_ventas_venta`
**Ordering:** `['-created_at']`

#### Campos de Identificacion

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `default=uuid4, unique=True, db_index=True, editable=False` |
| `estado` | CharField(16) | Choices: `BORRADOR / FACTURADA_DIAN / ANULADA`, `default=BORRADOR`, `db_index=True` |
| `numero_factura` | CharField(50) | `null=True, blank=True, db_index=True` — asignado por la resolucion al facturar (Ej: `FE1001`) |

#### Relaciones

| Campo | Tipo | Notas |
|-------|------|-------|
| `cliente` | FK → `tenant_clientes.Cliente` | `PROTECT`, `related_name='ventas'` — SSoT DSV al crear |
| `proyecto` | FK → `tenant_proyectos.Proyecto` | `SET_NULL, null=True, blank=True`, `related_name='ventas'` — opcional |
| `resolucion` | FK → `ResolucionFacturacion` | `PROTECT, null=True, blank=True`, `related_name='ventas_asociadas'` — resolucion DIAN usada al facturar |
| `factura_asociada` | OneToOneField → `facturas.Factura` | `SET_NULL, null=True, blank=True`, `related_name='venta_origen'` — asignado en `vincular_factura()` |

#### Campos Temporales

| Campo | Tipo | Notas |
|-------|------|-------|
| `fecha_emision` | DateField | Requerido |
| `fecha_vencimiento` | DateField | `null=True, blank=True` |

#### Campos Financieros

| Campo | Tipo | Notas |
|-------|------|-------|
| `subtotal` | DecimalField(16,2) | `default=Decimal('0.00')` — calculado por `VentaCRUDService` |
| `impuestos` | DecimalField(16,2) | `default=Decimal('0.00')` — IVA total de items |
| `total_neto` | DecimalField(16,2) | `default=Decimal('0.00')` — `subtotal + impuestos` |
| `observaciones` | TextField | `blank=True` |

#### Indices BD

```python
indexes = [
    Index(fields=['empresa', 'estado']),
    Index(fields=['empresa', 'cliente']),
    Index(fields=['empresa', '-created_at']),
    Index(fields=['empresa', 'resolucion']),   # nuevo en 0003
]
```

#### Constraints

```python
constraints = [
    CheckConstraint(check=Q(subtotal__gte=Decimal('0.00')), name='ventas_venta_subtotal_gte_cero'),
    CheckConstraint(check=Q(total_neto__gte=Decimal('0.00')), name='ventas_venta_total_neto_gte_cero'),
]
```

---

### 2.3 `ItemVenta`

**Herencia:** `SintelTenantBaseModel` ✅
**Tabla:** `tenant_ventas_itemventa`
**Ordering:** `['id']`

| Campo | Tipo | Notas |
|-------|------|-------|
| `venta` | FK → `Venta` | `CASCADE, related_name='items'` |
| `producto` | FK → `tenant_inventario.Producto` | `PROTECT, null=True, blank=True`, `related_name='items_venta'` |
| `servicio` | FK → `tenant_inventario.Servicio` | `PROTECT, null=True, blank=True`, `related_name='items_venta'` |
| `descripcion` | CharField(500) | Snapshot de texto (no FK dependiente) |
| `cantidad` | DecimalField(12,4) | `default=Decimal('1.0000')` |
| `precio_unitario` | DecimalField(16,2) | Requerido |
| `porcentaje_iva` | DecimalField(5,2) | `default=Decimal('0.00')` — opciones: 0%, 5%, 19% |
| `subtotal` | DecimalField(16,2) | `default=Decimal('0.00')` — calculado en `save()` |

**Indice BD:** `(empresa, venta)`

**`save()` override:**
```python
def save(self, *args, **kwargs):
    cant = self.cantidad or Decimal("0")
    pu = self.precio_unitario or Decimal("0")
    self.subtotal = cant * pu
    if not self.empresa_id and self.venta_id:
        eid = Venta.objects.filter(id=self.venta_id).values_list('empresa_id', flat=True).first()
        if eid:
            self.empresa_id = eid
    super().save(*args, **kwargs)
```

---

## 3. Maquina de Estados

```
BORRADOR
   │
   ├─── [procesar_y_facturar_venta()]  ──→  FACTURADA_DIAN  (inmutable)
   │     (requiere ResolucionFacturacion vigente + en rango)
   │
   └─── [anular_venta()]  ──────────────→  ANULADA  (solo desde BORRADOR)

FACTURADA_DIAN  ──  NO se puede anular directamente  ──  emitir Nota Credito
```

**Reglas de transicion (en `VentaCRUDService`):**
- `actualizar_venta()`: solo ejecuta si `estado == BORRADOR`
- `anular_venta()`: lanza `ValueError` si `estado == FACTURADA_DIAN`
- `vincular_factura()`: asigna `factura_asociada` y cambia estado a `FACTURADA_DIAN`

**Precondicion para facturar:**
- `ResolucionFacturacion.vigente == True`
- `esta_vigente_en_fecha()` — `fecha_desde <= today <= fecha_hasta`
- `esta_en_rango()` — `consecutivo_actual <= rango_hasta`

---

## 4. Capa de Servicios (`services/`)

### 4.1 `selectors.py` — ZERO-COLLISION

**Regla critica:** `VENTA_LIST_FIELDS` y `VENTA_DETAIL_FIELDS` NUNCA contienen strings con `__`. Las traversals van en tuplas separadas.

```python
VENTA_LIST_FIELDS = (
    'id', 'uuid', 'fecha_emision', 'fecha_vencimiento', 'estado',
    'subtotal', 'impuestos', 'total_neto', 'observaciones',
    'numero_factura',              # nuevo en 0003
    'cliente_id', 'proyecto_id',
    'resolucion_id',               # nuevo en 0003
    'factura_asociada_id',
    'empresa_id', 'created_at', 'updated_at',
)
VENTA_DETAIL_FIELDS = VENTA_LIST_FIELDS  # mismo set

ITEM_LIST_FIELDS = (
    'id', 'descripcion', 'cantidad', 'precio_unitario',
    'porcentaje_iva', 'subtotal', 'venta_id', 'producto_id', 'servicio_id', 'empresa_id',
)

# Traversals (unico lugar donde __ esta permitido)
_CLIENTE_TRAVERSALS   = ('cliente__razon_social', 'cliente__numero_documento', 'cliente__tipo_documento')
_PROYECTO_TRAVERSALS  = ('proyecto__nombre',)
_FACTURA_TRAVERSALS   = ('factura_asociada__numero', 'factura_asociada__uuid',
                         'factura_asociada__estado', 'factura_asociada__cufe')
_RESOLUCION_TRAVERSALS = ('resolucion__uuid', 'resolucion__numero_resolucion',  # nuevo en 0003
                           'resolucion__prefijo', 'resolucion__tipo')
_PRODUCTO_TRAVERSALS  = ('producto__nombre', 'producto__codigo')
_SERVICIO_TRAVERSALS  = ('servicio__nombre', 'servicio__codigo')

# Campos para ResolucionFacturacion
RESOLUCION_LIST_FIELDS = (
    'id', 'uuid', 'numero_resolucion', 'prefijo', 'tipo',
    'fecha_resolucion', 'fecha_desde', 'fecha_hasta',
    'rango_desde', 'rango_hasta', 'consecutivo_actual', 'vigente',
    'empresa_id', 'created_at', 'updated_at',
)
RESOLUCION_DETAIL_FIELDS = RESOLUCION_LIST_FIELDS
```

**`VentaSelector.get_list(empresa_id, search=None, estado=None)`**
- Filtra por `empresa_id` + `select_related(cliente, proyecto, factura_asociada, resolucion)` + `.only(*VENTA_LIST_FIELDS, *traversals)`
- `estado` aplica `Q(estado=estado)` (filtrado backend para pills de Tabulator)
- `search` aplica `Q(cliente__razon_social__icontains=...) | Q(cliente__numero_documento__icontains=...) | Q(numero_factura__icontains=...) | Q(observaciones__icontains=...)`
- `order_by('-created_at')`

**`VentaSelector.get_detail(empresa_id, venta_uuid=None)`**
- `select_related(cliente, proyecto, factura_asociada, resolucion)` + `prefetch_related('items', 'items__producto', 'items__servicio')`
- Filtra opcionalmente por `uuid`

**`ResolucionFacturacionSelector` (nuevo en v3.17.0)**

```python
class ResolucionFacturacionSelector:
    get_list(empresa_id, vigente_only=False)    # todas o solo vigentes
    get_detail(empresa_id, resolucion_uuid)      # detalle por UUID
    get_vigentes(empresa_id)                     # vigente=True + rango de fechas activo
```

`get_vigentes()` filtra `vigente=True, fecha_desde__lte=hoy, fecha_hasta__gte=hoy` — usa para poblar el selector en el formulario de nueva venta.

---

### 4.2 `crud_service.py` — Persistencia Pura

Todas las operaciones decoradas con `@transaction.atomic`.

**`VentaCRUDService.crear_venta(empresa, cliente, data, items_data) → Venta`**
1. Crea `Venta` en estado `BORRADOR` con `resolucion=data.get('resolucion')` y `numero_factura=data.get('numero_factura')` (ambos opcionales)
2. `bulk_create(items_a_crear)` — calcula subtotal e impuestos por linea
3. Actualiza `venta.subtotal`, `venta.impuestos`, `venta.total_neto` con `save(update_fields=...)`
4. Retorna instancia con totales

**`VentaCRUDService.actualizar_venta(venta, data, items_data=None) → Venta`**
- Guard: `venta.estado != BORRADOR` → `ValueError`
- Actualiza solo campos cabecera: `fecha_emision`, `fecha_vencimiento`, `observaciones`, `proyecto`
- Si `items_data` provided: borra items existentes, crea nuevos con `bulk_create`

**`VentaCRUDService.vincular_factura(venta, factura) → Venta`**
- Asigna `venta.factura_asociada = factura`
- Cambia `venta.estado = FACTURADA_DIAN`
- `save(update_fields=['factura_asociada', 'estado'])`

**`VentaCRUDService.anular_venta(venta) → Venta`**
- Guard: `venta.estado == FACTURADA_DIAN` → `ValueError('Emita nota credito')`
- `venta.estado = ANULADA`, `save(update_fields=['estado'])`

**`ResolucionFacturacionCRUDService` (nuevo en v3.17.0)**

```python
crear_resolucion(empresa, data)                     # full_clean() + save()
actualizar_resolucion(resolucion, data)             # full_clean() + save(); no actualiza consecutivo_actual
eliminar_resolucion(resolucion)                     # guard: ventas_asociadas.exists() → ValueError
```

---

### 4.3 `business_service.py` — Logica de Negocio y Orquestacion DIAN

**Restriccion clave:** Todos los imports de apps externas van DENTRO de metodos (evitar circularidad). Cero emojis. Cero campos `cuenta_*_uuid`.

#### DSV Helpers (privados)

**`_dsv_cliente(cliente_uuid, empresa_id) → Cliente`**
- `Cliente.objects.filter(uuid=cliente_uuid, empresa_id=empresa_id).first()` o `ValueError`

**`_dsv_items(items_data, empresa_id) → list`**
- Valida descripcion requerida + precio > 0 por cada item
- Si `producto_id` presente: verifica pertenencia, convierte UUID → PK interno
- Si `servicio_id` presente: idem
- Acumula errores, levanta `ValueError('err1 | err2 | ...')` si hay fallas

**`_dsv_y_asignar_resolucion(empresa_id, resolucion_uuid) → (resolucion, numero_factura_str)` (nuevo)**
- `select_for_update()` en `ResolucionFacturacion` — previene race conditions
- Valida: `vigente == True`, `esta_vigente_en_fecha()`, `esta_en_rango()`
- Asigna `numero_factura = resolucion.formar_numero()`
- `resolucion.consecutivo_actual += 1; resolucion.save(update_fields=['consecutivo_actual'])`
- **Nota:** usa `+= 1` (no `F()`); es seguro porque `select_for_update()` bloquea la fila, pero el patron canonico del ERP es `F('consecutivo_actual') + 1`.

#### Helpers DIAN (nuevos en v3.17.0)

**`_leer_config_dian() → dict`**
Lee desde `settings`: `DIAN_PROVIDER_ID`, `DIAN_SOFTWARE_ID`, `DIAN_SOFTWARE_PIN`, `DIAN_CL_TECN`, `DIAN_TIP_AMB`, `DIAN_AUTHORIZATION_ID`, `DIAN_CUSTOMIZATION_ID`, `DIAN_PROFILE_ID`. Todos con defaults seguros para desarrollo.

**`_tax_level_code_emisor(regimen_tributario) → (tlc, list_name, ts_id, ts_name)`**
- `COMUN / IVA / GRAN` → `("O-13", "48", "01", "IVA")`
- Otro → `("R-99-PN", "49", "ZZ", "No aplica")`

**`_tax_level_code_receptor(tipo_documento) → (tlc, list_name, ts_id, ts_name, additional_account_id)`**
- `tipo_documento == "31"` (NIT) → `("O-13", "48", "01", "IVA", "1")`
- Otro → `("R-99-PN", "49", "ZZ", "No aplica", "2")`

**`_software_security_code(software_id, software_pin, num_fac) → str`**
- `SHA384(software_id + software_pin + num_fac)` — 96-char hex

#### DTO Canonico DIAN

**`_construir_dto_factura(empresa, cliente, venta, items_data, numero_factura=None, resolucion=None) → dict`**

Estructura completa UBL 2.1:

```python
{
    'document_type': 'FE',
    'tipo': 'FE',
    'naturaleza': 'VENTA',
    'customization_id': '10',
    'profile_id': 'DIAN 2.1',
    'tip_amb': '2',              # '2'=hab/pruebas, '1'=produccion
    'invoice_type_code': '01',
    'num_fac': numero_factura,   # prefijo+consecutivo o venta.uuid si sin resolucion
    'fec_fac': 'YYYY-MM-DD',
    'hor_fac': 'HH:MM:SS-05:00',
    'moneda': 'COP',
    'emisor': {
        'nit', 'dv', 'razon_social', 'direccion', 'ciudad', 'departamento',
        'email', 'telefono', 'tipo_documento': '31', 'additional_account_id': '1',
        'tax_level_code', 'tax_level_list_name', 'tax_scheme_id', 'tax_scheme_name',
    },
    'receptor': {
        'nit', 'razon_social', 'email', 'telefono', 'direccion', 'ciudad',
        'tipo_documento', 'additional_account_id',
        'tax_level_code', 'tax_level_list_name', 'tax_scheme_id', 'tax_scheme_name',
    },
    'dian_software': {
        'provider_id', 'software_id', 'software_security_code', 'authorization_id',
    },
    'resolucion': {               # solo si se provee resolucion
        'numero_autorizacion', 'prefijo', 'desde', 'hasta', 'fecha_inicio', 'fecha_fin',
    },
    'medio_pago': { 'codigo': '47', 'fecha_vencimiento', 'instruccion': 'Transferencia' },
    'totales': {
        'subtotal', 'impuestos', 'total',
        'line_extension_amount', 'tax_exclusive_amount', 'tax_inclusive_amount',
        'allowance_total', 'charge_total', 'payable_amount',
    },
    'impuestos_discriminados': [  # agrupados por tasa
        { 'porcentaje', 'valor', 'base', 'tax_scheme_id', 'tax_scheme_name' }
    ],
    'lineas': [
        { 'id', 'descripcion', 'cantidad', 'valor_unitario', 'porcentaje_iva',
          'subtotal', 'iva', 'total', 'unidad': 'NAL',
          'tax_scheme_id', 'tax_scheme_name', 'seller_item_id', 'std_item_id' }
    ],
    'venta_uuid', 'cliente_uuid',
    'fecha_emision', 'fecha_vencimiento', 'observaciones',
    # Solo si numero_factura != None:
    'numero_externo': numero_factura,
}
```

#### Metodos Publicos

**`crear_venta_borrador(empresa, payload) → (bool, venta|error_dict, status_code)`**
- DSV cliente + items + proyecto opcional
- `VentaCRUDService.crear_venta(...)` — sin resolucion ni numero_factura
- Retorna `(True, venta, 201)` o `(False, {'detail': ...}, 400|500)`

**`procesar_y_facturar_venta(empresa, payload) → (bool, venta|error_dict, status_code)`**

Flujo atomico completo en `@transaction.atomic`:

```
1. Validar campos obligatorios (cliente, fecha_emision, items)
2. DSV cliente + items + proyecto (opcional)
3. DSV resolucion + asignacion atomica del consecutivo (select_for_update)
   → (resolucion, numero_factura)  [opcional: si payload.resolucion]
4. VentaCRUDService.crear_venta() → venta en BORRADOR con numero_factura asignado
5. _construir_dto_factura(empresa, cliente, venta, items, numero_factura, resolucion)
5a. CufeService.calcular_desde_dto(dto) → cufe (SHA384 96 chars)
    CufeService.generar_qr_string(cufe, dto) → url QR DIAN
5b. UBL21BuilderService.build(dto, cufe, qr_string) → xml_bytes
5c. XadesSignerService.sign(xml_bytes) → xml_signed (no-op si DIAN_CERT_P12 vacio)
5d. AttachedDocumentService.build(xml_signed, dto, cufe) → attached_doc_bytes
    AttachedDocumentService.build_application_response(dto, cufe) → app_response_bytes
    Enriquecer dto: dto['xml_content'] + dto['dian_response_xml']
5e. FacturaBusinessService.crear_factura_desde_venta(empresa, dto)  [import lazy]
6. VentaCRUDService.vincular_factura(venta, factura) → estado FACTURADA_DIAN
7. Retorna (True, venta, 201)
```

**`anular_venta(venta_uuid, empresa_id) → (bool, venta|error_dict, status_code)`**
- Lookup `Venta.objects.filter(uuid=..., empresa_id=...)` + DSV implicita
- `VentaCRUDService.anular_venta(venta)`

**`ResolucionFacturacionBusinessService` (nuevo en v3.17.0)**

```python
crear_resolucion(empresa, payload)                           # → (True, obj, 201) | (False, err, 400)
actualizar_resolucion(resolucion_uuid, empresa_id, payload)  # → (True, obj, 200) | (False, err, 400|404)
eliminar_resolucion(resolucion_uuid, empresa_id)             # → (True, None, 204) | (False, err, 400|404|500)
```

---

### 4.4 `api_mixins.py`

```python
class VentaServiceMixin(BaseServiceMixin):
    selector_class = VentaSelector
    business_service_class = VentaBusinessService
    crud_service_class = VentaCRUDService

    service_crear_borrador(empresa, payload)       # -> (bool, obj, code)
    service_procesar_y_facturar(empresa, payload)  # -> (bool, obj, code)
    service_anular_venta(venta_uuid, empresa_id)   # -> (bool, obj, code)
    get_qs_list()   # search + estado desde request.query_params
    get_qs_detail() # filtra por uuid del kwargs


class ResolucionFacturacionServiceMixin(BaseServiceMixin):   # nuevo en v3.17.0
    selector_class = ResolucionFacturacionSelector
    business_service_class = ResolucionFacturacionBusinessService
    crud_service_class = ResolucionFacturacionCRUDService

    service_crear_resolucion(empresa, payload)
    service_actualizar_resolucion(resolucion_uuid, empresa_id, payload)
    service_eliminar_resolucion(resolucion_uuid, empresa_id)
    get_qs_list()    # vigente_only desde request.query_params
    get_qs_detail()  # filtra por uuid del kwargs
```

---

### 4.5 `__init__.py` — Re-exports

```python
from .selectors import (
    VentaSelector, VENTA_LIST_FIELDS, VENTA_DETAIL_FIELDS,
    ResolucionFacturacionSelector, RESOLUCION_LIST_FIELDS,
)
from .crud_service import VentaCRUDService, ResolucionFacturacionCRUDService
from .business_service import VentaBusinessService, ResolucionFacturacionBusinessService
from .api_mixins import VentaServiceMixin, ResolucionFacturacionServiceMixin
```

---

## 5. Capa API (`api/`)

### 5.1 `serializers.py`

**`ResolucionFacturacionSerializer`** (nuevo en v3.17.0)

| Campo | Tipo | Notas |
|-------|------|-------|
| `id`, `uuid` | read_only | |
| `numero_resolucion`, `prefijo`, `tipo`, `vigente` | R/W | |
| `fecha_resolucion`, `fecha_desde`, `fecha_hasta` | R/W | |
| `rango_desde`, `rango_hasta` | R/W | |
| `consecutivo_actual` | read_only | gestionado internamente |
| `tipo_display` | read_only | `get_tipo_display()` — label legible |
| `numero_formado` | SerializerMethodField | `obj.formar_numero()` |
| `agotada` | SerializerMethodField | `not obj.esta_en_rango()` |

**`ItemVentaSerializer`** — read-only `id`, `subtotal`

| Campo | Tipo |
|-------|------|
| `id` | read_only |
| `descripcion`, `cantidad`, `precio_unitario`, `porcentaje_iva` | R/W |
| `subtotal` | read_only (calculado) |
| `producto_id`, `servicio_id` | R/W (enteros del ORM, no UUIDs) |

**`VentaListSerializer`** — optimizado para Tabulator

Campos planos: `id`, `uuid`, `fecha_emision`, `fecha_vencimiento`, `estado`, `subtotal`, `impuestos`, `total_neto`, `numero_factura`, `cliente_id`, `cliente_nombre` (source), `cliente_documento` (source), `proyecto_id`, `resolucion_id`, `resolucion_prefijo` (SerializerMethodField), `factura_asociada_id`, `factura_numero` (SMF — primero `factura_asociada.numero`, fallback `venta.numero_factura`), `factura_uuid` (SMF), `created_at`.

Todos `read_only_fields = fields`.

**`VentaDetailSerializer`** — incluye `items = ItemVentaSerializer(many=True, read_only=True)` y campos adicionales: `proyecto_nombre` (source), `resolucion_numero` (SMF), `resolucion_prefijo` (SMF), `factura_estado` (SMF).

---

### 5.2 `viewsets.py`

```python
class VentaViewSet(VentaServiceMixin, BaseTenantViewSet):
    queryset = Venta.objects.none()
    serializer_class = VentaDetailSerializer
    lookup_field = 'uuid'
    lookup_url_kwarg = 'uuid'
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['observaciones', 'numero_factura']   # numero_factura nuevo
    ordering_fields = ['fecha_emision', 'total_neto', 'created_at']
    ordering = ['-created_at']


class ResolucionFacturacionViewSet(ResolucionFacturacionServiceMixin, BaseTenantViewSet):
    queryset = ResolucionFacturacion.objects.none()
    serializer_class = ResolucionFacturacionSerializer
    lookup_field = 'uuid'
    lookup_url_kwarg = 'uuid'
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    filter_backends = [OrderingFilter]
    ordering_fields = ['fecha_resolucion', 'vigente', 'created_at']
    ordering = ['-vigente', '-fecha_resolucion']
```

**`VentaViewSet.get_object()`** — DSV: `Venta.objects.filter(uuid=..., empresa_id=...)` — lanza `NotFound` si no existe.

#### Endpoints — VentaViewSet

| Metodo | URL | Handler | Descripcion |
|--------|-----|---------|-------------|
| `GET` | `/api/v1/ventas/` | `list` | Lista paginada (Tabulator) — soporta `?search=` y `?estado=` |
| `GET` | `/api/v1/ventas/{uuid}/` | `retrieve` | Detalle |
| `POST` | `/api/v1/ventas/` | `create` | Crea BORRADOR via `service_crear_borrador` |
| `DELETE` | `/api/v1/ventas/{uuid}/` | `destroy` | Anula logicamente (llama a `service_anular_venta`) |
| `POST` | `/api/v1/ventas/{uuid}/procesar-facturar/` | `procesar_facturar` | Flujo atomico DIAN completo: CUFE + XML + Firma + Factura + FACTURADA_DIAN |
| `POST` | `/api/v1/ventas/{uuid}/anular/` | `anular` | Anula (BORRADOR solamente) |
| `GET` | `/api/v1/ventas/render-offcanvas/crear/` | `render_offcanvas_crear` | HTMX — template con clientes + resoluciones vigentes |
| `GET` | `/api/v1/ventas/render-offcanvas/detalle/` | `render_offcanvas_detalle` | HTMX — template con venta completa |

**`procesar_facturar` — logica del action:**
```python
# Rellena payload desde venta existente si los campos no vienen en request.data
payload["cliente"] = str(venta.cliente.uuid)
payload["fecha_emision"] = str(venta.fecha_emision)
payload.setdefault("fecha_vencimiento", ...)
payload.setdefault("observaciones", ...)
if not payload.get("items"):
    payload["items"] = [rebuild from venta.items.select_related('producto','servicio')]
# payload["resolucion"] = UUID de resolucion (debe venir en request.data)
ok, result, code = self.service_procesar_y_facturar(empresa, payload)
```

#### Endpoints — ResolucionFacturacionViewSet (nuevos en v3.17.0)

| Metodo | URL | Handler | Descripcion |
|--------|-----|---------|-------------|
| `GET` | `/api/v1/ventas/resoluciones/` | `list` | Lista paginada; soporta `?vigente=true` |
| `POST` | `/api/v1/ventas/resoluciones/` | `create` | Crea nueva resolucion DIAN |
| `GET` | `/api/v1/ventas/resoluciones/{uuid}/` | `retrieve` | Detalle |
| `PATCH` | `/api/v1/ventas/resoluciones/{uuid}/` | `partial_update` | Actualiza campos editables |
| `PUT` | `/api/v1/ventas/resoluciones/{uuid}/` | `update` | Alias de `partial_update` |
| `DELETE` | `/api/v1/ventas/resoluciones/{uuid}/` | `destroy` | Elimina si no tiene ventas asociadas |
| `GET` | `/api/v1/ventas/resoluciones/panel/` | `render_panel` | HTMX — panel de administracion |
| `GET` | `/api/v1/ventas/resoluciones/render-offcanvas/crear/` | `render_offcanvas_crear` | HTMX — offcanvas crear resolucion |
| `GET` | `/api/v1/ventas/resoluciones/render-offcanvas/editar/` | `render_offcanvas_editar` | HTMX — offcanvas editar resolucion |

---

### 5.3 `urls.py`

```python
from rest_framework.routers import DefaultRouter
from apps.tenant.ventas.api.viewsets import VentaViewSet, ResolucionFacturacionViewSet

router = DefaultRouter()
router.register(r'', VentaViewSet, basename='venta')
router.register(r'resoluciones', ResolucionFacturacionViewSet, basename='resolucion-facturacion')
urlpatterns = router.urls
```

**Registro en `config/api_urls.py`:**
```python
path('ventas/', include('apps.tenant.ventas.api.urls'))
```

**URL base:** `/api/v1/ventas/`

---

## 6. Templates (`templates/tenant/ventas/`)

### 6.1 `list_ventas.html`

Componente puro (sin layout), incluido por `workspace.html` en `#tab-ventas`.

**Estructura:**
- `.ui-ventas` — scope CSS del modulo
- 4 KPI cards (col-6 col-xl-3): `#kpi-ventas-total`, `#kpi-ventas-monto`, `#kpi-ventas-borradores`, `#kpi-ventas-facturadas`
- Toolbar: `#btn-nueva-venta` (hx-get crear), `#btn-resoluciones-dian` (hx-get `/api/v1/ventas/resoluciones/panel/`), `#btn-refresh-ventas`, `#search-venta` con icono prefijo
- `#feedback-ventas-list` — zona de errores
- Grid container con borde/sombra:
  - Pills de filtro `[data-filtro-venta-estado]`: `""` (Todas), `BORRADOR`, `FACTURADA_DIAN`, `ANULADA`
  - `[data-spinner="ventas"]` — spinner inicial
  - `#grid-ventas` — contenedor Tabulator
  - `[data-empty-state="ventas"]` — estado vacio
- `#offcanvas-container-ventas` — receptor HTMX para offcanvas
- `{% include 'tenant/ventas/partials/assets_ventas.html' %}` — carga JS

### 6.2 `offcanvas_crear_venta.html`

ID raiz: `#offcanvas-venta-crear` (width: 800px, backdrop static)

**Inputs del formulario:**

| ID | Tipo | Descripcion |
|----|------|-------------|
| `#venta-cliente` | `<select>` | Opciones con `data-uuid="{{ c.uuid }}"` — captura UUID sin parseInt |
| `#venta-cliente-uuid` | `<input hidden>` | UUID capturado por JS al cambiar select |
| `#venta-resolucion` | `<select>` | Resoluciones vigentes — `data-uuid="{{ r.uuid }}"` |
| `#venta-resolucion-uuid` | `<input hidden>` | UUID de la resolucion seleccionada |
| `#venta-fecha-emision` | date | `value="{{ fecha_default }}"` |
| `#venta-fecha-vencimiento` | date | opcional |
| `#venta-observaciones` | textarea | opcional |
| `#venta-items-body` | `<tbody>` | Filas dinamicas agregadas por `venta_editor.js` |
| `#btn-agregar-item-venta` | button | Agrega fila item |
| `#venta-display-subtotal/iva/total` | readonly | Totales calculados en JS |
| `#btn-guardar-borrador` | button | Crea BORRADOR (`POST /api/v1/ventas/`) |
| `#btn-facturar-dian` | button.btn-success | Crea BORRADOR + Factura DIAN atomicamente |
| `#form-venta-crear-feedback` | `.alert.d-none` | Zona de errores |

Contexto del ViewSet: `{ 'clientes': qs, 'resoluciones': qs_vigentes, 'fecha_default': hoy.isoformat() }`

### 6.3 `offcanvas_detalle_venta.html`

ID raiz: `#offcanvas-venta-detalle`

**Contenido:**
- Badge de estado (`BORRADOR / FACTURADA_DIAN / ANULADA`)
- Info cliente, fechas, proyecto, observaciones
- Bloque resolucion — numero y prefijo si existe
- Bloque `{% if venta.factura_asociada %}` — numero CUFE, numero factura DIAN
- Tabla de `{% for item in venta.items.all %}` — cantidad, precio, IVA, subtotal
- Totales: subtotal / IVA / total_neto con `|intcomma`
- Footer con botones condicionales por estado:
  - `BORRADOR`: `[data-venta-action="anular"]` + `[data-venta-action="facturar-dian"]`
- `#detalle-venta-feedback` — zona de errores

### 6.4 `panel_resoluciones.html` (nuevo en v3.17.0)

Renderizado por `ResolucionFacturacionViewSet.render_panel` en `#offcanvas-container-ventas`.

Contenido: tabla de resoluciones con numero, prefijo, tipo, rango, consecutivo actual, vigencia, estado. Botones: "Nueva Resolucion" (hx-get offcanvas/crear), "Editar" por fila (hx-get offcanvas/editar?uuid=...).

### 6.5 `offcanvas_crear_resolucion.html` / `offcanvas_editar_resolucion.html` (nuevos en v3.17.0)

Formularios HTMX para CRUD de `ResolucionFacturacion`. Campos: `numero_resolucion`, `prefijo`, `tipo` (select), `fecha_resolucion`, `fecha_desde`, `fecha_hasta`, `rango_desde`, `rango_hasta`, `vigente`.

### 6.6 `partials/assets_ventas.html`

```html
{% load static %}
<script src="{% static 'ventas/js/ventas.api.js' %}"></script>
<script src="{% static 'ventas/js/features/venta_list.js' %}"></script>
<script src="{% static 'ventas/js/features/venta_editor.js' %}"></script>
```

---

## 7. JavaScript (`static/ventas/js/`)

### 7.1 `ventas.api.js` — SSoT URLs

**Namespace:** `window.Sintel.Ventas.API`

```javascript
const API_ROOT = '/api/v1/ventas/';

// Headers: Content-Type JSON + X-CSRFToken + Authorization: Bearer {token}
// Usa window.jwtAuth.getAccessToken() — NUNCA window.jwtAuth.token

API.list(params)                 // GET /api/v1/ventas/?...
API.detail(uuid)                 // GET /api/v1/ventas/{uuid}/
API.create(data)                 // POST /api/v1/ventas/
API.update(uuid, data)           // PATCH /api/v1/ventas/{uuid}/
API.eliminar(uuid, motivo)       // DELETE /api/v1/ventas/{uuid}/
API.procesarFacturar(uuid)       // POST /api/v1/ventas/{uuid}/procesar-facturar/
API.anular(uuid, motivo)         // POST /api/v1/ventas/{uuid}/anular/
API.renderCrear()                // -> URL string para HTMX
API.renderDetalle(uuid)          // -> URL string para HTMX
```

**Notas:**
- HTTP 204 retorna `{ success: true }`
- Errores no-OK levantan `Error` con `.status` y `.data` (JSON parseado)

---

### 7.2 `features/venta_list.js`

**Namespace:** `window.Sintel.Ventas.List`

**Anti-Zombies (tope de script):**
```javascript
if (w._SintelVentasTable) {
    try { w._SintelVentasTable.destroy(); } catch (_) {}
    w._SintelVentasTable = null;
}
```

**Module-level `_filtroEstado = ''`** — capturado por closure de `ajaxParams`:
```javascript
ajaxParams: function() {
    return _filtroEstado ? { estado: _filtroEstado } : {};
}
```

`TabulatorFactory` requiere que `ajaxParams` sea **funcion** (no objeto plano) — la funcion se evalua en cada request al cambiar de pagina o recargar.

**`ESTADO_CONFIG`:**
```javascript
BORRADOR:       { cls: 'secondary', label: 'Borrador' },
FACTURADA_DIAN: { cls: 'success',   label: 'Facturada DIAN' },
ANULADA:        { cls: 'danger',    label: 'Anulada' },
```

**KPIs actualizados en `dataLoaded` y `dataFiltered`:**
- `#kpi-ventas-total` — todos los rows
- `#kpi-ventas-monto` — suma `total_neto` (excluyendo ANULADAS)
- `#kpi-ventas-borradores` — `estado == BORRADOR`
- `#kpi-ventas-facturadas` — `estado == FACTURADA_DIAN`

**Columnas Tabulator:**

| Campo | Titulo | Notas |
|-------|--------|-------|
| `cliente_nombre` | Cliente | Doble linea: nombre + NIT |
| `fecha_emision` | Fecha | Formato `es-CO` |
| `estado` | Estado | `chipEstado()` badge |
| `numero_factura` | No. Factura | Badge con prefijo si existe |
| `factura_numero` | Factura DIAN | Badge verde si existe, `—` si no |
| `total_neto` | Total | `Intl.NumberFormat('es-CO', COP)` |
| `_acciones` | Acciones | Boton "Ver detalle" → `List.abrirDetalle(uuid)` |

**Filter pills** (`bindFiltrosEstado`):
```javascript
pills.forEach(btn => btn.addEventListener('click', function() {
    pills.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    _filtroEstado = btn.getAttribute('data-filtro-venta-estado') || '';
    if (List.table) { List.table.setPage(1); }  // recarga con nuevo estado
}));
```

**`List.abrirDetalle(uuid)`:**
```javascript
htmx.ajax('GET', API.renderDetalle(uuid), {
    target: '#offcanvas-container-ventas', swap: 'innerHTML'
});
```

---

### 7.3 `features/venta_editor.js`

**Namespace:** `window.Sintel.Ventas.Editor`

**Dispara evento al cargar:** `document.dispatchEvent(new CustomEvent('sintel:ventas:editor:ready'))`

#### `mostrarOffcanvasSeguro(elOrId)`
- Elimina `.offcanvas-backdrop` huerfanos
- Limpia `body.classList` y `body.style.overflow`
- `dispose()` instancia previa + `new bootstrap.Offcanvas(el).show()`

#### Gestion de Items

**`crearFilaItem(idx) → <tr>`** — fila con inputs `.item-descripcion`, `.item-cantidad`, `.item-precio`, `.item-iva` (select 0/5/19%), `.item-subtotal` (readonly), boton eliminar.

**`calcularTotalesForm()`** — recorre `#venta-items-body tr[data-item-idx]`, actualiza `.item-subtotal` + `#venta-display-subtotal/iva/total`.

**`recolectarItems() → Array`**
```javascript
items.push({
    descripcion, cantidad: parseFloat(...),
    precio_unitario: parseFloat(...), porcentaje_iva: parseFloat(...),
});
```

#### Captura de Cliente y Resolucion (ZERO parseInt)
```javascript
function capturarClienteUUID() {
    var opt = d.getElementById('venta-cliente').options[selectedIndex];
    return opt.getAttribute('data-uuid');
}
function capturarResolucionUUID() {
    var opt = d.getElementById('venta-resolucion').options[selectedIndex];
    return opt ? opt.getAttribute('data-uuid') : null;
}
```

#### `guardarVenta(facturarDian)`

```
1. _validarYConstruirPayload()
     ├── capturarClienteUUID() → null → error
     ├── #venta-fecha-emision → vacio → error
     ├── recolectarItems() → vacio → error
     └── validar descripcion + precio > 0 por item
2. if (facturarDian) → agregar resolucion: capturarResolucionUUID()
3. API.create(payload)
4. if (!facturarDian) → cerrar offcanvas + recargar tabla
5. if (facturarDian)  → API.procesarFacturar(venta.uuid) → cerrar + recargar
```

#### API Publica

```javascript
Editor.onHtmxLoaded()          // offcanvas crear: bindFormCrear + mostrarOffcanvasSeguro
Editor.onDetalleLoaded(el)     // offcanvas detalle: bindDetalleAcciones + mostrarOffcanvasSeguro
Editor.abrirCrear()            // HTMX GET a renderCrear() → #offcanvas-container-ventas
```

#### Acciones de Detalle (`bindDetalleAcciones`)

Listeners en `[data-venta-action]`:

| `data-venta-action` | Accion |
|--------------------|--------|
| `facturar-dian` | `API.procesarFacturar(uuid)` → cerrar + recargar tabla |
| `anular` | `window.prompt(motivo)` → `API.anular(uuid, motivo)` → cerrar + recargar |

---

## 8. Integracion DIAN — Pipeline Completo

**Regla de desacoplamiento:**
- `ventas` NUNCA importa `Factura`, `AsientoContable`, ni `MovimientoContable` a nivel de modulo.
- Todos los imports de `apps.tenant.facturas.*` van **dentro del cuerpo de metodos** (`business_service.py`).
- `Contabilidad` extrae de `Factura` via Pull Model (extractores en `integracion/extractores/`).

**Flujo completo (Paso 5 expandido):**

```
VentaBusinessService.procesar_y_facturar_venta()
    │
    ├─ CufeService.calcular_desde_dto(dto)                       # SHA384 de campos fiscales
    ├─ CufeService.generar_qr_string(cufe, dto)                  # URL DIAN (hab o prod segun tip_amb)
    ├─ UBL21BuilderService.build(dto, cufe, qr_string) → bytes   # XML estandar DIAN
    ├─ XadesSignerService.sign(xml_bytes) → bytes                 # XAdES-EPES (no-op si sin cert)
    ├─ AttachedDocumentService.build(signed, dto, cufe) → bytes  # Sobre de envio DIAN
    ├─ AttachedDocumentService.build_application_response(...)   # Respuesta aplicacion
    └─ FacturaBusinessService.crear_factura_desde_venta(empresa, dto_enriquecido)
           ↓
       FacturaCRUDService.crear(...)   → Factura con numero_factura asignado
       bulk_create(ItemFactura, ...)
           ↓
       VentaCRUDService.vincular_factura(venta, factura)
           ↓
       venta.estado = FACTURADA_DIAN
       venta.factura_asociada = factura
```

**Numero de factura:**
- Con resolucion: `resolucion.formar_numero()` = `"{prefijo}{consecutivo_actual}"` (ej: `FE1001`)
- Sin resolucion: `str(venta.uuid)` — provisional, satisface `unique=True`

**Configuracion DIAN (`settings.py`):**

| Setting | Descripcion | Default dev |
|---------|-------------|-------------|
| `DIAN_PROVIDER_ID` | NIT proveedor tecnologico | `'800197268'` |
| `DIAN_SOFTWARE_ID` | UUID software registrado | zeros |
| `DIAN_SOFTWARE_PIN` | PIN para SoftwareSecurityCode | `''` |
| `DIAN_CL_TECN` | Clave tecnica 64 hex | `''` |
| `DIAN_TIP_AMB` | `'1'`=prod, `'2'`=hab/pruebas | `'2'` |
| `DIAN_AUTHORIZATION_ID` | NIT entidad autorizadora | `'800197268'` |
| `DIAN_CERT_P12` | Ruta al certificado PKCS#12 | `''` (firma desactivada) |

---

## 9. Integracion con Workspace

**Archivo:** `apps/tenant/core/templates/tenant/core/workspace.html`

```html
<!-- Nav -->
<li class="nav-item">
  <a href="#ventas" data-tab="ventas" class="nav-link">
    <i class="bi bi-bag-check me-2"></i>Ventas
  </a>
</li>

<!-- Section -->
<section id="tab-ventas" class="workspace-tab" style="display: none;">
  {% include 'tenant/ventas/list_ventas.html' %}
</section>

<!-- Assets (en bloque extra_js) -->
{% include 'tenant/ventas/partials/assets_ventas.html' %}
```

---

## 10. Migraciones

| Migracion | Contenido |
|-----------|-----------|
| `0001_init_ventas.py` | Crea `OrdenVenta` e `ItemOrdenVenta` (modelos originales v3.10.5) |
| `0002_rewrite_venta_v2.py` | Drop `OrdenVenta` / `ItemOrdenVenta`; Create `Venta` / `ItemVenta` con FK, constraints e indexes (v3.16.x) |
| `0003_venta_numero_factura_resolucionfacturacion_and_more.py` | Create `ResolucionFacturacion`; Add `Venta.numero_factura` + `Venta.resolucion` FK; Indexes `(empresa, resolucion)` y `(empresa, vigente)` en ResolucionFacturacion |

**Dependencias de `0003`:**
- `empresa.0009_sedes_areas_explicit_fk`
- `facturas.0030_facturaimpuesto`
- `tenant_clientes.0008_cartera`
- `tenant_proyectos.0019_proyecto_sede`
- `tenant_ventas.0002_rewrite_venta_v2`

---

## 11. Reglas Criticas del Modulo

| Regla | Descripcion |
|-------|-------------|
| **No emojis en `.py`** | `SyntaxError` → Django 500. Hook `py_compile` verifica cada edicion. |
| **ZERO-COLLISION selectores** | `LIST_FIELDS` / `DETAIL_FIELDS` sin `__`. Traversals en tuplas separadas. |
| **DSV en todas las capas** | Todo FK validado contra `empresa_id` antes de `save()`. Incluye `ResolucionFacturacion`. |
| **Imports lazy cross-domain** | Imports de `facturas`, `clientes`, `inventario`, `proyectos` dentro de metodos. |
| **Sin FK a `cuenta_*_uuid`** | Pull Model: Contabilidad extrae desde `Factura`, Ventas no tiene campos contables. |
| **Zero `parseInt()` sobre UUIDs** | Frontend usa `getAttribute('data-uuid')` o `formData.get('campo')`. |
| **`mostrarOffcanvasSeguro(el)`** | Obligatorio para abrir cualquier offcanvas. Previene backdrop acumulado. |
| **`procesar_y_facturar_venta` es atomico** | `@transaction.atomic` — si cualquier paso falla, todo rollback incluyendo el consecutivo. |
| **`total_neto` (no `total`)** | El campo financiero del modelo se llama `total_neto`. JS y serializers deben usar este nombre. |
| **`estado FACTURADA_DIAN`** | El choice exact value es `'FACTURADA_DIAN'`. Tabulator, serializers y templates deben usar este string. |
| **`ajaxParams` debe ser funcion** | `TabulatorFactory` solo acepta `ajaxParams` como funcion (no objeto plano). Ver `venta_list.js`. |
| **`select_for_update()` en consecutivo** | `_dsv_y_asignar_resolucion()` bloquea la fila antes de leer y escribir el consecutivo. El `+= 1` es safe con el lock, pero el patron canonico del ERP es `F('consecutivo_actual') + 1`. |

---

## 12. Checklist de Mantenimiento

Antes de cualquier cambio en este modulo verificar:

- [ ] `models.py` — `SintelTenantBaseModel`, no `models.Model`
- [ ] `selectors.py` — `LIST_FIELDS` y `DETAIL_FIELDS` sin `__` en strings
- [ ] Nuevos FKs en `ItemVenta` → DSV en `business_service._dsv_items()`
- [ ] Nuevo campo en `Venta` → actualizar `VENTA_LIST_FIELDS` + `crear_venta()` + `actualizar_venta()`
- [ ] Nuevo estado en `Venta.Estado` → actualizar `ESTADO_CONFIG` en `venta_list.js` + badge en `offcanvas_detalle_venta.html`
- [ ] Nuevo campo en `ResolucionFacturacion` → actualizar `RESOLUCION_LIST_FIELDS` + `ResolucionFacturacionSerializer`
- [ ] Nueva accion de ViewSet → registrar en `ventas.api.js` + handler en `venta_editor.js`
- [ ] Cambio en DTO DIAN → revisar `_construir_dto_factura()` + `FacturaBusinessService.crear_factura_desde_venta()`
- [ ] Cambio en pipeline DIAN → actualizar steps 5a-5e en `procesar_y_facturar_venta()`
- [ ] Nueva migracion → `make makemigrations` + `make migrate-tenants`
- [ ] `py_compile` en todos los `.py` modificados antes de commit

---

## 13. Deuda Tecnica Registrada

| Item | Descripcion | Prioridad |
|------|-------------|-----------|
| DT-VENTAS-01 | `ResolucionFacturacion.clean()` sin `CheckConstraint` DB para `rango_hasta >= rango_desde` | MEDIUM |
| DT-VENTAS-02 | `_dsv_y_asignar_resolucion()` usa `+= 1` en lugar de `F('consecutivo_actual') + 1` (safe con `select_for_update` pero no canonico) | LOW |
| DT-VENTAS-03 | No existe `UniqueConstraint(empresa, tipo)` en `ResolucionFacturacion` para garantizar una sola resolucion vigente por tipo | MEDIUM |
