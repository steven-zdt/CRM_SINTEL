# 📝 Comandos para Crear Tenant Público

## 🚀 Opciones Disponibles

### Opción 1: Comando Make (Más Simple)

```powershell
make setup
```

### Opción 2: Comando Django Directo

```powershell
docker compose exec web python manage.py setup_public_tenant
```

### Opción 3: Script PowerShell Completo

```powershell
.\setup_tenant_publico.ps1
```

Este script:
- ✅ Verifica que Docker esté corriendo
- ✅ Verifica que el contenedor web esté activo
- ✅ Ejecuta migraciones automáticamente
- ✅ Crea el tenant público
- ✅ Verifica la configuración

### Opción 4: Script PowerShell Rápido

```powershell
.\crear_tenant_publico.ps1
```

Versión simplificada que solo ejecuta el comando de setup.

### Opción 5: Script Batch (Windows)

```cmd
setup_tenant_publico.bat
```

Para usar desde CMD o doble clic.

### Opción 6: Script Python Standalone

```powershell
docker compose exec web python setup_tenants.py
```

## 📋 Orden Recomendado (Primera Vez)

```powershell
# 1. Levantar servicios
make up

# 2. Ejecutar migraciones
make migrate

# 3. Crear tenant público (elige una opción)
make setup
# o
.\setup_tenant_publico.ps1

# 4. Crear superusuario
make superuser
```

## 🔍 Verificación

Después de ejecutar el setup, verifica que todo esté correcto:

```powershell
docker compose exec web python manage.py shell
```

```python
from apps.public.tenants.models import Client, Domain

# Las apps en SHARED_APPS están automáticamente en el esquema public
# No necesitamos cambiar el tenant explícitamente
print("Tenants:", list(Client.objects.all()))
print("Dominios:", list(Domain.objects.all()))
```

Deberías ver:
- Un tenant con `schema_name='public'` y `nombre='SINTEL Global'`
- Al menos un dominio con `domain='localhost'`

## ⚠️ Solución de Problemas

### Error: "command not found: setup_public_tenant"

**Causa:** Las migraciones no se han ejecutado o el comando no está disponible.

**Solución:**
```powershell
# Primero ejecutar migraciones
make migrate

# Luego crear tenant
make setup
```

### Error: "Docker no está corriendo"

**Solución:**
- Inicia Docker Desktop
- Espera a que esté completamente iniciado
- Vuelve a ejecutar el script

### Error: "El contenedor web no está corriendo"

**Solución:**
```powershell
# Levantar servicios
make up

# Esperar unos segundos y volver a intentar
.\setup_tenant_publico.ps1
```

## 📁 Archivos Disponibles

- `setup_tenant_publico.ps1` - Script PowerShell completo con verificaciones
- `crear_tenant_publico.ps1` - Script PowerShell rápido
- `setup_tenant_publico.bat` - Script Batch para Windows
- `setup_tenants.py` - Script Python standalone
- `apps/public/tenants/management/commands/setup_public_tenant.py` - Comando Django

## 🎯 Uso Rápido Diario

Para uso diario, simplemente:

```powershell
make up
```

El setup se ejecuta automáticamente al iniciar los servicios (configurado en `docker-compose.yaml`).
