# F21 — Baseline (Auditoria Real: Compras, Inventario, Empresa, Organizacional)

**Fecha:** 2026-08-09
**Metodo:** lectura directa de codigo real (`models.py`, `business_service.py`,
`selectors.py`), no solo de los `.agent/AUDITORIA_*.md` existentes (algunos
predatan ADR-003 y el rollout de Sede). Los `.agent/*.md` se usaron como punto
de partida, verificados/corregidos contra el codigo.

## 1. Compras — estado real antes de F21

- `OrdenCompra(SedeAwareModel)` — `apps/tenant/compras/models.py`. `sede`
  endurecida `NOT NULL` (migraciones 0006/0007). `ESTADO_CHOICES`:
  BORRADOR/PENDIENTE/APROBADA/RECIBIDA/ANULADA — **sin estado PARCIAL**, sin
  `CheckConstraint` de BD sobre el campo (solo `choices=` a nivel Python).
- `ItemOrdenCompra(SintelTenantBaseModel)` — `item_inventario_uuid` (UUID
  nullable, soft reference a Producto **o** Servicio del catalogo de
  inventario). **Sin `cantidad_recibida`** — no existia forma de trackear
  recepcion parcial.
- `OrdenCompraBusinessService.cambiar_estado_orden_compra()` —
  `apps/tenant/compras/services/business_service.py:328-345` (linea real
  verificada) — cambia unicamente el campo `estado`. **Cero conexion con
  inventario.** Confirma exactamente la brecha ya documentada en
  `F15_F20_FINAL_REPORT.md` §12: "compras -> inventario (recepcion de
  OrdenCompra no genera MovimientoInventario automaticamente hoy)".
- No existia ningun modelo `RecepcionCompra` ni equivalente.

## 2. Inventario — estado real antes de F21

- `MovimientoInventario` — `apps/tenant/inventario/models.py:237-331`.
  `TipoMovimiento` ya incluia `ENTRADA_COMPRA` (reutilizado en F21, no se creo
  un tipo nuevo). `TRASLADO_MANTENIMIENTO`/`RETORNO_MANTENIMIENTO` existian
  pero son transiciones de estado de `ActivoFijo` (mapeadas via
  `_TRANSICION_ESTADO_ACTIVO`), **no** movimiento de stock de `Producto` entre
  sedes — no son el mismo concepto que "traslado entre sedes".
- `sede` (FK `empresa.Sede`, `SET_NULL`, nullable, `db_index=True`) ya
  existia (DT-SEDE-05) pero era puramente informativo para KPIs — ningun
  selector lo usaba para calcular stock.
- **Sin campos de idempotencia** (`documento_origen_*`) en
  `MovimientoInventario` antes de F21 — a diferencia de `AsientoContable`
  (`apps/tenant/contabilidad/models.py:304-335`), que ya tenia el patron
  completo (triple soft-reference + `UniqueConstraint` condicional).
- `KardexService` (`apps/tenant/inventario/services/business_service.py:45-193`
  antes de F21) — motor transaccional real: `calcular_stock()`,
  `recalcular_stock_producto()` (con `select_for_update`),
  `registrar_movimiento()` (valida cantidad, tipo, stock suficiente en
  salidas, crea el movimiento y recalcula). **Unico punto de entrada real
  para mutar stock** — F21 lo extiende aditivamente (no lo duplica).
- Stock era puramente agregado por empresa (`Producto.stock_actual`) — sin
  ninguna nocion de "stock por sede".
- **Sin `TrasladoInventario`** ni equivalente.

## 3. Empresa (Empresa -> Sede -> Area) — re-verificado

- `Area.empresa_id == Area.sede.empresa_id` se aplica en Service Layer
  (`apps/tenant/empresa/services/crud_service.py:187-220`), no como
  `CheckConstraint` de BD — mismo hallazgo ya documentado en
  `F16_ORGANIZATIONAL_MODEL.md`, re-confirmado aqui sin cambios.

## 4. Servicios organizacionales — re-verificados

- `OrganizationalContext`/`OrganizationalScope`/`HasOrganizationalScope`
  (`apps/tenant/core/services/organizational_*.py`) siguen siendo la unica
  implementacion — F21 no crea una segunda. `RecepcionCompraViewSet` y
  `OrdenCompraViewSet` comparten el mismo `HasOrganizationalScope` (piloto
  ya existente, extendido al nuevo ViewSet).

## 5. Contabilidad — auditoria del extractor (F21.17)

- `apps/tenant/contabilidad/integracion/extractores/inventario.py` —
  **extractor legacy deshabilitado**, `extraer_pendientes()` retorna `[]`
  incondicionalmente. El docstring afirma "el mapeo vive en Inventario" pero
  no existe codigo real en `apps/tenant/inventario` que llame a
  `Contabilizador`/`ReglaContable`/ningun mecanismo de contabilizacion —
  verificado por grep, 0 referencias.
- Conclusion: **hoy, ningun movimiento de inventario (compra, venta, ajuste,
  traslado) genera asiento contable.** Esto es deuda preexistente a F21, no
  introducida por esta fase — ver `F21_ORGANIZATIONAL_DECISIONS.md` §Contabilidad
  para la decision de alcance (no se reactiva/reescribe el extractor en F21).

## 6. Conclusion de la auditoria

La brecha objetivo de F21 (`OrdenCompra -> [BRECHA] -> Inventario`, y la
ausencia total de traslados entre sedes) esta confirmada exactamente como la
describian `F15_F20_FINAL_REPORT.md` §12 y `F18_COLOMBIAN_BUSINESS_FLOWS.md`
§F18.6/§F18.11. `KardexService.registrar_movimiento()` es solido y reutilizable
como punto de integracion unico — la implementacion de F21 lo extiende en vez
de crear un segundo motor de Kardex.
