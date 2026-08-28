# REM-P0-02 — Período contable cerrado no bloquea Facturas/Gastos

**Estado:** VERIFIED
**Prioridad:** P0
**Apps propietarias:** `facturas`, `gastos` (consumidores faltantes de
`contabilidad.services.selectors.verificar_periodo_cerrado()`, que sí es
propiedad de `contabilidad`)
**Fecha:** 2026-08-28

## Hallazgo

`PeriodoContable.__doc__` (`apps/tenant/contabilidad/models.py:568-575`)
afirma explícitamente: *"Bloquea edición/anulación de Facturas y Gastos en
periodos cerrados."* La función real que implementaría ese bloqueo,
`verificar_periodo_cerrado()` (`apps/tenant/contabilidad/services/
selectors.py:542-556`), solo se invocaba desde dentro de `contabilidad`
misma (para `AsientoContable`) — grep exhaustivo confirmó cero usos en
`apps/tenant/facturas/` y `apps/tenant/gastos/`.

## Causa raíz

La función se implementó como parte del ciclo de vida de `AsientoContable`
(FASE "v2.60 Fase 3: Inmutabilidad de Periodos Cerrados") pero nunca se
conectó a los dos consumidores adicionales que el propio docstring promete
cubrir. No hay evidencia de que fuera una decisión deliberada de excluir
Facturas/Gastos — es una integración incompleta, no una decisión de
negocio documentada.

## Impacto

Una `Factura` o un `DocumentoSoporte` (Gasto) podían editarse (PATCH) o
anularse con una fecha dentro de un período contable ya cerrado, sin ningún
bloqueo — descuadrando retroactivamente reportes de un período que ya se
consideraba definitivo.

## Corrección

Se invoca `verificar_periodo_cerrado(fecha, empresa_id)` (función de solo
lectura ya existente en `contabilidad`, mismo patrón de llamada cross-app
service-layer ya sancionado que usa `gastos → contabilidad.
RetencionesService`) desde los 2 puntos de edición/anulación reales de cada
app:

**Facturas** (`apps/tenant/facturas/services/business_service.py`):
- `actualizar_factura_limitado()` — valida contra `factura.fecha_emision`
  antes de aplicar cualquier PATCH (edición limitada).
- `FacturaViewSet.cambiar_estado()` (`apps/tenant/facturas/api/
  viewsets.py`) — valida solo cuando `nuevo_estado == 'ANULADA'` (la
  "anulación" explícita del docstring; otras transiciones ENVIADA/ACEPTADA/
  RECHAZADA/ERROR_TRANSMISION son parte del ciclo administrativo de
  sincronización con el portal DIAN, no una edición de negocio).

**Gastos** (`apps/tenant/gastos/`):
- `GastoBusinessService.anular_gasto()` — valida contra `documento.fecha`
  antes de anular.
- `GastoViewSet.perform_update()` (nuevo override, `apps/tenant/gastos/
  api/viewsets.py`) — DRF no tenía ningún hook de negocio en el PATCH por
  defecto; se agregó el override mínimo necesario, valida tanto la fecha
  actual del documento como la nueva fecha si se está editando.

Ninguna app importa modelos de `contabilidad` directamente — solo llama a
una función de selector de solo lectura, mismo patrón arquitectónico ya
usado por `gastos.RetencionesService`.

## Archivos modificados

- `apps/tenant/facturas/services/business_service.py`
- `apps/tenant/facturas/api/viewsets.py`
- `apps/tenant/gastos/services/business_service.py`
- `apps/tenant/gastos/api/viewsets.py`

## Modelo afectado

Ninguno. Sin migración.

## Tests

- `apps/tenant/facturas/tests/test_remediation_p0_02_periodo_cerrado.py`
  (4 tests: PATCH en período abierto/cerrado, anulación en período
  abierto/cerrado).
- `apps/tenant/gastos/tests/test_remediation_p0_02_periodo_cerrado.py`
  (4 tests, mismo patrón).

Se buscó primero tests existentes de `PeriodoContable` — los 6 archivos
encontrados (`test_multitenant_isolation.py`, `test_f24_e2e_circuito_
completo.py`, etc.) cubren el ciclo de `AsientoContable`, no de Facturas/
Gastos — no había ningún test previo del hallazgo real, se creó cobertura
nueva sin duplicar.

## Evidencia

Corrida local, 2026-08-28 (batch combinado con P0-03 y regresión de
retenciones, `DATABASE_HOST=127.0.0.1`/`REDIS_URL=redis://127.0.0.1:6379/0`):

```
26 passed, 1 warning in 607.33s (0:10:07)
```

## Governance

Pendiente de confirmar en el barrido conjunto final de la misión.

## Riesgos / deuda pendiente

- El guard de Gastos solo cubre el PATCH por defecto (`perform_update`) —
  no existe un método `actualizar()` de negocio dedicado en esta app (a
  diferencia de Facturas), así que se intervino en la capa más cercana
  disponible sin reestructurar la arquitectura existente de `gastos`.
- No se bloqueó `CREATE` de documentos con fecha en un período cerrado —
  el docstring de `PeriodoContable` solo promete "edición/anulación", y
  bloquear creación arriesgaría romper flujos legítimos de importación/
  backfill histórico no verificados en esta corrección (ver regla "no
  inventar reglas sin evidencia").
