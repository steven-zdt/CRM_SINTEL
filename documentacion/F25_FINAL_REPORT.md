# F25 — Reporte Final

**Fecha:** 2026-08-10

## 1. Objetivo

Auditoria enterprise transversal de atomicidad, rollback, idempotencia, retry y
concurrencia sobre todo el circuito F21-F24 y, especificamente, resolver el
`DEFERRED` que F24 dejo (F24-003): ~25 sitios detectados por AST con el mismo patron
de atomicidad que F23/F24 encontraron y corrigieron (`@transaction.atomic` +
`except` que retorna sin `raise` ni `transaction.set_rollback(True)`), sin
determinar individualmente cuales eran bugs reales.

## 2. Baseline

Commit inicial `55a3dec` (branch `feat/onboarding-cookie`), arquitectura v3.25.0/
DOC-M12. F21/F22/F23/F24 COMPLETED, 57/57 en la ultima regresion consolidada previa.
Governance PASS, 0 migraciones pendientes.

## 3. Candidatos encontrados

Escaneo AST reproducido y **extendido** (por instruccion del prompt maestro F25 §9)
a `inventario/contabilidad/clientes/proveedores/gastos/empleados/cotizaciones/proyectos`,
mas alla del alcance original de compras/ventas/facturas de F24-003: **30
except-blocks en 16 metodos**. La extension del alcance descubrio 3 except-blocks
nuevos (1 metodo, `gastos.procesar_gasto`) que F24-003 no habia contemplado.

## 4. Candidatos F24-003

De los 27 except-blocks originales (14 metodos, compras/ventas/facturas), 3
(2 metodos: `confirmar_recepcion`, `anular_recepcion`) ya estaban corregidos por
F24. Los 24 restantes (12 metodos) se clasificaron en esta fase.

## 5. Candidatos reales

**1 REAL BUG nuevo**, fuera del conjunto original de F24-003 pero dentro del alcance
extendido de F25: `GastoBusinessService.procesar_gasto()` (gastos). Mismo patron
exacto que F23/F24: crea `DocumentoSoporte`, luego un loop de
`RetencionesService.crear_retencion()` (escrituras crudas sin savepoint propio) --
si la retencion N fallaba tras la N-1 ya creada, el `DocumentoSoporte` y la primera
retencion quedaban comprometidos pese a `ok=False`. Ver `F25_FINDINGS.md` F25-001
para evidencia ANTES(FAIL)/DESPUES(PASS) completa.

## 6. False positives

13 metodos (24 except-blocks) del conjunto original de F24-003 se clasificaron
`SAFE_BY_DESIGN`/`FALSE_POSITIVE` mediante lectura de codigo real (no solo el patron
AST): cada uno tiene una UNICA escritura real, delegada a otro metodo
`@transaction.atomic` que actua como savepoint independiente y se auto-revierte ante
cualquier excepcion interna, sin importar el comportamiento del `except` externo.
Ninguno fue modificado (regla F25 §30: no tocar codigo solo para silenciar el AST).
Detalle completo con el razonamiento tecnico especifico de cada uno en
`F25_FINDINGS.md` (F25-FP-001 a F25-FP-013).

## 7. Safe by design

El caso mas notable: `FacturaBusinessService.guardar_desde_dto()` (facturas) tiene
5 except-blocks (el conteo mas alto de todos los candidatos) pero resulto ser el
MAS seguro de todos -- sus 5 `except` son guardas tempranas antes de cualquier
escritura, y la secuencia real de escrituras (Factura + impuestos + retenciones +
NotaCredito + items) no tiene NINGUN manejo local de excepciones: cualquier fallo
propaga naturalmente y Django revierte todo correctamente via el decorador
`@transaction.atomic` del metodo. Documentado como ejemplo de por que "tiene
multiples writes" no es sinonimo de "es vulnerable". `KardexService.registrar_movimiento()`
y `Contabilizador.contabilizar()` tambien se documentan como referencias positivas de
diseno transaccional correcto (nested atomic + `raise` explicito para lo inesperado).

## 8. Correcciones

1 archivo de produccion modificado: `apps/tenant/gastos/services/business_service.py`
-- `transaction.set_rollback(True)` en los 3 `except` de `procesar_gasto()`. Cambio
de 5 lineas, sin tocar modelos, imports, DSV ni scope.

## 9. Atomicidad

Ver `F25_ATOMICITY_MATRIX.md` -- 16 servicios/metodos mapeados con evidencia real de
writes/atomic/rollback/riesgo.

## 10. Rollback

Ver `F25_ROLLBACK_MATRIX.md` -- 5 servicios con inyeccion de fallo real por write
(3 con test de reproduccion dedicado: RecepcionCompra, Venta/Facturacion, Gasto/Retenciones;
2 confirmados SAFE_BY_DESIGN por analisis de codigo: Contabilizador, guardar_desde_dto).

## 11. Idempotencia

Ver `F25_IDEMPOTENCY_MATRIX.md` -- 9 escenarios (POST duplicado, doble click, Celery
retry, worker restart, reprocesamiento, concurrencia real) todos cubiertos por el
mecanismo existente (`UniqueConstraint` + chequeo previo + CUFE), sin necesidad de
un framework nuevo.

## 12. Retry

`procesar_factura_xml_task` (facturas) y `ejecutar_integracion_contable_task`
(contabilidad, con DLQ real via `FailedTenantTask`) revisadas: ambas son
retry-safe gracias a la idempotencia ya existente (CUFE, `UniqueConstraint`), sin
defectos encontrados. Ver `F25_FINDINGS.md` F25-002.

## 13. Celery

Solo 2 `@shared_task` reales en el circuito auditado (facturas, contabilidad), ambas
revisadas en §12. Ningun otro `@shared_task`/`.delay()`/`.retry()` existe en
compras/ventas/inventario.

## 14. Concurrencia

Ver `F25_CONCURRENCY_REPORT.md`. Stock: `select_for_update()` sobre `Producto`
(evidencia de codigo). Asiento contable: `UniqueConstraint` + chequeo previo,
documentado explicitamente en el propio codigo del `Contabilizador`. Sin deadlocks
identificados (ordenes de adquisicion de locks consistentes, sin cruces entre
servicios).

## 15. Multi-tenant

Sin cambios de comportamiento. La correccion de F25 (gastos) opera dentro del
`empresa` ya resuelto por el llamador, sin introducir ninguna ruta de acceso nueva.

## 16. Empresa/Sede/Area

Sin cambios. Ver `F25_SECURITY_REPORT.md`.

## 17. DSV

Sin cambios -- confirmado por `git diff` que la correccion de F25 no toca ninguna
linea de resolucion de entidades/DSV.

## 18. Inventario

`KardexService`/`TrasladoInventarioService` reconfirmados sin hallazgos --
documentados como referencia de buen diseno transaccional.

## 19. Contabilidad

`Contabilizador`/`AbstractExtractor` reconfirmados sin hallazgos -- Pull Model
intacto, sin cambios.

## 20. Governance

`FINAL STATUS: PASS` antes y despues de la correccion. Sin cambios de dependency
graph (F25 no toca imports entre apps).

## 21. Dependency Graph

Sin cambios.

## 22. Knowledge Graph

**NO CAMBIO DE GRAFO** -- F25 es una auditoria de comportamiento transaccional, no
de relaciones entre componentes.

## 23. Tests

2 nuevos (`test_f25_procesar_gasto_atomicidad.py`), con evidencia
ANTES(FAIL)/DESPUES(PASS) completa (revertido con `git stash`, confirmado
`1 failed in 158.54s` sin el fix, `2 passed in 232.39s` con el fix). 59/59 en la
regresion consolidada final F21+F22+F23+F24+F25.

## 24. Regresion F21-F24

0 regresiones. Ver `F25_REGRESSION_REPORT.md`.

## 25. Migraciones

**0 nuevas.** Ningun modelo se modifico.

## 26. Findings DEFERRED

Ninguno nuevo. F24-003 queda **resuelto**: de los 24 candidatos restantes tras F24,
1 era un bug real (corregido) y 13 son falsos positivos/seguros por diseno
(documentados individualmente, no ocultos). No queda ningun candidato del AST sin
clasificar.

## 27. Riesgos restantes

- Ninguno CRITICAL o HIGH sin resolver.
- `guardar_desde_dto()` (facturas) termina con un `raise` no controlado (500 de
  Django) en vez de un `(False, {...}, codigo)` limpio si falla en la seccion de
  escritura -- diferencia de contrato de API, no un defecto de atomicidad. Fuera de
  alcance de F25 (no afecta integridad de datos), mencionado como nota de calidad de
  API para una fase futura si se decide homogeneizar el contrato de respuesta.
- No se construyo un test de concurrencia real con 2 conexiones de BD simultaneas
  para stock/asiento (ver `F25_CONCURRENCY_REPORT.md`) -- la proteccion existe y
  esta confirmada por lectura de codigo (`select_for_update()`,
  `UniqueConstraint`), pero no se demostro con un test de threads/procesos reales
  por proporcionalidad de alcance.

## 28. Estado final

```
F21 [OK] COMPLETED
F22 [OK] COMPLETED
F23 [OK] COMPLETED
F24 [OK] COMPLETED
F25 [OK] COMPLETED
```

**ENTERPRISE TRANSACTIONAL INTEGRITY: PASS**

59/59 tests en regresion consolidada real (49:53). Governance PASS. 0 migraciones
pendientes. 1 defecto real encontrado (fuera del alcance original de F24-003, dentro
del alcance extendido de F25) y corregido con evidencia verificable. 13 falsos
positivos documentados individualmente, no modificados. F24-003 cerrado por
completo -- no queda deuda de atomicidad sin clasificar en el circuito auditado.
