# Auditoría de Flujo - Módulo Inventario v2.60

**Fecha de Auditoría:** 2026-02-10  
**Versión del Módulo:** v2.60  
**App:** `apps/tenant/inventario`

---

## 📋 Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura General](#arquitectura-general)
3. [Modelos de Datos](#modelos-de-datos)
4. [API REST (Backend)](#api-rest-backend)
5. [Capa de Servicios](#capa-de-servicios)
6. [Frontend](#frontend)
7. [Flujos Principales](#flujos-principales)
8. [Integraciones](#integraciones)
9. [Optimizaciones y Mejores Prácticas](#optimizaciones-y-mejores-prácticas)
10. [Puntos de Atención](#puntos-de-atención)

---

## 1. Resumen Ejecutivo

### 1.1. Propósito del Módulo

El módulo **Inventario** gestiona:
- **Categorías**: Agrupación comercial de ítems (Productos, Servicios, Activos)
- **Productos**: Bienes tangibles con control de stock (Kardex)
- **Servicios**: Bienes intangibles sin stock
- **Activos Fijos**: Activos de uso interno con control de estado
- **Movimientos de Inventario**: Kardex (historial de entradas/salidas)
- **Historial de Servicios**: Log de ventas de servicios

### 1.2. Arquitectura

- **Backend**: Django REST Framework (DRF) con ViewSets
- **Frontend**: Vanilla JS + Tabulator Factory + HTMX + Bootstrap Offcanvas
- **Patrón**: API-First Architecture
- **Multi-tenancy**: Filtrado automático por `empresa` (SSoT)
- **Zero Trust**: Validación estricta de pertenencia al tenant

### 1.3. Principios de Diseño

- ✅ **Service Layer Pattern**: Lógica de negocio en `services.py`
- ✅ **QuerySet Optimization**: Campos estrictamente necesarios (`only()`)
- ✅ **Error Boundary Pattern**: Manejo centralizado de errores
- ✅ **Aislamiento Gradual**: Sin bloques try/catch, usa `UIManager.handleError()`
- ✅ **Performance Bible**: Prohibido `.all()`, uso de `select_related()`, `only()`

---

## 2. Arquitectura General

### 2.1. Estructura de Archivos

```
apps/tenant/inventario/
├── models.py              # Modelos de datos (6 modelos)
├── api/
│   ├── viewsets.py        # ViewSets DRF (6 ViewSets)
│   ├── serializers.py     # Serializers DRF (12 serializers)
│   └── urls.py            # Router DRF
├── services.py            # Lógica de negocio (Service Layer)
└── migrations/            # Migraciones Django

apps/tenant/core/
├── static/core/js/inventario/
│   ├── inventario.api.js      # Wrapper API (Capa de Datos)
│   ├── inventario_list.js     # Listado principal (Tabulator)
│   ├── inventario_editor.js   # Editor de productos (Offcanvas)
│   ├── productos.page.js      # Módulo Productos
│   ├── servicios.page.js      # Módulo Servicios
│   ├── activos.page.js        # Módulo Activos Fijos
│   ├── movimientos.page.js    # Módulo Movimientos (Kardex)
│   └── categorias.page.js     # Módulo Categorías
└── templates/tenant/core/partials/inventario/
    ├── list.html              # Vista principal (Tabs)
    ├── offcanvas_form.html    # Formulario Offcanvas (HTMX)
    ├── list_productos.html    # Tab Productos
    ├── list_servicios.html    # Tab Servicios
    ├── list_activos.html      # Tab Activos
    ├── list_movimientos.html  # Tab Movimientos
    └── assets_inventario.html # Assets y eventos HTMX
```

### 2.2. Flujo de Datos

```
┌─────────────┐
│   Frontend  │
│  (Tabulator)│
└──────┬──────┘
       │ HTTP (GET/POST/PATCH/DELETE)
       ▼
┌─────────────┐
│  inventario │
│   .api.js   │  ← Capa de Datos (retorna {ok, status, data})
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   ViewSets  │  ← DRF ViewSets (filtrado por empresa SSoT)
│  (viewsets) │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Services   │  ← Lógica de Negocio (recalcular_stock, etc.)
│ (services)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Models    │  ← Base de Datos (PostgreSQL)
│  (models)   │
└─────────────┘
```

### 2.3. Multi-tenancy

- **SSoT (Single Source of Truth)**: Todos los modelos tienen `empresa = ForeignKey(Empresa)`
- **Filtrado Automático**: ViewSets filtran por `empresa` automáticamente
- **Zero Trust**: Validación estricta de pertenencia al tenant en servicios

---

## 3. Modelos de Datos

### 3.1. Modelos Principales

#### 3.1.1. `CategoriaItem`
**Propósito**: Agrupación comercial de ítems

```python
class CategoriaItem(TimeStampedModel):
    empresa = ForeignKey(Empresa)  # SSoT
    nombre = CharField(max_length=100)
    descripcion = TextField(blank=True)
    aplicacion = CharField(choices=[
        'TODO', 'PRODUCTO', 'SERVICIO', 'ACTIVO'
    ])
    imagen = ImageField(upload_to='inventario/categorias/')
    activo = BooleanField(default=True)
```

**Relaciones**:
- `productos` (related_name) → `Producto.categoria`
- `servicios` (related_name) → `Servicio.categoria`
- `activos` (related_name) → `ActivoFijo.categoria`

**Reglas de Negocio**:
- Al eliminar categoría, los ítems asociados quedan con `categoria=None` (no se eliminan)
- No se puede eliminar categoría activa (debe desactivarse primero)

#### 3.1.2. `Producto`
**Propósito**: Bienes tangibles con control de stock

```python
class Producto(TimeStampedModel):
    empresa = ForeignKey(Empresa)  # SSoT
    codigo = CharField(max_length=64, unique=True)  # SKU único
    nombre = CharField(max_length=200)
    categoria = ForeignKey(CategoriaItem, null=True, blank=True)
    descripcion = TextField(blank=True)
    unidad = CharField(max_length=16, default="UND")
    imagen = ImageField(upload_to='inventario/productos/')
    
    # Precios
    precio_venta = DecimalField(max_digits=14, decimal_places=2)
    costo_promedio = DecimalField(max_digits=14, decimal_places=2)
    
    # Stock (desnormalizado - se recalcula desde Kardex)
    stock_actual = DecimalField(max_digits=14, decimal_places=3)
    stock_minimo = DecimalField(max_digits=14, decimal_places=3)
    
    activo = BooleanField(default=True)
```

**Relaciones**:
- `movimientos` (related_name) → `MovimientoInventario.producto` (CASCADE)

**Reglas de Negocio**:
- `stock_actual` se recalcula automáticamente desde `MovimientoInventario` (Kardex)
- No se puede eliminar producto activo (debe desactivarse primero)
- Al eliminar producto, se eliminan todos sus movimientos (CASCADE)

#### 3.1.3. `Servicio`
**Propósito**: Bienes intangibles sin stock

```python
class Servicio(TimeStampedModel):
    empresa = ForeignKey(Empresa)  # SSoT
    codigo = CharField(max_length=64, unique=True)
    nombre = CharField(max_length=200)
    categoria = ForeignKey(CategoriaItem, null=True, blank=True)
    descripcion = TextField(blank=True)
    imagen = ImageField(upload_to='inventario/servicios/')
    precio_venta = DecimalField(max_digits=14, decimal_places=2)
    activo = BooleanField(default=True)
```

**Relaciones**:
- `historial_ventas` (related_name) → `HistorialServicio.servicio` (CASCADE)

**Reglas de Negocio**:
- No tiene control de stock (es intangible)
- No se puede eliminar servicio activo (debe desactivarse primero)
- Al eliminar servicio, se eliminan todos sus historiales (CASCADE)

#### 3.1.4. `ActivoFijo`
**Propósito**: Activos de uso interno

```python
class ActivoFijo(TimeStampedModel):
    empresa = ForeignKey(Empresa)  # SSoT
    codigo = CharField(max_length=64, unique=True)  # Placa, Serial
    nombre = CharField(max_length=200)
    categoria = ForeignKey(CategoriaItem, null=True, blank=True)
    marca = CharField(max_length=100, blank=True)
    modelo = CharField(max_length=100, blank=True)
    descripcion = TextField(blank=True)
    imagen = ImageField(upload_to='inventario/activos/')
    ubicacion = CharField(max_length=100, blank=True)
    responsable = CharField(max_length=100, blank=True)
    fecha_adquisicion = DateField(null=True, blank=True)
    costo_adquisicion = DecimalField(max_digits=14, decimal_places=2)
    estado = CharField(choices=[
        'ACTIVO', 'MANTENIMIENTO', 'BAJA', 'VENDIDO'
    ])
```

**Reglas de Negocio**:
- No se puede eliminar activo con estado 'ACTIVO' (debe cambiar estado primero)
- No tiene control de stock (es activo fijo, no inventario)

#### 3.1.5. `MovimientoInventario` (Kardex)
**Propósito**: Historial de movimientos de stock

```python
class MovimientoInventario(TimeStampedModel):
    empresa = ForeignKey(Empresa)  # SSoT
    producto = ForeignKey(Producto, CASCADE)  # Si se elimina producto, se eliminan movimientos
    tipo = CharField(choices=[
        # ENTRADAS
        'ENTRADA_COMPRA', 'ENTRADA_AJUSTE', 'ENTRADA_DEVOLUCION',
        # SALIDAS
        'SALIDA_VENTA', 'SALIDA_BAJA', 'SALIDA_CONSUMO'
    ])
    cantidad = DecimalField(max_digits=14, decimal_places=3)
    costo_unitario = DecimalField(max_digits=14, decimal_places=2)
    
    # Trazabilidad externa
    origen_referencia = CharField(max_length=100, blank=True)  # "FAC-123", "ORD-456"
    cliente_referencia = CharField(max_length=200, blank=True)
    observaciones = TextField(blank=True)
```

**Reglas de Negocio**:
- **Solo lectura y creación**: No se puede editar/eliminar movimientos (integridad del Kardex)
- **Recálculo automático**: Al crear movimiento, se recalcula `stock_actual` del producto
- **Validación de stock**: Al registrar salida, se valida que haya stock suficiente

#### 3.1.6. `HistorialServicio`
**Propósito**: Log de ventas de servicios

```python
class HistorialServicio(TimeStampedModel):
    empresa = ForeignKey(Empresa)  # SSoT
    servicio = ForeignKey(Servicio, CASCADE)
    fecha_registro = DateField(default=timezone.now)
    cantidad = DecimalField(max_digits=10, decimal_places=2, default=1)
    valor_cobrado = DecimalField(max_digits=14, decimal_places=2)
    
    # Trazabilidad externa
    origen_referencia = CharField(max_length=100, blank=True)
    cliente_referencia = CharField(max_length=200, blank=True)
    observaciones = TextField(blank=True)
```

**Reglas de Negocio**:
- Solo lectura y creación (no se edita/elimina)
- Al eliminar servicio, se eliminan todos sus historiales (CASCADE)

### 3.2. Modelo Base

```python
class TimeStampedModel(models.Model):
    """Modelo base abstracto para auditoría de tiempos."""
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
```

---

## 4. API REST (Backend)

### 4.1. ViewSets

#### 4.1.1. `CategoriaItemViewSet`
**Endpoint**: `/api/v1/inventario/categorias/`

**Acciones**:
- `GET /categorias/` - Lista paginada (Tabulator)
- `GET /categorias/{id}/` - Detalle
- `POST /categorias/` - Crear (solo ADMIN)
- `PATCH /categorias/{id}/` - Actualizar (solo ADMIN)
- `DELETE /categorias/{id}/` - Eliminar (solo ADMIN, debe estar inactiva)
- `GET /categorias/{id}/resumen/` - Resumen con conteo de ítems asociados
- `GET /categorias/dt/` - DataTables client-side (DEPRECATED v2.40)

**Filtrado**:
- Automático por `empresa` (SSoT)
- Búsqueda: `?search=texto` (busca en `nombre`, `descripcion`)

**Reglas de Eliminación**:
- No se puede eliminar categoría activa
- Al eliminar, los ítems asociados quedan con `categoria=None`

#### 4.1.2. `ProductoViewSet`
**Endpoint**: `/api/v1/inventario/productos/`

**Acciones**:
- `GET /productos/` - Lista paginada (Tabulator)
- `GET /productos/{id}/` - Detalle
- `POST /productos/` - Crear (solo ADMIN)
- `PATCH /productos/{id}/` - Actualizar (solo ADMIN)
- `DELETE /productos/{id}/` - Eliminar (solo ADMIN, debe estar inactivo)
- `GET /productos/{id}/stock/` - Stock actual (optimizado)
- `GET /productos/{id}/kardex/` - Historial de movimientos (Kardex)
- `GET /productos/gestor-offcanvas/` - HTML del formulario Offcanvas (HTMX)
- `POST /productos/dt/` - DataTables server-side (DEPRECATED v2.40)

**Filtrado**:
- Automático por `empresa` (SSoT)
- Búsqueda: `?search=texto` (busca en `codigo`, `nombre`, `categoria__nombre`)

**Reglas de Eliminación**:
- No se puede eliminar producto activo
- Al eliminar, se eliminan todos sus movimientos (CASCADE)

#### 4.1.3. `ServicioViewSet`
**Endpoint**: `/api/v1/inventario/servicios/`

**Acciones**:
- `GET /servicios/` - Lista paginada (Tabulator)
- `GET /servicios/{id}/` - Detalle
- `POST /servicios/` - Crear (solo ADMIN)
- `PATCH /servicios/{id}/` - Actualizar (solo ADMIN)
- `DELETE /servicios/{id}/` - Eliminar (solo ADMIN, debe estar inactivo)
- `POST /servicios/dt/` - DataTables server-side (DEPRECATED v2.40)

**Filtrado**:
- Automático por `empresa` (SSoT)
- Búsqueda: `?search=texto` (busca en `codigo`, `nombre`, `categoria__nombre`)

#### 4.1.4. `ActivoFijoViewSet`
**Endpoint**: `/api/v1/inventario/activos/`

**Acciones**:
- `GET /activos/` - Lista paginada (Tabulator)
- `GET /activos/{id}/` - Detalle
- `POST /activos/` - Crear (solo ADMIN)
- `PATCH /activos/{id}/` - Actualizar (solo ADMIN)
- `DELETE /activos/{id}/` - Eliminar (solo ADMIN, no puede estar en estado 'ACTIVO')
- `GET /activos/list-all/` - Lista completa sin paginación (client-side DataTables)
- `POST /activos/dt/` - DataTables server-side (DEPRECATED v2.40)

**Filtrado**:
- Automático por `empresa` (SSoT)
- Búsqueda: `?search=texto` (busca en `codigo`, `nombre`, `categoria__nombre`, `ubicacion`, `responsable`)

#### 4.1.5. `MovimientoInventarioViewSet`
**Endpoint**: `/api/v1/inventario/movimientos/`

**Acciones**:
- `GET /movimientos/` - Lista paginada (Tabulator)
- `GET /movimientos/{id}/` - Detalle
- `POST /movimientos/` - Crear (solo ADMIN, recalcula stock automáticamente)
- `POST /movimientos/dt/` - DataTables server-side (DEPRECATED v2.40)

**Restricciones**:
- **Solo lectura y creación**: No permite `update()` ni `destroy()` (integridad del Kardex)

**Filtrado**:
- Automático por `empresa` (a través de `producto__empresa`)
- Búsqueda: `?search=texto` (busca en `producto__codigo`, `producto__nombre`, `origen_referencia`, `observaciones`)

#### 4.1.6. `HistorialServicioViewSet`
**Endpoint**: `/api/v1/inventario/historial-servicios/`

**Acciones**:
- `GET /historial-servicios/` - Lista (sin paginación)
- `GET /historial-servicios/{id}/` - Detalle
- `POST /historial-servicios/` - Crear (solo ADMIN)

**Restricciones**:
- **Solo lectura y creación**: No permite `update()` ni `destroy()`

### 4.2. BaseViewSet (Clase Base)

**Características**:
- **Enforced Mode**: Solo ADMIN/STAFF puede crear/editar/eliminar
- **Asignación automática de Empresa**: `perform_create()` asigna `empresa` automáticamente
- **Multi-tenancy**: Filtrado automático por `empresa` (SSoT)
- **Parser Classes**: Soporta `JSONParser`, `FormParser`, `MultiPartParser` (para imágenes)

**Métodos sobrescritos**:
- `create()` - Valida permisos (Enforced Mode)
- `update()` - Valida permisos (Enforced Mode)
- `destroy()` - Valida permisos (Enforced Mode)
- `perform_create()` - Asigna `empresa` automáticamente

### 4.3. Serializers

#### 4.3.1. Serializers de Lista (Optimizados)

**Propósito**: Solo campos necesarios para tablas Tabulator

- `CategoriaItemListSerializer`: `['id', 'nombre', 'descripcion', 'aplicacion', 'activo']`
- `ProductoListSerializer`: Incluye campos calculados (`valor_inventario`, `alerta_stock`)
- `ServicioListSerializer`: `['id', 'codigo', 'nombre', 'categoria_nombre', 'precio_venta', 'activo']`
- `ActivoFijoListSerializer`: `['id', 'codigo', 'nombre', 'categoria_nombre', 'ubicacion', 'responsable', 'estado']`
- `MovimientoInventarioListSerializer`: `['id', 'created_at', 'producto_codigo', 'producto_nombre', 'tipo_display', 'cantidad', ...]`

#### 4.3.2. Serializers Completos

**Propósito**: Todos los campos para detalle/edición

- `CategoriaItemSerializer`
- `ProductoSerializer`
- `ServicioSerializer`
- `ActivoFijoSerializer`
- `MovimientoInventarioSerializer`
- `HistorialServicioSerializer`

### 4.4. Paginación

**Clase**: `StandardResultsSetPagination`

```python
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10  # Default
    page_size_query_param = 'page_size'
    max_page_size = 100
```

**Formato de respuesta**:
```json
{
  "count": 100,
  "next": "http://.../api/v1/inventario/productos/?page=2",
  "previous": null,
  "results": [...]
}
```

### 4.5. Router DRF

**Archivo**: `apps/tenant/inventario/api/urls.py`

```python
router = DefaultRouter()
router.register(r'categorias', CategoriaItemViewSet, basename='inv-categorias')
router.register(r'productos', ProductoViewSet, basename='inv-productos')
router.register(r'servicios', ServicioViewSet, basename='inv-servicios')
router.register(r'activos', ActivoFijoViewSet, basename='inv-activos')
router.register(r'movimientos', MovimientoInventarioViewSet, basename='inv-movimientos')
router.register(r'historial-servicios', HistorialServicioViewSet, basename='inv-historial-servicios')
```

---

## 5. Capa de Servicios

### 5.1. QuerySets Optimizados

**Archivo**: `apps/tenant/inventario/services.py`

**Funciones**:
- `qs_categoria_list()` - QuerySet optimizado para categorías
- `qs_producto_list(empresa_id, search=None)` - QuerySet optimizado para productos
- `qs_servicio_list(empresa_id, search=None)` - QuerySet optimizado para servicios
- `qs_activo_list(empresa_id, search=None)` - QuerySet optimizado para activos
- `qs_movimiento_list(empresa_id, search=None)` - QuerySet optimizado para movimientos

**Optimizaciones**:
- Uso de `select_related()` para evitar N+1 queries
- Uso de `only()` para cargar solo campos necesarios
- Campos alineados con serializers de lista

**Constantes de campos**:
```python
CATEGORIA_LIST_FIELDS = ('id', 'nombre', 'descripcion', 'aplicacion', 'activo', 'empresa_id')
PRODUCTO_LIST_FIELDS = ('id', 'codigo', 'nombre', 'categoria', 'categoria__id', 'categoria__nombre', ...)
# ... etc
```

### 5.2. Gestión de Stock (Motor de Kardex)

#### 5.2.1. `calcular_stock(producto_id)`
**Propósito**: Calcula el stock actual basado en movimientos (solo lectura)

**Lógica**:
```
Stock = Entradas - Salidas + Ajustes Positivos - Ajustes Negativos
```

**Tipos de Entrada**:
- `ENTRADA_COMPRA`
- `ENTRADA_DEVOLUCION`
- `ENTRADA_AJUSTE` (solo si cantidad > 0)

**Tipos de Salida**:
- `SALIDA_VENTA`
- `SALIDA_BAJA`
- `SALIDA_CONSUMO`

#### 5.2.2. `recalcular_stock_producto(producto_id)`
**Propósito**: Recalcula y actualiza el campo `stock_actual` del producto

**Características**:
- Usa `select_for_update()` para lock optimista
- Transaccional (`@transaction.atomic`)
- Solo actualiza `stock_actual` y `updated_at` (`update_fields`)

**Llamado automáticamente**:
- Al crear `MovimientoInventario` (en `perform_create()` del ViewSet)
- Al usar `registrar_entrada()`, `registrar_salida()`, `ajustar_stock()`

#### 5.2.3. `registrar_entrada(producto_id, empresa_id, cantidad, ...)`
**Propósito**: Registra entrada de producto (compra, devolución, ajuste positivo)

**Validaciones**:
- Cantidad debe ser positiva
- Producto debe existir y pertenecer al tenant (Zero Trust)
- Tipo de movimiento debe ser de entrada válido

**Tipos de movimiento soportados**:
- `ENTRADA_COMPRA` (default)
- `ENTRADA_DEVOLUCION`
- `ENTRADA_AJUSTE`

**Efectos**:
- Crea `MovimientoInventario`
- Recalcula `stock_actual` automáticamente

#### 5.2.4. `registrar_salida(producto_id, empresa_id, cantidad, ...)`
**Propósito**: Registra salida de producto (venta, baja, consumo interno)

**Validaciones**:
- Cantidad debe ser positiva
- Producto debe existir y pertenecer al tenant (Zero Trust)
- **Stock suficiente**: `stock_actual >= cantidad`
- Tipo de movimiento debe ser de salida válido

**Tipos de movimiento soportados**:
- `SALIDA_VENTA` (default)
- `SALIDA_BAJA`
- `SALIDA_CONSUMO`

**Efectos**:
- Crea `MovimientoInventario`
- Recalcula `stock_actual` automáticamente

#### 5.2.5. `ajustar_stock(producto_id, empresa_id, cantidad_ajuste, ...)`
**Propósito**: Ajusta el stock (puede ser positivo o negativo)

**Validaciones**:
- Producto debe existir y pertenecer al tenant (Zero Trust)
- **No puede resultar en stock negativo**: `stock_actual + cantidad_ajuste >= 0`

**Lógica**:
- Si `cantidad_ajuste > 0`: Crea movimiento tipo `ENTRADA_AJUSTE`
- Si `cantidad_ajuste < 0`: Crea movimiento tipo `SALIDA_BAJA` (con cantidad positiva)

**Efectos**:
- Crea `MovimientoInventario`
- Recalcula `stock_actual` automáticamente

#### 5.2.6. `registrar_movimiento(...)`
**Propósito**: Función genérica para crear movimiento (usada por APIs externas)

**Características**:
- Transaccional
- Recalcula stock automáticamente
- Soporta todos los tipos de movimiento

### 5.3. Ingesta de Datos (Carga Masiva)

#### 5.3.1. `materializar_inventario_desde_dto(dto)`
**Propósito**: Materializa inventario desde DTO canónico del pipeline de documentos

**Soporta**:
- Productos
- Servicios
- Activos Fijos

**Características**:
- Crea categoría automáticamente si no existe
- Si es producto nuevo con stock inicial, crea movimiento de ajuste
- Transaccional

**Retorna**:
- `(payload, 201)` si se crea nuevo registro
- `(payload, 200)` si se actualiza registro existente
- `(error, 422)` si hay error

#### 5.3.2. `materializar_carga_masiva_productos(empresa_id, lista_datos, usuario=None)`
**Propósito**: Carga masiva de productos desde lista de diccionarios

**Características**:
- Procesa lista de productos
- Crea categorías automáticamente
- Si es producto nuevo con stock inicial, crea movimiento de ajuste
- Transaccional (todo o nada)

**Retorna**:
```python
{
  "creados": int,
  "actualizados": int,
  "errores": [str, ...]
}
```

### 5.4. Gestión de Activos Fijos

#### 5.4.1. `crear_activo_fijo(...)`
**Propósito**: Crea un ActivoFijo

**Características**:
- Si `empresa_id` es `None`, usa empresa singleton del tenant
- Transaccional

---

## 6. Frontend

### 6.1. Arquitectura Frontend

**Patrón**: Feature-Sliced Architecture

```
┌─────────────────────────────────────┐
│   Capa de Presentación              │
│   (Tabulator, Bootstrap Offcanvas)  │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Capa de Lógica                    │
│   (inventario_list.js,              │
│    inventario_editor.js, etc.)      │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Capa de Datos                     │
│   (inventario.api.js)                │
│   Retorna: {ok, status, data}       │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   HTTP Layer                        │
│   (w.http)                          │
└─────────────────────────────────────┘
```

### 6.2. Capa de Datos: `inventario.api.js`

**Propósito**: Wrapper de API que retorna siempre `{ok, status, data}`

**Métodos principales**:
```javascript
w.inventarioAPI = {
  productos: {
    list: async (params) => {...},      // GET /productos/
    get: async (id) => {...},           // GET /productos/{id}/
    save: async (payload) => {...},     // POST /productos/
    update: async (id, payload) => {...}, // PATCH /productos/{id}/
    delete: async (id) => {...},       // DELETE /productos/{id}/
    stock: async (id) => {...},         // GET /productos/{id}/stock/
    kardex: async (id) => {...}         // GET /productos/{id}/kardex/
  },
  servicios: {...},
  activos: {...},
  movimientos: {...},
  categorias: {...}
}
```

**Características**:
- Resuelve URL base dinámicamente usando `w.Routes` (si está disponible)
- Fallback a URL hardcodeada si `Routes` no está disponible
- Todos los métodos son `async`

### 6.3. Capa de Lógica

#### 6.3.1. `inventario_list.js`
**Propósito**: Listado principal con Tabs (Productos, Servicios, Activos, Movimientos)

**Características**:
- Usa Tabulator Factory para tablas
- Navegación por Tabs (Bootstrap 5)
- Búsqueda en tiempo real
- Botones de acción (Nuevo, Entrada/Salida, Refrescar)

#### 6.3.2. `inventario_editor.js`
**Propósito**: Editor de productos (crear/editar) usando Offcanvas

**Características**:
- Carga formulario mediante HTMX (`/api/v1/inventario/productos/gestor-offcanvas/`)
- Validación de formulario
- Manejo de errores (Error Boundary Pattern)
- Soporta modo creación y edición

#### 6.3.3. Módulos Específicos

- `productos.page.js` - Módulo Productos (Tabulator)
- `servicios.page.js` - Módulo Servicios (Tabulator)
- `activos.page.js` - Módulo Activos Fijos (Tabulator)
- `movimientos.page.js` - Módulo Movimientos/Kardex (Tabulator)
- `categorias.page.js` - Módulo Categorías (DataTables client-side)

### 6.4. Templates

#### 6.4.1. `list.html`
**Propósito**: Vista principal con Tabs

**Estructura**:
- Tabs: Existencias | Movimientos Recientes
- Toolbar con botones de acción
- Contenedores para tablas Tabulator
- Offcanvas container para formularios

#### 6.4.2. `offcanvas_form.html`
**Propósito**: Formulario Offcanvas (HTMX)

**Características**:
- Carga dinámicamente mediante HTMX
- Soporta modo creación y edición
- Soporta formulario de producto y formulario de ajuste de inventario
- Validación HTML5

#### 6.4.3. Templates de Listado

- `list_productos.html` - Tab Productos
- `list_servicios.html` - Tab Servicios
- `list_activos.html` - Tab Activos
- `list_movimientos.html` - Tab Movimientos

#### 6.4.4. `assets_inventario.html`
**Propósito**: Assets y eventos HTMX

**Eventos**:
- `htmx:afterSwap` - Inicializa módulos después de cargar contenido HTMX
- `initInventarioEditor` - Inicializa editor de productos

---

## 7. Flujos Principales

### 7.1. Flujo: Crear Producto

```
1. Usuario hace clic en "Nuevo Producto"
   ↓
2. HTMX carga formulario Offcanvas
   GET /api/v1/inventario/productos/gestor-offcanvas/
   ↓
3. Backend renderiza template offcanvas_form.html
   (con catálogo de categorías)
   ↓
4. Usuario completa formulario y hace clic en "Guardar"
   ↓
5. inventario_editor.js recolecta datos del formulario
   ↓
6. inventario.api.js envía POST /api/v1/inventario/productos/
   ↓
7. ProductoViewSet.create() valida permisos (Enforced Mode)
   ↓
8. ProductoViewSet.perform_create() asigna empresa automáticamente
   ↓
9. Se crea Producto en BD
   ↓
10. Se retorna respuesta 201 Created
    ↓
11. Frontend cierra Offcanvas y muestra notificación de éxito
    ↓
12. Frontend dispara evento 'productoGuardado' para refrescar tabla
```

### 7.2. Flujo: Registrar Entrada de Stock

```
1. Usuario hace clic en "Entrada/Salida"
   ↓
2. HTMX carga formulario Offcanvas (tipo=ajuste)
   GET /api/v1/inventario/productos/gestor-offcanvas/?tipo=ajuste
   ↓
3. Backend renderiza template offcanvas_form.html
   (con tipos de movimiento)
   ↓
4. Usuario selecciona producto, tipo de movimiento, cantidad, etc.
   ↓
5. inventario_editor.js recolecta datos del formulario
   ↓
6. inventario.api.js envía POST /api/v1/inventario/movimientos/
   ↓
7. MovimientoInventarioViewSet.create() valida permisos
   ↓
8. MovimientoInventarioViewSet.perform_create():
   - Crea MovimientoInventario
   - Llama a recalcular_stock_producto() automáticamente
   ↓
9. services.recalcular_stock_producto():
   - Calcula nuevo stock desde movimientos
   - Actualiza Producto.stock_actual
   ↓
10. Se retorna respuesta 201 Created
    ↓
11. Frontend cierra Offcanvas y muestra notificación de éxito
    ↓
12. Frontend refresca tabla de productos (stock actualizado)
```

### 7.3. Flujo: Consultar Kardex de Producto

```
1. Usuario hace clic en "Ver Kardex" en tabla de productos
   ↓
2. inventario_list.js obtiene ID del producto
   ↓
3. inventario.api.js envía GET /api/v1/inventario/productos/{id}/kardex/
   ↓
4. ProductoViewSet.kardex():
   - Valida que producto pertenezca al tenant (Zero Trust)
   - Obtiene movimientos con select_related('producto')
   - Usa only() para optimizar campos
   ↓
5. Retorna JSON con producto y movimientos
   ↓
6. Frontend muestra modal/offcanvas con historial de movimientos
```

### 7.4. Flujo: Eliminar Producto

```
1. Usuario hace clic en "Eliminar" en tabla de productos
   ↓
2. Frontend muestra confirmación (SweetAlert2 o similar)
   ↓
3. Si confirma, inventario.api.js envía DELETE /api/v1/inventario/productos/{id}/
   ↓
4. ProductoViewSet.destroy():
   - Valida permisos (Enforced Mode)
   - Valida que producto no esté activo
   ↓
5. Si está activo, retorna 400 Bad Request
   ↓
6. Si está inactivo:
   - Django elimina Producto (CASCADE elimina MovimientoInventario)
   ↓
7. Se retorna respuesta 204 No Content
   ↓
8. Frontend refresca tabla
```

---

## 8. Integraciones

### 8.1. Pipeline Universal de Documentos

**Endpoint**: `materializar_inventario_desde_dto(dto)`

**Propósito**: Materializa inventario desde DTO canónico del pipeline de documentos

**Flujo**:
```
Document Parser → DTO Canónico → materializar_inventario_desde_dto() → BD
```

**Soporta**:
- Productos
- Servicios
- Activos Fijos

**Características**:
- Crea categorías automáticamente
- Si es producto nuevo con stock inicial, crea movimiento de ajuste
- Transaccional

### 8.2. Módulo de Ventas (Futuro)

**Integración propuesta**:
- Al crear venta, registrar salida de stock automáticamente
- Usar `registrar_salida()` o `registrar_movimiento()`

**Ejemplo**:
```python
from apps.tenant.inventario.services import registrar_salida

# En módulo de ventas
for item in venta.items:
    if item.tipo == 'producto':
        registrar_salida(
            producto_id=item.producto_id,
            empresa_id=empresa.id,
            cantidad=item.cantidad,
            tipo_movimiento=MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
            origen_referencia=f"VENTA-{venta.id}",
            cliente_referencia=venta.cliente.razon_social
        )
```

### 8.3. Módulo de Compras (Futuro)

**Integración propuesta**:
- Al crear compra, registrar entrada de stock automáticamente
- Usar `registrar_entrada()` o `registrar_movimiento()`

**Ejemplo**:
```python
from apps.tenant.inventario.services import registrar_entrada

# En módulo de compras
for item in compra.items:
    registrar_entrada(
        producto_id=item.producto_id,
        empresa_id=empresa.id,
        cantidad=item.cantidad,
        tipo_movimiento=MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
        costo_unitario=item.costo_unitario,
        origen_referencia=f"COMPRA-{compra.id}"
    )
```

---

## 9. Optimizaciones y Mejores Prácticas

### 9.1. Performance Bible

#### 9.1.1. QuerySets Optimizados
- ✅ **PROHIBIDO `.all()`**: Siempre filtrar por `empresa` (SSoT)
- ✅ **Uso de `only()`**: Cargar solo campos necesarios
- ✅ **Uso de `select_related()`**: Evitar N+1 queries
- ✅ **Uso de `prefetch_related()`**: Para relaciones reversas (si es necesario)

**Ejemplo**:
```python
# ✅ CORRECTO
qs = Producto.objects.filter(empresa_id=empresa_id)\
    .select_related('categoria')\
    .only('id', 'codigo', 'nombre', 'categoria__nombre', 'stock_actual')

# ❌ INCORRECTO
qs = Producto.objects.all()  # PROHIBIDO
```

#### 9.1.2. Empresa Singleton
- ✅ **Usar `.only('id')`**: Solo obtener ID de empresa
- ✅ **Usar `.first()`**: No usar `.all()` ni `.get()`

**Ejemplo**:
```python
# ✅ CORRECTO
empresa = Empresa.objects.only('id').first()

# ❌ INCORRECTO
empresa = Empresa.objects.all().first()  # Carga todos los campos
empresa = Empresa.objects.get()  # Puede fallar si no existe
```

#### 9.1.3. Actualizaciones Parciales
- ✅ **Usar `update_fields`**: Solo actualizar campos necesarios

**Ejemplo**:
```python
# ✅ CORRECTO
producto.stock_actual = nuevo_stock
producto.save(update_fields=['stock_actual', 'updated_at'])

# ❌ INCORRECTO
producto.save()  # Actualiza todos los campos
```

#### 9.1.4. Transacciones
- ✅ **Usar `@transaction.atomic`**: Para operaciones que deben ser atómicas
- ✅ **Usar `select_for_update()`**: Para locks optimistas

**Ejemplo**:
```python
@transaction.atomic
def recalcular_stock_producto(producto_id):
    producto = Producto.objects.select_for_update()\
        .only('id', 'stock_actual')\
        .get(id=producto_id)
    # ... calcular y actualizar
```

### 9.2. Zero Trust

**Principio**: Validar siempre que los recursos pertenezcan al tenant

**Implementación**:
```python
# ✅ CORRECTO
producto = Producto.objects.filter(
    pk=producto_id, 
    empresa_id=empresa_id
).first()
if not producto:
    raise ValidationError("Producto no encontrado o no pertenece a este tenant")

# ❌ INCORRECTO
producto = Producto.objects.get(pk=producto_id)  # No valida tenant
```

### 9.3. Error Boundary Pattern

**Frontend**: Usar `UIManager.handleError()` para manejo centralizado de errores

**Ejemplo**:
```javascript
if (!res.ok) {
    if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, '[inventario.editor]', {
            modalSelector: '#offcanvas-inventario',
            errorContainerSelector: '#form-inventario-feedback'
        });
    }
}
```

### 9.4. Aislamiento Gradual

**Principio**: Sin bloques try/catch, solo verificar `ok` en respuestas

**Ejemplo**:
```javascript
// ✅ CORRECTO
const res = await w.inventarioAPI.productos.save(data);
if (!res.ok) {
    // Manejar error con UIManager
    return;
}
// Continuar con éxito

// ❌ INCORRECTO
try {
    const res = await w.inventarioAPI.productos.save(data);
    // ...
} catch (e) {
    // ...
}
```

---

## 10. Puntos de Atención

### 10.1. Reglas de Eliminación

⚠️ **IMPORTANTE**: No se puede eliminar registros activos

- **Categorías**: Debe estar `activo=False` antes de eliminar
- **Productos**: Debe estar `activo=False` antes de eliminar
- **Servicios**: Debe estar `activo=False` antes de eliminar
- **Activos Fijos**: No puede estar en estado `ACTIVO` antes de eliminar

### 10.2. Integridad del Kardex

⚠️ **CRÍTICO**: Los movimientos de inventario no se pueden editar/eliminar

- **Razón**: Garantizar integridad del historial de stock
- **Solución**: Crear movimiento de ajuste si hay error

### 10.3. Stock Desnormalizado

⚠️ **ATENCIÓN**: `Producto.stock_actual` es un campo desnormalizado

- **Razón**: Performance (evitar calcular stock en cada consulta)
- **Mantenimiento**: Se recalcula automáticamente al crear movimientos
- **Riesgo**: Si se modifica manualmente, puede desincronizarse

**Solución**: Nunca modificar `stock_actual` manualmente, siempre usar movimientos

### 10.4. Endpoints Deprecated

⚠️ **DEPRECATED v2.40**: Endpoints DataTables server-side

- `POST /api/v1/inventario/productos/dt/`
- `POST /api/v1/inventario/servicios/dt/`
- `POST /api/v1/inventario/activos/dt/`
- `POST /api/v1/inventario/movimientos/dt/`

**Reemplazo**: Usar endpoints GET estándar con paginación DRF

**Eliminación**: v2.50

### 10.5. Categorías y Relaciones

⚠️ **ATENCIÓN**: Al eliminar categoría, los ítems asociados quedan con `categoria=None`

- **Razón**: Evitar eliminar ítems al eliminar categoría
- **Comportamiento**: Los ítems siguen existiendo, solo pierden la categoría

### 10.6. Validación de Stock en Salidas

⚠️ **CRÍTICO**: Se valida stock suficiente antes de registrar salida

- **Regla**: `stock_actual >= cantidad`
- **Error**: Si no hay stock suficiente, se retorna `ValidationError`

### 10.7. Multi-tenancy

⚠️ **CRÍTICO**: Siempre filtrar por `empresa` (SSoT)

- **Riesgo**: Si no se filtra, se pueden ver/editar recursos de otros tenants
- **Solución**: ViewSets filtran automáticamente, pero servicios deben validar también

---

## 11. Conclusión

El módulo **Inventario v2.60** es un sistema completo y robusto para la gestión de inventario con:

✅ **Arquitectura sólida**: API-First, Service Layer, Multi-tenancy  
✅ **Performance optimizado**: QuerySets optimizados, campos estrictamente necesarios  
✅ **Integridad de datos**: Kardex inmutable, stock desnormalizado mantenido automáticamente  
✅ **Zero Trust**: Validación estricta de pertenencia al tenant  
✅ **Frontend moderno**: Tabulator Factory, HTMX, Bootstrap Offcanvas  
✅ **Extensibilidad**: Preparado para integraciones con Ventas, Compras, etc.

**Próximos pasos recomendados**:
1. Integración con módulo de Ventas (registrar salidas automáticamente)
2. Integración con módulo de Compras (registrar entradas automáticamente)
3. Dashboard de inventario (alertas de stock bajo, valor de inventario, etc.)
4. Reportes de inventario (Kardex por rango de fechas, movimientos por tipo, etc.)

---

**Fin del Documento**
