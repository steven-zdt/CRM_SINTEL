# 🚀 Guía de Reinicio Total (Nuclear Reset) - SINTEL

Esta guía te permite realizar un reinicio completo del proyecto SINTEL, eliminando todos los datos y reconstruyendo todo desde cero.

## ⚠️ ADVERTENCIA

**Este proceso elimina TODOS los datos de la base de datos y reconstruye todo desde cero.**
Solo ejecutar en desarrollo o cuando se necesite un reinicio completo.

---

## 📋 Scripts Creados

1. **`scripts/reset_docker.sh`** - Limpia y reconstruye contenedores Docker
2. **`scripts/reset_migrations.py`** - Elimina todos los archivos de migración (excepto `__init__.py`)
3. **`scripts/init_project.sh`** - Inicializa el proyecto en el orden correcto

---

## 🎯 Instrucciones de Ejecución (Windows PowerShell)

### Paso 1: Limpiar y Reconstruir Docker

```powershell
# Opción A: Ejecutar script bash (si tienes Git Bash o WSL)
bash scripts/reset_docker.sh

# Opción B: Ejecutar comandos manualmente
docker compose down -v --remove-orphans
docker compose build --no-cache
```

**Tiempo estimado:** 5-10 minutos (depende de la velocidad de descarga de imágenes)

---

### Paso 2: Eliminar Archivos de Migración

```powershell
# Ejecutar script Python
python scripts/reset_migrations.py
```

**O si prefieres ejecutar manualmente:**

```powershell
# Eliminar archivos de migración (excepto __init__.py)
Get-ChildItem -Path "apps\public\*\migrations\*.py" -Exclude "__init__.py" | Remove-Item
Get-ChildItem -Path "apps\tenant\*\migrations\*.py" -Exclude "__init__.py" | Remove-Item
```

**Tiempo estimado:** < 1 minuto

---

### Paso 3: Levantar Contenedores

```powershell
# Levantar servicios Docker
docker compose up -d
```

**Tiempo estimado:** 1-2 minutos

**Esperar a que los servicios estén listos:**
```powershell
# Verificar que los servicios estén corriendo
docker compose ps

# Ver logs del servicio web
docker compose logs -f web
```

---

### Paso 4: Inicializar el Proyecto

```powershell
# Ejecutar script de inicialización dentro del contenedor
docker compose exec web bash scripts/init_project.sh
```

**O si prefieres ejecutar los comandos manualmente:**

```powershell
# 1. Crear migraciones (orden de dependencia)
docker compose exec web python manage.py makemigrations accounts
docker compose exec web python manage.py makemigrations

# 2. Aplicar esquema público
docker compose exec web python manage.py migrate_schemas --shared

# 3. Setup del tenant público
docker compose exec web python manage.py setup_public_tenant

# 4. Poblar catálogo DIAN (si existe el comando)
docker compose exec web python manage.py poblar_catalogo_dian

# 5. Crear superusuario por defecto
docker compose exec web python manage.py shell
```

Dentro del shell de Django:
```python
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@sintel.net.co').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@sintel.net.co',
        password='admin'
    )
    print('Superusuario creado: admin / admin@sintel.net.co / admin')
else:
    print('Superusuario ya existe')
exit()
```

**Tiempo estimado:** 2-3 minutos

---

## ✅ Verificación Final

```powershell
# Verificar que el servidor está corriendo
docker compose ps

# Verificar que puedes acceder al admin
# Abrir navegador: http://localhost:8000/admin/
# Credenciales: admin / admin
```

---

## 📝 Resumen de Comandos (Todo en Uno)

### Opción A: Script Automatizado (Recomendado)

```powershell
# Ejecutar script PowerShell que automatiza todo el proceso
.\scripts\reinicio_total.ps1
```

**Tiempo total estimado:** 8-15 minutos

### Opción B: Comandos Manuales

```powershell
# 1. Limpiar Docker
docker compose down -v --remove-orphans
docker compose build --no-cache

# 2. Eliminar migraciones
python scripts/reset_migrations.py

# 3. Levantar servicios
docker compose up -d

# 4. Esperar a que los servicios estén listos (30-60 segundos)
Start-Sleep -Seconds 30

# 5. Inicializar proyecto
docker compose exec web bash scripts/init_project.sh
```

**Tiempo total estimado:** 8-15 minutos

---

## 🔧 Solución de Problemas

### Error: "Python no encontrado" en reset_migrations.py

**Solución:** Asegúrate de tener Python instalado y en el PATH:
```powershell
python --version
```

### Error: "docker compose: command not found"

**Solución:** Usa `docker-compose` (con guion) en lugar de `docker compose`:
```powershell
docker-compose down -v --remove-orphans
```

### Error: "manage.py no encontrado" en init_project.sh

**Solución:** El script debe ejecutarse dentro del contenedor:
```powershell
docker compose exec web bash scripts/init_project.sh
```

### Error: "setup_public_tenant: command not found"

**Solución:** El comando puede no existir. Continúa con los siguientes pasos.

---

## 🎉 ¡Listo!

Una vez completados todos los pasos, tu proyecto SINTEL estará completamente reiniciado y listo para usar.

**Credenciales por defecto:**
- **Usuario:** admin
- **Email:** admin@sintel.net.co
- **Contraseña:** admin

**URLs:**
- **Admin:** http://localhost:8000/admin/
- **API Pública:** http://localhost:8000/api/public/v1/
- **Consola:** http://localhost:8000/console/
