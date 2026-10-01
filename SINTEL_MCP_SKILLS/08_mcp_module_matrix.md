---
name: sintel-mcp-module-matrix
description: Matriz de habilitación CRUD MCP por dominio SINTEL.
---
# MODULE MATRIX

| Dominio | Modelos documentados | Uso MCP inicial |
|---|---:|---|
| empresa | 3 | CRUD/configuración con reglas |
| perfil | 2 principales | CRUD controlado |
| facturas | 33 | READ + acciones; WRITE gateado |
| contabilidad | 16 | READ + acciones; WRITE gateado |
| gastos | 2 | CRUD gateado |
| inventario | 11 | CRUD + Kardex/traslados |
| empleados | 13 | CRUD + nómina gateada |
| cotizaciones | 5 | CRUD + máquina de estados |
| clientes | 8 | CRUD |
| proveedores | 18 | CRUD + CxP |
| proyectos | 20 | CRUD + tareas/presupuesto |
| dashboard | 3 | READ principalmente |
| bancos | 5 | READ + conciliación gateada |
| compras | 8 | CRUD + recepción |
| ventas | 3 | CRUD + facturación |
| ai_knowledge | 2 | Retrieval/Indexing Service, no edición directa por defecto |

Estados por dominio: `NOT_DISCOVERED`, `DISCOVERED`, `READ_READY`, `VALIDATE_READY`, `DRY_RUN_READY`, `WRITE_READY`, `DOMAIN_ACTIONS_READY`, `BLOCKED`, `DEFERRED`.

`core`, `landing`, `db_extensions` no son CRUD de negocio por defecto.
