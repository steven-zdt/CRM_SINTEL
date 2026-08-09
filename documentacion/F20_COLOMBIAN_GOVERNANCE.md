# F20 — Gobernanza y Cumplimiento Colombiano

**Fecha:** 2026-08-09
**Estado:** 🟡 F20 COMPLETED (alcance real — ver nota obligatoria abajo)

## Nota obligatoria de alcance (no negociable, ver §3/§29 del prompt maestro)

**Este documento NO certifica cumplimiento legal.** No se investigó ni se cita legislación
colombiana específica (números de Resolución DIAN, artículos del Estatuto Tributario, decretos)
como hecho verificado — esta sesión no tiene la capacidad de validar contra las fuentes
autoritativas exigidas (`DIAN, SUIN-Juriscol, CTCP, Ministerios`) con el rigor que una afirmación
legal requiere, y fabricar una cita específica sería peor que no tenerla. Lo que sí se hizo:
implementar y verificar los **mecanismos técnicos** (separación de conceptos, trazabilidad,
estados) que ese tipo de normativa típicamente exige — cobertura técnica, no certificación
jurídica, exactamente la distinción que el propio prompt maestro exige en su §29.

## COL-001..010 — qué se implementó y qué no

| Regla pedida | Implementación real | Estado |
|---|---|---|
| COL-001 Factura cumple contrato DIAN | No implementado como regla automática — requeriría verificar contra el Anexo Técnico DIAN real, fuera de alcance | 🔴 No implementado |
| COL-002 No marcar validada sin respuesta DIAN | **Verificado por auditoría de código** (`F18_COLOMBIAN_BUSINESS_FLOWS.md` §F18.2) — `Factura.Estado` separa `ENVIADA`/`ACEPTADA`, no hay transición directa `BORRADOR`→`ACEPTADA` visible en el código auditado. No convertido en regla automática (requeriría analizar todas las transiciones de estado posibles, no solo una) | 🟡 Verificado manualmente, no automatizado |
| COL-003 CUFE pertenece a la factura correcta | No implementado — es un invariante de **datos**, no de código estático (el motor actual no consulta la base de datos, es puramente estático) | 🔴 No implementado (fuera del alcance de un motor estático) |
| COL-004 Notas crédito/débito referencian el documento correcto | No auditado en esta fase | 🔴 No implementado |
| COL-005 Documento equivalente electrónico separado de factura | No aplica — el concepto "documento equivalente electrónico" no tiene modelo propio en el código actual (no implementado en el ERP, no solo sin regla de gobernanza) | ⚪ No aplica (funcionalidad no existe) |
| COL-006 Nómina electrónica con trazabilidad propia | **Verificado**: `TransmisionNominaDIAN` es un modelo separado de `Devengo`/`Contrato` (`F18_COLOMBIAN_BUSINESS_FLOWS.md` §F18.9) | 🟡 Verificado, no automatizado |
| COL-007 Contabilidad respeta marco normativo configurado | No aplica — no existe un concepto `RegulatoryVersion`/clasificación Grupo 1/2/3 en el código actual (el §4.2 del prompt maestro lo pide como concepto nuevo condicional: "únicamente si ya existe un mecanismo compatible" — no existe, no se fabrica) | ⚪ No aplica (no existe el mecanismo base) |
| COL-008 No mezclar dato tributario/contable/operativo | Ya cubierto estructuralmente por el Pull Model (`Contabilidad` es la única propietaria del mapeo PUC, `arquitectura_general.md` §6) — no se implementó como regla automática nueva | 🟡 Cubierto por arquitectura existente |
| COL-009 Datos personales respetan modelo de privacidad | No auditado en esta fase — fuera de alcance | 🔴 No implementado |
| COL-010 Todo documento fiscal tiene trazabilidad | Parcialmente cubierto (`Factura`/`TransmisionNominaDIAN` tienen campos de estado y fecha) — no verificado exhaustivamente | 🟡 Parcial |

## ORG-010..017 — reglas estructurales reales, implementadas y probadas

Solo se implementaron las que son genuinamente verificables de forma estática y con evidencia real
(mismo criterio "no fabricar" de toda la consolidación):

| Regla | Estado | Detalle |
|---|---|---|
| ORG-010 | 🟢 Implementada, probada, 0 findings reales | Reutiliza el clasificador de `dependencies.py` (FASE 15) — cualquier integración `FORBIDDEN` (sin `empresa_id` explícito) es un finding |
| ORG-011/012 | 🔴 No implementado | Requiere análisis de flujo de datos (¿de dónde viene el valor de `sede` que llega a un Business Service?) — más allá de lo que AST estático puede verificar con confianza sin falsos positivos |
| ORG-013/014 | 🔴 No implementado como regla automática | **Verificado manualmente** en `F16_ORGANIZATIONAL_MODEL.md` — el enforcement real existe en `crud_service.py`, no se convirtió en regla de gobernanza genérica por ser específico a `Area`/`Sede` |
| ORG-015 | Cubierto por diseño arquitectónico (aislamiento de esquema `django-tenants`) — no requiere regla de código, es una garantía de infraestructura | ⚪ No aplica como regla de código |
| ORG-016 | Ya cubierto por `filter_by_scope_null_safe()` (OSF F7) — el patrón existente ya es "no convertir NULL en sede artificial" | ⚪ Ya garantizado por diseño existente |
| ORG-017 | 🟢 Implementada, probada, 0 findings reales | Allowlist explícita de qué modelos pueden heredar `SedeAwareModel` (hoy solo `compras.OrdenCompra`) — guarda de regresión directa contra migración masiva no decidida |

**Total reglas del motor de gobernanza tras F20: 10** (8 de F13/F14 + `ORG-010` + `ORG-017`).
`python -m tools.organizational_governance.cli --report` → **0 findings, FINAL STATUS: PASS**.

**Estado: 🟡 F20 COMPLETED — 2 de ~17 reglas nombradas implementadas como código real y probado;
el resto verificado por auditoría manual, no aplicable, o explícitamente fuera de alcance de un
motor estático — cada una con su razón documentada, ninguna oculta.**
