# F25 — Reporte de Regresion

**Fecha:** 2026-08-10

## Corrida consolidada final (F25.28/F25.37/F25.55)

```bash
docker compose exec -T web python -m pytest \
  apps/tenant/compras/tests/test_f21_recepcion_compra.py \
  apps/tenant/inventario/tests/test_f21_traslado_inventario.py \
  apps/tenant/contabilidad/tests/test_f22_extractor_inventario_mapping.py \
  apps/tenant/contabilidad/tests/test_f22_extractor_inventario_integration.py \
  apps/tenant/contabilidad/tests/test_f22_extractor_inventario_multitenant.py \
  apps/tenant/ventas/tests/test_f23_venta_inventario.py \
  apps/tenant/ventas/tests/test_f23_venta_inventario_multitenant.py \
  apps/tenant/compras/tests/test_f24_confirmar_recepcion_atomicidad.py \
  apps/tenant/contabilidad/tests/test_f24_e2e_circuito_completo.py \
  apps/tenant/contabilidad/tests/test_f24_e2e_multitenant_dsv.py \
  apps/tenant/gastos/tests/test_f25_procesar_gasto_atomicidad.py \
  -q --tb=long
```

```
59 passed in 2993.50s (0:49:53)
```

## Desglose

| Fase | Tests | Resultado |
|---|---|---|
| F21 | 16 | incluido en 59/59 |
| F22 | 20 | incluido en 59/59 |
| F23 | 9 | incluido en 59/59 |
| F24 | 12 | incluido en 59/59 |
| F25 | 2 | incluido en 59/59 |
| **Total** | **59** | **59/59 PASS** |

(57 previas de F21+F22+F23+F24, confirmado en `F24_REGRESSION_REPORT.md`, + 2 nuevas
de F25 = 59, sin ninguna regresion.)

## Interpretacion

**0 regresiones** en F21, F22, F23 o F24 tras la unica correccion de codigo de F25
(`gastos/services/business_service.py::procesar_gasto`, 3 lineas de
`transaction.set_rollback(True)` dentro de `except` ya existentes -- no toca ningun
modelo, import, ni logica de negocio/DSV/scope). Los 59 tests corrieron en un solo
proceso pytest, no como suma manual de corridas separadas.

## Regresion de fases individuales (ya confirmada, no repetida aqui)

`F21_TEST_MATRIX.md`, `F22_TEST_MATRIX.md`, `F23_TEST_MATRIX.md`,
`F24_E2E_TEST_MATRIX.md`/`F24_REGRESSION_REPORT.md` documentan el detalle
escenario-por-escenario de sus respectivas fases; F25 solo confirma que siguen en
verde dentro de la misma corrida consolidada.
