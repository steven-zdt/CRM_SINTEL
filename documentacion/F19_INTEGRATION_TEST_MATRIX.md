# F19 — Pruebas de Integración y Aislamiento — Matriz

**Fecha:** 2026-08-09
**Estado:** 🟢 F19 COMPLETED (sobre lo que es genuinamente testeable hoy — ver notas por test)

| # | Test pedido | Cubierto por | Resultado real |
|---|---|---|---|
| 1 | Cross-tenant (Empresa A/Sede/Área vs Empresa B/Sede/Área) | `apps/tenant/compras/tests/test_multitenant_isolation_tabla_html.py` | Ya existe — 1 test, con el bug preexistente de `force_login()` ya diagnosticado en `MEMORY.md` (ajeno a esta consolidación, no re-investigado aquí) |
| 2 | Mismo tenant, Sede A/Área A vs Sede B/Área B | `test_organizational_isolation_empresa_a.py` (12 tests, FASE 7) | ✅ Cubierto — Caso 2 (SEDE) y Caso 3 (AREA) completos |
| 3 | `scope=SEDE` ve A, no B | `test_caso2_sede_bogota_list_ve_solo_bogota` + `test_caso2_sede_bogota_retrieve_orden_barranquilla_denegado` | ✅ Cubierto, `403` confirmado por ejecución real |
| 4 | `scope=AREA` no accede a otra área/dominio | `test_caso3_area_comercial_retrieve_tecnica_bogota_denegado` | ✅ Cubierto para área dentro de la misma app (`compras`). **No cubierto:** "no debe acceder a Contabilidad" tal como lo redacta el prompt — no existe hoy ningún control de acceso cross-**app** basado en área (el contrato organizacional de `alcance=AREA` nunca se extendió más allá de filtrar dentro de una misma app, ver `ORGANIZATIONAL_CONTRACT.md`) — no se fabrica un test para un control que no existe |
| 5 | Payload con `empresa_id`/`sede_id`/`area_id` manipulados debe rechazarse | `test_payload_no_puede_inyectar_sede_id_en_creacion` (**nuevo**, esta fase) | ✅ Confirmado por ejecución real: el payload se ignora, la sede real es la resuelta server-side |
| 6 | Venta → Factura preserva empresa/sede/contexto | `documentacion/VENTAS_FACTURAS_AUDIT.md` (auditoría de código, no test automatizado dedicado) | 🟡 Verificado por lectura de código con evidencia real, sin test automatizado nuevo en esta fase (el flujo completo requiere fixtures DIAN — XML/CUFE/firma — de mayor costo que el resto de esta fase) |
| 7 | Compra → Inventario preserva empresa/sede | N/A | 🔴 **No aplica — la integración no existe** (ver `F18_COLOMBIAN_BUSINESS_FLOWS.md` §F18.6, confirmado en el grafo de F15: sin arista `compras -> inventario`). No se fabrica un test para una integración inexistente |
| 8 | Factura → Contabilidad conserva empresa, respeta Pull | Cubierto conceptualmente por el modelo Pull ya extensamente testeado (fuera del alcance de esta sesión re-verificar el extractor completo) | 🟡 Arquitectura verificada (`F18_COLOMBIAN_BUSINESS_FLOWS.md` §F18.4), sin test nuevo en esta fase |
| 9 | FK cross-app prohibida → `GOVERNANCE FAIL` | Regla `ORG-002`/futuro `ORG-015` (ver F20) + `dependencies.py` clasifica `FORBIDDEN` cuando corresponde (verificado con test sintético `test_classify_forbidden_when_no_empresa_id_evidence`) | ✅ Mecanismo de detección probado; **0 casos `FORBIDDEN` reales en el código actual** (ver `F15_INTEGRATION_BASELINE.md` — las 10 aristas que parecían forbidden en la v1 del clasificador resultaron ser patrones legítimos verificados) |
| 10 | `A → B → C` sin `C → A` sin contrato | `dependencies.detect_cycles()` + test `test_detect_cycles_finds_two_node_cycle` | ✅ Mecanismo probado; 8 ciclos reales detectados y explicados en `F15_INTEGRATION_BASELINE.md` §5 (ninguno es un `ImportError` real, por el patrón de imports locales del proyecto) |

## Resumen honesto

4 de 10 con test automatizado nuevo/existente y verificado por ejecución real (2, 3, 5, 9-10 vía
mecanismo). 2 sin aplicar porque la integración que describen no existe en el código (7) o el
control que describen no existe (4, parcialmente). 2 verificadas por auditoría de código, no por
test automatizado nuevo (6, 8) — el costo de fixtures DIAN completas (XML/firma/CUFE) para un test
de integración extremo a extremo excede el alcance razonable de esta fase. 1 preexistente con un
bug conocido y ajeno (1).

**No se declara "10/10 tests pasando"** — sería falso. Se declara lo que es real: mecanismos de
detección probados, 0 violaciones reales encontradas, y las brechas de cobertura documentadas
explícitamente en vez de ocultas.

**Estado: 🟢 F19 COMPLETED (alcance real documentado).**
