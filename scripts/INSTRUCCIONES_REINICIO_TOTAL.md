# 🚀 Instrucciones de Reinicio Total (Nuclear Reset) - SINTEL

## ⚠️ ADVERTENCIA

**Este proceso elimina TODOS los datos de la base de datos y reconstruye todo desde cero.**
Solo ejecutar en desarrollo o cuando se necesite un reinicio completo.

---

## 🎯 Comandos Exactos para Ejecutar (5 minutos)

### **Opción 1: Script Automatizado (Recomendado - Windows PowerShell)**

```powershell
# Ejecutar script PowerShell que automatiza todo el proceso
.\scripts\reinicio_total.ps1
```

**Tiempo estimado:** 8-15 minutos (depende de la velocidad de descarga de imágenes Docker)

---

### **Opción 2: Comandos Manuales (Paso a Paso)**

#### **Paso 1: Limpiar y Reconstruir Docker** (5-10 minutos)

```powershell
# Detener servicios y eliminar volúmenes
docker compose down -v --remove-orphans

# Reconstruir imágenes sin caché
docker compose build --no-cache
```

#### **Paso 2: Eliminar Archivos de Migración** (< 1 minuto)

```powershell
# Ejecutar script Python
python scripts/reset_migrations.py
```

**O manualmente:**
```powershell
# Eliminar archivos de migración (excepto __init__.py)
Get-ChildItem -Path "apps\public\*\migrations\*.py" -Exclude "__init__.py" -Recurse | Remove-Item -Force
Get-ChildItem -Path "apps\tenant\*\migrations\*.py" -Exclude "__init__.py" -Recurse | Remove-Item -Force
```

#### **Paso 3: Levantar Contenedores** (1-2 minutos)

```powershell
# Levantar servicios Docker
docker compose up -d

# Esperar a que los servicios estén listos (30-60 segundos)
Start-Sleep -Seconds 30

# Verificar que los servicios estén corriendo
docker compose ps
```

#### **Paso 4: Inicializar el Proyecto** (2-3 minutos)

```powershell
# Ejecutar script de inicialización dentro del contenedor
docker compose exec web bash scripts/init_project.sh
```

**O ejecutar comandos manualmente:**

```powershell
# 1. Crear migraciones (orden de dependencia)
docker compose exec web python manage.py makemigrations accounts
docker compose exec web python manage.py makemigrations

# 2. Aplicar esquema público
docker compose exec web python manage.py migrate_schemas --shared

# 3. Setup del tenant público
docker compose exec web python manage.py setup_public_tenant --domain sintel.com

# 4. Poblar catálogo DIAN
docker compose exec web python manage.py poblar_catalogo_dian

# 5. Crear superusuario por defecto
docker compose exec web python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser(username='admin', email='admin@sintel.com', password='admin') if not User.objects.filter(email='admin@sintel.com').exists() else print('Superusuario ya existe')"
```

---

## ✅ Verificación Final

```powershell
# Verificar que el servidor está corriendo
docker compose ps

# Ver logs del servicio web
docker compose logs web

# Verificar acceso al admin
# Abrir navegador: http://localhost:8000/admin/
# Credenciales: admin / admin
```

---

## 📋 Resumen de Scripts Disponibles

1. **`scripts/reset_docker.sh`** - Limpia y reconstruye contenedores Docker
2. **`scripts/reset_migrations.py`** - Elimina todos los archivos de migración (excepto `__init__.py`)
3. **`scripts/init_project.sh`** - Inicializa el proyecto en el orden correcto
4. **`scripts/reinicio_total.ps1`** - Script PowerShell que automatiza todo el proceso

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

**Solución:** El comando existe en `apps/public/tenants/management/commands/setup_public_tenant.py`. Si falla, continúa con los siguientes pasos.

### Error: "poblar_catalogo_dian: command not found"

**Solución:** El comando existe en `apps/public/impuestos/management/commands/poblar_catalogo_dian.py`. Si falla, continúa con los siguientes pasos (el catálogo DIAN se puede poblar después).

---

## 🎉 ¡Listo!

Una vez completados todos los pasos, tu proyecto SINTEL estará completamente reiniciado y listo para usar.

**Credenciales por defecto:**
- **Usuario:** admin
- **Email:** admin@sintel.com
- **Contraseña:** admin

**URLs:**
- **Admin:** http://localhost:8000/admin/
- **Consola:** http://localhost:8000/console/
- **API Pública:** http://localhost:8000/api/public/v1/

---

## 📝 Notas Importantes

1. **Orden de Migraciones:** `accounts` debe migrarse antes que `tenants` y el resto de apps.
2. **Esquema Público:** Se crea con `migrate_schemas --shared` antes de crear tenants.
3. **Tenant Público:** Se crea con `setup_public_tenant --domain sintel.com`.
4. **Superusuario:** Se crea automáticamente si no existe.

---

## 🚀 Comandos Rápidos (Todo en Uno)

```powershell
# Reinicio completo en una sola ejecución
.\scripts\reinicio_total.ps1
```

O manualmente:

```powershell
docker compose down -v --remove-orphans
docker compose build --no-cache
python scripts/reset_migrations.py
docker compose up -d
Start-Sleep -Seconds 30
docker compose exec web bash scripts/init_project.sh
```

**Tiempo total estimado:** 8-15 minutos
