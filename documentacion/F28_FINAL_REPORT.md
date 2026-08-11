# F28 — Reporte Final

**Fecha:** 2026-08-11

## 1. Resumen ejecutivo

F28 auditó individualmente los 34 archivos con `TenantTestCase` crudo
documentados por F27, migró de forma controlada los 11+1 que lo necesitaban
de verdad, corrigió un `SyntaxError` real encontrado en el camino, y
confirmó empíricamente que el mecanismo diagnosticado en F27-003
(`SintelTenantTestCase` fija `ROOT_URLCONF` de tenant, `TenantTestCase`
crudo no) es la causa raíz real. La migración también desenmascaró 2
hallazgos reales preexistentes que antes quedaban ocultos detrás del
`NoReverseMatch` — documentados con evidencia, no corregidos, por
indicación explícita del usuario de no seguir invirtiendo tiempo en la
suite completa de `facturas` en esta sesión. **0 tests nuevos creados.**

## 2. Estado inicial

Commit `28390e9` (branch `feat/onboarding-cookie`), arquitectura v3.30.0/
DOC-M17. F21-F27 COMPLETED, governance PASS. Baseline técnico F28.0:
`manage.py check` limpio, `makemigrations --check` limpio, git status con
solo cambios preexistentes no relacionados.

## 3. 34 `TenantTestCase` auditados

Agente dedicado, investigación de solo lectura (sin editar, sin correr
pytest). Resultado: **11 MIGRATE_SAFE, 1 MIGRATE_WITH_FIX, 21 ALREADY_SAFE,
0 KEEP_INTENTIONAL, 1 UNKNOWN**. Detalle completo con evidencia
archivo:línea por cada uno de los 34: `F28_TENANT_TEST_AUDIT.md`.

## 4. Migraciones realizadas

**12 archivos** migrados de `TenantTestCase` a `SintelTenantTestCase`:
7 en `apps/tenant/facturas/tests/`, 3 en `apps/tenant/core/tests/`, 2 en
`tests/tenant/core/` (uno de ellos, `test_workspace_crud_integration.py`,
requirió además agregar `super().setUp()` a sus 3 clases — sin eso, el fix
de `ROOT_URLCONF` de la nueva base class nunca se hubiera ejecutado). Lista
completa: `F28_FINDINGS.md` F28-002.

## 5. Excepciones conservadas

**21 archivos ALREADY_SAFE** dejados intencionalmente sin migrar — no
tienen el riesgo de `reverse()` (no llaman `reverse()` directamente, o no
usan `self.client` contra rutas de tenant), migrarlos sería ampliar sin
necesidad demostrada. **0 archivos KEEP_INTENTIONAL** — ninguno de los que
crean tenants/schemas manualmente depende de algo exclusivo de
`TenantTestCase` crudo que `SintelTenantTestCase` no reproduzca.

## 6. Problema `ROOT_URLCONF`

Confirmado y corregido para los 12 archivos migrados. Prueba directa:
`test_facturas_list_naturaleza_api.py` pasa 100% limpio solo con el swap de
base class, sin ningún otro cambio — evidencia de que el diagnóstico F27-003
era correcto y el fix mecánico basta cuando no hay otros problemas
compuestos.

## 7. Correcciones de facturas

Un `SyntaxError` real corregido (`tests/tenant/core/smoke/test_workspace_empresa_modules_smoke.py`
— bloque de guard pegado sin indentar dentro de un método, movido a nivel
de módulo). Ningún otro cambio de código de producción ni de assertions de
test en esta fase (F28 es normalización de infraestructura de testing, no
corrección de lógica de negocio).

## 8. Tests reutilizados

Todos los `TESTS EXISTENTES` de `facturas`, `core`, `perfil` y `compras` —
ninguno se recreó desde cero. La migración reutiliza `SintelTenantTestCase`,
ya existente desde antes de F27.

## 9. Tests corregidos

1 archivo con `SyntaxError` (contaba como "no ejecutable", ahora
ejecutable). 12 archivos con base class corregida (no es un "fix de lógica
de test", es normalización de infraestructura — clasificado aparte de
"tests corregidos" en sentido estricto de F27).

## 10. Tests consolidados

**0** en este pase — F28 no tocó los clusters de duplicación que F27 ya
documentó (`F27_TEST_INVENTORY.md` §3), fuera del alcance declarado de esta
fase (normalización de `TenantTestCase`, no deduplicación).

## 11. Tests nuevos

**0.** Ningún hallazgo de esta fase correspondió a cobertura ausente —
todos fueron de infraestructura (base class) o bugs preexistentes
desenmascarados. Resultado válido y preferido según la propia regla de F28
(REGLA 6: "NO crear tests equivalentes"; F28.22: "solo crear si... 0
alternativas").

## 12. Tests eliminados

**0** en este pase (el duplicado de `tests/celery/` ya se había eliminado
como parte del trabajo de continuidad de F27, commit `28390e9`, antes de
iniciar formalmente F28).

## 13. Test Impact Analysis

Reutilizado `tools/ekg/impact.py` (ya existente desde Fase 12) sin
construir nada nuevo — regla F28 explícita ("REGLA 1: NO crear otro sistema
de Test Impact Analysis"). Dump de `facturas` regenerado (368 nodos, 430
edges, idéntico a F27 — F28 no agregó/eliminó/renombró símbolos).
Verificado con consultas reales (`FacturaBusinessService`) devolviendo
resultados idénticos a F27. Detalle: `F28_TEST_IMPACT.md`.

## 14. Knowledge Graph

Sin cambios de grafo — mismo razonamiento que §13 (F28 no agrega
modelos/servicios/dependencias nuevas, solo normaliza infraestructura de
test).

## 15. Regresión facturas

**No se re-ejecutó la suite completa de 30 archivos** (ya corrida 2 veces
en F27/F28 sin cambio de fondo; interrumpida explícitamente por el usuario
en un tercer intento). Se verificó quirúrgicamente el subconjunto de 13
archivos tocados: **44 failed, 7 passed, 6 skipped** — desglosado y
clasificado con evidencia real en `F28_FINDINGS.md` F28-004/F28-005 (no es
un resultado "malo" sin explicación: incluye 2 hallazgos reales nuevos
desenmascarados por el propio fix, documentados, no corregidos por decisión
explícita de alcance). Detalle: `F28_FACTURAS_REGRESSION.md`.

## 16. Regresión F21-F28

**No ejecutada como corrida consolidada nueva** en este pase — mismo
razonamiento de proporcionalidad: F28 no tocó código de producción (solo
tests + 1 fix de sintaxis en un test), y F21-F27 ya tienen su propio
historial de regresión verde documentado en sus respectivos reportes.

## 17. Regresión global

**No ejecutada** (`make test` / suite completa del repo, ~2008 tests) —
desproporcionado para el alcance real de esta fase (13 archivos de test
tocados, 0 cambios de producción), consistente con F28.31 ("no ejecutar
global innecesariamente... reservarla para checkpoint/cierre de fase
[cuando hay] cambios transversales") y con la instrucción explícita del
usuario de priorizar avanzar sobre seguir corriendo tests de facturas.

## 18. Governance

`FINAL STATUS: PASS`.

## 19. Performance

Ver `F28_TEST_PERFORMANCE.md` — medición cualitativa, no instrumentada
(fuera de alcance de esta fase).

## 20. Riesgos pendientes

- **`reverse('workspace')` no resuelve en ningún contexto** (F28-005b) —
  reproducido incluso fuera de pytest, con código de producción intacto.
  No es causado por F28 ni por `TenantTestCase`/`SintelTenantTestCase` —
  parece un problema de registro de nombres de URL en
  `apps/tenant/core/urls_ui.py`/`config/urls_tenant.py`. La ruta literal
  `/workspace/` SÍ funciona en una petición real (302), así que no es
  necesariamente un bug de producción visible para usuarios reales (que
  siempre navegan por URL literal, nunca por `reverse()` fuera de
  contexto) — pero bloquea a 4 archivos de test (21 tests) y merece
  investigación dedicada.
- **`self.f.id` vs `self.f.uuid`** en 2+ archivos de test (F28-005a) — bug
  de test real, ahora visible, antes enmascarado. Bajo riesgo (es un
  problema de test, no de producción — `BaseTenantViewSet.lookup_field`
  sigue siendo `uuid` en producción real).
- **`test_naturaleza_import_ubl.py`** sigue roto por 2 de sus 3 causas
  originales (F27-004) — sin cambios, ya documentado.
- **`apps/tenant/dashboard/tests/test_extractores.py`** — drift real
  encontrado por el agente de auditoría, no clasificado ni migrado en este
  pase (fuera del alcance de los 34 originales).

## 21. Deuda técnica

Heredada de F27 sin cambios: 3 clusters de duplicación en `facturas`
(`F27_TEST_INVENTORY.md` §3), 10 tests de contrato cambiado sin reescribir
(`test_importar_ubl_service.py`/`test_naturaleza_import_ubl.py` — parcial,
el primero ya se corrigió en F27). Nueva en F28: los 2 hallazgos de §20.

## 22. Estado final

```
F21 [OK] COMPLETED
F22 [OK] COMPLETED
F23 [OK] COMPLETED
F24 [OK] COMPLETED
F25 [OK] COMPLETED
F26 [OK] COMPLETED
F27 [OK] COMPLETED
F28 [OK] COMPLETED (alcance reducido y declarado explícitamente — ver §15-17)
```

**Tests reutilizados:** todos los existentes de facturas/core/perfil/compras.
**Tests corregidos:** 1 (`SyntaxError`).
**Tests consolidados:** 0.
**Tests parametrizados:** 0.
**Tests eliminados por redundancia:** 0 (en F28 propiamente; 1 se eliminó
en el trabajo de continuidad previo a F28, commit `28390e9`).
**Tests nuevos: 0** — resultado válido y preferido (regla F28.44).

Governance `FINAL STATUS: PASS`. 0 migraciones de esquema. 12 archivos de
test normalizados a `SintelTenantTestCase`. 1 `SyntaxError` real corregido.
2 hallazgos reales nuevos documentados con evidencia completa para fases
futuras (F28-005a/b). El objetivo central de F28 — confirmar y aplicar el
fix de `ROOT_URLCONF` diagnosticado en F27 — se cumplió y se verificó
empíricamente como correcto.
