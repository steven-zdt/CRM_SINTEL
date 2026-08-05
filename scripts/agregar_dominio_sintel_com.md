# Configuración del Dominio sintel.net.co para Tenant Público

## ✅ Cambios Realizados

### 1. Comando `setup_public_tenant` Actualizado
**Archivo:** `apps/public/tenants/management/commands/setup_public_tenant.py`

- Ahora crea automáticamente el dominio `sintel.net.co` como dominio adicional del tenant público
- Normaliza dominios quitando el puerto (django-tenants no maneja puertos en el nombre del dominio)

### 2. Configuración de Django (`config/settings.py`)

#### ALLOWED_HOSTS
- ✅ Agregado `sintel.net.co` y `.sintel.net.co` tanto en desarrollo como producción
- ✅ Permite acceso desde `http://sintel.net.co:8000` (el puerto se maneja en la URL, no en el dominio)

#### CORS_ALLOWED_ORIGIN_REGEXES
- ✅ Agregado regex para `http://sintel.net.co(:\d+)?$` (con puerto opcional)
- ✅ Agregado regex para `http://.*\.sintel\.com(:\d+)?$` (subdominios con puerto opcional)

#### CSRF_TRUSTED_ORIGINS
- ✅ Agregado `http://sintel.net.co`
- ✅ Agregado `http://sintel.net.co:8000`
- ✅ Agregado `http://*.sintel.net.co` (cualquier subdominio)

## 🚀 Cómo Agregar el Dominio

### Opción 1: Usar el Comando de Management (Recomendado)

```bash
python manage.py setup_public_tenant --skip-migrations
```

Este comando:
- Verifica que el tenant público existe
- Crea el dominio `sintel.net.co` si no existe
- Actualiza el dominio si estaba asignado a otro tenant

### Opción 2: Usar Django Shell

```bash
python manage.py shell
```

```python
from apps.public.tenants.models import Client, Domain

# Obtener el tenant público
tenant = Client.objects.get(schema_name='public')

# Crear o actualizar el dominio sintel.net.co
domain, created = Domain.objects.get_or_create(
    domain='sintel.net.co',
    defaults={
        'tenant': tenant,
        'is_primary': False,
    }
)

if created:
    print(f"✅ Dominio 'sintel.net.co' creado")
else:
    if domain.tenant != tenant:
        domain.tenant = tenant
        domain.save()
        print(f"✅ Dominio 'sintel.net.co' actualizado")
    else:
        print(f"ℹ️  Dominio 'sintel.net.co' ya existe")

# Verificar
print("\n📋 Dominios del tenant público:")
for d in Domain.objects.filter(tenant=tenant):
    print(f"   - {d.domain} (primary: {d.is_primary})")
```

### Opción 3: Script Python

```bash
python manage.py shell < scripts/agregar_dominio_publico.py
```

## ⚠️ Nota Importante sobre Puertos

**django-tenants NO maneja puertos en el nombre del dominio.**

- El dominio en la base de datos debe ser: `sintel.net.co` (sin puerto)
- El puerto se especifica en la URL: `http://sintel.net.co:8000`
- Django y django-tenants manejan el puerto automáticamente desde el `HTTP_HOST` header

## 🔍 Verificación

Después de agregar el dominio, verifica que todo esté correcto:

```bash
python manage.py shell
```

```python
from apps.public.tenants.models import Client, Domain

tenant = Client.objects.get(schema_name='public')
domains = Domain.objects.filter(tenant=tenant)

print("Tenant:", tenant.nombre)
print("Dominios:")
for d in domains:
    print(f"  - {d.domain} (primary: {d.is_primary})")
```

Deberías ver `sintel.net.co` en la lista de dominios.

## 🌐 Acceso

Una vez configurado, puedes acceder al tenant público desde:

- `http://sintel.net.co:8000/` ✅
- `http://localhost:8000/` ✅
- `http://127.0.0.1:8000/` ✅
- `http://sintel.localhost:8000/` ✅ (si está configurado)

## 📝 Configuración del Servidor

Si estás usando un servidor web (nginx, Apache), asegúrate de:

1. **Configurar el DNS** para que `sintel.net.co` apunte a tu servidor
2. **Configurar el proxy** para que pase el `Host` header correctamente
3. **Configurar el puerto** en el servidor web (no en django-tenants)

### Ejemplo Nginx

```nginx
server {
    listen 8000;
    server_name sintel.net.co;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Ejemplo para Desarrollo Local

Si estás desarrollando localmente, puedes agregar a `/etc/hosts` (Linux/Mac) o `C:\Windows\System32\drivers\etc\hosts` (Windows):

```
127.0.0.1    sintel.net.co
```

Luego acceder desde: `http://sintel.net.co:8000/`