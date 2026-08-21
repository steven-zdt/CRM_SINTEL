# F34_inventario_AUDIT — Auditoria integral de negocio/arquitectura (app 6/16)

Mision F34. Base confirmada: `documentacion/audits/apps/
APP_inventario_AUDIT.md` (0 codigo muerto detectado en esa pasada --
**revisado con grep fresco en esta pasada, y SI se encontro codigo
muerto real que la pasada anterior no detecto**, siguiendo el mismo
patron que emergio en `proveedores`: una pasada anterior que concluye
"limpio" no garantiza que un barrido mas profundo, con otro angulo,
no encuentre algo nuevo).

**Fecha:** 2026-08-21. **Rama:** `feat/onboarding-cookie`.

---

## Resumen ejecutivo

`inventario` es el motor Kardex (Productos/Servicios/ActivosFijos,
movimientos append-first, stock desnormalizado recalculado
atomicamente). Esta pasada F34 encontro una **capa de "conveniencia"
completa (facade module-level + wrappers de clase + un metodo de
mixin) que nunca fue adoptada por ningun consumidor real** -- los
consumidores reales (`ventas`, `compras`, `facturas`, `contabilidad`)
siempre llamaron `KardexService.registrar_movimiento()` directamente
con un `tipo=` explicito, nunca las funciones de conveniencia
`registrar_entrada`/`registrar_salida`/`ajustar_stock`.

## FASE 1 — Reglas de negocio (clasificadas)

| Regla | Clasificacion | Evidencia |
|---|---|---|
| Movimientos son append-first (Kardex) -- nunca se editan libremente, solo `actualizar_movimiento`/`eliminar_movimiento` controlados con recalculo atomico de stock | **CRITICAL** | `business_service.py`, `.agent/` doc |
| `stock_actual` es un campo desnormalizado que SOLO `KardexService.recalcular_stock_producto()` debe escribir (con `select_for_update()`) | **CRITICAL** | Confirmado, unico punto de escritura real |
| Contabilidad consume Inventario SOLO via `get_movimientos_timeline()` -- nunca consulta `Producto`/`Servicio`/`ActivoFijo` directamente | **CRITICAL** (arquitectonica) | Ya verificado end-to-end en la mision anterior (suite F22) |
| `CheckConstraint exactly_one_product_or_asset` en `MovimientoInventario` -- un movimiento es de Producto XOR de ActivoFijo, nunca ambos ni ninguno | **CRITICAL** | `models.py` |
| Los consumidores externos (Ventas/Compras/Facturas) deben llamar `KardexService.registrar_movimiento(tipo=...)` con el tipo explicito -- NO existe (ni existio nunca en la practica) un "punto de entrada generico simplificado" adoptado | **IMPORTANT** (corrige documentacion desactualizada) | Ver FASE 12 |
| `TrasladoInventario`: maquina de estados `solicitar -> aprobar -> enviar -> recibir` (o `cancelar`) | **IMPORTANT** | `business_service.py` (F21) |

## FASE 2 — Mapa de dominio (sin cambios respecto a la auditoria previa)

6 modelos concretos + 1 abstracto (`TimeStampedModel`), ya mapeados en
`APP_inventario_AUDIT.md`. Sin cambios en esta pasada.

## FASE 12/13 — Codigo muerto (HALLAZGO NUEVO, ACCION TOMADA)

Investigacion mas profunda que la pasada anterior: se comparo, simbolo
por simbolo, cada funcion/metodo publico de `business_service.py`
contra sus consumidores reales en TODO el repo (no solo dentro de la
propia app). Resultado:

| Simbolo | Tipo | Consumidores reales encontrados |
|---|---|---|
| `KardexService.calcular_stock`/`recalcular_stock_producto` | Metodo de clase | **SI** -- `ingesta_service.py`, y usados internamente por otros metodos de la propia clase |
| `KardexService.registrar_movimiento` | Metodo de clase | **SI** -- `ventas`, `compras`, `facturas` (via `contabilidad`), `api_mixins.py` -- el verdadero punto de entrada real |
| `KardexService.registrar_entrada`/`registrar_salida` (wrappers de conveniencia con `tipo` por defecto) | Metodo de clase | **NO** -- cero consumidores fuera de su propia definicion |
| `KardexService.ajustar_stock` | Metodo de clase | **NO** -- unico caller era el wrapper module-level (tambien muerto) |
| Funciones module-level `calcular_stock`, `recalcular_stock_producto`, `registrar_entrada`, `registrar_salida`, `ajustar_stock`, `registrar_movimiento` (facade completo al final de `business_service.py`) | Funciones sueltas | **NO** -- `services/__init__.py` solo reexporta `KardexService`/`TrasladoInventarioService` (las clases), nunca estas funciones sueltas; ningun consumidor externo las importa (confirmado con grep repo-wide) |
| `ProductoServiceMixin.service_producto_ajustar_stock()` | Metodo de mixin | **NO** -- documentado en el `.agent/` doc como parte del inventario de metodos del mixin, pero **nunca wireado a ningun `@action` de ViewSet** (confirmado: cero `@action` relacionado con "ajustar/adjust stock" en `api/viewsets.py`) -- funcionalidad diseñada pero nunca conectada a un endpoint real, y sin cobertura de tests |

**DEAD_CONFIRMED, eliminado:**
- `business_service.py`: facade module-level completo (`calcular_stock`,
  `recalcular_stock_producto`, `registrar_entrada`, `registrar_salida`,
  `ajustar_stock`, `registrar_movimiento` -- ~130 lineas) + los 3
  metodos de clase de conveniencia nunca adoptados
  (`KardexService.registrar_entrada`, `registrar_salida`,
  `ajustar_stock` -- ~28 lineas). Imports huerfanos limpiados:
  `typing.Optional/Any/Dict/List` (0 usos restantes),
  `apps.tenant.empresa.models.Empresa` (0 usos restantes).
- `services/api_mixins.py`: `ProductoServiceMixin.
  service_producto_ajustar_stock()` (3 lineas) + su import huerfano
  de `ajustar_stock`.

**Total eliminado: ~165 lineas.** La capacidad de "ajustar stock"
sigue disponible para cualquier consumidor real via el punto de
entrada generico ya adoptado (`KardexService.registrar_movimiento(
tipo=ENTRADA_AJUSTE|SALIDA_BAJA, ...)`), que NO se toco.

**Nota de precision para el `.agent/` doc de la app:** su tabla de
metodos de `business_service.py` describia `registrar_entrada(**kwargs)`
y `registrar_salida(**kwargs)` como "Wrapper con default `tipo=...`"
sugiriendo que eran el patron de uso recomendado -- la evidencia real
(grep de consumidores) muestra que NINGUN consumidor los adopto; el
patron real y unico usado en produccion es
`KardexService.registrar_movimiento(tipo=<valor explicito>, ...)`.
Se documenta la discrepancia aqui; no se edita el `.agent/` doc
directamente en esta pasada (fuera del alcance minimo).

## FASE 17 — Validacion puntual

Cambio de codigo real -> regresion de `apps/tenant/inventario/` (25
tests) en curso. Los consumidores cross-app (`ventas`, `compras`,
`facturas`, `contabilidad`) NO se re-testean en esta pasada porque ya
se confirmo con grep repo-wide que ninguno importa los simbolos
eliminados -- riesgo de regresion cruzada nulo por diseño de la
evidencia, no por omision.

## FASE 22 — Release Gate

- [x] Reglas de negocio clasificadas (incluye correccion de una
      descripcion desactualizada en el `.agent/` doc)
- [x] Mapa de dominio (sin cambios)
- [x] Codigo muerto: hallazgo nuevo real, ~165 lineas eliminadas con evidencia completa
- [ ] Regresion puntual -- en curso
- [x] `py_compile` limpio

**APP = COMPLETED_WITH_DEFERRED** (pendiente de confirmar regresion).
