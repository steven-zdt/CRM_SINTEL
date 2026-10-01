---
name: sintel-mcp-testing-release-gate
description: Verifica capacidades MCP con tests, tenant isolation, idempotencia y release gates.
---
# TESTING & RELEASE GATE

Checks base según mecanismos reales del proyecto: `manage.py check`, `makemigrations --check --dry-run`, governance CLI, production readiness, tests focalizados y regresión del dominio.

Tests MCP mínimos: auth, authz, cross-tenant, organizational scope, CREATE válido/inválido/FK cruzado/rollback, READ scope/paginación/redacción, UPDATE campos/estado/FK, DELETE según semántica, idempotencia, dry-run sin persistencia ni side effects.

Release gate:
```yaml
discovery: PASS
service_layer: PASS
authz: PASS
tenant_isolation: PASS
crud_contract: PASS
business_rules: PASS
transactions: PASS
idempotency: PASS|NA
audit: PASS
tests: PASS
integration_contract: PASS|DEFERRED
mcp_tool: PASS
```

Tenant isolation o autorización en FAIL bloquean el dominio.

Usar EKG para determinar regresión real. No asumir dependencias.
