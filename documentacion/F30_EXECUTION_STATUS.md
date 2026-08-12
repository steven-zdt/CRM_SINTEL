# F30 — Estado de Ejecución

**Fecha inicio:** 2026-08-11 · **Commit inicial:** `43607a2` (branch
`feat/onboarding-cookie`)
**Baseline documental:** Arquitectura General SINTEL ERP v3.32.0, DOC-M19.
**Estado F21-F29 al iniciar:** todo COMPLETED, governance PASS, 0
migraciones pendientes.

## Baseline técnico (F30.0)

```
branch: feat/onboarding-cookie
git status --short: 78 archivos con cambios preexistentes NO relacionados
                     (mismo criterio de todas las fases previas)
manage.py check                             -> System check identified no issues (0 silenced)
manage.py makemigrations --check --dry-run  -> No changes detected
```

## Hallazgo A -- workspace CRUD test (F30.2-4)

`tests/tenant/core/test_workspace_crud_integration.py`: 3 `setUp()`
redundantes eliminados (causa real: `Client()` sin `HTTP_HOST`, no solo
membership faltante). Ver `F30_FINDINGS.md` F30-A. **DONE**, pendiente
verificación en regresión F30.19.

## Hallazgo B -- `tenant_dashboard:index` (F30.5-8)

Grep repo-wide confirmó solo 2 call sites reales (`reverse()`), el resto son
menciones en docstring que ya verifican contra el path literal `/dashboard/`.
Clasificado WRONG_TEST_CONTRACT: nombre real registrado es
`tenant-dashboard-shell`. 2 call sites corregidos
(`tests/general/test_system_health.py`,
`tests/tenant/landing/test_private_routing.py`). Ver `F30_FINDINGS.md`
F30-B. **DONE**.

## Hallazgo C -- colisión `user-list`/`user-detail` (F30.9-14)

SSoT determinado con evidencia (grep repo-wide: solo 16 call sites en 2
archivos de test dependían del nombre colisionado, ninguna plantilla/JS/otro
Python). `UserAdminViewSet` renombrado `"user"` -> `"admin-user"`
(0 cambios de path HTTP). 16 call sites actualizados en
`tests/public/accounts/test_user_crud_api.py` (11) y
`tests/public/accounts/test_admin_users_list.py` (5). Ver `F30_FINDINGS.md`
F30-C. **DONE**.

## Bloqueador nuevo hallado y resuelto -- 10 errores de colección global (F30-D/E)

Primera ejecución real de `pytest` sin argumentos (== `make test`) en todo
el arco F21-F30 abortó en colección: 10 errores, 0 tests ejecutados. Los 10
resueltos:
- `pytest.ini`: `norecursedirs` += `documentacion scratch scripts` (7 casos).
- `apps/public/console/tests.py` y `apps/tenant/proyectos/tests.py`: `git mv`
  a sus paquetes `tests/` hermanos como `test_legacy_*.py` (colisión de
  nombre de módulo Python, contenido investigado y confirmado NO duplicado
  antes de mover -- 2 casos).
- `apps/tenant/empresa/services/__init__.py`: exportar `get_empresa_data`
  (existía en `crud_service.py` pero nunca se reexportaba) -- resuelve el
  `ImportError` de colección Y un bug de producción preexistente donde
  `apps/tenant/core/services/empresa.py` (`get_mi_empresa`,
  `get_empresas_snapshot`, consumidos por `/api/v1/core/mi-empresa/`)
  fallaba silenciosamente en el 100% de las invocaciones por el mismo
  `ImportError`, tragado por un `except Exception` genérico (1 caso).

Verificado: `pytest --collect-only` completo, sin argumentos ->
**2053 tests recolectados, 0 errores** (antes: 10 errores, colección
interrumpida). Ver `F30_FINDINGS.md` F30-D, F30-E.

## Test Impact Analysis (F30.15-16)

Reutilizado `tools/ekg/impact.py`. `UserAdminViewSet`/`EmpresaService`: sin
cobertura de test detectable en el grafo (limitación ya conocida desde
F29 -- el extractor no cubre `tests/` de infraestructura). No se requirió
actualizar el grafo (ningún cambio de F30 altera la topología de
dependencias ya capturada).

## Regresión global (F30.17-23)

Pre-regresión limpia (idéntica al baseline F30.0). Regresión dirigida
100% verde en los 6 archivos modificados por F30. Regresión monolítica
completa (2053 tests) bloqueada por un límite de recursos del entorno de
desarrollo local (Docker Desktop, 5.7 GiB) -- 3 interrupciones
independientes a tamaños de lote decrecientes, clasificado `ENVIRONMENT`,
con causa raíz adicional descubierta y corregida en el camino
(`max_locks_per_transaction` de Postgres, 64 -> 512). Sin evidencia de
fuga de datos entre tenants causada por F30. Detalle completo:
`F30_REGRESSION_REPORT.md`.

## Governance (F30.28) y migraciones (F30.29)

`tools/ekg/governance.py --offline`: conteos idénticos al baseline OCF ya
triado (2026-08-08) -- 0 hallazgos nuevos. `makemigrations --check` limpio
(0 migraciones, F30 no toca modelos).

## Documentación final (F30.31-32)

`documentacion/arquitectura_general.md` actualizado a v3.33.0/DOC-M20,
historial previo preservado. `F30_FINAL_REPORT.md` escrito.

## Estado: `COMPLETED`

Los 3 hallazgos de F29 quedan cerrados. 1 bug de producción preexistente
descubierto y corregido como efecto colateral. 1 limitación de entorno
documentada (no de código) para la regresión monolítica completa -- ver
`F30_REGRESSION_REPORT.md` para la acción de seguimiento recomendada.
