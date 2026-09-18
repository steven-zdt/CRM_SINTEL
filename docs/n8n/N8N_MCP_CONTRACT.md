# N8N_MCP_CONTRACT — contrato REST (MCP formal DEFERRED)

Mision N8N-SINTEL-01. Ver `N8N_ARCHITECTURE.md` seccion "Por que REST
API y no MCP formal" para la justificacion completa de esta decision
(confirmada por el usuario).

**Re-auditado 2026-09-10 (N8N-SINTEL-02, FASE 1/2):** el bloqueo sigue
vigente, re-verificado contra el codigo real (no solo releido de este
documento) -- misma version `django-rest-framework-mcp==0.1.0a4` fijada
en `requirements.txt`, `grep -rn "mcp_viewset" apps/` sigue en cero. El
usuario confirmo explicitamente continuar con REST puro y no reintentar
MCP en esta mision. El catalogo de herramientas de abajo (Fase 7 de
N8N-SINTEL-01) sigue siendo el allowlist real -- no se agrego ninguna
herramienta WRITE genérica, y `upload-document` sigue siendo el unico
camino determinista de recepcion documental (FASE 6 de N8N-SINTEL-02).

**Conexion de transporte validada 2026-09-10** (a pedido del usuario,
una vez creada la cuenta owner de n8n): `POST http://<tenant>/mcp/`
responde correctamente a `initialize`/`tools/list` con la identidad
tecnica real (`crear_identidad_tecnica_n8n`) -- `tools/list` devuelve
`{"tools": []}`, consistente con 0 ViewSets decorados. **No se probo
`tools/call`** (ahi vive el defecto de terceros). Hallazgo adicional
real encontrado en la validacion (transporte sin autenticacion para
`initialize`/`tools/list`, distinto del bug de `execute_tool()`):
detalle completo en `docs/ai/AI_MCP_POLICY.md`.

## Estado real de MCP en SINTEL (Fase 5, auditado)

```
MCP infrastructure = INSTALLED (django-rest-framework-mcp>=0.1.0a4, /mcp/ montado)
MCP business surface = NOT READY (0 ViewSets decorados, mismo defecto de
                        terceros que ya bloqueo AI-07 sigue vigente en la
                        misma version del paquete)
```

No se declara MCP operativo. No se decoro ningun ViewSet nuevo con
`@mcp_viewset()` en esta mision.

## Contrato REST real (Workflow A del piloto)

n8n consume estos endpoints **ya existentes**, sin duplicar nada:

| Operacion | Metodo/Ruta | Estado |
|---|---|---|
| Subir documento (XML/PDF/XLS/CSV/TXT) | `POST /api/v1/core/_apps/facturas/upload-document/` | **HABILITADO** en esta mision (`FEATURE_UPLOAD_DOCUMENT_ENDPOINT=true`), ya existia construido |
| Consultar Factura por uuid | `GET /api/v1/facturas/{uuid}/` | Ya existente, sin cambios |
| Buscar Facturas | `GET /api/v1/facturas/?search=...` | Ya existente, sin cambios |
| Estado de tarea de ingesta (batch grande) | `GET /api/v1/facturas/ingest/{task_id}/status/` | Ya existente, sin cambios |
| Refrescar el JWT de la identidad tecnica | `POST /api/token/refresh/` | Ya existente, sin cambios |

Todos requieren `Authorization: Bearer <access_token>` de la identidad
tecnica (ver `N8N_SECURITY.md`).

## Herramientas de automatizacion diseñadas (Fase 7) — catalogo, no todas implementadas

Nomenclatura semantica pedida por la mision, mapeada a los endpoints
REST reales (ninguna requiere codigo nuevo salvo lo ya listado arriba):

| Nombre semantico | Endpoint real | Implementado |
|---|---|---|
| `invoice.ingestion.upload` | `POST .../upload-document/` | SI |
| `invoice.ingestion.status` | `GET .../ingest/{task_id}/status/` | SI (ya existia) |
| `invoice.get` | `GET /api/v1/facturas/{uuid}/` | SI (ya existia) |
| `invoice.search` | `GET /api/v1/facturas/?search=` | SI (ya existia) |
| `sale.get` / `sale.search` | `GET /api/v1/ventas/{uuid}/` / `?search=` | SI (ya existia, sin cambios) |
| `purchase.get` / `purchase.search` | `GET /api/v1/compras/{uuid}/` / `?search=` | SI (ya existia, sin cambios) |
| `customer.get` / `customer.search` | `GET /api/v1/clientes/{uuid}/` / `?search=` | SI (ya existia, sin cambios) |
| `supplier.get` / `supplier.search` | `GET /api/v1/proveedores/{uuid}/` / `?search=` | SI (ya existia, sin cambios) |
| `workflow.department_notification` | evento saliente, ver `N8N_WORKFLOWS.md` | DISEÑADO, DEFERRED (Fase 10, sin fuente configurable de departamentos aun) |

**No se creo ningun endpoint nuevo de busqueda/consulta** -- los
ViewSets reales de `ventas`/`compras`/`clientes`/`proveedores` ya
exponen `search=` en sus selectors (confirmado, mismo patron en todo el
proyecto). n8n los consume directamente, con la identidad tecnica.

## Explicitamente NO expuesto (Fase 6, prohibiciones)

```
delete / bulk_delete       -- ningun endpoint DELETE se documenta para n8n
raw_query / execute_sql    -- no existe tal endpoint en SINTEL
admin                      -- /admin/ nunca se expone a la identidad tecnica
filesystem                 -- ninguna operacion de filesystem expuesta
crear_factura (emision)    -- BLOQUEADO estructuralmente, ver mision
                               VENTAS-COMPRAS-FACTURAS-01 (EMISION_FISCAL_VENTA_AUTORIZADA)
```
