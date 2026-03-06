# Auditoría Completa: Módulo de Empleados v2.60

**Fecha de Auditoría:** 2026-03-XX  
**Versión de Arquitectura:** SINTEL v2.60 (Standalone Architecture)  
**Módulo:** `apps/tenant/empleados`  
**Ubicación de Templates:** `apps/tenant/core/templates/tenant/core/partials/empleados/`

---

## 📋 Índice

1. [Arquitectura General](#1-arquitectura-general)
2. [Modelos y Estructura de Datos](#2-modelos-y-estructura-de-datos)
3. [Capa de Servicios (Service Layer)](#3-capa-de-servicios-service-layer)
4. [API y ViewSets (Backend)](#4-api-y-viewsets-backend)
5. [Frontend: JavaScript y Templates](#5-frontend-javascript-y-templates)
6. [Flujos CRUD Completos](#6-flujos-crud-completos)
7. [Flujo de Nóminas (Multitanda)](#7-flujo-de-nóminas-multitanda)
8. [Historial de Nóminas](#8-historial-de-nóminas)
9. [Integración HTMX y Offcanvas](#9-integración-htmx-y-offcanvas)
10. [Validaciones y Zero Trust](#10-validaciones-y-zero-trust)
11. [Manejo de Errores](#11-manejo-de-errores)
12. [Checklist de Validación](#12-checklist-de-validación)

---

## 1. Arquitectura General

### 1.1 Principios Arquitectónicos (v2.60)

- **API-First**: Todas las funcionalidades expuestas vía REST API (DRF)
- **Single Source of Truth (SSoT)**: `empresa = ForeignKey(Empresa, on_delete=PROTECT)` en todos los modelos
- **Zero Trust**: Validación estricta de pertenencia al tenant en cada operación
- **Service Layer Pattern**: Lógica de negocio centralizada en `services.py`
- **Anemic Models**: Modelos solo definen estructura de datos, sin lógica de negocio
- **Feature-Sliced Frontend**: JavaScript modular por funcionalidad
- **HTMX + Offcanvas**: Interfaz dinámica sin recargas de página
- **Tabulator Factory**: Tablas interactivas con paginación remota

### 1.2 Flujo Secuencial (Máquina de Estados)

```
1. Empleado (creación inicial)
   ↓
2. Contrato (requiere Empleado, habilita botón "Registrar Nómina")
   ↓
3. Devengo/Nómina (requiere Contrato ACTIVO, habilita botón "Historial")
```

### 1.3 Estructura de Archivos

```
apps/tenant/empleados/
├── models.py              # Modelos: Empleado, Contrato, Devengo
├── services.py            # Lógica de negocio y querysets optimizados
├── choices.py             # Constantes y choices para campos
├── api/
│   ├── serializers.py     # Serializers con NormalizationMixin
│   └── viewsets.py        # ViewSets con acciones HTMX
└── migrations/            # Migraciones de base de datos

apps/tenant/core/templates/tenant/core/partials/empleados/
├── list.html              # Vista principal con Tabulator
├── empleado_offcanvas.html      # Formulario CRUD Empleado
├── contrato_offcanvas.html      # Formulario CRUD Contrato
├── devengo_offcanvas.html       # Formulario CRUD Nómina
├── historial_nominas_offcanvas.html  # Historial de nóminas
├── devengo_calculo_partial.html      # Partial HTMX para preview
├── devengo_calculo_error.html        # Partial HTMX para errores
├── assets_empleados.html              # Carga de scripts JS
└── modals.html                        # ⚠️ DEPRECATED (v2.60: Offcanvas)

apps/tenant/core/static/core/js/empleados/
├── empleados.api.js       # Capa de datos (window.http)
├── empleados.page.js      # Lógica de negocio y UI
└── empleados.modals.js    # ⚠️ DEPRECATED (v2.60: HTMX)
```

---

## 2. Modelos y Estructura de Datos

### 2.1 Modelo: Empleado

**Ubicación:** `apps/tenant/empleados/models.py`

**Campos Principales:**
- `empresa` (FK, PROTECT, índice) - SSoT
- `tipo_documento`, `numero_documento` (único por tenant)
- `primer_nombre`, `segundo_nombre`, `primer_apellido`, `segundo_apellido`
- `email`, `telefono`
- `eps`, `afp`, `arl`, `nivel_riesgo_arl` (seguridad social)
- `estado` (ACTIVO, RETIRADO)
- `fecha_ingreso`, `fecha_retiro`

**Constraints:**
```python
UniqueConstraint(
    fields=['empresa', 'tipo_documento', 'numero_documento'],
    name='uniq_empleado_per_tenant'
)
```

**Índices:**
- `['empresa', 'estado']`
- `['numero_documento']`

### 2.2 Modelo: Contrato

**Campos Principales:**
- `empresa` (FK, PROTECT, índice) - SSoT
- `empleado` (FK, PROTECT)
- `tipo` (FIJO, INDEFINIDO, PRESTACION_SERVICIOS)
- `fecha_inicio`, `fecha_fin`
- `salario_mensual`, `auxilio_transporte`
- `prestamos_empresa` (Decimal, para reversión de préstamos)
- `cargo`, `archivo_pdf`
- `estado` (ACTIVO, INACTIVO)
- `activo` (Boolean, para máquina de estados)

**Constraints:**
```python
UniqueConstraint(
    fields=['empleado', 'activo'],
    condition=Q(activo=True),
    name='uniq_contrato_activo_per_empleado'
)
```

**Validaciones:**
- Solo UN contrato ACTIVO por empleado (garantizado por constraint)
- `fecha_fin` debe ser >= `fecha_inicio` (validación en `clean()`)

### 2.3 Modelo: Devengo (Nómina)

**Campos Principales:**
- `empresa` (FK, PROTECT, índice) - SSoT
- `empleado` (FK, PROTECT)
- `contrato` (FK, PROTECT)
- `periodo_mes` (CharField, formato: YYYY-MM)
- `fecha_pago` (DateField) - ⚠️ **Nómina Multitanda**: Parte de la clave de unicidad
- `dias_laborados` (Decimal)
- `salario_base`, `auxilio_transporte` (readonly, calculados)
- `otros_devengos`, `prestamos`, `descuentos_operativos`
- `salud_empleado`, `pension_empleado` (readonly, calculados)
- `neto_pagar` (readonly, calculado en backend - Zero Trust)
- `anulado` (Boolean)
- `observaciones`

**Constraints (Nómina Multitanda):**
```python
UniqueConstraint(
    fields=['empleado', 'periodo_mes', 'fecha_pago'],
    condition=Q(anulado=False),
    name='uniq_nomina_per_empleado_periodo_fecha'
)
```

**Validaciones:**
- Permite múltiples nóminas en el mismo mes si `fecha_pago` es diferente
- La suma de `dias_laborados` en el mes no puede exceder 31 días (validación en `services.py`)

---

## 3. Capa de Servicios (Service Layer)

### 3.1 Querysets Optimizados

**Ubicación:** `apps/tenant/empleados/services.py`

**Constantes de Campos (SSoT):**
```python
EMPLEADO_LIST_FIELDS = (
    'id', 'tipo_documento', 'numero_documento', 'primer_nombre', 
    'primer_apellido', 'estado', 'fecha_ingreso', 'empresa_id'
)

CONTRATO_LIST_FIELDS = (
    'id', 'empleado', 'empleado__id', 'empleado__primer_nombre',
    'tipo', 'fecha_inicio', 'salario_mensual', 'estado', 'activo'
)

DEVENGO_LIST_FIELDS = (
    'id', 'empleado', 'empleado__id', 'periodo_mes', 'fecha_pago',
    'dias_laborados', 'neto_pagar', 'anulado'
)
```

**Funciones Principales:**

1. **`qs_empleado_list(empresa_id, search=None)`**
   - Retorna queryset optimizado con `.only(*EMPLEADO_LIST_FIELDS)`
   - Soporta búsqueda por `numero_documento`, `primer_nombre`, `primer_apellido`
   - Anotaciones: `tiene_contrato_activo`, `tiene_nominas_registradas`

2. **`qs_empleado_detail(empresa_id, empleado_id)`**
   - Retorna objeto con `.only(*EMPLEADO_DETAIL_FIELDS)`
   - Usa `select_related('empresa')` para evitar N+1

3. **`qs_contrato_list(empresa_id, empleado_id=None)`**
   - Filtra por `empresa_id` y opcionalmente por `empleado_id`
   - Usa `select_related('empleado')`

4. **`qs_devengo_list(empresa_id, empleado_id=None)`**
   - Filtra por `empresa_id` y opcionalmente por `empleado_id`
   - Usa `select_related('empleado', 'contrato')`

5. **`qs_historial_list(empleado_id, empresa_id)`**
   - Lista de nóminas para un empleado específico
   - Filtra por `empresa_id` y `empleado_id` (Zero Trust)

### 3.2 Cálculos de Nómina (Zero Trust)

**Función Principal:** `calcular_nomina_colombia()`

**Parámetros:**
- `empleado_id`, `contrato_id`, `periodo_mes`, `fecha_pago`
- `dias_laborados`, `otros_devengos`, `prestamos`, `descuentos_operativos`
- `empresa_id` (para validación Zero Trust)

**Cálculos Realizados:**

1. **Salario Proporcional:**
   ```python
   salario_proporcional = (salario_base / 30) * dias_laborados
   ```

2. **Auxilio de Transporte Proporcional:**
   ```python
   auxilio_proporcional = (auxilio_transporte / 30) * dias_laborados
   ```

3. **IBC (Ingreso Base de Cotización):**
   ```python
   ibc = salario_proporcional + otros_devengos
   # ⚠️ NO incluye auxilio_transporte (Ley Colombiana)
   ```

4. **Deducciones de Ley:**
   ```python
   salud_empleado = ibc * Decimal('0.04')  # 4%
   pension_empleado = ibc * Decimal('0.04')  # 4%
   ```

5. **Neto a Pagar:**
   ```python
   neto_pagar = (salario_proporcional + auxilio_proporcional + otros_devengos) - \
                (salud_empleado + pension_empleado + prestamos + descuentos_operativos)
   ```

**Validaciones:**
- `dias_laborados` debe ser > 0 y <= 31
- `prestamos` no puede exceder el saldo pendiente en el contrato
- `empresa_id` y `empleado_id` deben coincidir (Zero Trust)

### 3.3 Validación de Solapamiento (Nómina Multitanda)

**Función:** `validar_limite_dias_mes()`

**Lógica:**
```python
def validar_limite_dias_mes(empleado_id, periodo_mes, nuevos_dias, empresa_id, devengo_id_excluir=None):
    """
    Zero Trust: Valida que la suma de todos los pagos del mes no exceda 31 días.
    """
    total_dias_existentes = Devengo.objects.filter(
        empleado_id=empleado_id,
        periodo_mes=periodo_mes,
        empresa_id=empresa_id,
        anulado=False
    ).exclude(pk=devengo_id_excluir).aggregate(total=Sum('dias_laborados'))['total'] or Decimal('0')
    
    total_final = total_dias_existentes + Decimal(str(nuevos_dias))
    
    if total_final > Decimal('31'):
        raise ValidationError({
            'dias_laborados': f'La suma de días laborados excede los 31 días del mes.',
            'code': 'dias_excedidos',
            'dias_registrados': str(total_dias_existentes),
            'total': str(total_final)
        })
```

---

## 4. API y ViewSets (Backend)

### 4.1 EmpleadoViewSet

**Ubicación:** `apps/tenant/empleados/api/viewsets.py`

**Endpoints Principales:**

1. **`GET /api/v1/empleados/`** - Listado paginado
   - Usa `qs_empleado_list()` del service layer
   - Retorna formato DRF: `{count, results}`
   - Soporta `?search=` para filtrado

2. **`GET /api/v1/empleados/{id}/`** - Detalle
   - Usa `qs_empleado_detail()` del service layer
   - Zero Trust: Valida pertenencia al tenant

3. **`POST /api/v1/empleados/`** - Crear
   - Serializer: `EmpleadoDetailSerializer` (NormalizationMixin)
   - Asigna `empresa` automáticamente desde tenant context

4. **`PATCH /api/v1/empleados/{id}/`** - Actualizar
   - Valida Zero Trust antes de actualizar

5. **`DELETE /api/v1/empleados/{id}/`** - Eliminar
   - Solo si `estado == 'RETIRADO'` (Hard Delete)
   - Usa `eliminar_empleado_retirado()` del service layer

6. **`GET /api/v1/empleados/gestor-offcanvas/?tipo=empleado&id={id}`** - HTMX Offcanvas
   - Retorna `TemplateResponse` con `empleado_offcanvas.html`
   - Si `id` está presente, carga datos del empleado

7. **`GET /api/v1/empleados/{id}/historial-nominas/`** - Historial de Nóminas
   - Retorna `TemplateResponse` con `historial_nominas_offcanvas.html`
   - Filtra por `empresa_id` y `empleado_id` (Zero Trust)

8. **`GET /api/v1/empleados/summary/`** - Resumen de Nómina
   - Retorna estadísticas: total nómina mes, empleados activos, etc.

### 4.2 ContratoViewSet

**Endpoints Principales:**

1. **`GET /api/v1/empleados/contratos/`** - Listado
   - Filtra por `empresa_id`
   - Soporta `?empleado={id}` para filtrar por empleado

2. **`GET /api/v1/empleados/gestor-offcanvas/?tipo=contrato&empleado={id}`** - HTMX Offcanvas
   - Retorna `contrato_offcanvas.html`
   - Si `empleado` está presente, pre-carga datos del empleado

3. **`POST /api/v1/empleados/contratos/`** - Crear
   - Valida que solo haya UN contrato ACTIVO por empleado
   - Usa `gestionar_contrato_service()` del service layer

4. **`PATCH /api/v1/empleados/contratos/{id}/`** - Actualizar
   - Valida Zero Trust

5. **`POST /api/v1/empleados/contratos/{id}/cancelar/`** - Cancelar Contrato
   - Cambia `estado` a INACTIVO y `activo` a False
   - Máquina de Estados: Deshabilita creación de nuevas nóminas

### 4.3 DevengoViewSet

**Endpoints Principales:**

1. **`GET /api/v1/empleados/devengos/`** - Listado
   - Filtra por `empresa_id`
   - Soporta `?empleado={id}` para filtrar por empleado
   - Retorna formato DRF: `{count, results}`

2. **`GET /api/v1/empleados/gestor-offcanvas/?tipo=devengo&id={id}`** - HTMX Offcanvas
   - Retorna `devengo_offcanvas.html`
   - Si `id` está presente, carga datos del devengo
   - Si `empleado` está presente, pre-carga datos del empleado y contrato

3. **`POST /api/v1/empleados/devengos/`** - Crear Nómina
   - **Validación Preventiva de Duplicados:**
     ```python
     # Verifica si ya existe nómina para empleado + periodo_mes + fecha_pago
     devengo_existente = Devengo.objects.filter(
         empleado_id=empleado_id,
         periodo_mes=periodo_mes,
         fecha_pago=fecha_pago_obj,
         anulado=False,
         empresa_id=empresa.id
     ).first()
     
     if devengo_existente:
         return Response({
             "error": "Ya existe una nómina para este empleado, periodo y fecha de pago.",
             "code": "duplicate_nomina",
             "devengo_existente_id": devengo_existente.id
         }, status=status.HTTP_409_CONFLICT)
     ```
   
   - **Validación de Solapamiento de Días:**
     ```python
     # Valida que la suma de días no exceda 31
     validacion_dias = validar_limite_dias_mes(
         empleado_id=empleado_id,
         periodo_mes=periodo_mes,
         nuevos_dias=dias_laborados,
         empresa_id=empresa.id
     )
     
     if validacion_dias['excede_limite']:
         return Response({
             "error": "La suma de días laborados excede los 31 días del mes.",
             "code": "dias_excedidos",
             "dias_registrados": str(validacion_dias['total_dias']),
             "total": str(validacion_dias['total_final'])
         }, status=status.HTTP_400_BAD_REQUEST)
     ```
   
   - **Cálculo Inmutable:**
     ```python
     # Recalcula todos los valores usando la Capa de Servicio (Zero Trust)
     resultado_calculo = calcular_nomina_colombia(
         empleado_id=empleado_id,
         contrato_id=contrato_id,
         periodo_mes=periodo_mes,
         fecha_pago=fecha_pago_obj,
         dias_laborados=Decimal(str(dias_laborados)),
         otros_devengos=Decimal(str(otros_devengos or 0)),
         prestamos=Decimal(str(prestamos or 0)),
         descuentos_operativos=Decimal(str(descuentos_operativos or 0)),
         empresa_id=empresa.id
     )
     ```

4. **`POST /api/v1/empleados/devengos/preview-calculo/`** - Preview en Tiempo Real
   - Endpoint HTMX para previsualizar cálculos sin guardar
   - Retorna `devengo_calculo_partial.html` con valores actualizados
   - Usa `calcular_nomina_colombia()` como única fuente de verdad
   - Maneja errores con `devengo_calculo_error.html`

5. **`DELETE /api/v1/empleados/devengos/{id}/`** - Eliminar Nómina
   - **Reversión de Préstamos:**
     ```python
     if instance.prestamos and instance.prestamos > 0:
         contrato = instance.contrato
         if contrato:
             contrato.refresh_from_db()
             prestamo_actual = Decimal(str(contrato.prestamos_empresa or 0))
             nuevo_prestamo = prestamo_actual + Decimal(str(instance.prestamos))
             contrato.prestamos_empresa = nuevo_prestamo
             contrato.save(update_fields=['prestamos_empresa'])
     ```
   - Elimina la nómina de la base de datos (Hard Delete)
   - Registra en log de auditoría

---

## 5. Frontend: JavaScript y Templates

### 5.1 Estructura de JavaScript

**Archivo Principal:** `apps/tenant/core/static/core/js/empleados/empleados.page.js`

**Dependencias Globales:**
- `TabulatorFactory` (tabulator.factory.js)
- `DOMUtils.onVisibleOnce()` (lazy loading)
- `window.http()` (http.js - Capa de Datos)
- `window.UIManager` (ui-manager.js - Error Boundary)
- `htmx` (para cargar offcanvas)

**Namespace:**
```javascript
window.EmpleadosModule = {
  inicializarModulo: initEmpleadosTable,
  openEmpleadoOffcanvas: openEmpleadoOffcanvas,
  openContratoOffcanvas: openContratoOffcanvas,
  openDevengoOffcanvas: openDevengoOffcanvas,
  openHistorialNominas: openHistorialNominas,
  refreshTable: function() { if (table) table.replaceData(); }
};
```

### 5.2 Inicialización de Tabla (Tabulator Factory)

**Función:** `initEmpleadosTable()`

**Configuración:**
```javascript
const columns = [
  { title: "Documento", field: "numero_documento", width: 150 },
  { title: "Nombre Completo", field: "primer_nombre", formatter: nombreCompletoFormatter },
  { title: "Estado", field: "estado", formatter: estadoFormatter },
  { title: "Fecha Ingreso", field: "fecha_ingreso", formatter: "datetime", formatterParams: { inputFormat: "YYYY-MM-DD", outputFormat: "DD/MM/YYYY" } },
  {
    title: "Acciones",
    hozAlign: "center",
    width: 300,
    headerSort: false,
    formatter: function(cell) {
      const data = cell.getRow().getData();
      const id = data.id;
      return `
        <div class="btn-group btn-group-sm">
          <button type="button" class="btn btn-outline-info btn-ver-empleado" data-id="${id}">
            <i class="bi bi-eye"></i> Ver
          </button>
          <button type="button" class="btn btn-outline-primary btn-registrar-nomina" data-id="${id}">
            <i class="bi bi-cash-coin"></i> Nómina
          </button>
          <button type="button" class="btn btn-outline-secondary btn-historial-nominas" data-id="${id}">
            <i class="bi bi-clock-history"></i> Historial
          </button>
        </div>
      `;
    }
  }
];

const tableConfig = {
  searchInputSelector: '#search-empleado',
  pagination: true,
  paginationMode: "remote",
  paginationSize: 10,
  layout: "fitColumns",
  placeholder: "No hay empleados registrados"
};

const table = window.TabulatorFactory.create('#grid-empleados', '/api/v1/empleados/', columns, tableConfig);
```

**Lazy Loading:**
```javascript
window.DOMUtils.onVisibleOnce('#tab-empleados', function() {
  initEmpleadosTable();
});
```

### 5.3 Event Delegation para Botones Dinámicos

**Problema:** Los botones generados por Tabulator no tienen event listeners directos.

**Solución:** Event delegation en el contenedor padre.

```javascript
// Event delegation para botones de acciones
document.addEventListener('click', function(e) {
  // Botón Ver Empleado
  if (e.target.closest('.btn-ver-empleado')) {
    const btn = e.target.closest('.btn-ver-empleado');
    const id = btn.getAttribute('data-id');
    window.EmpleadosModule.openEmpleadoOffcanvas(id);
  }
  
  // Botón Registrar Nómina
  if (e.target.closest('.btn-registrar-nomina')) {
    const btn = e.target.closest('.btn-registrar-nomina');
    const id = btn.getAttribute('data-id');
    window.EmpleadosModule.openDevengoOffcanvas(null, id);
  }
  
  // Botón Historial de Nóminas
  if (e.target.closest('.btn-historial-nominas')) {
    const btn = e.target.closest('.btn-historial-nominas');
    const id = btn.getAttribute('data-id');
    window.EmpleadosModule.openHistorialNominas(id);
  }
});
```

### 5.4 Funciones de Apertura de Offcanvas

**1. `openEmpleadoOffcanvas(id)`**
```javascript
async function openEmpleadoOffcanvas(id) {
  const url = id 
    ? `/api/v1/empleados/gestor-offcanvas/?tipo=empleado&id=${id}`
    : `/api/v1/empleados/gestor-offcanvas/?tipo=empleado`;
  
  await htmx.ajax('GET', url, {
    target: '#offcanvas-container-empleado',
    swap: 'innerHTML',
    headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '' }
  });
  
  const offcanvasEl = document.getElementById('offcanvas-empleado');
  if (offcanvasEl) {
    const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
    offcanvas.show();
  }
}
```

**2. `openContratoOffcanvas(empleadoId, contratoId)`**
```javascript
async function openContratoOffcanvas(empleadoId, contratoId = null) {
  let url;
  if (contratoId) {
    url = `/api/v1/empleados/gestor-offcanvas/?tipo=contrato&id=${contratoId}`;
  } else if (empleadoId) {
    url = `/api/v1/empleados/gestor-offcanvas/?tipo=contrato&empleado=${empleadoId}`;
  }
  
  await htmx.ajax('GET', url, {
    target: '#offcanvas-container-contrato',
    swap: 'innerHTML',
    headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '' }
  });
  
  const offcanvasEl = document.getElementById('offcanvas-contrato');
  if (offcanvasEl) {
    const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
    offcanvas.show();
  }
}
```

**3. `openDevengoOffcanvas(devengoId, empleadoId)`**
```javascript
async function openDevengoOffcanvas(devengoId, empleadoId = null) {
  let url;
  if (devengoId) {
    url = `/api/v1/empleados/gestor-offcanvas/?tipo=devengo&id=${devengoId}`;
  } else if (empleadoId) {
    url = `/api/v1/empleados/gestor-offcanvas/?tipo=devengo&empleado=${empleadoId}`;
  }
  
  await htmx.ajax('GET', url, {
    target: '#offcanvas-container-devengo',
    swap: 'innerHTML',
    headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '' }
  });
  
  const offcanvasEl = document.getElementById('offcanvas-devengo');
  if (offcanvasEl) {
    const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
    offcanvas.show();
  }
}
```

**4. `openHistorialNominas(empleadoId)`**
```javascript
async function openHistorialNominas(empleadoId) {
  const url = `/api/v1/empleados/${empleadoId}/historial-nominas/`;
  
  await htmx.ajax('GET', url, {
    target: '#offcanvas-container-historial-nominas',
    swap: 'innerHTML',
    headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '' }
  });
  
  const offcanvasEl = document.getElementById('offcanvas-historial-nominas');
  if (offcanvasEl) {
    const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
    offcanvas.show();
    
    // Inicializar tabla de historial después de un delay
    setTimeout(function() {
      initHistorialNominas(empleadoId);
    }, 500);
  }
}
```

### 5.5 Inicialización de Historial de Nóminas

**Función:** `initHistorialNominas(empleadoId)`

**Configuración:**
```javascript
function initHistorialNominas(empleadoId) {
  // ⚠️ Anti-Zombies Pattern: Destruir instancia previa
  if (window.SintelEmpleadosTables && window.SintelEmpleadosTables.historialNominas) {
    try {
      window.SintelEmpleadosTables.historialNominas.destroy();
      window.SintelEmpleadosTables.historialNominas = null;
    } catch (error) {
      console.warn('Error al destruir tabla previa:', error);
    }
  }
  
  const historialUrl = `/api/v1/empleados/devengos/?empleado=${empleadoId}`;
  
  const columns = [
    { title: "Periodo", field: "periodo_mes", width: 120 },
    { title: "Fecha de Pago", field: "fecha_pago", formatter: "datetime", formatterParams: { inputFormat: "YYYY-MM-DD", outputFormat: "DD/MM/YYYY" } },
    { title: "Días Laborados", field: "dias_laborados", hozAlign: "right", formatter: "money", formatterParams: { precision: 1 } },
    { title: "Neto a Pagar", field: "neto_pagar", hozAlign: "right", formatter: "money", formatterParams: { symbol: "$", precision: 0 } },
    {
      title: "Acciones",
      hozAlign: "center",
      width: 220,
      headerSort: false,
      formatter: function(cell) {
        const data = cell.getRow().getData();
        const id = data.id;
        const anulado = data.anulado === true;
        
        let html = '<div class="btn-group btn-group-sm">';
        
        if (!anulado) {
          html += `<button type="button" class="btn btn-outline-info btn-sm btn-ver-nomina-historial" data-devengo-id="${id}">
                     <i class="bi bi-eye me-1"></i>Ver
                   </button>`;
          html += `<button type="button" class="btn btn-outline-danger btn-sm btn-eliminar-nomina-historial" 
                           data-devengo-id="${id}" data-empleado-id="${empleadoId}">
                     <i class="bi bi-trash me-1"></i>Eliminar
                   </button>`;
        } else {
          html += `<button type="button" class="btn btn-outline-secondary btn-sm" disabled>
                     <i class="bi bi-lock me-1"></i>Anulada
                   </button>`;
        }
        
        html += '</div>';
        return html;
      }
    }
  ];
  
  const tableConfig = {
    searchInputSelector: '#search-historial-nominas',
    pagination: true,
    paginationMode: "remote",
    paginationSize: 10,
    layout: "fitColumns"
  };
  
  const table = window.TabulatorFactory.create('#grid-historial-nominas', historialUrl, columns, tableConfig);
  
  if (!window.SintelEmpleadosTables) {
    window.SintelEmpleadosTables = {};
  }
  window.SintelEmpleadosTables.historialNominas = table;
  
  // ⚠️ Event delegation para botones de acciones
  const offcanvasHistorial = document.querySelector('#offcanvas-historial-nominas');
  if (offcanvasHistorial && !offcanvasHistorial.hasAttribute('data-historial-listener')) {
    offcanvasHistorial.setAttribute('data-historial-listener', 'true');
    
    offcanvasHistorial.addEventListener('click', function(e) {
      // Botón Ver/Editar
      const btnVer = e.target.closest('.btn-ver-nomina-historial');
      if (btnVer) {
        e.preventDefault();
        const devengoId = btnVer.getAttribute('data-devengo-id');
        
        htmx.ajax('GET', `/api/v1/empleados/gestor-offcanvas/?tipo=devengo&id=${devengoId}`, {
          target: '#offcanvas-container-devengo',
          swap: 'innerHTML',
          headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '' }
        }).then(function() {
          const offcanvasDevengoEl = document.getElementById('offcanvas-devengo');
          if (offcanvasDevengoEl) {
            const offcanvasDevengo = bootstrap.Offcanvas.getOrCreateInstance(offcanvasDevengoEl);
            offcanvasDevengo.show();
          }
        });
        return;
      }
      
      // Botón Eliminar
      const btnEliminar = e.target.closest('.btn-eliminar-nomina-historial');
      if (btnEliminar) {
        e.preventDefault();
        const devengoId = btnEliminar.getAttribute('data-devengo-id');
        const empleadoId = btnEliminar.getAttribute('data-empleado-id');
        
        if (!confirm('¿Está seguro de que desea eliminar esta nómina? Esta acción no se puede deshacer.')) {
          return;
        }
        
        btnEliminar.disabled = true;
        btnEliminar.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Eliminando...';
        
        window.http('DELETE', `/api/v1/empleados/devengos/${devengoId}/`)
          .then(function(response) {
            if (response.ok) {
              if (window.SintelFeedback && typeof window.SintelFeedback.success === 'function') {
                window.SintelFeedback.success('Nómina eliminada correctamente');
              }
              
              // Refrescar tabla de historial
              if (window.SintelEmpleadosTables && window.SintelEmpleadosTables.historialNominas) {
                window.SintelEmpleadosTables.historialNominas.replaceData();
              }
              
              // También refrescar tabla principal
              if (window.SintelEmpleadosTables && window.SintelEmpleadosTables.empleados) {
                window.SintelEmpleadosTables.empleados.replaceData();
              }
            } else {
              btnEliminar.disabled = false;
              btnEliminar.innerHTML = '<i class="bi bi-trash me-1"></i>Eliminar';
              
              if (window.UIManager && typeof window.UIManager.handleError === 'function') {
                window.UIManager.handleError(response, '[empleados.page]', {
                  errorContainerSelector: '#form-historial-feedback'
                });
              }
            }
          })
          .catch(function(error) {
            console.error('Error en petición DELETE:', error);
            btnEliminar.disabled = false;
            btnEliminar.innerHTML = '<i class="bi bi-trash me-1"></i>Eliminar';
            
            if (window.UIManager && typeof window.UIManager.handleError === 'function') {
              window.UIManager.handleError(
                { status: 500, data: { detail: `Error de conexión: ${error.message || error}` } },
                '[empleados.page]',
                { errorContainerSelector: '#form-historial-feedback' }
              );
            }
          });
      }
    });
  }
}
```

---

## 6. Flujos CRUD Completos

### 6.1 Flujo: Crear Empleado

**1. Usuario hace clic en "Nuevo Empleado"**
   - JavaScript: `openEmpleadoOffcanvas(null)`
   - HTMX: `GET /api/v1/empleados/gestor-offcanvas/?tipo=empleado`
   - Backend: `EmpleadoViewSet.gestor_offcanvas()` retorna `empleado_offcanvas.html` (vacío)

**2. Usuario completa formulario y hace clic en "Guardar"**
   - HTMX: `POST /api/v1/empleados/`
   - Backend: `EmpleadoViewSet.create()`
     - Serializer: `EmpleadoDetailSerializer` (NormalizationMixin)
     - Asigna `empresa` desde tenant context
     - Valida Zero Trust
   - Frontend: `htmx:afterOnLoad` cierra offcanvas y refresca tabla

### 6.2 Flujo: Crear Contrato

**1. Usuario hace clic en "Registrar Contrato" (desde tabla de empleados)**
   - JavaScript: `openContratoOffcanvas(empleadoId)`
   - HTMX: `GET /api/v1/empleados/gestor-offcanvas/?tipo=contrato&empleado={id}`
   - Backend: `EmpleadoViewSet.gestor_offcanvas()` retorna `contrato_offcanvas.html` (con datos del empleado pre-cargados)

**2. Usuario completa formulario y hace clic en "Guardar"**
   - HTMX: `POST /api/v1/empleados/contratos/`
   - Backend: `ContratoViewSet.create()`
     - Valida que solo haya UN contrato ACTIVO por empleado (constraint)
     - Usa `gestionar_contrato_service()` del service layer
   - Frontend: `htmx:afterOnLoad` cierra offcanvas y refresca tabla

### 6.3 Flujo: Crear Nómina

**1. Usuario hace clic en "Registrar Nómina" (desde tabla de empleados)**
   - JavaScript: `openDevengoOffcanvas(null, empleadoId)`
   - HTMX: `GET /api/v1/empleados/gestor-offcanvas/?tipo=devengo&empleado={id}`
   - Backend: `EmpleadoViewSet.gestor_offcanvas()` retorna `devengo_offcanvas.html` (con datos del empleado y contrato pre-cargados)

**2. Usuario ingresa `dias_laborados` o cambia `periodo_mes`/`fecha_pago`**
   - HTMX: `POST /api/v1/empleados/devengos/preview-calculo/`
   - Backend: `DevengoViewSet.preview_calculo()`
     - Usa `calcular_nomina_colombia()` del service layer
     - Retorna `devengo_calculo_partial.html` con valores actualizados
   - Frontend: HTMX reemplaza `#devengo-campos-calculados` con el partial

**3. Usuario hace clic en "Guardar Nómina"**
   - HTMX: `POST /api/v1/empleados/devengos/`
   - Backend: `DevengoViewSet.create()`
     - **Validación Preventiva de Duplicados:**
       - Verifica si ya existe nómina para `empleado + periodo_mes + fecha_pago`
       - Si existe, retorna `409 Conflict` con `devengo_existente_id`
     - **Validación de Solapamiento de Días:**
       - Usa `validar_limite_dias_mes()` para verificar que la suma no exceda 31 días
       - Si excede, retorna `400 Bad Request` con `code: 'dias_excedidos'`
     - **Cálculo Inmutable:**
       - Usa `calcular_nomina_colombia()` para recalcular todos los valores
       - Guarda en base de datos
   - Frontend: `htmx:afterOnLoad` (solo si `status === 201`) cierra offcanvas y refresca tabla

**4. Manejo de Errores:**
   - **409 Conflict (Duplicado):**
     ```javascript
     document.addEventListener('htmx:responseError', function(event) {
       if (event.detail.xhr?.status === 409) {
         const parsedResponse = JSON.parse(event.detail.xhr.responseText);
         const devengoExistenteId = parsedResponse?.devengo_existente_id;
         
         // Deshabilitar botón "Guardar"
         const btnGuardar = document.getElementById('btn-guardar-devengo');
         if (btnGuardar) {
           btnGuardar.disabled = true;
           btnGuardar.innerHTML = '<i class="bi bi-lock me-1"></i>Nómina Duplicada (Deshabilitado)';
         }
         
         // Mostrar mensaje de error
         const feedbackEl = document.querySelector('#form-devengo-feedback');
         if (feedbackEl) {
           feedbackEl.classList.remove('d-none');
           feedbackEl.classList.add('alert-danger');
           feedbackEl.innerHTML = `
             <i class="bi bi-exclamation-triangle-fill me-2"></i>
             <strong>Error de Integridad:</strong> ${parsedResponse.error}
             <br>
             <small>Use el <strong>Historial de Nóminas</strong> para anular el registro previo.</small>
             ${devengoExistenteId ? `
               <br>
               <button type="button" class="btn btn-sm btn-outline-info mt-2" 
                       onclick="window.EmpleadosModule.openDevengoOffcanvas(null, ${devengoExistenteId})">
                 <i class="bi bi-eye me-1"></i>Ver Registro Existente
               </button>
             ` : ''}
           `;
         }
         
         // Marcar campos como inválidos
         const periodoInput = document.getElementById('devengo-periodo_mes');
         const fechaPagoInput = document.getElementById('devengo-fecha_pago');
         if (periodoInput) { periodoInput.classList.add('is-invalid'); }
         if (fechaPagoInput) { fechaPagoInput.classList.add('is-invalid'); }
       }
     });
     ```
   
   - **400 Bad Request (Días Excedidos):**
     ```javascript
     if (parsedResponse && parsedResponse.code === 'dias_excedidos') {
       const feedbackEl = document.querySelector('#form-devengo-feedback');
       if (feedbackEl) {
         feedbackEl.classList.remove('d-none');
         feedbackEl.classList.add('alert-danger');
         feedbackEl.innerHTML = `
           <i class="bi bi-exclamation-triangle-fill me-2"></i>
           <strong>Días Excedidos:</strong> ${parsedResponse.detail}
           <br>
           <small>Días registrados: ${parsedResponse.dias_registrados} | Nuevos días: ${parsedResponse.dias_nuevos} | Total: ${parsedResponse.total}</small>
         `;
       }
       
       const diasInput = document.getElementById('devengo-dias_laborados');
       if (diasInput) { diasInput.classList.add('is-invalid'); }
     }
     ```

### 6.4 Flujo: Editar Empleado/Contrato/Nómina

**1. Usuario hace clic en "Ver" (desde tabla)**
   - JavaScript: `openEmpleadoOffcanvas(id)` / `openContratoOffcanvas(null, contratoId)` / `openDevengoOffcanvas(devengoId)`
   - HTMX: `GET /api/v1/empleados/gestor-offcanvas/?tipo={tipo}&id={id}`
   - Backend: `EmpleadoViewSet.gestor_offcanvas()` retorna offcanvas con datos pre-cargados

**2. Usuario modifica datos y hace clic en "Guardar"**
   - HTMX: `PATCH /api/v1/empleados/{id}/` / `PATCH /api/v1/empleados/contratos/{id}/` / `PATCH /api/v1/empleados/devengos/{id}/`
   - Backend: ViewSet actualiza registro
   - Frontend: `htmx:afterOnLoad` cierra offcanvas y refresca tabla

### 6.5 Flujo: Eliminar Nómina

**1. Usuario hace clic en "Eliminar" (desde historial de nóminas)**
   - JavaScript: Event delegation captura click en `.btn-eliminar-nomina-historial`
   - Confirmación: `confirm('¿Está seguro de que desea eliminar esta nómina?')`

**2. Usuario confirma**
   - JavaScript: `window.http('DELETE', '/api/v1/empleados/devengos/{id}/')`
   - Backend: `DevengoViewSet.destroy()`
     - **Reversión de Préstamos:**
       ```python
       if instance.prestamos and instance.prestamos > 0:
           contrato = instance.contrato
           if contrato:
               contrato.refresh_from_db()
               prestamo_actual = Decimal(str(contrato.prestamos_empresa or 0))
               nuevo_prestamo = prestamo_actual + Decimal(str(instance.prestamos))
               contrato.prestamos_empresa = nuevo_prestamo
               contrato.save(update_fields=['prestamos_empresa'])
       ```
     - Elimina la nómina de la base de datos
     - Registra en log de auditoría
   - Frontend: Refresca tabla de historial y tabla principal

---

## 7. Flujo de Nóminas (Multitanda)

### 7.1 Concepto de Nómina Multitanda

**Problema Anterior:**
- Solo se permitía UNA nómina por empleado por mes (`unique_together = ['empleado', 'periodo_mes']`)

**Solución v2.60:**
- Permite múltiples nóminas en el mismo mes si `fecha_pago` es diferente
- Clave de unicidad: `['empleado', 'periodo_mes', 'fecha_pago']`
- Validación: La suma de `dias_laborados` en el mes no puede exceder 31 días

### 7.2 Cambios en el Modelo

**Antes:**
```python
class Meta:
    unique_together = [['empleado', 'periodo_mes']]
```

**Después:**
```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=['empleado', 'periodo_mes', 'fecha_pago'],
            condition=Q(anulado=False),
            name='uniq_nomina_per_empleado_periodo_fecha'
        )
    ]
```

### 7.3 Validación de Solapamiento

**Función:** `validar_limite_dias_mes()`

**Lógica:**
```python
def validar_limite_dias_mes(empleado_id, periodo_mes, nuevos_dias, empresa_id, devengo_id_excluir=None):
    total_dias_existentes = Devengo.objects.filter(
        empleado_id=empleado_id,
        periodo_mes=periodo_mes,
        empresa_id=empresa_id,
        anulado=False
    ).exclude(pk=devengo_id_excluir).aggregate(total=Sum('dias_laborados'))['total'] or Decimal('0')
    
    nuevos_dias_decimal = Decimal(str(nuevos_dias))
    total_final_dias = total_dias_existentes + nuevos_dias_decimal
    
    if total_final_dias > Decimal('31'):
        raise ValidationError({
            'dias_laborados': f'La suma de días laborados excede los 31 días del mes.',
            'code': 'dias_excedidos',
            'dias_registrados': str(total_dias_existentes),
            'dias_nuevos': str(nuevos_dias_decimal),
            'total': str(total_final_dias)
        })
```

**Llamada en ViewSet:**
```python
# En DevengoViewSet.create()
validacion_dias = validar_limite_dias_mes(
    empleado_id=empleado_id,
    periodo_mes=periodo_mes,
    nuevos_dias=dias_laborados,
    empresa_id=empresa.id
)

if validacion_dias['excede_limite']:
    return Response({
        "error": "La suma de días laborados excede los 31 días del mes.",
        "code": "dias_excedidos",
        "dias_registrados": str(validacion_dias['total_dias']),
        "total": str(validacion_dias['total_final'])
    }, status=status.HTTP_400_BAD_REQUEST)
```

### 7.4 Cambios en el Frontend

**Template:** `devengo_offcanvas.html`

**Campo `fecha_pago` (ahora obligatorio y parte de la clave de unicidad):**
```html
<div class="mb-3">
  <label for="devengo-fecha_pago" class="form-label">Fecha de Pago <span class="text-danger">*</span></label>
  <input type="date" class="form-control" id="devengo-fecha_pago" name="fecha_pago" 
         value="{% if devengo %}{{ devengo.fecha_pago|date:'Y-m-d' }}{% endif %}" 
         required
         hx-post="/api/v1/empleados/devengos/preview-calculo/"
         hx-target="#devengo-campos-calculados, #devengo-deducciones-calculadas"
         hx-swap="innerHTML"
         hx-trigger="change, keyup changed delay:500ms, blur"
         hx-include="#devengo-contrato-id, #devengo-dias_laborados, #devengo-otros_devengos, #devengo-prestamos, #devengo-descuentos_operativos, #devengo-periodo_mes"
         hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'
         hx-on::htmx:before-request="document.getElementById('devengo-campos-calculados').innerHTML = '';"
         hx-on::htmx:response-error="window.UIManager && window.UIManager.handleError && window.UIManager.handleError(event.detail, '[devengo.offcanvas]', {errorContainerSelector: '#form-devengo-feedback'})">
  <small class="form-text text-muted">Permite registrar múltiples pagos (semanas/quincenas) en el mismo mes.</small>
</div>
```

**Campo `periodo_mes` (ahora informativo, permite múltiples registros):**
```html
<div class="mb-3">
  <label for="devengo-periodo_mes" class="form-label">Periodo (YYYY-MM) <span class="text-danger">*</span></label>
  <input type="text" class="form-control" 
         id="devengo-periodo_mes" name="periodo_mes" 
         value="{% if devengo %}{{ devengo.periodo_mes }}{% else %}{{ 'now'|date:'Y-m' }}{% endif %}" 
         pattern="\d{4}-\d{2}" placeholder="2024-01" 
         title="Formato: YYYY-MM (ej: 2024-01)" 
         required
         hx-post="/api/v1/empleados/devengos/preview-calculo/"
         hx-target="#devengo-campos-calculados, #devengo-deducciones-calculadas"
         hx-swap="innerHTML"
         hx-trigger="change, keyup changed delay:500ms, blur"
         hx-include="#devengo-contrato-id, #devengo-dias_laborados, #devengo-otros_devengos, #devengo-prestamos, #devengo-descuentos_operativos, #devengo-fecha_pago"
         hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'
         hx-on::htmx:before-request="document.getElementById('devengo-campos-calculados').innerHTML = '';"
         hx-on::htmx:response-error="window.UIManager && window.UIManager.handleError && window.UIManager.handleError(event.detail, '[devengo.offcanvas]', {errorContainerSelector: '#form-devengo-feedback'})">
  <small class="form-text text-muted">Formato: YYYY-MM (ej: 2024-01). Puede registrar múltiples nóminas en el mismo mes usando diferentes fechas de pago (semanas, quincenas, etc.).</small>
</div>
```

---

## 8. Historial de Nóminas

### 8.1 Endpoint Backend

**Ubicación:** `apps/tenant/empleados/api/viewsets.py`

**Método:** `EmpleadoViewSet.historial_nominas()`

```python
@action(detail=True, methods=["get"], renderer_classes=[TemplateHTMLRenderer, JSONRenderer], url_path="historial-nominas")
def historial_nominas(self, request, pk=None):
    """
    ⚠️ v2.60: Devuelve el HTML del historial de nóminas para un empleado específico (HTMX)
    o los datos JSON para Tabulator (paginación remota).
    
    Endpoint: GET /api/v1/empleados/{id}/historial-nominas/
    """
    empresa = Empresa.objects.only('id').first()
    if not empresa:
        return Response({"error": "sin_empresa"}, status=404)
    
    empleado_id = pk
    empleado = get_object_or_404(Empleado, pk=empleado_id, empresa_id=empresa.id)
    
    # Si es petición HTMX (Accept: text/html), retornar template
    if request.accepted_renderer.format == 'html':
        context = {
            'empleado': empleado,
            'empleado_id': empleado_id
        }
        return Response(context, template_name='tenant/core/partials/empleados/historial_nominas_offcanvas.html')
    
    # Si es petición JSON (Tabulator), retornar datos paginados
    queryset = qs_historial_list(empleado_id, empresa.id)
    page = self.paginate_queryset(queryset)
    
    if page is not None:
        serializer = DevengoSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
    
    serializer = DevengoSerializer(queryset, many=True)
    return Response(serializer.data)
```

### 8.2 Template Frontend

**Ubicación:** `apps/tenant/core/templates/tenant/core/partials/empleados/historial_nominas_offcanvas.html`

```html
<div class="offcanvas offcanvas-end" tabindex="-1" id="offcanvas-historial-nominas" aria-labelledby="offcanvas-historial-nominas-label">
  <div class="offcanvas-header">
    <h5 class="offcanvas-title" id="offcanvas-historial-nominas-label">
      <i class="bi bi-clock-history me-2"></i>Historial de Nóminas
    </h5>
    <button type="button" class="btn-close" data-bs-dismiss="offcanvas" aria-label="Cerrar"></button>
  </div>
  <div class="offcanvas-body">
    <div class="mb-3">
      <p class="text-muted">
        <strong>Empleado:</strong> {{ empleado.primer_nombre }} {{ empleado.primer_apellido }}
        <br>
        <small>Documento: {{ empleado.numero_documento }}</small>
      </p>
    </div>
    
    <div class="mb-3">
      <input type="text" id="search-historial-nominas" class="form-control" 
             placeholder="Buscar por periodo o fecha de pago..." 
             aria-label="Buscar historial">
    </div>
    
    <div id="grid-historial-nominas" style="min-height: 400px;"></div>
    
    <div id="form-historial-feedback" class="alert d-none mt-3" role="alert" aria-live="polite"></div>
  </div>
</div>
```

### 8.3 Inicialización JavaScript

**Función:** `initHistorialNominas(empleadoId)`

**Características:**
- Anti-Zombies Pattern: Destruye instancia previa antes de crear nueva
- Event Delegation: Botones "Ver/Editar" y "Eliminar" manejados por event delegation
- Validación: Verifica que `empleadoId` sea válido antes de inicializar
- Integración con UIManager: Manejo de errores centralizado

---

## 9. Integración HTMX y Offcanvas

### 9.1 Arquitectura HTMX

**Principios:**
- **Sin Recargas de Página:** HTMX maneja todas las interacciones dinámicas
- **Partial Swapping:** Solo se actualiza el contenido necesario
- **Progressive Enhancement:** Funciona sin JavaScript (fallback)

### 9.2 Contenedores Offcanvas Globales

**Ubicación:** `apps/tenant/core/templates/tenant/core/workspace.html`

```html
{# Módulo Empleados - Contenedores Offcanvas globales #}
<div id="offcanvas-container-empleado"></div>
<div id="offcanvas-container-contrato"></div>
<div id="offcanvas-container-devengo"></div>
<div id="offcanvas-container-historial-nominas"></div>
```

**Razón:** Centralizar contenedores para evitar duplicación y asegurar consistencia.

### 9.3 Flujo HTMX: Cargar Offcanvas

**1. Usuario hace clic en botón de acción**
   - JavaScript: `htmx.ajax('GET', url, { target: '#offcanvas-container-{tipo}', swap: 'innerHTML' })`

**2. Backend retorna HTML del offcanvas**
   - ViewSet: `TemplateResponse` con template correspondiente

**3. HTMX reemplaza contenido del contenedor**
   - Swap: `innerHTML` (reemplaza todo el contenido)

**4. JavaScript muestra el offcanvas**
   - Bootstrap: `bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show()`

### 9.4 Flujo HTMX: Enviar Formulario

**1. Usuario completa formulario y hace clic en "Guardar"**
   - HTMX: `hx-post="/api/v1/empleados/{endpoint}/"` en el `<form>`

**2. HTMX envía datos al backend**
   - Headers: `X-CSRFToken` (CSRF protection)
   - Body: Form data serializado

**3. Backend procesa y retorna respuesta**
   - Success (201/200): JSON con datos del objeto creado/actualizado
   - Error (400/409/500): JSON con mensaje de error estructurado

**4. Frontend maneja respuesta**
   - Success: `htmx:afterOnLoad` cierra offcanvas y refresca tabla
   - Error: `htmx:responseError` muestra mensaje con `UIManager.handleError()`

### 9.5 Flujo HTMX: Preview en Tiempo Real

**1. Usuario cambia `dias_laborados`, `periodo_mes` o `fecha_pago`**
   - HTMX: `hx-post="/api/v1/empleados/devengos/preview-calculo/"` en el `<input>`
   - Trigger: `change, keyup changed delay:500ms, blur`

**2. Backend calcula valores**
   - ViewSet: `DevengoViewSet.preview_calculo()`
   - Service: `calcular_nomina_colombia()`

**3. Backend retorna partial HTML**
   - Template: `devengo_calculo_partial.html` (success) o `devengo_calculo_error.html` (error)

**4. HTMX reemplaza contenedor de resultados**
   - Target: `#devengo-campos-calculados`
   - Swap: `innerHTML`

---

## 10. Validaciones y Zero Trust

### 10.1 Validación de Tenant (Zero Trust)

**Principio:** Todos los datos deben pertenecer al tenant actual.

**Implementación en ViewSets:**
```python
def get_queryset(self):
    # Obtener empresa del usuario autenticado
    user = getattr(self.request, 'user', None)
    if not user or not user.is_authenticated:
        return Empleado.objects.none()
    
    # Intentar obtener empresa del usuario
    empresa = None
    if hasattr(user, 'empresa'):
        empresa = user.empresa
    elif hasattr(user, 'empresa_id'):
        try:
            empresa = Empresa.objects.only('id').get(id=user.empresa_id)
        except Empresa.DoesNotExist:
            pass
    
    # Fallback: Si no hay empresa en el usuario, usar la del tenant (compatibilidad)
    if not empresa:
        empresa = Empresa.objects.only('id').first()
    
    if not empresa: 
        return Empleado.objects.none()
    
    empresa_id = empresa.id
    return Empleado.objects.filter(empresa_id=empresa_id)
```

**Validación en Serializers:**
```python
class EmpleadoDetailSerializer(NormalizationMixin, serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar queryset de ForeignKeys por empresa del tenant
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            empresa = getattr(request.user, 'empresa', None)
            if empresa:
                # Asegurar que los ForeignKeys solo muestren opciones del tenant
                pass
```

### 10.2 Validación de Integridad de Datos

**1. Unicidad de Empleado por Tenant:**
   - Constraint: `UniqueConstraint(fields=['empresa', 'tipo_documento', 'numero_documento'])`

**2. Un Contrato Activo por Empleado:**
   - Constraint: `UniqueConstraint(fields=['empleado', 'activo'], condition=Q(activo=True))`

**3. Unicidad de Nómina (Multitanda):**
   - Constraint: `UniqueConstraint(fields=['empleado', 'periodo_mes', 'fecha_pago'], condition=Q(anulado=False))`

**4. Validación de Solapamiento de Días:**
   - Service: `validar_limite_dias_mes()` verifica que la suma no exceda 31 días

### 10.3 Validación de Cálculos (Zero Trust)

**Principio:** El frontend NUNCA envía valores calculados. El backend siempre recalcula.

**Implementación:**
```python
# En DevengoViewSet.create()
# ⚠️ Zero Trust: Recalcular todos los valores antes de guardar
resultado_calculo = calcular_nomina_colombia(
    empleado_id=empleado_id,
    contrato_id=contrato_id,
    periodo_mes=periodo_mes,
    fecha_pago=fecha_pago_obj,
    dias_laborados=Decimal(str(dias_laborados)),
    otros_devengos=Decimal(str(otros_devengos or 0)),
    prestamos=Decimal(str(prestamos or 0)),
    descuentos_operativos=Decimal(str(descuentos_operativos or 0)),
    empresa_id=empresa.id
)

# Asignar valores calculados (no confiar en el frontend)
serializer.validated_data['salario_base'] = resultado_calculo['salario_base']
serializer.validated_data['auxilio_transporte'] = resultado_calculo['auxilio_transporte']
serializer.validated_data['salud_empleado'] = resultado_calculo['salud_empleado']
serializer.validated_data['pension_empleado'] = resultado_calculo['pension_empleado']
serializer.validated_data['neto_pagar'] = resultado_calculo['neto_pagar']
```

**Campos Readonly en Serializer:**
```python
class DevengoSerializer(NormalizationMixin, serializers.ModelSerializer):
    salario_base = serializers.DecimalField(read_only=True)
    auxilio_transporte = serializers.DecimalField(read_only=True)
    salud_empleado = serializers.DecimalField(read_only=True)
    pension_empleado = serializers.DecimalField(read_only=True)
    neto_pagar = serializers.DecimalField(read_only=True)
```

---

## 11. Manejo de Errores

### 11.1 Error Boundary Pattern

**Implementación:** `window.UIManager.handleError()`

**Uso en HTMX:**
```html
<form hx-post="/api/v1/empleados/devengos/" 
      hx-on::htmx:response-error="window.UIManager && window.UIManager.handleError && window.UIManager.handleError(event.detail, '[devengo.offcanvas]', {errorContainerSelector: '#form-devengo-feedback'})">
  <div id="form-devengo-feedback" class="alert d-none" role="alert"></div>
  <!-- ... campos del formulario ... -->
</form>
```

**Uso en JavaScript:**
```javascript
window.http('DELETE', `/api/v1/empleados/devengos/${devengoId}/`)
  .then(function(response) {
    if (response.ok) {
      // Success
    } else {
      if (window.UIManager && typeof window.UIManager.handleError === 'function') {
        window.UIManager.handleError(response, '[empleados.page]', {
          errorContainerSelector: '#form-historial-feedback'
        });
      }
    }
  })
  .catch(function(error) {
    if (window.UIManager && typeof window.UIManager.handleError === 'function') {
      window.UIManager.handleError(
        { status: 500, data: { detail: `Error de conexión: ${error.message || error}` } },
        '[empleados.page]',
        { errorContainerSelector: '#form-historial-feedback' }
      );
    }
  });
```

### 11.2 Tipos de Errores Manejados

**1. 400 Bad Request (Validación):**
   - Campos requeridos faltantes
   - Valores inválidos
   - Días excedidos (`code: 'dias_excedidos'`)

**2. 403 Forbidden (Permisos):**
   - Usuario no tiene permisos para la acción
   - Recurso no pertenece al tenant (Zero Trust)

**3. 404 Not Found:**
   - Recurso no existe
   - Recurso no pertenece al tenant (Zero Trust)

**4. 409 Conflict (Duplicado):**
   - Nómina duplicada (`code: 'duplicate_nomina'`)
   - Incluye `devengo_existente_id` para enlace directo

**5. 500 Internal Server Error:**
   - Errores inesperados del servidor
   - Errores de base de datos

### 11.3 Mensajes de Error Específicos

**Nómina Duplicada (409):**
```javascript
if (statusCode === 409 || parsedResponse?.code === 'duplicate_nomina') {
  const errorMessage = parsedResponse?.error || 'Ya existe una nómina para este empleado, periodo y fecha de pago.';
  const devengoExistenteId = parsedResponse?.devengo_existente_id;
  
  // Deshabilitar botón "Guardar"
  const btnGuardar = document.getElementById('btn-guardar-devengo');
  if (btnGuardar) {
    btnGuardar.disabled = true;
    btnGuardar.innerHTML = '<i class="bi bi-lock me-1"></i>Nómina Duplicada (Deshabilitado)';
  }
  
  // Mostrar mensaje con enlace a registro existente
  const feedbackEl = document.querySelector('#form-devengo-feedback');
  if (feedbackEl) {
    feedbackEl.classList.remove('d-none');
    feedbackEl.classList.add('alert-danger');
    feedbackEl.innerHTML = `
      <i class="bi bi-exclamation-triangle-fill me-2"></i>
      <strong>Error de Integridad:</strong> ${errorMessage}
      <br>
      <small>Use el <strong>Historial de Nóminas</strong> para anular el registro previo.</small>
      ${devengoExistenteId ? `
        <br>
        <button type="button" class="btn btn-sm btn-outline-info mt-2" 
                onclick="window.EmpleadosModule.openDevengoOffcanvas(null, ${devengoExistenteId})">
          <i class="bi bi-eye me-1"></i>Ver Registro Existente
        </button>
      ` : ''}
    `;
  }
  
  // Marcar campos como inválidos
  const periodoInput = document.getElementById('devengo-periodo_mes');
  const fechaPagoInput = document.getElementById('devengo-fecha_pago');
  if (periodoInput) { periodoInput.classList.add('is-invalid'); }
  if (fechaPagoInput) { fechaPagoInput.classList.add('is-invalid'); }
}
```

**Días Excedidos (400):**
```javascript
if (parsedResponse && parsedResponse.code === 'dias_excedidos') {
  const feedbackEl = document.querySelector('#form-devengo-feedback');
  if (feedbackEl) {
    feedbackEl.classList.remove('d-none');
    feedbackEl.classList.add('alert-danger');
    feedbackEl.innerHTML = `
      <i class="bi bi-exclamation-triangle-fill me-2"></i>
      <strong>Días Excedidos:</strong> ${parsedResponse.detail}
      <br>
      <small>Días registrados: ${parsedResponse.dias_registrados} | Nuevos días: ${parsedResponse.dias_nuevos} | Total: ${parsedResponse.total}</small>
    `;
  }
  
  const diasInput = document.getElementById('devengo-dias_laborados');
  if (diasInput) { diasInput.classList.add('is-invalid'); }
}
```

### 11.4 Re-habilitación de Botones y Limpieza de Errores

**Función:** `reenableButton()`

```javascript
const reenableButton = function() {
  const btnGuardar = document.getElementById('btn-guardar-devengo');
  const feedbackEl = document.querySelector('#form-devengo-feedback');
  const periodoInput = document.getElementById('devengo-periodo_mes');
  const fechaPagoInput = document.getElementById('devengo-fecha_pago');
  const diasInput = document.getElementById('devengo-dias_laborados');
  
  if (btnGuardar && btnGuardar.disabled) {
    btnGuardar.disabled = false;
    btnGuardar.classList.remove('btn-secondary');
    btnGuardar.classList.add('btn-primary');
    btnGuardar.innerHTML = '<i class="bi bi-check-lg me-1"></i>Guardar Nómina';
  }
  
  if (feedbackEl) {
    feedbackEl.classList.add('d-none');
    feedbackEl.innerHTML = '';
  }
  
  if (periodoInput) {
    periodoInput.classList.remove('is-invalid');
    periodoInput.removeAttribute('aria-invalid');
  }
  
  if (fechaPagoInput) {
    fechaPagoInput.classList.remove('is-invalid');
    fechaPagoInput.removeAttribute('aria-invalid');
  }
  
  if (diasInput) {
    diasInput.classList.remove('is-invalid');
    diasInput.removeAttribute('aria-invalid');
  }
};

// Escuchar cambios en campos para re-habilitar el botón
document.addEventListener('change', function(event) {
  if (event.target.id === 'devengo-periodo_mes' || event.target.id === 'devengo-fecha_pago') {
    reenableButton();
  }
});

document.addEventListener('input', function(event) {
  if (event.target.id === 'devengo-dias_laborados') {
    reenableButton();
  }
});
```

---

## 12. Checklist de Validación

### 12.1 Backend

- [ ] **Modelos:**
  - [ ] Todos los modelos tienen `empresa = ForeignKey(Empresa, on_delete=PROTECT)` con índice
  - [ ] Constraints de unicidad correctamente definidos
  - [ ] Validaciones en `clean()` para integridad de datos

- [ ] **Services:**
  - [ ] `LIST_FIELDS` y `DETAIL_FIELDS` definidos como tuplas (no `__all__`)
  - [ ] Querysets optimizados con `.only()` y `select_related()`
  - [ ] `calcular_nomina_colombia()` implementa normativa colombiana (46 horas semanales)
  - [ ] `validar_limite_dias_mes()` valida solapamiento de días

- [ ] **ViewSets:**
  - [ ] `get_queryset()` filtra siempre por `empresa_id` (Zero Trust)
  - [ ] `get_object()` usa querysets optimizados del service layer
  - [ ] `list()` retorna formato DRF: `{count, results}`
  - [ ] `gestor_offcanvas` retorna `TemplateResponse` con template correcto
  - [ ] `create()` valida duplicados y solapamiento antes de guardar
  - [ ] `destroy()` revierte préstamos al contrato antes de eliminar

- [ ] **Serializers:**
  - [ ] Heredan de `NormalizationMixin` para limpieza de datos
  - [ ] Campos calculados marcados como `read_only=True`
  - [ ] ForeignKeys validan pertenencia al tenant

### 12.2 Frontend

- [ ] **Templates:**
  - [ ] Todos los offcanvas tienen `{% csrf_token %}`
  - [ ] Campos readonly tienen clase `bg-light` o atributo `readonly`
  - [ ] Inputs de fecha tienen `type="date"` y formato correcto
  - [ ] Inputs numéricos tienen `step="0.01"` para decimales

- [ ] **JavaScript:**
  - [ ] `window.EmpleadosModule` expone todas las funciones necesarias
  - [ ] `initEmpleadosTable()` usa `TabulatorFactory.create()`
  - [ ] Lazy loading con `DOMUtils.onVisibleOnce()`
  - [ ] Event delegation para botones dinámicos
  - [ ] Anti-Zombies Pattern: Destruye instancias previas
  - [ ] `UIManager.handleError()` integrado en todos los flujos de error

- [ ] **HTMX:**
  - [ ] Todos los formularios tienen `hx-post` o `hx-put`
  - [ ] `hx-target` apunta a contenedores correctos
  - [ ] `hx-swap` configurado correctamente (`innerHTML`, `none`, etc.)
  - [ ] `hx-headers` incluye `X-CSRFToken`
  - [ ] `hx-on::htmx:response-error` maneja errores con `UIManager`

### 12.3 Flujos CRUD

- [ ] **Crear:**
  - [ ] Offcanvas se carga correctamente vía HTMX
  - [ ] Formulario envía datos al endpoint correcto
  - [ ] Backend valida y crea registro
  - [ ] Frontend cierra offcanvas y refresca tabla

- [ ] **Leer:**
  - [ ] Tabla Tabulator carga datos paginados correctamente
  - [ ] Búsqueda funciona con `?search=`
  - [ ] Botones de acción abren offcanvas correcto

- [ ] **Actualizar:**
  - [ ] Offcanvas carga datos existentes
  - [ ] Formulario envía cambios al endpoint correcto
  - [ ] Backend valida y actualiza registro
  - [ ] Frontend cierra offcanvas y refresca tabla

- [ ] **Eliminar:**
  - [ ] Confirmación antes de eliminar
  - [ ] Backend elimina registro y revierte préstamos (si aplica)
  - [ ] Frontend refresca tabla después de eliminar

### 12.4 Nómina Multitanda

- [ ] **Modelo:**
  - [ ] `UniqueConstraint` incluye `fecha_pago` en la clave de unicidad
  - [ ] Constraint tiene `condition=Q(anulado=False)`

- [ ] **Validación:**
  - [ ] `validar_limite_dias_mes()` verifica que la suma no exceda 31 días
  - [ ] ViewSet llama a `validar_limite_dias_mes()` antes de crear

- [ ] **Frontend:**
  - [ ] Campo `fecha_pago` es obligatorio y parte del formulario
  - [ ] Mensaje de error para duplicados incluye `fecha_pago`
  - [ ] Mensaje de error para días excedidos muestra detalles

### 12.5 Historial de Nóminas

- [ ] **Backend:**
  - [ ] `historial_nominas` retorna template HTML para HTMX
  - [ ] `historial_nominas` retorna JSON paginado para Tabulator
  - [ ] Filtra por `empresa_id` y `empleado_id` (Zero Trust)

- [ ] **Frontend:**
  - [ ] Offcanvas se carga correctamente vía HTMX
  - [ ] Tabla Tabulator se inicializa después de cargar offcanvas
  - [ ] Botones "Ver/Editar" abren offcanvas de nómina
  - [ ] Botones "Eliminar" envían petición DELETE y refrescan tabla

---

## 📝 Notas Finales

### Versión de Arquitectura
- **v2.60**: Standalone Architecture con HTMX + Offcanvas
- **v2.40**: API-First Architecture con Tabulator Factory
- **v2.95**: Flujo Secuencial (Máquina de Estados)

### Dependencias Críticas
- `django-tenants`: Multi-tenancy por esquema
- `djangorestframework`: API REST
- `Tabulator`: Tablas interactivas
- `HTMX`: Interacciones dinámicas sin JavaScript complejo
- `Bootstrap 5`: Componentes UI (Offcanvas, Modals, etc.)

### Mejoras Futuras
- [ ] Implementar soft delete para nóminas (flag `anulado` en lugar de hard delete)
- [ ] Agregar exportación de nóminas a Excel/PDF
- [ ] Implementar notificaciones en tiempo real para cambios en nóminas
- [ ] Agregar auditoría de cambios (quién, cuándo, qué cambió)

---

**Documento generado automáticamente por Cursor AI**  
**Última actualización:** 2026-03-XX
