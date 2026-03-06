# 📋 Informe de Estructura Funcional - App Cotizaciones v2.40

**Versión:** 2.40  
**Fecha:** 2026-02-17  
**Arquitectura:** SINTEL v2.40 (API-First, Service Layer, Multi-tenant)

---

## 📑 Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura General](#arquitectura-general)
3. [Modelos de Datos](#modelos-de-datos)
4. [Capa de Servicios](#capa-de-servicios)
5. [Capa API (DRF)](#capa-api-drf)
6. [Capa Frontend](#capa-frontend)
7. [Flujos Principales](#flujos-principales)
8. [Integraciones](#integraciones)
9. [Endpoints API](#endpoints-api)
10. [Diagramas de Flujo](#diagramas-de-flujo)
11. [Configuración y Numeración](#11-configuración-y-numeración)
12. [AIU (Administración, Imprevistos, Utilidad)](#12-aiu-administración-imprevistos-utilidad)

---

## 🎯 Resumen Ejecutivo

La aplicación **Cotizaciones** es un módulo completo para la gestión de cotizaciones comerciales en un sistema multi-tenant. Implementa:

- ✅ **Gestión de Cotizaciones**: Creación, edición, visualización y eliminación de cotizaciones
- ✅ **Catálogo de Productos (STS)**: Gestión de productos con importación masiva desde Excel/PDF
- ✅ **Editor Estilo Excel**: Creación rápida de cotizaciones con pegado desde Excel
- ✅ **Inmutabilidad**: Protección de cotizaciones aceptadas contra modificaciones
- ✅ **Utilidad Dinámica**: Cálculo automático de precios con porcentaje de utilidad configurable
- ✅ **Document Ingest Pipeline**: Integración con sistema universal de procesamiento de documentos
- ✅ **Numeración Automática e Inmutable**: Generación automática de números en formato COT-XXXX-YYYY
- ✅ **Configuración Global de Parámetros**: Centralización de valores por defecto para todas las cotizaciones
- ✅ **Soporte para Numeración Manual**: Opción configurable para ingresar números personalizados
- ✅ **AIU (Administración, Imprevistos, Utilidad)**: Característica habilitable por cotización con cálculo especial de IVA (solo sobre Utilidad)

> **📚 Documentación Adicional:**
> - Para detalles sobre **Configuración y Numeración Automática**, ver: [COTIZACIONES_CONFIGURACION_Y_NUMERACION.md](./COTIZACIONES_CONFIGURACION_Y_NUMERACION.md)
> - Para detalles sobre **Implementación de AIU**, ver: [COTIZACIONES_AIU_IMPLEMENTACION.md](./COTIZACIONES_AIU_IMPLEMENTACION.md)

### Tecnologías Principales

- **Backend**: Django 4.x + Django Rest Framework
- **Frontend**: Vanilla JavaScript + Tabulator.js
- **Base de Datos**: PostgreSQL (Multi-tenant)
- **Arquitectura**: API-First, Service Layer Pattern

---

## 🏗️ Arquitectura General

### Estructura de Directorios

```
apps/tenant/cotizaciones/
├── models.py              # Modelos de datos (Cotizacion, CotizacionItem, Producto, Servicio)
├── services.py            # Lógica de negocio (Service Layer)
├── admin.py               # Configuración Django Admin
├── api/
│   ├── viewsets.py        # ViewSets DRF (API endpoints)
│   ├── serializers.py     # Serializers DRF (validación y transformación)
│   └── urls.py            # Routing de API
└── migrations/            # Migraciones de base de datos

apps/tenant/core/
├── static/core/js/cotizaciones/
│   ├── cotizaciones.page.js      # Módulo principal de cotizaciones
│   ├── cotizacion_editor.js      # Editor estilo Excel
│   ├── productos.page.js         # Módulo de catálogo de productos
│   └── cotizaciones.api.js       # Wrapper de API
└── templates/tenant/core/partials/cotizaciones/
    ├── list.html                 # Vista de lista de cotizaciones
    ├── list_productos.html       # Vista de catálogo de productos
    ├── modal_editor.html         # Modal del editor estilo Excel
    ├── modals_productos.html    # Modales del catálogo
    └── assets_cotizaciones.html  # Assets (scripts y estilos)
```

### Principios Arquitectónicos

1. **Service Layer Pattern**: Toda la lógica de negocio está en `services.py`
2. **SSoT (Single Source of Truth)**: Empresa como singleton del tenant
3. **API-First**: Frontend consume exclusivamente APIs REST
4. **Inmutabilidad**: Cotizaciones aceptadas no pueden modificarse
5. **Optimización de Queries**: QuerySets optimizados con `select_related()` y `only()`

---

## 📊 Modelos de Datos

### 1. Producto (Catálogo STS)

**Ubicación**: `apps/tenant/cotizaciones/models.py`

```python
class Producto(models.Model):
    empresa = ForeignKey(Empresa)  # SSoT
    codigo = CharField(max_length=64, db_index=True)  # Único por empresa
    nombre = CharField(max_length=200)
    descripcion = TextField(blank=True, null=True)
    marca = CharField(max_length=100, blank=True, null=True)
    referencia = CharField(max_length=100, blank=True, null=True)
    unidad = CharField(max_length=16, default="UND")
    precio_venta = DecimalField(max_digits=14, decimal_places=2)
    activo = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
```

**Características**:
- Único por empresa + código (`unique_together`)
- Precio de venta actúa como costo base para cotizaciones
- Integrado con Document Ingest Pipeline para importación masiva

### 2. Servicio

**Ubicación**: `apps/tenant/cotizaciones/models.py`

```python
class Servicio(models.Model):
    empresa = ForeignKey(Empresa)  # SSoT
    codigo = CharField(max_length=64)
    nombre = CharField(max_length=200)
    descripcion = TextField(blank=True, null=True)
    precio_venta = DecimalField(max_digits=14, decimal_places=2)
    created_at = DateTimeField(auto_now_add=True)
```

**Características**:
- Catálogo de servicios (mano de obra, instalaciones)
- Similar a Producto pero sin marca/referencia

### 3. Cotizacion

**Ubicación**: `apps/tenant/cotizaciones/models.py`

```python
class Cotizacion(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR"
        ENVIADA = "ENVIADA"
        ACEPTADA = "ACEPTADA"
        RECHAZADA = "RECHAZADA"
    
    empresa = ForeignKey(Empresa)  # SSoT
    cliente = ForeignKey(Cliente)
    numero = CharField(max_length=50, db_index=True)  # Formato: COT-YYYY-NNNN
    atencion_a = CharField(max_length=255, blank=True, null=True)
    asunto = CharField(max_length=255, blank=True, null=True)
    fecha_emision = DateField()
    fecha_vencimiento = DateField()
    estado = CharField(max_length=20, choices=Estado.choices, default=Estado.BORRADOR)
    
    # Resumen Económico
    subtotal = DecimalField(max_digits=15, decimal_places=2, default=0.00)
    iva_porcentaje = DecimalField(max_digits=5, decimal_places=2, default=19.00)
    iva_valor = DecimalField(max_digits=15, decimal_places=2, default=0.00)
    total_neto = DecimalField(max_digits=15, decimal_places=2, default=0.00)
    
    created_at = DateTimeField(auto_now_add=True)
    
    @property
    def es_inmutable(self) -> bool:
        """Indica si la cotización está en estado ACEPTADA (inmutable)"""
        return self.estado == self.Estado.ACEPTADA
    
    def actualizar_totales(self):
        """Recalcula totales basándose en los ítems"""
        items = self.items.all()
        self.subtotal = sum(item.subtotal_linea for item in items)
        self.iva_valor = self.subtotal * (self.iva_porcentaje / Decimal('100.00'))
        self.total_neto = self.subtotal + self.iva_valor
        Cotizacion.objects.filter(pk=self.pk).update(
            subtotal=self.subtotal,
            iva_valor=self.iva_valor,
            total_neto=self.total_neto
        )
```

**Características**:
- Inmutabilidad cuando estado = ACEPTADA
- Número correlativo automático (COT-YYYY-NNNN)
- Totales calculados automáticamente desde ítems

### 4. CotizacionItem

**Ubicación**: `apps/tenant/cotizaciones/models.py`

```python
class CotizacionItem(models.Model):
    class TipoItem(models.TextChoices):
        PRODUCTO = "PRODUCTO"
        SERVICIO = "SERVICIO"
    
    cotizacion = ForeignKey(Cotizacion, related_name='items')
    tipo_item = CharField(max_length=20, choices=TipoItem.choices)
    
    # Llaves foráneas al catálogo
    producto = ForeignKey(Producto, null=True, blank=True)
    servicio = ForeignKey(Servicio, null=True, blank=True)
    
    # Snapshot (Inmutable una vez creado)
    descripcion = TextField()
    marca = CharField(max_length=100, blank=True, null=True)
    referencia = CharField(max_length=100, blank=True, null=True)
    unidad = CharField(max_length=16)
    
    # Precios y Utilidad
    cantidad = DecimalField(max_digits=12, decimal_places=2, default=1.00)
    costo_unitario = DecimalField(max_digits=15, decimal_places=2)
    porcentaje_utilidad = DecimalField(max_digits=5, decimal_places=2, default=10.00)
    
    # Valores calculados
    precio_unitario_venta = DecimalField(max_digits=15, decimal_places=2)
    subtotal_linea = DecimalField(max_digits=15, decimal_places=2)
    
    orden = PositiveIntegerField(default=0)
    
    def save(self, *args, **kwargs):
        # 1. Poblar snapshot desde catálogo si es nuevo
        if not self.pk:
            source = self.producto if self.tipo_item == TipoItem.PRODUCTO else self.servicio
            if source:
                self.descripcion = source.descripcion or source.nombre
                self.costo_unitario = source.precio_venta
                self.unidad = getattr(source, 'unidad', 'UND')
                self.marca = getattr(source, 'marca', '')
                self.referencia = getattr(source, 'referencia', '')
        
        # 2. Cálculos de utilidad dinámica
        factor = (Decimal('1.00') + (self.porcentaje_utilidad / Decimal('100.00')))
        self.precio_unitario_venta = self.costo_unitario * factor
        self.subtotal_linea = self.cantidad * self.precio_unitario_venta
        
        super().save(*args, **kwargs)
        self.cotizacion.actualizar_totales()
```

**Características**:
- Snapshot inmutable: guarda copia de datos del catálogo al crear
- Utilidad dinámica: cálculo automático de precio de venta
- Actualización automática de totales de cotización

---

## 🔧 Capa de Servicios

**Ubicación**: `apps/tenant/cotizaciones/services.py`

### Funciones Principales

#### 1. QuerySets Optimizados

```python
def qs_list(empresa_id: int, search: Optional[str] = None):
    """QuerySet optimizado para listado (Tabulator)"""
    # Usa select_related() y only() para optimizar queries
    # Filtra por empresa (SSoT)
    # Soporta búsqueda en número, cliente, asunto

def qs_detail(empresa_id: int):
    """QuerySet optimizado para detalle"""
    # Incluye prefetch_related() para items
    # Carga relaciones necesarias
```

#### 2. Cálculo de Totales

```python
def calcular_totales_cotizacion(
    subtotal: Decimal,
    descuento_porcentaje: Decimal = Decimal('0.00'),
    iva_porcentaje: Decimal = Decimal('19.00'),
    retefuente_porcentaje: Decimal = Decimal('0.00'),
    reteica_porcentaje: Decimal = Decimal('0.00')
) -> Dict[str, Decimal]:
    """Calcula totales de cotización (Colombia)"""
    # Fórmula: Subtotal -> Descuento -> IVA -> Retenciones -> Total Neto

def recalcular_totales_cotizacion(cotizacion_id: int) -> Dict[str, Any]:
    """Recalcula totales de una cotización existente"""
    # Valida inmutabilidad
    # Suma subtotales de ítems
    # Actualiza cotización
```

#### 3. Generación de Números

```python
def obtener_siguiente_numero_cotizacion(empresa_id: int) -> str:
    """Genera número correlativo (COT-YYYY-NNNN)"""
    # Busca último número del año actual
    # Incrementa secuencialmente
    # Formato: COT-2026-0001
```

#### 4. Resumen y Estadísticas

```python
def get_cotizaciones_summary(empresa_id: Optional[int] = None) -> Dict[str, Any]:
    """Calcula resumen de cotizaciones para dashboard"""
    # Agregaciones optimizadas
    # Total neto, cantidad por estado
```

#### 5. Materialización de Productos

```python
@transaction.atomic
def materializar_producto_desde_dto(dto: dict, empresa_id: Optional[int] = None) -> tuple[dict, int]:
    """Materializa producto desde DTO del Document Ingest Pipeline"""
    # Usa SemanticMapper para mapeo inteligente
    # Deducción de campos faltantes
    # update_or_create basado en empresa + código

@transaction.atomic
def materializar_catalogo_desde_plantilla(dto_list: list[Dict[str, Any]], empresa_id: Optional[int] = None) -> tuple[Dict[str, Any], int]:
    """Materializa múltiples productos desde plantilla Excel"""
    # Procesamiento masivo optimizado
    # Estadísticas de creación/actualización
    # Manejo de errores por ítem
```

#### 6. Guardado Masivo de Cotizaciones

```python
@transaction.atomic
def procesar_guardado_masivo(
    empresa_id: int,
    cliente_id: int,
    data_items: List[Dict[str, Any]],
    fecha_emision: Optional[str] = None,
    fecha_vencimiento: Optional[str] = None,
    atencion_a: Optional[str] = None,
    asunto: Optional[str] = None,
    iva_porcentaje: Decimal = Decimal('19.00')
) -> tuple[Dict[str, Any], int]:
    """Procesa guardado masivo desde editor estilo Excel"""
    # Crea Cotizacion con número correlativo
    # Persiste cada fila como CotizacionItem
    # Toma snapshot del catálogo si producto existe
    # Usa actualizar_totales() del modelo
```

---

## 🌐 Capa API (DRF)

**Ubicación**: `apps/tenant/cotizaciones/api/viewsets.py`

### ViewSets Principales

#### 1. CotizacionViewSet

**Endpoints Base**:
- `GET /api/v1/cotizaciones/` - Lista paginada (Tabulator)
- `POST /api/v1/cotizaciones/` - Crear cotización
- `GET /api/v1/cotizaciones/{id}/` - Detalle
- `PATCH /api/v1/cotizaciones/{id}/` - Actualizar (solo si no aceptada)
- `DELETE /api/v1/cotizaciones/{id}/` - Eliminar (solo si no aceptada)

**Acciones Personalizadas**:
- `POST /api/v1/cotizaciones/{id}/cambiar-estado/` - Cambiar estado
- `GET /api/v1/cotizaciones/summary/` - Resumen para dashboard
- `POST /api/v1/cotizaciones/bulk-save/` - Guardado masivo desde editor

**Características**:
- Paginación: `StandardResultsSetPagination`
- Filtros: `estado`, `cliente`
- Búsqueda: `numero`, `cliente__razon_social`, `asunto`
- Ordenamiento: `-fecha_emision`, `-numero`
- Validación de inmutabilidad en `perform_update()` y `perform_destroy()`

#### 2. CotizacionItemViewSet

**Endpoints**:
- `POST /api/v1/cotizaciones/cotizaciones-items/` - Crear ítem
- `PATCH /api/v1/cotizaciones/cotizaciones-items/{id}/` - Actualizar ítem
- `DELETE /api/v1/cotizaciones/cotizaciones-items/{id}/` - Eliminar ítem

**Características**:
- Recalcula totales automáticamente después de crear/actualizar/eliminar
- Valida inmutabilidad de cotización padre

#### 3. ProductoViewSet

**Endpoints Base**:
- `GET /api/v1/cotizaciones/productos/` - Lista paginada
- `POST /api/v1/cotizaciones/productos/` - Crear producto
- `GET /api/v1/cotizaciones/productos/{id}/` - Detalle
- `PATCH /api/v1/cotizaciones/productos/{id}/` - Actualizar
- `DELETE /api/v1/cotizaciones/productos/{id}/` - Eliminar

**Acciones Personalizadas**:
- `GET /api/v1/cotizaciones/productos/descargar-plantilla/` - Descargar plantilla Excel
- `POST /api/v1/cotizaciones/productos/create-from-dto/` - Materializar desde DTO

**Características**:
- Filtros: `activo`
- Búsqueda: `codigo`, `nombre`, `marca`, `referencia`
- Soporta materialización masiva desde plantilla

---

## 💻 Capa Frontend

### Módulos JavaScript

#### 1. cotizaciones.page.js

**Responsabilidad**: Módulo principal de gestión de cotizaciones

**Funcionalidades**:
- Tabla Tabulator con paginación remota
- Búsqueda en tiempo real
- Panel de resumen (totales por estado)
- Acciones: Ver, Editar, Cambiar Estado, Generar PDF, Eliminar
- Integración con editor estilo Excel

**Dependencias**:
- `TabulatorFactory` (The Engine)
- `cotizaciones.api.js` (Wrapper de API)
- `DOMUtils.onVisibleOnce()` (Lazy loading)

#### 2. cotizacion_editor.js

**Responsabilidad**: Editor estilo Excel para crear cotizaciones

**Funcionalidades**:
- Tabla Tabulator editable con clipboard (Ctrl+V)
- Celdas editables: Cantidad, Costo Unitario
- Autocompletado: búsqueda de productos por código
- Cálculos automáticos: precio unitario de venta, subtotal línea
- Panel de totales en tiempo real
- Validación de campos obligatorios
- Guardado masivo al endpoint `bulk-save`

**Características**:
- Clipboard habilitado para pegar desde Excel
- Búsqueda automática de productos en catálogo
- Cálculo de utilidad dinámica
- Actualización de totales en tiempo real

#### 3. productos.page.js

**Responsabilidad**: Gestión de catálogo de productos (STS)

**Funcionalidades**:
- Tabla Tabulator con productos
- Descarga de plantilla Excel oficial
- Importación masiva desde Excel/PDF
- CRUD completo de productos
- Integración con Document Ingest Pipeline

**Flujo de Importación**:
1. Usuario descarga plantilla Excel
2. Usuario llena plantilla con productos
3. Usuario sube archivo al endpoint `/api/v1/core/documentos/upload/`
4. Sistema parsea y valida archivo
5. Sistema materializa productos en catálogo

### Templates HTML

#### 1. list.html
- Vista principal de cotizaciones
- Panel de resumen (cards)
- Tabla Tabulator
- Toolbar con acciones

#### 2. list_productos.html
- Vista de catálogo de productos
- Botones: Descargar Plantilla, Subir Catálogo, Nuevo Producto

#### 3. modal_editor.html
- Modal fullscreen para editor estilo Excel
- Formulario de cabecera (cliente, fechas, etc.)
- Tabla editor Tabulator
- Panel de totales

---

## 🔄 Flujos Principales

### Flujo 1: Crear Cotización desde Editor Estilo Excel

```
1. Usuario hace click en "Nueva Cotización"
   ↓
2. Se abre modal del editor (modal_editor.html)
   ↓
3. Usuario selecciona cliente y completa cabecera
   ↓
4. Usuario pega datos desde Excel (Ctrl+V) o edita manualmente
   ↓
5. Sistema autocompleta productos si código existe en catálogo
   ↓
6. Sistema calcula automáticamente:
   - Precio unitario de venta (costo * (1 + %utilidad))
   - Subtotal línea (cantidad * precio_unitario_venta)
   - Totales (subtotal, IVA, total neto)
   ↓
7. Usuario hace click en "Guardar Cotización"
   ↓
8. Frontend envía POST /api/v1/cotizaciones/bulk-save/
   {
     "cliente_id": 1,
     "fecha_emision": "2026-02-17",
     "items": [...]
   }
   ↓
9. Backend valida cliente pertenece a empresa
   ↓
10. Backend llama procesar_guardado_masivo()
    ↓
11. Backend crea Cotizacion con número correlativo
    ↓
12. Backend crea cada CotizacionItem:
    - Busca producto en catálogo si código existe
    - Toma snapshot (marca, referencia, unidad, costo)
    - Calcula precio_unitario_venta y subtotal_linea
    ↓
13. Backend llama cotizacion.actualizar_totales()
    ↓
14. Backend retorna respuesta con cotización creada
    ↓
15. Frontend muestra notificación de éxito
    ↓
16. Frontend cierra modal y recarga lista de cotizaciones
```

### Flujo 2: Importar Catálogo de Productos desde Excel

```
1. Usuario hace click en "Descargar Plantilla"
   ↓
2. Frontend llama GET /api/v1/cotizaciones/productos/descargar-plantilla/
   ↓
3. Backend genera Excel con encabezados del modelo Producto
   ↓
4. Usuario descarga plantilla Excel
   ↓
5. Usuario llena plantilla con productos
   ↓
6. Usuario hace click en "Subir Catálogo"
   ↓
7. Frontend sube archivo a POST /api/v1/core/documentos/upload/?tipo=inventario
   ↓
8. Document Ingest Pipeline:
    - Detecta tipo de archivo (Excel)
    - Usa parser específico de cotizaciones (apps.services.document_parser.cotizaciones)
    - Usa SemanticMapper para mapeo inteligente de columnas
    - Valida con CotizacionesValidator (NO valida campos de facturas)
    - Retorna DTO con items
   ↓
9. Frontend recibe DTO con items parseados
   ↓
10. Frontend envía POST /api/v1/cotizaciones/productos/create-from-dto/
    {
      "dto": {
        "items": [...]
      }
    }
    ↓
11. Backend detecta que dto tiene "items" (catálogo completo)
    ↓
12. Backend llama materializar_catalogo_desde_plantilla()
    ↓
13. Backend procesa cada item:
    - update_or_create basado en empresa + código
    - Evita duplicados
    - Retorna estadísticas (creados, actualizados, errores)
    ↓
14. Frontend muestra notificación con estadísticas
    ↓
15. Frontend recarga tabla de productos
```

### Flujo 3: Cambiar Estado de Cotización

```
1. Usuario hace click en "Cambiar Estado" en una cotización
   ↓
2. Frontend muestra modal de selección de estado
   ↓
3. Usuario selecciona nuevo estado (ej: ENVIADA)
   ↓
4. Frontend envía POST /api/v1/cotizaciones/{id}/cambiar-estado/
   {
     "estado": "ENVIADA"
   }
   ↓
5. Backend valida:
    - Cotización existe
    - Estado es válido
    - Si estado actual es ACEPTADA, solo permite mantener ACEPTADA
   ↓
6. Backend actualiza estado
   ↓
7. Backend retorna respuesta
   ↓
8. Frontend recarga tabla
```

### Flujo 4: Editar Ítem de Cotización

```
1. Usuario edita ítem de cotización existente
   ↓
2. Frontend envía PATCH /api/v1/cotizaciones/cotizaciones-items/{id}/
   {
     "cantidad": "20.00",
     "porcentaje_utilidad": "15.00"
   }
   ↓
3. Backend valida:
    - Cotización padre no está ACEPTADA (inmutable)
    - Campos son válidos
   ↓
4. Backend actualiza ítem
   ↓
5. Backend recalcula:
    - precio_unitario_venta = costo_unitario * (1 + %utilidad)
    - subtotal_linea = cantidad * precio_unitario_venta
   ↓
6. Backend llama recalcular_totales_cotizacion()
   ↓
7. Backend actualiza totales de cotización
   ↓
8. Backend retorna respuesta
   ↓
9. Frontend recarga tabla de cotizaciones
```

---

## 🔗 Integraciones

### 1. Document Ingest Pipeline

**Ubicación**: `apps/services/document_ingest/`

**Integración**:
- Parser específico: `apps/services/document_parser/cotizaciones/excel_parser.py`
- Validador específico: `apps/services/document_ingest/validations/cotizaciones.py`
- Normalizador: `apps/services/document_parser/cotizaciones/normalizers.py`
- DTO: `apps/services/document_parser/cotizaciones/dto.py`

**Flujo**:
1. Usuario sube archivo Excel/PDF
2. Router detecta `kind_hint=inventario` y usa parser de cotizaciones
3. Parser usa `SemanticMapper` para mapeo inteligente de columnas
4. Validador valida campos de catálogo (NO campos de facturas)
5. Retorna DTO canónico con items
6. Frontend materializa productos en catálogo

### 2. Sistema de Clientes

**Ubicación**: `apps/tenant/clientes/`

**Integración**:
- Cotizacion tiene ForeignKey a Cliente
- Validación: cliente debe pertenecer a empresa (SSoT)
- Frontend carga clientes en select del editor

### 3. Sistema de Empresa (SSoT)

**Ubicación**: `apps/tenant/empresa/`

**Integración**:
- Todas las entidades filtran por empresa (SSoT)
- Empresa es singleton del tenant
- QuerySets optimizados usan `empresa_id` para filtrado

---

## 📡 Endpoints API

### Cotizaciones

| Método | Endpoint | Descripción | Autenticación |
|--------|----------|-------------|---------------|
| GET | `/api/v1/cotizaciones/` | Lista paginada | IsTenantMember |
| POST | `/api/v1/cotizaciones/` | Crear cotización | IsTenantAdminOrReadOnly |
| GET | `/api/v1/cotizaciones/{id}/` | Detalle | IsTenantMember |
| PATCH | `/api/v1/cotizaciones/{id}/` | Actualizar | IsTenantAdminOrReadOnly |
| DELETE | `/api/v1/cotizaciones/{id}/` | Eliminar | IsTenantAdminOrReadOnly |
| POST | `/api/v1/cotizaciones/{id}/cambiar-estado/` | Cambiar estado | IsTenantAdminOrReadOnly |
| GET | `/api/v1/cotizaciones/summary/` | Resumen dashboard | IsTenantMember |
| POST | `/api/v1/cotizaciones/bulk-save/` | Guardado masivo | IsTenantAdminOrReadOnly |

### Cotizaciones Items

| Método | Endpoint | Descripción | Autenticación |
|--------|----------|-------------|---------------|
| POST | `/api/v1/cotizaciones/cotizaciones-items/` | Crear ítem | IsTenantAdminOrReadOnly |
| PATCH | `/api/v1/cotizaciones/cotizaciones-items/{id}/` | Actualizar ítem | IsTenantAdminOrReadOnly |
| DELETE | `/api/v1/cotizaciones/cotizaciones-items/{id}/` | Eliminar ítem | IsTenantAdminOrReadOnly |

### Productos (Catálogo)

| Método | Endpoint | Descripción | Autenticación |
|--------|----------|-------------|---------------|
| GET | `/api/v1/cotizaciones/productos/` | Lista paginada | IsTenantMember |
| POST | `/api/v1/cotizaciones/productos/` | Crear producto | IsTenantAdminOrReadOnly |
| GET | `/api/v1/cotizaciones/productos/{id}/` | Detalle | IsTenantMember |
| PATCH | `/api/v1/cotizaciones/productos/{id}/` | Actualizar | IsTenantAdminOrReadOnly |
| DELETE | `/api/v1/cotizaciones/productos/{id}/` | Eliminar | IsTenantAdminOrReadOnly |
| GET | `/api/v1/cotizaciones/productos/descargar-plantilla/` | Descargar plantilla | IsTenantMember |
| POST | `/api/v1/cotizaciones/productos/create-from-dto/` | Materializar desde DTO | IsTenantAdminOrReadOnly |

### Parámetros de Consulta Comunes

- `?page=1` - Número de página
- `?page_size=10` - Tamaño de página
- `?search=texto` - Búsqueda (cotizaciones: número, cliente, asunto | productos: código, nombre, marca, referencia)
- `?estado=BORRADOR` - Filtro por estado (cotizaciones)
- `?activo=true` - Filtro por activo (productos)
- `?ordering=-fecha_emision` - Ordenamiento

---

## 📈 Diagramas de Flujo

### Diagrama de Arquitectura General

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │cotizaciones. │  │cotizacion_  │  │productos.    │      │
│  │page.js       │  │editor.js    │  │page.js       │      │
│  └──────┬───────┘  └──────┬──────┘  └──────┬──────┘      │
│         │                  │                 │              │
│         └──────────────────┴─────────────────┘              │
│                            │                                │
│                            ▼                                │
│                   ┌─────────────────┐                       │
│                   │ TabulatorFactory│                       │
│                   └────────┬────────┘                       │
└────────────────────────────┼────────────────────────────────┘
                             │ HTTP REST API
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND (DRF)                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         CotizacionViewSet                           │   │
│  │  - list()                                           │   │
│  │  - create()                                         │   │
│  │  - retrieve()                                       │   │
│  │  - update()                                         │   │
│  │  - destroy()                                        │   │
│  │  - cambiar_estado()                                 │   │
│  │  - summary()                                        │   │
│  │  - bulk_save()                                      │   │
│  └──────────────┬──────────────────────────────────────┘   │
│                 │                                            │
│  ┌──────────────▼──────────────────────────────────────┐   │
│  │         CotizacionItemViewSet                       │   │
│  │  - create()                                         │   │
│  │  - update()                                         │   │
│  │  - destroy()                                        │   │
│  └──────────────┬──────────────────────────────────────┘   │
│                 │                                            │
│  ┌──────────────▼──────────────────────────────────────┐   │
│  │         ProductoViewSet                              │   │
│  │  - list()                                           │   │
│  │  - create()                                         │   │
│  │  - descargar_plantilla()                            │   │
│  │  - create_from_dto()                                │   │
│  └──────────────┬──────────────────────────────────────┘   │
└─────────────────┼───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  services.py                                         │   │
│  │  - qs_list()                                         │   │
│  │  - qs_detail()                                       │   │
│  │  - calcular_totales_cotizacion()                     │   │
│  │  - recalcular_totales_cotizacion()                   │   │
│  │  - obtener_siguiente_numero_cotizacion()             │   │
│  │  - get_cotizaciones_summary()                        │   │
│  │  - materializar_producto_desde_dto()                 │   │
│  │  - materializar_catalogo_desde_plantilla()          │   │
│  │  - procesar_guardado_masivo()                        │   │
│  └──────────────┬──────────────────────────────────────┘   │
└─────────────────┼───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                      MODELS (Django ORM)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Cotizacion  │  │CotizacionItem│  │   Producto   │      │
│  └──────┬───────┘  └──────┬──────┘  └──────┬──────┘      │
│         │                  │                 │              │
│         └──────────────────┴─────────────────┘              │
│                            │                                │
│                            ▼                                │
│                   ┌─────────────────┐                       │
│                   │   PostgreSQL     │                       │
│                   │  (Multi-tenant)  │                       │
│                   └──────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

### Diagrama de Flujo: Crear Cotización desde Editor

```
Usuario
  │
  ├─► Click "Nueva Cotización"
  │
  ▼
Modal Editor (cotizacion_editor.js)
  │
  ├─► Selecciona Cliente
  ├─► Completa Cabecera (fechas, atención, asunto)
  │
  ▼
Tabla Tabulator Editable
  │
  ├─► Opción A: Pega desde Excel (Ctrl+V)
  │   └─► Sistema parsea y crea filas
  │
  ├─► Opción B: Edita manualmente
  │   └─► Sistema autocompleta si código existe
  │
  ▼
Cálculos Automáticos
  │
  ├─► Precio Unit. Venta = Costo * (1 + %Utilidad)
  ├─► Subtotal Línea = Cantidad * Precio Unit. Venta
  └─► Totales = Suma de Subtotales + IVA
  │
  ▼
Click "Guardar Cotización"
  │
  ▼
POST /api/v1/cotizaciones/bulk-save/
  │
  ▼
CotizacionViewSet.bulk_save()
  │
  ├─► Valida Empresa (SSoT)
  ├─► Valida Cliente pertenece a Empresa
  └─► Valida Items no vacíos
  │
  ▼
procesar_guardado_masivo()
  │
  ├─► Genera número correlativo (COT-YYYY-NNNN)
  ├─► Crea Cotizacion
  │
  ▼
Para cada Item:
  │
  ├─► Busca Producto en Catálogo (por código o ID)
  ├─► Si existe: Toma Snapshot (marca, ref, unidad, costo)
  ├─► Si no existe: Usa datos manuales
  ├─► Calcula Precio Unit. Venta y Subtotal Línea
  └─► Crea CotizacionItem
  │
  ▼
cotizacion.actualizar_totales()
  │
  ├─► Suma Subtotales de Items
  ├─► Calcula IVA
  └─► Calcula Total Neto
  │
  ▼
Retorna Respuesta (201 Created)
  │
  ▼
Frontend
  │
  ├─► Muestra Notificación de Éxito
  ├─► Cierra Modal
  └─► Recarga Lista de Cotizaciones
```

---

## 🔒 Reglas de Negocio

### Inmutabilidad

- **Regla**: Cotizaciones con estado `ACEPTADA` son inmutables
- **Implementación**:
  - `Cotizacion.es_inmutable` property retorna `True` si estado = ACEPTADA
  - `perform_update()` y `perform_destroy()` validan inmutabilidad
  - `CotizacionItemViewSet` valida inmutabilidad de cotización padre
  - `clean()` método del modelo valida antes de guardar

### SSoT (Single Source of Truth)

- **Regla**: Empresa es singleton del tenant
- **Implementación**:
  - Todos los QuerySets filtran por `empresa_id`
  - `perform_create()` asigna empresa automáticamente
  - Validación de cliente pertenece a empresa

### Utilidad Dinámica

- **Regla**: Precio de venta = Costo * (1 + %Utilidad)
- **Implementación**:
  - Cálculo automático en `CotizacionItem.save()`
  - Actualización automática de totales de cotización

### Snapshot de Catálogo

- **Regla**: Al crear ítem, se guarda snapshot de datos del catálogo
- **Implementación**:
  - `CotizacionItem.save()` pobla snapshot si es nuevo
  - Snapshot es inmutable una vez creado
  - Permite cambios en catálogo sin afectar cotizaciones existentes

---

## 📊 Métricas y Performance

### Optimizaciones Implementadas

1. **QuerySets Optimizados**:
   - Uso de `select_related()` para relaciones ForeignKey
   - Uso de `prefetch_related()` para relaciones reversas
   - Uso de `only()` para cargar solo campos necesarios
   - Campos alineados con serializers del frontend

2. **Paginación Remota**:
   - Tabulator usa paginación server-side
   - Reduce carga de datos en frontend
   - Mejora tiempo de respuesta

3. **Transacciones Atómicas**:
   - `@transaction.atomic` en operaciones críticas
   - Garantiza integridad de datos
   - Rollback automático en caso de error

4. **Caché de Catálogo**:
   - Frontend cachea productos en memoria
   - Reduce llamadas API para autocompletado

---

## 🚀 Extensiones Futuras

### Funcionalidades Planificadas

1. **Generación de PDF**:
   - Endpoint: `GET /api/v1/cotizaciones/{id}/generar-pdf/`
   - Template PDF con formato profesional
   - Incluye logo de empresa, datos de cliente, ítems, totales

2. **Envío por Email**:
   - Integración con sistema de correo
   - Envío automático al cambiar estado a ENVIADA

3. **Historial de Cambios**:
   - Auditoría de modificaciones
   - Tracking de cambios de estado

4. **Plantillas de Cotización**:
   - Guardar cotizaciones como plantillas
   - Reutilizar plantillas para nuevas cotizaciones

5. **Aprobaciones**:
   - Flujo de aprobación multi-nivel
   - Notificaciones de aprobación

---

## 📝 Notas Técnicas

### Versionado

- **v2.40**: Implementación actual con Service Layer y Tabulator Factory
- **v2.60**: Modelos actualizados con inmutabilidad y snapshot

### Dependencias

- Django 4.x
- Django Rest Framework
- Tabulator.js (CDN)
- pandas (para generación de plantillas Excel)
- openpyxl (para lectura/escritura de Excel)

### Configuración Requerida

1. **INSTALLED_APPS**:
   ```python
   'apps.tenant.cotizaciones',
   ```

2. **URLs**:
   ```python
   path('api/v1/cotizaciones/', include('apps.tenant.cotizaciones.api.urls')),
   ```

3. **Permisos**:
   - `IsTenantMember`: Lectura
   - `IsTenantAdminOrReadOnly`: Escritura

---

## ✅ Checklist de Funcionalidades

### Gestión de Cotizaciones
- [x] Listar cotizaciones con paginación
- [x] Crear cotización (individual y masiva)
- [x] Ver detalle de cotización
- [x] Editar cotización (solo si no aceptada)
- [x] Eliminar cotización (solo si no aceptada)
- [x] Cambiar estado de cotización
- [x] Resumen de cotizaciones (dashboard)
- [x] Editor estilo Excel
- [ ] Generar PDF (placeholder)

### Gestión de Ítems
- [x] Crear ítem
- [x] Actualizar ítem
- [x] Eliminar ítem
- [x] Recalcular totales automáticamente

### Catálogo de Productos
- [x] Listar productos
- [x] Crear producto manualmente
- [x] Actualizar producto
- [x] Eliminar producto
- [x] Descargar plantilla Excel
- [x] Importar catálogo desde Excel/PDF
- [x] Materialización desde DTO (Document Ingest Pipeline)

### Validaciones
- [x] Inmutabilidad de cotizaciones aceptadas
- [x] Validación de cliente pertenece a empresa
- [x] Validación de campos obligatorios
- [x] Validación de números de cotización únicos

### Configuración y Numeración
- [x] Numeración automática e inmutable (formato COT-XXXX-YYYY)
- [x] Módulo de configuración global de parámetros
- [x] Aplicación automática de valores por defecto
- [x] Soporte para numeración manual (opcional)
- [x] API endpoints para configuración (GET/PATCH)
- [x] Integración con Editor Estilo Excel

---

## 11. Configuración y Numeración

> **📚 Documentación Detallada:** Para información completa sobre configuración y numeración, ver: [COTIZACIONES_CONFIGURACION_Y_NUMERACION.md](./COTIZACIONES_CONFIGURACION_Y_NUMERACION.md)

### 11.1 Numeración Automática e Inmutable

El sistema genera números de cotización automáticamente en formato `COT-XXXX-YYYY` donde:
- `COT`: Prefijo fijo
- `XXXX`: Número secuencial con padding de 4 dígitos
- `YYYY`: Año actual

**Características:**
- Generación automática en `procesar_guardado_masivo()`
- Inmutabilidad total después de la creación
- Validación multi-capa (Modelo, Serializer, ViewSet, Frontend)
- Bloqueo de cualquier intento de modificación

**Implementación:**
- Service Layer: `obtener_siguiente_numero_cotizacion(empresa_id)`
- Serializers: Campo `numero` en `read_only_fields` con validación
- ViewSets: Eliminación de `numero` en `perform_create()` y bloqueo en `perform_update()`
- Frontend: Campo de solo lectura que se actualiza después de guardar

### 11.2 Módulo de Configuración (Perfiles Múltiples)

**⚠️ v2.40:** Sistema de perfiles múltiples gestionables (CRUD completo).

**Modelo:** `ConfiguracionCotizacion` (ForeignKey con Empresa)

**Gestión de Perfiles:**
- `nombre_configuracion`: Nombre descriptivo del perfil
- `tipo_plantilla`: Tipo de plantilla (EQUIPO, MATERIAL, SERVICIO, MIXTO)
- `es_activo`: Indica si el perfil está activo (solo uno activo por empresa)

**Modelos de Cotización Habilitados:**
- `permitir_modelo_equipos`: Controla si el modelo "1.0 Equipos" está disponible
- `permitir_modelo_materiales`: Controla si el modelo "2.0 Materiales" está disponible
- `permitir_modelo_servicios`: Controla si el modelo "3.0 Servicios" está disponible
- `permitir_modelo_mixto`: Controla si el modelo "Mixto" está disponible

**Parámetros Configurables:**
- `porcentaje_utilidad_default`: Porcentaje de utilidad predeterminado (fallback)
- `iva_porcentaje_default`: IVA por defecto (fallback)
- `dias_vencimiento_default`: Días hasta vencimiento (default: 30)
- `plantilla_numeracion`: Plantilla para números (default: 'COT-XXXX-YYYY')
- `numero_manual_habilitado`: Permite número manual (default: False)
- `unidad_default`: Unidad por defecto (default: 'UND')
- `formato_moneda`: Formato de moneda (default: 'COP')
- `notas_comerciales_default`: Texto por defecto para notas
- Parámetros específicos por modelo (utilidad e IVA por tipo)
- Parámetros AIU (solo para SERVICIO y MATERIAL)

**API Endpoints:**
- `GET /api/v1/cotizaciones/configuracion/`: Lista de perfiles (paginada)
- `GET /api/v1/cotizaciones/configuracion/{id}/`: Detalle de un perfil
- `POST /api/v1/cotizaciones/configuracion/`: Crear nuevo perfil
- `PATCH /api/v1/cotizaciones/configuracion/{id}/`: Actualizar perfil
- `POST /api/v1/cotizaciones/configuracion/{id}/activar/`: Activar perfil
- `DELETE /api/v1/cotizaciones/configuracion/{id}/`: Eliminar perfil

**Integración:**
- Los valores se aplican automáticamente desde el perfil activo al crear cotizaciones
- El editor carga la configuración activa al inicializar
- Se aplican valores por defecto según el modelo seleccionado
- Filtrado dinámico de opciones en "Nueva Cotización" según modelos habilitados

### 11.3 Numeración Manual (Opcional)

Si `numero_manual_habilitado = true`:
- El campo número se habilita para edición en el frontend
- El usuario puede ingresar un número personalizado
- El sistema valida que el número no exista (duplicados)
- Si es válido, se usa el número manual en lugar del automático
- El número manual también es inmutable después de creado

**Validación:**
```python
if numero_manual and config and config.numero_manual_habilitado:
    if Cotizacion.objects.filter(empresa_id=empresa_id, numero=numero_manual).exists():
        return {"error": "numero_duplicado", ...}, 422
    numero = numero_manual
else:
    numero = obtener_siguiente_numero_cotizacion(empresa_id)
```

> **📚 Para documentación detallada, ver:** [COTIZACIONES_CONFIGURACION_Y_NUMERACION.md](./COTIZACIONES_CONFIGURACION_Y_NUMERACION.md)

---

## 12. AIU (Administración, Imprevistos, Utilidad)

> **📚 Documentación Detallada:** Para información completa sobre la implementación de AIU, ver: [COTIZACIONES_AIU_IMPLEMENTACION.md](./COTIZACIONES_AIU_IMPLEMENTACION.md)

### 12.1 Resumen

**AIU (Administración, Imprevistos, Utilidad)** es una característica habilitable por cotización individual que permite aplicar un cálculo especial de IVA según la normativa colombiana, donde el IVA se aplica únicamente sobre el componente de **Utilidad**.

### 12.2 Características Principales

- ✅ **Característica por Cotización**: AIU se configura individualmente para cada cotización, no es una configuración global
- ✅ **Modal de Configuración**: Interfaz dedicada para activar/desactivar y configurar porcentajes AIU
- ✅ **Validación de Modelo**: Solo aplicable para cotizaciones de tipo `SERVICIO` o `MATERIAL`
- ✅ **Inmutabilidad**: No se puede modificar el modo AIU en cotizaciones `ACEPTADA`
- ✅ **Cálculo Automático**: El sistema calcula automáticamente los valores de A, I, U y el IVA sobre Utilidad

### 12.3 Campos en el Modelo

El modelo `Cotizacion` incluye los siguientes campos para AIU:

- `es_aiu` (Boolean): Indica si el modo AIU está activo
- `aiu_admin_porcentaje` (Decimal): Porcentaje de administración
- `aiu_imprevistos_porcentaje` (Decimal): Porcentaje de imprevistos
- `aiu_utilidad_porcentaje` (Decimal): Porcentaje de utilidad (base para IVA)
- `valor_administracion` (Decimal): Valor calculado de administración
- `valor_imprevistos` (Decimal): Valor calculado de imprevistos
- `valor_utilidad` (Decimal): Valor calculado de utilidad

### 12.4 Lógica de Cálculo

**Modo AIU Activo (`es_aiu = True`)**:
```
Subtotal Base = Suma de (cantidad × costo_unitario) sin utilidad
Administración = Subtotal Base × (aiu_admin_porcentaje / 100)
Imprevistos = Subtotal Base × (aiu_imprevistos_porcentaje / 100)
Utilidad = Subtotal Base × (aiu_utilidad_porcentaje / 100)
IVA = Utilidad × (iva_porcentaje / 100)  ← Solo sobre Utilidad
Total Neto = Subtotal Base + Administración + Imprevistos + Utilidad + IVA
```

**Modo Estándar (`es_aiu = False`)**:
```
Subtotal = Suma de subtotal_linea (con utilidad)
IVA = Subtotal × (iva_porcentaje / 100)  ← Sobre subtotal completo
Total Neto = Subtotal + IVA
```

### 12.5 Interfaz de Usuario

El botón "Configurar AIU" se encuentra en el panel de totales del Editor Estilo Excel. Al hacer clic, se abre un modal que permite:

1. Activar/desactivar el modo AIU
2. Configurar porcentajes de A, I y U
3. Ver advertencias sobre aplicabilidad (solo SERVICIO o MATERIAL)

### 12.6 Validaciones

1. **Validación de Modelo**: AIU solo es válido para `SERVICIO` o `MATERIAL`
2. **Inmutabilidad de `es_aiu`**: No se puede cambiar una vez guardada la cotización
3. **Inmutabilidad por Estado**: Cotizaciones `ACEPTADA` no permiten modificar AIU

### 12.7 Ejemplo de Uso

**Escenario**: Cotización de servicios de instalación con AIU activo.

**Datos**:
- Subtotal Base: $1,000,000
- % Administración: 10%
- % Imprevistos: 5%
- % Utilidad: 10%
- % IVA: 19%

**Cálculo**:
```
Subtotal Base: $1,000,000
Administración (10%): $100,000
Imprevistos (5%): $50,000
Utilidad (10%): $100,000
IVA (19% sobre Utilidad): $19,000
─────────────────────────────
Total Neto: $1,169,000
```

---

**Fin del Informe**

*Documento generado automáticamente - SINTEL v2.40*
