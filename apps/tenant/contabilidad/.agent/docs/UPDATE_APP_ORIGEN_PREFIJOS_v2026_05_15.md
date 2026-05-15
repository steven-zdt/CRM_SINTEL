# Update: Códigos PUC para Todas las Apps de Negocio

**Fecha:** 2026-05-15  
**Archivo:** `apps/tenant/contabilidad/services/selectors.py`  
**Función:** `APP_ORIGEN_PREFIJOS` (líneas 88-177)  
**Estado:** ✅ COMPLETADO

---

## 📊 Resumen de Cambios

Se **actualizaron 5 de 6 apps** de negocio para agregar códigos PUC faltantes. Se mantuvo la estrategia de **códigos específicos detallados** pero se agregaron prefijos genéricos donde aplica.

### Matriz de Cambios

| App | Cambios | Códigos Agregados | Propósito |
|-----|---------|-------------------|-----------|
| **facturas** | +1 código | `418` | Descuentos en ventas |
| **clientes** | +4 códigos | `4135`, `413505`, `413510`, `1375` | Ingresos + Retenciones por cobrar |
| **gastos** | +2 prefijos | `51`, `6` | Gastos generales + Costos de venta |
| **empleados** | +1 prefijo | `51` | Gastos de personal genéricos |
| **inventario** | Sin cambios | (ya tiene `51` + `15`) | ✅ Ya actualizado |
| **proveedores** | +7 códigos | `2365`, `236505-540`, `236805`, `2368`, `2805`, `280505` | Retenciones + Anticipos |

---

## 🔄 Detalles por App

### 1. FACTURAS (Ventas) — 1 código agregado

**Antes:**
```python
'facturas': [
    '130505', '130510', '1305',        # Cartera
    '135515', '135517', '135518', '1355',  # Retenciones a favor
    '413505', '413510', '4135',        # Ingresos
    '4175',                            # Devoluciones
    '240805',                          # IVA generado
    '236505', '236510', '236515', '236525', '236540', '2365',
    '236805', '2368',                  # Retenciones por pagar
],
```

**Después:**
```python
'facturas': [
    '130505', '130510', '1305',        # Cartera
    '135515', '135517', '135518', '1355',  # Retenciones a favor
    '413505', '413510', '4135',        # Ingresos
    '4175', '418',  # ← AGREGADO: Descuentos en ventas
    '240805',                          # IVA generado
    '236505', '236510', '236515', '236525', '236540', '2365',
    '236805', '2368',                  # Retenciones por pagar
],
```

**Razón:** Permitir registro de descuentos, bonificaciones, y rebajas comerciales en el módulo de Ventas.

---

### 2. CLIENTES (Deudores) — 4 códigos agregados

**Antes:**
```python
'clientes': [
    '1305', '130505',  # Cartera clientes
],
```

**Después:**
```python
'clientes': [
    '1305', '130505',                  # Cartera clientes
    '4135', '413505', '413510',        # ← AGREGADO: Ingresos por ventas
    '1375',                            # ← AGREGADO: Retenciones por cobrar
],
```

**Razón:**
- **Ingresos (4135):** Vincular facturas de venta a la cartera de clientes (Pull Model)
- **Retenciones (1375):** Registrar retenciones en la fuente practicadas a clientes (retefuente, reteica, reteiva)

---

### 3. GASTOS — 2 prefijos agregados

**Antes:**
```python
'gastos': [
    '233505', '233550', '233595', '2335',  # Cuentas por pagar
    '236505', '236510', '236515', '236525', '236540', '2365',
    '236805', '2368',                      # Retenciones practicadas
    '240810',                              # IVA descontable
    '510506', '511005', '511505', '512010',
    '513505', '513520', '513525', '513530', '513535',
    '514510', '514525', '519525', '519530',
    '5110', '5115', '5120', '5130', '5135', '5140', '5145', '5150', '5155', '5195', '5199',
],
```

**Después:**
```python
'gastos': [
    '233505', '233550', '233595', '2335',  # Cuentas por pagar
    '236505', '236510', '236515', '236525', '236540', '2365',
    '236805', '2368',                      # Retenciones practicadas
    '240810',                              # IVA descontable
    '510506', '511005', '511505', '512010',
    '513505', '513520', '513525', '513530', '513535',
    '514510', '514525', '519525', '519530',
    '5110', '5115', '5120', '5130', '5135', '5140', '5145', '5150', '5155', '5195', '5199',
    '51',  # ← AGREGADO: Gastos generales (Clase 5)
    '6',   # ← AGREGADO: Costos de venta
],
```

**Razón:**
- **'51' (Clase 5 — Gastos):** Permitir registro de cualquier gasto administrativo u operacional
- **'6' (Clase 6 — Costos):** Si hay compra de inventario o costo de servicios desde gastos

---

### 4. EMPLEADOS (Nómina) — 1 prefijo agregado

**Antes:**
```python
'empleados': [
    '5105', '5110', '5115', '5120', '5125', '5130', '5140',  # Gastos específicos
    '510506', '510527', '510530', '510533', '510536', '510539', '510568', '510570',
    '2335', '233505', '233550', '233595',  # Cuentas por pagar
    '25',                                  # Obligaciones laborales
    '2370', '2375', '2380', '2590',        # Retenciones + otros pasivos
],
```

**Después:**
```python
'empleados': [
    '5105', '5110', '5115', '5120', '5125', '5130', '5140',  # Gastos específicos
    '510506', '510527', '510530', '510533', '510536', '510539', '510568', '510570',
    '51',  # ← AGREGADO: Gastos de personal genéricos
    '2335', '233505', '233550', '233595',  # Cuentas por pagar
    '25',                                  # Obligaciones laborales
    '2370', '2375', '2380', '2590',        # Retenciones + otros pasivos
],
```

**Razón:** Permitir registro de otros gastos de personal (bonificaciones especiales, auxilios, etc.) que no encajen en los códigos específicos.

---

### 5. INVENTARIO (Activos e Inventario) — Sin cambios

```python
'inventario': [
    '143505', '143510', '1435',        # Inventarios
    '613505', '613510', '6135',        # Costos de ventas
    '413505', '413510', '4135',        # Ingresos
    '51',                              # ✅ Depreciación (agregado en fix anterior)
    '15',                              # Activos fijos
],
```

**Estado:** ✅ Actualizado en fix anterior (2026-05-15 FIX_DEPRECIACION_ACCOUNT_SEARCH.md)

---

### 6. PROVEEDORES (Acreedores) — 7 códigos agregados

**Antes:**
```python
'proveedores': [
    '2205', '220501', '220505',        # Proveedores nacionales
    '2335', '233505', '233550', '233595',  # Cuentas por pagar
],
```

**Después:**
```python
'proveedores': [
    '2205', '220501', '220505',        # Proveedores nacionales
    '2335', '233505', '233550', '233595',  # Cuentas por pagar
    '2365', '236505', '236510', '236515', '236525', '236540',  # ← AGREGADO: Retenciones
    '236805', '2368',
    '2805', '280505',                  # ← AGREGADO: Anticipos recibidos
],
```

**Razón:**
- **Retenciones (2365):** Registrar retenciones practicadas a proveedores (retefuente, reteica, etc.)
- **Anticipos (2805):** Registrar anticipos recibidos de proveedores (pasivo)

---

## 🔗 Flujo: Cómo Funciona `APP_ORIGEN_PREFIJOS`

El diccionario **`APP_ORIGEN_PREFIJOS`** se usa en `filtrar_cuentas_por_app_origen()` para **limitar qué cuentas contables puede ver/acceder cada módulo**:

```
Frontend (Módulo X) [ej: inventario]
  ↓ Búsqueda de cuenta: /api/v1/contabilidad/cuentas-contables/?app_origen=inventario
  ↓
Backend (CuentaContableViewSet)
  ↓ filtrar_cuentas_por_app_origen(qs, 'inventario')
  ↓
Django Filter
  ↓ codigo__startswith in ['143505', '143510', '1435', '613505', ..., '51', '15']
  ↓ Retorna solo cuentas permitidas
```

### Ejemplo: Buscar "Depreciación" desde Inventario

1. Usuario abre "Nuevo Activo Fijo"
2. Busca en campo "Cuenta de Depreciación" → escribe "51"
3. Frontend envía: `GET /api/v1/contabilidad/cuentas-contables/?search=51&app_origen=inventario`
4. Backend filtra:
   - Busca "51" en códigos, nombres, descripciones
   - Y limita a `APP_ORIGEN_PREFIJOS['inventario']` = `['143505', ..., '51', '15']`
   - Retorna cuentas como 5100, 5105, 5160, 5199
5. Frontend renderiza resultados

---

## ✅ Testing Checklist

- [ ] **Facturas:** Buscar descuento ("418") al crear nota crédito
- [ ] **Clientes:** Vincular factura a cliente, aparecen retenciones por cobrar (1375)
- [ ] **Gastos:** Buscar gasto genérico ("51"), aparecen cuentas 5100-5199
- [ ] **Empleados:** Buscar gasto de personal ("51"), aparecen cuentas de nómina
- [ ] **Inventario:** Búsqueda de depreciación ("51") sigue funcionando ✅
- [ ] **Proveedores:** Buscar retención ("2365"), aparecen retenciones practicadas

---

## 📋 Cambios Resumidos

```
📊 DIFF: APP_ORIGEN_PREFIJOS

 facturas:    +1  (418)
 clientes:    +4  (4135, 413505, 413510, 1375)
 gastos:      +2  (51, 6)
 empleados:   +1  (51)
 inventario:   0  (ya actualizado)
 proveedores: +7  (2365, 236505-540, 236805, 2368, 2805, 280505)
─────────────────────
 TOTAL:      +15  códigos/prefijos agregados
```

**Impacto:** 
- ✅ Bajo riesgo (solo suma permisos, no quita)
- ✅ Coherente con el negocio
- ✅ Facilita búsquedas desde frontend
- ✅ Mantiene isolamiento por app (still uses allow-list)

---

## 🚀 Próximos Pasos

1. ✅ Fix implementado
2. ⏳ Redeploy en desarrollo
3. ⏳ Testing en navegador (ver checklist arriba)
4. ⏳ Desplegar en staging/producción si OK

---

## 📝 Historial de Cambios

| Fecha | App | Cambio | Razón |
|-------|-----|--------|-------|
| 2026-05-15 | inventario | +51 (depreciación) | Búsqueda de cuentas de depreciación en Activos Fijos |
| 2026-05-15 | facturas | +418 (descuentos) | Registro de descuentos en ventas |
| 2026-05-15 | clientes | +4 códigos | Vincular facturas + Retenciones por cobrar |
| 2026-05-15 | gastos | +51, +6 | Gastos genéricos + Costos |
| 2026-05-15 | empleados | +51 | Gastos de personal genéricos |
| 2026-05-15 | proveedores | +7 códigos | Retenciones + Anticipos |

---

## 🔗 Referencias

- **File:** `apps/tenant/contabilidad/services/selectors.py` (líneas 88-177)
- **Función:** `filtrar_cuentas_por_app_origen(qs, app_origen)`
- **Patrón:** Security Allow-List Pattern (Bounded Context isolement)
- **Docs previos:**
  - `FIX_DEPRECIACION_ACCOUNT_SEARCH.md` (2026-05-15)
  - `ADR-001-retention-pull-model.md` (Contabilidad Pull Model)
