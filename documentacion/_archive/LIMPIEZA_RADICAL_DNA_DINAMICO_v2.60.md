# Limpieza Radical y Alineación Tabulator (DNA Dinámico v2.60)

**Fecha de Actualización**: 2024-12-19  
**Estado**: ✅ Backend Completado | ⏳ Frontend Pendiente

## 📋 Resumen Ejecutivo

Esta documentación describe la limpieza radical y alineación del módulo de Cotizaciones con el estándar **DNA Dinámico v2.60** y **Tabulator Factory**. El objetivo es eliminar código legacy y transformar el editor de cotizaciones en un sistema de tablas dinámicas que respondan al perfil de configuración (AIU, Utilidad, IVA).

### Estado Actual
- ✅ **Backend**: 100% completado y alineado con v2.60
- ⏳ **Frontend**: Pendiente implementación de generador dinámico de columnas, mutators e inmutabilidad

---

## ✅ Tareas Completadas

### 1. Purga de Código Legacy

#### 1.1. Eliminación de Forms y Views Obsoletos
- ✅ **forms.py**: No existe (ya eliminado en limpieza anterior)
- ✅ **views.py**: No existe (solo ViewSets DRF en `api/viewsets.py`)
- ✅ **Verificación**: Confirmado que no hay vistas basadas en Django Forms o clases genéricas (CreateView, UpdateView)

#### 1.2. Eliminación de JS Incompatible
- ✅ **Búsqueda exhaustiva**: No se encontraron archivos:
  - `wizard_items.js`
  - `calculos_manuales.js`
  - `form_wizard.js`
  - Cualquier script que no use el estándar de TabulatorFactory
- ✅ **Templates**: No hay referencias a archivos JS obsoletos en `assets_cotizaciones.html`

### 2. Alineación con Tabulator Factory (Backend)

#### 2.1. Serializers v2.60 ✅

**Archivo**: `apps/tenant/cotizaciones/api/serializers.py`

**Cambios Implementados**:

1. **Campo `configuracion` agregado a `CotizacionDetailSerializer`**:
   ```python
   configuracion = serializers.SerializerMethodField()
   ```
   - Retorna objeto completo de `ConfiguracionCotizacion` si existe plantilla
   - Permite que el frontend configure Tabulator dinámicamente según `tipo_plantilla`

2. **Método `get_items()` implementado**:
   ```python
   def get_items(self, obj):
       """
       ⚠️ DNA Dinámico v2.60: Retorna items ordenados por campo 'orden'.
       """
       items = obj.items.all().order_by('orden', 'id')
       return CotizacionItemNestedSerializer(items, many=True).data
   ```
   - Garantiza que los items se retornen ordenados por campo `orden`
   - Mantiene secuencia correcta en el frontend

3. **Método `get_configuracion()` implementado**:
   ```python
   def get_configuracion(self, obj):
       """
       ⚠️ DNA Dinámico v2.60: Retorna objeto de configuración completo si existe plantilla.
       Permite que el frontend configure Tabulator dinámicamente según tipo_plantilla.
       """
       if not obj.plantilla:
           return None
       
       from apps.tenant.cotizaciones.configuracion.serializers import ConfiguracionCotizacionDetailSerializer
       return ConfiguracionCotizacionDetailSerializer(obj.plantilla).data
   ```
   - Retorna configuración completa incluyendo:
     - `tipo_plantilla` (EQUIPO, MATERIAL, SERVICIO, MIXTO)
     - Parámetros por modelo (utilidad, IVA)
     - Parámetros AIU (si aplica)
     - Configuración de columnas visibles

4. **Campo `configuracion` agregado a `fields`**:
   ```python
   fields = (
       # ... otros campos ...
       'plantilla', 'secciones_activas', 'configuracion',
       # ... otros campos ...
   )
   ```

#### 2.2. ViewSet ✅

**Archivo**: `apps/tenant/cotizaciones/api/viewsets.py`

**Cambios Implementados**:
- ✅ **Items ordenados**: El ordenamiento se realiza en el serializer (`get_items()`), no requiere ordenamiento adicional en el queryset
- ✅ **Optimización**: El ViewSet mantiene su estructura optimizada con servicios (`qs_list`, `qs_detail`)

### 3. Limpieza de Templates y Errores 404 ✅

**Archivo**: `apps/tenant/core/templates/tenant/core/partials/cotizaciones/assets_cotizaciones.html`

**Estado**:
- ✅ Sin referencias a archivos 404
- ✅ Solo incluye archivos válidos:
  - `cotizaciones.api.js`
  - `cotizaciones.page.js`
  - `cotizacion_editor.js`
- ✅ Comentadas referencias a archivos eliminados (ej: `productos.page.js`)

---

## ⏳ Tareas Pendientes (Frontend)

### 3.1. Generador Dinámico de Columnas
**Estado**: ⏳ Pendiente  
**Ubicación**: `apps/tenant/core/static/core/js/cotizaciones/cotizacion_editor.js`  
**Prioridad**: Alta

**Requisitos**:
- Función que defina `columnLayout` de Tabulator basado en `tipo_plantilla` del objeto `configuracion` retornado por el serializer
- Si `tipo_plantilla` es `SERVICIO` o `MATERIAL`: 
  - Habilitar columnas de Costo, % Utilidad y Factor AIU
  - Ocultar columnas de Marca y Referencia
- Si `tipo_plantilla` es `EQUIPO`: 
  - Habilitar columnas de Marca, Referencia y Unidad (Campos STS)
  - Mostrar todas las columnas relacionadas con productos físicos
- Si `tipo_plantilla` es `MIXTO`: 
  - Habilitar todas las columnas

**Datos Disponibles**:
El serializer ahora retorna `configuracion` con:
```json
{
  "tipo_plantilla": "SERVICIO" | "EQUIPO" | "MATERIAL" | "MIXTO",
  "porcentaje_utilidad_servicio": 20.00,
  "iva_porcentaje_servicio": 19.00,
  // ... otros campos de configuración
}
```

**Implementación sugerida**:
```javascript
/**
 * ⚠️ DNA Dinámico v2.60: Genera layout de columnas según tipo_plantilla
 * @param {string} tipoPlantilla - Tipo de plantilla (SERVICIO, EQUIPO, MATERIAL, MIXTO)
 * @param {string} seccion - Sección del editor (accesorios, mano-obra, etc.)
 * @param {object} configuracion - Objeto completo de configuración (opcional)
 * @returns {Array} Array de definiciones de columnas para Tabulator
 */
function getColumnLayoutByTipoPlantilla(tipoPlantilla, seccion, configuracion = null) {
  const baseColumns = COLUMNS_CONFIG[seccion](tipoPlantilla, {});
  
  // Aplicar visibilidad según tipo_plantilla
  if (tipoPlantilla === 'SERVICIO' || tipoPlantilla === 'MATERIAL') {
    // Mostrar columnas de Costo, % Utilidad, Factor AIU
    return baseColumns.map(col => {
      if (col.field === 'marca' || col.field === 'referencia') {
        col.visible = false;
      }
      if (col.field === 'costo_unitario' || col.field === 'porcentaje_utilidad') {
        col.visible = true;
        col.editor = 'number';
      }
      // Si hay configuración AIU, mostrar columnas relacionadas
      if (configuracion && configuracion.aiu_admin_default > 0) {
        // Agregar columnas AIU si no existen
      }
      return col;
    });
  } else if (tipoPlantilla === 'EQUIPO') {
    // Mostrar Marca, Referencia, Unidad
    return baseColumns.map(col => {
      if (col.field === 'marca' || col.field === 'referencia' || col.field === 'unidad') {
        col.visible = true;
      }
      return col;
    });
  }
  
  return baseColumns; // MIXTO: todas visibles
}
```

**Integración**:
- Llamar esta función al inicializar cada tabla Tabulator
- Usar `configuracion.tipo_plantilla` del objeto retornado por el serializer
- Aplicar el layout antes de crear la instancia de Tabulator

### 3.2. Cálculos en Tiempo Real (Mutators)
**Estado**: ⏳ Pendiente  
**Ubicación**: `apps/tenant/core/static/core/js/cotizaciones/cotizacion_editor.js`  
**Prioridad**: Alta

**Requisitos**:
- Configurar mutators de Tabulator para recalcular `subtotal_linea` automáticamente
- Fórmula según `models.py`: `subtotal = cantidad * costo * (1 + utilidad/100)`
- Actualmente se usa `cellEdited` callback en `recalcularSubtotalLinea()`, debe migrarse a mutators para mejor rendimiento
- Los mutators se ejecutan automáticamente cuando cambian los campos dependientes

**Implementación sugerida**:
```javascript
/**
 * ⚠️ DNA Dinámico v2.60: Mutators para cálculos en tiempo real
 * Estos mutators se ejecutan automáticamente cuando cambian los campos dependientes
 */
const TabulatorMutators = {
  /**
   * Calcula precio_unitario_venta basado en costo_unitario y porcentaje_utilidad
   */
  precio_unitario_venta: function(value, data, type, params, component) {
    const costo = parseFloat(data.costo_unitario) || 0;
    const utilidad = parseFloat(data.porcentaje_utilidad) || 10.00;
    const precioUnitario = costo * (1 + (utilidad / 100));
    return parseFloat(precioUnitario.toFixed(2));
  },
  
  /**
   * Calcula subtotal_linea basado en cantidad, costo_unitario y porcentaje_utilidad
   * Fórmula: subtotal = cantidad * costo * (1 + utilidad/100)
   */
  subtotal_linea: function(value, data, type, params, component) {
    const cantidad = parseFloat(data.cantidad) || 0;
    const costo = parseFloat(data.costo_unitario) || 0;
    const utilidad = parseFloat(data.porcentaje_utilidad) || 10.00;
    const precioUnitario = costo * (1 + (utilidad / 100));
    const subtotal = cantidad * precioUnitario;
    return parseFloat(subtotal.toFixed(2));
  }
};

// Registrar mutators globalmente (una sola vez)
if (typeof Tabulator !== 'undefined') {
  Tabulator.extendModule("mutator", "mutators", TabulatorMutators);
}
```

**Uso en definición de columnas**:
```javascript
{
  title: "Precio Unit. Venta",
  field: "precio_unitario_venta",
  mutator: "precio_unitario_venta", // Usa el mutator definido
  editor: false,
  formatter: function(cell) {
    return formatCOP(cell.getValue());
  }
},
{
  title: "Total",
  field: "subtotal_linea",
  mutator: "subtotal_linea", // Usa el mutator definido
  editor: false,
  formatter: function(cell) {
    return formatCOP(cell.getValue());
  }
}
```

**Migración desde `cellEdited`**:
- Eliminar o simplificar `recalcularSubtotalLinea()` (los mutators hacen el trabajo)
- Mantener `cellEdited` solo para actualizar totales del panel (`actualizarPanelTotales()`)
- Los mutators se ejecutan automáticamente, no requieren llamadas manuales

### 3.3. Inmutabilidad en Tabulator
**Estado**: ⏳ Pendiente  
**Ubicación**: `apps/tenant/core/static/core/js/cotizaciones/cotizacion_editor.js`  
**Prioridad**: Media

**Requisitos**:
- Si `Cotizacion.estado` es `ACEPTADA`, inicializar Tabulator con `editable: false` en todas las columnas
- Deshabilitar botones de agregar/eliminar filas
- Mostrar indicador visual de que la cotización está aceptada (badge, mensaje, etc.)
- Prevenir cualquier modificación de datos cuando `estado === 'ACEPTADA'`

**Datos Disponibles**:
El serializer retorna `estado` y `estado_display`:
```json
{
  "estado": "ACEPTADA",
  "estado_display": "Aceptada"
}
```

**Implementación sugerida**:
```javascript
/**
 * ⚠️ DNA Dinámico v2.60: Inicializa tabla con inmutabilidad si estado es ACEPTADA
 * @param {string} seccion - Sección del editor
 * @param {string} estado - Estado de la cotización
 * @param {string} tipoPlantilla - Tipo de plantilla
 * @param {object} configuracion - Objeto de configuración
 * @returns {Tabulator} Instancia de Tabulator configurada
 */
function initTableWithImmutability(seccion, estado, tipoPlantilla, configuracion) {
  const selector = GRID_IDS[seccion];
  const columns = getColumnLayoutByTipoPlantilla(tipoPlantilla, seccion, configuracion);
  const isInmutable = estado === 'ACEPTADA';
  
  // Aplicar inmutabilidad a todas las columnas editables
  if (isInmutable) {
    columns.forEach(col => {
      if (col.editor && col.field !== 'acciones') {
        col.editor = false;
      }
      // Deshabilitar formatters que permitan edición
      if (col.cellEdited) {
        col.cellEdited = null;
      }
    });
    
    // Mostrar indicador visual
    console.log(`[${MOD}] ⚠️ Cotización ACEPTADA - Modo solo lectura activado`);
  }
  
  const tableConfig = {
    selector: selector,
    columns: columns,
    editable: !isInmutable, // Deshabilitar edición global si es inmutable
    // ... resto de configuración
  };
  
  const table = new Tabulator(tableConfig);
  
  // Deshabilitar botones de agregar/eliminar si es inmutable
  if (isInmutable) {
    // Ocultar botones de acciones
    table.on("tableBuilt", function() {
      const actionButtons = d.querySelectorAll(`${selector} .btn-agregar-fila-interna, ${selector} [data-action="eliminar-fila"]`);
      actionButtons.forEach(btn => {
        btn.style.display = 'none';
        btn.disabled = true;
      });
    });
  }
  
  return table;
}
```

**Indicador Visual**:
```javascript
// Agregar badge o mensaje en el modal cuando estado === 'ACEPTADA'
function mostrarIndicadorInmutabilidad(estado) {
  if (estado === 'ACEPTADA') {
    const modalHeader = d.querySelector('#modal-cotizacion-editor .modal-header');
    if (modalHeader && !modalHeader.querySelector('.badge-inmutable')) {
      const badge = d.createElement('span');
      badge.className = 'badge bg-success ms-2 badge-inmutable';
      badge.textContent = 'COTIZACIÓN ACEPTADA - Solo Lectura';
      modalHeader.appendChild(badge);
    }
  }
}
```

### 3.4. Integración Completa
**Estado**: ⏳ Pendiente  
**Prioridad**: Alta

**Flujo de Integración**:
1. Al cargar cotización existente:
   - Leer `configuracion.tipo_plantilla` del objeto retornado por el serializer
   - Leer `estado` para determinar inmutabilidad
   - Llamar `getColumnLayoutByTipoPlantilla()` con los datos correctos
   - Llamar `initTableWithImmutability()` con estado y configuración

2. Al crear nueva cotización:
   - Usar valores por defecto o configuración del perfil seleccionado
   - Aplicar layout según `tipo_plantilla` seleccionado en el modal de configuración inicial

3. Durante edición:
   - Los mutators calculan automáticamente `precio_unitario_venta` y `subtotal_linea`
   - No se requieren llamadas manuales a `recalcularSubtotalLinea()`
   - Solo se llama `actualizarPanelTotales()` para actualizar totales generales

---

## 📊 Archivos Modificados

### Backend

1. **`apps/tenant/cotizaciones/api/serializers.py`**
   - ✅ Agregado campo `configuracion` (SerializerMethodField) a `CotizacionDetailSerializer`
   - ✅ Implementado método `get_items()` con ordenamiento por campo `orden`
   - ✅ Implementado método `get_configuracion()` que retorna configuración completa
   - ✅ Agregado `configuracion` a la lista de `fields` en `Meta`

### Documentación

2. **`apps/tenant/cotizaciones/LIMPIEZA_RADICAL_DNA_DINAMICO_v2.60.md`**
   - ✅ Documento completo con resumen de cambios
   - ✅ Guía de implementación para tareas pendientes
   - ✅ Ejemplos de código para frontend

### Verificaciones

3. **Estructura de Archivos**
   - ✅ Verificado que no existe `forms.py`
   - ✅ Verificado que no existe `views.py` (solo ViewSets DRF)
   - ✅ Verificado que no hay archivos JS incompatibles
   - ✅ Verificado que `assets_cotizaciones.html` está limpio

---

## 📋 Próximos Pasos (Frontend)

### Prioridad Alta
1. **Implementar generador dinámico de columnas** basado en `configuracion.tipo_plantilla`
   - Leer `configuracion` del objeto retornado por el serializer
   - Aplicar layout según tipo (SERVICIO/MATERIAL vs EQUIPO vs MIXTO)

2. **Migrar cálculos a mutators de Tabulator**
   - Registrar mutators globalmente
   - Reemplazar `cellEdited` callbacks por mutators
   - Simplificar `recalcularSubtotalLinea()`

### Prioridad Media
3. **Implementar inmutabilidad** cuando `estado === 'ACEPTADA'`
   - Deshabilitar edición en todas las columnas
   - Ocultar botones de agregar/eliminar filas
   - Mostrar indicador visual

4. **Integración completa**
   - Probar flujo de creación con diferentes tipos de plantilla
   - Probar flujo de edición con cotizaciones ACEPTADAS
   - Validar que los mutators funcionan correctamente

---

## 🎯 Resultado Esperado

Un módulo donde:

### Backend ✅
- ✅ El serializer retorna `configuracion` completo con `tipo_plantilla` y todos los parámetros
- ✅ Los items se retornan ordenados por campo `orden`
- ✅ No hay código legacy (forms.py, views.py)
- ✅ Solo ViewSets DRF en la capa de API

### Frontend ⏳
- ⏳ El JS lee el "DNA" del modelo (`configuracion.tipo_plantilla`) y configura Tabulator automáticamente
- ⏳ Los cálculos se realizan en tiempo real mediante mutators (sin callbacks manuales)
- ⏳ La inmutabilidad se aplica automáticamente cuando `estado === 'ACEPTADA'`
- ⏳ No hay código legacy ni referencias a archivos 404
- ⏳ La estructura es completamente modular y mantenible

---

## 🔍 Validación

### Checklist de Validación Backend ✅
- [x] Serializer retorna `configuracion` completo
- [x] Items ordenados por campo `orden`
- [x] No hay `forms.py` o `views.py` obsoletos
- [x] No hay referencias a archivos JS incompatibles
- [x] Templates limpios sin errores 404

### Checklist de Validación Frontend ⏳
- [ ] Generador dinámico de columnas implementado
- [ ] Mutators de Tabulator configurados
- [ ] Inmutabilidad implementada para estado ACEPTADA
- [ ] Pruebas de flujo completo realizadas

---

## 📝 Notas Técnicas

### Estructura de Datos Retornada por Serializer

```json
{
  "id": 1,
  "numero": "COT-0001",
  "estado": "ACEPTADA",
  "estado_display": "Aceptada",
  "modelo_tipo": "SERVICIO",
  "plantilla": 1,
  "configuracion": {
    "id": 1,
    "tipo_plantilla": "SERVICIO",
    "tipo_plantilla_display": "Servicios",
    "porcentaje_utilidad_servicio": 20.00,
    "iva_porcentaje_servicio": 19.00,
    "aiu_admin_default": 10.00,
    "aiu_imprevistos_default": 5.00,
    "aiu_utilidad_default": 10.00,
    // ... otros campos
  },
  "items": [
    {
      "id": 1,
      "orden": 0,
      "descripcion": "Servicio de instalación",
      "cantidad": 1.00,
      "costo_unitario": 100000.00,
      "porcentaje_utilidad": 20.00,
      "precio_unitario_venta": 120000.00,
      "subtotal_linea": 120000.00
    }
    // ... más items ordenados por campo 'orden'
  ]
}
```

### Fórmulas de Cálculo (models.py)

```python
# Precio unitario de venta
precio_unitario_venta = costo_unitario * (1 + (porcentaje_utilidad / 100))

# Subtotal de línea
subtotal_linea = cantidad * precio_unitario_venta
```

Estas fórmulas deben replicarse en los mutators de Tabulator para mantener consistencia.

---

**Última Actualización**: 2024-12-19  
**Versión**: DNA Dinámico v2.60  
**Estado**: Backend Completado | Frontend Pendiente
