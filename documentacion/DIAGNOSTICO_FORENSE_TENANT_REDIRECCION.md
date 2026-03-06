# 🔍 Diagnóstico Forense: Redirección a /admin/login/

## ❌ Problema Reportado

Al acceder a `http://home.localhost:8000/`, el sistema redirige a `http://home.localhost:8000/admin/login/` en lugar de mostrar la landing page del tenant.

## 🔬 Análisis Forense

### 1. Flujo de Resolución de Tenants

Cuando Django recibe una petición a `http://home.localhost:8000/`:

1. **TenantMainMiddleware** (PRIMER middleware) intenta resolver el tenant:
   - Extrae el hostname: `home.localhost` (sin puerto)
   - Busca en la tabla `tenants_domain` un registro con `domain='home.localhost'`
   - Si encuentra el dominio:
     - Establece `connection.schema_name = <schema_del_tenant>`
     - Asigna `request.tenant = <objeto_tenant>`
     - Django usa `TENANT_URLCONF = 'config.urls_tenant'`
   - Si NO encuentra el dominio:
     - Mantiene `connection.schema_name = 'public'`
     - Django usa `ROOT_URLCONF = 'config.urls_public'`

2. **URLConf Resuelto**:
   - Si se resuelve el tenant → `config/urls_tenant.py` → `apps.tenant.landing.urls` → `TenantLandingView` ✅
   - Si NO se resuelve → `config/urls_public.py` → `PublicIndexView` → Redirige a `/admin/login/` ❌

### 2. Causa Raíz Identificada

**El dominio `home.localhost` NO está registrado en la base de datos**, por lo que:
- `TenantMainMiddleware` no puede resolver el tenant
- Django cae al esquema `public`
- Se usa `ROOT_URLCONF = 'config.urls_public'`
- `PublicIndexView` redirige a `/admin/login/`

### 3. Verificación de Configuración

#### 3.1. Configuración de Dominio Base

En `config/settings.py`:
```python
TENANT_DOMAIN_BASE = os.getenv('TENANT_DOMAIN_BASE', 'localhost' if DEBUG else 'sintel.com')
```

**Regla de construcción de dominios:**
- Dominio esperado para tenant `home`: `home.{TENANT_DOMAIN_BASE}`
- En desarrollo: `home.localhost`
- En producción: `home.sintel.com`

#### 3.2. Señal de Creación de Dominios

En `apps/public/tenants/signals.py`:
- Al crear un `Client`, se crea automáticamente un `Domain` con:
  - `domain = f"{schema_name}.{TENANT_DOMAIN_BASE}"`
  - `is_primary = True`
- En desarrollo, también se crea un dominio con puerto (no principal)

## ✅ Soluciones

### Solución 1: Verificar Dominios Registrados (Diagnóstico)

Ejecutar el script de diagnóstico dentro del contenedor Docker:

```bash
docker compose exec web python scripts/diagnostico_forense_tenant.py home.localhost
```

Este script mostrará:
- Todos los dominios registrados en la BD
- Si existe `home.localhost`
- Qué tenant se resuelve para ese hostname
- Qué URLConf se está usando

### Solución 2: Verificar Dominios Manualmente

```bash
docker compose exec web python manage.py shell
```

```python
from apps.public.tenants.models import Client, Domain
from django_tenants.utils import set_tenant_to_public

# Asegurar que estamos en el esquema público
set_tenant_to_public()

# Listar todos los dominios
domains = Domain.objects.all().select_related('tenant')
for d in domains:
    print(f"{d.domain} -> {d.tenant.schema_name} (primary: {d.is_primary})")

# Buscar específicamente home.localhost
home_domain = Domain.objects.filter(domain='home.localhost').first()
if home_domain:
    print(f"✅ Encontrado: {home_domain.domain} -> {home_domain.tenant.schema_name}")
else:
    print("❌ NO existe dominio 'home.localhost'")
```

### Solución 3: Crear/Corregir Dominio Manualmente

Si el dominio no existe, crearlo:

```python
from apps.public.tenants.models import Client, Domain
from django_tenants.utils import set_tenant_to_public

set_tenant_to_public()

# Buscar el tenant 'home'
try:
    client = Client.objects.get(schema_name='home')
    
    # Crear o actualizar el dominio
    domain, created = Domain.objects.get_or_create(
        domain='home.localhost',
        defaults={
            'tenant': client,
            'is_primary': True,
        }
    )
    
    if created:
        print(f"✅ Dominio creado: {domain.domain}")
    else:
        # Verificar que el tenant sea correcto
        if domain.tenant != client:
            domain.tenant = client
            domain.is_primary = True
            domain.save()
            print(f"✅ Dominio actualizado: {domain.domain}")
        else:
            print(f"ℹ️  Dominio ya existe: {domain.domain}")
            
except Client.DoesNotExist:
    print("❌ El tenant 'home' no existe. Debe crearse primero.")
```

### Solución 4: Verificar Creación Automática de Dominios

Si el tenant `home` existe pero no tiene dominio, verificar la señal:

```python
from apps.public.tenants.models import Client, Domain
from django_tenants.utils import set_tenant_to_public

set_tenant_to_public()

# Verificar tenant
client = Client.objects.get(schema_name='home')
print(f"Tenant: {client.nombre} ({client.schema_name})")

# Verificar dominios del tenant
domains = Domain.objects.filter(tenant=client)
print(f"Dominios registrados: {domains.count()}")
for d in domains:
    print(f"  - {d.domain} (primary: {d.is_primary})")

# Si no hay dominios, la señal no se ejecutó correctamente
if domains.count() == 0:
    print("⚠️  PROBLEMA: El tenant no tiene dominios. La señal no se ejecutó.")
    print("💡 SOLUCIÓN: Crear dominio manualmente (ver Solución 3)")
```

### Solución 5: Verificar Middleware y URLConf

Verificar que el middleware esté configurado correctamente:

```python
# En config/settings.py debe estar:
MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',  # ✅ PRIMERO
    # ... otros middlewares
]

ROOT_URLCONF = 'config.urls_public'  # ✅ Para esquema public
TENANT_URLCONF = 'config.urls_tenant'  # ✅ Para tenants privados
```

### Solución 6: Verificar Headers HTTP

Si hay un proxy reverso (nginx), verificar que esté pasando el header `Host` correctamente:

```nginx
# nginx.conf (si existe)
server {
    listen 80;
    server_name *.localhost;
    
    location / {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;  # ✅ CRÍTICO
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 🔧 Comandos de Diagnóstico Rápido

### Verificar todos los tenants y sus dominios:

```bash
docker compose exec web python manage.py shell -c "
from apps.public.tenants.models import Client, Domain
from django_tenants.utils import set_tenant_to_public
set_tenant_to_public()
print('Tenants y Dominios:')
for c in Client.objects.all():
    print(f'\n{c.nombre} ({c.schema_name}):')
    for d in Domain.objects.filter(tenant=c):
        print(f'  - {d.domain} (primary: {d.is_primary})')
"
```

### Verificar resolución de un hostname específico:

```bash
docker compose exec web python manage.py shell -c "
from django_tenants.utils import get_tenant_model, get_tenant_domain_model
from django_tenants.middleware.main import TenantMainMiddleware
from django.http import HttpRequest

Domain = get_tenant_domain_model()
domain = Domain.objects.filter(domain='home.localhost').first()
if domain:
    print(f'✅ Dominio encontrado: {domain.domain} -> {domain.tenant.schema_name}')
else:
    print('❌ Dominio NO encontrado')
"
```

## 📋 Checklist de Verificación

- [ ] El tenant `home` existe en la base de datos
- [ ] Existe un `Domain` con `domain='home.localhost'` y `is_primary=True`
- [ ] El `Domain` está asociado al tenant `home`
- [ ] `TenantMainMiddleware` está como PRIMER middleware en `settings.py`
- [ ] `TENANT_URLCONF = 'config.urls_tenant'` está configurado
- [ ] `ROOT_URLCONF = 'config.urls_public'` está configurado
- [ ] Si hay nginx, está pasando el header `Host` correctamente

## 🎯 Resultado Esperado

Después de aplicar las soluciones:

1. Al acceder a `http://home.localhost:8000/`:
   - `TenantMainMiddleware` resuelve el tenant `home`
   - Se usa `TENANT_URLCONF = 'config.urls_tenant'`
   - Se carga `apps.tenant.landing.urls`
   - Se ejecuta `TenantLandingView`
   - Se muestra la landing page del tenant ✅

2. Si el usuario está autenticado:
   - `TenantLandingView` redirige a `/dashboard/` ✅

3. Si el usuario es anónimo:
   - `TenantLandingView` renderiza `tenant/landing/index.html` ✅

## 🚨 Notas Importantes

1. **django-tenants usa SOLO el hostname sin puerto** para resolver el tenant:
   - `http://home.localhost:8000/` → busca dominio `home.localhost`
   - El puerto NO se usa en la resolución

2. **El dominio PRINCIPAL debe ser SIN puerto**:
   - ✅ Correcto: `home.localhost` (is_primary=True)
   - ⚠️  Opcional: `home.localhost:8000` (is_primary=False) - solo para desarrollo

3. **Si el dominio no se resuelve, siempre cae al esquema público**:
   - Esto es el comportamiento esperado de django-tenants
   - Por eso es crítico que los dominios estén correctamente registrados
