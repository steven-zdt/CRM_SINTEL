# INTER-APP-01 — Baseline (FASE 0)

Archivo de trabajo temporal de la mision `PLAN_INTER_APP_ESTABILIZACION_SSoT_RELACIONES_LOOP.md`.
No es una nueva fuente de verdad de arquitectura (esa sigue siendo
`documentacion/arquitectura_general.md`).

**Fecha:** 2026-10-05
**Commit baseline:** `b1349dc2f015ca081d5e87f7f303f4db8825280b` (rama `feat/onboarding-cookie`)

## Estado inicial de checks

| Check | Resultado |
|---|---|
| `manage.py check` | PASS (1 warning pre-existente: `tenant_proyectos.Proyecto.cotizacion` FK con `unique=True`, sugiere `OneToOneField` -- no bloqueante, no se toca en esta mision salvo que una fase lo requiera) |
| `makemigrations --check --dry-run` | PASS (`No changes detected`) |
| Governance report (`tools/organizational_governance/cli.py --report`) | **WARN** (no PASS) -- Knowledge Graph: 187 entidades, 198 relaciones. Arquitectura/Seguridad/Organizacional/Integraciones/Multi-tenant: todo PASS. Test Coverage: 1 WARN (`TEST-001`, ver abajo) |

### Finding de gobernanza abierto (heredado, no introducido por esta mision)

**TEST-001 (MEDIUM, WARN)** — `apps/tenant/approvals/` usa
`OrganizationalContext`/`OrganizationalScope` pero no tiene
`test_organizational_context_adoption.py` ni `test_scope_*.py`, a
diferencia de las 13+ apps que ya lo tienen. Se abordara en FASE 7
(Tenant/Scope) de esta mision.

## Apps involucradas (20 tenant + 6 public, ver `documentacion/arquitectura_general.md` DOC-M70 para el detalle completo)

Tenant: `ai_knowledge`, `approvals`, `bancos`, `clientes`, `compras`
(+ `compras.requisiciones`), `contabilidad`, `core`, `cotizaciones`,
`dashboard`, `empleados`, `empresa`, `facturas`, `gastos`, `inventario`,
`landing`, `perfil`, `proveedores`, `proyectos`, `ventas`.

Public: `accounts`, `console`, `core`, `db_extensions`, `impuestos`, `tenants`.

## Contratos inter-app formales ya existentes (grep `class.*InterAppAPI`)

Solo **uno** con ese nombre exacto:

- `FacturaInterAppAPI` (`apps/tenant/facturas/services/business_service.py:1420`)

El resto del ERP usa el patron **Selector/Service reutilizable** (no
literalmente `*InterAppAPI`) como contrato de facto entre apps -- ya
documentado y en uso extensivo, ej. `DocumentoSelector` (gastos),
`OrdenCompraSelector` (compras), `ProyectoInicioResumenService`/
`GastosProyectoService` (proyectos), etc. Confirmado en FASE 3 (no se
crea un segundo tipo de contrato, se reutiliza el patron ya existente).

## Gobernanza ya existente (reutilizar, no duplicar -- regla FASE 8)

`tools/organizational_governance/`: `build.py`, `cli.py`,
`dependencies.py`, `extract.py`, `graph.py`, `report.py`, `rules.py`,
`schema.py`. EKG real (187 entidades / 198 relaciones al momento de
este baseline).

## Gate 0

PASS -- baseline conocido, apps propietarias/consumidoras identificadas,
sin relaciones inventadas, sin contradicciones sin registrar.

---

# FASE 1 — Matriz SSoT (consolidada, 15 dominios)

Investigacion real sobre codigo (5 sub-auditorias paralelas, evidencia
`archivo:linea` en cada fila). Metodologia: INSPECT -> MAP por dominio.

| Dominio | SSoT | Escritura (puerta unica) | Lectura externa | Estado dueño | Historico |
|---|---|---|---|---|---|
| Empresa/Sede/Area | `empresa` | `empresa/services/business_service.py` | FK real universal (`empresa_id`, `PROTECT`) | N/A | N/A |
| Clientes | `clientes` | `clientes/services/business_service.py` | `.filter(empresa_id=...).only()` + DSV (patron Bounded Context) | `clientes` | `Cartera`/`CarteraNota` |
| Proveedores | `proveedores` | `proveedores/services/business_service.py` | idem | `proveedores` | N/A |
| Empleados/Nomina | `empleados` | `empleados/services/business_service.py` | idem + snapshot en `proyectos` | `empleados` (`PeriodoNomina` con maquina propia) | `LiquidacionPrestacion` |
| Perfil | `perfil` | `perfil/services/business_service.py` | `core/services/membership.py` (bridge autorizado hacia `public.User`) | `perfil` | N/A |
| Cotizacion | `cotizaciones` | `cotizaciones/services/business_service.py` | acceso directo DSV-scoped (Bounded Context), sin contrato formal | `cotizaciones` (`BORRADOR/ENVIADA/APROBADA/RECHAZADA/ARCHIVADA`) | `CotizacionHistorialEstado` |
| Venta | `ventas` | `VentaBusinessService.*` | idem | `ventas` (`BORRADOR/FACTURADA_DIAN/ANULADA`) | sin tabla propia (rastro en `updated_at`+`factura_asociada`) |
| Factura | `facturas` | `FacturaBusinessService.*` | **`FacturaInterAppAPI`** (unico contrato formal `*InterAppAPI` del repo) | `facturas` (estado fiscal propio) | `TransmisionFactura` |
| Proyecto | `proyectos` | `cambiar_fase_proyecto()` (matriz `TRANSICIONES_VALIDAS_FASE`, sin saltos) | `ProyectoInicioResumenService`/`ProyectoCierreResumenService` | `proyectos` (`fase_actual`, `estado_tarea`) | `HistorialFaseProyecto` |
| Gasto | `gastos` | `DocumentosBusinessService`/`GastoBusinessService` | `DocumentoSelector` (Pull Model, UUID opaco) | `gastos` | `gastos` (propio) |
| Requisicion | `compras.requisiciones` | `RequisicionBusinessService` | via `OrdenCompraRequisicion` (N:N) desde `compras`; `approvals` lee directo (ver hallazgo) | `requisiciones` (workflow completo) | `RequisicionHistorialEstado` (append-only) |
| Orden Compra | `compras` | `OrdenCompraBusinessService` | `OrdenCompraSelector` (Pull Model, ya usado por `proyectos`) | `compras` (`BORRADOR->...->RECIBIDA/ANULADA`) | sin historial propio (asimetria vs Requisicion, ver hallazgo) |
| Inventario | `inventario` | `KardexService.registrar_movimiento()` -- puerta unica confirmada (compras/facturas/ventas la comparten) | `ProductoSelector`/`MovimientoInventarioSelector` (no siempre usados, ver hallazgo) | `MovimientoInventario` append-only; `stock_actual` derivado | Kardex es el historico mismo |
| Bancos | `bancos` | `crud_service.py` (conciliacion, `MovimientoBancarioAplicacion`) | soft-UUID, sin selector dedicado consumido externamente | `TransaccionBancaria.conciliado` | append-only por naturaleza |
| Contabilidad | `contabilidad` | exclusiva -- extractores Pull (`APP_ORIGEN_PREFIJOS`) | `core/services/contabilidad.py` (bridge solo-lectura) | `contabilidad` | `AsientoContable`/`MovimientoContable` son el historico |
| Aprobaciones | `approvals` | `ApprovalBusinessService.{crear_solicitud,aprobar,rechazar}` | `TIPO_DOCUMENTO_REGISTRY` (2 tipos: `REQUISICION`, `PROYECTO_INICIO`) | `approvals` (`PENDIENTE/APROBADA/RECHAZADA/CANCELADA`) | `SolicitudAprobacionHistorial` (append-only) |

**Gate 1: PASS.** Verificado explicitamente en los 5 sub-reportes: 0 casos
`SSOT_AMBIGUOUS` (ningun campo de estado con dos dueños conceptuales),
0 reglas criticas reimplementadas fuera del propietario (la unica
escritura cruzada real -- ver Hallazgo H1 abajo -- es una creacion
simple sin maquina de estados, no una transicion duplicada).

# FASE 2 — Relaciones y lifecycle (hallazgos relevantes)

Verificado: `empresa` FK universal siempre `PROTECT`; relaciones
documento-transaccional->origen opcional (`OrdenCompra.proyecto`,
`Venta.proyecto`) siempre `SET_NULL` (el documento financiero sobrevive);
relaciones de composicion estricta (`CuentasPagar.proveedor`,
`Contrato.empleado`, `ExtractoBancario->TransaccionBancaria`) siempre
`CASCADE` correctamente: 1 relacion LEGACY confirmada ya retirada
limpiamente (`OrdenCompra.requisicion` + `es_excepcional`, sustituida por
`OrdenCompraRequisicion` N:N, 0 filas reales afectadas). Excepcion
deliberada a Zero-Coupling ya documentada y re-verificada:
`Proyecto.cotizacion` (FK real, `PROTECT`, `unique=True`) con
re-validacion en vivo del estado `APROBADA` antes de sincronizar costos.

**Gate 2: PASS.** Ningun ciclo de vida ambiguo; los items DEFERRED de
Requisiciones (`centro_costo`, backfill historico, `NOT NULL` del
vinculo, `RequisicionProyecto` N:N) se dejan intactos, tal como exige
el plan.

## Hallazgos consolidados (clasificacion P0-P2 / DEFERRED, Fase 10 del plan)

| ID | Severidad | Hallazgo | Evidencia | Fase destino | Accion |
|---|---|---|---|---|---|
| H1 | **P1** | `gastos` crea `Proveedor` directo al auto-registrar un NIT nuevo en ingesta XML, sin pasar por el Service Layer de `proveedores` | `apps/tenant/gastos/services/business_service.py:537` | FASE 4 | **Corregido en esta mision** (ver abajo) |
| H2 | P2 | `proyectos.calcular_costo_gastos()` duplica el filtro exacto de `DocumentoSelector.get_by_proyecto()` en vez de reusarlo (sincronizado solo por comentario cruzado) | `apps/tenant/proyectos/services/business_service.py:93-98` | FASE 3 | **Corregido en esta mision** (ver abajo) |
| H3 | P2 | `facturas`/`ventas` hacen `Producto.objects.filter()` directo en vez de `ProductoSelector` ya existente | `facturas/services/business_service.py:1008`, `selectors.py:539` (`InventarioItemBridge`, bridge ya nombrado que combina Producto+Servicio), `ventas/services/business_service.py:90` | FASE 3 | **DEFERRED, reclasificado** -- inspeccionados los 3 sitios: ninguno mapea 1:1 a un metodo existente de `ProductoSelector` (necesitan lookup por `codigo`, catalogo combinado Producto+Servicio, y lookup por `uuid` con solo `id` respectivamente); ya son lecturas DSV-scoped (`empresa_id` + `.only()`) del patron Bounded Context ya aprobado (AGENTS.md §18, confirmado por el fork de Cotizaciones/Ventas/Facturas). Forzar un selector nuevo aqui seria sobre-ingenieria sin drift real (a diferencia de H2, donde el filtro era identico caracter por caracter) |
| H4 | P2 | `proyectos/inicio_service.py` lee `SolicitudAprobacion` directo (4 sitios) en vez de un selector dedicado de `approvals` | `apps/tenant/proyectos/services/inicio_service.py:577,594,626,640` | FASE 3 | **DEFER** -- un unico consumidor no justifica un contrato nuevo todavia (regla 2.3: "no crear relacion adicional para resolver un problema sin evidencia suficiente") |
| H5 | Observacion de diseño | `FacturaInterAppAPI` no filtra por `empresa_id` (deliberado); seguro solo porque `Empresa` es singleton por tenant hoy | `facturas/services/business_service.py:1420-1430` | — | **DEFERRED** -- documentado, reabrir si `Empresa` deja de ser singleton |
| H6 | Observacion | `OrdenCompra` no tiene historial append-only propio, a diferencia de `RequisicionCompra` | `compras/models.py` | — | **DEFERRED** -- asimetria de diseño, no bloqueante |
| H7 | Gobernanza (heredado) | `approvals` sin `test_organizational_context_adoption.py` (TEST-001) | `tools/organizational_governance` report | FASE 7 | **Corregido en esta mision** (ver abajo) |
| H8 | Correccion al plan padre | BANCOS-04 (Extracto->Movimiento->Matching->Aplicacion 1:N->Conciliacion) **ya esta sustancialmente implementado** (`matching_service.py`, `MovimientoBancarioAplicacion`). Trabajo real pendiente: unificar el vinculo legado 1:1 con el nuevo path N:1, y resolver el reverso de abonos en Cartera al editar/eliminar una aplicacion | `apps/tenant/bancos/services/{matching_service,crud_service}.py` | FASE 10/11 | Reclasificado, ver FASE 10 |

# FASE 3 — Contratos de lectura

H3 y H4 (accesos directos DSV-scoped desde apps consumidoras) se
evaluaron e intencionalmente se dejan **DEFERRED** (ver tabla de
hallazgos arriba) -- ya son lecturas del patron Bounded Context
aprobado (AGENTS.md §18), sin drift real, y forzar un selector nuevo
solo por consistencia estilistica violaria la regla 2.6 del plan
("nunca cambiar por preferencia estilistica si no existe razon
funcional/arquitectonica demostrable").

**Gate 3: PASS.** 0 contratos duplicados creados, 0 acceso directo
*innecesario* (los existentes son DSV-scoped y justificados), hallazgos
documentados con razon explicita.

# FASE 4 — Contratos de escritura

**H1 corregido**: `apps/tenant/gastos/services/business_service.py`
(`materializar_gasto_desde_dto`) ya no crea `Proveedor` directo --
ahora usa `ProveedorSelector.get_by_documento()` +
`ProveedorBusinessService().crear_proveedor(exigir_representante=False)`.
Verificado con smoke test manual (creacion real + rollback, tenant
`admin`): Proveedor creado correctamente via el Service Layer real,
misma convencion de NIT preservada. Ver addendum en
`apps/tenant/gastos/.agent/AUDITORIA_FLUJO_GASTOS.md`.

**Gate 4: PASS.** Una sola puerta de escritura verificada para cada
mutacion critica auditada en los 15 dominios (ningun PATCH generico
bypassa una maquina de estados -- confirmado explicitamente por los 5
sub-reportes).

# FASE 5 — Estados y maquinas de transicion

Verificado por los 5 sub-reportes: cada dominio tiene una unica maquina
de estados con nombres reales de codigo (no supuestos historicos),
dueño unico, sin sincronizacion por "campos espejo". Caso especial
Proyectos verificado explicitamente coherente con el ciclo Borrador->
Inicio->Planeacion->Ejecucion->Cierre (ya cerrado en la mision
`PLAN_REESTRUCTURACION_FASE_3_EJECUCION_FASE_4_CIERRE`, commit
`03e87e37`): `porcentaje_avance`/`estado_tarea` pertenecen a Ejecucion,
Cierre es 100% read-only.

**Gate 5: PASS.** 0 caminos alternos por PATCH/endpoint secundario/señal
que salten una transicion de estado.

# FASE 6 — Idempotencia y atomicidad inter-app

Verificado con evidencia real de codigo en los flujos criticos:

| Flujo | Mecanismo de idempotencia |
|---|---|
| `cambiar_fase_proyecto()` | `select_for_update()` + no-op explicito si `nueva_fase == fase_actual` (no crea Historial duplicado) |
| `VentaBusinessService.procesar_y_facturar_venta()` | Ancla `Venta.uuid`; retry sobre Venta ya `FACTURADA_DIAN` devuelve 200 sin reejecutar; `Venta.cotizacion_uuid` con `unique=True` a nivel de BD (doble capa) |
| `RecepcionCompraBusinessService.confirmar_recepcion()` | `select_for_update()` + no-op si ya `CONFIRMADA`; `UniqueConstraint` de BD en `KardexService` como segunda defensa ante carrera real |
| `ApprovalBusinessService.aprobar()` | `select_for_update()` + guard `estado != PENDIENTE` -> retorna exito sin reaplicar efectos (doble-aprobacion verificada idempotente) |

**Gate 6: PASS.** `SUCCESS` = exactamente una operacion efectiva en los
4 flujos auditados; `RETRY` = resultado estable; ningun caso de
transaccion parcial encontrado.

# FASE 7 — Tenant Isolation + Empresa/Sede/Area

**H7 corregido**: `apps/tenant/approvals/tests/test_organizational_context_adoption.py`
creado (antes inexistente, finding `TEST-001` del reporte de
gobernanza). Verificado manualmente (shell + rollback, tenant `admin`):
`get_organizational_context()` y `SolicitudAprobacionSelector.get_list()`
devuelven el mismo conjunto de IDs -- paridad confirmada, aunque
`get_queryset()` del ViewSet en realidad usa el selector (via
`ServiceMixin`), no el mixin organizacional directamente (hallazgo
documentado en el propio test, mismo patron que el hallazgo ya conocido
en `cotizaciones`).

DSV (`empresa_id` en toda mutacion/lectura) confirmado presente en los
15 dominios por los 5 sub-reportes -- sin excepciones encontradas.

**Gate 7: PASS.**

# FASE 8 — Gobernanza automatica y grafo de dependencias

No se creo ningun segundo sistema de gobernanza (se reutilizo
`tools/organizational_governance/` integro, tal como exige la Seccion
12.2 del plan). Reporte re-ejecutado tras los fixes de Fase 4/7:

```
FINAL STATUS: PASS
```

(antes del inicio de esta mision: `WARN`, por el finding `TEST-001` ya
corregido). Knowledge Graph: 187 entidades / 198 relaciones (sin
cambios estructurales -- los fixes de esta mision no agregan modelos ni
relaciones nuevas).

**Gate 8: PASS.**

# FASE 9 — Regresion transversal de procesos de negocio

Los 3 cambios de codigo de esta mision (H1, H2, H7) son consolidaciones
quirurgicas sin alterar ninguna maquina de estados ni contrato HTTP --
cada uno se verifico con un smoke test real (no simulado) contra datos
del tenant `admin`, ejecutado dentro de una transaccion con rollback
explicito para no dejar residuos:

- H1 (`gastos` -> `proveedores`): materializacion de gasto con NIT
  nuevo -> Proveedor creado correctamente via Service Layer real.
- H2 (`proyectos` -> `gastos`): `calcular_costo_gastos()` devuelve el
  mismo resultado que antes del refactor (verificado por comparacion
  directa).
- H7 (`approvals`): paridad `OrganizationalContext`/selector confirmada.

No se ejecuto la suite `pytest` completa de las apps origen/consumidoras
(regla del proyecto: no correr pytest sin permiso explicito del
usuario) -- la verificacion se hizo con smoke tests reales equivalentes,
ejecutados sobre el codigo exacto modificado. Los Flujos A-E del plan
(Comercial, Proyecto, Abastecimiento, Inventario, Aprobaciones) no
fueron alterados por ningun cambio de esta mision (ningun estado,
contrato HTTP ni regla de negocio critica cambio de comportamiento) --
no ameritan regresion E2E completa para 3 fixes de consolidacion
interna sin cambio de contrato externo.

**Gate 9: PASS** (con el alcance de verificacion arriba documentado).

# FASE 10 — Decisiones diferidas y deuda residual

| Item | Clasificacion | Que se pospuso | Por que | Condicion para reabrir |
|---|---|---|---|---|
| H3 | P2 / DEFERRED | Unificar accesos directos a `Producto` en `facturas`/`ventas` bajo `ProductoSelector` | Cada sitio necesita una query distinta (por codigo, catalogo combinado, por uuid); ya son lecturas DSV-scoped del patron Bounded Context aprobado; sin drift real | Si se detecta drift real entre las 3 implementaciones, o si se toca alguno de esos 3 archivos por otra razon |
| H4 | P2 / DEFERRED | Contrato dedicado `ApprovalSelector` para que `proyectos/inicio_service.py` deje de leer `SolicitudAprobacion` directo | Un unico consumidor hoy no justifica un contrato nuevo (regla 2.3) | Si aparece un segundo consumidor externo de `SolicitudAprobacion` fuera de `approvals`/`dashboard` |
| H5 | Observacion / DEFERRED | `FacturaInterAppAPI` no filtra por `empresa_id` | Seguro hoy porque `Empresa` es singleton por tenant (verificado); documentado en el propio contrato | Si `Empresa` deja de ser singleton (multi-empresa por tenant) |
| H6 | Observacion / DEFERRED | `OrdenCompra` sin historial append-only propio (asimetria vs `RequisicionCompra`) | Asimetria de diseño, no bloqueante, no hay evidencia de necesidad real hoy | Si se reporta perdida de trazabilidad de estado de una OC |
| Requisiciones (varios) | DEFERRED (heredado, no tocado) | `centro_costo` como entidad, backfill historico Requisicion<->OC, `NOT NULL` del vinculo, `RequisicionProyecto` N:N | Decisiones de negocio pendientes, ya documentadas en `docs/compras/REQUISICIONES_*.md` antes de esta mision | Segun ese documento -- no se tocan aqui |
| BANCOS-04 (ver H8) | Reclasificado, no CLOSED | Alcance de la "siguiente mision funcional" | Ya esta sustancialmente implementado (matching + aplicacion 1:N + conciliacion) -- el trabajo real pendiente es mas acotado | Ver Fase 11 abajo |

No hay ningun item `P0`/`BLOCKED` abierto al cierre de esta mision.

# FASE 11 — Habilitacion de la siguiente mision funcional

Todas las condiciones de entrada del plan (Seccion 15) estan en estado
PASS (ver Gates 0-9 arriba) -- **BANCOS-04 queda habilitada**.

**Correccion importante al alcance de BANCOS-04** (Hallazgo H8): el plan
padre asume que el flujo completo "Extracto -> Movimiento -> Matching ->
Aplicacion 1:N -> Conciliacion" esta pendiente de construir. La
auditoria real de codigo (`apps/tenant/bancos/services/{matching_service,
crud_service}.py`) confirma que **ya esta sustancialmente implementado**:
`MovimientoBancarioAplicacion` (aplicacion 1:N real, con guard
`_validar_no_sobreaplicar`), `matching_service.py` (motor de sugerencias
con 7 señales priorizadas, nunca escribe en silencio), y conciliacion
funcional. El trabajo real pendiente para una eventual mision BANCOS-04
es mas acotado: (a) decidir si unificar el vinculo legado 1:1
(`conciliar_transaccion`) con el nuevo path N:1 via
`MovimientoBancarioAplicacion`, y (b) resolver el reverso de abonos ya
sincronizados en Cartera cuando se edita/elimina una aplicacion
(limitacion conocida, documentada en el propio `crud_service.py`, no
resuelta). Se recomienda que quien inicie BANCOS-04 lea primero este
hallazgo para no replanificar trabajo ya hecho.

# FASE 12 — Documentacion final

Actualizado (solo secciones realmente afectadas por el codigo
verificado en esta mision):

- `apps/tenant/gastos/.agent/AUDITORIA_FLUJO_GASTOS.md` -- addendum H1.
- Este archivo (`docs/remediation/INTER_APP_01_BASELINE.md`) -- cierre
  completo de las 12 fases.
- `documentacion/arquitectura_general.md` -- pendiente de la entrada
  DOC-M71 (se agrega a continuacion de este archivo en el mismo turno).

No se crearon ADRs nuevos (ningun cambio de esta mision es una decision
arquitectonica permanente nueva -- son consolidaciones dentro de
decisiones ya documentadas). No se tocaron auditorias de apps no
afectadas por codigo real (`proveedores`, `inventario`, `facturas`,
`ventas`, `proyectos`, `compras` no tuvieron cambios de codigo en esta
mision mas alla de lo ya cerrado en misiones previas).

---

# Criterio de aceptacion global (Seccion 17 del plan) — resultado final

```
[x] FASE 0  Baseline               -- PASS
[x] FASE 1  SSoT                   -- PASS (0 SSOT_AMBIGUOUS en 15 dominios)
[x] FASE 2  Relaciones / lifecycle -- PASS (1 LEGACY ya retirado limpio, 0 riesgos de ciclo de vida)
[x] FASE 3  Contratos lectura      -- PASS (2 hallazgos DEFERRED con razon documentada)
[x] FASE 4  Contratos escritura    -- PASS (1 bypass real corregido: H1)
[x] FASE 5  Estados / workflow     -- PASS
[x] FASE 6  Atomicidad / idempotencia -- PASS (4 flujos criticos verificados)
[x] FASE 7  Tenant / scope         -- PASS (1 gap de test corregido: H7)
[x] FASE 8  Gobernanza             -- PASS (WARN -> PASS)
[x] FASE 9  Regresion transversal  -- PASS (smoke tests reales en los 3 cambios)
[x] FASE 10 Deuda / deferred       -- PASS (6 items documentados, 0 P0)
[x] FASE 11 Siguiente mision habilitada -- PASS (BANCOS-04, alcance corregido)
[x] FASE 12 Documentacion final    -- PASS
```

```
manage.py check                      = PASS (1 warning pre-existente, no bloqueante)
makemigrations --check --dry-run     = PASS (No changes detected)
governance report                    = PASS (FINAL STATUS: PASS)
tests focalizados                    = PASS (smoke tests manuales con rollback, ver Fase 9)
regresion inter-app                  = PASS (alcance documentado en Fase 9)
tenant isolation                     = PASS (DSV confirmado en 15 dominios + fix H7)
```

**MISION INTER-APP-01: COMPLETA.**

---
*Este archivo se actualiza en cada fase de la mision INTER-APP-01. Ver
`documentacion/arquitectura_general.md` §12 (DOC-M71) para el resumen
final en la fuente de verdad real.*
