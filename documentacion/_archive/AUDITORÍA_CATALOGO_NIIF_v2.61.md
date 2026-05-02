# 🔍 AUDITORÍA PROFUNDA: Sincronización Catálogo NIIF v2.61

## Problema Reportado
El campo **"Buscar en Catálogo NIIF"** permanece **deshabilitado** incluso después de seleccionar un tipo en el campo **"Tipo"**.

---

## Auditoría Paso a Paso

### PASO 1: Verificar que los Scripts Estén Cargados

1. Abre el navegador en la página de **Crear Cuenta Contable**
2. Presiona **F12** para abrir la consola del navegador
3. Ejecuta este comando en la consola:

```javascript
CatalogoAudit.runFullAudit()
```

**Resultado esperado:**
- Debe aparecer un reporte completo con ✅ en todos los checks
- Si ves ❌, significa que falta cargar algún script

---

### PASO 2: Verificar Elementos del DOM

En la consola, ejecuta:

```javascript
CatalogoAudit.checkDOMElements()
```

**Resultado esperado:**
```
✅ select[name="tipo"]: select-tipo-cuenta
✅ #input-buscar-catalogo: (disabled=true)
✅ #btn-buscar-catalogo: (disabled=true)
✅ #catalogo-resultados
✅ form: form-cuenta-crear
```

Si ves ❌ en alguno, significa que el template no tiene los IDs correctos.

---

### PASO 3: Probar Sincronización Manual

En la consola, ejecuta:

```javascript
CatalogoAudit.testManualSync()
```

Esto simulará un cambio de tipo a "ACTIVO" y verificará si el buscador se habilita.

**Resultado esperado:**
```
📝 Simulando cambio de tipo a "ACTIVO"...
Resultado después del cambio:
  - Tipo: "ACTIVO"
  - Buscador disabled: false
  - Placeholder: "Buscar en cuentas de Activo..."
  - ¿Se habilitó?: ✅
```

Si ves ❌, la delegación de eventos no está funcionando.

---

### PASO 4: Forzar Sincronización Manualmente

Si el buscador no se habilita automáticamente, ejecuta:

```javascript
CatalogoAudit.forceSyncNow()
```

Esto disparará manualmente el evento `change` en el select de tipo.

---

### PASO 5: Ver Estado Actual del Sistema

En la consola, ejecuta:

```javascript
CatalogoIntegration.debug()
```

**Resultado esperado:**
```javascript
{
  selectTipo: "✅ select-tipo-cuenta = 'ACTIVO'",
  inputBuscador: "✅ input-buscar-catalogo (disabled=false)",
  btnBuscador: "✅ btn-buscar-catalogo (disabled=false)",
  resultados: "✅ catalogo-resultados"
}
```

---

## Solución de Problemas

### ❌ Problema: "CatalogoAudit is not defined"

**Causa:** El script `catalogo_audit.js` no se cargó.

**Solución:**
1. Verifica que `catalogo_audit.js` esté en: `apps/tenant/contabilidad/static/contabilidad/js/`
2. Verifica que `assets_cuentas.html` incluya: `<script src="{% static 'contabilidad/js/catalogo_audit.js' %}"></script>`
3. Recarga la página (Ctrl+F5 para limpiar caché)

---

### ❌ Problema: "select[name='tipo']" no encontrado

**Causa:** El template tiene un ID diferente para el select.

**Solución:**
1. Abre el inspector (F12 → Elements)
2. Busca el select de tipo
3. Verifica su `id` y `name`
4. Actualiza `catalogo_integration_v2.js` línea 27 con los selectores correctos

---

### ❌ Problema: El buscador no se habilita al cambiar tipo

**Causa:** La delegación de eventos no está escuchando cambios.

**Solución:**
1. En la consola, ejecuta: `CatalogoAudit.forceSyncNow()`
2. Si se habilita manualmente, el problema es que el evento `change` no se dispara
3. Verifica que el select tenga el atributo `name="tipo"`
4. Recarga la página

---

### ❌ Problema: HTMX no está definido

**Causa:** HTMX no se cargó antes que los scripts de catálogo.

**Solución:**
1. Verifica que `assets_core.html` incluya HTMX
2. Verifica el orden de carga en `assets_cuentas.html`:
   ```html
   {% include 'tenant/core/partials/assets_core.html' %}  <!-- HTMX aquí -->
   <script src="{% static 'contabilidad/js/catalogo_service.js' %}"></script>
   <script src="{% static 'contabilidad/js/catalogo_integration_v2.js' %}"></script>
   ```

---

## Checklist de Verificación

- [ ] Script `catalogo_audit.js` existe en `apps/tenant/contabilidad/static/contabilidad/js/`
- [ ] Script está incluido en `assets_cuentas.html`
- [ ] `CatalogoAudit.runFullAudit()` ejecuta sin errores
- [ ] Todos los elementos del DOM se encuentran (✅ en todos los checks)
- [ ] Al cambiar tipo, el buscador se habilita
- [ ] El placeholder del buscador actualiza dinámicamente
- [ ] El botón de búsqueda se habilita junto con el input
- [ ] Al limpiar el tipo, el buscador se deshabilita

---

## Comandos Útiles para Consola

```javascript
// Ver estado completo
CatalogoAudit.runFullAudit()

// Ver elementos del DOM
CatalogoAudit.checkDOMElements()

// Ver estado del buscador
CatalogoAudit.checkSearcherState()

// Probar sincronización
CatalogoAudit.testManualSync()

// Forzar sincronización
CatalogoAudit.forceSyncNow()

// Habilitar buscador manualmente (para testing)
CatalogoAudit.toggleSearcher(true)

// Deshabilitar buscador manualmente
CatalogoAudit.toggleSearcher(false)

// Ver estado actual del sistema
CatalogoIntegration.debug()
```

---

## Flujo Esperado (Correcto)

```
1. Usuario abre "Crear Cuenta Contable"
   ↓
2. Modal se carga vía HTMX
   ↓
3. catalogo_integration_v2.js detecta htmx:afterSwap
   ↓
4. Inicializa estado del buscador (deshabilitado)
   ↓
5. Usuario selecciona "ACTIVO" en select tipo
   ↓
6. Evento 'change' dispara en delegación global
   ↓
7. toggleBuscadorByTipo("ACTIVO") se ejecuta
   ↓
8. ✅ Input se habilita
   ✅ Placeholder: "Buscar en cuentas de Activo..."
   ✅ Botón se habilita
   ✅ Focus automático en input
   ↓
9. Usuario escribe "CAJA" y busca
   ↓
10. API recibe: ?search=CAJA&tipo=ACTIVO
    ↓
11. Resultados filtrados se muestran
```

---

## Archivos Involucrados

| Archivo | Propósito |
|---------|-----------|
| `cuenta_offcanvas_form.html` | Template del formulario (IDs: select-tipo-cuenta, input-buscar-catalogo) |
| `catalogo_service.js` | Servicio de búsqueda en catálogo (API calls) |
| `catalogo_integration_v2.js` | Sincronización robusta (delegación de eventos) |
| `catalogo_audit.js` | Script de auditoría (debugging) |
| `assets_cuentas.html` | Orden de carga de scripts |

---

## Próximos Pasos

1. **Ejecuta la auditoría:** `CatalogoAudit.runFullAudit()` en consola
2. **Identifica qué check falla** (si alguno)
3. **Aplica la solución correspondiente** según la sección "Solución de Problemas"
4. **Recarga la página** y prueba nuevamente
5. **Reporta resultados** con el output de la auditoría

---

**Última actualización:** v2.61 - Auditoría Profunda  
**Estado:** Listo para debugging
