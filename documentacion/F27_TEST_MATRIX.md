# F27 — Matriz de Decisión Aplicada

Matriz real (no plantilla) — cada fila es una decisión efectivamente tomada
en esta fase, con su evidencia.

| Situación real encontrada | Acción (regla F27 §10) | Ejecutado | Evidencia |
|---|---|---|---|
| `test_procesar_factura_xml_task`: fixture con NIT que no coincide con el XML | CORREGIR | Sí | `F27_FINDINGS.md` F27-001 |
| `test_importar_ubl_service.py`: XML con estructura de NIT equivocada + assertions de contrato viejo | CORREGIR | Sí (5/5 tests) | `F27_FINDINGS.md` F27-002 |
| `test_naturaleza_import_ubl.py`: mismo bug de XML + `TenantTestCase` sin urlconf + falta `async=false` + endpoint deprecado con cobertura duplicada | CONSOLIDAR/ELIMINAR (recomendado) | **No** (documentado, no ejecutado — ver razón) | `F27_FINDINGS.md` F27-004 |
| `tests/celery/test_tasks_import.py` == `tests/celery_tasks/test_tasks_import.py` (byte-idéntico) | ELIMINAR (uno de los dos) | **No** (bloqueado por permisos, recomendación lista) | `F27_FINDINGS.md` F27-005 |
| `test_naturaleza_rule_ssot.py` vs `test_naturaleza_unit.py` (mismo `norm_nit`, nombres casi idénticos) | CONSOLIDAR/PARAMETRIZAR (recomendado) | No (fuera de alcance de esta pasada) | `F27_TEST_INVENTORY.md` §3c |
| 9 archivos en `tests/tenant/facturas/` repiten el mismo contrato de upload-ubl | CONSOLIDAR (recomendado) | No (fuera de alcance de esta pasada) | `F27_TEST_INVENTORY.md` §3a |
| 3 archivos repiten "list retorna 200" | CONSOLIDAR (recomendado) | No (fuera de alcance de esta pasada) | `F27_TEST_INVENTORY.md` §3b |
| `ItemNotaCredito`: el grafo de impacto solo ve 1 archivo de test | Investigar antes de asumir hueco | Sí — confirmado que es subestimación del grafo, no hueco real | `F27_COVERAGE_MAP.md` |
| Cobertura de `NotaCredito`/`ENTRADA_DEVOLUCION` | Verificar suficiencia antes de crear | Sí — suficiente, NO CREAR | `F27_COVERAGE_MAP.md` |
| Selector de tests / test impact analysis | Buscar antes de construir | Sí — `tools/ekg/impact.py` ya existe y funciona, reutilizado (regenerando su dump) | `F27_SELECTIVE_TESTING.md` |
| `TenantTestCase` vs `SintelTenantTestCase`: ¿contaminación real entre archivos? | Demostrar, no asumir | Sí — refutado para el caso puntual (F27-001), confirmado un problema real distinto (F27-003) | `F27_FINDINGS.md` F27-003 |

## Tests nuevos creados en F27

**0.**

Ningún caso encontrado en esta fase cumplió los 5 criterios de F27 §63
("no existe test equivalente, no existe cobertura indirecta, no puede
ampliarse uno existente, el comportamiento es relevante, aporta una
garantía nueva"). Todos los problemas reales encontrados fueron de tests
**existentes rotos** (corregibles) o **redundantes** (documentados para
consolidación futura), nunca de cobertura ausente. Resultado explícitamente
válido y preferido según la regla F27 §59.

## Tests corregidos

**7** (2 en `test_ingesta_ubl.py`... no, 1 en `test_ingesta_ubl.py` +
5 en `test_importar_ubl_service.py` = 6 tests con assertions/fixtures
tocadas; el 7mo cambio es la reescritura completa de `test_422_sin_empresa`
que cuenta dentro de los 5 de `test_importar_ubl_service.py`). Total real:
**6 tests corregidos**, 2 archivos.

## Tests eliminados

**0 ejecutados** (1 confirmado y recomendado — `tests/celery/test_tasks_import.py`
— bloqueado por el clasificador de permisos de la sesión, no por falta de
evidencia).

## Tests consolidados / parametrizados

**0 ejecutados** en este pase (3 clusters identificados y documentados con
evidencia completa para una fase dedicada — ver `F27_TEST_INVENTORY.md` §3).
