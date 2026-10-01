---
name: sintel-mcp-tool-catalog
description: Catálogo funcional de herramientas MCP para CRUD, auditoría, validación y operación SINTEL.
---
# TOOL CATALOG

Discovery: `project_inventory`, `project_map`, `domain_inventory`, `inspect_model`, `inspect_api`, `inspect_service`, `inspect_dependencies`, `crud_capabilities`, `business_rule_inventory`.

Read: `read_record`, `list_records`, `search_records`, `get_related_records`.

Validate: `validate_create`, `validate_update`, `validate_delete`, `validate_domain_action`, `dry_run`.

Write: `create_record`, `update_record`, `delete_record`, `execute_domain_action`, `bulk_create`, `bulk_update` (bulk solo con servicio seguro).

Audit: `audit_domain`, `audit_endpoint`, `audit_service`, `audit_dependencies`, `audit_tenant_isolation`, `audit_frontend_api_contract`, `audit_integrations`.

Testing: `run_tests`, `django_check`, `migration_check`, `production_readiness`, `governance_audit`.

Repair: `propose_code_fix`, `apply_code_fix`.

Knowledge: `ekg_query`, `knowledge_search`. Reutilizar `tools/ekg/` y `RetrievalService`/`RetrievalTool`/pgvector.

Cada tool declara: `name`, `description`, `kind`, `risk`, `required_permissions`, `tenant_scoped`, `organizational_scope`, `supports_dry_run`, `requires_confirmation`, `writes_data`, `external_side_effect`, `idempotent`, `timeout`, `max_payload`, `audit_event`.

Reutilizar `ToolKind` y `ToolRisk` reales. Conceptualmente: READ LOW; VALIDATE LOW/MEDIUM; SUGGEST MEDIUM; WRITE HIGH; DELETE/CODE_MODIFICATION/MIGRATION CRITICAL.
