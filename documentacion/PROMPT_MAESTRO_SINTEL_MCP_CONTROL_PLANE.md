# SINTEL ERP — MCP CONTROL PLANE
## MCP para auditoría, CRUD, pruebas, dependencias y reparación segura

**Tipo de misión:** Arquitectura + implementación + auditoría + automatización controlada  
**Proyecto:** SINTEL ERP

---

## 0. REGLA ABSOLUTA — NO INVENTAR

Antes de implementar cualquier herramienta MCP:

1. Inspeccionar el código real.
2. Inspeccionar modelos, Services, APIs, serializers y permisos.
3. Auditar tenant isolation.
4. Inspeccionar tests, EKG, RAG y documentación vigente.
5. Identificar qué funcionalidades ya existen.
6. Reutilizar lo existente.

No crear un segundo CRUD, Service Layer, RBAC, Tool Registry, EKG, sistema de auditoría, permisos o mecanismo de tenant isolation.

---

## 1. ESTADO ARQUITECTÓNICO BASE

La arquitectura actual utiliza `apps/services/ai/` como capa transversal de IA, con:

```text
providers/
context/
tools/
engine/
```

y contratos/componentes como:

```text
AIProvider
AIContext
build_context()
BaseTool
ToolKind
ToolRisk
AIToolRegistry
AIEngine
```

Existen tools como:

```text
buscar_cliente
buscar_producto
ai_project_map
buscar_conocimiento
```

El estado documentado de AI Engine es `NOT_VERIFIED`.

MCP ya aparece instalado/montado, pero el estado documentado es de andamiaje inerte, sin una capa MCP operativa completa.

**Objetivo:** evolucionar esta arquitectura, no reemplazarla.

---

# 2. OBJETIVO

Construir una capa MCP interna que permita a un agente autorizado:

- inspeccionar el proyecto;
- auditar arquitectura;
- auditar APIs;
- auditar Services;
- auditar dependencias;
- validar reglas de negocio;
- consultar EKG;
- consultar RAG/pgvector;
- ejecutar tests y checks;
- realizar CRUD controlado;
- ejecutar acciones de dominio;
- ejecutar dry-run;
- proponer correcciones;
- aplicar correcciones autorizadas;
- verificar las correcciones.

Determinar mediante auditoría si MCP debe vivir en:

```text
mcp/
apps/services/mcp/
apps/services/ai/mcp/
```

o integrarse con `apps/services/ai/tools/`.

Documentar la decisión en un ADR.

---

# 3. ARQUITECTURA OBJETIVO

```text
MCP Client
     │
     ▼
SINTEL MCP Server
     │
     ├── Authentication
     ├── Authorization
     ├── Tenant Context
     ├── Scope Context
     ├── Audit
     └── Tool Policy
             │
             ▼
      AI Tool Registry / MCP Adapter
             │
             ▼
          AIEngine
             │
             ▼
        Domain Services
             │
             ▼
     PostgreSQL + pgvector
```

MCP no puede saltarse:

```text
Service Layer
Permissions
Tenant isolation
Business rules
Transactions
Idempotency
Audit
```

---

# 4. CATEGORÍAS DE TOOLS

## Inspección/Auditoría

Implementar tools como:

```text
project_inventory
project_health
project_map
domain_inventory
model_schema
api_inventory
service_inventory
tool_inventory
dependency_inventory
integration_inventory
tenant_context
business_rule_inventory
audit_domain
audit_endpoint
audit_service
audit_dependencies
run_tests
run_checks
```

## Acciones

Posteriormente:

```text
create_record
update_record
delete_record
execute_domain_action
repair_data
propose_code_fix
apply_code_fix
```

Las acciones de escritura requieren controles de riesgo superiores.

---

# 5. PROHIBIDO CRUD DIRECTO AL ORM

No utilizar MCP como:

```python
Model.objects.create(...)
Model.objects.update(...)
Model.objects.delete(...)
```

para lógica de negocio.

La ruta obligatoria es:

```text
MCP
 ↓
Tool
 ↓
AIEngine / Tool Registry
 ↓
Service Layer
 ↓
Domain rules
 ↓
Transaction
 ↓
DB
```

Si un dominio no tiene Service Layer:

```text
SERVICE_EXISTS
SERVICE_PARTIAL
SERVICE_MISSING
SERVICE_DUPLICATED
SERVICE_UNSAFE
```

Auditar primero. No inventar reglas automáticamente.

---

# 6. PROJECT INVENTORY

Crear:

```text
project_inventory
```

Debe descubrir realmente:

```text
apps
models
services
viewsets
serializers
urls
tasks
signals
management commands
AI tools
MCP tools
integrations
tests
```

---

# 7. PROJECT MAP

Crear:

```text
project_map
```

Reutilizar el EKG existente.

Combinar cuando corresponda:

```text
Django runtime registry
EKG snapshots
Service Layer
API registry
AI Tool Registry
```

Salida:

```text
domain
app
model
service
API
tool
dependencies
consumers
dependencies_in
dependencies_out
tests
```

No crear otro grafo.

---

# 8. MODEL INSPECT

Crear:

```text
inspect_model
```

Parámetros:

```text
app
model
```

Inspeccionar:

```text
fields
types
nullable
blank
choices
unique
indexes
constraints
foreign_keys
one_to_one
many_to_many
related_models
```

---

# 9. SERVICE INSPECT

Crear:

```text
inspect_service
```

Inspeccionar:

```text
service
methods
inputs
outputs
transactions
permissions
dependencies
called_services
called_models
idempotency
side_effects
```

---

# 10. API INSPECT

Crear:

```text
inspect_api
```

Analizar:

```text
endpoint
method
view
viewset
serializer
permissions
service
request_schema
response_schema
tenant_scope
```

Detectar:

```text
endpoint inexistente
ViewSet inexistente
serializer inconsistente
API sin Service Layer
tenant scope ausente
```

---

# 11. DEPENDENCY INSPECT

Crear:

```text
inspect_dependencies
```

Detectar:

```text
circular_dependencies
dead_dependencies
missing_dependencies
duplicate_logic
direct_cross_domain_writes
```

Representar las cadenas reales:

```text
API → Service → Model
API → Service → Service → External API
```

---

# 12. BUSINESS RULE AUDIT

Crear:

```text
audit_business_rules
```

Buscar:

```text
SSoT
duplicated calculations
duplicated state transitions
missing transactions
missing idempotency
invalid state transitions
direct model mutation
cross-domain coupling
permission bypass
tenant leakage
dead code
```

Cada finding debe incluir:

```json
{
  "finding": "...",
  "severity": "P0/P1/P2/P3",
  "file": "...",
  "line": "...",
  "evidence": "...",
  "affected_domain": "...",
  "risk": "...",
  "recommended_action": "..."
}
```

No declarar hallazgos sin evidencia.

---

# 13. CRUD DISCOVERY

Crear:

```text
crud_capabilities
```

Debe informar:

```text
Domain
Create
Read
Update
Delete
Service
API
Permissions
Tests
Status
```

Los datos deben proceder del código real.

---

# 14. READ RECORD

Crear, cuando sea seguro:

```text
read_record
```

Debe respetar:

```text
tenant context
organizational scope
permissions
field security
```

Nunca aceptar `tenant_id`, `schema_name` o `empresa_id` del agente como mecanismo para cambiar el contexto de seguridad.

---

# 15. CREATE RECORD

Crear:

```text
create_record
```

solamente cuando exista un contrato seguro.

Flujo:

```text
MCP
 ↓
Resolve domain
 ↓
Resolve Service
 ↓
Validate permissions
 ↓
Validate input
 ↓
Business Service
 ↓
transaction
 ↓
Persist
 ↓
Sanitized result
```

---

# 16. UPDATE RECORD

Crear:

```text
update_record
```

Respetar:

```text
state machine
immutable fields
audit fields
permissions
tenant scope
business invariants
```

---

# 17. DELETE RECORD

Crear:

```text
delete_record
```

Primero determinar si el dominio usa:

```text
soft delete
hard delete
blocked delete
domain cancellation
state transition
```

El Service Layer decide.

Nunca asumir que DELETE significa hard delete.

---

# 18. DOMAIN ACTION

Crear:

```text
execute_domain_action
```

Ejemplo:

```json
{
  "domain": "cotizaciones",
  "action": "convertir_a_venta",
  "record_id": "...",
  "arguments": {}
}
```

Resolver contra el Service Layer real.

No duplicar acciones de negocio.

---

# 19. DRY / SSoT

La misma operación debe utilizar la misma lógica:

```text
UI
API
MCP
AI
 ↓
Service Layer
```

No crear reglas diferentes para MCP.

---

# 20. TEST RUNNER

Crear:

```text
run_tests
```

con targets allowlisted.

Ejemplo:

```text
run_tests(
    target="apps/tenant/facturas/tests"
)
```

No crear una shell arbitraria.

Prohibido exponer:

```text
shell(command)
exec(command)
```

---

# 21. DJANGO CHECK

Crear:

```text
django_check
```

Reutilizar:

```text
python manage.py check
```

Devolver:

```text
status
errors
warnings
```

---

# 22. MIGRATION CHECK

Crear:

```text
migration_check
```

Comprobar:

```text
makemigrations --check
showmigrations
migration consistency
```

No ejecutar migraciones destructivas automáticamente.

---

# 23. PRODUCTION READINESS

Si existe:

```text
python manage.py production_readiness
```

reutilizarlo mediante:

```text
production_readiness
```

No crear otro framework.

---

# 24. GOVERNANCE

Si existe:

```text
tools/organizational_governance/cli.py
```

reutilizarlo mediante:

```text
governance_audit
```

---

# 25. EKG QUERY

Crear:

```text
ekg_query
```

Reutilizando:

```text
tools/ekg/
```

Debe responder:

```text
¿Quién consume FacturaBusinessService?
¿Qué depende de Inventario?
¿Qué APIs llaman este servicio?
¿Qué archivos conocen este modelo?
```

No crear Neo4j ni otro grafo.

---

# 26. KNOWLEDGE SEARCH

Reutilizar:

```text
RetrievalService
RetrievalTool
pgvector
```

Crear/adaptar:

```text
knowledge_search
```

Debe respetar tenant isolation.

No crear otra Vector DB.

---

# 27. AUDIT DOMAIN

Crear:

```text
audit_domain
```

Debe incluir:

```text
Models
Services
APIs
Tools
Permissions
Dependencies
Business rules
Tests
CRUD
Integrations
State machines
Transactions
Idempotency
Tenant isolation
Known findings
```

---

# 28. AUDIT ENDPOINT

Crear:

```text
audit_endpoint
```

Seguir:

```text
URL
 ↓
URLConf
 ↓
View
 ↓
Serializer
 ↓
Permission
 ↓
Service
 ↓
Model
 ↓
External integration
```

Detectar:

```text
endpoint muerto
endpoint inexistente
endpoint duplicado
serializer muerto
service inexistente
permission ausente
tenant scope incorrecto
frontend endpoint mismatch
```

---

# 29. FRONTEND → API AUDIT

Crear:

```text
audit_frontend_api_contract
```

Inspeccionar:

```text
fetch()
safeFetchJson()
api_client
URLs
HTTP methods
payload
response fields
```

Comparar con:

```text
Django URLs
ViewSets
Serializers
```

Detectar:

```text
404
405
400
campo inexistente
payload incorrecto
respuesta incompatible
endpoint muerto
```

---

# 30. INTEGRATION AUDIT

Crear:

```text
audit_integrations
```

Auditar las integraciones reales:

```text
Wompi
DIAN
email
WhatsApp
MCP
REST
LLM providers
Redis
Celery
PostgreSQL
pgvector
storage
external APIs
```

Informar:

```text
consumer
adapter
configuration
credentials source
health check
retry
timeout
idempotency
error handling
tests
```

---

# 31. CODE REPAIR — PROPOSAL

Crear:

```text
propose_code_fix
```

Inicialmente no modifica archivos.

Debe devolver:

```text
finding
root_cause
affected_files
proposed_change
risk
tests_required
rollback
```

---

# 32. CODE REPAIR — APPLY

Crear posteriormente:

```text
apply_code_fix
```

Riesgo:

```text
HIGH / CRITICAL
```

Debe requerir confirmación explícita.

Flujo:

```text
audit
 ↓
finding
 ↓
proposed fix
 ↓
tests plan
 ↓
human approval
 ↓
apply
 ↓
tests
 ↓
check
 ↓
migration check
 ↓
regression
 ↓
audit result
```

---

# 33. NO AUTONOMÍA ILIMITADA

No crear tools genéricas equivalentes a:

```text
execute_command(command)
shell(command)
python(code)
sql(query)
docker(command)
filesystem_write(path, content)
```

Toda capacidad sensible debe ser específica, allowlisted y controlada.

---

# 34. OPERACIONES DESTRUCTIVAS

Toda operación destructiva debe tener:

```text
risk = HIGH / CRITICAL
explicit_confirmation = true
```

y `dry_run` cuando sea posible.

Prohibir automatización directa de:

```text
rm -rf
docker system prune
docker compose down -v
DROP DATABASE
DROP SCHEMA
TRUNCATE
git reset --hard
```

y equivalentes.

---

# 35. AUDIT LOG

Toda acción MCP debe generar o reutilizar un sistema de auditoría existente.

Registrar:

```text
timestamp
actor
tenant
tool
action
target
parameters_hash
result
status
risk
duration
correlation_id
```

Nunca guardar secretos completos.

---

# 36. TENANT ISOLATION

Regla P0.

Toda MCP session debe resolver:

```text
user
tenant
empresa
organizational scope
permissions
```

mediante los mecanismos existentes.

No permitir cambiar arbitrariamente:

```text
tenant_id
schema_name
empresa_id
```

---

# 37. CROSS-TENANT TEST

Crear obligatoriamente:

```text
test_mcp_cross_tenant_isolation
```

Comprobar que Tenant A nunca pueda obtener datos de Tenant B mediante:

```text
id
UUID
search
filter
relationship
aggregation
MCP tool
AI tool
RAG
```

---

# 38. PERMISSIONS

Reutilizar permisos existentes:

```text
TenantMembership
roles
organizational scope
```

No construir RBAC paralelo.

---

# 39. TOOL RISK

Reutilizar:

```text
ToolKind
ToolRisk
```

Mapeo conceptual:

```text
READ → LOW
VALIDATE → MEDIUM
SUGGEST → MEDIUM
WRITE → HIGH
DELETE → CRITICAL
CODE_MODIFICATION → CRITICAL
MIGRATION → CRITICAL
```

Adaptar al contrato real existente.

---

# 40. DRY-RUN

Toda escritura importante debe soportar:

```text
dry_run=true
```

cuando sea técnicamente posible.

Debe validar sin persistir:

- permisos;
- campos;
- relaciones;
- reglas;
- estado.

---

# 41. TRANSACTIONS

Las operaciones de escritura deben utilizar el patrón transaccional existente del Service Layer.

Auditar:

```text
nested atomic
savepoint
IntegrityError
idempotency
retry
```

---

# 42. IDEMPOTENCY

Auditar obligatoriamente idempotencia para operaciones como:

```text
crear factura
procesar venta
registrar pago
transmitir DIAN
enviar documento
crear movimiento
```

Reutilizar mecanismos existentes.

---

# 43. EXTERNAL SIDE EFFECTS

Para:

```text
email
WhatsApp
DIAN
Wompi
external APIs
```

diferenciar:

```text
validate
preview
execute
```

Nunca ejecutar una acción externa solamente porque el LLM la sugirió.

---

# 44. MCP TOOL DISCOVERY

Crear:

```text
list_mcp_tools
```

Debe mostrar:

```text
tool
description
kind
risk
required_permissions
tenant_scoped
write
confirmation_required
```

---

# 45. MCP RESOURCES

Si el protocolo/implementación lo permite:

```text
project://architecture
project://domains
project://apis
project://services
project://tools
project://ekg
project://release-gates
```

No duplicar documentos.

---

# 46. MCP PROMPTS

Si el protocolo lo permite:

```text
audit_domain
audit_api
audit_service
audit_dependencies
release_check
repair_workflow
```

Deben reutilizar los mismos tools.

---

# 47. FULL PROJECT AUDIT

Crear:

```text
full_project_audit
```

Ejecutar:

```text
1. project_inventory
2. project_map
3. api_inventory
4. service_inventory
5. dependency_inventory
6. business_rule_audit
7. tenant_security_audit
8. frontend_api_audit
9. integration_audit
10. test_health
11. migration_check
12. governance_audit
13. production_readiness
```

Resultado:

```text
P0
P1
P2
P3
```

con evidencia.

---

# 48. ESTADO REAL VS DOCUMENTACIÓN

Diferenciar:

```text
DOCUMENTED
IMPLEMENTED
VERIFIED
PARTIAL
DEFERRED
NOT_IMPLEMENTED
BROKEN
```

Nunca considerar documentación como prueba de implementación.

---

# 49. SOURCE OF TRUTH

Prioridad:

```text
1. Código ejecutable actual
2. Tests ejecutados
3. Configuración actual
4. Base de datos real cuando sea seguro consultarla
5. EKG generado
6. Documentación
7. Documentación histórica
```

Si existe conflicto:

```text
REPORTAR CONFLICTO
```

No ocultarlo.

---

# 50. MCP + EKG

Debe poder responder:

```text
¿Quién es dueño de este modelo?
¿Qué servicio crea esta entidad?
¿Qué API la modifica?
¿Qué APIs consumen este servicio?
¿Qué módulos dependen de esta entidad?
¿Qué tests cubren este flujo?
¿Qué documentación existe?
```

---

# 51. MCP + RAG

Para preguntas conceptuales:

```text
"¿Cuál es la regla documentada para convertir una cotización?"
```

usar:

```text
RAG / pgvector
```

Para estructura:

```text
"¿Qué servicio llama a FacturaBusinessService?"
```

usar:

```text
EKG / project map
```

Para ejecución:

```text
"Registra este abono"
```

usar:

```text
Service Layer
```

No mezclar responsabilidades.

---

# 52. MCP + AI ENGINE

Integrar con la arquitectura existente:

```text
MCP
 ↓
AIToolRegistry
 ↓
AIEngine
```

o mediante un adaptador equivalente que mantenga una única semántica de tools.

No duplicar AI Tools como implementaciones MCP independientes.

---

# 53. WRITE

Actualmente WRITE está bloqueado estructuralmente en AIEngine.

Por tanto, durante la primera implementación:

```text
READ
AUDIT
VALIDATE
DRY_RUN
```

y después WRITE por dominio.

---

# 54. ACTIVACIÓN PROGRESIVA

Inicialmente:

```text
MCP_READ_ENABLED=true
MCP_AUDIT_ENABLED=true
MCP_VALIDATE_ENABLED=true
MCP_WRITE_ENABLED=false
```

Los nombres definitivos deben integrarse con settings existentes.

WRITE se habilita por dominio tras superar los gates.

---

# 55. RELEASE GATE POR DOMINIO

Un dominio alcanza:

```text
DOMAIN_MCP_READY
```

solo con:

- [ ] Service Layer
- [ ] CRUD auditado
- [ ] permissions
- [ ] tenant isolation
- [ ] business rules
- [ ] transaction safety
- [ ] idempotency cuando aplique
- [ ] API contract
- [ ] MCP tool
- [ ] tests
- [ ] cross-tenant test
- [ ] negative tests
- [ ] audit evidence

---

# 56. TEST MATRIX

Crear pruebas para:

```text
MCP authentication
MCP authorization
MCP tenant isolation
MCP organizational scope
MCP READ
MCP CREATE
MCP UPDATE
MCP DELETE
MCP domain actions
MCP dry-run
MCP audit logging
MCP idempotency
MCP external integrations
MCP tool discovery
MCP EKG
MCP RAG
MCP AI Engine
```

---

# 57. TEST DE BYPASS

Intentar saltarse:

```text
tenant
permissions
service
state machine
idempotency
confirmation
```

Todos los intentos no autorizados deben fallar correctamente.

---

# 58. TEST UI/API/MCP

Para una misma operación:

```text
UI
API
MCP
```

deben utilizar la misma regla de negocio y, cuando aplique, el mismo Service Layer.

---

# 59. REPARACIÓN CONTROLADA

Patrón obligatorio:

```text
OBSERVE
   ↓
AUDIT
   ↓
FINDING
   ↓
ROOT CAUSE
   ↓
PROPOSE
   ↓
TEST PLAN
   ↓
HUMAN APPROVAL
   ↓
APPLY
   ↓
TEST
   ↓
VERIFY
   ↓
DOCUMENT
```

Nunca modificar automáticamente operaciones de alto riesgo sin autorización.

---

# 60. OBSERVABILIDAD

Cada ejecución MCP debe tener:

```text
correlation_id
execution_id
tool
actor
tenant
duration
status
```

Debe poder reconstruirse:

```text
MCP
→ Service
→ API
→ External API
```

cuando exista.

---

# 61. SECRETOS

Nunca devolver:

```text
API_KEY
SECRET
PASSWORD
TOKEN
PRIVATE_KEY
```

Utilizar referencias a secretos y mecanismos existentes.

---

# 62. SSRF / RED

Para REST, MCP remoto, LLM providers y APIs externas:

- usar allowlists;
- validar URLs;
- aplicar timeout;
- bloquear destinos no autorizados;
- reutilizar controles SSRF existentes.

No permitir arbitrariamente:

```text
127.0.0.1
localhost
169.254.169.254
private networks
metadata endpoints
```

salvo destinos explícitamente autorizados.

---

# 63. RATE LIMIT / TIMEOUT / PAGINACIÓN

Cada tool debe tener límites apropiados:

```text
timeout
max_rows
max_payload
max_execution_time
```

Las consultas grandes deben paginar.

---

# 64. DOCUMENTACIÓN

Crear:

```text
docs/mcp/
```

con:

```text
MCP_BASELINE.md
MCP_ARCHITECTURE.md
MCP_SECURITY_MODEL.md
MCP_TOOL_CATALOG.md
MCP_DOMAIN_MATRIX.md
MCP_RELEASE_GATE.md
MCP_OPERATIONS.md
MCP_AUDIT_WORKFLOW.md
ADR-MCP-001.md
```

---

# 65. FASE 0 — SOLO INSPECCIÓN

No modificar código de negocio.

Ejecutar:

```text
INSPECT
INVENTORY
MAP
CLASSIFY
```

Generar:

```text
docs/mcp/MCP_BASELINE.md
```

Debe documentar:

```text
MCP existente
MCP instalado
MCP endpoints
AIToolRegistry
AIEngine
AIContext
Service Layer
EKG
RAG
Permissions
Tenant context
Existing APIs
Existing services
Tests
```

### PROHIBIDO

```text
crear modelos
crear migraciones
habilitar WRITE
crear CRUD
modificar reglas de negocio
eliminar código
eliminar dependencias
```

---

# 66. FASE 1 — MCP READ/AUDIT

Implementar:

```text
project_inventory
project_map
inspect_model
inspect_service
inspect_api
inspect_dependencies
audit_domain
audit_endpoint
audit_integrations
ekg_query
knowledge_search
```

Sin WRITE.

---

# 67. FASE 2 — VALIDATE

Agregar:

```text
run_tests
django_check
migration_check
governance_audit
production_readiness
```

Sin modificar código.

---

# 68. FASE 3 — DRY RUN

Agregar:

```text
create_record(dry_run)
update_record(dry_run)
delete_record(dry_run)
execute_domain_action(dry_run)
```

No persistir.

---

# 69. FASE 4 — WRITE CONTROLADO

Activar WRITE por dominio.

Seleccionar únicamente dominios cuyo Service Layer y seguridad estén verificados.

---

# 70. FASE 5 — CODE REPAIR

Implementar:

```text
propose_code_fix
apply_code_fix
```

con:

```text
human approval
audit
rollback strategy
tests
regression
```

---

# 71. FASE 6 — LOOP OPERATIVO

Permitir:

```text
AUDIT
→ FIND
→ PROPOSE
→ APPROVE
→ FIX
→ TEST
→ VERIFY
→ DOCUMENT
```

---

# 72. COMANDOS PROHIBIDOS

No ofrecer interfaces arbitrarias equivalentes a:

```text
shell(command)
exec(command)
python(code)
sql(query)
docker(command)
filesystem_write(path, content)
```

---

# 73. SQL

No exponer:

```text
execute_sql
```

genérico.

Para diagnóstico, utilizar solamente queries allowlisted y específicas cuando sean necesarias.

---

# 74. FILESYSTEM

No exponer:

```text
write_file(path, content)
```

genérico.

Usar:

```text
propose_code_fix
apply_code_fix
```

con paths allowlisted.

---

# 75. GIT

No exponer:

```text
git(command)
```

genérico.

Si se necesita gestión de cambios, utilizar herramientas específicas y seguras.

Nunca ejecutar automáticamente:

```text
git reset --hard
```

---

# 76. CONFIGURACIÓN MCP

Crear/adaptar settings:

```text
MCP_ENABLED
MCP_READ_ENABLED
MCP_AUDIT_ENABLED
MCP_VALIDATE_ENABLED
MCP_DRY_RUN_ENABLED
MCP_WRITE_ENABLED
MCP_CODE_REPAIR_ENABLED
```

Por defecto:

```text
READ = false
AUDIT = false
VALIDATE = false
DRY_RUN = false
WRITE = false
CODE_REPAIR = false
```

No duplicar el sistema de settings existente.

---

# 77. PRODUCCIÓN

No exponer MCP públicamente sin:

```text
authentication
authorization
TLS
rate limiting
audit
tenant isolation
tool allowlist
```

Auditar la exposición real de `/mcp/`.

---

# 78. CRITERIOS DE ACEPTACIÓN

- [ ] MCP server real.
- [ ] Authentication.
- [ ] Authorization.
- [ ] Tenant context.
- [ ] Organizational scope.
- [ ] Audit logging.
- [ ] Tool Registry integrado.
- [ ] AIEngine integrado.
- [ ] Service Layer reutilizado.
- [ ] EKG reutilizado.
- [ ] RAG/pgvector reutilizado.
- [ ] CRUD auditado.
- [ ] Domain actions auditadas.
- [ ] API dependencies auditadas.
- [ ] Frontend/API contracts auditados.
- [ ] Integrations auditadas.
- [ ] Tests.
- [ ] Cross-tenant tests.
- [ ] Negative tests.
- [ ] Dry-run.
- [ ] WRITE controlado.
- [ ] Code repair controlado.
- [ ] Documentación.
- [ ] Release Gate.

---

# 79. PRINCIPIO CENTRAL

> **El MCP no es otro ERP. Es la interfaz operativa controlada que permite a un agente autorizado observar, auditar, validar y ejecutar las capacidades reales del SINTEL ERP sin saltarse su arquitectura ni sus reglas de negocio.**

La fuente de verdad continúa siendo:

```text
Django
+
Service Layer
+
APIs
+
AI Tool Registry
+
EKG
+
PostgreSQL
+
pgvector
```

---

# 80. LOOP 0 OBLIGATORIO

La IA editora debe comenzar exactamente así:

```text
LOOP 0
│
├── Leer MEMORY.md
├── Leer AGENTS.md
├── Leer arquitectura_general actual
├── Auditar apps/services/ai/
├── Auditar AIToolRegistry
├── Auditar AIEngine
├── Auditar AIContext
├── Auditar EKG
├── Auditar RAG
├── Auditar Service Layer
├── Auditar /mcp/
├── Auditar django-rest-framework-mcp
├── Auditar permisos
├── Auditar tenant isolation
├── Auditar APIs
├── Auditar tests
│
└── GENERAR MCP_BASELINE.md
```

No modificar código de negocio en LOOP 0.

---

# 81. LOOP 1 — DISEÑO E IMPLEMENTACIÓN READ

```text
LOOP 1
│
├── Diseñar MCP architecture
├── Crear ADR
├── Crear MCP Tool Registry / Adapter
├── Integrar con AIToolRegistry
├── Integrar AIEngine
├── Integrar Tenant Context
├── Integrar Authorization
└── Implementar READ/AUDIT
```

---

# 82. LOOP 2 — VALIDACIÓN

```text
LOOP 2
│
├── Tests
├── Cross-tenant
├── Permission bypass
├── API contract
├── Service Layer
├── EKG
├── RAG
└── Release Gate
```

---

# 83. LOOP 3 — DRY RUN

```text
LOOP 3
│
├── Dry-run CRUD
├── Domain actions
├── Idempotency
├── Transactions
├── Audit
└── Release Gate
```

---

# 84. LOOP 4 — WRITE POR DOMINIO

```text
LOOP 4
│
├── WRITE por dominio
├── Human approval
├── Tests
├── Regression
└── Verification
```

---

# 85. LOOP 5 — CODE REPAIR

```text
LOOP 5
│
├── Code audit
├── Root cause
├── Proposed fix
├── Approval
├── Apply
├── Tests
├── Regression
├── Re-audit
└── Documentation
```

---

# 86. REPORTE FINAL

Toda misión MCP debe terminar con:

```text
MISSION
STATUS

CHANGES
TESTS
AUDITS
FINDINGS
FIXES
DEFERRED
RISKS
ROLLBACK
EVIDENCE
```

Estados válidos:

```text
PASS
PASS_WITH_LIMITATIONS
PARTIAL
FAILED
BLOCKED
DEFERRED
NOT_VERIFIED
```

No declarar éxito sin evidencia.

---

# 87. REGLA FINAL DE CONSOLIDACIÓN

Si durante una auditoría se encuentra:

```text
código duplicado
API duplicada
Service duplicado
regla duplicada
tool duplicada
integración duplicada
```

NO crear otra abstracción encima.

Primero determinar:

```text
¿Cuál es el SSoT real?
```

Después:

```text
reutilizar
consolidar
o documentar deuda
```

según evidencia.

---

# 88. ENTREGABLES OBLIGATORIOS

Al finalizar las fases iniciales deben existir:

```text
docs/mcp/MCP_BASELINE.md
docs/mcp/MCP_ARCHITECTURE.md
docs/mcp/MCP_SECURITY_MODEL.md
docs/mcp/MCP_TOOL_CATALOG.md
docs/mcp/MCP_DOMAIN_MATRIX.md
docs/mcp/MCP_AUDIT_WORKFLOW.md
docs/mcp/MCP_RELEASE_GATE.md
docs/mcp/ADR-MCP-001.md
```

más la implementación MCP en la ubicación determinada por la auditoría.

---

# 89. RESULTADO ESPERADO

El agente autorizado debe poder solicitar:

```text
Audita proveedores.
```

```text
Audita las dependencias de facturas.
```

```text
¿Qué APIs consumen Venta?
```

```text
¿Qué servicio crea Factura?
```

```text
Ejecuta los tests de cotizaciones.
```

```text
Valida el estado de producción.
```

```text
Haz dry-run de crear este proveedor.
```

```text
Propón una corrección para este bug.
```

y, después de autorización explícita:

```text
Aplica la corrección.
```

La ejecución debe pasar por:

```text
AUTH
→ TENANT CONTEXT
→ PERMISSIONS
→ TOOL POLICY
→ SERVICE LAYER
→ BUSINESS RULES
→ TRANSACTION
→ AUDIT
→ TEST
→ VERIFICATION
```

Nunca mediante acceso arbitrario al proyecto.

# FIN DEL PROMPT
