# F27 — Reporte de Regresión

**Fecha:** 2026-08-11

## Corrida 1 — Suite completa de `apps/tenant/facturas/tests/` (baseline real, 30 archivos)

```bash
docker compose exec -T web python -m pytest apps/tenant/facturas/tests/ -q --tb=line
```
```
31 failed, 110 passed, 4 skipped in 3771.39s (1:02:51)
```

Corrida ANTES de los fixes de F27 (después de aplicar solo el fix de
`test_procesar_factura_xml_task`, F27-001). Confirma el alcance real:
31 fallos, no los ~18 "históricos" de F26 ni una cifra menor — la mayoría
(no verificados uno por uno, ver `F27_EXECUTION_STATUS.md` "reducción de
alcance") comparten el patrón `NoReverseMatch` de F27-003
(`test_factura_detail_anexos_api.py`, `test_facturas_list_detail_payloads.py`,
`test_import_ubl_heavy_payload.py`, `test_upload_async_flow.py`,
`test_services_ingest_integration.py`, `test_multitenant_isolation_tabla_html.py`,
`test_naturaleza_import_ubl.py`) o el patrón de fixture XML de F27-002
(`test_importar_ubl_service.py`, `test_ssot_empresa_provider.py`).

## Corrida 2 — Archivos tocados en F26-006 + F27 (post-fix, aislado del resto de la suite)

```bash
docker compose exec -T web python -m pytest \
  apps/tenant/facturas/tests/test_ingesta_ubl.py \
  apps/tenant/facturas/tests/test_importar_ubl_service.py \
  apps/tenant/facturas/tests/test_naturaleza_import_ubl.py \
  apps/tenant/facturas/tests/test_materializar_from_dto.py \
  apps/tenant/facturas/tests/test_nota_credito_pipeline.py \
  apps/tenant/facturas/tests/test_devolucion_nota_credito.py \
  -q --tb=line
```
```
5 failed, 31 passed in 792.34s (0:13:12)
```

| Archivo | Tests | Resultado |
|---|---|---|
| `test_ingesta_ubl.py` | 2 | **2/2 PASS** (F27-001, `test_procesar_factura_xml_task` corregido) |
| `test_importar_ubl_service.py` | 5 | **5/5 PASS** (F27-002, fixtures + assertions corregidas) |
| `test_naturaleza_import_ubl.py` | 5 | **0/5 PASS** — falla exactamente como predijo F27-003/004 (`NoReverseMatch: factura-upload-ubl`), documentado, no corregido en este pase |
| `test_materializar_from_dto.py` | 7 | 7/7 PASS |
| `test_nota_credito_pipeline.py` | 12 | 12/12 PASS |
| `test_devolucion_nota_credito.py` | 5 | 5/5 PASS |
| **Total** | **36** | **31/36 PASS** |

**Interpretación:** los 5 fallos son el archivo completo
`test_naturaleza_import_ubl.py`, con exactamente la causa documentada en
`F27_FINDINGS.md` F27-003/F27-004 (`NoReverseMatch` por `TenantTestCase`
crudo + `reverse()` directo sin `urlconf` de tenant) — **no una regresión
nueva ni un fallo inesperado**, es el resultado predicho por el análisis de
causa raíz antes de decidir no corregirlo en este pase. 0 sorpresas.

## Comparación ANTES/DESPUÉS de F27 (mismos archivos, mismo alcance)

| Métrica | Antes de F27 | Después de F27 |
|---|---|---|
| `test_procesar_factura_xml_task` | FAIL (NIT dummy incorrecto) | **PASS** |
| `test_importar_ubl_service.py` (5 tests) | 5 FAIL (documentados, no corregidos por F26) | **5 PASS** |
| `test_naturaleza_import_ubl.py` (5 tests) | 5 FAIL (documentados, no corregidos por F26) | 5 FAIL (causa raíz ahora identificada con precisión, no corregido — ver F27-004) |
| Tests nuevos creados | — | **0** (regla F27 §59, resultado válido) |
| Tests eliminados | — | 0 ejecutados (1 duplicado byte-idéntico confirmado, bloqueado por permisos — ver F27-005) |
| Tests corregidos | — | **7** (2 + 5) |

## Regresión F21-F26 (no re-ejecutada completa en este pase)

F27 no modifica ningún modelo, migración, ni código de producción fuera de
`apps/tenant/facturas/tests/` (los únicos archivos de producción tocados en
esta sesión pertenecen a F26-006, ya regresionados y commiteados por
separado — ver `F26-006_FIX_REPORT.md`). Por la norma "Testing Progresivo
por Alcance" de `CLAUDE.md` (no correr la suite completa por defecto tras
un cambio pequeño, reservarlo para cambios transversales), y dado que F27
es estrictamente cambios en archivos de test (sin tocar
`apps/tenant/api/`, `apps/tenant/core/`, ni mixins heredados por 3+ apps),
no se re-ejecutó la regresión consolidada F21-F26 completa en esta fase —
sigue vigente el último resultado verde conocido
(`F26-006_FIX_REPORT.md`: 25/26, único fallo ya reatribuido correctamente
en F27-003).

## Quality gates

```
manage.py check                             -> System check identified no issues (0 silenced)
manage.py makemigrations --check --dry-run  -> No changes detected
```

## Governance

Ver `F27_FINAL_REPORT.md` para el resultado del CLI de gobernanza.
