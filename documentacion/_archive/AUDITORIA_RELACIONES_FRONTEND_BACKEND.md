# Auditoria: Integracion Frontend-Backend para Relaciones de Modelo

**Version**: SINTEL v2.61.8  
**Fecha**: 2026-04-04  
**Alcance**: Facturas, Cotizaciones, Gastos, Inventario, Clientes, Perfil, Empresa  
**Estado**: Auditoria completada - Plan de accion definido

---

## Indice

1. [Matriz de Relaciones Criticas](#1-matriz-de-relaciones-criticas)
2. [Estado Actual por Modulo](#2-estado-actual-por-modulo)
3. [Anti-Patterns Detectados](#3-anti-patterns-detectados)
4. [Estandar Tecnico Propuesto](#4-estandar-tecnico-propuesto)
5. [Plan de Migracion por Fases](#5-plan-de-migracion-por-fases)
6. [Modulo Piloto: Inventario](#6-modulo-piloto-inventario)
7. [Checklist por Modulo](#7-checklist-por-modulo)

---

## 1. Matriz de Relaciones Criticas

### 1.1 Relaciones FK por Modelo

| Modelo | FK/Relacion | Modelo Relacionado | on_delete | Criticidad |
|--------|-------------|--------------------|-----------|------------|
| **Cotizacion** | `cliente` | Cliente | SET_NULL | ALTA |
| **Cotizacion** | `configuracion` | ConfiguracionCotizacion | SET_NULL | MEDIA |
| **CotizacionItem** | `cotizacion` | Cotizacion | CASCADE | ALTA |
| **CotizacionItem** | `producto` | Producto | SET_NULL | MEDIA |
| **CotizacionItem** | `servicio` | Servicio | SET_NULL | MEDIA |
| **Gasto** | `documento_soporte` | DocumentoSoporte | PROTECT (1:1) | ALTA |
| **DocumentoSoporte** | `resolucion_dian` | ResolucionDIAN | PROTECT | ALTA |
| **Factura** | `nota_credito` | NotaCredito | (reverse 1:1) | MEDIA |
| **Factura** | `anexos` | FacturaAnexos | (reverse 1:1) | BAJA |
| **ItemFactura** | `factura` | Factura | CASCADE | ALTA |
| **Producto** | `categoria` | CategoriaItem | PROTECT | MEDIA |
| **Servicio** | `categoria` | CategoriaItem | PROTECT | MEDIA |
| **ActivoFijo** | `categoria` | CategoriaItem | SET_NULL | MEDIA |
| **MovimientoInventario** | `producto` | Producto | CASCADE | ALTA |
| **ContactoCliente** | `cliente` | Cliente | CASCADE | ALTA |
| **TenantProfile** | `user` | User (public) | CASCADE (1:1) | ALTA |
| **TenantProfile** | `empresa` | Empresa | CASCADE | ALTA |

### 1.2 Estado Actual vs Deseado

| Relacion | Backend (Selector) | Backend (Serializer) | Frontend (List) | Frontend (Editor) | Estado |
|----------|--------------------|----------------------|-----------------|-------------------|--------|
| Cotizacion->Cliente | `select_related` | PrimaryKeyRelatedField + display | campo plano | fetch directo `/api/v1/clientes/` | PARCIAL |
| Gasto->Proveedor | `select_related` + FK traversal `.only()` | source='doc_soporte.field' flat | campo plano via serializer | fetch `/api/v1/proveedores/` | BUENO |
| Producto->Categoria | `select_related` + FK traversal `.only()` | `source='categoria.nombre'` | `categoria_nombre` plano | fetch `/api/v1/inventario/categorias/` | BUENO |
| Servicio->Categoria | `select_related` + FK traversal `.only()` | `source='categoria.nombre'` | `categoria_nombre` plano | fetch `/api/v1/inventario/categorias/` | BUENO |
| Factura->Cliente | N/A (snapshot) | `source='receptor_razon_social'` | campo plano | N/A (ingesta UBL) | OPTIMO |
| TenantProfile->User | `select_related('user')` + `user__*` | user_* ReadOnlyField | campos planos | N/A | BUENO |

---

## 2. Estado Actual por Modulo

### 2.1 Facturas (OPTIMO)

**Patron**: Snapshot de datos al momento de emision. No FK viva a Cliente.

- **Selectors**: `select_related('nota_credito', 'anexos')` con `.only(*FIELDS)` estricto
- **Serializers**: Campos planos (`receptor_razon_social`, `emisor_nit`), `SerializerMethodField` para anexos
- **ViewSet**: Action-based optimization (`list` -> `qs_list()`, `retrieve` -> `qs_detail()`, `destroy` -> `.only('id', 'estado')`)
- **Frontend**: `factura_table.js` usa `cliente_nombre` plano del serializer. Sin fetch cross-module.

**Calificacion**: Sin hallazgos. Modelo de referencia para relaciones tipo snapshot.

### 2.2 Inventario (BUENO)

**Patron**: FK a CategoriaItem con `select_related` + FK traversal en `.only()`.

- **Selectors**: `PRODUCTO_LIST_FIELDS` incluye `categoria__id`, `categoria__nombre`. `select_related('categoria')` correcto.
- **Serializers**: `categoria_nombre = CharField(source='categoria.nombre', read_only=True)` - patron consistente
- **ViewSet**: Delega a selectores via Service Mixins. Usa `.only()` correctamente.
- **Frontend**: Tabulator muestra `categoria_nombre` plano. Editor carga categorias via `w.http('GET', '/api/v1/inventario/categorias/')` con filtrado por `aplicacion`.

**Hallazgos**:
- El fetch de categorias en `productos_editor.js` y `servicios_editor.js` es **codigo duplicado identico** (misma URL, mismo patron de populate).
- Sin cacheo de categorias entre aperturas consecutivas del offcanvas.
- `CotizacionItemSelector.get_list()` no usa `.only()` - usa `select_related('producto', 'servicio')` sin restriccion de campos.

**Calificacion**: Funcional. Oportunidad de centralizar fetch de categorias y agregar cache.

### 2.3 Gastos (BUENO)

**Patron**: FK One-to-One Gasto->DocumentoSoporte con FK traversal flattened en serializer.

- **Selectors**: `select_related('documento_soporte', 'empresa')` + `.only()` con traversal (`documento_soporte__consecutivo`, etc.)
- **Serializers**: `GastoListSerializer` usa `source='documento_soporte.field'` para aplanar - patron eficiente. `GastoDetailSerializer` anida `DocumentoSoporteDetailSerializer` completo.
- **ViewSet**: Action-based routing a `qs_list()`/`qs_detail()`. Correcto.
- **Frontend**: `gastos.api.js` define URLs cross-module (proveedores, contabilidad). `gasto_editor.js` carga proveedores via fetch directo.

**Hallazgos**:
- `qs_list()` no filtra por `empresa_id` internamente - se delega al ViewSet (patron valido pero requere atencion).
- `gasto_form.js` en `core/static/` es legacy duplicado: carga proveedores con patron diferente al `gasto_editor.js` moderno.
- ~~Variable `proveedoresCatalogo` en closure scope como "cache" manual - sin TTL ni invalidacion.~~ CORREGIDO: Delegado a `gastos.utils.js` con cache 5min + `invalidateCache()`.

**Calificacion**: Funcional. Legacy `gasto_form.js` debe eliminarse.

### 2.4 Cotizaciones (CRITICO - Multiples Defectos)

**Patron**: FK directa a Cliente, ConfiguracionCotizacion; nested items.

- **Selectors**: DETAIL_FIELDS referencia **campos inexistentes** en el modelo.
- **ViewSet**: `get_queryset()` **no usa `.only()`** (viola Rule 4.5 Zero Waste).
- **ViewSet**: No delega a Selectors - construye query inline.

**Hallazgos criticos**:

| # | Severidad | Detalle |
|---|-----------|---------|
| COT-1 | CRITICO | `LIST_FIELDS` referencia `"numero"` pero el modelo usa `numero_cotizacion` |
| COT-2 | CRITICO | `LIST_FIELDS` referencia `"total"` pero el modelo usa `total_con_impuestos` |
| COT-3 | CRITICO | `LIST_FIELDS` y `DETAIL_FIELDS` referencian `"cliente__nombre"` pero Cliente no tiene campo `nombre` (tiene `razon_social` y `nombre_comercial`) |
| COT-4 | CRITICO | `DETAIL_FIELDS` incluye `"proyecto"`, `"subtotal"`, `"total_iva"`, `"observaciones"` - **ninguno existe en el modelo** |
| COT-5 | ALTO | `CotizacionViewSet.get_queryset()` no usa `.only()` - carga TODOS los campos (Zero Waste) |
| COT-6 | ALTO | ViewSet no delega a `CotizacionSelector` - duplica logica de query inline |
| COT-7 | MEDIO | ViewSet busca `numero_cotizacion` y `cliente__razon_social` pero Selector busca `numero` y `cliente__nombre` - incoherencia |
| COT-8 | MEDIO | `CotizacionItemSelector.get_list()` no usa `.only()` |

**Calificacion**: Requiere correccion urgente para alinear selectors con modelo real.

### 2.5 Clientes (BUENO)

**Patron**: Modelo plano. ContactoCliente con FK a Cliente + DSV.

- **Selectors**: `LIST_FIELDS` y `DETAIL_FIELDS` correctos. `.only()` aplicado.
- **Serializers**: `ClienteListSerializer` sin FK, solo display fields. `ContactoClienteSerializer` usa `PrimaryKeyRelatedField` con validacion DSV empresa_id.
- **Frontend**: Sin hallazgos criticos.

**Calificacion**: Funcional. Bien alineado.

### 2.6 Perfil (BUENO)

**Patron**: FK cross-schema a User via `select_related('user')` con `user__*` traversal.

- **Selectors**: `LIST_FIELDS` incluye `user__id`, `user__email`, etc. `select_related('user')` correcto.
- **Serializers**: Expone campos `user_*` como ReadOnlyField con `source='user.field'`.

**Calificacion**: Funcional. Patron de referencia para FK cross-schema.

### 2.7 Empresa (OPTIMO)

**Patron**: Singleton. Sin FK complejas. `logo` como `SerializerMethodField` con URL absoluta.

**Calificacion**: Optimo. Sin hallazgos.

---

## 3. Anti-Patterns Detectados

### AP-1: Codigo Duplicado para Carga de Entidades Relacionadas (MEDIO)

**Ubicacion**: Frontend editors

| Archivo | Linea(s) | Detalle |
|---------|----------|---------|
| `inventario/js/features/productos_editor.js` | ~151 | Fetch categorias + populate select |
| `inventario/js/features/servicios_editor.js` | ~112 | Misma logica identica |
| `inventario/js/features/activos_editor.js` | ~114 | Misma logica + `?page_size=200` |

**Impacto**: Triplicacion de codigo. Si cambia la API de categorias, hay que actualizar 3 archivos.

**Solucion**: Centralizar en helper reutilizable `inventario.utils.js`:
```javascript
// inventario.utils.js
async function loadCategoriasSelect(selectId, aplicacionFilter, selectedId) {
    const res = await w.http('GET', w.Sintel.Inventario.API.categorias.list());
    // ... populate logic
}
```

### AP-2: Fetch sin Cache para Entidades de Referencia (MEDIO)

**Ubicacion**: Cada apertura de offcanvas dispara un GET nuevo.

| Editor | Entidad Cargada | Frecuencia |
|--------|----------------|-----------|
| `productos_editor.js` | Categorias | Cada apertura |
| `servicios_editor.js` | Categorias | Cada apertura |
| `activos_editor.js` | Categorias | Cada apertura |
| `gasto_editor.js` | Proveedores | Cada apertura |
| Cotizaciones legacy | Clientes `?page_size=100` | Cada apertura |

**Impacto**: Requests redundantes. Las categorias/proveedores cambian infrecuentemente.

**Solucion**: Cache en memoria con TTL (patron ya implementado en `routes.js`):
```javascript
const _cache = {};
const CACHE_TTL = 5 * 60 * 1000; // 5 minutos

async function getCachedList(key, fetchFn) {
    const entry = _cache[key];
    if (entry && (Date.now() - entry.ts) < CACHE_TTL) return entry.data;
    const data = await fetchFn();
    _cache[key] = { data, ts: Date.now() };
    return data;
}
```

### AP-3: DETAIL_FIELDS con Campos Inexistentes (CRITICO)

**Ubicacion**: `apps/tenant/cotizaciones/services/selectors.py`

`DETAIL_FIELDS` y `LIST_FIELDS` contienen campos que **no existen** en el modelo `Cotizacion`:
- `"numero"` -> campo real: `numero_cotizacion`
- `"total"` -> campo real: `total_con_impuestos`
- `"cliente__nombre"` -> campo real: `cliente__razon_social`
- `"proyecto"` -> NO EXISTE
- `"subtotal"` -> NO EXISTE
- `"total_iva"` -> NO EXISTE
- `"observaciones"` -> NO EXISTE

**Impacto**: Django `.only()` ignora campos inexistentes sin error (silently), pero difiere el campo real causando queries adicionales al accederlo. El search por `proyecto` y `cliente__nombre` lanza `FieldError` en runtime.

**Solucion**: Alinear con campos reales del modelo (ver Seccion 5, Fase 1).

### AP-4: ViewSet Construye Queries Inline sin Delegar a Selector (ALTO)

**Ubicacion**: `CotizacionViewSet.get_queryset()` (linea ~65-75)

```python
# ACTUAL: query inline sin .only()
queryset = Cotizacion.objects.filter(empresa_id=empresa.id)\
    .select_related('cliente', 'configuracion')\
    .prefetch_related('items')
```

**Impacto**: Viola Rule 4.5 (Zero Waste) y Rule 5 (Service Layer). Carga TODOS los campos de Cotizacion, Cliente, ConfiguracionCotizacion y todos los Items.

**Solucion**: Delegar a `CotizacionSelector.get_list()` / `get_detail()` corregidos.

### AP-5: URLs Hardcodeadas Cross-Modulo (BAJO)

**Ubicacion**: Multiples archivos JS

| Archivo | URL Hardcodeada |
|---------|----------------|
| `productos_editor.js` | `'/api/v1/inventario/categorias/'` |
| `servicios_editor.js` | `'/api/v1/inventario/categorias/'` |
| `gasto_form.js` (legacy) | `/api/v1/proveedores/filtrar-por-tipo/?tipo=...` |
| `cotizaciones.helpers.js` (legacy) | `/api/v1/clientes/?page_size=100&activo=true` |

**Impacto**: Si un endpoint cambia de ruta, multiples archivos se rompen.

**Solucion**: Toda URL cross-modulo debe declararse en el `<app>.api.js` del modulo consumidor (ya implementado en `gastos.api.js` con `proveedores.list` y `contabilidad.cuentasGasto`).

### AP-6: Legacy Core JS Duplicando Funcionalidad FSD (BAJO)

**Ubicacion**: `apps/tenant/core/static/core/js/`

| Legacy | Moderno (FSD) |
|--------|--------------|
| `core/js/gastos/gasto_form.js` | `gastos/js/features/gasto_editor.js` |
| `core/js/cotizaciones/cotizaciones.helpers.js` | `cotizaciones/js/cotizaciones.editor.js` |
| `core/js/cotizaciones/cotizacion_factory.js` | `cotizaciones/js/cotizaciones.module.js` |

**Impacto**: Dos flujos paralelos para la misma funcionalidad. Confusion sobre cual es SSoT.

**Solucion**: Marcar legacy con banners de deprecacion. Migrar gradualmente a FSD.

---

## 4. Estandar Tecnico Propuesto

### 4.1 Estandar de Serializacion para Relaciones

**Principio**: El backend siempre entrega los datos de display listos. El frontend NUNCA debe hacer joins manuales.

#### Tier 1 - Campos Planos (List Serializers)
Para listados Tabulator: aplanar FKs como campos escalares.

```python
class ModeloListSerializer(serializers.ModelSerializer):
    # FK display: ReadOnlyField con source traversal
    cliente_nombre = serializers.ReadOnlyField(source='cliente.razon_social')
    categoria_nombre = serializers.ReadOnlyField(source='categoria.nombre')

    # Choice display
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Modelo
        fields = LIST_FIELDS + ('cliente_nombre', 'categoria_nombre', 'estado_display')
```

**Requisito Backend**: El Selector DEBE usar `select_related()` para toda FK referenciada en `source=`.

#### Tier 2 - Nested Read-Only (Detail Serializers)
Para vistas detalle: incluir objetos anidados read-only.

```python
class ModeloDetailSerializer(serializers.ModelSerializer):
    # FK anidada read-only
    cliente = ClienteMiniSerializer(read_only=True)  # Solo campos esenciales
    items = ItemSerializer(many=True, read_only=True)  # Reverse relation

    class Meta:
        model = Modelo
        fields = DETAIL_FIELDS + ('cliente', 'items')
```

**Requisito Backend**: El Selector DEBE usar `prefetch_related()` para reverse relations.

#### Tier 3 - IDs para Escritura (Create/Update Serializers)
Para formularios: aceptar IDs, retornar confirmacion con display.

```python
class ModeloCreateSerializer(serializers.ModelSerializer):
    cliente_id = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.all(),
        source='cliente',
        write_only=True
    )
    # DSV: validar que cliente.empresa_id == empresa_id del request

    def validate_cliente_id(self, value):
        empresa_id = self.context.get('empresa_id')
        if value.empresa_id != empresa_id:
            raise serializers.ValidationError('Cliente no pertenece a esta empresa.')
        return value
```

### 4.2 Estandar de Selectores (Backend)

**Regla**: `LIST_FIELDS` y `DETAIL_FIELDS` son SSoT. Solo campos que **existen en el modelo**.

```python
# Patron canonico para Selector con FK
LIST_FIELDS = (
    "id", "numero_cotizacion", "estado", "fecha_emision",
    "total_con_impuestos", "empresa_id", "created_at",
)

# FK traversal para display - el campo FK id se incluye implicitamente con select_related
LIST_FK_FIELDS = (
    "cliente__razon_social",
)

class ModeloSelector:
    @staticmethod
    def get_list(empresa_id, search=None):
        return Modelo.objects.filter(
            empresa_id=empresa_id
        ).select_related(
            'cliente'           # Eager load FK
        ).only(
            *LIST_FIELDS,
            *LIST_FK_FIELDS     # FK traversal fields
        ).order_by('-created_at')
```

### 4.3 Estandar de Carga Frontend

#### 4.3.1 Tabulator (Listados)
Los listados Tabulator consumen campos planos del List Serializer. Sin fetch adicional.

```javascript
// Correcto: campo plano del serializer
{ title: "Cliente", field: "cliente_nombre", headerFilter: "input" }

// PROHIBIDO: fetch separado para resolver FK en frontend
```

#### 4.3.2 Editor Offcanvas (Formularios)
Para selects/dropdowns de entidades relacionadas:

```javascript
// Patron: Helper centralizado con cache
async function loadRelatedSelect(selectEl, apiUrl, displayFn, filterFn) {
    const data = await getCachedList(apiUrl, () => w.http('GET', apiUrl));
    const items = (filterFn ? data.filter(filterFn) : data);
    selectEl.innerHTML = '<option value="">Seleccione...</option>' +
        items.map(i => `<option value="${i.id}">${displayFn(i)}</option>`).join('');
}
```

#### 4.3.3 Cache de Entidades de Referencia
Entidades que cambian infrecuentemente (categorias, configuraciones, proveedores activos) deben cachearse con TTL de 5 minutos en memoria del modulo.

```javascript
// Patron: Ya implementado en routes.js - replicar para entidades
const CATALOG_TTL = 5 * 60 * 1000;
const _catalogCache = new Map();

async function getCatalog(key, fetchFn) {
    const cached = _catalogCache.get(key);
    if (cached && (Date.now() - cached.ts) < CATALOG_TTL) return cached.data;
    const data = await fetchFn();
    _catalogCache.set(key, { data, ts: Date.now() });
    return data;
}
```

### 4.4 Estandar de URLs Cross-Modulo

Toda URL de endpoint externo debe declararse en el `<app>.api.js` del modulo consumidor.

```javascript
// gastos.api.js - Correcto: URLs externas declaradas en api.js
const API = {
    gastos: { list: '/api/v1/gastos/', ... },
    proveedores: { list: '/api/v1/proveedores/' },       // Cross-module
    contabilidad: { cuentasGasto: '/api/v1/contabilidad/cuentas-gasto/' }  // Cross-module
};
```

---

## 5. Plan de Migracion por Fases

### Fase 0: Correccion Critica - Cotizaciones Selectors (COMPLETADA v2.61.8)

**Estado**: COMPLETADA
**Prioridad**: P0 - Los campos inexistentes causaban queries ineficientes y potenciales FieldError.

**Archivos modificados**:
- `apps/tenant/cotizaciones/services/selectors.py` - Reescrito v3.6: LIST_FIELDS, DETAIL_FIELDS, LIST_FK_FIELDS, DETAIL_FK_FIELDS, ITEM_LIST_FIELDS corregidos
- `apps/tenant/cotizaciones/api/viewsets.py` - ViewSet hereda CotizacionServiceMixin, delega a CotizacionSelector con `.only()`, get_serializer_class() action-based
- `apps/tenant/cotizaciones/api/serializers.py` - Agregado CotizacionListSerializer con campos planos para Tabulator

**Cambios especificos**:

```python
# selectors.py - CORREGIDO
LIST_FIELDS = (
    "id",
    "uuid",
    "numero_cotizacion",       # era "numero"
    "cliente_id",              # FK id
    "fecha_emision",
    "fecha_vencimiento",
    "estado",
    "total_con_impuestos",     # era "total"
    "empresa_id",
    "created_at",
)

LIST_FK_FIELDS = (
    "cliente__razon_social",   # era "cliente__nombre" (no existe)
)

DETAIL_FIELDS = (
    "id",
    "uuid",
    "numero_cotizacion",       # era "numero"
    "cliente_id",
    "fecha_emision",
    "fecha_vencimiento",
    "estado",
    "tipo_cotizacion",
    "iva_porcentaje",
    "porcentaje_aiu_admin",
    "porcentaje_aiu_imprevistos",
    "porcentaje_aiu_utilidad",
    "total_con_impuestos",     # era "total_iva" y "total"
    "codigo_unico",
    "empresa_id",
    "created_at",
    "updated_at",
)
# Removidos: "proyecto", "subtotal", "total_iva", "total", "observaciones" (no existen)

DETAIL_FK_FIELDS = (
    "cliente__razon_social",
    "cliente__numero_documento",
    "configuracion__id",
)
```

### Fase 1: Estandarizacion de Inventario (COMPLETADA v2.61.8)

**Estado**: COMPLETADA
**Prioridad**: P1 - Modulo mas maduro, sirve como referencia.

1. ~~Crear `inventario.utils.js` con helper `loadCategoriasSelect()` reutilizable~~ HECHO
2. ~~Refactorizar `productos_editor.js`, `servicios_editor.js`, `activos_editor.js` para usar helper~~ HECHO
3. ~~Agregar cache en memoria con TTL 5min para catalogos de categorias~~ HECHO
4. ~~Agregar `.only()` a `CotizacionItemSelector.get_list()`~~ HECHO (Fase 0)
5. ~~Registrar `inventario.utils.js` en `assets_inventario.html`~~ HECHO
6. ~~Invalidar cache en `categorias_editor.js` tras CRUD exitoso~~ HECHO

### Fase 2: Estandarizacion de Gastos (COMPLETADA v2.61.8)

**Estado**: COMPLETADA
**Prioridad**: P2

1. ~~Verificar que `qs_list()` en selectors reciba y aplique `empresa_id`~~ HECHO - selectors OK, ViewSet corregido (faltaba empresa_id en qs_list/qs_detail)
2. ~~Marcar `core/js/gastos/gasto_form.js` como deprecated~~ HECHO - Header DEPRECATED agregado
3. ~~Centralizar URL de proveedores en `gastos.api.js`~~ Ya estaba hecho
4. Agregar cache para lista de proveedores en editor (diferido - solo 1 editor lo usa)

**Bugs criticos corregidos**:
- `GastoViewSet.get_queryset()`: `qs_list(search=search)` y `qs_detail()` llamados SIN `empresa_id` (TypeError en runtime) - CORREGIDO
- `GASTO_DETAIL_FIELDS`: `cuenta_contable_uuid` y `cuenta_contable_display` no existen en modelo (campo real: `codigo_contable`) - CORREGIDO en selectors.py y services.py
- Legacy `core/partials/gastos/assets_gastos.html`: Header DEPRECATED agregado

### Fase 3: Limpieza Legacy Cotizaciones (COMPLETADA v2.61.8)

**Estado**: COMPLETADA
**Prioridad**: P2

1. ~~Aplicar correcciones de Fase 0 (selectors)~~ COMPLETADA en Fase 0
2. ~~Refactorizar `CotizacionViewSet.get_queryset()` para delegar a Selector con `.only()`~~ COMPLETADA en Fase 0
3. ~~Agregar `CotizacionListSerializer` con `cliente_nombre = ReadOnlyField(source='cliente.razon_social')`~~ COMPLETADA en Fase 0
4. ~~Separar serializers List vs Detail (actualmente solo `CotizacionSerializer`)~~ COMPLETADA en Fase 0
5. ~~Limpiar legacy en `core/js/cotizaciones/`~~ HECHO - Header DEPRECATED agregado en `core/partials/cotizaciones/assets_cotizaciones.html`

**Nota**: La eliminacion fisica de scripts legacy en `core/js/cotizaciones/` y `core/js/gastos/` requiere migrar `workspace.html` a los assets modernos de cada app, lo cual necesita aprobacion explicita.

### Fase 4: Clientes - Normalizacion Display (COMPLETADA v2.61.8)

**Estado**: COMPLETADA
**Prioridad**: P3

1. ~~Agregar `ClienteMiniSerializer` (id, razon_social, numero_documento) para uso nested en otros modulos~~ HECHO
   - Campos: id, numero_documento, razon_social, nombre_comercial, email, telefono (read-only)
   - Ubicacion: `apps/tenant/clientes/api/serializers.py`
2. ~~Garantizar que todos los modulos que referencian Cliente usen `razon_social` (no `nombre`)~~ VERIFICADO
   - Auditoria cross-modulo confirma que ningun modulo usa `cliente__nombre` en queries
   - Frontend usa `cliente_nombre` como campo aplanado del serializer (correcto)
3. Fix adicional: `cotizacion_list.js` alineado con `CotizacionListSerializer`
   - `"numero"` -> `"numero_cotizacion"`, `"total"` -> `"total_con_impuestos"`

---

## 6. Modulo Piloto: Inventario

### Estado Actual (BUENO)

El modulo Inventario ya implementa correctamente la mayoria del estandar:

| Componente | Estado | Detalle |
|------------|--------|---------|
| Selectors | OK | `select_related('categoria')` + FK traversal en `.only()` |
| List Serializer | OK | `categoria_nombre = CharField(source='categoria.nombre')` |
| Detail Serializer | OK | Misma patron consistente |
| ViewSet | OK | Delega a Selectors via Service Mixins |
| Tabulator | OK | Usa `categoria_nombre` plano |
| Editor | MEJORABLE | Fetch duplicado de categorias sin cache |

### Implementacion Propuesta

**Paso 1**: Crear helper en `inventario.utils.js`:

```javascript
// apps/tenant/inventario/static/inventario/js/inventario.utils.js
(function(w, d) {
    'use strict';
    const MOD = '[inventario.utils]';
    const CACHE_TTL = 5 * 60 * 1000;
    let _categoriasCache = null;
    let _categoriasCacheTs = 0;

    async function fetchCategorias() {
        if (_categoriasCache && (Date.now() - _categoriasCacheTs) < CACHE_TTL) {
            return _categoriasCache;
        }
        const res = await w.http('GET', '/api/v1/inventario/categorias/');
        if (!res.ok || !res.data) {
            console.warn(MOD, 'Error al cargar categorias');
            return [];
        }
        _categoriasCache = Array.isArray(res.data) ? res.data : (res.data.results || []);
        _categoriasCacheTs = Date.now();
        return _categoriasCache;
    }

    async function loadCategoriasSelect(selectId, aplicacionFilter, selectedId) {
        const select = d.querySelector(selectId);
        if (!select) return;
        const categorias = await fetchCategorias();
        const filtered = aplicacionFilter
            ? categorias.filter(c => c.aplicacion === aplicacionFilter || c.aplicacion === 'TODO')
            : categorias;
        select.innerHTML = '<option value="">Sin categoria</option>';
        filtered.forEach(cat => {
            const opt = d.createElement('option');
            opt.value = cat.id;
            opt.textContent = cat.nombre;
            if (selectedId && cat.id == selectedId) opt.selected = true;
            select.appendChild(opt);
        });
    }

    function invalidateCache() {
        _categoriasCache = null;
        _categoriasCacheTs = 0;
    }

    w.Sintel = w.Sintel || {};
    w.Sintel.Inventario = w.Sintel.Inventario || {};
    w.Sintel.Inventario.Utils = { loadCategoriasSelect, invalidateCache };
})(window, document);
```

**Paso 2**: Refactorizar editors para usar helper:

```javascript
// productos_editor.js - ANTES (~25 lineas duplicadas)
const res = await w.http('GET', '/api/v1/inventario/categorias/');
// ... 20 lineas de populate logic

// productos_editor.js - DESPUES (1 linea)
await w.Sintel.Inventario.Utils.loadCategoriasSelect('#producto-categoria', 'PRODUCTO', categoriaActual);
```

**Paso 3**: Invalidar cache al crear/editar categoria:

```javascript
// categorias_editor.js - tras submit exitoso
w.Sintel.Inventario.Utils.invalidateCache();
```

---

## 7. Checklist por Modulo

### Facturas
- [x] Selector con select_related + .only()
- [x] List Serializer con campos planos
- [x] Detail Serializer con nested read-only
- [x] ViewSet delega a Selectors
- [x] Frontend usa campos planos
- [x] Sin fetch cross-module redundante
- [N/A] Cache de entidades relacionadas (no aplica - snapshot)

### Inventario
- [x] Selector con select_related + FK traversal en .only()
- [x] List Serializer con source='categoria.nombre'
- [x] Detail Serializer consistente
- [x] ViewSet delega a Selectors via Mixins
- [x] Tabulator usa campo plano categoria_nombre
- [ ] Helper centralizado para load categorias (AP-1)
- [ ] Cache en memoria con TTL (AP-2)
- [ ] CotizacionItemSelector con .only() (COT-8)

### Gastos
- [x] Selector con select_related + FK traversal en .only()
- [x] List Serializer con source='documento_soporte.field'
- [x] Detail Serializer con nested DocumentoSoporteDetailSerializer
- [x] ViewSet delega a Selectors (qs_list/qs_detail)
- [x] URLs cross-module en gastos.api.js
- [ ] Verificar empresa_id en qs_list() internamente
- [ ] Deprecar core/js/gastos/gasto_form.js (AP-6)
- [ ] Cache de proveedores en editor (AP-2)

### Cotizaciones
- [ ] Corregir LIST_FIELDS: numero -> numero_cotizacion, total -> total_con_impuestos (COT-1, COT-2)
- [ ] Corregir FK traversal: cliente__nombre -> cliente__razon_social (COT-3)
- [ ] Eliminar campos inexistentes de DETAIL_FIELDS (COT-4)
- [ ] ViewSet .only() via Selector (COT-5)
- [ ] ViewSet delega a CotizacionSelector (COT-6)
- [ ] Alinear search fields entre Selector y ViewSet (COT-7)
- [ ] CotizacionItemSelector con .only() (COT-8)
- [ ] Crear CotizacionListSerializer separado
- [ ] Agregar cliente_nombre = ReadOnlyField(source='cliente.razon_social')
- [ ] Limpiar legacy core/js/cotizaciones/

### Clientes
- [x] Selector con .only()
- [x] ContactoSelector con select_related('cliente')
- [x] DSV en ContactoClienteSerializer
- [x] Sin hallazgos criticos
- [ ] Crear ClienteMiniSerializer para uso nested cross-module

### Perfil
- [x] Selector con select_related('user') + user__* traversal
- [x] Serializer con user_* ReadOnlyField
- [x] Sin hallazgos

### Empresa
- [x] Selector con .only()
- [x] Serializer con logo URL absoluta
- [x] Sin hallazgos

---

## Resumen Ejecutivo

| Modulo | Estado | Hallazgos Criticos | Hallazgos Medios | Accion Requerida |
|--------|--------|--------------------|-------------------|------------------|
| Facturas | OPTIMO | 0 | 0 | Ninguna |
| Inventario | COMPLETADO | 0 | 0 | ~~Centralizar fetch categorias + cache~~ HECHO v2.61.8 |
| Gastos | CORREGIDO | 0 | 0 | ~~Corregir empresa_id + campos inexistentes~~ HECHO v2.61.8. ~~Cache proveedores~~ HECHO v2.61.8 |
| Cotizaciones | CORREGIDO | 0 | 1 | ~~Correccion urgente de selectors + ViewSet~~ HECHO v2.61.8. Pendiente: eliminar legacy core/js |
| Clientes | COMPLETADO | 0 | 0 | ~~ClienteMiniSerializer~~ HECHO v2.61.8 |
| Perfil | BUENO | 0 | 0 | Ninguna |
| Empresa | OPTIMO | 0 | 0 | Ninguna |

**Prioridad de ejecucion**: ~~Fase 0~~ COMPLETADA -> ~~Fase 1~~ COMPLETADA -> ~~Fase 2~~ COMPLETADA -> ~~Fase 3~~ COMPLETADA -> ~~Fase 4~~ COMPLETADA

**Estado final v2.61.8**: Todas las fases completadas. Pendiente unicamente la migracion de workspace.html a assets modernos (requiere aprobacion explicita).

---

## 8. Hallazgo Critico: Doble Carga de Assets en workspace.html

### 8.1 Cotizaciones: Doble Carga Legacy + Moderno

**Estado actual en workspace.html:**
1. **Global (linea ~241):** `{% include 'tenant/core/partials/cotizaciones/assets_cotizaciones.html' %}` - LEGACY
2. **Dentro del tab:** `{% include 'cotizaciones/list.html' %}` -> incluye `cotizaciones/assets_cotizaciones.html` - MODERNO

**Impacto:**
- Ambos conjuntos de scripts se cargan simultaneamente en la pagina.
- Ambos intentan inicializar Tabulator en `#tabla-cotizaciones-principal`.
- Legacy usa `TabulatorFactory.create()` con `DOMUtils.onVisibleOnce()` (lazy, completo).
- Moderno usa `new Tabulator()` directo en `DOMContentLoaded` (basico, incompleto).
- Los scripts modernos (`cotizaciones.table.js`) son un borrador incompleto: solo 6 columnas basicas, JWT mal inyectado, sin CRUD.
- El codigo de produccion real es el legacy (`cotizaciones.page.js`).

**Namespaces en conflicto:**
- Legacy: `window.cotizacionesAPI`, `window.CotizacionesHelpers`, `window.getCotizacionColumns`, `window.cotizacionesPage`
- Moderno: `window.Sintel.Cotizaciones.*`

**Nota sobre cotizacion_list.js (Fase 4):**
- El fix de campos `numero_cotizacion` / `total_con_impuestos` fue correcto respecto al `CotizacionListSerializer`.
- Sin embargo, `cotizacion_list.js` solo se carga en `list_full.html`, que no esta referenciado por ninguna vista ni template activo.
- La tabla activa se renderiza via el legacy `cotizaciones.page.js` con sus propias definiciones de columnas.

**Migracion requerida (alta complejidad):**
1. Completar los scripts modernos para cubrir toda la funcionalidad legacy (TabulatorFactory, CRUD, configuraciones, PDF, estadisticas).
2. Solo entonces, remover el include legacy de workspace.html.

### 8.2 Gastos: Solo Legacy Activo

**Estado actual en workspace.html:**
- **Global (linea ~240):** `{% include 'tenant/core/partials/gastos/assets_gastos.html' %}` - LEGACY (core)
- **El tab NO carga assets modernos.** `tenant/gastos/list.html` es un wrapper que incluye `gastos_list.html` sin assets propios.

**Scripts legacy activos (produccion):**
- `core/js/gastos/gastos.api.js` -> `w.gastosAPI`
- `core/js/gastos/gastos_main.js` -> `w.AppGastos` (Tabulator + resumen + acciones)
- `core/js/gastos/gasto_form.js` -> Formulario de gasto (DEPRECATED header)
- `core/js/gastos/resolucion_dian_main.js` -> Lista resoluciones
- `core/js/gastos/resolucion_dian_form.js` -> Formulario resoluciones

**Scripts modernos (preparados, NO cargados en workspace):**
- `gastos/js/gastos.api.js` -> `window.Sintel.Gastos.API`
- `gastos/js/gastos.utils.js` -> `window.Sintel.Gastos.Utils` (cache proveedores/cuentas)
- `gastos/js/features/gasto_list.js` -> `window.Sintel.Gastos.GastoList`
- `gastos/js/features/gasto_editor.js` -> `window.Sintel.Gastos.GastoEditor`
- `gastos/js/features/resolucion_editor.js` -> `window.Sintel.Gastos.ResolucionEditor`

**Migracion requerida (alta complejidad):**
1. Asegurar que los scripts modernos cubran toda la funcionalidad de `gastos_main.js` (Tabulator via TabulatorFactory, resumen, acciones anular/desactivar).
2. Cambiar workspace.html de legacy a moderno: `{% include 'tenant/gastos/assets_gastos.html' %}`
3. Actualizar `tenant/gastos/list.html` para incluir assets propios (como cotizaciones/list.html ya lo hace).

### 8.3 Impacto en el Plan

Las migraciones de workspace.html para gastos y cotizaciones son proyectos de alta complejidad que requieren:
- Auditoria funcional completa de cada script legacy para mapear features a sus equivalentes modernos.
- Completar los scripts modernos donde tengan gaps (especialmente `cotizaciones.table.js`).
- Testing E2E en Docker con datos reales (crear, editar, eliminar, exportar PDF, estadisticas).
- Requiere aprobacion explicita del usuario antes de ejecutar.
