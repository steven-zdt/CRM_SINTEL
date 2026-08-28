# REM-P3-03 — Widget "Gastos → Vencidos" mal etiquetado

**Estado:** VERIFIED
**Prioridad:** P3
**App propietaria:** `dashboard` (con `gastos` como fuente de dato)
**Fecha:** 2026-08-28

## Hallazgo

`GastosExtractor.extraer_metricas()` (`apps/tenant/dashboard/services/
extractores/gastos_ext.py:34`, hallazgo original de
`documentacion/auditoria_empresarial/BUSINESS_GAP_MATRIX.md`) calculaba
`gastos_pendientes = gastos_activos` (documentos NO anulados) y
`gastos_vencidos = gastos_anulados` (documentos anulados/cancelados). El
frontend (`dashboard_main.js:166`) pintaba esto literalmente como columna
"Vencidos" en rojo — un usuario veía "Vencidos: 5" pensando en gastos
atrasados de pago, cuando en realidad eran documentos anulados.

## Investigación (regla explícita: confirmar qué significa "Vencido" antes de corregir)

`DocumentoSoporte` (`apps/tenant/gastos/models.py`) **no tiene ningún
campo `fecha_vencimiento` ni `estado_pago`/`pagado`** — confirmado con
grep. El concepto de "vencido" (fecha de pago superada, aún sin pagar) no
existe en el modelo de datos real de Gastos. No hay forma honesta de
calcular un "vencido" real sin inventar una regla de negocio nueva
(¿vencido a los N días de la fecha del documento? ¿basado en qué campo?) —
prohibido explícitamente por el plan ("No inventar reglas fiscales sin
evidencia").

## Corrección

Se optó por **relabeling honesto** en vez de fabricar un cálculo: el campo
se renombró de `gastos_vencidos` a `gastos_anulados` en toda la cadena
(DTO → serializer → extractor → frontend), reflejando exactamente lo que
el dato mide. La etiqueta visible cambió de "Vencidos" a "Anulados".

## Archivos modificados

- `apps/tenant/dashboard/services/dtos.py` (`WidgetGastosDTO`)
- `apps/tenant/dashboard/services/extractores/gastos_ext.py`
- `apps/tenant/dashboard/api/serializers.py` (`WidgetGastosSerializer`)
- `apps/tenant/dashboard/static/dashboard/js/features/dashboard_main.js`
- `apps/tenant/dashboard/tests/test_simple.py` (2 usos del kwarg antiguo)
- `apps/tenant/dashboard/tests/test_viewsets.py` (1 uso del kwarg antiguo)

## Modelo afectado

Ninguno — es un DTO en memoria (dataclass), no un modelo persistido. Sin
migración.

## Tests

No se creó un test nuevo dedicado — el cambio es un rename de campo sin
lógica nueva que probar; los 3 tests existentes que construían
`WidgetGastosDTO(gastos_vencidos=...)` se actualizaron al nuevo nombre de
kwarg (`REUSE/UPDATE`, no se duplicó cobertura). Se confirmó que ningún
test ejercitaba `GastosExtractor.extraer_metricas()` directamente (grep
sin resultados) — ese cálculo en sí seguía sin cobertura antes y después
de esta corrección, fuera del alcance mínimo de un rename de etiqueta.

## Evidencia

Regresión completa de `dashboard` (los 3 archivos de tests existentes que
referencian el campo renombrado), corrida local 2026-08-28:
`test_simple.py` + `test_viewsets.py`, 22/22 PASSED.

## Governance

Pendiente de confirmar en el barrido conjunto final de la misión.

## Riesgos / deuda pendiente

- Si el negocio necesita un indicador real de "gastos vencidos" (pago
  atrasado), requiere primero agregar los campos de dato necesarios
  (`fecha_vencimiento`, estado de pago) a `DocumentoSoporte` — fuera de
  alcance de esta corrección de etiqueta.
