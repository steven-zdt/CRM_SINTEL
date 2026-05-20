# Auditoría Flujo Completo — Módulo Inventario

**Versión auditada:** v3.7.5  
**Fecha:** 2026-05-19  
**Estado:** ✅ OPERATIVO (0 CRÍTICOS)  
**Auditor:** Claude Code (claude-sonnet-4-6)  
**Ubicación:** `apps/tenant/inventario/`

---

## 1. Responsabilidades del Módulo

| # | Responsabilidad | Estado |
|---|----------------|--------|
| 1 | **Catálogo Multitipo** — Gestión diferenciada de Productos (stock), Servicios (intangibles) y Activos Fijos (uso interno) | ✅ |
| 2 | **Motor Kardex** — `KardexService` con `select_for_update()`: movimientos append-only, `stock_actual` desnormalizado recalculado atómicamente | ✅ |
| 3 | **Inmutabilidad de Movimientos** — `MovimientoInventario` es append-only: no PUT/PATCH, solo CREATE + historial | ✅ |
| 4 | **Ingesta Masiva** — Pipeline de carga desde Excel: `IngestaService.materializar_carga_masiva_productos()` con auto-creación de categorías | ✅ |
| 5 | **Vinculación Contable** — 5 campos UUID (cuenta_inventario, cuenta_costo, cuenta_ingreso, cuenta_activo, cuenta_depreciacion) hacia PUC de Contabilidad | ✅ (mig 0003/0004) |
| 6 | **Aislamiento Pull Model** — Contabilidad lee de Inventario; Inventario NO importa de Contabilidad | ✅ |
| 7 | **UUID Lookup** — `lookup_field = 'uuid'` en todos los ViewSets (mig 0005) | ✅ |
| 8 | **Búsqueda Cuentas Depreciación** — Prefijo `'51'` en `APP_ORIGEN_PREFIJOS['inventario']` para cuentas de depreciación en Activos Fijos | ✅ (v3.7.2) |

---

## 2. Modelos

### 2.1 `TimeStampedModel` (abstracto)
**Herencia:** `SintelTenantBaseModel` ✅ (base de todos los modelos del módulo)

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
| `uuid` | UUIDField | `unique=True, db_index=True, editable=False` ✅ (mig 0005) |
| `empresa` | FK → `Empresa` | `PROTECT, related_name='categorias_inventario'` |
| `nombre` | CharField(100) | `db_index=True` |
| `descripcion` | TextField | nullable |
| `aplicacion` | CharField(16) | Choices: `TODO / PRODUCTO / SERVICIO / ACTIVO` |
| `imagen` | ImageField | `upload_to='inventario/categorias/'`, nullable |
| `activo` | BooleanField | `default=True` |
| `cuenta_inventario_uuid` | UUIDField | nullable — PUC Inventario/Activo (heredado por ítems) |
| `cuenta_costo_uuid` | UUIDField | nullable — PUC Costo de Ventas/Depreciación |
| `cuenta_ingreso_uuid` | UUIDField | nullable — PUC Ingreso por Ventas |

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
| `marca` / `modelo` | CharField(100) | nullable |
| `descripcion` | TextField | nullable |
| `imagen` | ImageField | `upload_to='inventario/activos/'`, nullable |
| `ubicacion` / `responsable` | CharField(100) | nullable |
| `fecha_adquisicion` | DateField | nullable |
| `costo_adquisicion` | DecimalField(14,2) | `default=0` |
| `estado` | CharField(20) | Choices: `ACTIVO / MANTENIMIENTO / BAJA / VENDIDO` |
| `cuenta_activo_uuid` | UUIDField | nullable — PUC Control Activo (p.ej. 15xxxx) |
| `cuenta_depreciacion_uuid` | UUIDField | nullable — PUC Depreciación (p.ej. 51xxxx) |

**Índices BD:** `(codigo)`, `(empresa)`  
**Constraint:** `UNIQUE(Lower('codigo'), empresa)` → `unique_activo_codigo_per_empresa`

**Nota `cuenta_depreciacion_uuid`:** Requiere prefijo `'51'` en `APP_ORIGEN_PREFIJOS['inventario']` (fix v3.7.2). Ver `contabilidad/services/selectors.py:APP_ORIGEN_PREFIJOS`.

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
| `descripcion` | TextField | nullable |
| `unidad` | CharField(16) | `default='UND'` |
| `imagen` | ImageField | `upload_to='inventario/productos/'`, nullable |
| `precio_venta` | DecimalField(14,2) | `default=0` |
| `costo_promedio` | DecimalField(14,2) | `default=0` — actualizado por `KardexService` en ENTRADA_COMPRA |
| `stock_actual` | DecimalField(14,3) | **desnormalizado** — recalculado por `KardexService.recalcular_stock_producto()` |
| `stock_minimo` | DecimalField(14,3) | `default=0` — para alertas de reposición |
| `activo` | BooleanField | `default=True` |
| `cuenta_inventario_uuid` | UUIDField | nullable — PUC Activo de Inventario (p.ej. 143505) |
| `cuenta_costo_uuid` | UUIDField | nullable — PUC Costo de Ventas (p.ej. 6135xx) |

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
| `descripcion` | TextField | nullable |
| `imagen` | ImageField | `upload_to='inventario/servicios/'`, nullable |
| `precio_venta` | DecimalField(14,2) | `default=0` |
| `activo` | BooleanField | `default=True` |
| `cuenta_ingreso_uuid` | UUIDField | nullable — PUC Ingreso (p.ej. 4135xx) |

**Índices BD:** `(empresa, nombre)`  
**Constraint:** `UNIQUE(Lower('codigo'), empresa)` → `unique_servicio_codigo_per_empresa`

---

### 2.6 `MovimientoInventario` (Kardex — append-only)
**Herencia:** `TimeStampedModel` → `SintelTenantBaseModel` ✅  
**Ordering:** `['-created_at']`

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `unique=True, db_index=True, editable=False` ✅ |
| `empresa` | FK → `Empresa` | `PROTECT, related_name='movimientos_inventario'` |
| `producto` | FK → `Producto` | `CASCADE, related_name='movimientos'` |
| `tipo` | CharField(20) | `TipoMovimiento` choices (ver abajo) |
| `cantidad` | DecimalField(14,3) | |
| `costo_unitario` | DecimalField(14,2) | `default=0` |
| `origen_referencia` | CharField(100) | nullable — referencia al documento origen |
| `cliente_referencia` | CharField(200) | nullable — referencia al cliente/proveedor |
| `observaciones` | TextField | nullable |

**Choices `TipoMovimiento`:**
```
ENTRADAS:  ENTRADA_COMPRA | ENTRADA_AJUSTE | ENTRADA_DEVOLUCION
SALIDAS:   SALIDA_VENTA   | SALIDA_BAJA    | SALIDA_CONSUMO
```

**Regla Inmutabilidad:** Los movimientos son append-only. No se expone PUT/PATCH en `MovimientoInventarioViewSet`. Eliminar un movimiento requiere recalcular `stock_actual`.

**Índices BD:** `(empresa, created_at)`, `(producto, created_at)`

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

**Índices BD:** `(empresa, fecha_registro)`

---

### 2.8 Migraciones (5 total)

| # | Archivo | Cambio Principal |
|---|---------|-----------------|
| 0001 | `0001_initial.py` | Creación de los 6 modelos: CategoriaItem, ActivoFijo, Producto, Servicio, MovimientoInventario, HistorialServicio |
| 0002 | `...unique_categoria_nombre_per_empresa.py` | Constraint `UNIQUE(Lower('nombre'), empresa)` en CategoriaItem |
| 0003 | `...activofijo_cuenta_contable_uuid_and_more.py` | Agrega campos UUID contables a ActivoFijo, Producto, Servicio, CategoriaItem |
| 0004 | `...rename_cuenta_contable_uuid_activofijo_cuenta_activo_uuid.py` | Renombra campos contables en ActivoFijo (`cuenta_activo_uuid`, `cuenta_depreciacion_uuid`) + constraints de código únicos |
| 0005 | `...uuid_lookup_and_tenant_code_constraints.py` | **UUID fields** en todos los modelos + constraints `unique_*_codigo_per_empresa` + `RunPython populate_uuids` |

---

## 3. Service Layer (FSD)

### 3.1 `services/selectors.py` — Lectura Zero-Waste (327 líneas)

**Constantes SSoT (campos optimizados):**
```python
CATEGORIA_LIST_FIELDS  = (11 campos: id, uuid, nombre, aplicacion, activo, cuentas_uuid, empresa_id)
PRODUCTO_LIST_FIELDS   = (13 campos: id, uuid, codigo, nombre, precio_venta, costo_promedio,
                          stock_actual, stock_minimo, activo, cuentas_uuid, empresa_id, categoria_id)
SERVICIO_LIST_FIELDS   = (9 campos: id, uuid, codigo, nombre, precio_venta, activo, cuenta_ingreso_uuid, empresa_id)
ACTIVO_LIST_FIELDS     = (11 campos: id, uuid, codigo, nombre, marca, estado, costo_adquisicion,
                          cuentas_uuid, empresa_id, categoria_id)
MOVIMIENTO_LIST_FIELDS = (11 campos: id, uuid, tipo, cantidad, costo_unitario, created_at,
                          origen_referencia, empresa_id, producto_id + refs producto)
CATEGORIA_DETAIL_FIELDS  = (12 campos: + descripcion, imagen)
PRODUCTO_DETAIL_FIELDS   = (16 campos: + descripcion, unidad, imagen, created_at, updated_at)
SERVICIO_DETAIL_FIELDS   = (12 campos: + descripcion, imagen, created_at, updated_at)
ACTIVO_DETAIL_FIELDS     = (16 campos: + modelo, descripcion, imagen, ubicacion, responsable,
                            fecha_adquisicion, created_at, updated_at)
MOVIMIENTO_DETAIL_FIELDS = (13 campos: + observaciones, cliente_referencia)
```

**Clases Selector (todas `@staticmethod`):**

| Clase | Métodos |
|-------|---------|
| `ProductoSelector` | `get_list(empresa_id, search)`, `get_detail(empresa_id, producto_uuid)`, `get_by_id(empresa_id, producto_id)` |
| `ServicioSelector` | `get_list(empresa_id, search)`, `get_detail(empresa_id, servicio_uuid)`, `get_by_id(empresa_id, servicio_id)` |
| `ActivoFijoSelector` | `get_list(empresa_id, search)`, `get_detail(empresa_id, activo_uuid)`, `get_by_id(empresa_id, activo_id)` |
| `MovimientoInventarioSelector` | `get_list(empresa_id, search)`, `get_detail(empresa_id, movimiento_uuid)`, `get_kardex_for_producto(empresa_id, producto_id)` |
| `CategoriaItemSelector` | `get_list(empresa_id, search)`, `get_detail(empresa_id, categoria_uuid)`, `get_by_id(empresa_id, categoria_id)` |
| `HistorialServicioSelector` | `get_list(empresa)` |

**Funciones helpers:** `get_empresa_singleton()`, `_obtener_empresa_singleton()`

---

### 3.2 `services/crud_service.py` — Escritura Atómica (239 líneas)

Todas las funciones son `@transaction.atomic`:

| Función | Descripción |
|---------|-------------|
| `crear_producto(empresa, codigo, nombre, *, categoria, ...)` | Crea Producto — todos los campos opcionales via `**kwargs` |
| `actualizar_producto(*, producto, **kwargs)` | Actualiza campos recibidos — ignora campos no enviados |
| `crear_servicio(empresa, codigo, nombre, *, categoria, ...)` | Crea Servicio |
| `actualizar_servicio(*, servicio, **kwargs)` | Actualiza Servicio |
| `crear_activo(empresa, codigo, nombre, *, categoria, ...)` | Crea ActivoFijo con campos contables |
| `actualizar_activo(*, activo, **kwargs)` | Actualiza ActivoFijo |
| `crear_movimiento_raw(empresa, producto, tipo, cantidad, ...)` | Crea MovimientoInventario sin recalcular stock (lo hace KardexService) |

---

### 3.3 `services/business_service.py` — Reglas de Negocio (653 líneas)

#### `KardexService` — Motor de Stock

```python
TIPOS_ENTRADA = (ENTRADA_COMPRA, ENTRADA_AJUSTE, ENTRADA_DEVOLUCION)
TIPOS_SALIDA  = (SALIDA_VENTA, SALIDA_BAJA, SALIDA_CONSUMO)
```

| Método | Descripción |
|--------|-------------|
| `calcular_stock(producto_id, empresa_id)` | `SUM(entradas) - SUM(salidas)` para el producto del tenant |
| `recalcular_stock_producto(producto_id, empresa_id)` | `@transaction.atomic + select_for_update()` — recalcula y persiste `Producto.stock_actual` |
| `registrar_entrada(**kwargs)` | `@transaction.atomic` — crea movimiento ENTRADA_* + recalcula stock |
| `registrar_salida(**kwargs)` | `@transaction.atomic` — valida stock suficiente + crea SALIDA_* + recalcula stock |
| `ajustar_stock(producto_id, empresa_id, cantidad_ajuste, observaciones)` | `@transaction.atomic` — `cantidad_ajuste > 0` → ENTRADA_AJUSTE; `< 0` → SALIDA_BAJA |
| `registrar_movimiento(**kwargs)` | Dispatcher — detecta tipo y delega a `registrar_entrada` o `registrar_salida` |

**Invariante de stock:**
```
stock_actual = SUM(cantidad WHERE tipo IN TIPOS_ENTRADA)
             - SUM(cantidad WHERE tipo IN TIPOS_SALIDA)
```

#### `IngestaService` — Carga Masiva

| Método | Descripción |
|--------|-------------|
| `materializar_inventario_desde_dto(dto)` | Materializa un DTO (dict) en Producto/Servicio/Activo — crea o actualiza |
| `materializar_carga_masiva_productos(empresa_id, lista_datos, usuario)` | Procesa lista de DTOs desde Excel: auto-crea categorías, registra stock inicial via `ENTRADA_AJUSTE` |

#### Service Mixins (inyectados en ViewSets)

| Mixin | Métodos clave |
|-------|---------------|
| `CategoriaItemServiceMixin` | `service_categoria_destroy()`, `service_categoria_get_resumen()`, `service_categoria_get_offcanvas_context()` |
| `ProductoServiceMixin` | `service_producto_destroy()`, `service_producto_ajustar_stock()`, `service_producto_get_stock()`, `service_producto_get_kardex()`, `service_producto_get_offcanvas_context()` |
| `ServicioServiceMixin` | `service_servicio_destroy()`, `service_servicio_get_offcanvas_context()`, `service_servicio_get_historial_context()` |
| `ActivoFijoServiceMixin` | `service_activo_destroy()`, `service_activo_list_all()`, `service_activo_get_offcanvas_context()` |
| `MovimientoServiceMixin` | `service_movimiento_perform_create(serializer, empresa)`, `service_movimiento_get_offcanvas_context()` |
| `HistorialServiceMixin` | `service_historial_get_queryset(empresa)` |

---

## 4. API Layer

### 4.1 ViewSets (677 líneas)

**Base:** `BaseViewSet(BaseTenantViewSet)` — provee:
- `get_authenticators()` → `[JWTAuthentication, SessionAuthentication]`
- `perform_create(serializer)` → inyecta `empresa`
- `get_serializer_context()` → `{request, empresa, empresa_id}`
- `_get_empresa_id()` → extrae empresa_id del request

| ViewSet | Herencia | lookup_field | Acciones |
|---------|----------|-------------|----------|
| `CategoriaItemViewSet` | `BaseViewSet + CategoriaItemServiceMixin` | `uuid` | CRUD + `resumen`, `gestor_offcanvas` |
| `ProductoViewSet` | `BaseViewSet + ProductoServiceMixin` | `uuid` | CRUD + `stock`, `kardex`, `ingesta_masiva`, `datatables` |
| `ServicioViewSet` | `BaseViewSet + ServicioServiceMixin` | `uuid` | CRUD + `gestor_offcanvas`, `historial_offcanvas`, `datatables` |
| `ActivoFijoViewSet` | `BaseViewSet + ActivoFijoServiceMixin` | `uuid` | CRUD + `list_all`, `gestor_offcanvas` |
| `MovimientoInventarioViewSet` | `BaseViewSet + MovimientoServiceMixin` | `uuid` | List + Create (**sin** update/delete) + `gestor_offcanvas`, `datatables` |
| `HistorialServicioViewSet` | `BaseViewSet + HistorialServiceMixin` | `uuid` | CRUD completo |

**Paginación:** `StandardResultsSetPagination` → `page_size=50`

---

### 4.2 Serializers (`api/serializers.py` — 580 líneas)

**Mixins:**

| Clase | Propósito |
|-------|-----------|
| `NormalizationMixin` | `_get_empresa_id()` + `to_representation()` normalizando UUIDs/FKs |
| `UUIDOrPKRelatedField` | RelatedField custom que acepta UUID o PK entero |

**Serializers (patrón List / Detail):**

| Serializer | Uso |
|------------|-----|
| `CategoriaItemListSerializer` | GET `/categorias/` — campos mínimos |
| `CategoriaItemDetailSerializer` | GET/POST/PATCH `/categorias/{uuid}/` — completo + NormalizationMixin |
| `ProductoListSerializer` | GET `/productos/` — con `stock_actual`, `stock_minimo` |
| `ProductoDetailSerializer` | GET/POST/PATCH `/productos/{uuid}/` — con cuentas UUID |
| `StockResponseSerializer` | Response de `stock` action |
| `ServicioListSerializer` | GET `/servicios/` |
| `ServicioDetailSerializer` | GET/POST/PATCH `/servicios/{uuid}/` |
| `ActivoFijoListSerializer` | GET `/activos/` |
| `ActivoFijoDetailSerializer` | GET/POST/PATCH `/activos/{uuid}/` — con `cuenta_activo_uuid`, `cuenta_depreciacion_uuid` |
| `MovimientoInventarioListSerializer` | GET `/movimientos/` |
| `MovimientoInventarioDetailSerializer` | POST `/movimientos/` |
| `HistorialServicioDetailSerializer` | CRUD `/historial-servicios/` |
| `ProductoCargaMasivaItemSerializer` | Un ítem de carga masiva |
| `CargaMasivaInventarioSerializer` | Lista de ítems para `ingesta_masiva` action |

---

### 4.3 Endpoints REST

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/api/v1/inventario/categorias/` | Lista categorías |
| POST | `/api/v1/inventario/categorias/` | Crear categoría |
| GET | `/api/v1/inventario/categorias/{uuid}/` | Detalle + cuentas contables heredadas |
| PATCH | `/api/v1/inventario/categorias/{uuid}/` | Actualizar |
| DELETE | `/api/v1/inventario/categorias/{uuid}/` | Eliminar (solo si sin ítems) |
| GET | `/api/v1/inventario/categorias/{uuid}/resumen/` | Cuenta de productos/servicios/activos vinculados |
| GET | `/api/v1/inventario/categorias/gestor-offcanvas/` | HTML offcanvas HTMX |
| GET | `/api/v1/inventario/productos/` | Lista con stock + alertas |
| POST | `/api/v1/inventario/productos/` | Crear producto |
| GET | `/api/v1/inventario/productos/{uuid}/` | Detalle |
| PATCH | `/api/v1/inventario/productos/{uuid}/` | Actualizar |
| DELETE | `/api/v1/inventario/productos/{uuid}/` | Eliminar (requiere `activo=False`, cascade movimientos) |
| GET | `/api/v1/inventario/productos/{uuid}/stock/` | Stock actual |
| GET | `/api/v1/inventario/productos/{uuid}/kardex/` | Historial de movimientos del producto |
| POST | `/api/v1/inventario/productos/ingesta-masiva/` | Carga desde Excel (batch) |
| GET | `/api/v1/inventario/servicios/` | Lista servicios |
| POST | `/api/v1/inventario/servicios/` | Crear servicio |
| GET/PATCH/DELETE | `/api/v1/inventario/servicios/{uuid}/` | CRUD servicio |
| GET | `/api/v1/inventario/servicios/gestor-offcanvas/` | HTML offcanvas HTMX |
| GET | `/api/v1/inventario/servicios/historial-offcanvas/` | Historial de ventas del servicio |
| GET | `/api/v1/inventario/activos/` | Lista activos fijos |
| POST | `/api/v1/inventario/activos/` | Crear activo |
| GET/PATCH/DELETE | `/api/v1/inventario/activos/{uuid}/` | CRUD activo |
| GET | `/api/v1/inventario/activos/list-all/` | Lista completa sin paginación |
| GET | `/api/v1/inventario/activos/gestor-offcanvas/` | HTML offcanvas HTMX |
| GET | `/api/v1/inventario/movimientos/` | Lista Kardex (append-only) |
| POST | `/api/v1/inventario/movimientos/` | Registrar movimiento → recalcula stock |
| GET | `/api/v1/inventario/movimientos/{uuid}/` | Detalle movimiento |
| GET | `/api/v1/inventario/movimientos/gestor-offcanvas/` | HTML offcanvas HTMX |
| GET/POST | `/api/v1/inventario/historial-servicios/` | CRUD historial servicios |
| GET/PATCH/DELETE | `/api/v1/inventario/historial-servicios/{uuid}/` | CRUD historial |

**Endpoints DEPRECATED (mantener hasta v2.50):**
```
POST /api/v1/inventario/productos/dt/    → usar GET /productos/
POST /api/v1/inventario/servicios/dt/    → usar GET /servicios/
POST /api/v1/inventario/activos/dt/      → usar GET /activos/
POST /api/v1/inventario/movimientos/dt/  → usar GET /movimientos/
```

---

## 5. Frontend

### 5.1 JavaScript Base (`static/inventario/js/`)

| Archivo | Líneas | Responsabilidad |
|---------|--------|----------------|
| `inventario.api.js` | 295 | **SSoT URLs** — `window.Sintel.Inventario.API` con objetos `productos`, `servicios`, `activos`, `movimientos`, `categorias`, `historial_servicios` cada uno con `list`, `get`, `save`, `update`, `delete`, `dt` |
| `inventario.utils.js` | 180 | `invalidateCache()`, `setupCuentaAutocomplete(config)` — autocomplete para cuentas PUC |

---

### 5.2 JavaScript Features — Listas (Tabulator)

| Archivo | Líneas | Funciones Clave |
|---------|--------|----------------|
| `productos_list.js` | 589 | `getColumns()`, `initTable()`, `initListEvents()`, `recargar()`, `init()` |
| `servicios_list.js` | 398 | `getColumns()`, `initTable()`, `initListEvents()`, `recargar()`, `init()` |
| `activos_list.js` | 460 | `getColumns()`, `formatearEstado()`, `initTable()`, `initListEvents()`, `recargar()` |
| `categorias_list.js` | 428 | `getColumns()`, `formatearAplicacion()`, `initTable()`, `initListEvents()`, `recargar()` |
| `movimientos_list.js` | 362 | `getColumns()`, `formatearTipoMovimiento()`, `initTable()`, `initListEvents()` |
| `inventario_list.js` | 592 | `getColumns()`, `formatearNumero()`, `initTable()`, `initListEvents()` (vista consolidada con `locale: 'es'` + `langs`) |

---

### 5.3 JavaScript Features — Editores (CRUD UX)

| Archivo | Líneas | Funciones Clave |
|---------|--------|----------------|
| `productos_editor.js` | 446 | `recolectarDatosProducto()`, `initFormProductoEvents()`, `init()` |
| `servicios_editor.js` | 321 | `recolectarDatosFormulario()`, `initFormEvents()`, `init()` |
| `activos_editor.js` | 289 | `recolectarDatosFormulario()`, `initFormEvents()`, `init()` |
| `categorias_editor.js` | 266 | `recolectarDatosFormulario()`, `initFormEvents()`, `init()` |
| `movimientos_editor.js` | 334 | `recolectarDatosFormulario()`, `abrirOffcanvasCrear()`, `initFormEvents()`, `init()` |
| `inventario_editor.js` | 362 | `recolectarDatosAjuste()`, `actualizarUnidadProducto()`, `initEditorEvents()`, `init()` |

---

### 5.4 Templates HTML (`templates/inventario/`)

| Template | Líneas | Propósito |
|----------|--------|-----------|
| `list_inventario.html` | 77 | Vista consolidada: resumen de stock, filtros, tabs |
| `list_productos.html` | 30 | Grid productos Tabulator |
| `list_servicios.html` | 37 | Grid servicios Tabulator |
| `list_activos.html` | 30 | Grid activos fijos Tabulator |
| `list_categorias.html` | 30 | Grid categorías Tabulator |
| `list_movimientos.html` | 30 | Grid Kardex Tabulator |
| `offcanvas_producto.html` | 192 | Form crear/editar Producto: código, categoría, precios, stock, cuentas PUC |
| `offcanvas_activo.html` | 115 | Form crear/editar ActivoFijo: código, marca, modelo, cuentas PUC activo/depreciación |
| `offcanvas_categoria.html` | 47 | Form crear/editar CategoriaItem: nombre, aplicación, cuentas PUC heredadas |
| `offcanvas_movimiento.html` | 95 | Form registrar MovimientoInventario: tipo, producto, cantidad, costo |
| `offcanvas_servicio.html` | 76 | Form crear/editar Servicio: código, categoría, precio, cuenta ingreso |
| `offcanvas_historial_servicio.html` | 51 | Vista read-only historial de prestación del servicio |
| `assets_inventario.html` | 43 | Include JS/CSS: Tabulator 6.2.5, Bootstrap Icons, HTMX, módulos propios |

---

## 6. Vinculación Contable (Pull Model)

### 6.1 Mapa de Cuentas PUC por Modelo

| Modelo | Campo UUID | Tipo Cuenta PUC | Prefijo Típico |
|--------|------------|-----------------|---------------|
| `Producto` | `cuenta_inventario_uuid` | Activo circulante | `143505`, `143510` |
| `Producto` | `cuenta_costo_uuid` | Costo de ventas | `6135xx` |
| `Servicio` | `cuenta_ingreso_uuid` | Ingresos | `4135xx`, `4175xx` |
| `ActivoFijo` | `cuenta_activo_uuid` | Activo fijo | `15xxxx` |
| `ActivoFijo` | `cuenta_depreciacion_uuid` | Depreciación | `51xxxx` (gastos) |
| `CategoriaItem` | `cuenta_inventario_uuid` | Heredado por Productos | — |
| `CategoriaItem` | `cuenta_costo_uuid` | Heredado por Productos | — |
| `CategoriaItem` | `cuenta_ingreso_uuid` | Heredado por Servicios | — |

### 6.2 `APP_ORIGEN_PREFIJOS['inventario']` (SSoT en `contabilidad/services/selectors.py`)

```python
APP_ORIGEN_PREFIJOS['inventario'] = [
    '143505', '143510',  # Inventario mercancías
    '6135',              # Costo de ventas
    '4135', '4175',      # Ingresos
    '15',                # Activos fijos (prefijo)
    '51',                # Gastos depreciación ← agregado v3.7.2
]
```

**Regla:** Nunca hardcodear prefijos en este módulo. Siempre usar `APP_ORIGEN_PREFIJOS` desde Contabilidad.

---

## 7. Checklist AGENTS.md — Estado de Cumplimiento

| Regla | Estado | Detalle |
|-------|--------|---------|
| `SintelTenantBaseModel` | ✅ | Todos via `TimeStampedModel` |
| `empresa_id` en queries | ✅ | Todos los selectors + ViewSets filtran por `empresa_id` |
| `.only()` en querysets | ✅ | Constantes `*_LIST_FIELDS` / `*_DETAIL_FIELDS` en `selectors.py` |
| `lookup_field = 'uuid'` | ✅ | Todos los ViewSets (heredado + mig 0005) |
| UUID en todos los modelos | ✅ | Mig 0005 — 6 modelos |
| No signals para negocio | ✅ | Service Layer exclusivo |
| `@transaction.atomic` en CRUD | ✅ | Todos los métodos de `crud_service.py` + `KardexService` |
| `BaseTenantViewSet` sin override auth | ⚠️ | `BaseViewSet.get_authenticators()` lo sobreescribe explícitamente — pero retorna el mismo resultado (`[JWT, Session]`); acción segura pero innecesaria |
| FK a `perfil.TenantProfile` correcta | ✅ | No hay FKs incorrectas a `AUTH_USER_MODEL` |
| Pull Model Contabilidad | ✅ | Inventario NO importa de contabilidad; las cuentas UUID son referencias opacas |
| `APP_ORIGEN_PREFIJOS` como SSoT | ✅ | Fix v3.7.2 completado |
| Constraint `Lower()` en códigos | ✅ | `unique_*_codigo_per_empresa` en Producto, Servicio, ActivoFijo, CategoriaItem |
| Movimientos append-only | ✅ | `MovimientoInventarioViewSet` no expone PUT/PATCH |
| Imports globales (no dentro de `def`) | ⚠️ | `business_service.py` es correcto; `services/__init__.py` usa `from .X import *` — funcional pero menos explícito que re-exports nombrados |

---

## 8. Fixes Aplicados (v3.7.x)

### F1 — Prefijo `'51'` para Cuentas de Depreciación (v3.7.2)

**Causa:** Al buscar `cuenta_depreciacion_uuid` para un Activo Fijo, el selector de cuentas contables filtraba por `APP_ORIGEN_PREFIJOS['inventario']`. El prefijo `'51'` (Gastos/Depreciación) no estaba incluido, así que las cuentas de depreciación no aparecían en el autocomplete.

**Fix:** Agregar `'51'` a `APP_ORIGEN_PREFIJOS['inventario']` en `contabilidad/services/selectors.py`.

**Archivo:** `apps/tenant/contabilidad/services/selectors.py:APP_ORIGEN_PREFIJOS`

---

### F2 — UUID Fields en todos los modelos (mig 0005)

**Causa:** Los modelos no tenían `uuid` field, por lo que `lookup_field='uuid'` en los ViewSets fallaba en detalle/actualización.

**Fix:** Migración 0005 — AddField para UUID en todos los modelos + `RunPython populate_uuids` + AlterField con unique constraint.

---

## 9. Deuda Técnica

| ID | Archivo | Severidad | Descripción |
|----|---------|-----------|-------------|
| DEUDA-01 | `api/viewsets.py` | MEDIA | 677 líneas — `BaseViewSet` sobreescribe `get_authenticators()` retornando lo mismo que el padre. Eliminar override innecesario. |
| DEUDA-02 | `services/__init__.py` | BAJA | `from .X import *` — opaco. Preferir re-exports explícitos como en otros módulos (`from .selectors import ProductoSelector, ...`) |
| DEUDA-03 | `inventario_list.js` + otros | BAJA | Varios JS usan `locale: 'es'` pero sin `langs` definidos → warning en consola. **Fix aplicado globalmente en `TabulatorFactory` v3.7.5** |
| DEUDA-04 | `api/urls.py` | BAJA | Endpoints `dt/` DEPRECATED desde v2.40 aún registrados. Eliminar en v2.50 (ya pasado). |
| DEUDA-05 | `services/business_service.py` | BAJA | 653 líneas — `IngestaService` podría separarse en `services/ingesta_service.py`. Los 6 ServiceMixins también podrían tener su propio archivo. |
| DEUDA-06 | Tests | ALTA | No se encontró directorio `tests/` en la app. Faltan tests para: `KardexService` (concurrencia, stock negativo), `IngestaService` (carga masiva), constraints únicos por empresa. |

---

## 10. Patrones Clave

### 10.1 Motor Kardex (Stock Desnormalizado)

```
KardexService.registrar_entrada(producto_id, empresa_id, cantidad, tipo, ...):
  @transaction.atomic
  → Producto.objects.select_for_update().get(pk=producto_id, empresa_id=empresa_id)
  → crud_service.crear_movimiento_raw(tipo=ENTRADA_*, cantidad=cantidad, ...)
  → recalcular_stock_producto(producto_id, empresa_id)
       → stock = SUM(entradas) - SUM(salidas)
       → Producto.objects.filter(pk=pk).update(stock_actual=stock)
```

`select_for_update()` garantiza que dos transacciones simultáneas no corrompan `stock_actual`.

### 10.2 Carga Masiva desde Excel

```
POST /api/v1/inventario/productos/ingesta-masiva/
  Body: {empresa_id, productos: [{codigo, nombre, categoria, precio_venta, stock_inicial, ...}]}
    ↓
IngestaService.materializar_carga_masiva_productos(empresa_id, lista_datos, usuario)
  Para cada ítem:
    → buscar/crear CategoriaItem si no existe
    → materializar_inventario_desde_dto(dto) → crear_producto() o actualizar_producto()
    → Si stock_inicial > 0:
        KardexService.registrar_entrada(tipo=ENTRADA_AJUSTE, cantidad=stock_inicial)
```

### 10.3 Constraint Código Único Case-Insensitive

```sql
UNIQUE(Lower('codigo'), empresa)
```
Aplicado en: `Producto`, `Servicio`, `ActivoFijo`. Garantiza que `"PRD001"` y `"prd001"` sean el mismo producto dentro de una empresa.

### 10.4 Herencia de Cuentas Contables

```
CategoriaItem.cuenta_inventario_uuid (hereda por defecto)
    ↓ si Producto.cuenta_inventario_uuid is None
Serializer/Service usa cuenta de la categoría como fallback
```

---

## 11. Flujo Completo: Registrar Movimiento de Inventario

```
[Frontend offcanvas_movimiento.html]
  ↓ usuario selecciona producto, tipo, cantidad, costo
  → POST /api/v1/inventario/movimientos/
    Body: {producto: uuid, tipo: "ENTRADA_COMPRA", cantidad: 10, costo_unitario: 50000}
      ↓
[MovimientoInventarioViewSet.perform_create(serializer)]
  → empresa = _get_empresa()
  → service_movimiento_perform_create(serializer, empresa)
    ↓
[MovimientoServiceMixin.service_movimiento_perform_create()]
  → KardexService.registrar_movimiento(
        empresa_id=empresa.id,
        producto_id=serializer.validated_data['producto'].id,
        tipo=tipo,
        cantidad=cantidad,
        costo_unitario=costo_unitario,
        ...
    )
    ↓
[KardexService.registrar_entrada() @transaction.atomic]
  → Producto.objects.select_for_update().get(pk=producto_id, empresa_id=empresa_id)
  → crud_service.crear_movimiento_raw(empresa, producto, tipo, cantidad, costo_unitario, ...)
  → recalcular_stock_producto(producto_id, empresa_id)
      → stock = SUM(ENTRADA_*) - SUM(SALIDA_*)
      → UPDATE producto SET stock_actual = stock
    ↓
[Response 201 + MovimientoInventarioDetailSerializer]
  ↓
[movimientos_list.js] → table.replaceData() → nueva fila aparece con tipo badge
[productos_list.js]   → recargar() → stock_actual actualizado en tabla
```

---

## 12. Estadísticas del Módulo

| Categoría | Cantidad |
|-----------|---------|
| Modelos (1 abstracto + 6 concretos) | 7 |
| Migraciones | 5 |
| Clases de Servicio (KardexService, IngestaService, 6 Mixins) | 8 |
| Clases Selector (1 por modelo) | 6 |
| Funciones CRUD | 7 |
| ViewSets | 6 |
| Serializers | 14 |
| Archivos JS (2 base + 12 features) | 14 |
| Templates HTML | 13 |
| Tests | 0 ⚠️ |
