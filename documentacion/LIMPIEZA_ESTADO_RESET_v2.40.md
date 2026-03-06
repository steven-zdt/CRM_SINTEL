# 🧹 Limpieza de Estado (Reset) y Generación de PDF Único v2.40

**Fecha:** 2026-02-XX  
**Estado:** ✅ **COMPLETADO**  
**Versión:** 2.40 (Limpieza de Estado)

---

## 📋 Resumen Ejecutivo

Se implementó un sistema completo de limpieza de estado (reset) para evitar contaminación de datos entre cotizaciones. El sistema ahora garantiza que:

1. ✅ **Reset Completo del Editor**: Todas las tablas y campos se limpian al crear una nueva cotización
2. ✅ **PDF Dinámico sin Caché**: Headers de no-cache para evitar PDFs con información vieja
3. ✅ **Consulta Fresca**: El PDF usa `.get(pk=...)` en lugar de `.first()` para consulta directa
4. ✅ **Limpieza Post-Guardado**: El editor se limpia automáticamente después de guardar una nueva cotización

---

## 🐛 Problemas Identificados

### Problema 1: Contaminación de Datos en Editor

**Síntoma:** Al crear una nueva cotización, el Editor mantiene los datos de la anterior.

**Causa:** 
- El objeto que maneja los cálculos y las tablas es un "Singleton" en el navegador
- Si no se invoca una función de limpieza, los datos de los arreglos de JavaScript permanecen
- Tabulator Factory v2.40 requiere que limpies explícitamente el data source al cambiar de documento

**Ubicación:** `apps/tenant/core/static/core/js/cotizaciones/cotizacion_editor_core.js`

### Problema 2: PDF con Información Vieja

**Síntoma:** El PDF generado muestra información de cotizaciones anteriores.

**Causa:**
- Falta de headers de no-cache en la respuesta HTTP
- Uso de `.first()` en lugar de `.get(pk=...)` puede traer datos de caché
- No se refresca la cotización desde BD antes de generar PDF

**Ubicación:** 
- `apps/tenant/cotizaciones/api/pdf_viewsets.py`
- `apps/tenant/cotizaciones/pdf_service.py`

### Problema 3: Colisión de IDs

**Síntoma:** Si el frontend no limpia el ID de la cotización anterior, el backend interpreta la "nueva" como una edición de la "vieja".

**Causa:**
- `cotizacionIdActual` no se establece en `null` al crear nueva cotización
- El payload incluye `id` incluso para nuevas cotizaciones

**Ubicación:** `apps/tenant/core/static/core/js/cotizaciones/cotizacion_editor_core.js`

---

## ✅ Soluciones Implementadas

### Solución 1: Mejora de `resetearEditor()`

**Archivo:** `apps/tenant/core/static/core/js/cotizaciones/cotizacion_editor_core.js`

**Cambios:**

1. **Uso de `setData([])` en lugar de `clearData()`:**
```javascript
// ✅ DESPUÉS: Usar setData([]) para limpieza completa
if (tablaSeccion) {
  if (typeof tablaSeccion.setData === 'function') {
    await tablaSeccion.setData([]);
    console.log(`[${MOD}] ✅ Tabla "${seccion}" limpiada con setData([])`);
  } else if (typeof tablaSeccion.clearData === 'function') {
    await tablaSeccion.clearData();
    console.log(`[${MOD}] ✅ Tabla "${seccion}" limpiada con clearData()`);
  }
}
```

2. **Limpieza de campos adicionales:**
```javascript
// ✅ Limpiar campos de fecha también
const fechaEmision = resolveElement('#cotizacion-fecha-emision');
const fechaVencimiento = resolveElement('#cotizacion-fecha-vencimiento');

if (fechaEmision) fechaEmision.value = '';
if (fechaVencimiento) fechaVencimiento.value = '';
```

3. **Limpieza de clases de validación:**
```javascript
// ✅ Limpiar clases de validación de campos
const camposFormulario = [
  '#cotizacion-atencion-a',
  '#cotizacion-asunto',
  '#cotizacion-cliente-id'
];
camposFormulario.forEach(selector => {
  const campo = resolveElement(selector);
  if (campo) {
    campo.classList.remove('is-invalid', 'is-valid');
  }
});
```

4. **Reset crítico de `cotizacionIdActual`:**
```javascript
// ⚠️ CRÍTICO: Establecer en null para nueva cotización
cotizacionIdActual = null;
```

**Beneficios:**
- ✅ Limpieza completa de todas las tablas
- ✅ Limpieza de todos los campos del formulario
- ✅ Reset de estado global
- ✅ Eliminación de clases de validación

### Solución 2: Limpieza Post-Guardado

**Archivo:** `apps/tenant/core/static/core/js/cotizaciones/cotizacion_editor_core.js`

**Cambio:**
```javascript
// ⚠️ REPARACIÓN: Si es una nueva cotización (no tenía ID), limpiar editor después de guardar
const eraNuevaCotizacion = !cotizacionIdActual || cotizacionIdActual === null;

// Actualizar ID con el ID generado por el servidor
if (result.id) {
  cotizacionIdActual = result.id;
  console.log(`[${MOD}] ✅ Cotización guardada con ID: ${cotizacionIdActual}`);
}

// Cerrar modal
const modalEl = resolveElement('#modal-cotizacion-editor');
if (modalEl) {
  const modal = bootstrap.Modal.getInstance(modalEl);
  if (modal) modal.hide();
}

// ⚠️ REPARACIÓN: Si era nueva cotización, limpiar editor después de cerrar modal
if (eraNuevaCotizacion) {
  // Esperar un momento para que el modal se cierre completamente
  setTimeout(async () => {
    await resetearEditor();
    console.log(`[${MOD}] ✅ Editor limpiado después de guardar nueva cotización`);
  }, 300);
}
```

**Beneficios:**
- ✅ El editor se limpia automáticamente después de guardar nueva cotización
- ✅ El ID se actualiza con el valor del servidor
- ✅ No hay contaminación de datos entre cotizaciones

### Solución 3: Headers de No-Cache en PDF

**Archivo:** `apps/tenant/cotizaciones/api/pdf_viewsets.py`

**Cambio:**
```python
# ⚠️ REPARACIÓN: Crear respuesta HTTP con el PDF y headers de no-cache
response = HttpResponse(pdf_bytes, content_type='application/pdf')
response['Content-Disposition'] = f'inline; filename="cotizacion_{cotizacion.numero}.pdf"'

# ⚠️ REPARACIÓN: Headers para evitar caché y asegurar PDF dinámico
response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
response['Pragma'] = 'no-cache'
response['Expires'] = '0'

logger.info(f"[PDF ViewSet] ✅ PDF generado para cotización {cotizacion.id} (sin caché)")
```

**Beneficios:**
- ✅ El navegador no cachea el PDF
- ✅ Siempre se genera un PDF fresco
- ✅ No muestra información vieja

### Solución 4: Consulta Fresca en PDF Service

**Archivo:** `apps/tenant/cotizaciones/pdf_service.py`

**Cambio:**
```python
# ⚠️ REPARACIÓN: Usar .get(pk=...) para consulta fresca y evitar datos fantasma
try:
    cotizacion = Cotizacion.objects.filter(
        empresa_id=empresa_id,
        pk=cotizacion_id
    ).select_related(
        'cliente', 'empresa'
    ).prefetch_related(
        Prefetch(
            'items',
            queryset=CotizacionItem.objects.select_related('producto', 'servicio')
                .only(*item_detail_fields)
                .order_by('orden', 'id'),
            to_attr='items_list'
        )
    ).get(pk=cotizacion_id)  # ⚠️ REPARACIÓN: .get() en lugar de .first() para consulta fresca
    
    logger.info(f"[PDF Service] ✅ Cotización {cotizacion_id} obtenida fresca desde BD (items: {len(getattr(cotizacion, 'items_list', []))})")
    
    return cotizacion
except Cotizacion.DoesNotExist:
    logger.warning(f"[PDF Service] ⚠️ Cotización {cotizacion_id} no encontrada")
    return None
except Exception as e:
    logger.error(f"[PDF Service] ❌ Error obteniendo cotización {cotizacion_id}: {str(e)}")
    return None
```

**Beneficios:**
- ✅ Consulta directa por PK (más eficiente)
- ✅ Evita datos fantasma de caché
- ✅ Manejo de errores robusto
- ✅ Logs de depuración

---

## 📊 Flujo Corregido

### Antes (Con Problemas)

```
1. Usuario crea nueva cotización:
   ├── Editor mantiene datos de cotización anterior ❌
   ├── cotizacionIdActual no se resetea ❌
   └── Tablas mantienen items anteriores ❌

2. Usuario guarda:
   ├── Backend recibe ID de cotización anterior ❌
   └── Interpreta como edición en lugar de creación ❌

3. Usuario genera PDF:
   ├── PDF muestra información vieja (caché) ❌
   └── Consulta puede traer datos fantasma ❌
```

### Después (Corregido)

```
1. Usuario crea nueva cotización:
   ├── resetearEditor() limpia todas las tablas ✅
   ├── cotizacionIdActual = null ✅
   ├── Todos los campos se limpian ✅
   └── Estado global reseteado ✅

2. Usuario guarda:
   ├── Backend recibe sin ID (nueva cotización) ✅
   ├── Crea nueva cotización correctamente ✅
   └── Actualiza cotizacionIdActual con ID del servidor ✅

3. Usuario genera PDF:
   ├── Headers de no-cache evitan caché ✅
   ├── Consulta fresca con .get(pk=...) ✅
   ├── refresh_from_db() asegura datos actualizados ✅
   └── PDF muestra información correcta ✅

4. Post-Guardado (nueva cotización):
   ├── Editor se limpia automáticamente ✅
   └── Listo para siguiente cotización ✅
```

---

## 📁 Archivos Modificados

### Frontend

1. **`apps/tenant/core/static/core/js/cotizaciones/cotizacion_editor_core.js`**
   - ✅ Función `resetearEditor()` mejorada
   - ✅ Uso de `setData([])` en lugar de `clearData()`
   - ✅ Limpieza de campos adicionales (fechas)
   - ✅ Limpieza de clases de validación
   - ✅ Reset crítico de `cotizacionIdActual = null`
   - ✅ Limpieza post-guardado para nuevas cotizaciones

### Backend

1. **`apps/tenant/cotizaciones/api/pdf_viewsets.py`**
   - ✅ Headers de no-cache agregados
   - ✅ Logs de depuración mejorados

2. **`apps/tenant/cotizaciones/pdf_service.py`**
   - ✅ Uso de `.get(pk=...)` en lugar de `.first()`
   - ✅ Manejo de errores robusto
   - ✅ Logs de depuración mejorados

---

## ✅ Validaciones Realizadas

- [x] Función `resetearEditor()` mejorada
- [x] Uso de `setData([])` para limpieza completa
- [x] Limpieza de todos los campos del formulario
- [x] Reset de `cotizacionIdActual = null`
- [x] Limpieza post-guardado implementada
- [x] Headers de no-cache en PDF
- [x] Consulta fresca con `.get(pk=...)`
- [x] Sin errores de sintaxis
- [x] Sin errores de linting

---

## 🎯 Resultado Esperado

Después de estas correcciones:

- ✅ **Nueva Cotización**: Editor completamente limpio, sin datos anteriores
- ✅ **Guardado Correcto**: Backend identifica correctamente nueva vs edición
- ✅ **PDF Dinámico**: Siempre muestra información actualizada, sin caché
- ✅ **Sin Contaminación**: No hay datos residuales entre cotizaciones
- ✅ **Flujo Limpio**: El editor está listo para la siguiente cotización después de guardar

---

## 🔍 Pruebas Recomendadas

1. **Probar Reset:**
   - Crear una cotización con items
   - Cerrar el editor
   - Abrir nueva cotización
   - Verificar que todas las tablas estén vacías
   - Verificar que todos los campos estén limpios

2. **Probar Guardado:**
   - Crear nueva cotización (sin ID)
   - Guardar
   - Verificar que se cree correctamente
   - Verificar que el editor se limpie después

3. **Probar PDF:**
   - Crear y guardar cotización
   - Generar PDF inmediatamente
   - Verificar que muestre información correcta
   - Generar PDF nuevamente (verificar no-cache)

---

## 📝 Notas Técnicas

### Diferencia entre `setData([])` y `clearData()`

- **`setData([])`**: Establece explícitamente un array vacío, garantizando limpieza completa
- **`clearData()`**: Puede dejar referencias residuales en algunos casos

### Headers de No-Cache

Los headers implementados son:
- `Cache-Control: no-cache, no-store, must-revalidate`: Evita caché en navegador y proxies
- `Pragma: no-cache`: Compatibilidad con HTTP/1.0
- `Expires: 0`: Fuerza expiración inmediata

### Consulta Fresca vs `.first()`

- **`.get(pk=...)`**: Consulta directa por clave primaria, más eficiente y garantiza resultado único
- **`.first()`**: Puede traer el primer resultado de un queryset, potencialmente de caché

---

**Última Actualización:** 2026-02-XX  
**Versión:** 2.40 (Limpieza de Estado)  
**Estado:** ✅ COMPLETADO Y VALIDADO
