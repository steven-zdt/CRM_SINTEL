# 🗑️ Guía: Eliminar Tenant Completamente

## ⚠️ IMPORTANTE

Eliminar un tenant requiere eliminar múltiples componentes en el orden correcto:

1. **TenantMembership** (relaciones usuario-tenant)
2. **Domain** (dominios asociados)
3. **Client** (el tenant en sí)
4. **Esquema PostgreSQL** (si `auto_drop_schema=False`, debe eliminarse manualmente)

## 🔍 Verificar Estado Actual

### Opción 1: Comando de Management

```bash
python manage.py verificar_eliminacion_tenant home
```

### Opción 2: Django Shell

```bash
python manage.py shell
```

```python
exec(open('scripts/verificar_tenant_home.py').read())
```

## 🗑️ Eliminar Tenant Completamente

### Paso 1: Eliminar TenantMembership

```python
from apps.public.tenants.models import Client, Domain, TenantMembership

client = Client.objects.get(schema_name='home')
TenantMembership.objects.filter(client=client).delete()
```

### Paso 2: Eliminar Domain

```python
Domain.objects.filter(tenant=client).delete()
```

### Paso 3: Eliminar Client

```python
# Si auto_drop_schema=True, esto eliminará el esquema automáticamente
client.delete()
```

### Paso 4: Eliminar Esquema Manualmente (si es necesario)

Si `auto_drop_schema=False` en el modelo Client, el esquema puede quedar en PostgreSQL:

```python
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("DROP SCHEMA IF EXISTS home CASCADE;")
```

## ✅ Verificar Eliminación

```python
from django_tenants.utils import schema_exists
from apps.public.tenants.models import Client, Domain, TenantMembership

# Verificar Client
try:
    client = Client.objects.get(schema_name='home')
    print("❌ Client aún existe")
except Client.DoesNotExist:
    print("✅ Client eliminado")

# Verificar Domain
try:
    domain = Domain.objects.get(domain='home.sintel.com')
    print("❌ Domain aún existe")
except Domain.DoesNotExist:
    print("✅ Domain eliminado")

# Verificar TenantMembership
memberships = TenantMembership.objects.filter(client__schema_name='home')
if memberships.exists():
    print(f"❌ Existen {memberships.count()} membresías")
else:
    print("✅ No hay membresías")

# Verificar esquema
if schema_exists('home'):
    print("❌ Esquema aún existe")
else:
    print("✅ Esquema eliminado")
```

## 🚨 Script de Eliminación Completa

```python
from apps.public.tenants.models import Client, Domain, TenantMembership
from django.db import connection
from django_tenants.utils import schema_exists

SCHEMA_NAME = 'home'

try:
    client = Client.objects.get(schema_name=SCHEMA_NAME)
    
    # 1. Eliminar TenantMembership
    count_memberships = TenantMembership.objects.filter(client=client).count()
    TenantMembership.objects.filter(client=client).delete()
    print(f"✅ Eliminadas {count_memberships} TenantMembership")
    
    # 2. Eliminar Domain
    count_domains = Domain.objects.filter(tenant=client).count()
    Domain.objects.filter(tenant=client).delete()
    print(f"✅ Eliminados {count_domains} Domain")
    
    # 3. Eliminar Client
    client.delete()
    print(f"✅ Client '{SCHEMA_NAME}' eliminado")
    
    # 4. Eliminar esquema si existe
    if schema_exists(SCHEMA_NAME):
        with connection.cursor() as cursor:
            cursor.execute(f"DROP SCHEMA IF EXISTS {SCHEMA_NAME} CASCADE;")
        print(f"✅ Esquema '{SCHEMA_NAME}' eliminado")
    else:
        print(f"✅ Esquema '{SCHEMA_NAME}' ya no existe")
    
    print("\n🎉 Tenant eliminado completamente")
    
except Client.DoesNotExist:
    print(f"✅ El tenant '{SCHEMA_NAME}' ya no existe")
    
    # Verificar si quedó el esquema
    if schema_exists(SCHEMA_NAME):
        print(f"⚠️  El esquema '{SCHEMA_NAME}' aún existe, eliminándolo...")
        with connection.cursor() as cursor:
            cursor.execute(f"DROP SCHEMA IF EXISTS {SCHEMA_NAME} CASCADE;")
        print(f"✅ Esquema eliminado")
```

## 📋 Notas Técnicas

- **auto_drop_schema**: Si está en `True`, el esquema se elimina automáticamente al eliminar el Client
- **CASCADE**: Al eliminar el esquema con CASCADE, se eliminan todas las tablas y datos
- **TenantMembership**: Debe eliminarse antes del Client para evitar errores de integridad referencial
- **Domain**: Debe eliminarse antes del Client para evitar errores de integridad referencial