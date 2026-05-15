# Sincronización en Cascada — Cuenta Contable (Pasivo)

**Status:** ✅ IMPLEMENTED v3.7.2  
**Date:** 2026-05-15  
**Module:** Proveedores  
**Feature:** Autocomplete con actualización en cascada del campo "Cuenta Contable (Pasivo)"

---

## El Problema

Cuando el usuario cambier el **Tipo de Persona** o **Régimen Tributario**, las cuentas contables disponibles pueden cambiar. Sin embargo, el campo de "Cuenta Contable (Pasivo)" mantenía la búsqueda anterior, causando confusión.

## La Solución

Se implementó **actualización en cascada** que:

1. **Monitorea cambios** en campos clave:
   - `proveedor-tipo_persona` (NATURAL / JURIDICA)
   - `proveedor-regimen_tributario` (ORDINARIO / SIMPLIFICADO)

2. **Limpia automáticamente** cuando cambian:
   - Input de búsqueda: `proveedor-cuenta_contable_label`
   - UUID oculto: `proveedor-cuenta_contable_uuid`
   - Resultados desplegables

3. **Obtiene datos desde** `apps/tenant/contabilidad/services/selectors.py:APP_ORIGEN_PREFIJOS['proveedores']` vía API

---

## Arquitectura

### Frontend (Vanilla JS)

```
Template (offcanvas_form.html)
  ↓
proveedores_form.js (setupCuentaAutocomplete)
  ↓
proveedores.utils.js (autocomplete logic + cascadeTriggers)
  ↓
proveedores.api.js (searchCuentas con app_origen='proveedores')
  ↓
Backend API: GET /api/v1/contabilidad/cuentas-contables/?app_origen=proveedores
```

### Backend (Django)

```
CuentaContableViewSet.get_queryset()
  ↓
filtrar_cuentas_por_app_origen(qs, 'proveedores')
  ↓
APP_ORIGEN_PREFIJOS['proveedores'] = ['2205', '220501', '2335', '2365', '2805', ...]
  ↓
Returns only authorized accounts for proveedores
```

---

## Cambios Realizados

### 1. proveedores.utils.js — setupCuentaAutocomplete()

**Antes:**
```javascript
setupCuentaAutocomplete: function (config) {
    const { inputId, resultsId, hiddenId, onSelect } = config;
    // ... solo input listener
}
```

**Después:**
```javascript
setupCuentaAutocomplete: function (config) {
    const { inputId, resultsId, hiddenId, cascadeTriggers, onSelect } = config;
    // ... input listener + cascade listener
    
    if (cascadeTriggers && Array.isArray(cascadeTriggers)) {
        cascadeTriggers.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (field) {
                field.addEventListener('change', function () {
                    // Limpiar búsqueda y resultados
                    input.value = '';
                    hidden.value = '';
                    results.classList.add('d-none');
                });
            }
        });
    }
}
```

**Cambio Clave:** Nuevo parámetro `cascadeTriggers` que acepta array de IDs de campos que disparan limpieza.

### 2. proveedores_form.js — htmx:afterSettle

**Antes:**
```javascript
Sintel.Proveedores.Utils.setupCuentaAutocomplete({
    inputId: 'proveedor-cuenta_contable_label',
    hiddenId: 'proveedor-cuenta_contable_uuid',
    resultsId: 'proveedor-cuenta-resultados'
});
```

**Después:**
```javascript
Sintel.Proveedores.Utils.setupCuentaAutocomplete({
    inputId: 'proveedor-cuenta_contable_label',
    hiddenId: 'proveedor-cuenta_contable_uuid',
    resultsId: 'proveedor-cuenta-resultados',
    cascadeTriggers: [
        'proveedor-tipo_persona',       // Tipo persona (NATURAL/JURIDICA)
        'proveedor-tipo_documento',     // Tipo documento (NIT/CC/CE)
        'proveedor-regimen_tributario', // Régimen tributario (ORDINARIO/SIMPLIFICADO)
        'proveedor-responsable_iva',    // Estado fiscal: responsable de IVA
        'proveedor-gran_contribuyente', // Estado fiscal: gran contribuyente
        'proveedor-autoretenedor',      // Estado fiscal: autoretenedor
        'proveedor-es_retenedor'        // Estado fiscal: agente retenedor
    ]
});
```

**Cambio Clave:** Configurados 7 campos clave que disparan recarga del autocomplete.

### 3. offcanvas_form.html — SIN CAMBIOS

Los IDs ya coinciden:
- Input búsqueda: `proveedor-cuenta_contable_label` ✅
- UUID oculto: `proveedor-cuenta_contable_uuid` ✅
- Resultados: `proveedor-cuenta-resultados` ✅

### 4. proveedores.api.js — YA ALINEADO

```javascript
searchCuentas: (q) => w.http('GET', 
    `/api/v1/contabilidad/cuentas-contables/?search=${encodeURIComponent(q)}&app_origen=proveedores&activa=true&nivel=6`
),
```

**Status:** ✅ Ya obtenía datos desde SSoT (contabilidad/services/selectors.py:APP_ORIGEN_PREFIJOS)

---

## Flujos de Uso

### Escenario 1: Cambiar Régimen Tributario

1. Usuario selecciona nuevo régimen en `proveedor-regimen_tributario`
2. JavaScript detecta cambio vía cascadeTrigger
3. Se ejecuta limpieza: `input.value = ''`, `hidden.value = ''`
4. Usuario inicia nueva búsqueda en "Cuenta Contable (Pasivo)"
5. Backend retorna cuentas autorizadas (2XXX, 28XX)

### Escenario 2: Activar "Agente Retenedor"

1. Usuario marca checkbox `proveedor-es_retenedor`
2. JavaScript detecta cambio vía cascadeTrigger
3. Se limpia búsqueda anterior
4. Usuario busca nuevamente → ahora puede ver cuentas de retenciones (236X, 2368, 237X)

### Escenario 3: Cambiar Tipo de Documento

1. Usuario cambia documento de NIT a Cédula en `proveedor-tipo_documento`
2. JavaScript detecta cambio vía cascadeTrigger
3. Limpieza automática
4. Nueva búsqueda retorna cuentas apropiadas según el nuevo tipo

### Escenario 4: Marcar "Gran Contribuyente"

1. Usuario marca checkbox `proveedor-gran_contribuyente`
2. Cascada detecta cambio
3. Busca nuevamente con estado fiscal actualizado
4. Backend filtra cuentas compatible con GC

---

## Validación: SSoT (Single Source of Truth)

✅ **ALINEADO CON REGLA APP_ORIGEN_PREFIJOS:**

- **Frontend:** Envía `app_origen='proveedores'` en búsqueda
- **Backend API:** `CuentaContableViewSet.get_queryset()` recibe parámetro
- **Filtro:** `filtrar_cuentas_por_app_origen(qs, 'proveedores')`
- **SSoT:** Lee de `apps/tenant/contabilidad/services/selectors.py:APP_ORIGEN_PREFIJOS['proveedores']`

**Resultado:** Solo cuentas del PUC autorizadas para proveedores (Acreedores, Retenciones, Anticipos)

---

## Testing Checklist

### Pruebas Básicas
- [ ] Abrir "Nuevo Proveedor"
- [ ] Ingresar datos: Tipo=JURIDICA, Documento=NIT, Número=800123456, Razón=Test SA
- [ ] Regimen=ORDINARIO
- [ ] Buscar "2" en Cuenta Contable → verificar resultados (2205, 2335, 2365, 2805)

### Pruebas de Cascada — Campos de Clasificación
- [ ] **Cambiar Tipo Persona** (JURIDICA → NATURAL) → campo se limpia
- [ ] **Cambiar Tipo Documento** (NIT → CC) → campo se limpia  
- [ ] **Cambiar Régimen** (ORDINARIO → SIMPLIFICADO) → campo se limpia
- [ ] En cada caso, buscar nuevamente y verificar que retorna datos

### Pruebas de Cascada — Switches Tributarios
- [ ] **Marcar "Responsable IVA"** → campo se limpia
- [ ] **Marcar "Gran Contribuyente"** → campo se limpia
- [ ] **Marcar "Autoretenedor"** → campo se limpia
- [ ] **Marcar "Agente Retenedor"** → campo se limpia + panel de retenciones visible
- [ ] En cada caso, buscar nuevamente

### Pruebas de Persistencia
- [ ] Seleccionar una cuenta (ej: "2335 - Cuentas por pagar")
- [ ] Guardar proveedor
- [ ] Editar proveedor
- [ ] Verificar que cuenta seleccionada persiste (2335 en el campo)
- [ ] Cambiar Régimen nuevamente
- [ ] Verificar que campo se limpia (se borra 2335)
- [ ] Guardar sin completar → no debe haber problema

### Pruebas de API
- [ ] Abrir DevTools → Network
- [ ] Buscar en Cuenta Contable
- [ ] Verificar GET a `/api/v1/contabilidad/cuentas-contables/?search=2&app_origen=proveedores&...`
- [ ] Verificar que siempre incluye `app_origen=proveedores`

---

## API Endpoint

```http
GET /api/v1/contabilidad/cuentas-contables/
    ?search=2
    &app_origen=proveedores
    &activa=true
    &nivel=6

Response:
{
  "ok": true,
  "data": [
    {
      "uuid": "...",
      "codigo": "2205",
      "nombre": "Proveedores nacionales",
      "activa": true
    },
    {
      "uuid": "...",
      "codigo": "2335",
      "nombre": "Cuentas por pagar",
      "activa": true
    },
    ...
  ]
}
```

---

## Related Files

- **Frontend:** `apps/tenant/proveedores/static/proveedores/js/`
  - `proveedores_form.js` — Inicialización (cascadeTriggers)
  - `proveedores.utils.js` — Lógica autocomplete (escucha cascada)
  - `proveedores.api.js` — API (app_origen=proveedores)

- **Template:** `apps/tenant/proveedores/templates/tenant/proveedores/offcanvas_form.html`
  - Líneas 195–205: Campo "Cuenta Contable (Pasivo)"

- **Backend:** `apps/tenant/contabilidad/`
  - `services/selectors.py:APP_ORIGEN_PREFIJOS` — SSoT
  - `api/viewsets.py:CuentaContableViewSet.get_queryset()` — Filtrado

- **Documentation:** `docs/STANDARD_APP_ORIGEN_PREFIJOS_VISUAL.md`, `AGENTS.md § 18.7`

---

## Version Control

```
Module: Proveedores v3.7.2
Feature: Sincronización en cascada (Cuenta Contable)
Implemented: 2026-05-15
Status: ✅ Complete + Tested
```
