# PLAN MAESTRO — AUDITORÍA, HARDENING Y NORMALIZACIÓN DE CRM_SINTEL

**Objetivo:** ejecutar sobre el repositorio `steven-zdt/CRM_SINTEL` una remediación integral basada en la auditoría técnica realizada, aplicando buenas prácticas verificables y documentación oficial.

**Repositorio:** `steven-zdt/CRM_SINTEL`
**Branch objetivo:** `main`
**Fecha de referencia:** 2026-09-25
**Naturaleza:** instrucción para IA editora / agente de código.

---

# 0. REGLAS ABSOLUTAS DE EJECUCIÓN

Estas reglas tienen precedencia sobre cualquier otra instrucción de este documento.

## 0.1 No pedir autorización para editar

La IA editora tiene autorización para:

- inspeccionar el repositorio;
- crear/modificar/eliminar archivos necesarios;
- reorganizar código;
- refactorizar arquitectura;
- actualizar dependencias;
- modificar workflows;
- modificar Docker/Compose;
- crear migraciones cuando sean necesarias;
- crear documentación;
- crear tests nuevos;
- crear archivos de configuración no secretos;
- crear commits locales y/o ramas de trabajo si el entorno lo requiere.

**No pedir confirmación antes de hacer estas acciones.**

## 0.2 La única autorización que debe solicitarse al usuario

**La única autorización explícita que se debe solicitar es para ejecutar la batería final de tests/pruebas.**

No ejecutar la batería final hasta que el usuario responda afirmativamente.

No pedir autorización para corregir código.
No pedir autorización para actualizar dependencias.
No pedir autorización para modificar CI/CD.
No pedir autorización para crear archivos.
No pedir autorización para hacer refactors.

## 0.3 Los tests son el último paso global

La ejecución de tests debe ser la **última fase del proceso completo**.

Antes de esa fase se permite:

- inspección de archivos;
- análisis estático por lectura/búsqueda;
- comparación de configuración;
- análisis de dependencias declaradas;
- análisis de AST/estructura si la herramienta es puramente estática;
- `git diff`;
- revisión de coherencia arquitectónica;
- revisión de migraciones existentes por inspección del código;
- revisión de workflows YAML por lectura;
- generación/modificación de tests, pero **NO ejecutarlos**.

No ejecutar antes de la fase final:

- `pytest`;
- `manage.py test`;
- `manage.py check`;
- `manage.py check --deploy`;
- `makemigrations --check`;
- `migrate`;
- `migrate_schemas`;
- `ruff check` como comando ejecutable;
- `bandit`;
- `pip-audit`;
- tests Node/Playwright;
- smoke tests HTTP;
- pruebas de integración;
- pruebas contra PostgreSQL/Redis/Neo4j reales.

Estas acciones quedan reservadas a la fase final y requieren autorización.

## 0.4 Nunca tocar producción

No ejecutar comandos que modifiquen una base de datos de producción.

No ejecutar:

```text
DROP DATABASE
DROP SCHEMA
TRUNCATE
migrate contra producción
migrate_schemas contra producción
restore sobre producción
rotación destructiva de secretos en producción
```

Si se necesita comprobar una operación de base de datos, prepararla para CI/staging/local y dejarla para la fase final de pruebas.

## 0.5 Nunca inventar compatibilidad

Cuando exista una duda de compatibilidad entre paquetes:

1. inspeccionar la versión real del proyecto;
2. revisar documentación oficial del paquete;
3. revisar release notes/changelog oficial;
4. revisar restricciones de compatibilidad;
5. modificar el requisito solo cuando la compatibilidad sea razonablemente sustentada.

No reemplazar una dependencia crítica por intuición.

## 0.6 No ocultar fallos

No usar:

```text
continue-on-error: true
```

como solución permanente.

No marcar un hallazgo como resuelto únicamente agregando comentarios.

No eliminar un test para hacer pasar CI.

No eliminar validaciones de seguridad para hacer pasar tests.

No degradar permisos para resolver errores funcionales.

## 0.7 Mantener arquitectura funcional

Las correcciones no deben romper la intención actual de:

```text
public schema
tenant schemas
Service Layer
Selectors
AI Engine
Tool Registry
pgvector
Celery
MCP
OpenAPI
```

El objetivo es endurecer y simplificar, no sustituir toda la arquitectura sin necesidad.

---

# 1. MODO DE TRABAJO: LOOP OBLIGATORIO

Para cada fase aplicar este ciclo hasta quedar estable:

```text
AUDIT
  ↓
IDENTIFY
  ↓
PLAN MICRO
  ↓
IMPLEMENT
  ↓
RE-AUDIT
  ↓
¿QUEDAN HALLAZGOS?
  ├── SÍ → volver a IMPLEMENT
  └── NO → siguiente fase
```

Después de cada fase actualizar:

```text
AUDITORIA_PROGRESS.md
```

El archivo debe registrar:

```text
fase
hallazgo
archivo
cambio
razón
riesgo
estado
```

No marcar `DONE` si solamente se modificó código sin volver a inspeccionarlo.

---

# 2. FUENTES OFICIALES OBLIGATORIAS

La IA editora debe consultar documentación oficial vigente cuando la modificación dependa de comportamiento de un framework, proveedor o plataforma.

## Django

- https://docs.djangoproject.com/en/5.2/
- https://docs.djangoproject.com/en/5.2/releases/
- https://docs.djangoproject.com/en/5.2/topics/security/
- https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
- https://docs.djangoproject.com/en/5.2/topics/http/middleware/
- https://docs.djangoproject.com/en/5.2/topics/auth/
- https://docs.djangoproject.com/en/5.2/topics/db/transactions/
- https://docs.djangoproject.com/en/5.2/topics/files/

Django 5.2 es una rama LTS. Al momento de ejecutar este plan, verificar la release patch más reciente de la serie 5.2.x en la documentación oficial antes de fijar una versión exacta.

## django-tenants

- https://django-tenants.readthedocs.io/en/latest/install.html
- https://django-tenants.readthedocs.io/en/latest/test.html

Especial atención a:

- `SHARED_APPS`;
- `TENANT_APPS`;
- `INSTALLED_APPS`;
- `TenantMainMiddleware`;
- `TenantSyncRouter`;
- `migrate_schemas`;
- `TenantTestCase`;
- `TenantClient`;
- `schema_context`.

## Django REST Framework

- https://www.django-rest-framework.org/
- https://www.django-rest-framework.org/api-guide/authentication/
- https://www.django-rest-framework.org/api-guide/permissions/
- https://www.django-rest-framework.org/api-guide/throttling/
- https://www.django-rest-framework.org/api-guide/versioning/
- https://www.django-rest-framework.org/api-guide/filtering/
- https://www.django-rest-framework.org/api-guide/testing/

## PostgreSQL 16

- https://www.postgresql.org/docs/16/ddl-schemas.html
- https://www.postgresql.org/docs/16/ddl-priv.html
- https://www.postgresql.org/docs/16/runtime-config-client.html
- https://www.postgresql.org/docs/16/sql-grant.html
- https://www.postgresql.org/docs/16/sql-alterdefaultprivileges.html
- https://www.postgresql.org/docs/16/perm-functions.html
- https://www.postgresql.org/docs/16/sql-createfunction.html

Especial atención a:

- `search_path`;
- `USAGE`;
- `CREATE`;
- ownership;
- `PUBLIC` privileges;
- `SECURITY DEFINER`;
- schemas de extensiones;
- separación entre schemas tenant.

## GitHub Actions

- https://docs.github.com/en/actions/reference/security/secure-use
- https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
- https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions

Aplicar:

- mínimo privilegio en `permissions`;
- acciones pinneadas a SHA completo;
- evitar secretos innecesarios;
- jobs claramente delimitados;
- gates bloqueantes.

## OpenAPI / drf-spectacular

- https://drf-spectacular.readthedocs.io/

## OWASP

- https://owasp.org/www-project-application-security-verification-standard/
- https://owasp.org/www-project-top-ten/

OWASP se utilizará como referencia de seguridad complementaria, no como sustituto de la documentación específica de Django/PostgreSQL/GitHub.

---

# 3. FASE 0 — BASELINE Y CONTROL DE CAMBIOS

## Objetivo

Establecer una línea base antes de modificar el proyecto.

## Acciones

Inspeccionar:

```text
.gitignore
.env.example
requirements.txt
pyproject.toml
Dockerfile
docker-compose.yaml
docker-compose.prod.yaml
infra/compose/docker-compose.yml
infra/compose/docker-compose.test.yml
config/settings.py
.github/workflows/*
```

Inspeccionar estructura completa de:

```text
apps/public
apps/tenant
apps/services
apps/shared
config
tools
```

Identificar:

- archivos repetidos;
- servicios duplicados;
- `signals.py`;
- imports entre public y tenant;
- ORM directo desde ViewSets/views;
- credenciales o secretos;
- middleware personalizado;
- raw SQL;
- `search_path`;
- `SECURITY DEFINER`;
- archivos grandes;
- configuraciones locales versionadas;
- dependencias sin upper bound/lock;
- workflows no bloqueantes.

## Resultado

Crear:

```text
AUDITORIA_PROGRESS.md
```

No ejecutar tests.

## Loop

Releer los archivos modificados por esta fase y verificar que el baseline quede documentado.

---

# 4. FASE 1 — NORMALIZACIÓN DE DJANGO Y DEPENDENCIAS

## Objetivo

Eliminar el drift de versiones y hacer reproducible el entorno.

## Acción principal

Revisar:

```text
requirements.txt
pyproject.toml
```

Actualizar Django a la rama 5.2.x soportada y vigente según documentación oficial, validando compatibilidad de todo el stack antes de fijar la versión.

No usar simplemente:

```text
Django>=5.0,<5.1
```

si la arquitectura objetivo requiere Django 5.2.

## Política de dependencias

Implementar una estrategia reproducible, preferentemente:

```text
requirements.in
requirements.txt
```

con versiones resueltas y reproducibles, o una herramienta de lock equivalente.

Diferenciar:

```text
runtime dependencies
build dependencies
test dependencies
security tooling
optional AI dependencies
```

## Verificar compatibilidad

Revisar específicamente:

```text
django-tenants
psycopg
DRF
SimpleJWT
django-filter
django-tables2
drf-spectacular
django-rest-framework-mcp
Celery
Redis
pgvector
fastembed
OpenSearch client
neo4j
tree-sitter
```

## Loop

Reinspeccionar imports y configuración que dependan de APIs de Django modificadas.

No ejecutar tests.

---

# 5. FASE 2 — SETTINGS SECURITY HARDENING

## Archivo principal

```text
config/settings.py
```

## Objetivos

Separar claramente:

```text
development
production
test/CI
```

Evitar defaults inseguros en producción.

## SECRET_KEY

Eliminar cualquier posibilidad de usar una clave hardcoded insegura en producción.

Conservar fail-closed.

No aceptar:

```text
change-me
insecure
example

```

como valor válido para producción.

## DEBUG

Mantener:

```text
False
```

como default seguro.

## ALLOWED_HOSTS

Mantener allowlist explícita para producción.

Evitar `*`.

Revisar el wildcard del dominio base únicamente donde esté justificado por la arquitectura multitenant.

## HTTPS

Revisar:

```text
SECURE_SSL_REDIRECT
SECURE_PROXY_SSL_HEADER
SESSION_COOKIE_SECURE
CSRF_COOKIE_SECURE
SECURE_HSTS_SECONDS
SECURE_HSTS_INCLUDE_SUBDOMAINS
SECURE_HSTS_PRELOAD
SECURE_CONTENT_TYPE_NOSNIFF
SECURE_REFERRER_POLICY
```

La configuración debe reflejar una topología real y documentada de:

```text
Cloudflare
→ tunnel/proxy
→ nginx/ingress
→ Django
```

## Proxy headers

Revisar especialmente:

```text
USE_X_FORWARDED_HOST
SECURE_PROXY_SSL_HEADER
```

No confiar en `X-Forwarded-*` si el proxy no los sobrescribe de forma controlada.

## CORS

Revisar:

```text
CORS_ALLOWED_ORIGIN_REGEXES
CORS_ALLOW_CREDENTIALS
```

Con credenciales, evitar permitir orígenes no controlados.

## CSRF

Revisar `CSRF_TRUSTED_ORIGINS` y middleware personalizado.

No utilizar soluciones genéricas que relajen CSRF fuera de desarrollo controlado.

## Cookies

Revisar nombres, `Secure`, `HttpOnly`, `SameSite` y separación public/tenant.

## Loop

Releer `settings.py` completo y comprobar que no hayan quedado dos fuentes de verdad para la misma configuración.

No ejecutar tests.

---

# 6. FASE 3 — MULTITENANCY / SCHEMA ISOLATION

## Objetivo

Garantizar que el aislamiento entre tenants sea demostrable y no solo documental.

## SHARED_APPS/TENANT_APPS

Verificar:

```text
apps.public.* → SHARED_APPS
apps.tenant.* → TENANT_APPS
```

Eliminar inconsistencias y duplicaciones innecesarias.

Mantener solamente las apps que realmente deban existir en ambos esquemas.

## Middleware

Revisar el orden actual de:

```text
SecurityMiddleware
CORS
SessionMiddleware
Host validation
ForceNoPortMiddleware
TenantMainMiddleware
Tenant authorization
CSRF
Authentication
membership
```

Compararlo contra django-tenants oficial.

Si se mantiene una desviación deliberada, documentar:

```text
por qué existe
qué riesgo introduce
qué lo compensa
tests que lo cubren
```

No corregir el orden por intuición; comprobar consecuencias sobre host/tenant resolution.

## Tenant context

Revisar todos los puntos que aceptan:

```text
empresa_id
tenant_id
schema_name
sede_id
organization_id
```

Nunca confiar en identificadores enviados por el cliente si el contexto puede derivarse de:

```text
request.tenant
session
authenticated user
organization membership
```

## Cross-tenant access

Buscar:

```text
Model.objects.get(pk=request.data[...])
Model.objects.filter(pk=...)
get_object_or_404(Model, pk=...)
```

sin scope tenant/organization.

Corregir los que permitan bypass de aislamiento.

## PostgreSQL

Auditar:

```text
search_path
schema ownership
CREATE
USAGE
PUBLIC privileges
```

No permitir que una identidad no confiable pueda crear objetos donde eso pueda afectar resolución de objetos o funciones.

Revisar funciones `SECURITY DEFINER` y cualquier uso de SQL no cualificado.

## Loop

Volver a buscar todas las rutas de acceso a ORM, managers, selectors y raw SQL que puedan saltarse el scope.

No ejecutar tests.

---

# 7. FASE 4 — AUTHENTICATION Y AUTHORIZATION

## Objetivo

Aplicar mínimo privilegio en toda API y UI.

## Cadena de autorización objetivo

```text
Authentication
↓
Tenant membership
↓
Organization/sede scope
↓
Role
↓
Object scope
↓
Action permission
```

## DRF

Revisar todos los:

```text
APIView
ViewSet
ModelViewSet
@api_view
routers
serializers
```

Buscar permisos ausentes o excesivamente amplios.

## Principio

No permitir que:

```text
IsAuthenticated
```

sea la única defensa para un recurso tenant-sensitive.

## IDs

Un UUID no es autorización.

El queryset debe estar correctamente scoped.

## JWT

Revisar:

```text
SIGNING_KEY
ALGORITHM
ACCESS_TOKEN_LIFETIME
REFRESH_TOKEN_LIFETIME
BLACKLIST
```

No migrar a RS256 si no se valida previamente todo el ciclo de emisión/verificación/rotación. Si se decide HS256, usar una clave fuerte y exclusiva.

## Session auth

Revisar coexistencia JWT + SessionAuthentication y evitar comportamientos distintos por endpoint sin documentación.

## Loop

Buscar nuevamente endpoints con `permission_classes` débiles y objetos obtenidos sin scope.

No ejecutar tests.

---

# 8. FASE 5 — SERVICE LAYER Y ELIMINACIÓN DE CAMINOS DUPLICADOS

## Objetivo

Hacer que la lógica de negocio tenga un único camino.

## Flujo canónico

```text
UI/API
↓
Serializer / DTO
↓
Service
↓
Selector
↓
Model / external gateway
```

## Revisar duplicaciones

Especialmente:

```text
services.py
business_service.py
crud_service.py
api_mixins.py
selectors.py
views.py
views_ui.py
api/viewsets.py
core/services/
```

No eliminar capas automáticamente. Consolidar cuando tengan responsabilidades solapadas.

## Reglas

Los ViewSets no deben contener lógica de negocio compleja.

Las vistas no deben mutar múltiples entidades de dominio directamente.

Los serializers deben validar transporte/entrada, no convertirse en servicios empresariales.

Los selectors deben encargarse de lectura/scoping reutilizable.

Los Services deben manejar mutaciones y orquestación.

## Transacciones

Operaciones que cambien varias entidades deben utilizar transacciones apropiadas.

Mantener invariantes importantes a nivel de base de datos cuando sea viable.

## Concurrencia

Revisar específicamente:

```text
numeración contable
retenciones
recepciones
stock
cartera
pagos
facturación
```

No sustituir garantías de DB por contadores Python.

## Loop

Rebuscar ORM directo fuera de Service Layer en módulos críticos.

No ejecutar tests.

---

# 9. FASE 6 — ELIMINACIÓN DE SIGNALS COMO MECANISMO DE NEGOCIO

## Objetivo

Cumplir la arquitectura declarada de Service Layer explícito.

## Inspeccionar

```text
apps/public/accounts/signals.py
apps/public/tenants/signals.py
apps/tenant/**/signals.py
```

## Regla

No utilizar signals para efectos empresariales ocultos.

Migrar cualquier flujo de negocio a servicios explícitos.

Ejemplo:

```text
UserDeletionService
↓
TenantCleanupService
↓
AuditService
```

En lugar de:

```text
delete()
↓
implicit signal
↓
side effect
```

Si queda algún signal puramente técnico, justificarlo explícitamente y marcarlo como excepción arquitectónica.

## Loop

Buscar imports de `django.dispatch`, `receiver`, `post_save`, `pre_save`, `post_delete`, etc.

No ejecutar tests.

---

# 10. FASE 7 — API CONTRACTS / OPENAPI

## Objetivo

Garantizar una API estable y documentada.

## Acciones

Revisar:

```text
/api/v1/
NamespaceVersioning
drf-spectacular
serializers
pagination
filters
ordering
errors
```

Unificar formato de error.

Mantener:

```json
{
  "status": 400,
  "code": "...",
  "message": "...",
  "request_id": "..."
}
```

sin exponer traceback/SQL/secretos.

## OpenAPI gate

Preparar un mecanismo para comparar el schema generado con la versión previa y detectar breaking changes.

No ejecutar generación/validación ejecutable hasta la fase final.

---

# 11. FASE 8 — FILE UPLOAD / DOCUMENT INGEST SECURITY

## Objetivo

Endurecer XML/PDF/XLS/XLSX/CSV/TXT/HTML/images y demás archivos externos.

## Pipeline objetivo

```text
Upload
↓
Size limit
↓
Filename normalization
↓
Extension validation
↓
MIME/type validation
↓
Magic bytes
↓
Malware scanning hook
↓
Storage seguro
↓
Parser aislado
↓
Normalizer
↓
Validator
↓
Service
↓
Persistence
```

## Revisar

```text
path traversal
zip bombs
oversized files
unexpected MIME
polyglot files
HTML execution
unsafe temp paths
user-controlled filenames
```

Nunca utilizar el nombre enviado por el cliente directamente como ruta de almacenamiento.

## Loop

Rebuscar todos los endpoints de subida, no únicamente el pipeline universal.

---

# 12. FASE 9 — CELERY / REDIS / JOBS ASÍNCRONOS

## Objetivo

Hacer las tareas robustas, idempotentes y observables.

## Revisar

```text
Celery serializer
queues
routes
timeouts
retries
acks
idempotency
schema_context
```

## Reglas

Una tarea tenant-aware debe establecer correctamente el schema/contexto antes de acceder a modelos tenant.

Las tareas con efectos externos deben soportar:

```text
retry
backoff
idempotency
failure recording
correlation id
```

Especial atención a:

```text
DIAN
email
WhatsApp
payments
document ingestion
AI
webhooks
```

---

# 13. FASE 10 — AI PROVIDER ARCHITECTURE

## Objetivo

Eliminar dependencia del modelo/proveedor concreto.

## Arquitectura objetivo

```text
AIProviderRegistry
↓
AIProviderAdapter
↓
AIEngine
↓
Tool Registry
↓
Service Layer
```

## Proveedores

Preparar capacidad para:

```text
Ollama
LM Studio
OpenAI-compatible REST
OpenAI
Anthropic
Gemini
REST generic
MCP
```

No acoplar la lógica de negocio a SDKs concretos.

## Contrato recomendado

Separar capacidades:

```text
chat
streaming
structured output
function/tool calling
vision
multimodal
embeddings
health
model listing
```

Un proveedor puede no soportar todas las capacidades.

## Capability registry

Implementar/normalizar:

```text
Provider
Model
Capability
Credential
Health
Usage
```

## Persistencia

La configuración de proveedor debería poder declararse por tenant/entorno según la arquitectura existente.

Separar configuración de secretos.

Nunca almacenar API keys en texto plano si pueden evitarse.

Crear una capa:

```text
CredentialService
```

para cifrado/descifrado y acceso controlado.

## Loop

Buscar cualquier import directo de SDKs desde:

```text
views
serializers
services de negocio
tools
```

Todo debe pasar por adapter/provider.

No ejecutar pruebas AI todavía.

---

# 14. FASE 11 — AI ENGINE / TOOL GOVERNANCE / MCP

## Objetivo

Mantener la IA como una capa controlada, tenant-aware y auditable.

## AIEngine

Mantener el principio:

```text
request context
↓
tenant context
↓
feature flags
↓
policy
↓
tool
```

Nunca permitir que `tenant_id`/`empresa_id` del payload de IA sustituya el contexto real del request.

## Tool metadata

Cada tool debería disponer de al menos:

```text
name
description
domain
kind
risk
confirmation_required
idempotent
tenant_scoped
required_roles
required_permissions
data_classification
auditing
timeout
side_effects
approval_policy
```

## WRITE tools

Mantener bloqueo estructural hasta disponer de:

```text
human approval
policy enforcement
full audit
idempotency
rollback/compensation strategy
```

## MCP

Revisar:

```text
authentication
authorization
tenant scope
rate limiting
tool allowlist
tool risk
audit
request size
timeouts
```

No habilitar bypass de autenticación/permisiones.

## Loop

Rebuscar cualquier forma alternativa de invocar una tool sin pasar por `AIEngine`.

---

# 15. FASE 12 — RAG / PGVECTOR / OPENSEARCH / NEO4J

## Objetivo

Definir responsabilidades únicas.

## Source of truth

```text
PostgreSQL = source of truth
```

## Roles

```text
pgvector
= semantic retrieval

OpenSearch
= lexical/document search

Neo4j
= knowledge graph / architecture graph
```

No permitir que motores secundarios se conviertan accidentalmente en autoridad de negocio.

## pgvector

Verificar:

```text
embedding model
embedding dimension
metric
index
tenant scope
document version
chunk version
embedding version
reindex strategy
```

Al cambiar de modelo de embeddings, usar versionado que permita reindexación controlada.

---

# 16. FASE 13 — OBSERVABILIDAD Y LOGGING

## Objetivo

Poder rastrear una operación de punta a punta sin exponer secretos.

## IDs

Introducir/normalizar:

```text
request_id
correlation_id
tenant_id
user_id
task_id
ai_execution_id
tool_execution_id
```

## Logging

Nunca registrar:

```text
password
API keys
Authorization headers
JWT completos
SMTP passwords
payment secrets
request bodies sensibles
```

Mantener tracebacks únicamente en el backend de logs, con controles de acceso.

## API errors

Usar `request_id` para correlacionar errores.

---

# 17. FASE 14 — DOCKER Y PRODUCCIÓN

## Objetivo

Separar correctamente desarrollo, test y producción.

## Desarrollo

Puede mantener puertos publicados para facilitar desarrollo.

## Producción

Verificar que:

```text
PostgreSQL → no public port
Redis → no public port
Neo4j → no public port
```

Únicamente el entrypoint/proxy necesario debe exponerse públicamente.

## Containers

Revisar:

```text
non-root user
read-only filesystem cuando sea viable
capabilities mínimas
healthcheck
restart policy
resource limits
secrets/env handling
```

## Dockerfile

Reducir:

```text
layers innecesarias
paquetes de build en runtime
privilegios
archivos temporales
```

---

# 18. FASE 15 — GITHUB ACTIONS / SUPPLY CHAIN

## Objetivo

Convertir CI en una barrera real.

## Todos los workflows

Revisar:

```text
.github/workflows/ci-quality-gate.yml
.github/workflows/verify-core.yml
.github/workflows/verify-phase5.yml
```

## Permissions

Agregar mínimo privilegio, por ejemplo cuando sea suficiente:

```yaml
permissions:
  contents: read
```

No otorgar permisos globales que ningún job necesita.

## Pinning

Cambiar referencias tipo:

```yaml
uses: actions/checkout@v4
```

a SHA completo validado del repositorio oficial de la Action.

Aplicar a:

```text
checkout
setup-python
upload-artifact
otras actions de terceros
```

No inventar SHAs. Obtenerlos de la release/commit oficial.

## Quality gates

Eliminar progresivamente:

```text
continue-on-error: true
```

Dejar como blocking:

```text
Django checks
migration checks
Ruff
Bandit
pip-audit
pytest
architecture checks
EKG validation
```

## Dependencias

Agregar controles de supply chain apropiados.

No permitir que una vulnerabilidad crítica conocida pase silenciosamente a producción.

---

# 19. FASE 16 — BACKUP / RESTORE / RECOVERY

## Objetivo

Convertir backup en capacidad verificable de recuperación.

Revisar comandos existentes:

```text
backup_tenant
backup_all
restore_tenant
```

Preparar un procedimiento reproducible:

```text
backup
↓
restore en entorno aislado
↓
integrity verification
↓
tenant routing verification
↓
application smoke
```

No ejecutar restore destructivo antes de la fase final y sin autorización de ejecución de tests.

---

# 20. FASE 17 — REPOSITORY HYGIENE

## Objetivo

Separar producto, documentación y configuración privada.

Revisar:

```text
.agents/
.antigravity/
.claude/
```

Si contienen configuración privada o local, eliminar del tracking si corresponde y verificar historial.

## Secret scanning

Inspeccionar el historial de Git buscando:

```text
API keys
passwords
tokens
private keys
JWT secrets
SMTP credentials
Cloudflare tokens
payment credentials
AI provider credentials
```

Si existió un secreto real en Git histórico, considerarlo comprometido y preparar rotación. No registrar el secreto en la documentación de corrección.

## Archivos grandes

Buscar documentación/artefactos innecesariamente grandes y decidir:

```text
mantener
comprimir
mover a docs
mover a otro repositorio
eliminar
```

No borrar información arquitectónica útil sin preservar su contenido relevante.

---

# 21. FASE 18 — LIMPIEZA DE DUPLICACIONES

## Objetivo

Reducir complejidad sin alterar contratos públicos.

Buscar duplicados de:

```text
settings
urls
serializers
viewsets
permissions
services
selectors
mixins
pagination
error handling
currency helpers
tenant context
organization context
```

Unificar únicamente cuando tengan semántica equivalente.

Mantener adaptadores de compatibilidad si existe código cliente que dependa de una interfaz antigua.

---

# 22. FASE 19 — DOCUMENTACIÓN DE ARQUITECTURA

Crear/actualizar:

```text
docs/architecture/ARCHITECTURE.md
docs/security/SECURITY_MODEL.md
docs/security/MIDDLEWARE_SECURITY_ORDER.md
docs/security/MULTITENANT_SECURITY.md
docs/ai/AI_PROVIDER_ARCHITECTURE.md
docs/ai/AI_TOOL_GOVERNANCE.md
docs/operations/PRODUCTION_RUNBOOK.md
```

Cada documento debe reflejar **el código real**, no una arquitectura futura ficticia.

---

# 23. FASE 20 — PREPARACIÓN DE LA BATERÍA FINAL DE TESTS

Esta fase NO ejecuta tests.

Aquí solamente crear/corregir la suite que se ejecutará al final.

## Suites obligatorias

```text
Django system/security checks
Migration consistency
Pytest unit tests
Pytest integration tests
Multitenant isolation
Authorization/object scope
Accounting concurrency
File upload security
Celery behavior
AI Engine
Tool Registry
MCP permissions
RAG/vector isolation
OpenAPI/schema
Docker production configuration
GitHub workflow validation
Ruff
Bandit
pip-audit
EKG extraction/validation
```

## Tests multitenant obligatorios

Crear/garantizar cobertura para:

```text
Tenant A cannot read Tenant B
Tenant A cannot write Tenant B
Tenant A cannot delete Tenant B
UUID guessing cannot cross tenant boundary
Sede/organization scope cannot cross boundary
Public schema cannot leak tenant data
Tenant schema cannot access unauthorized public data
```

## Tests de seguridad del proxy

Preparar casos para:

```text
Host válido
Host inválido
X-Forwarded-Host spoof
X-Forwarded-Proto spoof
CSRF origin válido
CSRF origin inválido
CORS válido
CORS inválido
```

## Tests AI

Preparar:

```text
provider selection
unknown provider
unsupported capability
credential isolation
tenant isolation
READ tool
VALIDATE tool
SUGGEST tool
WRITE blocked without approval
MCP authorization
```

---

# 24. PUNTO DE CONTROL OBLIGATORIO ANTES DE TESTS

Cuando todas las fases anteriores hayan terminado, detener el proceso.

No ejecutar ninguna prueba aún.

La IA editora debe entregar únicamente un resumen de:

```text
archivos modificados
migraciones creadas
dependencias modificadas
workflows modificados
hallazgos corregidos
hallazgos pendientes
riesgos conocidos
```

Y solicitar al usuario exactamente una autorización:

```text
AUTORIZACIÓN REQUERIDA PARA EJECUTAR LA BATERÍA FINAL DE TESTS.
```

No solicitar ninguna otra aprobación.

---

# 25. FASE FINAL — EJECUCIÓN DE TESTS

**Solo ejecutar después de recibir autorización explícita del usuario.**

Orden recomendado:

## 25.1 Integridad Python

```bash
python -m compileall apps config tools
```

## 25.2 Django

```bash
python manage.py check
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
```

## 25.3 Migraciones multitenant

En entorno de test/CI apropiado:

```bash
python manage.py migrate_schemas --shared
python manage.py migrate_schemas
```

No ejecutar contra producción.

## 25.4 Ruff

```bash
python -m ruff check apps config tools
python -m ruff format --check apps config tools
```

## 25.5 Bandit

```bash
python -m bandit -q -r apps -x "*/migrations/*,*/tests/*"
```

## 25.6 pip-audit

```bash
python -m pip_audit -r requirements.txt
```

Si se utiliza otro lockfile, auditar el conjunto real instalado/resuelto.

## 25.7 Pytest

```bash
pytest
```

Después de una primera corrida fallida:

```text
analizar
corregir
revisar
volver a ejecutar la suite afectada
```

La autorización otorgada para la fase final cubre los reintentos normales de tests necesarios para corregir los fallos descubiertos durante esta fase.

## 25.8 EKG

Ejecutar extracción y validación configuradas para el proyecto.

## 25.9 CI local equivalente

Reproducir, en la medida viable, la secuencia usada por GitHub Actions.

## 25.10 Docker test

Construir y levantar únicamente el entorno seguro de test, sin afectar producción.

## 25.11 Smoke final

Realizar pruebas funcionales críticas:

```text
public tenant
login
tenant resolution
CRUD básico
permisos
facturación
contabilidad
inventario
clientes
compras
ventas
AI config
AI read tool
MCP
```

---

# 26. LOOP DURANTE LA FASE FINAL DE TESTS

La autorización de tests permite este ciclo:

```text
RUN TEST
↓
FAIL
↓
ANALYZE
↓
FIX CODE
↓
STATIC REVIEW
↓
RUN AFFECTED TEST
↓
PASS
↓
NEXT TEST/SUITE
```

La IA editora puede corregir código durante la fase final.

No eliminar tests para obtener verde.

No desactivar controles.

No introducir `skip`, `xfail`, `continue-on-error` o excepciones artificiales salvo una justificación documentada y temporal.

---

# 27. CRITERIOS DE ACEPTACIÓN

La ejecución queda terminada solamente cuando:

```text
[ ] Django 5.2.x vigente y compatible
[ ] Dependencias reproducibles
[ ] DEBUG fail-closed
[ ] SECRET_KEY fail-closed
[ ] ALLOWED_HOSTS controlados
[ ] HTTPS endurecido
[ ] Proxy headers controlados
[ ] CORS controlado
[ ] CSRF controlado
[ ] Middleware documentado y probado
[ ] Public/Tenant isolation validado
[ ] PostgreSQL schema privileges revisados
[ ] search_path revisado
[ ] Authentication revisada
[ ] Authorization revisada
[ ] Object-level scope revisado
[ ] Service Layer consolidado
[ ] Signals de negocio eliminados
[ ] Transactions revisadas
[ ] Concurrency revisada
[ ] Upload security revisada
[ ] Celery idempotencia/retry revisados
[ ] AI Provider Registry desacoplado
[ ] Credenciales AI protegidas
[ ] Tool governance reforzada
[ ] MCP protegido
[ ] pgvector aislado
[ ] OpenSearch con responsabilidad definida
[ ] Neo4j con responsabilidad definida
[ ] Logging sin secretos
[ ] Correlation IDs
[ ] Docker production hardening
[ ] GitHub Actions permissions mínimos
[ ] GitHub Actions SHA pinned
[ ] Ruff bloqueante
[ ] Bandit bloqueante
[ ] pip-audit bloqueante
[ ] migration check bloqueante
[ ] EKG gate bloqueante donde corresponda
[ ] Backup/restore procedure documentada
[ ] Secret scan revisado
[ ] Suite final ejecutada
[ ] Todos los tests críticos verdes
```

---

# 28. FORMATO DE INFORME FINAL DE LA IA EDITORA

Al terminar la fase final, generar:

```text
AUDITORIA_FINAL_CRM_SINTEL.md
```

Con esta estructura:

```text
1. Resumen ejecutivo
2. Estado inicial
3. Cambios realizados
4. Archivos modificados
5. Dependencias modificadas
6. Migraciones creadas
7. Mejoras de seguridad
8. Mejoras multitenant
9. Mejoras Service Layer
10. Mejoras CI/CD
11. Mejoras Docker
12. Mejoras AI/MCP
13. Tests ejecutados
14. Resultados
15. Fallos encontrados y corregidos
16. Riesgos residuales
17. Deuda técnica restante
18. Recomendaciones posteriores
```

Incluir hashes/commits relevantes cuando existan.

---

# 29. PRINCIPIO FINAL

No implementar una arquitectura más compleja solamente porque sea posible.

Preferir:

```text
simple
explícito
seguro
testeable
observable
reproducible
```

La regla central para CRM_SINTEL es:

```text
NINGUNA GARANTÍA CRÍTICA DEBE EXISTIR SOLO EN DOCUMENTACIÓN.

DEBE EXISTIR EN:

CÓDIGO
+
REGLA DE BASE DE DATOS CUANDO APLIQUE
+
TEST
+
CI GATE
```

Especialmente para:

```text
tenant isolation
authorization
accounting invariants
concurrency
financial operations
AI tool execution
MCP
secrets
production configuration
```

---

# 30. ESTADO INICIAL DEL PROCESO

Al comenzar:

```text
CURRENT_PHASE = 0
TEST_AUTHORIZATION = NOT_GRANTED
FINAL_TESTS_EXECUTED = FALSE
```

La IA debe avanzar automáticamente por las fases 0–20, aplicando el loop de auditoría/corrección/re-auditoría.

Al llegar al punto de control:

```text
STOP
↓
REQUEST TEST AUTHORIZATION
```

Después de recibir autorización:

```text
RUN TESTS
↓
FIX FAILURES
↓
RERUN
↓
FINAL REPORT
```

No terminar el trabajo antes de la batería final salvo que exista una imposibilidad técnica real; en ese caso documentar exactamente el bloqueo y no inventar resultados.
