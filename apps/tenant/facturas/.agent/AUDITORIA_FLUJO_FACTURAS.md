# [PORTAL] Auditoría y SSoT: Módulo Facturas (Documentos Electrónicos)

**Versión:** 3.5.0 (UI/UX v2.98)  
**Estado:** ✅ PRODUCTION READY
**Ubicación:** `apps/tenant/facturas/`
**Última Auditoría:** 2026-05-13  
**Última Actualización (UI/UX):** 2026-05-13 (Bugfixes edición segura + vinculación contable)

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

## 🎯 Responsabilidades Core

El módulo de **Facturas** gestiona la recepción y emisión de documentos electrónicos con validez legal.

1.  **Pipeline UBL 2.1**: Extracción de datos maestros desde XMLs estándar (Parser especializado).
2.  **Idempotencia Legal**: Prevención de duplicados mediante validación única de CUFE (Facturas) y CUDE (Notas Crédito).
3.  **Snapshot de Identidad**: Almacenamiento histórico de datos de emisor/receptor para resiliencia fiscal (Inmutabilidad).
4.  **Ingesta Multi-Canal**: Carga manual (Drag & Drop), carga masiva (ZIP/Batch) e ingesta automática por correo (IMAP).
5.  **Resolución de Naturaleza**: Clasificación automática entre VENTA (Emitida) y COMPRA (Recibida) comparando NITs con el SSoT de Empresa.
6.  **Gestión de Anexos**: Almacenamiento optimizado de XMLs originales (`AttachedDocument`) y ApplicationResponses DIAN.
7.  **Rastreo de Pagos** ⭐ **(v2.97)**: Campo `estado_pago` para marcar facturas como NO_PAGADA, PAGO_PARCIAL o PAGADA.
8.  **Edición Controlada** ⭐ **(v2.97-2.98)**: Interfaz centralizada en modal para editar solo campos manuales (9 campos) con separación clara XML ↔ Manual. Bugfixes v2.98: validación fechas, detección de botones en Tabulator, persistencia segura.

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

## 📌 Bugfixes Críticos (v2.98 - 2026-05-13)

### 🔧 Corrección 1: Error 500 en `partial_update` — Empresa ID

**Síntoma:** PATCH `/api/v1/facturas/{id}/` retornaba 500 "Unexpected error"  
**Root Cause:** `self.get_empresa_id()` no existe en `FacturaViewSet` (heredaba de `ReadOnlyModelViewSet`, no de `BaseTenantViewSet`)  
**Solución:** 
```python
# Antes (❌)
empresa_id = self.get_empresa_id()  # AttributeError

# Después (✅)
from apps.tenant.perfil.services.perfil_service import get_or_create_profile
empresa_id = get_or_create_profile(request.user).empresa_id
```
**Impacto:** Guardar cambios en modal de edición ahora funciona (retorna 200)

### 🔧 Corrección 2: Modal Edit + View Offcanvas Simultáneos

**Síntoma:** Clickear botón "Editar campos manuales" abría AMBOS: modal de edición + offcanvas Ver Factura  
**Root Cause:** `rowClick` de Tabulator usaba `e.target.closest()` que fallaba porque Tabulator asigna `e.target` al elemento `<div class="tabulator-row">`, no al botón clickeado  
**Solución:**
```javascript
// Antes (❌)
const target = e.target || e.originalEvent?.target;
if (target && target.closest('button')) return;  // Falla si e.target es la fila

// Después (✅)
const path = e.composedPath ? e.composedPath() : (e.path || []);
const enBotones = path.some(el => 
    el.tagName === 'BUTTON' || 
    el.classList?.contains('btn-group')
);
if (enBotones) return;  // Detecta el botón en la ruta real del evento
```
**Impacto:** Evento delegation ahora funciona correctamente; botones de acción son mutuamente excluyentes

### 🔧 Corrección 3: Plantilla `offcanvas_editar_factura.html` — Campos XML vs Manuales

**Síntoma:** Campos que deberían ser editables (estado, fecha_vencimiento, etc.) aparecían readonly cuando el estado ≠ BORRADOR  
**Root Cause:** Plantilla usaba `{% if readonly %}readonly{% endif %}` para TODOS los campos. Para facturas importadas (estado = ENVIADA, ACEPTADA, etc.), `readonly=True` bloqueaba todo  
**Solución:** Reescribir plantilla con secciones explícitas:
```html
<!-- Sección XML: Siempre readonly (fuente de verdad del documento) -->
<div class="card-header bg-secondary text-white">
  <span class="badge bg-light text-secondary"><i class="bi bi-lock-fill"></i>XML</span>
</div>
<input type="text" readonly class="bg-light" ...>  <!-- numero, emisor, receptor, etc. -->

<!-- Sección Gestión Manual: Siempre editable (sin {% if readonly %}) -->
<div class="card-header bg-primary text-white">
  <span class="badge bg-light text-primary"><i class="bi bi-pencil"></i>Editable</span>
</div>
<select class="form-select" ...>  <!-- estado, categoria, etc. sin readonly -->
```
**Campos Siempre Editables:**
- `estado`, `fecha_vencimiento`, `categoria`, `forma_pago`, `medio_pago_codigo`, `payment_due_date`, `cuenta_contable_uuid`

**Campos Siempre Readonly (XML):**
- `numero`, `tipo`, `fecha_emision`, `emisor_*`, `receptor_*`, `moneda`, `naturaleza`, ítems, totales

**Impacto:** Usuario puede editar campos manuales incluso en facturas emitidas; contabilización automática (§18) siempre disponible

### 🔧 Corrección 4: Validación de Campos Fecha — Empty String → Null

**Síntoma:** PATCH con campos fecha vacíos retornaba 400 Bad Request (DRF rechaza `""` en DateField)  
**Root Cause:** `FormData` convierte `null` → `""` en campos sin valor  
**Solución:** Sanitizar antes de enviar
```javascript
// Convertir "" → null para fechas y UUID antes de PATCH
const DATE_FIELDS = ['fecha_vencimiento', 'payment_due_date'];
DATE_FIELDS.forEach(f => {
    if (f in payload && !payload[f]) payload[f] = null;
});
if ('cuenta_contable_uuid' in payload && !payload.cuenta_contable_uuid) {
    payload.cuenta_contable_uuid = null;
}
```
**Bonus:** Backend ahora captura `DjangoValidationError` como 400 (antes era 500)

**Impacto:** Modal de edición acepta campos vacíos sin errores

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

**Completado en v2.98:**
- ✅ Error 500 en `partial_update` — empresa_id resolution
- ✅ Edit button + View offcanvas mutuamente excluyentes (Tabulator `composedPath()`)
- ✅ Campos XML siempre readonly, campos manuales siempre editables
- ✅ Validación de fechas vacías → null (sin 422 Bad Request)

**Opcionales futuros:**
- 💭 Columna "Monto Pagado" para pago parcial
- 💭 Historial de cambios en estado de pago
- 💭 Notificaciones automáticas por vencimiento
- 💭 Reportes de cobranza

> [!CAUTION]
> La eliminación de una factura implica el borrado en cascada de sus ítems y anexos; este proceso es irreversible y debe auditarse contra el libro mayor contable.

