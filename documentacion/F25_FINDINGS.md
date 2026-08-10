# F25 — Hallazgos

**Fecha:** 2026-08-10

Metodologia: reproduccion del escaneo AST de F24-003 (`@transaction.atomic` + `except`
que retorna sin `raise` ni `transaction.set_rollback(True)`), extendido a
`inventario/contabilidad/clientes/proveedores/gastos/empleados/cotizaciones/proyectos`
por instrucción del prompt maestro F25 §9. Resultado: **30 except-blocks** en
**16 metodos**, distribuidos en `compras` (13, 5 metodos), `facturas` (5, 1 metodo),
`ventas` (9, 5 metodos) y **gastos** (3, 3 metodos -- hallazgo nuevo de esta fase, no
contemplado en el conteo original de F24-003 que solo cubria compras/ventas/facturas).

Cada metodo se clasifico leyendo su codigo real (no solo el patron AST) para
determinar si existe un escenario **write -> write -> error -> commit parcial**, o si
el (los) `except` son estructuralmente inalcanzables por esa clase de bug.

**Regla de clasificacion aplicada:** un metodo es vulnerable solo si realiza **2 o
mas escrituras reales separadas** (ya sea directas o via llamadas a otros metodos
`@transaction.atomic`, que actuan como savepoints independientes) donde una escritura
anterior puede quedar ya liberada/fusionada a la transaccion antes de que una
posterior falle. Un metodo cuya UNICA escritura es una sola llamada a otro metodo
`@transaction.atomic` es seguro por diseño: el savepoint de esa llamada se revierte
automaticamente si algo falla dentro de ella, sin importar que el `except` externo no
relance la excepcion.

---

## F25-001 — `GastoBusinessService.procesar_gasto()`: atomicidad rota (REAL BUG)

- **Severidad:** HIGH
- **App:** gastos
- **Archivo:** `apps/tenant/gastos/services/business_service.py`
- **Metodo:** `procesar_gasto()` (linea 101-240 antes de la correccion)
- **Descripcion:** Mismo patron que F23 (ventas) y F24 (compras): decorado
  `@transaction.atomic`, crea el `DocumentoSoporte` (linea 206) y luego un loop sobre
  `RETEFUENTE/RETEICA/RETEIVA` llamando `RetencionesService.crear_retencion()` (linea
  212) por cada porcentaje configurado > 0. **`crear_retencion()` NO esta decorado
  `@transaction.atomic`** -- es una escritura cruda (`retencion.save()`) directamente
  en la transaccion externa de `procesar_gasto()`, sin savepoint propio. Si la
  retencion N (N>1) falla despues de que la retencion N-1 ya se creo, los 3 `except`
  (`ValidationError`, `DjangoValidationError`, `Exception`) capturaban la excepcion y
  retornaban `(False, ..., codigo)` sin relanzar ni forzar
  `transaction.set_rollback(True)`.
- **Escenario:** Proveedor con RETEFUENTE y RETEICA configurados. `procesar_gasto()`
  crea el `DocumentoSoporte`, crea la retencion RETEFUENTE exitosamente, y la
  creacion de la retencion RETEICA falla. Antes del fix: el `DocumentoSoporte` y la
  retencion RETEFUENTE quedaban comprometidos (commit) pese a `ok=False`.
- **Impacto:** Corrompe datos fiscales/contables: un gasto con retenciones
  incompletas es mas grave que un gasto inexistente (subestima retenciones
  declarables), y el usuario nunca sabe que el registro parcial existe porque la API
  reporto error.
- **Evidencia:** Reproducido con `unittest.mock.patch` forzando el fallo en la
  segunda llamada a `crear_retencion()` (2 tipos de retencion configurados,
  RETEFUENTE+RETEICA, ambos > 0). Confirmado ANTES(FAIL)/DESPUES(PASS) revirtiendo el
  fix con `git stash`: sin el fix, `DocumentoSoporte.objects.count()` y
  `Retencion.objects.count()` NO vuelven al valor previo tras el error (158.54s); con
  el fix, ambos permanecen sin cambios (232.39s, 2/2 tests).
- **Correccion:** `transaction.set_rollback(True)` en los 3 `except` de
  `procesar_gasto()`.
- **Test:** `apps/tenant/gastos/tests/test_f25_procesar_gasto_atomicidad.py` (2/2).
- **Estado:** FIXED, VERIFIED.

---

## F25-FP-001 a F25-FP-013 — 13 candidatos SAFE_BY_DESIGN (no modificados)

Regla F25 §30/§39: no modificar codigo solo para eliminar un resultado del AST
cuando el candidato es genuinamente seguro. Los siguientes 13 metodos coinciden con
el patron AST pero su UNICA escritura real es una sola llamada a otro metodo
`@transaction.atomic` (savepoint independiente, auto-revertido ante cualquier
excepcion interna, sin importar el comportamiento del `except` externo):

| ID | App | Metodo | Unica escritura real | Evidencia |
|---|---|---|---|---|
| FP-001 | compras | `crear_orden_compra` | `OrdenCompraCRUDService.crear_orden()` (atomic) | toda la resolucion DSV (plantilla, proveedor, proyecto, documento_soporte, area) ocurre antes; el unico write es la ultima linea antes del `return` |
| FP-002 | compras | `actualizar_orden_compra` | `OrdenCompraCRUDService.actualizar_orden()` (atomic) | internamente hace `items.all().delete()` + `bulk_create()`, pero AMBOS ocurren dentro del MISMO savepoint de `actualizar_orden()` -- si `bulk_create` nunca se alcanza (ValidationError antes), Django revierte el `delete()` automaticamente al salir del savepoint, antes de que el `except` externo se ejecute |
| FP-003 | compras | `cambiar_estado_orden_compra` | `OrdenCompraCRUDService.cambiar_estado()` (atomic) | lookup + 1 escritura |
| FP-004 | compras | `eliminar_orden_compra` | `OrdenCompraCRUDService.eliminar_orden()` (atomic) | lookup + 1 escritura |
| FP-005 | compras | `crear_recepcion` | `RecepcionCompraCRUDService.crear_recepcion()` (atomic) | toda la validacion (orden, sede, items, cantidades pendientes) ocurre antes del unico write final; ya identificado como bajo riesgo en `F24_FINDINGS.md` F24-003 |
| FP-006 | ventas | `crear_venta_borrador` | `VentaCRUDService.crear_venta()` (atomic) | DSV cliente/items/proyecto antes; `crear_venta()` hace `venta.save()` + `bulk_create(items)` dentro de SU PROPIO savepoint |
| FP-007 | ventas | `anular_venta` | `VentaCRUDService.anular_venta()` (atomic) | lookup + 1 escritura |
| FP-008 | ventas | `crear_resolucion` | `ResolucionFacturacionCRUDService.crear_resolucion()` (atomic) | 1 escritura |
| FP-009 | ventas | `actualizar_resolucion` | `ResolucionFacturacionCRUDService.actualizar_resolucion()` (atomic) | lookup + 1 escritura |
| FP-010 | ventas | `eliminar_resolucion` | `ResolucionFacturacionCRUDService.eliminar_resolucion()` (atomic) | lookup + 1 escritura |
| FP-011 | gastos | `anular_gasto` | `DocumentoCRUDService.anular_documento()` (atomic) | lookup + 1 escritura |
| FP-012 | gastos | `eliminar_gasto` | `DocumentoCRUDService.eliminar_documento()` (atomic) | lookup + 1 escritura |
| FP-013 | facturas | `guardar_desde_dto` | ver detalle abajo (caso especial) | ver F25-FP-013 |

### F25-FP-013 — `FacturaBusinessService.guardar_desde_dto()` (caso especial, analisis detallado)

5 `except` localizados (lineas 332, 464, 480, 552, 567), pero los 5 son guardas
**tempranas y locales** (cada uno envuelve una unica llamada a un resolver de
cliente/proveedor, ANTES de cualquier escritura real de Factura) que retornan un
error limpio sin haber escrito nada aun. La secuencia real de escrituras
(`FacturaCRUDService.crear()` en linea 637, `FacturaImpuesto.objects.create()` en
loop linea 642, `RetencionesService.crear_retencion()` en loop linea 657,
`NotaCredito.objects.create()` linea 672, `ItemFactura.objects.create()` en loop
linea 701) **no tiene NINGUN `try/except` local que la envuelva** -- si cualquiera de
estas escrituras falla, la excepcion se propaga naturalmente fuera de
`guardar_desde_dto()`, y como el metodo esta decorado `@transaction.atomic` sin nada
que la capture antes, Django ejecuta el rollback automatico correcto de toda la
transaccion. Es decir: `guardar_desde_dto()` tiene el MISMO riesgo estructural que
`confirmar_recepcion()` (multiples escrituras crudas en secuencia, incluyendo loops)
pero **no tiene el bug**, porque a diferencia de `confirmar_recepcion()` esas
escrituras no estan protegidas por un `try/except` que las capture-y-retorne. Es el
ejemplo mas claro de por que "tiene multiples writes" no es sinonimo de "es
vulnerable" -- lo que importa es si algo atrapa la excepcion sin relanzarla.

**Nota de diseno:** esto significa que `guardar_desde_dto()` termina la ejecucion con
un `raise` no controlado (500 de Django) en vez de un `(False, {...}, codigo)` limpio
si falla en la seccion de escritura -- una diferencia de contrato de API (menos
amigable) pero NO un defecto de atomicidad. Fuera del alcance de F25 (no es un
hallazgo de atomicidad/rollback/idempotencia).

**Estado (FP-001 a FP-013):** FALSE_POSITIVE / SAFE_BY_DESIGN, no modificados,
evidencia de lectura de codigo documentada arriba.

---

## F25-002 — Celery retry safety (revision, sin defecto nuevo)

- **Severidad:** INFO
- **Apps:** facturas, contabilidad
- **Archivos:** `apps/tenant/facturas/tasks.py`, `apps/tenant/contabilidad/tasks.py`
- **Descripcion:** 2 `@shared_task` reales en el circuito auditado:
  `procesar_factura_xml_task` (facturas, `max_retries=3`) y
  `ejecutar_integracion_contable_task` (contabilidad, `max_retries=3`, con DLQ real
  via `FailedTenantTask` tras agotar reintentos).
- **`procesar_factura_xml_task`**: `with transaction.atomic(): FacturaService.crear_desde_xml(...)`
  dentro de un `try/except Exception: self.retry(exc=exc)` -- el `with atomic()`
  revierte correctamente cualquier escritura parcial antes de que `self.retry()`
  reencole la tarea (no hay swallow: `self.retry()` re-lanza una excepcion especial
  de Celery). `crear_desde_xml()` -> `importar_documento()` ->
  `guardar_desde_dto()`, que tiene idempotencia real por CUFE (verificado en
  F25-FP-013): un reintento tras un fallo transitorio (ej. timeout de red) no
  duplica la Factura porque el chequeo de CUFE ocurre antes de cualquier escritura.
- **`ejecutar_integracion_contable_task`**: delega en
  `ContabilidadBusinessService.ejecutar_integracion_completa()`, que a su vez llama a
  `contabilizar_pendientes()` de cada extractor (F22) -- ya verificado exhaustivamente
  en F22/F23/F24 como idempotente por documento (`AsientoContable` +
  `UniqueConstraint uniq_asiento_documento_origen_no_reversado`, con aislamiento de
  fallos por documento). Reintentos de la tarea completa nunca duplican asientos.
- **Correccion:** Ninguna necesaria -- el mecanismo de idempotencia existente (CUFE
  para facturas, `UniqueConstraint` + documento_origen para movimientos/asientos) ya
  cubre retry HTTP, doble click y retry de Celery sin necesidad de un framework de
  idempotencia nuevo (regla F25 §24).
- **Estado:** PASS, sin cambios.

---

## F25-003 — `KardexService.registrar_movimiento()`: patron ejemplar (no un finding, referencia positiva)

Nested `atomic()` usado correctamente para aislar el `INSERT` de
`MovimientoInventario` de forma que un `IntegrityError` especifico (constraint de
idempotencia `uniq_movimiento_documento_origen_tipo`) pueda capturarse y traducirse a
"devolver el movimiento existente", mientras que **cualquier otro** `IntegrityError`
se re-lanza explicitamente (`raise` sin argumentos, linea 190) en vez de ser
absorbido. `select_for_update()` sobre el `Producto` (linea 146) serializa
escrituras concurrentes de stock sobre el mismo producto. Documentado como
referencia de buen diseno para el resto del codebase, no como hallazgo.

---

## F25-004 — Traslados (`TrasladoInventarioService.enviar/recibir`): confirmado sin regresion

`enviar()` y `recibir()` son 2 transiciones de estado deliberadamente separadas (no
una sola operacion atomica combinada -- el estado `EN_TRANSITO` existe precisamente
para representar el tiempo real entre ambos pasos). Cada una es individualmente
segura: `select_for_update()` sobre el `TrasladoInventario`, un unico
`KardexService.registrar_movimiento()` (atomic, idempotente), actualizacion de
estado, **sin ningun `try/except` que absorba excepciones** -- cualquier fallo
propaga naturalmente y revierte la transicion completa via el decorador
`@transaction.atomic` del metodo. Confirma la conclusion de F24 (F24_E2E_AUDIT_REPORT.md
§F24.3): sin hallazgos.

---

## Resumen

| ID | Severidad | Estado |
|---|---|---|
| F25-001 | HIGH | FIXED, VERIFIED |
| F25-FP-001..013 | — | FALSE_POSITIVE / SAFE_BY_DESIGN |
| F25-002 | INFO | PASS (revisado, sin defecto) |
| F25-003 | — | Referencia positiva |
| F25-004 | — | Confirmado sin regresion |

0 findings CRITICAL. 1 finding HIGH, corregido y verificado con evidencia
ANTES(FAIL)/DESPUES(PASS). 0 findings ocultos: los 13 falsos positivos estan
documentados individualmente con la razon tecnica exacta de por que son seguros, no
simplemente descartados.
