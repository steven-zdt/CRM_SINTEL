# 🚀 Script de Inicialización del Tenant Público

## 📋 Descripción

Este script (`setup_public_domain.py`) crea automáticamente el tenant público y asocia los dominios necesarios para el esquema público de SINTEL.

## ⚠️ Requisitos Previos

1. **Migraciones aplicadas**: Asegúrate de haber ejecutado las migraciones:
   ```bash
   docker exec crm_sintel-web-1 python manage.py migrate_schemas --shared
   docker exec crm_sintel-web-1 python manage.py migrate_schemas --tenant
   ```

2. **Base de datos inicializada**: El contenedor de PostgreSQL debe estar corriendo y saludable.

## 🎯 Uso

### Opción 1: Ejecutar directamente (Recomendado)

```bash
# Desde el contenedor web
docker exec -it crm_sintel-web-1 python scripts/setup_public_domain.py
```

### Opción 2: Usar Django shell

```bash
# Desde el contenedor web
docker exec -it crm_sintel-web-1 python manage.py shell < scripts/setup_public_domain.py
```

### Opción 3: Ejecutar desde el host (si tienes acceso a la BD)

```bash
# Desde el directorio raíz del proyecto
python scripts/setup_public_domain.py
```

## 📊 Qué hace el script

1. **Verifica/Crea el tenant público**:
   - Schema name: `public` (según `get_public_schema_name()`)
   - Nombre: "SINTEL Public"

2. **Crea/Verifica dominios**:
   - `sintel.com` (dominio principal, `is_primary=True`)
   - `localhost` (desarrollo)
   - `127.0.0.1` (desarrollo)
   - `0.0.0.0` (desarrollo)

3. **Establece dominio primario**:
   - Si no existe un dominio primario, establece `sintel.com` como primario.

## ✅ Verificación

Después de ejecutar el script, deberías ver:

```
✅ Tenant público 'public' creado exitosamente (ID: X)
✅ Dominio 'sintel.com' creado exitosamente (ID: Y, Primary: True)
✅ Dominio 'localhost' creado exitosamente (ID: Z, Primary: False)
...
```

## 🔍 Verificar manualmente

```bash
# Desde Django shell
docker exec -it crm_sintel-web-1 python manage.py shell

# En el shell:
from apps.public.tenants.models import Client, Domain
from django_tenants.utils import get_public_schema_name

public_schema = get_public_schema_name()
tenant = Client.objects.get(schema_name=public_schema)
domains = Domain.objects.filter(tenant=tenant)

print(f"Tenant: {tenant.schema_name} (ID: {tenant.id})")
for domain in domains:
    print(f"  - {domain.domain} (Primary: {domain.is_primary})")
```

## 🐛 Solución de Problemas

### Error: "No tenant for hostname"

**Causa**: El tenant público o el dominio no están creados.

**Solución**: Ejecuta el script de inicialización.

### Error: "Tenant already exists"

**Causa**: El tenant público ya existe (normal si ejecutas el script varias veces).

**Solución**: El script es idempotente y no causará problemas. Solo verifica y crea lo que falta.

### Error: "Domain already exists for another tenant"

**Causa**: Un dominio está asociado a otro tenant.

**Solución**: El script mostrará una advertencia. Revisa manualmente y actualiza si es necesario.

## 📝 Notas

- El script es **idempotente**: puedes ejecutarlo múltiples veces sin problemas.
- Solo crea lo que falta; no elimina ni modifica datos existentes.
- Los dominios de desarrollo (`localhost`, `127.0.0.1`, `0.0.0.0`) son útiles para desarrollo local.
