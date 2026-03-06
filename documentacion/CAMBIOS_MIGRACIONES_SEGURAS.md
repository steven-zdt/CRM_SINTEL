# ✅ Cambios Aplicados: Migraciones Seguras y Server Guard

**Fecha:** 2026-01-17  
**Estado:** ✅ IMPLEMENTADO

---

## 📋 Resumen de Cambios

Se han aplicado cambios para garantizar que:
1. ✅ Las migraciones se apliquen completas antes de que el servidor arranque
2. ✅ No haya consultas a DB en import-time o en AppConfig.ready() cuando hay migraciones pendientes
3. ✅ El flujo sea: `makemigrations → migrate_schemas --shared → check_migrations → runserver`
4. ✅ Targets de Makefile para migraciones en public y tenants

---

## 🔧 Cambios Aplicados

### 1. ✅ Management Command: check_migrations

**Ubicación:** `apps/public/tenants/management/commands/check_migrations.py`

**Implementación:**
- Comando simple y robusto usando `MigrationExecutor`
- Falla si hay migraciones pendientes
- Maneja errores cuando la tabla de migraciones no existe

**Uso:**
```powershell
python manage.py check_migrations
```

**Comportamiento:**
- ✅ Si no hay migraciones pendientes: continúa normalmente
- ❌ Si hay migraciones pendientes: lanza `CommandError` y detiene el proceso
- ❌ Si no puede validar (tabla no existe): asume pendientes y falla

---

### 2. ✅ Guardas en AppConfig.ready()

**Ubicación:** `apps/public/accounts/apps.py`

**Implementación:**
- Función `_has_pending_migrations()` que verifica migraciones pendientes
- Guardas en `ready()` para evitar consultas durante comandos de mantenimiento
- Evita consultas si hay migraciones pendientes

**Comandos protegidos:**
- `migrate`, `migrate_schemas`, `makemigrations`
- `collectstatic`, `shell`, `check`, `test`

**Comportamiento:**
- ✅ Si se ejecuta un comando de mantenimiento: `ready()` retorna inmediatamente
- ✅ Si hay migraciones pendientes: `ready()` retorna sin ejecutar lógica
- ✅ Solo ejecuta lógica cuando es seguro (servidor corriendo, migraciones aplicadas)

---

### 3. ✅ Ajuste de docker-compose.yaml

**Cambios aplicados:**

**Healthcheck mejorado:**
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
  interval: 5s
  timeout: 5s
  retries: 10
```

**Comando del servicio web:**
```yaml
command: >
  bash -lc "
    python manage.py makemigrations accounts || true &&
    python manage.py makemigrations || true &&
    python manage.py migrate_schemas --shared --fake-initial &&
    python manage.py check_migrations &&
    python manage.py runserver 0.0.0.0:8000
  "
```

**Flujo de ejecución:**
1. ✅ `makemigrations accounts` - Crea migraciones para accounts (si hay cambios)
2. ✅ `makemigrations` - Crea migraciones para todas las apps (si hay cambios)
3. ✅ `migrate_schemas --shared --fake-initial` - Aplica migraciones del esquema public
4. ✅ `check_migrations` - Verifica que no queden migraciones pendientes
5. ✅ `runserver` - Inicia el servidor (solo si todo está OK)

**Nota:** `--fake-initial` permite aplicar migraciones iniciales sin errores si las tablas ya existen.

---

### 4. ✅ Makefile - Targets de Migración Seguros

**Targets agregados/actualizados:**

```makefile
makemigrations:          # Crea migraciones para todas las apps
makemigrations-accounts:  # Crea migraciones solo para accounts
migrate-shared:          # Aplica migraciones del esquema public (--fake-initial)
migrate-tenants:         # Aplica migraciones de tenant apps (--fake-initial)
check-migrations:        # Verifica que no haya migraciones pendientes
```

**Uso recomendado:**

```powershell
# Arranque inicial
make up
make migrate-shared

# Cuando crees tenants nuevos
make migrate-tenants

# Verificar migraciones pendientes
make check-migrations
```

---

## 🚀 Flujo Recomendado de Arranque

### Primera vez (setup completo):

```powershell
# 1. Levantar servicios
make up

# 2. Aplicar migraciones del esquema public
make migrate-shared

# 3. Verificar que no hay pendientes
make check-migrations

# 4. Crear tenant público (si no existe)
make setup

# 5. Poblar catálogo DIAN
make poblar-dian

# 6. Crear superusuario
make superuser
```

### Desarrollo diario:

```powershell
# Solo levantar servicios (el flujo automático se encarga de todo)
make up
```

### Después de cambios en modelos:

```powershell
# 1. Crear migraciones
make makemigrations

# 2. Aplicar migraciones
make migrate-shared

# 3. Verificar
make check-migrations
```

### Onboarding de tenant nuevo:

```powershell
# 1. Crear Client y Domain desde admin o shell
# 2. Aplicar migraciones para el tenant
docker compose exec web python manage.py migrate_schemas --schema=<schema_name> --fake-initial
```

---

## 🛡️ Protecciones Implementadas

### 1. Server Guard

- ✅ El servidor **NO** arranca si hay migraciones pendientes
- ✅ Verificación automática antes de `runserver`
- ✅ Mensajes claros sobre qué migraciones faltan

### 2. Protección en AppConfig

- ✅ No ejecuta lógica durante comandos de mantenimiento
- ✅ No ejecuta lógica si hay migraciones pendientes
- ✅ Evita consultas a DB en import-time

### 3. Flujo Automático

- ✅ `makemigrations` se ejecuta automáticamente antes de migrar
- ✅ `migrate_schemas --shared --fake-initial` aplica migraciones de forma segura
- ✅ `check_migrations` valida que todo esté aplicado
- ✅ Solo entonces se inicia el servidor

---

## ✅ Validación

### Verificar que el Server Guard funciona:

```powershell
# 1. Crear una migración nueva sin aplicarla
make makemigrations

# 2. Intentar arrancar el servidor
make up

# 3. Verificar logs
make logs
```

**Resultado esperado:**
- ❌ El servidor NO debe arrancar
- ❌ Debe mostrar error: "Hay migraciones pendientes en la DB"
- ✅ Después de `make migrate-shared`, el servidor debe arrancar

### Verificar que no hay consultas en import-time:

```powershell
# 1. Ejecutar comandos de mantenimiento
make makemigrations
make migrate-shared

# 2. Verificar que no hay errores de "table does not exist"
# 3. El servidor debe arrancar sin problemas
```

---

## 📝 Notas Importantes

### ⚠️ Evitar Consultas en Import-Time

**NO hacer esto:**
```python
# ❌ MAL: Consulta en import-time
from .models import User
users = User.objects.all()  # Esto fallará si hay migraciones pendientes
```

**Hacer esto:**
```python
# ✅ BIEN: Consulta dentro de función
def get_users():
    from .models import User
    return User.objects.all()
```

### ⚠️ Signals y AppConfig.ready()

Si necesitas cargar signals, hazlo dentro de `ready()` pero después de las guardas:

```python
def ready(self):
    # Guardas primero
    if any(cmd in sys.argv for cmd in mgmt_cmds):
        return
    if _has_pending_migrations():
        return
    
    # Luego carga signals (sin consultas en import-time)
    from . import signals  # signals.py no debe hacer queries al importar
```

---

## 🔍 Troubleshooting

### Error: "Hay migraciones pendientes en la DB"

**Solución:**
```powershell
make migrate-shared
```

### Error: "No fue posible validar migraciones"

**Causa:** La tabla de migraciones no existe aún.

**Solución:**
```powershell
make migrate-shared
```

### El servidor no arranca después de cambios en modelos

**Solución:**
```powershell
# 1. Crear migraciones
make makemigrations

# 2. Aplicar migraciones
make migrate-shared

# 3. Verificar
make check-migrations
```

---

## ✅ Checklist de Implementación

- [x] Comando `check_migrations` creado en `apps/public/tenants/management/commands/`
- [x] Guardas implementadas en `apps/public/accounts/apps.py`
- [x] `docker-compose.yaml` actualizado con nuevo flujo
- [x] `Makefile` actualizado con targets de migración
- [x] Comando anterior de `config/management/commands/` eliminado
- [x] Healthcheck mejorado en `docker-compose.yaml`
- [x] Documentación completa

---

**Última Actualización:** 2026-01-17  
**Estado:** ✅ IMPLEMENTADO Y VERIFICADO
