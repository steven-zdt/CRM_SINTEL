---
name: sintel-mcp-implementation
description: Prompt por fases para implementar las skills MCP en SINTEL sin romper módulos existentes.
---
# IMPLEMENTATION PROMPT

## F0 INSPECT
No modificar. Auditar `/mcp/`, `django-rest-framework-mcp`, `apps/services/ai`, AIToolRegistry, AIEngine, AIContext, Service Layer, permisos, tenant middleware, EKG, RAG y tests. Crear `MCP_BASELINE.md`.

## F1 DISCOVERY
Implementar `project_inventory`, `domain_inventory`, `inspect_model`, `inspect_api`, `inspect_service`, `crud_capabilities`. Sin WRITE.

## F2 READ
Implementar `read_record`, `list_records`, `search_records`, `get_related_records`. Probar auth, authz, tenant y secretos.

## F3 VALIDATE/DRY RUN
Implementar validadores y dry-run. No persistir ni generar side effects.

## F4 WRITE
Habilitar dominio por dominio después del gate. Secuencia técnica sugerida: clientes, inventario, proveedores, proyectos, compras, ventas, cotizaciones, facturas, bancos, empleados, gastos, empresa, perfil, contabilidad. Esta secuencia no es ranking funcional.

## F5 DOMAIN ACTIONS
Registrar solo acciones reales descubiertas en BusinessServices.

## F6 AUDIT/REPAIR
Implementar auditorías, impact analysis, proposal y apply controlado.

## F7 AI INTEGRATION
Conectar MCP con AIToolRegistry, AIEngine, AIContext, EKG y RetrievalTool. No crear herramientas AI paralelas.

## F8 FLAGS
Usar configuración existente o equivalente para `MCP_ENABLED`, `MCP_READ_ENABLED`, `MCP_AUDIT_ENABLED`, `MCP_VALIDATE_ENABLED`, `MCP_DRY_RUN_ENABLED`, `MCP_WRITE_ENABLED`, `MCP_CODE_REPAIR_ENABLED`. Defaults seguros.

## F9 RELEASE
Ejecutar tests MCP, focalizados, cross-tenant, authz negativa, idempotencia, dry-run, audit, check, migrations check, governance y production readiness.

## Gate final
No declarar MCP operacional si existe bypass ORM, falla tenant isolation/authz, se salta Service Layer, fallan tests críticos, se exponen secretos o un efecto externo puede ejecutarse sin control.

## Reporte
`STATUS / DOMAINS / READ / VALIDATE / DRY RUN / WRITE / ACTIONS / BLOCKED / DEFERRED / SECURITY / TESTS / ROLLBACK / EVIDENCE`.
