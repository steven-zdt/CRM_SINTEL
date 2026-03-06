# Módulo de Gastos v2.40 - Documentación Completa

## 📋 Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura General](#arquitectura-general)
3. [Modelos de Datos](#modelos-de-datos)
4. [Service Layer](#service-layer)
5. [API REST (ViewSets y Serializers)](#api-rest-viewsets-y-serializers)
6. [Frontend (Templates y JavaScript)](#frontend-templates-y-javascript)
7. [Funcionalidades Implementadas](#funcionalidades-implementadas)
8. [Flujos de Trabajo](#flujos-de-trabajo)
9. [Validaciones y Reglas de Negocio](#validaciones-y-reglas-de-negocio)

---

## Resumen Ejecutivo

El módulo de Gastos v2.40 implementa un sistema completo de gestión de Documentos Soporte según la normativa DIAN colombiana (Art. 1.6.1.4.12 DR 1625 de 2016). El sistema garantiza **inmutabilidad legal**, **consecutividad única** y **cálculo automático de retenciones** (Retefuente y ReteICA).

### Características Principales

- ✅ **Documento Soporte Inmutable**: Una vez generado el consecutivo, los valores son inmutables
- ✅ **Resoluciones DIAN**: Gestión independiente de resoluciones DIAN con validación de rangos
- ✅ **Cálculo Automático de Retenciones**: Retefuente e ICA calculados automáticamente desde porcentajes
- ✅ **Consecutividad Garantizada**: Números consecutivos únicos, incluso si hay documentos anulados
- ✅ **Summary Financiero**: Panel de resumen con Retefuente e ICA independientes
- ✅ **API-First**: Arquitectura REST con TabulatorFactory para tablas interactivas

---

## Arquitectura General

### Patrón de Diseño

El módulo sigue el patrón **Service Layer** con separación clara de responsabilidades:

```
Frontend (Templates + JavaScript)
    ↓
API REST (ViewSets + Serializers)
    ↓
Service Layer (Lógica de Negocio)
    ↓
Models (Datos)
```

### Componentes Principales

1. **Models**: `DocumentoSoporte`, `Gasto`, `ResolucionDIAN`
2. **Services**: `services.py` - Lógica de negocio centralizada
3. **ViewSets**: `GastoViewSet`, `ResolucionDIANViewSet`
4. **Serializers**: Serializadores para listado, detalle y creación
5. **Frontend**: Templates HTML + JavaScript modular

---

## Modelos de Datos

### DocumentoSoporte

**Ubicación**: `apps/tenant/gastos/models.py`

**Descripción**: Evidencia legal inmutable según normativa DIAN. Una vez generado el consecutivo, los valores monetarios son inmutables.

#### Campos Principales

##### Datos Fiscales
- `empresa`: FK a Empresa (SSoT - Single Source of Truth)
- `resolucion_dian`: FK a ResolucionDIAN
- `prefijo`: CharField (ej: "SI", "DS")
- `consecutivo`: IntegerField (único por resolución, inmutable)
- `fecha`: DateField

##### Datos del Vendedor (Snapshot Histórico)
- `vendedor_nit`: CharField
- `vendedor_nombre`: CharField
- `vendedor_direccion`: CharField (opcional)
- `vendedor_telefono`: CharField (opcional)
- `numero_factura_proveedor`: CharField (opcional)

##### Valores Monetarios (Inmutables)
- `subtotal`: DecimalField (base gravable)
- `retefuente_porcentaje`: CharField con choices (0%, 4%, 6%, 10%, 11%)
- `retefuente`: DecimalField (calculado automáticamente)
- `reteica_porcentaje`: CharField con choices (0%, 0.69%, 0.966%, 1.104%)
- `reteica`: DecimalField (calculado automáticamente)
- `total`: DecimalField (Subtotal - Retefuente - ReteICA)

##### Estado
- `activo`: BooleanField (default=True, db_index=True)
  - Indica si el documento está activo
  - **REGLAS**: Debe estar desactivado (`activo=False`) para poder anular
  - Los documentos desactivados se excluyen del summary financiero
- `anulado`: BooleanField (default=False, db_index=True)
  - Indica si el documento ha sido anulado
  - **REGLAS**: Solo se puede anular si está desactivado (`activo=False`)
- `fecha_anulacion`: DateTimeField (opcional)
  - Fecha y hora de anulación

#### Choices de Retenciones

**Retefuente**:
```python
RETEFUENTE_CHOICES = [
    ('0.00', '0% - Sin Retefuente'),
    ('0.04', '4% - Servicios (Declarantes)'),
    ('0.06', '6% - Servicios (No Declarantes)'),
    ('0.10', '10% - Honorarios y Consultoría (Persona Natural no declarante)'),
    ('0.11', '11% - Honorarios y Consultoría (Persona Jurídica o declarante)'),
]
```

**ReteICA**:
```python
RETEICA_CHOICES = [
    ('0.00', '0% - Exento'),
    ('0.0069', '0.69% - Tarifa 0.69% (6.9/1000)'),
    ('0.00966', '0.966% - Tarifa 0.966% (9.66/1000)'),
    ('0.01104', '1.104% - Tarifa 1.104% (11.04/1000)'),
]
```

#### Propiedades de Formato COP

Todas las propiedades retornan valores formateados como dinero en pesos colombianos:

- `subtotal_cop`: `"$1.000.000"`
- `retefuente_cop`: `"$40.000"`
- `reteica_cop`: `"$9.660"`
- `total_cop`: `"$950.340"`
- `total_retenciones_cop`: `"$49.660"`

#### Validaciones

1. **Consecutivo dentro del rango**: Valida que el consecutivo esté entre `rango_desde` y `rango_hasta` de la resolución
2. **Cálculo automático**: En `clean()`, calcula automáticamente las retenciones basándose en los porcentajes
3. **Fórmula de total**: Valida que `total = subtotal - retefuente - reteica`

#### Constraints

- `unique_ds_resolucion_consecutivo`: Garantiza que no haya duplicados de consecutivo por resolución
- `unique_ds_vendedor_factura`: Evita duplicados de factura del mismo vendedor (solo si no está anulado)

### Gasto

**Descripción**: Clasificación contable del DocumentoSoporte (centro de costos/categoría).

#### Campos Principales

- `documento_soporte`: OneToOneField a DocumentoSoporte
- `empresa`: FK a Empresa (SSoT)
- `periodo`: CharField (formato: YYYY-MM)
- `centro_costo`: CharField con choices
- `categoria_contable`: CharField con choices
- `descripcion`: TextField
- `observaciones`: TextField

#### Properties Delegadas

Todas las propiedades monetarias delegan al DocumentoSoporte:
- `subtotal`, `retefuente`, `reteica`, `total`
- `subtotal_cop`, `retefuente_cop`, `reteica_cop`, `total_cop`, `total_retenciones_cop`
- `fecha`, `numero_documento`

### ResolucionDIAN

**Descripción**: Resolución DIAN que autoriza la emisión de Documentos Soporte.

#### Campos Principales

- `empresa`: FK a Empresa (SSoT)
- `numero_resolucion`: CharField (número asignado por DIAN)
- `prefijo`: CharField (ej: "SI", "DS")
- `rango_desde`: IntegerField
- `rango_hasta`: IntegerField
- `fecha_resolucion`: DateField (fecha de emisión)
- `fecha_inicio`: DateField (inicio de vigencia)
- `fecha_fin`: DateField (fin de vigencia)
- `vigente`: BooleanField (solo una por empresa puede estar vigente)

#### Validaciones

- `fecha_fin > fecha_inicio`
- `rango_hasta > rango_desde`
- Solo una resolución puede estar `vigente=True` por empresa

---

## Service Layer

**Ubicación**: `apps/tenant/gastos/services.py`

### Funciones Principales

#### Cálculo de Retenciones

```python
def calcular_retenciones(subtotal: Decimal, retefuente_porcentaje: str, reteica_porcentaje: str) -> Dict[str, Decimal]
```

**Descripción**: Calcula las retenciones basándose en el subtotal y los porcentajes.

**Parámetros**:
- `subtotal`: Base gravable
- `retefuente_porcentaje`: Porcentaje de Retefuente (string, ej: '0.04')
- `reteica_porcentaje`: Porcentaje de ReteICA (string, ej: '0.00966')

**Retorna**:
```python
{
    'retefuente': Decimal('40000.00'),
    'reteica': Decimal('9660.00'),
    'total': Decimal('950340.00')
}
```

**Validaciones**:
- Subtotal no puede ser negativo
- Total no puede ser negativo (retenciones no pueden exceder subtotal)

#### Gestión de Consecutivos

```python
def obtener_siguiente_numero_soporte(empresa: Any) -> int
```

**Descripción**: Calcula el siguiente consecutivo disponible para la resolución vigente.

**Características**:
- Busca automáticamente la resolución vigente
- Incluye TODOS los documentos (incluso anulados) para evitar duplicados
- Valida que el consecutivo esté dentro del rango
- Valida que no exista ya el consecutivo (doble verificación)

**Ejemplo**:
```python
# Si el último consecutivo es 150, retorna 151
consecutivo = obtener_siguiente_numero_soporte(empresa)
```

#### Resumen Financiero

```python
def get_gastos_summary(empresa_id: Optional[int] = None) -> Dict[str, Any]
```

**Descripción**: Calcula totales financieros netos excluyendo documentos anulados.

**Retorna**:
```python
{
    "subtotal_neto": Decimal('1000000.00'),
    "retefuente_neto": Decimal('40000.00'),  # ⚠️ v2.40: Independiente
    "reteica_neto": Decimal('9660.00'),  # ⚠️ v2.40: Independiente
    "retenciones_neto": Decimal('49660.00'),  # Total combinado
    "total_neto": Decimal('950340.00'),
    "cantidad": 10
}
```

**Características**:
- Excluye automáticamente documentos anulados (`anulado=False`)
- Excluye automáticamente documentos desactivados (`activo=True`)
- Solo suma documentos activos y no anulados (`activo=True AND anulado=False`)
- Retorna Retefuente e ICA por separado
- Mantiene `retenciones_neto` para compatibilidad

#### Gestión de Documentos (Desactivación y Anulación)

```python
def desactivar_gasto_service(gasto_id: int) -> Dict[str, Any]
def anular_gasto_service(gasto_id: int) -> Dict[str, Any]
```

**Características**:
- `desactivar_gasto_service()`: 
  - Marca el documento como `activo=False`
  - Paso previo obligatorio antes de anular
  - Usa `update()` directamente para evitar validaciones del modelo
  - Valida que no esté ya desactivado o anulado
- `anular_gasto_service()`:
  - **REGLAS CRÍTICAS**: Solo permite anular si `activo=False`
  - Si el documento está activo, retorna error: "No se puede anular un documento activo. Debe desactivarlo primero."
  - Usa `update()` directamente para evitar validaciones de total
  - Conserva valores originales (inmutabilidad legal)

#### Gestión de Resoluciones

```python
def crear_resolucion(empresa: Any, data: Dict[str, Any]) -> ResolucionDIAN
def desactivar_resolucion(empresa: Any, resolucion_id: int) -> ResolucionDIAN
def puede_eliminar_resolucion(empresa: Any, resolucion_id: int) -> Tuple[bool, str]
def obtener_resolucion_vigente(empresa: Any) -> Optional[ResolucionDIAN]
```

**Características**:
- `crear_resolucion()`: Si se marca como vigente, desactiva automáticamente las anteriores
- `desactivar_resolucion()`: Solo desactiva, no elimina (los documentos conservan su referencia)
- `puede_eliminar_resolucion()`: Valida que no tenga Documentos de Soporte asociados
- `obtener_resolucion_vigente()`: Retorna la única resolución vigente por empresa

#### QuerySets Optimizados

```python
def qs_list(search=None) -> QuerySet
def qs_detail() -> QuerySet
def qs_resolucion_list(empresa_id: int) -> QuerySet
def qs_resolucion_detail(empresa_id: int, resolucion_id: int) -> QuerySet
```

**Características**:
- `qs_list()`: **INCLUYE TODOS LOS DOCUMENTOS** (anulados y no anulados) para mantener secuencia de consecutivos
- Optimizado con `select_related()` y `only()` para reducir queries
- Soporta búsqueda con parámetro `?search=`

---

## API REST (ViewSets y Serializers)

### GastoViewSet

**Ubicación**: `apps/tenant/gastos/api/viewsets.py`

**Endpoints**:
- `GET /api/v1/gastos/` - Lista paginada (incluye anulados y desactivados)
- `POST /api/v1/gastos/` - Crear nuevo gasto
- `GET /api/v1/gastos/{id}/` - Detalle
- `DELETE /api/v1/gastos/{id}/` - Eliminar
- `GET /api/v1/gastos/summary/` - Resumen financiero (solo activos y no anulados)
- `POST /api/v1/gastos/{id}/desactivar/` - Desactivar documento (paso previo a anular)
- `POST /api/v1/gastos/{id}/anular/` - Anular documento (solo si está desactivado)

**Características**:
- **Bloquea PUT/PATCH**: Los documentos son inmutables
- **Usa resolución vigente automáticamente**: No requiere enviar `resolucion_dian`
- **Cálculo automático**: Usa `calcular_retenciones()` del service layer
- **Paginación**: `StandardResultsSetPagination` para Tabulator

#### Método `create()`

```python
def create(self, request, *args, **kwargs):
    # 1. Obtiene empresa del tenant (SSoT)
    # 2. Obtiene resolución vigente automáticamente
    # 3. Calcula siguiente consecutivo
    # 4. Calcula retenciones usando calcular_retenciones()
    # 5. Crea DocumentoSoporte con valores calculados
    # 6. Crea Gasto asociado
```

**Payload esperado**:
```json
{
    "fecha": "2026-02-15",
    "vendedor_nit": "900123456",
    "vendedor_nombre": "Proveedor S.A.S.",
    "subtotal": "1000000.00",
    "retefuente_porcentaje": "0.04",
    "reteica_porcentaje": "0.00966",
    "periodo": "2026-02",
    "categoria_contable": "SERVICIOS_PROFESIONALES",
    "centro_costo": "ADMINISTRATIVOS"
}
```

### ResolucionDIANViewSet

**Endpoints**:
- `GET /api/v1/resoluciones-dian/` - Lista
- `POST /api/v1/resoluciones-dian/` - Crear
- `GET /api/v1/resoluciones-dian/{id}/` - Detalle
- `DELETE /api/v1/resoluciones-dian/{id}/` - Eliminar (solo si no tiene documentos)
- `POST /api/v1/resoluciones-dian/{id}/desactivar/` - Desactivar
- `GET /api/v1/resoluciones-dian/activa/` - Obtener resolución vigente

**Características**:
- **Bloquea PUT/PATCH**: Las resoluciones son inmutables
- **Validación de eliminación**: No permite eliminar si tiene Documentos de Soporte asociados
- **Desactivación automática**: Si se crea una nueva como vigente, desactiva las anteriores

### Serializers

#### GastoListSerializer

**Campos aplanados** (prefijo `ds_`):
- `ds_consecutivo`, `ds_prefijo`, `ds_numero_documento`
- `ds_vendedor`, `ds_fecha`, `ds_total`
- `ds_activo`: Estado activo del documento (⚠️ v2.40)
- `ds_anulado`: Estado anulado del documento

**Uso**: Optimizado para Tabulator (tabla de listado)

#### GastoDetailSerializer

**Incluye**:
- `documento_soporte`: Serialización completa del DocumentoSoporte
- `retefuente_porcentaje`, `reteica_porcentaje`: Porcentajes aplicados
- Todos los campos del Gasto

**Uso**: Vista detallada del gasto

---

## Frontend (Templates y JavaScript)

### Template Principal

**Ubicación**: `apps/tenant/core/templates/tenant/core/partials/gastos/list.html`

#### Panel de Resumen

Muestra 4 tarjetas:
1. **Gasto Total Neto** (azul): Total neto a pagar
2. **Retefuente** (rojo): Total de retención en la fuente
3. **ReteICA** (amarillo): Total de retención ICA
4. **Documento Soporte Inmutable** (gris): Información del sistema

#### Tabla de Gastos

- Usa `TabulatorFactory` para tabla interactiva
- Búsqueda en tiempo real
- Paginación server-side
- Muestra documentos anulados con estilo diferente (tachado + badge)

### Modal de Creación

**Ubicación**: `apps/tenant/core/templates/tenant/core/partials/gastos/modals.html`

#### Características

1. **Selectores de Porcentajes**:
   - Retefuente: Dropdown con opciones (0%, 4%, 6%, 10%, 11%)
   - ReteICA: Dropdown con opciones (0%, 0.69%, 0.966%, 1.104%)

2. **Cálculo en Tiempo Real**:
   - Al cambiar subtotal o porcentajes, se calculan automáticamente las retenciones
   - Muestra valores calculados debajo de cada selector
   - Muestra Total Neto calculado automáticamente

3. **Resolución DIAN Automática**:
   - Campo readonly que muestra la resolución vigente
   - Se obtiene automáticamente al abrir el modal

### JavaScript

#### gastos.page.js

**Funcionalidades**:
- Inicialización lazy con `DOMUtils.onVisibleOnce`
- Renderizado de summary financiero
- Configuración de eventos
- Integración con TabulatorFactory

**Funciones principales**:
- `renderSummary()`: Actualiza panel de resumen
- `getColumns()`: Define columnas de la tabla
- `initTable()`: Inicializa Tabulator con event delegation para botones
- `confirmarDesactivar()`: Confirma y ejecuta desactivación (⚠️ v2.40)
- `confirmarAnulacion()`: Confirma y ejecuta anulación

**Event Delegation** (⚠️ v2.40):
- Los botones de acciones usan atributos `data-action` y `data-id`
- Event listener en el contenedor de la tabla (no en cada botón)
- Funciona con contenido dinámico de Tabulator
- Acciones: `ver`, `desactivar`, `anular`

#### gastos.modals.js

**Funcionalidades**:
- `showCreate()`: Abre modal y carga resolución vigente
- `save()`: Guarda gasto (solo envía porcentajes, backend calcula valores)
- `showDetail()`: Muestra detalle del documento
- `calcularRetenciones()`: Calcula retenciones en tiempo real

**Cálculo en Tiempo Real**:
```javascript
function calcularRetenciones() {
    const subtotal = parseFloat(subtotalInput.value) || 0;
    const retefuentePorcentaje = parseFloat(retefuenteSelect.value) || 0;
    const reteicaPorcentaje = parseFloat(reteicaSelect.value) || 0;
    
    const retefuente = subtotal * retefuentePorcentaje;
    const reteica = subtotal * reteicaPorcentaje;
    const totalNeto = subtotal - retefuente - reteica;
    
    // Actualiza displays
}
```

---

## Funcionalidades Implementadas

### ✅ Gestión de Documentos Soporte

1. **Creación**:
   - Validación de resolución vigente
   - Cálculo automático de consecutivo
   - Cálculo automático de retenciones
   - Validación de rangos

2. **Listado**:
   - Muestra todos los documentos (anulados y no anulados)
   - Consecutivos siempre visibles
   - Búsqueda en tiempo real
   - Paginación server-side

3. **Desactivación** (⚠️ v2.40):
   - Marca documento como `activo=False`
   - Paso previo obligatorio antes de anular
   - Excluye del summary financiero
   - Botón "Anular" solo aparece si está desactivado

4. **Anulación**:
   - Solo permite anular si está desactivado (`activo=False`)
   - Marca documento como anulado
   - Conserva valores originales (inmutabilidad)
   - Excluye del summary financiero
   - Mantiene consecutivo visible en lista

### ✅ Gestión de Resoluciones DIAN

1. **Creación**:
   - Validación de rangos y fechas
   - Desactivación automática de anteriores si se marca como vigente
   - Validación de unicidad (solo una vigente por empresa)

2. **Desactivación**:
   - Solo desactiva, no elimina
   - Los documentos conservan su referencia (snapshot inmutable)

3. **Eliminación**:
   - Solo permite eliminar si no tiene Documentos de Soporte asociados
   - Validación estricta para mantener integridad legal

### ✅ Cálculo de Retenciones

1. **Automático**:
   - Se calcula en el modelo (`clean()`)
   - Se calcula en el service layer (`calcular_retenciones()`)
   - Se calcula en el frontend (tiempo real)

2. **Porcentajes Configurables**:
   - Retefuente: 0%, 4%, 6%, 10%, 11%
   - ReteICA: 0%, 0.69%, 0.966%, 1.104%

3. **Validaciones**:
   - Subtotal no negativo
   - Total no negativo (retenciones no exceden subtotal)
   - Redondeo a 2 decimales

### ✅ Panel de Resumen Financiero

1. **Valores Independientes**:
   - Retefuente total (independiente)
   - ReteICA total (independiente)
   - Total Neto
   - Cantidad de documentos

2. **Exclusión de Anulados**:
   - Solo suma documentos no anulados
   - Mantiene integridad contable

---

## Flujos de Trabajo

### Flujo 1: Crear Documento Soporte

```
1. Usuario hace clic en "Nuevo Gasto"
   ↓
2. Sistema valida resolución vigente
   - Si no existe → Abre modal de configuración
   - Si existe → Continúa
   ↓
3. Usuario completa formulario:
   - Ingresa subtotal
   - Selecciona porcentaje Retefuente
   - Selecciona porcentaje ReteICA
   - Sistema calcula valores en tiempo real
   ↓
4. Usuario hace clic en "Guardar"
   ↓
5. Backend:
   - Obtiene resolución vigente
   - Calcula siguiente consecutivo
   - Calcula retenciones (calcular_retenciones)
   - Crea DocumentoSoporte
   - Crea Gasto
   ↓
6. Frontend:
   - Cierra modal
   - Actualiza tabla
   - Actualiza summary
```

### Flujo 2: Desactivar y Anular Documento (⚠️ v2.40)

```
1. Usuario hace clic en "Desactivar" (si está activo)
   ↓
2. Sistema muestra confirmación
   ↓
3. Usuario confirma
   ↓
4. Backend:
   - Marca documento como activo=False
   - Usa update() directamente (sin validaciones)
   ↓
5. Frontend:
   - Actualiza tabla (muestra como INACTIVO)
   - Botón "Anular" ahora está habilitado
   ↓
6. Usuario hace clic en "Anular"
   ↓
7. Sistema valida que esté desactivado
   - Si está activo → Error: "Debe desactivarlo primero"
   - Si está desactivado → Continúa
   ↓
8. Backend:
   - Marca documento como anulado
   - Registra fecha de anulación
   - NO elimina el registro (inmutabilidad)
   ↓
9. Frontend:
   - Actualiza tabla (muestra como ANULADO)
   - Actualiza summary (excluye del total)
   - Consecutivo sigue visible
```

### Flujo 3: Configurar Resolución DIAN

```
1. Usuario hace clic en "Configurar Resolución"
   ↓
2. Sistema abre modal de configuración
   ↓
3. Usuario completa datos:
   - Número de resolución
   - Prefijo
   - Rango de consecutivos
   - Fechas de vigencia
   ↓
4. Usuario marca como "Vigente"
   ↓
5. Backend:
   - Si es vigente → Desactiva anteriores
   - Valida rangos y fechas
   - Crea resolución
   ↓
6. Frontend:
   - Cierra modal
   - Muestra confirmación
```

---

## Validaciones y Reglas de Negocio

### Reglas de Inmutabilidad

1. **Consecutivo**: Una vez asignado, NO puede modificarse
2. **Valores Monetarios**: Una vez generado el consecutivo, NO pueden modificarse
3. **Resolución**: Una vez asociada, NO puede cambiarse (snapshot histórico)

### Reglas de Consecutividad

1. **Único por Resolución**: No puede haber dos documentos con el mismo consecutivo en la misma resolución
2. **Incluye Anulados**: Los documentos anulados se cuentan para calcular el siguiente consecutivo
3. **Rango Validado**: El consecutivo debe estar dentro del rango de la resolución

### Reglas de Retenciones

1. **Cálculo Automático**: Siempre se calcula desde porcentajes, nunca se ingresa manualmente
2. **Fórmula**: `total = subtotal - retefuente - reteica`
3. **Validación**: Total no puede ser negativo

### Reglas de Resoluciones

1. **Una Vigente**: Solo una resolución puede estar vigente por empresa
2. **No Eliminar con Documentos**: No se puede eliminar si tiene Documentos de Soporte asociados
3. **Rangos Válidos**: `rango_hasta > rango_desde`, `fecha_fin > fecha_inicio`

### Reglas de Summary

1. **Excluye Anulados y Desactivados**: Solo suma documentos con `anulado=False AND activo=True`
2. **Valores Independientes**: Retefuente e ICA se muestran por separado
3. **Actualización Automática**: Se actualiza al crear/desactivar/anular documentos

### Reglas de Desactivación y Anulación (⚠️ v2.40)

1. **Desactivación Obligatoria**: No se puede anular un documento activo
2. **Orden de Operaciones**: 
   - Primero: Desactivar (`activo=False`)
   - Segundo: Anular (`anulado=True`)
3. **Validación Estricta**: Backend valida que `activo=False` antes de permitir anulación
4. **Sin Validaciones en Desactivación**: Usa `update()` directamente para evitar validaciones de total
5. **Exclusión del Summary**: Documentos desactivados o anulados se excluyen automáticamente

---

## Ejemplos de Uso

### Ejemplo 1: Crear Documento con Retenciones

```python
# Backend (ViewSet)
data = {
    "fecha": "2026-02-15",
    "vendedor_nit": "900123456",
    "vendedor_nombre": "Proveedor S.A.S.",
    "subtotal": "1000000.00",
    "retefuente_porcentaje": "0.04",  # 4%
    "reteica_porcentaje": "0.00966",  # 0.966%
    "periodo": "2026-02",
    "categoria_contable": "SERVICIOS_PROFESIONALES"
}

# El backend calcula automáticamente:
# retefuente = 1000000 * 0.04 = 40000
# reteica = 1000000 * 0.00966 = 9660
# total = 1000000 - 40000 - 9660 = 950340
```

### Ejemplo 2: Obtener Summary

```python
# Service Layer
summary = get_gastos_summary(empresa_id=1)

# Retorna:
{
    "subtotal_neto": Decimal('5000000.00'),
    "retefuente_neto": Decimal('200000.00'),
    "reteica_neto": Decimal('48300.00'),
    "retenciones_neto": Decimal('248300.00'),
    "total_neto": Decimal('4751700.00'),
    "cantidad": 5
}
```

### Ejemplo 3: Usar Propiedades COP

```python
# En templates o serializers
documento = DocumentoSoporte.objects.get(id=1)

# Formato automático en COP
documento.subtotal_cop  # "$1.000.000"
documento.retefuente_cop  # "$40.000"
documento.reteica_cop  # "$9.660"
documento.total_cop  # "$950.340"
```

---

## Migraciones Requeridas

### Migración 1: Agregar Campos de Porcentajes

```python
# Agregar campos:
# - retefuente_porcentaje (CharField con choices)
# - reteica_porcentaje (CharField con choices)
```

### Migración 2: Índices y Constraints

```python
# Ya implementados en el modelo:
# - unique_ds_resolucion_consecutivo
# - unique_ds_vendedor_factura
# - Índices para optimización
```

---

## Notas Técnicas

### Precisión Decimal

- Todos los valores monetarios usan `DecimalField` con `decimal_places=2`
- Cálculos usan `quantize(Decimal('0.01'))` para redondeo a 2 decimales
- Formato COP usa `:,.0f` (sin decimales) para presentación

### Multi-Tenant

- Todos los modelos tienen FK a `Empresa` (SSoT)
- Filtrado automático por tenant mediante `django-tenants`
- Aislamiento completo por esquema

### Performance

- QuerySets optimizados con `select_related()` y `only()`
- Paginación server-side para tablas grandes
- Índices en campos frecuentemente consultados

---

## Estado de Implementación

### ✅ Completado

- [x] Modelos (DocumentoSoporte, Gasto, ResolucionDIAN)
- [x] Campo `activo` en DocumentoSoporte (⚠️ v2.40)
- [x] Service Layer (cálculo de retenciones, gestión de consecutivos)
- [x] Funciones de desactivación y anulación (⚠️ v2.40)
- [x] ViewSets (CRUD completo, acciones personalizadas)
- [x] Endpoint de desactivación (`POST /api/v1/gastos/{id}/desactivar/`) (⚠️ v2.40)
- [x] Serializers (list, detail, nested) con campo `ds_activo`
- [x] Templates (list, modals)
- [x] JavaScript (cálculo en tiempo real, integración Tabulator)
- [x] Event delegation para botones de acciones (⚠️ v2.40)
- [x] Panel de resumen (Retefuente e ICA independientes)
- [x] Summary excluye documentos desactivados y anulados (⚠️ v2.40)
- [x] Validaciones y reglas de negocio
- [x] Propiedades de formato COP

### 🔄 Pendiente (Opcional)

- [ ] Exportación a Excel/PDF
- [ ] Historial de cambios
- [ ] Notificaciones por email
- [ ] Integración con contabilidad

---

## Referencias

- **Normativa DIAN**: Art. 1.6.1.4.12 DR 1625 de 2016
- **Arquitectura**: SINTEL v2.40 - Service Layer Pattern
- **Frontend**: TabulatorFactory, DOMUtils, Vanilla JS
- **Backend**: Django REST Framework, django-tenants

---

---

## Cambios Recientes (v2.40 - Actualización)

### Campo `activo` en DocumentoSoporte

**Fecha**: 2026-02-15

**Descripción**: Se agregó el campo `activo` (BooleanField) al modelo `DocumentoSoporte` para implementar un flujo de desactivación antes de anulación, similar a otros módulos del sistema (Clientes, Proveedores, Inventario).

**Cambios Implementados**:

1. **Modelo**:
   - Campo `activo = BooleanField(default=True, db_index=True)`
   - Índice agregado para optimización de consultas
   - Help text: "Debe estar desactivado para poder anular"

2. **Service Layer**:
   - Nueva función `desactivar_gasto_service()`: Marca documento como `activo=False`
   - Actualizada `anular_gasto_service()`: Valida que `activo=False` antes de anular
   - Actualizada `get_gastos_summary()`: Excluye documentos desactivados (`activo=True AND anulado=False`)

3. **API REST**:
   - Nuevo endpoint: `POST /api/v1/gastos/{id}/desactivar/`
   - Endpoint `anular` ahora valida estado activo antes de proceder

4. **Frontend**:
   - Columna "Estado" muestra: ACTIVO (verde), INACTIVO (amarillo), ANULADO (rojo)
   - Botones de acciones:
     - Si está ACTIVO: Botón "Desactivar" habilitado, "Anular" deshabilitado
     - Si está INACTIVO: Botón "Anular" habilitado
     - Si está ANULADO: Sin botones de acción
   - Event delegation implementado para botones (usa `data-action` y `data-id`)

5. **Validaciones**:
   - No se puede anular si está activo
   - Mensaje de error claro: "No se puede anular un documento activo. Debe desactivarlo primero."
   - Summary excluye automáticamente documentos desactivados

**Flujo de Trabajo**:
```
Documento Creado → ACTIVO
    ↓ (Usuario desactiva)
INACTIVO
    ↓ (Usuario anula)
ANULADO
```

**Beneficios**:
- Protección contra anulación accidental
- Flujo consistente con otros módulos del sistema
- Mejor control de estados del documento
- Summary financiero más preciso (solo documentos activos)

---

**Última actualización**: 2026-02-15  
**Versión**: 2.40  
**Estado**: ✅ Implementado y Funcional
