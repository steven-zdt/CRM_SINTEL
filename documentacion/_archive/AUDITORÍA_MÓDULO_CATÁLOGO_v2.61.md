# 🔍 AUDITORÍA GENERAL — Módulo Catálogo NIIF v2.61

## Resumen Ejecutivo

**Directorio auditado:** `apps/tenant/contabilidad/static/contabilidad/js/`

**Total de archivos:** 16 archivos JavaScript

**Archivos analizados:** 9 archivos de catálogo + 7 archivos de otros módulos

---

## 📊 MATRIZ DE ARCHIVOS

### Archivos de Catálogo (CRÍTICOS)

| Archivo | Líneas | Propósito | Estado | Sincronización |
|---------|--------|----------|--------|-----------------|
| `catalogo_service.js` | 389 | Service Layer para API | ✅ ACTIVO | ✅ HTMX integrado |
| `catalogo_integration_v2.js` | 317 | Sincronización Tipo ↔ Buscador | ✅ ACTIVO | ✅ Delegación eventos |
| `catalogo_audit.js` | 300+ | Auditoría con 6 checks | ✅ ACTIVO | ✅ Debugging |
| `catalogo_init.js` | 150+ | Inicializador explícito | ✅ ACTIVO | ✅ DOMContentLoaded + HTMX |
| `catalogo_htmx_reactivator.js` | 200+ | Reactivador de HTMX | ✅ ACTIVO | ✅ htmx:afterSettle |

### Archivos de Otros Módulos

| Archivo | Líneas | Propósito | Estado |
|---------|--------|----------|--------|
| `contabilidad.js` | ? | Módulo principal | ⚠️ REVISAR |
| `asiento/asiento.api.js` | ? | API de asientos | ✅ ACTIVO |
| `asiento/features/*.js` | ? | Features de asientos | ✅ ACTIVO |
| `cuenta/cuenta.api.js` | ? | API de cuentas | ✅ ACTIVO |
| `cuenta/features/*.js` | ? | Features de cuentas | ✅ ACTIVO |
| `periodo/periodo.api.js` | ? | API de períodos | ✅ ACTIVO |
| `periodo/features/*.js` | ? | Features de períodos | ✅ ACTIVO |

---

## 🔴 PROBLEMAS IDENTIFICADOS

### 1. CÓDIGO REPETIDO EN CATÁLOGO

**Archivos afectados:**
- `catalogo_integration_v2.js` (líneas 110-129)
- `catalogo_htmx_reactivator.js` (líneas 110-129)
- `catalogo_init.js` (líneas 35-70)

**Problema:** Delegación de eventos `change` duplicada en 3 archivos

**Código repetido:**
```javascript
d.addEventListener('change', (event) => {
  const target = event.target;
  const isTipoSelect = (
    target.tagName === 'SELECT'
    && (target.name === 'tipo' || target.id === 'select-tipo-cuenta' || target.id === 'select-tipo')
  );
  if (!isTipoSelect) return;
  // ... lógica duplicada
});
```

**Impacto:** Múltiples listeners registrados para el mismo evento

**Recomendación:** Consolidar en un único módulo (catalogo_service.js)

---

### 2. FUNCIONES ZOMBIE (Sin sincronización)

**Archivo:** `catalogo_integration_v2.js`

**Funciones sin uso:**
- `getCatalogoElements()` (línea 29) — Duplicada en catalogo_htmx_reactivator.js
- `findElement()` (línea 40) — Nunca se llama directamente
- `toggleBuscadorByTipo()` (línea 97) — Llamada solo internamente

**Recomendación:** Mover a módulo centralizado o eliminar

---

### 3. INICIALIZADORES MÚLTIPLES

**Problema:** 3 inicializadores independientes

- `catalogo_integration_v2.js` — Inicializa en DOMContentLoaded
- `catalogo_init.js` — Inicializa en DOMContentLoaded + HTMX
- `catalogo_htmx_reactivator.js` — Inicializa en HTMX events

**Impacto:** Código ejecutándose múltiples veces

**Recomendación:** Consolidar en un único inicializador

---

### 4. LISTENERS HTMX DUPLICADOS

**Problema:** Múltiples listeners para los mismos eventos HTMX

| Evento | Archivo 1 | Archivo 2 | Archivo 3 |
|--------|-----------|-----------|-----------|
| `htmx:afterSettle` | catalogo_integration_v2.js | catalogo_htmx_reactivator.js | catalogo_service.js |
| `htmx:afterSwap` | catalogo_integration_v2.js | catalogo_htmx_reactivator.js | - |
| `htmx:load` | catalogo_integration_v2.js | catalogo_init.js | - |

**Impacto:** Sincronización ejecutándose 3 veces

**Recomendación:** Consolidar en catalogo_service.js

---

### 5. EXPORTACIONES INCONSISTENTES

**Problema:** Diferentes patrones de exportación

```javascript
// catalogo_service.js
w.CatalogoService = Object.freeze(CatalogoService);
w.CatalogoService.sincronizarBuscador = sincronizarBuscadorNIIF;

// catalogo_integration_v2.js
w.CatalogoIntegration = { log, getCatalogoElements, toggleBuscadorByTipo, initialize, debug };

// catalogo_audit.js
w.CatalogoAudit = { runFullAudit, checkDOMElements, ... };

// catalogo_init.js
w.CatalogoInit = { init, debug };

// catalogo_htmx_reactivator.js
w.CatalogoReactivator = { reactivate, debug };
```

**Impacto:** 5 namespaces diferentes para la misma funcionalidad

**Recomendación:** Consolidar en `w.CatalogoModule`

---

## ✅ RECOMENDACIONES DE LIMPIEZA

### PASO 1: Consolidar en catalogo_service.js

Mover toda la lógica de sincronización a `catalogo_service.js`:
- Función `sincronizarBuscadorNIIF()` (ya existe)
- Delegación de eventos `change`
- Listeners HTMX (`afterSettle`, `afterSwap`, `load`)
- Inicializador centralizado

### PASO 2: Eliminar archivos redundantes

**Eliminar:**
- `catalogo_integration_v2.js` (funcionalidad movida a catalogo_service.js)
- `catalogo_init.js` (funcionalidad movida a catalogo_service.js)
- `catalogo_htmx_reactivator.js` (funcionalidad movida a catalogo_service.js)

**Mantener:**
- `catalogo_service.js` (consolidado)
- `catalogo_audit.js` (auditoría, no duplica funcionalidad)

### PASO 3: Consolidar exportaciones

```javascript
// Único namespace
w.CatalogoModule = {
  service: CatalogoService,
  sync: sincronizarBuscadorNIIF,
  audit: { runFullAudit, checkDOMElements, ... },
  debug: () => { /* debug info */ }
};
```

### PASO 4: Actualizar assets_cuentas.html

**Antes:**
```html
<script src="{% static 'contabilidad/js/catalogo_service.js' %}"></script>
<script src="{% static 'contabilidad/js/catalogo_integration_v2.js' %}"></script>
<script src="{% static 'contabilidad/js/catalogo_audit.js' %}"></script>
<script src="{% static 'contabilidad/js/catalogo_init.js' %}"></script>
<script src="{% static 'contabilidad/js/catalogo_htmx_reactivator.js' %}"></script>
```

**Después:**
```html
<script src="{% static 'contabilidad/js/catalogo_service.js' %}"></script>
<script src="{% static 'contabilidad/js/catalogo_audit.js' %}"></script>
```

---

## 📋 CHECKLIST DE LIMPIEZA

- [ ] Consolidar toda la lógica de sincronización en `catalogo_service.js`
- [ ] Eliminar `catalogo_integration_v2.js`
- [ ] Eliminar `catalogo_init.js`
- [ ] Eliminar `catalogo_htmx_reactivator.js`
- [ ] Actualizar `assets_cuentas.html` (solo 2 scripts)
- [ ] Verificar que `catalogo_audit.js` no tenga duplicaciones
- [ ] Crear namespace único `w.CatalogoModule`
- [ ] Ejecutar auditoría final: `CatalogoAudit.runFullAudit()`
- [ ] Probar sincronización completa en navegador

---

## 🎯 BENEFICIOS DE LA LIMPIEZA

| Aspecto | Antes | Después |
|--------|-------|---------|
| **Scripts cargados** | 5 | 2 |
| **Namespaces globales** | 5 | 1 |
| **Listeners HTMX** | 3x duplicados | 1x único |
| **Inicializadores** | 3 | 1 |
| **Código repetido** | 3 instancias | 0 |
| **Líneas de código** | 1000+ | ~500 |
| **Complejidad** | Alta | Baja |
| **Mantenibilidad** | Difícil | Fácil |

---

## 📝 ESTRUCTURA FINAL PROPUESTA

```
apps/tenant/contabilidad/static/contabilidad/js/
├── catalogo_service.js (CONSOLIDADO - 450 líneas)
│   ├── CatalogoService (API calls)
│   ├── sincronizarBuscadorNIIF() (Sincronización)
│   ├── Delegación de eventos (change, click)
│   ├── Listeners HTMX (afterSettle, afterSwap, load)
│   └── Inicializador centralizado
│
├── catalogo_audit.js (MANTENIDO - 300 líneas)
│   ├── Auditoría con 6 checks
│   ├── Debugging en consola
│   └── Funciones de testing
│
├── contabilidad.js (REVISAR)
├── asiento/
├── cuenta/
└── periodo/
```

---

## ⚠️ PRÓXIMOS PASOS

1. **Revisar** este reporte
2. **Confirmar** que deseas proceder con la limpieza
3. **Ejecutar** la consolidación en catalogo_service.js
4. **Eliminar** archivos redundantes
5. **Actualizar** assets_cuentas.html
6. **Probar** sincronización completa

---

**Estado:** 🔍 Auditoría completada  
**Versión:** v2.61 - Análisis de código  
**Última actualización:** Marzo 9, 2026
