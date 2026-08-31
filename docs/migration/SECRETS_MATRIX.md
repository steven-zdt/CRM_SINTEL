# SECRETS_MATRIX — Fases 9, 10, 25

Solo NOMBRES de variables -- **ningún valor real en este documento**.

## Almacenamiento actual

Todos los secretos viven en `.env` (raíz del repo, **no versionado** --
confirmado: `git status --porcelain .env` no lo lista, y no aparece en
ningún commit del historial reciente auditado). `docker-compose.yaml`
los inyecta a cada contenedor vía `environment:`. No hay Docker
secrets, vault, ni almacenamiento en el host fuera de `.env`.

## Inventario de variables (nombre → categoría → sensible?)

| Variable | Categoría | Sensible |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django | **Sí** |
| `JWT_SECRET_KEY` | Auth/JWT | **Sí** |
| `DATABASE_HOST` | DB | No |
| `DATABASE_NAME` | DB | No |
| `DATABASE_USER` | DB | No |
| `DATABASE_PASSWORD` | DB | **Sí** |
| `DATABASE_PORT` | DB | No |
| `REDIS_URL` | Redis | No (sin credenciales embebidas) |
| `NEO4J_URI` | Storage | No |
| `NEO4J_USER` | Storage | No |
| `NEO4J_PASSWORD` | Storage | **Sí** |
| `EMAIL_BACKEND` | SMTP | No |
| `EMAIL_HOST` | SMTP | No |
| `EMAIL_HOST_USER` | SMTP | No (email, no secreto per se) |
| `EMAIL_HOST_PASSWORD` | SMTP | **Sí** |
| `EMAIL_PORT` | SMTP | No |
| `EMAIL_USE_TLS` / `EMAIL_USE_SSL` | SMTP | No |
| `DEFAULT_FROM_EMAIL` | SMTP | No |
| `TUNNEL_TOKEN` | Cloudflare | **Sí** |
| `ALLOWED_HOSTS` | Django | No (config, no secreto) |
| `DJANGO_DEBUG` | Django | No |
| `ACTIVATION_BASE_URL` | Django | No |
| `SITE_PROTOCOL` | Django | No |

No se detectaron variables DIAN/IMAP en el `.env` actual de este
entorno (el adaptador DIAN real usa mock en desarrollo, ver
`docs/production/PRODUCTION_BLOCKERS.md` `FISCAL-01`).

## Secretos hardcodeados en código (Fase 10)

**Ninguno detectado** -- ya verificado por el check automatizado
`SEC-01-secret-scanning` del framework de producción de esta misma
sesión (`apps/public/core/production_readiness/checks.py`), que
escanea `apps/`+`config/` en busca de patrones de claves/certificados
hardcodeados. Última corrida real: `PASS`.

`ROTATION_REQUIRED`: **No** -- no se detectaron secretos hardcodeados
que requieran rotación por esta causa. Nota aparte (ya documentada en
la misión de producción previa, no repetida aquí): `DJANGO_SECRET_KEY`
usa un valor de desarrollo con el marcador `django-insecure-` --
blocker `APP-02-secret-key` ya conocido, requiere una clave real
generada para el entorno de destino (acción de configuración del
TARGET, no de este documento).

## Transferencia a TARGET (recomendación, no ejecutada)

Nunca copiar `.env` por un canal no cifrado (chat, email plano, Git).
Canal recomendado: gestor de secretos del proveedor del TARGET, o
transferencia cifrada punto a punto (ej. `age`/`gpg`) fuera de este
repositorio. Rotar `DJANGO_SECRET_KEY`/`JWT_SECRET_KEY` en el TARGET
en vez de reusar los de SOURCE (invalida sesiones activas de SOURCE,
lo cual es exactamente el comportamiento deseado tras un cutover real).
