# Resumen de Implementación: DNA Dinámico y Fase A (Cotizaciones v2.40)

## ✅ Cambios Implementados

### 1. Modelo `Cotizacion` (`apps/tenant/cotizaciones/models.py`)

#### Campos Añadidos:
- ✅ **`plantilla`**: ForeignKey a `ConfiguracionCotizacion` (nullable)
  - Permite asociar una cotización con un perfil de configuración
  - Pre-carga valores de AIU e IVA desde la plantilla
  
- ✅ **`secciones_activas`**: JSONField (default=dict)
  - Almacena qué secciones del editor están habilitadas
  - Estructura: `{"equipos_dispositivos": bool, "accesorios_materiales": bool, "mano_obra_instalacion": bool}`

#### Métodos Añadidos:
- ✅ **`get_tipo_cotizacion()`**: Mapea `modelo_tipo` a `tipo_cotizacion` para compatibilidad con frontend
  - EQUIPO → PRODUCTOS
  - SERVICIO → SERVICIOS
  - MATERIAL → MATERIALES
  - MIXTO → MIXTO

- ✅ **`get_secciones_activas_default()`**: Obtiene secciones activas por defecto según `modelo_tipo`

#### Validaciones Añadidas:
- ✅ Inmutabilidad de `plantilla_id` (no puede cambiarse si estado=ACEPTADA)
- ✅ Inmutabilidad de `secciones_activas` (no puede cambiarse si estado=ACEPTADA)
- ✅ Validación de que `secciones_activas` tenga al menos una sección activa

### 2. Serializers (`apps/tenant/cotizaciones/api/serializers.py`)

#### Campos Añadidos a Serializers:
- ✅ `plantilla` y `secciones_activas` añadidos a `CotizacionDetailSerializer`
- ✅ `plantilla` y `secciones_activas` añadidos a `CotizacionCreateSerializer`

#### Validaciones Añadidas:
- ✅ Validación de inmutabilidad de `plantilla` y `secciones_activas` en `validate()`
- ✅ Validación de que `secciones_activas` tenga al menos una sección activa

### 3. ViewSet (`apps/tenant/cotizaciones/api/viewsets.py`)

#### Endpoint Añadido:
- ✅ **`POST /api/v1/cotizaciones/preforma/`**: Crea una preforma de cotización (Fase A)
  - Recibe: `cliente_id`, `tipo_cotizacion` (PRODUCTOS, SERVICIOS, MATERIALES, MIXTO), `plantilla_id` (opcional)
  - Mapea `tipo_cotizacion` a `modelo_tipo`
  - Pre-carga valores de AIU e IVA desde plantilla si se proporciona
  - Genera número automático y fechas por defecto
  - Retorna datos de preforma sin guardar en BD

## ⚠️ Pendiente: Migración de Base de Datos

### Problema Actual:
La referencia lazy al modelo `ConfiguracionCotizacion` requiere ajuste. El modelo está en `apps/tenant/cotizaciones/configuracion/models.py` pero Django lo registra bajo la app `apps.tenant.cotizaciones` con label `tenant_cotizaciones`.

### Solución Propuesta:
1. **Opción 1 (Recomendada)**: Usar importación directa en lugar de referencia lazy:
   ```python
   from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion
   
   plantilla = models.ForeignKey(
       ConfiguracionCotizacion,
       on_delete=models.SET_NULL,
       ...
   )
   ```

2. **Opción 2**: Verificar si `ConfiguracionCotizacion` está correctamente registrado en `configuracion/models.py` y usar el label correcto.

### Migración de Datos:
Una vez resuelto el problema de referencia, crear migración de datos que:
1. Poblar `secciones_activas` para cotizaciones existentes según `modelo_tipo`
2. Asociar `plantilla_id` con el último perfil activo de cada empresa (o null si no existe)

## 📋 Próximos Pasos

1. ✅ Resolver referencia lazy a `ConfiguracionCotizacion`
2. ✅ Crear migración de schema
3. ✅ Crear migración de datos
4. ⏳ Crear modal de Configuración Inicial (Frontend)
5. ⏳ Actualizar editor de cotizaciones para usar `secciones_activas`

## 🎯 Decisiones de Diseño Implementadas

1. **`tipo_cotizacion` vs `modelo_tipo`**: 
   - ✅ Mantener `modelo_tipo` como campo único
   - ✅ Añadir método `get_tipo_cotizacion()` para mapeo

2. **`secciones_activas` como JSONField**: 
   - ✅ Estructura flexible para futuras extensiones
   - ✅ Validación de al menos una sección activa

3. **`plantilla_id` como ForeignKey**: 
   - ✅ Nullable para compatibilidad con cotizaciones existentes
   - ✅ `SET_NULL` on delete para preservar datos históricos
