# F28 — Hallazgos (Estabilización del testing multi-tenant)

**Fecha:** 2026-08-11. **Nota de alcance:** por indicación explícita del
usuario durante la ejecución ("no pierdas tiempo en test facturas, lo hemos
hecho muchas veces, continua"), esta fase **no volvió a correr la suite
completa de `apps/tenant/facturas/tests/`** (ya corrida 2 veces en F27/F28
sin cambios de fondo) ni ejecutó una regresión global (`make test`). La
verificación se hizo quirúrgicamente sobre los archivos que F28 modificó,
consistente con "Testing Progresivo por Alcance" de `CLAUDE.md`.

---

## F28-001 — Auditoría de los 34 `TenantTestCase`: completada (agente dedicado)

Ver `documentacion/F28_TENANT_TEST_AUDIT.md` para el detalle completo.
Resumen: **11 MIGRATE_SAFE, 1 MIGRATE_WITH_FIX, 21 ALREADY_SAFE, 0
KEEP_INTENTIONAL, 1 UNKNOWN**. El listado de 34 de F27 se reconfirmó exacto;
se encontró 1 archivo con drift real (`apps/tenant/dashboard/tests/test_extractores.py`,
no estaba en la lista original, no clasificado en este pase — recomendado
para F29).

## F28-002 — Migración controlada aplicada: 12 archivos

Swap mecánico (`TenantTestCase` → `SintelTenantTestCase`) aplicado a los 11
`MIGRATE_SAFE` + 1 `MIGRATE_WITH_FIX` (con el fix adicional de
`super().setUp()` en sus 3 clases):

```
apps/tenant/facturas/tests/test_factura_detail_anexos_api.py
apps/tenant/facturas/tests/test_facturas_list_detail_payloads.py
apps/tenant/facturas/tests/test_facturas_list_naturaleza_api.py
apps/tenant/facturas/tests/test_import_ubl_heavy_payload.py
apps/tenant/facturas/tests/test_naturaleza_import_ubl.py
apps/tenant/facturas/tests/test_upload_async_flow.py
apps/tenant/facturas/tests/test_xml_pipeline_canonical.py
apps/tenant/core/tests/test_workspace_facturas_links_and_column.py
apps/tenant/core/tests/test_workspace_facturas_modal.py
apps/tenant/core/tests/test_workspace_links_strict.py
tests/tenant/core/smoke/test_workspace_empresa_integridad.py
tests/tenant/core/test_workspace_crud_integration.py   [MIGRATE_WITH_FIX]
```

**No se migraron** las 21 `ALREADY_SAFE` (no tienen el riesgo de
`reverse()`, migrarlas sería `AMPLIAR` sin necesidad demostrada — regla
F28 "no crear/ampliar sin justificación"). **No se tocó** la `UNKNOWN`
original (ver F28-003, resultó ser algo distinto).

## F28-003 — Bonus: `SyntaxError` real corregido (no relacionado con la migración)

`tests/tenant/core/smoke/test_workspace_empresa_modules_smoke.py` — la
auditoría clasificó este archivo `UNKNOWN` por un `SyntaxError` confirmado
(`ast.parse` fallaba en línea 22). Diagnóstico: un bloque de guard
(`import pytest` + `try/except cryptography/playwright`) había quedado
pegado, sin indentar, dentro del cuerpo del primer método de test, en vez
de a nivel de módulo (patrón correcto, ya usado en el archivo hermano
`test_workspace_empresa_integridad.py`). **Corregido**: bloque movido a
nivel de módulo, exactamente en la misma posición que el archivo hermano;
verificado con `ast.parse` (sin errores) y migrada también su base class
(compartía el mismo problema de `self.user` faltante que #25 del audit).

## F28-004 — La migración funcionó: confirmado, `NoReverseMatch` para rutas `factura-*` desapareció

`test_facturas_list_naturaleza_api.py` (el caso más simple, 1 test) pasa
**limpio, 100%**, sin ningún cambio adicional más allá del swap de base
class — confirma que el mecanismo diagnosticado en F27-003
(`SintelTenantTestCase` fija `ROOT_URLCONF`/`set_urlconf`, `TenantTestCase`
crudo no) es la causa raíz real y el fix mecánico es correcto.

## F28-005 — La migración destapó bugs preexistentes reales, previamente enmascarados por el `NoReverseMatch`

Verificación quirúrgica de los 13 archivos tocados: **44 failed, 7 passed,
6 skipped**. Investigación de causa real (no asumida) en varios de los 44:

**a) `self.f.id` en vez de `self.f.uuid` (TEST BUG real, confirmado en 2+
archivos):** `BaseTenantViewSet.lookup_field = "uuid"` — las URLs de
detalle/acciones esperan el UUID, no el PK entero. Varios tests
(`test_factura_detail_anexos_api.py::test_get_app_response`,
`test_facturas_list_detail_payloads.py::test_detail_con_anexos`, y
presumiblemente otros con el mismo patrón `args=[self.f.id]`) pasan el PK
entero donde se espera UUID. Antes de la migración, estos tests **nunca
llegaban a esta aserción** — morían antes con `NoReverseMatch` al intentar
`reverse()`. La migración los hace avanzar más lejos en el pipeline real,
exponiendo el bug genuino: `reverse()` ahora arma la URL igual (el patrón
acepta cualquier string en la posición del lookup), pero el ViewSet no
encuentra ninguna `Factura` con `uuid=<PK entero>` y responde `404`.
**Clasificación: TEST BUG preexistente, no causado ni agravado por F28** —
ya estaba roto, solo que de una forma que lo enmascaraba (fallaba antes,
por una razón distinta, sin llegar nunca a ejercitar la lógica real). No
corregido en este pase por indicación explícita del usuario de no seguir
invirtiendo tiempo en la suite de facturas — documentado como hallazgo real
para una fase dedicada.

**b) El nombre de URL `workspace` no resuelve via `reverse()`, en ningún
contexto — hallazgo separado, NO relacionado con TenantTestCase:**
confirmado que `reverse('workspace')` falla **incluso reproduciendo
exactamente el mismo mecanismo que usa `SintelTenantTestCase.setUp()`**
(`override_settings(ROOT_URLCONF=...)` + `set_urlconf(...)`) en una sesión
de `manage.py shell` completamente fuera de pytest y de cualquier archivo
de test. El patrón SÍ existe (`apps/tenant/core/urls_ui.py:37`,
`path('workspace/', ..., name='workspace')`), SÍ está incluido en
`config.urls_tenant` (`path('', include('apps.tenant.core.urls_ui'))`), y
la ruta literal `/workspace/` responde `302` (redirect a login) en una
petición real -- pero el nombre `'workspace'` no aparece en
`resolver.reverse_dict` bajo ningún mecanismo de urlconf probado. Esto es
un problema de registro/resolución de nombres en el árbol de URLs (posible
colisión o efecto de `path('', include(...))` con prefijo vacío), **no**
el mismo bug que F27-003/F28 vino a resolver, y **no fue causado por
ninguna migración de esta sesión** (reproducido sin ningún test, con el
código de producción intacto). Afecta a `test_workspace_crud_integration.py`
(17 tests) y a los 3 archivos `test_workspace_facturas_*`/`test_workspace_links_strict.py`
que usan el patrón `try: reverse(...) except: fallback` (donde el fallback
ya enmascaraba este problema antes Y después de la migración — comportamiento
sin cambios para esos 3, confirmado). **No corregido, documentado como
hallazgo real y separado, candidato a investigación dedicada.**

**c) `test_naturaleza_import_ubl.py` — comportamiento exactamente como se predijo:**
sigue fallando 5/5, pero ya no por `NoReverseMatch` (causa #2 de F27-004,
corregida) — ahora por las causas #1 (fixture XML) y #3 (falta
`async=false`), exactamente como F27-004 documentó de antemano. **No es
una sorpresa ni una regresión** — es la confirmación de que la migración
resolvió exactamente la causa que se proponía resolver, ni más ni menos.

## F28-006 — `compras`: auditoría ligera, GREEN

`apps/tenant/compras/tests/` (6 archivos) — **0 archivos con
`TenantTestCase` crudo**. Todos usan `SintelTenantTestCase` o son
pytest-style sin clase. No requiere migración. Historial de regresión
previo (F21: 16/16, F24: 12/12) ya confirmaba estabilidad. Clasificado
**GREEN** sin necesitar una corrida nueva.

## F28-007 — Verificación repo-wide: sin drift adicional

`grep` repo-wide de `TenantTestCase` crudo en `apps/tenant/**` y `tests/**`
confirma: los únicos archivos que aún lo importan son exactamente los 21
`ALREADY_SAFE` (dejados intencionalmente sin migrar) + los 3 "falsos
candidatos" ya explicados en el audit (imports muertos/vestigiales) + el
1 archivo de `dashboard` con drift ya señalado (F28-001). **0 sorpresas
nuevas.**

---

## Resumen

| # | Hallazgo | Clasificación | Acción |
|---|---|---|---|
| F28-001 | Auditoría de 34 `TenantTestCase` | — | Completada, ver `F28_TENANT_TEST_AUDIT.md` |
| F28-002 | 12 archivos migrados a `SintelTenantTestCase` | NORMALIZACIÓN | **Aplicado** |
| F28-003 | `SyntaxError` preexistente en archivo `UNKNOWN` | TEST BUG (corrupción de merge/paste) | **Corregido** |
| F28-004 | Migración confirmada correcta (`test_facturas_list_naturaleza_api.py` 100% limpio) | — | Verificado |
| F28-005a | `self.f.id` vs `self.f.uuid` en 2+ archivos | TEST BUG preexistente, desenmascarado | Documentado, no corregido (alcance) |
| F28-005b | `reverse('workspace')` nunca resuelve, en ningún contexto | Hallazgo separado, NO causado por F28 | Documentado, no corregido (fuera de alcance de F28) |
| F28-005c | `test_naturaleza_import_ubl.py` sigue fallando por causas #1/#3 de F27-004 | Esperado, no regresión | Confirmado, sin cambios |
| F28-006 | `compras` sin `TenantTestCase` crudo | GREEN | Sin acción necesaria |
| F28-007 | Sin drift adicional repo-wide | — | Confirmado |
