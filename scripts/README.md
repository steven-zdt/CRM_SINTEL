# Scripts de Reconstrucción y Mantenimiento

## Reconstrucción Total de Base de Datos

### Scripts Disponibles

1. **`reconstruir_db.sh`** (Linux/Mac)
2. **`reconstruir_db.ps1`** (Windows PowerShell)

### Uso

#### Linux/Mac:
```bash
chmod +x scripts/reconstruir_db.sh
./scripts/reconstruir_db.sh
```

#### Windows PowerShell:
```powershell
.\scripts\reconstruir_db.ps1
```

### ¿Qué hace el script?

1. **Limpieza de Migraciones:**
   - Elimina todos los archivos `.py` en carpetas `migrations/` (excepto `__init__.py`)
   - Elimina archivos `.pyc` de migraciones

2. **Recreación de Migraciones (Orden Estricto):**
   - `makemigrations accounts` (Usuario global - DEBE IR PRIMERO)
   - `makemigrations tenants` (Modelo de tenant - depende de accounts)
   - `makemigrations` (Resto de aplicaciones)

3. **Aplicación de Migraciones:**
   - `migrate_schemas --shared` (Crea esquema `public`)

4. **Bootstrapping:**
   - Ejecuta `setup_public_tenant` (Crea tenant público y dominio)
   - Crea superusuario por defecto: `admin` / `admin@sintel.net.co` / `admin`

5. **Verificación Final:**
   - Muestra el estado del sistema (tenant público, dominios, superusuario)

### ⚠️ ADVERTENCIA

Este script **ELIMINA TODAS LAS MIGRACIONES** y recrea la base de datos desde cero.
**NO ejecutar en producción** sin hacer backup primero.

### Próximos Pasos Después de la Reconstrucción

1. **Ejecutar Tests de Salud:**
   ```bash
   python manage.py test tests.general.test_system_health
   ```

2. **Crear un Tenant de Prueba:**
   ```bash
   python manage.py crear_empresa "Mi Empresa" "admin@miempresa.com"
   ```

3. **Acceder al Admin:**
   - URL: http://localhost:8000/admin/
   - Usuario: `admin`
   - Contraseña: `admin`

---

## Tests de Salud del Sistema

### Ubicación
`tests/general/test_system_health.py`

### Ejecución
```bash
# Todos los tests de salud
python manage.py test tests.general.test_system_health

# Test específico
python manage.py test tests.general.test_system_health.TestSystemHealth.test_public_health
```

### Casos de Prueba

#### A. `test_public_health`
- Verifica que el tenant `public` existe
- Verifica que el dominio principal existe
- Verifica que la API pública responde (no 500)

#### B. `test_tenant_lifecycle`
- Crea un tenant usando `empresa_service`
- Valida que se creó el esquema en PostgreSQL
- Valida que se creó el dominio como subdominio (v2.17)
- Valida que se creó la membresía de admin

#### C. `test_private_access`
- Verifica redirección 302 al acceder sin login
- Verifica acceso 200 OK con login
- Verifica aislamiento de datos entre esquemas
- Verifica aislamiento cross-tenant

#### D. `test_subdomain_strictness` (v2.17)
- Valida que los dominios SIEMPRE son subdominios
- Valida formato: `{schema_name}.{TENANT_DOMAIN_BASE}`
- Valida que no se permiten FQDN arbitrarios

---

## Requisitos

- Python 3.12+
- Django 5.0+
- django-tenants
- PostgreSQL 16+
- Base de datos limpia (o eliminada)

---

## Troubleshooting

### Error: "No such file or directory"
- Asegúrate de ejecutar el script desde la raíz del proyecto
- Verifica que `manage.py` existe en el directorio actual

### Error: "ModuleNotFoundError"
- Asegúrate de tener el entorno virtual activado
- Instala las dependencias: `pip install -r requirements.txt`

### Error: "Database connection failed"
- Verifica que PostgreSQL esté corriendo
- Verifica las variables de entorno: `DATABASE_HOST`, `DATABASE_NAME`, etc.
- En Docker: `docker compose up -d db`

---

## Scripts SQL de Mantenimiento

### Scripts de Eliminación de Tablas

Estos scripts SQL son útiles para mantenimiento y limpieza de la base de datos durante el desarrollo.

#### 1. `ELIMINAR_TABLAS_COTIZACIONES.sql`

**Propósito:** Elimina todas las tablas de la app `cotizaciones` de un esquema tenant específico.

**Uso:**
```sql
-- 1. Conectarse al esquema del tenant (ej: sintel_com)
SET search_path TO sintel_com;

-- 2. Ejecutar el script completo
\i scripts/ELIMINAR_TABLAS_COTIZACIONES.sql

-- 3. Luego ejecutar migraciones
python manage.py migrate tenant_cotizaciones
```

**⚠️ ADVERTENCIA:**
- Este script elimina **TODAS** las tablas de cotizaciones del tenant
- Asegúrate de hacer backup antes de ejecutar
- Reemplaza `sintel_com` con el nombre del esquema de tu tenant

**Tablas eliminadas:**
- `tenant_cotizaciones_item`
- `tenant_cotizaciones_documento`
- `tenant_cotizaciones_configuracion`
- `tenant_cotizaciones_producto`
- `tenant_cotizaciones_servicio`

#### 2. `hard_reset_cotizaciones.sql`

**Propósito:** Hard reset completo de la app `cotizaciones` (elimina tablas y registros de migraciones).

**Uso:**
```sql
-- 1. Conectarse al esquema del tenant
SET search_path TO nombre_del_tenant;

-- 2. Ejecutar el script
\i scripts/hard_reset_cotizaciones.sql
```

**⚠️ ADVERTENCIA:**
- Elimina tablas y registros de migraciones de Django
- Requiere recrear migraciones después de ejecutar
- **NO ejecutar en producción** sin backup

**Después de ejecutar:**
```bash
# Recrear migraciones
python manage.py makemigrations tenant_cotizaciones

# Aplicar migraciones
python manage.py migrate tenant_cotizaciones
```

---

## Notas Importantes

- Estos scripts son **únicamente para desarrollo y mantenimiento**
- Siempre hacer backup antes de ejecutar scripts destructivos
- Los scripts respetan el orden de dependencias (CASCADE)
- Verifican la eliminación al final con consultas a `information_schema`