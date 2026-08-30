# P0-03 — Duplicados de Retenciones sin protección estructural

**Estado:** VERIFIED
**App propietaria:** `contabilidad`
**Fecha:** 2026-08-28

## Hallazgo

`Retencion` no tenía protección contra duplicados — ni `UniqueConstraint`
de BD ni `.exists()` de aplicación en
`RetencionesService.crear_retenciones_desde_dict()`.

## Investigación de datos reales (previa a diseñar el constraint — regla P0-03-B/E)

Consulta a los 3 tenants reales (`home`, `qaisotest`, `shelltest1`) vía
`docker compose exec db psql`:

```sql
SELECT empresa_id, documento_origen_app, documento_origen_modelo,
       documento_origen_id, tipo, reversada, count(*)
FROM <schema>.contabilidad_retencion
GROUP BY 1,2,3,4,5,6 HAVING count(*) > 1;
```

**Resultado: 0 filas duplicadas, 0 filas totales, en los 3 schemas.**
Clasificación de datos existentes: **N/A — tabla vacía en los 3
tenants**. No hubo necesidad de limpieza previa (P0-03-E) porque no
existía dato real de producción sobre el cual aplicar la constraint —
confirmado antes, no asumido.

## Identidad de retención (P0-03-C — no asumida, confirmada contra el modelo real)

El propio docstring del modelo confirma: *"Múltiples retenciones
(RETEFUENTE + RETEICA + RETEIVA) pueden existir para el mismo
documento"* — la clave NO es `documento_origen` solo. Clave real
confirmada: `(empresa, documento_origen_app, documento_origen_modelo,
documento_origen_id, tipo)`.

**Caso crítico descubierto durante el diseño**: `reversar_retencion()`
crea una segunda fila `Retencion` que, en el caso "in place" (sin
`documento_reversada_id` explícito), comparte exactamente el mismo
`documento_origen_*`/`tipo` que el original. Un constraint sin condición
habría bloqueado esta reversa legítima — se excluyen las filas
`reversada=True` (`condition=Q(reversada=False)`), mismo patrón que
`AsientoContable.documento_origen_reversado`.

## Constraint (P0-03-D, tenant-safe)

```python
UniqueConstraint(
    fields=['empresa', 'documento_origen_app', 'documento_origen_modelo',
            'documento_origen_id', 'tipo'],
    condition=Q(reversada=False) & ~Q(documento_origen_id=0),
    name='uniq_retencion_documento_origen_tipo_activa',
)
```

`empresa` es parte de la clave → aislamiento por tenant garantizado a
nivel de constraint, no solo por schema. `documento_origen_id=0`
(sentinel de "sin origen real") excluido explícitamente.

## Idempotencia (P0-03-F)

`RetencionesService.crear_retencion()`: si el `INSERT` viola el
constraint (creación repetida, retry, doble request), se captura
`IntegrityError` y se retorna la fila activa ya existente — nunca
falla ni duplica. Probado explícitamente en
`test_remediation_p0_03_retencion_duplicados.py::test_crear_retencion_duplicada_retorna_la_existente_idempotente`.

## Reversas (P0-03-G)

`reversar_retencion()` reordenado (`@transaction.atomic`, antes no lo
era): el original se marca `reversada=True` ANTES de crear la fila de
reversa — el par original+reversa nunca se interpreta como 2 retenciones
activas duplicadas (el constraint excluye `reversada=True`). Probado en
`test_reversar_retencion_in_place_no_colisiona_con_el_constraint` +
regresión completa de `test_retenciones_service.py::test_reversar_retencion`
(14 tests preexistentes, 0 fallas).

## Migración

`contabilidad/migrations/0017_retencion_uniq_retencion_documento_origen_tipo_activa.py`
— generada y **aplicada a los 3 tenants reales**.

## Tests

4 nuevos (`test_remediation_p0_03_retencion_duplicados.py`) + 14
regresión (`test_retenciones_service.py`) — 18/18 PASS (parte del batch
combinado de 26, 607.33s).

## Riesgos / deuda pendiente

Ninguno — identidad confirmada contra el modelo real, datos verificados
antes de aplicar, idempotencia y reversas probadas.
