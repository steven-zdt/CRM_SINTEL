# F27 — Mapa de Cobertura (facturas, símbolos críticos)

Generado con el impact engine reutilizado (`tools/ekg/impact.py`, ver
`F27_SELECTIVE_TESTING.md`) sobre el dump regenerado de `facturas`
(368 nodos, 430 aristas). Cobertura = archivos de test conectados por
`TESTED_BY` al símbolo o a cualquier nodo impactado por él (Serializers,
ViewSets, Endpoints que dependen de ese símbolo).

**Limitación conocida del grafo** (documentada en `impact.py`, no
introducida por F27): `TESTED_BY` solo se resuelve cuando el test importa o
referencia el símbolo de forma reconocible por el extractor estático — un
test que ejercita un modelo solo indirectamente vía una llamada HTTP de
alto nivel puede no aparecer aquí aunque sí lo cubra en la práctica (ver
`test_nota_credito_pipeline.py`, que cubre `ItemNotaCredito` end-to-end vía
`guardar_desde_dto()` pero no aparece en su columna de tests abajo — la
cobertura real es mayor a la que el grafo puede ver).

| Símbolo | Nodos impactados | Archivos de test conectados (`TESTED_BY`) | Lectura |
|---|---|---|---|
| `Model:Factura` | 17 | **35 archivos** (ver lista completa corrida en esta fase) | Sobre-cubierto en cantidad de archivos — consistente con el hallazgo de duplicación de `F27_TEST_INVENTORY.md` §3a/3b (9 archivos solo para upload-ubl, 3 solo para "list retorna 200"). Cantidad de archivos ≠ calidad de cobertura. |
| `Service:FacturaBusinessService` | 9 | 4 (`test_devolucion_nota_credito.py`, `test_nota_credito_pipeline.py`, `test_organizational_context_adoption.py`, `test_scope_ventas_facturas_f10.py`) | El grafo solo resuelve el import directo de la clase; `guardar_desde_dto()` (el método más crítico) se ejercita también desde `test_materializar_from_dto.py`/`test_importar_ubl_service.py`/`test_naturaleza_import_ubl.py` vía funciones wrapper (`materializar_factura_desde_result`, `importar_ubl`) que el extractor no conecta de vuelta al Service — subestimación conocida, no un hueco real. |
| `Model:NotaCredito` | 6 | 2 (`test_devolucion_nota_credito.py`, `test_nota_credito_pipeline.py`) | Cobertura real y suficiente — confirmado por lectura directa de ambos archivos (17 tests entre los dos, ver `F27_TEST_INVENTORY.md` §4.1), no solo por el conteo del grafo. |
| `Model:ItemNotaCredito` | 1 | 1 (`test_devolucion_nota_credito.py`) | El grafo solo ve 1 archivo, pero `test_nota_credito_pipeline.py` también crea `ItemNotaCredito` indirectamente (vía `dto["items"]` en el pipeline completo) — cobertura real mayor a la que el grafo reporta (ver limitación arriba). No se creó un test nuevo para "cerrar" este hueco aparente porque no es un hueco real (regla F27 §59: NO CREAR si la cobertura indirecta ya es suficiente). |

## Funciones críticas auditadas individualmente (F27.3)

| Función | Tests directos | Tests indirectos | Casos no cubiertos identificados |
|---|---|---|---|
| `FacturaBusinessService.guardar_desde_dto()` | `test_materializar_from_dto.py` (7), `test_devolucion_nota_credito.py` (5) | `test_nota_credito_pipeline.py`, `test_importar_ubl_service.py`, `test_naturaleza_import_ubl.py` (vía wrappers) | Ninguno nuevo encontrado en F27 — F26 ya cubrió atomicidad/idempotencia exhaustivamente (ver `F25_FINDINGS.md`, `F26_FINDINGS.md` F26-006). |
| `FacturaBusinessService._generar_entrada_devolucion()` | `test_devolucion_nota_credito.py` (5 escenarios: resoluble, sin match, multi-item, reimport idempotente, NC sin items) | `test_nota_credito_pipeline.py` (E2E) | Ninguno — cobertura completa desde DOC-M14. |
| `importar_ubl()` (`[COMPAT]` wrapper) | `test_importar_ubl_service.py` (5/5, corregidos en F27-002) | — | Cerrado en este pase. |
| `upload_ubl()` (endpoint deprecado) | `test_naturaleza_import_ubl.py` (roto, ver F27-004), 9 archivos en `tests/tenant/facturas/` (ver `F27_TEST_INVENTORY.md` §3a) | — | Cobertura real existe (9 archivos), pero duplicada — no es un hueco, es un exceso. |

## Conclusión de cobertura

No se identificó ningún caso de **cobertura realmente inexistente** que
justifique crear un test nuevo (criterio F27 §63). Los huecos aparentes
(`ItemNotaCredito` con "solo 1 archivo" según el grafo) resultaron ser
subestimaciones del grafo estático, no huecos reales, verificado por
lectura directa del código de test. El problema real de la suite de
`facturas` no es falta de cobertura — es **exceso de archivos duplicados
cubriendo el mismo contrato** (ver `F27_TEST_INVENTORY.md` §3) combinado
con **tests rotos por deriva de contrato** (F27-001 a F27-004), no huecos.
**0 tests nuevos creados en F27** — resultado esperado y preferible según
la regla F27 §59.
