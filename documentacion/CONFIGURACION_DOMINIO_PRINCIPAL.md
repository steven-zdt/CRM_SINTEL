# 🌐 Configuración del Dominio Principal: sintel.com

## ✅ Estado: Configurado como Dominio Principal y Definitivo

El dominio `sintel.com` está establecido como **dominio principal y definitivo** para el tenant público.

## 📋 Configuración Actual

### Base de Datos

- **Dominio principal**: `sintel.com`
- **Tenant**: `SINTEL Global` (schema: `public`)
- **Estado**: `is_primary=True`
- **Otros dominios**: `localhost`, `127.0.0.1` (no primarios)

### Settings

- **TENANT_DOMAIN_BASE**: `sintel.com` (definitivo)
- **ALLOWED_HOSTS**: Incluye `sintel.com` y `.sintel.com`
- **ROOT_URLCONF**: `config.urls_public` (se activa con sintel.com)

## 🔧 Configuración Aplicada

### 1. Dominio en Base de Datos

El dominio `sintel.com` está registrado como primario:

```python
Domain(domain='sintel.com', tenant=public, is_primary=True)
```

### 2. Settings.py

```python
# Dominio principal definitivo (siempre sintel.com)
_default_tenant_domain_base = 'sintel.com'
TENANT_DOMAIN_BASE = os.getenv('TENANT_DOMAIN_BASE', _default_tenant_domain_base)
```

### 3. ALLOWED_HOSTS

```python
ALLOWED_HOSTS = [
    '.sintel.com',  # Acepta cualquier subdominio
    'sintel.com',   # Dominio principal
    # ... otros dominios para desarrollo
]
```

## 🌍 Acceso

### Dominio Público

- **URL principal**: `http://sintel.com/`
- **Admin**: `http://sintel.com/admin/`
- **Consola**: `http://sintel.com/console/tenants/`
- **APIs públicas**: `http://sintel.com/api/public/v1/`

### Tenants Privados

Los tenants privados usan subdominios automáticos:

- **Ejemplo**: `http://cliente.sintel.com/`
- **Login**: `http://cliente.sintel.com/login/`
- **Dashboard**: `http://cliente.sintel.com/dashboard/`
- **Activación**: `http://cliente.sintel.com/activate?token=...`

## 🔄 Flujo de Resolución

1. **Request llega**: `http://sintel.com/console/tenants/`
2. **ForceNoPortMiddleware**: Normaliza `HTTP_HOST` (elimina puerto)
3. **TenantMainMiddleware**: Busca dominio en BD → encuentra `sintel.com` → activa schema `public`
4. **ROOT_URLCONF**: Usa `config.urls_public`
5. **Routing**: Resuelve `/console/tenants/` → `TenantsListView`

## 🛠️ Mantenimiento

### Verificar Configuración

```bash
docker compose exec web python scripts/verify_public_domain_access.py
```

### Establecer como Principal (si es necesario)

```bash
docker compose exec web python scripts/set_sintel_as_primary_domain.py
```

### Ver Dominio Principal

```bash
docker compose exec web python manage.py shell
```

```python
from apps.public.tenants.models import Domain, Client
from django_tenants.utils import schema_context

with schema_context('public'):
    public = Client.objects.get(schema_name='public')
    primary = Domain.objects.filter(tenant=public, is_primary=True).first()
    print(f"Dominio principal: {primary.domain}")
```

## ⚠️ Notas Importantes

1. **Desarrollo Local**: 
   - Añadir `127.0.0.1 sintel.com` a `/etc/hosts` (Linux/Mac) o `C:\Windows\System32\drivers\etc\hosts` (Windows)
   - O usar variable de entorno: `TENANT_DOMAIN_BASE=localhost` (solo para pruebas)

2. **Producción**:
   - Configurar DNS para que `sintel.com` apunte al servidor
   - Configurar certificado SSL para HTTPS
   - Asegurar que `ALLOWED_HOSTS` incluya `sintel.com`

3. **Subdominios**:
   - Los tenants privados se crean automáticamente como subdominios
   - Ejemplo: tenant `acme` → `acme.sintel.com`
   - Requiere configuración DNS de wildcard: `*.sintel.com`

## 📚 Referencias

- **Arquitectura**: `documentacion/arquitectura_general.md` (v2.24)
- **Solución 404**: `documentacion/SOLUCION_404_CONSOLA.md`
- **Verificación**: `scripts/verify_public_domain_access.py`
- **Configuración**: `scripts/set_sintel_as_primary_domain.py`
