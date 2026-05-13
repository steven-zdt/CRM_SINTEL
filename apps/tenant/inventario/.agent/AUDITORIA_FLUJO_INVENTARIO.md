# [PORTAL] Auditoría y SSoT: Módulo Inventario (Catálogo y Kardex)

**Versión:** 3.5.0
**Estado:** ✅ PRODUCTION READY
**Ubicación:** `apps/tenant/inventario/`
**Última Auditoría:** 2026-05-09

---

## 📑 Documentación Especializada (SSoT)

> [!NOTE]
> La documentación se ha fragmentado para garantizar la mantenibilidad y claridad siguiendo el estándar SINTEL v3.5.0.

| Documento | Descripción |
| :--- | :--- |
| [📂 Arquitectura y Microtareas](docs/inventario_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas. |
| [🗺️ Mapas de Flujo](docs/inventario_flow_map.md) | Diagramas Mermaid de ciclo de vida y procesos. |
| [🧠 Lógica de Negocio](docs/inventario_business_logic.md) | SSoT de reglas, validaciones y cálculos. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---
 | :--- |
| [📂 Arquitectura y Microtareas](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/inventario/docs/inventario_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas (MT-INV). |
| [🗺️ Mapas de Flujo](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/inventario/docs/inventario_flow_map.md) | Ciclo de vida del producto, motor de Kardex y procesos de ingesta masiva. |
| [🧠 Lógica de Negocio](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/inventario/docs/inventario_business_logic.md) | SSoT de invariantes de stock, inmutabilidad de movimientos y reglas de eliminación. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---

## 🎯 Responsabilidades Core

El módulo de **Inventario** centraliza la gestión de activos y bienes del tenant.

1.  **Catálogo Multitipo**: Gestión diferenciada de `Productos` (Stock), `Servicios` (Intangibles) y `Activos Fijos` (Uso interno).
2.  **Motor Kardex**: Control de stock desnormalizado en `Producto.stock_actual`, recalculado de forma atómica tras cada movimiento.
3.  **Inmutabilidad de Movimientos**: Registro append-only de entradas y salidas para garantizar la integridad histórica.
4.  **Ingesta Inteligente**: Pipeline de carga masiva desde Excel con auto-creación de categorías y registro de stock inicial.
5.  **Aislamiento Gradual**: Cero dependencias directas de módulos externos; integración via Pull-Model (Contabilidad lee Inventario).

---

## 🛠️ Stack Tecnológico (Alineación v3.5.0)

- **Backend**: Django DRF (6 ViewSets especializados).
- **Service Layer**: Paquete `services/` con Selectors, Business y CRUD logic.
- **Frontend**: Vanilla JS (Namespace `window.Sintel.Inventario`).
- **UI**: Tabulator para grillas de alta densidad y Bootstrap Offcanvas para editores.
- **Seguridad**: DSV (Double Semantic Verification) en movimientos y mutaciones.

---

## 🏗️ Estructura de Servicios y APIs

### Servicios Principales
- `InventarioSelector`: Consultas optimizadas con `.only()` y `select_related()`.
- `KardexService`: Motor de recalculo de stock con `select_for_update()`.
- `IngestaService`: Materialización de DTOs y carga masiva de catálogos.

### Endpoints Estratégicos
- `GET /api/v1/inventario/productos/`: Listado de existencias y alertas de stock.
- `GET /api/v1/inventario/productos/{id}/kardex/`: Historial cronológico de movimientos.
- `POST /api/v1/inventario/movimientos/`: Registro de entradas/salidas con validación de stock.

---

## 🚀 Próximos Pasos (MT-INV)

Las tareas de evolución técnica se encuentran en [Arquitectura de Microtareas](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/inventario/docs/inventario_microtasks_architecture.md).

> [!CAUTION]
> La eliminación de un producto requiere que esté marcado como `inactivo` y borrará en cascada su historial de Kardex. Para preservación legal, se recomienda la desactivación permanente sobre el borrado físico.
