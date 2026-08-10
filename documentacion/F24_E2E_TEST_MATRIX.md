# F24 — Matriz E2E (seccion 54 del prompt maestro)

**Fecha:** 2026-08-10

| Escenario | Empresa | Sede | Tenant | Inventario | Kardex | Contabilidad | Resultado |
|---|---|---|---|---|---|---|---|
| Compra | v | v | v | v | v | v | PASS |
| Venta | v | v | v | v | v | v | PASS |
| Compra + Venta | v | v | v | v | v | v | PASS |
| Traslado | v | A/B | v | v | v | NO asiento externo | PASS |
| Multi-item | v | v | v | v | v | v | PASS |
| Multi-tenant | v | v | A/B | v | v | v | PASS |
| Scope SEDE | v | v | v | v | v | v | PASS |
| Idempotencia | v | v | v | v | v | v | PASS |
| Rollback | v | v | v | v | v | v | PASS |
| Servicio | v | v | v | NO | NO | segun factura | PASS |

Cada fila se resuelve a un test real ejecutable, no a una afirmacion sin evidencia:

| Escenario | Test |
|---|---|
| Compra | `test_f24_e2e_circuito_completo.py::test_f24_compra_e2e_hasta_asiento_contable` |
| Venta | `test_f24_e2e_circuito_completo.py::test_f24_venta_e2e_costo_promedio_no_precio_venta` |
| Compra + Venta | `test_f24_e2e_circuito_completo.py::test_f24_compra_mas_venta_reconciliacion_stock` |
| Traslado | `test_f24_e2e_circuito_completo.py::test_f24_traslado_no_genera_asiento_contable_externo` |
| Multi-item | `test_f24_e2e_circuito_completo.py::test_f24_multi_item_tres_productos_y_servicio` |
| Multi-sede | `test_f24_e2e_circuito_completo.py::test_f24_multi_sede_stock_independiente` |
| Multi-tenant | `test_f24_e2e_multitenant_dsv.py::test_flujo_completo_compra_venta_asiento_independiente_por_tenant` |
| DSV (UUID de otro tenant) | `test_f24_e2e_multitenant_dsv.py::test_producto_uuid_de_otro_tenant_es_rechazado_limpiamente_en_venta` |
| Idempotencia contable | `test_f24_e2e_circuito_completo.py::test_f24_idempotencia_contable_doble_corrida` |
| Idempotencia compra/venta | ya cubierta por F21 (`test_dos_recepciones_parciales...`) y F23 (`test_reintentar_generar_salida_no_duplica_movimiento`) -- no reimplementada |
| Rollback (atomicidad) | `test_f24_confirmar_recepcion_atomicidad.py::test_fallo_en_segundo_item_revierte_por_completo_el_primero` (nuevo, F21) + F23 `test_stock_insuficiente_revierte_venta_y_factura_completas` (ya existente, ventas) |
| Periodo cerrado | `test_f24_e2e_circuito_completo.py::test_f24_periodo_cerrado_rechaza_contabilizacion` |
| Servicio | ya cubierto por F23 (`test_item_servicio_no_genera_movimiento_inventario`) -- reconfirmado dentro de `test_f24_multi_item_tres_productos_y_servicio` |

## Resultado de ejecucion real

- `test_f24_confirmar_recepcion_atomicidad.py`: 2/2 (242.56s con fix; 1/2 fallando sin
  el fix, evidencia ANTES/DESPUES documentada en `F24_FINDINGS.md` F24-001).
- `test_f24_e2e_circuito_completo.py`: 8/8 (247.45s).
- `test_f24_e2e_multitenant_dsv.py`: 2/2 (397.57s, 2 schemas fisicos reales).
- Regresion consolidada final F21+F22+F23+F24: ver `F24_REGRESSION_REPORT.md`.
