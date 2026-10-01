---
name: sintel-mcp-security-tenant
description: Aplica aislamiento multitenant, DSV, permisos y alcance organizacional a cada herramienta MCP.
---
# SECURITY / TENANT SCOPE

El tenant es P0. El agente no puede cambiar de tenant pasando `tenant_id`, `schema_name`, `empresa_id` ni equivalentes.

Resolver contexto desde usuario autenticado, TenantProfile, TenantMembership, OrganizationalContext/Scope y middleware existente. No crear RBAC nuevo.

Toda mutación valida: recurso dentro del tenant; cada FK dentro del tenant; membresía activa; sede/área compatibles; estado permite operación.

Para modelos `SedeAwareModel` o equivalentes respetar sede/área. Nunca ampliar scope por payload.

Toda WRITE requiere prueba negativa cross-tenant: A intenta operar sobre B → bloqueado y B intacto.

Nunca retornar secretos. Registrar hashes/metadatos, no secretos.

URLs externas: allowlist, timeout, bloqueo metadata/private networks no autorizadas y SSRF. No aceptar URL arbitraria del prompt como autoridad.

Audit mínimo: actor, tenant, tool, action, target, parameter hash, correlation_id, execution_id, timestamp, status, risk, duration.
