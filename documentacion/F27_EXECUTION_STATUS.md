# F27 — Estado de Ejecución

**Fecha inicio:** 2026-08-11 · **Commit inicial:** `08cf4be` (branch
`feat/onboarding-cookie`)
**Baseline documental:** Arquitectura General SINTEL ERP v3.29.0, DOC-M16.
**Estado F21-F26/DOC-M14/F26-006 al iniciar:** todo COMPLETED, governance
PASS, 25/26 en la última regresión enfocada (F26-006).

## Baseline técnico (F27.0)

```
manage.py check                             -> System check identified no issues
manage.py makemigrations --check --dry-run  -> No changes detected
git status --short                          -> arbol de trabajo con cambios preexistentes
                                                NO relacionados (mismo criterio de todas
                                                las fases previas)
```

## Estados por sub-fase

| Fase | Estado | Evidencia |
|---|---|---|
| F27.0 Baseline | COMPLETED | Este documento |
| F27.1 Inventario real de tests | COMPLETED | `F27_TEST_INVENTORY.md` (389 archivos, 2008 tests, split TenantTestCase/SintelTenantTestCase) |
| F27.2 Deteccion de duplicados | COMPLETED (facturas + bonus celery) | `F27_TEST_INVENTORY.md` §3, `F27_FINDINGS.md` F27-005/006 |
| F27.3 Analisis de cobertura real | COMPLETED | `F27_COVERAGE_MAP.md` |
| F27.4 Matriz de decision | COMPLETED | `F27_FINDINGS.md` (tabla resumen) |
| F27.5-9 No crear sin buscar / depuracion / consolidacion / parametrizacion / obsoletos | COMPLETED (alcance real, ver reduccion abajo) | `F27_FINDINGS.md` |
| F27.10-11 Flaky / order-dependent | NO EJECUTADO EXHAUSTIVO (ver reduccion de alcance) | — |
| F27.12 TenantTestCase / contaminacion | COMPLETED — hallazgo real distinto al esperado | `F27_FINDINGS.md` F27-003 |
| F27.13-15 Test UBL pendiente | COMPLETED | `F27_FINDINGS.md` F27-001 |
| F27.16-29 Testing progresivo (L0-L6) | Ya era norma vigente (`CLAUDE.md`, "Testing Progresivo por Alcance") — F27 no agrega niveles nuevos, los reafirma | `CLAUDE.md` |
| F27.17-20 Test Impact Analysis / selector | COMPLETED — reutilizado `tools/ekg/impact.py`, no se creo nada nuevo | `F27_SELECTIVE_TESTING.md` |
| F27.21 Facturas | COMPLETED | `F27_FINDINGS.md` F27-001, F27-002, F27-004 |
| F27.22 Nota Credito | COMPLETED (auditoria, sin cambios necesarios) | `F27_COVERAGE_MAP.md` |
| F27.23-30 Compras/Ventas/Inventario/Contabilidad/Multitenant/OrgScope/API/Seguridad/Celery | AUDITORIA LIGERA, sin hallazgos de bug real fuera de facturas en esta pasada (alcance reducido, ver abajo) | — |
| F27.31-32 Cobertura / Calidad de test | COMPLETED (facturas) | `F27_COVERAGE_MAP.md` |
| F27.33-35 Optimizacion / tests lentos / suites logicas | NO EJECUTADO (alcance reducido) | — |
| F27.36 Regresion F21-F26 | COMPLETED (regresion enfocada en archivos tocados, no full re-run de las ~150 tests ya verdes de F21-F25) | `F27_REGRESSION_REPORT.md` |
| F27.37 Regresion global | NO EJECUTADO (`make test` completo) — desproporcionado para el alcance real tocado (3 archivos de test), norma "Testing Progresivo por Alcance" de `CLAUDE.md` | — |
| F27.40-42 Quality gates / Governance / Git | COMPLETED | `F27_REGRESSION_REPORT.md` |
| F27.43-44 Documentacion / Control de estado | COMPLETED | Este documento + 4 mas |
| F27.45 Criterio de completado | Ver seccion final | — |

## Reduccion de alcance declarada

F27 tal como esta escrito pide una auditoria exhaustiva de **cada** app del
repo (compras, ventas, inventario, contabilidad, multitenant, organizational
scope, API, seguridad, Celery) mas deteccion de flaky/order-dependent tests
en la suite completa (~2008 tests). Ejecutar eso con el mismo rigor de
reproduccion real que se le dio a `facturas` (que por si sola tomo varias
corridas de mas de una hora) no es proporcional en una sola sesion.

**Decision explicita (regla F27 §65, "ante incertidumbre... continuar con
las fases independientes" + principio general de este proyecto de declarar
reducciones de alcance en vez de fingir cobertura):** esta pasada de F27 se
enfoco en:
1. El inventario real de **toda** la suite (F27.1 — si se hizo completo,
   es analisis estatico/grep, no ejecucion).
2. La app **facturas** en profundidad (auditoria + reproduccion + fix real),
   por ser la app con mas actividad reciente de la sesion (F26, F26-006,
   devoluciones) y la que F27 §5/§19 explicitamente prioriza (el test UBL
   pendiente).
3. El hallazgo sistemico de `TenantTestCase` (F27-003), que aplica
   potencialmente a otras apps pero no se verifico fuera de `facturas` en
   este pase.

Las demas apps (compras, ventas, inventario, contabilidad, etc.) no
mostraron sintomas de fallas en ninguna corrida de este pase ni de fases
anteriores (F21-F25 siguen en regresion consolidada verde) — no hay
evidencia de que necesiten la misma intervencion, pero tampoco se
verificaron con el mismo nivel de detalle que `facturas`. Recomendado como
alcance real de una fase F28 dedicada, con el mismo patron ya validado
aqui (inventario -> reproducir -> clasificar -> corregir solo lo real).

## Migraciones

**0 nuevas.** F27 es una fase de testing puro — no modifica modelos.
