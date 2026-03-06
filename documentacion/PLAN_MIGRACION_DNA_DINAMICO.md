# Plan de Migración: DNA Dinámico y Fase A (Cotizaciones v2.40)

## 📋 Análisis del Estado Actual

### Campos Existentes en `Cotizacion`:
- ✅ `modelo_tipo`: CharField con choices SERVICIO, EQUIPO, MATERIAL, MIXTO
- ✅ `es_aiu`: BooleanField para modo AIU
- ✅ `aiu_admin_porcentaje`, `aiu_imprevistos_porcentaje`, `aiu_utilidad_porcentaje`: DecimalField
- ✅ Campos de totales: `subtotal`, `iva_porcentaje`, `iva_valor`, `total_neto`
- ✅ Campos de inmutabilidad: `estado`, `numero` (automático)

### Campos a Añadir:
1. **`tipo_cotizacion`**: CharField con choices PRODUCTOS, SERVICIOS, MATERIALES, MIXTO
   - **Decisión**: Mapear a `modelo_tipo` existente:
     - PRODUCTOS → EQUIPO
     - SERVICIOS → SERVICIO
     - MATERIALES → MATERIAL
     - MIXTO → MIXTO
   - **Alternativa**: Mantener ambos campos y sincronizarlos
   - **Recomendación**: Usar `modelo_tipo` como fuente única de verdad, añadir `tipo_cotizacion` como propiedad calculada o campo derivado

2. **`secciones_activas`**: JSONField para almacenar qué secciones están habilitadas
   - Estructura propuesta:
     ```json
     {
       "equipos_dispositivos": true,
       "accesorios_materiales": true,
       "mano_obra_instalacion": false
     }
     ```

3. **`plantilla_id`**: ForeignKey a `ConfiguracionCotizacion` (nullable)
   - Permite asociar una cotización con un perfil de configuración específico
   - Si se proporciona, pre-carga valores de AIU e IVA desde la plantilla

## 🔄 Plan de Migración de Datos

### Paso 1: Migración de Schema
1. Añadir `secciones_activas` (JSONField, default={})
2. Añadir `plantilla_id` (ForeignKey, nullable=True)
3. **NO añadir `tipo_cotizacion`** (usar `modelo_tipo` como fuente única)

### Paso 2: Migración de Datos Existentes
1. **`secciones_activas`**: 
   - Para cotizaciones existentes, inferir desde `modelo_tipo`:
     - EQUIPO → `{"equipos_dispositivos": true, "accesorios_materiales": false, "mano_obra_instalacion": false}`
     - MATERIAL → `{"equipos_dispositivos": false, "accesorios_materiales": true, "mano_obra_instalacion": false}`
     - SERVICIO → `{"equipos_dispositivos": false, "accesorios_materiales": false, "mano_obra_instalacion": true}`
     - MIXTO → `{"equipos_dispositivos": true, "accesorios_materiales": true, "mano_obra_instalacion": true}`

2. **`plantilla_id`**: 
   - Para cotizaciones existentes, buscar el último perfil activo de la empresa
   - Si no existe, dejar como `null`

### Paso 3: Actualización de Validaciones
1. Añadir validación de inmutabilidad para `plantilla_id` (no puede cambiarse si estado=ACEPTADA)
2. Añadir validación de inmutabilidad para `secciones_activas` (no puede cambiarse si estado=ACEPTADA)

## 🎯 Decisiones de Diseño

### 1. `tipo_cotizacion` vs `modelo_tipo`
**Decisión**: Mantener `modelo_tipo` como campo único y añadir método helper `get_tipo_cotizacion()` que mapea:
- `modelo_tipo.EQUIPO` → `"PRODUCTOS"`
- `modelo_tipo.SERVICIO` → `"SERVICIOS"`
- `modelo_tipo.MATERIAL` → `"MATERIALES"`
- `modelo_tipo.MIXTO` → `"MIXTO"`

**Razón**: Evita duplicación de datos y mantiene consistencia.

### 2. `secciones_activas` como JSONField
**Estructura**:
```json
{
  "equipos_dispositivos": true,
  "accesorios_materiales": true,
  "mano_obra_instalacion": false
}
```

**Validación**: Debe tener al menos una sección activa.

### 3. `plantilla_id` como ForeignKey
- **Nullable**: `True` (para compatibilidad con cotizaciones existentes)
- **On Delete**: `SET_NULL` (si se elimina la plantilla, la cotización mantiene sus valores)
- **Validación**: Si se proporciona, debe pertenecer a la misma empresa

## 📝 Cambios en el Código

### Backend (models.py)
1. Añadir `secciones_activas` (JSONField)
2. Añadir `plantilla_id` (ForeignKey)
3. Añadir método `get_tipo_cotizacion()` para mapeo
4. Actualizar `clean()` para validar inmutabilidad de nuevos campos

### Backend (serializers.py)
1. Añadir `secciones_activas` y `plantilla_id` a serializers
2. Añadir validación de `secciones_activas` (al menos una sección activa)
3. Añadir validación de `plantilla_id` (pertenencia a empresa)

### Backend (viewsets.py)
1. Crear acción `@action(detail=False, methods=['post'], url_path='preforma')` para crear preforma
2. Endpoint debe recibir: `cliente_id`, `tipo_cotizacion` (mapeado a `modelo_tipo`), `plantilla_id`
3. Pre-cargar valores de AIU e IVA desde plantilla si se proporciona

### Frontend (JS/HTML)
1. Crear modal de "Configuración Inicial" que pregunte:
   - Cliente
   - Tipo de Cotización (PRODUCTOS, SERVICIOS, MATERIALES, MIXTO)
   - Plantilla (opcional)
2. Al confirmar, llamar a `/api/cotizaciones/preforma/` para crear preforma
3. Inyectar contenedores Tabulator según `secciones_activas`

## ⚠️ Restricciones de Inmutabilidad v2.40

1. **Si `estado == ACEPTADA`**:
   - ❌ No se puede cambiar `modelo_tipo`
   - ❌ No se puede cambiar `plantilla_id`
   - ❌ No se puede cambiar `secciones_activas`
   - ❌ No se puede cambiar `es_aiu`
   - ✅ Solo se puede cambiar `estado` (para cancelar si el flujo lo permite)

2. **Validación en `clean()`**:
   ```python
   if self.pk and original.estado == self.Estado.ACEPTADA:
       if original.plantilla_id != self.plantilla_id:
           raise ValidationError(_("La plantilla no puede modificarse en cotizaciones ACEPTADAS."))
       if original.secciones_activas != self.secciones_activas:
           raise ValidationError(_("Las secciones activas no pueden modificarse en cotizaciones ACEPTADAS."))
   ```

## 🚀 Orden de Implementación

1. ✅ Crear migración de schema (añadir campos)
2. ✅ Crear migración de datos (poblar campos existentes)
3. ✅ Actualizar modelo `Cotizacion`
4. ✅ Actualizar serializers
5. ✅ Crear endpoint `/api/cotizaciones/preforma/`
6. ✅ Actualizar validaciones de inmutabilidad
7. ✅ Crear modal de Configuración Inicial (Frontend)
8. ✅ Actualizar editor de cotizaciones para usar `secciones_activas`
