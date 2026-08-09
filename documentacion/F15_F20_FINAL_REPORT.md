# F15-F20 — Reporte Final

**Fecha:** 2026-08-09

## 1. Estado inicial

Commit base `e403232`. `tools/organizational_governance/` con 165 entidades/218-220 relaciones, 8
reglas, 23/23 tests, `FINAL STATUS: PASS` (heredado del cierre de F13/F14). 74 archivos de
categoría E sin tocar. Ver `documentacion/F15_BASELINE.md`.

## 2. Estado final

`tools/organizational_governance/dependencies.py` (nuevo módulo, extiende el paquete existente):
368 aristas de dependencia inter-app reales, clasificadas, 8 ciclos detectados y explicados. Motor
de gobernanza extendido a **10 reglas** (+`ORG-010`, +`ORG-017`), **33/33 tests** pasan.
`FINAL STATUS: PASS` sostenido en todo momento. 2 conflictos con decisiones previas detectados y
resueltos sin sobrescribir silenciosamente (ver §3).

## 3. Apps analizadas

Las 17 apps tenant, por AST real (no grep de texto) — mismo mecanismo que F13/F14, extendido a
detección de imports cross-app.

## 4. Integraciones

368 aristas descubiertas. Clasificación final: `ALLOWED` 150, `CONTROLLED` 123, `PUSH_CONTROLLED`
63, `PULL` 15, `UNKNOWN` 17 (12 patrones únicos sin forzar clasificación), `FORBIDDEN` 0 (la
primera versión del clasificador marcó 10 como `FORBIDDEN` por una regla demasiado simple;
verificación manual de cada una contra el código fuente real mostró que 9 eran patrones ya
sancionados por auditorías previas — corregido antes de reportar cualquier número). Ver
`documentacion/F15_INTEGRATION_BASELINE.md` para el detalle completo, incluida la corrección
documentada como proceso, no solo como resultado.

## 5. Dependencias — ciclos

8 ciclos detectados a nivel de grafo de dependencias declaradas. Ninguno es un `ImportError` real
— el proyecto usa consistentemente imports locales (dentro de función, no a nivel de módulo) para
toda referencia cross-app, patrón ya documentado en el propio código como mitigación deliberada de
circularidad. Verificado indirectamente por `manage.py check` limpio con las 17 apps cargadas
simultáneamente.

## 6. Empresa/Sede/Área

Modelo verificado contra código real, no solo declarado: `Area.empresa_id == Area.sede.empresa_id`
**sí se aplica**, a nivel de Service Layer (`crud_service.py:187-220`), no de constraint de base
de datos — matiz real, documentado. Ver `documentacion/F16_ORGANIZATIONAL_MODEL.md` y
`documentacion/ORGANIZATIONAL_FIELD_MATRIX.md`.

## 7. Rollout

**0 migraciones nuevas ejecutadas.** Decisión registrada, no un olvido: el propio §5 del prompt
maestro de esta fase prohíbe la migración masiva sin necesidad de dominio demostrada, y esa
necesidad ya fue analizada y descartada para 5 de las 6 apps pendientes en FASE 10 de la
consolidación anterior. Conflicto real detectado con F17.2 (pedía migrar `ventas`, decisión
explícita del usuario 2 turnos antes fue no hacerlo) — resuelto manteniendo la decisión vigente
como SSoT, sin re-litigarla, sin pedir autorización de nuevo (consistente con "no preguntar entre
fases" del §0). Ver `documentacion/F17_SEDE_ROLLOUT_STATUS.md`.

## 8. Facturación DIAN

Estados reales verificados (`BORRADOR/ENVIADA/ACEPTADA/RECHAZADA/ANULADA` + `EstadoPago`
independiente), CUFE existe como campo. Sin certificación de cumplimiento del Anexo Técnico DIAN
(fuera de alcance verificable en esta sesión). Ver `documentacion/F18_COLOMBIAN_BUSINESS_FLOWS.md`
§F18.2.

## 9. Contabilidad

Pull Model ya documentado y re-verificado (`facturas` nunca crea `AsientoContable` directamente —
0 referencias, confirmado por grep). Sin concepto `RegulatoryVersion`/Grupo 1-2-3 (no existe en el
código, no se fabricó).

## 10. Nómina

`TransmisionNominaDIAN` confirmado como modelo separado de `Devengo`/`Contrato` — separación
conceptual nómina interna/DIAN ya existe.

## 11. Bancos

Control real verificado: `Factura` no puede marcarse `PAGADA` sin conciliación 100% en bancos
(`business_service.py:915-928`) — el control que F18.3 pedía **ya existía**, confirmado, no
fabricado.

## 12. Inventario

2 brechas funcionales reales documentadas, no ocultas: `compras -> inventario` (recepción de
`OrdenCompra` no genera `MovimientoInventario` automáticamente hoy) y traslados entre sedes (no
implementado, ni silencioso ni explícito — el campo `sede` de inventario ni siquiera está
endurecido).

## 13. Protección de datos

Aislamiento técnico entre tenants (schema PostgreSQL) verificado y ya garantizado por diseño
arquitectónico previo. Sin auditoría específica de Ley 1581 (consentimiento, minimización,
derechos ARCO) — declarado explícitamente fuera de alcance, no fabricado.

## 14. Tests

`tools/organizational_governance/tests/`: **33/33 pasan** (`docker compose exec web python -m
pytest tools/organizational_governance/tests/ -q` → `33 passed in 10.15s`). 1 test nuevo de
integración real: `test_payload_no_puede_inyectar_sede_id_en_creacion` (`apps/tenant/compras/tests/`),
verificado por ejecución real (`1 passed in 176.04s`, incluye el setup completo de schema tenant).

## 15. Governance

```
python -m tools.organizational_governance.cli --report
KNOWLEDGE GRAPH: Entities 165, Relations 218-220
ARCHITECTURE PASS:1 SECURITY PASS:3 ORGANIZATIONAL PASS:4 INTEGRATIONS PASS:1 TEST_COVERAGE PASS:1
FINAL STATUS: PASS
```

## 16. Knowledge Graph

Extendido con `dependencies.py` (grafo de aristas inter-app, separado del grafo de nodos
App/Model/ViewSet/Permission/ADR/GitCommit ya existente de F13 — no fusionados en una sola
estructura en esta fase, oportunidad de consolidación futura).

## 17. Findings

0 reales contra el código actual, en las 10 reglas implementadas.

## 18. Correcciones

1 corrección real durante el desarrollo: el clasificador de dependencias (v1) marcaba 10 aristas
legítimas como `FORBIDDEN` — corregido tras verificación manual contra el código fuente real de
cada una, documentado en `F15_INTEGRATION_BASELINE.md` §3 como proceso, no ocultado.

## 19. Riesgos

Heredados sin cambios de la consolidación OCF/OSF anterior (`GOVERNANCE_REMEDIATION_PLAN.md`) +
2 brechas funcionales nuevas documentadas en §12 de este reporte (compras→inventario, traslados
entre sedes) — ninguna es una regresión, ambas son ausencia de funcionalidad ya conocida, ahora
formalmente registrada.

## 20. Deuda técnica

`F15.6` (contrato de integración formal) y `F15.9` (auditoría de integraciones) no implementados.
`ORG-011/012/013/014` no convertidas en reglas automáticas (verificadas manualmente en su lugar).
`COL-001/003/004/009` no implementados (requieren investigación legal o consulta de datos en
runtime, fuera del alcance de un motor estático).

## 21. Git

```bash
git status --short   # confirmado antes del commit: solo archivos de F15-F20 + docs de
                      # sincronizacion, los 74 de categoria E sin tocar
git diff --check      # sin conflictos de whitespace
```

Commit(s): ver hash real en el mensaje de cierre de esta sesión — un solo commit cohesivo (mismo
criterio que F13/F14: no crear separaciones artificiales entre partes que se desarrollaron y
probaron juntas dentro de la misma sesión).

## 22. Estado normativo

**Cobertura técnica verificada, no certificación legal** — ver
`documentacion/COLOMBIA_COMPLIANCE_TRACEABILITY.md` y la advertencia obligatoria en
`documentacion/F20_COLOMBIAN_GOVERNANCE.md`. Ningún hallazgo de esta fase debe interpretarse como
una afirmación de cumplimiento ante la DIAN, la CTCP, o cualquier autoridad colombiana.

---

**FINAL STATUS: PASS, sobre el alcance real documentado en este reporte y en
`documentacion/F15_F20_EXECUTION_STATUS.md`.**
