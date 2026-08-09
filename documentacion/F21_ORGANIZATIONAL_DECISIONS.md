# F21 — Decisiones Organizacionales

**Fecha:** 2026-08-09

Cada decision de este documento responde explicitamente a las 9 preguntas del
prompt maestro §4 antes de agregar cualquier campo organizacional a un modelo
(necesidad de dominio, de query, de autorizacion, de persistencia, impacto
historico, impacto de migracion, impacto contable, impacto EKG, impacto de
governance).

## 1. RecepcionCompra hereda SedeAwareModel (no SintelTenantBaseModel)

- **Dominio:** la recepcion fisica de mercancia ocurre en una sede concreta;
  es information de negocio real, no derivable de otro campo.
- **Query:** filtrar recepciones por sede (ej. "que llego a Bogota esta
  semana") es un caso de uso real de bodega/almacen.
- **Autorizacion:** `HasOrganizationalScope` ya opera sobre `sede`/`area` en
  todo el resto del piloto (compras) — reutilizar el mismo mecanismo evita
  una segunda logica de permisos.
- **Persistencia:** tabla nueva sin datos historicos -> se endurece `sede`
  `NOT NULL` desde el primer dia (a diferencia de `OrdenCompra`, que
  necesito el ciclo nullable->backfill->harden por tener filas
  preexistentes).
- **Impacto historico:** ninguno (tabla nueva).
- **Impacto de migracion:** una sola migracion aditiva, sin backfill.
- **Impacto contable:** ninguno directo — la Sede de la recepcion se copia
  como `sede_id` en el `MovimientoInventario` generado (informativo, ya
  existia el campo).
- **Impacto EKG/governance:** una relacion nueva real (`RecepcionCompra ->
  Sede`), no una duplicacion de una relacion existente.
- **Decision:** SI, adopta `SedeAwareModel` (extension del piloto ya
  aprobado en `compras`, no una app nueva adoptando el mixin).

## 2. Producto NO gana un campo `sede_id` — stock por sede se resuelve en lectura

- **Dominio:** el stock fisico de un producto SI varia por sede (motivador
  central de F21: Bogota=100/Barranquilla=20 antes de un traslado).
- **Query:** el calculo de "stock en sede X" es exactamente el mismo patron
  ya usado por `KardexService.calcular_stock()` (suma entradas menos
  salidas), con un filtro adicional `sede_id` — no requiere un campo
  persistido nuevo en `Producto`.
- **Autorizacion:** no aplica (es un calculo derivado, no un campo que
  necesite su propio control de acceso).
- **Persistencia:** `Producto.stock_actual` permanece **agregado por
  empresa** (invariante que muchos otros flujos ya asumen: ventas, ajustes,
  compras sin sede). Agregar un segundo campo de stock por sede en
  `Producto` obligaria a mantener 2 fuentes de verdad sincronizadas (riesgo
  real de divergencia) cuando `MovimientoInventario.sede` (ya existente)
  es suficiente para derivarlo en lectura.
- **Impacto historico:** movimientos previos a F21 tienen `sede=NULL` — NO
  se les asigna una sede inventada (prohibido explicitamente por el prompt
  maestro). `StockPorSedeSelector.calcular_stock_sin_asignar()` expone ese
  resto por separado, visible pero no fusionado con el stock de una sede
  real.
- **Impacto de migracion:** cero (no se toca `Producto`).
- **Impacto contable:** ninguno (el costo promedio/valorizacion sigue siendo
  por empresa, sin cambios).
- **Impacto EKG/governance:** ninguna relacion nueva forzada.
- **Decision:** NO se agrega `sede_id` a `Producto`. `MovimientoInventario`
  ya es `Empresa + Sede + Producto`, exactamente como el prompt maestro
  autoriza explicitamente en su §18.

## 3. Area — opcional, no obligatoria, en Recepcion y Traslado

- `RecepcionCompra` hereda `area` de `SedeAwareModel` (opcional, `SET_NULL`)
  — la mayoria de recepciones no necesitan un area responsable explicita,
  pero cuando la orden de compra tiene un area asignada, tiene sentido
  poder heredarla/asignarla.
- `TrasladoInventario.area_origen`/`area_destino` — opcionales por la misma
  razon: no todo traslado nace de/hacia un area especifica (puede ser a
  nivel de bodega general de la sede).
- **Decision:** ningun campo de Area es obligatorio en F21 — consistente con
  "no toda tabla debe forzar area" (regla explicita del prompt maestro).

## 4. TrasladoInventario: un producto por traslado (no un carrito multi-item)

- **Alcance reducido, documentado explicitamente:** el dominio real descrito
  en el prompt maestro (ejemplo Bogota->Barranquilla, 30 unidades de un
  producto) es 1 producto por operacion. Modelar
  `TrasladoInventarioItem` (multi-producto) habria multiplicado el trabajo
  de implementacion/tests sin evidencia de necesidad real en el dominio
  descrito. Si en el futuro se necesita mover varios productos en una sola
  operacion logistica, la extension es aditiva (nueva tabla
  `TrasladoInventarioItem`, `TrasladoInventario` pasa a ser cabecera) sin
  romper lo ya construido.

## 5. Contabilidad — extractor de inventario permanece deshabilitado

- **Hallazgo (F21.17, ver `F21_BASELINE.md` §5):** el extractor de
  inventario ya estaba deshabilitado (`extraer_pendientes()` retorna `[]`)
  antes de F21, con 0 codigo real conectandolo a `Contabilizador`/
  `ReglaContable`. Esto significa que ni antes ni despues de F21 los
  movimientos de inventario (compra, venta, ajuste, ahora tambien traslado)
  generan asiento contable.
- **Decision de alcance:** F21 **no reactiva ni reescribe** el extractor.
  Hacerlo correctamente requeriria: definir `ReglaContable` para las cuentas
  de inventario/costo de mercancia vendida por cada `TipoMovimiento`,
  decidir el tratamiento contable de un traslado entre sedes (que NO debe
  generar un asiento con impacto en resultados, solo un posible movimiento
  interno de existencias si la empresa maneja cuentas de inventario por
  sede) y validar todo contra el Plan Unico de Cuentas real de la empresa —
  trabajo de dominio contable/legal, no solo tecnico, y explicitamente fuera
  del alcance verificable de esta sesion (mismo criterio que
  `COLOMBIA_COMPLIANCE_TRACEABILITY.md`: no fabricar cobertura no
  verificada). Se registra como deuda preexistente, no como regresion de
  F21.
- Esto **no viola el Pull Model**: no se agrego ningun `crear_asiento()`
  directo desde `compras` ni desde `inventario` — la ausencia de
  contabilizacion es un vacio de cobertura, no un bypass del patron Pull.

## 6. RecepcionCompra/TrasladoInventario CONFIRMADA/RECIBIDO son terminales

- Una vez que una recepcion genera `MovimientoInventario` (CONFIRMADA), o un
  traslado genera su `TRASLADO_SALIDA` (EN_TRANSITO), esos movimientos son
  append-only reales. Revertirlos requeriria un movimiento compensatorio
  explicito (ej. `AJUSTE` inverso) — deliberadamente fuera de alcance de F21
  (riesgo de corromper trazabilidad historica, categoria de riesgo que el
  prompt maestro instruye bloquear en vez de intentar). `anular_recepcion()`
  y `cancelar()` (traslado) solo operan en los estados previos a la
  generacion de movimientos (BORRADOR / antes de EN_TRANSITO).
