# Matriz de Contratos - Service Layer ↔ UI

| APP | UI Endpoints | Service Function(s) | Parse-only (sí/no) | Persistencia (endpoint app) | Observaciones |
|-----|--------------|---------------------|-------------------|----------------------------|---------------|
| empresa | GET/POST/PATCH/DELETE `/api/v1/core/empresa/`<br>GET `/api/v1/core/empresa/mi-empresa/` | `apps.tenant.empresa.impl.empresa_service` | No | `/api/v1/core/empresa/` | SSoT singleton |
| facturas | GET `/api/v1/facturas/`<br>GET `/api/v1/facturas/{id}/`<br>POST `/api/v1/core/documentos/upload/?preview=true\|false`<br>GET `/api/v1/core/documentos/{id}/xml/`<br>DELETE `/api/v1/core/documentos/{id}/`<br>POST `/api/v1/facturas/create-from-dto/` | `apps.tenant.facturas.services`<br>`guardar_factura_desde_dto`<br>`guardar_nota_credito_desde_dto` | ✅ Sí | `/api/v1/facturas/create-from-dto/` | Inmutables, parse-only universal |
| inventario | GET/POST/PATCH/DELETE `/api/v1/inventario/catalogo/`<br>POST `/api/v1/core/documentos/upload/?tipo=inventario&preview=true`<br>POST `/api/v1/inventario/create-from-dto/` | `apps.tenant.inventario.services` | ✅ Sí (opcional) | `/api/v1/inventario/create-from-dto/` | CRUD + parse-only opcional |
| gastos | GET/POST/PATCH/DELETE `/api/v1/gastos/`<br>POST `/api/v1/core/documentos/upload/?tipo=gasto&preview=true`<br>POST `/api/v1/gastos/create-from-dto/` | `apps.tenant.gastos.services` | ✅ Sí (opcional) | `/api/v1/gastos/create-from-dto/` | CRUD + parse-only opcional |
| landing | GET `/api/v1/landing/info/` | N/A (read-only) | No | N/A | Panel informativo |
| perfil | GET/PATCH `/api/v1/core/mi-perfil/`<br>PATCH `/api/v1/core/mi-perfil/configuracion/` | `apps.tenant.core.api.views.MiPerfilView` | No | `/api/v1/core/mi-perfil/` | Perfil del usuario autenticado |
| proveedores | GET/POST/PATCH/DELETE `/api/v1/proveedores/` | DRF ViewSet estándar | No | `/api/v1/proveedores/` | CRUD estándar |
| empleados | GET/POST/PATCH/DELETE `/api/v1/empleados/empleados/` | DRF ViewSet estándar | No | `/api/v1/empleados/empleados/` | CRUD estándar + submódulos |
| dashboard | GET `/api/v1/core/dashboard/` | `apps.tenant.core.api.views` | No | N/A | Read-only, orquestado por Core |
| contabilidad | GET/POST/PATCH/DELETE `/api/v1/contabilidad/cuentas-contables/`<br>GET/POST/PATCH/DELETE `/api/v1/contabilidad/asientos-contables/`<br>POST `/api/v1/contabilidad/asientos-contables/{id}/aprobar/` | DRF ViewSets estándar | No | `/api/v1/contabilidad/*/` | CRUD cuentas y asientos |
| mail | POST `/api/v1/core/maildigester/run/`<br>GET `/api/v1/core/maildigester/runs/`<br>GET `/api/v1/core/maildigester/run/{id}/details/`<br>POST `/api/v1/core/maildigester/run/{id}/stop/`<br>DELETE `/api/v1/core/maildigester/run/{id}/`<br>GET `/api/v1/core/maildigester/configs/` | `apps.services.maildigester.tasks`<br>`apps.tenant.facturas.services_mail_ingestion` | ✅ Sí (parse-only en pipeline) | `apps.tenant.facturas.services`<br>`guardar_factura_desde_dto` | IMAP→UID→ZIP/7z→XML UBL→DTO→persistencia Facturas |

## Notas Importantes

1. **Parse-only**: `document_ingest` **NUNCA** persiste; siempre devuelve DTO
2. **Persistencia**: Cada app persiste con su propio endpoint/service layer
3. **MailDigester**: Usa pipeline universal para parse, pero persiste en Facturas con idempotencia (CUFE/CUDE)
4. **Empresa**: Singleton SSoT, solo una instancia por tenant
