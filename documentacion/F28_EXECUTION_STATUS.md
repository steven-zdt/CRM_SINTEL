# F28 — Estado de Ejecución

**Fecha inicio:** 2026-08-11 · **Commit inicial:** `e26406d` (branch
`feat/onboarding-cookie`)
**Baseline documental:** Arquitectura General SINTEL ERP v3.30.0, DOC-M17.
**Estado F21-F27 al iniciar:** todo COMPLETED, governance PASS.

## Baseline técnico (F28.0)

```
branch: feat/onboarding-cookie
git status --short: 78 archivos con cambios preexistentes NO relacionados
                     (mismo criterio de todas las fases previas -- ninguno
                     tocado por F21-F27)
manage.py check                             -> System check identified no issues (0 silenced)
manage.py makemigrations --check --dry-run  -> No changes detected
git diff --check -> 2 lineas de whitespace en archivos preexistentes NO
                     relacionados (test_retenciones_api.py:282, notas.txt:10)
```

## Estados por sub-fase

| Fase | Estado | Evidencia |
|---|---|---|
| F28.0-1 Baseline + recuperar F27 | COMPLETED | Este documento |
| F28.2-5 Auditoría 34 TenantTestCase + migración controlada | COMPLETED | `F28_TENANT_TEST_AUDIT.md`, `F28_FINDINGS.md` F28-002 |
| F28.6 Validación del harness | COMPLETED (empírico) | `test_facturas_list_naturaleza_api.py` 100% limpio tras el swap — prueba directa |
| F28.7 No confundir problemas | COMPLETED | `F28_FINDINGS.md` F28-005a/b clasificados por separado |
| F28.8-14 Facturas: re-baseline + clasificación | COMPLETED (alcance reducido, verificación quirúrgica) | `F28_FACTURAS_REGRESSION.md` |
| F28.16 Duplicado Celery | COMPLETED | Eliminado (commit previo a F28 formal) |
| F28.17-19 Aislamiento/multi-tenant/org scope | COMPLETED (verificación quirúrgica) | `F28_FINDINGS.md` |
| F28.23-25 Test Impact Analysis + Knowledge Graph | COMPLETED | `F28_TEST_IMPACT.md` |
| F28.26-28 Expansión inicial (compras) | COMPLETED (compras GREEN) | `F28_FINDINGS.md` F28-006 |
| F28.32-34 Regresión facturas/consolidada/global | NO EJECUTADO (alcance reducido, indicación explícita del usuario) | `F28_FACTURAS_REGRESSION.md` |
| F28.36 Performance | COMPLETED (ligero, no instrumentado) | `F28_TEST_PERFORMANCE.md` |
| F28.37-38 Quality gates + Governance | COMPLETED | `FINAL STATUS: PASS` |
| F28.39-45 Git + Documentación + arquitectura DOC-M18 | COMPLETED | `F28_FINAL_REPORT.md`, commits |

## Estado: `COMPLETED`
