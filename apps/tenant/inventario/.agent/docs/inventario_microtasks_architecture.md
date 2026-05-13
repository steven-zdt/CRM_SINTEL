# 🏗️ Arquitectura de Microtareas: Módulo Inventario (MT-INV)

Estado de estandarización: **SINTEL v3.5.0 COMPLIANT**

---

## 🟢 MT-INV-01: Backend & Data Layer (Core Integrity)

- [ ] **MT-INV-01-01**: Refactorizar los 6 ViewSets para usar `lookup_field="uuid"` (Standard v3.5.0).
- [ ] **MT-INV-01-02**: Unificar lógica de `calcular_stock()` y `recalcular_stock_producto()` en una única función de servicio atómica.
- [ ] **MT-INV-01-03**: Optimizar `qs_movimiento_list()` para filtrar por `empresa_id` directo en lugar de `producto__empresa_id`.
- [ ] **MT-INV-01-04**: Hacer obligatorio el parámetro `empresa_id` en `qs_categoria_list()` para eliminar el riesgo de IDOR (MT-INV-007).
- [ ] **MT-INV-01-05**: Implementar validación DSV (Double Semantic Verification) en el `MaterializarCargaMasiva` para validar existencia de empresa.

---

## 🔵 MT-INV-02: Frontend & UI (Standard Experience)

- [ ] **MT-INV-02-01**: Migrar lógica de `inventario_list.js` a submódulos especializados por feature (`productos_list.js`, `servicios_list.js`).
- [ ] **MT-INV-02-02**: Implementar DOM Shield en todos los formularios de edición de ítems.
- [ ] **MT-INV-02-03**: Optimizar el rendimiento de Tabulator en el listado de movimientos mediante carga remota (`ajax`).
- [ ] **MT-INV-02-04**: Eliminar definitivamente los endpoints obsoletos `/dt/` tras verificar que no hay dependencias en el frontend (MT-INV-009).

---

## 🟣 MT-INV-03: Integraciones & Bridge (Pull Model)

- [ ] **MT-INV-03-01**: Refinar el `ExtractorInventario` en Contabilidad para soportar nuevos tipos de movimientos operativos.
- [ ] **MT-INV-03-02**: Implementar sistema de notificaciones de "Stock Crítico" via Celery integrado con el módulo de `Mail`.
- [ ] **MT-INV-03-03**: Automatizar la actualización de `costo_promedio` ponderado tras cada entrada de compra (MT-INV-010).

---

## 🔴 MT-INV-04: Testing & Compliance

- [ ] **MT-INV-04-01**: Implementar tests de concurrencia para el motor de Kardex (Simulación de múltiples entradas paralelas).
- [ ] **MT-INV-04-02**: Verificar cumplimiento de `AGENTS.md` (Cero caracteres especiales en docstrings de modelos).
- [ ] **MT-INV-04-03**: Test de integridad de eliminación: Validar que el SET_NULL de categorías funciona correctamente en todos los tipos de ítems.
