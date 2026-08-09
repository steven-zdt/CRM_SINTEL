# Governance Remediation Plan

**Fecha:** 2026-08-09

## Findings contra el código real (las 8 reglas implementadas)

**Ninguno.** `python -m tools.organizational_governance.cli --report` sobre el estado real del
repositorio (commit base `34fc020` + el trabajo de F13/F14 en curso) produce `0 findings` en las
8 reglas implementadas (`ARCH-002`, `SEC-001`, `SEC-002`, `SEC-003`, `ORG-001`, `ORG-002`,
`ORG-004`, `TEST-001`). Esto es consistente con — no una casualidad de — el trabajo de FASE 0-7 de
la consolidación OCF/OSF anterior, que encontró y corrigió exactamente los 2 bugs reales que
`SEC-002`/`SEC-003` fueron diseñadas para detectar.

No se fabrica un finding para tener contenido que remediar — un plan de remediación vacío porque
no hay nada que remediar es el resultado correcto y honesto, no una omisión.

## Findings encontrados y corregidos DURANTE el desarrollo del motor (no contra el código objetivo)

Estos 3 casos no son findings del `governance_check` contra SINTEL — son bugs reales en las
propias reglas de `tools/organizational_governance/`, encontrados por smoke-test antes de confiar
en el resultado (disciplina ya aplicada en toda la consolidación anterior, ver `OCF_TECHNICAL_AUDIT.md`).

| # | Root Cause | Affected Component | Fix | Tests |
|---|---|---|---|---|
| 1 | `ARCH-002` usaba texto crudo y marcaba `SintelTenantBaseModel` (la raíz del árbol) como violación de sí misma | `rules._detect_arch_001_002` | Excluir explícitamente la clase raíz | `test_arch_002_does_not_fire_on_the_base_class_itself` |
| 2 | `ORG-004` usaba `re.finditer` sobre texto crudo, coincidía con `filter_by_scope(` dentro de un docstring de `facturas/services/selectors.py` que dice "no filter_by_scope()" (explicando lo contrario) | `rules._detect_org_004_strict_filter_without_hardening` | Reescrito con AST (`ast.Call` real, nunca ve docstrings) | `test_org_004_does_not_fire_on_docstring_mention_regression_guard` |
| 3 | `extract.app_uses_organizational_scope()` usaba texto crudo, contaba `ventas` como consumidor de `OrganizationalScope` porque su docstring dice literalmente "no OrganizationalScope" (explicando que usa `OrganizationalContext`) | `extract.app_uses_organizational_scope/context` | Reescrito con AST (`_file_has_real_reference`) | `test_app_uses_organizational_scope_ignores_negated_docstring_mention` |

**Contrato arquitectónico relevante en los 3 casos:** "precisión > cantidad de findings" (F14.24
del prompt maestro) — un motor de gobernanza que reporta falsos positivos pierde la confianza que
lo justifica; se priorizó corregir cada uno antes de generar cualquier reporte citable.

## Findings NO cubiertos por ninguna regla implementada (deuda declarada, no oculta)

Heredados de la auditoría OCF/OSF anterior, sin regla automática que los detecte hoy:
- Triplicación de `empresa_id` sin test de paridad completo (`OCF_TECHNICAL_AUDIT.md` §1).
- Asimetría NULL entre `filter_by_scope_null_safe()`/`HasOrganizationalScope` (`OSF_TECHNICAL_AUDIT.md` §4).
- `FacturaInterAppAPI` sin filtro `empresa_id` (`FACTURAS_AUDIT.md` §2, riesgo D-4 de ADR-004).

Ninguno de los 3 se convirtió en una regla `ORG-*`/`SEC-*` nueva en esta sesión — implementarlos
correctamente (sin falsos positivos, siguiendo la misma disciplina de arriba) es trabajo real
adicional, documentado como pendiente en `documentacion/F13_F14_FINAL_REPORT.md`, no fabricado.
