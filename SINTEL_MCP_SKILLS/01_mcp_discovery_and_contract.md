---
name: sintel-mcp-discovery-contract
description: Descubre modelos, APIs, servicios, permisos, reglas y contratos antes de exponer CRUD por MCP.
---
# DISCOVERY & CONTRACT

## Dominios documentados
Public: `accounts`, `tenants`, `impuestos`, `console`, `core`, `db_extensions`.
Tenant: `empresa`, `perfil`, `facturas`, `contabilidad`, `gastos`, `inventario`, `empleados`, `cotizaciones`, `clientes`, `proveedores`, `proyectos`, `dashboard`, `bancos`, `compras`, `ventas`, `ai_knowledge`.

`core`, `landing`, `db_extensions` no deben convertirse automáticamente en CRUD de negocio.

## Por cada app descubrir
path, app_label, modelos, campos, constraints, relaciones, APIs, ViewSets, serializers, ServiceMixins, BusinessServices, CRUDServices, Selectors, permisos, estados, acciones, tests, integraciones y snapshot EKG.

## Capability contract
```yaml
domain:
model:
app:
read: true|false
create: true|false
update: true|false
delete: true|false
delete_mode: soft|hard|domain_action|blocked|not_applicable
business_actions: []
service:
selector:
viewset:
serializer:
permissions:
tenant_scope:
organizational_scope:
state_machine:
idempotency:
transactions:
external_side_effects:
tests:
status:
evidence:
```

Un endpoint existente no demuestra que CRUD sea seguro. Debe existir ruta verificable al Service Layer.

Si no existe Service Layer, marcar `CRUD_BLOCKED`; auditar el gap y no crear bypass ORM.
