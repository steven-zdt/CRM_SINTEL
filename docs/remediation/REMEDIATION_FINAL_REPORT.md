# REMEDIATION_FINAL_REPORT

Cierre de la ejecución de `REMEDIATION_MASTER_PLAN.md`. Ver
`REMEDIATION_EXECUTION_STATUS.md` para el detalle fila-por-fila; este
documento resume totales, clasificación por dominio, e incidentes
operativos relevantes para quien retome este trabajo.

**Fecha:** 2026-08-28
**Rama:** `feat/onboarding-cookie`

## Resumen ejecutivo

De los 26 hallazgos del `REMEDIATION_MASTER_PLAN.md` (4 P0, 5 P1, 4 P2,
11 P3 — incluyendo 2 correcciones a la auditoría original — y 2
EXTERNAL_DEPENDENCY):

- **VERIFIED (con test real pasando, o corrección puramente documental
  confirmada):** 13 — P0-01, P0-02, P0-03, P0-04 (los 4 P0 completos),
  P1-01, P1-02, P1-03, P1-04, P1-05 (los 5 P1 completos), P3-03, P3-04,
  P3-05, P3-08 (4 de 11 P3 que eran correcciones puntuales reales).
- **BLOCKED (EXTERNAL_DEPENDENCY):** 2 — EXT-01 (DIAN facturas), EXT-02
  (DSPNE nómina). Correctamente bloqueados, no se intentó cerrar con
  código inventado.
- **DEFERRED (decisión explícita, trabajo de nueva funcionalidad):** 5 —
  P3-01, P3-02, P3-06, P3-07 (frontend cross-cutting/nueva
  funcionalidad), y P2-01 (requiere decisión de negocio sobre
  segregación de funciones).
- **NO_ACTION_REQUIRED (hallazgo original incorrecto o ya resuelto):** 6 —
  P2-02, P2-03, P2-04, P3-09, P3-10, P3-11.

**Total: 13 VERIFIED + 2 BLOCKED + 5 DEFERRED + 6 NO_ACTION_REQUIRED = 26**
(4 P0 + 5 P1 + 4 P2 + 11 P3 + 2 EXT = 26 hallazgos del
`REMEDIATION_MASTER_PLAN.md`, todos con disposición final registrada en
`REMEDIATION_EXECUTION_STATUS.md`). **100% de los hallazgos P0 y P1 (9 de
9) están VERIFIED** — ningún P0/P1 quedó sin corregir o sin validar.

## Clasificación por dominio

| Dominio | Hallazgos | Resultado |
|---|---|---|
| Seguridad / integridad de datos | P0-01 (hard-delete sin guard) | VERIFIED |
| Contabilidad / cierre de período | P0-02, P1-05 | VERIFIED |
| Fiscalidad / retenciones | P0-03, P2-04 | VERIFIED / reclasificado (NO_ACTION_REQUIRED) |
| Transaccional / concurrencia | P0-04, P1-03 | VERIFIED |
| Procesos de negocio (estados) | P1-01 | VERIFIED |
| Controles internos | P1-02, P2-01 | VERIFIED / decisión de negocio pendiente (BUSINESS_DECISION_REQUIRED) |
| Conciliación bancaria | P1-03, P1-04 | VERIFIED |
| Datos / calidad | P3-03, P3-04, P3-05, P3-08 | VERIFIED |
| UX / frontend | P3-06, P3-07 | DEFERRED |
| Integraciones externas (DIAN/DSPNE) | EXT-01, EXT-02 | BLOCKED |
| Documentación de auditoría | P3-09, P3-10 | Corregido (documental) |

## Regla aplicada consistentemente

Ningún hallazgo se declaró `VERIFIED` solo porque el código fue
modificado. El criterio de cierre fue siempre: implementación +
validación con test real (nuevo o existente) + evidencia de la corrida
adjunta en el `REM-*.md` correspondiente. Los hallazgos que no admitían
una corrección de código responsable dentro del alcance mínimo (P2-01,
P3-01, P3-02, P3-06, P3-07) se documentaron como DEFERRED con el alcance
explícito para una sesión futura dedicada, en vez de forzar una
implementación apresurada — por instrucción explícita del plan ("Regla
de No Expansión").

## Incidente operativo: hang de pytest por resolución IPv6 de "localhost"

Durante la corrida del batch combinado P0-02/P0-03/P0-04/regresión de
retenciones, el proceso quedó colgado **42 minutos con 0.05s de CPU
consumido y 0 bytes de salida**, sin ninguna query activa en Postgres
(`pg_stat_activity` mostraba una única conexión idle). Diagnóstico:

1. `Get-Process` confirmó CPU casi nula sostenida — no es
   `TenantTestCase` overhead legítimo (que sí consume CPU real
   creando/migrando schemas), es un hang genuino.
2. `.env` define `DATABASE_HOST=localhost` y este proceso usa
   `REDIS_URL=redis://localhost:6379/0` (override estándar de esta
   sesión). En esta máquina, `localhost` resuelve primero a `::1`
   (IPv6), y `Test-NetConnection -ComputerName localhost -Port 6379`
   confirmó explícitamente el fallo IPv6 (`TCP connect to (::1:6379)
   failed`) antes de caer a IPv4. Docker Desktop en Windows expone los
   puertos mapeados solo sobre IPv4 — una conexión que insiste en `::1`
   nunca conecta y puede quedarse esperando indefinidamente en vez de
   fallar rápido.
3. **Corrección aplicada (solo para esta corrida, no es un cambio de
   código de producto):** forzar IPv4 explícito en las variables de
   entorno de la corrida local: `DATABASE_HOST=127.0.0.1` y
   `REDIS_URL=redis://127.0.0.1:6379/0`. Confirmado que con este cambio
   el mismo test progresa normalmente (conexión a Postgres visible en
   `pg_stat_activity`, uso de CPU real, salida de pytest fluyendo).

**Nota para sesiones futuras:** si una corrida de pytest local contra
Docker Desktop en Windows parece "colgada" sin avanzar, verificar
primero `Get-Process -Id <pid> | select CPU` — CPU cercana a cero
sostenida por varios minutos es la señal de este mismo problema de
resolución IPv6, no de overhead legítimo de `TenantTestCase`. La
corrección es forzar `127.0.0.1` en `DATABASE_HOST` y `REDIS_URL` para
la corrida local (no se tocó `.env` ni ninguna configuración de Docker —
es un override de entorno solo para el proceso de test).

## Fallas reales encontradas y corregidas durante la validación (paso G/I del ciclo)

El plan exige diagnóstico de causa raíz antes de tocar código cuando un
test falla, nunca ajustar el test a ciegas para que pase. 4 fallas
surgieron en las corridas de esta misión:

| Finding | Falla | Causa raíz | Corrección |
|---|---|---|---|
| P1-02 | Test asumía `settings.DEBUG=True` ambiental | El entorno de test real corre con `DEBUG=False` | Bug del test — se forzó `@override_settings(DEBUG=True)` para probar el escenario exacto de forma determinística |
| P1-04 | Test esperaba HTTP 400, código devolvía 422 | `SintelServiceMixin.handle_service_error()` mapea `ValidationError` de la capa de servicio a 422 (convención ya establecida, distinta de los 400 de `serializer.is_valid()`) | Bug del test — se corrigió la aserción a 422 |
| P1-05 | `pre_close_validation()` no detectaba un asiento deliberadamente descuadrado en el test | **Bug real de código**: la query filtraba `total_debe`/`total_haber` (campos legado que `AsientoContable.save()` sobreescribe automáticamente con `debe_total`/`haber_total` en cada guardado) en vez de los campos autoritativos | Corregido en `business_service.py` (query) y en el test (construcción del descuadre) |
| P3-04 | KPI devolvía `0` en vez del valor esperado | Bug del test — `setUp()` no creaba `TenantProfile` para el usuario, `ProductoTableView` no podía resolver la empresa y devolvía queryset vacío | Se agregó la creación de `TenantProfile` (mismo patrón ya usado en el resto de tests de la sesión) |

Las 4 fallas se re-verificaron con corrida real tras cada corrección — ver
el `REM-*.md` de cada finding para el detalle diagnóstico completo.

## Migraciones aplicadas

Las 3 migraciones nuevas de esta misión están **APLICADAS a los 3
tenants reales** (`home`, `qaisotest`, `shelltest1`) y verificadas
directamente contra `pg_constraint`/`information_schema` en cada schema
(no solo por el registro de `django_migrations`):

- `contabilidad/migrations/0017_retencion_uniq_retencion_documento_origen_tipo_activa.py`
  (0 filas afectadas, verificado antes de generar).
- `bancos/migrations/0006_extractobancario_uniq_extracto_bancario_empresa_cuenta_periodo.py`
  (0 dupes verificado antes de generar; constraint
  `uniq_extracto_bancario_empresa_cuenta_periodo` confirmado presente en
  los 3 schemas).
- `facturas/migrations/0040_alter_factura_consecutivo.py` (solo
  `help_text`, sin impacto de datos).

## Barrido de gobernanza final

Ejecutado 2026-08-28 (`docker compose exec web`, tras aplicar las 3
migraciones y con 0 pytest local activo):

- `manage.py check`: **PASS** — "System check identified no issues (0 silenced)".
- `manage.py makemigrations --check --dry-run` (global): **PASS** — "No changes detected".
- `git diff --check`: **PASS** — sin errores de whitespace ni marcadores de conflicto.

**FINAL STATUS: PASS** — sin hallazgos nuevos de gobernanza introducidos
por esta misión. Clasificación: 0 REGRESSION, 0 NEW (fuera de las
correcciones intencionales), todo lo modificado es FIXED según su
`REM-*.md` correspondiente.

## Estado final de la misión

**REMEDIATION = COMPLETED_WITH_DEFERRED**

Justificación: los 9 hallazgos P0 y P1 (100%) están VERIFIED — corregidos
en código, con tests dirigidos, y con corrida real pasando (ver
`REMEDIATION_EXECUTION_STATUS.md` para la evidencia exacta por fila). Los
P2/P3 se resolvieron con la disciplina de "no expandir el alcance": los
que eran correcciones puntuales se
implementaron y verificaron; los que eran trabajo de nueva
funcionalidad o requerían decisión de negocio se documentaron como
DEFERRED/BUSINESS_DECISION_REQUIRED con alcance explícito, nunca
forzados. Los 2 EXTERNAL_DEPENDENCY quedan correctamente BLOCKED sin
código inventado. No se declara `COMPLETED` puro porque quedan ítems
DEFERRED y BLOCKED por diseño — exactamente la distinción que exige el
plan.
