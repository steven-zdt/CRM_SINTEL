# Migraciones de la App Empleados (TENANT_APP)

## Verificaciones Previas

### 1. App instalada en TENANT_APPS

Verificar en `config/settings.py`:

```python
TENANT_APPS = [
    # ...
    "apps.tenant.empleados",    # ← Debe estar presente
    # ...
]
```

### 2. AppConfig con label único

Verificar en `apps/tenant/empleados/apps.py`:

```python
class EmpleadosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tenant.empleados'
    label = 'tenant_empleados'  # ← Label único para evitar colisiones
    verbose_name = 'Empleados'
```

El label `tenant_empleados` explica por qué las tablas se llaman `tenant_empleados_*`. No cambiar este label evita divergencias entre nombres de tabla y migraciones ya generadas.

## Generar Migraciones

```bash
# Usando el label de la app
python manage.py makemigrations tenant_empleados

# Alternativa usando el import path
python manage.py makemigrations apps.tenant.empleados
```

Esto crea/actualiza `apps/tenant/empleados/migrations/00xx_*.py`.

## Aplicar Migraciones

### Opción A: Todos los tenants

```bash
python manage.py migrate_schemas --tenant --fake-initial
```

### Opción B: Un tenant específico (útil en desarrollo)

```bash
python manage.py migrate_schemas --schema=<schema_del_tenant> --fake-initial
```

**Nota:** `--fake-initial` evita conflictos si alguna tabla ya existía con la misma estructura inicial.

### Crear esquemas faltantes

Si creaste recientemente un tenant y no tiene esquema:

```bash
python manage.py create_missing_schemas
```

## Script Idempotente (Desarrollo)

Para aplicar migraciones en todos los esquemas de una vez:

```bash
python scripts/migrate_all_schemas.py
```

Este script:
1. Aplica migraciones en `public` (SHARED_APPS)
2. Aplica migraciones en todos los tenants (TENANT_APPS)
3. Crea esquemas faltantes si hay nuevos tenants registrados

**⚠️ Solo usar en desarrollo. En producción, usar `migrate_schemas` manualmente con control.**

## Verificación en Base de Datos

### Verificar que las tablas existen

```bash
python manage.py dbshell
```

En la consola psql:

```sql
SET search_path TO <schema_del_tenant>, public;
\d tenant_empleados_devengo
\d tenant_empleados_empleado
\d tenant_empleados_contrato
\d tenant_empleados_afiliacion
\d tenant_empleados_capacitacion
```

Debes ver el layout de todas las tablas. Si `\d` responde "No relations found", vuelve a aplicar las migraciones.

### Verificar con smoke test

```bash
pytest apps/tenant/empleados/tests/test_schema_migrations_smoke.py -v
```

Este test verifica que:
- Las 5 tablas principales existen en el esquema del tenant
- La tabla `devengo` tiene la estructura esperada (campos principales)

## Reiniciar y Probar la API

1. Reinicia el contenedor/app para limpiar conexiones
2. Abre `https://home.sintel.net.co/workspace/` (o el host que uses)
3. La tabla de devengos debe cargar (200 en `GET /api/v1/empleados/devengos/?ordering=-periodo_inicio`)

### Autenticación por Sesión

Si tu UI usa sesión para el workspace, asegúrate de que los ViewSets tengan:

```python
from rest_framework.authentication import SessionAuthentication

class DevengoViewSet(...):
    authentication_classes = [SessionAuthentication]
    # ...
```

Esto hace que la cookie de sesión del tenant funcione con DRF (GET/POST/...).

## Referencias

- [django-tenants documentation](https://django-tenants.readthedocs.io/en/latest/)
- `migrate_schemas` es el mecanismo recomendado por django-tenants para aplicar migraciones de TENANT_APPS en cada esquema
- No confundir con `migrate` a secas, que aplica al esquema `public`

## Troubleshooting

### Error: "relation tenant_empleados_devengo does not exist"

**Causa:** Las migraciones no se aplicaron en el esquema del tenant.

**Solución:**
```bash
python manage.py migrate_schemas --tenant --fake-initial
```

### Error: "No relations found" al verificar tablas

**Causa:** El esquema del tenant no existe o las migraciones no se aplicaron.

**Solución:**
1. Verificar que el tenant existe: `python manage.py list_tenants`
2. Crear esquema faltante: `python manage.py create_missing_schemas`
3. Aplicar migraciones: `python manage.py migrate_schemas --tenant --fake-initial`
