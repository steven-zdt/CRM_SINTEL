# F21 — Traslado de Inventario entre Sedes

**Fecha:** 2026-08-09

## 1. Flujo implementado

```
SOLICITADO -> APROBADO -> EN_TRANSITO -> RECIBIDO
     \-> CANCELADO (solo desde SOLICITADO o APROBADO)
```

Archivos: `apps/tenant/inventario/models.py` (`TrasladoInventario`,
`TipoMovimiento.TRASLADO_SALIDA`/`TRASLADO_ENTRADA`,
`MovimientoInventario.documento_origen_*`),
`apps/tenant/inventario/services/business_service.py`
(`TrasladoInventarioService`), `services/selectors.py`
(`StockPorSedeSelector`, `TrasladoInventarioSelector`),
`services/api_mixins.py` (`TrasladoInventarioServiceMixin`),
`api/{serializers,viewsets,urls}.py`.

No se modifica `MovimientoInventario.sede` de un movimiento existente en
ningun punto del flujo — cada transicion que afecta stock genera un
movimiento append-only nuevo:

- `enviar()`: SOLICITADO/APROBADO -> EN_TRANSITO, genera
  `TRASLADO_SALIDA` con `sede_id=sede_origen`.
- `recibir()`: EN_TRANSITO -> RECIBIDO, genera `TRASLADO_ENTRADA` con
  `sede_id=sede_destino`.

## 2. Por que stock_actual (empresa) no cambia con un traslado

`KardexService.TIPOS_ENTRADA`/`TIPOS_SALIDA` (que alimentan
`Producto.stock_actual`, agregado por empresa) **deliberadamente no
incluyen** `TRASLADO_SALIDA`/`TRASLADO_ENTRADA` — un traslado interno no
cambia cuanto stock tiene la empresa en total, solo en que sede esta. El
stock por sede se calcula aparte via `StockPorSedeSelector`, que si filtra
por `sede_id` y si incluye los tipos de traslado en su propia agregacion.

## 3. Escenario E2E verificado (Bogota=100, Barranquilla=20, traslado de 30)

| Momento | Bogota | En transito | Barranquilla | Total |
|---|---|---|---|---|
| Antes | 100 | 0 | 20 | 120 |
| Despues de `enviar()` (EN_TRANSITO) | 70 | 30 | 20 | 120 |
| Despues de `recibir()` (RECIBIDO) | 70 | 0 | 50 | 120 |

Sin doble conteo en ningun punto — verificado por
`apps/tenant/inventario/tests/test_f21_traslado_inventario.py::TrasladoHappyPathTests::test_flujo_completo_bogota_a_barranquilla_30_unidades`.
"En transito" se resuelve contra `TrasladoInventario.estado ==
EN_TRANSITO` (no re-derivado de `MovimientoInventario`, para no crear una
segunda fuente de verdad sobre el estado del traslado).

## 4. Validaciones (todas con test real)

| Regla | Donde se aplica | Test |
|---|---|---|
| sede_origen != sede_destino | `CheckConstraint` de BD + validacion en `solicitar()` | `test_sede_origen_igual_destino_es_rechazado` |
| sedes de la misma empresa | `solicitar()` (Zero Trust: nunca confia en el `sede_id` del payload sin verificar `empresa_id`) | `test_sede_de_otra_empresa_es_rechazada`, `TrasladoMultiTenantTests` |
| cantidad > 0 | `CheckConstraint` de BD + validacion en `solicitar()` | (cubierto por validacion de serializer + modelo) |
| cantidad <= stock disponible en sede origen | `enviar()`, via `StockPorSedeSelector` (NO via `Producto.stock_actual`, que es agregado por empresa y daria falsos positivos/negativos) | `test_cantidad_mayor_a_stock_disponible_en_origen_es_rechazado_al_enviar` |
| transiciones de estado invalidas | cada metodo valida el estado previo exacto | `test_enviar_sin_aprobar_es_rechazado` |
| cancelar solo antes de EN_TRANSITO | `cancelar()` | `test_cancelar_en_transito_es_rechazado`, `test_cancelar_en_solicitado_es_permitido` |

## 5. Idempotencia

Mismo patron que Recepcion de Compras:
`documento_origen_app='inventario'`, `documento_origen_modelo=
'TrasladoInventario'`, `documento_origen_id=<id del traslado>`. Como un
mismo traslado genera legitimamente DOS movimientos (`TRASLADO_SALIDA` en
`enviar()`, `TRASLADO_ENTRADA` en `recibir()`), el `UniqueConstraint` de
`MovimientoInventario` incluye `tipo` en la clave — un reintento de
`enviar()` sobre un traslado ya `EN_TRANSITO` es un no-op exitoso (mismo
resultado, sin segundo movimiento); igual para `recibir()`. Verificado por
`TrasladoIdempotenciaTests`.

## 6. Reduccion de alcance (declarada)

- **Un producto por traslado**, no un carrito multi-producto — ver
  `F21_ORGANIZATIONAL_DECISIONS.md` §4 para la justificacion completa.
- **Sin frontend/HTMX** — mismo criterio que Recepcion de Compras.
- **Sin reversion de un traslado RECIBIDO** — terminal, igual que
  `RecepcionCompra` CONFIRMADA (ver decision §6 del documento de
  decisiones organizacionales).
