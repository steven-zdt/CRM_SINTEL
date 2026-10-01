---
name: sintel-mcp-crud
description: Ejecuta CRUD MCP con validación, dry-run, autorización, transacciones, idempotencia y auditoría.
---
# CRUD READ/WRITE

## CREATE
Resolver tenant → recurso → permiso → payload → DSV → relaciones → estado → idempotencia → dry-run → confirmación → BusinessService → CRUDService → audit → test → verify.

## READ
Usar Selector/Service Layer. Soportar get/list/search/filter/order/pagination/relations permitidas. Redactar passwords, tokens, API keys, credenciales y campos prohibidos por AI_SECURITY_MODEL.

## UPDATE
Cargar dentro del tenant; comprobar permiso, estado y campos editables; validar FKs; ejecutar BusinessService. No permitir update masivo sin filtro explícito, límite, preview y confirmación.

## DELETE
Resolver primero `delete_mode`: `soft`, `hard`, `domain_action`, `blocked`, `not_applicable`. Si existe anulación/cancelación/archivado, usarla. Nunca llamar `.delete()` desde MCP para imponer semántica propia.

## Bulk
Solo si existe operación segura de dominio. No iterar miles de registros con ORM desde MCP.

## Errores
Clasificar: AUTHENTICATION_ERROR, AUTHORIZATION_ERROR, TENANT_SCOPE_ERROR, VALIDATION_ERROR, BUSINESS_RULE_ERROR, STATE_TRANSITION_ERROR, INTEGRITY_ERROR, IDEMPOTENCY_REPLAY, EXTERNAL_INTEGRATION_ERROR, NOT_IMPLEMENTED, NOT_VERIFIED, INTERNAL_ERROR.
Nunca ocultar una excepción de programación como SUCCESS.
