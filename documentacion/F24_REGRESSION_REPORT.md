# F24 — Reporte de Regresion

**Fecha:** 2026-08-10

## Corrida consolidada final (F24.30-32/F24.53)

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
  -q --tb=long
```

```
57 passed in 2812.16s (0:46:52)
```

## Desglose por fase

| Fase | Archivo | Tests | Resultado |
|---|---|---|---|
| F21 | `test_f21_recepcion_compra.py` | 6 | incluido en 57/57 |
| F21 | `test_f21_traslado_inventario.py` | 10 | incluido en 57/57 |
| F22 | `test_f22_extractor_inventario_mapping.py` | 9 | incluido en 57/57 |
| F22 | `test_f22_extractor_inventario_integration.py` | 10 | incluido en 57/57 |
| F22 | `test_f22_extractor_inventario_multitenant.py` | 1 | incluido en 57/57 |
| F23 | `test_f23_venta_inventario.py` | 8 | incluido en 57/57 |
| F23 | `test_f23_venta_inventario_multitenant.py` | 1 | incluido en 57/57 |
| F24 | `test_f24_confirmar_recepcion_atomicidad.py` | 2 | incluido en 57/57 |
| F24 | `test_f24_e2e_circuito_completo.py` | 8 | incluido en 57/57 |
| F24 | `test_f24_e2e_multitenant_dsv.py` | 2 | incluido en 57/57 |
| **Total** | | **57** | **57/57 PASS** |

(16 F21 + 20 F22 + 9 F23 + 12 F24 = 57, consistente con `F21_TEST_MATRIX.md`,
`F22_TEST_MATRIX.md` y `F23_TEST_MATRIX.md`.)

## Interpretacion

- **0 regresiones** en F21, F22 o F23: los 45 tests que ya pasaban al cierre de F23
  (ver `F23_TEST_MATRIX.md` §3) siguen pasando exactamente igual despues de los 2
  fixes de codigo que F24 aplico (`confirmar_recepcion`/`anular_recepcion` en
  compras, `validar_periodo_abierto` en contabilidad).
- Los 12 tests nuevos de F24 cubren los escenarios E2E que ninguna fase anterior
  habia ejercitado juntos (ver `F24_E2E_TEST_MATRIX.md`), incluyendo los 2 que
  expusieron los hallazgos reales documentados en `F24_FINDINGS.md`.
- No se acepta "PASS" basado solo en los tests nuevos: esta es una corrida
  consolidada real de las 4 fases en un solo proceso pytest, no 4 corridas
  separadas sumadas manualmente.

## Regresion de fases individuales (previamente confirmada, no repetida aqui)

`F21_TEST_MATRIX.md`, `F22_TEST_MATRIX.md`, `F23_TEST_MATRIX.md` documentan el
detalle escenario-por-escenario de sus respectivos tests; F24 no los duplica, solo
confirma que siguen en verde dentro de la misma corrida.
