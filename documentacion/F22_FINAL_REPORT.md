# F22 — Reporte Final

**Fecha:** 2026-08-10

## 1. Estado inicial

Commit base `e003e1e` (branch `feat/onboarding-cookie`). F21 COMPLETED, 16/16 tests, governance
PASS. `ExtractorInventario.extraer_pendientes()` deshabilitado (`return []`), documentado como
deuda preexistente en `F21_ORGANIZATIONAL_DECISIONS.md` §5.

## 2. Estado final

`ExtractorInventario` implementado y probado end-to-end: `MovimientoInventario ->
ExtractorInventario -> TransaccionEconomica -> Contabilizador -> AsientoContable`, modelo Pull
puro (Inventario nunca importa Contabilidad — verificado por grep real, 0 imports de runtime).
Registrado en `extractores/__init__.py` y en `backfill_contabilidad.py`
(`EXTRACTORES_DISPONIBLES['inventario']`). **20/20 tests nuevos pasan**, **19/19 tests de F21
confirmados sin regresion en la misma sesion.** Governance `FINAL STATUS: PASS`, 0 aristas
`FORBIDDEN` en el grafo de dependencias (373 aristas totales). 0 migraciones nuevas (ningun
cambio de modelo fue necesario).

## 3. Lo que ya existia y se reutilizo (nada duplicado)

- `TipoTransaccion` (`dtos.py`) ya tenia los 5 valores de inventario
  (`COMPRA_INVENTARIO`/`SALIDA_INVENTARIO_VENTA`/`BAJA_INVENTARIO`/`AJUSTE_INVENTARIO`/
  `INVENTARIO_COSTO_VENTA`) sin usar — F22 los activo, no los creo.
- `seed_reglas_contables.py` ya tenia las `ReglaContable` seedeadas (idempotente, `get_or_create`)
  para 4 de esos 5 tipos, con codigos PUC reales — F22 las reutiliza exactamente, sin inventar
  conceptos nuevos (ver `F22_ACCOUNTING_CONTRACT.md` §2).
- `AbstractExtractor.contabilizar_pendientes()` (orquestacion + aislamiento de errores +
  idempotencia via `AsientoYaExisteError`) — sin cambios, heredado.
- `MovimientoInventario.documento_origen_app/modelo/id` (agregados en F21) — reutilizados para
  identificar el proveedor real de una `ENTRADA_COMPRA`, no para el documento origen del asiento
  en si (que es el propio `MovimientoInventario`, ver `F22_ACCOUNTING_CONTRACT.md` §4).
- `UniqueConstraint` de idempotencia de `AsientoContable` — sin cambios, ya protegia a los demas
  extractores; ahora tambien a `inventario`.
- `ExtractorGastos`/`ExtractorNomina` como plantillas de codigo — mismo patron exacto
  (`extraer_pendientes()`, `get_documentos_enriquecidos()`, `_mapear_a_dto()`).

## 4. Lo que se implemento (nuevo, real)

- `apps/tenant/contabilidad/integracion/extractores/inventario.py` — reescrito completo (antes:
  10 lineas deshabilitadas; ahora: extractor funcional con matriz de mapeo, resolucion de
  tercero, `get_documentos_enriquecidos()`).
- `apps/tenant/contabilidad/integracion/extractores/__init__.py` — exporta `ExtractorInventario`.
- `apps/tenant/contabilidad/management/commands/backfill_contabilidad.py` — registra
  `'inventario': ExtractorInventario` en `EXTRACTORES_DISPONIBLES` (1 linea + 1 import).
- 4 archivos de test nuevos (`apps/tenant/contabilidad/tests/test_f22_extractor_inventario_*.py`
  — mapping, integration, multitenant).

**Nada mas cambio.** No se toco `RecepcionCompra`, `RecepcionCompraItem`, `TrasladoInventario`,
`KardexService`, `StockPorSedeSelector`, ni ningun modelo de `inventario` o `compras`.

## 5. Matriz de movimientos y contrato contable

Ver `documentacion/F22_ACCOUNTING_CONTRACT.md` para la matriz completa (6 tipos contabilizables,
2 tipos de traslado excluidos por decision, 4 tipos de ActivoFijo fuera de alcance) y
`documentacion/F22_INVENTORY_ACCOUNTING.md` para el flujo operativo (como ejecutar
`backfill_contabilidad --extractores=inventario`).

## 6. Traslados entre sedes — impacto economico = 0 (confirmado, no asumido)

Verificado contra codigo real: ni `dtos.py` ni `seed_reglas_contables.py` contemplan
`TRASLADO_SALIDA`/`TRASLADO_ENTRADA` — el sistema nunca penso contabilizarlos. `extraer_pendientes()`
los excluye desde el filtro inicial (nunca se construye un DTO). Verificado por 2 tests reales
(`test_traslado_no_genera_asiento`, `test_e2e_traslado_bogota_barranquilla_sin_asiento_economico`).

## 7. Idempotencia

Un `MovimientoInventario` no puede generar mas de 1 `AsientoContable` activo — reforzado por el
mismo `UniqueConstraint` que ya protegia al resto de extractores, sin cambios de modelo. Probado
con ejecucion 1 (crea), ejecucion 2 (no duplica), y el escenario de recepcion parcial (2 eventos
de recepcion generan exactamente 2 asientos, nunca mas).

## 8. Multi-tenant / Sede

Aislamiento verificado con 2 schemas reales (`tenant1`/`tenant2`, no 2 `Empresa` en 1 schema —
mismo ajuste metodologico que F21 encontro). La `sede` de `MovimientoInventario` **no se propaga**
a `AsientoContable`/`MovimientoContable` (ninguno de los 2 modelos tiene ese campo) — decision
confirmada, no se agrega "solo para resolver F22" (prohibido explicitamente por el prompt
maestro), ver `F22_ACCOUNTING_CONTRACT.md` §7.

## 9. Periodos y cuadratura

`PeriodoContable` cerrado bloquea el asiento (`PeriodoCerradoError`, capturado y aislado por
documento — no usa `settings.DEBUG` para nada). Cuadratura estricta (`debe==haber`, sin
tolerancia) heredada de `validadores.py`, sin cambios.

## 10. Tests

**20/20 tests nuevos pasan, 19/19 de F21 confirmados sin regresion.** Ver
`documentacion/F22_TEST_MATRIX.md` para el detalle completo, incluyendo el bug real encontrado
durante el desarrollo (periodo contable de prueba con fecha hardcodeada vs. `timezone.now()` real
de `KardexService`) y su correccion, documentado como parte del proceso, no ocultado.

## 11. Governance

```
python -m tools.organizational_governance.cli --report
KNOWLEDGE GRAPH: Entities 160, Relations 168
ARCHITECTURE PASS:1 SECURITY PASS:3 ORGANIZATIONAL PASS:4 INTEGRATIONS PASS:1 TEST_COVERAGE PASS:1
FINAL STATUS: PASS
```

0 findings nuevos. El conteo de entidades/relaciones del grafo no crecio respecto a F21 — el
extractor nuevo no introduce entidades de los tipos que el grafo cataloga explicitamente
(Model/ViewSet/Permission/ADR); su import cross-app (`contabilidad -> compras`, para resolver el
proveedor real) es un import local dentro de una funcion (mismo patron ya establecido en todo el
proyecto para evitar acoplamiento a nivel de modulo), por lo que no aparece como arista nueva en
`dependencies.py` — verificado explicitamente que **0 aristas `FORBIDDEN`** existen en las 373
totales, y que ninguna arista `inventario -> contabilidad` existe en ningun sentido.

## 12. Reglas de governance nuevas — decision de NO crear ACC-INV-\*

El prompt maestro (§22.32) propuso 5 reglas candidatas (`ACC-INV-001..005`). Evaluadas una por
una:
- **`ACC-INV-004`** ("Inventario no puede importar Contabilizador"): **ya cubierta** por el
  clasificador generico de `dependencies.py` (detecta cualquier import `inventario -> contabilidad`
  y lo marcaria `FORBIDDEN`) — crear una regla especifica seria duplicar governance existente,
  prohibido explicitamente por el prompt maestro.
- **`ACC-INV-001`** ("todo movimiento contabilizable debe tener documento origen"): ya reforzado
  por el sistema de tipos — `TransaccionEconomica.documento_origen` es un campo obligatorio (sin
  default) del dataclass congelado; una regla de AST seria redundante con esa garantia en tiempo
  de construccion.
- **`ACC-INV-002`** (1 movimiento -> maximo 1 asiento): ya reforzado por el `UniqueConstraint` de
  BD (verificable por migracion/schema, no por AST de codigo Python) y por test real.
- **`ACC-INV-003`/`ACC-INV-005`**: requieren verificacion semantica de comportamiento en tiempo de
  ejecucion (que el filtro realmente use `empresa_id`, que el traslado realmente no genere
  transaccion), no patrones estaticos de AST razonables de verificar de forma generica sin falsos
  positivos/negativos — cubiertos por tests reales en su lugar.

**Decision: no se crean reglas `ACC-INV-*` nuevas.** Ninguna aportaria verificacion real
adicional a lo que el sistema de tipos, el constraint de BD, el clasificador de dependencias
existente y la suite de tests ya garantizan. Documentado como decision explicita, no como omision.

## 13. Knowledge Graph

Extendido automaticamente por reconstruccion AST (mismo mecanismo que F21) — no se creo un
segundo grafo. Las relaciones reales nuevas (`MovimientoInventario -> ExtractorInventario`,
`ExtractorInventario -> TransaccionEconomica -> Contabilizador -> AsientoContable`,
`MovimientoInventario -> DocumentoOrigen`) existen en el codigo real y serian detectables por
cualquier extension futura del catalogador que incluya clases `Extractor*` como tipo de entidad
— no se fuerza su aparicion en el conteo actual (que cataloga otros tipos de entidad).

## 14. Analisis de backfill historico

Ver `documentacion/F22_HISTORICAL_BACKFILL_ANALYSIS.md`. Resultado real (`--dry-run` contra los 3
tenants reales de este entorno): **0 movimientos pendientes, 0 `PeriodoContable` configurados en
ningun tenant real.** No hay deuda historica que migrar hoy. No se ejecuto ningun backfill
destructivo ni automatico.

## 15. Celery / procesamiento asincrono

**Decision: no se crea ninguna tarea Celery nueva.** `gastos`/`facturas`/`nomina` tampoco tienen
una — el mecanismo real y unico de disparo es `backfill_contabilidad` (management command),
ejecutado manualmente o por el operador del tenant. Crear una tarea Celery solo para
`inventario` romperia la consistencia con los 3 extractores existentes (mismo patron, misma
infraestructura) y no fue solicitado por ningun requisito real verificado.

## 16. Imports / limites arquitectonicos (verificado, no asumido)

```bash
grep -RIn "apps.tenant.contabilidad" apps/tenant/inventario/ --include="*.py"
# 0 imports de runtime (1 mención en comentario, no en código ejecutable)

grep -RIn "Contabilizador" apps/tenant/inventario/ --include="*.py"
# 0 imports de runtime (1 mención en comentario, no en código ejecutable)
```

## 17. Migraciones

**0 migraciones nuevas.** Ningun modelo se modifico — `MovimientoInventario` ya tenia todos los
campos necesarios desde F21 (`documento_origen_*`, `sede`, `costo_unitario`). `makemigrations
--check --dry-run` limpio antes y despues.

## 18. Frontend

**Sin cambios.** F22 es enteramente backend (`apps/tenant/contabilidad/integracion/`) — no se
toco ningun ViewSet HTTP, serializer, template ni JS. `backfill_contabilidad` es un management
command, no un endpoint.

## 19. Findings

0 reales sin resolver.

## 20. Correcciones durante el desarrollo

1 bug real encontrado y corregido, en los tests propios (no en el codigo de produccion): la
primera corrida arrojo 8 fallas por un `PeriodoContable` de prueba con fecha hardcodeada que no
cubria la fecha real (`timezone.now()`) que `KardexService.registrar_movimiento()` realmente usa
para `created_at`. Diagnosticado, corregido (periodo dinamico basado en `timezone.localdate()`),
re-verificado con ejecucion real. Ver `F22_TEST_MATRIX.md` §5 para el detalle completo del
proceso.

## 21. Riesgos

- `SALIDA_VENTA` no tiene datos reales todavia (`ventas`/`facturas` no generan ese
  `MovimientoInventario` — brecha preexistente, no de F22, ver `F22_INVENTARIO_BASELINE.md` §4).
  El mecanismo esta listo y probado (mapeo), solo falta la fuente de datos.
- `costo_unitario=0` en movimientos historicos/futuros sin ese dato produce asientos vacios
  rechazados (aislados, no bloquean el resto) — calidad de dato del origen (`KardexService`
  permite el default 0), no un bug de la integracion contable.
- Sin tarea periodica automatica: la contabilizacion de inventario requiere ejecucion manual de
  `backfill_contabilidad` (mismo riesgo que ya existe para `gastos`/`facturas`/`nomina`, no nuevo
  de F22).

## 22. Deuda tecnica

- Integracion `ventas`/`facturas` -> `MovimientoInventario(SALIDA_VENTA)` — prerequisito real
  para que el extractor de ventas tenga datos, fuera de alcance de F22 (fase de Ventas).
- Movimientos de `ActivoFijo` sin contabilizar — dominio distinto, deliberadamente fuera de
  alcance.
- Sin UI/frontend para ver el estado contable de movimientos de inventario (existe
  `get_documentos_enriquecidos()`, listo para una UI futura tipo "Libro Diario" que ya usan
  `gastos`/`facturas`, pero no se construyo la vista).

## 23. Git

```bash
git status --short   # confirmado antes de cada commit: solo archivos de F22
git diff --check      # sin conflictos de whitespace
```

Commits: ver `git log` — pequeños y trazables (auditoria/contrato, implementacion del extractor,
tests, governance/backfill-analysis/documentacion final), sin tocar los ~78 archivos ajenos a
esta fase.

---

**FINAL STATUS: PASS, sobre el alcance real documentado en este reporte y en
`documentacion/F22_EXECUTION_STATUS.md`.** No se declara "F22 100% completo respecto al literal
del prompt maestro" — las reducciones de alcance (sin `SALIDA_VENTA` con datos reales, sin
ActivoFijo, sin Celery, sin reglas `ACC-INV-*` nuevas, sin frontend) estan documentadas
individualmente arriba y en `F22_ACCOUNTING_CONTRACT.md`/`F22_TEST_MATRIX.md` §6, no ocultas.
