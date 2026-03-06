# 🚨 HARD RESET DATABASE - SINTEL v2.40

## ⚠️ ADVERTENCIA CRÍTICA

Este proceso eliminará **TODOS** los datos de tenants y regenerará migraciones desde cero. Solo ejecutar en desarrollo o cuando se requiera un reset completo.

## 📋 Proceso Manual (Paso a Paso)

### Paso 1: Limpiar Archivos de Migración

**Linux/Mac:**
```bash
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete
find . -path "*/migrations/__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
```

**Windows (PowerShell):**
```powershell
Get-ChildItem -Path . -Recurse -Filter "*.py" | 
    Where-Object { $_.FullName -match "migrations" -and $_.Name -ne "__init__.py" } | 
    Remove-Item -Force

Get-ChildItem -Path . -Recurse -Filter "*.pyc" | 
    Where-Object { $_.FullName -match "migrations" } | 
    Remove-Item -Force

Get-ChildItem -Path . -Recurse -Directory | 
    Where-Object { $_.FullName -match "migrations.*__pycache__" } | 
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
```

### Paso 2: Limpiar Base de Datos PostgreSQL

**Conectar a PostgreSQL y ejecutar:**

```sql
-- ⚠️ CRÍTICO: Eliminar todos los esquemas de tenants (excepto public e information_schema)
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT schema_name FROM information_schema.schemata 
              WHERE schema_name NOT IN ('public', 'information_schema', 'pg_catalog', 'pg_toast', 'pg_temp_1', 'pg_toast_temp_1')
              AND schema_name NOT LIKE 'pg_%')
    LOOP
        EXECUTE 'DROP SCHEMA IF EXISTS ' || quote_ident(r.schema_name) || ' CASCADE';
        RAISE NOTICE 'Eliminado esquema: %', r.schema_name;
    END LOOP;
END $$;

-- Truncar tablas de tenants en el esquema public
TRUNCATE TABLE IF EXISTS tenants_client CASCADE;
TRUNCATE TABLE IF EXISTS tenants_domain CASCADE;

-- Verificar que las tablas estén vacías
SELECT 'Client count: ' || COUNT(*)::text FROM tenants_client;
SELECT 'Domain count: ' || COUNT(*)::text FROM tenants_domain;
```

**O usando docker-compose:**
```bash
docker-compose exec db psql -U sintel -d sintel -c "TRUNCATE TABLE tenants_client CASCADE; TRUNCATE TABLE tenants_domain CASCADE;"
```

### Paso 3: Regenerar Migraciones

```bash
docker-compose exec web python manage.py makemigrations
```

**Verificar que se generaron correctamente:**
```bash
docker-compose exec web python manage.py makemigrations --dry-run
```

### Paso 4: Aplicar Migraciones al Esquema Público

```bash
docker-compose exec web python manage.py migrate_schemas --shared
```

### Paso 5: Verificar Integridad

```bash
docker-compose exec web python manage.py showmigrations --plan
```

### Paso 6: Crear Superusuario Base

```bash
docker-compose exec web python manage.py createsuperuser
```

### Paso 7: Configurar Tenant Público

```bash
docker-compose exec web python manage.py setup_public_tenant
```

## 🔍 Verificaciones Post-Reset

### 1. Verificar SHARED_APPS y TENANT_APPS

```bash
docker-compose exec web python manage.py shell -c "from django.conf import settings; print('SHARED_APPS:', settings.SHARED_APPS); print('TENANT_APPS:', settings.TENANT_APPS)"
```

### 2. Verificar que no haya dependencias circulares

```bash
docker-compose exec web python manage.py check
```

### 3. Verificar que el modelo Cotizacion no tenga conflictos con Empresa

```bash
docker-compose exec web python manage.py shell -c "from apps.tenant.cotizaciones.models import Cotizacion; from apps.tenant.empresa.models import Empresa; print('✅ Modelos importados correctamente')"
```

### 4. Verificar que el Monkey Patch de admin.py no interfiera

```bash
docker-compose exec web python manage.py shell -c "from apps.tenant.core.admin import tenant_admin_site; print('✅ Admin site cargado correctamente')"
```

## 📋 Checklist de Apps en TENANT_APPS

Verificar que todas estas apps estén en `config/settings.py`:

- ✅ `apps.tenant.empresa`
- ✅ `apps.tenant.cotizaciones`
- ✅ `apps.tenant.gastos`
- ✅ `apps.tenant.facturas`
- ✅ `apps.tenant.clientes`
- ✅ `apps.tenant.proveedores`
- ✅ `apps.tenant.empleados`
- ✅ `apps.tenant.inventario`
- ✅ `apps.tenant.contabilidad`
- ✅ `apps.tenant.proyectos`
- ✅ `apps.tenant.perfil`

## ⚠️ Notas Importantes

1. **No hay fixtures requeridas**: El sistema de cotizaciones no requiere datos iniciales (tipos de impuestos o monedas) porque:
   - Los porcentajes de IVA se configuran en `ConfiguracionCotizacion` por empresa
   - Las monedas se definen en el modelo `ConfiguracionCotizacion.formato_moneda`
   - No hay catálogos de impuestos predefinidos

2. **Dependencias circulares**: El modelo `Cotizacion` tiene una ForeignKey a `Empresa`, pero esto es correcto porque:
   - `Empresa` está en `apps.tenant.empresa` (TENANT_APPS)
   - `Cotizacion` está en `apps.tenant.cotizaciones` (TENANT_APPS)
   - Ambos están en el mismo esquema de tenant, por lo que no hay conflicto

3. **Monkey Patch de admin.py**: El patch `_safe_index` solo se aplica al `admin.site` global y no interfiere con la creación de tablas durante las migraciones.

## 🚀 Scripts Automatizados

Se han creado scripts automatizados:
- `scripts/hard_reset_database.sh` (Linux/Mac)
- `scripts/hard_reset_database.ps1` (Windows PowerShell)

Ejecutar con:
```bash
# Linux/Mac
chmod +x scripts/hard_reset_database.sh
./scripts/hard_reset_database.sh

# Windows PowerShell
.\scripts\hard_reset_database.ps1
```
