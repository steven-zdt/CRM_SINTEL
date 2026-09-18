# N8N_ARCHITECTURE — n8n como orquestador externo

Mision N8N-SINTEL-01 (2026-09-09). n8n es una plataforma de automatizacion
EXTERNA al dominio SINTEL -- nunca conoce reglas fiscales, contables, de
inventario, ni de Ventas/Compras. Toda regla de negocio vive y se ejecuta
exclusivamente dentro de SINTEL (Service Layer).

## Decision arquitectonica (confirmada por el usuario, 2026-09-09)

```
n8n
 |
 v
REST API de SINTEL (no MCP formal en esta pasada -- ver justificacion abajo)
 |
 v
SINTEL Service Layer
 |
 v
Dominio (facturas/ventas/compras/inventario/contabilidad)
 |
 v
SSoT
```

n8n **nunca** tiene acceso directo a PostgreSQL de SINTEL. n8n tiene su
**propia** base de datos, completamente aislada.

## Por que REST API y no MCP formal (Fase 14, decision explicita)

`django-rest-framework-mcp>=0.1.0a4` (el paquete MCP ya instalado en este
proyecto, `/mcp/` montado en `config/urls_tenant.py`/`urls_public.py`)
tiene un **defecto real de terceros ya documentado**: nunca asigna
`HttpRequest.method` en la peticion interna que ejecuta la accion de un
ViewSet decorado, lo que rompe `IsTenantAdminOrReadOnly` (la clase de
permiso mas usada del proyecto) -- confirmado en la mision AI-07
(2026-09-01, ver `docs/ai/AI_MCP_POLICY.md`) y **re-confirmado hoy**
(misma version del paquete sigue fijada en `requirements.txt`, 0
ViewSets decorados en todo `apps/`).

Para las tools READ deterministas que esta mision necesita
(`get_invoice`, `search_invoices`, etc.), REST API simple es:
- mas seguro (sin el defecto de terceros);
- mas simple (n8n consume con su nodo HTTP Request nativo, sin necesitar
  el nodo MCP Client Tool/AI Agent);
- suficiente (estas operaciones son deterministas, no requieren que un
  LLM elija dinamicamente que tool llamar -- eso es exactamente lo que
  MCP aporta, y no es lo que este piloto necesita).

**MCP formal queda DEFERRED** -- si en el futuro se necesita composicion
inteligente real (un agente de n8n decidiendo dinamicamente que
operacion de SINTEL ejecutar segun lenguaje natural), retomar
`django-rest-framework-mcp` requiere primero resolver o mitigar su
defecto (actualizar el paquete, o decorar solo ViewSets cuyos permisos
no dependan de `request.method`, ver `AI_MCP_POLICY.md` para las 3 rutas
ya evaluadas). Alternativa ya construida y reutilizable si se retoma
MCP: el AI Engine (`apps/services/ai/`) ya tiene 20 tools semanticas
registradas con DSV/scope/clasificacion de riesgo -- exponerlas via MCP
en el futuro es mas seguro que decorar ViewSets de negocio directamente.

## Topologia real (verificada, `docker-compose.yaml`)

```
Internet
   |
   v
Cloudflare Tunnel (cloudflared, TUNNEL_TOKEN)
   |
   v
nginx (unico server compartido, server_name "_", puertos 80/443)
   |
   v
web (Django, ruteo multi-tenant real por Host header)
```

n8n **no** participa de esta cadena publica -- corre en su propio
contenedor, puerto **solo en `127.0.0.1:5678`** (mismo patron que
`db`/`redis`/`neo4j`: accesible desde el host para configuracion, nunca
desde la LAN/Internet). **Exposicion publica queda DEFERRED** (decision
explicita del usuario, ver `N8N_RELEASE_GATE.md`) -- el diseño para
cuando se decida exponerlo:

```
automation.sintel.net.co
   |
   v
nginx (nuevo server_name en nginx/nginx.conf, proxy_pass http://n8n:5678)
   |
   v
n8n
```

## Base de datos de n8n — aislamiento real, verificado con evidencia

n8n usa el **mismo servidor** Postgres que SINTEL (`db`, contenedor
`crm_sintel-db-1`) pero una **base de datos separada** (`n8n`), con un
**rol dedicado** (`n8n`, sin superusuario). Verificado con evidencia
real (no solo diseñado):

```sql
-- Confirmado ANTES del fix: el rol n8n SI podia conectar a `sintel`
-- (Postgres otorga CONNECT a PUBLIC por defecto en toda DB nueva).
REVOKE CONNECT ON DATABASE sintel FROM PUBLIC;
GRANT CONNECT ON DATABASE sintel TO sintel;

-- Confirmado DESPUES del fix:
-- $ psql -U n8n -d sintel -> "FATAL: permission denied for database sintel"
-- $ psql -U sintel -d sintel -> funciona normal (no se rompio nada)
```

n8n **nunca** recibe `DATABASE_PASSWORD`/`DATABASE_USER` de SINTEL --
solo conoce `N8N_DB_*` (variables separadas en `.env`).

## Contenedor n8n (`docker-compose.yaml`)

```yaml
n8n:
  image: n8nio/n8n:1.81.0   # version fijada, NO latest (verificado real en Docker Hub)
  environment:
    - N8N_ENCRYPTION_KEY=...       # obligatorio, sin fallback debil
    - DB_TYPE=postgresdb
    - DB_POSTGRESDB_HOST=db        # mismo servidor, DB distinta
    - DB_POSTGRESDB_DATABASE=n8n
    - DB_POSTGRESDB_USER=n8n
    - GENERIC_TIMEZONE=America/Bogota
  volumes:
    - n8n_data:/home/node/.n8n     # named volume Docker nativo -- no bind-mount
                                     # del checkout, evita el overhead de I/O
                                     # que un bind-mount tiene en Windows
  ports:
    - "127.0.0.1:5678:5678"        # solo host local
  healthcheck:
    test: wget http://127.0.0.1:5678/healthz
```

Verificado real (2026-09-09): `docker compose up -d n8n` -> pull de la
imagen real, migraciones internas de n8n corridas sin error, healthcheck
`healthy` en segundos, `curl http://127.0.0.1:5678/healthz` -> `200`.
Resto del stack SINTEL (`db`/`redis`/`neo4j`/`nginx`/`celery`/`web`)
verificado sano despues del cambio -- nada se rompio.

## Autenticacion SINTEL <-> n8n (Fase 13)

Identidad tecnica dedicada (nunca un usuario humano), un JWT por tenant,
reutilizando el mecanismo JWT ya existente de SINTEL (simplejwt, con
rotacion/blacklist ya configurados) -- no se crea un segundo mecanismo
de auth. Ver `N8N_SECURITY.md` para el detalle completo.

## Eventos SINTEL -> n8n (Fase 8)

`apps/services/integration_events/` -- modulo nuevo, transversal, que NO
conoce reglas de dominio (mismo principio que
`apps/services/document_intake/`). Los dominios llaman explicitamente a
`publish_event()` en el punto donde la operacion de negocio ya se
completo -- **nunca** via Django signal (regla del proyecto: cero
signals para logica de negocio/integracion, confirmada sin excepciones
en todo el codebase). Entrega asincrona via Celery (`send_webhook_event`,
mismo patron de retry que `maildigester.tasks`), firmada con
HMAC-SHA256 (`X-Sintel-Signature`) para que n8n valide el origen.

Primer punto de integracion real conectado (Workflow A, ver
`N8N_WORKFLOWS.md`): `FacturaUBLMixin.upload_document()` publica
`invoice.processed`/`invoice.duplicate` tras persistir con exito -- "best
effort", nunca rompe la respuesta HTTP si la publicacion falla.
