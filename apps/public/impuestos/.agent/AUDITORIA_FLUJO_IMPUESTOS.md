# [PORTAL] Auditoría y SSoT: Módulo Impuestos (Catálogo Tributario DIAN)

**Versión:** 3.5.0
**Estado:** ✅ PRODUCTION READY
**Ubicación:** `apps/public/impuestos/`
**Esquema:** `public`
**Última Auditoría:** 2026-05-09

---

## 📑 Documentación Especializada (SSoT)

> [!NOTE]
> La documentación se ha fragmentado para garantizar la mantenibilidad y claridad siguiendo el estándar SINTEL v3.5.0.

| Documento | Descripción |
| :--- | :--- |
| [📂 Arquitectura y Microtareas](docs/impuestos_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas. |
| [🗺️ Mapas de Flujo](docs/impuestos_flow_map.md) | Diagramas Mermaid de ciclo de vida y procesos. |
| [🧠 Lógica de Negocio](docs/impuestos_business_logic.md) | SSoT de reglas, validaciones y cálculos. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---
 | :--- |
| [📂 Arquitectura y Microtareas](docs/impuestos_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas (MT-IMP). |
| [🗺️ Mapas de Flujo](docs/impuestos_flow_map.md) | Ciclo de vida del catálogo compartido y flujo de provisión hacia los tenants. |
| [🧠 Lógica de Negocio](docs/impuestos_business_logic.md) | SSoT de tipos de impuestos, tarifas IVA, regímenes y validación de Actividades Económicas (CIIU). |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---

## 🎯 Responsabilidades Core

El módulo de **Impuestos** gestiona la integridad normativa de la plataforma.

1.  **Catálogo Maestro**: Centralización de códigos DIAN para Impuestos (IVA, Retención, ICA), Tipos de Contribuyente y Regímenes.
2.  **Referencia Cross-Schema**: Provisión de datos maestros a todos los inquilinos mediante el `ImpuestosProvider` (Lectura compartida).
3.  **Gestión CIIU**: Repositorio canónico de Actividades Económicas actualizadas según estándares nacionales.
4.  **Consistencia Fiscal**: Garantía de que todos los cálculos de los tenants (Facturación, Gastos, Nómina) utilicen las mismas tarifas y conceptos legales.
5.  **Auditabilidad Normativa**: Registro histórico de cambios en leyes tributarias que afectan los cálculos del ERP.

---

## 🛠️ Stack Tecnológico (Alineación v3.5.0)

- **Backend**: Django (Esquema Public).
- **Consumo**: `ImpuestosProvider` (API interna para apps tenant).
- **Service Layer**: Automatización de ingesta ETL para actualización de catálogos desde fuentes oficiales.
- **Choices**: Módulos especializados de enums para códigos tributarios y responsabilidades RUT.
- **API**: Endpoints de solo lectura para el sistema y administrativos para actualización masiva.

---

## 🏗️ Estructura de Servicios y APIs

### Servicios Principales
- `ImpuestosProvider`: Único punto de acceso autorizado para que los tenants consulten tarifas y códigos.
- `ETLIngestaService`: Pipeline de actualización de catálogos (Normativa DIAN).

### Endpoints Estratégicos
- `GET /api/public/v1/impuestos/tipos-impuesto/`: Listado público de impuestos soportados.
- `GET /api/public/v1/impuestos/actividades-ciiu/`: Buscador de códigos CIIU.
- `POST /api/admin/v1/impuestos/run-pipeline/`: (Staff) Ejecución del proceso de actualización legal.

---

## 🚀 Próximos Pasos (MT-IMP)

Las tareas de evolución técnica se encuentran en [Arquitectura de Microtareas](docs/impuestos_microtasks_architecture.md).

> [!CAUTION]
> Cualquier cambio en las tarifas del catálogo global afecta de inmediato a todos los inquilinos. Las actualizaciones deben realizarse mediante procesos de auditoría rigurosos.

