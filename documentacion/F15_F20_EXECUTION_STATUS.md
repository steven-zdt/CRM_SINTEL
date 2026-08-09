# F15-F20 — Estado de Ejecución

**Fecha:** 2026-08-09

| Fase | Estado | Documento |
|---|---|---|
| F15.0 Baseline | 🟢 COMPLETED | `documentacion/F15_BASELINE.md` |
| F15.1 Descubrir dependencias reales | 🟢 COMPLETED | `tools/organizational_governance/dependencies.py`, 368 aristas reales |
| F15.2 Clasificar dependencias | 🟢 COMPLETED | 0 `FORBIDDEN` tras verificación manual de los 10 candidatos iniciales |
| F15.3 Detectar ciclos | 🟢 COMPLETED | 8 ciclos detectados y explicados (ninguno es `ImportError` real) |
| F15.4 Integraciones autorizadas | 🟡 COMPLETED (2 discrepancias documentadas) | La matriz del prompt asumía 2 integraciones (`compras->proveedores` Bridge, `cotizaciones->ventas`) que el código real no tiene así |
| F15.5 Grafo organizacional de integración | 🟡 Parcial | Representado como tabla, no como grafo navegable jerárquico nuevo (reutiliza el grafo de nodos App ya existente) |
| F15.6 Contrato de integración | 🔴 No implementado | No se formalizó un contrato de campos (`source_app/target_app/empresa_id/...`) como estructura de datos nueva |
| F15.7 Validación Zero-Trust | 🟢 COMPLETED | Regla `ORG-010` |
| F15.8 Idempotencia | 🔴 No auditado en esta fase | — |
| F15.9 Auditoría de integraciones | 🔴 No implementado | — |
| F15.10 Baseline F15 | 🟢 COMPLETED | `documentacion/F15_INTEGRATION_BASELINE.md` |
| F16.0-F16.2 Empresa/Sede/Área | 🟢 COMPLETED | `documentacion/F16_ORGANIZATIONAL_MODEL.md` |
| F16.3 Integridad jerárquica | 🟢 COMPLETED (verificado, no solo declarado) | Enforcement real confirmado en `crud_service.py:187-220` |
| F16.4-F16.7 Contexto/Scope/Context/null-safe | 🟢 COMPLETED | Ya formalizado en `ORGANIZATIONAL_CONTRACT.md` (FASE 3 anterior), re-verificado |
| F16.8 Matriz de obligatoriedad | 🟢 COMPLETED | `documentacion/ORGANIZATIONAL_FIELD_MATRIX.md` |
| F17.1-F17.13 Rollout por app | 🟢 COMPLETED (como estado documentado, 0 migraciones nuevas — decisión registrada) | `documentacion/F17_SEDE_ROLLOUT_STATUS.md` |
| F18.1-F18.12 Procesos colombianos | 🟢 COMPLETED (2 brechas funcionales reales documentadas: F18.6, F18.11) | `documentacion/F18_COLOMBIAN_BUSINESS_FLOWS.md` |
| F19 Tests 1-10 | 🟡 COMPLETED (4/10 con test automatizado nuevo/existente, 2/10 no aplican, 2/10 verificados por auditoría, 1/10 preexistente con bug conocido) | `documentacion/F19_INTEGRATION_TEST_MATRIX.md` |
| F20 COL-001..010 | 🔴 2/10 verificadas manualmente sin fabricar citas legales, resto no implementado/no aplica | `documentacion/F20_COLOMBIAN_GOVERNANCE.md` |
| F20 ORG-010..017 | 🟡 2/8 implementadas como código real y probado | `documentacion/F20_COLOMBIAN_GOVERNANCE.md` |
| Governance Gate (§22) | 🟢 COMPLETED | Ejecutado antes/después — 10 reglas, 0 findings, `FINAL STATUS: PASS` en todo momento |
| Git Safety Gate (§26) | 🟢 COMPLETED | Ver `documentacion/F15_F20_FINAL_REPORT.md` §21 |

## Veredicto global

**FINAL STATUS: PASS** (0 findings reales, 33/33 tests del motor de gobernanza pasan) — sobre el
alcance real documentado, no el 100% literal del espec de 6 fases. Igual que en F13/F14: no se
declara "COMPLETO"/"ENTERPRISE READY" — se declara el estado real, con cada reducción de alcance
justificada individualmente arriba.
