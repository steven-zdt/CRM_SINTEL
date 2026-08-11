# F26-006 — Fix: idempotencia real cuando el documento no trae CUFE

**Fecha:** 2026-08-11
**Contexto:** hallazgo DEFERRED de F26 (`F26_FINDINGS.md`, `F26_FINAL_REPORT.md`
§25), seleccionado como siguiente paso post-F26 por decisión explícita del
usuario entre varias opciones DEFERRED.

## Bug

`FacturaBusinessService.guardar_desde_dto()` solo hacía el chequeo de
idempotencia dentro de `if cufe:`. Cuando `identificadores` venía vacío,
`cufe` se resolvía a `""` (cadena vacía, no `None`) — esa rama se saltaba
por completo y el código intentaba crear un segundo documento igual. Como
`Factura.cufe` (y `NotaCredito.cude`) tienen `unique=True`, el segundo
`INSERT` con `cufe=""`/`cude=""` chocaba contra la constraint de BD y
propagaba un `IntegrityError` sin manejar hasta el llamador, en vez de una
respuesta HTTP limpia (200, `created: False`) como sí ocurre en el camino
con CUFE.

## Fix

En `apps/tenant/facturas/services/business_service.py`, dentro de
`guardar_desde_dto()`:

1. **Fallback de idempotencia por `numero`+`empresa`** cuando `cufe` es
   falsy — mismo criterio "ya existe" (200, `created: False`) que la rama
   por CUFE, tanto para `Factura` como para `NotaCredito`.
2. **Normalización `cufe or None` / `cude or None`** al construir
   `factura_data`/al crear `NotaCredito` — restaura la semántica real de
   `unique=True` + `null=True` (Postgres permite múltiples `NULL`, no
   permite múltiples `""`), para que dos documentos **legítimamente
   distintos** sin CUFE (numero distinto) no choquen entre sí por accidente.

`NotaCredito.cude` no tenía `null=True` (a diferencia de `Factura.cufe`, que
ya lo tenía desde v2.60) — se agregó `null=True, blank=True` al campo y se
generó la migración `0033_alter_notacredito_cude.py` (aditiva, sin pérdida
de datos: filas existentes con `cude=""` permanecen `""`, solo se relaja la
restricción `NOT NULL` a nivel de columna).

## Tests

- `test_materializar_from_dto.py::test_idempotencia_por_numero` — reescrito:
  antes documentaba el `IntegrityError` con `assertRaises`; ahora verifica
  el comportamiento correcto (200, `created: False`, `cufe is None`).
- `test_materializar_from_dto.py::test_dos_facturas_distintas_sin_cufe_no_chocan`
  (nuevo) — dos facturas con `numero` distinto y sin CUFE coexisten sin
  chocar.
- `test_nota_credito_pipeline.py::test_12_idempotencia_sin_cude_no_revienta`
  (nuevo) — mismo escenario para `NotaCredito`, usando el shape real del
  pipeline universal (`"type": "creditnote"`, no `"tipo": "NC"` literal) para
  no confundirse con el chequeo preexistente "already_has_nc" (que ya
  cubría con gracia el caso de reimportar la misma NC para la misma
  factura, independientemente del CUFE — ver nota abajo).

## Nota: por qué el gap era más estrecho de lo documentado para `NotaCredito`

Para `NotaCredito` existe un chequeo independiente y preexistente
("¿la factura original ya tiene una NC?", `business_service.py` ~línea 537)
que ya devolvía un 422 limpio (`already_has_nc`) al reimportar una NC para
la misma factura, **con o sin CUFE**. El `IntegrityError` real solo podía
ocurrir para **dos NC de facturas distintas**, ambas sin CUDE — un caso más
angosto que el documentado originalmente, pero real (y ahora cubierto por
la normalización a `None`).

## Regresión

```
docker compose exec -T web python -m pytest \
  apps/tenant/facturas/tests/test_materializar_from_dto.py \
  apps/tenant/facturas/tests/test_nota_credito_pipeline.py \
  apps/tenant/facturas/tests/test_devolucion_nota_credito.py \
  apps/tenant/facturas/tests/test_ingesta_ubl.py \
  -q --tb=short
```

`25 passed, 1 failed in 602.87s`. El único fallo
(`test_ingesta_ubl.py::test_procesar_factura_xml_task`) es un bug de test
preexistente y **no relacionado**: la `Empresa` dummy que crea el test usa
`nit="900000001"`, que no coincide con ninguna de las partes del XML de
fixture (`900123456`/`901999888`), así que falla en la validación de NIT
(`business_service.py:375`) **antes** de llegar a cualquier código tocado
por este fix (que empieza en la línea ~433). Confirmado corriendo el mismo
test **completamente solo** (un solo archivo, sin ningún otro
`TenantTestCase` antes) — falla igual, lo cual además corrige el diagnóstico
previo de F26 (`F26_REGRESSION_REPORT.md`) que lo atribuía a contaminación
de schema compartido entre archivos `TenantTestCase`. Issue real,
independiente, flageado por separado (no corregido aquí — fuera de alcance
de F26-006).

`manage.py check`: sin issues. `makemigrations --check`: sin cambios
pendientes. Governance CLI: `FINAL STATUS: PASS`.

## Migraciones

**1 nueva:** `0033_alter_notacredito_cude.py` — `AlterField` aditivo
(`null=True, blank=True` en `NotaCredito.cude`), aplicada a las 3 empresas
del entorno (`home`, `qaisotest`, `shelltest1`).

## Estado

`F26-006`: **RESUELTO**. `F26_FINDINGS.md` y `F26_FINAL_REPORT.md`
actualizados para reflejar el fix.
