# Corrección de Deadlock en Editor de Cotizaciones - SINTEL v2.40

**Versión:** SINTEL v2.40  
**Fecha:** 2026  
**Tipo:** Corrección de Bug Crítico  
**Módulo:** Editor de Cotizaciones Estilo Excel

---

## Resumen Ejecutivo

Se corrigió un **deadlock crítico** en el Editor de Cotizaciones que impedía la inicialización de las tablas Tabulator cuando estaban ubicadas en pestañas ocultas (Bootstrap tabs). El problema causaba que los botones "Agregar Fila" permanecieran deshabilitados indefinidamente.

### Problema Identificado

El sistema esperaba el evento `tableBuilt` de Tabulator para resolver las promesas de inicialización. Sin embargo, las tablas ubicadas en pestañas ocultas (Bootstrap tabs) **no disparan el evento `tableBuilt`** hasta que la pestaña se hace visible, causando un deadlock donde:

1. `initAllTables()` esperaba indefinidamente a que `tableBuilt` se disparara
2. Los botones "Agregar Fila" permanecían deshabilitados
3. La interfaz quedaba bloqueada esperando la inicialización

---

## Solución Implementada

### 1. Refactorización de `initTable()` - Resolución Inmediata

**Antes:**
```javascript
function initTable(seccion, columns) {
  return new Promise((resolve, reject) => {
    // ... configuración ...
    tableBuilt: function() {
      resolve(table); // ❌ Esperaba tableBuilt (deadlock en pestañas ocultas)
    }
  });
}
```

**Después:**
```javascript
function initTable(seccion, columns) {
  return new Promise((resolve, reject) => {
    // ... configuración ...
    tableBuilt: function() {
      // ✅ Solo para logs, NO bloquea la inicialización
      console.log(`[${MOD}] ✅ Tabla construida completamente para sección: ${seccion}`);
    }
    // ...
    table = new w.Tabulator(container, tableOptions);
    tables[seccion] = table;
    
    // ✅ Resolver INMEDIATAMENTE después de crear la instancia
    resolve(table);
  });
}
```

**Beneficios:**
- ✅ Elimina el deadlock con pestañas ocultas
- ✅ Las tablas se inicializan inmediatamente
- ✅ Los botones se habilitan sin esperar `tableBuilt`

### 2. Eliminación de Clonación de Botones

**Problema:**
- El código clonaba los botones usando `cloneNode(true)` y `replaceChild()`
- Esto rompía el estado de Bootstrap y podía copiar el atributo `disabled` permanentemente

**Solución:**
- ✅ Eliminado completamente el bloque de clonación (líneas 2832-2852)
- ✅ Confianza en Event Delegation configurado en `init()`
- ✅ Más eficiente y evita duplicar listeners

**Código Eliminado:**
```javascript
// ❌ ELIMINADO - Causaba problemas con estado de Bootstrap
const newBtn = btn.cloneNode(true);
btn.parentNode.replaceChild(newBtn, btn);
newBtn.addEventListener('click', function(e) { ... });
```

### 3. Habilitación Prioritaria de UI

**Mejora:**
- `habilitarBotonesAgregarFila()` se llama **inmediatamente** después de `await initAllTables()`
- Función agresiva que elimina todos los estilos inline bloqueantes:
  - `btn.disabled = false`
  - `btn.removeAttribute('disabled')`
  - `btn.classList.remove('disabled')`
  - `btn.style.removeProperty('pointer-events')`
  - `btn.style.pointerEvents = 'auto'`
  - `btn.style.cursor = 'pointer'`

**Implementación:**
```javascript
// En onModalShown, después de await initAllTables()
habilitarBotonesAgregarFila(); // ✅ Habilitación prioritaria

// Luego actualizar totales con guardias
try {
  actualizarPanelTotales();
} catch (error) {
  // No crítico si las tablas ocultas aún no tienen datos
}
```

### 4. Sincronización de Totales con Guardias

**Problema:**
- `actualizarPanelTotales()` fallaba si las tablas ocultas no tenían datos aún

**Solución:**
```javascript
function actualizarPanelTotales() {
  // ⚠️ CRÍTICO: Guardia para no fallar si las tablas ocultas aún no tienen datos
  if (!isTablesInitialized) {
    console.warn(`[${MOD}] ⚠️ Tablas no inicializadas, omitiendo actualización de totales`);
    return;
  }
  
  let totales;
  try {
    totales = recalcularTodo();
  } catch (error) {
    // ✅ Retornar valores por defecto si hay error
    totales = {
      subtotal: 0,
      iva: 0,
      total: 0,
      valorAdministracion: 0,
      valorImprevistos: 0,
      valorUtilidad: 0
    };
  }
  // ... resto de la función
}
```

### 5. Actualización de Verificaciones de `table.initialized`

**Problema:**
- El código verificaba `table.initialized === false`, pero esta propiedad puede no estar disponible en tablas de pestañas ocultas

**Solución:**
- ✅ Eliminadas todas las verificaciones de `table.initialized`
- ✅ Ahora solo se verifica que `table` existe y tiene métodos necesarios:
  - `typeof table.addRow === 'function'`
  - `typeof table.getRows === 'function'`

**Cambios en `agregarFila()`:**
```javascript
// ❌ ANTES
if (table.initialized === false || table.initialized === undefined) {
  return; // Deadlock si tableBuilt no se disparó
}

// ✅ DESPUÉS
if (!table || typeof table.addRow !== 'function' || typeof table.getRows !== 'function') {
  return; // Verifica métodos, no estado interno
}
```

**Cambios en `recalcularTodo()`:**
```javascript
// ❌ ANTES
if (table.initialized === false) {
  return; // Omitía tablas ocultas
}

// ✅ DESPUÉS
if (!table || typeof table.getRows !== 'function') {
  return; // Solo verifica que existe y tiene métodos
}
```

---

## Archivos Modificados

### `apps/tenant/core/static/core/js/cotizaciones/cotizacion_editor.js`

**Cambios Principales:**

1. **Función `initTable()` (línea ~1009)**
   - Resolución inmediata de promesa después de crear instancia
   - `tableBuilt` solo para logs, no bloquea inicialización

2. **Función `initAllTables()` (línea ~1224)**
   - Actualizado para reflejar resolución inmediata
   - Logs actualizados

3. **Evento `shown.bs.modal` (línea ~2709)**
   - Eliminado código de clonación de botones
   - Uso de `habilitarBotonesAgregarFila()` prioritariamente
   - Guardias en `actualizarPanelTotales()`

4. **Función `actualizarPanelTotales()` (línea ~1563)**
   - Guardias con `try-catch` para tablas ocultas
   - Valores por defecto en caso de error

5. **Función `agregarFila()` (línea ~1818)**
   - Verificación simplificada (solo métodos, no `initialized`)

6. **Función `recalcularTodo()` (línea ~1458)**
   - Verificación simplificada (solo métodos, no `initialized`)

---

## Flujo de Inicialización Corregido

### Antes (Con Deadlock)

```
1. Modal se abre (shown.bs.modal)
2. initAllTables() se ejecuta
3. initTable() crea instancia de Tabulator
4. initTable() espera tableBuilt... ⏳ (DEADLOCK si pestaña oculta)
5. Botones permanecen deshabilitados ❌
6. Interfaz bloqueada ❌
```

### Después (Sin Deadlock)

```
1. Modal se abre (shown.bs.modal)
2. initAllTables() se ejecuta
3. initTable() crea instancia de Tabulator
4. initTable() resuelve INMEDIATAMENTE ✅
5. habilitarBotonesAgregarFila() se ejecuta ✅
6. Botones habilitados ✅
7. Interfaz funcional ✅
```

---

## Beneficios de la Corrección

### 1. Eliminación de Deadlock
- ✅ Las tablas se inicializan aunque estén en pestañas ocultas
- ✅ No hay espera indefinida por `tableBuilt`
- ✅ Inicialización inmediata y confiable

### 2. Habilitación Confiable de Botones
- ✅ Botones se habilitan inmediatamente después de inicialización
- ✅ Eliminación agresiva de estilos inline bloqueantes
- ✅ Event Delegation eficiente sin clonación

### 3. Resiliencia con Tablas Ocultas
- ✅ `actualizarPanelTotales()` no falla con tablas ocultas
- ✅ Guardias con `try-catch` y valores por defecto
- ✅ Verificaciones simplificadas (solo métodos, no estado interno)

### 4. Mejor Experiencia de Usuario
- ✅ Interfaz responde inmediatamente
- ✅ Sin bloqueos visuales
- ✅ Botones funcionales desde el inicio

---

## Pruebas Recomendadas

### Escenario 1: Modal con Pestaña Activa
1. Abrir modal de editor
2. Verificar que botones "Agregar Fila" se habilitan inmediatamente
3. Verificar que se pueden agregar filas en la pestaña activa

### Escenario 2: Cambio de Pestañas
1. Abrir modal de editor
2. Cambiar a pestaña "Accesorios" (inicialmente oculta)
3. Verificar que botones "Agregar Fila" funcionan
4. Verificar que se pueden agregar filas

### Escenario 3: Cálculo de Totales
1. Agregar filas en diferentes pestañas
2. Verificar que los totales se calculan correctamente
3. Verificar que no hay errores en consola

### Escenario 4: Reinicialización
1. Cerrar modal
2. Abrir modal nuevamente
3. Verificar que todo funciona correctamente

---

## Notas Técnicas

### Event Delegation vs Clonación

**Event Delegation (Implementado):**
- ✅ Más eficiente (un solo listener en el contenedor)
- ✅ Funciona con elementos dinámicos
- ✅ No rompe estado de Bootstrap
- ✅ No duplica listeners

**Clonación (Eliminada):**
- ❌ Menos eficiente (múltiples listeners)
- ❌ Puede romper estado de Bootstrap
- ❌ Puede copiar atributos `disabled` permanentemente
- ❌ Duplica listeners innecesariamente

### Resolución Inmediata vs Espera de tableBuilt

**Resolución Inmediata (Implementado):**
- ✅ Funciona con pestañas ocultas
- ✅ Inicialización confiable
- ✅ Sin deadlocks

**Espera de tableBuilt (Eliminado):**
- ❌ Deadlock con pestañas ocultas
- ❌ Inicialización bloqueada
- ❌ Botones permanecen deshabilitados

---

## Referencias

- **Archivo Principal:** `apps/tenant/core/static/core/js/cotizaciones/cotizacion_editor.js`
- **Documentación Relacionada:**
  - `documentacion/COTIZACIONES_CONFIGURACION_Y_NUMERACION.md`
  - `documentacion/INFORME_ESTRUCTURA_FUNCIONAL_COTIZACIONES.md`
- **Versión:** SINTEL v2.40
- **Fecha de Corrección:** 2026

---

## Changelog

### v2.40 - Corrección de Deadlock en Editor

**Correcciones:**
- ✅ Eliminado deadlock en inicialización de tablas Tabulator
- ✅ Resolución inmediata de promesas en `initTable()`
- ✅ Eliminada clonación de botones que rompía estado de Bootstrap
- ✅ Habilitación prioritaria de botones "Agregar Fila"
- ✅ Guardias en `actualizarPanelTotales()` para tablas ocultas
- ✅ Verificaciones simplificadas (solo métodos, no `initialized`)

**Mejoras:**
- ✅ Mejor experiencia de usuario (sin bloqueos)
- ✅ Event Delegation más eficiente
- ✅ Resiliencia con pestañas ocultas de Bootstrap

---

**Fin del Documento**
