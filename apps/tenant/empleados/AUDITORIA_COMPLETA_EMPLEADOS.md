# Auditoría y Flujo Completo: Módulo de Empleados v2.60

**Fecha de Auditoría:** 2026-03-XX  
**Versión de Arquitectura:** SINTEL v2.60 (Standalone Architecture)  
**Módulo:** `apps/tenant/empleados`  
**Estado:** ✅ Producción - Completamente funcional

---

## 📋 Índice

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Arquitectura General](#2-arquitectura-general)
3. [Estructura de la Aplicación](#3-estructura-de-la-aplicación)
4. [Modelos y Estructura de Datos](#4-modelos-y-estructura-de-datos)
5. [Capa de Servicios (Service Layer)](#5-capa-de-servicios-service-layer)
6. [API y ViewSets (Backend)](#6-api-y-viewsets-backend)
7. [Frontend: JavaScript y Templates](#7-frontend-javascript-y-templates)
8. [Flujos CRUD Completos](#8-flujos-crud-completos)
9. [Flujo de Nóminas (Multitanda)](#9-flujo-de-nóminas-multitanda)
10. [Historial de Nóminas](#10-historial-de-nóminas)
11. [Integración HTMX y Offcanvas](#11-integración-htmx-y-offcanvas)
12. [Validaciones y Zero Trust](#12-validaciones-y-zero-trust)
13. [Manejo de Errores](#13-manejo-de-errores)
14. [Historial de Cambios (Changelog)](#14-historial-de-cambios-changelog)
15. [Checklist de Validación](#15-checklist-de-validación)

---

## 1. Resumen Ejecutivo

### 1.1 Descripción del Módulo

El módulo de **Empleados** gestiona el ciclo completo de recursos humanos:
- **Empleados**: Información personal, documentos, seguridad social
- **Contratos**: Tipos de contrato, salarios, fechas de inicio/fin
- **Nóminas (Devengos)**: Cálculo y registro de pagos de nómina según normativa colombiana

### 1.2 Características Principales

✅ **Flujo Secuencial (Máquina de Estados)**
- Empleado → Contrato → Nómina
- Validación de dependencias en cada paso

✅ **Nómina Multitanda**
- Múltiples pagos por mes (semanas, quincenas)
- Validación de solapamiento de días (máximo 31 días/mes)

✅ **Cálculos Automáticos (Zero Trust)**
- Salario proporcional según días laborados
- Deducciones de ley (Salud 4%, Pensión 4%)
- Neto a pagar calculado en backend

✅ **Arquitectura v2.60**
- HTMX + Offcanvas (sin modales)
- Tabulator Factory para tablas interactivas
- API-First con DRF

✅ **Validaciones Robustas**
- Zero Trust: Validación de tenant en cada operación
- Integridad de datos: Constraints de unicidad
- Validación de solapamiento de días

### 1.3 Tecnologías Utilizadas

- **Backend:** Django 4.x, Django REST Framework, django-tenants
- **Frontend:** Vanilla JavaScript, HTMX, Bootstrap 5, Tabulator.js
- **Base de Datos:** PostgreSQL (multi-tenant por esquema)
- **Arquitectura:** API-First, Service Layer Pattern, Zero Trust

---

## 2. Arquitectura General

### 2.1 Principios Arquitectónicos (v2.60)

- **API-First**: Todas las funcionalidades expuestas vía REST API (DRF)
- **Single Source of Truth (SSoT)**: `empresa = ForeignKey(Empresa, on_delete=PROTECT)` en todos los modelos
- **Zero Trust**: Validación estricta de pertenencia al tenant en cada operación
- **Service Layer Pattern**: Lógica de negocio centralizada en `services.py`
- **Anemic Models**: Modelos solo definen estructura de datos, sin lógica de negocio
- **Feature-Sliced Frontend**: JavaScript modular por funcionalidad
- **HTMX + Offcanvas**: Interfaz dinámica sin recargas de página
- **Tabulator Factory**: Tablas interactivas con paginación remota

### 2.2 Flujo Secuencial (Máquina de Estados)

```
┌─────────────────┐
│    Empleado     │ ← Creación inicial (datos personales, documentos)
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│    Contrato     │ ← Requiere Empleado, habilita "Registrar Nómina"
│   (ACTIVO)      │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Devengo/Nómina │ ← Requiere Contrato ACTIVO, habilita "Historial"
│  (Multitanda)   │
└─────────────────┘
```

**Reglas de Negocio:**
- Solo UN contrato ACTIVO por empleado (constraint de base de datos)
- Nómina requiere contrato ACTIVO
- Múltiples nóminas por mes permitidas si `fecha_pago` es diferente
- Suma de `dias_laborados` en el mes no puede exceder 31 días

### 2.3 Aislamiento Multi-Tenant

- **django-tenants**: Aislamiento por esquema de base de datos
- **Validación Zero Trust**: Todos los querysets filtran por `empresa_id`
- **Serializers**: Validan que ForeignKeys pertenezcan al tenant actual
- **ViewSets**: `get_queryset()` siempre filtra por `request.user.empresa`

---

## 3. Estructura de la Aplicación

### 3.1 Estructura de Directorios

```
apps/tenant/empleados/
├── __init__.py
├── admin.py                    # Configuración de Django Admin
├── apps.py                     # Configuración de la app
├── models.py                   # Modelos: Empleado, Contrato, Devengo
├── services.py                 # Lógica de negocio y querysets optimizados
├── choices.py                  # Constantes y choices para campos
├── api/
│   ├── __init__.py
│   ├── serializers.py         # Serializers con NormalizationMixin
│   ├── viewsets.py            # ViewSets con acciones HTMX
│   └── urls.py                # Rutas de la API
├── services/
│   ├── __init__.py
│   ├── empleado_service.py    # Servicios específicos de Empleado
│   └── devengo_service.py     # Servicios específicos de Devengo
├── migrations/                # Migraciones de base de datos
│   ├── 0001_initial.py
│   ├── 0002_contrato_empresa_devengo_empresa_and_more.py
│   └── 0003_cambiar_unicidad_nomina_multitanda.py
└── tests/                     # Tests unitarios e integración
    ├── test_api_smoke.py
    ├── test_devengos_api_and_service.py
    └── test_routing_smoke.py

apps/tenant/core/templates/tenant/core/partials/empleados/
├── list.html                          # Vista principal con Tabulator
├── empleado_offcanvas.html           # Formulario CRUD Empleado
├── contrato_offcanvas.html            # Formulario CRUD Contrato
├── devengo_offcanvas.html             # Formulario CRUD Nómina
├── historial_nominas_offcanvas.html   # Historial de nóminas
├── devengo_calculo_partial.html       # Partial HTMX para preview
├── devengo_calculo_error.html         # Partial HTMX para errores
├── assets_empleados.html              # Carga de scripts JS
└── modals.html                        # ⚠️ DEPRECATED (v2.60: Offcanvas)

apps/tenant/core/static/core/js/empleados/
├── empleados.api.js       # Capa de datos (window.http)
└── features/              # ⚠️ v2.60: Feature-Sliced Architecture
    ├── empleados_list.js      # Tabla principal y delegación de eventos
    ├── empleados_editor.js    # CRUD de empleados + listeners HTMX
    ├── contratos_editor.js    # CRUD de contratos + listeners HTMX
    ├── devengos_editor.js     # CRUD de nóminas + listeners HTMX (409/400)
    └── historial_nominas.js   # Historial de nóminas + event delegation
```

### 3.2 Dependencias de la Aplicación

**Backend:**
- `django` >= 4.2
- `djangorestframework` >= 3.14
- `django-tenants` >= 3.5
- `django-filter` >= 23.0

**Frontend:**
- `htmx` >= 1.9
- `bootstrap` >= 5.3
- `tabulator` >= 5.5

---

## 4. Modelos y Estructura de Datos

### 4.1 Modelo: Empleado

**Ubicación:** `apps/tenant/empleados/models.py`

**Descripción:** Información personal y laboral del empleado.

**Campos Principales:**
```python
# ⚠️ SSoT: FK a Empresa (única FK externa)
empresa = ForeignKey(Empresa, on_delete=PROTECT, related_name='empleados')

# Identificación
tipo_documento = CharField(max_length=5, choices=TIPO_DOC)  # CC, CE, PA, PPT
numero_documento = CharField(max_length=32, db_index=True)

# Datos Personales
primer_nombre = CharField(max_length=80)
segundo_nombre = CharField(max_length=80, blank=True)
primer_apellido = CharField(max_length=80)
segundo_apellido = CharField(max_length=80, blank=True)
email = EmailField()
telefono = CharField(max_length=32, blank=True)

# Seguridad Social
eps = CharField(max_length=10, choices=EPS_CHOICES)
afp = CharField(max_length=10, choices=AFP_CHOICES)
arl = CharField(max_length=10, choices=ARL_CHOICES)
nivel_riesgo_arl = CharField(max_length=5, choices=RIESGO_ARL_CHOICES, default='I')

# Estado y Fechas
estado = CharField(max_length=12, choices=ESTADOS, default='ACTIVO')  # ACTIVO, RETIRADO
fecha_ingreso = DateField()
fecha_retiro = DateField(null=True, blank=True)
```

**Constraints:**
```python
UniqueConstraint(
    fields=['empresa', 'tipo_documento', 'numero_documento'],
    name='uniq_empleado_per_tenant'
)
```

**Índices:**
- `['empresa', 'estado']` - Para filtrado rápido por estado
- `['numero_documento']` - Para búsqueda por documento

**Propiedades:**
```python
@property
def nombre_completo(self):
    return f"{self.primer_nombre} {self.primer_apellido}"
```

### 4.2 Modelo: Contrato

**Descripción:** Contrato de trabajo vinculado a un empleado.

**Campos Principales:**
```python
# ⚠️ SSoT: FK a Empresa
empresa = ForeignKey(Empresa, on_delete=PROTECT, related_name='contratos')
empleado = ForeignKey(Empleado, on_delete=PROTECT, related_name='contratos')

# Tipo y Fechas
tipo = CharField(max_length=20, choices=TIPO_CHOICES)  # FIJO, INDEFINIDO, PRESTACION_SERVICIOS
fecha_inicio = DateField()
fecha_fin = DateField(null=True, blank=True)

# Remuneración
salario_mensual = DecimalField(max_digits=12, decimal_places=2)
auxilio_transporte = DecimalField(max_digits=12, decimal_places=2, default=0)
prestamos_empresa = DecimalField(max_digits=12, decimal_places=2, default=0)  # Para reversión

# Información Adicional
cargo = CharField(max_length=100)
archivo_pdf = FileField(upload_to='contratos/', null=True, blank=True)

# Estado
estado = CharField(max_length=12, choices=ESTADO_CHOICES, default='ACTIVO')  # ACTIVO, INACTIVO
activo = BooleanField(default=True)  # Para máquina de estados
```

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
- Al activar un contrato, se desactivan automáticamente los demás (en `save()`)

### 4.3 Modelo: Devengo (Nómina)

**Descripción:** Registro de pago de nómina con cálculos automáticos.

**Campos Principales:**
```python
# ⚠️ SSoT: FK a Empresa
empresa = ForeignKey(Empresa, on_delete=PROTECT, related_name='nominas')
empleado = ForeignKey(Empleado, on_delete=PROTECT, related_name="nominas")
contrato = ForeignKey(Contrato, on_delete=PROTECT, related_name="pagos_nomina")

# Periodo y Fecha
periodo_mes = CharField(max_length=7, help_text="Formato: YYYY-MM")  # ⚠️ Parte de clave de unicidad
fecha_pago = DateField()  # ⚠️ Parte de clave de unicidad (Nómina Multitanda)

# Días Laborados
dias_laborados = DecimalField(
    max_digits=5,
    decimal_places=2,
    default=30,
    validators=[MinValueValidator(Decimal('0.5'))],
    help_text="Días laborados (0.5-30, permite decimales)"
)

# ⚠️ DEVENGOS (valores proporcionales calculados en COP)
salario_base = DecimalField(max_digits=12, decimal_places=2)  # readonly
auxilio_transporte = DecimalField(max_digits=12, decimal_places=2, default=0)  # readonly
otros_devengos = DecimalField(max_digits=12, decimal_places=2, default=0)

# ⚠️ DEDUCCIONES (porcentajes legales + descuentos en COP)
salud_empleado = DecimalField(max_digits=12, decimal_places=2)  # 4% - readonly
pension_empleado = DecimalField(max_digits=12, decimal_places=2)  # 4% - readonly
prestamos = DecimalField(max_digits=12, decimal_places=2, default=0)
descuentos_operativos = DecimalField(max_digits=12, decimal_places=2, default=0)

# Resultado
neto_pagar = DecimalField(max_digits=12, decimal_places=2)  # readonly - calculado en backend

# Estado
anulado = BooleanField(default=False)
observaciones = TextField(blank=True)
```

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
- Campos calculados (`salario_base`, `auxilio_transporte`, `salud_empleado`, `pension_empleado`, `neto_pagar`) son `readonly` en el serializer

---

## 5. Capa de Servicios (Service Layer)

### 5.1 Querysets Optimizados

**Ubicación:** `apps/tenant/empleados/services.py`

**Constantes de Campos (SSoT):**
```python
# ⚠️ v2.60: Campos explícitos como tuplas (PROHIBIDO __all__)
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

### 5.2 Cálculos de Nómina (Zero Trust)

**Función Principal:** `calcular_nomina_colombia()`

**Parámetros:**
```python
calcular_nomina_colombia(
    empleado_id,
    contrato_id,
    periodo_mes,
    fecha_pago,
    dias_laborados,
    otros_devengos,
    prestamos,
    descuentos_operativos,
    empresa_id  # ⚠️ Para validación Zero Trust
)
```

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

### 5.3 Validación de Solapamiento (Nómina Multitanda)

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
    
    return {
        'total_dias': total_dias_existentes,
        'nuevos_dias': nuevos_dias_decimal,
        'total_final': total_final_dias,
        'excede_limite': False
    }
```

---

## 6. API y ViewSets (Backend)

### 6.1 EmpleadoViewSet

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
   - ⚠️ Paso 4: Retorna respuesta con `was_updated: true` y `message`
   - Valida Zero Trust antes de actualizar
   - Listeners JS detectan `was_updated` para distinguir creación/actualización

5. **`DELETE /api/v1/empleados/{id}/`** - Eliminar
   - Solo si `estado == 'RETIRADO'` (Hard Delete)
   - Usa `eliminar_empleado_retirado()` del service layer

6. **`GET /api/v1/empleados/gestor-offcanvas/?tipo=empleado&id={id}`** - HTMX Offcanvas
   - ⚠️ Paso 4: Centraliza entrega de templates HTML para HTMX
   - Zero Trust: Usa `getattr(request.user, 'empresa', None)` y `get_object_or_404`
   - Retorna `TemplateResponse` con `empleado_offcanvas.html`
   - Si `id` está presente, carga datos del empleado
   - Soporta `tipo`: 'empleado', 'contrato', 'devengo'

7. **`GET /api/v1/empleados/{id}/historial-nominas/`** - Historial de Nóminas
   - Retorna `TemplateResponse` con `historial_nominas_offcanvas.html`
   - Filtra por `empresa_id` y `empleado_id` (Zero Trust)

8. **`GET /api/v1/empleados/summary/`** - Resumen de Nómina
   - Retorna estadísticas: total nómina mes, empleados activos, etc.

### 6.2 ContratoViewSet

**Endpoints Principales:**

1. **`GET /api/v1/empleados/contratos/`** - Listado
   - Filtra por `empresa_id`
   - Soporta `?empleado={id}` para filtrar por empleado

2. **`GET /api/v1/empleados/gestor-offcanvas/?tipo=contrato&empleado={id}`** - HTMX Offcanvas
   - ⚠️ Paso 4: Usa `gestor_offcanvas` centralizado en `EmpleadoViewSet`
   - Retorna `contrato_offcanvas.html`
   - Si `empleado` está presente, pre-carga datos del empleado
   - Si `id` está presente, carga datos del contrato existente

3. **`POST /api/v1/empleados/contratos/`** - Crear
   - Valida que solo haya UN contrato ACTIVO por empleado
   - Usa `gestionar_contrato_service()` del service layer

4. **`PATCH /api/v1/empleados/contratos/{id}/`** - Actualizar
   - ⚠️ Paso 4: Retorna respuesta con `was_updated: true` y `message`
   - Valida Zero Trust
   - Usa `perform_update()` con service layer

5. **`POST /api/v1/empleados/contratos/{id}/cancelar/`** - Cancelar Contrato
   - Cambia `estado` a INACTIVO y `activo` a False
   - Máquina de Estados: Deshabilita creación de nuevas nóminas

### 6.3 DevengoViewSet

**Endpoints Principales:**

1. **`GET /api/v1/empleados/devengos/`** - Listado
   - Filtra por `empresa_id`
   - Soporta `?empleado={id}` para filtrar por empleado
   - Retorna formato DRF: `{count, results}`

2. **`GET /api/v1/empleados/gestor-offcanvas/?tipo=devengo&id={id}`** - HTMX Offcanvas
   - ⚠️ Paso 4: Usa `gestor_offcanvas` centralizado en `EmpleadoViewSet`
   - Retorna `devengo_offcanvas.html`
   - Si `id` está presente, carga datos del devengo
   - Si `empleado` está presente, pre-carga datos del empleado y contrato ACTIVO

3. **`POST /api/v1/empleados/devengos/preview-calculo/`** - Pre-cálculo en Tiempo Real
   - ⚠️ Paso 4: Endpoint HTMX para cálculo en tiempo real
   - Zero Trust: Usa `getattr(request.user, 'empresa', None)`
   - Usa `calcular_nomina_colombia()` del service layer (SSoT)
   - Retorna `devengo_calculo_partial.html` en éxito
   - Retorna `devengo_calculo_error.html` en errores
   - Validaciones: contrato activo, días laborados (0.5-30), préstamos disponibles

4. **`POST /api/v1/empleados/devengos/`** - Crear Nómina
   - ⚠️ Paso 4: Retorna respuesta con `was_updated: false` y `message`
   - **Validación Preventiva de Duplicados:**
     ```python
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

## 7. Frontend: JavaScript y Templates

### 7.1 Estructura de JavaScript

**Archivos Principales (Feature-Sliced Architecture):**
- `apps/tenant/core/static/core/js/empleados/features/empleados_list.js` - Tabla principal
- `apps/tenant/core/static/core/js/empleados/features/empleados_editor.js` - CRUD empleados
- `apps/tenant/core/static/core/js/empleados/features/contratos_editor.js` - CRUD contratos
- `apps/tenant/core/static/core/js/empleados/features/devengos_editor.js` - CRUD nóminas
- `apps/tenant/core/static/core/js/empleados/features/historial_nominas.js` - Historial

**Dependencias Globales:**
- `TabulatorFactory` (tabulator.factory.js)
- `DOMUtils.onVisibleOnce()` (lazy loading)
- `window.http()` (http.js - Capa de Datos)
- `window.UIManager` (ui-manager.js - Error Boundary)
- `htmx` (para cargar offcanvas)

**Namespaces (Feature-Sliced Architecture):**
```javascript
// empleados_list.js
window.EmpleadosList = {
  table: table,
  refresh: function() { if (table) table.replaceData(); updateSummaryPanel(); },
  updateSummaryPanel: updateSummaryPanel,
  initEmpleadosTable: initEmpleadosTable,
  inicializarModulo: inicializarModulo
};

// empleados_editor.js
window.EmpleadosEditor = {
  openEmpleadoOffcanvas: openEmpleadoOffcanvas,
  eliminarEmpleado: eliminarEmpleado
};

// contratos_editor.js
window.ContratosEditor = {
  openContratoOffcanvas: openContratoOffcanvas
};

// devengos_editor.js
window.DevengosEditor = {
  openDevengoOffcanvas: openDevengoOffcanvas
};

// historial_nominas.js
window.HistorialNominas = {
  openHistorialNominas: openHistorialNominas,
  initHistorialNominas: initHistorialNominas,
  refresh: function() { if (historialTable) historialTable.replaceData(); }
};
```

### 7.2 Inicialización de Tabla (Tabulator Factory)

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

### 7.3 Event Delegation para Botones Dinámicos

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

---

## 8. Flujos CRUD Completos

### 8.1 Flujo: Crear Empleado

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

### 8.2 Flujo: Crear Contrato

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

### 8.3 Flujo: Crear Nómina

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
     - Valida duplicados (409 Conflict)
     - Valida solapamiento de días (400 Bad Request)
     - Calcula valores usando `calcular_nomina_colombia()`
     - Guarda en base de datos
   - Frontend: `htmx:afterOnLoad` (solo si `status === 201`) cierra offcanvas y refresca tabla

### 8.4 Flujo: Eliminar Nómina

**1. Usuario hace clic en "Eliminar" (desde historial de nóminas)**
   - JavaScript: Event delegation captura click en `.btn-eliminar-nomina-historial`
   - Confirmación: `confirm('¿Está seguro de que desea eliminar esta nómina?')`

**2. Usuario confirma**
   - JavaScript: `window.http('DELETE', '/api/v1/empleados/devengos/{id}/')`
   - Backend: `DevengoViewSet.destroy()`
     - Revierte préstamos al contrato (si aplica)
     - Elimina la nómina de la base de datos
     - Registra en log de auditoría
   - Frontend: Refresca tabla de historial y tabla principal

---

## 9. Flujo de Nóminas (Multitanda)

### 9.1 Concepto de Nómina Multitanda

**Problema Anterior:**
- Solo se permitía UNA nómina por empleado por mes (`unique_together = ['empleado', 'periodo_mes']`)

**Solución v2.60:**
- Permite múltiples nóminas en el mismo mes si `fecha_pago` es diferente
- Clave de unicidad: `['empleado', 'periodo_mes', 'fecha_pago']`
- Validación: La suma de `dias_laborados` en el mes no puede exceder 31 días

### 9.2 Cambios en el Modelo

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

### 9.3 Validación de Solapamiento

**Función:** `validar_limite_dias_mes()`

**Lógica:**
- Suma todos los `dias_laborados` del mes (excluyendo el registro actual si es update)
- Valida que el total no exceda 31 días
- Retorna `ValidationError` con detalles si excede

---

## 10. Historial de Nóminas

### 10.1 Endpoint Backend

**Método:** `EmpleadoViewSet.historial_nominas()`

```python
@action(detail=True, methods=["get"], renderer_classes=[TemplateHTMLRenderer, JSONRenderer], url_path="historial-nominas")
def historial_nominas(self, request, pk=None):
    """
    ⚠️ v2.60: Devuelve el HTML del historial de nóminas para un empleado específico (HTMX)
    o los datos JSON para Tabulator (paginación remota).
    """
    empresa = Empresa.objects.only('id').first()
    empleado_id = pk
    empleado = get_object_or_404(Empleado, pk=empleado_id, empresa_id=empresa.id)
    
    # Si es petición HTMX (Accept: text/html), retornar template
    if request.accepted_renderer.format == 'html':
        context = {'empleado': empleado, 'empleado_id': empleado_id}
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

### 10.2 Inicialización JavaScript

**Función:** `initHistorialNominas(empleadoId)`

**Características:**
- Anti-Zombies Pattern: Destruye instancia previa antes de crear nueva
- Event Delegation: Botones "Ver/Editar" y "Eliminar" manejados por event delegation
- Validación: Verifica que `empleadoId` sea válido antes de inicializar
- Integración con UIManager: Manejo de errores centralizado

---

## 11. Integración HTMX y Offcanvas

### 11.1 Arquitectura HTMX

**Principios:**
- **Sin Recargas de Página:** HTMX maneja todas las interacciones dinámicas
- **Partial Swapping:** Solo se actualiza el contenido necesario
- **Progressive Enhancement:** Funciona sin JavaScript (fallback)

### 11.2 Contenedores Offcanvas Globales

**Ubicación:** `apps/tenant/core/templates/tenant/core/workspace.html`

```html
{# Módulo Empleados - Contenedores Offcanvas globales #}
<div id="offcanvas-container-empleado"></div>
<div id="offcanvas-container-contrato"></div>
<div id="offcanvas-container-devengo"></div>
<div id="offcanvas-container-historial-nominas"></div>
```

**Razón:** Centralizar contenedores para evitar duplicación y asegurar consistencia.

### 11.3 Flujo HTMX: Cargar Offcanvas

**1. Usuario hace clic en botón de acción**
   - JavaScript: `htmx.ajax('GET', '/api/v1/empleados/gestor-offcanvas/?tipo={tipo}&id={id}', { target: '#offcanvas-container-{tipo}', swap: 'innerHTML' })`

**2. Backend retorna HTML del offcanvas**
   - ViewSet: `gestor_offcanvas()` retorna `TemplateResponse` con template correspondiente
   - Zero Trust: Valida `empresa_id` usando `get_object_or_404`

**3. HTMX reemplaza contenido del contenedor**
   - Swap: `innerHTML` (reemplaza todo el contenido)

**4. JavaScript muestra el offcanvas**
   - Bootstrap: `bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show()`

### 11.4 Flujo HTMX: Envío de Formularios (Paso 3)

**Templates Puramente Declarativos:**
- Formularios usan `hx-post` para crear y `hx-patch` para actualizar
- Error Boundary Pattern: `hx-on::htmx:response-error` apunta a `#form-{tipo}-feedback`
- Sin handlers de éxito en templates: Los listeners JS globales manejan el éxito

**Ejemplo (empleado_offcanvas.html):**
```html
<form id="form-empleado" method="POST" onsubmit="return false;"
      {% if empleado %}
      hx-patch="/api/v1/empleados/{{ empleado.id }}/"
      {% else %}
      hx-post="/api/v1/empleados/"
      {% endif %}
      hx-target="#grid-empleados" 
      hx-swap="none"
      hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'
      hx-on::htmx:response-error="window.UIManager && window.UIManager.handleError && window.UIManager.handleError(event.detail, '[empleado.offcanvas]', {errorContainerSelector: '#form-empleado-feedback'})">
    <div id="form-empleado-feedback" class="alert d-none" role="alert"></div>
    <!-- Campos del formulario -->
</form>
```

### 11.5 Listeners HTMX Globales (Feature-Sliced)

**Cada feature module tiene sus propios listeners:**

**`empleados_editor.js`:**
```javascript
d.addEventListener('htmx:afterOnLoad', function(event) {
    if (event.detail.path && event.detail.path.includes('/api/v1/empleados/') && 
        !event.detail.path.includes('/contratos/') && !event.detail.path.includes('/devengos/')) {
        const statusCode = event.detail.xhr?.status;
        if (statusCode === 201 || statusCode === 200) {
            // Cerrar offcanvas, mostrar mensaje, refrescar tabla
        }
    }
});
```

**`devengos_editor.js`:**
- Maneja errores 409 (Duplicado) y 400 (Días excedidos)
- NO cierra offcanvas en errores (permite corrección)
- Cierra offcanvas solo en éxito (201 Created)
- Refresca tabla principal y historial

### 11.6 Pre-cálculo en Tiempo Real (Nóminas)

**Inputs con HTMX triggers:**
- `periodo_mes`, `fecha_pago`, `dias_laborados`, `otros_devengos`, `prestamos`, `descuentos_operativos`

**Atributos HTMX:**
```html
hx-post="/api/v1/empleados/devengos/preview-calculo/"
hx-target="#devengo-campos-calculados, #devengo-deducciones-calculadas"
hx-swap="innerHTML"
hx-trigger="change, keyup changed delay:500ms, blur"
hx-include="#devengo-contrato-id, #devengo-dias_laborados, #devengo-otros_devengos, #devengo-prestamos, #devengo-descuentos_operativos, #devengo-periodo_mes, #devengo-fecha_pago"
hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'
hx-on::htmx:before-request="document.getElementById('devengo-campos-calculados').innerHTML = '';"
hx-on::htmx:response-error="window.UIManager && window.UIManager.handleError && window.UIManager.handleError(event.detail, '[devengo.offcanvas]', {errorContainerSelector: '#form-devengo-feedback'})"
```

**Backend (`preview_calculo`):**
- Usa `calcular_nomina_colombia()` del service layer
- Retorna `devengo_calculo_partial.html` con valores calculados
- Retorna `devengo_calculo_error.html` en errores

---

## 12. Validaciones y Zero Trust

### 12.1 Validación de Tenant (Zero Trust)

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

### 12.2 Validación de Cálculos (Zero Trust)

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

## 13. Manejo de Errores

### 13.1 Error Boundary Pattern

**Implementación:** `window.UIManager.handleError()`

**Uso en HTMX:**
```html
<form hx-post="/api/v1/empleados/devengos/" 
      hx-on::htmx:response-error="window.UIManager && window.UIManager.handleError && window.UIManager.handleError(event.detail, '[devengo.offcanvas]', {errorContainerSelector: '#form-devengo-feedback'})">
  <div id="form-devengo-feedback" class="alert d-none" role="alert"></div>
  <!-- ... campos del formulario ... -->
</form>
```

### 13.2 Tipos de Errores Manejados

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

### 13.3 Mensajes de Error Específicos

**Nómina Duplicada (409):**
- Mensaje: "Ya existe una nómina para este empleado, periodo y fecha de pago"
- Deshabilita botón "Guardar Nómina"
- Muestra enlace a "Ver Registro Existente"
- Marca campos `periodo_mes` y `fecha_pago` como inválidos

**Días Excedidos (400):**
- Mensaje: "La suma de días laborados excede los 31 días del mes"
- Muestra detalles: días registrados, días nuevos, total
- Marca campo `dias_laborados` como inválido

---

## 14. Historial de Cambios (Changelog)

### v2.60 - Feature-Sliced Architecture + HTMX Integration (2026-03-XX)

#### Cambios Principales:

1. **Migración a Feature-Sliced Architecture**
   - ✅ Eliminado `empleados.page.js` y `empleados.modals.js` (deprecated)
   - ✅ Creado directorio `features/` con módulos independientes:
     - `empleados_list.js` - Tabla principal, columnas, summary panel, event delegation
     - `empleados_editor.js` - CRUD empleados + listeners HTMX globales (`htmx:afterOnLoad`)
     - `contratos_editor.js` - CRUD contratos + listeners HTMX globales (`htmx:afterOnLoad`)
     - `devengos_editor.js` - CRUD nóminas + listeners HTMX (manejo 409/400, `htmx:afterOnLoad`)
     - `historial_nominas.js` - Historial + event delegation para botones dinámicos
   - ✅ Cada módulo expone métodos públicos en namespace global (`w.EmpleadosList`, `w.EmpleadosEditor`, etc.)
   - ✅ IIFE (Immediately Invoked Function Expression) para encapsulación
   - ✅ Orden de carga estricto en `assets_empleados.html` (sin `async`/`defer`)

2. **Integración HTMX Completa (Paso 3)**
   - ✅ Templates puramente declarativos: `hx-post` para crear, `hx-patch` para actualizar
   - ✅ Error Boundary Pattern: `hx-on::htmx:response-error` apunta a contenedores de feedback
   - ✅ Sin handlers de éxito en templates: Listeners JS globales manejan éxito
   - ✅ Pre-cálculo en tiempo real: Inputs con atributos HTMX para `preview-calculo`
   - ✅ Contenedores offcanvas globales en `workspace.html`

3. **Adaptación Backend (Paso 4)**
   - ✅ `gestor_offcanvas()` centralizado en `EmpleadoViewSet`:
     - Usa `getattr(request.user, 'empresa', None)` para Zero Trust
     - Usa `get_object_or_404` para simplificar obtención de objetos
     - Soporta `tipo`: 'empleado', 'contrato', 'devengo'
   - ✅ `preview_calculo()` en `DevengoViewSet`:
     - Endpoint HTMX para cálculo en tiempo real
     - Usa `calcular_nomina_colombia()` del service layer (SSoT)
     - Retorna partials HTML (`devengo_calculo_partial.html` / `devengo_calculo_error.html`)
   - ✅ Métodos `update()` y `partial_update()` en todos los ViewSets:
     - Retornan respuesta con `was_updated: true` y `message`
     - Permiten que listeners JS distingan entre creación/actualización
   - ✅ Métodos `create()` actualizados:
     - Retornan respuesta con `was_updated: false` y `message`

4. **Listeners HTMX Globales**
   - ✅ `empleados_editor.js`: Maneja éxito de empleados (cierra offcanvas, refresca tabla)
   - ✅ `contratos_editor.js`: Maneja éxito de contratos (cierra offcanvas, refresca tabla)
   - ✅ `devengos_editor.js`: Maneja éxito y errores de nóminas:
     - Errores 409 (Duplicado): NO cierra offcanvas, muestra mensaje específico
     - Errores 400 (Días excedidos): NO cierra offcanvas, muestra detalles
     - Éxito (201): Cierra offcanvas, refresca tablas, muestra mensaje

5. **Mejoras de UX**
   - ✅ Botones con spinner durante guardado (`hx-on::htmx:before-request`)
   - ✅ Offcanvas permanece abierto en errores para permitir corrección
   - ✅ Mensajes de éxito/error consistentes usando `SintelFeedback`
   - ✅ Refresh automático de tablas y summary panel después de operaciones exitosas

6. **Implementación de Nómina Multitanda**
   - Cambio de constraint de unicidad: `['empleado', 'periodo_mes', 'fecha_pago']`
   - Validación de solapamiento de días (máximo 31 días/mes)
   - Soporte para múltiples pagos por mes (semanas, quincenas)

7. **Corrección de Error `Decimal` en Eliminación**
   - Import agregado en método `destroy()`
   - Corrección de conversión de tipos para reversión de préstamos

8. **Historial de Nóminas con Event Delegation**
   - Botones "Ver/Editar" y "Eliminar" funcionales
   - Event delegation para botones dinámicos generados por Tabulator
   - Anti-Zombies Pattern implementado

9. **Mejoras en Manejo de Errores**
   - Error 409 Conflict (duplicados) con mensajes específicos
   - Error 400 Bad Request (días excedidos) con detalles
   - Función `reenableButton()` para re-habilitar botones después de corrección

10. **Cierre Condicional de Offcanvas**
   - Solo se cierra en éxito (201 Created)
   - Permanece abierto en errores para permitir corrección

11. **Anti-Zombies Pattern**
   - Implementado en todas las inicializaciones
   - Previene memory leaks y comportamientos inesperados

12. **Reversión de Préstamos**
   - Lógica implementada en `destroy()`
   - Mantiene integridad financiera al eliminar nóminas

13. **Corrección de URL Malformada**
   - Fix en `tabulator.factory.js` para manejar múltiples parámetros
   - Soporte correcto para paginación remota

14. **Validación de Solapamiento de Días**
    - Función `validar_limite_dias_mes()` en `services.py`
    - Validación Zero Trust en backend antes de guardar

### v2.95 (2024-12-XX) - Flujo Secuencial y Cálculos Proporcionales

#### Cambios Principales:

1. **Campo "Auxilio de Transporte" con Lógica Condicional**
   - Campos separados según método de pago
   - Cálculo automático desde contrato activo

2. **Corrección de Error 400 al Crear Devengo**
   - Campo `fecha_pago` agregado (requerido)
   - Serializer actualizado para campos editables

3. **Corrección de Botones en Columna de Acciones**
   - Event delegation mejorado
   - Manejo de clicks en iconos dentro de botones

4. **Botón Delete para Empleados RETIRADOS**
   - Eliminación definitiva solo para empleados retirados
   - Confirmación antes de eliminar

---

## 16. Checklist de Validación

### 16.1 Backend

- [x] **Modelos:**
  - [x] Todos los modelos tienen `empresa = ForeignKey(Empresa, on_delete=PROTECT)` con índice
  - [x] Constraints de unicidad correctamente definidos
  - [x] Validaciones en `clean()` para integridad de datos

- [x] **Services:**
  - [x] `LIST_FIELDS` y `DETAIL_FIELDS` definidos como tuplas (no `__all__`)
  - [x] Querysets optimizados con `.only()` y `select_related()`
  - [x] `calcular_nomina_colombia()` implementa normativa colombiana (46 horas semanales)
  - [x] `validar_limite_dias_mes()` valida solapamiento de días

- [x] **ViewSets:**
  - [x] `get_queryset()` filtra siempre por `empresa_id` (Zero Trust)
  - [x] `get_object()` usa querysets optimizados del service layer
  - [x] `list()` retorna formato DRF: `{count, results}`
  - [x] `gestor_offcanvas` retorna `TemplateResponse` con template correcto
  - [x] `create()` valida duplicados y solapamiento antes de guardar
  - [x] `destroy()` revierte préstamos al contrato antes de eliminar

- [x] **Serializers:**
  - [x] Heredan de `NormalizationMixin` para limpieza de datos
  - [x] Campos calculados marcados como `read_only=True`
  - [x] ForeignKeys validan pertenencia al tenant

### 16.2 Frontend

- [x] **Templates:**
  - [x] Todos los offcanvas tienen `{% csrf_token %}`
  - [x] Campos readonly tienen clase `bg-light` o atributo `readonly`
  - [x] Inputs de fecha tienen `type="date"` y formato correcto
  - [x] Inputs numéricos tienen `step="0.01"` para decimales
  - [x] Formularios usan `hx-post` para crear y `hx-patch` para actualizar
  - [x] Error Boundary Pattern: `hx-on::htmx:response-error` apunta a contenedores de feedback
  - [x] Pre-cálculo en tiempo real: Inputs con atributos HTMX para `preview-calculo`

- [x] **JavaScript (Feature-Sliced Architecture):**
  - [x] Módulos en `features/` con IIFE para encapsulación
  - [x] Namespaces globales expuestos correctamente:
    - `w.EmpleadosList` - Tabla principal y summary panel
    - `w.EmpleadosEditor` - CRUD empleados + listeners HTMX
    - `w.ContratosEditor` - CRUD contratos + listeners HTMX
    - `w.DevengosEditor` - CRUD nóminas + listeners HTMX (409/400)
    - `w.HistorialNominas` - Historial + event delegation
  - [x] `initEmpleadosTable()` usa `TabulatorFactory.create()`
  - [x] Lazy loading con `DOMUtils.onVisibleOnce()` y fallback `shown.bs.tab`
  - [x] Event delegation para botones dinámicos de Tabulator
  - [x] Anti-Zombies Pattern: Destruye instancias previas antes de crear nuevas
  - [x] `UIManager.handleError()` integrado en todos los flujos de error

- [x] **HTMX:**
  - [x] Todos los formularios tienen `hx-post` o `hx-patch`
  - [x] `hx-target` apunta a contenedores correctos
  - [x] `hx-swap` configurado correctamente (`innerHTML`, `none`, etc.)
  - [x] `hx-headers` incluye `X-CSRFToken`
  - [x] Listeners HTMX globales en cada feature module (`htmx:afterOnLoad`, `htmx:responseError`)
  - [x] Pre-cálculo en tiempo real con `hx-trigger="change, keyup changed delay:500ms, blur"`
  - [x] `hx-on::htmx:response-error` maneja errores con `UIManager`

### 16.3 Flujos CRUD

- [x] **Crear:**
  - [x] Offcanvas se carga correctamente vía HTMX
  - [x] Formulario envía datos al endpoint correcto
  - [x] Backend valida y crea registro
  - [x] Frontend cierra offcanvas y refresca tabla

- [x] **Leer:**
  - [x] Tabla Tabulator carga datos paginados correctamente
  - [x] Búsqueda funciona con `?search=`
  - [x] Botones de acción abren offcanvas correcto

- [x] **Actualizar:**
  - [x] Offcanvas carga datos existentes
  - [x] Formulario envía cambios al endpoint correcto
  - [x] Backend valida y actualiza registro
  - [x] Frontend cierra offcanvas y refresca tabla

- [x] **Eliminar:**
  - [x] Confirmación antes de eliminar
  - [x] Backend elimina registro y revierte préstamos (si aplica)
  - [x] Frontend refresca tabla después de eliminar

### 16.4 Nómina Multitanda

- [x] **Modelo:**
  - [x] `UniqueConstraint` incluye `fecha_pago` en la clave de unicidad
  - [x] Constraint tiene `condition=Q(anulado=False)`

- [x] **Validación:**
  - [x] `validar_limite_dias_mes()` verifica que la suma no exceda 31 días
  - [x] ViewSet llama a `validar_limite_dias_mes()` antes de crear

- [x] **Frontend:**
  - [x] Campo `fecha_pago` es obligatorio y parte del formulario
  - [x] Mensaje de error para duplicados incluye `fecha_pago`
  - [x] Mensaje de error para días excedidos muestra detalles

### 16.5 Historial de Nóminas

- [x] **Backend:**
  - [x] `historial_nominas` retorna template HTML para HTMX
  - [x] `historial_nominas` retorna JSON paginado para Tabulator
  - [x] Filtra por `empresa_id` y `empleado_id` (Zero Trust)

- [x] **Frontend:**
  - [x] Offcanvas se carga correctamente vía HTMX
  - [x] Tabla Tabulator se inicializa después de cargar offcanvas
  - [x] Botones "Ver/Editar" abren offcanvas de nómina
  - [x] Botones "Eliminar" envían petición DELETE y refrescan tabla

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
- [ ] Implementar reportes de nómina por periodo
- [ ] Agregar validación de límites de préstamos desde módulo de tesorería

---

**Documento generado automáticamente**  
**Última actualización:** 2026-03-XX (Feature-Sliced Architecture + HTMX Integration)  
**Versión del Módulo:** v2.60  
**Estado:** ✅ Producción - Completamente funcional
