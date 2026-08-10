# F24 — Reporte Final

**Fecha:** 2026-08-10

## 1. Objetivo

Auditoria E2E Enterprise del circuito F21+F22+F23 (Compras/Ventas -> Inventario ->
Kardex -> Costo -> Contabilidad Pull). F24 no agrega funcionalidad de negocio nueva:
demuestra con codigo real, tests reales y escenarios E2E que el circuito completo
funciona, corrige los defectos reales que encuentra dentro de su alcance quirurgico,
y documenta honestamente lo que queda fuera.

## 2. Baseline

Commit inicial `d1725e1` (branch `feat/onboarding-cookie`), arquitectura v3.24.0/
DOC-M11. F21/F22/F23 COMPLETED, 45/45 en la ultima regresion consolidada previa.
Governance `FINAL STATUS: PASS`, 0 migraciones pendientes, 0 issues de `manage.py check`.
Ver `F24_EXECUTION_STATUS.md` para el detalle completo.

## 3. Escenarios E2E ejecutados

12 tests nuevos, 3 archivos, cubriendo Compra E2E, Venta E2E (costo vs precio),
Compra+Venta (reconciliacion de stock), multi-item (3 productos + 1 servicio),
multi-sede, multi-tenant (2 schemas reales), DSV (UUID de otro tenant inyectado),
idempotencia contable (doble corrida de extractor+contabilizador), atomicidad
(reproduccion real de escritura parcial), periodo cerrado, y traslado sin asiento
externo. Detalle completo en `F24_E2E_TEST_MATRIX.md` (matriz obligatoria seccion 54
del prompt maestro, con cada celda resuelta a un test ejecutable real).

## 4. Hallazgos

2 hallazgos reales con impacto funcional, ambos corregidos y verificados; 1 hallazgo
del mismo tipo documentado como DEFERRED por proporcionalidad de alcance; 1 hallazgo
INFO (limitacion del clasificador de governance, no del codigo). Detalle completo,
con ID/severidad/evidencia/reproduccion/correccion/test/estado en `F24_FINDINGS.md`.

Resumen:

| ID | Severidad | Resumen | Estado |
|---|---|---|---|
| F24-001 | HIGH | Atomicidad rota en `confirmar_recepcion()` (compras) -- commit parcial de `MovimientoInventario` si un item posterior fallaba en el mismo loop | FIXED |
| F24-002 | MEDIUM | `PeriodoCerradoError` referenciaba `periodo.nombre` (inexistente), enmascarando el mensaje real tras un `AttributeError` | FIXED |
| F24-003 | MEDIUM | Mismo patron (except-return-sin-reraise) detectado por AST en 25 sitios mas de compras/ventas/facturas, no verificados individualmente | DEFERRED |
| F24-004 | INFO | `ventas -> facturas` (imports DIAN) clasificado `UNKNOWN` por el motor de governance | FALSE_POSITIVE |

## 5. Correcciones

Ambos fixes son de 1-3 lineas, dentro de metodos ya existentes, sin tocar modelos ni
crear nueva arquitectura:

- `apps/tenant/compras/services/business_service.py`: `transaction.set_rollback(True)`
  agregado en los `except` de `confirmar_recepcion()` (2) y `anular_recepcion()` (1).
- `apps/tenant/contabilidad/integracion/validadores.py`: `periodo.nombre` ->
  `periodo.periodo` en `validar_periodo_abierto()`.

Ambos con evidencia ANTES(FAIL)/DESPUES(PASS) real -- ver `F24_FINDINGS.md` F24-001
para la reproduccion explicita via `git stash` del fix.

## 6. Tests

12 nuevos (2+8+2), 57/57 en la regresion consolidada final F21+F22+F23+F24. Ver
`F24_E2E_TEST_MATRIX.md` y `F24_REGRESSION_REPORT.md`.

## 7. Regresion F21

16/16 (`test_f21_recepcion_compra.py` + `test_f21_traslado_inventario.py`), sin
cambios de comportamiento salvo la correccion de atomicidad (que no altera ningun
resultado observable en el camino feliz, solo el camino de fallo).

## 8. Regresion F22

20/20 (`test_f22_extractor_inventario_*.py`), sin cambios -- `ExtractorInventario` no
fue tocado por F24.

## 9. Regresion F23

9/9 (`test_f23_venta_inventario*.py`), sin cambios -- `VentaBusinessService` no fue
tocado por F24 (el fix de atomicidad de F24 esta en `compras`, no en `ventas`; F23 ya
habia corregido su propio caso analogo).

## 10. Seguridad

0 hallazgos CRITICAL/HIGH de seguridad nuevos. DSV confirmado con manipulacion real
de UUID entre tenants (rechazo limpio, nunca 200 con datos ajenos). `settings.DEBUG`
fallback en `OrganizationalContext`/`OrganizationalScope` revisado y confirmado
pre-existente, documentado, gateado por ausencia de `TenantProfile` + `DEBUG=True`
(nunca produccion) -- no se modifica sin evidencia de explotacion real. Detalle en
`F24_SECURITY_AUDIT.md`.

## 11. Multi-tenant

2 schemas fisicos reales (`tenant1`/`tenant2`). Circuito completo Compra->Venta->
Asiento corrido en un tenant sin dejar rastro en el otro (0 productos, 0 movimientos,
0 asientos cruzados). UUID de un tenant inyectado en el payload del otro rechazado
limpiamente.

## 12. Empresa/Sede/Area

Sin cambios de comportamiento. Multi-sede reconfirmado con el escenario literal del
prompt maestro (Bogota/Barranquilla, ventas secuenciales sin contaminacion). Detalle
en `F24_ORGANIZATIONAL_AUDIT.md`.

## 13. Idempotencia

Compra (F21) y Venta (F23) reconfirmadas sin cambios. Contable (F22, Contabilizador)
verificada con doble corrida explicita de `contabilizar_pendientes()`: 1 asiento por
documento origen, segunda corrida reporta 0 pendientes (no error, no duplicado).

## 14. Atomicidad

Hallazgo real (F24-001) encontrado y corregido con evidencia ANTES/DESPUES completa.
Ver §5 y `F24_FINDINGS.md`.

## 15. Contabilidad

Asientos verificados semanticamente cuadrados (`debe_total == haber_total`) en cada
escenario E2E, con montos verificados matematicamente (`cantidad x costo_unitario`,
nunca `precio_venta`). Periodo cerrado bloquea contabilizacion real (hallazgo F24-002
corregido, la proteccion en si nunca fallo -- solo el mensaje de error).

## 16. Governance

`FINAL STATUS: PASS` antes y despues de los fixes. 0 `FORBIDDEN` en el dependency
graph (375 edges). Ver `F24_GOVERNANCE_REPORT.md`.

## 17. Dependency Graph

Sin cambios estructurales. `ventas -> contabilidad` e `inventario -> contabilidad`
confirmados ausentes del grafo (Pull real, no solo ausencia de `FORBIDDEN`).

## 18. Knowledge Graph

NO CAMBIO DE GRAFO -- F24 no descubrio relaciones reales nuevas que no estuvieran ya
registradas por F21/F22/F23.

## 19. Migraciones

**0 nuevas.** Ningun modelo se modifico; los 2 fixes de F24 son correcciones de logica
dentro de metodos existentes.

## 20. Deuda DEFERRED

- F24-003: 25 sitios adicionales con el mismo patron de atomicidad detectados por AST
  pero no verificados individualmente (recomendacion: auditoria dedicada, fuera de
  una fase de negocio especifica).
- Devoluciones (`NotaCredito` sin lineas de producto), despacho parcial, reverso por
  anulacion: siguen DEFERRED, sin inconsistencia documental nueva encontrada (F24.23-25,
  auditoria confirmatoria unicamente, sin implementacion, tal como exige el prompt
  maestro).

## 21. Riesgos restantes

- F24-003 (ver §20): riesgo latente no cuantificado en 25 sitios fuera del circuito
  critico de escritura de inventario/kardex (la mayoria son operaciones CRUD de un
  solo objeto, riesgo estructural bajo, pero no verificado caso por caso).
- El fallback `settings.DEBUG` de `OrganizationalContext`/`OrganizationalScope`
  (§10) sigue siendo un riesgo teorico en entornos de desarrollo mal configurados
  (nunca en produccion) -- pre-existente, fuera del alcance de F24.

## 22. Estado final

```
F21 [OK] COMPLETED
F22 [OK] COMPLETED
F23 [OK] COMPLETED
F24 [OK] COMPLETED
```

**ENTERPRISE E2E BASELINE: PASS**

57/57 tests en regresion consolidada real (46:52). Governance PASS. 0 migraciones
pendientes. 2 defectos reales encontrados y corregidos con evidencia verificable.
0 hallazgos CRITICAL sin resolver. 0 hallazgos HIGH sin resolver. Deuda DEFERRED
documentada explicitamente en §20, no oculta.
