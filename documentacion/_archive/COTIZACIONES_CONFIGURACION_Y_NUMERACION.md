# Documentación: Módulo de Cotizaciones - Configuración y Numeración Automática

**Versión:** SINTEL v2.40  
**Fecha:** 2026  
**Autor:** Sistema SINTEL

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Numeración Automática e Inmutable](#numeración-automática-e-inmutable)
3. [Módulo de Configuración de Cotizaciones](#módulo-de-configuración-de-cotizaciones)
4. [Integración con Editor Estilo Excel](#integración-con-editor-estilo-excel)
5. [API Reference](#api-reference)
6. [Flujos de Trabajo](#flujos-de-trabajo)
7. [Arquitectura Técnica](#arquitectura-técnica)
8. [Selección de Modelos Habilitados](#selección-de-modelos-habilitados)
9. [Changelog](#changelog)

## Documentación Relacionada

- **[Corrección de Deadlock en Editor](COTIZACIONES_EDITOR_DEADLOCK_CORRECCION.md)**: Documentación detallada sobre la corrección del deadlock en el Editor de Cotizaciones (v2.40)
- **[Implementación AIU](COTIZACIONES_AIU_IMPLEMENTACION.md)**: Documentación sobre el modo AIU (Administración, Imprevistos, Utilidad)
- **[Estructura Funcional](INFORME_ESTRUCTURA_FUNCIONAL_COTIZACIONES.md)**: Informe completo de la estructura funcional del módulo

---

## Resumen Ejecutivo

El módulo de Cotizaciones (SINTEL v2.40) implementa un sistema completo de gestión de cotizaciones con las siguientes características principales:

### Características Principales

1. **Numeración Automática e Inmutable**
   - Generación automática de números en formato `COT-XXXX-YYYY`
   - Inmutabilidad total después de la creación
   - Soporte opcional para numeración manual (configurable)

2. **Perfiles de Configuración (Sistema Multi-Perfil)**
   - Sistema de perfiles múltiples gestionables por empresa
   - CRUD completo de perfiles de configuración
   - Solo un perfil activo por empresa
   - Control de modelos de cotización habilitados por perfil
   - Aplicación automática de parámetros desde el perfil activo

3. **Editor Estilo Excel**
   - Interfaz tipo Excel con Tabulator
   - Soporte para pegar datos desde Excel (clipboard)
   - Celdas editables para cantidad y precio
   - Tres secciones: Dispositivos, Accesorios, Mano de Obra

4. **Inmutabilidad de Cotizaciones Aceptadas**
   - Bloqueo total de modificaciones para cotizaciones en estado `ACEPTADA`
   - Validación en múltiples capas (Modelo, Serializer, ViewSet)

---

## Numeración Automática e Inmutable

### Formato de Numeración

El sistema genera números de cotización automáticamente en el formato:

```
COT-XXXX-YYYY
```

Donde:
- `COT`: Prefijo fijo
- `XXXX`: Número secuencial con padding de 4 dígitos (ej: 0001, 0045, 0123)
- `YYYY`: Año actual (ej: 2026)

**Ejemplos:**
- `COT-0001-2026`
- `COT-0045-2026`
- `COT-0123-2026`

### Implementación

#### Service Layer

**Función:** `obtener_siguiente_numero_cotizacion(empresa_id: int) -> str`

```python
# apps/tenant/cotizaciones/services.py

def obtener_siguiente_numero_cotizacion(empresa_id: int) -> str:
    """
    Genera el siguiente número de cotización automático e inmutable.
    
    ⚠️ v2.40: Formato COT-XXXX-YYYY (ej: COT-0045-2026)
    - XXXX: Número secuencial con padding de 4 dígitos
    - YYYY: Año actual
    
    El número es generado automáticamente y nunca puede ser modificado después de creado.
    """
    año_actual = timezone.now().year
    
    # Buscar el último número de cotización (secuencia global)
    ultima_cotizacion = Cotizacion.objects.filter(
        empresa_id=empresa_id,
        numero__startswith='COT-'
    ).order_by('-numero').first()
    
    if ultima_cotizacion:
        # Extraer el número secuencial del formato COT-XXXX-YYYY
        partes = ultima_cotizacion.numero.split('-')
        if len(partes) >= 2:
            ultimo_numero = int(partes[1])  # XXXX es el segundo elemento
            siguiente_numero = ultimo_numero + 1
        else:
            siguiente_numero = 1
    else:
        siguiente_numero = 1
    
    # Formato: COT-XXXX-YYYY (ej: COT-0045-2026)
    return f"COT-{str(siguiente_numero).zfill(4)}-{año_actual}"
```

#### Serializers

**Bloqueo de Modificación:**

```python
# apps/tenant/cotizaciones/api/serializers.py

class CotizacionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        read_only_fields = ('id', 'numero', 'subtotal', 'iva_valor', 'total_neto', 'created_at')
    
    def validate(self, attrs):
        # ⚠️ BLOQUEO TOTAL: El número nunca puede ser modificado
        if 'numero' in attrs:
            raise serializers.ValidationError(
                _("El campo 'numero' es automático e inmutable. No puede ser modificado.")
            )
        return attrs
```

#### ViewSets

**Generación Automática en Creación:**

```python
# apps/tenant/cotizaciones/api/viewsets.py

def perform_create(self, serializer):
    # ⚠️ BLOQUEO: Eliminar 'numero' de los datos validados si existe
    if 'numero' in serializer.validated_data:
        del serializer.validated_data['numero']
    
    # Generar número automático e inmutable
    numero = obtener_siguiente_numero_cotizacion(empresa.id)
    serializer.save(empresa=empresa, numero=numero)

def perform_update(self, serializer):
    # ⚠️ BLOQUEO TOTAL: El número nunca puede ser modificado
    if 'numero' in serializer.validated_data:
        raise ValidationError("El campo 'numero' es automático e inmutable.")
    serializer.save()
```

#### Frontend

**Campo de Solo Lectura:**

```html
<!-- apps/tenant/core/templates/tenant/core/partials/cotizaciones/modal_editor.html -->

<div class="col-md-3 mb-3">
  <label for="cotizacion-numero" class="form-label">N.° Cotización</label>
  <input type="text" class="form-control bg-light" id="cotizacion-numero" name="numero" readonly disabled>
  <small class="form-text text-muted">Se generará automáticamente al guardar</small>
</div>
```

**Actualización después de Guardar:**

```javascript
// apps/tenant/core/static/core/js/cotizaciones/cotizacion_editor.js

const result = await response.json();

// Mostrar el número generado en el campo de solo lectura
const numeroInput = d.querySelector('#cotizacion-numero');
if (numeroInput && result.numero) {
  numeroInput.value = result.numero;
  numeroInput.classList.remove('bg-light');
  numeroInput.classList.add('bg-success', 'text-white', 'fw-bold');
}
```

### Reglas de Inmutabilidad

1. **Creación:** El número se genera automáticamente, nunca puede ser enviado desde el cliente
2. **Actualización:** Cualquier intento de modificar el número es bloqueado
3. **Estado ACEPTADA:** La cotización completa es inmutable (incluido el número)
4. **Validación Multi-capa:** Modelo, Serializer, ViewSet y Frontend

---

## Módulo de Configuración de Cotizaciones

### Perfiles de Configuración (Sistema Multi-Perfil)

**⚠️ v2.40:** El sistema de configuración evolucionó de un singleton a un sistema de **perfiles múltiples gestionables**, permitiendo crear y administrar múltiples perfiles de configuración por empresa.

### Modelo

**Ubicación:** `apps/tenant/cotizaciones/configuracion/models.py`

```python
class ConfiguracionCotizacion(models.Model):
    """
    Perfil de configuración de cotizaciones para una empresa.
    
    ⚠️ v2.40: SSoT Empresa - Múltiples perfiles por empresa.
    Cada perfil puede estar activo o inactivo.
    Los valores se aplican automáticamente a las cotizaciones que usen este perfil.
    """
    empresa = models.ForeignKey(Empresa, ...)  # Cambió de OneToOneField a ForeignKey
    
    # ⚠️ v2.40: Campos de gestión de perfiles
    nombre_configuracion = models.CharField(max_length=200, ...)
    tipo_plantilla = models.CharField(choices=TipoPlantilla.choices, default='MIXTO', ...)
    es_activo = models.BooleanField(default=False, ...)
    
    # ⚠️ v2.40: Modelos de Cotización Habilitados
    permitir_modelo_equipos = models.BooleanField(default=True, ...)
    permitir_modelo_materiales = models.BooleanField(default=True, ...)
    permitir_modelo_servicios = models.BooleanField(default=True, ...)
    permitir_modelo_mixto = models.BooleanField(default=True, ...)
    
    # Parámetros económicos (valores por defecto generales)
    porcentaje_utilidad_default = models.DecimalField(default=10.00, ...)
    iva_porcentaje_default = models.DecimalField(default=19.00, ...)
    
    # Parámetros de fechas
    dias_vencimiento_default = models.PositiveIntegerField(default=30, ...)
    
    # Configuración de numeración
    plantilla_numeracion = models.CharField(default='COT-XXXX-YYYY', ...)
    numero_manual_habilitado = models.BooleanField(default=False, ...)
    
    # Configuración de unidades y formato
    unidad_default = models.CharField(default='UND', ...)
    formato_moneda = models.CharField(default='COP', choices=[...])
    
    # Textos por defecto
    notas_comerciales_default = models.TextField(blank=True, null=True, ...)
    
    # ⚠️ v2.40: Parámetros por Modelo de Cotización
    porcentaje_utilidad_servicio = models.DecimalField(default=20.00, ...)
    iva_porcentaje_servicio = models.DecimalField(default=19.00, ...)
    porcentaje_utilidad_equipo = models.DecimalField(default=15.00, ...)
    iva_porcentaje_equipo = models.DecimalField(default=19.00, ...)
    porcentaje_utilidad_material = models.DecimalField(default=15.00, ...)
    iva_porcentaje_material = models.DecimalField(default=19.00, ...)
    porcentaje_utilidad_mixto = models.DecimalField(default=10.00, ...)
    iva_porcentaje_mixto = models.DecimalField(default=19.00, ...)
    
    # ⚠️ v2.40: Parámetros AIU (solo para SERVICIO y MATERIAL)
    aiu_admin_default = models.DecimalField(default=10.00, ...)
    aiu_imprevistos_default = models.DecimalField(default=5.00, ...)
    aiu_utilidad_default = models.DecimalField(default=10.00, ...)
```

### Campos Configurables

#### Campos de Gestión de Perfiles

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `nombre_configuracion` | String | - | Nombre descriptivo del perfil (ej: "Perfil Licitación AIU") |
| `tipo_plantilla` | String | 'MIXTO' | Tipo de plantilla (EQUIPO, MATERIAL, SERVICIO, MIXTO) |
| `es_activo` | Boolean | False | Si está activo, este perfil se usa por defecto para nuevas cotizaciones |

#### Modelos de Cotización Habilitados

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `permitir_modelo_equipos` | Boolean | True | Si está activo, el modelo "1.0 Equipos" estará disponible |
| `permitir_modelo_materiales` | Boolean | True | Si está activo, el modelo "2.0 Materiales" estará disponible |
| `permitir_modelo_servicios` | Boolean | True | Si está activo, el modelo "3.0 Servicios" estará disponible |
| `permitir_modelo_mixto` | Boolean | True | Si está activo, el modelo "Mixto" estará disponible |

**⚠️ Validación:** Al menos un modelo debe estar habilitado. No se permite desactivar todos los modelos.

#### Parámetros Generales

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `porcentaje_utilidad_default` | Decimal | 10.00 | Porcentaje de utilidad predeterminado (fallback) |
| `iva_porcentaje_default` | Decimal | 19.00 | Porcentaje de IVA predeterminado (fallback) |
| `dias_vencimiento_default` | Integer | 30 | Días desde emisión hasta vencimiento por defecto |
| `plantilla_numeracion` | String | 'COT-XXXX-YYYY' | Plantilla para generación automática de números |
| `numero_manual_habilitado` | Boolean | False | Permite ingresar manualmente el número de cotización |
| `unidad_default` | String | 'UND' | Unidad de medida predeterminada para nuevos ítems |
| `formato_moneda` | String | 'COP' | Formato de moneda predeterminado (COP/USD/EUR) |
| `notas_comerciales_default` | Text | '' | Texto que se incluirá automáticamente en todas las cotizaciones |

#### Parámetros por Modelo

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `porcentaje_utilidad_servicio` | Decimal | 20.00 | Utilidad por defecto para cotizaciones SERVICIO |
| `iva_porcentaje_servicio` | Decimal | 19.00 | IVA por defecto para cotizaciones SERVICIO |
| `porcentaje_utilidad_equipo` | Decimal | 15.00 | Utilidad por defecto para cotizaciones EQUIPO |
| `iva_porcentaje_equipo` | Decimal | 19.00 | IVA por defecto para cotizaciones EQUIPO |
| `porcentaje_utilidad_material` | Decimal | 15.00 | Utilidad por defecto para cotizaciones MATERIAL |
| `iva_porcentaje_material` | Decimal | 19.00 | IVA por defecto para cotizaciones MATERIAL |
| `porcentaje_utilidad_mixto` | Decimal | 10.00 | Utilidad por defecto para cotizaciones MIXTO |
| `iva_porcentaje_mixto` | Decimal | 19.00 | IVA por defecto para cotizaciones MIXTO |

#### Parámetros AIU

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `aiu_admin_default` | Decimal | 10.00 | % Administración por defecto (solo SERVICIO/MATERIAL) |
| `aiu_imprevistos_default` | Decimal | 5.00 | % Imprevistos por defecto (solo SERVICIO/MATERIAL) |
| `aiu_utilidad_default` | Decimal | 10.00 | % Utilidad por defecto (solo SERVICIO/MATERIAL) |

### Service Layer

**Función:** `get_configuracion_cotizacion(empresa_id: int, perfil_id: Optional[int] = None) -> ConfiguracionCotizacion`

```python
# apps/tenant/cotizaciones/services.py

def get_configuracion_cotizacion(
    empresa_id: int, 
    perfil_id: Optional[int] = None
) -> ConfiguracionCotizacion:
    """
    Obtiene un perfil de configuración de cotización para una empresa.
    
    ⚠️ v2.40: Catálogo de Perfiles - Múltiples perfiles por empresa.
    ⚠️ Zero Trust: Validación estricta de pertenencia al tenant.
    
    Args:
        empresa_id: ID de la empresa (SSoT)
        perfil_id: ID del perfil específico (opcional). Si se proporciona, busca ese perfil.
        
    Returns:
        ConfiguracionCotizacion: Perfil de configuración encontrado
        
    Raises:
        ConfiguracionNoEncontrada: Si no se encuentra ningún perfil (ni por ID ni activo)
        ValidationError: Si el perfil_id no pertenece a la empresa
    """
    # ⚠️ Zero Trust: Validar que la empresa existe
    empresa = Empresa.objects.only('id').get(pk=empresa_id)
    
    # Si se proporciona perfil_id, buscar ese específico
    if perfil_id is not None:
        config = ConfiguracionCotizacion.objects.filter(
            empresa_id=empresa_id,
            id=perfil_id
        ).first()
        
        if not config:
            raise ConfiguracionNoEncontrada(empresa_id, perfil_id)
        
        return config
    
    # Si no se proporciona perfil_id, buscar el último perfil activo
    config = ConfiguracionCotizacion.objects.filter(
        empresa_id=empresa_id,
        es_activo=True
    ).order_by('-updated_at').first()
    
    if not config:
        raise ConfiguracionNoEncontrada(empresa_id)
    
    return config
```

**⚠️ Cambios Importantes (v2.40):**

1. **Eliminado `get_or_create`**: Ya no crea perfiles automáticamente (evita `MultipleObjectsReturned`)
2. **Soporte para `perfil_id`**: Permite buscar un perfil específico
3. **Último activo por defecto**: Si no se especifica `perfil_id`, busca el último perfil activo ordenado por `updated_at`
4. **Excepción personalizada**: Lanza `ConfiguracionNoEncontrada` si no encuentra ningún perfil (obliga a crear perfiles explícitamente)
5. **Zero Trust**: Validación estricta de pertenencia al tenant y normalización de IDs

**Integración con `procesar_guardado_masivo()`:**

```python
# Aplicar días de vencimiento desde configuración
config = get_configuracion_cotizacion(empresa_id)
dias_vencimiento = config.dias_vencimiento_default if config else 30
fecha_vencimiento = fecha_emision + timedelta(days=dias_vencimiento)

# Aplicar IVA por defecto desde configuración
if not iva_porcentaje:
    iva_porcentaje = config.iva_porcentaje_default if config else Decimal('19.00')

# Aplicar porcentaje de utilidad por defecto a ítems
porcentaje_utilidad = config.porcentaje_utilidad_default if config else Decimal('10.00')

# Aplicar unidad por defecto a ítems
unidad = item_data.get('unidad') or (config.unidad_default if config else 'UND')

# Validar y usar número manual si está habilitado
if numero_manual and config and config.numero_manual_habilitado:
    if Cotizacion.objects.filter(empresa_id=empresa_id, numero=numero_manual).exists():
        return {"error": "numero_duplicado", ...}, 422
    numero = numero_manual
else:
    numero = obtener_siguiente_numero_cotizacion(empresa_id)
```

### API Endpoints

#### GET /api/v1/cotizaciones/configuracion/

**⚠️ v2.40:** Retorna una lista de perfiles de configuración (CRUD completo).

**Response (Lista):**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "empresa": 1,
      "empresa_nombre": "Mi Empresa S.A.",
      "nombre_configuracion": "Perfil Principal",
      "tipo_plantilla": "MIXTO",
      "tipo_plantilla_display": "Mixto",
      "es_activo": true,
      "permitir_modelo_equipos": true,
      "permitir_modelo_materiales": true,
      "permitir_modelo_servicios": true,
      "permitir_modelo_mixto": true,
      "porcentaje_utilidad_default": "10.00",
      "iva_porcentaje_default": "19.00",
      "created_at": "2026-01-15T10:00:00Z",
      "updated_at": "2026-01-15T10:00:00Z"
    },
    {
      "id": 2,
      "empresa": 1,
      "empresa_nombre": "Mi Empresa S.A.",
      "nombre_configuracion": "Perfil Licitación AIU",
      "tipo_plantilla": "SERVICIO",
      "tipo_plantilla_display": "Servicios",
      "es_activo": false,
      "permitir_modelo_equipos": false,
      "permitir_modelo_materiales": true,
      "permitir_modelo_servicios": true,
      "permitir_modelo_mixto": false,
      "porcentaje_utilidad_default": "20.00",
      "iva_porcentaje_default": "19.00",
      "created_at": "2026-01-16T10:00:00Z",
      "updated_at": "2026-01-16T10:00:00Z"
    }
  ]
}
```

#### GET /api/v1/cotizaciones/configuracion/{id}/

Obtiene el detalle completo de un perfil específico.

**Response:**
```json
{
  "id": 1,
  "empresa": 1,
  "empresa_nombre": "Mi Empresa S.A.",
  "nombre_configuracion": "Perfil Principal",
  "tipo_plantilla": "MIXTO",
  "tipo_plantilla_display": "Mixto",
  "es_activo": true,
  "permitir_modelo_equipos": true,
  "permitir_modelo_materiales": true,
  "permitir_modelo_servicios": true,
  "permitir_modelo_mixto": true,
  "porcentaje_utilidad_default": "10.00",
  "iva_porcentaje_default": "19.00",
  "dias_vencimiento_default": 30,
  "plantilla_numeracion": "COT-XXXX-YYYY",
  "numero_manual_habilitado": false,
  "unidad_default": "UND",
  "formato_moneda": "COP",
  "notas_comerciales_default": "",
  "porcentaje_utilidad_servicio": "20.00",
  "iva_porcentaje_servicio": "19.00",
  "porcentaje_utilidad_equipo": "15.00",
  "iva_porcentaje_equipo": "19.00",
  "porcentaje_utilidad_material": "15.00",
  "iva_porcentaje_material": "19.00",
  "porcentaje_utilidad_mixto": "10.00",
  "iva_porcentaje_mixto": "19.00",
  "aiu_admin_default": "10.00",
  "aiu_imprevistos_default": "5.00",
  "aiu_utilidad_default": "10.00",
  "created_at": "2026-01-15T10:00:00Z",
  "updated_at": "2026-01-15T10:00:00Z"
}
```

#### POST /api/v1/cotizaciones/configuracion/

Crea un nuevo perfil de configuración.

**Request Body:**
```json
{
  "nombre_configuracion": "Perfil Licitación AIU",
  "tipo_plantilla": "SERVICIO",
  "es_activo": false,
  "permitir_modelo_equipos": false,
  "permitir_modelo_materiales": true,
  "permitir_modelo_servicios": true,
  "permitir_modelo_mixto": false,
  "porcentaje_utilidad_default": "20.00",
  "iva_porcentaje_default": "19.00",
  "dias_vencimiento_default": 45,
  "plantilla_numeracion": "COT-XXXX-YYYY",
  "numero_manual_habilitado": false,
  "unidad_default": "UND",
  "formato_moneda": "COP",
  "notas_comerciales_default": "Condiciones comerciales estándar...",
  "aiu_admin_default": "10.00",
  "aiu_imprevistos_default": "5.00",
  "aiu_utilidad_default": "10.00"
}
```

**Response:** Detalle completo del perfil creado (mismo formato que GET /{id}/)

#### PATCH /api/v1/cotizaciones/configuracion/{id}/

Actualiza un perfil de configuración existente.

**Request Body:**
```json
{
  "nombre_configuracion": "Perfil Principal Actualizado",
  "permitir_modelo_servicios": false,
  "porcentaje_utilidad_default": "15.00"
}
```

**Response:** Detalle completo del perfil actualizado

#### POST /api/v1/cotizaciones/configuracion/{id}/activar/

Activa un perfil de configuración, desactivando automáticamente otros perfiles activos de la misma empresa.

**Response:**
```json
{
  "id": 2,
  "es_activo": true,
  "message": "Perfil activado exitosamente"
}
```

#### DELETE /api/v1/cotizaciones/configuracion/{id}/

Elimina un perfil de configuración.

**Response:** 204 No Content

### Frontend

#### Interfaz de Gestión de Perfiles

**Ubicación:** `apps/tenant/core/templates/tenant/core/partials/cotizaciones/modal_configuracion.html`

El sistema incluye dos modales principales:

1. **Modal "Ver Parámetros"** (`#modal-ver-parametros`):
   - Tabla Tabulator con lista de perfiles de configuración
   - Columnas: Nombre, Tipo, IVA, Utilidad, Estado Activo
   - Acciones: Ver, Editar, Activar, Eliminar
   - Botones: "Crear Perfil", "Refrescar Perfiles"
   - Búsqueda de perfiles

2. **Modal "Configurar Parámetros"** (`#modal-cotizacion-configuracion`):
   - Formulario completo para crear/editar perfiles
   - Secciones organizadas:
     - **Modelos de Cotización Habilitados**: Checkboxes para cada modelo
     - **Parámetros Económicos**: Utilidad e IVA
     - **Parámetros de Fechas**: Días de vencimiento
     - **Configuración de Numeración**: Plantilla y número manual
     - **Unidades y Formato**: Unidad y moneda
     - **Textos por Defecto**: Notas comerciales
   - Validación de rangos (0-100 para porcentajes, 1-365 para días)
   - Botones Guardar/Cancelar

#### JavaScript

**Cargar Lista de Perfiles:**

```javascript
// apps/tenant/core/static/core/js/cotizaciones/cotizaciones.page.js

async function cargarConfiguracion() {
  // Obtener listado de perfiles
  const response = await fetch('/api/v1/cotizaciones/configuracion/', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    credentials: 'include'
  });

  if (response.ok) {
    const data = await response.json();
    // Buscar perfil activo o usar el primero disponible
    let perfilActivo = null;
    if (data.results && Array.isArray(data.results)) {
      perfilActivo = data.results.find(p => p.es_activo) || data.results[0];
    }
    
    if (perfilActivo) {
      perfilActivoId = perfilActivo.id;
      configuracionActiva = perfilActivo; // ⚠️ v2.40: Almacenar para filtrar modelos
      
      // Cargar detalle completo del perfil
      const detailResponse = await fetch(`/api/v1/cotizaciones/configuracion/${perfilActivoId}/`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        credentials: 'include'
      });
      
      if (detailResponse.ok) {
        const detailData = await detailResponse.json();
        configuracionActiva = detailData;
        llenarFormularioConfiguracion(detailData);
      }
    }
  }
}
```

**Guardar Configuración (Crear o Actualizar):**

```javascript
async function guardarConfiguracion() {
  const formData = new FormData(form);
  
  const data = {
    nombre_configuracion: formData.get('nombre_configuracion') || 'Perfil Principal',
    tipo_plantilla: formData.get('tipo_plantilla') || 'MIXTO',
    es_activo: formData.get('es_activo') === 'on' || perfilActivoId === null,
    // ⚠️ v2.40: Modelos de Cotización Habilitados
    permitir_modelo_equipos: formData.get('permitir_modelo_equipos') === 'on',
    permitir_modelo_materiales: formData.get('permitir_modelo_materiales') === 'on',
    permitir_modelo_servicios: formData.get('permitir_modelo_servicios') === 'on',
    permitir_modelo_mixto: formData.get('permitir_modelo_mixto') === 'on',
    // ... otros campos
  };

  let url, method;
  if (perfilActivoId) {
    url = `/api/v1/cotizaciones/configuracion/${perfilActivoId}/`;
    method = 'PATCH';
  } else {
    url = '/api/v1/cotizaciones/configuracion/';
    method = 'POST';
  }

  const response = await fetch(url, {
    method: method,
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken') || '',
      'Accept': 'application/json'
    },
    credentials: 'include',
    body: JSON.stringify(data)
  });
}
```

**Filtrar Opciones de Modelo en "Nueva Cotización":**

```javascript
// ⚠️ v2.40: Función para filtrar opciones del selector de modelo_tipo según configuración
function filtrarOpcionesModeloTipo() {
  const selectorModeloTipo = d.querySelector('#cotizacion-modelo-tipo');
  if (!selectorModeloTipo || !configuracionActiva) return;
  
  // Obtener flags de modelos habilitados
  const permitirEquipos = configuracionActiva.permitir_modelo_equipos !== undefined 
    ? configuracionActiva.permitir_modelo_equipos : true;
  const permitirMateriales = configuracionActiva.permitir_modelo_materiales !== undefined 
    ? configuracionActiva.permitir_modelo_materiales : true;
  const permitirServicios = configuracionActiva.permitir_modelo_servicios !== undefined 
    ? configuracionActiva.permitir_modelo_servicios : true;
  const permitirMixto = configuracionActiva.permitir_modelo_mixto !== undefined 
    ? configuracionActiva.permitir_modelo_mixto : true;
  
  // Filtrar opciones según configuración
  Array.from(selectorModeloTipo.options).forEach(option => {
    const valor = option.value;
    let habilitado = true;
    
    switch (valor) {
      case 'EQUIPO': habilitado = permitirEquipos; break;
      case 'MATERIAL': habilitado = permitirMateriales; break;
      case 'SERVICIO': habilitado = permitirServicios; break;
      case 'MIXTO': habilitado = permitirMixto; break;
    }
    
    if (habilitado) {
      option.style.display = '';
      option.disabled = false;
    } else {
      option.style.display = 'none';
      option.disabled = true;
    }
  });
  
  // Si la opción seleccionada está deshabilitada, seleccionar la primera habilitada
  if (selectorModeloTipo.selectedOptions[0] && selectorModeloTipo.selectedOptions[0].disabled) {
    const primeraHabilitada = Array.from(selectorModeloTipo.options).find(opt => !opt.disabled && opt.value);
    if (primeraHabilitada) {
      selectorModeloTipo.value = primeraHabilitada.value;
    }
  }
}
```

---

## Integración con Editor Estilo Excel

### Carga de Configuración

El editor carga automáticamente la configuración al inicializar:

```javascript
// apps/tenant/core/static/core/js/cotizaciones/cotizacion_editor.js

async function cargarConfiguracion() {
  const response = await fetch(CONFIGURACION_API_URL, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken') || '',
      'Accept': 'application/json'
    },
    credentials: 'include'
  });

  if (response.ok) {
    configuracionGlobal = await response.json();
    aplicarConfiguracionAlFormulario();
  }
}
```

### Aplicación de Valores por Defecto

```javascript
function aplicarConfiguracionAlFormulario() {
  if (!configuracionGlobal) return;

  // Aplicar IVA por defecto
  const ivaInput = d.querySelector('#cotizacion-iva-porcentaje');
  if (ivaInput && configuracionGlobal.iva_porcentaje_default) {
    ivaInput.value = configuracionGlobal.iva_porcentaje_default;
  }

  // Aplicar fecha de vencimiento por defecto
  const fechaEmision = d.querySelector('#cotizacion-fecha-emision');
  const fechaVencimiento = d.querySelector('#cotizacion-fecha-vencimiento');
  if (fechaEmision && fechaVencimiento && configuracionGlobal.dias_vencimiento_default) {
    const fechaEmisionValue = fechaEmision.value;
    if (fechaEmisionValue) {
      const fecha = new Date(fechaEmisionValue);
      fecha.setDate(fecha.getDate() + configuracionGlobal.dias_vencimiento_default);
      fechaVencimiento.value = fecha.toISOString().split('T')[0];
    }
  }

  // Habilitar/deshabilitar número manual según configuración
  const numeroInput = d.querySelector('#cotizacion-numero');
  if (numeroInput) {
    if (configuracionGlobal.numero_manual_habilitado) {
      numeroInput.removeAttribute('readonly');
      numeroInput.removeAttribute('disabled');
      numeroInput.classList.remove('bg-light');
      numeroInput.classList.add('bg-white');
    } else {
      numeroInput.setAttribute('readonly', 'readonly');
      numeroInput.setAttribute('disabled', 'disabled');
      numeroInput.classList.remove('bg-white');
      numeroInput.classList.add('bg-light');
    }
  }
}
```

### Envío de Número Manual

Si el número manual está habilitado y el usuario lo proporciona:

```javascript
// Obtener número manual si está habilitado
let numeroManual = null;
const numeroInput = d.querySelector('#cotizacion-numero');
if (numeroInput && !numeroInput.hasAttribute('readonly') && numeroInput.value && numeroInput.value.trim()) {
  numeroManual = numeroInput.value.trim();
}

const payload = {
  cliente_id: parseInt(clienteId, 10),
  fecha_emision: ...,
  fecha_vencimiento: ...,
  iva_porcentaje: d.querySelector('#cotizacion-iva-porcentaje')?.value || (configuracionGlobal?.iva_porcentaje_default || '19.00'),
  items: items
};

// Agregar número manual si está habilitado y se proporcionó
if (numeroManual) {
  payload.numero = numeroManual;
}
```

---

## API Reference

### Endpoints de Configuración

#### GET /api/v1/cotizaciones/configuracion/

**⚠️ v2.40:** Retorna una lista paginada de perfiles de configuración (CRUD completo).

**Descripción:** Obtiene todos los perfiles de configuración de cotizaciones para la empresa actual.

**Método:** GET

**Autenticación:** Requerida (IsAuthenticated, IsCotizacionesConfigAllowed)

**Response 200 (Lista Paginada):**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "empresa": 1,
      "empresa_nombre": "Mi Empresa S.A.",
      "nombre_configuracion": "Perfil Principal",
      "tipo_plantilla": "MIXTO",
      "tipo_plantilla_display": "Mixto",
      "es_activo": true,
      "permitir_modelo_equipos": true,
      "permitir_modelo_materiales": true,
      "permitir_modelo_servicios": true,
      "permitir_modelo_mixto": true,
      "porcentaje_utilidad_default": "10.00",
      "iva_porcentaje_default": "19.00",
      "created_at": "2026-01-15T10:00:00Z",
      "updated_at": "2026-01-15T10:00:00Z"
    }
  ]
}
```

#### GET /api/v1/cotizaciones/configuracion/{id}/

**Descripción:** Obtiene el detalle completo de un perfil específico.

**Método:** GET

**Autenticación:** Requerida (IsAuthenticated, IsCotizacionesConfigAllowed)

**Response 200:** Ver formato completo en la sección "API Endpoints" anterior.

#### POST /api/v1/cotizaciones/configuracion/

**Descripción:** Crea un nuevo perfil de configuración.

**Método:** POST

**Autenticación:** Requerida (IsAuthenticated, IsCotizacionesConfigAllowed)

**Request Body:** Ver formato completo en la sección "API Endpoints" anterior.

#### PATCH /api/v1/cotizaciones/configuracion/{id}/

**Descripción:** Actualiza un perfil de configuración existente.

**Método:** PATCH

**Autenticación:** Requerida (IsAuthenticated, IsCotizacionesConfigAllowed)

**Request Body:**
```json
{
  "nombre_configuracion": "Perfil Principal Actualizado",
  "permitir_modelo_servicios": false,
  "permitir_modelo_equipos": true,
  "permitir_modelo_materiales": true,
  "permitir_modelo_mixto": true,
  "porcentaje_utilidad_default": "15.00",
  "iva_porcentaje_default": "19.00",
  "dias_vencimiento_default": 45
}
```

**Response:** Detalle completo del perfil actualizado

#### POST /api/v1/cotizaciones/configuracion/{id}/activar/

**Descripción:** Activa un perfil de configuración, desactivando automáticamente otros perfiles activos de la misma empresa.

**Método:** POST

**Autenticación:** Requerida (IsAuthenticated, IsCotizacionesConfigAllowed)

**Response:** Detalle completo del perfil activado

#### DELETE /api/v1/cotizaciones/configuracion/{id}/

**Descripción:** Elimina un perfil de configuración.

**Método:** DELETE

**Autenticación:** Requerida (IsAuthenticated, IsCotizacionesConfigAllowed)

**Response:** 204 No Content

**Response 200:** Mismo formato que GET

**Response 422 (Validación):**
```json
{
  "porcentaje_utilidad_default": ["El porcentaje de utilidad debe estar entre 0 y 100."],
  "dias_vencimiento_default": ["Los días de vencimiento deben estar entre 1 y 365."]
}
```

### Endpoints de Cotizaciones

#### POST /api/v1/cotizaciones/bulk-save/

**Descripción:** Crea una cotización con múltiples ítems desde el Editor Estilo Excel.

**Método:** POST

**Autenticación:** Requerida (IsAuthenticated, IsTenantMember)

**Request Body:**
```json
{
  "cliente_id": 1,
  "fecha_emision": "2026-01-15",
  "fecha_vencimiento": "2026-02-15",
  "atencion_a": "Juan Pérez",
  "asunto": "Propuesta de instalación",
  "iva_porcentaje": "19.00",
  "numero": "COT-0045-2026",  // Opcional, solo si numero_manual_habilitado = true
  "items": [
    {
      "descripcion": "Producto ejemplo",
      "cantidad": "10.00",
      "precio_unitario_venta": "1000.00",
      "marca": "CEB",
      "referencia": "REF-001",
      "unidad": "UND"
    }
  ]
}
```

**Response 201:**
```json
{
  "id": 1,
  "numero": "COT-0045-2026",
  "cliente_id": 1,
  "cliente_nombre": "Cliente Ejemplo S.A.",
  "fecha_emision": "2026-01-15",
  "fecha_vencimiento": "2026-02-15",
  "estado": "BORRADOR",
  "subtotal": "10000.00",
  "iva_porcentaje": "19.00",
  "iva_valor": "1900.00",
  "total_neto": "11900.00",
  "items_count": 1,
  "items": [...],
  "message": "Cotización creada exitosamente"
}
```

**Response 422 (Validación):**
```json
{
  "error": "numero_duplicado",
  "message": "El número de cotización 'COT-0045-2026' ya existe."
}
```

---

## Flujos de Trabajo

### Flujo 1: Gestionar Perfiles de Configuración

1. Usuario hace clic en "Ver Parámetros" en el toolbar de cotizaciones
2. Se abre el modal con tabla Tabulator de perfiles
3. El sistema carga la lista de perfiles de configuración
4. Usuario puede:
   - **Ver** detalles de un perfil
   - **Editar** un perfil existente
   - **Activar** un perfil (desactiva automáticamente otros)
   - **Eliminar** un perfil
   - **Crear** un nuevo perfil
5. Al hacer clic en "Crear Perfil" o "Editar":
   - Se abre el modal de configuración con formulario completo
   - Usuario configura:
     - Nombre del perfil
     - Tipo de plantilla
     - Modelos de cotización habilitados (checkboxes)
     - Parámetros económicos, fechas, numeración, etc.
   - Usuario hace clic en "Guardar Perfil"
6. El sistema valida que al menos un modelo esté habilitado
7. El sistema crea/actualiza el perfil en la base de datos
8. Se muestra notificación de éxito
9. El modal se cierra y la tabla se actualiza

### Flujo 1.1: Seleccionar Modelos Habilitados

1. Usuario abre el modal de configuración (crear o editar perfil)
2. En la sección "Modelos de Cotización Habilitados":
   - Usuario activa/desactiva checkboxes para cada modelo
   - El sistema valida que al menos un modelo esté habilitado
3. Al guardar:
   - Los modelos deshabilitados no aparecerán en el selector de "Nueva Cotización"
   - Solo los modelos habilitados estarán disponibles para crear cotizaciones

### Flujo 2: Crear Cotización con Valores por Defecto

1. Usuario hace clic en "Nueva Cotización"
2. **⚠️ v2.40:** El sistema carga la configuración activa (perfil con `es_activo=True`)
3. **⚠️ v2.40:** El sistema filtra las opciones del selector de modelo_tipo según `permitir_modelo_*`:
   - Solo muestra opciones habilitadas en la configuración activa
   - Oculta opciones deshabilitadas
   - Selecciona automáticamente la primera opción habilitada
4. Se abre el modal del Editor Estilo Excel
5. Se aplican automáticamente valores desde el perfil activo:
   - IVA por defecto (según modelo seleccionado o fallback)
   - Utilidad por defecto (según modelo seleccionado o fallback)
   - Fecha de vencimiento calculada desde días de vencimiento
   - Habilitación/deshabilitación del campo número según configuración
6. Usuario completa el formulario y agrega ítems
7. Si `numero_manual_habilitado = true`, usuario puede ingresar número personalizado
8. Usuario hace clic en "Guardar Cotización"
9. El sistema:
   - Valida el número manual (si se proporcionó) contra duplicados
   - Genera número automático si no hay número manual
   - Aplica valores por defecto desde configuración a ítems (utilidad, unidad)
   - Crea la cotización y sus ítems
10. Se muestra el número generado en el campo de solo lectura
11. Se muestra notificación de éxito

### Flujo 3: Numeración Automática

1. Usuario crea una nueva cotización
2. El sistema busca la última cotización con formato `COT-XXXX-YYYY`
3. Extrae el número secuencial (XXXX)
4. Incrementa el número en 1
5. Genera el nuevo número: `COT-XXXX-YYYY`
6. Persiste el número en la base de datos
7. El número nunca puede ser modificado después

### Flujo 4: Numeración Manual (si está habilitada)

1. Usuario configura `numero_manual_habilitado = true`
2. Al crear nueva cotización, el campo número se habilita para edición
3. Usuario ingresa número personalizado (ej: "COT-9999-2026")
4. Al guardar, el sistema valida que el número no exista
5. Si existe, retorna error 422
6. Si no existe, usa el número manual en lugar del automático
7. El número manual también es inmutable después de creado

---

## Arquitectura Técnica

### Estructura de Archivos

```
apps/tenant/cotizaciones/
├── configuracion/
│   ├── __init__.py
│   ├── models.py              # ConfiguracionCotizacion
│   ├── serializers.py         # ConfiguracionCotizacionSerializer
│   └── viewsets.py            # ConfiguracionCotizacionViewSet
├── api/
│   ├── urls.py                # Incluye ruta de configuración
│   ├── serializers.py         # Serializers de Cotizacion
│   └── viewsets.py            # ViewSets de Cotizacion
├── models.py                  # Cotizacion, CotizacionItem, Producto
├── services.py                # Lógica de negocio
└── admin.py                   # Admin de todos los modelos

apps/tenant/core/
├── templates/tenant/core/partials/cotizaciones/
│   ├── list.html              # Lista de cotizaciones
│   ├── modal_editor.html      # Editor Estilo Excel
│   └── modal_configuracion.html  # Modal de configuración
└── static/core/js/cotizaciones/
    ├── cotizaciones.page.js   # Lógica de lista y configuración
    └── cotizacion_editor.js   # Lógica del editor
```

### Principios de Diseño

1. **SSoT (Single Source of Truth):**
   - Múltiples perfiles de configuración por empresa
   - Relación `ForeignKey` con `Empresa`
   - Solo un perfil activo por empresa (`es_activo=True`)

2. **Service Layer Pattern:**
   - Toda la lógica de negocio en `services.py`
   - ViewSets solo orquestan llamadas al service layer

3. **Inmutabilidad:**
   - Números de cotización nunca pueden ser modificados
   - Cotizaciones ACEPTADAS son completamente inmutables

4. **Configuración Centralizada:**
   - Valores por defecto en perfiles gestionables
   - Aplicación automática desde el perfil activo
   - Parámetros específicos por modelo de cotización

5. **Validación Multi-capa:**
   - Modelo: Validaciones de campo (al menos un modelo habilitado)
   - Serializer: Validaciones de negocio (AIU solo SERVICIO/MATERIAL)
   - ViewSet: Validaciones de permisos y estado
   - Frontend: Validaciones de UX y filtrado dinámico

6. **Control de Modelos Habilitados:**
   - Los perfiles controlan qué modelos están disponibles
   - Filtrado dinámico en el selector de "Nueva Cotización"
   - Validación: al menos un modelo debe estar habilitado

### Dependencias

- **Django:** Framework base
- **Django REST Framework:** API REST
- **Tabulator:** Editor estilo Excel en frontend
- **Bootstrap 5:** UI components
- **Notyf:** Notificaciones toast

---

## Notas de Implementación

### Migraciones

Después de crear el modelo `ConfiguracionCotizacion`, ejecutar:

```bash
python manage.py makemigrations cotizaciones
python manage.py migrate cotizaciones
```

### Valores por Defecto

Si no existe configuración, el sistema usa estos valores hardcodeados:

- `porcentaje_utilidad_default`: 10.00
- `iva_porcentaje_default`: 19.00
- `dias_vencimiento_default`: 30
- `plantilla_numeracion`: 'COT-XXXX-YYYY'
- `numero_manual_habilitado`: False
- `unidad_default`: 'UND'
- `formato_moneda`: 'COP'
- `notas_comerciales_default`: ''

### Consideraciones de Rendimiento

1. **Cache de Configuración:**
   - La configuración se carga una vez al inicializar el editor
   - Se almacena en variable `configuracionGlobal` para evitar múltiples requests

2. **Query Optimization:**
   - Uso de `select_related('empresa')` en queries de configuración
   - Uso de `.only('id')` para obtener empresa singleton

3. **Validación de Número Duplicado:**
   - Solo se valida si `numero_manual_habilitado = true` y se proporciona número manual
   - La validación es atómica dentro de una transacción

---

## Selección de Modelos Habilitados

### Funcionalidad

**⚠️ v2.40:** Los perfiles de configuración permiten controlar qué tipos de modelos de cotización estarán disponibles para crear nuevas cotizaciones.

### Implementación

1. **Campos en el Modelo:**
   - `permitir_modelo_equipos` (Boolean, default: True)
   - `permitir_modelo_materiales` (Boolean, default: True)
   - `permitir_modelo_servicios` (Boolean, default: True)
   - `permitir_modelo_mixto` (Boolean, default: True)

2. **Validación:**
   - Backend: El modelo valida que al menos un modelo esté habilitado
   - Frontend: Validación implícita (no permite desactivar todos)

3. **Filtrado Dinámico:**
   - Al hacer clic en "Nueva Cotización", el sistema consulta el perfil activo
   - Filtra las opciones del selector `#cotizacion-modelo-tipo`
   - Solo muestra opciones con `permitir_modelo_* = true`
   - Oculta y deshabilita opciones con `permitir_modelo_* = false`

### Ejemplo de Uso

**Escenario:** Empresa que solo trabaja con servicios y materiales.

1. Usuario configura perfil activo:
   - `permitir_modelo_equipos = false`
   - `permitir_modelo_materiales = true`
   - `permitir_modelo_servicios = true`
   - `permitir_modelo_mixto = false`

2. Al hacer clic en "Nueva Cotización":
   - El selector de modelo_tipo solo muestra: "Materiales" y "Servicios"
   - Las opciones "Equipos" y "Mixto" están ocultas y deshabilitadas

3. Usuario solo puede crear cotizaciones de tipo MATERIAL o SERVICIO

---

## Changelog

### v2.40 (2026-02-XX) - Zero Trust + Corrección MultipleObjectsReturned

**Correcciones Críticas:**
- ✅ **Corrección de error `MultipleObjectsReturned`**: Eliminado `get_or_create` que causaba conflictos con múltiples perfiles
- ✅ **Refactorización de `get_configuracion_cotizacion`**: Ahora acepta `perfil_id` opcional y busca último activo si no se especifica
- ✅ **Excepción personalizada `ConfiguracionNoEncontrada`**: Implementada para manejo de errores cuando no se encuentra configuración
- ✅ **Zero Trust aplicado**: Normalización y validación estricta en obtención de configuración
- ✅ **Soporte para `perfil_id`**: Funciones `get_configuracion_cotizacion` y `get_configuracion_por_modelo` aceptan `perfil_id` opcional

**Mejoras de Seguridad:**
- ✅ Validación estricta de pertenencia al tenant (empresa_id)
- ✅ Normalización de IDs antes de usar (validación de enteros positivos)
- ✅ Normalización de valores Decimal (no strings/floats)
- ✅ Manejo de excepciones claro (no crea perfiles automáticamente)

**Cambios Técnicos:**
- `get_configuracion_cotizacion(empresa_id, perfil_id=None)`: Busca perfil específico o último activo
- `get_configuracion_por_modelo(empresa_id, modelo_tipo, perfil_id=None)`: Acepta `perfil_id` y normaliza valores Decimal
- `procesar_guardado_masivo()`: Normaliza `configuracion_id` y maneja `ConfiguracionNoEncontrada`

### v2.40 (2026-02-17) - Corrección de Deadlock en Editor

**Correcciones Críticas:**
- ✅ **Corrección de Deadlock en Editor de Cotizaciones**
  - Eliminado deadlock en inicialización de tablas Tabulator
  - Resolución inmediata de promesas en `initTable()` (sin esperar `tableBuilt`)
  - Eliminada clonación de botones que rompía estado de Bootstrap
  - Habilitación prioritaria de botones "Agregar Fila"
  - Guardias en `actualizarPanelTotales()` para tablas ocultas
  - Verificaciones simplificadas (solo métodos, no `initialized`)
  - **Documentación:** Ver `COTIZACIONES_EDITOR_DEADLOCK_CORRECCION.md`

**Nuevas Funcionalidades:**
- ✅ Sistema de perfiles múltiples de configuración (CRUD completo)
- ✅ Selección de modelos de cotización habilitados por perfil
- ✅ Filtrado dinámico de opciones en "Nueva Cotización"
- ✅ Tabla Tabulator para gestión de perfiles
- ✅ Acción "Activar" para cambiar perfil activo
- ✅ Parámetros específicos por modelo de cotización
- ✅ Parámetros AIU configurables por perfil

**Cambios Arquitectónicos:**
- `ConfiguracionCotizacion.empresa`: Cambió de `OneToOneField` a `ForeignKey`
- Agregados campos `permitir_modelo_*` para control de modelos disponibles
- Agregados campos de parámetros por modelo (utilidad e IVA específicos)
- Agregados campos de parámetros AIU (solo para SERVICIO y MATERIAL)

**Validaciones:**
- Al menos un modelo debe estar habilitado por perfil
- AIU solo válido para perfiles de tipo SERVICIO o MATERIAL
- Solo un perfil activo por empresa

### v2.40 (2026-01-15)

- ✅ Implementación de numeración automática e inmutable
- ✅ Creación del módulo de configuración de cotizaciones
- ✅ Integración con Editor Estilo Excel
- ✅ Soporte para numeración manual (opcional)
- ✅ Aplicación automática de valores por defecto
- ✅ Validación multi-capa de inmutabilidad

---

**Fin del Documento**
