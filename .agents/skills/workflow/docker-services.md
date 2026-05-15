# Skill: Docker Services & Healthchecks — SINTEL

**Carga cuando:** Modificar `docker-compose.yaml`, `entrypoint.sh`, o diagnosticar errores de startup de contenedores.

---

## Regla Fundamental: `pg_isready` NO es suficiente

| Check | Qué verifica | Suficiente para `service_healthy` |
|---|---|---|
| `pg_isready -U user -d db` | TCP + servidor aceptando conexiones | ❌ NO — no autentica ni verifica que el DB exista |
| `psql -c 'SELECT 1'` | Conexión real + autenticación + DB inicializado | ✅ SÍ |

**Raíz del bug (2026-05-15):** `pg_isready` retornaba OK mientras PostgreSQL todavía ejecutaba los scripts de inicialización (`POSTGRES_DB`, `POSTGRES_USER`). Docker arrancaba `web`/`celery` y el `psql` del `entrypoint.sh` fallaba en el intento 1.

---

## Patrón Correcto: Healthcheck PostgreSQL

```yaml
db:
  healthcheck:
    test: ["CMD-SHELL", "psql -U ${POSTGRES_USER:-sintel} -d ${POSTGRES_DB:-sintel} -c 'SELECT 1' -q 2>/dev/null"]
    interval: 5s
    timeout: 3s
    retries: 10
    start_period: 15s   # margen para inicialización del volumen en arranque en frío
```

**Nunca usar:**
```yaml
test: ["CMD-SHELL", "pg_isready -U user -d db"]   # INSUFICIENTE
```

---

## Dependencias entre Servicios

```yaml
web:
  depends_on:
    db:
      condition: service_healthy   # espera healthcheck real
    redis:
      condition: service_healthy   # usar service_healthy si el entrypoint depende de Redis

celery:
  depends_on:
    db:
      condition: service_healthy
    redis:
      condition: service_healthy
```

`service_started` solo es aceptable para servicios que no son dependencia crítica de startup.

---

## Patrón Correcto: `entrypoint.sh` — wait_for_db

El entrypoint mantiene su propio retry loop como red de seguridad, pero con `service_healthy` correcto raramente se activa:

```bash
wait_for_db() {
    DB_HOST="${DATABASE_HOST:-db}"
    DB_PORT="${DATABASE_PORT:-5432}"
    DB_USER="${DATABASE_USER:-sintel}"
    DB_PASSWORD="${DATABASE_PASSWORD:-sintel}"
    DB_NAME="${DATABASE_NAME:-sintel}"

    for i in {1..60}; do
        if PGPASSWORD="$DB_PASSWORD" \
           psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
           -c "SELECT 1;" >/dev/null 2>&1; then
            echo "PostgreSQL disponible."
            return 0
        fi
        echo "   Base de datos no disponible, esperando... (intento $i/60)"
        sleep 1
    done
    echo "ERROR: No fue posible conectarse a PostgreSQL después de 60 intentos"
    exit 1
}
```

**Prohibido añadir fallback `nc`** si `postgresql-client` está instalado en la imagen — `nc` solo verifica TCP, es equivalente a `pg_isready` y produce falsos positivos.

---

---

## Admin User — Acceso al Panel Django

`ensure_admin` corre automáticamente en cada `make up` vía `entrypoint.sh`.

| Campo | Valor |
|---|---|
| URL | `http://localhost/admin/` |
| Usuario | `sintel_dev` |
| Password | `admin123` |

`ensure_admin` usa el username **`sintel_dev`** (reservado para dev, nunca colisiona con usuarios de tenant). Solo crea el usuario si no existe — **nunca sobreescribe contraseñas de usuarios existentes**.

**Regla crítica:** `ensure_admin` NUNCA debe modificar la contraseña de un usuario ya existente. Hacerlo rompe el login de administradores de tenant que comparten el mismo `username`. Solo se permite:
- `is_staff = True` y `is_superuser = True` en usuarios existentes
- `set_password(...)` únicamente en la **creación inicial** (`created = True`)

**No ejecutar `createsuperuser` manualmente** — ya existe `sintel_dev`. Si se ejecuta y el username ya está tomado, el volumen no se limpió (`make down`).

### Diagnóstico rápido: POST /admin/login/ retorna 200

200 en login = fallo de autenticación. Causas en orden de frecuencia:

1. **Credenciales incorrectas** — usar `admin` / `admin123`
2. **Volumen no limpiado** — usuario existe con contraseña diferente → `make down && make up`
3. **`is_staff=False`** — `ensure_admin` lo corrige en el próximo arranque, o manualmente:
   ```bash
   docker compose exec web python manage.py ensure_admin
   ```
4. **Schema incorrecto** — `TenantAwareBackend` solo permite admin en schema `public` (host `localhost`). Desde un subdominio de tenant, `/admin/` retorna 404.

### Limpiar todo y empezar desde cero

```bash
make down    # docker compose down -v — elimina volúmenes nombrados
make up      # reconstruye imagen + crea DB + ensure_admin
```

`docker compose down` **sin `-v`** NO borra el volumen `crm_sintel_postgres_data`. Los usuarios de sesiones anteriores persisten.

---

## Reglas

- El healthcheck del `db` SIEMPRE usa `psql -c 'SELECT 1'`, nunca `pg_isready`
- `start_period` del `db` mínimo 15s para arranques con volumen vacío (primera vez)
- `web`/`celery` SIEMPRE con `depends_on: db: condition: service_healthy`
- No agregar fallbacks de conectividad que sean más débiles que el check principal
- `ensure_admin` es la SSoT del superusuario de desarrollo — no crear usuarios admin manualmente
- Para limpiar la BD: `make down` (con `-v`), nunca `docker compose down` a secas
