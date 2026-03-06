# Análisis: Función del Módulo `configuracion` en Arquitectura "DNA Dinámico" v2.40

## 🎯 Función Principal

El módulo `apps/tenant/cotizaciones/configuracion/` actúa como **"Catálogo de Plantillas de Configuración"** que permite definir perfiles reutilizables con valores pre-configurados para crear cotizaciones.

## 📋 Propósito en la Arquitectura Actual

### 1. **Almacenamiento de Plantillas Reutilizables**

El modelo `ConfiguracionCotizacion` almacena **perfiles de configuración** que contienen:

#### Parámetros Económicos por Tipo de Modelo:
- **Utilidad por defecto**: Diferentes porcentajes según el tipo (SERVICIO: 20%, EQUIPO: 15%, MATERIAL: 10%, MIXTO: 12%)
- **IVA por defecto**: Diferentes porcentajes según el tipo (típicamente 19% para Colombia)
- **Parámetros AIU** (Administración, Imprevistos, Utilidad): Valores por defecto para cotizaciones AIU

#### Configuración Operativa:
- **Días de vencimiento por defecto**: Número de días desde emisión hasta vencimiento
- **Plantilla de numeración**: Formato para generación automática de números (ej: COT-XXXX-YYYY)
- **Número manual habilitado**: Permite ingresar números manualmente
- **Unidad por defecto**: Unidad de medida predeterminada (ej: UND, MT)
- **Formato de moneda**: COP, USD, EUR

#### Control de Modelos Disponibles:
- **permitir_modelo_equipos**: Controla si el modelo "1.0 Equipos" está disponible
- **permitir_modelo_materiales**: Controla si el modelo "2.0 Materiales" está disponible
- **permitir_modelo_servicios**: Controla si el modelo "3.0 Servicios" está disponible
- **permitir_modelo_mixto**: Controla si el modelo "Mixto" está disponible

#### Textos por Defecto:
- **notas_comerciales_default**: Texto que se incluye automáticamente en todas las cotizaciones

### 2. **Integración con "DNA Dinámico" v2.40**

#### En el Modelo `Cotizacion`:
```python
plantilla = models.ForeignKey(
    'tenant_cotizaciones.ConfiguracionCotizacion',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='cotizaciones'
)
```

**Función**: Asocia una cotización con un perfil de configuración específico que pre-cargó sus valores.

#### En el Endpoint `preforma` (Fase A):
```python
POST /api/v1/cotizaciones/preforma/
{
    "cliente_id": 1,
    "tipo_cotizacion": "PRODUCTOS",
    "plantilla_id": 1  # Opcional
}
```

**Función**: Si se proporciona `plantilla_id`, el endpoint pre-carga:
- Valores de AIU desde `plantilla.aiu_admin_default`, `aiu_imprevistos_default`, `aiu_utilidad_default`
- IVA desde `get_configuracion_por_modelo()` que lee los valores específicos del modelo desde la plantilla
- Días de vencimiento desde `plantilla.dias_vencimiento_default`

#### En el Servicio `procesar_guardado_masivo`:
```python
configuracion_id = request.data.get('configuracion_id')
config = get_configuracion_cotizacion(empresa_id, perfil_id=configuracion_id)
```

**Función**: Obtiene el perfil de configuración seleccionado para aplicar sus valores por defecto durante el guardado masivo.

### 3. **Flujo de Uso en "DNA Dinámico" v2.40**

```
1. Usuario crea/edita Perfil de Configuración
   └─> ConfiguracionCotizacionViewSet (CRUD completo)
       └─> Define valores por defecto para cada tipo de modelo

2. Usuario inicia creación de Cotización (Fase A)
   └─> Modal de Configuración Inicial
       └─> Selecciona: Cliente, Tipo de Cotización, Plantilla (opcional)
           └─> POST /api/v1/cotizaciones/preforma/
               └─> Si plantilla_id existe:
                   ├─> Pre-carga AIU desde plantilla
                   ├─> Pre-carga IVA desde plantilla (según modelo)
                   └─> Pre-carga días de vencimiento

3. Usuario guarda Cotización
   └─> POST /api/v1/cotizaciones/bulk-save/
       └─> Si configuracion_id existe:
           ├─> Obtiene perfil: get_configuracion_cotizacion()
           ├─> Obtiene valores por modelo: get_configuracion_por_modelo()
           └─> Aplica valores por defecto si no se proporcionaron

4. Cotización guardada
   └─> Campo `plantilla` (ForeignKey) almacena referencia al perfil usado
       └─> Inmutable una vez guardada (no puede cambiarse si estado=ACEPTADA)
```

## 🔗 Relación con Otros Componentes

### 1. **Service Layer (`services.py`)**
- `get_configuracion_cotizacion()`: Obtiene un perfil específico o el último activo
- `get_configuracion_por_modelo()`: Extrae valores de utilidad e IVA según el tipo de modelo desde el perfil
- `qs_configuracion_list()` / `qs_configuracion_detail()`: QuerySets optimizados

### 2. **ViewSet Principal (`api/viewsets.py`)**
- Endpoint `preforma`: Usa plantilla para pre-cargar valores
- Endpoint `bulk_save`: Usa `configuracion_id` para obtener valores por defecto
- Endpoint `configuracion-por-modelo`: Retorna configuración específica para un modelo

### 3. **PDF Service (`pdf_service.py`)**
- Usa `perfil_configuracion` para determinar qué secciones mostrar en el PDF
- Controla visibilidad de secciones según `permitir_modelo_*`

## ✅ Estado Actual en "DNA Dinámico" v2.40

### ✅ Correctamente Integrado:
- ✅ Modelo `ConfiguracionCotizacion` existe y está completo
- ✅ ViewSet `ConfiguracionCotizacionViewSet` con CRUD completo
- ✅ Serializers optimizados (List/Detail)
- ✅ Integración con endpoint `preforma` (Fase A)
- ✅ Integración con `procesar_guardado_masivo`
- ✅ Campo `plantilla` en modelo `Cotizacion` (ForeignKey)
- ✅ Inmutabilidad de `plantilla_id` en cotizaciones ACEPTADAS

### ⚠️ Pendiente de Implementación:
- ⏳ Migración de base de datos para campo `plantilla` en `Cotizacion`
- ⏳ Frontend: Modal de "Configuración Inicial" que permita seleccionar plantilla
- ⏳ Frontend: UI para gestionar perfiles de configuración (CRUD)

## 🎯 Conclusión

El módulo `configuracion` es **esencial** para la arquitectura "DNA Dinámico" v2.40 porque:

1. **Centraliza la configuración**: Permite definir valores por defecto una vez y reutilizarlos
2. **Facilita la creación**: Pre-carga valores en la Fase A (preforma) para acelerar el proceso
3. **Mantiene consistencia**: Asegura que todas las cotizaciones de un tipo usen los mismos parámetros
4. **Flexibilidad**: Múltiples perfiles permiten diferentes configuraciones según el contexto (ej: "Perfil Licitación AIU", "Perfil Venta Equipos Directa")
5. **Trazabilidad**: El campo `plantilla` en `Cotizacion` permite saber qué perfil se usó para crear cada cotización

**No debe eliminarse** - Es parte fundamental del "DNA Dinámico" v2.40.
