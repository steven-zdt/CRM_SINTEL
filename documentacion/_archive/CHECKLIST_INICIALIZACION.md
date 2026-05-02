# ✅ Checklist de Inicialización - SINTEL Multi-tenant

## 📋 Estado Actual del Proyecto

### [ ] 1. Migraciones Creadas

**Verificar que las migraciones existan para las apps en SHARED_APPS:**

```powershell
# Crear migraciones para tenants
docker compose exec web python manage.py makemigrations tenants

# Verificar que se crearon
docker compose exec web python manage.py showmigrations tenants
```

**Apps que necesitan migraciones:**
- [ ] `apps.public.tenants` - ✅ Ya tiene estructura
- [ ] `apps.public.accounts` - Verificar si tiene modelos
- [ ] `apps.public.impuestos` - Verificar si tiene modelos

### [ ] 2. Permisos de Base de Datos

**El usuario de PostgreSQL debe tener permisos SUPERUSER o CREATEDB:**

```powershell
# Verificar permisos del usuario
docker compose exec db psql -U sintel -d sintel -c "\du"

# Si no tiene permisos, otorgarlos (como superuser de postgres)
docker compose exec db psql -U postgres -d sintel -c "ALTER USER sintel WITH SUPERUSER;"
# O solo CREATEDB:
docker compose exec db psql -U postgres -d sintel -c "ALTER USER sintel WITH CREATEDB;"
```

**Verificar en docker-compose.yaml:**
- El usuario debe tener permisos para crear esquemas
- Por defecto, PostgreSQL 16 requiere permisos especiales

### [ ] 3. Modelo Domain Correcto

**Verificar que el modelo Domain coincida con lo que busca el middleware:**

```python
# En apps/public/tenants/models.py
class Domain(DomainMixin):
    pass
```

**Verificar en settings.py:**
```python
TENANT_DOMAIN_MODEL = "tenants.Domain"  # ✅ Correcto
```

El middleware busca `tenants_domain` (app_label `tenants` + modelo `Domain`).

### [ ] 4. Ejecutar Setup Inicial

**Opción A: Usar el comando de management (Recomendado)**

```powershell
# Ejecutar migraciones primero
make migrate

# Ejecutar setup del tenant público
make setup
```

**Opción B: Usar el script Python**

```powershell
docker compose exec web python setup_tenants.py
```

**Opción C: Manualmente desde shell**

```powershell
docker compose exec web python manage.py shell
```

Luego en el shell:
```python
from apps.public.tenants.models import Client, Domain
from django_tenants.utils import set_tenant_to_public

set_tenant_to_public()

# Crear tenant público
tenant, created = Client.objects.get_or_create(
    schema_name='public',
    defaults={'nombre': 'SINTEL Global', 'on_trial': False}
)

# Crear dominio
domain, created = Domain.objects.get_or_create(
    domain='localhost',
    defaults={'tenant': tenant, 'is_primary': True}
)
```

## 🔍 Verificación Post-Setup

### Verificar que el tenant público existe:

```powershell
docker compose exec web python manage.py shell
```

```python
from apps.public.tenants.models import Client, Domain
from django_tenants.utils import set_tenant_to_public

set_tenant_to_public()
print("Tenants:", Client.objects.all())
print("Dominios:", Domain.objects.all())
```

### Verificar esquemas en PostgreSQL:

```powershell
docker compose exec db psql -U sintel -d sintel -c "\dn"
```

Deberías ver:
- `public` (esquema compartido)
- Posiblemente otros esquemas si creaste tenants adicionales

### Verificar tablas en esquema public:

```powershell
docker compose exec db psql -U sintel -d sintel -c "\dt public.*"
```

Deberías ver:
- `tenants_client`
- `tenants_domain`
- Otras tablas de Django contrib

## 🚨 Solución de Problemas

### Error: "relation does not exist"

**Causa:** Las migraciones no se han ejecutado.

**Solución:**
```powershell
make migrate
make setup
```

### Error: "permission denied to create schema"

**Causa:** El usuario de PostgreSQL no tiene permisos.

**Solución:**
```powershell
docker compose exec db psql -U postgres -d sintel -c "ALTER USER sintel WITH SUPERUSER;"
```

### Error: "TenantMainMiddleware domain lookup failed"

**Causa:** No existe el tenant público o el dominio localhost.

**Solución:**
```powershell
make setup
```

### Error: "schema 'public' does not exist"

**Causa:** Las migraciones no se ejecutaron correctamente.

**Solución:**
```powershell
docker compose down -v
docker compose up --build
make migrate
make setup
```

## 📝 Orden Correcto de Ejecución

1. **Primera vez (setup completo):**
   ```powershell
   # 1. Levantar servicios
   make up
   
   # 2. Crear migraciones (si hay cambios en modelos)
   docker compose exec web python manage.py makemigrations
   
   # 3. Ejecutar migraciones
   make migrate
   
   # 4. Setup del tenant público
   make setup
   
   # 5. Crear superusuario
   make superuser
   ```

2. **Desarrollo diario:**
   ```powershell
   # Solo levantar servicios (el setup se ejecuta automáticamente)
   make up
   ```

3. **Después de cambios en modelos:**
   ```powershell
   # Crear migraciones
   docker compose exec web python manage.py makemigrations
   
   # Aplicar migraciones
   make migrate
   ```

## ✅ Checklist Final

- [ ] Migraciones creadas para todas las apps en SHARED_APPS
- [ ] Usuario de PostgreSQL tiene permisos SUPERUSER o CREATEDB
- [ ] Modelo Domain correctamente configurado
- [ ] Migraciones del esquema public ejecutadas
- [ ] Tenant público creado (schema_name='public')
- [ ] Dominio 'localhost' creado y asociado al tenant público
- [ ] Servidor corriendo sin errores
- [ ] Admin accesible en http://localhost:8000/admin/

## 🎯 Comandos Rápidos

```powershell
# Setup completo desde cero
make up          # Levanta servicios y ejecuta setup automáticamente
make migrate      # Solo migraciones
make setup        # Solo setup del tenant público
make superuser   # Crear superusuario
```
