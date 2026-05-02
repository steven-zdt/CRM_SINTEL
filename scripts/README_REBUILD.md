# 🔄 Scripts de Hard Reset y Reconstrucción de Base de Datos

## 📋 Descripción

Estos scripts regeneran completamente las migraciones y reconstruyen la base de datos desde cero, alineados con la arquitectura SINTEL v2.9.

## 📁 Archivos

- **`rebuild_database.sh`**: Script para Linux/Mac/Bash
- **`rebuild_database.ps1`**: Script para Windows PowerShell
- **`test_crud_full.py`**: Suite completa de tests CRUD (ubicado en `tests/public/tenants/`)

## 🚀 Uso

### Opción 1: Linux/Mac/Bash

```bash
# Dar permisos de ejecución
chmod +x scripts/rebuild_database.sh

# Ejecutar (desde la raíz del proyecto)
./scripts/rebuild_database.sh

# O si usas Docker:
docker-compose exec web bash scripts/rebuild_database.sh
```

### Opción 2: Windows PowerShell

```powershell
# Ejecutar desde la raíz del proyecto
.\scripts\rebuild_database.ps1

# O si usas Docker:
docker-compose exec web powershell -File scripts/rebuild_database.ps1
```

### Opción 3: Docker Compose (Recomendado)

```bash
# Asegurar que la base de datos esté corriendo
docker-compose up -d db redis

# Ejecutar el script dentro del contenedor
docker-compose run --rm web bash scripts/rebuild_database.sh
```

## 📝 Qué hace el script

1. **Limpieza Preventiva**:
   - Elimina archivos `.pyc` y `__pycache__`
   - Elimina archivos de migración (excepto `__init__.py`)

2. **Generación de Migraciones**:
   - Prioridad 1: `accounts` (modelo de usuario)
   - Prioridad 2: `tenants` (modelo de tenant)
   - Resto de apps

3. **Aplicación de Migraciones**:
   - Ejecuta `migrate_schemas --shared` para crear el esquema `public`

4. **Bootstrap del Sistema**:
   - Crea el tenant público usando `setup_public_tenant`
   - Crea superusuario por defecto (`admin@admin.com` / `admin`)

5. **Verificación Final**:
   - Verifica que el tenant público existe
   - Verifica que el superusuario existe

## 🧪 Ejecutar Tests

Después de ejecutar el script, valida que todo funcione:

```bash
# Tests CRUD completos
pytest tests/public/tenants/test_crud_full.py -v

# Tests de UI
pytest tests/public/console/test_tenant_ui_flow.py -v

# Todos los tests
pytest tests/ -v
```

## ⚠️ Notas Importantes

1. **Este script destruye todas las migraciones existentes**. Asegúrate de tener un backup si estás en producción.

2. **El script asume que la base de datos está vacía o puede ser recreada**. Si necesitas preservar datos, haz un backup primero.

3. **El superusuario por defecto es**:
   - Email: `admin@admin.com`
   - Password: `admin`
   - ⚠️ **Cambia esto en producción**

4. **El tenant público se crea con**:
   - Schema: `public`
   - Nombre: `SINTEL Global`
   - Dominio principal: `localhost`

## 🔍 Verificación Manual

Después de ejecutar el script, verifica manualmente:

```bash
python manage.py shell
```

```python
from apps.public.tenants.models import Client, Domain
from django.contrib.auth import get_user_model
User = get_user_model()

# Verificar tenant público
public = Client.objects.get(schema_name='public')
print(f"Tenant público: {public.nombre}")

# Verificar dominios
domains = Domain.objects.filter(tenant=public)
for d in domains:
    print(f"Dominio: {d.domain}")

# Verificar superusuario
admin = User.objects.get(email='admin@admin.com')
print(f"Superusuario: {admin.email}")
```

## 🐛 Solución de Problemas

### Error: "No module named 'django'"

**Causa**: El entorno virtual no está activado o Django no está instalado.

**Solución**:
```bash
# Activar entorno virtual
source venv/bin/activate  # Linux/Mac
# o
.\venv\Scripts\Activate.ps1  # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### Error: "relation does not exist"

**Causa**: Las migraciones no se aplicaron correctamente.

**Solución**:
```bash
# Ejecutar migraciones manualmente
python manage.py migrate_schemas --shared
python manage.py setup_public_tenant
```

### Error: "permission denied to create schema"

**Causa**: El usuario de PostgreSQL no tiene permisos.

**Solución**:
```bash
# Conceder permisos (dentro de Docker)
docker-compose exec db psql -U postgres -d sintel -c "ALTER USER sintel WITH SUPERUSER;"
```

## 📚 Referencias

- Arquitectura SINTEL: `documentacion/arquitectura_general.md`
- Tests CRUD: `tests/public/tenants/test_crud_full.py`
- Tests UI: `tests/public/console/test_tenant_ui_flow.py`
