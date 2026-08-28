# Auditoría Flujo Completo — Módulo Inventario

**Versión auditada:** v3.10.2
**Fecha:** 2026-05-28
**Estado:** PRODUCTION READY (0 CRÍTICOS) — histórico, ver nota 2026-08-27 abajo
**Auditor:** Claude Code (claude-sonnet-4-6)
**Ubicación:** `apps/tenant/inventario/`

> **DRIFT CONFIRMADO 2026-08-27** (misión de modernización integral): el módulo
> evolucionó de forma real desde esta auditoría (F21 Traslados entre Sedes,
> `MovimientoInventario.sede`/`documento_origen_*`, idempotencia por
> documento origen) sin que este documento se actualizara. Ver
> `docs/inventario/INVENTARIO_BASELINE.md` y el resto de
> `docs/inventario/INVENTARIO_*.md` para el estado real verificado contra
> código. Correcciones puntuales aplicadas abajo donde el drift era engañoso
> (costo_promedio, DEUDA-04/05/08); el resto del documento permanece como
> referencia histórica de v3.10.2, no como fuente de verdad vigente.

---

## 1. Responsabilidades del Módulo

| # | Responsabilidad | Estado |
|---|----------------|--------|
| 1 | **Catálogo Multitipo** — Gestión diferenciada de Productos (stock), Servicios (intangibles) y Activos Fijos (uso interno) | ✅ |
| 2 | **Motor Kardex** — `KardexService` con `select_for_update()`: movimientos append-first, `stock_actual` desnormalizado recalculado atómicamente | ✅ |
| 3 | **Kardex de Activos** — `KardexService.registrar_movimiento_activo()` gestiona ciclo de vida de `ActivoFijo` con transiciones de estado automáticas | ✅ (mig 0006) |
| 4 | **Mutabilidad Controlada de Movimientos** — `actualizar_movimiento` + `eliminar_movimiento` en `KardexService` con recálculo atómico de stock | ✅ (v3.9.1) |
| 5 | **Ingesta Masiva** — Pipeline desde Excel: `IngestaService.materializar_carga_masiva_productos()` con auto-creación de categorías | ✅ |
| 6 | **Desacoplamiento Contable Completo** — Campos `cuenta_*_uuid` eliminados de todos los modelos (mig 0009). Contabilidad es única propietaria de mapeos PUC via Pull Model (v3.10.2) | ✅ (mig 0009) |
| 7 | **Aislamiento Contable** — Contabilidad consume Inventario solo mediante `get_movimientos_timeline()` / Movimientos Recientes; no consulta `Producto`, `Servicio` ni `ActivoFijo` directamente | ✅ |
| 8 | **UUID Lookup** — `lookup_field = 'uuid'` en todos los ViewSets (mig 0005) | ✅ |
| 9 | **Prefijos PUC en `APP_ORIGEN_PREFIJOS`** — `'51'` incluido en `APP_ORIGEN_PREFIJOS['inventario']` para depreciación de Activos Fijos (v3.7.2) | ✅ (v3.7.2) |
| 10 | **Vinculación Gastos** — `MovimientoInventario` almacena soft-ref `factura_uuid` / `factura_numero`; referenciado por Gastos via `movimiento_inventario_uuid` (Pull Model v3.8+) | ✅ (mig 0007) |
| 11 | **Ledger Universal / Movimientos Recientes** — `get_movimientos_timeline()` combina Productos + Activos + Servicios en un único historial ordenado cronológicamente, expone `documento_id`/`modelo_origen`, y es el contrato autorizado para Contabilidad | ✅ |
| 12 | **Vinculación Proyectos en HistorialServicio** — Endpoint `vincular_proyecto` agrega `proyecto_uuid`/`nombre` como soft-ref en historial de servicios | ✅ (mig 0008) |

---

## 2. Modelos

### 2.1 `TimeStampedModel` (abstracto)
**Herencia:** `SintelTenantBaseModel` ✅

| Campo | Tipo | Notas |
|-------|------|-------|
| `created_at` | DateTimeField | `default=timezone.now, editable=False` |
| `updated_at` | DateTimeField | `auto_now=True` |

---

### 2.2 `CategoriaItem`
**Herencia:** `TimeStampedModel` → `SintelTenantBaseModel` ✅
**Ordering:** `['nombre']`

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `unique=True, db_index=True, editable=False` ✅ |
| `empresa` | FK → `Empresa` | `PROTECT, related_name='categorias_inventario'` |
| `nombre` | CharField(100) | `db_index=True` |
| `descripcion` | TextField | blank=True |
| `aplicacion` | CharField(16) | Choices: `TODO / PRODUCTO / SERVICIO / ACTIVO` |
| `imagen` | ImageField | `upload_to='inventario/categorias/'`, nullable |
| `activo` | BooleanField | `default=True` |

> **v3.10.2:** Campos `cuenta_inventario_uuid`, `cuenta_costo_uuid`, `cuenta_ingreso_uuid` eliminados (mig 0009). El mapeo contable es responsabilidad exclusiva de Contabilidad.

**Índices BD:** `(empresa, nombre)`
**Constraint:** `UNIQUE(Lower('nombre'), empresa)` → `unique_categoria_nombre_per_empresa`

---

### 2.3 `ActivoFijo`
**Herencia:** `TimeStampedModel` → `SintelTenantBaseModel` ✅
**Ordering:** `['nombre']`

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `unique=True, db_index=True, editable=False` ✅ |
| `empresa` | FK → `Empresa` | `PROTECT, related_name='activos_fijos'` |
| `categoria` | FK → `CategoriaItem` | `SET_NULL`, `limit_choices_to={aplicacion__in: [ACTIVO, TODO]}` |
| `codigo` | CharField(64) | Placa, serial o identificador único |
| `nombre` | CharField(200) | `db_index=True` |
| `marca` / `modelo` | CharField(100) | blank=True |
| `descripcion` | TextField | blank=True |
| `imagen` | ImageField | `upload_to='inventario/activos/'`, nullable |
| `ubicacion` / `responsable` | CharField(100) | blank=True |
| `fecha_adquisicion` | DateField | nullable |
| `costo_adquisicion` | DecimalField(14,2) | `default=0` |
| `estado` | CharField(20) | Choices: `ACTIVO / MANTENIMIENTO / BAJA / VENDIDO` |

> **v3.10.2:** Campos `cuenta_activo_uuid` (PUC Activo, prefijo `15xxxx`) y `cuenta_depreciacion_uuid` (PUC Depreciación, prefijo `51xxxx`) eliminados (mig 0009). El mapeo contable es responsabilidad exclusiva de Contabilidad.

**Índices BD:** `(codigo)`, `(empresa)`
**Constraint:** `UNIQUE(Lower('codigo'), empresa)` → `unique_activo_codigo_per_empresa`

---

### 2.4 `Producto`
**Herencia:** `TimeStampedModel` → `SintelTenantBaseModel` ✅
**Ordering:** `['nombre']`

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `unique=True, db_index=True, editable=False` ✅ |
| `empresa` | FK → `Empresa` | `PROTECT, related_name='productos_venta'` |
| `codigo` | CharField(64) | SKU único |
| `nombre` | CharField(200) | `db_index=True` |
| `categoria` | FK → `CategoriaItem` | `SET_NULL`, `limit_choices_to={aplicacion__in: [PRODUCTO, TODO]}` |
| `descripcion` | TextField | blank=True |
| `unidad` | CharField(16) | `default='UND'` |
| `imagen` | ImageField | `upload_to='inventario/productos/'`, nullable |
| `precio_venta` | DecimalField(14,2) | `default=0` |
| `costo_promedio` | DecimalField(14,2) | `default=0` — **CORREGIDO 2026-08-27**: es un campo ESTÁTICO, nunca recalculado automáticamente por ninguna entrada (ni `ENTRADA_COMPRA` ni ninguna otra). Poblado manualmente o por ingesta. Decisión arquitectónica deliberada, ver `documentacion/F23_SALE_INVENTORY_CONTRACT.md` §6. La afirmación original de esta fila era incorrecta. |
| `stock_actual` | DecimalField(14,3) | **desnormalizado** — recalculado por `KardexService.recalcular_stock_producto()` |
| `stock_minimo` | DecimalField(14,3) | `default=0` — para alertas de reposición |
| `activo` | BooleanField | `default=True` |

> **v3.10.2:** Campos `cuenta_inventario_uuid` (PUC Activo circulante, p.ej. `143505`) y `cuenta_costo_uuid` (PUC Costo de ventas, p.ej. `6135xx`) eliminados (mig 0009).

**Índices BD:** `(codigo)`, `(empresa, nombre)`
**Constraint:** `UNIQUE(Lower('codigo'), empresa)` → `unique_producto_codigo_per_empresa`

---

### 2.5 `Servicio`
**Herencia:** `TimeStampedModel` → `SintelTenantBaseModel` ✅
**Ordering:** `['nombre']`

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `unique=True, db_index=True, editable=False` ✅ |
| `empresa` | FK → `Empresa` | `PROTECT, related_name='servicios_venta'` |
| `codigo` | CharField(64) | |
| `nombre` | CharField(200) | `db_index=True` |
| `categoria` | FK → `CategoriaItem` | `SET_NULL`, `limit_choices_to={aplicacion__in: [SERVICIO, TODO]}` |
| `descripcion` | TextField | blank=True |
| `imagen` | ImageField | `upload_to='inventario/servicios/'`, nullable |
| `precio_venta` | DecimalField(14,2) | `default=0` |
| `activo` | BooleanField | `default=True` |

> **v3.10.2:** Campo `cuenta_ingreso_uuid` (PUC Ingresos, p.ej. `4135xx`, `4175xx`) eliminado (mig 0009).

**Índices BD:** `(empresa, nombre)`
**Constraint:** `UNIQUE(Lower('codigo'), empresa)` → `unique_servicio_codigo_per_empresa`

---

### 2.6 `MovimientoInventario` (Kardex — append-first)
**Herencia:** `TimeStampedModel` → `SintelTenantBaseModel` ✅
**Ordering:** `['-created_at']`

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `unique=True, db_index=True, editable=False` ✅ |
| `empresa` | FK → `Empresa` | `PROTECT, related_name='movimientos_inventario'` |
| `producto` | FK → `Producto` | `CASCADE, null=True, blank=True` |
| `activo_fijo` | FK → `ActivoFijo` | `CASCADE, null=True, blank=True` — agregado mig 0006 |
| `tipo` | CharField(20) | `TipoMovimiento` choices (ver abajo) |
| `cantidad` | DecimalField(14,3) | |
| `costo_unitario` | DecimalField(14,2) | `default=0` |
| `factura_uuid` | UUIDField | nullable — soft-ref a Factura (mig 0007) |
| `factura_numero` | CharField | nullable — snapshot número (mig 0007) |
| `origen_referencia` | CharField(100) | nullable |
| `cliente_referencia` | CharField(200) | nullable |
| `observaciones` | TextField | nullable |

**Choices `TipoMovimiento`:**
```
Para Productos:
  ENTRADAS:  ENTRADA_COMPRA | ENTRADA_AJUSTE | ENTRADA_DEVOLUCION
  SALIDAS:   SALIDA_VENTA   | SALIDA_BAJA    | SALIDA_CONSUMO

Para Activos:
  ASIGNACION_RESPONSABLE | TRASLADO_MANTENIMIENTO | RETORNO_MANTENIMIENTO | SALIDA_BAJA_ACTIVO
```

**CheckConstraint:** `exactly_one_product_or_asset` — exactamente uno de `producto` o `activo_fijo` debe ser no nulo.

**Índices BD:** `(empresa, created_at)`, `(producto, created_at)`, `(activo_fijo, created_at)`

> **Nota Mutabilidad (v3.9.1):** El ViewSet expone `partial_update` y `destroy` con recálculo atómico de stock via `KardexService.actualizar_movimiento()` / `eliminar_movimiento()`.

---

### 2.7 `HistorialServicio` (Log de Ventas)
**Herencia:** `TimeStampedModel` → `SintelTenantBaseModel` ✅
**Ordering:** `['-fecha_registro']`

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `unique=True, db_index=True, editable=False` ✅ |
| `empresa` | FK → `Empresa` | `PROTECT, related_name='historial_servicios'` |
| `servicio` | FK → `Servicio` | `CASCADE, related_name='historial_ventas'` |
| `fecha_registro` | DateField | `default=timezone.now` |
| `cantidad` | DecimalField(10,2) | `default=1` |
| `valor_cobrado` | DecimalField(14,2) | `default=0` |
| `origen_referencia` | CharField(100) | nullable |
| `cliente_referencia` | CharField(200) | nullable |
| `observaciones` | TextField | nullable |
| `proyecto_uuid` | UUIDField | nullable — soft-ref a Proyecto (mig 0008) |
| `proyecto_nombre` | CharField | nullable — snapshot nombre (mig 0008) |

**Índices BD:** `(empresa, fecha_registro)`

---

### 2.8 Migraciones (9 total)

| # | Archivo | Cambio Principal |
|---|---------|-----------------|
| 0001 | `0001_initial.py` | Creación de los 6 modelos: CategoriaItem, ActivoFijo, Producto, Servicio, MovimientoInventario, HistorialServicio |
| 0002 | `...unique_categoria_nombre_per_empresa.py` | Constraint `UNIQUE(Lower('nombre'), empresa)` en CategoriaItem |
| 0003 | `...activofijo_cuenta_contable_uuid_and_more.py` | Agrega campos UUID contables a ActivoFijo, Producto, Servicio, CategoriaItem |
| 0004 | `...rename_cuenta_contable_uuid_activofijo_cuenta_activo_uuid.py` | Renombra campos contables en ActivoFijo (`cuenta_activo_uuid`, `cuenta_depreciacion_uuid`) + constraints código único |
| 0005 | `...uuid_lookup_and_tenant_code_constraints.py` | **UUID fields** en todos los modelos + constraints `unique_*_codigo_per_empresa` + `RunPython populate_uuids` |
| 0006 | `...movimientoinventario_activo_fijo_and_more.py` | Agrega FK `activo_fijo` a `MovimientoInventario` + `CheckConstraint exactly_one_product_or_asset` + tipos de movimiento para activos |
| 0007 | `...add_factura_vinculacion_movimiento.py` | Agrega soft-ref `factura_uuid` / `factura_numero` a `MovimientoInventario` |
| 0008 | `...historialservicio_proyecto_nombre_and_more.py` | Agrega soft-ref `proyecto_uuid` / `proyecto_nombre` a `HistorialServicio` |
| **0009** | `...remove_activofijo_cuenta_activo_uuid_and_more.py` | **Elimina 8 campos `cuenta_*_uuid`** de CategoriaItem (3), Producto (2), Servicio (1), ActivoFijo (2) — Desacoplamiento contable completo (v3.10.2) |

---

## 3. Service Layer (FSD)

### 3.1 `services/selectors.py` — Lectura Zero-Waste

**Constantes SSoT (campos optimizados):**
```python
CATEGORIA_LIST_FIELDS    = (7 campos: id, uuid, nombre, aplicacion, activo, empresa_id, imagen)
CATEGORIA_DETAIL_FIELDS  = (8 campos: + descripcion)
PRODUCTO_LIST_FIELDS     = (11 campos: id, uuid, codigo, nombre, precio_venta, costo_promedio,
                             stock_actual, stock_minimo, activo, empresa_id, categoria_id)
PRODUCTO_DETAIL_FIELDS   = (13 campos: + descripcion, unidad, imagen, created_at, updated_at)
SERVICIO_LIST_FIELDS     = (6 campos: id, uuid, codigo, nombre, precio_venta, activo, empresa_id)
SERVICIO_DETAIL_FIELDS   = (9 campos: + descripcion, imagen, created_at, updated_at)
ACTIVO_LIST_FIELDS       = (11 campos: id, uuid, codigo, nombre, marca, estado, costo_adquisicion,
                             empresa_id, categoria_id, fecha_adquisicion, responsable)
ACTIVO_DETAIL_FIELDS     = (13 campos: + modelo, descripcion, imagen, ubicacion,
                             created_at, updated_at)
MOVIMIENTO_LIST_FIELDS   = (13 campos: id, uuid, tipo, cantidad, costo_unitario, created_at,
                             origen_referencia, empresa_id, producto_id, activo_fijo_id + refs)
MOVIMIENTO_DETAIL_FIELDS = (13 campos: + observaciones, cliente_referencia)
```

> **v3.10.2:** Todos los campos `cuenta_*_uuid` eliminados de las constantes `*_LIST_FIELDS` y `*_DETAIL_FIELDS`.

**Clases Selector (todas `@staticmethod`):**

| Clase | Métodos |
|-------|---------|
| `ProductoSelector` | `get_list(empresa_id, search)`, `get_detail(empresa_id, producto_uuid)`, `get_by_id(empresa_id, producto_id)` |
| `ServicioSelector` | `get_list(empresa_id, search)`, `get_detail(empresa_id, servicio_uuid)`, `get_by_id(empresa_id, servicio_id)` |
| `ActivoFijoSelector` | `get_list(empresa_id, search)`, `get_detail(empresa_id, activo_uuid)`, `get_by_id(empresa_id, activo_id)` — busca en `codigo`, `nombre`, `categoria__nombre`, `ubicacion`, `responsable` |
| `MovimientoInventarioSelector` | `get_list(empresa_id, search)`, `get_detail(empresa_id, movimiento_uuid)`, `get_kardex_for_producto(empresa_id, producto_id)` — `select_related('producto', 'activo_fijo')` |
| `CategoriaItemSelector` | `get_list(empresa_id, search)`, `get_detail(empresa_id, categoria_uuid)`, `get_by_id(empresa_id, categoria_id)` |
| `HistorialServicioSelector` | `get_list(empresa)` — `select_related('servicio')` |

**Función Ledger Universal:**
```python
get_movimientos_timeline(empresa_id, search=None)
```
Combina `MovimientoInventario` + `HistorialServicio` en una lista unificada de dicts con datetime normalizado para ordenación cronológica. Es la SSoT del endpoint `/movimientos/timeline/` y el contrato autorizado para el Extractor de Contabilidad.

**Helpers:** `get_empresa_singleton()`, `_obtener_empresa_singleton()`

---

### 3.2 `services/crud_service.py` — Escritura Atómica

Todas las funciones son `@transaction.atomic`:

| Función | Descripción |
|---------|-------------|
| `crear_producto(empresa, codigo, nombre, *, categoria, ...)` | Crea Producto — todos los campos opcionales via `**kwargs` |
| `actualizar_producto(*, producto, **kwargs)` | Actualiza solo los campos recibidos |
| `crear_servicio(empresa, codigo, nombre, *, categoria, ...)` | Crea Servicio |
| `actualizar_servicio(*, servicio, **kwargs)` | Actualiza Servicio |
| `crear_activo(empresa, codigo, nombre, *, categoria, ...)` | Crea ActivoFijo |
| `actualizar_activo(*, activo, **kwargs)` | Actualiza ActivoFijo |
| `crear_movimiento_raw(empresa, producto, tipo, cantidad, ...)` | Crea `MovimientoInventario` sin recalcular stock (lo hace `KardexService`) |

---

### 3.3 `services/business_service.py` — Reglas de Negocio

#### `KardexService` — Motor de Stock

```python
TIPOS_ENTRADA = (ENTRADA_COMPRA, ENTRADA_AJUSTE, ENTRADA_DEVOLUCION)
TIPOS_SALIDA  = (SALIDA_VENTA, SALIDA_BAJA, SALIDA_CONSUMO)

_TRANSICION_ESTADO_ACTIVO = {
    ASIGNACION_RESPONSABLE:  ACTIVO,
    TRASLADO_MANTENIMIENTO:  MANTENIMIENTO,
    RETORNO_MANTENIMIENTO:   ACTIVO,
    SALIDA_BAJA_ACTIVO:      BAJA,
}
```

| Método | Descripción |
|--------|-------------|
| `calcular_stock(producto_id, empresa_id)` | `SUM(entradas) - SUM(salidas)` para el producto del tenant |
| `recalcular_stock_producto(producto_id, empresa_id)` | `@transaction.atomic + select_for_update()` — recalcula y persiste `Producto.stock_actual` |
| `registrar_movimiento(**kwargs)` | `@transaction.atomic` — detecta tipo, valida stock suficiente para salidas, crea `MovimientoInventario`, recalcula stock |
| `registrar_entrada(**kwargs)` | Wrapper con default `tipo=ENTRADA_COMPRA` |
| `registrar_salida(**kwargs)` | Wrapper con default `tipo=SALIDA_VENTA` |
| `ajustar_stock(producto_id, empresa_id, cantidad_ajuste, observaciones)` | `@transaction.atomic` — `cantidad > 0` → ENTRADA_AJUSTE; `< 0` → SALIDA_BAJA |
| `registrar_movimiento_activo(**kwargs)` | `@transaction.atomic` — crea `MovimientoInventario` para `ActivoFijo`; actualiza `ActivoFijo.estado` via `_TRANSICION_ESTADO_ACTIVO` |
| `actualizar_movimiento(movimiento, empresa_id, nueva_cantidad, nuevo_tipo, ...)` | `@transaction.atomic` — edita movimiento existente + recalcula `stock_actual` si cambia cantidad o tipo |
| `eliminar_movimiento(movimiento, empresa_id)` | `@transaction.atomic` — elimina movimiento + recalcula `stock_actual` |

**Invariante de stock:**
```
stock_actual = SUM(cantidad WHERE tipo IN TIPOS_ENTRADA)
             - SUM(cantidad WHERE tipo IN TIPOS_SALIDA)
```

#### `IngestaService` — Carga Masiva

| Método | Descripción |
|--------|-------------|
| `materializar_inventario_desde_dto(dto)` | Crea o actualiza Producto/Servicio/ActivoFijo desde DTO; crea movimiento inicial si `stock_inicial > 0` |
| `materializar_carga_masiva_productos(empresa_id, lista_datos, usuario)` | Procesa lista de DTOs desde Excel: auto-crea categorías, retorna `{creados, actualizados, errores}` |

#### Service Mixins (inyectados en ViewSets)

| Mixin | Métodos clave |
|-------|---------------|
| `CategoriaItemServiceMixin` | `service_categoria_destroy()`, `service_categoria_get_resumen()`, `service_categoria_get_offcanvas_context()` |
| `ProductoServiceMixin` | `service_producto_destroy()`, `service_producto_ajustar_stock()`, `service_producto_get_stock()`, `service_producto_get_kardex()`, `service_producto_get_offcanvas_context()` |
| `ServicioServiceMixin` | `service_servicio_destroy()`, `service_servicio_get_offcanvas_context()`, `service_servicio_get_historial_context()` |
| `ActivoFijoServiceMixin` | `service_activo_destroy()`, `service_activo_list_all()`, `service_activo_get_offcanvas_context()` |
| `MovimientoServiceMixin` | `service_movimiento_perform_create(serializer, empresa)`, `service_movimiento_perform_update(instance, validated_data, empresa)`, `service_movimiento_perform_destroy(instance, empresa)`, `service_movimiento_get_offcanvas_context()` |
| `HistorialServiceMixin` | `service_historial_get_queryset(empresa)` |

---

## 4. API Layer

### 4.1 ViewSets

**Base:** `BaseViewSet(BaseTenantViewSet)` — provee:
- Permission classes: `[IsTenantMember, IsTenantAdminOrReadOnly]`
- `perform_create(serializer)` → inyecta `empresa`
- `get_serializer_context()` → `{request, empresa, empresa_id}`
- `list()` → formato `{count, next, previous, results}`

| ViewSet | Herencia | lookup_field | Acciones |
|---------|----------|-------------|----------|
| `CategoriaItemViewSet` | `BaseViewSet + CategoriaItemServiceMixin` | `uuid` | CRUD + `resumen`, `gestor_offcanvas` |
| `ProductoViewSet` | `BaseViewSet + ProductoServiceMixin` | `uuid` | CRUD + `stock`, `kardex`, `ingesta_masiva`, `gestor_offcanvas` |
| `ServicioViewSet` | `BaseViewSet + ServicioServiceMixin` | `uuid` | CRUD + `gestor_offcanvas`, `historial_offcanvas` |
| `ActivoFijoViewSet` | `BaseViewSet + ActivoFijoServiceMixin` | `uuid` | CRUD + `list_all`, `gestor_offcanvas` |
| `MovimientoInventarioViewSet` | `BaseViewSet + MovimientoServiceMixin` | `uuid` | List + Create + `partial_update` + `destroy` + `gestor_offcanvas` + `timeline` |
| `HistorialServicioViewSet` | `BaseViewSet + HistorialServiceMixin` | `uuid` | List + Create (sin PUT/PATCH propios) + `vincular_proyecto` |

**Paginación:** `StandardResultsSetPagination` → `page_size=10`, `max_page_size=100`

---

### 4.2 Serializers (`api/serializers.py`)

**Mixins:**

| Clase | Propósito |
|-------|-----------|
| `NormalizationMixin` | `_get_empresa_id()` + `to_representation()` normalizando UUIDs/FKs |
| `UUIDOrPKRelatedField` | `RelatedField` custom que acepta UUID string o PK entero; filtra queryset por `empresa_id` del contexto |

**Serializers:**

| Serializer | Uso |
|------------|-----|
| `CategoriaItemListSerializer` | GET `/categorias/` |
| `CategoriaItemDetailSerializer` | GET/POST/PATCH `/categorias/{uuid}/` + `validate_nombre()` anti-duplicados |
| `ProductoListSerializer` | GET `/productos/` — incluye `valor_inventario`, `alerta_stock` |
| `ProductoDetailSerializer` | GET/POST/PATCH `/productos/{uuid}/` |
| `StockResponseSerializer` | Response de `stock` action |
| `ServicioListSerializer` | GET `/servicios/` |
| `ServicioDetailSerializer` | GET/POST/PATCH `/servicios/{uuid}/` |
| `ActivoFijoListSerializer` | GET `/activos/` |
| `ActivoFijoDetailSerializer` | GET/POST/PATCH `/activos/{uuid}/` |
| `MovimientoInventarioListSerializer` | GET `/movimientos/` — campos calculados: `item_tipo`, `item_nombre`, `item_codigo`, `item_uuid` (desde `producto` o `activo_fijo`) |
| `MovimientoInventarioDetailSerializer` | POST/PATCH `/movimientos/` — soporta partial PATCH; valida `exactly_one_product_or_asset` |
| `MovimientoUnificadoListSerializer` | GET `/movimientos/timeline/` — read-only, Ledger Universal |
| `HistorialServicioDetailSerializer` | CRUD `/historial-servicios/` — `servicio` via `UUIDOrPKRelatedField`; `proyecto_uuid/nombre` read-only |
| `ProductoCargaMasivaItemSerializer` | Un ítem de carga masiva |
| `CargaMasivaInventarioSerializer` | Lista de ítems para `ingesta_masiva` action |

> **v3.10.2:** Todos los serializers tienen campos `cuenta_*_uuid` eliminados de `Meta.fields` y `Meta.read_only_fields`. Los métodos `get_cuenta_*_label()` y `validate_cuenta_*_uuid()` también eliminados.

---

### 4.3 Endpoints REST

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/api/v1/inventario/categorias/` | Lista categorías |
| POST | `/api/v1/inventario/categorias/` | Crear categoría |
| GET/PATCH/DELETE | `/api/v1/inventario/categorias/{uuid}/` | CRUD categoría |
| GET | `/api/v1/inventario/categorias/{uuid}/resumen/` | Cuenta de ítems vinculados |
| GET | `/api/v1/inventario/categorias/gestor-offcanvas/` | HTML offcanvas HTMX |
| GET | `/api/v1/inventario/productos/` | Lista con stock + alertas |
| POST | `/api/v1/inventario/productos/` | Crear producto (captura `IntegrityError` por código duplicado) |
| GET/PATCH/DELETE | `/api/v1/inventario/productos/{uuid}/` | CRUD producto |
| GET | `/api/v1/inventario/productos/{uuid}/stock/` | Stock actual |
| GET | `/api/v1/inventario/productos/{uuid}/kardex/` | Historial de movimientos |
| POST | `/api/v1/inventario/productos/ingesta-masiva/` | Carga desde Excel (batch) |
| GET | `/api/v1/inventario/productos/gestor-offcanvas/` | HTML offcanvas HTMX |
| GET | `/api/v1/inventario/servicios/` | Lista servicios |
| POST | `/api/v1/inventario/servicios/` | Crear servicio |
| GET/PATCH/DELETE | `/api/v1/inventario/servicios/{uuid}/` | CRUD servicio |
| GET | `/api/v1/inventario/servicios/gestor-offcanvas/` | HTML offcanvas HTMX |
| GET | `/api/v1/inventario/servicios/historial-offcanvas/` | Historial ventas del servicio |
| GET | `/api/v1/inventario/activos/` | Lista activos fijos |
| POST | `/api/v1/inventario/activos/` | Crear activo |
| GET/PATCH/DELETE | `/api/v1/inventario/activos/{uuid}/` | CRUD activo |
| GET | `/api/v1/inventario/activos/list-all/` | Lista completa sin paginación |
| GET | `/api/v1/inventario/activos/gestor-offcanvas/` | HTML offcanvas HTMX |
| GET | `/api/v1/inventario/movimientos/` | Lista Kardex |
| POST | `/api/v1/inventario/movimientos/` | Registrar movimiento → recalcula stock |
| GET | `/api/v1/inventario/movimientos/{uuid}/` | Detalle movimiento |
| PATCH | `/api/v1/inventario/movimientos/{uuid}/` | Editar movimiento → recálculo atómico stock |
| DELETE | `/api/v1/inventario/movimientos/{uuid}/` | Eliminar movimiento → recálculo atómico stock |
| GET | `/api/v1/inventario/movimientos/timeline/` | Ledger Universal (Productos + Activos + Servicios) |
| GET | `/api/v1/inventario/movimientos/gestor-offcanvas/` | HTML offcanvas HTMX |
| GET/POST | `/api/v1/inventario/historial-servicios/` | CRUD historial servicios |
| GET | `/api/v1/inventario/historial-servicios/{uuid}/` | Detalle historial |
| POST | `/api/v1/inventario/historial-servicios/{uuid}/vincular-proyecto/` | Vincula soft-ref proyecto_uuid/nombre |

**Endpoints DEPRECATED (registrados, por eliminar):**
```
POST /api/v1/inventario/productos/dt/    → usar GET /productos/
POST /api/v1/inventario/servicios/dt/    → usar GET /servicios/
POST /api/v1/inventario/activos/dt/      → usar GET /activos/
POST /api/v1/inventario/movimientos/dt/  → usar GET /movimientos/
```

---

## 5. Frontend

### 5.1 JavaScript Base (`static/inventario/js/`)

| Archivo | Responsabilidad |
|---------|----------------|
| `inventario.api.js` | **SSoT URLs** — `window.Sintel.Inventario.API` con objetos `productos`, `servicios`, `activos`, `movimientos`, `categorias`, `historialServicios`; cada uno con métodos `list`, `get`, `save`, `update`, `delete` (async); `searchCuentas(query, options)` para autocomplete PUC (solo usado en prefijo de código) |
| `inventario.utils.js` | `invalidateCache()`, `loadCategoriasSelect(selector, aplicacion, selected, placeholder)`, `setupCuentaAutocomplete(config)` — autocomplete PUC reutilizable para el campo de código de activos |

**`movimientos` expone:** `list`, `get`, `save`, `update`, `delete`, `timeline` — alineado con el backend v3.9.1+.

> **v3.10.2:** `searchCuentas()` y `setupCuentaAutocomplete()` ya no se usan para campos `cuenta_*_uuid` en modelos (eliminados). Se mantienen únicamente para la derivación del **prefijo de código** en Activos Fijos (`initCodigoPrefijo()` en `activos_editor.js`), donde el código del activo usa el código PUC de la cuenta de activo como prefijo visual — sin almacenarlo.

---

### 5.2 JavaScript Features — Listas (Tabulator)

| Archivo | Funciones Clave |
|---------|----------------|
| `productos_list.js` | `getColumns()`, `initTable()`, `initListEvents()`, `recargar()`, `init()` |
| `servicios_list.js` | `getColumns()`, `initTable()`, `initListEvents()`, `recargar()`, `init()` |
| `activos_list.js` | `getColumns()`, `formatearEstado()`, `initTable()`, `initListEvents()`, `recargar()` |
| `categorias_list.js` | `getColumns()`, `formatearAplicacion()`, `initTable()`, `initListEvents()`, `recargar()` |
| `movimientos_list.js` | `getColumns()`, `formatearTipoMovimiento()`, `initTable()`, `initListEvents()` |
| `inventario_list.js` | Vista consolidada: `getColumns()`, `formatearNumero()`, `initTable()`, `initListEvents()` |

---

### 5.3 JavaScript Features — Editores (CRUD UX)

| Archivo | Funciones Clave |
|---------|----------------|
| `productos_editor.js` | `recolectarDatosProducto()`, `initFormProductoEvents()`, `init()` |
| `servicios_editor.js` | `recolectarDatosFormulario()`, `initFormEvents()`, `init()` |
| `activos_editor.js` | `recolectarDatosFormulario()`, `initFormEvents()`, `initCodigoPrefijo()`, `init()` |
| `categorias_editor.js` | `recolectarDatosFormulario()`, `initFormEvents()`, `init()` |
| `movimientos_editor.js` | `recolectarDatosFormulario()`, `abrirOffcanvasCrear()`, `initFormEvents()`, `init()` |
| `inventario_editor.js` | `recolectarDatosAjuste()`, `actualizarUnidadProducto()`, `initEditorEvents()`, `init()` |
| `inventario_movimiento_facturas.js` | Integración con Facturas — vinculación soft-ref `factura_uuid`/`factura_numero` desde el formulario de movimientos |

> **v3.10.2:** Funciones `_preCargarLabelCuenta()` y llamadas a `setupCuentaAutocomplete()` para campos contables eliminadas de `productos_editor.js` y `servicios_editor.js`. En `activos_editor.js`, `initCodigoPrefijo()` subsiste únicamente para derivar el prefijo visual del campo `codigo` (no persiste UUID alguno).

---

### 5.4 Templates HTML (`templates/inventario/`)

| Template | Propósito |
|----------|-----------|
| `list_inventario.html` | Vista consolidada: resumen de stock, filtros, tabs |
| `list_productos.html` | Grid productos Tabulator |
| `list_servicios.html` | Grid servicios Tabulator |
| `list_activos.html` | Grid activos fijos Tabulator |
| `list_categorias.html` | Grid categorías Tabulator |
| `list_movimientos.html` | Grid Kardex Tabulator |
| `offcanvas_producto.html` | Form crear/editar Producto: código, categoría, precios, stock |
| `offcanvas_activo.html` | Form crear/editar ActivoFijo: código (con prefijo PUC visual), marca, modelo, estado, ubicación, costo |
| `offcanvas_categoria.html` | Form crear/editar CategoriaItem: nombre, aplicación |
| `offcanvas_movimiento.html` | Form registrar/editar `MovimientoInventario`: tipo, producto o activo_fijo, cantidad, costo, vinculación factura |
| `offcanvas_servicio.html` | Form crear/editar Servicio: código, categoría, precio |
| `offcanvas_historial_servicio.html` | Form registro historial servicio + vista vincular proyecto |
| `assets_inventario.html` | Include JS/CSS: Tabulator 6.2.5, Bootstrap Icons, HTMX, módulos propios |

> **v3.10.2:** Secciones "Vinculación Contable Dual" (offcanvas_producto.html), "Vinculación Contable" (offcanvas_servicio.html) e "Integración Contable v3.5" (offcanvas_activo.html) completamente eliminadas. Los offcanvas ya no exponen inputs de búsqueda de cuentas PUC ni campos hidden UUID contables.

---

## 6. Integración Contable — Pure Pull Model (v3.10.2)

### 6.1 Arquitectura Post-Desacoplamiento

**Antes (v3.9.x):** Los modelos Producto, Servicio, ActivoFijo y CategoriaItem almacenaban campos `cuenta_*_uuid` como soft-references al PUC de Contabilidad. El frontend usaba `setupCuentaAutocomplete()` para que el usuario seleccionara cuentas al crear/editar ítems.

**Después (v3.10.2):** Los modelos NO almacenan cuentas contables. El extractor de Contabilidad resuelve cuentas via `ReglaContable` consultando el tipo de movimiento y la categoría del ítem.

```
Antes:
  Producto.cuenta_inventario_uuid → UUID opaco → CuentaContable (en Contabilidad)

Ahora (Pure Pull):
  Producto (sin cuentas) ← ExtractorInventario (lee Producto, resuelve via ReglaContable)
```

### 6.2 Contrato con Contabilidad — `get_movimientos_timeline()`

El único punto de entrada autorizado para que Contabilidad lea datos de Inventario es:

```python
# En selectors.py de Inventario
get_movimientos_timeline(empresa_id, search=None)
```

Retorna dicts unificados con campos:
- `id`, `uuid`, `tipo`, `cantidad`, `costo_unitario`, `created_at`
- `item_tipo` (`'producto'` | `'activo'` | `'servicio'`)
- `item_nombre`, `item_codigo`, `item_uuid`
- `modelo_origen` (`'MovimientoInventario'` | `'HistorialServicio'`)
- `documento_id`, `factura_uuid`, `factura_numero`

### 6.3 `APP_ORIGEN_PREFIJOS['inventario']` (SSoT en `contabilidad/services/selectors.py`)

Los prefijos PUC que Contabilidad usa para resolver cuentas de ítems de inventario:

```python
APP_ORIGEN_PREFIJOS['inventario'] = [
    '143505', '143510',  # Inventario mercancías
    '6135',              # Costo de ventas
    '4135', '4175',      # Ingresos por servicios
    '15',                # Activos fijos
    '51',                # Gastos depreciación (agregado v3.7.2)
]
```

**Regla:** Nunca hardcodear prefijos en este módulo. Siempre usar `APP_ORIGEN_PREFIJOS` desde Contabilidad.

### 6.4 Campos Eliminados (mig 0009)

| Modelo | Campos Eliminados |
|--------|------------------|
| `CategoriaItem` | `cuenta_inventario_uuid`, `cuenta_costo_uuid`, `cuenta_ingreso_uuid` |
| `Producto` | `cuenta_inventario_uuid`, `cuenta_costo_uuid` |
| `Servicio` | `cuenta_ingreso_uuid` |
| `ActivoFijo` | `cuenta_activo_uuid`, `cuenta_depreciacion_uuid` |

**Total:** 8 campos eliminados de 4 modelos.

---

## 7. Checklist AGENTS.md — Estado de Cumplimiento

| Regla | Estado | Detalle |
|-------|--------|---------|
| `SintelTenantBaseModel` | ✅ | Todos los modelos via `TimeStampedModel` |
| `empresa_id` en queries | ✅ | Todos los selectors + ViewSets filtran por `empresa_id` |
| `.only()` en querysets | ✅ | Constantes `*_LIST_FIELDS` / `*_DETAIL_FIELDS` en `selectors.py` |
| `lookup_field = 'uuid'` | ✅ | Todos los ViewSets (mig 0005) |
| UUID en todos los modelos | ✅ | Mig 0005 — 6 modelos |
| No signals para negocio | ✅ | Service Layer exclusivo |
| `@transaction.atomic` en CRUD | ✅ | Todos los métodos de `crud_service.py` + `KardexService` |
| Dual-Auth sin override innecesario | ✅ | `BaseViewSet` no sobreescribe `get_authenticators()` |
| FK a `perfil.TenantProfile` correcta | ✅ | No hay FKs incorrectas a `AUTH_USER_MODEL` |
| **Pure Pull Model Contabilidad** | ✅ | **v3.10.2**: Inventario NO tiene campos `cuenta_*_uuid`. Contabilidad es única propietaria de mapeos PUC via `ExtractorInventario` + `ReglaContable` |
| `APP_ORIGEN_PREFIJOS` como SSoT | ✅ | Fix v3.7.2 + mantenido en v3.10.2 |
| Constraint `Lower()` en códigos | ✅ | `unique_*_codigo_per_empresa` en Producto, Servicio, ActivoFijo, CategoriaItem |
| CheckConstraint en `MovimientoInventario` | ✅ | `exactly_one_product_or_asset` (mig 0006) |
| Imports globales (no dentro de `def`) | ✅ | `services/__init__.py` re-exports explícitos |
| Campos contables eliminados de modelos origen | ✅ | mig 0009 — 8 campos en 4 modelos |

---

## 8. Deuda Técnica

| ID | Archivo | Severidad | Descripción |
|----|---------|-----------|-------------|
| DEUDA-04 | `api/urls.py` | RESUELTA (2026-08-27) | Endpoints `dt/` ya no existen en el código — confirmado por grep exhaustivo, sin consumidores. |
| DEUDA-05 | `services/business_service.py` | RESUELTA (2026-08-27) | `IngestaService` ya vive en su propio archivo `services/ingesta_service.py`. Los 6 `ServiceMixins` siguen juntos en `api_mixins.py` (no separados por modelo) — asimetría documentada, no un bug. |
| DEUDA-06 | Tests | COMPLETADA (histórico) | Ampliada de nuevo 2026-08-27: `test_kardex_service.py` (KardexService directo), `test_multitenant_isolation.py` (Producto/Categoria/ActivoFijo cross-tenant), y suite de permisos CRUD extendida a Producto/Servicio/ActivoFijo-destroy-guard/Movimiento-update-delete/HistorialServicio en `tests/tenant/inventario/test_crud_permissions.py`. |
| DEUDA-08 | `activos_editor.js` | RESUELTA (2026-08-27) | `initCodigoPrefijo()`/`setupCuentaAutocomplete()` ya no existen en el JS real (confirmado por grep) — esta entrada quedó desactualizada, el código ya había sido eliminado. |
| DEUDA-09 | `services/crud_service.py` | RESUELTA (2026-08-27) | Archivo completo (7 funciones: `crear_producto`, `actualizar_producto`, `crear_servicio`, `actualizar_servicio`, `crear_activo`, `actualizar_activo`, `crear_movimiento_raw`) confirmado sin consumidores reales — eliminado junto con su re-export en `services/__init__.py`. Los ViewSets ya persistían vía `serializer.save()`/`BaseViewSet.perform_create()`, nunca vía este módulo. |

---

## 9. Historial de Cambios Relevantes

| Versión | Migración | Cambio |
|---------|-----------|--------|
| v3.7.2 | — | `'51'` agregado a `APP_ORIGEN_PREFIJOS['inventario']` para cuentas de depreciación |
| v3.8.0+ | 0006 | `activo_fijo` FK + `CheckConstraint` + tipos de movimiento para Activos en `MovimientoInventario` |
| v3.8.0+ | 0007 | Soft-ref `factura_uuid`/`factura_numero` en `MovimientoInventario` |
| v3.9.0 | — | `get_movimientos_timeline()` + endpoint `GET /movimientos/timeline/` (Ledger Universal) |
| v3.9.1 | — | `KardexService.actualizar_movimiento()` + `eliminar_movimiento()`; ViewSet expone PATCH y DELETE en movimientos |
| v3.9.1 | 0008 | Soft-ref `proyecto_uuid`/`proyecto_nombre` en `HistorialServicio` + endpoint `vincular_proyecto` |
| **v3.10.2** | **0009** | **Eliminación de 8 campos `cuenta_*_uuid`** de CategoriaItem (3), Producto (2), Servicio (1), ActivoFijo (2) — Desacoplamiento contable completo. Contabilidad es única propietaria de mapeos PUC. Templates y JS actualizados (secciones contables removidas). |

---

## 10. Flujos Completos

### 10.1 Registrar Movimiento de Inventario (Producto)

```
[Frontend offcanvas_movimiento.html]
  usuario selecciona producto, tipo, cantidad, costo
  POST /api/v1/inventario/movimientos/
  Body: {producto: uuid, tipo: "ENTRADA_COMPRA", cantidad: 10, costo_unitario: 50000}
    ↓
[MovimientoInventarioViewSet.perform_create(serializer)]
  service_movimiento_perform_create(serializer, empresa)
    ↓
[KardexService.registrar_movimiento() @transaction.atomic]
  Producto.objects.select_for_update().get(pk=producto_id, empresa_id=empresa_id)
  crud_service.crear_movimiento_raw(empresa, producto, tipo, cantidad, ...)
  recalcular_stock_producto(producto_id, empresa_id)
    stock = SUM(ENTRADA_*) - SUM(SALIDA_*)
    UPDATE producto SET stock_actual = stock
    ↓
[Response 201 + MovimientoInventarioDetailSerializer]
[movimientos_list.js] → table.replaceData()
[productos_list.js]   → recargar() → stock_actual actualizado
```

### 10.2 Registrar Movimiento de Activo Fijo

```
[Frontend offcanvas_movimiento.html]
  usuario selecciona activo_fijo, tipo (ej. TRASLADO_MANTENIMIENTO)
  POST /api/v1/inventario/movimientos/
  Body: {activo_fijo: uuid, tipo: "TRASLADO_MANTENIMIENTO", cantidad: 1, ...}
    ↓
[KardexService.registrar_movimiento_activo() @transaction.atomic]
  ActivoFijo.objects.select_for_update().get(pk=activo_id, empresa_id=empresa_id)
  crud_service.crear_movimiento_raw(empresa, activo_fijo=activo, tipo, ...)
  activo.estado = _TRANSICION_ESTADO_ACTIVO[tipo]  # MANTENIMIENTO
  activo.save()
    ↓
[Response 201] → activos_list.js recargar() → estado actualizado en tabla
```

### 10.3 Motor Kardex (Stock Desnormalizado)

```
stock_actual = SUM(cantidad WHERE tipo IN TIPOS_ENTRADA)
             - SUM(cantidad WHERE tipo IN TIPOS_SALIDA)

select_for_update() garantiza que dos transacciones simultáneas
no corrompan stock_actual.
```

### 10.4 Ledger Universal (Timeline Unificado)

```
GET /api/v1/inventario/movimientos/timeline/
  ↓
get_movimientos_timeline(empresa_id, search=None)
  movimientos = MovimientoInventario.objects.filter(empresa_id=empresa_id)
  historial   = HistorialServicio.objects.filter(empresa=empresa)
  unificado   = merge([*movimientos_dicts, *historial_dicts])
  sorted_por  = datetime normalizado descendente
  ↓
MovimientoUnificadoListSerializer (read-only)
  ↓
ExtractorInventario (Contabilidad) ← único consumidor externo autorizado
```

### 10.5 Flujo Contable Post-Desacoplamiento (v3.10.2)

```
[Usuario crea/edita Producto, Servicio o ActivoFijo]
  → NO selecciona cuentas contables (sección eliminada)
  → Solo configura datos operativos (código, nombre, precio, stock)
    ↓
[Celery / manage.py backfill] → ExtractorInventario.extraer_pendientes()
  movimientos_sin_contabilizar = MovimientoInventario.filter(empresa_id, ...)
  para cada movimiento:
    tipo_tx = resolver desde movimiento.tipo (ENTRADA_COMPRA → COMPRA_GASTO, etc.)
    cuenta  = ReglaContable.resolver(tipo_tx, concepto, tenant)
    Contabilizador.contabilizar(dto)
    ↓
[AsientoContable creado en esquema de Contabilidad]
```

---

## 11. Estadísticas del Módulo (v3.10.2)

| Categoría | Cantidad |
|-----------|---------|
| Modelos (1 abstracto + 6 concretos) | 7 |
| Migraciones | **9** |
| Campos contables eliminados (v3.10.2) | **8** (en 4 modelos) |
| Clases de Servicio (KardexService + IngestaService + 6 Mixins) | **8** |
| Métodos nuevos en KardexService (v3.9.1) | 3 (`registrar_movimiento_activo`, `actualizar_movimiento`, `eliminar_movimiento`) |
| Clases Selector (1 por modelo) + 1 función timeline | 7 |
| Funciones CRUD | 7 |
| ViewSets | 6 |
| Serializers | **15** |
| Archivos JS base | 2 |
| Archivos JS features | **15** |
| Templates HTML | 13 |
| Tests | **24 (4 archivos)** ✅ |
