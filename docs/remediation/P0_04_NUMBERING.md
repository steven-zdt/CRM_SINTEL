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

**Hallazgo operativo -- RESUELTO (actualizado tras diagnóstico de causa
raíz)**: la pasada anterior reportó *"2 passed, 2 errors"* y atribuyó los
`ERROR` (durante el `flush` automático de `pytest-django` entre tests
`django_db(transaction=True)`) al patrón de threads/conexiones reales de
este test, por comparación con
`test_idempotence_v2614.py::TestHTTPStatusCodesProveedores` (que no usa
threads y "corría limpio"). Esa comparación fue insuficiente: se investigó
más a fondo consultando `pg_constraint` directamente contra la BD de test
y ejecutando `sql_flush()` de Django manualmente, y la causa raíz **no
tiene relación con threads**:

`TenantProfile.user` (`apps/tenant/perfil/models.py`) es un FK real de
Postgres, intencional y documentado, de `<schema_tenant>.perfil_tenantprofile`
hacia `public.accounts_user` -- una FK que cruza schemas. En cuanto
`migrate_schemas` crea (con COMMIT real, requisito de `transaction=True`)
un schema de tenant nuevo, esa tabla y esa FK quedan creadas junto con él,
sin que el test necesite usar `TenantProfile` en absoluto. El `flush` que
`pytest-django` corre después de cada test `transaction=True`
(`allow_cascade=False`) intenta `TRUNCATE` de `public.accounts_user`, pero
la introspección de `django-tenants` (`DatabaseSchemaIntrospection`) está
acotada al schema `public` -- nunca puede ver ni incluir en el mismo
`TRUNCATE` la tabla referenciante que vive en el schema del tenant.
Postgres rechaza correctamente ese `TRUNCATE` parcial con
`FeatureNotSupported: cannot truncate a table referenced in a foreign key
constraint`. Esto ocurre para **cualquier** test `transaction=True` cuyo
schema de tenant ya tenga `perfil_tenantprofile` migrado -- el archivo de
referencia sin threads no es inmune al problema por estructura, solo no
se había verificado en aislamiento con el mismo rigor.

**Corrección aplicada**: se agregó un fixture `autouse=True` en
`test_remediation_p0_04_concurrencia_real.py`
(`_drop_cross_schema_fk_before_flush`) que, tras cada test y antes de que
corra el `flush` automático de `pytest-django` (ordenado explícitamente
como dependencia de `db`, para que su teardown se ejecute primero por
LIFO), suelta cualquier FK del schema del tenant hacia `public` --
verificado con `pg_constraint` -- ya que este test nunca usa
`TenantProfile` y el schema es desechable. Confirmado localmente:
`test_remediation_p0_04_concurrencia_real.py` corre "2 passed" sin
errores de teardown.

**Nota operativa -- `DATABASE_HOST` local en Windows**: durante el
diagnóstico se reprodujo, de forma separada al problema del `flush`, un
cuelgue real de ~130s en las conexiones nuevas que abre cada thread
cuando `DATABASE_HOST=localhost` (valor por defecto de `.env` en este
checkout). Con `DATABASE_HOST=127.0.0.1` el mismo test corre en <10s sin
cuelgues -- consistente con que la evidencia original de esta misión ya
se había capturado explícitamente con `DATABASE_HOST=127.0.0.1` (ver
sección "Evidencia" arriba). No es un bug de la corrección ni del test:
es resolución de `localhost` lenta en este entorno Windows para
conexiones nuevas por thread. Para correr este archivo localmente fuera
de Docker, usar `DATABASE_HOST=127.0.0.1`.

## Riesgos / deuda pendiente

Los threads de Python comparten el mismo proceso (GIL) — no es
concurrencia multi-proceso real (2 servidores Django distintos), pero sí
es concurrencia real de conexiones/transacciones de BD distintas, que es
exactamente lo que `select_for_update()` protege (contención a nivel de
fila de PostgreSQL, no a nivel de proceso Python). Esto cubre el
escenario real de la aplicación: múltiples requests HTTP concurrentes,
cada uno con su propia conexión de BD del pool.

**Deuda de infraestructura de tests (resuelta para este archivo, pendiente
en general)**: cualquier test `pytest.mark.django_db(transaction=True)`
que haga que `migrate_schemas` cree un schema de tenant real (COMMIT, no
rollback) con `perfil_tenantprofile` migrado disparará el mismo
`FeatureNotSupported` en su propio `flush` de teardown, tenga threads o
no. El fixture agregado aquí resuelve el caso puntual de este archivo;
otros tests `transaction=True` que creen tenants nuevos (y no ya lo
resuelvan de otra forma) podrían necesitar el mismo patrón. Candidato a
una solución de infraestructura de testing más general (p. ej. usar
`django_tenants.test.runner.TenantTestRunner` o un fixture compartido en
`conftest.py`), fuera del alcance de este hallazgo P0 de producto.
