# F25 — Estado de Ejecucion

**Fecha inicio:** 2026-08-10 · **Fecha cierre:** 2026-08-10
**Commit inicial:** `55a3dec` (branch `feat/onboarding-cookie`)
**Baseline documental:** Arquitectura General SINTEL ERP v3.25.0, DOC-M12.
**Estado F21/F22/F23/F24 al iniciar:** COMPLETED, governance PASS, 57/57 en la
ultima regresion consolidada (ver `F24_REGRESSION_REPORT.md`).

## Baseline tecnico (F25.0)

```
git status --short   -> arbol de trabajo con cambios preexistentes NO relacionados
                         (mismo criterio de todas las fases previas: nunca
                         `git add -A`, solo archivos de F25 se stagean)
manage.py check                             -> System check identified no issues
manage.py makemigrations --check --dry-run  -> No changes detected
governance --report                         -> FINAL STATUS: PASS
```

Suite existente a considerar como baseline: 57/57 (F21+F22+F23+F24), confirmado en
el cierre de F24 hace unas horas en la misma sesion -- no se re-ejecuto la suite
completa como "test inicial" separado dado que no hubo cambios de codigo entre el
cierre de F24 y el inicio de F25 (mismo commit HEAD).

## Inventario AST (F25.1)

Reproduccion del escaneo que origino F24-003, extendido a
`inventario/contabilidad/clientes/proveedores/gastos/empleados/cotizaciones/proyectos`
por instruccion del prompt maestro §9:

- **30 except-blocks** en **16 metodos** con el patron
  `@transaction.atomic` + `except` que retorna sin `raise` ni `set_rollback(True)`.
- De estos, **3 except-blocks** (2 metodos: `confirmar_recepcion`, `anular_recepcion`)
  ya estaban corregidos por F24.
- **27 except-blocks restantes en 14 metodos** se clasificaron individualmente en
  F25 (ver `F25_FINDINGS.md`): 1 metodo REAL BUG (`gastos.procesar_gasto`, 3
  except-blocks, corregido), 13 metodos SAFE_BY_DESIGN/FALSE_POSITIVE (24
  except-blocks restantes, sin modificar codigo, evidencia documentada).

## Estados por sub-fase

| Fase | Estado | Evidencia |
|---|---|---|
| F25.0 Baseline | COMPLETED | Este documento |
| F25.1 AST Inventory | COMPLETED | 30 except-blocks / 16 metodos, ver arriba |
| F25.2 Transaction Map | COMPLETED | `F25_ATOMICITY_MATRIX.md` |
| F25.3 Try/Except Audit | COMPLETED | `F25_FINDINGS.md` |
| F25.4 Reproduccion 25 candidatos | COMPLETED | 1 reproducido y corregido (gastos), 13 clasificados via analisis de codigo (regla F25 §30: no modificar solo para silenciar el AST) |
| F25.5 Atomic Audit | COMPLETED | `F25_ATOMICITY_MATRIX.md` |
| F25.6 Rollback Audit | COMPLETED | `F25_ROLLBACK_MATRIX.md` |
| F25.7 Verificacion F23 | COMPLETED, sin regresion | `procesar_y_facturar_venta()` releido, fix intacto |
| F25.8 Verificacion F24 | COMPLETED, sin regresion | `confirmar_recepcion()` releido, fix intacto |
| F25.9 Facturas | COMPLETED | `guardar_desde_dto()` -- SAFE_BY_DESIGN, ver F25-FP-013 |
| F25.10 Compras | COMPLETED | 5 metodos SAFE_BY_DESIGN + 2 ya fijos de F24 |
| F25.11 Ventas | COMPLETED | 5 metodos SAFE_BY_DESIGN |
| F25.12 Inventario | COMPLETED, sin hallazgos | `KardexService`/`TrasladoInventarioService` -- referencia positiva |
| F25.13 Contabilidad | COMPLETED, sin hallazgos | `Contabilizador` -- referencia positiva |
| F25.14 Idempotencia | COMPLETED | `F25_IDEMPOTENCY_MATRIX.md` |
| F25.15 HTTP Retry | COMPLETED, sin hallazgos nuevos | idempotencia por CUFE/UniqueConstraint ya suficiente |
| F25.16 Double Click | COMPLETED, sin hallazgos nuevos | mismo mecanismo, ya probado en F21/F23 |
| F25.17 Celery Retry | COMPLETED, sin hallazgos | `F25_FINDINGS.md` F25-002 |
| F25.18 Concurrencia | COMPLETED | `F25_CONCURRENCY_REPORT.md` |
| F25.19 Stock Concurrency | COMPLETED, evidencia de codigo (`select_for_update`) | `F25_CONCURRENCY_REPORT.md` §1 |
| F25.20 Accounting Concurrency | COMPLETED, evidencia de codigo (`UniqueConstraint`) | `F25_CONCURRENCY_REPORT.md` §2 |
| F25.21 Nested Transactions | COMPLETED, sin hallazgos | `KardexService` (patron ejemplar) |
| F25.22 External Side Effects | COMPLETED, sin hallazgos | Celery tasks revisadas, DB atomic no envuelve I/O externo indebidamente |
| F25.23 Signal Audit | COMPLETED, 0 signals | grep extendido a 6 apps |
| F25.24 Service Layer | COMPLETED, intacto | `F25_SECURITY_REPORT.md` |
| F25.25 DSV | COMPLETED, sin cambios | `F25_SECURITY_REPORT.md` |
| F25.26 Multi-Tenant | COMPLETED, sin cambios | `F25_SECURITY_REPORT.md` |
| F25.27 Empresa/Sede/Area | COMPLETED, sin cambios | `F25_SECURITY_REPORT.md` |
| F25.28 Regression | COMPLETED | `F25_REGRESSION_REPORT.md` |
| F25.29-31 Fix/FP/Deferred | COMPLETED | `F25_FINDINGS.md` |
| F25.32-35 Findings/Matrices | COMPLETED | los 3 documentos correspondientes |
| F25.36 Tests | COMPLETED | `apps/tenant/gastos/tests/test_f25_procesar_gasto_atomicidad.py` (2/2) |
| F25.37-58 Regresion final, governance, migraciones, git, check | COMPLETED | `F25_REGRESSION_REPORT.md`, `F25_FINAL_REPORT.md` |

## Migraciones

**0 nuevas.** Ningun modelo se modifico -- la unica correccion de codigo de F25
(`gastos/services/business_service.py`) es una adicion de 3 lineas
(`transaction.set_rollback(True)`) dentro de `except` ya existentes.

## Knowledge Graph / Dependency Graph

**NO CAMBIO DE GRAFO.** F25 no descubrio ninguna dependencia, componente o contrato
real nuevo -- es una auditoria de comportamiento transaccional dentro de servicios ya
mapeados, no de relaciones entre apps.
