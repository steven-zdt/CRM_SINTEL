# 🔧 Solución: Migraciones Inconsistentes (InconsistentMigrationHistory)

**Error:** `Migration admin.0001_initial is applied before its dependency accounts.0001_initial`

**Causa:** El historial de migraciones está inconsistente porque `admin` depende de `accounts` (AUTH_USER_MODEL), pero `admin.0001_initial` está marcada como aplicada antes que `accounts.0001_initial`.

---

## 🚀 Soluciones

### Opción 1: Corregir Historial Automáticamente (Recomendado)

El comando `fix_migration_history` se ejecuta automáticamente en el flujo de Docker Compose:

```bash
make up
```

Esto ejecutará:
1. `fix_migration_history --fake-accounts` - Marca accounts.0001_initial como aplicada si la tabla existe
2. `makemigrations` - Crea nuevas migraciones si hay cambios
3. `migrate_schemas --shared --fake-initial` - Aplica migraciones
4. `check_migrations` - Verifica que no queden pendientes
5. `runserver` - Inicia el servidor

### Opción 2: Corregir Manualmente

```bash
# 1. Marcar migración de accounts como aplicada (fake)
make fix-migrations

# 2. Aplicar migraciones
make migrate-shared

# 3. Verificar
make check-migrations
```

### Opción 3: Resetear Todo (Solo Desarrollo)

⚠️ **PELIGROSO:** Esto elimina todo el historial de migraciones. Solo usar en desarrollo.

```bash
# 1. Detener servicios y eliminar volúmenes
make down

# 2. Levantar servicios (se recreará todo)
make up
```

### Opción 4: Resetear Historial Manualmente

```bash
# Acceder al shell
make shell

# Dentro del shell
python manage.py fix_migration_history --reset
# Confirmar escribiendo "yes"

# Luego aplicar migraciones con fake-initial
python manage.py migrate_schemas --shared --fake-initial
```

---

## 🔍 Verificación

Después de aplicar la solución, verifica:

```bash
# Ver estado de migraciones
docker compose exec web python manage.py showmigrations

# Verificar que no hay errores
make check-migrations
```

---

## 📝 Comando fix_migration_history

**Ubicación:** `apps/public/tenants/management/commands/fix_migration_history.py`

**Opciones:**
- `--fake-accounts`: Marca migraciones de accounts como aplicadas si las tablas existen
- `--reset`: ⚠️ Elimina todo el historial de migraciones (solo desarrollo)

**Uso:**
```bash
# Automático (recomendado)
make fix-migrations

# Manual
docker compose exec web python manage.py fix_migration_history --fake-accounts
```

---

## ✅ Prevención

Para evitar este problema en el futuro:

1. **Configurar AUTH_USER_MODEL ANTES de la primera migración**
   - Ya está configurado en `settings.py`: `AUTH_USER_MODEL = "accounts.User"`

2. **Usar --fake-initial cuando sea necesario**
   - Ya está en el flujo: `migrate_schemas --shared --fake-initial`

3. **El comando fix_migration_history se ejecuta automáticamente**
   - Ya está integrado en `docker-compose.yaml`

---

**Última Actualización:** 2026-01-17
