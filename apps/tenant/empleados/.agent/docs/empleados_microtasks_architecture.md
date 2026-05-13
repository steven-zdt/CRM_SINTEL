# 📂 Arquitectura de Microtareas: Módulo Empleados

Este documento desglosa el módulo en tareas atómicas para asegurar trazabilidad y cumplimiento de estándares SINTEL v3.5.0.

---

## 🏗️ Mapa de Microtareas (MT-EMP)

### 🧩 [MT-EMP-INF] Infraestructura y Modelos
- `[x]` Implementar herencia de `SintelTenantBaseModel` en Empleado, Contrato y Devengo.
- `[x]` Configurar constraints de unicidad multi-tenant (`uniq_empleado_per_tenant`).
- `[x]` Implementar máquina de estados secuencial (Empleado -> Contrato -> Devengo).
- `[x]` Sincronización legacy: campo `activo` vs `estado` en Contrato.

### 🔌 [MT-EMP-API] Capa de Datos (API-First)
- `[x]` Implementar `EmpleadoViewSet`, `ContratoViewSet` y `DevengoViewSet`.
- `[x]` Implementar `gestor_offcanvas` centralizado para entrega de templates HTMX.
- `[x]` Crear endpoint `preview-calculo/` para hidratación reactiva del frontend.
- `[ ]` Refactorizar `lookup_field` a UUID en todos los ViewSets para cumplimiento AGENTS.md.

### 🧠 [MT-EMP-BUS] Lógica de Negocio y Servicios
- `[x]` Implementar `NominaCalculationService` (SSoT de liquidación colombiana).
- `[x]` Implementar validación de solapamiento de días (Nómina Multitanda).
- `[x]` Implementar reversión atómica de préstamos al eliminar/anular nóminas.
- `[x]` Implementar lógica de retiro en cascada (cancelación de contratos activos).

### 🎨 [MT-EMP-UI] Interfaz de Usuario y JS
- `[x]` Implementar `empleado_list.js` con Tabulator Factory y anotaciones reactivas.
- `[x]` Crear sub-módulos `contratos_form.js` y `contratos_editar.js` para separación de responsabilidades.
- `[x]` Implementar preview de nómina en tiempo real con triggers HTMX.
- `[ ]` Optimizar scroll horizontal en la tabla de historial de nóminas para dispositivos móviles.

---

## 🏛️ Decisiones Arquitectónicas

1.  **Inmutabilidad Contable**: Los registros de `Devengo` no se editan. Los errores se corrigen mediante anulación y creación de un nuevo registro para mantener la trazabilidad.
2.  **Aislamiento Total**: El módulo no importa de `contabilidad` ni `facturas`. La integración contable se realiza mediante el modelo "Pull" desde el extractor de contabilidad.
3.  **Doble Verificación (DSV)**: Todas las mutaciones validan que el `empleado_id`, `contrato_id` y `empresa_id` pertenezcan al mismo contexto de seguridad.

---

## 🔗 Navegación
- [⬅️ Volver al Portal](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/empleados/AUDITORIA_FLUJO_EMPLEADOS.md)
- [🗺️ Mapas de Flujo](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/empleados/docs/empleados_flow_map.md)
- [🧠 Lógica de Negocio](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/empleados/docs/empleados_business_logic.md)
