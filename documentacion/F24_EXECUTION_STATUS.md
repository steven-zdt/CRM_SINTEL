# F24 — Estado de Ejecucion

**Fecha inicio:** 2026-08-10 · **Fecha cierre:** 2026-08-10
**Commit inicial:** `d1725e1` (branch `feat/onboarding-cookie`)
**Baseline documental:** Arquitectura General SINTEL ERP v3.24.0, DOC-M11.
**Estado F21/F22/F23 al iniciar:** COMPLETED, governance PASS, 45/45 en la ultima
regresion consolidada (ver `F23_EXECUTION_STATUS.md`).

## Estado git al iniciar (F24.0)

```
git status --short   -> arbol de trabajo con numerosos cambios preexistentes NO
                         relacionados con F21/F22/F23/F24 (otras sesiones/ramas en
                         curso: empresa, gastos, proveedores, tools/ekg, etc.) --
                         mismo criterio ya establecido: nunca `git add -A`, solo
                         archivos de F24 se stagean.
git log -5 --oneline -> d1725e1 docs(f23): governance y reporte final F23
                         87f3c77 test(f23): suite real Venta->Inventario
                         e5b2a0c feat(ventas): generar SALIDA_VENTA real (F23)
                         aeb6151 docs(f23): auditoria real y contrato F23
                         4354674 docs(f22): governance y reporte final F22
```

## Baseline tecnico (F24.0)

- Governance: `FINAL STATUS: PASS` (ver `F24_GOVERNANCE_REPORT.md`).
- `manage.py check`: sin issues.
- `makemigrations --check --dry-run`: sin cambios pendientes.
- Knowledge Graph: 160 entidades, 168 relaciones.
- Dependency Graph: 375 edges, 0 `FORBIDDEN`.

## Estados por sub-fase

| Fase | Estado | Evidencia |
|---|---|---|
| F24.0 Baseline | COMPLETED | Este documento |
| F24.1 Dependency Audit | COMPLETED | `F24_GOVERNANCE_REPORT.md` |
| F24.2 Auditoria F21 | COMPLETED (sin regresion) | `F24_REGRESSION_REPORT.md` |
| F24.3 Traslados | COMPLETED | `test_f24_traslado_no_genera_asiento_contable_externo` |
| F24.4 Auditoria F22 | COMPLETED (sin regresion) | `F24_REGRESSION_REPORT.md` |
| F24.5 Auditoria F23 | COMPLETED (sin regresion) | `F24_REGRESSION_REPORT.md` |
| F24.6 E2E Compra | COMPLETED | `F24_E2E_TEST_MATRIX.md` |
| F24.7 E2E Venta | COMPLETED | `F24_E2E_TEST_MATRIX.md` |
| F24.8 Compra+Venta | COMPLETED | `F24_E2E_TEST_MATRIX.md` |
| F24.9 Multi-item | COMPLETED | `F24_E2E_TEST_MATRIX.md` |
| F24.10 Multi-sede | COMPLETED | `F24_E2E_TEST_MATRIX.md` |
| F24.11 Multi-tenant | COMPLETED | `F24_E2E_TEST_MATRIX.md` |
| F24.12 DSV | COMPLETED | `F24_SECURITY_AUDIT.md` |
| F24.13 Scope organizacional | COMPLETED (auditoria, sin test HTTP nuevo) | `F24_ORGANIZATIONAL_AUDIT.md` |
| F24.14 Idempotencia compra | COMPLETED (ya cubierta por F21, reconfirmada) | `F24_E2E_TEST_MATRIX.md` |
| F24.15 Idempotencia venta | COMPLETED (ya cubierta por F23, reconfirmada) | `F24_E2E_TEST_MATRIX.md` |
| F24.16 Idempotencia contable | COMPLETED | `test_f24_idempotencia_contable_doble_corrida` |
| F24.17 Atomicidad | COMPLETED -- HALLAZGO REAL CORREGIDO | `F24_FINDINGS.md` F24-001 |
| F24.18 Stock insuficiente | COMPLETED (politica ya auditada y probada en F23: RECHAZO atomico completo) | `F23_TEST_MATRIX.md` |
| F24.19 Servicios | COMPLETED (ya cubierta por F23, reconfirmada) | `F24_E2E_TEST_MATRIX.md` |
| F24.20 Costo de venta | COMPLETED | `test_f24_venta_e2e_costo_promedio_no_precio_venta` |
| F24.21 Contabilidad | COMPLETED | asientos cuadrados verificados en cada E2E |
| F24.22 Periodos cerrados | COMPLETED -- HALLAZGO REAL CORREGIDO | `F24_FINDINGS.md` F24-002 |
| F24.23 Devoluciones (audit only) | COMPLETED, sigue DEFERRED (sin inconsistencia documental encontrada) | `F23_FINAL_REPORT.md` #5 |
| F24.24 Anulacion (audit only) | COMPLETED, comportamiento confirmado sin cambios | `F23_TEST_MATRIX.md` |
| F24.25 Despacho parcial (audit only) | COMPLETED, no existe el concepto, sigue DEFERRED | `F23_FINAL_REPORT.md` #5 |
| F24.26 Migraciones | COMPLETED | 0 migraciones nuevas |
| F24.27-29 Tests unit/integracion/E2E | COMPLETED | `F24_E2E_TEST_MATRIX.md` |
| F24.30-32 Regresion F21+F22+F23 | COMPLETED | `F24_REGRESSION_REPORT.md` |
| F24.33 Governance | COMPLETED | `F24_GOVERNANCE_REPORT.md` |
| F24.34 Dependency Graph | COMPLETED | `F24_GOVERNANCE_REPORT.md` |
| F24.35 Knowledge Graph | COMPLETED -- NO CAMBIO DE GRAFO | ver nota abajo |
| F24.36 Service Layer | COMPLETED | `F24_GOVERNANCE_REPORT.md` |
| F24.37 Zero-Trust | COMPLETED | `F24_SECURITY_AUDIT.md` |
| F24.38 UUID | COMPLETED | `F24_SECURITY_AUDIT.md` |
| F24.39 Frontend | COMPLETED -- N/A, F21/F22/F23 no tocaron frontend | confirmado via `git show --stat` de los 13 commits F21+F22+F23 |
| F24.40 Performance | COMPLETED, sin hallazgos (select_related/only ya aplicados en `ExtractorInventario.extraer_pendientes()` y `VentaBusinessService._generar_salida_inventario()`; sin optimizaciones prematuras) | spot-check manual, sin regresion de queries |
| F24.41 Transacciones | COMPLETED -- ver F24.17 | `F24_FINDINGS.md` |
| F24.42-46 Findings y correccion controlada | COMPLETED | `F24_FINDINGS.md` |
| F24.47-56 Documentacion, matriz, informe final | COMPLETED | este documento y los listados en `F24_FINAL_REPORT.md` |

## Nota sobre Knowledge Graph (F24.35/F24.54)

F24 no descubrio ninguna relacion real nueva entre entidades que no estuviera ya
registrada por F21/F22/F23 (`Venta -> ItemVenta -> MovimientoInventario`,
`RecepcionCompraItem -> MovimientoInventario`, `MovimientoInventario -> AsientoContable`
via extractor, todas preexistentes). **NO CAMBIO DE GRAFO** -- no se modifico para
generar actividad artificial.

## Migraciones

**0 nuevas.** Los 2 fixes de codigo de F24 (`compras/services/business_service.py`,
`contabilidad/integracion/validadores.py`) no tocan modelos.
