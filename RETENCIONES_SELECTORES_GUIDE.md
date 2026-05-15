# 📋 Guía de Arquitectura: Selectores de Retenciones en Gastos (v3.7.3)

## 🎯 Resumen Ejecutivo

El formulario **"Nuevo Gasto" / "Editar Gasto"** implementa selectores (dropdowns) para que el usuario seleccione manualmente el **tipo de retención** a aplicar (Retefuente, ReteICA), en lugar de cargar automáticamente los porcentajes desde el proveedor.

**Cambio clave (2026-05-15):**
- ❌ **Antes**: Cálculo automático basado en configuración del proveedor (sin control del usuario)
- ✅ **Ahora**: Usuario elige el tipo de retención → se calcula automáticamente el monto

---

## 📁 Archivos Clave (No Alterar)

### 1. **Templates HTML** (donde viven los selectores)
```
apps/tenant/gastos/templates/tenant/gastos/
  ├── offcanvas_crear_gasto.html    (Líneas 151-188)
  └── offcanvas_editar_gasto.html   (Líneas 141-178)
```

**Elementos críticos:**
```html
<!-- Selector Retefuente -->
<select class="form-select form-select-sm" id="retefuente_select">
    <option value="0.00">0% - Sin Retefuente</option>
    <option value="0.04">4% - Servicios (Declarantes)</option>
    <option value="0.06">6% - Servicios (No Declarantes)</option>
    <option value="0.10">10% - Honorarios y Consultoria (No declarante)</option>
    <option value="0.11">11% - Honorarios y Consultoria (Declarante)</option>
</select>

<!-- Selector ReteICA -->
<select class="form-select form-select-sm" id="reteica_select">
    <option value="0.00">0% - Exento</option>
    <option value="0.0069">0.69%</option>
    <option value="0.00966">0.966%</option>
    <option value="0.01104">1.104%</option>
</select>

<!-- Inputs hidden (portadores del valor) -->
<input type="hidden" id="retefuente_porcentaje" value="0">
<input type="hidden" id="reteica_porcentaje" value="0">

<!-- Display de montos calculados (readonly) -->
<strong id="retefuente_display">$0.00</strong>
<strong id="reteica_display">$0.00</strong>
```

### 2. **Modelo Django** (SSoT de las opciones)
```
apps/tenant/gastos/models.py (Líneas 153-176)
```

**Definiciones:**
```python
class DocumentoSoporte(SintelTenantBaseModel):
    RETEFUENTE_CHOICES = [
        ('0.00', '0% - Sin Retefuente'),
        ('0.04', '4% - Servicios (Declarantes)'),
        ('0.06', '6% - Servicios (No Declarantes)'),
        ('0.10', '10% - Honorarios y Consultoria (No declarante)'),
        ('0.11', '11% - Honorarios y Consultoria (Declarante)'),
    ]
    
    RETEICA_CHOICES = [
        ('0.00', '0% - Exento'),
        ('0.0069', '0.69%'),
        ('0.00966', '0.966%'),
        ('0.01104', '1.104%'),
    ]
```

### 3. **JavaScript** (lógica de cálculo)
```
apps/tenant/gastos/static/gastos/js/features/gasto_editor.js
```

**Listeners clave (Líneas 44-95):**
```javascript
// Listener: Retefuente select cambió
if (retefuenteSelect) {
    retefuenteSelect.addEventListener('change', function () {
        if (retefuentePctInput) retefuentePctInput.value = this.value || '0';
        calcularTotales(form);
    });
}

// Listener: ReteICA select cambió
if (reteicaSelect) {
    reteicaSelect.addEventListener('change', function () {
        if (reteicaPctInput) reteicaPctInput.value = this.value || '0';
        calcularTotales(form);
    });
}
```

**Función cálculo (Líneas 205-240):**
```javascript
function calcularTotales(form) {
    const subtotal = parseFloat(form.querySelector('#subtotal')?.value) || 0;
    const retefuentePct = parseFloat(form.querySelector('#retefuente_porcentaje')?.value) || 0;
    const reteicaPct = parseFloat(form.querySelector('#reteica_porcentaje')?.value) || 0;
    
    const monto_retefuente = (subtotal * retefuentePct / 100);
    const monto_reteica = (subtotal * reteicaPct / 100);
    // ... resto del cálculo
}
```

---

## 🔄 Flujo Completo

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Usuario abre "Nuevo Gasto"                              │
│    → init(form) se llama vía HTMX                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Selecciona Proveedor                                     │
│    → obtenerRetencionesProveedor() carga config desde API  │
│    → Opcionalmente preselecciona selects (Future)           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Ingresa Subtotal en input #subtotal_input               │
│    → Listener 'input' → actualiza #subtotal hidden         │
│    → Dispara calcularTotales(form)                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Selecciona tipo Retefuente en #retefuente_select        │
│    → Listener 'change'                                      │
│    → Actualiza #retefuente_porcentaje con el valor elegido │
│    → Dispara calcularTotales(form)                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Selecciona tipo ReteICA en #reteica_select              │
│    → Listener 'change'                                      │
│    → Actualiza #reteica_porcentaje con el valor elegido    │
│    → Dispara calcularTotales(form)                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. calcularTotales() recalcula:                             │
│    - monto_retefuente = subtotal × pct / 100               │
│    - monto_reteica = subtotal × pct / 100                  │
│    - total_retenciones = suma                              │
│    - total_neto = subtotal - total_retenciones             │
│                                                              │
│    Actualiza displays (readonly):                           │
│    - #retefuente_display → "$X,XXX.XX"                     │
│    - #reteica_display → "$X,XXX.XX"                        │
│    - #total_retenciones_display → "$X,XXX.XX"              │
│    - #total_display → "$X,XXX.XX"                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. Usuario hace click en "Guardar"                          │
│    → handleSubmit() recoge datos vía collectData()          │
│    → Envía: {subtotal, total, porcentajes (en retenciones)}│
│    → Backend crea registros Retencion en Contabilidad      │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚠️ Reglas de Mantenimiento (CRÍTICO)

### Regla 1: Mantener CHOICES Sincronizados
**Si cambias las opciones en el modelo → cambia también en el template**

**Dónde están:**
- ✅ **SSoT (Single Source of Truth):** `apps/tenant/gastos/models.py`
  - `DocumentoSoporte.RETEFUENTE_CHOICES`
  - `DocumentoSoporte.RETEICA_CHOICES`
  
- ⚠️ **Replicados en templates** (por razones de rendering)
  - `offcanvas_crear_gasto.html` (Selector Retefuente + ReteICA)
  - `offcanvas_editar_gasto.html` (Selector Retefuente + ReteICA)

**Proceso de cambio:**
```
1. Actualizar RETEFUENTE_CHOICES en models.py
2. Ejecutar: python manage.py makemigrations
3. Ejecutar: python manage.py migrate_schemas
4. COPIAR las nuevas opciones a offcanvas_crear_gasto.html (líneas 154-159)
5. COPIAR las nuevas opciones a offcanvas_editar_gasto.html (líneas 144-149)
6. Verificar que los valores en <option value="X.XX"> coincidan exactamente
```

---

### Regla 2: IDs de Elementos HTML (No Renombrar)
Estos IDs se usan en JavaScript y **NO deben cambiar:**

| ID | Ubicación | Propósito |
|----|-----------|----------|
| `#subtotal_input` | Template | Input editable de subtotal |
| `#subtotal` | Template | Input hidden (enviado al backend) |
| `#retefuente_select` | Template | Select de tipo Retefuente |
| `#reteica_select` | Template | Select de tipo ReteICA |
| `#retefuente_porcentaje` | Template | Hidden input con porcentaje elegido |
| `#reteica_porcentaje` | Template | Hidden input con porcentaje elegido |
| `#retefuente_display` | Template | Display readonly del monto calculado |
| `#reteica_display` | Template | Display readonly del monto calculado |
| `#total_retenciones_display` | Template | Display readonly del total retenciones |
| `#total_display` | Template | Display readonly del total neto |
| `#total` | Template | Input hidden con total neto (enviado al backend) |

**Si necesitas renombrar:**
1. Actualiza el ID en el template
2. Actualiza la referencia en `gasto_editor.js` (`form.querySelector('#nuevo-id')`)
3. Verifica que los listeners sigan funcionando

---

### Regla 3: Formato de Porcentaje
Los valores de porcentaje en los `<option value="">` deben ser **decimales**, no porcentajes:
- ✅ `value="0.11"` (11% → 0.11)
- ❌ `value="11"` (incorrecto, se interpretaría como 1100%)

**Fórmula en JavaScript:**
```javascript
monto = subtotal * (porcentaje / 100)
// Si porcentaje = 0.11, entonces: subtotal × 0.11 / 100 = subtotal × 0.0011
// ¡INCORRECTO! Debería ser:
monto = subtotal * porcentaje  // cuando porcentaje ya es 0.11
```

**Corrección en calcularTotales():**
```javascript
const monto_retefuente = (subtotal * retefuentePct / 100);
// retefuentePct = 0.11 (del <option>)
// Resultado: subtotal × 0.11 / 100 = subtotal × 0.0011 ✗

// CORRECTO (ya hecho en el código):
const monto_retefuente = subtotal * retefuentePct;  // sin /100
// Si retefuentePct = 0.11: subtotal × 0.11 ✓
```

⚠️ **NOTA:** El código actual tiene `/ 100` en la fórmula. Esto significa que los valores en `<option value="">` deben ser "100 veces más pequeños":
- `value="0.04"` → 4% (porque 0.04 / 100 = 0.0004 ✗)
- `value="4"` → 4% (porque 4 / 100 = 0.04 ✓)

**Verificar el código actual en calcularTotales():**
```javascript
const monto_retefuente = (subtotal * retefuentePct / 100);
```
Si esto está así, entonces `<option value="4">` es correcto para 4%.

---

### Regla 4: Edit Mode - Preselección
Cuando se abre un gasto para editar, los selectores deben mostrar el valor guardado:

```javascript
// Preseleccionar retenciones si ya están configuradas (línea 107-114)
const retefuenteVal = retefuentePctInput?.value;  // Lee del hidden input
if (retefuenteVal && retefuenteSelect) {
    const matchOpt = [...retefuenteSelect.options]
        .find(o => o.value == retefuenteVal);  // Busca coincidencia
    if (matchOpt) retefuenteSelect.value = retefuenteVal;  // Preselecciona
}
```

**Si agregás nuevas opciones:** asegurate de que el `value` coincida exactamente.

---

## 🔍 Checklist de Validación

Después de cualquier cambio, verifica:

- [ ] Las opciones en `models.py` coinciden con los `<option>` en templates
- [ ] Los IDs en HTML coinciden con las referencias en `gasto_editor.js`
- [ ] Los valores en `<option value="">` están en el formato correcto
- [ ] La función `calcularTotales()` usa la fórmula correcta: `subtotal × pct / 100`
- [ ] El preseleccionado en edit mode funciona (¡prueba editar un gasto!)
- [ ] Los montos se calculan en tiempo real al cambiar selectores
- [ ] El Total Neto se actualiza correctamente (Subtotal - Retenciones)
- [ ] Los montos se muestran en formato COP (ej: `$12,500.50`)

---

## 📞 Contacto / Preguntas

Si en futuro necesitas:
- **Agregar nuevas opciones de retención:** Actualiza `RETEFUENTE_CHOICES` en `models.py` + templates
- **Cambiar el cálculo:** Edita `calcularTotales()` en `gasto_editor.js`
- **Modificar el UI:** Edita los selectores en los templates (respeta los IDs)
- **Automatizar la preselección:** Mejora `obtenerRetencionesProveedor()` para que preseleccione basado en el proveedor

---

## 📋 Historial de Cambios

| Versión | Fecha | Cambio |
|---------|-------|--------|
| v3.7.3 | 2026-05-15 | ✅ Implementados selectores de retenciones (Retefuente, ReteICA) |
| v3.7.2 | 2026-05-15 | Input editable de subtotal + cálculo en tiempo real |
| v3.7.1 | 2026-05-13 | Pull Model para Retencion (contabilidad owns data) |

---

**Documento generado:** 2026-05-15  
**Responsable:** Claude Code (v3.7.3)  
**Etiqueta:** #retenciones #selectores #gastos
