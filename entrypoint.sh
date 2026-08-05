#!/bin/bash
set -e

# Entrypoint unificado para contenedores de SINTEL
# ⚠️ Lógica condicional: Si los argumentos son exactamente "python manage.py runserver",
# ejecuta migrate_schemas antes de continuar

# Determinar el rol del servicio desde variable de entorno
SERVICE_ROLE=${SERVICE_ROLE:-web}

echo "🚀 Iniciando SINTEL Multi-tenant SaaS (Rol: ${SERVICE_ROLE})..."

# Función para esperar a que la BD esté lista
wait_for_db() {
    echo "⏳ Verificando disponibilidad de PostgreSQL..."
    
    # Variables de entorno con valores por defecto
    DB_HOST="${DATABASE_HOST:-db}"
    DB_PORT="${DATABASE_PORT:-5432}"
    DB_USER="${DATABASE_USER:-sintel}"
    # DEVOPS-M1: sin fallback debil — falla explicito si falta en .env
    DB_PASSWORD="${DATABASE_PASSWORD:?DATABASE_PASSWORD debe estar definido en .env}"
    DB_NAME="${DATABASE_NAME:-sintel}"
    
    # Intentar con psql primero (más directo, no carga Django)
    for i in {1..60}; do
        if PGPASSWORD="$DB_PASSWORD" \
           psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
           -c "SELECT 1;" >/dev/null 2>&1; then
            echo "✅ PostgreSQL disponible."
            return 0
        fi
        echo "   Base de datos no disponible, esperando... (intento $i/60)"
        sleep 1
    done
    
    echo "❌ ERROR: No fue posible conectarse a PostgreSQL después de 60 intentos"
    echo "   Verifica que el servicio 'db' esté corriendo y saludable"
    exit 1
}

# Función para esperar a que Redis esté lista
wait_for_redis() {
    echo "Verificando disponibilidad de Redis..."

    # Parsear host:port desde REDIS_URL (formato redis://host:port/db)
    # o usar variables individuales como fallback
    local _url="${REDIS_URL:-redis://redis:6379/0}"
    local _hostport="${_url#redis://}"        # quitar prefijo redis://
    _hostport="${_hostport%%/*}"              # quitar /db al final
    REDIS_HOST="${_hostport%%:*}"
    REDIS_PORT="${_hostport##*:}"
    REDIS_HOST="${REDIS_HOST:-redis}"
    REDIS_PORT="${REDIS_PORT:-6379}"

    for i in $(seq 1 30); do
        # nc -z: solo verificar conectividad, -w 3: timeout 3 segundos
        if nc -z -w 3 "$REDIS_HOST" "$REDIS_PORT" 2>/dev/null; then
            echo "Redis disponible en ${REDIS_HOST}:${REDIS_PORT}"
            return 0
        fi
        echo "   Redis no disponible en ${REDIS_HOST}:${REDIS_PORT}, esperando... (intento $i/30)"
        sleep 2
    done

    echo "ERROR: No fue posible conectarse a Redis en ${REDIS_HOST}:${REDIS_PORT} despues de 30 intentos"
    exit 1
}

# Esperar servicios dependientes
wait_for_db
if [ "$SERVICE_ROLE" = "celery" ]; then
    wait_for_redis
fi

# ⚠️ CRÍTICO: Exportar DJANGO_SETTINGS_MODULE antes de cualquier comando Django
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings}"
echo "🔧 DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE}"

# ⚠️ LÓGICA CONDICIONAL: Si los argumentos son exactamente "python manage.py runserver"
# ejecutar migrate_schemas antes de continuar
# Nota: "$*" concatena todos los argumentos con espacios, "$@" los mantiene separados
ARGS_STR="$*"
if [ "$ARGS_STR" = "python manage.py runserver 0.0.0.0:8000" ] || \
   ([ "$1" = "python" ] && [ "$2" = "manage.py" ] && [ "$3" = "runserver" ]); then
    echo ""
    echo "📋 Detectado comando runserver, ejecutando migraciones..."
    echo ""
    
    # Aplicar migraciones del esquema público y tenants
    echo "🔄 Aplicando migraciones del esquema public..."
    python manage.py migrate_schemas --shared || exit 1
    echo "✅ Migraciones del esquema public aplicadas"
    
    echo "🏢 Aplicando migraciones a todos los tenants..."
    python manage.py migrate_schemas --tenant || exit 1
    echo "✅ Migraciones de tenants aplicadas"

    # Garantizar tenant/dominios públicos de forma idempotente en cada arranque.
    # Esto evita pérdida funcional de enrutamiento cuando la BD fue reiniciada.
    PUBLIC_PRIMARY_DOMAIN="${TENANT_DOMAIN_BASE:-sintel.net.co}"
    export PUBLIC_TENANT_DOMAINS="${PUBLIC_TENANT_DOMAINS:-${PUBLIC_PRIMARY_DOMAIN},localhost,127.0.0.1}"

    echo "🌐 Garantizando tenant público y dominios (${PUBLIC_TENANT_DOMAINS})..."
    python manage.py create_public_tenant --domain "${PUBLIC_PRIMARY_DOMAIN}" || exit 1
    python manage.py ensure_public_domains --primary "${PUBLIC_PRIMARY_DOMAIN}" || exit 1
    echo "✅ Tenant público y dominios garantizados"

    echo "📦 Recolectando archivos estáticos..."
    python manage.py collectstatic --noinput --clear 2>&1 | tail -5 || echo "⚠️  collectstatic tuvo advertencias (no fatal)"
    echo "✅ Archivos estáticos recolectados"
    echo ""
fi


# Pasar el control al comando recibido
exec "$@"
