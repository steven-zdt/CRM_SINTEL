# 🏗️ Arquitectura de Microtareas: Módulo Gastos (MT-GST)

Estado de estandarización: **SINTEL v3.5.0 COMPLIANT**

---

## 🟢 MT-GST-01: Backend & Data Layer (Core Integrity)

- [ ] **MT-GST-01-01**: Refactorizar `GastosViewSet` para usar `lookup_field="uuid"` (Standard v3.5.0).
- [ ] **MT-GST-01-02**: Implementar `GastoSelector` con métodos `.only()` optimizados para KPIs (`total_gastado_mes`, `top_proveedores`).
- [ ] **MT-GST-01-03**: Asegurar atomicidad en `ResolucionDIANService.obtener_siguiente_consecutivo()` usando `select_for_update()`.
- [ ] **MT-GST-01-04**: Implementar DSV (Double Semantic Verification) en el endpoint de creación para validar `proveedor_id` y `resolucion_id`.
- [ ] **MT-GST-01-05**: Auditoría de integridad: Evitar que un `Gasto` se guarde sin un `DocumentoSoporte` asociado en la misma transacción.

---

## 🔵 MT-GST-02: Frontend & UI (Standard Experience)

- [ ] **MT-GST-02-01**: Migrar lógica de formularios a `gastos_editor.js` bajo el patrón Feature-Sliced.
- [ ] **MT-GST-02-02**: Implementar DOM Shield en `gasto_form.html` para proteger inputs de proveedores.
- [ ] **MT-GST-02-03**: Integrar Tabulator en `gasto_list.js` con soporte para agrupación por `Proveedor`.
- [ ] **MT-GST-02-04**: Crear micro-componente de feedback visual para resoluciones próximas a expirar (UI Magic).
- [ ] **MT-GST-02-05**: Implementar exportación a Excel nativa desde el listado usando `Tabulator` y `xlsx.js`.

---

## 🟣 MT-GST-03: Integraciones & Desacoplamiento (Bridge)

- [ ] **MT-GST-03-01**: Refinar el Bridge con `apps/tenant/contabilidad` para materialización asíncrona de asientos.
- [ ] **MT-GST-03-02**: Implementar webhook para notificar al módulo de `Caja/Bancos` tras el registro de un egreso pagado.
- [ ] **MT-GST-03-03**: Preparar extractor para `apps/tenant/impuestos` (Reporte de Retenciones).

---

## 🔴 MT-GST-04: Testing & Compliance

- [ ] **MT-GST-04-01**: Crear `tests/test_documento_soporte.py` validando la inmutabilidad de consecutivos.
- [ ] **MT-GST-04-02**: Test de carga para generación concurrente de egresos (Prevención de colisiones de numeración).
- [ ] **MT-GST-04-03**: Verificación de cumplimiento AGENTS.md (No emojis en código Python).
