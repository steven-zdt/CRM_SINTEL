# LAN_MULTI_TENANT — Arquitectura de acceso multi-tenant por LAN

Documento de referencia (Fase 32). Para la investigación completa,
hallazgos y evidencia, ver `LAN_MULTI_TENANT_FINAL_REPORT.md`. Para el
levantamiento crudo, ver `LAN_MULTI_TENANT_BASELINE.md`.

## Arquitectura (obligatoria, no modificada por esta misión)

```
IP LAN del servidor
    |
DNS / hostname (wildcard *.sintel.net.co)
    |
Nginx (0.0.0.0:80 / 0.0.0.0:443, server_name _, proxy_set_header Host $host)
    |
Django (runserver/gunicorn, SOLO alcanzable via Nginx -- 127.0.0.1:8000, nunca 0.0.0.0:8000)
    |
TenantMainMiddleware (django-tenants) -- hostname normalizado -> Domain -> schema
    |
TenantSecurityAndURLConfMiddleware -- valida ambito publico/privado, establece URLConf
    |
Domain (tabla, schema public) -- 1 fila por hostname, is_primary
    |
Client/Tenant (schema public) -- 1 fila por tenant
    |
PostgreSQL schema aislado
```

**Regla que no se rompe:** la IP identifica la máquina servidora. El
`Domain` (hostname) identifica el tenant. Nunca se convierte una IP en
identificador de tenant -- un mismo servidor sirve N tenants distintos
por hostname.

## IP del servidor

`192.168.2.17` (estática, adaptador Ethernet). **Actualizado
2026-08-31**: originalmente configurada como `192.168.2.15`, que
resultó estar duplicada en la red (otra máquina física respondía con el
mismo valor -- ver Hallazgo 1 del informe final). Reasignada a `.17`
(verificada libre por ARP antes de asignarla, sin conflicto desde
entonces). La arquitectura de código no depende de un valor
hardcodeado de IP en ningún punto del stack Django/Nginx/Docker; toda
referencia a la IP del servidor es configuración de entorno (`.env`,
`TENANT_DOMAIN_BASE`, `extra_hosts`), no una constante de código -- el
cambio de IP no requirió tocar Nginx/Django/Docker.

## DNS

Diseño: Windows DNS Server (en `192.168.2.15`) con zona `sintel.net.co`,
registro wildcard `* -> 192.168.2.15`, distribuido a la LAN vía DHCP del
router (`Primary DNS = 192.168.2.15`). **Estado real:** no operativo hoy
-- ver Hallazgo 2 del informe final. `docker-compose.yaml`'s
`dns: [192.168.2.15]` solo afecta la resolución DNS *dentro* de los
contenedores (para sus propias necesidades salientes), no resuelve nada
para clientes de la LAN.

## Domain (tenant objetivo de esta misión)

| Campo | Valor |
|---|---|
| `domain` | `admin.sintel.net.co` |
| `tenant` (schema) | `admin` |
| `is_primary` | `True` |
| Owner | `admin@sintel.net.co` |
| Creado | 2026-08-31, vía `crear_tenant_con_owner()` (no existía antes de esta misión) |

## Nginx

`nginx/nginx.conf` -- bloques `listen 80` y `listen 443 ssl`,
`server_name _` (catch-all, correcto para multi-tenant por Host header),
`proxy_set_header Host $host` (preserva el hostname real hacia Django,
nunca lo reemplaza por `localhost`/`127.0.0.1`).

## Firewall (esta máquina)

Regla "Docker Desktop Backend" (perfil `Public`) permite cualquier
puerto publicado por Docker. Tras esta misión: 80/443 (Nginx, correcto,
LAN-alcanzable) y 8000 (Django, corregido a solo-loopback, ya no
LAN-alcanzable). `db`/`redis`/`neo4j` ya estaban correctamente acotados
a `127.0.0.1`.

## ALLOWED_HOSTS / CSRF / CORS

`config/settings.py` -- todos derivados de `TENANT_DOMAIN_BASE`
(`sintel.net.co`) vía wildcards con punto inicial (`.sintel.net.co`),
sin usar `ALLOWED_HOSTS = ["*"]` ni CORS abierto universal. Detalle
completo con líneas exactas en `LAN_MULTI_TENANT_FINAL_REPORT.md`.

## TenantMiddleware

Resuelve por **hostname**, nunca por email. El email
(`admin@sintel.net.co`) identifica al usuario dentro de un tenant ya
resuelto; el hostname (`admin.sintel.net.co`) identifica el tenant en
sí, vía la tabla `Domain`. Confirmado en vivo: requests con distinto
`Host` header devuelven respuestas de distinto tenant.
