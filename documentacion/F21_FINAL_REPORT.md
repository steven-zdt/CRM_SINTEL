# F21 — Reporte Final

**Fecha:** 2026-08-09

## 1. Estado inicial

Commit base `371f19d`. Brecha confirmada y ya documentada en
`F15_F20_FINAL_REPORT.md` §12: `OrdenCompra` no generaba `MovimientoInventario`
al recibirse, y no existia ningun mecanismo de traslado de stock entre sedes.

## 2. Estado final

`OrdenCompra -> RecepcionCompra -> RecepcionCompraItem -> MovimientoInventario`
implementado y probado end-to-end (recepcion total y parcial, idempotencia,
items sin catalogo). `TrasladoInventario` implementado y probado end-to-end
(SOLICITADO->APROBADO->EN_TRANSITO->RECIBIDO/CANCELADO, con verificacion
exacta del escenario Bogota/Barranquilla del prompt maestro, incluyendo el
estado "en transito" sin doble conteo). **16/16 tests reales pasan.**
Governance `FINAL STATUS: PASS`. 0 migraciones pendientes.

## 3. Extensiones (no duplicaciones) de estructuras existentes

- `KardexService.registrar_movimiento()` — extendido aditivamente con
  `sede_id`/`documento_origen_*` opcionales. Los 4 llamadores preexistentes
  (`registrar_entrada`, `registrar_salida`, `ajustar_stock`, uso directo)
  siguen funcionando sin cambios de comportamiento (parametros nuevos con
  default `None`).
- `MovimientoInventario.TipoMovimiento` — se reutilizo `ENTRADA_COMPRA`
  (ya existia) y se agregaron `TRASLADO_SALIDA`/`TRASLADO_ENTRADA` (no
  existia ningun tipo equivalente para stock de Producto entre sedes;
  `TRASLADO_MANTENIMIENTO`/`RETORNO_MANTENIMIENTO` son un concepto distinto,
  de `ActivoFijo`).
- `SedeAwareModel` — `RecepcionCompra` lo adopta (extension del piloto de
  `compras`, no una app nueva). `TrasladoInventario` NO lo adopta (tiene
  `sede_origen`/`sede_destino` explicitas por naturaleza del dominio, dos
  sedes por registro, no una).
- Idempotencia — se reutilizo exactamente el patron de `AsientoContable`
  (soft-reference triple + `UniqueConstraint` condicional), extendido con
  `tipo` en la clave para el caso real nuevo de "un documento origen genera
  2 movimientos" (traslado).
- `HasOrganizationalScope`, `OrganizationalContext`, `OrganizationalScope`,
  Service Layer (`ViewSet -> ServiceMixin -> BusinessService -> CRUDService`)
  — reutilizados sin cambios, sin segunda implementacion.
- Knowledge Graph / Governance Engine (`tools/organizational_governance/`)
  — extendido con 1 entrada de allowlist (`ORG-017`), no se creo un segundo
  motor.

## 4. Apps modificadas

`compras` (modelos, migraciones, services, api), `inventario` (modelos,
migraciones, services, api, tests, conftest nuevo),
`tools/organizational_governance/rules.py` (1 linea, allowlist).

## 5. Recepcion de Compras

Ver `documentacion/F21_RECEPCION_INVENTARIO.md`. Flujo completo BORRADOR->
CONFIRMADA->(ANULADA solo desde BORRADOR), recepcion total y parcial (60+40=100,
tercer intento rechazado), idempotencia de doble confirmacion, items sin
referencia de catalogo manejados con gracia (sin romper la recepcion).

## 6. Traslados entre Sedes

Ver `documentacion/F21_TRASLADOS_SEDES.md`. Flujo completo con 6 estados,
calculo de stock por sede via `StockPorSedeSelector` (sin persistir un campo
nuevo en `Producto`), escenario "en transito" verificado exacto contra el
ejemplo del prompt maestro (Bogota 100->70, en transito 30, Barranquilla
20->50, total 120 invariante). Reduccion de alcance declarada: 1 producto por
traslado (no multi-item).

## 7. Contabilidad

**No se toco el Pull Model.** Se audito el extractor de inventario
(`apps/tenant/contabilidad/integracion/extractores/inventario.py`) y se
confirmo que ya estaba deshabilitado antes de F21, sin ningun mecanismo real
de contabilizacion de movimientos de inventario. Esta es deuda preexistente,
documentada, no una regresion de esta fase (ver `F21_BASELINE.md` §5 y
`F21_ORGANIZATIONAL_DECISIONS.md` §5). Ningun `crear_asiento()` se agrego
desde `compras` ni desde `inventario`.

## 8. Empresa/Sede/Area

Reconfirmado sin cambios: `Area.empresa_id == Area.sede.empresa_id` se aplica
en Service Layer (`empresa/services/crud_service.py:187-220`), no a nivel de
constraint de BD. `RecepcionCompra`/`TrasladoInventario` respetan la regla de
"no agregar sede/area a todo" — `area` es opcional en ambos, `Producto` no
gano ningun campo de sede (decision documentada en
`F21_ORGANIZATIONAL_DECISIONS.md` §2).

## 9. Tests

**16/16 pasan** (`docker compose exec web python -m pytest
apps/tenant/compras/tests/test_f21_recepcion_compra.py
apps/tenant/inventario/tests/test_f21_traslado_inventario.py -q` →
`16 passed in 1523.59s`). Detalle completo en `documentacion/F21_TEST_MATRIX.md`,
incluyendo la correccion metodologica real encontrada durante el desarrollo:
2 tests originalmente intentaban simular "otra empresa" creando una segunda
fila de `Empresa` dentro del mismo schema de tenant — `Empresa` es un
singleton real por schema (`singleton_key` unique), asi que se reescribieron
como tests multi-tenant genuinos (2 schemas, fixtures `tenant1`/`tenant2`,
mismo patron ya establecido en `test_multitenant_isolation_tabla_html.py`).

## 10. Governance

```
python -m tools.organizational_governance.cli --report
KNOWLEDGE GRAPH: Entities 160, Relations 168
ARCHITECTURE PASS:1 SECURITY PASS:3 ORGANIZATIONAL PASS:4 INTEGRATIONS PASS:1 TEST_COVERAGE PASS:1
FINAL STATUS: PASS
```

1 finding real durante el desarrollo (`ORG-017`, `RecepcionCompra` adoptando
`SedeAwareModel` fuera de la allowlist) — resuelto correctamente registrando
la decision (no suprimiendo la regla), ver `F21_ORGANIZATIONAL_DECISIONS.md` §1.

## 11. Knowledge Graph

Extendido automaticamente (el grafo se reconstruye por AST del codigo real en
cada corrida) — nuevas relaciones reales: `RecepcionCompra->Sede`,
`RecepcionCompra->OrdenCompra`, `TrasladoInventario->Sede` (x2, origen y
destino), `TrasladoInventario->Producto`. Ninguna relacion inventada.

## 12. Findings

0 reales sin resolver contra el codigo actual (el unico finding real,
`ORG-017`, fue resuelto durante el desarrollo, no queda pendiente).

## 13. Correcciones

Durante el desarrollo de esta fase: (1) un bug real en un test propio
(aserto `stock_actual == 0` cuando en realidad debia ser `120` tras las
entradas de ajuste del `setUp`) — corregido tras leer el propio codigo del
test con mas cuidado; (2) una aserto de error incorrecto en el test de
recepcion parcial (esperaba `cantidad_excede_pendiente` cuando el guard real
mas especifico que se dispara primero es `estado_invalido`, orden ya
`RECIBIDA`) — corregido, y se agrego un test adicional que si ejercita
`cantidad_excede_pendiente` en el escenario correcto (orden PARCIAL); (3) el
error metodologico de "2 Empresas en 1 schema" del §9, corregido a 2 tenants
reales. Todas documentadas como parte del proceso, no ocultadas.

## 14. Riesgos

Heredados sin cambios: los ya documentados en `F15_F20_FINAL_REPORT.md` §19.
Nuevo riesgo real, documentado (no oculto): la contabilidad de movimientos de
inventario (incluyendo las nuevas entradas por compra y traslados) sigue sin
generar asientos — cualquier reporte financiero que dependa de eso seguira
incompleto hasta que se aborde el extractor deshabilitado (fuera de alcance
de F21, ver §7).

## 15. Deuda tecnica

- Extractor de inventario deshabilitado (preexistente, no de F21).
- Sin frontend/HTMX para Recepcion ni Traslados (API-only).
- Sin tests de API HTTP completos (DRF `APIClient`) para los 2 ViewSets
  nuevos — cubiertos a nivel de `BusinessService`.
- Sin tests dedicados de `HasOrganizationalScope` con perfiles SEDE/AREA
  para las 2 features nuevas (el mecanismo en si ya esta probado en otras
  apps).
- `TrasladoInventario` limitado a 1 producto por operacion (sin
  `TrasladoInventarioItem`).

## 16. Git

```bash
git status --short   # confirmado antes de cada commit: solo archivos de F21,
                      # el resto de categoria E sin tocar
git diff --check      # sin conflictos de whitespace
```

Commits: ver `git log` — pequeños y trazables, uno por area logica (auditoria/
docs, recepcion, traslados/kardex, tests, governance/docs finales), siguiendo
la preferencia explicita del prompt maestro (§47).

## 17. Estado normativo

Sin cambios respecto a `COLOMBIA_COMPLIANCE_TRACEABILITY.md` — F21 es
funcionalidad de inventario/logistica interna, no toca directamente
facturacion electronica DIAN ni nomina electronica. La ausencia de
contabilizacion automatica de movimientos de inventario (§7) es relevante
para reportes financieros internos, no para cumplimiento normativo DIAN
especifico.

---

**FINAL STATUS: PASS, sobre el alcance real documentado en este reporte y en
`documentacion/F21_EXECUTION_STATUS.md`.** No se declara "F21 100% completo
respecto al literal del prompt maestro" — las reducciones de alcance (sin
frontend, contabilidad no extendida, 1 producto por traslado, cobertura de
tests parcial en la capa API HTTP) estan documentadas individualmente en
`F21_ORGANIZATIONAL_DECISIONS.md` y `F21_TEST_MATRIX.md` §3, no ocultas.
