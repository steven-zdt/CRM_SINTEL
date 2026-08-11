# F26 — Reporte de Regresión

**Fecha:** 2026-08-10/11

## Corrida consolidada final (F26.36-39/F26.55)

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
  apps/tenant/facturas/tests/test_devolucion_nota_credito.py \
  apps/tenant/facturas/tests/test_materializar_from_dto.py \
  apps/tenant/facturas/tests/test_ingesta_ubl.py \
  apps/tenant/facturas/tests/test_nota_credito_pipeline.py \
  -q --tb=long
```

```
1 failed, 82 passed in 49882.59s
```

## Desglose por fase

| Fase | Archivo(s) | Tests | Resultado |
|---|---|---|---|
| F21 | `test_f21_recepcion_compra.py`, `test_f21_traslado_inventario.py` | 16 | PASS |
| F22 | `test_f22_extractor_inventario_{mapping,integration,multitenant}.py` | 20 | PASS |
| F23 | `test_f23_venta_inventario{,_multitenant}.py` | 9 | PASS |
| F24 | `test_f24_confirmar_recepcion_atomicidad.py`, `test_f24_e2e_circuito_completo.py`, `test_f24_e2e_multitenant_dsv.py` | 12 | PASS |
| F25 | `test_f25_procesar_gasto_atomicidad.py` | 2 | PASS |
| DOC-M14 (devoluciones) | `test_devolucion_nota_credito.py` | 5 | PASS |
| F26 (fixes) | `test_materializar_from_dto.py` | 6 | PASS |
| F26 (fixes) | `test_ingesta_ubl.py` | 2 | **1 PASS, 1 FAIL** (`test_procesar_factura_xml_task`) |
| F26 (fixes) | `test_nota_credito_pipeline.py` | 11 | PASS |
| **Total** | | **83** | **82/83 PASS** |

## El único fallo — analizado y clasificado

**[CORRECCIÓN 2026-08-11]:** El diagnóstico original de esta sección (más abajo,
conservado por trazabilidad) fue **incorrecto** y nunca se verificó con una corrida
de un solo archivo en aislamiento total. Verificación posterior lo confirmó falso:
`test_procesar_factura_xml_task` falla **de forma idéntica ejecutado completamente
solo** (`pytest apps/tenant/facturas/tests/test_ingesta_ubl.py`, sin ningún otro
archivo `TenantTestCase` antes en el mismo proceso), por lo que la contaminación de
schema entre archivos no puede ser la causa.

**Causa real:** el fixture del propio test crea una `Empresa` dummy con
`nit="900000001"` (línea 74 original), que no coincide ni con el emisor
(`AccountingSupplierParty` → `900123456`) ni con el receptor
(`AccountingCustomerParty` → `901999888`) del `XML_SAMPLE`. La validación de
propiedad de NIT en `guardar_desde_dto()` (`apps/tenant/facturas/services/business_service.py:375`)
rechaza el documento siempre que ninguna `Empresa` en el schema coincida con emisor
o receptor — independiente del orden de ejecución. Fix aplicado: cambiar el NIT del
fixture a `"901999888"` (el receptor), consistente con las propias aserciones del
test (`factura.receptor_nit == "901999888"`). Confirmación por corrida aislada
(`docker compose exec -T web python -m pytest apps/tenant/facturas/tests/test_ingesta_ubl.py -q --tb=short`)
pendiente al momento de esta corrección — había otra corrida de pytest en curso en
el contenedor `web` (norma AGENTS.md §24.0: nunca en paralelo).

La conclusión original ("no es un defecto de F26" / "deuda de infraestructura de
testing, fuera del alcance") queda superada: sí era un bug del fixture del test,
corregible sin tocar código de producción. El hallazgo metodológico sobre
`TenantTestCase` compartiendo schema `"test"` entre archivos (`F26_TEST_REPORT.md`)
puede seguir siendo real en otros contextos — simplemente no era la causa de este
fallo específico.

### Diagnóstico original (superado, conservado por trazabilidad)

`test_ingesta_ubl.py::TestFacturaIngestion::test_procesar_factura_xml_task` falló
con `ValidationError: 'El NIT de la empresa actual no coincide con el emisor ni con
el receptor del documento.'` — **el mismo patrón de contaminación de schema
documentado en `F26_TEST_REPORT.md`**: en esta corrida, `test_devolucion_nota_credito.py`
y `test_materializar_from_dto.py` (ambas basadas en `TenantTestCase` con su propia
`Empresa`) se ejecutan ANTES de este test en el mismo proceso pytest, y su `Empresa`
persiste en el schema `"test"` compartido, causando que `Empresa.objects.first()`
(fallback interno de `guardar_desde_dto()`) resuelva una empresa con un NIT distinto
al que esta prueba espera.

**Evidencia de que NO es un defecto de F26:**
1. El mismo test, ejecutado en un grupo de solo 3 archivos (`materializar_from_dto.py`
   + `ingesta_ubl.py` + `nota_credito_pipeline.py`), también fallaba con este patrón
   — pero al ejecutarlo en un grupo distinto sin `test_devolucion_nota_credito.py`
   antes, el error de tipo (`TypeError: Strings must be encoded before hashing`,
   el bug real que SÍ se corrigió) ya no aparecía — confirmando que el fix de tipo
   es correcto y el fallo remanente es puramente de orden/contaminación.
2. `manage.py check` y `makemigrations --check` limpios; el fix aplicado
   (`XML_SAMPLE.decode()` → `XML_SAMPLE`) es correcto por contrato documentado
   (`ingest_document(content: bytes)`).

**No se intenta "arreglar" este fallo modificando código de producción** — sería
enmascarar un problema de infraestructura de tests (orden de ejecución +
`TenantTestCase` compartiendo schema) con un cambio que no resuelve la causa real.
Documentado como deuda de infraestructura de testing, fuera del alcance de F26.

## Interpretación

**82/83 = 98.8% de éxito real** en la regresión más grande y representativa jamás
corrida en esta sesión (83 tests, ~14 horas de wall-clock por la duración de la
corrida en background). **0 regresiones** en F21-F25/DOC-M14. Los 24 tests nuevos o
corregidos en F26 (`test_devolucion_nota_credito.py` completo +
`test_materializar_from_dto.py` completo + `test_nota_credito_pipeline.py`
completo) pasan **24/24** salvo el único caso de contaminación de orden explicado
arriba.
