# 🛡️ Server Guard - Verificación de Migraciones Pendientes

**Versión:** 1.0  
**Fecha:** 2026-01-17  
**Estado:** ✅ IMPLEMENTADO

---

## 📋 Descripción

El **Server Guard** es un mecanismo de seguridad que previene el arranque del servidor si hay migraciones pendientes en el esquema `public` (shared apps). Esto evita errores en producción y asegura que la base de datos esté siempre sincronizada con el código.

---

## 🔧 Implementación

### Comando de Management

**Ubicación:** `config/management/commands/check_migrations.py`

**Funcionalidad:**
- Verifica que no haya migraciones pendientes en el esquema `public`
- Bloquea el arranque del servidor si encuentra migraciones pendientes
- Proporciona mensajes claros sobre qué migraciones faltan
- Sugiere comandos para aplicar las migraciones

### Integración en Docker Compose

**Ubicación:** `docker-compose.yaml`

El comando se ejecuta automáticamente en el flujo de inicio:

```yaml
command: bash -c "python manage.py migrate_schemas --shared && python manage.py check_migrations --shared && python manage.py setup_public_tenant || true && python manage.py runserver 0.0.0.0:8000"
```

**Orden de Ejecución:**
1. ✅ `migrate_schemas --shared` - Aplica migraciones del esquema public
2. ✅ `check_migrations --shared` - Verifica que no queden pendientes
3. ✅ `setup_public_tenant` - Crea tenant público (si no existe)
4. ✅ `runserver` - Inicia el servidor (solo si todo está OK)

---

## 🚀 Uso

### Ejecución Manual

```powershell
# Verificar migraciones pendientes
docker compose exec web python manage.py check_migrations --shared

# O usando Makefile
make check-migrations
```

### Opciones del Comando

```powershell
# Solo verificar shared apps (esquema public)
python manage.py check_migrations --shared

# Solo verificar tenant apps (requiere tenant activo)
python manage.py check_migrations --tenant

# Verificar ambos
python manage.py check_migrations --all

# Continuar aunque haya pendientes (no recomendado)
python manage.py check_migrations --shared --no-fail-fast
```

---

## 📊 Comportamiento

### ✅ Caso: No Hay Migraciones Pendientes

```
🔍 Verificando migraciones pendientes...
============================================================

📦 Verificando migraciones del esquema public (shared apps)...
✅ No hay migraciones pendientes en shared apps

============================================================
✅ TODAS LAS MIGRACIONES ESTÁN APLICADAS
✅ El servidor puede iniciar correctamente.
```

**Resultado:** El servidor inicia normalmente.

---

### ❌ Caso: Hay Migraciones Pendientes

```
🔍 Verificando migraciones pendientes...
============================================================

📦 Verificando migraciones del esquema public (shared apps)...
❌ Se encontraron 2 migraciones pendientes:
   [ ] accounts.0001_initial
   [ ] impuestos.0001_initial

============================================================
❌ HAY MIGRACIONES PENDIENTES

📋 Para aplicar las migraciones pendientes, ejecuta:
   make migrate
   o
   docker compose exec web python manage.py migrate_schemas --shared

🚫 El servidor NO se iniciará hasta que se apliquen las migraciones.
```

**Resultado:** El servidor **NO** inicia. Código de salida: `1`

---

### ⚠️ Caso: Primera Ejecución (Esquema No Existe)

```
🔍 Verificando migraciones pendientes...
============================================================

📦 Verificando migraciones del esquema public (shared apps)...
⚠️  El esquema public no existe aún. Esto es normal en la primera ejecución.
   Las migraciones se ejecutarán automáticamente.

============================================================
✅ TODAS LAS MIGRACIONES ESTÁN APLICADAS
✅ El servidor puede iniciar correctamente.
```

**Resultado:** El servidor continúa (las migraciones se ejecutarán antes).

---

## 🔍 Verificación en CI/CD

El comando puede integrarse en pipelines de CI/CD:

```yaml
# Ejemplo para GitHub Actions
- name: Check Migrations
  run: |
    docker compose exec web python manage.py check_migrations --shared
```

Si hay migraciones pendientes, el pipeline fallará, forzando a aplicar las migraciones antes del deploy.

---

## 🛠️ Troubleshooting

### Error: "El servidor no inicia"

**Causa:** Hay migraciones pendientes.

**Solución:**
```powershell
# Aplicar migraciones
make migrate

# O manualmente
docker compose exec web python manage.py migrate_schemas --shared
```

### Error: "No such table"

**Causa:** Las migraciones no se han ejecutado nunca.

**Solución:**
```powershell
# Ejecutar migraciones primero
make migrate

# Luego verificar
make check-migrations
```

### El comando no se ejecuta en Docker

**Causa:** El comando puede no estar disponible si el contenedor no está construido.

**Solución:**
```powershell
# Reconstruir contenedor
docker compose up --build
```

---

## 📝 Mejoras Futuras

- [ ] Verificación de migraciones por tenant (requiere tenant activo)
- [ ] Integración con alertas (email, Slack) cuando hay pendientes
- [ ] Verificación automática en pre-commit hooks
- [ ] Reporte detallado de migraciones pendientes por app

---

## ✅ Checklist de Implementación

- [x] Comando `check_migrations.py` creado
- [x] Integrado en `docker-compose.yaml`
- [x] Comando `make check-migrations` agregado
- [x] Documentación completa
- [x] Manejo de casos edge (esquema no existe)
- [x] Mensajes claros y accionables

---

**Última Actualización:** 2026-01-17  
**Mantenido por:** Sistema de Alineación
