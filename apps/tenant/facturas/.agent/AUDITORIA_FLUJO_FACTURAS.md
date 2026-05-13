# [PORTAL] Auditoría y SSoT: Módulo Facturas (Documentos Electrónicos)

**Versión:** 3.5.0 (UI/UX v2.97)  
**Estado:** ✅ PRODUCTION READY
**Ubicación:** `apps/tenant/facturas/`
**Última Auditoría:** 2026-05-11  
**Última Actualización (UI/UX):** 2026-05-11 (Edición centralizada + Estado de Pago)

---

## 📑 Documentación Especializada (SSoT)

> [!NOTE]
> La documentación se ha fragmentado para garantizar la mantenibilidad y claridad siguiendo el estándar SINTEL v3.5.0.

| Documento | Descripción |
| :--- | :--- |
| [✅ Estado Actual v2.97](ESTADO_ACTUAL_v297.md) | **[NUEVO]** Estado de la app: edición centralizada, Estado de Pago, garantías de seguridad. |
| [🔒 Garantía de Edición Controlada](GARANTIA_EDICION_CONTROLADA.md) | Documentación técnica de protección de campos XML y edición segura. |
| [📂 Arquitectura y Microtareas](docs/facturas_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas. |
| [🗺️ Mapas de Flujo](docs/facturas_flow_map.md) | Diagramas Mermaid de ciclo de vida y procesos. |
| [🧠 Lógica de Negocio](docs/facturas_business_logic.md) | SSoT de reglas, validaciones y cálculos. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---
 | :--- |
| [📂 Arquitectura y Microtareas](docs/facturas_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas (MT-FAC). |
| [🗺️ Mapas de Flujo](docs/facturas_flow_map.md) | Pipeline de importación XML, Ingesta IMAP y ciclo de vida de facturas/notas. |
| [🧠 Lógica de Negocio](docs/facturas_business_logic.md) | SSoT de idempotencia por CUFE/CUDE, resolución de naturaleza y reglas de inmutabilidad. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---

## 🎯 Responsabilidades Core

El módulo de **Facturas** gestiona la recepción y emisión de documentos electrónicos con validez legal.

1.  **Pipeline UBL 2.1**: Extracción de datos maestros desde XMLs estándar (Parser especializado).
2.  **Idempotencia Legal**: Prevención de duplicados mediante validación única de CUFE (Facturas) y CUDE (Notas Crédito).
3.  **Snapshot de Identidad**: Almacenamiento histórico de datos de emisor/receptor para resiliencia fiscal (Inmutabilidad).
4.  **Ingesta Multi-Canal**: Carga manual (Drag & Drop), carga masiva (ZIP/Batch) e ingesta automática por correo (IMAP).
5.  **Resolución de Naturaleza**: Clasificación automática entre VENTA (Emitida) y COMPRA (Recibida) comparando NITs con el SSoT de Empresa.
6.  **Gestión de Anexos**: Almacenamiento optimizado de XMLs originales (`AttachedDocument`) y ApplicationResponses DIAN.
7.  **Rastreo de Pagos** ⭐ **(v2.97)**: Campo `estado_pago` para marcar facturas como NO_PAGADA, PAGO_PARCIAL o PAGADA.
8.  **Edición Controlada** ⭐ **(v2.97)**: Interfaz centralizada en modal para editar solo campos manuales (9 campos permitidos).

---

## 📌 Cambios Recientes (v2.97 - 2026-05-11)

### ✅ Nuevo Campo: Estado de Pago

- **Propósito:** Rastrear el estado de pago de facturas emitidas
- **Opciones:** NO_PAGADA, PAGO_PARCIAL, PAGADA
- **Default:** NO_PAGADA
- **Ubicación UI:** Columna en tabla + Campo en modal de edición
- **Styling:** Badges con colores (🔴 Rojo, 🟡 Amarillo, 🟢 Verde)
- **Validación:** Incluido en allowed_fields (9 campos totales)

### ✅ Edición Centralizada en Modal

- **Cambio:** Toda la lógica de edición está SOLO en el modal "Editar Factura"
- **Grid:** 100% SOLO LECTURA (sin editores inline)
- **Beneficio:** Mayor seguridad + UX más clara
- **Campos Editables:** 9 (estado, estado_pago, vencimiento, retenciones, formas de pago)
- **Validación:** 6 capas (Frontend UI, Modal, Network, Backend ViewSet, Serializer, ORM)

### ✅ Contexto Visual: Emisor

- **Agregado:** Campo `emisor_razon_social` visible en modal
- **Estado:** Deshabilitado (read-only)
- **Ubicación:** Inicio del formulario modal
- **Beneficio:** Usuario sabe para quién edita la factura

Para detalles completos, consultar [Estado Actual v2.97](ESTADO_ACTUAL_v297.md).

---

## 🛠️ Stack Tecnológico (Alineación v3.5.0)

- **Backend**: Django DRF + Celery (Async Ingestion).
- **Formatos**: UBL 2.1 (XML), PDF (Render).
- **Servicios**: `FacturaSelector`, `FacturaBusinessService`, `UBLParser`.
- **Frontend**: Vanilla JS (Namespace `window.Sintel.Factura`) + Tabulator.
- **UI**: Offcanvas dinámicos con HTMX para detalle y carga de documentos.

---

## 🏗️ Estructura de Servicios y APIs

### Servicios Principales
- `FacturaSelector`: Consultas con `.only()` optimizadas para millones de registros.
- `UBLParser`: Extractor canónico de DTOs desde fuentes XML.
- `MailIngestionService`: Orquestador de tareas Celery para el buzón de entrada.

### Endpoints Estratégicos
- `GET /api/v1/facturas/`: Listado principal (SSoT de facturación).
- `POST /api/v1/facturas/upload-ubl/`: (Legacy) Punto de entrada para XMLs individuales.
- `GET /api/v1/facturas/{uuid}/xml/`: Acceso directo al artefacto XML (Anexo).

---

## 🚀 Próximos Pasos (MT-FAC)

Las tareas de evolución técnica se encuentran en [Arquitectura de Microtareas](docs/facturas_microtasks_architecture.md).

**Completado en v2.97:**
- ✅ Edición centralizada en modal
- ✅ Campo "Estado de Pago" implementado
- ✅ Garantía de seguridad (6 capas de validación)
- ✅ Contexto visual (Emisor readonly)

**Opcionales futuros:**
- 💭 Columna "Monto Pagado" para pago parcial
- 💭 Historial de cambios en estado de pago
- 💭 Notificaciones automáticas por vencimiento
- 💭 Reportes de cobranza

> [!CAUTION]
> La eliminación de una factura implica el borrado en cascada de sus ítems y anexos; este proceso es irreversible y debe auditarse contra el libro mayor contable.

