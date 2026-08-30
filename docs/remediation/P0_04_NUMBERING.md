# P0-04 — Numeración contable concurrente

**Estado:** VERIFIED
**App propietaria:** `contabilidad`
**Fecha:** 2026-08-28

## Hallazgo

`TipoComprobante.obtener_siguiente_numero()` era el único generador de
numeración de todo el sistema sin `select_for_update()` — leía
`consecutivo_actual` (potencialmente obsoleto en memoria), lo
incrementaba y guardaba sin bloqueo de fila.

## Corrección (ya aplicada y VERIFIED en la pasada anterior)

Reescrito con `select_for_update()` sobre la propia fila dentro de
`transaction.atomic()`, antes de leer/incrementar/guardar. Mismo patrón
ya usado en `cotizaciones`, `compras`, `ventas`, `empleados`.

## Concurrencia real (P0-04-D — cierre del gap admitido en la pasada anterior)

La pasada anterior (`REM-P0-04.md`) documentó honestamente: *"no se
escribió un test con threads/conexiones DB concurrentes reales... no
existe un harness para eso en la base de tests actual"*. Esta misión
exige explícitamente simular 2 y 10 usuarios concurrentes — se construyó
el harness (reutilizando el patrón ya establecido en
`apps/tenant/proveedores/tests/test_idempotence_v2614.py`:
`pytest.mark.django_db(transaction=True)` + tenant fixture module-scoped
+ `schema_context()`), sin inventar infraestructura nueva.

**Diseño del test** (`test_remediation_p0_04_concurrencia_real.py`):

- `django_db(transaction=True)` — los datos de setup quedan realmente
  COMMITEADOS (no en una transacción de test sin commit), condición
  necesaria para que `select_for_update()` bloquee de verdad entre
  conexiones distintas.
- Cada `threading.Thread` de Python obtiene su propia conexión de BD
  (`django.db.connection` es thread-local); `schema_context()` dentro de
  cada thread fija el `search_path` de esa conexión específica.
- Se cierra la conexión de cada thread explícitamente al finalizar
  (`connection.close()`).
- 2 escenarios: 2 threads concurrentes, 10 threads concurrentes, cada
  uno contra su propio `TipoComprobante` (aislado por `codigo` para no
  interferir entre escenarios).

**Resultado:** ver evidencia abajo (sección actualizada tras la corrida).

## Tests

- `test_remediation_p0_04_numeracion_comprobante.py` (3 tests,
  secuencial, mismo proceso/conexión) — VERIFIED en la pasada anterior,
  156.90s.
- `test_remediation_p0_04_concurrencia_real.py` (2 tests, concurrencia
  real multi-thread/multi-conexión, 2 y 10 usuarios) — **nuevo en esta
  pasada**.

## Evidencia

Corrida local, 2026-08-30 (`DATABASE_HOST=127.0.0.1`/
`REDIS_URL=redis://127.0.0.1:6379/0`), 167.32s:

```
test_dos_usuarios_concurrentes_numeros_unicos_sin_deadlock   PASSED
test_diez_usuarios_concurrentes_numeros_unicos_sin_deadlock  PASSED
```

**2 usuarios concurrentes**: 2 threads con conexiones de BD distintas
generaron `{'DOS0-00001', 'DOS0-00002'}` — únicos, secuencia sin huecos,
`consecutivo_actual` final = 3 (1 inicial + 2), sin excepciones ni
deadlock.

**10 usuarios concurrentes**: 10 threads con conexiones de BD distintas
generaron los 10 números `DIEZ-00001` … `DIEZ-00010` — todos únicos, sin
huecos, `consecutivo_actual` final = 11 (1 inicial + 10), sin
excepciones ni deadlock. `select_for_update()` serializó correctamente
las 10 transacciones concurrentes contra la misma fila.

**Hallazgo operativo (no afecta la corrección del fix, documentado por
transparencia — regla de "documentar honestamente lo que se hizo y lo
que quedó fuera")**: pytest reportó *"2 passed, 2 errors"* — los 2
`ERROR` ocurren **después** de que cada test ya completó y afirmó
correctamente sus asserts (`PASSED` visible en el log antes del error),
durante el `flush` automático que `pytest-django` ejecuta entre tests
`django_db(transaction=True)` para resetear la BD. El error real
subyacente es
`psycopg.errors.FeatureNotSupported: cannot truncate a table referenced
in a foreign key constraint` — un conflicto entre el `TRUNCATE` genérico
de `pytest-django`/Django y las relaciones FK del modelo, específico al
patrón de esta prueba (threads reales con conexiones de BD
independientes, cada uno abriendo y cerrando su propia conexión — un
patrón nuevo en la suite, distinto del resto de tests `transaction=True`
existentes que operan en una sola conexión). Se investigó comparando
contra el único otro test `transaction=True` de la suite
(`test_idempotence_v2614.py::TestHTTPStatusCodesProveedores`, que NO usa
threads) — ese archivo corre limpio sin este error, confirmando que el
origen es el patrón de multi-conexión/multi-thread, no una condición
preexistente del harness. Dado que **la evidencia que realmente prueba
el fix (unicidad, secuencia,
ausencia de deadlock) ya quedó capturada antes de que el error de
teardown ocurra**, y que profundizar más en esto es arqueología de
infraestructura de testing (no una corrección del hallazgo P0-04 en sí),
se documenta como deuda de infraestructura de tests, no como bloqueante
de este hallazgo.

## Riesgos / deuda pendiente

Los threads de Python comparten el mismo proceso (GIL) — no es
concurrencia multi-proceso real (2 servidores Django distintos), pero sí
es concurrencia real de conexiones/transacciones de BD distintas, que es
exactamente lo que `select_for_update()` protege (contención a nivel de
fila de PostgreSQL, no a nivel de proceso Python). Esto cubre el
escenario real de la aplicación: múltiples requests HTTP concurrentes,
cada uno con su propia conexión de BD del pool.

**Deuda de infraestructura de tests (no de producto)**: el patrón
"threads reales + conexiones de BD independientes" bajo
`pytest.mark.django_db(transaction=True)` dispara un `FeatureNotSupported`
de Postgres durante el `flush` automático que corre `pytest-django`
entre tests (ver evidencia arriba) — no reproducido por ningún otro test
`transaction=True` existente en la suite porque ninguno usa threads
reales. No bloquea el resultado de este hallazgo (la evidencia de
corrección ya se capturó antes del teardown), pero sí es la razón por la
que este patrón de test no debería reutilizarse tal cual para otros
hallazgos de concurrencia sin antes resolver esto — candidato a una
tarea de infraestructura de testing dedicada, fuera del alcance de un
hallazgo P0 de producto.
