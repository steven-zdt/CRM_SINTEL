# F23 — Estado de Ejecucion

**Fecha inicio:** 2026-08-10 · **Fecha cierre:** 2026-08-10
**Commit inicial:** `4354674` (branch `feat/onboarding-cookie`)
**Estado F21/F22 al iniciar:** COMPLETED, governance PASS.
**Estado F21/F22 al cerrar F23:** confirmado sin regresion — 36/36 tests (F21 16 + F22 20)
re-ejecutados junto con los 9 de F23 en una corrida consolidada (45/45).
**Governance final:** `FINAL STATUS: PASS`, 0 aristas `FORBIDDEN` (375 totales, +2
`ventas -> inventario` legitimas sobre las 373 de F22).
**Migraciones:** 0 nuevas — `makemigrations --check --dry-run` limpio antes y despues.

```bash
git status --short
docker compose exec web python -m tools.organizational_governance.cli --report   # FINAL STATUS: PASS
docker compose exec web python manage.py makemigrations --check --dry-run        # No changes detected
docker compose exec web python manage.py check                                   # System check identified no issues
```

## Estados

| Fase | Estado | Evidencia |
|---|---|---|
| F23.0 Baseline | 🟢 COMPLETED | Este documento |
| F23.1 Ventas Audit | 🟢 COMPLETED | `documentacion/F23_VENTAS_BASELINE.md` |
| F23.2 Facturas Audit | 🟢 COMPLETED | `documentacion/F23_FACTURAS_BASELINE.md` |
| F23.3 Inventario Audit | 🟢 COMPLETED (re-confirmacion, sin cambios sobre F21/F22) | `F23_VENTAS_BASELINE.md` §8 |
| F23.4 Contabilidad Audit | 🟢 COMPLETED (re-confirmacion, sin cambios sobre F22) | `documentacion/F23_SALE_INVENTORY_CONTRACT.md` §7 |
| F23.5 Evento de Salida | 🟢 COMPLETED | `documentacion/F23_INVENTORY_ISSUE_POLICY.md` §1 |
| F23.6 Politica Stock | 🟢 COMPLETED | `F23_INVENTORY_ISSUE_POLICY.md` §8 |
| F23.7 Contexto Empresa/Sede/Area | 🟢 COMPLETED | `F23_VENTAS_BASELINE.md` §3 |
| F23.8 Contrato Venta -> Inventario | 🟢 COMPLETED | `documentacion/F23_SALE_INVENTORY_CONTRACT.md` |
| F23.9 Idempotencia | 🟢 COMPLETED | `F23_SALE_INVENTORY_CONTRACT.md` §3, test real |
| F23.10 Multi-item | 🟢 COMPLETED | test real |
| F23.11 Stock | 🟢 COMPLETED | test real (rollback atomico completo) |
| F23.12 Venta Parcial | 🟡 DEFERRED (documentado, no existe el concepto en el modelo) | `F23_INVENTORY_ISSUE_POLICY.md` §9 |
| F23.13 Devoluciones | 🟡 DEFERRED (documentado, `NotaCredito` sin lineas) | `F23_FACTURAS_BASELINE.md` §3 |
| F23.14 Anulaciones | 🟢 COMPLETED (confirmado que no aplica reverso) | test real |
| F23.15 Facturacion | 🟢 COMPLETED (sin cambios, preservado) | `F23_FACTURAS_BASELINE.md` §1 |
| F23.16 Costo | 🟢 COMPLETED | `Producto.costo_promedio`, test real |
| F23.17 Contabilidad Pull | 🟢 COMPLETED (sin cambios, F22 lo detecta solo) | test E2E real |
| F23.18 Multi-Tenant | 🟢 COMPLETED | 2 schemas reales |
| F23.19 E2E | 🟢 COMPLETED | Venta -> SALIDA_VENTA -> Extractor -> Asiento |
| F23.20 Regresion F21 | 🟢 COMPLETED | 16/16 |
| F23.21 Regresion F22 | 🟢 COMPLETED | 20/20 |
| F23.22 Governance | 🟢 COMPLETED | `FINAL STATUS: PASS` |
| F23.23 Knowledge Graph | 🟢 COMPLETED (extension automatica) | — |
| F23.24 Dependency Graph | 🟢 COMPLETED | 0 `FORBIDDEN`, 0 `ventas->contabilidad` en produccion |
| F23.25 Documentacion | 🟢 COMPLETED | 8 documentos + `arquitectura_general.md` |
| F23.26 Auditoria Final | 🟢 COMPLETED | ruff/bandit limpios, 45/45 tests, governance PASS |

## Hallazgo destacado

Bug real de atomicidad preexistente en `VentaBusinessService.procesar_y_facturar_venta()`
(decorado `@transaction.atomic` pero su try/except no re-lanzaba, permitiendo commits parciales
en caso de error) — corregido con `transaction.set_rollback(True)`. Ver
`documentacion/F23_FINAL_REPORT.md` §3 para el detalle completo.

## Nota de alcance

Mismo criterio que F21/F22: no se declara "F23 100% completo" respecto al literal del prompt
maestro. Devoluciones, despacho parcial y reverso por anulacion quedan `DEFERRED`, documentados
individualmente, no ocultos.
