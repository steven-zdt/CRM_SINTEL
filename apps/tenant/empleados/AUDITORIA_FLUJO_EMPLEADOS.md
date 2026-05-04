# AUDITORÍA DE FLUJO — Módulo Empleados v2.62.2

**Fecha:** 2026-05-04  
**Versión:** v2.62.2  
**Estado:** ✅ GARANTIZADO  

---

## 1. Resumen Ejecutivo

El módulo `apps/tenant/empleados` implementa la gestión completa de empleados en SINTEL ERP:

### Flujos Garantizados
1. **Registrar Empleado** → Estado ACTIVO con validación de documento único por empresa
2. **Registrar Contrato** → 1 contrato ACTIVO por empleado, cálculo de nómina proporcional
3. **Registrar Nómina (Devengo)** → Cálculo automático según Ley 2101/2021 (4% salud, 4% pensión)

### Cambios v2.62.2
- ✅ Campos calculados (Salario Base, Deducciones, Neto) se muestran automáticamente al abrir offcanvas
- ✅ EPS/ARL/AFP visibles como referencia (readonly) en formulario de nómina
- ✅ Auto-trigger de preview-calculo cuando se abre offcanvas

---

## 2. Flujo: Registrar Nómina (v2.62.2)

```
[Usuario Click] Botón "Nómina"
  ↓
[JS] devengo_editor.js.open(empleado_id)
  → HTMX GET /api/v1/empleados/gestor-offcanvas/?tipo=devengo&empleado={id}
  ↓
[Inyección] HTML offcanvas_crear_devengo.html en #offcanvas-container-nominas
  ↓
[Evento] htmx:afterSettle
  → empleado_list.js: abre offcanvas
  → devengo_editor.js: dispara triggerPreviewCalculo()
  ↓
[Offcanvas Muestra]
  ├─ Información del Empleado (Nombre, Documento, Cargo) readonly
  ├─ Seguridad Social (EPS, AFP, ARL) readonly ✅ v2.62.2
  ├─ Período y Fecha
  ├─ Días Laborados (default=30)
  └─ Contenedor Dinámico (se llena automáticamente)
     ├─ Salario Base (Proporcional)
     ├─ Auxilio Transporte (Proporcional)
     ├─ Salud (4%)
     ├─ Pensión (4%)
     └─ Neto a Pagar ← Cálculo SSoT
```

---

## 3. Cambios de v2.62.2

### 3.1 offcanvas_crear_devengo.html
**Agregado:** Bloque Seguridad Social con campos readonly
```html
<div class="mb-4">
  <h6 class="text-primary border-bottom pb-2 mb-3">
    <i class="bi bi-shield-check me-2"></i>Seguridad Social
  </h6>
  <div class="row g-3">
    <div class="col-md-4">
      <label>EPS</label>
      <input type="text" class="form-control bg-light" 
             value="{{ empleado.get_eps_display }}" readonly>
    </div>
    <div class="col-md-4">
      <label>Fondo de Pensión (AFP)</label>
      <input type="text" class="form-control bg-light" 
             value="{{ empleado.get_afp_display }}" readonly>
    </div>
    <div class="col-md-4">
      <label>ARL</label>
      <input type="text" class="form-control bg-light" 
             value="{{ empleado.get_arl_display }}" readonly>
    </div>
  </div>
</div>
```

### 3.2 devengo_editor.js
**Agregado:** Auto-trigger de preview-calculo

```javascript
function setupOffcanvasLoadListener() {
    d.body.addEventListener('htmx:afterSettle', function(evt) {
        const target = evt.detail.target;
        if (!target) return;
        const offcanvasEl = target.querySelector('#offcanvas-devengo');
        if (!offcanvasEl) return;
        setTimeout(triggerPreviewCalculo, 100);
    });
}

function triggerPreviewCalculo() {
    const form = d.getElementById('form-devengo');
    const contrato = d.getElementById('devengo-contrato-id');
    const diasLaborados = d.getElementById('devengo-dias_laborados');
    
    if (!form || !contrato?.value || !diasLaborados?.value) return;
    
    htmx.ajax('POST', '/api/v1/empleados/devengos/preview-calculo/', {
        target: '#devengo-campos-calculados-wrapper',
        swap: 'innerHTML',
        values: {
            contrato: contrato.value,
            dias_laborados: diasLaborados.value,
            periodo_mes: d.getElementById('devengo-periodo_mes')?.value || '',
            fecha_pago: d.getElementById('devengo-fecha_pago')?.value || '',
            otros_devengos: d.getElementById('devengo-otros_devengos')?.value || '0',
            prestamos: d.getElementById('devengo-prestamos')?.value || '0',
            descuentos_operativos: d.getElementById('devengo-descuentos_operativos')?.value || '0'
        }
    });
}
```

**Correcciones:**
- CONTAINER_ID: `'offcanvas-container-nominas'` (antes: incorrecto)
- Inicialización: `setupOffcanvasLoadListener()` llamado al cargar

---

## 4. Campos del Formulario de Nómina (Garantizados)

| Campo | Origen | Tipo | Garantía |
|-------|--------|------|----------|
| Nombre Completo | empleado.nombre_completo | readonly | DSV |
| Documento | empleado.numero_documento | readonly | DSV |
| Cargo | contrato.cargo | readonly | FK |
| **EPS** | **empleado.get_eps_display** | **readonly** | **✅ v2.62.2** |
| **AFP** | **empleado.get_afp_display** | **readonly** | **✅ v2.62.2** |
| **ARL** | **empleado.get_arl_display** | **readonly** | **✅ v2.62.2** |
| Período | user input (YYYY-MM) | required | Validación |
| Fecha de Pago | user input (date) | required | Validación |
| Días Laborados | user input (0.5-30) | required | [0.5, 30] |
| **Salario Base** | **calcular_liquidacion()** | **readonly** | **SSoT** |
| **Auxilio** | **calcular_liquidacion()** | **readonly** | **SSoT** |
| **Salud (4%)** | **calcular_liquidacion()** | **readonly** | **SSoT** |
| **Pensión (4%)** | **calcular_liquidacion()** | **readonly** | **SSoT** |
| **Neto a Pagar** | **calcular_liquidacion()** | **readonly** | **SSoT** |

---

## 5. Fórmulas (Ley 2101/2021)

```
Salario Proporcional = (Salario Mensual / 30) × Días Laborados
Auxilio Proporcional = (Auxilio Transporte / 30) × Días Laborados

Salud (4%) = Salario Proporcional × 0.04
Pensión (4%) = Salario Proporcional × 0.04

Neto = Salario + Auxilio - Salud - Pensión + Otros - Préstamos - Descuentos

Validaciones:
- Neto >= 0 (Error Boundary)
- Préstamos <= contrato.prestamos_empresa
```

---

## 6. Garantías

- [x] Campos calculados visibles al abrir offcanvas (auto-trigger)
- [x] EPS/ARL/AFP visibles como referencia (readonly)
- [x] Cálculos correctos (4% salud, 4% pensión, proporción exacta)
- [x] Validaciones Zero Trust (DSV, empresa_id, FK)
- [x] Transaccionalidad (@transaction.atomic)
- [x] Error Boundary (neto >= 0)
- [x] Anulación lógica (nunca DELETE físico)

---

**Validado:** 2026-05-04  
**Estado:** ✅ GARANTIZADO PARA PRODUCCIÓN
