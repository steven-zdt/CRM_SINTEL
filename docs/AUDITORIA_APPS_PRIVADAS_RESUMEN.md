# Auditoría y Alineación de Apps Privadas - Resumen Ejecutivo

**Fecha:** 2024  
**Versión Base:** Arquitectura Empresa v2.40  
**Objetivo:** Auditar y alinear todas las apps privadas (TENANT_APPS) con el boilerplate de `empresa`.

---

## Apps Auditadas

### ✅ **1. empresa** (Boilerplate/Referencia)
- **Estado:** ✅ Completo
- **FK a Empresa:** ✅ (Singleton, no aplica)
- **DataTables en ViewSet:** ✅
- **Parser/Renderer Classes:** ✅
- **Lazy Loading JS:** ✅
- **ENFORCED MODE:** ✅

### ✅ **2. facturas** (Completado)
- **Estado:** ✅ Completo
- **FK a Empresa:** ✅ Agregado (Factura, ItemFactura)
- **DataTables en ViewSet:** ✅ Movido de `datatables.py`
- **Parser/Renderer Classes:** ✅ Agregado
- **Lazy Loading JS:** ✅ Actualizado
- **ENFORCED MODE:** ✅ (ReadOnly, inmutable)

### 🔄 **3. clientes** (En Proceso)
- **Estado:** ⚠️ Parcial
- **FK a Empresa:** ✅ Ya existe
- **DataTables en ViewSet:** ✅ Ya existe (`@action`)
- **Parser/Renderer Classes:** ✅ Ya existe
- **Lazy Loading JS:** ⚠️ Verificar
- **ENFORCED MODE:** ✅ Ya implementado
- **Acción:** Verificar y corregir JavaScript

### 🔄 **4. proveedores** (Pendiente)
- **Estado:** ⚠️ Pendiente
- **FK a Empresa:** ✅ Ya existe
- **DataTables:** ⚠️ Verificar
- **Parser/Renderer Classes:** ⚠️ Verificar
- **Lazy Loading JS:** ⚠️ Verificar
- **ENFORCED MODE:** ⚠️ Verificar

### 🔄 **5. gastos** (Pendiente)
- **Estado:** ⚠️ Pendiente
- **FK a Empresa:** ✅ Ya existe
- **DataTables:** ⚠️ Verificar
- **Parser/Renderer Classes:** ⚠️ Verificar
- **Lazy Loading JS:** ⚠️ Verificar
- **ENFORCED MODE:** ⚠️ Verificar

### 🔄 **6. empleados** (Pendiente)
- **Estado:** ⚠️ Pendiente
- **FK a Empresa:** ✅ Ya existe (Empleado)
- **DataTables:** ⚠️ Verificar
- **Parser/Renderer Classes:** ⚠️ Verificar
- **Lazy Loading JS:** ⚠️ Verificar
- **ENFORCED MODE:** ⚠️ Verificar

### 🔄 **7. contabilidad** (Pendiente)
- **Estado:** ⚠️ Pendiente
- **FK a Empresa:** ⚠️ Verificar (CuentaContable, AsientoContable)
- **DataTables:** ⚠️ Verificar
- **Parser/Renderer Classes:** ⚠️ Verificar
- **Lazy Loading JS:** ⚠️ Verificar
- **ENFORCED MODE:** ⚠️ Verificar

### 🔄 **8. inventario** (Pendiente)
- **Estado:** ⚠️ Pendiente
- **FK a Empresa:** ✅ Ya existe (ActivoFijo)
- **DataTables:** ⚠️ Verificar
- **Parser/Renderer Classes:** ⚠️ Verificar
- **Lazy Loading JS:** ⚠️ Verificar
- **ENFORCED MODE:** ⚠️ Verificar

---

## Checklist de Correcciones por App

### Checklist Estándar (Aplicar a todas las apps):

- [ ] **FK a Empresa:** Verificar que todos los modelos principales tengan FK no-nullable
- [ ] **DataTables en ViewSet:** Verificar que esté como `@action`, no en archivo separado
- [ ] **Parser/Renderer Classes:** Verificar que estén explícitos (`JSONParser, FormParser`, `JSONRenderer`)
- [ ] **Lazy Loading JS:** Verificar que use `DOMUtils.onVisibleOnce()` en lugar de `awaitVisibleAny()`
- [ ] **ENFORCED MODE:** Verificar que tenga `_check_enforced_mode()` en mutaciones
- [ ] **Índices:** Verificar que FK a Empresa tenga índice
- [ ] **Service Layer:** Verificar que use `qs_list()` y `qs_detail()` con `LIST_FIELDS` y `DETAIL_FIELDS`

---

## Priorización

### **CRÍTICO (Hacer primero):**
1. ✅ facturas (Completado)
2. 🔄 clientes (Verificar JS)
3. 🔄 proveedores
4. 🔄 gastos
5. 🔄 empleados

### **IMPORTANTE:**
6. 🔄 contabilidad
7. 🔄 inventario

### **OPCIONAL:**
- perfil (endpoint `/me/` especial, no requiere ENFORCED MODE)
- dashboard (read-only, no requiere ENFORCED MODE)
- landing (pública, no requiere ENFORCED MODE)

---

## Próximos Pasos

1. Auditar cada app sistemáticamente
2. Aplicar correcciones críticas
3. Validar funcionamiento
4. Documentar cambios
