# Política Estricta de Subdominios - SINTEL

## 📋 Objetivo

Garantizar una arquitectura de dominios consistente y predecible:

1. **Tenant Público:** Siempre responde en `{TENANT_DOMAIN_BASE}` (ej: `sintel.com`)
2. **Tenants Privados:** Siempre usan subdominios: `{schema_name}.{TENANT_DOMAIN_BASE}` (ej: `home.sintel.com`)
3. **NO se permiten dominios arbitrarios o FQDN personalizados**

## ⚙️ Configuración

### 1. Variable de Entorno: `TENANT_DOMAIN_BASE`

**Ubicación:** `config/settings.py`

```python
# En PROD: 'sintel.com'
# En DEV: 'sintel.localhost' (o lo que dicte .env)
TENANT_DOMAIN_BASE = os.getenv('TENANT_DOMAIN_BASE', 'sintel.localhost' if DEBUG else 'sintel.com')
```

**Regla de Oro:**
- El tenant público siempre responde en `TENANT_DOMAIN_BASE`
- Los tenants privados siempre usan `{schema_name}.{TENANT_DOMAIN_BASE}`

### 2. ALLOWED_HOSTS

**Ubicación:** `config/settings.py`

```python
# Acepta cualquier subdominio del dominio base
ALLOWED_HOSTS = [
    f".{TENANT_DOMAIN_BASE}",  # .sintel.com (acepta cualquier subdominio)
    TENANT_DOMAIN_BASE,  # sintel.com (dominio base - tenant público)
    "localhost",
    "127.0.0.1",
]
```

## 🔧 Implementación

### 1. Creación de Tenants Privados

**Archivo:** `apps/services/onboarding/empresa_service.py`

La función `crear_tenant()` construye automáticamente el dominio como subdominio:

```python
# Input: schema_name = 'home'
# Output: dominio = 'home.sintel.com' (o 'home.sintel.localhost' en dev)
dominio_esperado = f"{schema_name}.{settings.TENANT_DOMAIN_BASE}"
```

**Validaciones:**
- ❌ Rechaza `schema_name` con puntos (no se permiten FQDN)
- ✅ Construye automáticamente el subdominio
- ✅ Verifica que el dominio no exista antes de crear

### 2. Tenant Público

**Comando:** `python manage.py ensure_public_domain`

Este comando garantiza que el tenant público tenga el dominio correcto:

```bash
# Verificar y corregir el dominio del tenant público
python manage.py ensure_public_domain

# Forzar actualización incluso si el dominio está asignado a otro tenant
python manage.py ensure_public_domain --force
```

**Lógica:**
1. Busca el tenant con `schema_name='public'`
2. Verifica que su dominio principal sea exactamente `TENANT_DOMAIN_BASE`
3. Si no coincide, actualiza o crea el dominio correcto
4. Marca el dominio correcto como `is_primary=True`

## ✅ Verificación

### Script de Verificación

**Archivo:** `scripts/verify_domains.py`

Ejecuta un "smoke test" completo:

```bash
python manage.py shell < scripts/verify_domains.py
# o
python scripts/verify_domains.py
```

**Verificaciones:**
1. ✅ Verifica que el tenant público tenga el dominio correcto
2. ✅ Simula la creación de un tenant y verifica que su dominio sea un subdominio

### Verificación Manual

```python
from django.conf import settings
from apps.public.tenants.models import Client, Domain

# Verificar tenant público
tenant = Client.objects.get(schema_name='public')
dominio_principal = Domain.objects.filter(tenant=tenant, is_primary=True).first()

print(f"TENANT_DOMAIN_BASE: {settings.TENANT_DOMAIN_BASE}")
print(f"Dominio principal: {dominio_principal.domain}")

# Deben coincidir
assert dominio_principal.domain == settings.TENANT_DOMAIN_BASE
```

## 🚀 Uso

### Crear un Tenant Privado

```python
from apps.services.onboarding.empresa_service import crear_tenant
from django.contrib.auth import get_user_model

User = get_user_model()
admin_user = User.objects.get(username='admin')

# Crear tenant 'home'
client, domain, login_url = crear_tenant(
    nombre='Mi Empresa',
    admin_user_id=admin_user.id,
    schema_name='home'  # Opcional, se genera desde 'nombre' si no se proporciona
)

# El dominio será automáticamente: 'home.sintel.com' (o 'home.sintel.localhost' en dev)
print(f"Dominio: {domain.domain}")  # 'home.sintel.com'
print(f"Login URL: {login_url}")  # 'http://home.sintel.com/'
```

### Garantizar Dominio del Tenant Público

```bash
# Verificar y corregir
python manage.py ensure_public_domain

# Si el dominio está asignado a otro tenant, forzar reasignación
python manage.py ensure_public_domain --force
```

## 📝 Ejemplos

### Desarrollo (DEBUG=True)

```python
TENANT_DOMAIN_BASE = 'sintel.localhost'

# Tenant público
dominio_publico = 'sintel.localhost'

# Tenant privado 'home'
dominio_home = 'home.sintel.localhost'
```

### Producción (DEBUG=False)

```python
TENANT_DOMAIN_BASE = 'sintel.com'

# Tenant público
dominio_publico = 'sintel.com'

# Tenant privado 'home'
dominio_home = 'home.sintel.com'
```

## ⚠️ Restricciones

1. **NO se permiten FQDN arbitrarios:**
   - ❌ `mi-empresa.com` (no es subdominio)
   - ❌ `empresa.local` (no es subdominio)
   - ✅ `empresa.sintel.com` (subdominio válido)

2. **NO se permiten puntos en `schema_name`:**
   - ❌ `schema_name='mi.empresa'` (rechazado)
   - ✅ `schema_name='mi-empresa'` (aceptado, genera `mi-empresa.sintel.com`)

3. **El tenant público NO puede ser un subdominio:**
   - ❌ `public.sintel.com` (incorrecto)
   - ✅ `sintel.com` (correcto)

## 🔍 Troubleshooting

### Error: "El dominio no coincide con el esperado"

**Causa:** El dominio del tenant público no es `TENANT_DOMAIN_BASE`.

**Solución:**
```bash
python manage.py ensure_public_domain
```

### Error: "El schema_name no puede contener puntos"

**Causa:** Intentaste crear un tenant con `schema_name='mi.empresa'`.

**Solución:** Usa guiones en lugar de puntos:
```python
schema_name='mi-empresa'  # Genera 'mi-empresa.sintel.com'
```

### Error: "El dominio ya está en uso"

**Causa:** El dominio ya existe en la base de datos.

**Solución:** Verifica si el tenant ya existe o usa otro `schema_name`.

## 📚 Referencias

- `config/settings.py`: Configuración de `TENANT_DOMAIN_BASE` y `ALLOWED_HOSTS`
- `apps/services/onboarding/empresa_service.py`: Lógica de creación de tenants
- `apps/public/tenants/management/commands/ensure_public_domain.py`: Comando de auditoría
- `scripts/verify_domains.py`: Script de verificación