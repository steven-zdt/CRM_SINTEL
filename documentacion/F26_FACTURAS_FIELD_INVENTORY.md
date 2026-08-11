# F26 — Matriz de Campos de `apps/tenant/facturas`

**Fecha:** 2026-08-10

Metodología: lectura completa de `models.py` + grep exhaustivo de consumidores reales
en todo el repo (servicios, selectors, serializers, viewsets, templates, JS,
management commands, tests). Ninguna fila se completó por suposición.

Acciones: `KEEP` (mantener sin cambios), `RENAME`, `MOVE`, `DERIVE` (calculado, no
almacenar crudo), `REMOVE` (eliminado en este pase), `DEFER` (candidato real pero no
ejecutable de forma segura ahora, con razón documentada).

## `Factura` (modelo esencial)

| Campo | Origen | Se usa | Quién lo usa | Acción |
|---|---|---|---|---|
| `uuid`, `numero`, `prefijo`, `consecutivo` | XML (ID) | Sí | Lookup API, idempotencia por número, UI | KEEP |
| `tipo`, `estado`, `estado_pago` | XML/calculado | Sí | Filtros, UI, flujo de negocio | KEEP |
| `naturaleza` | Calculado (NIT emisor vs `Empresa.nit`) | Sí | Filtros, reportes, DSV, `Categoria` en listados | KEEP (categoría B — derivado, no viene literal del XML) |
| `categoria` | Manual (usuario) | Sí | `MANUAL_EDITABLE_FIELDS`, UI editor, filtros | KEEP (confirmado con consumidor real en `offcanvas_editar_factura.html`) |
| `ubl_version`, `customization_id`, `profile_id`, `profile_execution_id`, `invoice_type_code` | XML | Parcial (trazabilidad técnica) | Reconstrucción del documento, auditoría DIAN | KEEP |
| `fecha_emision`, `fecha_vencimiento` | XML | Sí | Ordenamiento, reportes, vencimientos | KEEP |
| `emisor_*` (6 campos), `receptor_*` (5 campos) | XML (snapshot) | Sí | Cálculo `naturaleza`, DSV, **Snapshot Pattern legal** (ver `facturas_business_logic.md` §3: el nombre del cliente en la factura NO debe cambiar si el maestro de Clientes cambia después) | KEEP — no consolidar con `Cliente`/`Proveedor`/`Empresa` pese a la aparente redundancia: es un requisito legal deliberado, no deuda técnica |
| `moneda`, `subtotal`, `impuestos`, `total` | XML | Sí | Contabilidad, reportes, UI | KEEP |
| `forma_pago`, `medio_pago_codigo`, `payment_due_date` | XML/manual | Sí | UI, cartera | KEEP |
| `cotizacion_uuid`, `cotizacion_numero` | Vinculación manual | Sí | `CotizacionBridge`, cross-app con `proyectos`, 3 serializers, JS, templates | KEEP (confirmado activo, no vestigial) |
| `cliente_uuid`, `proveedor_uuid` | Resuelto en `guardar_desde_dto` | Sí | DSV, vinculación con `clientes`/`proveedores` | KEEP |
| `cufe` | XML | Sí | Idempotencia legal (unique constraint), `fast_get_cufe` | KEEP |
| `qr_code`, `qr_url` | XML | Sí | UI de detalle (código QR DIAN) | KEEP |
| `autorizacion_*` (6 campos) | XML | Sí | Validación de vigencia de resolución DIAN, UI | KEEP |
| `dian_validation_*` (4 campos) | XML (ApplicationResponse) | Sí | Estado de validación DIAN, UI | KEEP |
| `dian_response_xml` | XML | Parcial — redundante con `FacturaAnexos.application_response_xml` | Casi ningún lector directo (solo comentarios/backfill) | **DEFER** (F26-005) |
| `xml_content` | XML | Parcial — solo en flujo de venta emisora | `crear_factura_desde_venta`, `backfill_facturas_anexos.py` (fallback) | **DEFER** (F26-003) |
| `xml_file_path` | Nunca escrito | No | Ninguno (0 consumidores, 0 datos) | **REMOVED** (F26-002, migración `0032`) |
| `sede` | Manual/contexto organizacional | Sí | KPIs por sede, `MANUAL_EDITABLE_FIELDS`, `OrganizationalContext` | KEEP |

## `ItemFactura` (modelo esencial)

| Campo | Origen | Se usa | Quién lo usa | Acción |
|---|---|---|---|---|
| `uuid`, `linea_id`, `codigo`, `descripcion` | XML (`InvoiceLine`) | Sí | UI, resolución de inventario por código | KEEP |
| `item_inventario_uuid`/`tipo`/`codigo` | Resuelto por código contra catálogo | Sí | Vinculación a `Producto`/`Servicio`, `InventarioItemBridge` | KEEP |
| `cantidad`, `unidad_medida`, `valor_unitario` | XML | Sí | Cálculo de totales, contabilidad | KEEP |
| `porcentaje_iva`, `valor_iva` | XML/calculado | Sí | Desglose fiscal | KEEP |
| `porcentaje/valor_retefuente/reteiva/reteica` (6 campos) | XML | Parcial (fallback) | `total_*_item` properties, `migrate_retenciones.py` | **DEFER** (F26-004) |
| `subtotal`, `total` | Calculado en `save()` | Sí | UI, contabilidad | KEEP |
| `es_servicio` | Heurística (`unitCode == 'ZZ'`) | Sí | Excluir de Kardex/inventario | KEEP (categoría B — derivado) |
| `orden` | Manual/secuencial | Sí | Ordenamiento de líneas en UI | KEEP |

## `NotaCredito` / `ItemNotaCredito` (DOC-M14, sin cambios en F26)

Ya auditados y minimizados en DOC-M14 (`ItemNotaCredito` es un espejo deliberadamente
más pequeño que `ItemFactura`, sin los 6 campos de retención por línea — ver
docstring del modelo). F26 confirma que siguen siendo el conjunto mínimo necesario
para: identificar producto (`item_inventario_uuid`), cantidad devuelta, valor,
impuesto, documento origen (implícito via FK), sede (heredada de la factura
original), idempotencia (`UniqueConstraint` de `MovimientoInventario`),
`ENTRADA_DEVOLUCION`. Sin cambios.

## `FacturaAnexos` (modelo de integración/auditoría)

| Campo | Se usa | Acción |
|---|---|---|
| `ubl_xml`, `application_response_xml` | Sí — mecanismo de trazabilidad único y correcto (ver `F26_XML_DATA_POLICY.md`) | KEEP |
| `pdf_file` | Sí — representación gráfica, endpoint dedicado | KEEP |

## `FacturaImpuesto` (modelo de auditoría/integración)

Confirmado `KEEP`: desglose real por tipo/porcentaje/base que `Factura.impuestos`
(total agregado) no provee, con consumidor API activo (`FacturaImpuestoSerializer`).
Gap identificado pero NO corregido en este pase (fuera de alcance — no es
sobre-persistencia, es integración incompleta): el extractor de contabilidad no
existe (`apps/tenant/contabilidad/integracion/extractores/facturas.py` no se
encontró) — `FacturaImpuesto` no se consume aún desde Contabilidad Pull. Esto es una
brecha de integración, no un campo redundante; queda fuera del alcance de F26
(que es sobre `facturas`, no sobre extender Contabilidad).

## `MailIngestionRun` / `MailInboxState` (modelos de ingesta)

Auditados por lectura de modelo (sin necesidad de grep adicional — su propósito es
autoexplicativo y single-purpose): `MailIngestionRun` rastrea ejecuciones de Celery
(`task_id` único, `status`, `counts`/`summary` JSON ligero — sin duplicar datos de
`Factura`). `MailInboxState` rastrea `last_seen_uid` por buzón IMAP para
procesamiento incremental — sin datos redundantes con `Factura`/ingesta. **KEEP**
ambos sin cambios; no se encontró duplicación entre mail/factura/XML/ingesta que
amerite consolidación (regla F26 §34: "solo si el código lo demuestra").

## Código muerto identificado (no modelo, pero relevante)

`apps/tenant/facturas/tasks.py::procesar_factura_xml_task` — Celery task sin ningún
llamador real en todo el repo (grep exhaustivo, 0 resultados fuera de su propia
definición y 1 test). **DEFER** — no se elimina en este pase porque una Celery task
podría estar registrada en un `celery beat` schedule externo al repo (infraestructura,
no código) que no se puede auditar desde aquí con certeza.
