# Configuración de Producción con HTTPS (sintel.com)

## Objetivo

Servir el dominio público en `https://sintel.com` y los tenants privados en `https://cliente.sintel.com`, con ruteo por hostname, separación de URLConf público vs. tenant, y verificación end-to-end.

## Base Técnica

- **django-tenants**: Resuelve el tenant según el host (dominio) y activa el URLConf correspondiente (público o tenant) antes del despacho de URLs.
- **Django**: Permite cambiar el URLConf por request desde middleware mediante `request.urlconf`.

## 1. DNS y Certificados

### Zona DNS del dominio sintel.com

```
# Registro A/AAAA para el dominio principal
sintel.com.          A      <IP_PUBLICA_DEL_REVERSE_PROXY>
sintel.com.          AAAA   <IPV6_PUBLICA_DEL_REVERSE_PROXY>

# CNAME comodín para subdominios (tenants)
*.sintel.com.        CNAME  sintel.com.
```

**Nota**: Alternativamente, puedes usar registros A/AAAA directos para cada subdominio si prefieres más control.

### Certificados TLS

- **Opción 1 (Recomendada)**: Certificado comodín `*.sintel.com` emitido con Let's Encrypt (ACME) usando DNS-01 o HTTP-01.
- **Opción 2**: Certificados individuales para cada subdominio (más complejo de mantener).

**Configuración ACME/Let's Encrypt**:
```bash
# Ejemplo con certbot
certbot certonly --dns-cloudflare \
  --dns-cloudflare-credentials ~/.secrets/cloudflare.ini \
  -d sintel.com -d '*.sintel.com'
```

El ruteo por hostname lo hará django-tenants en la capa de aplicación; el proxy sólo termina TLS y reenvía tráfico HTTP/HTTPS a Django.

## 2. Reverse Proxy (Nginx/Traefik)

### Ejemplo Nginx

El proxy reenvía todas las peticiones a tu app (Gunicorn o Uvicorn) y deja que Django resuelva a qué schema/URLConf ir por dominio.

```nginx
# Redirección HTTP -> HTTPS
server {
    listen 80;
    server_name sintel.com *.sintel.com;
    return 301 https://$host$request_uri;
}

# Servidor HTTPS
server {
    listen 443 ssl http2;
    server_name sintel.com *.sintel.com;

    # Certificados TLS
    ssl_certificate     /etc/ssl/sintel/fullchain.pem;
    ssl_certificate_key /etc/ssl/sintel/privkey.pem;

    # Configuración SSL moderna
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Seguridad / headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        # ⚠️ CRÍTICO: Mantener Host intacto
        # django-tenants usa el Host para resolver el tenant
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Reenvío a Django
        proxy_pass http://app:8000;
    }

    # Servir archivos estáticos directamente desde Nginx (opcional)
    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /app/media/;
        expires 7d;
        add_header Cache-Control "public";
    }
}
```

**⚠️ CRÍTICO**: Mantener `Host` intacto es indispensable. django-tenants usa el host para buscar el `Domain` del tenant y fijar el schema + URLConf.

## 3. Django Settings (Producción)

### 3.1 Variables de Entorno

Asegúrate de configurar estas variables en tu `.env` o sistema de gestión de secretos:

```bash
# Producción
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<SECRET_KEY_FUERTE>
DJANGO_ALLOWED_HOSTS=sintel.com,.sintel.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://sintel.com,https://*.sintel.com

# Base de datos
DATABASE_URL=postgresql://user:password@db:5432/sintel_db

# Otros...
```

### 3.2 Hosts, CSRF y URLConf

El archivo `config/settings.py` ya está configurado para manejar producción vs. desarrollo:

```python
# config/settings.py

# DEBUG se lee desde variable de entorno
DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'

# ALLOWED_HOSTS (configuración dinámica)
if DEBUG:
    # Desarrollo: permite localhost y dominios locales
    ALLOWED_HOSTS = [
        'localhost',
        '127.0.0.1',
        '.localhost',  # Para subdominios locales
    ]
else:
    # Producción: solo dominios reales
    ALLOWED_HOSTS = [
        'sintel.com',
        '.sintel.com',  # Incluye subdominios como cliente.sintel.com
    ]

# CSRF_TRUSTED_ORIGINS
if DEBUG:
    # Desarrollo: permite orígenes locales
    CSRF_TRUSTED_ORIGINS = [
        'http://localhost:8000',
        'http://127.0.0.1:8000',
        'http://*.localhost:8000',
    ]
else:
    # Producción: solo orígenes HTTPS reales
    CSRF_TRUSTED_ORIGINS = [
        'https://sintel.com',
        'https://*.sintel.com',
    ]

# Enrutamiento público vs. tenants
ROOT_URLCONF = 'config.urls_public'   # Dominio público sintel.com
TENANT_URLCONF = 'config.urls_tenant'  # Subdominios cliente.sintel.com
```

Django usa `ROOT_URLCONF` como base, pero si un middleware define `request.urlconf` (como hace django-tenants), se usará ese módulo en su lugar. Con `TenantMainMiddleware`, el hostname decide qué URLConf se activa (público vs. tenant).

### 3.3 Orden de Middlewares (CRÍTICO)

El orden de middlewares en `config/settings.py` ya está correctamente configurado:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Servir staticfiles
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'apps.public.core.middleware.ForceNoPortMiddleware',  # Normaliza HTTP_HOST
    'django_tenants.middleware.main.TenantMainMiddleware',  # ⚠️ CRÍTICO: Resuelve tenant por hostname
    'apps.public.tenants.middleware.TenantSecurityMiddleware',  # Bloquea tenants suspendidos
    'apps.public.core.middleware.CSRFTrustedOriginMiddleware',  # Solo en DEBUG
    'apps.public.core.middleware.HTTPSRedirectMiddleware',  # Solo en DEBUG
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.public.tenants.authz.require_tenant_membership',  # Valida membresía
    'apps.public.tenants.middleware_admin_guard.block_public_routes_on_tenants',  # Guard-rail
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

**⚠️ CRÍTICO**: `TenantMainMiddleware` debe ir muy arriba para capturar el host, cambiar schema y seleccionar URLConf antes de resolver rutas.

## 4. URLConf Separados (Público vs. Tenant)

### 4.1 `config/urls_public.py` (Solo sintel.com)

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),  # Admin global solo en público
    path('console/', include('apps.public.console.urls')),  # Consola solo en público
    path('api/public/v1/', include('apps.public.tenants.api.urls')),
    path('api/admin/v1/', include('apps.public.console.api.urls')),
    path('api/admin/v1/accounts/', include('apps.public.accounts.api.urls')),
    # Cualquier otra ruta pública (landing corporativa, docs, swagger público, etc.)
]
```

El Admin existe donde lo enganchas (`admin.site.urls`); por eso debe estar solo en el URLConf público.

### 4.2 `config/urls_tenant.py` (Clientes *.sintel.com)

```python
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('', include('apps.tenant.landing.urls')),  # "/" landing/login de cada tenant
    path('dashboard/', include('apps.tenant.dashboard.urls', namespace='tenant_dashboard')),
    path('api/v1/', include('config.api_urls')),  # APIs por-tenant
    # Evitar confusiones con el admin del público:
    path('admin/login/', RedirectView.as_view(url='/', permanent=False)),
]
```

**⚠️ IMPORTANTE**: No incluyas `console/` ni `api/public/` en `urls_tenant.py`. Esas rutas solo existen en el público. El middleware ya separa público vs. tenant por host.

## 5. Modelo de Dominios (django-tenants)

### Crear/Asegurar en esquema public

**Public tenant**:
```python
from apps.public.tenants.models import Client, Domain

# Crear tenant público si no existe
public_client, _ = Client.objects.get_or_create(
    schema_name='public',
    defaults={'nombre': 'Sintel Public', 'is_active': True}
)

# Crear dominio principal
Domain.objects.get_or_create(
    domain='sintel.com',
    defaults={'tenant': public_client, 'is_primary': True}
)
```

**Tenants privados** (por cada empresa):
```python
# Ejemplo: crear tenant "acme"
acme_client = Client.objects.create(
    schema_name='acme',
    nombre='Acme Corporation',
    is_active=True
)

Domain.objects.create(
    domain='acme.sintel.com',
    tenant=acme_client,
    is_primary=True
)
```

django-tenants resuelve el tenant por hostname (tabla `Domain` en public) y cambia el `search_path` a ese schema; a partir de ahí, todas las queries/URLConf se resuelven en el esquema del tenant.

## 6. Seguridad y Mejores Prácticas

### HSTS + TLS Forzado

Ya configurado en Nginx (ver sección 2).

### CORS/CSRF

- Solo orígenes esperados (`sintel.com` / `*.sintel.com`).
- Configurado en `CSRF_TRUSTED_ORIGINS` (ver sección 3.2).

### Admin

- Únicamente en el público; `is_staff=True` para acceso.
- Ya bloqueado en tenants mediante `block_public_routes_on_tenants` middleware.

### Guard-rails (Defensa en Profundidad)

Ya implementados:
- **404 a `/console/` y `/api/public/`** si el schema != public (middleware `block_public_routes_on_tenants`).
- **404 a `/admin/`** cuando schema != public (mismo middleware).

## 7. Verificación End-to-End (Checklist)

### Pre-despliegue

- [ ] DNS resuelto (A/AAAA + CNAME * → sintel.com)
- [ ] TLS activo (cert comodín o individuales)
- [ ] Proxy reenvía con `Host` intacto
- [ ] `ALLOWED_HOSTS` contiene `sintel.com` y `.sintel.com`
- [ ] `CSRF_TRUSTED_ORIGINS` contiene `https://sintel.com` y `https://*.sintel.com`
- [ ] `TenantMainMiddleware` está antes de resolver rutas
- [ ] `DEBUG=False` en producción
- [ ] `SECRET_KEY` fuerte y seguro

### Verificación Pública (https://sintel.com)

- [ ] `/admin/` abre login de admin
- [ ] `/console/` carga la consola
- [ ] `/api/public/v1/...` responde OK
- [ ] Archivos estáticos se sirven correctamente (`/static/`)

### Verificación Tenant (https://cliente.sintel.com)

- [ ] `/` muestra landing del tenant
- [ ] `/login/` autentica correctamente
- [ ] `/dashboard/` carga tras login
- [ ] `/api/v1/...` responde en el schema del tenant
- [ ] No existen `/console/` ni `/api/public/v1/...` bajo el dominio del tenant (404)

### Verificación de Seguridad

- [ ] Usuario sin membresía no puede acceder a rutas privadas del tenant (403)
- [ ] Admin no está disponible en dominios de tenant (404)
- [ ] Consola no está disponible en dominios de tenant (404)
- [ ] APIs públicas no están disponibles en dominios de tenant (404)

## 8. Troubleshooting Rápido

### ¿https://cliente.sintel.com/ carga vistas del público?

**Causa**: `TenantMainMiddleware` no está resolviendo correctamente el tenant.

**Solución**:
1. Verifica que `TenantMainMiddleware` esté antes de resolver rutas.
2. Confirma que `TENANT_URLCONF` esté definido en `settings.py`.
3. Verifica que existe `Domain(domain='cliente.sintel.com')` en el esquema public.
4. Revisa los logs de Django para ver qué tenant se está resolviendo.

### ¿Ves `/admin/` en un tenant?

**Causa**: El admin está enganchado en `urls_tenant.py` o el middleware no está bloqueando.

**Solución**:
1. Verifica que NO esté enganchado en `urls_tenant.py`.
2. Verifica que el middleware `block_public_routes_on_tenants` esté activo.
3. El admin aparece donde conectas `admin.site.urls`.

### ¿JS de la consola llama `/api/public/...` en un tenant?

**Causa**: La consola se está sirviendo en un dominio de tenant.

**Solución**:
1. La consola debe servirse solo en `sintel.com`.
2. No montarla en tenants o añade un guard en front que aborte si `host !== 'sintel.com'`.
3. Ya implementado: `checkHostname()` en `console.js`, `tenants_manager.js`, `users_manager.js`.

### ¿Error "DisallowedHost"?

**Causa**: El dominio no está en `ALLOWED_HOSTS`.

**Solución**:
1. Verifica que el dominio esté en `ALLOWED_HOSTS`.
2. En producción, asegúrate de incluir `sintel.com` y `.sintel.com`.

### ¿Error CSRF?

**Causa**: El origen no está en `CSRF_TRUSTED_ORIGINS`.

**Solución**:
1. Verifica que el origen esté en `CSRF_TRUSTED_ORIGINS`.
2. En producción, asegúrate de incluir `https://sintel.com` y `https://*.sintel.com`.

## 9. Por Qué Este Diseño es el Correcto

1. **django-tenants** implementa multitenancy por esquemas y enrutamiento por hostname: el middleware captura el host, selecciona el schema y puede mutar el URLConf por request. Así, dominio público y dominios de tenants publican rutas distintas sin bifurcar proyectos.

2. **Django** soporta cambio de URLConf por middleware (atributo `request.urlconf`), de ahí la separación limpia `ROOT_URLCONF` vs. `TENANT_URLCONF`.

3. **El Admin** solo se habilita al "enganchar sus URLs", por eso debe permanecer en el público.

4. **Defensa en profundidad**: Los guard-rails (middlewares) aseguran que rutas públicas no se expongan en tenants, incluso si hay errores de configuración.

## 10. Comandos Útiles

### Verificar configuración de dominios

```bash
docker compose exec web python manage.py shell
```

```python
from apps.public.tenants.models import Client, Domain

# Ver todos los dominios
for domain in Domain.objects.all():
    print(f"{domain.domain} -> {domain.tenant.schema_name} (primary: {domain.is_primary})")
```

### Crear tenant público si no existe

```bash
docker compose exec web python manage.py shell
```

```python
from apps.public.tenants.models import Client, Domain

public_client, created = Client.objects.get_or_create(
    schema_name='public',
    defaults={'nombre': 'Sintel Public', 'is_active': True}
)

if created:
    print("✅ Tenant público creado")
else:
    print("✅ Tenant público ya existe")

domain, created = Domain.objects.get_or_create(
    domain='sintel.com',
    defaults={'tenant': public_client, 'is_primary': True}
)

if created:
    print("✅ Dominio público creado")
else:
    print("✅ Dominio público ya existe")
```

### Verificar orden de middlewares

```bash
docker compose exec web python manage.py shell
```

```python
from django.conf import settings

for i, mw in enumerate(settings.MIDDLEWARE):
    print(f"{i+1}. {mw}")
```

## Referencias

- [django-tenants Documentation](https://django-tenants.readthedocs.io/)
- [Django URLConf Documentation](https://docs.djangoproject.com/en/5.2/topics/http/urls/)
- [Django Middleware Documentation](https://docs.djangoproject.com/en/5.2/topics/http/middleware/)
- [Nginx Reverse Proxy](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
