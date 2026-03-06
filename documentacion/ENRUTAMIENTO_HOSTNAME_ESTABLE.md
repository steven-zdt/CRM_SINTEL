# 🛡️ Enrutamiento por Hostname Estable (TENANT_URLCONF)

## ✅ Estado: Configuración Optimizada y Verificada

El sistema garantiza que cada request se enrute correctamente según el hostname:
- `sintel.com` → `ROOT_URLCONF` (urls_public) - Consola pública
- `<schema>.sintel.com` → `TENANT_URLCONF` (urls_tenant) - URLs privadas del tenant

## 🔧 Configuración Crítica

### Orden de Middleware (v2.26)

El orden del middleware es **crítico** para el enrutamiento por hostname:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',  # ✅ CRÍTICO: Antes de normalización
    'apps.public.core.middleware.ForceNoPortMiddleware',  # ✅ Normaliza HTTP_HOST (elimina puerto)
    'django_tenants.middleware.main.TenantMainMiddleware',  # ✅ CRÍTICO: Resuelve tenant y selecciona URLConf
    'apps.public.tenants.middleware.TenantSecurityMiddleware',  # ✅ Bloquea tenants suspendidos
    # ... otros middlewares
]
```

### Flujo de Enrutamiento

1. **Request llega**: `http://home.sintel.com/activate/?token=...`
2. **SecurityMiddleware**: Headers de seguridad
3. **SessionMiddleware**: Inicializa sesión
4. **ForceNoPortMiddleware**: Normaliza `HTTP_HOST` (elimina puerto si existe)
   - `home.sintel.com:8000` → `home.sintel.com`
5. **TenantMainMiddleware**: ⚠️ **CRÍTICO**
   - Busca dominio en BD: `Domain.objects.filter(domain='home.sintel.com').first()`
   - Encuentra: `Domain(domain='home.sintel.com', tenant=Client(schema_name='home'))`
   - Activa schema: `connection.set_schema_to('home')`
   - Selecciona URLConf: `settings.URLConf = settings.TENANT_URLCONF` (urls_tenant)
6. **Resolución de URL**: Django resuelve `/activate/` en `TENANT_URLCONF`
   - `config/urls_tenant.py` → `apps.tenant.landing.urls` → `path('activate/', ...)`
7. **Vista ejecutada**: `ActivateOwnerView` en el contexto del tenant `home`

## 📋 URLConf Separados

### ROOT_URLCONF (Público)

**Archivo**: `config/urls_public.py`

**Se activa cuando**: `HTTP_HOST = 'sintel.com'` (o cualquier dominio del tenant público)

**Rutas disponibles**:
- `/` → `PublicIndexView`
- `/admin/` → Admin de Django
- `/console/` → Consola de administración pública
- `/console/tenants/` → Lista de tenants
- `/api/public/v1/` → APIs REST públicas
- `/api/admin/v1/` → APIs REST de administración

### TENANT_URLCONF (Privado)

**Archivo**: `config/urls_tenant.py`

**Se activa cuando**: `HTTP_HOST = '<schema>.sintel.com'` (cualquier tenant privado)

**Rutas disponibles**:
- `/` → `TenantLandingView` (landing page)
- `/login/` → `TenantLoginView` (login HTML)
- `/activate/` → `ActivateOwnerView` (activación con token) ⭐ v2.24
- `/logout/` → `LogoutView` (cierre de sesión)
- `/dashboard/` → Dashboard del tenant
- `/api/v1/` → APIs REST del tenant

## 🔍 Verificación

### Script de Prueba

```bash
# Verificar enrutamiento
docker compose exec web python scripts/test_hostname_routing.py
```

### Pruebas Manuales con curl

```bash
# Request a dominio público (ROOT_URLCONF)
curl -H 'Host: sintel.com' http://localhost:8000/console/tenants/

# Request a tenant privado (TENANT_URLCONF)
curl -H 'Host: home.sintel.com' http://localhost:8000/activate/?token=test123
```

### Verificación de Dominios

```bash
# Asegurar que sintel.com existe
docker compose exec web python manage.py ensure_public_domains

# Verificar dominio primario
docker compose exec web python scripts/verify_sintel_primary.py
```

## ⚠️ Puntos Críticos

### 1. Orden del Middleware

**CRÍTICO**: `TenantMainMiddleware` debe ir **inmediatamente después** de `ForceNoPortMiddleware`:

```python
# ✅ CORRECTO
'apps.public.core.middleware.ForceNoPortMiddleware',
'django_tenants.middleware.main.TenantMainMiddleware',  # Inmediatamente después

# ❌ INCORRECTO (causa problemas de enrutamiento)
'django_tenants.middleware.main.TenantMainMiddleware',
'apps.public.core.middleware.ForceNoPortMiddleware',  # Demasiado tarde
```

### 2. Normalización de HTTP_HOST

`ForceNoPortMiddleware` normaliza `HTTP_HOST` **antes** de que `TenantMainMiddleware` intente resolver el tenant:

- **Entrada**: `HTTP_HOST = "home.sintel.com:8000"`
- **Salida**: `HTTP_HOST = "home.sintel.com"`
- **Búsqueda en BD**: `Domain.objects.filter(domain='home.sintel.com')`

### 3. Selección de URLConf

`TenantMainMiddleware` establece `settings.URLConf` según el tenant resuelto:

- **Tenant público** (`sintel.com`): `settings.URLConf = settings.ROOT_URLCONF`
- **Tenant privado** (`home.sintel.com`): `settings.URLConf = settings.TENANT_URLCONF`

### 4. Dominios en Base de Datos

Los dominios en `Domain.domain` **NUNCA** deben tener puerto:

- ✅ **Correcto**: `home.sintel.com`
- ❌ **Incorrecto**: `home.sintel.com:8000`

## 🐛 Troubleshooting

### 404 en `/activate/` de tenant privado

**Síntoma**: `GET http://home.sintel.com/activate/?token=...` retorna 404

**Causas posibles**:
1. Dominio no existe en BD → Ejecutar `ensure_public_domains` o crear tenant
2. Middleware en orden incorrecto → Verificar `MIDDLEWARE` en `settings.py`
3. Ruta no incluida en `TENANT_URLCONF` → Verificar `config/urls_tenant.py`

**Solución**:
```bash
# 1. Verificar dominio
docker compose exec web python manage.py shell -c "from apps.public.tenants.models import Domain; print(Domain.objects.filter(domain='home.sintel.com').exists())"

# 2. Verificar enrutamiento
docker compose exec web python scripts/test_hostname_routing.py

# 3. Verificar middleware
docker compose exec web python -c "from django.conf import settings; print([i for i, m in enumerate(settings.MIDDLEWARE) if 'Tenant' in m])"
```

### 404 en `/console/tenants/` de dominio público

**Síntoma**: `GET http://sintel.com/console/tenants/` retorna 404

**Causas posibles**:
1. Dominio `sintel.com` no existe → Ejecutar `ensure_public_domains`
2. Acceso desde `localhost` en lugar de `sintel.com` → Añadir a hosts file

**Solución**:
```bash
# 1. Asegurar dominio público
docker compose exec web python manage.py ensure_public_domains

# 2. Verificar acceso
docker compose exec web python scripts/verify_sintel_primary.py

# 3. Añadir a hosts (Windows)
# C:\Windows\System32\drivers\etc\hosts
# 127.0.0.1 sintel.com
```

### Request se enruta al URLConf incorrecto

**Síntoma**: Request a `home.sintel.com/activate/` se resuelve en `ROOT_URLCONF` (404)

**Causas posibles**:
1. Dominio no existe en BD
2. `TenantMainMiddleware` no encuentra el dominio
3. Middleware en orden incorrecto

**Solución**:
```bash
# 1. Verificar dominio en BD
docker compose exec web python manage.py shell
>>> from apps.public.tenants.models import Domain
>>> Domain.objects.filter(domain='home.sintel.com').first()

# 2. Verificar orden de middleware
docker compose exec web python scripts/test_hostname_routing.py

# 3. Recrear dominio si es necesario
docker compose exec web python manage.py ensure_public_domains
```

## 📚 Referencias

- **Arquitectura**: `documentacion/arquitectura_general.md` (v2.26)
- **Configuración dominios**: `documentacion/CONFIGURACION_DOMINIOS_PUBLICOS.md`
- **Flujo de activación**: `documentacion/FLUJO_ACTIVACION_EMAIL.md`
- **Scripts de prueba**: 
  - `scripts/test_hostname_routing.py`
  - `scripts/test_tenant_routing.py`
  - `scripts/verify_sintel_primary.py`
