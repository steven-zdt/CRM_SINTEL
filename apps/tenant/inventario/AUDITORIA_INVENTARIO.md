# Auditoría de Flujo - Módulo Inventario v2.61.4

**Fecha de Auditoría:** 2026-03-12  
**Versión del Módulo:** v2.61.4  
**App:** `apps/tenant/inventario`  
**Última actualización:** 2026-03-12

---

## 📋 Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura General](#arquitectura-general)
3. [Modelos de Datos](#modelos-de-datos)
4. [API REST (Backend)](#api-rest-backend)
   - 4.0. [Core API Facade (v2.61.3)](#40-core-api-facade-v2613)
5. [Capa de Servicios](#capa-de-servicios)
6. [Frontend](#frontend)
   - 6.0. [Feature-Sliced Architecture (v2.61.3)](#60-feature-sliced-architecture-v2613)
7. [Flujos Principales](#flujos-principales)
8. [Integraciones](#integraciones)
9. [Optimizaciones y Mejores Prácticas](#optimizaciones-y-mejores-prácticas)
10. [Puntos de Atención](#puntos-de-atención)
11. [Flujo Completo: Workspace → Core API → Models](#11-flujo-completo-workspace--core-api--models)
12. [Conclusión](#12-conclusión)
13. [Notas de Versión](#13-notas-de-versión)

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
├── api/v1/inventario/
│   ├── viewsets.py            # Core API Facade ViewSets (5 ViewSets)
│   └── serializers.py         # Workspace Serializers (10 serializers)
├── static/core/js/inventario/
│   ├── features/              # ⚠️ v2.61.3: Feature-Sliced Architecture
│   │   ├── categorias_list.js      # Feature: READ categorías
│   │   ├── categorias_editor.js    # Feature: CREATE/UPDATE categorías
│   │   ├── productos_list.js       # Feature: READ productos
│   │   ├── productos_editor.js    # Feature: CREATE/UPDATE productos
│   │   ├── servicios_list.js       # Feature: READ servicios
│   │   ├── servicios_editor.js     # Feature: CREATE/UPDATE servicios
│   │   ├── activos_list.js         # Feature: READ activos
│   │   ├── activos_editor.js       # Feature: CREATE/UPDATE activos
│   │   ├── movimientos_list.js     # Feature: READ movimientos
│   │   ├── movimientos_editor.js   # Feature: CREATE movimientos
│   │   ├── inventario_list.js      # Legacy: Listado principal
│   │   └── inventario_editor.js    # Legacy: Editor principal
│   ├── inventario.api.js      # Wrapper API (Capa de Datos)
│   ├── categorias.page.js     # ⚠️ DEPRECATED v2.61.3
│   ├── productos.page.js      # ⚠️ DEPRECATED v2.61.3
│   ├── servicios.page.js      # ⚠️ DEPRECATED v2.61.3
│   ├── activos.page.js        # ⚠️ DEPRECATED v2.61.3
│   └── movimientos.page.js    # ⚠️ DEPRECATED v2.61.3
└── templates/tenant/core/partials/inventario/
    ├── list.html              # Vista principal (Tabs)
    ├── offcanvas_form.html    # Formulario Offcanvas (HTMX)
    ├── list_productos.html    # Tab Productos
    ├── list_servicios.html    # Tab Servicios
    ├── list_activos.html      # Tab Activos
    ├── list_movimientos.html  # Tab Movimientos
    └── assets_inventario.html # Assets y eventos HTMX
```

### 2.2. Flujo de Datos Completo (v2.61.3)

```
┌─────────────────────────────────────────┐
│   workspace.html                        │
│   → #inventario (hash navigation)       │
│   → Carga list.html (HTMX)              │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│   Frontend (Tabulator + HTMX)           │
│   - inventario_list.js                  │
│   - inventario_editor.js                │
│   - productos.page.js                   │
└──────────────┬──────────────────────────┘
               │ HTTP (GET/POST/PATCH/DELETE)
               │ /api/v1/core/v1/inventario/...
               ▼
┌─────────────────────────────────────────┐
│   inventario.api.js                     │
│   ← Capa de Datos                       │
│   Retorna: {ok, status, data}           │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│   Core API Facade                       │
│   /api/v1/core/v1/inventario/           │
│   - ProductoCoreViewSet                 │
│   - CategoriaItemCoreViewSet            │
│   - MovimientoInventarioCoreViewSet     │
└──────────────┬──────────────────────────┘
               │ (Hereda acciones @action)
               ▼
┌─────────────────────────────────────────┐
│   App API ViewSets                      │
│   /api/v1/inventario/                   │
│   - ProductoViewSet                     │
│   - CategoriaItemViewSet                │
│   - MovimientoInventarioViewSet         │
│   (filtrado por empresa SSoT)           │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│   Services (services.py)                │
│   - recalcular_stock_producto()         │
│   - registrar_entrada()                 │
│   - registrar_salida()                  │
│   - qs_producto_list() (optimizado)     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│   Models (models.py)                     │
│   - Producto                            │
│   - MovimientoInventario                │
│   - CategoriaItem                       │
│   Base de Datos (PostgreSQL)            │
└─────────────────────────────────────────┘
```

**Flujo Alternativo (Gateway Directo):**
- Si el frontend usa `/api/v1/inventario/` directamente (sin Core API), el flujo omite el paso de Core API Facade y va directamente a App API ViewSets.

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

### 4.0. Core API Facade (v2.61.3)

**Ubicación:** `apps/tenant/core/api/v1/inventario/`

**Propósito:** Facade que expone los ViewSets de inventario a través de Core API unificada.

**Endpoints Base:**
- `/api/v1/core/v1/inventario/categorias/` → `CategoriaItemCoreViewSet`
- `/api/v1/core/v1/inventario/productos/` → `ProductoCoreViewSet`
- `/api/v1/core/v1/inventario/servicios/` → `ServicioCoreViewSet` ✅ v2.61.3
- `/api/v1/core/v1/inventario/activos/` → `ActivoFijoCoreViewSet` ✅ v2.61.3
- `/api/v1/core/v1/inventario/movimientos/` → `MovimientoInventarioCoreViewSet`

**Características:**
- ✅ **Herencia Completa**: Todas las acciones `@action` se heredan automáticamente
- ✅ **SessionAuthentication**: Autenticación por sesión (workspace)
- ✅ **Serializers Especializados**: `WorkspaceListSerializer` y `WorkspaceDetailSerializer`
- ✅ **Gateway Directo**: También disponible en `/api/v1/inventario/` (acceso directo a app)

**ViewSets Facade:**

```python
# apps/tenant/core/api/v1/inventario/viewsets.py

class CategoriaItemCoreViewSet(CategoriaItemViewSet):
    """Facade ViewSet para Categorías en Core API."""
    authentication_classes = [SessionAuthentication]
    def get_serializer_class(self):
        if self.action == "list":
            return ws_serializers.CategoriaItemWorkspaceListSerializer
        return ws_serializers.CategoriaItemWorkspaceDetailSerializer

class ProductoCoreViewSet(ProductoViewSet):
    """
    Facade ViewSet para Productos en Core API.
    
    Hereda todas las acciones @action de ProductoViewSet:
    - gestor-offcanvas: GET (TemplateHTMLRenderer)
    - stock: GET (stock actual optimizado)
    - kardex: GET (historial de movimientos)
    """
    authentication_classes = [SessionAuthentication]
    def get_serializer_class(self):
        if self.action == "list":
            return ws_serializers.ProductoWorkspaceListSerializer
        return ws_serializers.ProductoWorkspaceDetailSerializer

class ServicioCoreViewSet(ServicioViewSet):  # ✅ v2.61.3
    """Facade ViewSet para Servicios en Core API."""
    authentication_classes = [SessionAuthentication]
    def get_serializer_class(self):
        if self.action == "list":
            return ws_serializers.ServicioWorkspaceListSerializer
        return ws_serializers.ServicioWorkspaceDetailSerializer

class ActivoFijoCoreViewSet(ActivoFijoViewSet):  # ✅ v2.61.3
    """Facade ViewSet para Activos Fijos en Core API."""
    authentication_classes = [SessionAuthentication]
    def get_serializer_class(self):
        if self.action == "list":
            return ws_serializers.ActivoFijoWorkspaceListSerializer
        return ws_serializers.ActivoFijoWorkspaceDetailSerializer

class MovimientoInventarioCoreViewSet(MovimientoInventarioViewSet):
    """Facade ViewSet para Movimientos en Core API."""
    authentication_classes = [SessionAuthentication]
    def get_serializer_class(self):
        if self.action == "list":
            return ws_serializers.MovimientoInventarioWorkspaceListSerializer
        return ws_serializers.MovimientoInventarioWorkspaceDetailSerializer
```

**Registro en Router:**

```python
# apps/tenant/core/api/urls.py
router_v1.register(r"inventario/categorias", CategoriaItemCoreViewSet, basename="core-inventario-categorias")
router_v1.register(r"inventario/productos", ProductoCoreViewSet, basename="core-inventario-productos")
router_v1.register(r"inventario/servicios", ServicioCoreViewSet, basename="core-inventario-servicios")  # ✅ v2.61.3
router_v1.register(r"inventario/activos", ActivoFijoCoreViewSet, basename="core-inventario-activos")  # ✅ v2.61.3
router_v1.register(r"inventario/movimientos", MovimientoInventarioCoreViewSet, basename="core-inventario-movimientos")
```

**Serializers Workspace:**

```python
# apps/tenant/core/api/v1/inventario/serializers.py

# Todos los serializers incluyen _ImagenUrlMixin para URLs absolutas de imágenes
class CategoriaItemWorkspaceListSerializer(_ImagenUrlMixin, CategoriaItemListSerializer): ...
class CategoriaItemWorkspaceDetailSerializer(_ImagenUrlMixin, CategoriaItemDetailSerializer): ...
class ProductoWorkspaceListSerializer(_ImagenUrlMixin, ProductoListSerializer): ...
class ProductoWorkspaceDetailSerializer(_ImagenUrlMixin, ProductoDetailSerializer): ...
class ServicioWorkspaceListSerializer(_ImagenUrlMixin, ServicioListSerializer): ...  # ✅ v2.61.3
class ServicioWorkspaceDetailSerializer(_ImagenUrlMixin, ServicioDetailSerializer): ...  # ✅ v2.61.3
class ActivoFijoWorkspaceListSerializer(_ImagenUrlMixin, ActivoFijoListSerializer): ...  # ✅ v2.61.3
class ActivoFijoWorkspaceDetailSerializer(_ImagenUrlMixin, ActivoFijoDetailSerializer): ...  # ✅ v2.61.3
class MovimientoInventarioWorkspaceListSerializer(MovimientoInventarioListSerializer): ...
class MovimientoInventarioWorkspaceDetailSerializer(MovimientoInventarioDetailSerializer): ...
```

**CoreLinksViewSet:**

```python
# apps/tenant/core/api/viewsets.py
links = {
    "inventario-categorias": {
        "api": "/api/v1/core/v1/inventario/categorias/",
        "ui": "/workspace/#inventario",
    },
    "inventario-productos": {
        "api": "/api/v1/core/v1/inventario/productos/",
        "ui": "/workspace/#inventario",
    },
    "inventario-servicios": {  # ✅ v2.61.3
        "api": "/api/v1/core/v1/inventario/servicios/",
        "ui": "/workspace/#inventario",
    },
    "inventario-activos": {  # ✅ v2.61.3
        "api": "/api/v1/core/v1/inventario/activos/",
        "ui": "/workspace/#inventario",
    },
    "inventario-movimientos": {  # ✅ v2.61.3
        "api": "/api/v1/core/v1/inventario/movimientos/",
        "ui": "/workspace/#inventario",
    },
}
```

### 4.1. ViewSets (App API)

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

### 6.0. Feature-Sliced Architecture (v2.61.3)

**Ubicación:** `apps/tenant/core/static/core/js/inventario/features/`

**Propósito:** Modularización completa del frontend siguiendo el patrón Feature-Sliced Architecture.

**Estructura:**
```
features/
├── categorias_list.js      # Feature: READ categorías (Tabulator)
├── categorias_editor.js    # Feature: CREATE/UPDATE categorías (Offcanvas)
├── productos_list.js       # Feature: READ productos (Tabulator + Kardex)
├── productos_editor.js     # Feature: CREATE/UPDATE productos + Ajustes
├── servicios_list.js       # Feature: READ servicios (Tabulator)
├── servicios_editor.js     # Feature: CREATE/UPDATE servicios (Offcanvas)
├── activos_list.js         # Feature: READ activos (Tabulator)
├── activos_editor.js       # Feature: CREATE/UPDATE activos (Offcanvas)
├── movimientos_list.js     # Feature: READ movimientos (Tabulator)
├── movimientos_editor.js   # Feature: CREATE movimientos (Modal)
├── inventario_list.js      # Legacy: Listado principal
└── inventario_editor.js     # Legacy: Editor principal
```

**Características:**
- ✅ **Separación de Responsabilidades**: Cada feature tiene su módulo `_list.js` (READ) y `_editor.js` (CREATE/UPDATE)
- ✅ **Core API Facade**: Todos los módulos usan `/api/v1/core/v1/inventario/` para CRUD
- ✅ **Event Delegation**: Manejo de eventos centralizado en contenedores
- ✅ **Anti-Zombies**: Singleton global para prevenir instancias fantasma de Tabulator
- ✅ **Lazy Loading**: Inicialización solo cuando el tab está visible
- ✅ **Exposición Global**: Cada módulo expone `window.{Modulo}List` y `window.{Modulo}Editor`

**Patrón de Uso:**
```javascript
// Inicialización automática
window.CategoriasList.init();      // Inicializa tabla Tabulator
window.CategoriasEditor.init();    // Inicializa eventos del formulario

// Funciones expuestas
window.CategoriasList.recargar();           // Refrescar tabla
window.CategoriasList.getTable();           // Obtener instancia Tabulator
window.CategoriasEditor.guardar();          // Guardar categoría
window.CategoriasEditor.abrirModalCrear();  // Abrir offcanvas
```

**Endpoints Core API:**
- Todos los módulos `*_list.js` usan `API_URL = '/api/v1/core/v1/inventario/{modulo}/'`
- Todos los módulos `*_editor.js` usan `CORE_API_BASE = '/api/v1/core/v1/inventario/{modulo}'`
- `gestor-offcanvas` usa `CORE_API_BASE + '/gestor-offcanvas/'`
- Carga de catálogos (categorías, productos) usa Core API Facade

**Migración desde `.page.js`:**
- ✅ `categorias.page.js` → `categorias_list.js` + `categorias_editor.js`
- ✅ `productos.page.js` → `productos_list.js` + `productos_editor.js`
- ✅ `servicios.page.js` → `servicios_list.js` + `servicios_editor.js`
- ✅ `activos.page.js` → `activos_list.js` + `activos_editor.js`
- ✅ `movimientos.page.js` → `movimientos_list.js` + `movimientos_editor.js`

**Archivos Legacy:**
- ⚠️ `inventario_list.js` y `inventario_editor.js` se mantienen por compatibilidad
- ⚠️ Todos los archivos `.page.js` están marcados como DEPRECATED pero no eliminados

## 6. Frontend (Continuación)

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

### 7.1. Flujo Completo: Workspace → Core API → Models

#### 7.1.1. Flujo: Crear Producto (Paso a Paso)

```
1. Usuario: Navega a workspace.html → #inventario
   → workspace.js detecta hash #inventario
   → Muestra sección #tab-inventario
   → Carga list.html (partials/inventario/list.html)
   ↓
2. Frontend: assets_inventario.html carga scripts
   → inventario.api.js (wrapper API)
   → inventario_list.js (listado principal)
   → inventario_editor.js (editor Offcanvas)
   → productos.page.js (módulo Productos)
   ↓
3. Usuario: Hace clic en "Nuevo Producto" (botón en toolbar)
   → inventario_list.js detecta evento (data-action="nuevo-producto")
   → inventario_editor.js.abrirFormulario() o similar
   ↓
4. HTMX: Carga formulario Offcanvas
   GET /api/v1/core/v1/inventario/productos/gestor-offcanvas/
   (o GET /api/v1/inventario/productos/gestor-offcanvas/ si usa gateway directo)
   ↓
5. Core API Facade: ProductoCoreViewSet.gestor_offcanvas()
   → Hereda de ProductoViewSet.gestor_offcanvas()
   → Renderiza template offcanvas_form.html (TemplateHTMLRenderer)
   → Incluye catálogo de categorías (CategoriaItem.objects.filter(empresa=...))
   ↓
6. Frontend: HTMX inserta HTML en #offcanvas-container-inventario
   → inventario_editor.js detecta htmx:afterSwap
   → Inicializa validación de formulario
   ↓
7. Usuario: Completa formulario y hace clic en "Guardar"
   → inventario_editor.js recolecta datos del formulario
   → Valida campos requeridos (codigo, nombre, precio_venta, etc.)
   ↓
8. Frontend: inventario.api.js envía POST
   POST /api/v1/core/v1/inventario/productos/
   (o POST /api/v1/inventario/productos/ si usa gateway directo)
   Payload: {codigo, nombre, categoria_id, precio_venta, costo_promedio, ...}
   ↓
9. Core API Facade: ProductoCoreViewSet.create()
   → Hereda de ProductoViewSet.create()
   → Valida permisos (Enforced Mode: solo ADMIN/STAFF)
   ↓
10. App API: ProductoViewSet.perform_create()
    → Asigna empresa automáticamente (SSoT)
    → empresa = Empresa.objects.only('id').first()
    → producto.empresa = empresa
    ↓
11. Models: Producto.save()
    → Valida unique_together (codigo, empresa)
    → Persiste en BD
    ↓
12. Response: 201 Created
    Payload: {id, codigo, nombre, categoria_nombre, precio_venta, stock_actual, ...}
    (serializado con ProductoWorkspaceDetailSerializer)
    ↓
13. Frontend: inventario_editor.js maneja respuesta
    → Si res.ok: cierra Offcanvas, muestra notificación de éxito
    → Dispara evento 'productoGuardado' o recarga tabla directamente
    ↓
14. Frontend: inventario_list.js / productos.page.js
    → Escucha evento 'productoGuardado' o detecta cambio de tab
    → Tabulator.refresh() o Tabulator.replaceData()
    → GET /api/v1/core/v1/inventario/productos/?page=1&page_size=10
    ↓
15. Core API Facade: ProductoCoreViewSet.list()
    → Hereda de ProductoViewSet.list()
    → Filtra por empresa automáticamente
    → Usa qs_producto_list() optimizado (only(), select_related())
    → Serializa con ProductoWorkspaceListSerializer
    ↓
16. Response: 200 OK
    {count, next, previous, results: [...]}
    ↓
17. Frontend: Tabulator actualiza tabla con nuevos datos
```

### 7.2. Flujo: Registrar Entrada de Stock (Paso a Paso)

```
1. Usuario: En workspace.html → #inventario → Tab "Productos"
   → Hace clic en "Entrada/Salida" (botón en toolbar o acción de fila)
   ↓
2. Frontend: inventario_editor.js o inventario_list.js
   → Detecta acción "entrada-salida" o "ajuste-stock"
   → Abre Offcanvas con tipo=ajuste
   ↓
3. HTMX: Carga formulario Offcanvas
   GET /api/v1/core/v1/inventario/productos/gestor-offcanvas/?tipo=ajuste
   ↓
4. Core API Facade: ProductoCoreViewSet.gestor_offcanvas()
   → Renderiza template offcanvas_form.html
   → Incluye lista de productos (para select)
   → Incluye tipos de movimiento (ENTRADA_COMPRA, SALIDA_VENTA, etc.)
   ↓
5. Frontend: HTMX inserta HTML en #offcanvas-container-inventario
   → inventario_editor.js inicializa formulario de ajuste
   ↓
6. Usuario: Selecciona producto, tipo de movimiento, cantidad, costo_unitario, etc.
   → Valida que cantidad > 0
   → Si es SALIDA: valida stock suficiente (frontend muestra alerta si no hay)
   ↓
7. Frontend: inventario.api.js envía POST
   POST /api/v1/core/v1/inventario/movimientos/
   Payload: {producto_id, tipo, cantidad, costo_unitario, origen_referencia, ...}
   ↓
8. Core API Facade: MovimientoInventarioCoreViewSet.create()
   → Hereda de MovimientoInventarioViewSet.create()
   → Valida permisos (Enforced Mode)
   ↓
9. App API: MovimientoInventarioViewSet.perform_create()
   → Valida que producto pertenezca al tenant (Zero Trust)
   → Valida stock suficiente si es SALIDA (services.validar_stock_suficiente())
   → Crea MovimientoInventario
   → Llama a services.recalcular_stock_producto(producto_id) automáticamente
   ↓
10. Service Layer: services.recalcular_stock_producto(producto_id)
    → @transaction.atomic
    → Producto.objects.select_for_update().only('id', 'stock_actual').get(id=producto_id)
    → Calcula stock desde movimientos:
       Stock = SUM(ENTRADAS) - SUM(SALIDAS) + SUM(AJUSTES_POSITIVOS) - SUM(AJUSTES_NEGATIVOS)
    → producto.stock_actual = nuevo_stock
    → producto.save(update_fields=['stock_actual', 'updated_at'])
    ↓
11. Models: MovimientoInventario.save() → Producto.save()
    → Persiste movimiento en BD
    → Actualiza stock_actual del producto
    ↓
12. Response: 201 Created
    Payload: {id, created_at, producto_codigo, producto_nombre, tipo_display, cantidad, ...}
    ↓
13. Frontend: inventario_editor.js maneja respuesta
    → Si res.ok: cierra Offcanvas, muestra notificación de éxito
    → Dispara evento 'movimientoRegistrado' o recarga tablas
    ↓
14. Frontend: productos.page.js y movimientos.page.js
    → Refrescan tablas Tabulator
    → GET /api/v1/core/v1/inventario/productos/ (stock actualizado)
    → GET /api/v1/core/v1/inventario/movimientos/ (nuevo movimiento)
```

### 7.3. Flujo: Consultar Kardex de Producto (Paso a Paso)

```
1. Usuario: En workspace.html → #inventario → Tab "Productos"
   → Hace clic en botón "Ver Kardex" en fila de producto
   (o doble clic en fila si está configurado)
   ↓
2. Frontend: productos.page.js o inventario_list.js
   → Detecta click en botón con data-action="ver-kardex"
   → Obtiene producto_id desde data-id del botón o row.getData().id
   ↓
3. Frontend: inventario.api.js envía GET
   GET /api/v1/core/v1/inventario/productos/{id}/kardex/
   ↓
4. Core API Facade: ProductoCoreViewSet.kardex()
   → Hereda de ProductoViewSet.kardex()
   → Valida que producto pertenezca al tenant (Zero Trust)
   → producto = Producto.objects.filter(pk=id, empresa_id=empresa_id).first()
   ↓
5. App API: ProductoViewSet.kardex()
   → Obtiene movimientos optimizados:
     movimientos = MovimientoInventario.objects.filter(
         producto_id=producto_id,
         producto__empresa_id=empresa_id
     ).select_related('producto').only(
         'id', 'created_at', 'tipo', 'cantidad', 'costo_unitario',
         'origen_referencia', 'cliente_referencia', 'observaciones',
         'producto__codigo', 'producto__nombre'
     ).order_by('-created_at')
   ↓
6. Service Layer: (opcional) services.calcular_stock(producto_id)
   → Calcula stock actual desde movimientos (solo lectura, no actualiza BD)
   → Retorna: {stock_actual, entradas, salidas, ajustes}
   ↓
7. Response: 200 OK
   Payload: {
     producto: {id, codigo, nombre, stock_actual, ...},
     movimientos: [{id, created_at, tipo_display, cantidad, ...}, ...],
     resumen: {stock_actual, total_entradas, total_salidas, ...}
   }
   ↓
8. Frontend: inventario_list.js o productos.page.js
   → Muestra modal/offcanvas con historial de movimientos
   → Tabla Tabulator con movimientos ordenados por fecha (más reciente primero)
   → Muestra resumen: stock actual, total entradas, total salidas
```

### 7.4. Flujo: Eliminar Producto (Paso a Paso)

### 7.5. Mejoras de Robustez v2.61.4

#### 7.5.1. Prevención de Doble Envío

**Problema:** Múltiples clics en "Guardar" causaban `IntegrityError` por código duplicado.

**Solución Implementada:**
1. Flag `_guardandoProducto` activado **ANTES** de validar payload
2. Deshabilitación de botón y formulario (`pointerEvents: 'none'`)
3. Clonado de botón para eliminar listeners duplicados
4. Verificación adicional del flag dentro de listeners

**Ubicación:** `apps/tenant/core/static/core/js/inventario/features/productos_editor.js`

**Código:**
```javascript
// Activación temprana del flag
if (_guardandoProducto) {
    console.warn(`${MOD} Guardado ya en proceso, ignorando solicitud duplicada`);
    return;
}
_guardandoProducto = true;

// Deshabilitar botón y formulario
btnGuardar.disabled = true;
btnGuardar.style.pointerEvents = 'none';
form.style.pointerEvents = 'none';
```

#### 7.5.2. Manejo de Errores Mejorado

**Problema:** Tracebacks de Python se mostraban al usuario en errores de validación.

**Solución Implementada:**
1. Manejo de `IntegrityError` en `ProductoViewSet.create()` con mensajes amigables
2. Extracción automática de código duplicado del mensaje de error
3. Filtrado de tracebacks en `ui-manager.js`
4. Prioridad de mensajes: `error` + `message` > `error` > `detail`

**Ubicación Backend:** `apps/tenant/inventario/api/viewsets.py`  
**Ubicación Frontend:** `apps/tenant/core/static/core/js/lib/ui-manager.js`

**Ejemplo de Mensaje:**
```
Antes: "Traceback (most recent call last):\n  File ...\nIntegrityError: duplicate key..."
Ahora: "Ya existe un producto con el código '224932'. Por favor, use un código diferente."
```

#### 7.5.3. Recarga Automática de Tabla

**Problema:** La tabla no se actualizaba después de crear/actualizar un producto.

**Solución Implementada:**
1. Función `recargar()` expuesta en `inventario_list.js`
2. Módulo `ProductosList` expuesto para compatibilidad
3. Recarga automática después de crear/actualizar (delay 300ms)
4. Inicialización automática al hacer clic en menú "Productos"
5. Múltiples métodos de fallback

**Ubicación:** `apps/tenant/core/static/core/js/inventario/features/inventario_list.js`

**Código:**
```javascript
// Función recargar() expuesta
function recargar() {
    if (table && typeof table.replaceData === 'function') {
        table.replaceData();
    } else if (window.SintelInventarioTables.main) {
        window.SintelInventarioTables.main.replaceData();
    } else {
        init(); // Intentar inicializar si no está inicializada
    }
}

// Exposición para compatibilidad
w.ProductosList = {
    init: init,
    recargar: recargar,
    getTable: () => table || window.SintelInventarioTables.main
};
```

#### 7.5.4. Mapeo de Campos Corregido

**Problema:** Backend esperaba `producto` y `tipo`, pero frontend enviaba `producto_id` y `tipo_movimiento`.

**Solución Implementada:**
1. Mapeo en `recolectarDatosAjuste()`: `producto_id` → `producto`, `tipo_movimiento` → `tipo`
2. Validación actualizada para usar campos mapeados
3. Eliminación de campos incorrectos después del mapeo

**Ubicación:** `apps/tenant/core/static/core/js/inventario/features/inventario_editor.js`

**Código:**
```javascript
// Mapeo de campos para el backend
if (data.producto_id) {
    data.producto = parseInt(data.producto_id);
    delete data.producto_id;
}
if (data.tipo_movimiento) {
    data.tipo = data.tipo_movimiento;
    delete data.tipo_movimiento;
}
```

#### 7.5.5. Mejoras de UI

**Columna "Precio Venta" Agregada:**
- Nueva columna en listado de productos
- Formateo con `formatearMoneda()`
- Manejo de valores nulos

**Formatters Mejorados:**
- Validación de `null`/`undefined` en todos los formatters numéricos
- Retorno de valores por defecto (`'$ 0,00'`, `'0,00'`) para campos vacíos

**Fallback Mejorado:**
- Si `routes.js` falla, usar Core API Facade directamente
- Prevenir errores 404 al cargar productos

**Ubicación:** `apps/tenant/core/static/core/js/inventario/features/inventario_list.js`  
**Ubicación:** `apps/tenant/core/static/core/js/inventario/inventario.api.js`

```
1. Usuario: En workspace.html → #inventario → Tab "Productos"
   → Hace clic en botón "Eliminar" en fila de producto
   ↓
2. Frontend: productos.page.js o inventario_list.js
   → Detecta click en botón con data-action="eliminar-producto"
   → Obtiene producto_id desde data-id
   → Muestra confirmación (confirm() nativo o SintelFeedback.confirm)
   ↓
3. Si usuario confirma: inventario.api.js envía DELETE
   DELETE /api/v1/core/v1/inventario/productos/{id}/
   ↓
4. Core API Facade: ProductoCoreViewSet.destroy()
   → Hereda de ProductoViewSet.destroy()
   → Valida permisos (Enforced Mode: solo ADMIN/STAFF)
   ↓
5. App API: ProductoViewSet.destroy()
   → Valida que producto pertenezca al tenant (Zero Trust)
   → producto = Producto.objects.filter(pk=id, empresa_id=empresa_id).first()
   → Valida que producto.activo == False
   ↓
6. Si está activo:
   → Retorna 400 Bad Request
   → Payload: {error: "No se puede eliminar un producto activo. Debe desactivarlo primero."}
   ↓
7. Si está inactivo:
   → Django elimina Producto
   → CASCADE elimina todos los MovimientoInventario relacionados
   → CASCADE elimina relaciones con CategoriaItem (categoria queda None)
   ↓
8. Response: 204 No Content (o 200 OK con mensaje)
   ↓
9. Frontend: productos.page.js maneja respuesta
   → Si res.ok: muestra notificación de éxito
   → Tabulator.refresh() o Tabulator.deleteRow(id)
   → GET /api/v1/core/v1/inventario/productos/?page=1&page_size=10
   ↓
10. Core API Facade: ProductoCoreViewSet.list()
    → Retorna lista actualizada sin el producto eliminado
    ↓
11. Frontend: Tabulator actualiza tabla
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

## 11. Flujo Completo: Workspace → Core API → Models

### 11.1. Arquitectura de Navegación

```
workspace.html
    ↓ (hash navigation: #inventario)
workspace.js
    ↓ (muestra sección #tab-inventario)
list.html (partials/inventario/list.html)
    ↓ (carga assets_inventario.html)
Scripts JS (Feature-Sliced Architecture v2.61.3):
    - inventario.api.js (wrapper API)
    - features/categorias_list.js + categorias_editor.js
    - features/productos_list.js + productos_editor.js
    - features/servicios_list.js + servicios_editor.js
    - features/activos_list.js + activos_editor.js
    - features/movimientos_list.js + movimientos_editor.js
    - features/inventario_list.js + inventario_editor.js (legacy)
    - categorias.page.js, productos.page.js, etc. (⚠️ DEPRECATED v2.61.3)
    ↓
Tabulator Factory (tablas interactivas)
    ↓ (HTTP requests)
Core API Facade (/api/v1/core/v1/inventario/)
    ↓ (hereda acciones)
App API (/api/v1/inventario/)
    ↓ (lógica de negocio)
Services (services.py)
    ↓ (persistencia)
Models (models.py)
    ↓
PostgreSQL Database
```

### 11.2. Integración con Workspace

**Archivo:** `apps/tenant/core/templates/tenant/core/workspace.html`

```html
{# Módulo Inventario #}
<section id="tab-inventario" class="workspace-tab" style="display: none;">
  {% include 'tenant/core/partials/inventario/list.html' %}
  {# ⚠️ v2.60: modals.html eliminado - Todo funciona con HTMX + Offcanvas #}
</section>
```

**Navegación:**
- Usuario hace clic en sidebar: `<a href="#inventario" data-tab="inventario">`
- `workspace.js` detecta hash `#inventario`
- Muestra sección `#tab-inventario`
- Carga `list.html` que incluye tabs internos (Productos, Servicios, Activos, Movimientos, Categorías)

**Assets:**
- Cargados en `workspace.html` línea 347: `{% include 'tenant/core/partials/inventario/assets_inventario.html' %}`

### 11.3. Endpoints Disponibles

#### Core API Facade (Recomendado para Workspace) ✅ v2.61.3

**Categorías:**
- `GET /api/v1/core/v1/inventario/categorias/` - Lista categorías
- `GET /api/v1/core/v1/inventario/categorias/{id}/` - Detalle categoría
- `POST /api/v1/core/v1/inventario/categorias/` - Crear categoría
- `PATCH /api/v1/core/v1/inventario/categorias/{id}/` - Actualizar categoría
- `DELETE /api/v1/core/v1/inventario/categorias/{id}/` - Eliminar categoría
- `GET /api/v1/core/v1/inventario/categorias/gestor-offcanvas/` - HTML formulario (HTMX)

**Productos:**
- `GET /api/v1/core/v1/inventario/productos/` - Lista productos
- `GET /api/v1/core/v1/inventario/productos/{id}/` - Detalle producto
- `POST /api/v1/core/v1/inventario/productos/` - Crear producto
- `PATCH /api/v1/core/v1/inventario/productos/{id}/` - Actualizar producto
- `DELETE /api/v1/core/v1/inventario/productos/{id}/` - Eliminar producto
- `GET /api/v1/core/v1/inventario/productos/{id}/stock/` - Stock actual
- `GET /api/v1/core/v1/inventario/productos/{id}/kardex/` - Historial Kardex
- `GET /api/v1/core/v1/inventario/productos/gestor-offcanvas/` - HTML formulario (HTMX)

**Servicios:** ✅ v2.61.3
- `GET /api/v1/core/v1/inventario/servicios/` - Lista servicios
- `GET /api/v1/core/v1/inventario/servicios/{id}/` - Detalle servicio
- `POST /api/v1/core/v1/inventario/servicios/` - Crear servicio
- `PATCH /api/v1/core/v1/inventario/servicios/{id}/` - Actualizar servicio
- `DELETE /api/v1/core/v1/inventario/servicios/{id}/` - Eliminar servicio
- `GET /api/v1/core/v1/inventario/servicios/gestor-offcanvas/` - HTML formulario (HTMX)

**Activos Fijos:** ✅ v2.61.3
- `GET /api/v1/core/v1/inventario/activos/` - Lista activos
- `GET /api/v1/core/v1/inventario/activos/{id}/` - Detalle activo
- `POST /api/v1/core/v1/inventario/activos/` - Crear activo
- `PATCH /api/v1/core/v1/inventario/activos/{id}/` - Actualizar activo
- `DELETE /api/v1/core/v1/inventario/activos/{id}/` - Eliminar activo
- `GET /api/v1/core/v1/inventario/activos/gestor-offcanvas/` - HTML formulario (HTMX)

**Movimientos:** ✅ v2.61.3
- `GET /api/v1/core/v1/inventario/movimientos/` - Lista movimientos
- `GET /api/v1/core/v1/inventario/movimientos/{id}/` - Detalle movimiento
- `POST /api/v1/core/v1/inventario/movimientos/` - Crear movimiento

#### Gateway Directo (Acceso Directo a App)

- `GET /api/v1/inventario/productos/` - Lista productos
- `GET /api/v1/inventario/productos/{id}/` - Detalle producto
- `POST /api/v1/inventario/productos/` - Crear producto
- `PATCH /api/v1/inventario/productos/{id}/` - Actualizar producto
- `DELETE /api/v1/inventario/productos/{id}/` - Eliminar producto

**Nota:** Ambos endpoints funcionan igual, pero Core API Facade está optimizado para workspace con serializers especializados.

---

## 12. Conclusión

El módulo **Inventario v2.61.4** es un sistema completo y robusto para la gestión de inventario con:

✅ **Arquitectura sólida**: API-First, Service Layer, Multi-tenancy, Core API Facade  
✅ **Feature-Sliced Architecture**: Frontend completamente modularizado (10 módulos features)  
✅ **Core API Facade Completo**: 5 ViewSets facade con serializers especializados  
✅ **Performance optimizado**: QuerySets optimizados, campos estrictamente necesarios  
✅ **Integridad de datos**: Kardex inmutable, stock desnormalizado mantenido automáticamente  
✅ **Zero Trust**: Validación estricta de pertenencia al tenant  
✅ **Frontend moderno**: Tabulator Factory, HTMX, Bootstrap Offcanvas  
✅ **Endpoints unificados**: Todos los módulos usan Core API Facade (`/api/v1/core/v1/inventario/`)  
✅ **Robustez mejorada**: Prevención de doble envío, manejo de errores amigable, recarga automática  
✅ **UX optimizada**: Mensajes de error claros, valores numéricos formateados, inicialización automática  
✅ **Extensibilidad**: Preparado para integraciones con Ventas, Compras, etc.

**Logros v2.61.3**:
1. ✅ Migración completa a Feature-Sliced Architecture (10 módulos features)
2. ✅ Core API Facade completo (5 ViewSets: Categorías, Productos, Servicios, Activos, Movimientos)
3. ✅ Serializers Workspace con URLs absolutas de imágenes (`_ImagenUrlMixin`)
4. ✅ Alineación completa de endpoints JavaScript con Core API Facade
5. ✅ Links centralizados en `CoreLinksViewSet` para todos los módulos

**Logros v2.61.4**:
1. ✅ Prevención de doble envío implementada (flag `_guardandoProducto`)
2. ✅ Manejo de errores mejorado (IntegrityError con mensajes amigables)
3. ✅ Filtrado de tracebacks de Python en UI
4. ✅ Recarga automática de tabla después de crear/actualizar producto
5. ✅ Inicialización automática de tabla al hacer clic en menú "Productos"
6. ✅ Mapeo correcto de campos (producto_id → producto, tipo_movimiento → tipo)
7. ✅ Columna "Precio Venta" agregada al listado
8. ✅ Formatters mejorados para manejar valores nulos
9. ✅ Fallback robusto en `inventario.api.js` para Core API Facade

**Próximos pasos recomendados**:
1. Integración con módulo de Ventas (registrar salidas automáticamente)
2. Integración con módulo de Compras (registrar entradas automáticamente)
3. Dashboard de inventario (alertas de stock bajo, valor de inventario, etc.)
4. Reportes de inventario (Kardex por rango de fechas, movimientos por tipo, etc.)
5. Eliminación de archivos `.page.js` deprecados (v2.62)

---

## 13. Notas de Versión

### v2.61.4 (2026-03-12) - Correcciones de Robustez y UX

**Prevención de Doble Envío:**
- ✅ Flag `_guardandoProducto` implementado en `productos_editor.js`
- ✅ Activación temprana del flag antes de validar payload
- ✅ Deshabilitación de botón y formulario durante guardado (`pointerEvents: 'none'`)
- ✅ Clonado de botón para eliminar listeners duplicados
- ✅ Verificación adicional del flag dentro de listeners

**Manejo de Errores Mejorado:**
- ✅ Manejo de `IntegrityError` en `ProductoViewSet.create()` con mensajes amigables
- ✅ Extracción automática de código duplicado del mensaje de error
- ✅ Filtrado de tracebacks de Python en `ui-manager.js`
- ✅ Detección y formateo mejorado de errores de código duplicado
- ✅ Prioridad de mensajes: `error` + `message` > `error` > `detail`

**Recarga e Inicialización de Tabla:**
- ✅ Función `recargar()` expuesta en `inventario_list.js`
- ✅ Módulo `ProductosList` expuesto para compatibilidad con `productos_editor.js`
- ✅ Inicialización automática de tabla al hacer clic en menú "Productos"
- ✅ Recarga inmediata después de crear/actualizar producto (delay 300ms)
- ✅ Múltiples métodos de fallback para asegurar recarga
- ✅ Listener `shown.bs.tab` mejorado para detectar tab de productos

**Mapeo de Campos Corregido:**
- ✅ `producto_id` → `producto` (FK) en `inventario_editor.js`
- ✅ `tipo_movimiento` → `tipo` (string) en `inventario_editor.js`
- ✅ Validación actualizada para usar campos mapeados
- ✅ Eliminación de campos incorrectos después del mapeo

**Mejoras de UI:**
- ✅ Columna "Precio Venta" agregada al listado de productos
- ✅ Formatters mejorados para manejar valores `null`/`undefined`
- ✅ Retorno de valores por defecto (`'$ 0,00'`, `'0,00'`) para campos vacíos
- ✅ Fallback mejorado en `inventario.api.js` para usar Core API Facade directamente

**Bug Fixes:**
- ✅ Error 400 "PRODUCTO: Este campo es requerido" corregido (mapeo de campos)
- ✅ Error 400 "TIPO: Este campo es requerido" corregido (mapeo de campos)
- ✅ Error 500 con traceback completo corregido (filtrado de tracebacks)
- ✅ Error de código duplicado ahora muestra mensaje amigable
- ✅ Error 404 al cargar rutas corregido (fallback a Core API Facade)

### v2.61.3 (2026-03-12) - Migración Completa a Feature-Sliced Architecture

**Core API Facade - Completado:**
- ✅ `ServicioCoreViewSet` agregado a Core API
- ✅ `ActivoFijoCoreViewSet` agregado a Core API
- ✅ Serializers Workspace para Servicios y Activos (con `_ImagenUrlMixin`)
- ✅ URLs registradas en `router_v1` para todos los módulos
- ✅ Links agregados en `CoreLinksViewSet` para todos los módulos

**Feature-Sliced Architecture - Completado:**
- ✅ Migración completa de Categorías a `categorias_list.js` + `categorias_editor.js`
- ✅ Migración completa de Productos a `productos_list.js` + `productos_editor.js`
- ✅ Migración completa de Servicios a `servicios_list.js` + `servicios_editor.js`
- ✅ Migración completa de Activos a `activos_list.js` + `activos_editor.js`
- ✅ Migración completa de Movimientos a `movimientos_list.js` + `movimientos_editor.js`
- ✅ Archivos `.page.js` marcados como DEPRECATED (mantenidos por compatibilidad)

**Endpoints JavaScript - Alineados:**
- ✅ Todos los archivos `*_list.js` usan Core API Facade para Tabulator (`API_URL`)
- ✅ Todos los archivos `*_editor.js` usan Core API Facade para CRUD (`CORE_API_BASE`)
- ✅ Todos los endpoints de `gestor-offcanvas` usan Core API Facade
- ✅ Carga de catálogos (categorías, productos) usa Core API Facade
- ✅ Archivos legacy (`inventario_list.js`, `inventario_editor.js`) actualizados

**Documentación:**
- ✅ Documentación actualizada con flujos completos desde `workspace.html`
- ✅ Sección de Core API Facade expandida con todos los ViewSets
- ✅ Flujos principales detallados paso a paso (17 pasos para crear producto)
- ✅ Integración con workspace documentada
- ✅ Estructura de archivos actualizada con Feature-Sliced Architecture

### v2.60
- ✅ Migración a HTMX + Offcanvas
- ✅ Eliminación de modals.html (todo funciona con HTMX)
- ✅ API-First Architecture consolidada
- ✅ Tabulator Factory implementado

---

**Fin del Documento**  
**Última actualización**: 2026-03-12  
**Versión del Sistema**: 2.61.4  
**Estado**: ✅ Sincronizado con flujos completos desde workspace.html hasta models.py  
**Estado Core API**: ✅ Completo (5 ViewSets facade, 10 serializers workspace)  
**Estado Frontend**: ✅ Feature-Sliced Architecture completo (10 módulos features)  
**Estado Endpoints**: ✅ Todos alineados con Core API Facade  
**Estado Robustez**: ✅ Prevención de doble envío, manejo de errores mejorado, recarga automática  
**Estado UX**: ✅ Mensajes de error amigables, valores numéricos formateados correctamente
