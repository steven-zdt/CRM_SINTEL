# Auditoría Completa del Módulo de Gastos - Proyecto SINTEL v2.61.4

**Fecha de Auditoría:** 2026-03-12  
**Versión del Sistema:** v2.61.4  
**Módulo:** `apps/tenant/gastos`  
**Última actualización:** 2026-03-12

---

## 📋 Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura del Módulo](#arquitectura-del-módulo)
3. [Modelos de Datos](#modelos-de-datos)
4. [Capa de Servicios](#capa-de-servicios)
5. [Capa de API (DRF)](#capa-de-api-drf)
   - 5.0. [Core API Facade (v2.61.4)](#50-core-api-facade-v2614)
6. [Serializers](#serializers)
7. [Frontend](#frontend)
8. [Flujos Completos](#flujos-completos)
9. [Reglas de Negocio Críticas](#reglas-de-negocio-críticas)
10. [Inmutabilidad y Seguridad](#inmutabilidad-y-seguridad)
11. [Endpoints y URLs](#endpoints-y-urls)
12. [Admin Interface](#admin-interface)
13. [Choices y Configuración](#choices-y-configuración)
14. [Optimizaciones y Performance](#optimizaciones-y-performance)
15. [Casos de Uso](#casos-de-uso)
16. [Flujo Completo: Workspace → Core API → Models](#16-flujo-completo-workspace--core-api--models)
17. [Conclusión](#17-conclusión)
18. [Notas de Versión](#18-notas-de-versión)

---

## 1. Resumen Ejecutivo

### 1.1. Propósito del Módulo

El módulo de **Gastos** implementa el sistema de **Documentos Soporte** según la normativa colombiana (Art. 1.6.1.4.12 DR 1625 de 2016). Gestiona:

- **Documentos Soporte Inmutables**: Evidencia legal de gastos con consecutivos DIAN
- **Clasificación Contable**: Centros de costo y categorías contables
- **Retenciones**: Retefuente y ReteICA según normativa colombiana
- **Resoluciones DIAN**: Gestión de autorizaciones para emisión de documentos

### 1.2. Principios Arquitectónicos

- **Inmutabilidad Estricta**: Una vez generado el consecutivo, los valores monetarios son INMUTABLES
- **SSoT (Single Source of Truth)**: Empresa como fuente única de verdad por tenant
- **Separación de Responsabilidades**: DocumentoSoporte (evidencia legal) vs Gasto (clasificación contable)
- **Zero Waste**: Optimización de QuerySets con `only()` y `select_related()`
- **API-First**: Endpoints REST JSON-only para consumo por frontend

### 1.3. Estructura de Archivos

```
apps/tenant/gastos/
├── models.py                    # Modelos: ResolucionDIAN, DocumentoSoporte, Gasto
├── services.py                  # Service Layer: Lógica de negocio principal
├── services/
│   └── gasto_service.py        # Servicios adicionales (legacy)
├── api/
│   ├── viewsets.py             # ViewSets DRF (GastoViewSet, ResolucionDIANViewSet)
│   ├── serializers.py          # Serializers para API
│   └── urls.py                 # URLs del router DRF
├── admin.py                    # Admin interface Django
├── choices/
│   ├── categoria_contable.py   # Choices para categorías contables
│   └── centros_costo.py        # Choices para centros de costo
└── migrations/                 # Migraciones de base de datos

apps/tenant/core/
├── api/v1/gastos/
│   ├── viewsets.py            # Core API Facade ViewSets (GastoCoreViewSet, ResolucionDIANCoreViewSet)
│   └── serializers.py         # Workspace Serializers (GastoWorkspaceListSerializer, GastoWorkspaceDetailSerializer)
├── static/core/js/gastos/
│   ├── gastos.api.js          # Wrapper API (Capa de Datos)
│   ├── gastos.page.js         # Módulo principal (Tabulator)
│   ├── gastos_main.js         # Lógica principal
│   ├── gastos_crear.js        # Creación de gastos
│   ├── gastos_anular.js       # Anulación de gastos
│   ├── gastos_resolucion.js   # Gestión de resoluciones
│   ├── gastos_resoluciones_list.js  # Listado de resoluciones
│   └── resoluciones.page.js    # Página de resoluciones
└── templates/tenant/core/partials/gastos/
    ├── list.html               # Vista principal (Tabulator + Panel de totales)
    ├── modals.html             # Modals (legacy, migrado a Offcanvas)
    ├── offcanvas_crear.html    # Offcanvas para crear gasto
    ├── offcanvas_detalle.html  # Offcanvas para ver detalle
    ├── offcanvas_resolucion.html  # Offcanvas para configurar resolución
    ├── partial_summary.html    # Panel de totales netos
    └── assets_gastos.html      # Assets y eventos HTMX
```

---

## 2. Arquitectura del Módulo

### 2.1. Separación de Responsabilidades

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE PRESENTACIÓN                     │
│  (Frontend: Tabulator, Modals, Forms)                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      CAPA DE API (DRF)                      │
│  - GastoViewSet (CRUD + acciones)                          │
│  - ResolucionDIANViewSet (CRUD + acciones)                  │
│  - Serializers (List/Detail)                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE SERVICIOS                        │
│  - services.py (Lógica de negocio principal)               │
│  - Validaciones, cálculos, transacciones                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      CAPA DE MODELOS                        │
│  - ResolucionDIAN (Autorización DIAN)                       │
│  - DocumentoSoporte (Evidencia legal inmutable)             │
│  - Gasto (Clasificación contable)                          │
└─────────────────────────────────────────────────────────────┘
```

### 2.2. Relaciones entre Modelos

```
Empresa (SSoT)
    │
    ├── ResolucionDIAN (1:N)
    │       │
    │       └── DocumentoSoporte (1:N)
    │               │
    │               └── Gasto (1:1)
    │
    └── Gasto (1:N) [FK directa para optimización]
```

**Reglas de Relación:**
- **Empresa → ResolucionDIAN**: Una empresa puede tener múltiples resoluciones, pero solo UNA vigente
- **ResolucionDIAN → DocumentoSoporte**: Una resolución puede tener múltiples documentos
- **DocumentoSoporte → Gasto**: Relación OneToOne (1 documento = 1 clasificación contable)
- **Empresa → Gasto**: FK directa para optimización de queries (SSoT)

---

## 3. Modelos de Datos

### 3.1. ResolucionDIAN

**Archivo:** `apps/tenant/gastos/models.py` (líneas 21-129)

**Propósito:** Autorización DIAN para emisión de Documentos Soporte

**Campos Principales:**
- `empresa` (FK): Empresa propietaria (SSoT)
- `numero_resolucion` (CharField): Número de resolución DIAN
- `prefijo` (CharField): Prefijo del documento (ej: "SI")
- `rango_desde` / `rango_hasta` (IntegerField): Rango de consecutivos autorizados
- `fecha_resolucion` (DateField): Fecha de emisión de la resolución
- `fecha_inicio` / `fecha_fin` (DateField): Rango de vigencia
- `vigente` (BooleanField): Solo UNA resolución puede estar vigente por empresa

**Reglas de Negocio:**
- ⚠️ **REGLA CRÍTICA**: Solo UNA resolución puede estar vigente por empresa
- Si se marca como vigente, desactiva automáticamente las anteriores (en `save()`)
- Validación de rangos: `rango_hasta > rango_desde`
- Validación de fechas: `fecha_fin > fecha_inicio`, `fecha_inicio >= fecha_resolucion`
- Método `esta_dentro_de_fecha()`: Verifica si una fecha está en el rango permitido

**Índices:**
- `['empresa', 'vigente']`: Para búsqueda rápida de resolución vigente

**Inmutabilidad:**
- Las resoluciones son documentos legales y NO deben editarse
- Solo se pueden crear nuevas o desactivar/eliminar (si no tienen uso)

### 3.2. DocumentoSoporte

**Archivo:** `apps/tenant/gastos/models.py` (líneas 131-453)

**Propósito:** Evidencia legal inmutable de gasto según normativa DIAN

**Campos Principales:**

**Identificación:**
- `empresa` (FK): Empresa propietaria (SSoT)
- `resolucion_dian` (FK): Resolución DIAN que autoriza el documento
- `prefijo` (CharField): Prefijo del documento (snapshot desde resolución)
- `consecutivo` (IntegerField): **INMUTABLE** - Número consecutivo dentro del rango
- `fecha` (DateField): Fecha de emisión del documento

**Datos del Vendedor (Snapshot Histórico):**
- `vendedor_nombre` (CharField): Nombre o razón social
- `vendedor_nit` (CharField): NIT del vendedor
- `vendedor_direccion` (CharField): Dirección (opcional)
- `vendedor_telefono` (CharField): Teléfono (opcional)
- `numero_factura_proveedor` (CharField): Número de factura del proveedor (referencia)

**Detalle Económico (INMUTABLE una vez asignado consecutivo):**
- `subtotal` (DecimalField): Subtotal antes de retenciones
- `retefuente_porcentaje` (CharField): Porcentaje de Retefuente (choices)
- `retefuente` (DecimalField): Valor calculado de Retefuente
- `reteica_porcentaje` (CharField): Porcentaje de ReteICA (choices)
- `reteica` (DecimalField): Valor calculado de ReteICA
- `total` (DecimalField): **Total = Subtotal - Retefuente - ReteICA**

**Archivo y Estado:**
- `adjunto` (FileField): Archivo del documento (PDF, imagen, XML)
- `activo` (BooleanField): Indica si el documento está activo
- `anulado` (BooleanField): Indica si el documento ha sido anulado
- `fecha_anulacion` (DateTimeField): Fecha y hora de anulación

**Reglas de Negocio:**
- ⚠️ **REGLA DE ORO**: Una vez generado el consecutivo, los valores monetarios son INMUTABLES
- ⚠️ **Fórmula Crítica**: `Total = Subtotal - Retefuente - ReteICA`
- ⚠️ **Validación de Consecutivo**: Debe estar dentro del rango de la resolución
- ⚠️ **Cálculo Automático**: Las retenciones se calculan automáticamente en `clean()`
- ⚠️ **Anulación**: Solo se puede anular si está desactivado (`activo=False`)

**Choices de Retenciones:**

**Retefuente:**
- `'0.00'`: 0% - Sin Retefuente
- `'0.04'`: 4% - Servicios (Declarantes)
- `'0.06'`: 6% - Servicios (No Declarantes)
- `'0.10'`: 10% - Honorarios y Consultoría (Persona Natural no declarante)
- `'0.11'`: 11% - Honorarios y Consultoría (Persona Jurídica o declarante)

**ReteICA:**
- `'0.00'`: 0% - Exento
- `'0.0069'`: 0.69% - Tarifa 0.69% (6.9/1000)
- `'0.00966'`: 0.966% - Tarifa 0.966% (9.66/1000)
- `'0.01104'`: 1.104% - Tarifa 1.104% (11.04/1000)

**Índices:**
- `['empresa', 'fecha']`: Para búsqueda por empresa y fecha
- `['resolucion_dian', 'consecutivo']`: Para búsqueda por resolución y consecutivo
- `['prefijo', 'consecutivo']`: Para búsqueda por número completo ("SI 150")
- `['vendedor_nit', 'numero_factura_proveedor']`: Para evitar duplicados
- `['activo']`, `['anulado']`: Para filtrado rápido

**Constraints:**
- `unique_ds_resolucion_consecutivo`: Consecutivo único por resolución
- `unique_ds_vendedor_factura`: Vendedor + número factura único (solo si no anulado)

**Propiedades:**
- `numero_documento`: Retorna "Prefijo Consecutivo" (ej: "SI 150")
- `subtotal_cop`, `retefuente_cop`, `reteica_cop`, `total_cop`: Formateo como dinero COP
- `total_retenciones_cop`: Suma de retenciones formateada

### 3.3. Gasto

**Archivo:** `apps/tenant/gastos/models.py` (líneas 455-595)

**Propósito:** Clasificación contable de un Documento Soporte

**Campos Principales:**
- `documento_soporte` (OneToOneField): Documento Soporte asociado (evidencia legal)
- `empresa` (FK): Empresa propietaria (SSoT - FK directa para optimización)
- `centro_costo` (CharField): Centro de costo (choices)
- `categoria_contable` (CharField): Categoría contable (choices)
- `periodo` (CharField): Periodo contable (formato: YYYY-MM)
- `descripcion` (TextField): Descripción adicional (opcional)
- `observaciones` (TextField): Observaciones (opcional)

**Reglas de Negocio:**
- ⚠️ **Relación OneToOne**: Un DocumentoSoporte = Un Gasto (simplicidad inicial)
- ⚠️ **Periodo**: Formato YYYY-MM (validado con regex)
- ⚠️ **Propiedades Delegadas**: Todos los valores monetarios se delegan al DocumentoSoporte (INMUTABLES)

**Índices:**
- `['empresa', 'periodo']`: Para búsqueda por empresa y periodo
- `['centro_costo', 'categoria_contable']`: Para clasificación contable
- `['documento_soporte']`: Para búsqueda rápida del documento asociado

**Propiedades Delegadas (INMUTABLES):**
- `subtotal`, `retefuente`, `reteica`, `total`: Valores monetarios
- `fecha`, `numero_documento`: Datos del documento
- `subtotal_cop`, `retefuente_cop`, `reteica_cop`, `total_cop`: Formateo como dinero

---

## 4. Capa de Servicios

### 4.1. services.py

**Archivo:** `apps/tenant/gastos/services.py`

**Propósito:** Service Layer - Lógica de negocio sin presentación

#### 4.1.1. Funciones de Resolución DIAN

**`obtener_resolucion_vigente(empresa)`** (líneas 28-37)
- Obtiene la resolución DIAN vigente para una empresa
- ⚠️ SSoT: Solo una resolución vigente por empresa
- Retorna `None` si no hay resolución vigente

**`obtener_siguiente_numero_soporte(empresa)`** (líneas 39-91)
- ⚠️ **CRÍTICO**: Calcula el siguiente consecutivo inmutable
- Busca automáticamente la resolución vigente
- ⚠️ **INCLUYE documentos anulados** en el cálculo para evitar duplicados
- Valida que el consecutivo esté dentro del rango
- Valida que no exista ya el consecutivo (doble verificación)
- Retorna el siguiente número disponible

**`qs_resolucion_list(empresa_id)`** (líneas 248-254)
- QuerySet optimizado para listado de resoluciones
- ⚠️ SSoT: Filtrado por empresa

**`qs_resolucion_detail(empresa_id, resolucion_id)`** (líneas 257-263)
- QuerySet optimizado para detalle de resolución
- ⚠️ SSoT: Filtrado por empresa

**`crear_resolucion(empresa, data)`** (líneas 266-338)
- Crea una nueva resolución DIAN
- ⚠️ **REGLA CRÍTICA**: Si se marca como vigente, desactiva automáticamente las anteriores
- Valida fechas y rangos
- Retorna la instancia creada

**`desactivar_resolucion(empresa, resolucion_id)`** (líneas 341-367)
- Desactiva una resolución (marca `vigente=False`)
- ⚠️ **INMUTABILIDAD**: No afecta documentos ya generados (snapshot inalterable)

**`puede_eliminar_resolucion(empresa, resolucion_id)`** (líneas 426-451)
- Verifica si una resolución puede ser eliminada
- ⚠️ **REGLA**: No se puede eliminar si tiene Documentos de Soporte asociados
- Retorna `(puede_eliminar: bool, mensaje: str)`

**`calcular_retenciones(subtotal, retefuente_porcentaje, reteica_porcentaje)`** (líneas 370-423)
- Calcula las retenciones (Retefuente y ReteICA) basándose en el subtotal y porcentajes
- ⚠️ **Fórmula**: `Retefuente = subtotal * porcentaje_retefuente`, `ReteICA = subtotal * porcentaje_reteica`
- ⚠️ **Total Neto**: `total = subtotal - retefuente - reteica`
- Valida que el total no sea negativo
- Retorna `{'retefuente': Decimal, 'reteica': Decimal, 'total': Decimal}`

#### 4.1.2. Funciones de Gasto

**`qs_list(search=None)`** (líneas 93-129)
- QuerySet optimizado para Tabulator (v2.40)
- ⚠️ **CRÍTICO**: INCLUYE TODOS LOS DOCUMENTOS (anulados y no anulados)
- Los documentos anulados DEBEN aparecer en la lista para mantener la secuencia de consecutivos
- Soporta búsqueda con parámetro `?search=`
- Usa `select_related()` y `only()` para optimización

**`qs_detail()`** (líneas 131-135)
- QuerySet completo para vista de detalle
- Incluye relaciones con `select_related()`

**`desactivar_gasto_service(gasto_id)`** (líneas 137-166)
- Desactiva un gasto (soft-disable)
- ⚠️ **REGLA CRÍTICA**: Paso previo obligatorio antes de anular
- El documento debe estar desactivado para poder anularlo
- Usa `update()` directamente para evitar validaciones

**`anular_gasto_service(gasto_id)`** (líneas 169-209)
- Marca un gasto como anulado (Inmutable)
- ⚠️ **REGLA CRÍTICA**: Solo se puede anular si está desactivado (`activo=False`)
- Usa `update()` directamente para evitar validaciones del modelo
- Retorna información del documento anulado

**`get_gastos_summary(empresa_id=None)`** (líneas 211-237)
- Calcula totales financieros netos (v2.40)
- ⚠️ **REGLA CRÍTICA**: Excluye automáticamente registros anulados y desactivados
- Solo suma documentos activos y no anulados
- Retorna:
  ```python
  {
      "subtotal_neto": Decimal,
      "retefuente_neto": Decimal,
      "reteica_neto": Decimal,
      "retenciones_neto": Decimal,  # Suma de retefuente + reteica
      "total_neto": Decimal,
      "cantidad": int
  }
  ```

**`materializar_gasto_desde_dto(dto)`** (líneas 239-241)
- ⚠️ **PLACEHOLDER**: Integración con Document Ingest Pipeline
- Retorna 501 (Not Implemented)

#### 4.1.3. Funciones de Utilidad

**`normalize_document_number(value)`** (líneas 23-26)
- Limpia y normaliza identificadores legales
- Elimina espacios y caracteres no imprimibles

**Constantes:**
- `LIST_FIELDS`: Campos mínimos para optimización de QuerySets
- `DETAIL_FIELDS`: Campos completos para vista de detalle

### 4.2. services/gasto_service.py

**Archivo:** `apps/tenant/gastos/services/gasto_service.py`

**Propósito:** Servicios adicionales (legacy)

**`crear_o_actualizar_gasto(data)`** (líneas 24-61)
- ⚠️ **LEGACY**: Crea/actualiza un gasto SIN IVA con reglas mínimas
- Validaciones base: valor > 0, periodo YYYY-MM, coherencia tipo/subtipo
- Upsert por (fecha, periodo, tipo, subtipo, comprobante)

---

## 5. Capa de API (DRF)

### 5.1. GastoViewSet

**Archivo:** `apps/tenant/gastos/api/viewsets.py` (líneas 48-345)

**Propósito:** ViewSet principal para gestión de gastos

**Configuración:**
- `authentication_classes`: `[SessionAuthentication]`
- `permission_classes`: `[IsTenantMember, IsTenantAdminOrReadOnly]`
- `http_method_names`: `['get', 'post', 'delete', 'head', 'options']` (Bloquea PUT/PATCH)
- `pagination_class`: `StandardResultsSetPagination`

**Filtros y Búsqueda:**
- `filterset_fields`: `["periodo", "centro_costo", "categoria_contable"]`
- `search_fields`: `["descripcion", "documento_soporte__vendedor_nombre", "documento_soporte__prefijo"]`
- `ordering_fields`: `["documento_soporte__fecha", "documento_soporte__total"]`
- `ordering`: `["-documento_soporte__fecha"]`

#### 5.1.1. Acciones Estándar

**`list()`** (líneas 117-131)
- `GET /api/v1/gastos/`
- Lista paginada de gastos (Tabulator v2.40)
- Soporta `?search=` para búsqueda y `?page=` para paginación
- ⚠️ **CRÍTICO**: INCLUYE TODOS LOS DOCUMENTOS (anulados y no anulados)

**`retrieve()`** (heredado de `RetrieveModelMixin`)
- `GET /api/v1/gastos/{id}/`
- Obtiene detalle completo de un gasto

**`create()`** (líneas 133-221)
- `POST /api/v1/gastos/`
- Crea un nuevo Gasto con DocumentoSoporte
- ⚠️ **v2.40**: Usa automáticamente la resolución vigente si no se proporciona
- Obtiene siguiente consecutivo automáticamente
- Calcula retenciones usando `calcular_retenciones()`
- Crea DocumentoSoporte y Gasto en transacción atómica

**`destroy()`** (heredado de `DestroyModelMixin`)
- `DELETE /api/v1/gastos/{id}/`
- Elimina un gasto (y su DocumentoSoporte asociado)

#### 5.1.2. Acciones Personalizadas

**`desactivar()`** (líneas 223-239)
- `POST /api/v1/gastos/{id}/desactivar/`
- Desactiva un gasto (soft-disable)
- ⚠️ **REGLA CRÍTICA**: Paso previo obligatorio antes de anular

**`anular()`** (líneas 241-258)
- `POST /api/v1/gastos/{id}/anular/`
- Anula un gasto (Inmutable)
- ⚠️ **REGLA CRÍTICA**: Solo se puede anular si está desactivado

**`summary()`** (líneas 260-298)
- `GET /api/v1/gastos/summary/`
- Obtiene resumen financiero neto excluyendo documentos anulados
- ⚠️ **REGLA CRÍTICA**: Documentos con `anulado=True` => Valor 0

**`resoluciones()`** (líneas 300-305)
- `GET /api/v1/gastos/resoluciones/`
- ⚠️ **LEGACY**: Retorna resoluciones DIAN vigentes para el formulario

**`resolucion_activa()`** (líneas 307-345)
- `GET /api/v1/gastos/resolucion-activa/`
- ⚠️ **DEPRECATED**: Usar `/api/v1/resoluciones-dian/activa/`
- Retorna la resolución DIAN vigente para la empresa del tenant
- Retorna 404 si no existe (para que el frontend abra el modal de configuración)

**`configurar_resolucion()`** (líneas 347-460)
- `POST /api/v1/gastos/configurar-resolucion/`
- ⚠️ **DEPRECATED**: Usar `POST /api/v1/resoluciones-dian/`
- Crea o actualiza una resolución DIAN para la empresa del tenant
- ⚠️ **REGLA CRÍTICA**: Si se marca como vigente, desactiva automáticamente las anteriores

### 5.0. Core API Facade (v2.61.4)

**Ubicación:** `apps/tenant/core/api/v1/gastos/`

**Propósito:** Facade ViewSets para exponer funcionalidades de Gastos a través de Core API para workspace.

**ViewSets Facade:**
- `GastoCoreViewSet`: Hereda de `GastoViewSet`, expone serializers Workspace
- `ResolucionDIANCoreViewSet`: Hereda de `ResolucionDIANViewSet`, expone serializers Workspace

**Endpoints Core API:**
- `/api/v1/core/v1/gastos/operativos/` → `GastoCoreViewSet` ✅ v2.61.4
- `/api/v1/core/v1/gastos/resoluciones-dian/` → `ResolucionDIANCoreViewSet` ✅ v2.61.4

**Registro en Router:**
```python
# apps/tenant/core/api/urls.py
router_v1.register(r"gastos/operativos", GastoCoreViewSet, basename="core-gastos")
router_v1.register(r"gastos/resoluciones-dian", ResolucionDIANCoreViewSet, basename="core-gastos-resoluciones")
```

**Serializers Workspace:**
- `GastoWorkspaceListSerializer`: Hereda de `GastoListSerializer`
- `GastoWorkspaceDetailSerializer`: Hereda de `GastoDetailSerializer`, incluye `DocumentoSoporteWorkspaceDetailSerializer` con `adjunto_url`
- `DocumentoSoporteWorkspaceDetailSerializer`: Agrega `adjunto_url` (URL absoluta del adjunto)

**Características:**
- ✅ Hereda todas las acciones `@action` automáticamente (summary, anular, desactivar, render-offcanvas, etc.)
- ✅ Serializers Workspace con URLs absolutas de adjuntos
- ✅ Links centralizados en `CoreLinksViewSet`:
  - `"gastos-operativos": {"api": "/api/v1/core/v1/gastos/operativos/", "ui": "/workspace/#gastos"}`
  - `"gastos-resoluciones": {"api": "/api/v1/core/v1/gastos/resoluciones-dian/", "ui": "/workspace/#gastos"}`

**Acciones Heredadas:**
- `GET /api/v1/core/v1/gastos/operativos/` - Lista gastos
- `POST /api/v1/core/v1/gastos/operativos/` - Crear gasto
- `GET /api/v1/core/v1/gastos/operativos/{id}/` - Detalle gasto
- `DELETE /api/v1/core/v1/gastos/operativos/{id}/` - Eliminar gasto
- `POST /api/v1/core/v1/gastos/operativos/{id}/anular/` - Anular gasto
- `POST /api/v1/core/v1/gastos/operativos/{id}/desactivar/` - Desactivar gasto
- `GET /api/v1/core/v1/gastos/operativos/summary/` - Resumen financiero
- `GET /api/v1/core/v1/gastos/operativos/render-offcanvas/crear/` - Renderizar offcanvas crear
- `GET /api/v1/core/v1/gastos/operativos/render-offcanvas/detalle/` - Renderizar offcanvas detalle
- `GET /api/v1/core/v1/gastos/resoluciones-dian/` - Lista resoluciones
- `POST /api/v1/core/v1/gastos/resoluciones-dian/` - Crear resolución
- `GET /api/v1/core/v1/gastos/resoluciones-dian/activa/` - Obtener resolución activa
- `POST /api/v1/core/v1/gastos/resoluciones-dian/{id}/desactivar/` - Desactivar resolución

---

### 5.1. GastoViewSet

**Archivo:** `apps/tenant/gastos/api/viewsets.py` (líneas 48-345)

**Propósito:** ViewSet principal para gestión de gastos

**Configuración:**
- `authentication_classes`: `[SessionAuthentication]`
- `permission_classes`: `[IsTenantMember, IsTenantAdminOrReadOnly]`
- `http_method_names`: `['get', 'post', 'delete', 'head', 'options']` (Bloquea PUT/PATCH)
- `pagination_class`: `StandardResultsSetPagination`

**Filtros y Búsqueda:**
- `search_fields`: `['numero_resolucion', 'prefijo']`
- `ordering_fields`: `['fecha_resolucion', 'vigente', 'created_at']`
- `ordering`: `['-vigente', '-fecha_resolucion']`

#### 5.2.1. Acciones Estándar

**`list()`** (líneas 537-550)
- `GET /api/v1/resoluciones-dian/`
- Lista paginada de resoluciones (Tabulator v2.40)
- ⚠️ SSoT: Filtrado por empresa

**`retrieve()`** (líneas 552-559)
- `GET /api/v1/resoluciones-dian/{id}/`
- Obtiene detalle de una resolución

**`create()`** (líneas 561-584)
- `POST /api/v1/resoluciones-dian/`
- Crea una nueva resolución DIAN
- ⚠️ **REGLA CRÍTICA**: Si se marca como vigente, desactiva automáticamente las anteriores

**`destroy()`** (líneas 586-623)
- `DELETE /api/v1/resoluciones-dian/{id}/`
- Elimina una resolución DIAN
- ⚠️ **REGLA**: No se puede eliminar si tiene Documentos de Soporte asociados

#### 5.2.2. Acciones Personalizadas

**`desactivar()`** (líneas 625-649)
- `POST /api/v1/resoluciones-dian/{id}/desactivar/`
- Desactiva una resolución DIAN (marca `vigente=False`)
- ⚠️ **INMUTABILIDAD**: No afecta documentos ya generados

**`activa()`** (líneas 651-678)
- `GET /api/v1/resoluciones-dian/activa/`
- Retorna la resolución DIAN vigente para la empresa del tenant
- Retorna 404 si no existe

---

## 6. Serializers

### 6.1. GastoListSerializer

**Archivo:** `apps/tenant/gastos/api/serializers.py` (líneas 140-181)

**Propósito:** Serializer optimizado para Tabulator (v2.40)

**Características:**
- ⚠️ **Aplanamiento de campos**: Prefijo `ds_` para campos de DocumentoSoporte
- Campos aplanados: `ds_consecutivo`, `ds_prefijo`, `ds_numero_documento`, `ds_vendedor`, `ds_fecha`, `ds_total`, `ds_activo`, `ds_anulado`
- Campos display: `centro_costo_display`, `categoria_contable_display`
- ⚠️ **REGLA DE EXPOSICIÓN**: Mínimo payload, máximo rendimiento

**Campos Expuestos:**
```python
{
    'id',
    'categoria_contable',
    'categoria_contable_display',
    'centro_costo',
    'centro_costo_display',
    'ds_consecutivo',
    'ds_prefijo',
    'ds_numero_documento',  # Prefijo + Consecutivo completo
    'ds_vendedor',
    'ds_fecha',
    'ds_total',
    'ds_activo',
    'ds_anulado',
}
```

### 6.2. GastoDetailSerializer

**Archivo:** `apps/tenant/gastos/api/serializers.py` (líneas 249-288)

**Propósito:** Serializer completo para detalle de gasto

**Características:**
- Incluye `DocumentoSoporteDetailSerializer` anidado
- Campos display: `centro_costo_display`, `categoria_contable_display`
- Validación de periodo: Formato YYYY-MM

**Campos Expuestos:**
```python
{
    'id',
    'empresa',
    'documento_soporte',  # Serializer anidado completo
    'periodo',
    'centro_costo',
    'centro_costo_display',
    'categoria_contable',
    'categoria_contable_display',
    'descripcion',
    'observaciones',
    'created_at',
    'updated_at',
}
```

### 6.3. DocumentoSoporteDetailSerializer

**Archivo:** `apps/tenant/gastos/api/serializers.py` (líneas 184-246)

**Propósito:** Serializer completo para evidencia legal

**Características:**
- Incluye `ResolucionDIANNestedSerializer` anidado
- ⚠️ **CORRECCIÓN**: Campos de fecha explícitamente declarados (DateField vs DateTimeField)
- ⚠️ **INMUTABILIDAD**: Campos monetarios y legales son `read_only`

**Campos Expuestos:**
```python
{
    'id',
    'empresa',
    'resolucion_dian',  # Serializer anidado
    'prefijo',
    'consecutivo',
    'numero_documento_full',
    'fecha',
    'vendedor_nit',
    'vendedor_nombre',
    'vendedor_direccion',
    'vendedor_telefono',
    'numero_factura_proveedor',
    'subtotal',
    'retefuente_porcentaje',
    'retefuente',
    'reteica_porcentaje',
    'reteica',
    'total',
    'adjunto',
    'activo',
    'anulado',
    'fecha_anulacion',
    'created_at',
    'updated_at',
}
```

### 6.4. ResolucionDIANListSerializer

**Archivo:** `apps/tenant/gastos/api/serializers.py` (líneas 48-78)

**Propósito:** Serializer optimizado para listado de resoluciones

**Características:**
- Campo calculado: `conteo_documentos` (número de Documentos de Soporte asociados)
- Campos de fecha explícitamente declarados

**Campos Expuestos:**
```python
{
    'id',
    'numero_resolucion',
    'prefijo',
    'rango_desde',
    'rango_hasta',
    'fecha_resolucion',
    'fecha_inicio',
    'fecha_fin',
    'vigente',
    'conteo_documentos',
}
```

### 6.5. ResolucionDIANDetailSerializer

**Archivo:** `apps/tenant/gastos/api/serializers.py` (líneas 80-138)

**Propósito:** Serializer completo para detalle de resolución

**Características:**
- ⚠️ **INMUTABILIDAD**: Todos los campos son `read_only`
- Campo calculado: `conteo_documentos`
- ⚠️ **CORRECCIÓN**: Método `to_representation()` para asegurar serialización correcta de fechas

**Campos Expuestos:**
```python
{
    'id',
    'empresa',
    'numero_resolucion',
    'prefijo',
    'rango_desde',
    'rango_hasta',
    'fecha_resolucion',
    'fecha_inicio',
    'fecha_fin',
    'clave_tecnica',
    'vigente',
    'conteo_documentos',
    'created_at',
    'updated_at',
}
```

### 6.6. ResolucionDIANNestedSerializer

**Archivo:** `apps/tenant/gastos/api/serializers.py` (líneas 13-45)

**Propósito:** Serializer anidado para uso en otros serializers

**Características:**
- Todos los campos son `read_only`
- Campos de fecha explícitamente declarados

---

## 7. Frontend

### 7.1. Arquitectura Frontend

**Patrón**: Feature-Sliced Architecture (v2.60)

**Estructura:**
```
apps/tenant/core/static/core/js/gastos/
├── gastos.api.js              # Wrapper API (Capa de Datos)
├── gastos.page.js             # Módulo principal (Tabulator)
├── gastos_main.js             # Lógica principal
├── gastos_crear.js            # Creación de gastos
├── gastos_anular.js           # Anulación de gastos
├── gastos_resolucion.js       # Gestión de resoluciones
├── gastos_resoluciones_list.js # Listado de resoluciones
└── resoluciones.page.js       # Página de resoluciones
```

**Templates:**
```
apps/tenant/core/templates/tenant/core/partials/gastos/
├── list.html                  # Vista principal (Tabulator + Panel de totales)
├── modals.html                # Modals (legacy, migrado a Offcanvas)
├── offcanvas_crear.html       # Offcanvas para crear gasto
├── offcanvas_detalle.html     # Offcanvas para ver detalle
├── offcanvas_resolucion.html  # Offcanvas para configurar resolución
├── partial_summary.html       # Panel de totales netos
└── assets_gastos.html         # Assets y eventos HTMX
```

**Características:**
- ✅ **Tabulator Factory**: Tabla principal con paginación remota
- ✅ **HTMX**: Carga dinámica de offcanvas
- ✅ **Bootstrap Offcanvas**: Modales deslizantes para formularios
- ✅ **Panel de Totales**: Resumen financiero neto (excluye anulados)
- ✅ **API-First**: Consume DRF REST API exclusivamente
- ✅ **Aislamiento Gradual**: Sin bloques try/catch, usa `UIManager.handleError()`

**Endpoints JavaScript:**
- `gastos.api.js` usa `/api/v1/gastos/` (App API directa)
- ⚠️ **NOTA**: No usa Core API Facade aún (pendiente migración)

**Inicialización:**
- Lazy loading con `DOMUtils.onVisibleOnce('#tab-gastos')`
- Auto-inicialización cuando el tab se muestra
- Carga de resumen financiero automática

---

## 8. Flujos Completos

### 8.1. Flujo Completo: Workspace → Core API → Models

#### 8.1.1. Flujo: Crear Gasto (Paso a Paso)

```
1. Usuario: En workspace.html → #gastos
   → Hace clic en botón "Nuevo Gasto"
   ↓
2. Frontend: list.html
   → HTMX: GET /api/v1/gastos/render-offcanvas/crear/
   → Target: #offcanvas-container-gastos
   ↓
3. Backend: GastoViewSet.render_offcanvas_crear()
   → Renderiza offcanvas_crear.html
   → Retorna HTML del formulario
   ↓
4. Frontend: HTMX carga HTML en #offcanvas-container-gastos
   → Bootstrap Offcanvas se muestra automáticamente
   → gastos_crear.js inicializa eventos del formulario
   ↓
5. Usuario: Completa formulario y hace clic en "Guardar"
   → gastos_crear.js recolecta datos del formulario
   → Valida que exista resolución activa (si no, abre modal de configuración)
   ↓
6. Frontend: gastos.api.js
   → POST /api/v1/gastos/
   → Payload: {vendedor_nit, vendedor_nombre, subtotal, retefuente, reteica, ...}
   ↓
7. Backend: GastoViewSet.create()
   → Valida permisos (IsTenantAdminOrReadOnly)
   → Obtiene empresa singleton (SSoT)
   → Obtiene resolución vigente automáticamente (si no se proporciona)
   → Obtiene siguiente consecutivo usando obtener_siguiente_numero_soporte()
   → Calcula retenciones usando calcular_retenciones()
   ↓
8. Service Layer: services.py
   → crear_gasto_completo() crea DocumentoSoporte y Gasto en transacción atómica
   → Valida que el consecutivo esté dentro del rango
   → Valida que no exista ya el consecutivo
   ↓
9. Models: DocumentoSoporte.save()
   → Asigna consecutivo inmutable
   → Calcula total = subtotal - retefuente - reteica
   → Guarda en BD con constraints únicos
   ↓
10. Models: Gasto.save()
    → Asocia con DocumentoSoporte (OneToOne)
    → Guarda clasificación contable
    ↓
11. Response: 201 Created
    → Payload: GastoDetailSerializer con DocumentoSoporte anidado
    ↓
12. Frontend: gastos_crear.js maneja respuesta
    → Si res.ok: muestra notificación de éxito
    → Cierra offcanvas
    → Recarga tabla Tabulator
    → Recarga panel de totales (summary)
    ↓
13. Frontend: gastos.page.js
    → GET /api/v1/gastos/?page=1&page_size=10
    → GET /api/v1/gastos/summary/
    → Actualiza tabla y panel de totales
```

#### 8.1.2. Flujo: Anular Gasto (Paso a Paso)

```
1. Usuario: En workspace.html → #gastos
   → Hace clic en botón "Anular" en fila de gasto
   ↓
2. Frontend: gastos.page.js
   → Detecta click en botón con data-action="anular-gasto"
   → Obtiene gasto_id desde data-id
   → Muestra confirmación
   ↓
3. Si usuario confirma: gastos_anular.js
   → Verifica que el gasto esté desactivado (paso previo obligatorio)
   → POST /api/v1/gastos/{id}/anular/
   ↓
4. Backend: GastoViewSet.anular()
   → Valida que documento_soporte.activo == False
   → Llama a anular_gasto_service()
   ↓
5. Service Layer: services.py
   → anular_gasto_service() marca documento_soporte.anulado = True
   → Registra fecha_anulacion
   → ⚠️ INMUTABILIDAD: No modifica valores monetarios
   ↓
6. Response: 200 OK
   → Payload: GastoDetailSerializer actualizado
   ↓
7. Frontend: gastos_anular.js maneja respuesta
   → Si res.ok: muestra notificación de éxito
   → Recarga tabla Tabulator
   → Recarga panel de totales (summary excluye anulados)
```

#### 8.1.3. Flujo: Configurar Resolución DIAN (Paso a Paso)

```
1. Usuario: En workspace.html → #gastos
   → Hace clic en botón "Configurar Resolución"
   ↓
2. Frontend: list.html
   → HTMX: GET /api/v1/gastos/render-offcanvas/resolucion/
   → Target: #offcanvas-container-gastos
   ↓
3. Backend: GastoViewSet.render_offcanvas_resolucion()
   → Renderiza offcanvas_resolucion.html
   → Retorna HTML del formulario
   ↓
4. Frontend: HTMX carga HTML
   → Bootstrap Offcanvas se muestra
   → gastos_resolucion.js inicializa eventos
   ↓
5. Usuario: Completa formulario y hace clic en "Guardar"
   → gastos_resolucion.js recolecta datos
   → POST /api/v1/resoluciones-dian/
   ↓
6. Backend: ResolucionDIANViewSet.create()
   → Valida permisos
   → Obtiene empresa singleton
   → Llama a crear_resolucion()
   ↓
7. Service Layer: services.py
   → crear_resolucion() valida fechas y rangos
   → ⚠️ REGLA CRÍTICA: Si vigente=True, desactiva automáticamente las anteriores
   → Crea ResolucionDIAN en BD
   ↓
8. Response: 201 Created
   → Payload: ResolucionDIANDetailSerializer
   ↓
9. Frontend: gastos_resolucion.js maneja respuesta
   → Si res.ok: muestra notificación de éxito
   → Cierra offcanvas
   → Recarga tabla de resoluciones
```

#### 8.1.4. Flujo: Consultar Resumen Financiero (Paso a Paso)

```
1. Frontend: gastos.page.js (auto-inicialización)
   → GET /api/v1/gastos/summary/
   ↓
2. Backend: GastoViewSet.summary()
   → Llama a get_gastos_summary()
   ↓
3. Service Layer: services.py
   → get_gastos_summary() filtra documentos activos y no anulados
   → Calcula agregaciones: subtotal_neto, retefuente_neto, reteica_neto, total_neto
   → Cuenta cantidad de documentos
   ↓
4. Response: 200 OK
   → Payload: {
       "subtotal_neto": Decimal,
       "retefuente_neto": Decimal,
       "reteica_neto": Decimal,
       "total_neto": Decimal,
       "cantidad": int
     }
   ↓
5. Frontend: gastos.page.js renderSummary()
   → Actualiza elementos del DOM:
     - #gasto-total-neto
     - #gasto-retefuente
     - #gasto-reteica
     - #gasto-cantidad
```

---

### 8.2. Flujos Legacy (v2.40)

### 7.1. Flujo de Creación de Gasto

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Usuario hace clic en "Crear Gasto"                       │
│    → Frontend: Abre modal de creación                       │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Frontend: Verificar resolución vigente                   │
│    GET /api/v1/gastos/resolucion-activa/                    │
│    → Si 404: Abrir modal de configuración de resolución     │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Usuario completa formulario:                             │
│    - Datos del vendedor (NIT, nombre, dirección, teléfono) │
│    - Número de factura del proveedor                        │
│    - Fecha del documento                                     │
│    - Subtotal                                                │
│    - Porcentajes de retención (Retefuente, ReteICA)         │
│    - Periodo contable (YYYY-MM)                              │
│    - Centro de costo                                         │
│    - Categoría contable                                      │
│    - Descripción y observaciones                             │
│    - Archivo adjunto (opcional)                              │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Frontend: Enviar POST /api/v1/gastos/                   │
│    Body: {                                                   │
│      "fecha": "2026-01-15",                                 │
│      "vendedor_nit": "123456789-1",                         │
│      "vendedor_nombre": "Proveedor XYZ",                    │
│      "subtotal": "1000000.00",                              │
│      "retefuente_porcentaje": "0.04",                       │
│      "reteica_porcentaje": "0.00966",                       │
│      "periodo": "2026-01",                                  │
│      "centro_costo": "ADMINISTRATIVOS",                     │
│      "categoria_contable": "SERVICIOS_PUBLICOS",             │
│      ...                                                     │
│    }                                                         │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Backend: GastoViewSet.create()                           │
│    → Obtener empresa del tenant (SSoT)                      │
│    → Obtener resolución vigente automáticamente             │
│    → Obtener siguiente consecutivo                          │
│    → Calcular retenciones (calcular_retenciones)            │
│    → Crear DocumentoSoporte (transacción atómica)           │
│    → Crear Gasto (transacción atómica)                      │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Backend: Retornar respuesta                              │
│    Status: 201 Created                                       │
│    Body: GastoDetailSerializer                              │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. Frontend: Cerrar modal y recargar tabla                  │
│    → GET /api/v1/gastos/ (list)                             │
└─────────────────────────────────────────────────────────────┘
```

### 7.2. Flujo de Anulación de Gasto

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Usuario hace clic en "Anular Gasto"                      │
│    → Frontend: Verificar estado del documento                │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Si documento está ACTIVO:                                  │
│    → Mostrar mensaje: "Debe desactivar primero"             │
│    → Botón "Desactivar" disponible                          │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Usuario hace clic en "Desactivar"                        │
│    → POST /api/v1/gastos/{id}/desactivar/                   │
│    → Backend: desactivar_gasto_service()                    │
│    → Actualizar activo=False                                │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Usuario hace clic en "Anular"                            │
│    → POST /api/v1/gastos/{id}/anular/                       │
│    → Backend: anular_gasto_service()                        │
│    → Validar: activo=False (requisito)                      │
│    → Actualizar anulado=True, fecha_anulacion=now()         │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Backend: Retornar respuesta                              │
│    Status: 200 OK                                            │
│    Body: {                                                   │
│      "id": 123,                                              │
│      "numero_documento": "SI 150",                          │
│      "anulado": true,                                        │
│      "fecha_anulacion": "2026-01-15T10:30:00Z"              │
│    }                                                         │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Frontend: Recargar tabla                                 │
│    → GET /api/v1/gastos/ (list)                             │
│    → Mostrar badge "Anulado" en la fila                     │
└─────────────────────────────────────────────────────────────┘
```

### 7.3. Flujo de Configuración de Resolución DIAN

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Usuario hace clic en "Configurar Resolución"             │
│    → Frontend: Abrir modal de configuración                 │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Usuario completa formulario:                             │
│    - Número de resolución DIAN                              │
│    - Prefijo (ej: "SI")                                      │
│    - Rango desde/hasta                                       │
│    - Fecha de resolución                                     │
│    - Fecha de fin (vigencia)                                 │
│    - Clave técnica (opcional)                                │
│    - Marcar como vigente                                     │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Frontend: Enviar POST /api/v1/resoluciones-dian/         │
│    Body: {                                                   │
│      "numero_resolucion": "123456789",                      │
│      "prefijo": "SI",                                        │
│      "rango_desde": 1,                                       │
│      "rango_hasta": 1000,                                    │
│      "fecha_resolucion": "2026-01-01",                      │
│      "fecha_fin": "2026-12-31",                             │
│      "vigente": true                                         │
│    }                                                         │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Backend: ResolucionDIANViewSet.create()                  │
│    → Obtener empresa del tenant (SSoT)                      │
│    → Si vigente=True: Desactivar resoluciones anteriores    │
│    → Validar fechas y rangos                                │
│    → Crear ResolucionDIAN (transacción atómica)             │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Backend: Retornar respuesta                              │
│    Status: 201 Created                                       │
│    Body: ResolucionDIANDetailSerializer                      │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Frontend: Cerrar modal y recargar tabla                  │
│    → GET /api/v1/resoluciones-dian/ (list)                  │
└─────────────────────────────────────────────────────────────┘
```

### 7.4. Flujo de Cálculo de Summary

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Frontend: Cargar página de gastos                        │
│    → GET /api/v1/gastos/summary/                            │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Backend: GastoViewSet.summary()                          │
│    → get_gastos_summary(empresa_id)                         │
│    → Filtrar: anulado=False AND activo=True                 │
│    → Agregar: Sum(subtotal), Sum(retefuente),              │
│               Sum(reteica), Sum(total), Count(id)           │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Backend: Retornar respuesta                              │
│    Status: 200 OK                                            │
│    Body: {                                                   │
│      "subtotal_neto": "5000000.00",                         │
│      "retefuente_neto": "200000.00",                        │
│      "reteica_neto": "48300.00",                            │
│      "retenciones_neto": "248300.00",                       │
│      "total_neto": "4751700.00",                            │
│      "cantidad": 25                                          │
│    }                                                         │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Frontend: Actualizar paneles de resumen                  │
│    → Mostrar totales en cards de resumen                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Reglas de Negocio Críticas

### 8.1. Inmutabilidad

- ⚠️ **REGLA DE ORO**: Una vez generado el consecutivo, los valores monetarios son INMUTABLES
- ⚠️ **Bloqueo de Edición**: PUT/PATCH están bloqueados en el ViewSet
- ⚠️ **Snapshot Histórico**: Los datos del vendedor se guardan como snapshot (no FK)
- ⚠️ **Consecutivo Único**: El consecutivo es único por resolución (UniqueConstraint)

### 8.2. Resolución DIAN

- ⚠️ **REGLA CRÍTICA**: Solo UNA resolución puede estar vigente por empresa
- Si se marca como vigente, desactiva automáticamente las anteriores
- ⚠️ **Validación de Rangos**: `rango_hasta > rango_desde`
- ⚠️ **Validación de Fechas**: `fecha_fin > fecha_inicio`, `fecha_inicio >= fecha_resolucion`
- ⚠️ **Eliminación**: No se puede eliminar si tiene Documentos de Soporte asociados

### 8.3. Cálculo de Retenciones

- ⚠️ **Fórmula Crítica**: `Total = Subtotal - Retefuente - ReteICA`
- ⚠️ **Cálculo Automático**: Las retenciones se calculan automáticamente en `clean()`
- ⚠️ **Tolerancia de Redondeo**: Tolerancia de 100.00 para diferencias por redondeo acumulado
- ⚠️ **Validación**: El total no puede ser negativo

### 8.4. Anulación

- ⚠️ **REGLA CRÍTICA**: Solo se puede anular si está desactivado (`activo=False`)
- ⚠️ **Paso Previo**: Debe desactivarse primero antes de anular
- ⚠️ **Inmutabilidad**: La anulación no afecta los valores monetarios (snapshot inalterable)
- ⚠️ **Exclusión del Summary**: Los documentos anulados se excluyen del cálculo financiero

### 8.5. Listado

- ⚠️ **CRÍTICO**: INCLUYE TODOS LOS DOCUMENTOS (anulados y no anulados)
- Los documentos anulados DEBEN aparecer en la lista para mantener la secuencia de consecutivos
- El consecutivo prevalece en la lista, incluso si el documento está anulado
- Solo el summary excluye documentos anulados del cálculo financiero

---

## 9. Inmutabilidad y Seguridad

### 9.1. Protección de Campos Inmutables

**DocumentoSoporte:**
- `consecutivo`: `editable=False` (no editable una vez asignado)
- Campos monetarios: `read_only` en serializers
- Campos legales: `read_only` en serializers

**ResolucionDIAN:**
- Todos los campos: `read_only` en serializers (documento legal)

### 9.2. Transacciones Atómicas

- ⚠️ **Creación de Gasto**: `@transaction.atomic` en `create()`
- ⚠️ **Obtención de Consecutivo**: `@transaction.atomic` en `obtener_siguiente_numero_soporte()`
- ⚠️ **Anulación**: `@transaction.atomic` en `anular_gasto_service()`
- ⚠️ **Desactivación**: `@transaction.atomic` en `desactivar_gasto_service()`

### 9.3. Validaciones

- ⚠️ **Modelo**: `clean()` valida coherencia de totales y rango de consecutivo
- ⚠️ **Serializer**: `validate_periodo()` valida formato YYYY-MM
- ⚠️ **Service Layer**: Validaciones de negocio antes de persistir

---

## 10. Endpoints y URLs

### 10.1. Endpoints de Gasto

**Base URL:** `/api/v1/gastos/`

| Método | Endpoint | Acción | Descripción |
|--------|----------|--------|-------------|
| GET | `/api/v1/gastos/` | `list` | Lista paginada de gastos |
| GET | `/api/v1/gastos/{id}/` | `retrieve` | Detalle de un gasto |
| POST | `/api/v1/gastos/` | `create` | Crear nuevo gasto |
| DELETE | `/api/v1/gastos/{id}/` | `destroy` | Eliminar gasto |
| POST | `/api/v1/gastos/{id}/desactivar/` | `desactivar` | Desactivar gasto |
| POST | `/api/v1/gastos/{id}/anular/` | `anular` | Anular gasto |
| GET | `/api/v1/gastos/summary/` | `summary` | Resumen financiero neto |
| GET | `/api/v1/gastos/resoluciones/` | `resoluciones` | ⚠️ LEGACY: Resoluciones vigentes |
| GET | `/api/v1/gastos/resolucion-activa/` | `resolucion_activa` | ⚠️ DEPRECATED: Usar `/api/v1/resoluciones-dian/activa/` |
| POST | `/api/v1/gastos/configurar-resolucion/` | `configurar_resolucion` | ⚠️ DEPRECATED: Usar `POST /api/v1/resoluciones-dian/` |

### 10.2. Endpoints de Resolución DIAN

**Base URL:** `/api/v1/resoluciones-dian/`

| Método | Endpoint | Acción | Descripción |
|--------|----------|--------|-------------|
| GET | `/api/v1/resoluciones-dian/` | `list` | Lista paginada de resoluciones |
| GET | `/api/v1/resoluciones-dian/{id}/` | `retrieve` | Detalle de una resolución |
| POST | `/api/v1/resoluciones-dian/` | `create` | Crear nueva resolución |
| DELETE | `/api/v1/resoluciones-dian/{id}/` | `destroy` | Eliminar resolución (solo si no tiene documentos) |
| POST | `/api/v1/resoluciones-dian/{id}/desactivar/` | `desactivar` | Desactivar resolución |
| GET | `/api/v1/resoluciones-dian/activa/` | `activa` | Resolución vigente |

### 10.3. Configuración de URLs

**Archivo:** `apps/tenant/gastos/api/urls.py`

- Router DRF registra `GastoViewSet` con `basename='gastos'`
- Router DRF registra `ResolucionDIANViewSet` con `basename='resoluciones-dian'`
- URLs incluidas en `config/api_urls.py` bajo prefijos `/api/v1/gastos/` y `/api/v1/resoluciones-dian/`

---

## 11. Admin Interface

**Archivo:** `apps/tenant/gastos/admin.py`

### 11.1. ResolucionDIANAdmin

- `list_display`: `['numero_resolucion', 'prefijo', 'rango_desde', 'rango_hasta', 'fecha_resolucion', 'vigente', 'empresa']`
- `list_filter`: `['vigente', 'fecha_resolucion']`
- `search_fields`: `['numero_resolucion', 'prefijo']`
- `readonly_fields`: `['created_at', 'updated_at']`

### 11.2. DocumentoSoporteAdmin

- `list_display`: `['numero_documento', 'fecha', 'vendedor_nombre', 'vendedor_nit', 'subtotal', 'retefuente', 'reteica', 'total', 'anulado']`
- `list_filter`: `['anulado', 'fecha', 'resolucion_dian']`
- `search_fields`: `['numero_documento', 'vendedor_nombre', 'vendedor_nit', 'numero_factura_proveedor']`
- `date_hierarchy`: `'fecha'`
- `readonly_fields`: `['consecutivo', 'created_at', 'updated_at', 'numero_documento']`

### 11.3. GastoAdmin

- `list_display`: `['id', 'numero_documento', 'fecha', 'periodo', 'centro_costo', 'categoria_contable', 'total']`
- `list_filter`: `['periodo', 'centro_costo', 'categoria_contable']`
- `search_fields`: `['descripcion', 'observaciones', 'documento_soporte__numero_documento']`
- `readonly_fields`: `['created_at', 'updated_at', 'numero_documento', 'fecha', 'subtotal', 'retefuente', 'reteica', 'total']`
- Métodos personalizados: `numero_documento()`, `fecha()`, `subtotal()`, `retefuente()`, `reteica()`, `total()`

---

## 12. Choices y Configuración

### 12.1. Categorías Contables

**Archivo:** `apps/tenant/gastos/choices/categoria_contable.py`

**Choices Disponibles:**
- `ARRENDAMIENTOS`, `SERVICIOS_PUBLICOS`, `PAPELERIA_UTILES`, `MANTENIMIENTO_REPARACIONES`
- `EQUIPOS_HERRAMIENTAS`, `LICENCIAS_SOFTWARE`, `HOSTING_DOMINIO`, `TRANSPORTE_FLETES`
- `COMBUSTIBLE`, `VIATICOS`, `PUBLICIDAD_MARKETING`, `SEGUROS`
- `IMPUESTOS_TASAS`, `HONORARIOS`, `SERVICIOS_PROFESIONALES`, `ASEO_CAFETERIA`
- `VIGILANCIA_SEGURIDAD`, `CAPACITACION`, `GASTOS_FINANCIEROS`, `COMISIONES_BANCARIAS`
- `SUSCRIPCIONES`, `ELEMENTOS_PROTECCION`, `MATERIALES_INSUMOS`, `ADECUACIONES_INSTALACIONES`
- `COMUNICACIONES`, `ENERGIA`, `LIMPEZA_ASEO`, `TECNOLOGIA_INFORMATICA`
- `GASTOS_LEGALES`, `TRIBUTARIOS`, `OTROS`

**Función:** `get_categoria_contable_choices()` retorna lista de opciones

### 12.2. Centros de Costo

**Archivo:** `apps/tenant/gastos/choices/centros_costo.py`

**Choices Disponibles:**
- `ADMINISTRATIVOS`, `MATERIA_PRIMA`, `MANUTENCION`, `VIATICOS`
- `SERVICIOS_PUBLICOS`, `TRANSPORTE`, `COMUNICACIONES`, `SEGUROS`
- `ARRIENDOS`, `SERVICIOS_PROFESIONALES`, `PUBLICIDAD`, `CAPACITACION`
- `HERRAMIENTAS`, `INSUMOS`, `ENERGIA`, `LIMPEZA`
- `SEGURIDAD`, `TECNOLOGIA`, `LEGALES`, `TRIBUTARIOS`, `OTROS`

**Función:** `get_centro_costo_choices()` retorna lista de opciones

---

## 13. Optimizaciones y Performance

### 13.1. QuerySets Optimizados

**`qs_list()`:**
- Usa `select_related("documento_soporte", "empresa")` para evitar N+1 queries
- Usa `only()` para cargar solo campos necesarios
- ⚠️ **Zero Waste**: Mínimo payload, máximo rendimiento

**`qs_detail()`:**
- Usa `select_related("documento_soporte__resolucion_dian", "empresa")` para relaciones profundas

**`qs_resolucion_list()`:**
- Filtrado por empresa (SSoT)
- Ordenamiento optimizado: `['-vigente', '-fecha_resolucion']`

### 13.2. Índices de Base de Datos

**DocumentoSoporte:**
- `['empresa', 'fecha']`: Búsqueda por empresa y fecha
- `['resolucion_dian', 'consecutivo']`: Búsqueda por resolución y consecutivo
- `['prefijo', 'consecutivo']`: Búsqueda por número completo
- `['vendedor_nit', 'numero_factura_proveedor']`: Evitar duplicados
- `['activo']`, `['anulado']`: Filtrado rápido

**ResolucionDIAN:**
- `['empresa', 'vigente']`: Búsqueda rápida de resolución vigente

**Gasto:**
- `['empresa', 'periodo']`: Búsqueda por empresa y periodo
- `['centro_costo', 'categoria_contable']`: Clasificación contable
- `['documento_soporte']`: Búsqueda rápida del documento asociado

### 13.3. Paginación

- `StandardResultsSetPagination`: Paginación estándar para Tabulator
- Reduce carga de datos en listados grandes

---

## 14. Casos de Uso

### 14.1. Crear Documento Soporte

**Escenario:** Usuario necesita registrar un gasto con evidencia legal

**Pasos:**
1. Verificar que existe resolución DIAN vigente
2. Completar formulario con datos del vendedor y valores monetarios
3. Sistema calcula automáticamente retenciones
4. Sistema asigna consecutivo automáticamente
5. Sistema crea DocumentoSoporte y Gasto en transacción atómica

**Resultado:** Documento Soporte creado con número único (ej: "SI 150")

### 14.2. Anular Documento Soporte

**Escenario:** Usuario necesita anular un documento por error

**Pasos:**
1. Verificar que el documento está activo
2. Desactivar el documento (paso previo obligatorio)
3. Anular el documento (marca `anulado=True`)
4. Sistema registra fecha de anulación

**Resultado:** Documento anulado (no se incluye en cálculos financieros, pero mantiene consecutivo)

### 14.3. Configurar Resolución DIAN

**Escenario:** Usuario necesita configurar nueva resolución DIAN

**Pasos:**
1. Completar formulario con datos de la resolución
2. Marcar como vigente (opcional)
3. Sistema desactiva automáticamente resoluciones anteriores si se marca como vigente
4. Sistema valida rangos y fechas

**Resultado:** Resolución DIAN configurada y lista para usar

### 14.4. Consultar Resumen Financiero

**Escenario:** Usuario necesita ver totales de gastos

**Pasos:**
1. Frontend llama a `GET /api/v1/gastos/summary/`
2. Sistema filtra documentos activos y no anulados
3. Sistema calcula agregaciones (subtotal, retenciones, total)
4. Sistema retorna resumen financiero

**Resultado:** Resumen con totales netos excluyendo documentos anulados

---

---

## 15. Notas de Implementación

### 15.1. Cambios en v2.40

- ⚠️ **Sistema de Documento Soporte Inmutable**: Implementación completa según normativa DIAN
- ⚠️ **Separación de Responsabilidades**: DocumentoSoporte (evidencia legal) vs Gasto (clasificación contable)
- ⚠️ **Retenciones Independientes**: Retefuente y ReteICA como campos separados
- ⚠️ **Campo Activo**: Nuevo campo `activo` para desactivación previa a anulación
- ⚠️ **Resolución DIAN Independiente**: ViewSet separado para gestión de resoluciones
- ⚠️ **Optimización de QuerySets**: Uso de `only()` y `select_related()` para Zero Waste

### 15.2. Deprecaciones

- ⚠️ `GET /api/v1/gastos/resolucion-activa/`: Usar `GET /api/v1/resoluciones-dian/activa/`
- ⚠️ `POST /api/v1/gastos/configurar-resolucion/`: Usar `POST /api/v1/resoluciones-dian/`
- ⚠️ `GET /api/v1/gastos/resoluciones/`: Legacy, mantener por compatibilidad

### 15.3. Próximas Mejoras

- ⚠️ **Materialización desde DTO**: Implementar `materializar_gasto_desde_dto()` para integración con Document Ingest Pipeline
- ⚠️ **Distribución Contable**: Permitir múltiples Gastos por DocumentoSoporte (OneToMany)
- ⚠️ **Exportación PDF**: Generar PDF de Documento Soporte según formato DIAN
- ⚠️ **Migración Frontend**: Migrar `gastos.api.js` a usar Core API Facade
- ⚠️ **Feature-Sliced Architecture**: Modularizar frontend siguiendo patrón de Inventario

---

## 16. Referencias

- **Normativa DIAN**: Art. 1.6.1.4.12 DR 1625 de 2016
- **Arquitectura General**: `documentacion/arquitectura_general.md`
- **Reglas Core**: `.cursor/rules/reglas.mdc`
- **Core API Facade**: `apps/tenant/core/api/v1/gastos/`
- **Workspace Integration**: `apps/tenant/core/templates/tenant/core/workspace.html`

---

**Fin del Documento**  
**Última actualización**: 2026-03-12  
**Versión del Sistema**: 2.61.4  
**Estado**: ✅ Sincronizado con flujos completos desde workspace.html hasta models.py  
**Estado Core API**: ✅ Completo (2 ViewSets facade: GastoCoreViewSet, ResolucionDIANCoreViewSet)  
**Estado Frontend**: ✅ Tabulator Factory + HTMX + Bootstrap Offcanvas  
**Estado Endpoints**: ✅ Core API Facade disponible, App API directa también disponible
