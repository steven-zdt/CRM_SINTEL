# Auditoría Completa - App Contabilidad

**Fecha:** Diciembre 2024  
**Versión:** v2.61  
**Módulo:** `apps/tenant/contabilidad`

## 📋 Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Estructura de Archivos](#estructura-de-archivos)
3. [Modelos y Lógica de Negocio](#modelos-y-lógica-de-negocio)
4. [Capa de API (ViewSets, Serializers, URLs)](#capa-de-api)
5. [Capa de Servicios](#capa-de-servicios)
6. [Capa de Frontend](#capa-de-frontend)
7. [Flujos de Negocio](#flujos-de-negocio)
8. [Validaciones y Reglas](#validaciones-y-reglas)
9. [Optimizaciones y Performance](#optimizaciones-y-performance)
10. [Dependencias y Relaciones](#dependencias-y-relaciones)

---

## 1. Resumen Ejecutivo

### Propósito
La app `contabilidad` gestiona el plan de cuentas contables, asientos contables y movimientos contables para cada tenant. Proporciona funcionalidad completa de contabilidad básica con validaciones de cuadratura (debe = haber).

### Arquitectura
- **API-First**: Endpoints REST bajo `/api/v1/contabilidad/`
- **Service Layer Pattern**: Lógica de negocio en `services/` y `services.py`
- **Multi-tenant**: Aislamiento automático por esquema (django-tenants)
- **ENFORCED MODE v2.40**: Solo STAFF/ADMIN pueden crear/editar/eliminar
- **Zero Waste**: QuerySets optimizados con `only()` para reducir SELECT
- **Feature-Sliced Design v2.60**: UI modular con HTMX + Offcanvas
- **Event-Driven Accounting**: Materialización automática de asientos desde facturas/gastos
- **Tabulator Factory v2.40**: Tablas modernas con server-side pagination

### Componentes Principales
1. **CuentaContable**: Plan de cuentas (ACTIVO, PASIVO, PATRIMONIO, INGRESO, GASTO)
2. **AsientoContable**: Asientos contables con estados (BORRADOR, APROBADO, CERRADO)
3. **MovimientoContable**: Partidas de asientos (débito/crédito)
4. **PeriodoContable**: ⚠️ v2.60 Fase 3 - Periodos contables cerrados para inmutabilidad
5. **CatalogoMaestroNIIF**: ✅ v2.61 - Catálogo oficial NIIF Colombia (SSoT)

---

## 2. Estructura de Archivos

```
apps/tenant/contabilidad/
├── __init__.py
├── admin.py                    # Configuración Django Admin
├── apps.py                     # Configuración de la app
├── models.py                   # Modelos: CuentaContable, AsientoContable, MovimientoContable, PeriodoContable, CatalogoMaestroNIIF
├── services.py                 # Service Layer principal (LIST_FIELDS, DETAIL_FIELDS, qs_*)
├── choices/
│   └── choices.py              # ✅ v2.61 - CATALOGO_NIIF_COLOMBIA (catálogo oficial)
├── management/
│   └── commands/
│       └── poblar_catalogo_niif.py  # ✅ v2.61 - Comando para poblar catálogo NIIF
├── services/
│   ├── __init__.py
│   ├── cuentas_service.py     # Lógica de negocio para CuentaContable
│   ├── asientos_service.py     # Lógica de negocio para AsientoContable
│   └── movimientos_service.py # Lógica de negocio para MovimientoContable
├── api/
│   ├── __init__.py
│   ├── viewsets.py            # ViewSets: CuentaContable, AsientoContable, MovimientoContable, CatalogoMaestroNIIF
│   ├── serializers.py         # Serializers: List/Detail para cada modelo
│   ├── urls.py                # Router DRF y URLs
│   ├── filters.py             # Filtros personalizados (vacío, usa filterset_fields)
│   ├── permissions.py         # Permisos (re-exporta DEFAULT_VIEWSET_PERMISSIONS)
│   ├── pagination.py          # Paginación (re-exporta StandardResultsSetPagination)
│   └── datatables.py          # ⚠️ DEPRECATED: Endpoints DataTables legacy
├── migrations/
│   └── 0001_initial.py        # Migración inicial
├── templates/
│   └── tenant/contabilidad/partials/
│       ├── assets_contabilidad.html
│       ├── assets_cuentas.html
│       ├── assets_asientos.html
│       ├── list_cuentas.html
│       ├── list_asientos.html
│       ├── modals_cuentas.html
│       ├── modals_asientos.html
│       └── summary.html
├── static/
│   ├── contabilidad/js/contabilidad.js  # ⚠️ Legacy
│   └── tenant/contabilidad/contabilidad.ui.js  # ⚠️ Legacy
├── tests/
│   ├── __init__.py
│   ├── test_api_contabilidad.py
│   └── test_templates.py
└── views_ui.py                # ⚠️ DEPRECATED: UI movida a Core (archivo vacío, mantenido por compatibilidad)
```

### Archivos Frontend (Core)
```
apps/tenant/core/static/core/js/contabilidad/
├── contabilidad.page.js       # Módulo principal (OLA 3 - DataTables) ⚠️ Legacy
├── contabilidad.api.js        # API wrapper
├── contabilidad.ui.js          # UI helpers
├── contabilidad.modals.js      # Gestión de modales
├── cuentas.page.js            # Módulo Cuentas (v3.3 - Tabulator) ✅
├── asientos.page.js           # Módulo Asientos (v2.37 - DataTables) ⚠️ Legacy
├── asientos_main.js           # ✅ v2.60 - Tabla Tabulator para asientos
├── asientos_form.js           # ✅ v2.60 - Formulario con cuadratura en vivo
└── asientos_cargar_desde_docs.js # ✅ v2.60 - Asistente de selección de documentos
```

### Templates Frontend (Core)
```
apps/tenant/core/templates/tenant/core/partials/contabilidad/
├── list_cuentas.html
├── list_asientos.html
├── modals_cuentas.html
├── modals_asientos.html          # ⚠️ Legacy (reemplazado por offcanvas)
├── assets_cuentas.html
└── assets_asientos.html

apps/tenant/core/templates/tenant/core/contabilidad/partials/
├── asiento_offcanvas_detalle.html      # ✅ v2.60 - HTMX Offcanvas detalle asiento
├── asiento_offcanvas_form.html         # ✅ v2.60 - HTMX Offcanvas formulario asiento
├── asiento_offcanvas_cargar_desde_docs.html  # ✅ v2.60 - HTMX Offcanvas asistente documentos
├── cuenta_offcanvas_detalle.html       # ✅ v2.60 - HTMX Offcanvas detalle cuenta
├── cuenta_offcanvas_form.html          # ✅ v2.60 - HTMX Offcanvas formulario cuenta
├── periodo_offcanvas_detalle.html      # ✅ v2.60 - HTMX Offcanvas detalle periodo
├── periodo_offcanvas_form.html         # ✅ v2.60 - HTMX Offcanvas formulario periodo
├── list_asientos.html                  # Listado de asientos
├── list_cuentas.html                   # Listado de cuentas
├── list_periodos.html                  # ✅ v2.60 - Listado de periodos
├── assets_asiento.html                 # Assets JS para asientos
├── assets_asientos.html                 # Assets JS para módulo asientos
├── assets_cuenta.html                   # Assets JS para cuentas
├── assets_cuentas.html                  # Assets JS para módulo cuentas
├── assets_periodo.html                  # ✅ v2.60 - Assets JS para periodos
└── summary.html                         # Resumen contable
```

---

## 3. Modelos y Lógica de Negocio

### 3.1 CuentaContable

**Ubicación:** `apps/tenant/contabilidad/models.py:18-98`

**Propósito:** Plan de cuentas contables por tenant.

**Campos Principales:**
- `uuid`: UUIDField (lookup público, no expone PK interno)
- `codigo`: CharField(20, unique=True) - Código único de la cuenta
- `nombre`: CharField(200) - Nombre de la cuenta
- `tipo`: CharField(20, choices) - ACTIVO, PASIVO, PATRIMONIO, INGRESO, GASTO
- `descripcion`: TextField (opcional)
- `cuenta_padre`: ForeignKey('self') - Jerarquía de cuentas
- `empresa`: ForeignKey(Empresa, PROTECT) - ⚠️ ENFORCED MODE v2.40: FK NO NULA (SSoT)
- `activa`: BooleanField(default=True)
- `created_at`: DateTimeField(auto_now_add)

**Índices:**
- `['empresa']` - Optimización para FK a Empresa

**Validaciones:**
- `codigo` debe ser único por tenant (aislamiento automático)
- `tipo` debe ser uno de los valores permitidos

**Relaciones:**
- `cuenta_padre` → `CuentaContable` (self-referencing, nullable)
- `empresa` → `Empresa` (PROTECT, NO NULL)
- `cuentas_hijas` → Reverse relation (related_name)

---

### 3.2 AsientoContable

**Ubicación:** `apps/tenant/contabilidad/models.py:101-204`

**Propósito:** Asientos contables con validación de cuadratura.

**Campos Principales:**
- `uuid`: UUIDField (lookup público)
- `numero`: CharField(50, unique=True) - Número único del asiento
- `fecha`: DateField - Fecha del asiento
- `descripcion`: TextField - Descripción del asiento
- `estado`: CharField(20, choices) - BORRADOR, APROBADO, CERRADO
- `total_debe`: DecimalField(15,2) - Total débito (calculado)
- `total_haber`: DecimalField(15,2) - Total crédito (calculado)
- `empresa`: ForeignKey(Empresa, PROTECT) - ⚠️ ENFORCED MODE v2.40: FK NO NULA (SSoT)
- `factura`: ForeignKey('facturas.Factura', SET_NULL, nullable) - Relación opcional con factura
- `created_at`, `updated_at`: DateTimeField

**Índices:**
- `['fecha']` - Búsqueda por fecha
- `['estado']` - Filtrado por estado
- `['empresa']` - Optimización para FK a Empresa

**Validaciones (Model.save):**
```python
if self.estado == 'APROBADO' and self.total_debe != self.total_haber:
    raise ValueError('Un asiento aprobado debe tener débito igual a crédito')
```

**Relaciones:**
- `empresa` → `Empresa` (PROTECT, NO NULL)
- `factura` → `Factura` (SET_NULL, nullable)
- `movimientos` → Reverse relation (MovimientoContable)

**Reglas de Negocio:**
- Un asiento solo puede ser aprobado si `total_debe == total_haber`
- Los totales se calculan automáticamente desde los movimientos

---

### 3.3 MovimientoContable

**Ubicación:** `apps/tenant/contabilidad/models.py:207-275`

**Propósito:** Partidas de un asiento contable (débito/crédito).

**Campos Principales:**
- `asiento`: ForeignKey(AsientoContable, CASCADE) - Asiento al que pertenece
- `cuenta`: ForeignKey(CuentaContable, PROTECT) - Cuenta contable
- `debe`: DecimalField(15,2) - Valor débito
- `haber`: DecimalField(15,2) - Valor crédito
- `descripcion`: TextField (opcional)
- `orden`: IntegerField(default=1) - Orden en el asiento

**Validaciones (Model.save):**
```python
# No puede tener débito y crédito simultáneamente
if self.debe > 0 and self.haber > 0:
    raise ValueError('Un movimiento no puede tener débito y crédito simultáneamente')

# Debe tener al menos uno mayor a cero
if self.debe == 0 and self.haber == 0:
    raise ValueError('Un movimiento debe tener débito o crédito mayor a cero')
```

**Actualización Automática de Totales:**
```python
# Al guardar un movimiento, actualiza totales del asiento
self.asiento.total_debe = sum(m.debe for m in self.asiento.movimientos.all())
self.asiento.total_haber = sum(m.haber for m in self.asiento.movimientos.all())
self.asiento.save()
```

**Relaciones:**
- `asiento` → `AsientoContable` (CASCADE)
- `cuenta` → `CuentaContable` (PROTECT)

---

### 3.4 PeriodoContable ⚠️ v2.60 Fase 3

**Ubicación:** `apps/tenant/contabilidad/models.py:278-388`

**Propósito:** Periodos contables cerrados para garantizar inmutabilidad de datos contables.

**Campos Principales:**
- `empresa`: ForeignKey(Empresa, PROTECT) - ⚠️ ENFORCED MODE v2.40: FK NO NULA (SSoT)
- `periodo`: CharField(7) - Formato YYYY-MM (ej: 2024-01)
- `fecha_inicio`: DateField - Primer día del periodo
- `fecha_fin`: DateField - Último día del periodo
- `estado`: CharField(20, choices) - ABIERTO, CERRADO
- `fecha_cierre`: DateTimeField (nullable) - Fecha y hora de cierre
- `cerrado_por`: ForeignKey(User, SET_NULL, nullable) - Usuario que cerró
- `observaciones`: TextField (opcional)

**Índices:**
- `['empresa', 'periodo']` - Búsqueda por empresa y periodo
- `['empresa', 'estado']` - Filtrado por estado
- `['fecha_inicio', 'fecha_fin']` - Búsqueda por rango de fechas

**Validaciones:**
- `periodo` único por empresa (unique_together)
- `fecha_inicio <= fecha_fin`

**Métodos:**
- `esta_cerrado()`: Retorna `True` si estado es `CERRADO`
- `contiene_fecha(fecha)`: Verifica si una fecha está dentro del rango del periodo

**Reglas de Negocio:**
- Una vez cerrado un periodo, no se pueden editar/anular documentos en ese rango de fechas
- Bloquea edición/anulación de Facturas y Gastos en periodos cerrados
- Usado por `verificar_periodo_cerrado()` en services para validaciones

---

### 3.5 CatalogoMaestroNIIF ✅ v2.61

**Ubicación:** `apps/tenant/contabilidad/models.py:19-147`

**Propósito:** Catálogo Maestro de Cuentas NIIF para Colombia (Single Source of Truth). Referencia oficial para el plan de cuentas contables.

**Campos Principales:**
- `codigo`: CharField(20, unique=True) - Código oficial NIIF Colombia
- `nombre`: CharField(200, editable=False) - Nombre oficial (auto-seteado)
- `nivel`: IntegerField(editable=False) - Nivel de la cuenta (1=Clase, 2=Grupo, 4=Cuenta, 6=Subcuenta)
- `naturaleza`: CharField(1, choices) - D (Débito/Deudora), C (Crédito/Acreedora) (auto-seteado)
- `activa`: BooleanField(default=True) - Indica si la cuenta está activa

**Índices:**
- `['codigo']` - Búsqueda por código
- `['nivel']` - Filtrado por nivel

**Validaciones:**
- `codigo` único (catálogo oficial)
- Solo se puede crear con códigos que existan en `CATALOGO_NIIF_COLOMBIA`
- Campos `nombre`, `nivel` y `naturaleza` son auto-seteados desde el catálogo oficial

**Métodos:**
- `get_tipo_cuenta()`: Determina el tipo (ACTIVO, PASIVO, PATRIMONIO, INGRESO, GASTO, COSTO) basado en el primer dígito del código

**Auto-Seteo (Model.save):**
```python
def save(self, *args, **kwargs):
    """
    Auto-setear nombre, nivel y naturaleza desde CATALOGO_NIIF_COLOMBIA.
    Solo se requiere el campo 'codigo' al crear.
    """
    from apps.tenant.contabilidad.choices.choices import CATALOGO_NIIF_COLOMBIA
    
    # Buscar código en catálogo oficial
    cuenta_catalogo = buscar_en_catalogo(self.codigo)
    if not cuenta_catalogo:
        raise ValueError(f"El código '{self.codigo}' no existe en CATALOGO_NIIF_COLOMBIA")
    
    # Auto-setear campos
    self.nombre = cuenta_catalogo[1]
    self.nivel = cuenta_catalogo[2]
    self.naturaleza = cuenta_catalogo[3]
    
    super().save(*args, **kwargs)
```

**Política:**
- Cada tenant tiene su propia copia del catálogo maestro
- Permite que cada tenant personalice su plan de cuentas anclado al estándar NIIF
- Las `CuentaContable` pueden referenciar este catálogo mediante relación opcional

**Comando de Management:**
- `python manage.py poblar_catalogo_niif`: Puebla el catálogo desde `CATALOGO_NIIF_COLOMBIA`
- Elimina registros existentes y recrea desde el catálogo oficial
- Útil para inicializar o actualizar el catálogo maestro

---

## 4. Capa de API

### 4.1 ViewSets

**Ubicación:** `apps/tenant/contabilidad/api/viewsets.py`

#### CuentaContableViewSet

**Base:** `BaseTenantViewSet`  
**Permisos:** `IsAuthenticated, IsTenantAdminOrReadOnly`  
**Paginación:** `StandardResultsSetPagination`  
**Filtros:** `tipo`, `activa`, `cuenta_padre`  
**Búsqueda:** `codigo`, `nombre`, `descripcion`  
**Ordenamiento:** `codigo`, `nombre`, `tipo`

**Endpoints:**
- `GET /api/v1/contabilidad/cuentas-contables/` - Lista
- `GET /api/v1/contabilidad/cuentas-contables/{id}/` - Detalle
- `POST /api/v1/contabilidad/cuentas-contables/` - Crear (⚠️ ENFORCED: Solo STAFF/ADMIN)
- `PUT /api/v1/contabilidad/cuentas-contables/{id}/` - Actualizar (⚠️ ENFORCED: Solo STAFF/ADMIN)
- `PATCH /api/v1/contabilidad/cuentas-contables/{id}/` - Actualizar parcial (⚠️ ENFORCED: Solo STAFF/ADMIN)
- `DELETE /api/v1/contabilidad/cuentas-contables/{id}/` - Eliminar (⚠️ ENFORCED: Solo STAFF/ADMIN)
- `POST /api/v1/contabilidad/cuentas-contables/dt/cuentas-contables/` - DataTables server-side

**QuerySet Optimizado:**
```python
def get_queryset(self):
    if self.action == "list":
        return qs_cuenta_list().order_by('codigo')  # Usa CUENTA_LIST_FIELDS
    elif self.action == "retrieve":
        return qs_cuenta_detail()  # Usa CUENTA_DETAIL_FIELDS
    else:
        return CuentaContable.objects.all()  # Para create/update/delete
```

**ENFORCED MODE:**
- `_check_enforced_mode()` verifica permisos antes de mutaciones
- No-staff recibe `405 Method Not Allowed` con mensaje descriptivo

#### AsientoContableViewSet

**Base:** `BaseTenantViewSet`  
**Permisos:** `IsAuthenticated, IsTenantAdminOrReadOnly`  
**Paginación:** `StandardResultsSetPagination`  
**Filtros:** `estado`, `fecha`  
**Búsqueda:** `numero`, `descripcion`  
**Ordenamiento:** `fecha`, `numero`, `total_debe`, `total_haber`, `created_at`

**Endpoints:**
- `GET /api/v1/contabilidad/asientos-contables/` - Lista
- `GET /api/v1/contabilidad/asientos-contables/{id}/` - Detalle
- `POST /api/v1/contabilidad/asientos-contables/` - Crear (⚠️ ENFORCED: Solo STAFF/ADMIN)
- `PUT /api/v1/contabilidad/asientos-contables/{id}/` - Actualizar (⚠️ ENFORCED: Solo STAFF/ADMIN)
- `PATCH /api/v1/contabilidad/asientos-contables/{id}/` - Actualizar parcial (⚠️ ENFORCED: Solo STAFF/ADMIN)
- `DELETE /api/v1/contabilidad/asientos-contables/{id}/` - Eliminar (⚠️ ENFORCED: Solo STAFF/ADMIN)
- `POST /api/v1/contabilidad/asientos-contables/{id}/aprobar/` - Aprobar asiento (✅ v2.60: Análisis detallado de cuadratura)
- `GET /api/v1/contabilidad/asientos-contables/balance-prueba/` - ✅ v2.60 Fase 3: Balance de Prueba
- `GET /api/v1/contabilidad/asientos-contables/render-offcanvas/crear/` - ✅ v2.60: HTMX Offcanvas creación
- `GET /api/v1/contabilidad/asientos-contables/render-offcanvas/detalle/{id}/` - ✅ v2.60: HTMX Offcanvas detalle
- `GET /api/v1/contabilidad/asientos-contables/render-offcanvas/cargar-desde-documentos/` - ✅ v2.60: HTMX Asistente documentos
- `GET /api/v1/contabilidad/asientos-contables/documentos-sin-asiento/` - ✅ v2.60: Lista documentos sin asiento
- `POST /api/v1/contabilidad/asientos-contables/crear-desde-documentos/` - ✅ v2.60: Crear asientos desde documentos
- `POST /api/v1/contabilidad/asientos-contables/dt/asientos-contables/` - ⚠️ DEPRECATED: DataTables server-side

**QuerySet Optimizado:**
```python
def get_queryset(self):
    if self.action == "list":
        return qs_asiento_list().order_by('-fecha', '-numero')  # Usa ASIENTO_LIST_FIELDS
    elif self.action == "retrieve":
        return qs_asiento_detail()  # Usa ASIENTO_DETAIL_FIELDS con prefetch_related
    else:
        return AsientoContable.objects.all()
```

**Acciones Personalizadas:**

**aprobar()** ✅ v2.60 Fase 3 - Análisis Detallado de Cuadratura:
```python
@action(detail=True, methods=['post'], url_path='aprobar')
def aprobar(self, request, pk=None):
    """
    Aprueba un asiento con análisis detallado de cuadratura.
    Retorna 422 con estructura detallada para error_injector.js si no cuadra.
    """
    asiento = self.get_object()
    
    # Validar movimientos
    if not asiento.movimientos.exists():
        return Response({
            'error': 'asiento_sin_movimientos',
            'message': 'El asiento debe tener al menos un movimiento...',
            'detalles': {...}
        }, status=422)
    
    # Análisis detallado de cuadratura
    diferencia = float(asiento.total_debe) - float(asiento.total_haber)
    if abs(diferencia) > 0.01:
        # Detecta cuentas problemáticas, tipo de desbalance, sugerencias
        return Response({
            'error': 'asiento_no_cuadrado',
            'message': 'El asiento no está cuadrado...',
            'detalles': {
                'total_debe': str(asiento.total_debe),
                'total_haber': str(asiento.total_haber),
                'diferencia_absoluta': str(abs(diferencia)),
                'tipo_desbalance': 'falta_credito' | 'falta_debito',
                'valor_faltante': str(abs(diferencia)),
                'cuentas_problematicas': [...],
                'sugerencia': '...'
            }
        }, status=422)
    
    asiento.estado = 'APROBADO'
    asiento.save()
    return Response(serializer.data)
```

**balance_prueba()** ✅ v2.60 Fase 3:
```python
@action(detail=False, methods=['get'], url_path='balance-prueba')
def balance_prueba(self, request):
    """
    Genera Balance de Prueba agrupado por CuentaContable.codigo.
    Query params: fecha_desde, fecha_hasta, empresa_id
    """
    balance = get_balance_prueba(...)
    return Response(balance, status=200)
```

**render_offcanvas_crear()** ✅ v2.60:
```python
@action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], 
        url_path='render-offcanvas/crear')
def render_offcanvas_crear(self, request):
    """Endpoint HTMX para cargar offcanvas de creación"""
    return Response({}, template_name='tenant/core/contabilidad/partials/asiento_offcanvas_form.html')
```

**render_offcanvas_cargar_desde_documentos()** ✅ v2.60:
```python
@action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], 
        url_path='render-offcanvas/cargar-desde-documentos')
def render_offcanvas_cargar_desde_documentos(self, request):
    """
    Endpoint HTMX para cargar offcanvas de selección de documentos.
    ⚠️ v2.60 Fase 3: Asistente de Selección - Lista Facturas y Gastos sin asiento
    """
    return Response({}, template_name='tenant/core/contabilidad/partials/asiento_offcanvas_cargar_desde_docs.html')
```

**documentos_sin_asiento()** ✅ v2.60:
```python
@action(detail=False, methods=['get'], url_path='documentos-sin-asiento')
def documentos_sin_asiento(self, request):
    """
    Lista Facturas y Gastos que no tienen asiento contable asociado.
    Query params: tipo (facturas/gastos), estado
    """
    # Usa select_related para Zero Waste
    return Response({'facturas': [...], 'gastos': [...]})
```

**crear_desde_documentos()** ✅ v2.60:
```python
@action(detail=False, methods=['post'], url_path='crear-desde-documentos')
def crear_desde_documentos(self, request):
    """
    Crea asientos contables desde documentos seleccionados.
    Body: {"facturas": [1, 2], "gastos": [3, 4]}
    """
    # Usa materializar_asiento_desde_factura/gasto con idempotencia
    return Response({'asientos_creados': [...]})
```

#### MovimientoContableViewSet

**Base:** `viewsets.ModelViewSet`  
**Permisos:** `IsAuthenticated`  
**Paginación:** `StandardResultsSetPagination`  
**Filtros:** `asiento`, `cuenta`  
**Búsqueda:** `descripcion`, `cuenta__nombre`  
**Ordenamiento:** `asiento`, `orden`, `debe`, `haber`

**Endpoints:**
- `GET /api/v1/contabilidad/movimientos-contables/` - Lista
- `GET /api/v1/contabilidad/movimientos-contables/{id}/` - Detalle
- `POST /api/v1/contabilidad/movimientos-contables/` - Crear
- `PUT /api/v1/contabilidad/movimientos-contables/{id}/` - Actualizar
- `PATCH /api/v1/contabilidad/movimientos-contables/{id}/` - Actualizar parcial
- `DELETE /api/v1/contabilidad/movimientos-contables/{id}/` - Eliminar

**QuerySet Optimizado:**
```python
def get_queryset(self):
    list_fields = ('id', 'asiento', 'cuenta', 'orden', 'debe', 'haber', 'descripcion')
    if self.action == "list":
        return MovimientoContable.objects.only(*list_fields).select_related('cuenta')
    elif self.action == "retrieve":
        return MovimientoContable.objects.only(*list_fields).select_related('cuenta')
    else:
        return MovimientoContable.objects.all()
```

#### CatalogoMaestroNIIFViewSet ✅ v2.61

**Base:** `BaseTenantViewSet`  
**Permisos:** `IsAuthenticated, IsTenantAdminOrReadOnly`  
**Paginación:** `StandardResultsSetPagination`  
**Filtros:** `nivel`, `naturaleza`, `activa`  
**Búsqueda:** `codigo`, `nombre`  
**Ordenamiento:** `codigo`, `nombre`, `nivel`

**Endpoints:**
- `GET /api/v1/contabilidad/catalogo-niif/` - Lista del catálogo
- `GET /api/v1/contabilidad/catalogo-niif/{id}/` - Detalle de cuenta del catálogo
- `POST /api/v1/contabilidad/catalogo-niif/` - Crear cuenta (⚠️ ENFORCED: Solo ADMIN, solo requiere `codigo`)
- `GET /api/v1/contabilidad/catalogo-niif/por-nivel/{nivel}/` - ✅ v2.61: Filtra por nivel (1, 2, 4, 6)
- `GET /api/v1/contabilidad/catalogo-niif/buscar-por-tipo/?tipo=ACTIVO` - ✅ v2.61: Busca por tipo de cuenta

**QuerySet Optimizado:**
```python
def get_queryset(self):
    if self.action == "list":
        return CatalogoMaestroNIIF.objects.only(
            'id', 'codigo', 'nombre', 'nivel', 'naturaleza', 'activa'
        ).order_by('codigo')
    elif self.action == "retrieve":
        return CatalogoMaestroNIIF.objects.prefetch_related('cuentas_vinculadas')
    else:
        return CatalogoMaestroNIIF.objects.all()
```

**Acciones Personalizadas:**

**por_nivel()** ✅ v2.61:
```python
@action(detail=False, methods=['get'], url_path='por-nivel/(?P<nivel>[0-9]+)')
def por_nivel(self, request, nivel=None):
    """
    Filtra cuentas del catálogo por nivel.
    GET /api/v1/contabilidad/catalogo-niif/por-nivel/1/  - Nivel 1 (Clases)
    GET /api/v1/contabilidad/catalogo-niif/por-nivel/4/  - Nivel 4 (Cuentas)
    """
    queryset = self.get_queryset().filter(nivel=int(nivel))
    return Response(serializer.data)
```

**buscar_por_tipo()** ✅ v2.61:
```python
@action(detail=False, methods=['get'], url_path='buscar-por-tipo')
def buscar_por_tipo(self, request):
    """
    Busca cuentas del catálogo NIIF filtradas por tipo de cuenta.
    Query params: tipo (ACTIVO, PASIVO, PATRIMONIO, INGRESO, GASTO, COSTO), search, nivel
    """
    # Mapea tipo a primer dígito del código
    tipo_map = {'ACTIVO': '1', 'PASIVO': '2', ...}
    queryset = self.get_queryset().filter(codigo__startswith=primer_digito, activa=True)
    return Response(serializer.data)
```

**create()** - Auto-Seteo:
```python
def create(self, request, *args, **kwargs):
    """
    Crea una nueva cuenta en el catálogo NIIF.
    ⚠️ AUTO-SETEO: Solo se requiere el campo 'codigo'.
    Los campos nombre, nivel y naturaleza se auto-completan desde CATALOGO_NIIF_COLOMBIA.
    
    Body: {"codigo": "1110"}
    Response: {"id": 1, "codigo": "1110", "nombre": "BANCOS", "nivel": 4, "naturaleza": "D", ...}
    """
    # El método save() del modelo se encarga del auto-seteo
    # Si el código no existe en CATALOGO_NIIF_COLOMBIA, lanza ValueError
```

---

### 4.2 Serializers

**Ubicación:** `apps/tenant/contabilidad/api/serializers.py`

**Alineación con Service Layer:**
- Serializers usan `CUENTA_LIST_FIELDS`, `CUENTA_DETAIL_FIELDS`, `ASIENTO_LIST_FIELDS`, `ASIENTO_DETAIL_FIELDS` del service
- Separación ListSerializer vs DetailSerializer (Normativa SINTEL)

#### CuentaContableListSerializer
- **Campos:** `CUENTA_LIST_FIELDS` = `id`, `uuid`, `codigo`, `nombre`, `tipo`, `activa`, `created_at`
- **Read-only:** `id`, `created_at`

#### CuentaContableDetailSerializer
- **Campos:** `CUENTA_DETAIL_FIELDS` = `id`, `uuid`, `codigo`, `nombre`, `tipo`, `descripcion`, `cuenta_padre`, `activa`, `created_at`
- **Read-only:** `id`, `created_at`

#### AsientoContableListSerializer
- **Campos:** `ASIENTO_LIST_FIELDS` = `id`, `uuid`, `numero`, `fecha`, `descripcion`, `estado`, `total_debe`, `total_haber`, `created_at`
- **Read-only:** `id`, `total_debe`, `total_haber`, `created_at`

#### AsientoContableDetailSerializer
- **Campos:** `ASIENTO_DETAIL_FIELDS` + `movimientos` (nested)
- **Read-only:** `id`, `total_debe`, `total_haber`, `created_at`, `updated_at`
- **Validación:** Verifica que `debe == haber` si estado es APROBADO

#### MovimientoContableListSerializer / DetailSerializer
- **Campos:** `id`, `asiento`, `cuenta`, `cuenta_nombre`, `cuenta_codigo`, `orden`, `debe`, `haber`, `descripcion`
- **Read-only:** `id`

#### CatalogoMaestroNIIFListSerializer ✅ v2.61
- **Campos:** `id`, `codigo`, `nombre`, `nivel`, `naturaleza`, `activa`
- **Read-only:** `id`

#### CatalogoMaestroNIIFDetailSerializer ✅ v2.61
- **Campos:** `id`, `codigo`, `nombre`, `nivel`, `naturaleza`, `activa`, `created_at`, `cuentas_vinculadas` (nested)
- **Read-only:** `id`, `nombre`, `nivel`, `naturaleza`, `created_at`
- **Método:** `get_tipo_cuenta()` - Calcula tipo basado en primer dígito del código

#### CatalogoMaestroNIIFNestedSerializer ✅ v2.61
- **Uso:** Serializer anidado usado en `CuentaContableDetailSerializer` para mostrar referencia NIIF
- **Campos:** `id`, `codigo`, `nombre`, `nivel`, `naturaleza`

---

### 4.3 URLs

**Ubicación:** `apps/tenant/contabilidad/api/urls.py`

**Router DRF:**
```python
router = DefaultRouter(trailing_slash=True)
router.register(r'cuentas-contables', CuentaContableViewSet, basename='cuenta-contable')
router.register(r'asientos-contables', AsientoContableViewSet, basename='asiento-contable')
router.register(r'movimientos-contables', MovimientoContableViewSet, basename='movimiento-contable')
router.register(r'catalogo-niif', CatalogoMaestroNIIFViewSet, basename='catalogo-niif')  # ✅ v2.61
```

**Base URL:** `/api/v1/contabilidad/` (definido en `config/api_urls.py`)

---

## 5. Capa de Servicios

### 5.1 Service Layer Principal

**Ubicación:** `apps/tenant/contabilidad/services.py`

**Propósito:** Define `LIST_FIELDS` y `DETAIL_FIELDS` para alineación Serializers ↔ Services ↔ UI, y funciones `qs_*()` optimizadas.

**Campos Definidos:**
```python
CUENTA_LIST_FIELDS = ("id", "uuid", "codigo", "nombre", "tipo", "activa", "created_at")
CUENTA_DETAIL_FIELDS = ("id", "uuid", "codigo", "nombre", "tipo", "descripcion", "cuenta_padre", "activa", "created_at")

ASIENTO_LIST_FIELDS = ("id", "uuid", "numero", "fecha", "descripcion", "estado", "total_debe", "total_haber", "created_at")
ASIENTO_DETAIL_FIELDS = ("id", "uuid", "numero", "fecha", "descripcion", "estado", "total_debe", "total_haber", "factura", "created_at", "updated_at")
```

**Funciones QuerySet:**
- `qs_cuenta_list()`: `CuentaContable.objects.only(*CUENTA_LIST_FIELDS)`
- `qs_cuenta_detail()`: `CuentaContable.objects.select_related("cuenta_padre").only(*CUENTA_DETAIL_FIELDS)`
- `qs_asiento_list()`: `AsientoContable.objects.only(*ASIENTO_LIST_FIELDS)`
- `qs_asiento_detail()`: `AsientoContable.objects.select_related("factura").prefetch_related("movimientos").only(*ASIENTO_DETAIL_FIELDS)`

**Funciones de Reportes y Validación** ✅ v2.60 Fase 3:
- `get_balance_prueba(empresa_id, fecha_desde, fecha_hasta)`: Genera Balance de Prueba agrupado por cuenta
  - Filtra solo asientos APROBADOS o CERRADOS
  - Agrupa movimientos por `CuentaContable.codigo`
  - Calcula totales (debe, haber, saldo) por cuenta
  - Retorna estructura JSON con cuentas y totales generales

- `verificar_periodo_cerrado(fecha, empresa_id)`: Verifica si una fecha está en periodo cerrado
  - Retorna `(bool, str | None)`: `(True, "2024-01")` si está cerrado, `(False, None)` si está abierto
  - Usado para validar inmutabilidad de documentos en periodos cerrados

---

### 5.2 Services Modulares

#### cuentas_service.py

**Funciones:**
- `list_cuentas(filters, ordering, page, page_size)` - Lista paginada con filtros
- `create_cuenta(data)` - Crea cuenta con validaciones (código único, tipo válido)
- `update_cuenta(cuenta_id, data)` - Actualiza cuenta con validaciones
- `delete_cuenta(cuenta_id)` - Elimina cuenta

**Validaciones:**
- Código único por tenant
- Tipo debe ser válido (ACTIVO, PASIVO, PATRIMONIO, INGRESO, GASTO)
- Campos requeridos no vacíos

#### asientos_service.py ✅ v2.60 Fase 3

**Funciones:**
- `list_asientos(filters, ordering, page, page_size)` - Lista paginada con filtros
- `create_asiento(data)` - Crea asiento con validaciones (número único, estado válido)
- `update_asiento(asiento_id, data)` - Actualiza asiento con validaciones
- `aprobar_asiento(asiento_id)` - Aprueba asiento si `total_debe == total_haber`
- `delete_asiento(asiento_id)` - Elimina asiento
- `materializar_asiento_desde_factura(factura)` - ✅ v2.60: Crea asiento automático desde factura aceptada
- `materializar_asiento_desde_gasto(gasto)` - ✅ v2.60: Crea asiento automático desde gasto activo

**Validaciones:**
- Número único por tenant
- Estado debe ser válido (BORRADOR, APROBADO, CERRADO)
- Aprobación requiere cuadratura (`debe == haber`)

**Materialización Automática** ✅ v2.60 Fase 3 - "Contabilidad Invisible":
- **MAPEO_CUENTAS**: Diccionario con mapeo automático de cuentas (estilo Siigo Contador)
  - `VENTA`: Clientes (1305), Ingresos (4135), IVA (2408)
  - `COMPRA`: Compras (61xx), Proveedores (2335), IVA (2408)
  - `GASTO`: Gastos (51xx), Proveedores (2335), ReteFuente (2365), ReteICA (2368)
- **Idempotencia**: Verifica si ya existe asiento para el documento antes de crear
- **Hooks Automáticos**:
  - `facturas/services.py`: Llama `materializar_asiento_desde_factura()` cuando factura se acepta
  - `gastos/api/viewsets.py`: Llama `materializar_asiento_desde_gasto()` cuando gasto se crea activo
- **Fallback Inteligente**: Si no encuentra cuenta por código exacto, busca por prefijo o tipo

#### movimientos_service.py

**Funciones:**
- `list_movimientos(filters, ordering, page, page_size)` - Lista paginada con filtros
- `create_movimiento(data)` - Crea movimiento con validaciones y actualiza totales del asiento
- `update_movimiento(movimiento_id, data)` - Actualiza movimiento y recalcula totales
- `delete_movimiento(movimiento_id)` - Elimina movimiento y recalcula totales

**Validaciones:**
- No puede tener débito y crédito simultáneamente
- Debe tener al menos uno mayor a cero
- Asiento y cuenta deben existir

**Actualización Automática:**
- Al crear/actualizar/eliminar movimiento, recalcula `total_debe` y `total_haber` del asiento

---

## 6. Capa de Frontend

### 6.1 JavaScript Modules

#### contabilidad.page.js (OLA 3 - DataTables)

**Ubicación:** `apps/tenant/core/static/core/js/contabilidad/contabilidad.page.js`

**Tecnología:** DataTables client-side  
**Dependencias:** `Routes`, `DataTablesUtils`, `DOMUtils`, `API_HELPERS`, `CRUD`

**Funcionalidad:**
- Inicializa dos tablas: Cuentas y Asientos
- Usa `Routes.get('contabilidad')` para descubrir URLs
- `DataTablesUtils.initServerSide` para inicialización
- CRUD completo con modales

**Estado:**
- ⚠️ OLA 3 (legacy) - Migración a Tabulator pendiente

---

#### cuentas.page.js (v3.3 - Tabulator) ✅ v2.61

**Ubicación:** `apps/tenant/core/static/core/js/contabilidad/cuentas.page.js`

**Tecnología:** Tabulator (TabulatorFactory)  
**Dependencias:** `TabulatorFactory`, `Routes`, `http()`, `DOMUtils`, `UIManager`

**Funcionalidad:**
- Tabla Tabulator para listado de cuentas
- CRUD completo con modales Bootstrap
- Validaciones frontend
- Integración con `error_injector.js`
- ✅ v2.61: Eliminación con manejo de errores mejorado
- ✅ v2.61: Validación y normalización de IDs
- ✅ v2.61: Logs de depuración para diagnóstico

**API Endpoint:** `/api/v1/contabilidad/cuentas-contables/`

**Estado:**
- ✅ v3.3 - Migrado a Tabulator
- ✅ Usa TabulatorFactory (The Engine)
- ✅ v2.61 - Fix eliminación: Detección inteligente de ID/UUID en backend
- ✅ v2.61 - Fix UI: Manejo de errores 422 con mensajes de validación

---

#### asientos.page.js (v2.37 - DataTables) ⚠️ Legacy

**Ubicación:** `apps/tenant/core/static/core/js/contabilidad/asientos.page.js`

**Tecnología:** DataTables client-side  
**Dependencias:** `Routes`, `API_HELPERS`, `CRUD`

**Funcionalidad:**
- Tabla DataTables para listado de asientos
- CRUD completo con modales
- Acción "Aprobar" con validación de cuadratura
- Descubrimiento de URLs con `Routes.collectionUrl('contabilidad.asientos')`

**API Endpoint:** `/api/v1/contabilidad/asientos-contables/`

**Estado:**
- ⚠️ v2.37 - DataTables (DEPRECATED, reemplazado por asientos_main.js)

---

#### asientos_main.js ✅ v2.60 - Tabulator Factory

**Ubicación:** `apps/tenant/core/static/core/js/contabilidad/asientos_main.js`

**Tecnología:** Tabulator (TabulatorFactory v2.40)  
**Dependencias:** `TabulatorFactory`, `Routes`, `http()`, `DOMUtils`, `error_injector.js`

**Funcionalidad:**
- Tabla Tabulator con server-side pagination
- Columnas con formatters: moneda, fechas, estados, contador de movimientos
- Columna "Cuadratura" con badges visuales (verde=cuadrado, rojo=diferencia)
- Filtros: `estado` (default: BORRADOR), `cuadratura` (cuadrado/no_cuadrado)
- Event delegation para botones "Ver Detalle" y "Aprobar"
- Integración con `error_injector.js` para errores 422
- Función `handleAprobarAsiento()` con validación cliente y servidor
- Función `mostrarErrorCuadratura()` para mostrar errores detallados

**API Endpoint:** `/api/v1/contabilidad/asientos-contables/`

**Estado:**
- ✅ v2.60 - Migrado a Tabulator Factory
- ✅ Usa TabulatorFactory (The Engine)
- ✅ Lazy loading con `DOMUtils.onVisibleOnce()`

---

#### asientos_form.js ✅ v2.60 - Formulario con Cuadratura en Vivo

**Ubicación:** `apps/tenant/core/static/core/js/contabilidad/asientos_form.js`

**Tecnología:** Vanilla JavaScript + HTMX  
**Dependencias:** `error_injector.js`, API REST

**Funcionalidad:**
- Carga dinámica de cuentas contables desde API
- Gestión de filas de movimientos (agregar/eliminar)
- Cálculo en tiempo real de totales (débito/crédito)
- Panel de cuadratura con feedback visual
- Habilitación/deshabilitación de botón guardar según cuadratura
- Manejo de errores 422 con `error_injector.js`
- Validación de campos requeridos
- Formato de moneda en inputs

**Integración:**
- Cargado en `offcanvas_crear_asiento.html`
- Se inicializa automáticamente al cargar el offcanvas

**Estado:**
- ✅ v2.60 - Implementación completa

---

#### asientos_cargar_desde_docs.js ✅ v2.60 - Asistente de Selección

**Ubicación:** `apps/tenant/core/static/core/js/contabilidad/asientos_cargar_desde_docs.js`

**Tecnología:** Vanilla JavaScript + HTMX  
**Dependencias:** API REST, `error_injector.js`

**Funcionalidad:**
- Carga documentos sin asiento (Facturas y Gastos)
- Renderizado de tablas con checkboxes
- Selección múltiple con contadores
- Búsqueda en tiempo real
- Creación masiva de asientos
- Creación individual de asientos
- Manejo de errores y feedback visual

**Integración:**
- Cargado en `asiento_offcanvas_cargar_desde_docs.html`
- Endpoint: `GET /api/v1/contabilidad/asientos-contables/documentos-sin-asiento/`
- Endpoint: `POST /api/v1/contabilidad/asientos-contables/crear-desde-documentos/`

**Estado:**
- ✅ v2.60 - Implementación completa

---

### 6.2 Templates

**Ubicación:** `apps/tenant/core/templates/tenant/core/partials/contabilidad/`

**Archivos:**
- `list_cuentas.html` - Contenedor de tabla Tabulator para cuentas
- `list_asientos.html` - Contenedor de tabla DataTables para asientos
- `modals_cuentas.html` - Modales Bootstrap para CRUD de cuentas
- `modals_asientos.html` - Modales Bootstrap para CRUD de asientos
- `assets_cuentas.html` - Assets JavaScript para módulo cuentas
- `assets_asientos.html` - Assets JavaScript para módulo asientos

**Integración:**
- Cargados en `workspace.html` bajo tab `#tab-contabilidad`
- ✅ v2.60: Usan HTMX para interacciones dinámicas con offcanvas
- ✅ v2.60: Contenedor `#offcanvas-container-asientos` para inyección HTMX

**Templates HTMX** ✅ v2.60:
- `asiento_offcanvas_form.html`: Formulario de creación/edición con cuadratura en vivo
- `asiento_offcanvas_detalle.html`: Vista de solo lectura de asiento aprobado
- `asiento_offcanvas_cargar_desde_docs.html`: Asistente de selección de documentos (Facturas y Gastos sin asiento)

---

## 7. Flujos de Negocio

### 7.1 Flujo: Crear Cuenta Contable

```
1. Usuario hace clic en "Crear Cuenta" (frontend)
   ↓
2. Frontend abre modal con formulario
   ↓
3. Usuario completa: código, nombre, tipo, descripción, cuenta_padre (opcional)
   ↓
4. Frontend valida campos requeridos
   ↓
5. POST /api/v1/contabilidad/cuentas-contables/
   ↓
6. ViewSet.create() → _check_enforced_mode() (verifica STAFF/ADMIN)
   ↓
7. Serializer valida datos
   ↓
8. Model.save() → Validaciones de unicidad (código único)
   ↓
9. Response 201 Created con datos de la cuenta
   ↓
10. Frontend cierra modal y refresca tabla
```

### 7.2 Flujo: Crear Asiento Contable ✅ v2.61 - Actualizado

**⚠️ v2.60: Feature-Sliced Architecture - HTMX Offcanvas + Validación en Tiempo Real**

```
1. Usuario hace clic en "Crear Asiento" (workspace/#contabilidad → Asientos Contables)
   ↓
2. HTMX: GET /api/v1/contabilidad/asientos-contables/render-offcanvas/crear/
   ↓
3. Backend renderiza template: asiento_offcanvas_form.html
   ↓
4. HTMX inyecta HTML en #offcanvas-container-asientos
   ↓
5. asientos_form.js detecta htmx:afterSettle y muestra offcanvas
   ↓
6. configurarEventosFormulario() se ejecuta cuando offcanvas está visible
   ↓
7. Frontend carga cuentas contables desde API (cache en state.cuentas)
   ↓
8. Usuario completa formulario:
   - Número (opcional, se genera automáticamente si está vacío)
   - Fecha * (requerido, fecha por defecto = hoy)
   - Descripción * (requerido)
   - Estado (default: BORRADOR)
   ↓
9. Usuario hace clic en "Agregar Movimiento"
   ↓
10. agregarMovimiento() clona template-movimiento-row
   ↓
11. Se pobla select de cuentas desde state.cuentas
   ↓
12. Se agregan event listeners:
    - input-debe: Si debe > 0, limpiar haber y llamar actualizarTotales()
    - input-haber: Si haber > 0, limpiar debe y llamar actualizarTotales()
    - select-cuenta: Al cambiar, llamar actualizarTotales()
    - btn-eliminar-movimiento: Eliminar movimiento y actualizarTotales()
   ↓
13. actualizarTotales() se ejecuta en tiempo real:
    - Calcula total_debe y total_haber desde DOM
    - Actualiza estado de movimientos en state.movimientos
    - Calcula diferencia = |debe - haber|
    - Valida cuadratura (diferencia < 0.01)
    - Actualiza displays: total-debe-display, total-haber-display
    - Actualiza resumen: resumen-total-debe, resumen-total-haber, resumen-diferencia
    - Actualiza badge de estado: "Cuadrado" (verde) o "No cuadra" (rojo)
    - Valida que todos los movimientos tengan cuenta seleccionada
    - Habilita/deshabilita btn-guardar-asiento-crear:
      * HABILITADO si: cuadra && movimientos.length > 0 && todosTienenCuenta
      * DESHABILITADO si: !cuadra || movimientos.length === 0 || !todosTienenCuenta
   ↓
14. Usuario completa movimientos:
    - Selecciona cuenta contable (requerido)
    - Ingresa descripción (opcional)
    - Ingresa debe O haber (no ambos, no ambos en cero)
   ↓
15. Usuario hace clic en "Guardar Asiento" (solo habilitado si cuadra)
   ↓
16. guardar() ejecuta validaciones:
    - form.checkValidity() (HTML5 validation)
    - recolectarDatos() extrae datos del formulario y movimientos del DOM
    - Valida que haya movimientos (length > 0)
    - Valida cuadratura (calcularTotales() → cuadra === true)
   ↓
17. POST /api/v1/contabilidad/asientos-contables/
   Body: {
     "numero": "AS-001" | null,
     "fecha": "2024-12-19",
     "descripcion": "Descripción del asiento",
     "estado": "BORRADOR",
     "movimientos": [
       {
         "cuenta": 1,
         "descripcion": "Descripción movimiento",
         "debe": 1000.00,
         "haber": 0.00,
         "orden": 1
       },
       ...
     ]
   }
   ↓
18. AsientoContableViewSet.create():
    - _check_enforced_mode() → Verifica STAFF/ADMIN
    - Si no autorizado: Response 405 Method Not Allowed
    - Si autorizado: Delega a create_asiento(data)
   ↓
19. create_asiento() (Service Layer):
    a) Extrae movimientos_data del payload
    b) Valida que tenga movimientos (si está vacío → ValidationError)
    c) Valida estado (BORRADOR, APROBADO, CERRADO)
    d) Valida periodo cerrado:
       - Si fecha está en periodo cerrado → ValidationError
       - Usa verificar_periodo_cerrado(fecha, empresa_id)
    e) Obtiene empresa (SSoT):
       - Si no se proporciona, busca Empresa.objects.first()
       - Si no existe → ValidationError
    f) Crea asiento: AsientoContable.objects.create(**data)
    g) Crea movimientos en loop:
       - Valida que cada movimiento tenga cuenta
       - Valida que tenga debe O haber (no ambos, no ambos en cero)
       - Calcula total_debe y total_haber
       - Crea MovimientoContable.objects.create()
    h) Si estado == 'APROBADO':
       - Valida cuadratura: total_debe == total_haber
       - Si no cuadra → ValidationError con estructura para error_injector.js
    i) Actualiza asiento.total_debe y asiento.total_haber
    j) asiento.save()
    k) Retorna DTO con datos del asiento creado
   ↓
20. ViewSet.create() continúa:
    - Obtiene asiento completo con prefetch_related('movimientos__cuenta')
    - Serializa con AsientoContableDetailSerializer
    - Response 201 Created con datos completos
   ↓
21. Frontend recibe respuesta:
    - Si 201: Cierra offcanvas, refresca tabla Tabulator, muestra feedback de éxito
    - Si 422: UIManager.handleError() muestra errores de validación
    - Si 405: Muestra error de permisos
    - Si 500: Muestra error genérico
   ↓
22. Tabla Tabulator se refresca automáticamente (nuevo asiento visible)
```

**⚠️ Validaciones Frontend (asientos_form.js):**
- ✅ Cuadratura en tiempo real (debe == haber con tolerancia 0.01)
- ✅ Todos los movimientos deben tener cuenta seleccionada
- ✅ Al menos un movimiento requerido
- ✅ Formulario HTML5 validation (fecha, descripción requeridos)
- ✅ Botón guardar se habilita/deshabilita dinámicamente

**⚠️ Validaciones Backend (create_asiento service):**
- ✅ ENFORCED MODE: Solo STAFF/ADMIN pueden crear
- ✅ Movimientos requeridos (no puede estar vacío)
- ✅ Estado válido (BORRADOR, APROBADO, CERRADO)
- ✅ Periodo no cerrado (verificar_periodo_cerrado)
- ✅ Empresa existe (SSoT por tenant)
- ✅ Cada movimiento tiene cuenta
- ✅ Cada movimiento tiene debe O haber (no ambos, no ambos en cero)
- ✅ Si estado=APROBADO: Cuadratura obligatoria (total_debe == total_haber)

**⚠️ Manejo de Errores:**
- ✅ 422 Unprocessable Entity: Errores de validación estructurados
- ✅ 405 Method Not Allowed: Usuario sin permisos
- ✅ 500 Internal Server Error: Errores inesperados con logging
- ✅ UIManager.handleError() muestra errores en contenedor de feedback

**⚠️ IDs Dinámicos v2.61:**
- ✅ Botón: `btn-guardar-asiento-crear` o `btn-guardar-asiento-editar`
- ✅ Formulario: `form-asiento-crear` o `form-asiento-editar`
- ✅ Offcanvas: `offcanvas-asiento-crear` o `offcanvas-asiento-editar`
- ✅ El código busca ambos IDs posibles para compatibilidad

**Componentes Clave del Flujo:**

1. **Frontend (asientos_form.js):**
   - `configurarEventosFormulario()`: Inicializa event listeners cuando offcanvas se muestra
   - `agregarMovimiento()`: Clona template y agrega fila de movimiento con validaciones
   - `actualizarTotales()`: Calcula totales en tiempo real y habilita/deshabilita botón guardar
   - `recolectarDatos()`: Extrae datos del formulario y movimientos del DOM
   - `guardar()`: Valida y envía POST request al backend
   - `calcularTotales()`: Calcula total_debe y total_haber desde inputs del DOM

2. **Backend (AsientoContableViewSet):**
   - `create()`: Endpoint POST que valida permisos y delega al servicio
   - `_check_enforced_mode()`: Verifica que usuario sea STAFF/ADMIN

3. **Service Layer (asientos_service.py):**
   - `create_asiento()`: Lógica de negocio completa con validaciones:
     * Validación de movimientos (no vacío)
     * Validación de estado
     * Validación de periodo cerrado
     * Validación de empresa (SSoT)
     * Validación de movimientos (cuenta, debe/haber)
     * Validación de cuadratura (si estado=APROBADO)
     * Creación transaccional (asiento + movimientos)

4. **Template (asiento_offcanvas_form.html):**
   - Formulario HTMX con validación HTML5
   - Tabla dinámica de movimientos
   - Template clonable para filas de movimiento
   - Displays de totales y cuadratura en tiempo real

**Validaciones en Tiempo Real (Frontend):**
- ✅ Cuadratura: Se calcula automáticamente al cambiar debe/haber
- ✅ Cuentas: Se valida que todos los movimientos tengan cuenta seleccionada
- ✅ Botón Guardar: Se habilita solo si cuadra, hay movimientos y todos tienen cuenta
- ✅ Feedback Visual: Badges y colores indican estado de cuadratura

**Manejo de Errores:**
- ✅ Frontend: UIManager.handleError() muestra errores estructurados
- ✅ Backend: ValidationError con estructura para error_injector.js
- ✅ Logs: Errores inesperados se registran en logger con stack trace

### 7.3 Flujo: Aprobar Asiento ✅ v2.60 Mejorado

```
1. Usuario selecciona asiento en estado 'BORRADOR' (Tabulator)
   ↓
2. Frontend verifica que total_debe == total_haber (validación previa)
   ↓
3. POST /api/v1/contabilidad/asientos-contables/{id}/aprobar/
   ↓
4. ViewSet.aprobar() → get_object()
   ↓
5. Validación: if not movimientos.exists() → 422 con error 'asiento_sin_movimientos'
   ↓
6. Validación: if total_debe != total_haber → 422 con error 'asiento_no_cuadrado'
   ↓
7. Análisis detallado: Detecta cuentas problemáticas, tipo de desbalance, sugerencias
   ↓
8. Si inválido: Response 422 con estructura detallada para error_injector.js
   ↓
9. error_injector.js muestra análisis detallado en UI
   ↓
10. Si válido: asiento.estado = 'APROBADO', save()
   ↓
11. Response 200 con datos del asiento aprobado
   ↓
12. Frontend refresca tabla Tabulator (estado cambia a 'APROBADO')
```

### 7.4 Flujo: Crear Asiento desde Documentos ✅ v2.60 Fase 3

```
1. Usuario hace clic en "Cargar desde Documentos" (workspace.html)
   ↓
2. HTMX: GET /api/v1/contabilidad/asientos-contables/render-offcanvas/cargar-desde-documentos/
   ↓
3. Se inyecta asiento_offcanvas_cargar_desde_docs.html en #offcanvas-container-asientos
   ↓
4. asientos_cargar_desde_docs.js se inicializa
   ↓
5. GET /api/v1/contabilidad/asientos-contables/documentos-sin-asiento/
   ↓
6. Backend lista Facturas y Gastos sin asiento (select_related para Zero Waste)
   ↓
7. Frontend renderiza tablas con checkboxes
   ↓
8. Usuario selecciona documentos y hace clic en "Crear Asientos"
   ↓
9. POST /api/v1/contabilidad/asientos-contables/crear-desde-documentos/
   Body: {"facturas": [1, 2], "gastos": [3, 4]}
   ↓
10. Backend itera documentos y llama materializar_asiento_desde_factura/gasto()
   ↓
11. Cada función verifica idempotencia (no crear duplicados)
   ↓
12. Se crean asientos con mapeo automático de cuentas (MAPEO_CUENTAS)
   ↓
13. Response 200 con lista de asientos creados
   ↓
14. Frontend cierra offcanvas y refresca tabla Tabulator
```

### 7.5 Flujo: Materialización Automática de Asientos ✅ v2.60 Fase 3 - "Contabilidad Invisible"

```
1. Usuario aprueba una Factura (estado: ACEPTADA)
   ↓
2. facturas/services.py → guardar_factura_desde_dto()
   ↓
3. Hook: Si estado == ACEPTADA, llama materializar_asiento_desde_factura(factura)
   ↓
4. asientos_service.py verifica idempotencia (¿ya existe asiento para esta factura?)
   ↓
5. Si no existe, crea AsientoContable con:
   - Número automático
   - Fecha de la factura
   - Descripción: "Venta - Factura #{numero}"
   - Estado: BORRADOR
   - Relación: factura = factura
   ↓
6. Mapeo automático de cuentas (MAPEO_CUENTAS):
   - DB 1305 (Clientes) = valor_total
   - CR 4135 (Ingresos) = subtotal
   - CR 2408 (IVA) = iva (si aplica)
   ↓
7. Se crean MovimientoContable automáticamente
   ↓
8. Asiento queda en BORRADOR para revisión del contador
   ↓
9. Mismo flujo para Gastos (gastos/api/viewsets.py → create())
```

---

## 8. Validaciones y Reglas

### 8.1 Validaciones de Modelo

#### CuentaContable
- ✅ `codigo` único por tenant (aislamiento automático)
- ✅ `tipo` debe ser uno de: ACTIVO, PASIVO, PATRIMONIO, INGRESO, GASTO
- ✅ `empresa` NO NULL (ENFORCED MODE v2.40)

#### AsientoContable
- ✅ `numero` único por tenant
- ✅ `estado` debe ser: BORRADOR, APROBADO, CERRADO
- ✅ Si `estado == 'APROBADO'`: `total_debe == total_haber` (validado en `save()`)
- ✅ `empresa` NO NULL (ENFORCED MODE v2.40)

#### MovimientoContable
- ✅ No puede tener `debe > 0` y `haber > 0` simultáneamente
- ✅ Debe tener al menos uno (`debe` o `haber`) mayor a cero
- ✅ `asiento` y `cuenta` deben existir

#### CatalogoMaestroNIIF ✅ v2.61
- ✅ `codigo` único (catálogo oficial)
- ✅ Solo se puede crear con códigos que existan en `CATALOGO_NIIF_COLOMBIA`
- ✅ Campos `nombre`, `nivel` y `naturaleza` son auto-seteados (editable=False)
- ✅ Si el código no existe en el catálogo oficial, lanza `ValueError` en `save()`

### 8.2 Validaciones de Service Layer

#### cuentas_service.py
- ✅ Código único (verifica antes de crear/actualizar)
- ✅ Nombre no vacío
- ✅ Tipo válido
- ✅ Longitud máxima de campos

#### asientos_service.py
- ✅ Número único (verifica antes de crear/actualizar)
- ✅ Estado válido
- ✅ Aprobación requiere cuadratura (`debe == haber`)

#### movimientos_service.py
- ✅ Asiento y cuenta existen
- ✅ Débito o crédito, pero no ambos
- ✅ Al menos uno mayor a cero

### 8.3 Validaciones de API Layer

#### ENFORCED MODE v2.40
- ✅ Solo STAFF/ADMIN pueden crear/editar/eliminar
- ✅ No-staff recibe `405 Method Not Allowed` con mensaje descriptivo
- ✅ Lectura (GET) permitida para todos los autenticados

---

## 9. Optimizaciones y Performance

### 9.1 QuerySet Optimization (Zero Waste)

**Principio:** Solo cargar campos necesarios para cada acción.

**Implementación:**
- `LIST`: Usa `only(*LIST_FIELDS)` - Solo campos para tabla
- `RETRIEVE`: Usa `only(*DETAIL_FIELDS)` + `select_related()` / `prefetch_related()`
- `CREATE/UPDATE/DELETE`: Usa `.all()` (necesita todos los campos para validaciones)

**Ejemplo:**
```python
# List: Solo 7 campos
qs_cuenta_list() → CuentaContable.objects.only('id', 'uuid', 'codigo', 'nombre', 'tipo', 'activa', 'created_at')

# Detail: 9 campos + relación
qs_cuenta_detail() → CuentaContable.objects.select_related('cuenta_padre').only(*CUENTA_DETAIL_FIELDS)
```

### 9.2 Índices de Base de Datos

**CuentaContable:**
- `['empresa']` - Optimización para FK a Empresa

**AsientoContable:**
- `['fecha']` - Búsqueda por fecha
- `['estado']` - Filtrado por estado
- `['empresa']` - Optimización para FK a Empresa

### 9.3 Paginación

**Estándar:** `StandardResultsSetPagination` (10 items por página, configurable)

**DataTables Server-Side:**
- Maneja `length=-1` (todos los registros sin paginación)
- Búsqueda, ordenamiento y paginación en servidor

---

## 10. Dependencias y Relaciones

### 10.1 Dependencias Internas

**apps/tenant/empresa:**
- `Empresa` (FK) - SSoT para datos de empresa del tenant
- `IsTenantAdmin` (permission) - Verificación de permisos

**apps/tenant/facturas:**
- `Factura` (FK opcional) - Relación opcional con facturas

### 10.2 Dependencias Externas

**Django REST Framework:**
- `viewsets.ModelViewSet`, `viewsets.ReadOnlyModelViewSet`
- `serializers.ModelSerializer`
- `DefaultRouter`
- `SessionAuthentication`
- `StandardResultsSetPagination`

**Django:**
- `models.Model`, `ForeignKey`, `DecimalField`, `CharField`, etc.
- `transaction.atomic`
- `django-tenants` (aislamiento automático)

### 10.3 Frontend Dependencies

**Tabulator:**
- `TabulatorFactory` (The Engine)
- Versión: 6.2.5

**DataTables:**
- Client-side DataTables (legacy)
- Versión: Depende de base.html

**Helpers Core:**
- `Routes` - Descubrimiento de URLs
- `DOMUtils` - Utilidades DOM
- `API_HELPERS` / `http()` - HTTP requests
- `CRUD` - Operaciones CRUD

---

## 11. Estado de Migración y Mejoras Pendientes

### 11.1 Migraciones Completadas

- ✅ **Cuentas**: Migrado a Tabulator (v3.3)
- ✅ **Asientos**: ✅ v2.60 - Migrado a Tabulator Factory (asientos_main.js)
- ✅ **API**: Migrado a DRF ViewSets
- ✅ **Service Layer**: Implementado con LIST_FIELDS/DETAIL_FIELDS
- ✅ **ENFORCED MODE**: Implementado (v2.40)
- ✅ **HTMX + Offcanvas**: ✅ v2.60 - Feature-Sliced Design implementado
- ✅ **Error Injector**: ✅ v2.60 - Integrado con análisis detallado de cuadratura
- ✅ **Materialización Automática**: ✅ v2.60 Fase 3 - "Contabilidad Invisible"
- ✅ **Balance de Prueba**: ✅ v2.60 Fase 3 - Endpoint implementado
- ✅ **PeriodoContable**: ✅ v2.60 Fase 3 - Modelo para inmutabilidad
- ✅ **CatalogoMaestroNIIF**: ✅ v2.61 - Catálogo oficial NIIF Colombia (SSoT)

### 11.2 Migraciones Pendientes

- ⚠️ **Templates Legacy**: Algunos templates aún en `apps/tenant/contabilidad/templates/` (no crítico)
- ⚠️ **Validación Periodo Cerrado**: Agregar validación en `FacturaViewSet.destroy()` y `GastoViewSet.anular()`

### 11.3 Mejoras Completadas ✅ v2.60

1. **✅ Migración Asientos a Tabulator:**
   - `asientos_main.js` usa `TabulatorFactory`
   - Eliminada dependencia de DataTables para asientos

2. **✅ HTMX Integration:**
   - Reemplazados modales Bootstrap con Offcanvas HTMX
   - Implementada carga dinámica de formularios
   - Templates dedicados: `asiento_offcanvas_form.html`, `asiento_offcanvas_detalle.html`, `asiento_offcanvas_cargar_desde_docs.html`

3. **✅ Error Injector:**
   - Integrado `error_injector.js` para manejo de errores 422
   - Análisis detallado de cuadratura con cuentas problemáticas y sugerencias
   - Mapeo específico para campos contables

4. **✅ Validaciones Frontend:**
   - Validaciones en tiempo real en `asientos_form.js`
   - Feedback visual para cuadratura de asientos (panel de cuadratura)
   - Cálculo automático de totales (débito/crédito)

5. **✅ Materialización Automática:**
   - Hooks en `facturas/services.py` y `gastos/api/viewsets.py`
   - Mapeo automático de cuentas (MAPEO_CUENTAS)
   - Idempotencia para evitar duplicados

6. **✅ Reportes:**
   - Endpoint `balance-prueba` con agrupación por cuenta
   - QuerySet optimizado con `select_related` y `prefetch_related`

---

## 12. Testing

### 12.1 Tests Existentes

**Ubicación:** `apps/tenant/contabilidad/tests/`

- `test_api_contabilidad.py` - Tests de API
- `test_templates.py` - Tests de templates

### 12.2 Cobertura Sugerida

- ✅ Tests de modelos (validaciones)
- ✅ Tests de servicios (lógica de negocio)
- ✅ Tests de ViewSets (API endpoints)
- ✅ Tests de serializers (validación de datos)
- ⚠️ Tests de frontend (pendiente)

---

## 13. Documentación Adicional

### 13.1 Referencias

- **Django REST Framework:** https://www.django-rest-framework.org/
- **Tabulator:** https://tabulator.info/
- **DataTables:** https://datatables.net/
- **django-tenants:** https://django-tenants.readthedocs.io/

### 13.2 Convenciones

- **UUID para lookup público:** No exponer PK interno en URLs
- **ENFORCED MODE:** Solo STAFF/ADMIN para mutaciones
- **Zero Waste:** Solo cargar campos necesarios
- **Service Layer Pattern:** Lógica de negocio en services/
- **API-First:** Endpoints REST como única fuente de verdad

---

## 14. Conclusión

La app `contabilidad` es un módulo completo y bien estructurado que implementa:

- ✅ **Arquitectura sólida:** Service Layer, API-First, Zero Waste
- ✅ **Validaciones robustas:** Modelo, Service, API
- ✅ **Optimizaciones:** QuerySets optimizados, índices de BD
- ✅ **Seguridad:** ENFORCED MODE, aislamiento multi-tenant
- ✅ **Feature-Sliced Design v2.60:** HTMX + Offcanvas, UI modular
- ✅ **Tabulator Factory v2.40:** Tablas modernas con server-side pagination
- ✅ **Contabilidad Invisible:** Materialización automática desde facturas/gastos
- ✅ **Error Injector:** Análisis detallado de cuadratura con feedback visual
- ✅ **Balance de Prueba:** Reportes optimizados con agrupación por cuenta
- ✅ **Periodos Contables:** Inmutabilidad de datos en periodos cerrados
- ✅ **Catálogo Maestro NIIF:** Referencia oficial NIIF Colombia con auto-seteo y validación estricta
- ✅ **Fix Eliminación Cuentas v2.61:** Detección inteligente ID/UUID, manejo de errores 422 mejorado

**Estado General:** ✅ **Producción Ready** - Todas las mejoras v2.60 y v2.61 implementadas

---

## 11. Correcciones v2.61

### 11.1 Fix Eliminación Cuentas Contables ✅ v2.61

**Problema:** 
- Error 404 al eliminar cuentas (ID None) - `BaseTenantViewSet` usa `lookup_field="uuid"` pero frontend envía IDs numéricos
- Mensajes de error 422 no se mostraban en frontend - `UIManager` no manejaba formato HTTP.js correctamente

**Solución:**
- ✅ **ViewSet:** Detección automática si identificador es numérico (pk) o UUID
- ✅ **UIManager:** Soporte para formato HTTP.js y extracción correcta de mensajes de arrays
- ✅ **Frontend:** Validación y normalización de IDs antes de enviar requests

**Archivos modificados:**
- `apps/tenant/contabilidad/api/viewsets.py` - Método `destroy()` con detección inteligente
- `apps/tenant/core/static/core/js/lib/ui-manager.js` - Soporte HTTP.js y arrays
- `apps/tenant/core/static/core/js/contabilidad/cuentas.page.js` - Validación de IDs

**Documentación completa:** Ver `documentacion/FIX_ELIMINACION_CUENTAS_CONTABLES.md`

### Mejoras v2.60 Implementadas

1. **✅ Fase 1: Fragmentación de UI (Feature-Sliced Design)**
   - Templates dedicados por función
   - Offcanvas HTMX en lugar de modales pesados

2. **✅ Fase 2: Implementación HTMX en Workspace**
   - Botones con atributos HTMX
   - Contenedor central para inyección de contenido

3. **✅ Fase 3: Módulo de Errores Inyectable**
   - `error_injector.js` con análisis detallado
   - Manejo específico de errores contables

4. **✅ Fase 4: Migración a Tabulator Factory v2.40**
   - `asientos_main.js` con Tabulator
   - Columnas con formatters y badges visuales

5. **✅ Fase 5: Contabilidad Invisible (Event-Driven)**
   - Materialización automática desde facturas/gastos
   - Mapeo automático de cuentas (MAPEO_CUENTAS)
   - Idempotencia para evitar duplicados

6. **✅ Fase 6: Interfaz de Auditoría Rápida**
   - Dashboard del contador (filtro BORRADOR)
   - Columna de cuadratura con validación visual

7. **✅ Fase 7: Modularización HTMX y Offcanvas**
   - Asistente de selección de documentos
   - Creación masiva de asientos

8. **✅ Fase 8: Error Injector Contable**
   - Análisis detallado de cuadratura
   - Detección de cuentas problemáticas
   - Sugerencias automáticas

9. **✅ Fase 9: Estándar SSoT para Reportes**
   - Endpoint `balance-prueba`
   - QuerySet optimizado con agrupación
   - Modelo `PeriodoContable` para inmutabilidad

10. **✅ Fase 10: Catálogo Maestro NIIF Colombia (v2.61)**

---

## 12. Correcciones v2.61 - Manejo de Errores y Validaciones

**Fecha:** Diciembre 2024  
**Versión:** v2.61

### 12.1 Error Injector Visual en Offcanvas ✅ v2.61

**Problema:** Los errores de validación solo se mostraban en la consola, no visualmente en el offcanvas.

**Solución Implementada:**

1. **Función Helper `mostrarErrorVisual()`** en `asientos_form.js`:
   - Busca contenedor de errores en el offcanvas activo
   - Crea contenedor dinámicamente si no existe
   - Muestra mensaje de error con formato HTML
   - Muestra campos faltantes en lista
   - Hace scroll automático al contenedor de errores

2. **Manejo de Errores 422**:
   - Intenta usar `ErrorHandler.show()` primero
   - Si no funciona, usa fallback visual
   - Muestra detalles adicionales (diferencia, sugerencias)
   - Muestra campos faltantes en lista

3. **Manejo de Otros Errores (500, 400, etc.)**:
   - También se muestran visualmente en el offcanvas
   - Fallback a `SintelFeedback` o `alert` si no se puede mostrar visualmente

4. **Limpieza de Errores**:
   - Al iniciar `guardar()`, se limpian errores previos
   - En `limpiarFormulario()`, se limpian los errores visuales
   - Usa `ErrorHandler.reset()` si está disponible

**Archivos Modificados:**
- `apps/tenant/core/static/core/js/contabilidad/asientos_form.js`
- `apps/tenant/core/static/core/js/error_injector.js`

---

### 12.2 Corrección Validador de Cuadratura ✅ v2.61

**Problema:** El validador de cuadratura en `guardar()` usaba `calcularTotales()` directamente, lo que podía causar discrepancias con la lógica que habilita/deshabilita el botón.

**Solución Implementada:**

1. **Validación Unificada**:
   - `guardar()` ahora usa `actualizarTotales()` para validar la cuadratura
   - Misma lógica que habilita/deshabilita el botón
   - Misma tolerancia: `diferencia <= 0.01`

2. **Logs de Depuración**:
   - Log antes de validar: muestra debe, haber, diferencia, cuadra y número de movimientos
   - Log de advertencia si no cuadra: bloquea el guardado
   - Log de éxito si cuadra: procede con el guardado

3. **Manejo de Errores Visual**:
   - Si no cuadra, muestra el error en el offcanvas
   - Muestra diferencia, total débito y total crédito
   - Hace scroll automático al contenedor de errores

**Archivos Modificados:**
- `apps/tenant/core/static/core/js/contabilidad/asientos_form.js`

---

### 12.3 Corrección Campo `numero` en Payload ✅ v2.61

**Problema:** El campo `numero` se enviaba incluso si estaba vacío, causando errores de validación en el backend.

**Solución Implementada:**

1. **Validación en Frontend**:
   - Solo se envía `numero` si tiene un valor válido (no vacío, no null)
   - Si está vacío, no se envía y el backend lo genera automáticamente

2. **Código:**
```javascript
// ⚠️ v2.61: Si numero está vacío o es null, no enviarlo (el backend lo generará automáticamente)
...(datos.numero && datos.numero.trim() ? { numero: datos.numero.trim() } : {}),
```

**Archivos Modificados:**
- `apps/tenant/core/static/core/js/contabilidad/asientos_form.js`

---

### 12.4 Manejo de Errores de Campos Específicos (DRF) ✅ v2.61

**Problema:** Los errores de validación de campos específicos en formato DRF (`{campo: [mensaje]}`) no se mostraban correctamente.

**Solución Implementada:**

1. **Detección de Errores de Campos Específicos**:
   - Detecta errores en formato DRF: `{campo: [mensaje1, mensaje2]}`
   - Construye mensaje detallado con todos los campos con errores
   - Muestra los campos en la lista de campos faltantes
   - Usa `mapearCampoALegible()` para nombres legibles

2. **Código en `error_injector.js`:**
```javascript
// ⚠️ v2.61: Manejo de errores de validación de campos específicos (formato DRF)
const camposConErrores = [];
if (response && typeof response === 'object') {
    Object.keys(response).forEach(campo => {
        if (Array.isArray(response[campo]) && response[campo].length > 0) {
            // Es un error de campo específico
            camposConErrores.push({
                campo: campo,
                campoLegible: mapearCampoALegible(campo),
                mensajes: response[campo],
                mensajeUnificado: response[campo].join(', ')
            });
        }
    });
}
```

**Archivos Modificados:**
- `apps/tenant/core/static/core/js/error_injector.js`

---

### 12.5 Corrección Manejo de Fecha en `create_asiento()` ✅ v2.61

**Problema:** Error `AttributeError: 'str' object has no attribute 'isoformat'` al intentar convertir la fecha en el DTO de retorno.

**Solución Implementada:**

1. **Actualización de `data['fecha']` después de la conversión**:
   - La fecha se convierte de string a `date` y se actualiza en `data['fecha']` antes de crear el asiento

2. **Manejo Seguro de Fecha en el DTO de Retorno**:
   - Se verifica si es string o date antes de llamar `isoformat()`
   - Se recarga el objeto desde la BD para asegurar el tipo correcto

3. **Código:**
```python
# ⚠️ v2.61: Actualizar data con el objeto date convertido
if isinstance(fecha, str):
    try:
        fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
        data['fecha'] = fecha
    except ValueError:
        raise ValidationError({
            'fecha': ['Formato de fecha inválido. Use YYYY-MM-DD.']
        })

# En el DTO de retorno:
asiento.refresh_from_db()
fecha_str = None
if asiento.fecha:
    if isinstance(asiento.fecha, str):
        # Si es string, convertir a date primero
        try:
            fecha_obj = datetime.strptime(asiento.fecha, '%Y-%m-%d').date()
            fecha_str = fecha_obj.isoformat()
        except (ValueError, AttributeError):
            fecha_str = str(asiento.fecha)
    else:
        # Si es date, usar isoformat() directamente
        fecha_str = asiento.fecha.isoformat()
```

**Archivos Modificados:**
- `apps/tenant/contabilidad/services/asientos_service.py`

---

### 12.6 Resumen de Correcciones v2.61

**Errores Corregidos:**
1. ✅ Errores de validación ahora se muestran visualmente en el offcanvas
2. ✅ Validador de cuadratura unificado con la lógica del botón
3. ✅ Campo `numero` solo se envía si tiene valor válido
4. ✅ Errores de campos específicos (DRF) se muestran correctamente
5. ✅ Manejo seguro de fecha en `create_asiento()`

**Mejoras Implementadas:**
- Función helper `mostrarErrorVisual()` para mostrar errores visualmente
- Logs de depuración para validación de cuadratura
- Detección automática de errores de campos específicos (DRF)
- Manejo robusto de tipos de fecha (string/date)

**Archivos Modificados:**
- `apps/tenant/core/static/core/js/contabilidad/asientos_form.js`
- `apps/tenant/core/static/core/js/error_injector.js`
- `apps/tenant/contabilidad/services/asientos_service.py`

**Estado:** ✅ **Todas las correcciones implementadas y probadas**
    - Modelo `CatalogoMaestroNIIF` como Single Source of Truth
    - Auto-seteo de campos desde `CATALOGO_NIIF_COLOMBIA`
    - ViewSet con endpoints especializados (`por-nivel`, `buscar-por-tipo`)
    - Comando de management para poblar catálogo
    - Integración con `CuentaContable` mediante relación opcional
    - Validación estricta: solo códigos oficiales del catálogo NIIF

---

### 12.7 Sincronización Completa del Módulo PeriodoContable ✅ v2.61

**Problema:** El módulo `PeriodoContable` estaba parcialmente implementado, causando errores de importación al intentar cargar las URLs de la API.

**Errores Encontrados:**
1. `ImportError: cannot import name 'qs_periodo_list' from 'apps.tenant.contabilidad.services'`
2. Faltaban serializers `PeriodoContableListSerializer` y `PeriodoContableDetailSerializer`
3. Orden incorrecto de importaciones en `viewsets.py`

**Solución Implementada:**

#### 1. Serializers de PeriodoContable Agregados

**Archivo:** `apps/tenant/contabilidad/api/serializers.py`

```python
class PeriodoContableListSerializer(serializers.ModelSerializer):
    """
    Serializer mínimo para listado de periodos contables.
    
    ⚠️ v2.61: Alineado con PERIODO_LIST_FIELDS del service.
    """
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    
    class Meta:
        model = PeriodoContable
        fields = list(PERIODO_LIST_FIELDS) + ['estado_display', 'empresa_nombre']
        read_only_fields = ['id', 'uuid', 'created_at']


class PeriodoContableDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo para detalle de periodo contable.
    
    ⚠️ v2.61: Alineado con PERIODO_DETAIL_FIELDS del service.
    """
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    cerrado_por_nombre = serializers.SerializerMethodField()
    
    class Meta:
        model = PeriodoContable
        fields = list(PERIODO_DETAIL_FIELDS) + ['estado_display', 'empresa_nombre', 'cerrado_por_nombre']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at']
    
    def get_cerrado_por_nombre(self, obj):
        """Retorna el nombre del usuario que cerró el periodo."""
        if obj.cerrado_por:
            return obj.cerrado_por.get_full_name() or obj.cerrado_por.username
        return None
```

#### 2. Corrección de Exportaciones en `services/__init__.py`

**Archivo:** `apps/tenant/contabilidad/services/__init__.py`

**Problema:** Las funciones `qs_periodo_list()` y `qs_periodo_detail()` estaban definidas en `services.py` pero no estaban re-exportadas en `services/__init__.py`, causando errores de importación.

**Solución:**
```python
# Re-exportar símbolos desde services.py
PERIODO_LIST_FIELDS = services_module.PERIODO_LIST_FIELDS  # ⚠️ v2.61
PERIODO_DETAIL_FIELDS = services_module.PERIODO_DETAIL_FIELDS  # ⚠️ v2.61
qs_periodo_list = services_module.qs_periodo_list  # ⚠️ v2.61
qs_periodo_detail = services_module.qs_periodo_detail  # ⚠️ v2.61

# Actualizar __all__
__all__ = [
    # ... otros exports ...
    'PERIODO_LIST_FIELDS', 'PERIODO_DETAIL_FIELDS',  # ⚠️ v2.61
    'qs_periodo_list', 'qs_periodo_detail',  # ⚠️ v2.61
    # ...
]
```

#### 3. Corrección de Orden de Importaciones

**Archivo:** `apps/tenant/contabilidad/api/viewsets.py`

**Problema:** El `logger` estaba definido antes de todas las importaciones, causando posibles problemas de orden.

**Solución:**
```python
import logging
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.permissions import IsTenantAdminOrReadOnly

logger = logging.getLogger(__name__)  # ✅ Después de todas las importaciones
```

#### 4. Verificación de Modelo PeriodoContable

**Archivo:** `apps/tenant/contabilidad/models.py`

**Verificado:**
- ✅ Campo `uuid` correctamente definido con `default=uuid.uuid4`
- ✅ Importación de `uuid` presente
- ✅ Migración `0009_periodocontable_uuid.py` existe

**Archivos Modificados:**
- `apps/tenant/contabilidad/api/serializers.py` - Serializers agregados
- `apps/tenant/contabilidad/services/__init__.py` - Exportaciones agregadas
- `apps/tenant/contabilidad/api/viewsets.py` - Orden de importaciones corregido

**Estado:** ✅ **Módulo PeriodoContable completamente sincronizado y funcional**

**Endpoints Disponibles:**
- `GET /api/v1/contabilidad/periodos-contables/` - Listado paginado
- `GET /api/v1/contabilidad/periodos-contables/{id}/` - Detalle
- `POST /api/v1/contabilidad/periodos-contables/` - Crear (solo STAFF/ADMIN)
- `PUT /api/v1/contabilidad/periodos-contables/{id}/` - Actualizar (solo STAFF/ADMIN)
- `DELETE /api/v1/contabilidad/periodos-contables/{id}/` - Eliminar (solo STAFF/ADMIN)
- `GET /api/v1/contabilidad/periodos-contables/render-offcanvas/crear/` - HTMX crear
- `GET /api/v1/contabilidad/periodos-contables/{id}/render-offcanvas/editar/` - HTMX editar
- `GET /api/v1/contabilidad/periodos-contables/{id}/render-offcanvas/detalle/` - HTMX detalle

---

### 12.8 Corrección de Compatibilidad IDs Numéricos vs UUIDs en AsientoContable ✅ v2.61

**Problema:** El frontend envía IDs numéricos (ej: `71`) en las URLs, pero `BaseTenantViewSet` usa `lookup_field="uuid"`, causando errores 404 al intentar obtener, editar o actualizar asientos contables.

**Errores Encontrados:**
1. `GET /api/v1/contabilidad/asientos-contables/71/` → 404 Not Found
2. `PUT /api/v1/contabilidad/asientos-contables/71/` → 404 Not Found
3. `AsientoContableViewSet.render_offcanvas_editar() got an unexpected keyword argument 'uuid'`
4. `ImportError: cannot import name 'verificar_periodo_cerrado' from 'apps.tenant.contabilidad.services'`
5. `AttributeError: 'str' object has no attribute 'isoformat'` en `update_asiento()`

**Solución Implementada:**

#### 1. Método `retrieve()` Sobrescrito

**Archivo:** `apps/tenant/contabilidad/api/viewsets.py`

**Problema:** El método `retrieve()` heredado de `BaseTenantViewSet` solo acepta UUIDs, pero el frontend envía IDs numéricos.

**Solución:**
```python
def retrieve(self, request, *args, **kwargs):
    """
    Sobrescribir retrieve para manejar tanto IDs numéricos como UUIDs.
    
    ⚠️ v2.61: BaseTenantViewSet usa lookup_field="uuid", pero el frontend envía IDs numéricos
    """
    try:
        asiento_identifier = kwargs.get('uuid') or kwargs.get('pk')
        
        if asiento_identifier:
            try:
                # Intentar convertir a entero (es un ID numérico)
                asiento_id = int(asiento_identifier)
                asiento = qs_asiento_detail().get(id=asiento_id)
            except (ValueError, TypeError):
                # Si no es numérico, intentar como UUID
                asiento = self.get_object()  # Esto usa lookup_field="uuid"
        
        serializer = self.get_serializer(asiento)
        return Response(serializer.data)
    except Exception as e:
        # Manejo de errores...
```

#### 2. Método `render_offcanvas_editar()` Corregido

**Archivo:** `apps/tenant/contabilidad/api/viewsets.py`

**Problema:** El método recibía `pk=None` pero DRF pasaba `uuid` en `kwargs`, causando un error de argumento inesperado.

**Solución:**
```python
@action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/editar')
def render_offcanvas_editar(self, request, **kwargs):
    """
    ⚠️ v2.61: BaseTenantViewSet usa lookup_field="uuid", pero el frontend envía IDs numéricos
    """
    try:
        asiento_identifier = kwargs.get('uuid') or kwargs.get('pk')
        # Manejo de IDs numéricos y UUIDs...
```

#### 3. Método `update()` Corregido

**Archivo:** `apps/tenant/contabilidad/api/viewsets.py`

**Problema:** El método usaba `kwargs.get('pk')` pero el valor venía en `kwargs['uuid']`, causando 404 al actualizar.

**Solución:**
```python
def update(self, request, *args, **kwargs):
    """
    ⚠️ v2.61: BaseTenantViewSet usa lookup_field="uuid", pero el frontend envía IDs numéricos
    """
    try:
        asiento_identifier = kwargs.get('uuid') or kwargs.get('pk')
        
        # Convertir identificador a ID numérico para el servicio
        asiento_id = None
        if asiento_identifier:
            try:
                asiento_id = int(asiento_identifier)
            except (ValueError, TypeError):
                # Si no es numérico, obtener el ID desde el objeto UUID
                asiento = self.get_object()
                asiento_id = asiento.id
        
        resultado = update_asiento(asiento_id, data)
        # ...
```

#### 4. Exportación de `verificar_periodo_cerrado`

**Archivo:** `apps/tenant/contabilidad/services/__init__.py`

**Problema:** La función `verificar_periodo_cerrado` estaba definida en `services.py` pero no estaba re-exportada en `services/__init__.py`, causando `ImportError` en `update_asiento()`.

**Solución:**
```python
# Re-exportar funciones de validación
verificar_periodo_cerrado = services_module.verificar_periodo_cerrado  # ⚠️ v2.61
get_balance_prueba = services_module.get_balance_prueba

__all__ = [
    # ...
    'verificar_periodo_cerrado',  # ⚠️ v2.61
    'get_balance_prueba',
]
```

#### 5. Corrección de Manejo de Fecha en `update_asiento()`

**Archivo:** `apps/tenant/contabilidad/services/asientos_service.py`

**Problema:** Después de actualizar el asiento, `asiento.fecha` podía ser un string en lugar de un objeto `date`, causando `AttributeError: 'str' object has no attribute 'isoformat'` al intentar formatear la fecha en el DTO de retorno.

**Solución:**
```python
# ⚠️ v2.61: Asegurar que fecha sea un objeto date antes de llamar isoformat()
# Recargar desde BD para asegurar que tenga el tipo correcto
asiento.refresh_from_db()
fecha_str = None
if asiento.fecha:
    if isinstance(asiento.fecha, str):
        # Si es string, convertir a date primero
        try:
            fecha_obj = datetime.strptime(asiento.fecha, '%Y-%m-%d').date()
            fecha_str = fecha_obj.isoformat()
        except (ValueError, AttributeError):
            fecha_str = str(asiento.fecha)
    else:
        # Si es date, usar isoformat() directamente
        fecha_str = asiento.fecha.isoformat()

return {
    # ...
    'fecha': fecha_str,
    # ...
}
```

**Archivos Modificados:**
- `apps/tenant/contabilidad/api/viewsets.py` - Métodos `retrieve()`, `render_offcanvas_editar()` y `update()` corregidos
- `apps/tenant/contabilidad/services/__init__.py` - Exportación de `verificar_periodo_cerrado` agregada
- `apps/tenant/contabilidad/services/asientos_service.py` - Manejo seguro de fecha en `update_asiento()`

**Estado:** ✅ **Compatibilidad completa entre IDs numéricos y UUIDs implementada**

**Endpoints Corregidos:**
- `GET /api/v1/contabilidad/asientos-contables/{id}/` - Ahora acepta IDs numéricos y UUIDs
- `PUT /api/v1/contabilidad/asientos-contables/{id}/` - Ahora acepta IDs numéricos y UUIDs
- `GET /api/v1/contabilidad/asientos-contables/{id}/render-offcanvas/editar/` - Ahora acepta IDs numéricos y UUIDs

---

**Última actualización:** Diciembre 2024  
**Versión del documento:** 2.61  
**Estado:** ✅ **Completo y Alineado con Implementación Actual**

**Correcciones recientes v2.61:**
- ✅ Template `asiento_offcanvas_cargar_desde_docs.html` creado en ubicación correcta (`tenant/core/contabilidad/partials/`)
- ✅ Todas las referencias a templates actualizadas con nombres correctos
- ✅ Documentación del endpoint `render_offcanvas_cargar_desde_documentos()` agregada
- ✅ **Error Injector Visual en Offcanvas:** Errores de validación ahora se muestran visualmente en el offcanvas
- ✅ **Corrección Validador de Cuadratura:** Validación unificada con la lógica del botón
- ✅ **Corrección Campo `numero`:** Solo se envía si tiene valor válido
- ✅ **Manejo de Errores DRF:** Errores de campos específicos se muestran correctamente
- ✅ **Corrección Manejo de Fecha:** Manejo seguro de fecha en `create_asiento()`
- ✅ **Sincronización Completa PeriodoContable:** Serializers, ViewSet, URLs y Services completamente integrados (ver sección 12.7)
- ✅ **Corrección Importaciones:** `qs_periodo_list` y `qs_periodo_detail` exportados correctamente en `services/__init__.py`
- ✅ **Compatibilidad IDs Numéricos vs UUIDs:** Métodos `retrieve()`, `render_offcanvas_editar()` y `update()` corregidos para manejar ambos tipos de identificadores (ver sección 12.8)
- ✅ **Exportación `verificar_periodo_cerrado`:** Función agregada a `services/__init__.py` para evitar ImportError
- ✅ **Manejo Seguro de Fecha en `update_asiento()`:** Corrección de `AttributeError: 'str' object has no attribute 'isoformat'`