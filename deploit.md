# DEPLOIT.md — Guía de Alistamiento y Despliegue a Producción

> **Proyecto:** CRM Sintel — SaaS multi-tenant (Django 5 + django-tenants + Celery + Redis + PostgreSQL + Nginx)
> **Fecha de auditoría:** 2026-06-15
> **Alcance:** Auditoría de alistamiento (deployment readiness) + procedimiento de despliegue por fases.
>
> Este documento se lee **en orden, de la Fase 0 a la Fase 12**. No saltar fases.
> Cada fase tiene: objetivo, pasos numerados, comando de verificación y criterio de salida (✅).

---

## 📊 Resumen de la auditoría (estado actual)

| # | Hallazgo | Severidad | Archivo | Fase que lo resuelve |
|---|----------|-----------|---------|----------------------|
| 1 | `DJANGO_DEBUG=True` en entorno | 🔴 Bloqueador | `.env` | Fase 1 |
| 2 | Servicio `web` corre `runserver` (dev server) | 🔴 Bloqueador | `docker-compose.yaml:67` | Fase 2 |
| 3 | Bind-mount `.:/app` sobreescribe la imagen | 🔴 Bloqueador | `docker-compose.yaml:10` | Fase 2 |
| 4 | Postgres expuesto a `0.0.0.0:5432` | 🔴 Bloqueador | `docker-compose.yaml:33` | Fase 3 |
| 5 | `debug_headers_view` filtra `HTTP_AUTHORIZATION` | 🔴 Bloqueador | `config/urls_public.py` | Fase 1 |
| 6 | Cert SSL autofirmado (red local) | 🟠 Alto (si es internet) | `nginx/docker-entrypoint.sh` | Fase 4 |
| 7 | JWT HS256 (RS256 recomendado) | 🟡 Medio | `config/settings.py:731` | Fase 1 (opcional) |
| 8 | Sin `.env.example` versionado | 🟡 Medio | — | Fase 1 |
| 9 | Celery worker corre como root (`C_FORCE_ROOT=1`) | 🟡 Medio | `docker-compose.yaml:94` | Fase 9 |
| 10 | Sin Celery Beat / cron de backups automatizado | 🟡 Medio | — | Fase 11 |
| 11 | `SECRET_KEY` 53 chars | ✅ OK | `.env` | — |
| 12 | `JWT_SECRET_KEY` 43 chars (HS256) | ✅ OK | `.env` | — |
| 13 | Health endpoint `/health` operativo | ✅ OK | `config/urls_public.py:90` | Fase 10 |
| 14 | WhiteNoise + collectstatic configurado | ✅ OK | `config/settings.py:338` | Fase 8 |

**Veredicto:** El proyecto **NO está listo para publicar tal cual**. Hay 5 bloqueadores que deben resolverse (Fases 1–4). El resto del documento es el procedimiento completo, incluyendo los fixes.

---

## FASE 0 — Pre-requisitos e inventario del servidor

**Objetivo:** Confirmar que el host destino cumple los requisitos antes de tocar nada.

### Pasos

1. **Servidor destino**
   - SO: Linux (Ubuntu 22.04+ / Debian 12 recomendado) o Windows Server con WSL2/Docker Desktop.
   - CPU: 2+ vCPU. RAM: 4 GB mínimo (8 GB recomendado con Celery + OpenSearch).
   - Disco: 40 GB+ (Postgres + media + backups + logs).

2. **Software base instalado**
   ```bash
   docker --version          # >= 24.x
   docker compose version    # >= v2.20  (plugin, NO docker-compose v1)
   git --version
   ```

3. **Dominio y DNS**
   - Dominio principal: `sintel.net.co` (o el real de producción).
   - Registro **wildcard** `*.sintel.net.co` → IP pública del servidor (para subdominios de tenants).
   - Registro A `sintel.net.co` → IP pública.
   - Confirmar propagación: `dig +short sintel.net.co` y `dig +short cualquiercosa.sintel.net.co`.

4. **Puertos abiertos en el firewall del host/cloud**
   - `80/tcp` (HTTP → redirige a HTTPS y sirve ACME challenge).
   - `443/tcp` (HTTPS).
   - `22/tcp` (SSH, restringido a IPs de administración).
   - **NO abrir** `5432` (Postgres) ni `6379` (Redis) al exterior.

5. **Clonar el repositorio en el servidor**
   ```bash
   git clone <repo-url> /opt/crm_sintel
   cd /opt/crm_sintel
   git checkout main      # rama de producción
   ```

### ✅ Criterio de salida
- `docker compose version` responde v2+.
- `dig +short sintel.net.co` y `dig +short test.sintel.net.co` resuelven a la IP del servidor.
- Repositorio clonado en el servidor.

---

## FASE 1 — Hardening de configuración Django

**Objetivo:** Eliminar todo lo inseguro de desarrollo. Resuelve hallazgos #1, #5, #7, #8.

### 1.1 — Desactivar DEBUG

En el `.env` de **producción**:
```ini
DJANGO_DEBUG=False
```
> Con `DEBUG=False`, `settings.py` activa automáticamente: `ALLOWED_HOSTS` estricto (sin `localhost`), `CSRF_COOKIE_SECURE=True`, `CSRF_COOKIE_DOMAIN=.sintel.net.co`, COOP restrictivo y `SHOW_PUBLIC_IF_NO_TENANT_FOUND=False`. (Ver `config/settings.py:28`, `:285`, `:515`).

### 1.2 — Secrets fuertes y únicos

Generar valores nuevos **solo para producción** (no reutilizar los de desarrollo):
```bash
# SECRET_KEY (>= 50 chars)
python -c "import secrets; print(secrets.token_urlsafe(50))"

# JWT_SECRET_KEY (>= 32 bytes, base64)
python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```
Colocar en `.env`:
```ini
DJANGO_SECRET_KEY=<valor generado>
JWT_SECRET_KEY=<valor generado>
```

### 1.3 — Eliminar el endpoint de debug que filtra tokens 🔴

`config/urls_public.py` define `debug_headers_view`, que devuelve `HTTP_AUTHORIZATION` (tokens JWT) en texto plano. **Quitarlo o protegerlo**:

- **Opción A (recomendada):** eliminar la función `debug_headers_view` y su `path(...)` del `urlpatterns`.
- **Opción B:** envolverlo en `if settings.DEBUG:` para que no exista cuando `DEBUG=False`.

### 1.4 — (Opcional, recomendado) Migrar JWT a RS256

HS256 con clave fuerte es aceptable. Para mayor robustez (firma asimétrica), en `config/settings.py:750` está el bloque comentado. Generar par de llaves:
```bash
openssl genrsa -out jwt_private.pem 2048
openssl rsa -in jwt_private.pem -pubout -out jwt_public.pem
```
Y exportar `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY` en `.env`, descomentando el bloque RS256.

### 1.5 — Crear `.env.example` versionado (sin secretos)

Crear `.env.example` con todas las claves y valores vacíos/placeholder, para documentar el contrato de configuración. **Nunca** commitear el `.env` real (verificar que esté en `.gitignore`).

### 1.6 — Validación de seguridad de Django

```bash
docker compose exec web python manage.py check --deploy
```
Debe salir **sin warnings críticos** (`security.W*`). Los esperados a resolver: `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `SECURE_HSTS_SECONDS`.

> **Nota:** `settings.py` fija `SECURE_SSL_REDIRECT=False`, `SESSION_COOKIE_SECURE=False` y `CSRF_COOKIE_SECURE=False` de forma estática (líneas 363–365), pero la terminación TLS la hace **Nginx** y Django lo detecta vía `SECURE_PROXY_SSL_HEADER` (`:434`). Para endurecer, añadir al final de `settings.py` un bloque condicionado a `not DEBUG`:
> ```python
> if not DEBUG:
>     SECURE_SSL_REDIRECT = False          # Nginx ya redirige 80→443
>     SESSION_COOKIE_SECURE = True
>     SECURE_HSTS_SECONDS = 31536000
>     SECURE_HSTS_INCLUDE_SUBDOMAINS = True
>     SECURE_HSTS_PRELOAD = True
>     SECURE_CONTENT_TYPE_NOSNIFF = True
> ```

### ✅ Criterio de salida
- `DJANGO_DEBUG=False` en `.env` de producción.
- `SECRET_KEY` y `JWT_SECRET_KEY` nuevos y fuertes.
- `debug_headers_view` eliminado/gated.
- `manage.py check --deploy` sin warnings críticos.

---

## FASE 2 — Servidor WSGI de producción (Gunicorn)

**Objetivo:** Reemplazar `runserver` por Gunicorn y dejar de montar el código por bind-mount. Resuelve #2 y #3.

> Gunicorn y WhiteNoise ya están en `requirements.txt` (`:51-52`). Solo falta cablearlos.

### 2.1 — Crear un `docker-compose.prod.yaml`

No editar el `docker-compose.yaml` de desarrollo. Crear un override de producción que:
- Cambie el `command` de `web` a Gunicorn.
- **Elimine** el bind-mount `.:/app` (el código viene en la imagen).
- **Quite** la exposición pública de `5432` y `6379`.

```yaml
# docker-compose.prod.yaml
services:
  db:
    ports: []                      # NO exponer Postgres al exterior
    environment:
      POSTGRES_DB: ${DATABASE_NAME}
      POSTGRES_USER: ${DATABASE_USER}
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD}   # obligatorio, sin default

  redis:
    ports: []                      # NO exponer Redis al exterior

  web:
    volumes:
      - ./media:/app/media         # solo media persistente, NO todo el código
      - ./staticfiles:/app/staticfiles
    command: ["gunicorn", "config.wsgi:application",
              "--bind", "0.0.0.0:8000",
              "--workers", "3",
              "--threads", "2",
              "--timeout", "120",
              "--access-logfile", "-",
              "--error-logfile", "-"]
    ports: []                      # el puerto lo publica solo Nginx

  celery:
    volumes:
      - ./media:/app/media
```

> **Workers:** regla práctica `(2 × núcleos) + 1`. Con 2 vCPU → 3–5 workers.
> **Importante:** el `entrypoint.sh` solo corre migraciones/collectstatic cuando detecta `runserver` (líneas 64–66). Con Gunicorn, esas tareas se ejecutan **manualmente** en la Fase 7 y 8 (o se añade el comando gunicorn a la condición del entrypoint).

### 2.2 — Arranque siempre con ambos archivos

```bash
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d --build
```

### ✅ Criterio de salida
- `docker compose ... config` muestra `web` con `command: gunicorn ...`.
- `db` y `redis` sin `ports` publicados.
- `web` sin bind-mount de código.

---

## FASE 3 — Base de datos y persistencia

**Objetivo:** Postgres seguro, con password fuerte y volumen persistente. Resuelve #4.

### Pasos

1. **Password de BD fuerte** (no el default `sintel`):
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(24))"
   ```
   En `.env`:
   ```ini
   DATABASE_NAME=sintel_prod
   DATABASE_USER=sintel_prod
   DATABASE_PASSWORD=<password fuerte>
   DATABASE_HOST=db
   DATABASE_PORT=5432
   ```

2. **Volumen persistente** — ya configurado en `docker-compose.yaml:100` (`postgres_data`). Confirmar que el volumen no se borra: **nunca usar `docker compose down -v` en producción** (la `-v` borra los volúmenes → pérdida total de datos). El `make down` actual incluye `-v` (`Makefile:7`) — **no usar `make down` en prod**.

3. **Acceso restringido** — con `ports: []` (Fase 2.1), Postgres solo es accesible dentro de la red Docker. Para administración usar:
   ```bash
   docker compose exec db psql -U sintel_prod -d sintel_prod
   ```

### ✅ Criterio de salida
- `DATABASE_PASSWORD` ≠ `sintel`.
- Postgres no responde desde fuera del host (`nc -zv <ip-publica> 5432` debe fallar).
- Volumen `crm_sintel_postgres_data` existe (`docker volume ls`).

---

## FASE 4 — SSL/TLS y dominio

**Objetivo:** Certificado válido para el navegador. Resuelve #6.

El setup actual (`nginx/docker-entrypoint.sh`) genera un cert **autofirmado** `*.sintel.net.co`, válido para **red local interna** (los clientes instalan el `.crt` manualmente). Para **publicar a internet** esto NO sirve: los navegadores mostrarán advertencia de seguridad.

### Escenario A — Despliegue en red local / intranet (cert autofirmado)
- No requiere cambios. El cert se genera solo al levantar `nginx` y persiste en el volumen `nginx_certs`.
- Distribuir `http://<ip>/sintel.crt` a los clientes para que lo instalen como CA de confianza.

### Escenario B — Despliegue público en internet (Let's Encrypt) ✅ recomendado para "publicar"

Un wildcard `*.sintel.net.co` **requiere validación DNS-01** (no HTTP-01). Pasos:

1. Instalar `certbot` con plugin DNS de tu proveedor (Cloudflare, Route53, etc.):
   ```bash
   certbot certonly --dns-cloudflare \
     --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini \
     -d sintel.net.co -d '*.sintel.net.co'
   ```
2. Montar los certs reales en Nginx, reemplazando el bloque del `docker-entrypoint.sh`:
   ```
   ssl_certificate     /etc/letsencrypt/live/sintel.net.co/fullchain.pem;
   ssl_certificate_key /etc/letsencrypt/live/sintel.net.co/privkey.pem;
   ```
3. Programar la renovación automática (cron, cada 60 días):
   ```bash
   0 3 * * * certbot renew --quiet && docker compose exec nginx nginx -s reload
   ```

### Endurecimiento Nginx (ambos escenarios)
El `nginx.conf` ya tiene: redirección 80→443, HSTS implícito vía Django, `X-Content-Type-Options`, gzip, `client_max_body_size 50M`. Verificar que `client_max_body_size` (50M) sea ≥ `DATA_UPLOAD_MAX_MEMORY_SIZE` (20M, `settings.py:554`). ✅ OK.

### ✅ Criterio de salida
- `https://sintel.net.co` carga sin advertencia (Escenario B) o con cert instalado (Escenario A).
- `curl -I http://sintel.net.co` devuelve `301` → `https://`.

---

## FASE 5 — Variables de entorno de producción (`.env`)

**Objetivo:** `.env` completo y correcto. Contrato consolidado.

```ini
# ── Núcleo Django ───────────────────────────────────────────────
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<token_urlsafe(50)>
JWT_SECRET_KEY=<base64(token_bytes(32))>
TIME_ZONE=America/Bogota
SITE_PROTOCOL=https

# ── Dominio y hosts ─────────────────────────────────────────────
TENANT_DOMAIN_BASE=sintel.net.co
ALLOWED_HOSTS=sintel.net.co,.sintel.net.co
CSRF_TRUSTED_ORIGINS=https://sintel.net.co,https://.sintel.net.co

# ── Base de datos ───────────────────────────────────────────────
DATABASE_NAME=sintel_prod
DATABASE_USER=sintel_prod
DATABASE_PASSWORD=<password fuerte>
DATABASE_HOST=db
DATABASE_PORT=5432

# ── Redis / Celery ──────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ── Email SMTP ──────────────────────────────────────────────────
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=<correo>
EMAIL_HOST_PASSWORD=<app password>
DEFAULT_FROM_EMAIL=<correo>

# ── Activación de tenants ───────────────────────────────────────
ACTIVATION_BASE_URL=https://sintel.net.co
ALLOW_RESET_ACTIVATION=False
OWNER_ACTIVATION_TOKEN_TTL_MINUTES=120

# ── Integraciones (opcional) ────────────────────────────────────
DIAN_AMBIENTE=produccion
DIAN_API_KEY=<si aplica>
```

> **Revisar:** el `.env` actual tiene `GOGLE_API_GEMINY` (typo) — si no se usa, eliminar; si se usa, corregir el nombre en código y `.env`.

### ✅ Criterio de salida
- Todas las variables presentes y sin valores de desarrollo.
- `EMAIL_BACKEND` apunta a SMTP (no console).

---

## FASE 6 — Build de imágenes y arranque

**Objetivo:** Construir y levantar el stack productivo.

```bash
cd /opt/crm_sintel

# 1. Build de imágenes (web + nginx)
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml build

# 2. Levantar BD y Redis primero (healthchecks)
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d db redis

# 3. Esperar a que estén "healthy"
docker compose ps        # STATUS debe decir (healthy)

# 4. Levantar web, celery, nginx
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d
```

### ✅ Criterio de salida
- `docker compose ps` muestra `db`, `redis`, `web`, `celery`, `nginx` en estado `Up`/`healthy`.

---

## FASE 7 — Migraciones e inicialización multi-tenant

**Objetivo:** Esquemas `public` y de tenants migrados, tenant público y dominios garantizados.

> Con Gunicorn, el `entrypoint.sh` **no** corre migraciones automáticamente (solo lo hace con `runserver`). Ejecutarlas manualmente:

```bash
# 1. Migraciones del esquema público (shared)
docker compose exec web python manage.py migrate_schemas --shared

# 2. Migraciones de todos los tenants
docker compose exec web python manage.py migrate_schemas --tenant

# 3. Verificar que no quedan migraciones pendientes
docker compose exec web python manage.py check_migrations

# 4. Crear/garantizar el tenant público y sus dominios
docker compose exec web python manage.py create_public_tenant --domain sintel.net.co
docker compose exec web python manage.py ensure_public_domains --primary sintel.net.co

# 5. Poblar el catálogo DIAN (impuestos) — requerido para facturación
docker compose exec web python manage.py poblar_catalogo_dian

# 6. Crear superusuario para la consola admin
docker compose exec web python manage.py createsuperuser
```

### ✅ Criterio de salida
- `check_migrations` → sin pendientes.
- El tenant público (`sintel.net.co`) resuelve y existe en la tabla `tenants_domain`.
- Superusuario creado.

---

## FASE 8 — Archivos estáticos

**Objetivo:** Staticfiles recolectados y servidos por Nginx + WhiteNoise.

```bash
docker compose exec web python manage.py collectstatic --noinput --clear
```
- `STATIC_ROOT` = `staticfiles/` (`settings.py:324`), montado en Nginx como `/static/` (`nginx.conf:50`).
- WhiteNoise usa `CompressedManifestStaticFilesStorage` (`settings.py:343`) → archivos hasheados y comprimidos.

### ✅ Criterio de salida
- `curl -I https://sintel.net.co/static/<algún-archivo>.css` → `200` con `Cache-Control: public`.

---

## FASE 9 — Celery, Redis y tareas asíncronas

**Objetivo:** Worker procesando colas `high_priority` y `default`.

### Pasos

1. **Verificar el worker:**
   ```bash
   docker compose logs --tail=50 celery
   # Debe mostrar: "celery@... ready" y las colas [high_priority, default]
   ```

2. **Colas configuradas** (`settings.py:840`): onboarding de tenants, emails de activación y ingesta de correo van a `high_priority`; el resto a `default`. ✅

3. **(Recomendado) Endurecer el worker** — actualmente corre como root (`C_FORCE_ROOT=1`, `docker-compose.yaml:94`). Para producción, considerar un usuario no-root en el Dockerfile, o aceptar el riesgo si el contenedor está aislado.

4. **(Opcional) Celery Beat** — si se requieren tareas programadas (ej. ingesta periódica de correo, backups), añadir un servicio `celery-beat`:
   ```yaml
   celery-beat:
     <<: *app-base
     command: ["celery", "-A", "config", "beat", "-l", "info"]
   ```

### ✅ Criterio de salida
- `docker compose logs celery` muestra `ready` y las dos colas.
- Una tarea de prueba (ej. crear empresa de prueba que dispare onboarding) se procesa.

---

## FASE 10 — Verificación post-deploy (smoke tests)

**Objetivo:** Confirmar que el sistema responde de extremo a extremo.

### Pasos

1. **Health check:**
   ```bash
   curl -s https://sintel.net.co/health
   # Esperado: {"status":"ok","database":"ok","version":"1.0"}
   ```

2. **Redirección HTTP→HTTPS:**
   ```bash
   curl -I http://sintel.net.co        # 301 → https
   ```

3. **Consola admin pública:**
   - Navegar a `https://sintel.net.co/console/` → login con el superusuario.

4. **Crear un tenant de prueba y verificar subdominio:**
   ```bash
   docker compose exec web python manage.py crear_empresa "Demo SA" "demo.sintel.net.co" "admin@demo.com"
   ```
   - Navegar a `https://demo.sintel.net.co/` → debe cargar la landing del tenant.
   - Activar y entrar al dashboard.

5. **API JWT:**
   ```bash
   curl -X POST https://demo.sintel.net.co/api/token/ \
     -H "Content-Type: application/json" \
     -d '{"username":"admin@demo.com","password":"..."}'
   # Debe devolver access + refresh tokens
   ```

6. **Aislamiento multi-tenant (crítico):** crear datos en `demo.sintel.net.co` y confirmar que NO son visibles desde otro tenant. Este es el control de seguridad más importante del SaaS.

7. **Suite de smoke del proyecto:**
   ```bash
   docker compose exec web make smoke      # o: make health BASE_URL=https://sintel.net.co
   ```

### ✅ Criterio de salida
- `/health` → `200 ok`.
- Login en consola, creación de tenant, acceso a subdominio y API JWT funcionan.
- Aislamiento entre tenants verificado.

---

## FASE 11 — Backups, logs y mantenimiento

**Objetivo:** Recuperabilidad y observabilidad.

### 11.1 — Backups de base de datos

El proyecto trae comandos de backup (`Makefile:53-64`):
```bash
# Backup de un tenant
docker compose exec web python manage.py backup_tenant <schema_name>

# Backup de todos los tenants
docker compose exec web python manage.py backup_all_tenants
```
Programar en cron del host (diario, 2 AM):
```bash
0 2 * * * cd /opt/crm_sintel && docker compose exec -T web python manage.py backup_all_tenants
```
- Retención: `BACKUP_RETENTION_DAYS=30` (`settings.py:882`).
- **Backup completo de Postgres** (recomendado además del por-tenant):
  ```bash
  docker compose exec -T db pg_dumpall -U sintel_prod > /opt/backups/full_$(date +%F).sql
  ```
- **Copiar los backups fuera del servidor** (S3, otro host). Un backup en el mismo disco no es backup.

### 11.2 — Logs

- Logging a `console` (stdout) → capturado por Docker (`settings.py:904`).
- Configurar rotación de logs de Docker en `/etc/docker/daemon.json`:
  ```json
  { "log-driver": "json-file", "log-opts": { "max-size": "50m", "max-file": "5" } }
  ```

### 11.3 — Actualizaciones (deploy de nuevas versiones)

```bash
cd /opt/crm_sintel
git pull origin main
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml build web celery
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d web celery
docker compose exec web python manage.py migrate_schemas --shared
docker compose exec web python manage.py migrate_schemas --tenant
docker compose exec web python manage.py collectstatic --noinput
```

### ✅ Criterio de salida
- Backup automatizado en cron y verificado (restaurar un dump en entorno de staging).
- Rotación de logs activa.

---

## FASE 12 — Checklist final de seguridad (go / no-go)

Marcar **todo** antes de anunciar el lanzamiento:

```
SEGURIDAD
[ ] DJANGO_DEBUG=False
[ ] SECRET_KEY y JWT_SECRET_KEY nuevos, fuertes, solo en .env (no en git)
[ ] debug_headers_view eliminado/gated
[ ] manage.py check --deploy sin warnings críticos
[ ] ALLOWED_HOSTS sin '*' ni localhost
[ ] CSRF_COOKIE_SECURE / SESSION_COOKIE_SECURE = True (vía bloque not DEBUG)
[ ] HSTS activo
[ ] Postgres y Redis NO expuestos a internet
[ ] DATABASE_PASSWORD fuerte (≠ sintel)
[ ] Certificado SSL válido (Let's Encrypt para internet público)

INFRAESTRUCTURA
[ ] web corre con Gunicorn (no runserver)
[ ] Sin bind-mount de código en producción
[ ] Imágenes construidas desde main
[ ] Volumen postgres_data persistente y respaldado
[ ] NUNCA ejecutar `docker compose down -v` / `make down` en prod

FUNCIONAL
[ ] Migraciones shared + tenant aplicadas, sin pendientes
[ ] Catálogo DIAN poblado
[ ] Tenant público y dominios garantizados
[ ] /health responde 200
[ ] Crear tenant + subdominio + login + API JWT OK
[ ] Aislamiento entre tenants verificado
[ ] Email SMTP envía (activación de owners)
[ ] Celery worker procesando colas

OPERACIÓN
[ ] Backups automatizados y copiados fuera del host
[ ] Rotación de logs configurada
[ ] Renovación de cert automatizada (si Let's Encrypt)
[ ] Procedimiento de actualización documentado y probado
```

---

## Apéndice A — Comandos de referencia rápida

```bash
# Levantar producción
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d --build

# Estado
docker compose ps
docker compose logs -f web

# Migraciones
docker compose exec web python manage.py migrate_schemas --shared
docker compose exec web python manage.py migrate_schemas --tenant

# Validación de despliegue
docker compose exec web python manage.py check --deploy

# Health
curl -s https://sintel.net.co/health

# Backup total
docker compose exec -T db pg_dumpall -U sintel_prod > backup_$(date +%F).sql
```

## Apéndice B — Archivos clave de la auditoría

| Archivo | Rol |
|---------|-----|
| `config/settings.py` | Configuración central (DEBUG, ALLOWED_HOSTS, JWT, CORS, CSRF, Celery) |
| `docker-compose.yaml` | Stack de desarrollo (base) |
| `docker-compose.prod.yaml` | **(crear)** Override de producción (Fase 2.1) |
| `Dockerfile` | Imagen de la app (Python 3.12-slim) |
| `entrypoint.sh` | Espera BD/Redis + migraciones en modo runserver |
| `nginx/nginx.conf` | Reverse proxy, TLS, static/media, gzip |
| `nginx/docker-entrypoint.sh` | Generación de cert autofirmado |
| `.env` | Secretos y configuración de entorno (NO versionar) |
| `Makefile` | Atajos de operación (migrate, backup, test, audit) |

---

*Documento generado por auditoría de alistamiento. Resolver Fases 1–4 (bloqueadores) es obligatorio antes de exponer el servicio a internet.*
