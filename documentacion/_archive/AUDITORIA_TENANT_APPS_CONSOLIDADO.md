# Auditoría Consolidada de TENANT_APPS - Alineación con Arquitectura v2.40

**Fecha:** 2024  
**Versión Base:** Arquitectura Empresa v2.40  
**Objetivo:** Validar y corregir todas las apps privadas (`TENANT_APPS`) para alinearlas con el boilerplate.

---

## Apps a Auditar

Según `config/settings.py`, las `TENANT_APPS` son:
1. ✅ `empresa` - Boilerplate/Referencia (completado)
2. ✅ `facturas` - Completado
3. ⏳ `clientes` - Pendiente
4. ⏳ `proveedores` - Pendiente
5. ⏳ `gastos` - Pendiente
6. ⏳ `empleados` - Pendiente
7. ⏳ `contabilidad` - Pendiente
8. ⏳ `inventario` - Pendiente
9. ⏳ `perfil` - Pendiente
10. ⏸️ `landing` - Pública (no requiere)
11. ⏸️ `dashboard` - Pública (no requiere)
12. ⏸️ `core` - Base (no requiere)

---

## Checklist de Auditoría por App

### Criterios de Validación:

1. **FK a Empresa:** ¿Tiene ForeignKey a `empresa.Empresa`?
2. **DataTables en ViewSet:** ¿Está el endpoint DataTables como `@action` en ViewSet?
3. **Parser/Renderer Classes:** ¿Tiene `parser_classes` y `renderer_classes` explícitos?
4. **Lazy Loading JS:** ¿Usa `DOMUtils.onVisibleOnce()`?
5. **Service Layer:** ¿Tiene `LIST_FIELDS` y `DETAIL_FIELDS`?
6. **ENFORCED MODE:** ¿Tiene `_check_enforced_mode()` en ViewSet?

---

## Estado de Auditoría

| App | FK Empresa | DataTables | Parser/Renderer | Lazy Loading | Service Fields | ENFORCED MODE | Estado |
|-----|-----------|------------|-----------------|--------------|----------------|---------------|--------|
| empresa | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Completo |
| facturas | ✅ | ✅ | ✅ | ✅ | ✅ | N/A (ReadOnly) | ✅ Completo |
| clientes | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ Pendiente |
| proveedores | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ Pendiente |
| gastos | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ Pendiente |
| empleados | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ Pendiente |
| contabilidad | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ Pendiente |
| inventario | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ Pendiente |
| perfil | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | N/A (IsOwner) | ⏳ Pendiente |

---

## Plan de Ejecución

1. **Fase 1:** Auditar estructura de cada app
2. **Fase 2:** Aplicar correcciones críticas (FK, DataTables, Parser/Renderer)
3. **Fase 3:** Aplicar mejoras (Lazy Loading, Service Fields)
4. **Fase 4:** Validar y documentar

---

**Este documento se actualizará conforme se completen las auditorías.**
