# F26 — Reporte de Refactorización

**Fecha:** 2026-08-10

## 1. `guardar_desde_dto()` — decisión: NO fragmentar (documentada, no especulativa)

El prompt maestro sugería (§18) separar `guardar_desde_dto()` en servicios
especializados (`InvoiceDTOValidator`, `InvoiceIdentityResolver`,
`InvoicePartyResolver`, `InvoiceItemResolver`, `InvoicePersistenceService`,
`CreditNotePersistenceService`) **solo si existe responsabilidad real** (§18/§19: "NO
fragmentar por fragmentar").

**Auditoría real del método** (`business_service.py:310-780`, ~470 líneas): tiene
fases internas claras marcadas por comentarios (resolución de empresa, extracción de
campos, validación de NIT, resolución de naturaleza, idempotencia por CUFE,
resolución de cliente/proveedor, construcción de `factura_data`, persistencia,
impuestos, retenciones, rama NC con items + `ENTRADA_DEVOLUCION`, rama normal con
items). Es un método largo pero **no tiene ramas de responsabilidad mezclada de
dominios distintos** (no conoce Kardex directamente salvo la llamada explícita y
aislada a `_generar_entrada_devolucion()`, no conoce Contabilizador, no construye XML
DIAN) — su longitud viene de la cantidad de campos DIAN reales que debe mapear
(consistente con `F26_FACTURAS_FIELD_INVENTORY.md`: ~56 campos de `Factura` con
origen real en el XML), no de mezclar responsabilidades ajenas.

**Decisión:** `DEFER`, no fragmentar en este pase. Justificación (§75, preferir la
opción menos destructiva):
1. Fragmentar en 5-6 clases nuevas es un cambio de superficie amplia sobre un método
   que maneja datos legales/DIAN de producción, sin que el propio código demuestre
   una necesidad real de reutilización de esas piezas por separado (nadie más
   necesita `InvoiceItemResolver` de forma aislada hoy).
2. Verificar que una fragmentación de este tamaño preserva el comportamiento exacto
   (incluyendo los 3 casos de idempotencia, las 2 ramas DSV VENTA/COMPRA, la rama NC
   completa con `ENTRADA_DEVOLUCION`) requeriría una suite de tests unitarios por
   cada pieza nueva que no existe hoy y que este pase no puede construir con
   confianza suficiente dentro del alcance ya cubierto (18 tests históricos + 5
   DOC-M14 + regresión F21-F25).
3. El propio prompt maestro es explícito: "el objetivo es menos código, menos
   dependencias, menos duplicación, más claridad" — dividir un método cohesivo en 6
   clases nuevas **aumenta** el número de archivos/clases sin reducir líneas de
   código real ni duplicación demostrada.

**Lo que SÍ se hizo** (cambios reales, de bajo riesgo, dentro de `guardar_desde_dto`):
consumo de `dto["items"]` en la rama NC (ya implementado en DOC-M14, no en F26) —
sin cambios adicionales de estructura en F26.

## 2. Selectors — auditoría de `.only()`/`select_related()`

`apps/tenant/facturas/services/selectors.py` revisado: los usos de
`.objects.filter()` son mayoritariamente `.aggregate()` (no materializan instancias
completas, no aplica `.only()`) o `.first()` sobre lookups puntuales ya acotados. Los
`ViewSet.get_queryset()` (`viewsets.py`) ya usan `.select_related()`/`.only()`
consistentemente (confirmado en `NotaCreditoViewSet` durante DOC-M14, y en
`FacturaViewSet`/`ItemFacturaViewSet` por inspección — sin `SELECT *` real
encontrado). **Sin cambios necesarios** — la disciplina ya estaba aplicada antes de
F26.

## 3. Service Layer — confirmado intacto

`ViewSet → ServiceMixin → BusinessService → CRUDService` verificado sin lógica de
negocio filtrada hacia `ViewSet`/`Serializer`/`Model` más allá de validaciones
sintácticas (los `save()` de `ItemFactura`/`ItemNotaCredito` calculan totales
aritméticos simples — no lógica de negocio real, mismo patrón ya establecido y
aceptado en todo el codebase desde F21). Sin cambios.

## 4. Parser vs Persistencia — ya separado correctamente

Confirmado (§16): el parser universal (`apps/services/document_parser/xml_parser/parser.py`)
NO conoce Django ni llama a `Factura.objects.create()` en ningún punto — retorna un
DTO puro. `guardar_desde_dto()` es quien persiste. Esta separación **ya existía**
antes de F26 (arquitectura "Pipeline Universal — Solo Parsing", confirmada por el
propio docstring de `ingest_service.py`). Sin cambios necesarios.

## 5. Código muerto eliminado

- `Factura.xml_file_path` (campo, ver `F26_FINDINGS.md` F26-002).
- Referencia a `xml_file_path` en `admin.py`.
- `'orden_compra'` en `MANUAL_EDITABLE_FIELDS` (campo fantasma, no código muerto per
  se, pero un bug de configuración de riesgo real — ver F26-001).

## 6. Resumen

F26 confirma que `apps/tenant/facturas` **ya cumplía mayormente** con los principios
que el prompt maestro pedía verificar (parser/persistencia separados, Service Layer
intacto, XML no duplicado sistemáticamente en el modelo). Las correcciones reales
aplicadas son quirúrgicas (1 campo eliminado, 1 bug de configuración corregido, 8
tests reparados) en vez de una reescritura estructural — consistente con la regla
§19 "NO sobrearquitectar" y con la falta de evidencia de que una fragmentación mayor
resolviera un problema real y demostrado.
