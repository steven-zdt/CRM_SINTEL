---
name: sintel-mcp-code-repair
description: Audita y corrige defectos relacionados con MCP/CRUD sin cambios no autorizados ni duplicación arquitectónica.
---
# CODE REPAIR

Ciclo: `OBSERVE → AUDIT → FINDING → ROOT CAUSE → PROPOSE → TEST PLAN → APPROVAL → APPLY → TEST → VERIFY → DOCUMENT`.

`propose_code_fix` nunca modifica. Debe indicar archivo/líneas, evidencia, causa, impacto, solución, archivos afectados, tests, riesgo y rollback.

`apply_code_fix` exige autorización explícita. Bloquear si falta evidencia, causa raíz incierta, migración destructiva, conflicto o test plan.

Prohibido desde MCP: shell/Python/SQL arbitrario, `rm -rf`, `DROP DATABASE`, `DROP SCHEMA`, `TRUNCATE`, `docker system prune`, `docker compose down -v`, `git reset --hard`.

Antes de crear servicio/tool nuevo: buscar equivalente, EKG, AIToolRegistry, Service Layer y utilidades compartidas.
