# Migraciones para Apps de Tenant: Gastos, Clientes y Proveedores

## Problema

Las tablas `tenant_gastos_gasto`, `tenant_clientes_cliente`, `tenant_proveedores_proveedor` no existen en los esquemas de tenant, causando errores `ProgrammingError: relation does not exist`.

## Solución

Aplicar las migraciones de estas apps en todos los esquemas de tenant.

## Pasos

### 1. Verificar que las migraciones existen

```bash
# Verificar que existen los archivos de migración
ls apps/tenant/gastos/migrations/
ls apps/tenant/clientes/migrations/
ls apps/tenant/proveedores/migrations/
```

Deberías ver:
- `apps/tenant/gastos/migrations/0001_initial.py`
- `apps/tenant/clientes/migrations/0001_initial.py`
- `apps/tenant/proveedores/migrations/0001_initial.py`

### 2. Aplicar migraciones en todos los esquemas de tenant

```bash
# Opción A: Usar el script automatizado
python scripts/migrate_all_schemas.py

# Opción B: Usar migrate_schemas directamente
python manage.py migrate_schemas --tenant --fake-initial
```

### 3. Verificar que las tablas se crearon

```bash
# Conectarse a la base de datos y verificar
psql -h db -U sintel -d sintel -c "\dt tenant_*_gasto"
psql -h db -U sintel -d sintel -c "\dt tenant_*_cliente"
psql -h db -U sintel -d sintel -c "\dt tenant_*_proveedor"
```

O desde Django shell:

```python
from django.db import connection
from django_tenants.utils import schema_context
from apps.public.tenants.models import Client

# Verificar en un tenant específico
tenant = Client.objects.first()
with schema_context(tenant.schema_name):
    with connection.cursor() as c:
        c.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_name LIKE 'tenant_%_gasto'
        """, [tenant.schema_name])
        print(c.fetchall())
```

## Notas Importantes

- ⚠️ Las migraciones deben aplicarse en **todos los esquemas de tenant** existentes
- ⚠️ El comando `migrate_schemas --tenant` aplica migraciones en todos los tenants automáticamente
- ⚠️ `--fake-initial` marca las migraciones iniciales como aplicadas si las tablas ya existen (útil para evitar errores)

## Troubleshooting

### Error: "relation does not exist"

**Causa:** Las migraciones no se han aplicado en el esquema del tenant.

**Solución:**
```bash
python manage.py migrate_schemas --tenant --fake-initial
```

### Error: "No installed app with label 'tenant_gastos'"

**Causa:** El label de la app es incorrecto.

**Solución:** Usar el label correcto:
```bash
python manage.py makemigrations tenant_gastos  # ✅ Correcto
python manage.py makemigrations gastos          # ❌ Incorrecto
```

### Error: "failed to resolve host 'db'"

**Causa:** La base de datos no está disponible o el hostname es incorrecto.

**Solución:** Verificar que la base de datos esté corriendo y que `DATABASE_HOST` esté configurado correctamente en `config/settings.py`.

## Referencias

- Script de migración: `scripts/migrate_all_schemas.py`
- Documentación django-tenants: https://django-tenants.readthedocs.io/
