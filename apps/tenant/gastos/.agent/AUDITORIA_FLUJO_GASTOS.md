# Auditoria Flujo Completo — Modulo Gastos

**Version auditada:** v3.10.3
**Fecha:** 2026-05-25
**Estado:** PRODUCTION READY (0 criticos, 3 DEUDA BAJA/MEDIA)
**Ubicacion:** `apps/tenant/gastos/`

---

## 1. Responsabilidades del Modulo

| # | Responsabilidad | Estado |
|---|----------------|--------|
| 1 | **Documento Soporte (DS)** — Evidencia legal inmutable para proveedores no obligados a facturar (Decreto 1625/2016 DIAN) | OK |
| 2 | **Resolucion DIAN** — Gestion de numeracion oficial: consecutivos, prefijos, rangos, vigencia | OK |
| 3 | **Desacoplamiento Operativo** — `DocumentoSoporte` (legal) separado de clasificacion administrativa (`categoria_contable`) | OK |
| 4 | **Selectores de Retenciones** — Usuario elige tipo Retefuente/ReteICA desde dropdown; calculo en tiempo real en el formulario | OK (v3.7.3) |
| 5 | **Pull Model Retenciones** — `@property` lee desde `Contabilidad.Retencion`; `DocumentoSoporte` no almacena retenciones | OK (v3.7.1) |
| 6 | **Ciclo de Vida Controlado** — `activo -> anulado` con trazabilidad: `fecha_anulacion`, `motivo_anulacion`, `usuario_anulacion` | OK |
| 7 | **UUID Lookup** — `lookup_field = 'uuid'` en todos los ViewSets | OK (mig 0016) |
| 8 | **Vinculacion Contable** — `cuenta_gasto_uuid` mapea a `CuentaContable` via Pull Model de Contabilidad | OK (mig 0013) |
| 9 | **Precargar Editar Gasto** — Valores de retenciones y base gravable se precargan desde BD al abrir edicion | OK (v3.7.5) |
| 10 | **Pull Model Inventario (Kardex)** — `movimiento_inventario_uuid` (UUID opaco) vincula al Kardex; elimina FKs directos a Producto/Servicio/Activo | OK (mig 0019 — v3.8+) |
| 11 | **Buscador Unificado Movimientos** — Autocomplete `initMovimientoSearch()` reemplaza los 3 selects FK de inventario | OK (v3.8+) |

---

## 2. Modelos

### 2.1 `ResolucionDIAN`
**Herencia:** `SintelTenantBaseModel`
**Ordering:** `['-vigente', '-fecha_resolucion']`

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `unique=True, db_index=True, editable=False` |
| `numero_resolucion` | CharField(50) | `db_index=True` |
| `prefijo` | CharField(10) | p.ej. `"DS"`, `"GS"` |
| `rango_desde` | IntegerField | `MinValueValidator(1)` |
| `rango_hasta` | IntegerField | `MinValueValidator(1)` |
| `fecha_resolucion` | DateField | fecha de emision DIAN |
| `fecha_inicio` | DateField | `default=datetime.date.today` |
| `fecha_fin` | DateField | vencimiento |
| `clave_tecnica` | CharField(100) | nullable |
| `vigente` | BooleanField | `db_index=True` |
| `consecutivo` | IntegerField | `db_index=True, editable=False` — proximo a asignar |

**Indices BD:** `(empresa, vigente)`

**Metodos:**
```python
formar_consecutivo(numero) -> f"{prefijo} {numero}"
esta_dentro_de_fecha(fecha_referencia=None) -> bool
save() -> full_clean() + super().save()
```

---

### 2.2 `DocumentoSoporte`
**Herencia:** `SintelTenantBaseModel`
**Ordering:** `['-fecha', '-consecutivo']`

#### Choices SSoT (definidos en este modelo — criticos para sincronia con templates)

```python
RETEFUENTE_CHOICES = [
    ('0.00', '0% - Sin Retefuente'),
    ('0', '0% - Sin Retefuente'),
    ('0.0', '0% - Sin Retefuente'),
    ('0.04', '4% - Servicios (Declarantes)'),
    ('0.06', '6% - Servicios (No Declarantes)'),
    ('0.10', '10% - Honorarios y Consultoria (No declarante)'),
    ('0.11', '11% - Honorarios y Consultoria (Declarante)'),
]

RETEICA_CHOICES = [
    ('0.00', '0% - Exento'),
    ('0', '0% - Exento'),
    ('0.0', '0% - Exento'),
    ('0.0069', '0.69%'),
    ('0.00966', '0.966%'),
    ('0.01104', '1.104%'),
]
```

**REGLA CRITICA:** Si se modifican estos choices en `models.py`, los `<option>` de los templates `offcanvas_crear_gasto.html` y `offcanvas_editar_gasto.html` DEBEN sincronizarse manualmente (ver CLAUDE.md Seccion Selectores de Retenciones v3.7.3).

#### Campos

| Campo | Tipo | Null | Choices/Info |
|-------|------|------|--------------|
| `uuid` | UUIDField | No | `unique=True, db_index=True, editable=False` |
| `resolucion_dian` | FK ResolucionDIAN | No | `PROTECT`, `related_name='documentos_soporte'` |
| `consecutivo` | IntegerField | No | `db_index=True, editable=False` — asignado atomicamente |
| `categoria_contable` | CharField(50) | Si | `choices=CATEGORIA_CONTABLE_CHOICES` |
| `fecha` | DateField | No | fecha del documento |
| `proveedor` | FK Proveedor | No | `CASCADE` |
| `numero_documento_proveedor` | CharField(100) | Si | referencia factura del proveedor |
| `subtotal` | DecimalField(12,2) | No | `MinValueValidator(0.01)` — base gravable |
| `retefuente_porcentaje` | CharField(10) | No | **DEPRECATED v3.7.1** `editable=False` `choices=RETEFUENTE_CHOICES` |
| `retefuente` | DecimalField(15,2) | No | **DEPRECATED v3.7.1** `editable=False` |
| `reteica_porcentaje` | CharField(10) | No | **DEPRECATED v3.7.1** `editable=False` `choices=RETEICA_CHOICES` |
| `reteica` | DecimalField(15,2) | No | **DEPRECATED v3.7.1** `editable=False` |
| `total` | DecimalField(15,2) | No | `total = subtotal - retenciones` |
| `descripcion` | TextField | Si | |
| `observaciones` | TextField | No (blank=True) | |
| `cuenta_gasto_uuid` | UUIDField | Si | `db_index=True` — UUID opaco a `CuentaContable` |
| **`movimiento_inventario_uuid`** | **UUIDField** | **Si** | **`db_index=True` — UUID opaco a `MovimientoInventario` (Pull Model v3.8+, mig 0019)** |
| `adjunto` | FileField | Si | `upload_to='documentos_soporte/%Y/%m/'` |
| `activo` | BooleanField | No | `default=True, db_index=True` |
| `anulado` | BooleanField | No | `default=False` |
| `fecha_anulacion` | DateTimeField | Si | trazabilidad |
| `motivo_anulacion` | TextField | Si | trazabilidad |
| `usuario_anulacion` | FK TenantProfile | Si | `PROTECT` |

**Campos ELIMINADOS en mig 0019:**
- ~~`producto_relacionado`~~ FK directo a Producto — removido
- ~~`servicio_relacionado`~~ FK directo a Servicio — removido
- ~~`activo_relacionado`~~ FK directo a ActivoFijo — removido

**Indices BD:**
```
(empresa, fecha)
(resolucion_dian, consecutivo)
(proveedor, numero_documento_proveedor)
(categoria_contable)
(fecha) WHERE activo=True AND anulado=False  -> 'idx_gastos_activos'
```

**Constraints:**
```
UNIQUE (resolucion_dian, consecutivo)                               -> 'unique_ds_resolucion_consecutivo'
UNIQUE (empresa, proveedor, numero_documento_proveedor) WHERE NOT anulado  -> 'unique_ds_vendedor_documento'
```

#### Propiedades (@property — Pull Model)

```python
# Retenciones (Pull Model ADR-001 v3.7.1) — leen de Contabilidad.Retencion
total_retefuente     -> SUM(monto) WHERE tipo='RETEFUENTE' AND doc=self.id
total_reteica        -> SUM(monto) WHERE tipo='RETEICA'    AND doc=self.id
total_reteiva        -> SUM(monto) WHERE tipo='RETEIVA'    AND doc=self.id
total_retenciones    -> SUM(monto) todos los tipos
retefuente_calculada -> alias total_retefuente (retrocompat)
reteica_calculada    -> alias total_reteica

# Inventario (Pull Model v3.8+) — lee de MovimientoInventario via Selector
movimiento_referencia -> dict: {tipo, tipo_display, item_nombre, item_codigo, cantidad, item_tipo}
                         o None si movimiento_inventario_uuid es null

# Contabilidad
cuenta_gasto_label   -> CuentaContableSelector.get_label_by_uuid(empresa_id, cuenta_gasto_uuid)

# Proveedor (aplanado)
vendedor_nombre      -> proveedor.razon_social
vendedor_nit         -> proveedor.numero_documento
vendedor_direccion   -> proveedor.direccion
vendedor_telefono    -> proveedor.telefono_contacto

# Numeracion
numero_documento     -> resolucion_dian.formar_consecutivo(consecutivo)
prefijo              -> resolucion_dian.prefijo

# Formateo COP
total_cop, subtotal_cop, retefuente_cop, reteica_cop, total_retenciones_cop
```

---

### 2.3 Modulo `choices/`

| Archivo | Constante | Uso |
|---------|-----------|-----|
| `choices/categoria_contable.py` | `CATEGORIA_CONTABLE_CHOICES` | importado en `DocumentoSoporte.categoria_contable` |

---

### 2.4 Migraciones (19 total)

| # | Archivo | Cambio Principal |
|---|---------|-----------------|
| 0001 | `0001_initial.py` | Creacion inicial: ResolucionDIAN, DocumentoSoporte, modelo legacy Gasto |
| 0002–0006 | varios | Indices, constraints |
| 0007–0009 | varios | Indices Gasto legacy |
| 0010 | `...remove_gasto_documento_soporte.py` | **Elimina modelo legacy Gasto** |
| 0011–0012 | varios | Ajustes retenciones, FK proveedor |
| 0013 | `...add_cuenta_contable_uuid_fields.py` | Agrega `cuenta_gasto_uuid` |
| 0014 | `...remove_cuenta_contrapartida_uuid.py` | Elimina `cuenta_contrapartida_uuid` |
| 0015 | `...alter_cuenta_gasto_uuid.py` | Ajuste field |
| 0016 | `...add_uuid_fields.py` | UUID fields en ambos modelos |
| 0017 | `...alter_retefuente_and_more.py` | `editable=False` en campos retenciones (deprecacion v3.7.1) |
| 0018 | `...activo_relacionado_and_more.py` | Agregaba `producto_relacionado`, `servicio_relacionado`, `activo_relacionado` (FK directo — patron obsoleto) |
| **0019** | **`...remove_documentosoporte_activo_relacionado_and_more.py`** | **Elimina los 3 FK; agrega `movimiento_inventario_uuid` (UUIDField Pull Model v3.8+)** — ULTIMA |

---

## 3. Service Layer (FSD)

### 3.1 `services/selectors.py` — Lectura Zero-Waste

#### `ResolucionSelector`

| Metodo | Descripcion |
|--------|-------------|
| `get_list(empresa_id, search, solo_vigentes)` | `.only(RESOLUCION_LIST_FIELDS)` + `annotate(conteo_documentos=Count(...))` |
| `get_detail(empresa_id, resolucion_uuid)` | `.only(RESOLUCION_DETAIL_FIELDS)` |
| `get_vigente(empresa_id)` | Cache 1 hora → `filter(vigente=True).first()` |

#### `DocumentoSelector`

| Metodo | Descripcion |
|--------|-------------|
| `get_list(empresa_id, resolucion_id, search)` | `.only(DOCUMENTO_LIST_FIELDS)` + `select_related('resolucion_dian', 'proveedor')` |
| `get_detail(empresa_id, documento_uuid)` | `.select_related(...)` + filtro uuid |
| `get_summary(empresa_id)` | `SUM(total)` + `COUNT(id)` mes actual, sin anulados |

**Constantes SSoT:**
```python
RESOLUCION_LIST_FIELDS = (
    'id', 'uuid', 'numero_resolucion', 'prefijo', 'vigente',
    'rango_desde', 'rango_hasta', 'fecha_resolucion',
    'fecha_inicio', 'fecha_fin', 'consecutivo', 'empresa_id'
)

DOCUMENTO_LIST_FIELDS = (
    'id', 'uuid', 'consecutivo', 'subtotal', 'fecha', 'total',
    'categoria_contable', 'descripcion', 'activo', 'anulado',
    'numero_documento_proveedor', 'empresa_id', 'cuenta_gasto_uuid',
    'movimiento_inventario_uuid'   # <- v3.8+
)

DOCUMENTO_DETAIL_FIELDS = (
    'id', 'uuid', 'consecutivo', 'fecha', 'total', 'subtotal',
    'categoria_contable', 'descripcion', 'observaciones',
    'activo', 'anulado', 'numero_documento_proveedor', 'empresa_id',
    'cuenta_gasto_uuid', 'movimiento_inventario_uuid',  # <- v3.8+
    'resolucion_dian_id', 'proveedor_id', 'created_at', 'updated_at'
)

RESOLUCION_DETAIL_FIELDS = (
    'id', 'uuid', 'numero_resolucion', 'prefijo', 'vigente',
    'rango_desde', 'rango_hasta', 'fecha_resolucion',
    'fecha_inicio', 'fecha_fin', 'clave_tecnica',
    'empresa_id', 'created_at', 'updated_at'
)
```

---

### 3.2 `services/crud_service.py` — Escritura Atomica

#### `ResolucionCRUDService`

| Metodo | Descripcion |
|--------|-------------|
| `crear_resolucion(data, empresa)` | `@transaction.atomic` |
| `desactivar_resolucion(resolucion)` | `@transaction.atomic` — `vigente=False`, invalida cache |
| `actualizar_resolucion(resolucion, data)` | `@transaction.atomic` |
| `eliminar_resolucion(resolucion)` | Elimina si no tiene documentos asociados |
| `_invalidar_cache_vigente(empresa_id)` | Invalida `resolucion_vigente_{empresa_id}` |

#### `DocumentoCRUDService`

| Metodo | Descripcion |
|--------|-------------|
| `crear_documento(empresa, data, resolucion)` | `@transaction.atomic` — consecutivo atomico via `select_for_update` |
| `actualizar_documento(instance, data)` | `@transaction.atomic` |
| `anular_documento(instance, motivo, usuario)` | `@transaction.atomic` — registra trazabilidad completa |
| `desactivar_documento(instance)` | `@transaction.atomic` — soft delete |
| `eliminar_documento(instance)` | Elimina fisicamente si `anulado=True` |

---

### 3.3 `services/business_service.py` — Reglas de Negocio

#### `GastoBusinessService`

| Metodo | Descripcion |
|--------|-------------|
| `procesar_gasto(empresa, data)` | Orquestador principal (ver flujo completo abajo) |
| `materializar_gasto_desde_dto(dto)` | Materializa desde DTO canonico (idempotente) |
| `anular_gasto(gasto_id, motivo, usuario, empresa_id)` | DSV + `DocumentoCRUDService.anular_documento()` |
| `desactivar_gasto(gasto_id, empresa_id)` | DSV + `DocumentoCRUDService.desactivar_documento()` |
| `eliminar_gasto(gasto_id, empresa_id)` | DSV + valida `anulado=True` antes de eliminar |

**Flujo `procesar_gasto(empresa, data)` — v3.10.2:**
```
1. Limpiar campos deprecated (retefuente_porcentaje, reteica_porcentaje, retefuente, reteica)
2. DSV Resolucion: resolucion.empresa_id == empresa.id + vigencia de fecha
3. DSV Proveedor: UUID/ID resilente
4. DSV Movimiento Inventario (v3.8+):
     si data.movimiento_inventario_uuid:
       MovimientoInventarioSelector.get_detail(uuid) -> valida existencia
       almacena en ds_data['movimiento_inventario_uuid']
5. Validar DIAN: fecha dentro del rango de la resolucion
6. Calcular totales via RetencionesService.obtener_retenciones_desde_tercero(PROVEEDOR/COMPRA)
7. DocumentoCRUDService.crear_documento() @transaction.atomic
8. Si retefuente_porcentaje > 0 -> RetencionesService.crear_retencion(tipo='RETEFUENTE', ...)
9. Si reteica_porcentaje > 0 -> RetencionesService.crear_retencion(tipo='RETEICA', ...)
10. return (True, documento, 201)
```

#### `ResolucionBusinessService`

| Metodo | Descripcion |
|--------|-------------|
| `validar_fechas_y_rangos(data)` | Valida `rango_desde < rango_hasta`, `fecha_inicio < fecha_fin` |
| `crear_resolucion(empresa, data)` | Valida + `ResolucionCRUDService.crear_resolucion()` |
| `desactivar_resolucion(empresa_id, resolucion_id)` | DSV + desactivar |
| `puede_eliminar(empresa_id, resolucion_id)` | `(bool, mensaje)` — false si tiene documentos |

---

### 3.4 `services/api_mixins.py` — Inyeccion en ViewSet

#### `GastoServiceMixin`

| Metodo | Descripcion |
|--------|-------------|
| `_get_empresa_id_seguro()` | `tenant_profile.empresa_id` o fallback en DEBUG |
| `get_qs_list()` | `DocumentoSelector.get_list(empresa_id, ...)` |
| `get_qs_detail()` | `DocumentoSelector.get_detail(empresa_id)` |
| `service_crear_gasto(data, empresa)` | `GastoBusinessService.procesar_gasto()` |
| `service_anular_gasto(gasto, motivo, usuario)` | `GastoBusinessService.anular_gasto()` |
| `service_get_summary()` | `DocumentoSelector.get_summary(empresa_id)` |
| `_get_empresa()` | `resolve_tenant_empresa(request, self)` |

#### `ResolucionServiceMixin`

| Metodo | Descripcion |
|--------|-------------|
| `get_qs_list()` | `ResolucionSelector.get_list(empresa_id, ...)` |
| `get_qs_detail()` | `ResolucionSelector.get_detail(empresa_id)` |
| `service_crear_resolucion(empresa, data)` | `ResolucionBusinessService.crear_resolucion()` |
| `service_desactivar_resolucion(empresa_id, resolucion_id)` | `ResolucionBusinessService.desactivar_resolucion()` |
| `service_puede_eliminar(empresa_id, resolucion_id)` | `ResolucionBusinessService.puede_eliminar()` |

---

## 4. API Layer

### 4.1 ViewSets

| ViewSet | Herencia | lookup_field | Acciones |
|---------|----------|-------------|----------|
| `GastoViewSet` | `GastoServiceMixin, SintelDSVMixin, BaseTenantViewSet` | `uuid` (heredado) | CRUD + `anular`, `summary`, `render_offcanvas_crear`, `render_offcanvas_editar`, `render_offcanvas_detalle`, `render_offcanvas_resolucion` |
| `ResolucionDIANViewSet` | `ResolucionServiceMixin, SintelDSVMixin, BaseTenantViewSet` | `uuid` (heredado) | CRUD + `activa`, `desactivar` |

---

### 4.2 Serializers (`api/serializers.py`)

| Serializer | Proposito | Campos clave |
|------------|-----------|-------------|
| `ResolucionDIANNestedSerializer` | Embedding en DocumentoSoporte | campos minimos |
| `ResolucionDIANListSerializer` | GET lista resoluciones | |
| `ResolucionDIANCreateSerializer` | POST/PATCH resoluciones | |
| `ResolucionDIANDetailSerializer` | GET detalle resolucion | |
| `DocumentoSoporteListSerializer` | GET lista gastos (Tabulator) | `movimiento_inventario_uuid` |
| `DocumentoSoporteDetailSerializer` | GET detalle + formularios | `movimiento_inventario_uuid` (writable), `movimiento_referencia` (read-only dict), `cuenta_gasto_label` (SerializerMethodField) |

**Campos clave en `DocumentoSoporteDetailSerializer`:**
```python
# Escritura
movimiento_inventario_uuid  # UUIDField, required=False, allow_null=True

# Solo lectura (SerializerMethodField / @property)
movimiento_referencia  # dict: {tipo, tipo_display, item_nombre, item_codigo, cantidad, item_tipo} | null
cuenta_gasto_label     # str | null
total_retefuente       # Decimal (Pull Model Retencion)
total_reteica          # Decimal (Pull Model Retencion)
```

**`UUIDOrPKRelatedField`:** Campo custom que acepta UUID o PK entero. Filtra por `empresa_id` del contexto del serializer para DSV multi-tenant.

---

### 4.3 Endpoints REST

| Metodo | URL | Descripcion |
|--------|-----|-------------|
| GET | `/api/v1/gastos/` | Lista DS paginada |
| POST | `/api/v1/gastos/` | Crear DS + consecutivo atomico + Retenciones |
| GET | `/api/v1/gastos/{uuid}/` | Detalle completo |
| PATCH | `/api/v1/gastos/{uuid}/` | Actualizar campos editables |
| DELETE | `/api/v1/gastos/{uuid}/` | Eliminar (solo si anulado) |
| POST | `/api/v1/gastos/{uuid}/anular/` | Anular DS (inmutable) |
| GET | `/api/v1/gastos/summary/` | KPIs del mes |
| GET | `/api/v1/gastos/render-offcanvas/crear/` | HTML offcanvas crear |
| GET | `/api/v1/gastos/render-offcanvas/editar/?uuid=...` | HTML offcanvas editar |
| GET | `/api/v1/gastos/render-offcanvas/detalle/?uuid=...` | HTML offcanvas detalle |
| GET | `/api/v1/gastos/resoluciones/` | Lista resoluciones DIAN |
| POST | `/api/v1/gastos/resoluciones/` | Crear resolucion |
| GET | `/api/v1/gastos/resoluciones/{uuid}/` | Detalle resolucion |
| PATCH | `/api/v1/gastos/resoluciones/{uuid}/` | Actualizar resolucion |
| DELETE | `/api/v1/gastos/resoluciones/{uuid}/` | Eliminar resolucion (si no tiene DS) |
| GET | `/api/v1/gastos/resoluciones/activa/` | Resolucion vigente activa |
| POST | `/api/v1/gastos/resoluciones/{uuid}/desactivar/` | Desactivar resolucion |
| GET | `/api/v1/gastos/render-offcanvas/resolucion/?uuid=` | HTML offcanvas crear/editar ResolucionDIAN |

**Orden de registro en Router** (anti-greedy):
```python
router.register(r'resoluciones', ResolucionDIANViewSet, ...)  # PRIMERO
router.register(r'', GastoViewSet, ...)                       # AL FINAL
```
**Motivo:** `r''` genera `^(?P<uuid>[^/.]+)/$` que capturaria `"resoluciones"` como UUID si va primero.

---

## 5. Frontend

### 5.1 JavaScript (`static/gastos/js/`)

| Archivo | Namespace / Responsabilidad |
|---------|----------------------------|
| `gastos.api.js` | SSoT de URLs — `window.Sintel.Gastos.API`: metodos `gastos.*`, `resoluciones.*`, `contabilidad.obtenerRetenciones()`, `inventario.searchMovimientos(q)` |
| `gastos.utils.js` | Helpers con cache: `fetchProveedores()`, `fetchCuentas()`, `fetchResoluciones()`, `loadProveedoresSelect()`, `loadCuentasSelect()`, `loadResolucionesSelect()`, `invalidateCache()` |
| `features/gasto_editor.js` | Editor crear/editar — exports: `init, cargarResoluciones, calcularTotales, initMovimientoSearch` |
| `features/gasto_list.js` | Tabulator: `init()`, `getColumnas()`, `handleCellAction()`, `verDetalle()`, `abrirEditarGasto()`, `anularGasto()`, `eliminarGasto()` |
| `features/resolucion_editor.js` | CRUD resoluciones: `init()`, `submitResolucion()` |

**Export actual de `gasto_editor.js`:**
```javascript
window.Sintel.Gastos.Editor = { init, cargarResoluciones, calcularTotales, initMovimientoSearch };
```

**Funciones internas relevantes (no exportadas):**
- `cargarProveedores(form)`, `actualizarInfoProveedor(form, uuid)`, `obtenerRetencionesProveedor(form, nit)`
- `initCuentaSearch(form)` + `renderSuggestions()` — autocomplete cuentas contables
- `initMovimientoSearch(form)` + `renderMovimientoSuggestions()` — autocomplete movimientos kardex (v3.8+)
- `collectData(form)` — recoge `movimiento_inventario_uuid` del input oculto (NO `producto/servicio/activo_relacionado`)
- `handleSubmit(e)` — POST/PATCH via API

**Funciones ELIMINADAS en v3.8+ (ya no existen en el codigo):**
- ~~`initInventarioSelects(form)`~~
- ~~`cargarProductos(form)`~~
- ~~`cargarServicios(form)`~~
- ~~`cargarActivos(form)`~~

**Seccion `inventario` en `gastos.api.js` (actual):**
```javascript
inventario: {
    searchMovimientos: (q) => `/api/v1/inventario/movimientos/?search=${encodeURIComponent(q)}&page_size=10`,
},
```

**Flujo retenciones en formulario (v3.7.3):**
```
Usuario selecciona Retefuente desde dropdown
  -> #retefuente_select -> #retefuente_porcentaje (hidden) = valor
  -> calcularTotales():
       subtotal    = parseFloat(#base_gravable.value)
       retefuente  = subtotal * porcentaje_retefuente / 100
       reteica     = subtotal * porcentaje_reteica    / 100
       total       = subtotal - retefuente - reteica
  -> actualiza #retefuente_display, #reteica_display, #total_display
On save: backend recibe subtotal + total -> crea Retencion via Pull Model
```

**Flujo movimiento inventario (v3.8+):**
```
Usuario escribe >= 2 chars en #movimiento_inventario_search
  -> debounce 300ms -> GET /api/v1/inventario/movimientos/?search=...
  -> renderMovimientoSuggestions() muestra dropdown
  -> usuario selecciona -> #movimiento_inventario_uuid.value = UUID del movimiento
On save: collectData() incluye movimiento_inventario_uuid en el payload
```

---

### 5.2 Templates HTML (`templates/tenant/gastos/`)

| Template | Proposito |
|----------|-----------|
| `gastos_list.html` | Lista principal con Tabulator + botones crear, filtrar |
| `list.html` | Wrapper minimo (incluye `gastos_list.html`) |
| `offcanvas_crear_gasto.html` | Form crear DS: resolucion, proveedor, base gravable, selectores retenciones, cuenta contable, buscador movimiento |
| `offcanvas_editar_gasto.html` | Form editar DS: misma estructura con datos precargados |
| `offcanvas_detalle_gasto.html` | Vista read-only: todos los campos + retenciones + movimiento vinculado |
| `offcanvas_resolucion.html` | Form crear/editar ResolucionDIAN |
| `assets_gastos.html` | Include CSS/JS del modulo |

**Secciones en `offcanvas_crear_gasto.html` y `offcanvas_editar_gasto.html`:**
```
1. Documento Soporte: resolucion_dian (select), consecutivo (auto), fecha
2. Informacion Proveedor: proveedor (select), NIT/direccion/telefono (display)
3. Valores:
   - Base Gravable: #base_gravable (editable)
   - Retefuente: #retefuente_select (dropdown) + #retefuente_display (readonly)
   - ReteICA: #reteica_select (dropdown) + #reteica_display (readonly)
   - Total: #total_display (calculado)
   - Ocultos: #retefuente_porcentaje, #reteica_porcentaje
4. Categorizacion Contable: categoria_contable + cuenta_gasto_uuid (autocomplete)
5. Movimiento de Inventario (Opcional) — Pull Model v3.8+:
   - #movimiento_inventario_search (texto, autocomplete)
   - #movimiento_inventario_uuid (hidden, valor enviado al backend)
   - #movimiento-inventario-suggestions (dropdown sugerencias)
6. Observaciones: textarea
```

**Seccion movimiento en `offcanvas_detalle_gasto.html`:**
```django
{% if instance.movimiento_referencia %}
  Movimiento de Inventario Vinculado:
    tipo_display, item_nombre, item_codigo (si existe), cantidad (si existe)
{% endif %}
```

---

## 6. Tests (`tests/` — 6 archivos)

| Archivo | Proposito |
|---------|-----------|
| `conftest.py` | Fixtures multi-tenant: `tenant1`, `tenant2` con schemas aislados |
| `test_auth_session_smoke.py` | Smoke test de autenticacion |
| `test_fase9_persistence.py` | Tests de persistencia (fase 9 Contabilidad) |
| `test_gastos_login_session_loop.py` | Tests de sesion en loop |
| `test_multitenant_isolation.py` | Verifica aislamiento por schema entre `tenant1` y `tenant2` |
| `test_proveedor_integration.py` | Integracion con modulo Proveedores |

---

## 7. Checklist AGENTS.md — Estado de Cumplimiento

| Regla | Estado | Detalle |
|-------|--------|---------|
| `SintelTenantBaseModel` | OK | `ResolucionDIAN` y `DocumentoSoporte` |
| `empresa_id` en queries | OK | Todos los selectores filtran por `empresa_id` |
| `.only()` en querysets | OK | 4 constantes LIST/DETAIL_FIELDS |
| `lookup_field = 'uuid'` | OK | Ambos ViewSets (heredado de `BaseTenantViewSet`) |
| UUID en modelos | OK | Migracion 0016 |
| No signals para negocio | OK | Service Layer exclusivo |
| `@transaction.atomic` en CRUD | OK | Todos los metodos CRUD |
| `BaseTenantViewSet` sin override auth | OK | Ningun ViewSet sobreescribe `authentication_classes` |
| FK a `perfil.TenantProfile` (no `AUTH_USER_MODEL`) | OK | `usuario_anulacion` FK a `TenantProfile` |
| Pull Model retenciones (ADR-001) | OK | `@property` lee de `Contabilidad.Retencion`, `editable=False` en deprecated |
| Pull Model inventario (v3.8+) | OK | `movimiento_inventario_uuid` UUID opaco, DSV via `MovimientoInventarioSelector` |
| Sin FK directos a Producto/Servicio/ActivoFijo | OK | Eliminados en mig 0019 |
| Router anti-greedy | OK | `r'resoluciones'` registrado ANTES que `r''` |
| Sincronia CHOICES templates | OK | `RETEFUENTE_CHOICES`/`RETEICA_CHOICES` en `models.py` — templates sincronizados |
| `APP_ORIGEN_PREFIJOS['gastos']` en Contabilidad | OK | `cuenta_gasto_uuid` valida contra prefijos de contabilidad |
| Imports globales (no dentro de `def`) | OK | `business_service.py`: `DocumentoCRUDService`/`ResolucionCRUDService` movidos a globales (v3.10.3). Imports cross-app (`Proveedor`, `MovimientoInventarioSelector`, `RetencionesService`) permanecen lazy — justificado para evitar circulares. `models.py` @property: excepcion justificada |

---

## 8. Historial de Cambios

### v3.8+ — Pull Model Inventario (mig 0018 + 0019)

Sustitucion completa del patron FK directo a inventario por UUID opaco:

| Antes (eliminado) | Despues (actual) |
|-------------------|-----------------|
| `producto_relacionado` FK a Producto | `movimiento_inventario_uuid` UUIDField nullable |
| `servicio_relacionado` FK a Servicio | `movimiento_referencia` @property (Pull Model) |
| `activo_relacionado` FK a ActivoFijo | `initMovimientoSearch()` en JS (autocomplete unificado) |
| `initInventarioSelects()` + 3 `cargar*()` | `renderMovimientoSuggestions()` |
| `gastos.api.inventario.{productos,servicios,activos}` | `gastos.api.inventario.searchMovimientos(q)` |
| `tipo_relacion_inventario` + 3 selects en templates | `#movimiento_inventario_search` + `#movimiento_inventario_uuid` |
| `{% if instance.producto_relacionado %}` en detalle | `{% if instance.movimiento_referencia %}` |

### v3.7.5 — Router Greedy Fix + Precargar Editar

- `r'resoluciones'` antes de `r''` en `api/urls.py`
- Precargar base gravable, retenciones y cuenta contable al abrir offcanvas editar

### v3.7.3 — Selectores de Retenciones UI

Usuario selecciona tipo desde dropdown; calculo en tiempo real; Pull Model para persistencia.

### v3.7.1 — Pull Model Retenciones (ADR-001)

Campos `retefuente*`/`reteica*` marcados `editable=False`. Datos viven en `Contabilidad.Retencion`.

---

## 9. Deuda Tecnica

| ID | Archivo | Severidad | Descripcion | Estado |
|----|---------|-----------|-------------|--------|
| DEUDA-01 | `models.py` — `retefuente*`/`reteica*` | MEDIA | Campos `editable=False` DEPRECATED v3.7.1 aun en modelo. Eliminar en v3.9.0 segun cleanup plan (2026-08). | Mitigado — `editable=False`, pendiente migracion de borrado |
| DEUDA-02 | `services/selectors.py` | BAJA | Exportar LIST/DETAIL_FIELDS como dict vs tuplas — inconsistencia historica | RESUELTO (v3.9.1) |
| DEUDA-03 | `choices/` directory | BAJA | `centros_costo.py`, `niif_gastos_choices.py` obsoletos | RESUELTO (v3.9.1) |
| DEUDA-04 | `gasto_editor.js` | BAJA | Archivo largo — candidato a fragmentar en submódulos | Pendiente |
| DEUDA-05 | `models.py` imports locales en `@property` | BAJA | Repetitivo — centralizar con helper `_get_retencion_model()` | RESUELTO (v3.9.1) |
| DEUDA-06 | Tests | MEDIA | Faltan tests para `procesar_gasto()`, consecutivos atomicos, Pull Model retenciones, `movimiento_inventario_uuid` DSV | Pendiente |
| DEUDA-07 | `business_service.py` — imports locales crud | BAJA | `DocumentoCRUDService`/`ResolucionCRUDService` importados localmente 8 veces | ✅ **RESUELTO v3.10.3** — movidos a imports globales |
| DEUDA-08 | `viewsets.py` | BAJA | `from django.conf import settings` dentro de `get_permissions()` — import inofensivo pero estilo incorrecto | Pendiente |

---

## 10. Patrones Clave

### 10.1 Consecutivo Atomico

```
DocumentoCRUDService.crear_documento():
  @transaction.atomic
  -> ResolucionDIAN.objects.select_for_update().get(id=resolucion_id)
  -> consecutivo = resolucion.consecutivo
  -> DS.clean() -> valida rango
  -> resolucion.consecutivo += 1; resolucion.save()
  -> DocumentoSoporte.objects.create(consecutivo=consecutivo, ...)
```

### 10.2 Pull Model Retenciones (ADR-001 v3.7.1)

```python
DocumentoSoporte.total_retefuente  # @property
  -> Contabilidad.Retencion.objects.filter(
       tipo='RETEFUENTE',
       documento_origen_app='gastos',
       documento_origen_modelo='DocumentoSoporte',
       documento_origen_id=self.id,
       reversada=False
     ).aggregate(Sum('monto'))
```

### 10.3 Pull Model Inventario (v3.8+)

```python
DocumentoSoporte.movimiento_referencia  # @property
  -> si not self.movimiento_inventario_uuid: return None
  -> MovimientoInventarioSelector.get_detail(self.movimiento_inventario_uuid)
  -> return {tipo, tipo_display, item_nombre, item_codigo, cantidad, item_tipo}
```

En `procesar_gasto`:
```python
if movimiento_inventario_uuid:
    movimiento = MovimientoInventarioSelector.get_detail(movimiento_inventario_uuid)
    if not movimiento:
        raise ValidationError("Movimiento de inventario no encontrado (DSV)")
    ds_data['movimiento_inventario_uuid'] = movimiento_inventario_uuid
```

### 10.4 Cache Resolucion Vigente

```python
cache_key = f"resolucion_vigente_{empresa_id}"
# TTL: 1 hora
# Invalidado en: crear_resolucion() si vigente=True
#               desactivar_resolucion()
```

### 10.5 Inmutabilidad por Anulacion

```
DS.activo=True, DS.anulado=False  -> Activo, editable
DS.activo=False                   -> Desactivado, no editable
DS.anulado=True                   -> Anulado; eliminar fisicamente permitido
Consecutivo: NUNCA reutilizable (constraint unique)
```

---

## 11. Flujo Completo: Crear Documento Soporte

```
[Frontend offcanvas_crear_gasto.html]
  usuario selecciona proveedor -> obtenerRetencionesProveedor()
    -> GET /api/v1/contabilidad/retenciones/obtener-por-tercero/?nit=NIT&tipo=PROVEEDOR&naturaleza=COMPRA
    -> Pre-llena dropdown Retefuente/ReteICA
  usuario escribe en #movimiento_inventario_search (opcional) -> initMovimientoSearch()
    -> GET /api/v1/inventario/movimientos/?search=...
    -> usuario selecciona -> #movimiento_inventario_uuid = UUID
  usuario ingresa Base Gravable -> calcularTotales()
    -> retefuente = base * pct / 100
    -> total = base - retefuente - reteica
  usuario confirma -> POST /api/v1/gastos/
    Body: {resolucion_dian, proveedor, fecha, subtotal, total,
           retefuente_porcentaje, reteica_porcentaje,
           categoria_contable, cuenta_gasto_uuid, descripcion,
           movimiento_inventario_uuid (nullable)}
      |
[GastoViewSet.create()]
  -> service_crear_gasto(data, empresa)
      |
[GastoBusinessService.procesar_gasto(empresa, data)]
  -> DSV resolucion + proveedor + movimiento_inventario_uuid
  -> DocumentoCRUDService.crear_documento() @transaction.atomic
       -> select_for_update resolucion
       -> consecutivo atomico
       -> DocumentoSoporte.objects.create(movimiento_inventario_uuid=uuid, ...)
  -> RetencionesService.crear_retencion(RETEFUENTE / RETEICA) si > 0
  -> return (True, documento, 201)
      |
[Response 201 + serialized DocumentoSoporte]
  -> gasto_list.js: table.replaceData()
```

---

## 12. Flujo Completo: Anular Documento Soporte

```
[gasto_list.js] usuario clic "Anular"
  -> confirma en modal con campo motivo
  -> POST /api/v1/gastos/{uuid}/anular/
    Body: {motivo: "descripcion del motivo"}
      |
[GastoViewSet.anular()]
  -> get_object() -> DS con empresa_id verificado
  -> service_anular_gasto(instance, motivo, request.user)
      |
[GastoBusinessService.anular_gasto(gasto_id, motivo, usuario, empresa_id)]
  -> DSV: DS.empresa_id == empresa_id
  -> DocumentoCRUDService.anular_documento(instance, motivo, usuario_profile)
       @transaction.atomic
       -> DS.anulado = True
       -> DS.fecha_anulacion = timezone.now()
       -> DS.motivo_anulacion = motivo
       -> DS.usuario_anulacion = usuario_profile (TenantProfile)
       -> DS.save()
      |
[Response 200 + {detail: "Documento anulado"}]
  -> gasto_list.js: table.replaceData() -> fila con badge "Anulado"
```
