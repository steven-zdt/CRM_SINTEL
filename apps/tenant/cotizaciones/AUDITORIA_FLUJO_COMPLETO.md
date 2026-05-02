# Auditoria Completa: Flujo y Funcionalidad - App Cotizaciones

**Version:** 2.61.8  
**Fecha:** 2026-01-27  
**Ultima actualizacion:** 2026-02-07  
**Ubicacion:** `apps/tenant/cotizaciones/`

---

## Indice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura General](#arquitectura-general)
3. [Estructura de Directorios](#estructura-de-directorios)
4. [Modelos y Relaciones](#modelos-y-relaciones)
5. [Servicios y Logica de Negocio](#servicios-y-logica-de-negocio)
6. [APIs y Endpoints](#apis-y-endpoints)
7. [Serializers](#serializers)
8. [Vistas UI](#vistas-ui)
9. [Servicio de PDF](#servicio-de-pdf)
10. [Permisos y Seguridad](#permisos-y-seguridad)
11. [Frontend y JavaScript](#frontend-y-javascript)
12. [Flujos Completos](#flujos-completos)
13. [Flujo Completo: Workspace a Core API a Models](#flujo-completo-workspace-a-core-api-a-models)
14. [Dependencias y Aislamiento](#dependencias-y-aislamiento)
15. [Registro de Bugs y Correcciones v2.61.8](#registro-de-bugs-v2618)

---

## Resumen Ejecutivo

La app **Cotizaciones** es un modulo completo y autonomo para la gestion de cotizaciones comerciales. Implementa:

- **Arquitectura Resiliente**: Funciona incluso si otras apps fallan
- **Service Layer Package**: Logica de negocio modularizada en `services/` (business_service.py, crud_service.py, selectors.py, api_mixins.py)
- **API-First**: Endpoints REST completos con DRF (Gateway Directo)
- **DNA Dinamico**: Configuracion por perfiles (plantillas)
- **Generacion de PDF**: Exportacion profesional de cotizaciones
- **Numeracion Automatica**: Codigos unicos por perfil con folios dinamicos
- **Calculos Financieros**: IVA, AIU, utilidades
- **Frontend FSD Modular**: `window.Sintel.Cotizaciones` con 10 modulos JS especializados (v2.61.8)
- **TabulatorFactory**: Tablas interactivas con paginacion remota, JWT Dual-Auth y search binding

### Caracteristicas Principales

- **Desacoplamiento Radical**: No depende de otras apps excepto SSoT (Empresa)
- **Snapshot Pattern**: Datos reales guardados en items (resiliencia)
- **DNA Inheritance**: Valores heredados de plantillas (integridad historica)
- **Multi-tenant**: Aislamiento completo por empresa
- **Gateway Directo**: Consumo frontend via `/api/v1/cotizaciones/` sin facades (v2.61.8)
- **Tab-Activated Pattern**: Redraw de Tabulator al cambiar tab en workspace (v2.61.8)

---

## Arquitectura General

### Principios de Diseno

1. **Resiliencia**: Si el modulo de Clientes falla, las cotizaciones persisten
2. **SSoT (Single Source of Truth)**: Empresa se obtiene del tenant, nunca del payload
3. **Service Layer Package**: Logica modularizada en `services/` (business, crud, selectors, mixins)
4. **Zero Trust**: Validacion exhaustiva + DSV en business_service
5. **API-First**: Backend DRF + Frontend TabulatorFactory
6. **Error Boundary Pattern**: Manejo de errores centralizado (UIManager en frontend)
7. **Feature-Sliced Design (FSD)**: JavaScript modular bajo `window.Sintel.Cotizaciones`
8. **Gateway Directo**: Frontend consume `/api/v1/cotizaciones/` directamente (v2.61.8)
9. **Tab-Activated Pattern**: Inicializacion diferida y redraw al activar tab (v2.61.8)

### Flujo de Datos

```
Frontend (TabulatorFactory + Sintel.Cotizaciones)
    |
Gateway Directo (/api/v1/cotizaciones/)
    |
API Endpoints (DRF ViewSets + ServiceMixin)
    |
Serializers (Validacion sintactica)
    |
Business Service (Logica de Negocio + DSV)
    |
CRUD Service (Persistencia transaccional)
    |
Models (ORM)
    |
Database (PostgreSQL multi-tenant)
```

---

## Estructura de Directorios

```
apps/tenant/cotizaciones/
|-- __init__.py
|-- admin.py
|-- apps.py
|-- models.py                      # Modelos: Cotizacion, CotizacionItem, Producto, Servicio
|-- permissions.py                 # Permisos personalizados
|-- pdf_service.py                 # Generacion de PDFs
|-- ui_views.py                    # Vistas UI (templates HTML)
|-- AUDITORIA_FLUJO_COMPLETO.md   # Este archivo (SSoT documental)
|
|-- api/                           # APIs REST (DRF)
|   |-- __init__.py
|   |-- viewsets.py                # CotizacionViewSet, CotizacionItemViewSet
|   |-- serializers.py             # Serializers DRF
|   |-- urls.py                    # URLs API + UI
|   |-- pagination.py              # Paginacion personalizada
|   +-- pdf_viewsets.py            # ViewSets para PDF
|
|-- services/                      # [v2.61.8] Service Layer Package (modularizado)
|   |-- __init__.py                # Exports principales
|   |-- business_service.py        # CotizacionService: logica de negocio + DSV
|   |-- crud_service.py            # CotizacionCRUDService: persistencia transaccional
|   |-- selectors.py               # CotizacionSelector: consultas GET optimizadas
|   |-- api_mixins.py              # CotizacionServiceMixin: inyeccion en ViewSets
|   +-- services.py                # Reexport legacy para compatibilidad
|
|-- configuracion/                 # Modulo de Configuracion/Plantillas
|   |-- __init__.py
|   |-- models.py                  # ConfiguracionCotizacion
|   |-- serializers.py             # Serializers de configuracion
|   +-- viewsets.py                # ViewSet de configuracion
|
|-- static/cotizaciones/           # [v2.61.8] Assets FSD (SSoT frontend)
|   |-- css/
|   |   +-- cotizaciones.css       # Estilos dedicados
|   +-- js/
|       |-- cotizaciones.module.js  # 1. Namespace bootstrap
|       |-- cotizaciones.api.js     # 2. SSoT URLs + getHeaders()
|       |-- cotizaciones.utils.js   # 3. Funciones puras (formateo, validacion)
|       |-- cotizaciones.table.js   # 4. TabulatorFactory + columnas
|       |-- cotizaciones.ui.js      # 5. DOM Shield + Offcanvas lifecycle
|       |-- cotizaciones.list.js    # 6. Refresh helper
|       |-- cotizaciones.editor.js  # 7. HTMX crear/editar offcanvas
|       |-- cotizaciones.detalle.js # 8. HTMX detalle offcanvas
|       |-- cotizaciones.main.js    # 9. Orquestador (tab-activated)
|       +-- features/
|           +-- cotizacion_list.js  # DEPRECATED: Aliases compat -> Main/table
|
|-- templates/cotizaciones/         # [v2.61.8] Templates FSD
|   |-- assets_cotizaciones.html   # Inclusion de scripts (cargado desde workspace.html)
|   +-- list.html                  # Listado con search input + delete modal
|
|-- management/commands/
|   +-- limpiar_cotizaciones.py    # Comando limpieza (DESTRUCTIVO)
|
+-- migrations/
    |-- 0001_initial_v2_60.py
    |-- 0002_add_usa_aiu_to_configuracion.py
    |-- 0003_add_folios_dinamicos_to_configuracion.py
    |-- 0004_alter_cotizacion_cliente_nombre_manual.py
    |-- 0005_remove_cotizacion_cliente_nombre_manual.py
    +-- 0006_configuracioncotizacion_tipo_cotizacion_default_and_more.py
```

### Sistema Legacy (Deprecated - solo compatibilidad)

```
apps/tenant/core/static/core/js/cotizaciones/    # LEGACY (v2.60)
|-- cotizaciones.page.js           # Modulo principal legacy (~1334 lineas)
|-- cotizaciones.api.js            # API wrapper legacy
|-- cotizaciones.helpers.js        # Helpers
|-- cotizacion_factory.js          # Factory
|-- cotizacion_columns.js          # Columnas Tabulator
|-- cotizacion_mutators.js         # Mutators
|-- htmx-handlers.js               # HTMX handlers
+-- features/                      # Features legacy
    |-- cotizacion_crear.js
    |-- cotizacion_editar.js
    |-- cotizacion_detalle.js
    |-- cotizacion_editor.js       # DEPRECATED
    |-- plantillas_list.js
    |-- plantilla_crear.js
    |-- plantilla_editar.js
    +-- plantilla_ver.js
```

**NOTA v2.61.8:** workspace.html carga los assets modernos (`cotizaciones/assets_cotizaciones.html`), no los legacy. El sistema legacy se mantiene con patch `tab-activated` para safety net.

---

## 🗄️ Modelos y Relaciones

### 1. `Cotizacion` (Modelo Principal)

**Ubicación:** `apps/tenant/cotizaciones/models.py`

**Propósito:** Representa una cotización comercial completa.

#### Campos Principales

##### Identificación
- `uuid`: UUID único (lookup field para APIs)
- `numero_cotizacion`: Número de cotización (string, único por empresa+perfil)
- `codigo_unico`: Código único generado automáticamente (ej: "STS. 0422-2026")
- `empresa`: ForeignKey a Empresa (SSoT)

##### Relaciones Opcionales (Resiliencia)
- `cliente`: ForeignKey a Cliente (SET_NULL) - Puede ser null si falla
- `configuracion`: ForeignKey a ConfiguracionCotizacion (SET_NULL) - Perfil usado

##### Estado y Fechas
- `tipo_cotizacion`: CharField (MIXTO, PRODUCTOS, SERVICIOS, MATERIALES)
- `estado`: CharField (BORRADOR, ENVIADA, ACEPTADA)
- `fecha_emision`: DateField (auto_now_add)
- `fecha_vencimiento`: DateField

##### DNA Financiero (Heredado de Plantilla)
- `porcentaje_aiu_admin`: Decimal (copiado del perfil)
- `porcentaje_aiu_imprevistos`: Decimal (copiado del perfil)
- `porcentaje_aiu_utilidad`: Decimal (copiado del perfil)
- `iva_porcentaje`: Decimal (copiado del perfil, default 19.00)
- `total_con_impuestos`: Decimal (calculado por Service)

#### Constraints

```python
# Unicidad de numero_cotizacion por empresa y perfil
UniqueConstraint(
    fields=['empresa', 'configuracion', 'numero_cotizacion'],
    name='unique_numero_cotizacion_por_perfil'
)
```

#### Relaciones

- `items`: RelatedManager → `CotizacionItem` (one-to-many)
- `configuracion`: ForeignKey → `ConfiguracionCotizacion`
- `cliente`: ForeignKey → `Cliente` (opcional)

---

### 2. `CotizacionItem` (Items de Cotización)

**Ubicación:** `apps/tenant/cotizaciones/models.py`

**Propósito:** Representa un item individual dentro de una cotización.

#### Campos Principales

##### Relaciones
- `cotizacion`: ForeignKey a Cotizacion (CASCADE)
- `producto`: ForeignKey a Producto (SET_NULL, opcional)
- `servicio`: ForeignKey a Servicio (SET_NULL, opcional)

##### Tipo de Item
- `tipo_item`: CharField (PRODUCTO, MATERIAL, SERVICIO)

##### Snapshot (Datos Reales)
- `descripcion`: TextField (lo que se imprime)
- `marca`: CharField (snapshot)
- `referencia`: CharField (snapshot)
- `unidad`: CharField (UND, MTR, GLN, etc.)

##### Cálculos
- `cantidad`: Decimal
- `costo_unitario`: Decimal
- `porcentaje_utilidad`: Decimal
- `precio_unitario_venta`: Decimal (calculado en save())
- `subtotal_linea`: Decimal (calculado en save())
- `orden`: PositiveIntegerField (secuencia)

#### Lógica de Cálculo (en save())

```python
def save(self, *args, **kwargs):
    factor_utilidad = Decimal('1.00') + (self.porcentaje_utilidad / Decimal('100.00'))
    self.precio_unitario_venta = self.costo_unitario * factor_utilidad
    self.subtotal_linea = self.cantidad * self.precio_unitario_venta
    super().save(*args, **kwargs)
```

**Nota:** El cálculo completo de totales se hace en `CotizacionService.calcular_totales()`

---

### 3. `Producto` (Catálogo de Productos)

**Ubicación:** `apps/tenant/cotizaciones/models.py`

**Propósito:** Catálogo interno de productos/equipos.

#### Campos
- `empresa`: ForeignKey a Empresa
- `codigo`: CharField (código interno)
- `nombre`: CharField
- `marca`: CharField
- `referencia`: CharField
- `unidad`: CharField (default: 'UND')
- `precio_venta`: Decimal
- `activo`: BooleanField

**Uso:** Referencia opcional en `CotizacionItem` (snapshot se guarda en item)

---

### 4. `Servicio` (Catálogo de Servicios)

**Ubicación:** `apps/tenant/cotizaciones/models.py`

**Propósito:** Catálogo interno de servicios.

#### Campos
- `empresa`: ForeignKey a Empresa
- `nombre`: CharField
- `precio_venta`: Decimal
- `activo`: BooleanField

**Uso:** Referencia opcional en `CotizacionItem` (snapshot se guarda en item)

---

### 5. `ConfiguracionCotizacion` (Perfil/Plantilla)

**Ubicación:** `apps/tenant/cotizaciones/configuracion/models.py`

**Propósito:** Define el "DNA" de una cotización (valores por defecto, estructura).

#### Campos Principales

##### Identificación
- `empresa`: ForeignKey a Empresa (SSoT)
- `nombre_configuracion`: CharField (único por empresa)
- `tipo_plantilla`: CharField (EQUIPO, MATERIAL, SERVICIO, MIXTO)
- `tipo_cotizacion_default`: CharField (MIXTO, PRODUCTOS, SERVICIOS, MATERIALES)
- `es_activo`: BooleanField

##### DNA Financiero por Defecto
- `iva_porcentaje_default`: Decimal (default: 19.00)
- `porcentaje_utilidad_default`: Decimal (default: 10.00)

##### AIU Opcional
- `usa_aiu`: BooleanField (default: False)
- `aiu_admin_default`: Decimal (default: 0)
- `aiu_imprevistos_default`: Decimal (default: 0)
- `aiu_utilidad_default`: Decimal (default: 0)

##### Flags de Interfaz (DNA Dinámico)
- `permitir_modelo_equipos`: BooleanField (default: True)
- `permitir_modelo_materiales`: BooleanField (default: True)
- `permitir_modelo_servicios`: BooleanField (default: True)

##### Gestión de Folios Dinámicos
- `prefijo_secuencia`: CharField (ej: "STS. ")
- `sufijo_secuencia`: CharField (ej: "-2026")
- `semilla_inicial`: IntegerField (default: 1)
- `ultimo_numero`: IntegerField (default: 0) - Último número generado

#### Relaciones

- `cotizaciones`: RelatedManager → `Cotizacion` (one-to-many)

---

## Servicios y Logica de Negocio

### Service Layer Package (v2.61.8)

**Ubicacion:** `apps/tenant/cotizaciones/services/`

La logica de negocio esta modularizada en un paquete `services/` con responsabilidades estrictas:

| Archivo | Clase | Responsabilidad |
|---------|-------|-----------------|
| `business_service.py` | `CotizacionService` | Logica de negocio, DSV, calculos, idempotencia |
| `crud_service.py` | `CotizacionCRUDService` | Persistencia transaccional (`@transaction.atomic`) |
| `selectors.py` | `CotizacionSelector`, `CotizacionItemSelector` | Consultas GET optimizadas con `.only()` |
| `api_mixins.py` | `CotizacionServiceMixin`, `CotizacionItemServiceMixin` | Inyeccion de servicios en ViewSets |
| `services.py` | (reexport) | Compatibilidad legacy |
| `__init__.py` | (exports) | Punto de entrada del paquete |

### `CotizacionSelector` (selectors.py)

**Constantes SSoT de campos:**
- `LIST_FIELDS`: 9 campos para listado (numero_cotizacion, estado, fecha_emision, etc.)
- `LIST_FK_FIELDS`: 2 campos FK para listado (cliente, configuracion)
- `DETAIL_FIELDS`: 15 campos para detalle
- `DETAIL_FK_FIELDS`: 2 campos FK para detalle
- `ITEM_LIST_FIELDS`: 13 campos para items

**Metodos:**
- `get_list(empresa_id, search, estado, cliente)` -> QuerySet con `.only(LIST_FIELDS)`
- `get_detail(cotizacion_id, empresa_id)` -> QuerySet completo si pk=None, instancia si pk dado (v2.61.8 fix)

### `CotizacionService` (business_service.py)

**Propósito:** Cálculo estandarizado para una línea de item.

**Parámetros:**
- `cantidad`: Decimal
- `costo`: Decimal
- `utilidad`: Decimal (porcentaje)

**Retorna:**
```python
{
    'precio_unitario': Decimal,  # costo * (1 + utilidad/100)
    'subtotal': Decimal          # cantidad * precio_unitario
}
```

**Uso:** Llamado desde Tabulator (frontend) y serializers (backend)

---

##### 2. `crear_preforma(empresa, datos)`

**Propósito:** Crear una cotización completa con DNA de plantilla.

**Flujo:**
1. Validar que `configuracion` (perfil) esté presente
2. Obtener perfil y validar que pertenezca a la empresa (SSoT)
3. Validar que `cliente` esté presente y pertenezca a la empresa
4. Generar `codigo_unico` automáticamente si no se proporciona `numero_cotizacion`
5. Copiar valores del perfil a la cotización (DNA Inheritance):
   - `iva_porcentaje_default` → `iva_porcentaje`
   - `aiu_*_default` → `porcentaje_aiu_*`
   - `tipo_cotizacion_default` → `tipo_cotizacion`
6. Crear instancia de `Cotizacion`
7. Retornar cotización creada

**Características:**
- ⚠️ **Transaccional**: Todo o nada (`@transaction.atomic`)
- ⚠️ **DNA Inheritance**: Valores copiados, no referenciados (integridad histórica)
- ⚠️ **Resiliente**: Funciona incluso si cliente falla (pero cliente es obligatorio)

---

##### 3. `generar_codigo_unico(perfil_id, empresa_id)`

**Propósito:** Genera código único automático basado en el perfil.

**Lógica:**
1. Obtener perfil y validar pertenencia a empresa
2. Bloquear fila del perfil (`select_for_update()`) para evitar race conditions
3. Si `ultimo_numero == 0`: Usar `semilla_inicial`
4. Si `ultimo_numero > 0`: Incrementar `ultimo_numero` atómicamente (F() expression)
5. Formatear número con ceros a la izquierda (4 dígitos mínimo)
6. Construir código: `prefijo + numero_formateado + sufijo`
7. Actualizar `ultimo_numero` en el perfil

**Ejemplo:**
- Prefijo: "STS. "
- Sufijo: "-2026"
- Semilla: 1
- Resultado: "STS. 0001-2026"

**Características:**
- ⚠️ **Thread-safe**: Usa `select_for_update()` y `F()` expressions
- ⚠️ **Atómico**: Transacción completa

---

##### 4. `calcular_totales(cotizacion_id)`

**Propósito:** Calcula todos los totales de una cotización (SSoT).

**Lógica:**
1. Obtener cotización con items
2. Calcular subtotal: Suma de `subtotal_linea` de todos los items
3. Calcular IVA:
   - Si `usa_aiu = True`: IVA sobre (subtotal + AIU)
   - Si `usa_aiu = False`: IVA sobre subtotal
4. Calcular AIU (si está activo):
   - `aiu_admin` = subtotal * (aiu_admin_porcentaje / 100)
   - `aiu_imprevistos` = subtotal * (aiu_imprevistos_porcentaje / 100)
   - `aiu_utilidad` = subtotal * (aiu_utilidad_porcentaje / 100)
   - `aiu_total` = suma de los tres
5. Calcular total final: `subtotal + aiu_total + iva`
6. Actualizar `total_con_impuestos` en la cotización

**Retorna:**
```python
{
    'subtotal': Decimal,
    'iva': Decimal,
    'aiu_total': Decimal,
    'total_con_impuestos': Decimal
}
```

**Características:**
- ⚠️ **SSoT**: Única fuente de verdad para cálculos
- ⚠️ **Persistente**: Actualiza la cotización en BD

---

##### 5. `get_editor_config(perfil_id, empresa_id)`

**Propósito:** Obtiene configuración completa del editor (SSoT).

**Retorna:**
```python
{
    'tipo_plantilla': str,
    'tipo_cotizacion_default': str,
    'permitir_modelo_equipos': bool,
    'permitir_modelo_materiales': bool,
    'permitir_modelo_servicios': bool,
    'iva_porcentaje_default': str,
    'usa_aiu': bool,
    'aiu_admin_default': str,
    'aiu_imprevistos_default': str,
    'aiu_utilidad_default': str
}
```

**Uso:** Consumido por `ConfiguracionCotizacionDetailSerializer.to_representation()`

---

## 🌐 APIs y Endpoints

### Estructura de URLs

**Archivo:** `apps/tenant/cotizaciones/api/urls.py`

#### APIs REST (DRF Router)

```
/api/v1/cotizaciones/
├── GET    /                          # Lista cotizaciones (paginado)
├── POST   /                          # Crea cotización
├── GET    /{uuid}/                   # Obtiene cotización
├── PATCH  /{uuid}/                   # Actualiza cotización
├── DELETE /{uuid}/                   # Elimina cotización
├── POST   /{uuid}/recalcular/        # Recalcula totales
│
├── GET    /items/                    # Lista items
├── POST   /items/                    # Crea item
├── GET    /items/{id}/               # Obtiene item
├── PATCH  /items/{id}/               # Actualiza item
├── DELETE /items/{id}/               # Elimina item
│
└── GET    /configuracion/            # Lista plantillas
    POST   /configuracion/            # Crea plantilla
    GET    /configuracion/{id}/       # Obtiene plantilla
    PATCH  /configuracion/{id}/       # Actualiza plantilla
    DELETE /configuracion/{id}/       # Elimina plantilla
    POST   /configuracion/{id}/activar/  # Activa plantilla
```

#### URLs UI (HTMX) - ⚠️ v2.61: Nuevos Endpoints RESTful

**⚠️ v2.61:** Nuevos endpoints `render-offcanvas/*` alineados con patrón de contabilidad:

```
/api/v1/cotizaciones/
├── render-offcanvas/crear/          # GET - Cargar offcanvas para crear
├── {uuid}/render-offcanvas/editar/  # GET - Cargar offcanvas para editar
├── render-offcanvas/detalle/?id={uuid}  # GET - Cargar offcanvas para ver detalle
└── estadisticas/                    # GET - Obtener estadísticas (⚠️ v2.61.1)
```

**URLs UI Legacy (Deprecadas):**
```
/cotizaciones/
├── editor/<uuid>/                   # DEPRECATED - Usar render-offcanvas/editar
├── editor/draft/                    # DEPRECATED - Usar render-offcanvas/crear
│
└── partials/configuracion/
    ├── lista/                       # Lista de plantillas
    ├── crear/                       # Crear plantilla
    ├── editar/<id>/                 # Editar plantilla
    └── ver/<id>/                    # Ver detalle plantilla
```

---

### ViewSets

#### 1. `CotizacionViewSet`

**Ubicación:** `apps/tenant/cotizaciones/api/viewsets.py`

**Propósito:** CRUD completo de cotizaciones.

**Características:**
- Lookup por `uuid` (no por `id`)
- Paginación: `StandardResultsSetPagination`
- Búsqueda: `?search=` (filtra por número o cliente)
- Filtrado por empresa del tenant (SSoT)

**Métodos Personalizados:**
- `recalcular(uuid)`: POST para recalcular totales
- `render_offcanvas_crear()`: GET para cargar offcanvas de creación (⚠️ v2.61)
- `render_offcanvas_editar(uuid)`: GET para cargar offcanvas de edición (⚠️ v2.61)
- `render_offcanvas_detalle()`: GET para cargar offcanvas de detalle (⚠️ v2.61)
- `estadisticas()`: GET para obtener estadísticas de cotizaciones (⚠️ v2.61.1)
  - Retorna: `total_neto`, `cantidad_total`, `cantidad_aceptadas`, `cantidad_enviadas`, `cantidad_borrador`

**Flujo de Creación:**
1. `create()` → Valida serializer
2. `serializer.create()` → Llama a `CotizacionService.crear_preforma()`
3. Crea items si vienen en payload
4. Calcula totales con `CotizacionService.calcular_totales()`
5. Retorna cotización serializada

---

#### 2. `CotizacionItemViewSet`

**Ubicación:** `apps/tenant/cotizaciones/api/viewsets.py`

**Propósito:** CRUD de items individuales.

**Características:**
- Filtrado por empresa del tenant (SSoT)
- Recalcula totales automáticamente después de crear/actualizar/eliminar

**Hooks:**
- `perform_create()`: Recalcula totales después de crear
- `perform_update()`: Recalcula totales después de actualizar
- `perform_destroy()`: Recalcula totales después de eliminar

---

#### 3. `ConfiguracionCotizacionViewSet`

**Ubicación:** `apps/tenant/cotizaciones/configuracion/viewsets.py`

**Propósito:** CRUD de perfiles de configuración.

**Características:**
- Lookup por `id` (no UUID)
- Serializer ligero para `list()`, completo para `detail()`
- Filtrado por empresa del tenant (SSoT)
- Búsqueda: `?search=` (filtra por nombre)
- Filtro: `?solo_activos=true` (solo plantillas activas)

**Métodos Personalizados:**
- `activar(id)`: POST para activar plantilla

---

## 📝 Serializers

### 1. `CotizacionSerializer`

**Ubicación:** `apps/tenant/cotizaciones/api/serializers.py`

**Propósito:** Serialización de cotizaciones.

#### Campos Principales

##### Read-Only
- `uuid`: UUID único
- `empresa`: Empresa (asignada automáticamente)
- `fecha_emision`: Fecha de emisión
- `total_con_impuestos`: Total calculado
- `estado_display`: Estado formateado
- `cliente_display`: Nombre del cliente
- `configuracion_nombre`: Nombre del perfil
- `codigo_unico`: Código único generado

##### Write-Only (Creación)
- `cliente`: ID del cliente (obligatorio, PrimaryKeyRelatedField)
- `configuracion`: ID del perfil (obligatorio, PrimaryKeyRelatedField)
- `numero_cotizacion`: Opcional (se genera automáticamente si está vacío)
- `fecha_vencimiento`: Fecha de vencimiento
- `items`: Array de items (opcional en creación)

#### Validaciones

##### `validate()`
1. Validar que `configuracion` exista y pertenezca a la empresa
2. Validar que `cliente` exista y pertenezca a la empresa
3. Validar unicidad de `numero_cotizacion` por empresa y perfil

##### `create()`
1. Obtener empresa del tenant (SSoT)
2. Extraer items del payload
3. Llamar a `CotizacionService.crear_preforma()`
4. Crear items si vienen en payload
5. Calcular totales con `CotizacionService.calcular_totales()`
6. Retornar cotización creada

---

### 2. `CotizacionItemSerializer`

**Ubicación:** `apps/tenant/cotizaciones/api/serializers.py`

**Propósito:** Serialización de items.

#### Campos

##### Read-Only
- `precio_unitario_venta`: Calculado
- `subtotal_linea`: Calculado

##### Write
- `cotizacion`: ID de cotización
- `tipo_item`: Tipo (PRODUCTO, MATERIAL, SERVICIO)
- `producto`: ID de producto (opcional)
- `servicio`: ID de servicio (opcional)
- `descripcion`: Descripción
- `marca`: Marca
- `referencia`: Referencia
- `unidad`: Unidad
- `cantidad`: Cantidad
- `costo_unitario`: Costo unitario
- `porcentaje_utilidad`: Porcentaje de utilidad
- `porcentaje_iva`: Porcentaje de IVA a nivel de ítem (write_only, opcional)
- `orden`: Orden

---

### 3. `ConfiguracionCotizacionListSerializer`

**Ubicación:** `apps/tenant/cotizaciones/configuracion/serializers.py`

**Propósito:** Serializer ligero para listados (Tabulator).

#### Campos
- `id`, `empresa`, `empresa_nombre`
- `nombre_configuracion`
- `tipo_plantilla`, `tipo_plantilla_display`
- `es_activo`, `estado_display`
- `iva_porcentaje_default`
- `porcentaje_utilidad_default`
- `usa_equipos`, `usa_materiales`, `usa_mano_obra` (banderas calculadas)

---

### 4. `ConfiguracionCotizacionDetailSerializer`

**Ubicación:** `apps/tenant/cotizaciones/configuracion/serializers.py`

**Propósito:** Serializer completo para CRUD.

#### Campos Adicionales (vs List)
- `tipo_cotizacion_default`
- `usa_aiu`
- `aiu_admin_default`, `aiu_imprevistos_default`, `aiu_utilidad_default`
- `permitir_modelo_equipos`, `permitir_modelo_materiales`, `permitir_modelo_servicios`
- `prefijo_secuencia`, `sufijo_secuencia`, `semilla_inicial`
- `ultimo_numero` (read-only)
- `usa_equipos`, `usa_materiales`, `usa_mano_obra` (banderas calculadas)

#### `to_representation()`
Agrega `editor_config` con configuración completa del editor desde `CotizacionService.get_editor_config()`

#### Validaciones

##### `validate_nombre_configuracion()`
- Sanitización: strip y normalización de espacios
- Longitud: mínimo 3, máximo 100 caracteres

##### `validate_iva_porcentaje_default()`
- No negativo
- Máximo 100%

##### `validate_porcentaje_utilidad_default()`
- No negativo

##### `validate_aiu_*_default()`
- No negativo

##### `validate()`
1. Validar unicidad de `nombre_configuracion` por empresa
2. Validar que al menos un modelo esté habilitado
3. Si `usa_aiu = True`: Validar que al menos un porcentaje AIU sea > 0

---

## 🖥️ Vistas UI

**Ubicación:** `apps/tenant/cotizaciones/ui_views.py` y `apps/tenant/cotizaciones/api/viewsets.py`

**Propósito:** Renderizado de templates HTML (UI Shells) y endpoints HTMX RESTful.

### ⚠️ v2.61: Nuevos Endpoints HTMX RESTful (Alineados con Patrón de Contabilidad)

#### Endpoints `render-offcanvas/*` en `CotizacionViewSet`

**Ubicación:** `apps/tenant/cotizaciones/api/viewsets.py`

##### 1. `render_offcanvas_crear`
- **Método:** `GET`
- **URL:** `/api/v1/cotizaciones/render-offcanvas/crear/`
- **Template:** `tenant/core/partials/cotizaciones/editor_cotizacion.html`
- **Contexto:** 
  - `cotizacion`: `None`
  - `is_draft`: `True`
  - `clientes`: Lista de clientes activos
  - `configuraciones`: Lista de configuraciones activas
- **Propósito:** Cargar offcanvas para crear nueva cotización

##### 2. `render_offcanvas_editar`
- **Método:** `GET`
- **URL:** `/api/v1/cotizaciones/{uuid}/render-offcanvas/editar/`
- **Template:** `tenant/core/partials/cotizaciones/offcanvas_editar_cotizacion.html`
- **Contexto:**
  - `cotizacion`: Objeto Cotizacion (por UUID o ID numérico)
  - `is_draft`: `False`
  - `clientes`: Lista de clientes activos
  - `configuraciones`: Lista de configuraciones activas
- **Propósito:** Cargar offcanvas para editar cotización existente
- **Nota:** Soporta tanto UUID como ID numérico para compatibilidad

##### 3. `render_offcanvas_detalle`
- **Método:** `GET`
- **URL:** `/api/v1/cotizaciones/render-offcanvas/detalle/?id={uuid}`
- **Template:** `tenant/core/partials/cotizaciones/offcanvas_ver_detalle.html`
- **Contexto:**
  - `cotizacion`: Objeto Cotizacion (por UUID o ID numérico)
  - `clientes`: Lista de clientes activos
  - `configuraciones`: Lista de configuraciones activas
- **Propósito:** Cargar offcanvas para ver detalle de cotización (read-only)
- **Query Params:** `id` (requerido, puede ser UUID o ID numérico)

### Vistas UI Legacy (Deprecadas para Cotizaciones)

**⚠️ v2.61:** Las siguientes vistas UI se mantienen para compatibilidad pero se recomienda usar los nuevos endpoints `render-offcanvas/*`:

#### 1. `CotizacionEditorTemplateView` (DEPRECATED)
- **Template:** `tenant/core/partials/cotizaciones/editor_cotizacion.html`
- **URL:** `/cotizaciones/editor/<uuid>/`
- **Reemplazo:** Usar `render_offcanvas_editar`

#### 2. `CotizacionEditorDraftView` (DEPRECATED)
- **Template:** `tenant/core/partials/cotizaciones/editor_cotizacion.html`
- **URL:** `/cotizaciones/editor/draft/`
- **Reemplazo:** Usar `render_offcanvas_crear`

### Vistas UI para Configuraciones (Activas)

#### 3. `ConfiguracionListOffcanvasView`
- **Template:** `tenant/core/partials/cotizaciones/offcanvas_list_plantillas.html`
- **URL:** `/cotizaciones/partials/configuracion/lista/`

#### 4. `ConfiguracionCrearOffcanvasView`
- **Template:** `tenant/core/partials/cotizaciones/offcanvas_plantilla_crear.html`
- **URL:** `/cotizaciones/partials/configuracion/crear/`

#### 5. `ConfiguracionEditarOffcanvasView`
- **Template:** `tenant/core/partials/cotizaciones/offcanvas_plantilla_editar.html`
- **URL:** `/cotizaciones/partials/configuracion/editar/<id>/`
- **Contexto:** Configuración con ID

#### 6. `ConfiguracionVerOffcanvasView`
- **Template:** `tenant/core/partials/cotizaciones/offcanvas_ver_detalle.html`
- **URL:** `/cotizaciones/partials/configuracion/ver/<id>/`

**Nota:** Todas las vistas cargan clientes y configuraciones activas en el contexto.

---

## 📄 Servicio de PDF

**Ubicación:** `apps/tenant/cotizaciones/pdf_service.py`

**Propósito:** Generación profesional de PDFs de cotizaciones.

### Funciones Principales

#### 1. `obtener_secciones_render(items, perfil_configuracion)`

**Propósito:** Agrupa items por sección según `seccion_modulo`.

**Lógica:**
- Crea diccionario estático con 3 secciones: "1.0", "2.0", "3.0"
- Filtra items por `seccion_modulo` (normaliza a "1", "2", "3")
- Determina visibilidad según `permitir_modelo_*` del perfil
- Retorna solo secciones activas

**Retorna:**
```python
{
    "1.0": {
        "titulo": "Dispositivos y Equipos",
        "items": [...],
        "mostrar": bool
    },
    "2.0": {...},
    "3.0": {...}
}
```

---

#### 2. `calcular_totales(seccion_1, seccion_2, seccion_3, cotizacion)`

**Propósito:** Calcula totales para resumen económico.

**Lógica:**
1. Suma subtotales por sección
2. Calcula subtotal total
3. Si `usa_aiu = True`:
   - Calcula AIU sobre subtotal
   - Calcula IVA sobre (subtotal + AIU)
4. Si `usa_aiu = False`:
   - Calcula IVA sobre subtotal
5. Calcula total final

**Retorna:** Diccionario con todos los valores calculados

---

#### 3. `preparar_contexto_pdf(cotizacion, empresa, request, perfil_id)`

**Propósito:** Prepara contexto completo para template PDF.

**Flujo:**
1. Obtiene items con prefetch optimizado
2. Obtiene perfil de configuración
3. Agrupa items por sección
4. Calcula totales
5. Sanitiza textos
6. Construye contexto completo

---

#### 4. `generar_pdf_bytes(context, request)`

**Propósito:** Genera PDF a partir de contexto.

**Flujo:**
1. Renderiza template HTML
2. Convierte HTML a PDF (WeasyPrint eliminado - usar biblioteca alternativa)
3. Retorna bytes del PDF

---

## 🔐 Permisos y Seguridad

**Ubicación:** `apps/tenant/cotizaciones/permissions.py`

### Clases de Permisos

#### 1. `IsCotizacionesMember`
- Verifica autenticación
- Verifica existencia de empresa (SSoT)
- Permite acceso a usuarios autenticados del tenant

#### 2. `IsCotizacionesAdminOrReadOnly`
- Lectura: Usuarios autenticados del tenant
- Escritura: Usuarios autenticados del tenant (no solo admin)

#### 3. `IsCotizacionesConfigAllowed`
- Permite acceso a configuración para usuarios autenticados

**Nota:** Todos los permisos verifican pertenencia al tenant mediante existencia de empresa (SSoT).

---

## Frontend y JavaScript

### v2.61.8: Arquitectura FSD Moderna (SSoT)

**Ubicacion SSoT:** `apps/tenant/cotizaciones/static/cotizaciones/js/`
**Namespace:** `window.Sintel.Cotizaciones`
**Carga:** `workspace.html` incluye `cotizaciones/assets_cotizaciones.html`

#### Modulos JS (10 archivos, orden de carga estricto)

| # | Archivo | Responsabilidad |
|---|---------|-----------------|
| 1 | `cotizaciones.module.js` | Namespace bootstrap: `window.Sintel.Cotizaciones = {}` |
| 2 | `cotizaciones.api.js` | SSoT URLs + `getHeaders()` con JWT Bearer token |
| 3 | `cotizaciones.utils.js` | Funciones puras: `parseFloatSafe`, `fmtMoney` (COP), `formatDate` |
| 4 | `cotizaciones.table.js` | `TabulatorFactory.create()` con columnas, badges, acciones |
| 5 | `cotizaciones.ui.js` | DOM Shield, Offcanvas lifecycle, fetch con JWT, delete confirm |
| 6 | `cotizaciones.list.js` | Refresh helper -> delega a `table.refresh()` |
| 7 | `cotizaciones.editor.js` | HTMX triggers: `showCreate()`, `showEdit(uuid)` |
| 8 | `cotizaciones.detalle.js` | HTMX trigger: `show(uuid)` para offcanvas detalle |
| 9 | `cotizaciones.main.js` | Orquestador: `DOMUtils.onVisibleOnce` + `tab-activated` listener |

#### Endpoints SSoT (`cotizaciones.api.js`)

```javascript
var BASE = '/api/v1/cotizaciones';
// URLs expuestas:
// listUrl, createUrl, detailUrl(uuid), deleteUrl(uuid), updateUrl(uuid),
// recalcularUrl(uuid), exportarPdfUrl(uuid), estadisticasUrl,
// configuracionUrl, offcanvasCrearUrl, offcanvasEditarUrl(uuid),
// offcanvasDetalleUrl
```

#### TabulatorFactory (`cotizaciones.table.js`)

- Usa `TabulatorFactory.create(GRID_ID, API_URL, columns, options)` (patron proveedores)
- Columnas: numero_cotizacion, cliente_razon_social, fecha_emision, fecha_vencimiento, estado (badge), total_con_impuestos (COP), Acciones
- Badge de estado: BORRADOR=warning, ENVIADA=info, ACEPTADA=success, CANCELADA=danger
- Search binding via `searchInputSelector: '#search-cotizacion'`
- Event delegation en grid para botones (editar, detalle, PDF, eliminar)

#### DOM Shield (`cotizaciones.ui.js`)

- `bindForm()`: Remueve atributos `name` de selects visibles, captura valores de hidden inputs
- Fetch POST/PATCH con `api.getHeaders()` (JWT Bearer + CSRF)
- Modal de confirmacion para eliminacion (`#confirmarEliminarModal`)
- Listener `htmx:afterSettle` para auto-show offcanvas + bind form

#### Tab-Activated Pattern (`cotizaciones.main.js`)

```
DOMContentLoaded -> DOMUtils.onVisibleOnce('#tab-cotizaciones', init)
tab-activated (cotizaciones) -> init() si no inicializado, redraw() si ya existe
init() -> table.init() + ui.bindEvents()
```

### Sistema Legacy (DEPRECATED)

**Ubicacion:** `apps/tenant/core/static/core/js/cotizaciones/`

---

## Flujos Completos

### Flujo 1: Crear Nueva Cotización

```
1. Frontend: Usuario click "Nueva Cotización"
   ↓
2. HTMX: GET /cotizaciones/editor/draft/
   ↓
3. Backend: CotizacionEditorDraftView.render()
   → Carga template editor_cotizacion.html
   ↓
4. Frontend: cotizacion_editor.js se inicializa
   ↓
5. Usuario: Selecciona Cliente, Perfil, Fecha Vencimiento
   ↓
6. Usuario: Añade items (click "+" en columna ACCIONES)
   ↓
7. Usuario: Edita cantidad/precio → recalcularFila() calcula subtotal
   ↓
8. Usuario: Click "Guardar Cotización"
   ↓
9. Frontend: POST /api/v1/cotizaciones/
   Payload: {
     cliente: <id>,
     configuracion: <id>,
     fecha_vencimiento: "YYYY-MM-DD",
     items: [...]
   }
   ↓
10. Backend: CotizacionViewSet.create()
    → CotizacionSerializer.validate()
    → CotizacionSerializer.create()
    ↓
11. CotizacionService.crear_preforma()
    → Valida perfil y cliente
    → Genera codigo_unico automáticamente
    → Copia DNA del perfil (IVA, AIU, tipo_cotizacion)
    → Crea Cotizacion
    ↓
12. Crea CotizacionItem para cada item del payload
    → Calcula precio_unitario_venta y subtotal_linea
    ↓
13. CotizacionService.calcular_totales()
    → Suma subtotales
    → Calcula IVA y AIU
    → Actualiza total_con_impuestos
    ↓
14. Retorna cotización serializada con UUID
    ↓
15. Frontend: Cierra offcanvas y refresca tabla
```

---

### Flujo 2: Editar Cotización Existente (v2.61)

**⚠️ v2.61:** Flujo actualizado con nuevo endpoint `render-offcanvas/editar/`.

```
1. Frontend: Usuario click "Editar" en columna ACCIONES (Tabulator)
   → Botón con hx-get="/api/v1/cotizaciones/{uuid}/render-offcanvas/editar/"
   ↓
2. HTMX: GET /api/v1/cotizaciones/{uuid}/render-offcanvas/editar/
   → Atributos: hx-get, hx-target="#offcanvas-container", hx-swap="innerHTML"
   ↓
3. Backend: CotizacionViewSet.render_offcanvas_editar()
   → Obtiene cotización por UUID (o ID numérico como fallback)
   → Renderiza template: tenant/core/partials/cotizaciones/offcanvas_editar_cotizacion.html
   → Contexto: cotizacion, is_draft=False, clientes, configuraciones
   ↓
4. HTMX: Inserta contenido en #offcanvas-container
   ↓
5. Frontend: Script en offcanvas_editar_cotizacion.html se ejecuta
   → Bootstrap.Offcanvas.getOrCreateInstance().show()
   → Muestra offcanvas automáticamente
   ↓
6. Frontend: cotizacion_editar.js se inicializa (listener shown.bs.offcanvas)
   → GET /api/v1/cotizaciones/<uuid>/
   → Carga datos existentes
   → Muestra items en tablas
   → Recalcula subtotales de todas las filas usando w.recalcularFila()
   ↓
7. Usuario: Modifica items (añadir/editar/eliminar)
   → Al editar celda (cantidad, precio, utilidad, IVA):
     → cellEdited se dispara
     → recalcularFila() actualiza subtotal de la fila
     → getActiveCotizacionModule() obtiene CotizacionEditarModule
     → recalcularTotalesGlobales() actualiza panel "Resumen de Totales" en tiempo real
   ↓
8. Usuario: Click "Guardar Cotización"
   ↓
9. Frontend: PATCH /api/v1/cotizaciones/<uuid>/
   Payload: {
     items: [...],  // Items actualizados
     fecha_vencimiento: "...",
     ...
   }
   ↓
10. Backend: CotizacionViewSet.update()
    → CotizacionSerializer.validate()
    → Actualiza cotización
    → Actualiza/crea/elimina items
    ↓
11. CotizacionService.calcular_totales()
    → Recalcula totales
    ↓
10. Retorna cotización actualizada
    ↓
11. Frontend: Cierra offcanvas y refresca tabla
```

---

### Flujo 3: Generar PDF

```
1. Frontend: Usuario click "Generar PDF"
   ↓
2. Frontend: GET /api/v1/cotizaciones/<uuid>/pdf/
   ↓
3. Backend: PDFViewSet.generate_pdf()
    → Obtiene cotización por UUID
    → Obtiene empresa del tenant (SSoT)
    ↓
4. pdf_service.preparar_contexto_pdf()
    → Obtiene items con prefetch
    → Obtiene perfil de configuración
    → Agrupa items por sección (obtener_secciones_render)
    → Calcula totales (calcular_totales)
    → Sanitiza textos
    ↓
5. pdf_service.generar_pdf_bytes()
    → Renderiza template HTML
    → Convierte a PDF (WeasyPrint eliminado - usar biblioteca alternativa)
    ↓
6. Retorna PDF como HttpResponse
    ↓
7. Frontend: Descarga PDF
```

---

### Flujo 4: Crear Plantilla/Perfil

```
1. Frontend: Usuario click "Nueva Plantilla"
   ↓
2. HTMX: GET /cotizaciones/partials/configuracion/crear/
   ↓
3. Backend: ConfiguracionCrearOffcanvasView.render()
   → Carga template offcanvas_plantilla_crear.html
   ↓
4. Usuario: Completa formulario
   - Nombre, Tipo, IVA, Utilidad
   - AIU (opcional)
   - Prefijo, Sufijo, Semilla
   ↓
5. Usuario: Click "Crear Plantilla"
   ↓
6. Frontend: POST /api/v1/cotizaciones/configuracion/
   ↓
7. Backend: ConfiguracionCotizacionViewSet.create()
    → ConfiguracionCotizacionDetailSerializer.validate()
    → Valida unicidad de nombre
    → Valida que al menos un modelo esté habilitado
    → Asigna empresa del tenant (SSoT)
    ↓
8. Crea ConfiguracionCotizacion
    ↓
9. Retorna plantilla serializada
    ↓
10. Frontend: Cierra offcanvas y refresca tabla
```

---

### Flujo 4: Cargar Estadísticas del Panel (⚠️ v2.61.1: Nuevo)

```
1. Frontend: Módulo de cotizaciones se inicializa
   → inicializarModulo() en cotizaciones.page.js
   ↓
2. Frontend: cargarEstadisticas() se ejecuta automáticamente
   ↓
3. Frontend: GET /api/v1/cotizaciones/estadisticas/
   ↓
4. Backend: CotizacionViewSet.estadisticas()
   → Obtiene empresa del tenant (SSoT)
   → Agrega: Sum(total_con_impuestos), Count(id)
   → Filtra por estado: ACEPTADA, ENVIADA, BORRADOR
   ↓
5. Backend: Retorna JSON
   {
     "total_neto": "1000000.00",
     "cantidad_total": 50,
     "cantidad_aceptadas": 10,
     "cantidad_enviadas": 20,
     "cantidad_borrador": 20
   }
   ↓
6. Frontend: Actualiza elementos del panel
   → #total-cotizaciones-neto: fmtMoney(total_neto)
   → #cantidad-cotizaciones: cantidad_total
   → #cantidad-aceptadas: cantidad_aceptadas
   → #cantidad-enviadas: cantidad_enviadas
   → #cantidad-borrador: cantidad_borrador
   ↓
7. Frontend: Se actualiza automáticamente al refrescar tabla
   → w.cotizacionesPage.refresh() también llama a cargarEstadisticas()
```

---

## Flujo Completo: Workspace -> Gateway Directo -> Models

### Resumen del Flujo Arquitectonico (v2.61.8)

El flujo completo inicia desde `workspace.html`, pasa por Gateway Directo (`/api/v1/cotizaciones/`) y llega a los modelos via Service Layer Package. La arquitectura es desacoplada, modular y usa JWT Dual-Auth.

### Diagrama de Flujo Completo

```
1. Usuario accede a /workspace/
   |
2. Django: WorkspaceView.render() (apps/tenant/core/views_ui.py)
   |
3. Template: tenant/core/workspace.html
   |-- Incluye: cotizaciones/assets_cotizaciones.html (v2.61.8 moderno)
   |-- Carga 10 modulos JS bajo window.Sintel.Cotizaciones
   +-- Incluye list.html con search input y delete modal
   |
4. JavaScript: cotizaciones.main.js se inicializa
   |-- DOMUtils.onVisibleOnce('#tab-cotizaciones', init)
   |-- tab-activated listener detecta activacion
   +-- TabulatorFactory.create() crea tabla con paginacion remota
   |
5. TabulatorFactory: GET /api/v1/cotizaciones/?page=1&page_size=20
   |-- Header: Authorization: Bearer <jwt> (via jwtAuth.getAccessToken())
   +-- Header: X-CSRFToken (via cookie)
   |
6. Gateway Directo: config/api_urls.py
   +-- path("cotizaciones/", include("apps.tenant.cotizaciones.api.urls"))
   |
7. ViewSet: CotizacionViewSet.list()
   |-- ServiceMixin.get_qs_list() -> CotizacionSelector.get_list()
   +-- Paginacion: StandardResultsSetPagination
   |
8. Selector: CotizacionSelector.get_list(empresa_id)
   +-- QuerySet con .only(LIST_FIELDS) + select_related(LIST_FK_FIELDS)
   |
9. Response JSON paginado -> TabulatorFactory renderiza tabla
```

### Flujo CRUD: Crear Nueva Cotizacion (v2.61.8)

```
1. Usuario: Click boton "Nueva Cotizacion"
   |
2. cotizaciones.editor.showCreate()
   +-- htmx.ajax('GET', '/api/v1/cotizaciones/render-offcanvas/crear/', ...)
   |
3. CotizacionViewSet.render_offcanvas_crear()
   +-- Renderiza offcanvas template con clientes + configuraciones
   |
4. HTMX inserta HTML en #offcanvas-container
   |-- htmx:afterSettle -> cotizaciones.ui auto-show offcanvas + bind form
   |
5. Usuario completa formulario (cliente, configuracion, items, fecha)
   |
6. cotizaciones.ui.bindForm() captura payload JSON
   |-- DOM Shield: input hidden para FKs
   +-- Headers: api.getHeaders() (JWT Bearer + CSRF)
   |
7. fetch POST /api/v1/cotizaciones/
   |
8. CotizacionViewSet.create() -> CotizacionSerializer.validate()
   |
9. ServiceMixin.service_crear_cotizacion()
   +-- CotizacionService.crear_preforma(empresa, datos)
       |-- DSV: Valida perfil y cliente pertenecen al tenant
       |-- Genera codigo_unico automaticamente
       |-- DNA Inheritance: copia valores del perfil
       +-- @transaction.atomic
   |
10. CotizacionService.calcular_totales(cotizacion.id)
   |
11. Response 201 JSON -> UI cierra offcanvas + table.refresh()
```

### Punto de Entrada: workspace.html (v2.61.8)

**Ubicacion:** `apps/tenant/core/templates/tenant/core/workspace.html`

```html
{# Modulo Cotizaciones - Tab en workspace #}
<section id="tab-cotizaciones" class="workspace-tab" style="display: none;">
  <div class="ui-module ui-cotizaciones">
    {# Sub-tabs: Cotizaciones | Catalogo #}
    ...
    <div class="tab-content" id="cotizaciones-tab-content">
      <div class="tab-pane fade show active" id="subtab-cotizaciones">
        {% include 'cotizaciones/list.html' %}  {# v2.61.8: template FSD #}
      </div>
    </div>
  </div>
</section>

{# Assets cargados en bloque extra_js #}
{% include 'cotizaciones/assets_cotizaciones.html' %}  {# v2.61.8: assets modernos #}
```

**Cambio v2.61.8:** workspace.html ahora incluye `cotizaciones/assets_cotizaciones.html` (moderno) en vez de `tenant/core/partials/cotizaciones/assets_cotizaciones.html` (legacy).

### Gateway Directo (SSoT de URLs - v2.61.8)

**Archivo:** `config/api_urls.py`

```python
path("cotizaciones/", include("apps.tenant.cotizaciones.api.urls")),
```

**Todos los endpoints accesibles desde `/api/v1/cotizaciones/`:**
- CRUD principal: `GET/POST /`, `GET/PATCH/DELETE /{uuid}/`
- Items: `GET/POST /items/`, `GET/PATCH/DELETE /items/{id}/`
- Configuracion: `GET/POST /configuracion/`, etc.
- Offcanvas: `render-offcanvas/crear/`, `{uuid}/render-offcanvas/editar/`, `render-offcanvas/detalle/`
- Acciones: `{uuid}/recalcular/`, `{uuid}/exportar-pdf/`, `estadisticas/`

**NOTA:** El Core API Facade (`core/api/v1/cotizaciones/`) sigue existiendo para compatibilidad pero el frontend moderno usa Gateway Directo exclusivamente.

---

## Dependencias y Aislamiento

### Dependencias Externas

#### 1. **Empresa** (SSoT - Obligatorio)
- **Ubicación:** `apps/tenant/empresa.models.Empresa`
- **Uso:** Filtrado por tenant (singleton)
- **Relación:** ForeignKey en todos los modelos principales

#### 2. **Cliente** (Opcional - Resiliente)
- **Ubicación:** `apps.tenant.clientes.models.Cliente`
- **Uso:** Relación opcional en `Cotizacion`
- **Resiliencia:** `SET_NULL` - Si falla, cotización persiste

### Aislamiento

#### ✅ **No Depende De:**
- Inventario
- Facturas
- Proveedores
- Otros módulos de negocio

#### ✅ **Características de Resiliencia:**
- Snapshot Pattern: Datos reales guardados en items
- Relaciones opcionales: Cliente puede ser null
- Validación SSoT: Empresa siempre del tenant

---

## 📊 Diagramas de Flujo

### Diagrama de Modelos

```
Empresa (SSoT)
    │
    ├── ConfiguracionCotizacion (Perfil/Plantilla)
    │       │
    │       └── Cotizacion (1:N)
    │               │
    │               └── CotizacionItem (1:N)
    │                       │
    │                       ├── Producto (opcional, SET_NULL)
    │                       └── Servicio (opcional, SET_NULL)
    │
    ├── Producto (Catálogo)
    └── Servicio (Catálogo)

Cliente (Opcional, SET_NULL)
    │
    └── Cotizacion (N:1)
```

---

### Diagrama de Flujo de Creación

```
[Usuario] → Selecciona Cliente, Perfil, Fecha
    ↓
[Frontend] → POST /api/v1/cotizaciones/
    ↓
[CotizacionSerializer] → validate()
    ↓
[CotizacionService] → crear_preforma()
    ├── Valida perfil y cliente (SSoT)
    ├── Genera codigo_unico()
    └── Copia DNA del perfil
    ↓
[Crea Cotizacion]
    ↓
[Crea CotizacionItem] (por cada item)
    ↓
[CotizacionService] → calcular_totales()
    ↓
[Retorna Cotizacion con UUID]
```

---

## 🔍 Puntos Críticos

### 1. **SSoT (Single Source of Truth)**
- ⚠️ Empresa **SIEMPRE** se obtiene del tenant (singleton)
- ⚠️ Nunca se acepta `empresa` en el payload del frontend
- ⚠️ Todos los querysets filtran por empresa del tenant

### 2. **DNA Inheritance**
- ⚠️ Valores del perfil se **COPIAN** a la cotización (no referencian)
- ⚠️ Si el perfil cambia, las cotizaciones viejas mantienen sus valores
- ⚠️ Garantiza integridad histórica

### 3. **Numeración Automática**
- ⚠️ Usa `select_for_update()` para evitar race conditions
- ⚠️ Usa `F()` expressions para actualización atómica
- ⚠️ Thread-safe en entornos concurrentes

### 4. **Cálculos Financieros**
- ⚠️ **ÚNICA** fuente de verdad: `CotizacionService.calcular_totales()`
- ⚠️ No debe haber lógica de cálculos en serializers ni viewsets
- ⚠️ AIU se calcula sobre subtotal, IVA sobre (subtotal + AIU)

### 5. **Resiliencia**
- ⚠️ Cliente puede ser null (SET_NULL)
- ⚠️ Snapshot de datos en items (descripcion, marca, referencia)
- ⚠️ Funciona incluso si módulo de clientes falla

---

## 📝 Comandos de Gestión

### `limpiar_cotizaciones`

**Ubicación:** `apps/tenant/cotizaciones/management/commands/limpiar_cotizaciones.py`

**Propósito:** Elimina todos los datos de cotizaciones (⚠️ DESTRUCTIVO).

**Uso:**
```bash
# Modo simulación
python manage.py tenant_command limpiar_cotizaciones --schema=tenant_name --dry-run

# Eliminación real
python manage.py tenant_command limpiar_cotizaciones --schema=tenant_name --confirm
```

**Elimina:**
- CotizacionItem
- Cotizacion
- Producto
- Servicio
- ConfiguracionCotizacion

**Orden:** Respeta foreign keys (items primero, luego cotizaciones, luego catálogos)

---

## 🎯 Resumen de Finalidades

| Componente | Finalidad |
|------------|-----------|
| **Cotizacion** | Representa una cotización comercial completa |
| **CotizacionItem** | Representa un item individual dentro de una cotización |
| **Producto** | Catálogo interno de productos/equipos |
| **Servicio** | Catálogo interno de servicios |
| **ConfiguracionCotizacion** | Define el "DNA" de una cotización (plantilla) |
| **CotizacionService** | Única fuente de verdad para lógica de negocio |
| **CotizacionViewSet** | CRUD completo de cotizaciones vía API REST |
| **CotizacionItemViewSet** | CRUD de items individuales |
| **ConfiguracionCotizacionViewSet** | CRUD de perfiles de configuración |
| **CotizacionSerializer** | Serialización y validación de cotizaciones |
| **pdf_service** | Generación profesional de PDFs |
| **ui_views** | Renderizado de templates HTML (UI Shells) |

---

## Referencias

- **Arquitectura General**: `documentacion/arquitectura_general.md`
- **AGENTS.md**: Reglas Core de Arquitectura (SSoT)
- **Templates Frontend Modernos**: `apps/tenant/cotizaciones/templates/cotizaciones/`
- **JavaScript Frontend Moderno**: `apps/tenant/cotizaciones/static/cotizaciones/js/`
- **Templates Frontend Legacy**: `apps/tenant/core/templates/tenant/core/partials/cotizaciones/`
- **JavaScript Frontend Legacy**: `apps/tenant/core/static/core/js/cotizaciones/`

---

## Registro de Bugs y Correcciones v2.61.8

### Resumen

Auditoria completa realizada el 2026-02-07. Se identificaron y corrigieron 13 issues de cumplimiento con AGENTS.md. Todos los archivos Python compilan limpiamente (`py_compile`). Cero errores en validacion get_errors.

### Backend (4 fixes)

| # | Archivo | Bug | Correccion |
|---|---------|-----|------------|
| 1 | `api/viewsets.py` | `retrieve` usaba `get_list()` (LIST_FIELDS, sin prefetch) | Cambiado a `get_detail(None, empresa_id)` con DETAIL_FIELDS + prefetch |
| 2 | `services/selectors.py` | `get_detail()` siempre filtraba por id y retornaba `.first()` | Retorna queryset completo cuando pk=None (para uso como base en ViewSet) |
| 3 | `services/api_mixins.py` | `service_crear_cotizacion()` llamaba `crear_cotizacion()` (inexistente) | Cambiado a `crear_preforma()` con resolucion de empresa via `get_empresa_id()` |
| 4 | `services/api_mixins.py` | `get_qs_detail()` usaba `kwargs.get('pk')` pero lookup_field='uuid' | Pasa None al selector (retorna queryset completo para `get_object()`) |

### Frontend - Workspace Integration (2 fixes)

| # | Archivo | Bug | Correccion |
|---|---------|-----|------------|
| 5 | `core/static/core/js/workspace.js` | Title map no incluia 'cotizaciones' | Agregado `'cotizaciones': 'Cotizaciones'` |
| 6 | `core/static/core/js/cotizaciones/cotizaciones.page.js` | Solo escuchaba `shown.bs.tab`, no `tab-activated` | Agregado listener `tab-activated` con redraw(true) |

### Frontend - FSD Rewrite (7 fixes, 10 archivos reescritos)

| # | Issue | Alcance | Correccion |
|---|-------|---------|------------|
| 7 | JS modernos eran stubs sin funcionalidad | 10 archivos | Reescritura completa FSD con `window.Sintel.Cotizaciones` |
| 8 | Sin TabulatorFactory (Tabulator crudo) | `cotizaciones.table.js` | `TabulatorFactory.create()` con paginacion, search, JWT |
| 9 | Sin JWT en fetch calls | `cotizaciones.ui.js` | `api.getHeaders()` con `jwtAuth.getAccessToken()` |
| 10 | Doble carga de scripts | `list.html` + `workspace.html` | Removido include de list.html, workspace carga modernos |
| 11 | Sin input de busqueda | `list.html` | Agregado `#search-cotizacion` en toolbar |
| 12 | Sin modal de confirmacion delete | `list.html` | Agregado Bootstrap modal `#confirmarEliminarModal` |
| 13 | CSS referenciado no existia | Assets template | Creado `cotizaciones.css` placeholder |

### Archivos Modificados (inventario completo)

**Backend:**
- `apps/tenant/cotizaciones/api/viewsets.py`
- `apps/tenant/cotizaciones/services/selectors.py`
- `apps/tenant/cotizaciones/services/api_mixins.py`

**Frontend JS (reescritos completos):**
- `apps/tenant/cotizaciones/static/cotizaciones/js/cotizaciones.module.js`
- `apps/tenant/cotizaciones/static/cotizaciones/js/cotizaciones.api.js`
- `apps/tenant/cotizaciones/static/cotizaciones/js/cotizaciones.utils.js`
- `apps/tenant/cotizaciones/static/cotizaciones/js/cotizaciones.table.js`
- `apps/tenant/cotizaciones/static/cotizaciones/js/cotizaciones.ui.js`
- `apps/tenant/cotizaciones/static/cotizaciones/js/cotizaciones.list.js`
- `apps/tenant/cotizaciones/static/cotizaciones/js/cotizaciones.editor.js`
- `apps/tenant/cotizaciones/static/cotizaciones/js/cotizaciones.detalle.js`
- `apps/tenant/cotizaciones/static/cotizaciones/js/cotizaciones.main.js`
- `apps/tenant/cotizaciones/static/cotizaciones/js/features/cotizacion_list.js` (deprecated compat)

**Templates:**
- `apps/tenant/cotizaciones/templates/cotizaciones/assets_cotizaciones.html`
- `apps/tenant/cotizaciones/templates/cotizaciones/list.html`
- `apps/tenant/core/templates/tenant/core/workspace.html` (linea 241: modernos)

**Workspace:**
- `apps/tenant/core/static/core/js/workspace.js` (title map)
- `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.page.js` (tab-activated patch)

**Creados:**
- `apps/tenant/cotizaciones/static/cotizaciones/css/cotizaciones.css`

---

## ✅ Validación del Flujo Completo (2026-01-27)

### Estado de Validación

#### ✅ Modelos
- [x] `Cotizacion`: Modelo principal con UUID, codigo_unico, DNA financiero
- [x] `CotizacionItem`: Items con snapshot pattern y cálculos automáticos
- [x] `Producto` y `Servicio`: Catálogos internos
- [x] `ConfiguracionCotizacion`: Perfiles con folios dinámicos y DNA

#### ✅ Servicios
- [x] `CotizacionService.crear_preforma()`: Creación con DNA inheritance
- [x] `CotizacionService.generar_codigo_unico()`: Numeración thread-safe
- [x] `CotizacionService.calcular_totales()`: SSoT para cálculos financieros
- [x] `CotizacionService.calcular_linea()`: Cálculo estandarizado de líneas

#### ✅ APIs y ViewSets
- [x] `CotizacionViewSet`: CRUD completo con lookup por UUID
- [x] `CotizacionItemViewSet`: CRUD de items con recálculo automático
- [x] `ConfiguracionCotizacionViewSet`: CRUD de perfiles
- [x] Paginación: `StandardResultsSetPagination` implementada
- [x] Búsqueda: `?search=` funcional en todos los ViewSets

#### ✅ Serializers
- [x] `CotizacionSerializer`: Validación completa, items anidados
- [x] `CotizacionItemSerializer`: Campos snapshot y cálculos
- [x] `ConfiguracionCotizacionDetailSerializer`: Configuración completa del editor

#### ✅ Frontend
- [x] Tabulator Factory: Tablas interactivas con paginación
- [x] Editor de cotizaciones: Modo draft y edición
- [x] Gestión de plantillas: CRUD completo en Offcanvas
- [x] JavaScript modular: Feature-Sliced Architecture

#### ✅ Templates
- [x] `editor_cotizacion.html`: Editor principal
- [x] `list.html`: Lista de cotizaciones
- [x] `offcanvas_plantilla_*.html`: Gestión de plantillas
- [x] `offcanvas_ver_detalle.html`: Vista detallada

#### ✅ Servicio de PDF
- [x] `preparar_contexto_pdf()`: Preparación de contexto
- [x] `obtener_secciones_render()`: Agrupación por secciones
- [x] `calcular_totales()`: Cálculos para PDF
- [x] `generar_pdf_bytes()`: Generación de PDF (WeasyPrint eliminado - usar biblioteca alternativa)

#### ✅ Permisos y Seguridad
- [x] `IsTenantMember`: Verificación de tenant
- [x] SSoT: Empresa siempre del tenant
- [x] Zero Trust: Validación en serializers y viewsets

### Puntos de Atención

1. **Cliente Obligatorio**: Aunque la relación es opcional (SET_NULL), el serializer requiere cliente en creación
2. **DNA Inheritance**: Los valores del perfil se copian, no referencian (integridad histórica)
3. **Thread-Safety**: La generación de códigos únicos usa `select_for_update()` y `F()` expressions
4. **Snapshot Pattern**: Los items guardan datos reales (descripcion, marca, referencia) independientemente de referencias

### Mejoras Futuras Sugeridas

1. Implementar Error Boundary Pattern en ViewSets (similar a Empleados)
2. Agregar validación de límites de días/items en cotizaciones
3. Implementar historial de cambios en cotizaciones
4. Agregar exportación a Excel/CSV

---

## 🔧 Correcciones y Mejoras Aplicadas (2026-03-04)

### Resumen de Correcciones

Se aplicaron múltiples correcciones críticas para resolver errores de validación y sincronización en el flujo de guardado de cotizaciones. Todas las correcciones siguen el principio de "Fuerza Bruta Arquitectónica" para garantizar robustez y resiliencia.

---

### 1. Corrección de Validación del Campo Cliente

#### Problema Identificado
- Error 400: "ID de cliente inválido" o "tipo Cliente no soportado"
- El frontend enviaba texto descriptivo en lugar del ID numérico
- El serializer no reconocía correctamente el objeto Cliente después de la conversión

#### Correcciones Aplicadas

**A. Limpieza del Campo Cliente en Serializer (`serializers.py`)**
- Cambiado `queryset=Cliente.objects.none()` a `queryset=Cliente.objects.all()`
- Permite conversión ID → Objeto antes de validación
- Queryset se filtra por empresa en `__init__()` para seguridad (SSoT)

**B. Refactorización de `validate_cliente()`**
- Implementación con múltiples fallbacks para obtener empresa
- Verificación explícita de tipo con `isinstance(value, Cliente)`
- Uso de `getattr` para resiliencia cuando `request` es `None`
- Validación SSoT mantenida (cliente debe pertenecer a empresa del tenant)

**C. Limpieza del Método `validate()`**
- Eliminada toda lógica manual de conversión de IDs de cliente
- Confianza 100% en `PrimaryKeyRelatedField` para conversión
- Eliminadas validaciones redundantes de existencia en BD

**D. Sincronización con Service Layer (`services.py`)**
- Service layer acepta objetos `Cliente` directamente del serializer
- También acepta IDs como fallback (compatibilidad)
- Verificación de tipo explícita con `isinstance()`
- Eliminadas validaciones redundantes

**Archivos Modificados:**
- `apps/tenant/cotizaciones/api/serializers.py`
- `apps/tenant/cotizaciones/services.py`
- `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.helpers.js`
- `apps/tenant/core/static/core/js/cotizaciones/features/cotizacion_editor.js`

---

### 2. Corrección de Validación del Campo Configuración

#### Problema Identificado
- Error: "ID de perfil inválido: tipo ConfiguracionCotizacion no soportado"
- El serializer recibía objeto `ConfiguracionCotizacion` pero intentaba tratarlo como ID

#### Correcciones Aplicadas

**A. Campo `configuracion` en Serializer**
- Cambiado `queryset=ConfiguracionCotizacion.objects.none()` a `queryset=ConfiguracionCotizacion.objects.all()`
- Permite conversión ID → Objeto correctamente

**B. Limpieza del Método `validate()`**
- Eliminada lógica manual de conversión de IDs de configuración
- Confianza 100% en `PrimaryKeyRelatedField` para conversión

**C. Sincronización con Service Layer**
- Service layer acepta objetos `ConfiguracionCotizacion` directamente
- También acepta IDs como fallback
- Validación de pertenencia a empresa mantenida

**Archivos Modificados:**
- `apps/tenant/cotizaciones/api/serializers.py`
- `apps/tenant/cotizaciones/services.py`

---

### 3. Corrección de Importaciones

#### Problema Identificado
- Error: "No module named 'apps.tenant.configuracion'"
- Importaciones incorrectas usando `..configuracion` desde `services.py`

#### Correcciones Aplicadas
- Eliminada importación redundante e incorrecta en `services.py` (línea 73)
- Eliminada importación redundante en `serializers.py` (línea 329)
- `ConfiguracionCotizacion` se importa una sola vez en la parte superior de cada archivo

**Archivos Modificados:**
- `apps/tenant/cotizaciones/services.py`
- `apps/tenant/cotizaciones/api/serializers.py`

---

### 4. Guardado de Datos del Usuario

#### Problema Identificado
- La cotización se guardaba sin los datos proporcionados por el usuario
- El campo `fecha_emision` no se guardaba correctamente

#### Correcciones Aplicadas

**A. Definición Explícita de `fecha_emision` en Serializer**
- Agregado campo explícito `fecha_emision = serializers.DateField(required=False, allow_null=True)`
- Permite que el usuario proporcione la fecha o use `auto_now_add` como fallback

**B. Manejo de `fecha_emision` en Service Layer**
- Procesamiento de fecha proporcionada por el usuario
- Conversión de string a `date` si es necesario
- Actualización después de crear (porque `auto_now_add=True` no permite establecer en `create()`)

**C. Verificación de Datos Guardados**
- ✅ `cliente`: ID del cliente seleccionado
- ✅ `configuracion`: ID del perfil de configuración
- ✅ `fecha_emision`: Fecha proporcionada por el usuario
- ✅ `tipo_cotizacion`: Tipo de cotización (MIXTO, PRODUCTO, SERVICIO)
- ✅ `iva_porcentaje`: Porcentaje de IVA
- ✅ `porcentaje_aiu_admin`: Porcentaje AIU Administración
- ✅ `porcentaje_aiu_imprevistos`: Porcentaje AIU Imprevistos
- ✅ `porcentaje_aiu_utilidad`: Porcentaje AIU Utilidad
- ✅ `items`: Lista de items de la cotización

**Archivos Modificados:**
- `apps/tenant/cotizaciones/api/serializers.py`
- `apps/tenant/cotizaciones/services.py`

---

### 5. Corrección de Estado CANCELADA

#### Problema Identificado
- Error: "CANCELADA no es una elección válida"
- El modelo solo tenía: BORRADOR, ENVIADA, ACEPTADA
- El frontend intentaba establecer CANCELADA al borrar cotizaciones

#### Correcciones Aplicadas
- Agregado estado `CANCELADA = 'CANCELADA', _('Cancelada')` al modelo
- El serializer ahora acepta este estado automáticamente (usa `Estado.choices`)

**Archivos Modificados:**
- `apps/tenant/cotizaciones/models.py`

**Migración Requerida:**
```bash
python manage.py makemigrations cotizaciones
python manage.py migrate
```

---

### 6. Validación de ViewSet

#### Correcciones Aplicadas
- Simplificado método `create()` en `CotizacionViewSet`
- Empresa se pasa al contexto del serializer
- Eliminadas estrategias de fallback redundantes (el serializer las maneja)

**Archivos Modificados:**
- `apps/tenant/cotizaciones/api/viewsets.py`

---

### 7. Validación de Modelo CotizacionItem

#### Verificación Realizada
- Campo `descripcion` ya tiene `blank=True` y `null=True` ✅
- No se requirieron cambios

---

## 📊 Flujo Corregido de Guardado

```
Frontend (JS)
    ↓
    Envía: { cliente: 3, configuracion: 41, fecha_emision: "2026-03-04", ... }
    ↓
ViewSet.create()
    ↓
    Inyecta empresa en contexto
    ↓
Serializer.to_internal_value()
    ↓
    Normaliza: "123" → 123, "cliente SAS (10000000)" → 10000000
    ↓
Serializer.validate()
    ↓
    ✅ Solo normaliza strings a int
    ✅ NO intenta convertir a objeto
    ↓
PrimaryKeyRelatedField.to_internal_value()
    ↓
    Convierte: 123 → Cliente(id=123), 41 → ConfiguracionCotizacion(id=41)
    ↓
Serializer.validate_cliente() / validate_configuracion()
    ↓
    ✅ Verifica isinstance(value, Cliente/ConfiguracionCotizacion)
    ✅ Valida pertenencia a empresa
    ↓
Serializer.create()
    ↓
    Obtiene empresa con fallbacks
    Extrae items del validated_data
    ↓
Service.crear_preforma()
    ↓
    ✅ Acepta objetos Cliente y ConfiguracionCotizacion directamente
    ✅ Procesa fecha_emision del usuario
    ✅ Guarda todos los datos financieros del usuario
    ↓
✅ Cotización creada con todos los datos del usuario
```

---

## 🎯 Principios Aplicados

### Fuerza Bruta Arquitectónica
- Múltiples estrategias de fallback para obtener empresa
- Validación explícita de tipos en cada capa
- Eliminación de lógica redundante
- Confianza en DRF para conversiones estándar

### Zero Trust
- Validación de pertenencia a empresa en cada capa
- Verificación explícita de tipos antes de procesar
- Validación SSoT en serializer y service layer

### Separación de Responsabilidades
- `PrimaryKeyRelatedField`: Conversión ID → Objeto
- `validate_cliente()`: Validación de empresa
- `validate()`: Solo normalización, no conversión
- Service Layer: Lógica de negocio y persistencia

---

## ✅ Estado Final

### Errores Resueltos
- ✅ Error 400: "ID de cliente inválido"
- ✅ Error: "tipo Cliente no soportado"
- ✅ Error: "tipo ConfiguracionCotizacion no soportado"
- ✅ Error: "No module named 'apps.tenant.configuracion'"
- ✅ Error: "CANCELADA no es una elección válida"
- ✅ Datos del usuario no se guardaban correctamente

### Archivos Modificados
1. `apps/tenant/cotizaciones/api/serializers.py`
2. `apps/tenant/cotizaciones/services.py`
3. `apps/tenant/cotizaciones/api/viewsets.py`
4. `apps/tenant/cotizaciones/models.py`
5. `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.helpers.js`
6. `apps/tenant/core/static/core/js/cotizaciones/features/cotizacion_editor.js`

### Migraciones Requeridas
- Migración para agregar estado `CANCELADA` al modelo `Cotizacion`

---

## 🚀 Implementación de Edición de Cotizaciones (2026-03-04)

### Resumen de Implementación

Se implementó el flujo completo de edición de cotizaciones existentes, incluyendo:
1. **Fase 1**: Configuración de columna de acciones con HTMX
2. **Fase 2**: Lógica de carga de datos en el editor
3. **Fase 3**: Sincronización del backend para actualización (PATCH)
4. **Eliminación de Inmutabilidad**: Remoción de restricciones de edición para cotizaciones ACEPTADAS

### Fase 1: Configuración de Columna de Acciones con HTMX

#### Objetivo
Permitir que el botón "Editar" en la lista de cotizaciones use HTMX directamente para cargar el editor sin JavaScript adicional.

#### Cambios Aplicados

**Archivo**: `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.page.js`

1. **Columna de Acciones Actualizada**:
   - Botón "Editar" ahora usa atributos HTMX directamente:
     - `hx-get="/cotizaciones/editor/${uuid}/"`
     - `hx-target="#offcanvas-container"`
     - `hx-swap="innerHTML"`
     - `data-bs-toggle="offcanvas"` y `data-bs-target="#offcanvas-container"`
   - Botón "Ver PDF" agregado con icono Bootstrap Icons
   - Contenedor de botones con `d-flex gap-1` para mejor layout

2. **Procesamiento HTMX Automático**:
   - Eventos `dataLoaded` y `dataProcessed` de Tabulator
   - Llamada a `htmx.process()` después de cada carga de datos
   - Garantiza que los botones HTMX sean funcionales después del renderizado

#### Código Implementado

```javascript
// Columna de Acciones con HTMX
{
  title: "Acciones",
  formatter: function(cell) {
    const uuid = rowData.uuid || rowData.id;
    // Botón Editar con HTMX
    buttons += `
      <button class="btn btn-sm btn-outline-primary"
              hx-get="/cotizaciones/editor/${uuid}/"
              hx-target="#offcanvas-container"
              hx-swap="innerHTML"
              data-bs-toggle="offcanvas"
              data-bs-target="#offcanvas-container">
        <i class="bi bi-pencil"></i> Editar
      </button>
    `;
    // ... otros botones
  }
}

// Procesamiento HTMX después de renderizar
table.on('dataLoaded', function() {
  if (typeof htmx !== 'undefined' && typeof htmx.process === 'function') {
    htmx.process(container);
  }
});
```

### Fase 2: Lógica de Carga en el Editor

#### Objetivo
Cargar automáticamente los datos de una cotización existente cuando se abre el editor con un UUID válido.

#### Cambios Aplicados

**Archivo**: `apps/tenant/core/static/core/js/cotizaciones/features/cotizacion_editor.js`

1. **Detección de UUID**:
   - Lee `data-cotizacion-uuid` del elemento `#modal-cotizacion-editor`
   - Distingue entre modo borrador y edición

2. **Carga de Datos desde API**:
   - Usa `cotizacionesAPI.get(uuid)` para obtener la cotización completa
   - Manejo de errores con `UIManager.notifyError()`

3. **Relleno de Campos de Cabecera**:
   - Cliente: Selecciona el cliente en el select
   - Perfil: Selecciona el perfil y actualiza previsualización
   - Fecha de Emisión: Formatea fecha para input type="date"
   - Tipo de Cotización: Selecciona el tipo en el select

4. **Relleno de Campos Financieros**:
   - IVA: `input-iva-porcentaje`
   - AIU Administración: `input-aiu-admin`
   - AIU Imprevistos: `input-aiu-imprevistos`
   - AIU Utilidad: `input-aiu-utilidad`
   - Todos con formato de 2 decimales

5. **Carga de Ítems en Tablas**:
   - Filtra ítems por `tipo_item`:
     - `PRODUCTO` → tabla `equipos`
     - `MATERIAL` → tabla `materiales`
     - `SERVICIO` → tabla `servicios`
   - Activa secciones automáticamente si tienen ítems
   - Inicializa tablas antes de cargar datos
   - Mapea campos del backend al formato de Tabulator

6. **Actualización de Totales**:
   - Llama a `actualizarPanelTotales()` después de cargar todos los ítems
   - Delay para asegurar que las tablas estén renderizadas

#### Flujo de Carga

```
1. init() detecta UUID del template
2. Si UUID válido → Cargar datos del emisor y catálogos
3. Obtener cotización desde API (cotizacionesAPI.get(uuid))
4. Rellenar campos de cabecera (cliente, perfil, fecha, tipo)
5. Rellenar campos financieros (IVA, AIU)
6. Distribuir ítems por tipo_item en tablas correspondientes
7. Actualizar panel de totales
```

### Fase 3: Sincronización del Backend para Edición

#### Objetivo
Implementar el método `update()` en el serializer y ViewSet para permitir actualizaciones (PATCH) de cotizaciones existentes.

#### Cambios Aplicados

**Archivo**: `apps/tenant/cotizaciones/api/serializers.py`

1. **Método `update()` Implementado**:
   - Transaccionalidad atómica con `@transaction.atomic`
   - Actualización de campos de la cabecera
   - Sincronización de ítems (estrategia de reemplazo total)
   - Cálculo de precios y subtotales para cada ítem
   - Recálculo de totales de la cotización
   - Logging para auditoría

2. **Estrategia de Sincronización de Ítems**:
   - **Reemplazo Total**: Borrar ítems antiguos y crear nuevos
   - Evita duplicados y ítems huérfanos
   - Mismo patrón de cálculo que en `create()`

**Archivo**: `apps/tenant/cotizaciones/api/viewsets.py`

1. **Método `update()` Implementado**:
   - Inyección de empresa en el contexto del serializer
   - Manejo de errores con Error Boundary Pattern
   - Soporte para PATCH parcial

#### Código Implementado

```python
@transaction.atomic
def update(self, instance, validated_data):
    # 1. Limpiar campos que NO deben venir del frontend
    validated_data.pop('numero_cotizacion', None)
    validated_data.pop('codigo_unico', None)
    validated_data.pop('fecha_vencimiento', None)
    
    # 2. Extraer ítems antes de actualizar la cabecera
    items_data = validated_data.pop('items', None)
    
    # 3. Actualizar campos de la cabecera
    for attr, value in validated_data.items():
        setattr(instance, attr, value)
    instance.save()
    
    # 4. Sincronizar ítems (reemplazo total)
    if items_data is not None:
        instance.items.all().delete()
        for item_data in items_data:
            # Calcular precios y crear ítem
            calculos = CotizacionService.calcular_linea(...)
            CotizacionItem.objects.create(...)
    
    # 5. Recálculo final de totales
    CotizacionService.calcular_totales(instance.id)
    return instance
```

### Eliminación de Inmutabilidad

#### Objetivo
Remover todas las restricciones que impedían editar, eliminar o recalcular cotizaciones con estado ACEPTADA.

#### Cambios Aplicados

1. **Backend** (`apps/tenant/cotizaciones/api/viewsets.py`):
   - Eliminada validación de inmutabilidad en `update()`
   - Eliminada validación de inmutabilidad en `recalcular()`

2. **Backend** (`apps/tenant/cotizaciones/api/serializers.py`):
   - Eliminados comentarios sobre inmutabilidad en `update()`

3. **Frontend** (`apps/tenant/core/static/core/js/cotizaciones/cotizaciones.page.js`):
   - Eliminada lógica que ocultaba botón "Editar" si está ACEPTADA
   - Eliminada lógica que ocultaba botón "Eliminar" si está ACEPTADA
   - Los botones ahora se muestran siempre, independientemente del estado

4. **Frontend** (`apps/tenant/core/static/core/js/cotizaciones/cotizaciones.api.js`):
   - Eliminados comentarios sobre inmutabilidad en `update()` y `delete()`

#### Resultado

- ✅ Las cotizaciones ACEPTADAS pueden editarse
- ✅ Las cotizaciones ACEPTADAS pueden eliminarse
- ✅ Las cotizaciones ACEPTADAS pueden recalcularse
- ✅ Los botones de acción se muestran siempre

### Archivos Modificados

1. `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.page.js`
2. `apps/tenant/core/static/core/js/cotizaciones/features/cotizacion_editor.js`
3. `apps/tenant/cotizaciones/api/serializers.py`
4. `apps/tenant/cotizaciones/api/viewsets.py`
5. `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.api.js`

### Flujo Completo de Edición

```
1. Usuario hace clic en "Editar" en la lista de cotizaciones
   ↓
2. HTMX carga el template del editor con UUID
   ↓
3. cotizacion_editor.js detecta UUID y carga datos desde API
   ↓
4. Campos de cabecera y financieros se rellenan automáticamente
   ↓
5. Ítems se cargan en las tablas de Tabulator según tipo_item
   ↓
6. Usuario modifica datos y hace clic en "Guardar"
   ↓
7. Frontend envía PATCH con datos actualizados
   ↓
8. Backend actualiza cabecera y sincroniza ítems (reemplazo total)
   ↓
9. Backend recalcula totales automáticamente
   ↓
10. Respuesta exitosa y actualización de UI
```

### Beneficios Implementados

- ✅ **HTMX Directo**: Sin JavaScript adicional para cargar el editor
- ✅ **Carga Automática**: Los datos se cargan automáticamente al abrir el editor
- ✅ **Sincronización Robusta**: Reemplazo total de ítems evita duplicados
- ✅ **Transaccionalidad**: Todo el proceso es atómico (todo o nada)
- ✅ **Flexibilidad**: Sin restricciones de inmutabilidad
- ✅ **User-Driven**: Los datos del usuario tienen prioridad absoluta

---

## 🔧 Sincronización de Tabla de Cotizaciones con Modelo (2026-03-04)

### Resumen de Sincronización

Se realizó una sincronización completa de la tabla de listado de cotizaciones en `workspace/#cotizaciones` con los campos reales del modelo `Cotizacion` y el `CotizacionSerializer`. Esto garantiza que la tabla muestre datos correctos y consistentes desde la base de datos.

### Correcciones Aplicadas

#### 1. Actualización del HTML (`list.html`)

**Archivo**: `apps/tenant/core/templates/tenant/core/partials/cotizaciones/list.html`

**Cambios:**
- Actualizado el contenedor de la tabla con ID único: `tabla-cotizaciones-principal`
- Agregados atributos de datos para inicialización automática:
  - `data-url="/api/v1/cotizaciones/"` - URL de la API REST
  - `data-page-size="20"` - Tamaño de página para paginación
- Agregadas clases: `table-responsive tabulator-sintel flex-grow-1`

**Código:**
```html
<div id="tabla-cotizaciones-principal" 
     class="table-responsive tabulator-sintel flex-grow-1" 
     data-url="/api/v1/cotizaciones/" 
     data-page-size="20"
     style="min-height: 400px;" 
     role="grid" 
     aria-label="Tabla de cotizaciones">
</div>
```

#### 2. Sincronización de Columnas (`cotizaciones.page.js`)

**Archivo**: `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.page.js`

**Cambios:**

**A. Columna "NÚMERO":**
- **Antes**: `field: "numero"` (campo inexistente)
- **Ahora**: `field: "codigo_unico"` (campo del modelo)
- Muestra el código único generado (ej: "STS. 0422-2026")
- Formatter maneja valores nulos mostrando '-'

**B. Columna "CLIENTE":**
- **Antes**: `field: "cliente_nombre"` sin fallback
- **Ahora**: `field: "cliente_nombre"` con fallback a `cliente_display`
- Usa `cliente_nombre` del serializer (ReadOnlyField con source `cliente.nombre_comercial`)
- Si `cliente_nombre` no está disponible, usa `cliente_display` como fallback

**C. Columna "TOTAL":**
- **Antes**: `field: "total_neto"` (campo inexistente)
- **Ahora**: `field: "total_con_impuestos"` (campo del modelo)
- Muestra el total con impuestos calculado (subtotal + AIU + IVA)
- Agregado `bottomCalc: "sum"` para calcular suma total en el pie de la tabla
- Formatter maneja valores nulos mostrando `$0`

**Código de Columnas:**
```javascript
{
  title: "NÚMERO",
  field: "codigo_unico", // Campo del modelo
  width: 150,
  headerFilter: "input",
  formatter: function(cell) {
    const value = cell.getValue();
    return value || '-';
  }
},
{
  title: "CLIENTE",
  field: "cliente_nombre", // ReadOnlyField del serializer
  formatter: function(cell) {
    const value = cell.getValue();
    if (!value) {
      const rowData = cell.getRow().getData();
      return rowData.cliente_display || 'Sin cliente';
    }
    return value;
  },
  minWidth: 200,
  headerFilter: "input"
},
{
  title: "TOTAL",
  field: "total_con_impuestos", // Campo del modelo
  formatter: function(cell) {
    const value = cell.getValue();
    if (value === null || value === undefined) {
      return fmtMoney(0);
    }
    return fmtMoney(value);
  },
  width: 150,
  hozAlign: "right",
  sorter: "number",
  bottomCalc: "sum", // Suma total en el pie
  bottomCalcFormatter: function(cell) {
    const value = parseFloat(cell.getValue()) || 0;
    return fmtMoney(value);
  }
}
```

#### 3. Campos Legibles en el Serializer (`serializers.py`)

**Archivo**: `apps/tenant/cotizaciones/api/serializers.py`

**Cambios:**

**A. Campo `cliente_nombre`:**
- Agregado como `ReadOnlyField` con source `cliente.nombre_comercial`
- Proporciona el nombre comercial del cliente de forma legible
- Maneja automáticamente el caso cuando `cliente` es `None` (retorna `None`)

**B. Campo `subtotal`:**
- Agregado como `SerializerMethodField` con método `get_subtotal()`
- Calcula la suma de `subtotal_linea` de todos los items
- Maneja casos edge (instancias del modelo y diccionarios)
- Retorna `Decimal('0.00')` si no hay items

**Código:**
```python
cliente_nombre = serializers.ReadOnlyField(source='cliente.nombre_comercial')
subtotal = serializers.SerializerMethodField(read_only=True)

def get_subtotal(self, obj):
    """
    Calcula el subtotal sumando los subtotal_linea de todos los items.
    """
    from decimal import Decimal
    
    if hasattr(obj, 'items'):
        subtotal = sum(
            item.subtotal_linea 
            for item in obj.items.all() 
            if hasattr(item, 'subtotal_linea') and item.subtotal_linea is not None
        )
        return Decimal(str(subtotal)) if subtotal else Decimal('0.00')
    
    return Decimal('0.00')
```

**C. Campos agregados a `Meta.fields`:**
- `cliente_nombre` agregado en la sección de Cliente
- `subtotal` agregado en la sección de DNA Financiero

**D. Campos agregados a `read_only_fields`:**
- `cliente_nombre` y `subtotal` agregados a la lista

#### 4. Actualización de Selector JavaScript

**Archivo**: `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.page.js`

**Cambios:**
- Actualizado `TABLE_SELECTOR` de `#grid-cotizaciones` a `#tabla-cotizaciones-principal`
- Sincronizado con el nuevo ID del contenedor HTML

#### 5. Documentación en `workspace.html`

**Archivo**: `apps/tenant/core/templates/tenant/core/workspace.html`

**Cambios:**
- Agregados comentarios documentando la sincronización
- Documentado que el contenedor `tabla-cotizaciones-principal` está en `list.html`
- Documentados los atributos de datos para inicialización automática

### Campos Disponibles en la API

El `CotizacionSerializer` ahora expone los siguientes campos legibles:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `codigo_unico` | CharField (read_only) | Código único generado (ej: "STS. 0422-2026") |
| `cliente` | PrimaryKeyRelatedField | ID del cliente |
| `cliente_display` | SerializerMethodField | Nombre completo del cliente |
| `cliente_nombre` | ReadOnlyField | Nombre comercial del cliente |
| `subtotal` | SerializerMethodField | Subtotal calculado desde items |
| `total_con_impuestos` | DecimalField (read_only) | Total con impuestos calculado |

### Sincronización de Campos

#### Mapeo Frontend ↔ Backend

| Columna Frontend | Campo Backend | Tipo | Origen |
|------------------|---------------|------|--------|
| NÚMERO | `codigo_unico` | CharField | Modelo Cotizacion |
| CLIENTE | `cliente_nombre` | ReadOnlyField | Serializer (source: `cliente.nombre_comercial`) |
| TOTAL | `total_con_impuestos` | DecimalField | Modelo Cotizacion |
| SUBTOTAL | `subtotal` | SerializerMethodField | Calculado desde items |

### Beneficios Implementados

- ✅ **Sincronización Completa**: Todos los campos de la tabla coinciden con el modelo
- ✅ **Datos Reales**: La tabla muestra datos directamente desde la base de datos
- ✅ **Campos Legibles**: El serializer expone campos legibles para el frontend
- ✅ **Manejo de Errores**: Formatters manejan valores nulos correctamente
- ✅ **Cálculo de Totales**: Suma total automática en el pie de la tabla
- ✅ **Atributos de Datos**: HTML preparado para inicialización automática con Tabulator

### Archivos Modificados

1. `apps/tenant/core/templates/tenant/core/partials/cotizaciones/list.html`
2. `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.page.js`
3. `apps/tenant/cotizaciones/api/serializers.py`
4. `apps/tenant/core/templates/tenant/core/workspace.html`
5. `apps/tenant/core/static/core/js/cotizaciones/cotizacion_columns.js`

### Estado Final

- ✅ Tabla sincronizada con modelo `Cotizacion`
- ✅ Columnas usando campos reales del serializer
- ✅ Campos legibles agregados al serializer
- ✅ HTML con atributos de datos para inicialización automática
- ✅ Manejo robusto de valores nulos
- ✅ Cálculo de suma total en el pie de la tabla

---

## 🔄 Refactorización Completa del Módulo de PDF (2026-03-04)

### Resumen Ejecutivo

Se realizó una refactorización completa del sistema de generación de PDFs, eliminando WeasyPrint (que requería dependencias del sistema) e implementando `xhtml2pdf` con una arquitectura modular y desacoplada.

### 1. Purga Completa de WeasyPrint

#### Archivos Modificados

**A. `requirements.txt`**
- ❌ Eliminado: `weasyprint>=61.0`
- ❌ Eliminado: `pydyf>=0.10.0`
- ✅ Agregado: `xhtml2pdf>=0.2.11`

**B. `apps/tenant/cotizaciones/pdf_service.py`**
- Eliminadas todas las importaciones directas de `WeasyPrint`
- Eliminadas referencias a `weasyprint` en comentarios
- Refactorizado para usar el nuevo módulo generador

**C. `apps/tenant/cotizaciones/api/pdf_viewsets.py`**
- Actualizado para manejar la ausencia de WeasyPrint
- Retorna `501 NOT_IMPLEMENTED` si se intenta usar (legacy)

**D. `config/settings.py`**
- Eliminadas configuraciones de logging para `weasyprint` y `fontTools`

**E. Dockerfiles**
- `Dockerfile` y `infra/docker/app/Dockerfile`
- Eliminadas dependencias del sistema: `libcairo2`, `libpango-1.0-0`, `libgdk-pixbuf-2.0-0`, `libxml2-dev`, `libxslt1-dev`, `python3-cffi`, `python3-brotli`, `libglib2.0-0`, `libharfbuzz0b`, `libpangoft2-1.0-0`, `libjpeg62-turbo-dev`, `libopenjp2-7-dev`

**F. Documentación**
- `documentacion/arquitectura_general.md`: Actualizada sección de generación de PDFs

### 2. Implementación de Arquitectura Modular con xhtml2pdf

#### A. Módulo Generador Independiente

**Archivo Creado**: `apps/tenant/cotizaciones/utils/pdf_generator.py`

**Características:**
- ✅ **Único punto de importación**: `xhtml2pdf` solo se importa aquí
- ✅ **Desacoplado**: Separado completamente de la lógica de negocio
- ✅ **Fácil reemplazo**: Si se necesita cambiar de librería, solo se modifica este archivo
- ✅ **Manejo de errores robusto**: Validaciones y logging detallado

**Clase Principal:**
```python
class CotizacionPDFGenerator:
    @staticmethod
    def render_to_pdf(template_path, context):
        """
        Renderiza un template HTML a PDF usando xhtml2pdf.
        
        Args:
            template_path: Ruta relativa al directorio templates/ de la app
            context: Diccionario con el contexto para el template
        
        Returns:
            bytes: Contenido del PDF generado, o None si hay error
        """
```

**Principios Arquitectónicos:**
- **Single Responsibility**: Solo genera PDFs, no conoce lógica de negocio
- **Dependency Inversion**: El servicio depende de la abstracción, no de la implementación
- **Open/Closed**: Fácil de extender sin modificar código existente

#### B. Refactorización del Service Layer

**Archivo**: `apps/tenant/cotizaciones/pdf_service.py`

**Cambios:**
- Eliminadas importaciones directas de `xhtml2pdf`, `pisa`, `BytesIO`
- Ahora importa y usa `CotizacionPDFGenerator`
- El método `render_to_pdf()` solo valida contexto y delega al generador
- No contiene lógica de renderizado de PDF

**Flujo de Dependencias:**
```
pdf_service.py (preparar_contexto_pdf, render_to_pdf)
    ↓
pdf_generator.py (CotizacionPDFGenerator.render_to_pdf)
    ↓
xhtml2pdf (librería externa)
```

### 3. Implementación de Endpoint de Exportación

#### A. Acción `exportar_pdf` en ViewSet

**Archivo**: `apps/tenant/cotizaciones/api/viewsets.py`

**Endpoint**: `GET /api/v1/cotizaciones/{uuid}/exportar-pdf/`

**Características:**
- ✅ **Generación Múltiple**: Permite generar el PDF siempre que se solicite, independientemente del estado
- ✅ **Transición de Estado**: Solo cambia de `BORRADOR` a `ENVIADA` la primera vez
- ✅ **Atomicidad**: Usa `@transaction.atomic` para garantizar integridad
- ✅ **Fallback de Rutas**: Intenta múltiples rutas de templates automáticamente
- ✅ **Manejo de Errores**: Captura específica de `TemplateDoesNotExist` con mensajes claros

**Lógica de Transición de Estado:**
```python
# Solo cambia estado si está en BORRADOR (primera vez)
if cotizacion.estado == Cotizacion.Estado.BORRADOR:
    cotizacion.estado = Cotizacion.Estado.ENVIADA
    cotizacion.save(update_fields=['estado'])
```

**Fallback de Rutas:**
```python
template_paths = [
    'cotizaciones/pdf/formato_profesional.html',  # Ruta estándar
    'tenant/cotizaciones/pdf/formato_profesional.html',  # Ruta alternativa
]
```

### 4. Sincronización de Templates

#### A. Template con Layout de Tablas Clásico

**Archivo Creado**: `apps/tenant/cotizaciones/templates/cotizaciones/pdf/formato_profesional.html`

**Ubicación Correcta:**
```
apps/tenant/cotizaciones/
  └── templates/
      └── cotizaciones/
          └── pdf/
              └── formato_profesional.html
```

**Características del Template:**
- ✅ **Layout de Tablas**: Todo el layout usa `<table>` HTML (compatible con xhtml2pdf)
- ✅ **Sin Flexbox**: No usa CSS moderno incompatible con xhtml2pdf
- ✅ **Sin CSS Grid**: Solo propiedades básicas soportadas
- ✅ **Alineación con `align="right"`**: Para la tabla de totales (sin `margin-left: auto`)

**Estructura del Template:**
1. **Header**: Tabla con información de la cotización
2. **Empresa**: Tabla con datos de la empresa
3. **Cliente**: Tabla dentro de un div con fondo
4. **Sección 1 (PRODUCTO)**: Tabla de items con columnas completas
5. **Sección 2 (MATERIAL)**: Tabla de items con columnas completas
6. **Sección 3 (SERVICIO)**: Tabla de items simplificada
7. **Totales**: Tabla alineada a la derecha (`align="right"`)
8. **Footer**: Información de validez y fecha de generación

**Compatibilidad xhtml2pdf:**
- ✅ Solo propiedades CSS básicas
- ✅ Sin `margin-left: auto` (usa `align="right"` en tabla)
- ✅ Sin `display: flex` o `display: grid`
- ✅ Estructura HTML semántica con tablas

### 5. Corrección de Rutas y Diagnóstico

#### A. Corrección de Ruta del Template

**Problema Identificado:**
- Template estaba en ubicación incorrecta o ruta no coincidía con estructura de Django

**Solución Implementada:**
- Template creado en: `apps/tenant/cotizaciones/templates/cotizaciones/pdf/formato_profesional.html`
- Ruta en código: `cotizaciones/pdf/formato_profesional.html`
- Fallback automático a rutas alternativas

#### B. Logging y Diagnóstico Mejorado

**Archivo**: `apps/tenant/cotizaciones/utils/pdf_generator.py`

**Mejoras:**
- Logging detallado de carga de templates
- Validación de HTML renderizado
- Validación de PDF generado
- Mensajes de error descriptivos

**Archivo**: `apps/tenant/cotizaciones/api/viewsets.py`

**Mejoras:**
- Logging de ruta de template utilizada
- Captura específica de `TemplateDoesNotExist`
- Mensajes de error claros para debugging

### 6. Actualización del Frontend

#### A. Botones de PDF

**Archivos Modificados:**
- `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.page.js`
- `apps/tenant/core/static/core/js/cotizaciones/cotizacion_columns.js`

**Cambios:**
- Actualizado endpoint de `descargar-pdf` a `exportar-pdf`
- Botones ahora apuntan a: `/api/v1/cotizaciones/${uuid}/exportar-pdf/`

### Beneficios de la Refactorización

#### 1. Desacoplamiento Total
- ✅ Lógica de negocio en `services.py` y `serializers.py` permanece pura
- ✅ Solo maneja integridad de datos y cálculos
- ✅ No conoce detalles de generación de PDFs

#### 2. Mantenibilidad
- ✅ Si se decide cambiar `xhtml2pdf` por otra herramienta, solo se modifica `pdf_generator.py`
- ✅ Fácil de testear (mockeable)
- ✅ Código más limpio y organizado

#### 3. Seguridad de Estado
- ✅ Transición de `BORRADOR` a `ENVIADA` encapsulada en la acción del ViewSet
- ✅ Estado solo cambia si el cliente realmente recibe su documento
- ✅ Atomicidad garantizada con `@transaction.atomic`

#### 4. Resiliencia
- ✅ Snapshot Pattern: El PDF siempre muestra la descripción y precios que el usuario guardó
- ✅ Protege la oferta comercial de cambios futuros en los catálogos
- ✅ Generación múltiple sin restricciones de estado

#### 5. Compatibilidad
- ✅ `xhtml2pdf` es más ligero que WeasyPrint
- ✅ No requiere dependencias del sistema
- ✅ Compatible con Docker y entornos cloud

### Archivos Creados

1. `apps/tenant/cotizaciones/utils/__init__.py`
2. `apps/tenant/cotizaciones/utils/pdf_generator.py`
3. `apps/tenant/cotizaciones/templates/cotizaciones/pdf/formato_profesional.html`

### Archivos Modificados

1. `apps/tenant/cotizaciones/pdf_service.py`
2. `apps/tenant/cotizaciones/api/viewsets.py`
3. `apps/tenant/cotizaciones/api/pdf_viewsets.py`
4. `requirements.txt`
5. `config/settings.py`
6. `Dockerfile`
7. `infra/docker/app/Dockerfile`
8. `documentacion/arquitectura_general.md`
9. `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.page.js`
10. `apps/tenant/core/static/core/js/cotizaciones/cotizacion_columns.js`

### Archivos Eliminados

1. Referencias a WeasyPrint en múltiples archivos
2. Dependencias del sistema relacionadas con WeasyPrint

### Estado Final

- ✅ WeasyPrint completamente eliminado
- ✅ `xhtml2pdf` implementado con arquitectura modular
- ✅ Template con layout de tablas clásico compatible
- ✅ Generación múltiple de PDFs habilitada
- ✅ Rutas de templates corregidas y con fallback
- ✅ Logging y diagnóstico mejorado
- ✅ Frontend sincronizado con nuevo endpoint
- ✅ Sin errores de linter
- ✅ Código listo para producción

---

## 🎨 Modernización del Membrete y Optimización de Espacios (2026-03-04)

### Resumen Ejecutivo

Se realizó una modernización completa del membrete del template de PDF, aplicando un diseño más compacto y profesional que maximiza el contenido útil en la primera página, eliminando espacios innecesarios y mejorando la presentación visual.

### 1. Actualización de Estilos CSS Compactos

#### A. Reducción de Tamaños y Espaciados

**Cambios Aplicados:**
- **Tamaño de fuente general**: `10pt` → `9pt`
- **Interlineado general**: `1.4` → `1.1` (más compacto)
- **Margen de página**: `2cm` → `1.5cm` (más espacio útil)

**CSS del Body:**
```css
body {
    font-size: 9pt; /* Reducimos ligeramente el tamaño general */
    line-height: 1.1; /* Interlineado compacto */
}
```

#### B. Membrete Estilo Corporativo Compacto

**Cambios en `.header-table`:**
- Borde inferior: `2px` → `1.5px solid #2c3e50`
- Margen inferior: `25px` → `10px`
- Eliminado `padding-bottom`

**Cambios en `.brand-title`:**
- Tamaño de fuente: `22pt` → `20pt`
- Eliminado `letter-spacing: -1px`
- Agregado `margin: 0; padding: 0;`

**Cambios en `.issuer-data`:**
- Tamaño de fuente: `8.5pt` → `8pt`
- Color: `#555` → `#444`
- Interlineado: `1.2` → `1.0` (espacio mínimo entre líneas)
- Agregado `margin: 0; padding: 0;`

**Regla CSS adicional:**
```css
.issuer-data div {
    margin: 0;
    padding: 0;
    line-height: 1.0;
}
```

#### C. Caja de Cliente Compacta

**Cambios en `.client-box`:**
- Borde izquierdo: `4px` → `3px solid #2c3e50`
- Padding: `12px` → `5px 10px` (padding vertical reducido)
- Margen inferior: `20px` → `15px`

**Cambios en `.info-table td`:**
- Padding: `4px 8px` → `1px 0` (espacio mínimo entre filas)
- Agregado `font-size: 8.5pt`

### 2. Rediseño del Encabezado HTML

#### A. Estructura de Membrete Modernizado

**Layout de dos columnas (50/50):**
- **Columna izquierda:**
  - Título "COTIZACIÓN" con clase `brand-title`
  - Referencia en gris (`#7f8c8d`) con tamaño `9pt`
  - Alineación vertical: `valign="bottom"`

- **Columna derecha:**
  - Datos de la empresa con clase `issuer-data`
  - Nombre de la empresa con clase `issuer-name`
  - NIT, dirección, teléfono y email
  - Alineación vertical: `valign="bottom"`

**Atributos de tabla optimizados:**
- `cellpadding="0"` - Elimina espacios internos
- `cellspacing="0"` - Elimina espacios entre celdas
- `style="padding-bottom: 5px;"` - Control fino de alineación

#### B. Tabla de Fechas y Estado Compacta

**Estructura:**
- Una sola fila con tres columnas (33% cada una)
- **Columna 1:** Fecha de emisión (izquierda)
- **Columna 2:** Fecha de vencimiento (centro)
- **Columna 3:** Estado (derecha)

#### C. Caja de Cliente Simplificada

**Campos esenciales:**
- **CLIENTE:** Nombre comercial en mayúsculas
- **NIT/CC:** Número de documento
- **DIRECCIÓN:** Dirección del cliente (con fallback "N/A")

**Optimizaciones:**
- `cellpadding="0" cellspacing="0"` en tabla interna
- `style="margin: 0;"` para eliminar márgenes
- Etiquetas en mayúsculas y negrita

### 3. Eliminación de Espacios Fantasma

#### A. Atributos de Tabla

**Implementado:**
- `cellpadding="0"` en `header-table` y `info-table` dentro de `client-box`
- `cellspacing="0"` en ambas tablas
- **Resultado:** Elimina píxeles extra entre filas y celdas que el motor de PDF agregaba automáticamente

#### B. Control de Interlineado

**Implementado:**
- `line-height: 1.0` en `.issuer-data` y todos sus divs hijos
- Estilos inline `margin: 0; padding: 0; line-height: 1.0;` en cada div
- **Resultado:** Los datos de Sintel (NIT, Dirección, Teléfono, Email) aparecen pegados uno tras otro, como un membrete real

#### C. Reducción de Padding

**Implementado:**
- `padding: 5px 10px` en `.client-box` (antes `12px`)
- `padding: 1px 0` en `.info-table td` (antes `4px 8px`)
- `margin-bottom: 15px` en `.client-box` (antes `20px`)
- **Resultado:** La información del cliente no ocupa tanto espacio vertical antes de llegar a los ítems

### 4. Estructura HTML Final

```html
<!-- Header: Membrete Modernizado -->
<table class="header-table" cellpadding="0" cellspacing="0">
    <tr>
        <td width="50%" valign="bottom" style="padding-bottom: 5px;">
            <div class="brand-title">COTIZACIÓN</div>
            <div style="color: #7f8c8d; font-size: 9pt;">Ref: {{ cotizacion.codigo_unico }}</div>
        </td>
        <td width="50%" class="issuer-data" valign="bottom" style="padding-bottom: 5px;">
            <div class="issuer-name" style="margin: 0; padding: 0; line-height: 1.0;">{{ empresa.razon_social }}</div>
            <div style="margin: 0; padding: 0; line-height: 1.0;">NIT: {{ empresa.nit }}</div>
            <div style="margin: 0; padding: 0; line-height: 1.0;">{{ empresa.direccion }}</div>
            <div style="margin: 0; padding: 0; line-height: 1.0;">Tel: {{ empresa.telefono }}</div>
            <div style="margin: 0; padding: 0; line-height: 1.0;">{{ empresa.email }}</div>
        </td>
    </tr>
</table>

<!-- Tabla de Fechas -->
<table style="margin-bottom: 15px;">
    <tr>
        <td width="33%"><strong>Emisión:</strong> {{ cotizacion.fecha_emision|date:"d/m/Y" }}</td>
        <td width="33%" style="text-align: center;"><strong>Vencimiento:</strong> {{ cotizacion.fecha_vencimiento|date:"d/m/Y" }}</td>
        <td width="33%" style="text-align: right;"><strong>Estado:</strong> {{ cotizacion.get_estado_display }}</td>
    </tr>
</table>

<!-- Caja de Cliente -->
<div class="client-box">
    <table class="info-table" cellpadding="0" cellspacing="0" style="margin: 0;">
        <tr>
            <td width="15%"><strong>CLIENTE:</strong></td>
            <td>{{ cotizacion.cliente.nombre_comercial|upper }}</td>
        </tr>
        <tr>
            <td><strong>NIT/CC:</strong></td>
            <td>{{ cotizacion.cliente.numero_documento }}</td>
        </tr>
        <tr>
            <td><strong>DIRECCIÓN:</strong></td>
            <td>{{ cotizacion.cliente.direccion|default:"N/A" }}</td>
        </tr>
    </table>
</div>
```

### Beneficios de la Modernización

#### 1. Primera Página Más Llena
- ✅ **Menos espacios en blanco**: Optimización de márgenes y padding
- ✅ **Más contenido útil visible**: Reducción de tamaños de fuente e interlineado
- ✅ **Mejor aprovechamiento del espacio**: Diseño más compacto sin perder legibilidad

#### 2. Membrete Profesional
- ✅ **Diseño moderno**: Color corporativo `#2c3e50` y tipografía refinada
- ✅ **Bloque compacto**: Datos de empresa como membrete real sin espacios
- ✅ **Jerarquía visual clara**: Título destacado y datos organizados

#### 3. Optimización de Espacios
- ✅ **Eliminación de espacios fantasma**: `cellpadding="0"` y `cellspacing="0"`
- ✅ **Control de interlineado**: `line-height: 1.0` para bloque compacto
- ✅ **Reducción de padding**: Menos espacio vertical desperdiciado

#### 4. Compatibilidad Mantenida
- ✅ **xhtml2pdf compatible**: Solo tablas y CSS básico
- ✅ **Sin flexbox ni CSS Grid**: Layout clásico con tablas HTML
- ✅ **Renderizado consistente**: Funciona en todos los sistemas

### Archivos Modificados

1. `apps/tenant/cotizaciones/templates/cotizaciones/pdf/formato_profesional.html`
   - Estilos CSS compactos aplicados
   - Estructura HTML del membrete rediseñada
   - Atributos de tabla optimizados
   - Estilos inline para control fino

### Correcciones Específicas Aplicadas

#### 1. Eliminación de Espacios Fantasma
- `cellpadding="0"` y `cellspacing="0"` en tablas críticas
- Elimina píxeles extra que el motor de PDF agregaba automáticamente

#### 2. Control de Interlineado
- `line-height: 1.0` en `.issuer-data` y todos sus divs
- Estilos inline aplicados a cada elemento
- Datos de Sintel aparecen como bloque compacto

#### 3. Reducción de Padding
- Padding vertical reducido en `.client-box` (de `12px` a `5px 10px`)
- Padding mínimo en `.info-table td` (de `4px 8px` a `1px 0`)
- Margen inferior reducido (de `20px` a `15px`)

### Estado Final

- ✅ Membrete modernizado con diseño corporativo
- ✅ Espacios optimizados para máxima eficiencia
- ✅ Bloque compacto de datos del emisor
- ✅ Primera página con más contenido útil
- ✅ Compatible con xhtml2pdf
- ✅ Sin errores de linter

---

## 📋 CHANGELOG v2.61 (2026-01-27)

### 🎯 Integración con Core API y Alineación con Patrón de Contabilidad

#### Nuevos Endpoints HTMX RESTful
- ✅ **`render_offcanvas_crear`**: GET `/api/v1/cotizaciones/render-offcanvas/crear/`
  - Template: `editor_cotizacion.html`
  - Modo: Creación (is_draft=True)
  - Contexto: clientes y configuraciones activas

- ✅ **`render_offcanvas_editar`**: GET `/api/v1/cotizaciones/{uuid}/render-offcanvas/editar/`
  - Template: `offcanvas_editar_cotizacion.html`
  - Modo: Edición (is_draft=False)
  - Soporte: UUID y ID numérico (compatibilidad)

- ✅ **`render_offcanvas_detalle`**: GET `/api/v1/cotizaciones/render-offcanvas/detalle/?id={uuid}`
  - Template: `offcanvas_ver_detalle.html`
  - Modo: Solo lectura
  - Query params: `id` (UUID o ID numérico)

#### Core API Facade
- ✅ **Router dedicado**: `apps/tenant/core/api/v1/cotizaciones/urls.py`
  - Endpoints: `/api/v1/core/v1/cotizaciones/cotizaciones/`
  - Endpoints: `/api/v1/core/v1/cotizaciones/items/`
  - Endpoints: `/api/v1/core/v1/cotizaciones/configuracion/`
  - Todas las acciones `@action` se heredan automáticamente

- ✅ **CoreLinksViewSet actualizado**: Enlaces para cotizaciones en `/api/v1/core/links/`
  - `cotizaciones`: API y UI links
  - `cotizaciones-items`: API y UI links
  - `cotizaciones-configuracion`: API y UI links

#### Frontend: Corrección del Botón "Nueva Cotización"
- ✅ **Eliminada carga duplicada de HTMX**: Ya cargado en `workspace.html`
- ✅ **Listener de clic directo como fallback**: `handleButtonClick()` en `cotizaciones.page.js`
  - Detecta clics incluso si HTMX no procesa atributos
  - Ejecuta petición HTMX manualmente si es necesario
  - Logs de debugging en consola

- ✅ **Procesamiento HTMX mejorado**: `htmx.process()` cuando se muestra el tab
  - Procesa todo el tab cuando se muestra
  - Procesa específicamente el botón "Nueva Cotización"
  - Timeout de 200ms para asegurar renderizado completo

- ✅ **Offcanvas automático**: Script en `editor_cotizacion.html` muestra offcanvas después de carga HTMX
  - Usa `requestAnimationFrame` para asegurar renderizado
  - Manejo de errores con try/catch
  - Logs de debugging

#### Templates Actualizados
- ✅ **`list.html`**: Botón "Nueva Cotización" actualizado
  - Endpoint: `/api/v1/cotizaciones/render-offcanvas/crear/`
  - Contenedor: `#offcanvas-container` (unificado)
  - Eliminados atributos `data-bs-toggle` y `data-bs-target` (conflicto)

- ✅ **`editor_cotizacion.html`**: Script para mostrar offcanvas automáticamente
  - Ejecución inmediata cuando se carga el contenido
  - Bootstrap.Offcanvas.getOrCreateInstance()

- ✅ **`assets_cotizaciones.html`**: Eliminada carga duplicada de HTMX
  - HTMX ya cargado en `workspace.html`
  - Evita conflictos y doble carga

#### JavaScript Actualizado
- ✅ **`cotizaciones.page.js`**: 
  - Función `editar()` actualizada a nuevo endpoint
  - Listener de clic directo como fallback
  - Procesamiento HTMX cuando se muestra el tab
  - Logs de debugging

- ✅ **`cotizacion_columns.js`**: 
  - Botón Editar actualizado a nuevo endpoint
  - Atributo `hx-indicator` agregado

#### Sincronización con Core API
- ✅ **`apps/tenant/core/api/urls.py`**: 
  - Router dedicado para cotizaciones: `path("v1/cotizaciones/", ...)`
  - Gateway directo: `path("_apps/cotizaciones/", ...)`
  - Documentación completa de endpoints

- ✅ **`apps/tenant/core/api/viewsets.py`**: 
  - Enlaces para cotizaciones en `CoreLinksViewSet.list()`

#### Alineación con Patrón de Contabilidad
- ✅ Mismo patrón de endpoints `render-offcanvas/*`
- ✅ Mismo contenedor `#offcanvas-container`
- ✅ Mismo tipo de offcanvas (`offcanvas-end`)
- ✅ Mismo ancho y estilo (90%, max 1200px)
- ✅ Mismo procesamiento HTMX en tabs

### Archivos Modificados

#### Backend
- `apps/tenant/cotizaciones/api/viewsets.py`: Nuevos endpoints `render-offcanvas/*`
- `apps/tenant/core/api/v1/cotizaciones/urls.py`: Router dedicado (nuevo)
- `apps/tenant/core/api/urls.py`: Integración con Core API
- `apps/tenant/core/api/viewsets.py`: Enlaces para cotizaciones

#### Frontend
- `apps/tenant/core/templates/tenant/core/partials/cotizaciones/list.html`: Botón actualizado
- `apps/tenant/core/templates/tenant/core/partials/cotizaciones/editor_cotizacion.html`: Script automático
- `apps/tenant/core/templates/tenant/core/partials/cotizaciones/assets_cotizaciones.html`: HTMX eliminado
- `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.page.js`: Listener fallback
- `apps/tenant/core/static/core/js/cotizaciones/cotizacion_columns.js`: Botón actualizado

---

## 📋 CHANGELOG v2.61.1 (2026-01-28)

### 🎯 Endpoint de Estadísticas y Optimizaciones de UI

#### Nuevo Endpoint de Estadísticas
- ✅ **`estadisticas`**: GET `/api/v1/cotizaciones/estadisticas/`
  - Retorna resumen completo de cotizaciones:
    - `total_neto`: Suma de `total_con_impuestos` de todas las cotizaciones
    - `cantidad_total`: Total de cotizaciones
    - `cantidad_aceptadas`: Cotizaciones con estado `ACEPTADA`
    - `cantidad_enviadas`: Cotizaciones con estado `ENVIADA`
    - `cantidad_borrador`: Cotizaciones con estado `BORRADOR`
  - Filtrado por empresa del tenant actual (SSoT)
  - Disponible en:
    - `/api/v1/core/v1/cotizaciones/cotizaciones/estadisticas/` (Core API facade)
    - `/api/v1/core/_apps/cotizaciones/estadisticas/` (Gateway directo)

#### Frontend: Panel de Estadísticas
- ✅ **Función `cargarEstadisticas()`**: Consume endpoint y actualiza panel
  - Se ejecuta automáticamente al inicializar el módulo
  - Se actualiza al refrescar la tabla (`refresh()`)
  - Actualiza elementos:
    - `#total-cotizaciones-neto`: Total neto formateado
    - `#cantidad-cotizaciones`: Cantidad total
    - `#cantidad-aceptadas`: Cotizaciones aceptadas
    - `#cantidad-enviadas`: Cotizaciones enviadas
    - `#cantidad-borrador`: Cotizaciones en borrador
  - Exposición: `w.cotizacionesPage.cargarEstadisticas()` para uso manual

#### Optimización de Tabla Principal
- ✅ **Layout optimizado**: Cambio a `fitDataFill` para usar todo el ancho disponible
- ✅ **Columnas con crecimiento proporcional**:
  - `NÚMERO`: `minWidth: 160`, `widthGrow: 1.2`
  - `Fecha`: `minWidth: 110`, `widthGrow: 0.8`
  - `CLIENTE`: `minWidth: 250`, `widthGrow: 3` (mayor crecimiento)
  - `TOTAL`: `minWidth: 140`, `widthGrow: 1.5`
  - `Estado`: `minWidth: 120`, `widthGrow: 1`
  - `Vencimiento`: `minWidth: 120`, `widthGrow: 1`
  - `Acciones`: `minWidth: 280`, `widthGrow: 1.5`, `widthShrink: 0`
- ✅ **Contenedor HTML**: Agregado `width: 100%` y `overflow-x: auto`
- ✅ **Resultado**: Tabla usa todo el ancho disponible, distribuye columnas proporcionalmente

#### Actualización en Tiempo Real del Resumen de Totales (Edición)
- ✅ **Exposición de `recalcularTotalesGlobales()`**: Alias en `CotizacionEditarModule`
  - Compatibilidad con `cotizacion_columns.js`
  - Permite que `getActiveCotizacionModule()` encuentre y llame a esta función
- ✅ **Recálculo automático al cargar datos iniciales**:
  - Usa `w.recalcularFila()` para recalcular cada fila después de cargar datos
  - Asegura que los subtotales estén correctos desde el inicio
- ✅ **Actualización en tiempo real**:
  - Listeners `cellEdited` en columnas ya configurados
  - Cuando se edita una celda (cantidad, precio, utilidad, IVA):
    1. Se dispara `cellEdited`
    2. Se llama a `recalcularFila()` que actualiza el subtotal de la fila
    3. `recalcularFila()` llama a `getActiveCotizacionModule()`
    4. Se obtiene `CotizacionEditarModule` y se llama a `recalcularTotalesGlobales()`
    5. Se actualiza el panel "Resumen de Totales" en tiempo real
- ✅ **Listeners de inputs financieros**: Ya configurados para IVA y AIU

#### Modularización Completa de Crear/Editar/Detalle
- ✅ **Separación completa de templates**:
  - `offcanvas_crear_cotizacion.html`: Exclusivamente para creación
  - `offcanvas_editar_cotizacion.html`: Exclusivamente para edición
  - `offcanvas_cotizacion_detalle.html`: Exclusivamente para detalle (read-only)
- ✅ **Separación completa de JavaScript**:
  - `cotizacion_crear.js`: Lógica exclusiva de creación (POST)
  - `cotizacion_editar.js`: Lógica exclusiva de edición (PATCH)
  - `cotizacion_detalle.js`: Lógica exclusiva de detalle (read-only)
- ✅ **Safeguards mejorados**:
  - Verificación de `data-mode` y `data-cotizacion-uuid` antes de inicializar
  - Prevención de inicializaciones múltiples con flag `data-init`
  - Listeners `shown.bs.offcanvas` como fallback principal
  - Limpieza de estado en `hidden.bs.offcanvas`
- ✅ **Inicialización mejorada**:
  - Múltiples delays para asegurar DOM y dependencias listos
  - Verificación de dependencias críticas antes de inicializar
  - Retry automático si dependencias no están disponibles

#### Mejoras en Inicialización del Módulo
- ✅ **Flag `tableInitialized`**: Previene inicializaciones múltiples
- ✅ **Lazy loading de tabla de configuraciones**: Solo se inicializa cuando se expande el collapse
- ✅ **Verificación de visibilidad**: No inicializa si el tab no está visible
- ✅ **Limpieza de estado**: Función `limpiarEstado()` para reset completo

### Archivos Modificados

#### Backend
- `apps/tenant/cotizaciones/api/viewsets.py`: 
  - Nuevo endpoint `estadisticas()` con agregaciones Django
  - Imports: `Sum`, `Count`, `Q`, `DecimalField`, `Coalesce`, `Decimal`

#### Frontend
- `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.page.js`:
  - Función `cargarEstadisticas()` agregada
  - Llamada automática en `inicializarModulo()`
  - Actualización en `refresh()`
  - Optimización de columnas con `widthGrow` y `minWidth`
  - Configuración `layout: "fitDataFill"` en `tableConfig`
- `apps/tenant/core/static/core/js/cotizaciones/features/cotizacion_editar.js`:
  - Exposición de `recalcularTotalesGlobales()` como alias
  - Recálculo automático de filas al cargar datos iniciales
  - Uso de `w.recalcularFila()` para recalcular subtotales
- `apps/tenant/core/templates/tenant/core/partials/cotizaciones/list.html`:
  - Contenedor actualizado con `width: 100%` y `overflow-x: auto`

---

**Documento generado automáticamente**  
**Última actualización**: 2026-01-29  
**Versión del Sistema**: 2.61.2  
**Estado**: ✅ Validado y Actualizado con Flujo Completo desde Workspace hasta Models, incluyendo Core API y Gateway Directo
