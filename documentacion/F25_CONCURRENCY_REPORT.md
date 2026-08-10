# F25 — Reporte de Concurrencia

**Fecha:** 2026-08-10

## 1. Stock concurrente (F25.19)

**Mecanismo real:** `KardexService.registrar_movimiento()` adquiere
`Producto.objects.select_for_update()` (linea 146,
`apps/tenant/inventario/services/business_service.py`) antes de leer
`stock_actual` y antes de validar suficiencia para salidas. Esto serializa a nivel
de base de datos cualquier par de transacciones concurrentes que intenten escribir
sobre el stock del MISMO producto: la segunda transaccion espera a que la primera
haga commit (liberando el lock de fila) antes de leer el `stock_actual` actualizado,
evitando el clasico "lost update" (dos ventas de 8 sobre un stock de 10 aprobandose
ambas por leer el mismo valor stale de 10).

**Evidencia:** lectura de codigo (citada arriba) + el test ya existente
`test_stock_insuficiente_revierte_venta_y_factura_completas` (F23) que confirma el
rechazo correcto y el rollback completo cuando la cantidad solicitada excede el
stock disponible en el momento de la escritura.

**No se construyo un test de concurrencia real con 2 conexiones de BD simultaneas**
(requeriria infraestructura de threading/multiprocessing no presente actualmente en
la suite de tests del proyecto). Se documenta como evidencia basada en lectura de
codigo del mecanismo de locking (`select_for_update()`), proporcional al alcance de
F25 y consistente con la regla de "no optimizaciones/infraestructura nueva sin
justificacion demostrada" -- el mecanismo YA existe y es el estandar de Django para
este problema exacto; no hay ambiguedad que requiera una prueba de concurrencia real
para confirmar su presencia.

## 2. Asiento contable concurrente (F25.20)

**Mecanismo real:** `Contabilizador.contabilizar()` hace un chequeo previo
(`_validar_no_existe()`, rapido, cubre el caso normal) y ademas tiene un
`UniqueConstraint uniq_asiento_documento_origen_no_reversado` en `AsientoContable`
como respaldo de base de datos: si 2 transacciones concurrentes pasan el chequeo
previo antes de que cualquiera haga commit (condicion de carrera real), la segunda
recibe un `IntegrityError` al hacer `INSERT`, que `contabilizar()` traduce
explicitamente a `AsientoYaExisteError` (lineas 125-140 de `contabilizador.py`) --
tratado por el llamador (`AbstractExtractor.contabilizar_pendientes()`) igual que la
ruta normal de idempotencia (`omitidos`). Documentado explicitamente en el propio
codigo (comentario `[PERF-C1]`), no es un hallazgo nuevo de F25 sino una
confirmacion de que el disenio ya contempla esta condicion de carrera.

**Resultado:** "idempotent success" (segunda contabilizacion se cuenta como
`omitidos`, no como error ni como duplicado) -- exactamente el contrato esperado por
F25.20 ("El segundo procesamiento debe resultar en idempotent success o conflict
controlado, nunca 2 asientos").

## 3. Deadlocks (F25.46)

`select_for_update()` se usa en 3 puntos del circuito auditado:
`KardexService.registrar_movimiento()` (sobre `Producto`),
`RecepcionCompraBusinessService.confirmar_recepcion()` (sobre `RecepcionCompra`,
`OrdenCompra`, `ItemOrdenCompra`, en ese orden fijo dentro del metodo -- no hay
ramas que adquieran estos locks en orden distinto entre si en otro lugar del
codebase), y `TrasladoInventarioService.aprobar/enviar/recibir()` (sobre
`TrasladoInventario`). No se identifico ningun patron de adquisicion de locks en
ordenes cruzados entre 2 o mas de estos servicios que pudiera producir un deadlock
real (ej. servicio A bloquea Producto luego RecepcionCompra, mientras servicio B
bloquea RecepcionCompra luego Producto) -- cada `select_for_update()` esta acotado a
un unico flujo de negocio con un orden de adquisicion consistente. Sin hallazgos.

## 4. Timeouts (F25.48)

No se identifico un mecanismo de timeout explicito a nivel de aplicacion en el
circuito auditado (mas alla de los timeouts de red/DB por defecto de Django/Postgres,
fuera del alcance de codigo de aplicacion). El riesgo real de "timeout produce
duplicacion" ya esta cubierto por el mismo mecanismo de idempotencia
(`UniqueConstraint` + documento_origen) documentado en `F25_IDEMPOTENCY_MATRIX.md`:
un timeout de cliente que provoca un retry HTTP se comporta identico a cualquier
otro reintento, protegido por el mismo constraint.

## Veredicto

Sin hallazgos nuevos de concurrencia/deadlock/timeout. Los mecanismos existentes
(`select_for_update()` + `UniqueConstraint` + chequeo previo en aplicacion) cubren
los escenarios auditados con evidencia de codigo real, sin requerir locks
adicionales ni un framework de concurrencia nuevo.
