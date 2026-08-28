# REM-P1-03 — Duplicidad bancaria sin protección real de BD

**Estado:** VERIFIED
**Prioridad:** P1
**App propietaria:** `bancos`
**Fecha:** 2026-08-28

## Hallazgo

`ExtractoBancario`/`TransaccionBancaria` solo tenían protección de
aplicación (`.exists()` en `ExtractoBancarioCRUDService.crear_extracto()`,
`crud_service.py:66-70`) contra duplicados — sin `UniqueConstraint` de BD,
con ventana TOCTOU real bajo doble-submit concurrente.

## Determinación de la clave real (regla explícita: no bloquear reimportación legítima)

**`ExtractoBancario`**: el propio código de aplicación ya usa
`(empresa, cuenta, mes, anio)` como clave de unicidad — se agregó el
backstop de BD con exactamente esa misma clave, ya validada por el negocio.

**`TransaccionBancaria`**: **deliberadamente NO se le agregó un
`UniqueConstraint`.** No existe un identificador externo confiable —
`dcto` (columna "Documento" del extracto Excel) no está garantizado como
único ni siempre poblado, y 2 transacciones legítimas distintas pueden
compartir fecha+descripción+valor (ej. dos transferencias idénticas el
mismo día). Imponer una clave inventada aquí habría violado la instrucción
explícita del plan: *"No imponer constraint que bloquee reimportaciones
correctas."* En su lugar, se cerró la causa real del riesgo de duplicado:
`ExtractoBancarioBusinessService.procesar_archivo_extracto()` ya es
idempotente por diseño (`DELETE` + re-`INSERT` completo de las
transacciones de un extracto) pero sin lock — dos llamadas concurrentes al
mismo extracto podían intercalar sus `DELETE`/`INSERT` y duplicar filas
momentáneamente. Se agregó `select_for_update()` sobre el propio
`ExtractoBancario` al inicio del método: la segunda llamada concurrente
espera a que la primera termine su `DELETE`+`INSERT` completo antes de
repetir el suyo — resultado neto idéntico (idempotente), sin duplicar.

## Investigación de datos reales

Se consultaron los 3 tenants reales — **0 filas duplicadas de
`ExtractoBancario`** por `(empresa, cuenta, anio, mes)` en `home`,
`qaisotest`, `shelltest1`. Sin riesgo de dato al aplicar el constraint.

## Corrección

1. `ExtractoBancario.Meta.constraints` — nuevo `UniqueConstraint(fields=[
   'empresa','cuenta','anio','mes'], name='uniq_extracto_bancario_empresa_
   cuenta_periodo')`.
2. `ExtractoBancarioBusinessService.procesar_archivo_extracto()` —
   `select_for_update()` sobre el extracto antes de procesar.

## Archivos modificados

- `apps/tenant/bancos/models.py`
- `apps/tenant/bancos/services/business_service.py`

## Migración

`apps/tenant/bancos/migrations/0006_extractobancario_uniq_extracto_bancario_empresa_cuenta_periodo.py`
— generada y **aplicada a los 3 tenants reales** (0 filas afectadas
confirmado antes de generar). Verificado post-aplicación vía
`pg_constraint` en `home`, `qaisotest` y `shelltest1`: constraint
`uniq_extracto_bancario_empresa_cuenta_periodo` presente en los 3.

## Tests

`apps/tenant/bancos/tests/test_remediation_p1_03_extracto_duplicado.py`
(3 tests: rechazo de aplicación ya existente sigue funcionando, constraint
de BD bloquea INSERT directo duplicado, distintos períodos de la misma
cuenta coexisten sin problema).

## Evidencia

Corrida local, 2026-08-28 (`DATABASE_HOST=127.0.0.1`/
`REDIS_URL=redis://127.0.0.1:6379/0`), 3/3 PASSED (parte del batch P1
combinado). Migración `0006` se aplica al cierre de la corrida de tests,
una vez no haya pytest local activo (ver `REMEDIATION_FINAL_REPORT.md`).

## Governance

Pendiente de confirmar en el barrido conjunto final de la misión.

## Riesgos / deuda pendiente

- `TransaccionBancaria` sigue sin protección estructural contra un
  duplicado genuino (ej. reimportar el mismo archivo Excel dos veces sin
  pasar por `procesar_archivo_extracto()` del mismo extracto, sino creando
  un extracto NUEVO para el mismo período — bloqueado ahora por el
  constraint de `ExtractoBancario` del punto 1, así que este vector queda
  cerrado indirectamente). Si en el futuro el extracto Excel trae un
  identificador de transacción bancaria real y confiable, sería la base
  correcta para un constraint directo — no inventado en esta corrección.
