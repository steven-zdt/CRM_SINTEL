# REM-P1-05 — Cierre contable sin checklist previo

**Estado:** VERIFIED
**Prioridad:** P1
**App propietaria:** `contabilidad`
**Fecha:** 2026-08-28

## Hallazgo

`ContabilidadBusinessService.cerrar_periodo()` (`apps/tenant/contabilidad/
services/business_service.py:350-361`) solo verificaba que el período no
estuviera ya `CERRADO` — sin checklist de documentos pendientes ni
asientos descuadrados antes de permitir el cierre.

## Corrección

Nuevo método `ContabilidadBusinessService.pre_close_validation(periodo)`,
invocado desde `cerrar_periodo()` antes de cambiar el estado. Retorna
`{puede_cerrar: bool, bloqueos: [...]}`, cada bloqueo con `tipo`, `app`,
`cantidad`, `detalle` y `accion_recomendada` (nunca solo "no se puede
cerrar", per instrucción explícita del plan).

Dos categorías de bloqueo, ambas con evidencia real, ninguna inventada:

1. **Asientos descuadrados** — query defensiva sobre `AsientoContable.
   debe_total != haber_total` dentro del período. Por diseño,
   `Contabilizador._validar_cuadratura()` ya impide crear un asiento
   descuadrado — este chequeo es una verificación de defensa en
   profundidad, no se espera que encuentre nada en operación normal, pero
   se incluye porque el plan lo pide explícitamente.
2. **Documentos sin contabilizar dentro del período** — se reutilizan los
   4 extractores YA EXISTENTES (`ExtractorFacturas`, `ExtractorGastos`,
   `ExtractorInventario`, `ExtractorNomina`), cada uno SSoT de "qué falta
   contabilizar" de su propia app — no se reimplementó esa lógica. Se
   filtra su resultado (`TransaccionEconomica.fecha`) contra el rango
   `[periodo.fecha_inicio, periodo.fecha_fin]`.

## Archivos modificados

- `apps/tenant/contabilidad/services/business_service.py`

## Modelo afectado

Ninguno. Sin migración.

## Tests

`apps/tenant/contabilidad/tests/test_remediation_p1_05_cierre_checklist.py`
(5 tests: período limpio cierra sin problema, asiento descuadrado bloquea
el cierre, movimiento de inventario sin contabilizar dentro del período
bloquea el cierre, un documento pendiente FUERA del rango del período no
lo bloquea, guard original "ya cerrado" sigue funcionando). No existía
ningún test previo de `cerrar_periodo()` en absoluto — gap real, no
duplicado (grep repo-wide confirmó 0 referencias en `apps/tenant/
contabilidad/tests/`).

## Evidencia

Corrida local, 2026-08-28: 5/5 PASSED (parte del batch P1 combinado, 17/17
en la corrida final).

**Hallazgo real del propio ciclo de validación (paso G/I del plan) —
bug de código, no de test**: la primera corrida falló
(`test_asiento_descuadrado_en_el_periodo_bloquea_el_cierre`) porque la
query original filtraba `total_debe`/`total_haber` — campos LEGADO de
`AsientoContable` que `save()` sobreescribe automáticamente en cada
guardado con los valores de `debe_total`/`haber_total` (los campos
autoritativos, ver `models.py:434-438`, comentario *"Sync debe_total/
haber_total with new fields for compatibility"*). Con un `AsientoContable`
creado sin `debe_total`/`haber_total` explícitos (ambos en su default
`0.00`), `total_debe`/`total_haber` quedaban sincronizados a `0.00`/`0.00`
tras el `save()` — perfectamente "cuadrados" pese a que el test intentaba
simular un descuadre. **Corregido en `pre_close_validation()`**: la query
ahora filtra `debe_total`/`haber_total` (los campos reales). El test
también se corrigió para construir el descuadre sobre esos mismos campos
autoritativos.

## Governance

Pendiente de confirmar en el barrido conjunto final de la misión.

## Riesgos / deuda pendiente

- No se agregó un mecanismo de "forzar cierre pese a bloqueos" — el plan
  no lo pidió, y agregarlo por intuición violaría la regla de no inventar
  política de negocio. Si el negocio necesita una vía de excepción
  auditada, es una decisión de producto (P2), no parte de esta corrección.
- Los extractores de `gastos`/`facturas`/`nomina` no se ejercitaron con
  datos reales en los tests nuevos (solo `inventario`, el más simple de
  configurar) — el mecanismo es idéntico para los 4 (mismo bucle,
  `extraer_pendientes()` + filtro de fecha), así que el riesgo de que
  alguno se comporte distinto es bajo, pero no está cubierto con evidencia
  directa para esos 3.
