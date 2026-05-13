# [PORTAL] Auditoría y SSoT: Módulo Gastos (Egresos y Documento Soporte)

**Versión:** 3.5.0
**Estado:** ✅ PRODUCTION READY
**Ubicación:** `apps/tenant/gastos/`
**Última Auditoría:** 2026-05-09

---

## 📑 Documentación Especializada (SSoT)

> [!NOTE]
> La documentación se ha fragmentado para garantizar la mantenibilidad y claridad siguiendo el estándar SINTEL v3.5.0.

| Documento | Descripción |
| :--- | :--- |
| [📂 Arquitectura y Microtareas](docs/gastos_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas. |
| [🗺️ Mapas de Flujo](docs/gastos_flow_map.md) | Diagramas Mermaid de ciclo de vida y procesos. |
| [🧠 Lógica de Negocio](docs/gastos_business_logic.md) | SSoT de reglas, validaciones y cálculos. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---
 | :--- |
| [📂 Arquitectura y Microtareas](docs/gastos_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas (MT-GST). |
| [🗺️ Mapas de Flujo](docs/gastos_flow_map.md) | Ciclo de vida del Documento Soporte, anulación y gestión de resoluciones DIAN. |
| [🧠 Lógica de Negocio](docs/gastos_business_logic.md) | SSoT de cálculos de retenciones, inmutabilidad legal y patrón de desacoplamiento. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---

## 🎯 Responsabilidades Core

El módulo de **Gastos** centraliza el registro de costos y egresos del tenant.

1.  **Documento Soporte (DS)**: Generación de evidencia legal inmutable para proveedores no obligados a facturar, bajo rangos autorizados por la DIAN.
2.  **Resolución DIAN**: Gestión de numeración oficial (consecutivos, prefijos, rangos de vigencia).
3.  **Desacoplamiento Operativo**: Separación entre la capa legal (`DocumentoSoporte`) y la clasificación administrativa (`Gasto`), eliminando dependencias directas de cuentas contables en el modelo base.
4.  **Gestión de Retenciones**: Cálculo automático de Retefuente y ReteICA basado en porcentajes normalizados.
5.  **Ciclo de Vida Controlado**: Flujo de estados `Activo` -> `Desactivado` -> `Anulado`, preservando la integridad de la secuencia numérica.

---

## 🛠️ Stack Tecnológico (Alineación v3.5.0)

- **Backend**: Django DRF (ViewSets + Service Layer).
- **Aislamiento**: Multi-tenant estricto.
- **Frontend**: Vanilla JS (Namespace `window.Sintel.Gastos`).
- **UI**: Bootstrap 5 Offcanvas para gestión de egresos y resoluciones.
- **Seguridad**: DSV (Double Semantic Verification) para validación de Proveedores.

---

## 🏗️ Estructura de Servicios y APIs

### Servicios Principales
- `GastoSelector`: Consultas optimizadas para listados y sumarios financieros.
- `GastoBusinessService`: Orquestador de registro, anulación y reserva de consecutivos.
- `ResolucionDIANService`: SSoT para la vigencia y control de rangos de numeración.

### Endpoints Estratégicos
- `GET /api/v1/gastos/`: Listado operativo de egresos.
- `POST /api/v1/gastos/`: Creación de Documento Soporte + Gasto.
- `GET /api/v1/gastos/summary/`: KPIs financieros (Subtotal, Retenciones, Total Neto).

---

## 🚀 Próximos Pasos (MT-GST)

Las tareas de evolución técnica se encuentran en [Arquitectura de Microtareas](docs/gastos_microtasks_architecture.md).

> [!CAUTION]
> Los consecutivos de Documento Soporte son inmutables; una anulación no permite reutilizar el número, garantizando la trazabilidad ante auditorías tributarias.

