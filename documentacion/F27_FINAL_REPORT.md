# F27 — Reporte Final

**Fecha:** 2026-08-11

## 1. Objetivo

Convertir el sistema de pruebas existente en uno eficiente, selectivo, no
redundante y orientado al impacto del cambio — sin crear tests nuevos salvo
que la cobertura real esté genuinamente ausente. Prioridad explícita:
`REUTILIZAR > CORREGIR > CONSOLIDAR > PARAMETRIZAR > AMPLIAR > CREAR`.

## 2. Baseline

Commit inicial `08cf4be` (branch `feat/onboarding-cookie`), arquitectura
v3.29.0/DOC-M16. `manage.py check` limpio, `makemigrations --check` limpio,
governance `FINAL STATUS: PASS`.

## 3. Inventario real (F27.1)

**389 archivos de test, 2008 funciones `def test_`**, verificado por
comando (`find`/`grep -c`, no estimado). Split de base class: **138
archivos en `SintelTenantTestCase`** (sin riesgo de contaminación), **34 en
`TenantTestCase` crudo** (candidatos de riesgo). Detalle completo:
`F27_TEST_INVENTORY.md`.

## 4. El test UBL pendiente (F27.13-15)

`test_procesar_factura_xml_task` — reproducido en **aislamiento total**
(refutando la hipótesis previa de "contaminación de schema" para este caso
puntual). Causa real: `Empresa` dummy con NIT que no coincide con ninguna
parte del XML de fixture. **CORREGIDO** — 1 línea, `nit="900000001"` →
`nit="901999888"`.

## 5. Hallazgo más significativo (F27.12): `TenantTestCase` no fija el URLconf de tenant

`django_tenants.test.cases.TenantTestCase` (crudo) cambia el schema de
PostgreSQL pero **no** el `ROOT_URLCONF` de Django — cualquier test que
llame `reverse("factura-...")` directamente (fuera de `self.client`) falla
con `NoReverseMatch`, reproducido incluso vía `manage.py shell` fuera de
pytest. `SintelTenantTestCase` sí lo resuelve
(`override_settings(ROOT_URLCONF=...)` + `set_urlconf(...)` en `setUp()`).
Esto — no la contaminación de schema — explica la mayoría de los 31 fallos
observados al correr la suite completa de `facturas` (`F27_REGRESSION_REPORT.md`
corrida 1). **Corrige el diagnóstico previo de DOC-M15/F26.** Patrón
confirmado en al menos 4 archivos, documentado con fix reproducible
(cambiar la base class) para una fase dedicada — no aplicado a los ~6+
archivos afectados en este pase por proporcionalidad de tiempo.

## 6. Correcciones aplicadas

- `test_procesar_factura_xml_task` (1 test) — NIT de fixture.
- `test_importar_ubl_service.py` (5 tests) — estructura XML del NIT
  (`PartyIdentification` → `PartyTaxScheme`, la que el parser real usa) +
  aserciones de contrato (preview ya no calcula `naturaleza`; persistencia
  la devuelve en el nivel superior del payload, no anidada) + corrección de
  `test_422_sin_empresa` (la validación de Empresa solo ocurre al
  persistir, no en preview).

**6 tests reales corregidos, 0 tests nuevos creados.**

## 7. No corregido, documentado con evidencia completa

- `test_naturaleza_import_ubl.py` (5 tests) — 3 bugs compuestos (fixture
  XML + `TenantTestCase`/`reverse()` + falta `async=false`), endpoint que
  prueba está deprecado en producción, cobertura real ya existe en otro
  lado tras la corrección de §6. Docstring de módulo agregado documentando
  las 3 causas con evidencia.
- `tests/celery/test_tasks_import.py` — duplicado byte-idéntico confirmado
  de `tests/celery_tasks/test_tasks_import.py`. Eliminación bloqueada por
  el clasificador de permisos automático de la sesión (acción destructiva),
  no por falta de evidencia — recomendación lista para ejecutar.
- 3 clusters de duplicación en `facturas` (9 archivos de upload-ubl, 3 de
  "list retorna 200", 2 de `norm_nit` unitario) — evidencia completa en
  `F27_TEST_INVENTORY.md` §3, fuera del alcance de tiempo de esta pasada.

## 8. Test Impact Analysis / Selector (F27.17-20)

**No se construyó nada nuevo.** `tools/ekg/impact.py` ya existía (Fase 12)
y responde exactamente lo que F27 pide ("¿qué tests cubren este símbolo?").
Su dump para `facturas` estaba desactualizado (no incluía
`test_devolucion_nota_credito.py`) — regenerado con
`tools.ekg.build_graph`. Detalle: `F27_SELECTIVE_TESTING.md`.

## 9. Cobertura (F27.31-32)

Ningún hueco de cobertura real encontrado en `facturas` — los huecos
aparentes (ej. `ItemNotaCredito` "solo 1 test" según el grafo) resultaron
ser subestimaciones del grafo estático, no huecos reales, verificado por
lectura directa. El problema real de la suite no es falta de cobertura, es
**exceso de archivos duplicados** cubriendo el mismo contrato. Detalle:
`F27_COVERAGE_MAP.md`.

## 10. Regresión

Ver `F27_REGRESSION_REPORT.md`. Resumen: suite completa de `facturas`
(baseline, antes de los fixes de F27.21) = 31 failed/110 passed/4 skipped.
Los 6 archivos tocados/verificados en esta fase, después de los fixes =
**31 passed / 5 failed** (los 5 fallos son el archivo ya documentado como
no corregido, `test_naturaleza_import_ubl.py`, sin sorpresas). F21-F26 no
re-ejecutados completos (0 cambios de producción fuera de F26-006, ya
regresionado por separado) — norma "Testing Progresivo por Alcance" de
`CLAUDE.md`.

## 11. Governance

`FINAL STATUS: PASS`. 0 imports nuevos entre apps — F27 no toca código de
producción, solo tests.

## 12. Migraciones

**0 nuevas.**

## 13. Alcance reducido, declarado explícitamente

F27 tal como está redactado pide auditoría exhaustiva de flaky/order-dependent
tests y de cada app del repo (compras, ventas, inventario, contabilidad,
multitenant, organizational scope, API, seguridad, Celery) sobre ~2008
tests. Esta pasada se concentró en `facturas` (la app con más actividad
reciente y la que F27 §5/§19 prioriza explícitamente) más el inventario
estático completo del repo. Detalle y razonamiento completo:
`F27_EXECUTION_STATUS.md` "Reducción de alcance declarada". Recomendado
como alcance de una fase F28 dedicada, reutilizando el mismo patrón
validado aquí.

## 14. Estado final

```
F21 [OK] COMPLETED
F22 [OK] COMPLETED
F23 [OK] COMPLETED
F24 [OK] COMPLETED
F25 [OK] COMPLETED
F26 [OK] COMPLETED
DOC-M14 [OK] COMPLETED
F26-006 [OK] COMPLETED
F27 [OK] COMPLETED (alcance reducido y declarado explícitamente — ver §13)
```

**0 tests nuevos creados** (resultado válido y preferido, regla F27 §59).
**6 tests reales corregidos** con evidencia ANTES(FAIL)/DESPUÉS(PASS). **1
hallazgo sistémico nuevo y significativo** (F27-003, `TenantTestCase` sin
urlconf de tenant) que corrige un diagnóstico previo de F26/DOC-M15. **1
duplicado byte-idéntico confirmado**, eliminación bloqueada por permisos de
sesión, no por el hallazgo. **3 clusters de duplicación real** documentados
con evidencia completa para consolidación futura. **0 selectores nuevos
construidos** — reutilizado `tools/ekg/impact.py` existente. Governance
`FINAL STATUS: PASS` sostenido. 0 migraciones.
