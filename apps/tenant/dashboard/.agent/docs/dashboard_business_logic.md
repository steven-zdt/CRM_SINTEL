# 🧠 Lógica de Negocio: Módulo Dashboard

Este documento es la Single Source of Truth (SSoT) para las estrategias de agregación y definiciones de métricas del dashboard.

---

## 🎯 Estrategia de Agregación

El módulo de Dashboard no posee modelos propios. Actúa como un **Consumidor** de otros módulos de dominio:

- **Facturas**: KPIs de Ventas Totales, Facturas Pendientes y Recaudos.
- **Clientes**: KPIs de Clientes Activos y Prospección.
- **Contabilidad**: Series de ingresos/egresos y métricas de salud financiera.
- **Cotizaciones**: Tasa de conversión y volumen de ofertas.

---

## 👥 Permisos Basados en Roles

La lógica de visibilidad reside en `DashboardBusinessService`:

- **ADMIN**: Acceso a resúmenes financieros completos y acciones de configuración de empresa.
- **OPERADOR/STAFF**: Acceso a KPIs operativos (tareas pendientes, transacciones recientes).
- **VISOR**: Vista restringida (usualmente actividad personal o métricas públicas del tenant).

---

## ⚖️ Definición de KPIs (SSoT)

| Etiqueta KPI | Origen (Módulo) | Lógica de Cálculo |
| :--- | :--- | :--- |
| **Ventas (mes)** | `apps.tenant.facturas` | `SUM(total)` WHERE `estado='PAID'` AND `month=NOW()` |
| **Clientes activos** | `apps.tenant.clientes` | `COUNT(*)` WHERE `estado='ACTIVE'` |
| **Facturas pendientes** | `apps.tenant.facturas` | `COUNT(*)` WHERE `estado='PENDING'` |
| **Ingresos (mes)** | `apps.tenant.contabilidad` | Saldo de cuentas de ingresos (Grupo 4). |

---

## 📦 Estructura del Payload Estándar

El objeto `DashboardPayload` asegura un contrato consistente independientemente del rol o estado del inquilino:

1.  **Header**: Título y Subtítulo dinámico.
2.  **KPIs**: Lista de 3-4 métricas primarias con tendencias.
3.  **Series**: Puntos de datos para gráficas (Chart.js / ApexCharts).
4.  **Table**: Actividad reciente o items destacados (ej. Top 5 Clientes).

---

## 🔗 Navegación
- [⬅️ Volver al Portal](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/dashboard/AUDITORIA_FLUJO_DASHBOARD.md)
- [📂 Arquitectura y Microtareas](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/dashboard/docs/dashboard_microtasks_architecture.md)
- [🗺️ Mapas de Flujo](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/dashboard/docs/dashboard_flow_map.md)
