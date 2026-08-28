# REM-P0-03 — Duplicados de Retenciones sin protección estructural

**Estado:** VERIFIED
**Prioridad:** P0
**App propietaria:** `contabilidad`
**Fecha:** 2026-08-28

## Hallazgo

`Retencion` (`apps/tenant/contabilidad/models.py:951`) no tenía ninguna
protección contra duplicados — ni `UniqueConstraint` de BD ni `.exists()`
de aplicación en `RetencionesService.crear_retenciones_desde_dict()`
(`apps/tenant/contabilidad/services/retenciones_service.py:207-297`), a
diferencia de `AsientoContable`/`MovimientoInventario`, que sí tienen
constraints reales.

## Investigación de datos reales (paso obligatorio antes de diseñar el constraint)

Se consultaron los 3 tenants reales (`home`, `qaisotest`, `shelltest1`) vía
`docker compose exec db psql`:

```sql
SELECT empresa_id, documento_origen_app, documento_origen_modelo,
       documento_origen_id, tipo, reversada, count(*)
FROM <schema>.contabilidad_retencion
GROUP BY 1,2,3,4,5,6 HAVING count(*) > 1;
```

**Resultado: 0 filas duplicadas en los 3 schemas — la tabla está
completamente vacía en los 3 (0 filas totales)**, incluyendo 0 filas con
`documento_origen_id=0`. Sin riesgo de dato real al aplicar el constraint.

## Determinación de la clave real (no asumida)

El propio docstring del modelo confirma: *"Múltiples retenciones (RETEFUENTE
+ RETEICA + RETEIVA) pueden existir para el mismo documento"* — la clave NO
es `documento_origen` solo, sino `(empresa, documento_origen_app,
documento_origen_modelo, documento_origen_id, tipo)`.

**Caso crítico descubierto durante el diseño**: `RetencionesService.
reversar_retencion()` crea una SEGUNDA fila `Retencion` que, cuando no se
pasa un `documento_reversada_id` distinto (reversal "in place", sin nota de
crédito explícita), comparte exactamente el mismo `documento_origen_app/
modelo/id` y `tipo` que la retención original. Un `UniqueConstraint` sin
condición habría bloqueado esta reversa legítima. Se excluyen las filas
`reversada=True` de la unicidad (`condition=Q(reversada=False)`), mismo
patrón ya usado por `AsientoContable.documento_origen_reversado`.

## Corrección

1. **`Retencion.Meta.constraints`**: nuevo `UniqueConstraint(fields=[
   'empresa','documento_origen_app','documento_origen_modelo',
   'documento_origen_id','tipo'], condition=Q(reversada=False) &
   ~Q(documento_origen_id=0), name='uniq_retencion_documento_origen_tipo_activa')`.
   Se excluye `documento_origen_id=0` (sentinel de "sin origen real" que el
   propio `crear_retencion()` acepta como default).

2. **`RetencionesService.reversar_retencion()`**: reordenado — el original
   se marca `reversada=True` ANTES de crear la fila de reversal (antes era
   al revés), y se envolvió en `@transaction.atomic()` (no lo estaba). El
   efecto final committeado es idéntico; solo cambia el orden intermedio
   dentro de la transacción, necesario para que el nuevo constraint no se
   dispare contra sí mismo en el caso "in place".

3. **`RetencionesService.crear_retencion()`**: idempotencia real — mismo
   patrón que `KardexService.registrar_movimiento()` (Inventario, sesión
   anterior): si el `INSERT` viola el nuevo constraint, se captura el
   `IntegrityError` y se retorna la fila activa ya existente en vez de
   fallar o duplicar.

## Archivos modificados

- `apps/tenant/contabilidad/models.py` — constraint nuevo + import de
  `transaction`.
- `apps/tenant/contabilidad/services/retenciones_service.py` — reorden +
  atomicidad en `reversar_retencion()`, idempotencia en `crear_retencion()`.

## Migración

`apps/tenant/contabilidad/migrations/0017_retencion_uniq_retencion_documento_origen_tipo_activa.py`
(generada). Aplicada a los 3 tenants reales tras confirmar 0 filas afectadas.

## Tests

`apps/tenant/contabilidad/tests/test_remediation_p0_03_retencion_duplicados.py`
(4 tests: idempotencia de creación duplicada, constraint de BD bloquea
INSERT directo duplicado, tipos distintos del mismo documento coexisten,
reversa "in place" no colisiona con el constraint). Se revisó primero
`test_retenciones_service.py::test_reversar_retencion` (existente) — usa un
`documento_reversada_id` distinto al original, por lo que nunca ejercitó el
caso "in place" ni colisiona con el reorden — sigue pasando sin cambios.

## Evidencia

Corrida local, 2026-08-28 (batch combinado con P0-02 y regresión completa
de `test_retenciones_service.py`, `DATABASE_HOST=127.0.0.1`/
`REDIS_URL=redis://127.0.0.1:6379/0`):

```
26 passed, 1 warning in 607.33s (0:10:07)
```

Incluye las 14 pruebas preexistentes de `test_retenciones_service.py`
(regresión completa, incluyendo `test_reversar_retencion`) sin ninguna
falla.

## Governance

Pendiente de confirmar en el barrido conjunto final de la misión.

## Riesgos / deuda pendiente

- No se agregó protección de duplicados a nivel de aplicación en
  `crear_retenciones_desde_dict()` más allá de lo que `crear_retencion()`
  ya hereda (la idempotencia vive en la función base, correctamente — no
  se duplicó lógica en el wrapper).
