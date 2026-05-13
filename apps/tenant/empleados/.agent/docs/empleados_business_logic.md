# 🧠 Lógica de Negocio: Módulo Empleados

Este documento es la Single Source of Truth (SSoT) para las reglas de cálculo, validaciones legales y lógica de nómina.

---

## 📐 Motor de Cálculo Proporcional (v3.5.0)

Toda liquidación financiera en el módulo se rige por el principio de **proporcionalidad sobre 30 días**.

### 1. Factor de Proporción
```python
factor = dias_laborados / 30
```

### 2. Devengos
- **Salario Base**: `salario_mensual * factor`
- **Auxilio de Transporte**: `valor_legal_mensual * factor` (Si el salario es <= 2 SMMLV).

### 3. Deducciones de Ley (Seguridad Social)
Calculadas sobre el IBC (Ingreso Base de Cotización), que para empleados dependientes es igual al Salario Base (no incluye auxilio de transporte).
- **Salud**: `ibc * 0.04` (4%)
- **Pensión**: `ibc * 0.04` (4%)

---

## 🗓️ Reglas de Nómina Multitanda

El sistema permite fraccionar el pago mensual en múltiples registros (ej. quincenas).

1.  **Validación de Solapamiento**: No se permite que la suma de `dias_laborados` para un empleado en un mismo `periodo_mes` exceda los **31 días**.
2.  **Unicidad por Fecha**: Se permite más de un registro en el mes siempre que la `fecha_pago` sea distinta (Evita duplicados accidentales).
3.  **Idempotencia en Reversión**: Al eliminar una nómina que incluía descuentos por préstamos, el saldo del préstamo en el `Contrato` debe reversarse automáticamente de forma atómica.

---

## 🛡️ Validaciones Críticas (SSoT)

| Regla | Descripción | Acción en Error |
| :--- | :--- | :--- |
| **Contrato Único** | Solo se permite un contrato con `activo=True` por empleado. | `400 Bad Request` |
| **Estado Empleado** | No se pueden registrar nóminas para empleados con `estado='RETIRADO'`. | `403 Forbidden` |
| **Zero Trust** | El `empresa_id` de la nómina debe coincidir con el del empleado y contrato. | `401 Unauthorized / IDOR Block` |
| **Días Mínimos** | El valor mínimo de `dias_laborados` es 0.5. | `ValidationError` |

---

## 📦 Gestión de Contratos

- **Activación Automática**: Al marcar un contrato como activo, el sistema desactiva cualquier otro contrato previo para el mismo empleado.
- **SSoT de Salario**: El `salario_mensual` definido en el contrato es la base inmutable para todos los cálculos de `NominaCalculationService`.

---

## 🔗 Navegación
- [⬅️ Volver al Portal](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/empleados/AUDITORIA_FLUJO_EMPLEADOS.md)
- [📂 Arquitectura y Microtareas](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/empleados/docs/empleados_microtasks_architecture.md)
- [🗺️ Mapas de Flujo](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/empleados/docs/empleados_flow_map.md)
