# P0_CURRENT_BASELINE — Fase 0

Verificación de código real (sin modificar nada en esta fase) para los 4
hallazgos P0 de `documentacion/auditoria_empresarial/REMEDIATION_MASTER_PLAN.md`
(#1-4), en el estado actual del repositorio (commit `2ed017f`,
rama `feat/onboarding-cookie`).

**Fecha:** 2026-08-30

## Regla aplicada

Per §2 del programa de remediación: *"El reporte de remediación es la
agenda. NO asumir que el código actual todavía presenta exactamente el
defecto descrito."* Se verificó código real, no la descripción del plan.
Los 4 hallazgos ya fueron corregidos, testeados y verificados en 3
pasadas previas de esta misma sesión (commits `4dbe80c`, `81c98b2`,
`2ed017f`) — esta fase confirma que ese estado sigue vigente y no fue
revertido por ningún cambio posterior (no lo hay: `git log` confirma
`2ed017f` como HEAD, sin commits intermedios que toquen estos archivos).

## Clasificación por hallazgo

| ID | Hallazgo del plan | Clasificación | Evidencia de código actual |
|---|---|---|---|
| P0-01 | `Factura.destroy()` hace hard-delete sin reversa | **ALREADY_FIXED** | `apps/tenant/facturas/services/business_service.py:101` — `eliminar_factura()` bloquea DELETE salvo `BORRADOR`, comentario explícito referenciando el hallazgo original |
| P0-02 | `PeriodoContable` no bloquea edición/anulación de Facturas/Gastos | **ALREADY_FIXED** | `verificar_periodo_cerrado` referenciado 3× en `facturas/services/business_service.py`, 2× en `facturas/api/viewsets.py`, 3× en `gastos/services/business_service.py`, 2× en `gastos/api/viewsets.py` — los 4 puntos de mutación real están conectados |
| P0-03 | `Retencion` sin protección de duplicados | **ALREADY_FIXED** | `apps/tenant/contabilidad/models.py:1131` — constraint `uniq_retencion_documento_origen_tipo_activa` presente en el modelo, migración `0017` aplicada y verificada contra `pg_constraint` en los 3 tenants reales |
| P0-04 | `TipoComprobante.obtener_siguiente_numero()` sin `select_for_update()` | **ALREADY_FIXED** | `apps/tenant/contabilidad/models.py:237` — `select_for_update()` dentro de `transaction.atomic()`, verificado con concurrencia real (2 y 10 threads/conexiones independientes) |

**Ningún código fue modificado en esta fase.** Per §2: *"Si el problema ya
fue corregido: NO modificar código. Marcar: ALREADY_FIXED, y aportar
evidencia."*

## Evidencia de validación ya ejecutada (no re-ejecutada innecesariamente en esta fase)

| Suite | Resultado | Cuándo |
|---|---|---|
| P0-01 (`test_remediation_p0_01_delete_guard.py` + regresión `test_scope_facturas_f11.py`) | 12/12 PASS | Re-verificado en vivo en esta misma sesión, 1025.85s (batch combinado) |
| P0-02 (facturas + gastos) | 8/8 PASS | Ídem |
| P0-03 (`test_remediation_p0_03_retencion_duplicados.py` + regresión `test_retenciones_service.py`) | 18/18 PASS | Ídem |
| P0-04 secuencial (`test_remediation_p0_04_numeracion_comprobante.py`) | 3/3 PASS | Ídem |
| P0-04 concurrencia real (`test_remediation_p0_04_concurrencia_real.py`, 2 y 10 usuarios) | 2/2 PASS, 0 errores | Re-verificado en vivo, 151.89s, tras corrección de causa raíz del error de teardown (commit `2ed017f`) |
| Governance (`manage.py check`, `makemigrations --check`, `git diff --check`) | PASS | Ejecutado en la pasada anterior (commit `81c98b2`) sobre este mismo estado de código |

**Total re-confirmado en vivo en esta sesión: 43/43 tests dirigidos PASS.**
No se re-ejecuta la suite completa como condición de esta fase (§19 del
programa: *"La estrategia NO es ejecutar toda la suite después de cada
línea modificada"* — y aquí no hay línea modificada).

## DOCUMENTATION_DRIFT detectado (registro obligatorio per §3)

1. **P0-02 en sí mismo fue originalmente un caso de `DOCUMENTATION_DRIFT`**:
   `PeriodoContable.__doc__` (código) afirmaba *"Bloquea edición/anulación
   de Facturas y Gastos en periodos cerrados"* mientras que
   `verificar_periodo_cerrado()` nunca se invocaba desde esas 2 apps
   (confirmado por grep exhaustivo antes de corregir, ver
   `docs/remediation/REM-P0-02.md`). Ya corregido — el código ahora
   coincide con lo que su propia documentación siempre prometió.
2. **`apps/public/.agent/AUDITORIA_FLUJO_CORE_PUBLIC.md`** (hallazgo de la
   auditoría de onboarding de esta misma sesión, no parte de los P0 de
   facturas/contabilidad, pero registrado aquí por transparencia dado que
   es el mismo tipo de defecto): describe como vigente el diseño
   "Two-Phase DDL/DML" de una función `crear_tenant_con_owner()` que en
   realidad es código inalcanzable (colisión `services.py` vs
   `services/`). No afecta a P0-01..P0-04 (dominio distinto — onboarding,
   no facturas/contabilidad) pero se deja registrado como
   `DOCUMENTATION_DRIFT` activo en el repositorio, per la regla de "no
   aplicar cambios basados exclusivamente en documentación antigua" — ver
   `documentacion/AUDITORIA_ONBOARDING_TENANTS_2026-08-30.md` Hallazgo #3
   para el detalle completo. Fuera de alcance de esta misión P0.

No se detectó `DOCUMENTATION_DRIFT` vigente en P0-01, P0-03 o P0-04 al
momento de esta verificación — la documentación actual (`REM-P0-0{1,3,4}.md`,
`P0_0{1,3,4}_*.md`) coincide con el código real.

## Siguiente paso

Dado que los 4 hallazgos son `ALREADY_FIXED` con evidencia fresca, esta
misión procede directamente a completar los artefactos de rigor que este
programa exige y que las pasadas anteriores no cubrían explícitamente:

1. Grounding normativo fiscal/contable para P0-01 (conservación
   documental) y P0-03 (identidad de retenciones) — §4 del programa.
2. `docs/remediation/P0_CROSS_APP_VALIDATION.md` dedicado — §13 del
   programa (las pasadas anteriores lo incluyeron como sección dentro de
   `P0_FINAL_REPORT.md`, no como archivo independiente).
3. Actualización de `P0_EXECUTION_STATUS.md` y `P0_FINAL_REPORT.md` para
   referenciar estos artefactos y la clasificación `ALREADY_FIXED`.
