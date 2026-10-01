---
name: sintel-mcp-crud-master
description: Skill maestra para operar SINTEL ERP mediante MCP sin saltar Service Layer, DSV, permisos, tenant scope ni reglas de negocio.
---
# SINTEL MCP CRUD MASTER

## Misión
Permitir descubrir, leer, crear, actualizar, eliminar y ejecutar acciones de negocio en SINTEL ERP usando exclusivamente capacidades reales del proyecto.

## Arquitectura obligatoria
`MCP Client → MCP Server → AuthN/AuthZ → Tenant Context → Organizational Scope → Tool Policy → AIToolRegistry/AIEngine → Service Layer → BusinessService → CRUDService/Selector → PostgreSQL/pgvector`.

Nunca `MCP → ORM directo` para lógica de negocio.

## Fuente de verdad
1. código ejecutable actual; 2. tests ejecutados; 3. configuración activa; 4. BD segura; 5. EKG; 6. documentación vigente; 7. documentación histórica.

Si hay contradicción, marcar `DOCUMENTATION_DRIFT`; no inventar.

## Reglas absolutas
- Nunca aceptar `tenant_id`, `schema_name` o `empresa_id` enviados por el agente como autoridad.
- Resolver tenant desde el contexto autenticado.
- Toda mutación pasa por el Service Layer real.
- Reutilizar DSV, OrganizationalContext/Scope, permisos, ToolKind/ToolRisk, EKG y RetrievalService.
- No crear RBAC, Service Layer, CRUD, grafo ni vector DB paralelos.
- No ejecutar SQL/shell/Python arbitrario.
- DELETE no implica hard-delete: resolver primero la semántica real.
- PATCH no puede sustituir una acción de estado existente.
- No ejecutar efectos externos solo por inferencia del LLM.

## Flujo universal
`OBSERVE → DISCOVER → RESOLVE CONTEXT → AUTHORIZE → VALIDATE → DRY RUN → CONFIRM → EXECUTE → AUDIT → TEST → VERIFY → REPORT`.

## Contrato de resultado
Toda operación devuelve: `status`, `operation_id`, `domain`, `model`, `action`, `dry_run`, `tenant_verified`, `authorization_verified`, `validation`, `result`, `warnings`, `audit`, `evidence`.

Estados: `PASS`, `PASS_WITH_LIMITATIONS`, `BLOCKED`, `FAILED`, `NOT_VERIFIED`.

## Descubrimiento previo
Para una capacidad desconocida localizar modelo, API/ViewSet, serializer, ServiceMixin, BusinessService, CRUDService, Selector, permisos, estados, acciones y tests. Consultar EKG para impacto.
