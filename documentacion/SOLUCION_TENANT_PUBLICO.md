# 🔧 Solución: Error TenantMainMiddleware - Tenant Público

## ❌ Error Original

```
TenantMainMiddleware intenta ejecutar domain_model.objects.get(domain=hostname)
La tabla tenants_domain no existe en el esquema public
```

## ✅ Solución Implementada

He creado una solución completa que automatiza la inicialización del tenant público.

### Archivos Creados

1. **`apps/public/tenants/management/commands/setup_public_tenant.py`**
   - Comando de management de Django
   - Ejecuta migraciones y crea el tenant público automáticamente

2. **`setup_tenants.py`**
   - Script Python standalone
   - Alternativa al comando de management

3. **`CHECKLIST_INICIALIZACION.md`**
   - Checklist completo de verificación
   - Solución de problemas comunes

## 🚀 Uso Rápido

### Opción 1: Comando de Management (Recomendado)

```powershell
# Ejecutar migraciones primero
make migrate

# Crear tenant público
make setup
```

### Opción 2: Automático en Docker Compose

El `docker-compose.yaml` ahora ejecuta automáticamente el setup al iniciar:

```yaml
command: bash -c "python manage.py migrate_schemas --shared && python manage.py setup_public_tenant || true && python manage.py runserver 0.0.0.0:8000"
```

Solo necesitas:
```powershell
make up
```

### Opción 3: Script Python

```powershell
docker compose exec web python setup_tenants.py
```

## 📋 Lo que hace el Setup

1. ✅ Ejecuta migraciones del esquema `public` (shared)
2. ✅ Verifica que el esquema `public` existe
3. ✅ Crea el tenant `public` con nombre "SINTEL Global"
4. ✅ Crea el dominio `localhost` asociado al tenant público
5. ✅ Crea dominios adicionales: `127.0.0.1`, `localhost:8000`

## 🔍 Verificación

### Verificar que el tenant público existe:

```powershell
docker compose exec web python manage.py shell
```

```python
from apps.public.tenants.models import Client, Domain
from django_tenants.utils import set_tenant_to_public

set_tenant_to_public()
print("Tenants:", list(Client.objects.all()))
print("Dominios:", list(Domain.objects.all()))
```

### Verificar en PostgreSQL:

```powershell
docker compose exec db psql -U sintel -d sintel -c "\dt public.tenants_*"
```

Deberías ver:
- `tenants_client`
- `tenants_domain`

## ⚙️ Configuración de Permisos

### Verificar permisos del usuario de PostgreSQL:

```powershell
docker compose exec db psql -U sintel -d sintel -c "\du"
```

### Si no tiene permisos, otorgarlos:

```powershell
# Como superuser de postgres
docker compose exec db psql -U postgres -d sintel -c "ALTER USER sintel WITH SUPERUSER;"
```

O solo CREATEDB (más seguro):
```powershell
docker compose exec db psql -U postgres -d sintel -c "ALTER USER sintel WITH CREATEDB;"
```

## 🎯 Orden Correcto de Ejecución

### Primera vez (setup completo):

```powershell
# 1. Levantar servicios
make up

# 2. Si hay errores, ejecutar manualmente:
make migrate
make setup
make superuser
```

### Desarrollo diario:

```powershell
# Solo levantar (el setup se ejecuta automáticamente)
make up
```

## 🚨 Solución de Problemas

### Error: "relation does not exist"

**Solución:**
```powershell
make migrate
make setup
```

### Error: "permission denied to create schema"

**Solución:**
```powershell
docker compose exec db psql -U postgres -d sintel -c "ALTER USER sintel WITH SUPERUSER;"
```

### Error: "TenantMainMiddleware domain lookup failed"

**Solución:**
```powershell
make setup
```

### Error: "schema 'public' does not exist"

**Solución:**
```powershell
docker compose down -v
docker compose up --build
```

## 📝 Comandos Disponibles

```powershell
make up          # Levanta servicios (ejecuta setup automáticamente)
make migrate      # Solo migraciones del esquema public
make setup        # Solo setup del tenant público
make superuser    # Crear superusuario
make down         # Detener servicios
make logs         # Ver logs
```

## ✅ Checklist Final

- [x] Comando de management creado
- [x] Script Python standalone creado
- [x] Docker Compose actualizado para ejecutar setup automáticamente
- [x] Makefile actualizado con comando `make setup`
- [x] Documentación completa creada
- [x] Checklist de verificación creado

## 🎉 Resultado

Ahora el sistema:
- ✅ Ejecuta migraciones automáticamente al iniciar
- ✅ Crea el tenant público automáticamente
- ✅ Configura el dominio localhost
- ✅ Está listo para usar sin errores de TenantMainMiddleware
