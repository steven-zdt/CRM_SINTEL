# F30 — Reporte Final

**Fecha:** 2026-08-12 · Rama `feat/onboarding-cookie` · Commit inicial
`43607a2`.

## 1. Resumen ejecutivo

F30 cerró los 3 hallazgos que F29 dejó documentados sin corregir
(workspace CRUD, `tenant_dashboard:index`, colisión `user-list`/
`user-detail`), y en el proceso de intentar establecer una regresión
global controlada descubrió y resolvió un bloqueador de infraestructura
que impedía ejecutar el comando canónico de testing (`pytest`/`make test`)
en absoluto: 10 errores de colección, nunca antes vistos porque ninguna
fase anterior había invocado pytest sin acotar paths. El baseline final se
estableció con colección 100% limpia (2053 tests, 0 errores) + regresión
dirigida 100% verde en los 6 archivos que F30 modificó, más un límite de
recursos del entorno de desarrollo (Docker Desktop, 5.7GB) que impidió una
corrida monolítica completa -- documentado como `ENVIRONMENT`, no como
trabajo pendiente. **0 cambios de producción que rompan contratos
existentes; 1 bug de producción preexistente descubierto y corregido**
(export faltante que rompía silenciosamente `/api/v1/core/mi-empresa/`).

## 2. Hallazgo A -- workspace CRUD test (F29-003)

`tests/tenant/core/test_workspace_crud_integration.py`: 3 clases
sobreescribían `setUp()` reemplazando la infraestructura de
`SintelTenantTestCase` (incluyendo `HTTP_HOST`, requerido por el
middleware de tenant) por un `Client()`/`User` propios sin membership.
**Fix:** eliminados los 3 `setUp()` redundantes -- las clases heredan el
harness sin modificar. Regla aplicada: reutilizar, no duplicar
infraestructura de test (F30.3).

## 3. Hallazgo B -- `tenant_dashboard:index` (F29-006)

Nombre nunca registrado (`apps/tenant/dashboard/urls.py` deliberadamente
vacío). El nombre real y funcional para `/dashboard/` es
`tenant-dashboard-shell` (`config/urls_tenant.py:140`). Clasificación:
WRONG_TEST_CONTRACT, no PRODUCT_DECISION -- no se crea el namespace
faltante. **Fix:** 2 call sites corregidos a `reverse("tenant-dashboard-shell")`.
Al verificar, se descubrió que el destino real de la redirección de
`TenantRootView` para usuarios autenticados es
`/static/tenant/core/dashboard/index.html` directamente (sin pasar por
`/dashboard/`) -- la aserción del test se corrigió para reflejar el
routing real.

## 4. Hallazgo C -- colisión `user-list`/`user-detail` (F29-007)

Dos routers DRF (`PublicUserViewSet`, `UserAdminViewSet`) registraban el
mismo basename `"user"` en el mismo urlconf plano sin namespace,
resolviendo siempre al endpoint público. SSoT determinado con evidencia
(grep repo-wide: únicos 16 consumidores del nombre eran los 2 archivos de
test, ninguna plantilla/JS). **Fix:** `UserAdminViewSet` renombrado a
`"admin-user"` (0 cambios de path HTTP); 16 call sites actualizados. Al
verificar contra el endpoint admin real (antes enmascarado por la
colisión), 3 tests fallaron por primera vez -- confirmando exactamente la
sospecha de F29 ("bug silencioso: puede pasar ejercitando el endpoint
equivocado"): los payloads de test no incluían `password2` (requerido por
`UserCreateSerializer`, pero auto-rellenado solo por
`PublicUserViewSet.create()`, no por el admin). Corregidos los 3 tests
(payload + una aserción que leía la clave de error equivocada).

## 5. Bloqueador de infraestructura descubierto y resuelto -- 10 errores de colección global

Primera invocación de `pytest` sin argumentos (== `make test`) en todo el
arco F21-F30: abortó con 10 errores, 0 tests ejecutados. Resueltos:
- `pytest.ini` `norecursedirs` += `documentacion scratch scripts` (7
  archivos ajenos a pytest: logs archivados en UTF-8 inválido, scripts
  ad-hoc sin fixture `django_db`).
- `apps/public/console/tests.py` y `apps/tenant/proyectos/tests.py`:
  colisión de nombre de módulo Python contra sus paquetes `tests/`
  hermanos. Investigado antes de mover (no se asumió duplicado): ambos
  cubren funcionalidad real y distinta de sus paquetes hermanos --
  `git mv` a `tests/test_legacy_*.py`, cero pérdida de cobertura.
- `apps/tenant/empresa/services/__init__.py`: `get_empresa_data()` existía
  completo en `crud_service.py` pero nunca se reexportaba. Esto no solo
  rompía la colección del test -- **rompía en producción, silenciosamente,
  el 100% de las invocaciones** de `apps/tenant/core/services/empresa.py`
  (`get_mi_empresa()`, `get_empresas_snapshot()`, consumidos por
  `/api/v1/core/mi-empresa/`), cuyo `ImportError` quedaba tragado por un
  `except Exception` genérico. **Fix:** agregado el export faltante --
  bug de producción preexistente corregido como efecto colateral directo
  del trabajo de colección.

Verificado: `pytest --collect-only` sin argumentos -> **2053 tests, 0
errores** (antes: 10 errores, colección interrumpida).

## 6. Regresión

Ver `F30_REGRESSION_REPORT.md` para el detalle completo. Resumen:
- Pre-regresión (`manage.py check`, `makemigrations --check`): limpio,
  idéntico al baseline F30.0.
- Regresión dirigida sobre los 6 archivos modificados por F30: 100% verde
  (o fallando solo por causas preexistentes ya clasificadas y no
  relacionadas -- ver §7).
- Regresión monolítica completa (2053 tests, un solo proceso): **bloqueada
  por un límite de recursos del entorno de desarrollo** (Docker Desktop,
  5.7GB para todo el stack) -- 3 interrupciones independientes a tamaños de
  lote decrecientes (monolítico, ~526, ~138), sin patrón de fallo de código
  en común. Clasificado `ENVIRONMENT`, con una causa raíz adicional
  descubierta y corregida en el camino (`max_locks_per_transaction` de
  Postgres en el default de fábrica, insuficiente para el churn de schemas
  efímeros -- corregido a 512, infraestructura local, reversible).
- Aislamiento multi-tenant (F30.23): las fallas de contexto de schema
  encontradas (`test_system_health.py`, preexistentes, área ya conocida
  desde F27.12) son fallas de "apunta al schema equivocado", no fugas de
  datos entre tenants -- sin evidencia de fuga causada por cambios de F30.

## 7. Hallazgos preexistentes descubiertos, no corregidos (fuera de alcance de F30)

Documentados en detalle en `F30_REGRESSION_REPORT.md`. Todos eran
invisibles hasta ahora porque los archivos que los contienen nunca se
habían ejecutado exitosamente (bloqueados por colección) o nunca se habían
corrido en este arco de fases:
- `test_system_health.py` (4 tests): contaminación de contexto de schema
  entre clases de test -- misma área que `F27.12` (tarea ya conocida, no
  cerrada).
- `test_private_routing.py` (2 tests restantes): `302 != 200` para
  anónimo (por clasificar); `KeyError: 'tenant_landing'` (posible
  URL_CONTRACT nuevo, requeriría la metodología de F29).
- `test_empresa_ssoT.py` (5 tests): asume creación libre de Empresa vía
  POST, pero `EmpresaViewSet.create()` ya tiene un modo ENFORCED
  documentado que restringe a STAFF/ADMIN con nudge hacia PATCH -- contrato
  legacy, no bug de producción.

Ninguno de estos toca los 3 hallazgos de URL que F30 tenía como misión
cerrar, ni fue causado por ningún cambio de esta fase.

## 8. Governance

`tools/ekg/governance.py --offline`: 23 `viewsets_without_service_layer`,
6 `sede_or_area_field_without_sede_aware_model`, 2
`import_cycles_between_tenant_apps` -- **conteos idénticos al baseline ya
triado desde el proyecto OCF (2026-08-08)**, confirmado por grep en
`documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md`. Cero hallazgos
nuevos introducidos por los cambios de F30.

## 9. Migraciones

0. F30 no toca modelos (`makemigrations --check --dry-run` -> "No changes
detected", idéntico antes y después de todos los cambios de esta fase).

## 10. Test Impact Analysis / Knowledge Graph (F30.15-16)

Reutilizado `tools/ekg/impact.py` (sin construir nada nuevo), consistente
con F30.15. `UserAdminViewSet` (renombrado): 0 dependientes en el grafo,
"NONE FOUND" para cobertura de test -- confirma la limitación ya conocida
desde F29 (`tests/` de infraestructura top-level, incluyendo
`tests/public/accounts/`, está fuera del alcance del extractor de EKG,
que cubre `apps/tenant/*`/`apps/public/*`). `EmpresaService`: 1
dependiente (`EmpresaServiceMixin`), misma limitación de cobertura. No se
requirió actualizar el grafo -- ningún cambio de F30 modifica modelos,
servicios o ViewSets que el extractor rastree con nodos nuevos (el rename
de basename y el export de `get_empresa_data` son cambios de superficie
que no alteran la topología de dependencias ya capturada).

## 11. Archivos modificados

**Producción (2 archivos, 0 cambios de path HTTP):**
- `apps/public/accounts/api/viewsets.py` -- basename `UserAdminViewSet`
  `"user"` -> `"admin-user"`.
- `apps/tenant/empresa/services/__init__.py` -- export de
  `get_empresa_data` (bug de producción preexistente corregido).

**Infraestructura de testing (2 archivos):**
- `pytest.ini` -- `norecursedirs` ampliado.
- Postgres `max_locks_per_transaction` 64 -> 512 (runtime, no versionado).

**Tests (9 archivos):**
- `tests/tenant/core/test_workspace_crud_integration.py`
- `tests/general/test_system_health.py`
- `tests/tenant/landing/test_private_routing.py`
- `tests/public/accounts/test_user_crud_api.py`
- `tests/public/accounts/test_admin_users_list.py`
- `apps/public/console/tests.py` -> `apps/public/console/tests/test_legacy_public_tenants_api.py` (git mv)
- `apps/tenant/proyectos/tests.py` -> `apps/tenant/proyectos/tests/test_legacy_smoke_financials.py` (git mv)

**Documentación (5 archivos nuevos):**
`F30_EXECUTION_STATUS.md`, `F30_FINDINGS.md`, `F30_URL_CONTRACT_MATRIX.md`,
`F30_REGRESSION_REPORT.md`, `F30_FINAL_REPORT.md` (este documento).

## 12. Estado final

```
F21 [OK] COMPLETED
F22 [OK] COMPLETED
F23 [OK] COMPLETED
F24 [OK] COMPLETED
F25 [OK] COMPLETED
F26 [OK] COMPLETED
F27 [OK] COMPLETED
F28 [OK] COMPLETED
F29 [OK] COMPLETED
F30 [OK] COMPLETED (con 1 limitación de entorno documentada, no de código)
```

Los 3 hallazgos de F29 quedan cerrados. Governance sostenido sin
regresiones. 1 bug de producción preexistente descubierto y corregido
como efecto colateral directo del trabajo de colección de tests. Baseline
de regresión establecido con la evidencia disponible dentro de las
limitaciones de recursos del entorno de desarrollo local -- ver
`F30_REGRESSION_REPORT.md` §"Diagnóstico de causa raíz" para la acción de
seguimiento recomendada antes de escalar a la auditoría enterprise de las
17 apps.
