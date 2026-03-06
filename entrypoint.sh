#!/bin/bash
# Entrypoint unificado para contenedores de SINTEL
# Usa SERVICE_ROLE para distinguir entre web y celery

# ⚠️ NOTA: NO usar 'set -e' aquí porque wait_for_db() necesita manejar errores
# Los comandos críticos usarán '|| exit 1' explícitamente

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
    DB_PASSWORD="${DATABASE_PASSWORD:-sintel}"
    DB_NAME="${DATABASE_NAME:-sintel}"
    
    # Intentar con psql primero (más directo, no carga Django)
    for i in {1..60}; do
        if PGPASSWORD="$DB_PASSWORD" \
           psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
           -c "SELECT 1;" >/dev/null 2>&1; then
            echo "✅ PostgreSQL disponible."
            return 0
        fi
        
        # Si psql no está disponible, intentar con nc como fallback
        if ! command -v psql >/dev/null 2>&1; then
            if command -v nc >/dev/null 2>&1; then
                if nc -z "$DB_HOST" "$DB_PORT" >/dev/null 2>&1; then
                    echo "✅ PostgreSQL disponible (verificado con nc)."
                    return 0
                fi
            fi
        fi
        
        echo "   Base de datos no disponible, esperando... (intento $i/60)"
        sleep 1
    done
    
    echo "❌ ERROR: No fue posible conectarse a PostgreSQL después de 60 intentos"
    echo "   Verifica que el servicio 'db' esté corriendo y saludable"
    echo "   Variables de entorno:"
    echo "     DATABASE_HOST=${DB_HOST}"
    echo "     DATABASE_PORT=${DB_PORT}"
    echo "     DATABASE_USER=${DB_USER}"
    echo "     DATABASE_NAME=${DB_NAME}"
    echo "   Comando de diagnóstico:"
    echo "     docker compose logs db -f"
    exit 1
}

# Función para esperar a que Redis esté lista
wait_for_redis() {
    echo "⏳ Esperando a que Redis esté lista..."
    until python -c "import redis; r = redis.Redis(host='redis', port=6379, db=0); r.ping()" 2>/dev/null; do
        echo "   Redis no disponible, esperando..."
        sleep 2
    done
    echo "✅ Redis lista"
}

# Esperar servicios dependientes
wait_for_db
if [ "$SERVICE_ROLE" = "celery" ]; then
    wait_for_redis
fi

# ============================================================================
# LÓGICA ESPECÍFICA POR ROL
# ============================================================================

if [ "$SERVICE_ROLE" = "web" ]; then
    # ========================================================================
    # ROL: WEB (Servidor Django)
    # ========================================================================
    echo ""
    echo "📋 Configurando servicio WEB..."
    echo ""
    
    # ⚠️ CRÍTICO: Exportar DJANGO_SETTINGS_MODULE antes de cualquier comando Django
    # Esto asegura que Django pueda cargar settings y registrar management commands
    export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings}"
    echo "🔧 DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE}"
    
    # 1. Asegurar que los directorios estáticos existan (por si acaso)
    mkdir -p /app/static /app/media /app/staticfiles
    
    # 2. Corregir historial de migraciones si es necesario (silencioso)
    echo "🔧 Verificando historial de migraciones..."
    python manage.py fix_migration_history --fake-accounts --verbosity 0 || true
    
    # 3. Aplicar migraciones del esquema public (shared)
    echo "🔄 Aplicando migraciones del esquema public..."
    python manage.py migrate_schemas --shared --fake-initial --verbosity 0 || {
        echo "❌ ERROR: Fallo al aplicar migraciones del esquema public"
        exit 1
    }
    echo "✅ Migraciones del esquema public aplicadas"
    
    # 4. Server Guard: Verificar que no queden migraciones pendientes en shared
    echo "🛡️  Verificando migraciones pendientes (shared)..."
    python manage.py check_migrations --verbosity 0 2>/dev/null || {
        echo "⚠️  Advertencia: check_migrations falló o no está disponible"
    }
    
    # 5. Configurar tenant público si no existe (silencioso)
    echo "🏢 Configurando tenant público..."
    python manage.py setup_public_tenant --skip-migrations --verbosity 0 || true
    
    # 6. Asegurar que los dominios del tenant público existan (idempotente)
    echo "🛡️ Garantizando dominios del tenant público..."
    python manage.py ensure_public_domains --verbosity 0 || echo "⚠️ Advertencia: No se pudieron asegurar los dominios del tenant público"
    
    # 7. Aplicar migraciones a todos los esquemas de tenant
    # ⚠️ CRÍTICO: Primero intentar sin --fake-initial para crear tablas nuevas (ej: tenant_gastos_documentosoporte)
    # Si falla, usar --fake-initial solo para migraciones que ya están aplicadas
    # Usar variable de entorno TENANTS para controlar qué tenants migrar
    TENANTS="${TENANTS:-all}"
    if [ "$TENANTS" = "all" ]; then
        echo "🏢 Aplicando migraciones a todos los tenants..."
        # Intentar primero sin --fake-initial para asegurar que tablas nuevas se creen
        python manage.py migrate_schemas --tenant --verbosity 1 || {
            echo "⚠️  Primera aplicación falló, intentando con --fake-initial..."
            # Si falla, intentar con --fake-initial (para migraciones ya aplicadas)
            python manage.py migrate_schemas --tenant --fake-initial --verbosity 1 || {
                echo "❌ ERROR: Fallo al aplicar migraciones de tenants"
                exit 1
            }
        }
        echo "✅ Migraciones de tenants aplicadas"
    else
        echo "🏢 Aplicando migraciones al schema: $TENANTS ..."
        # Intentar primero sin --fake-initial
        python manage.py migrate_schemas --schema="$TENANTS" --verbosity 1 || {
            echo "⚠️  Primera aplicación falló, intentando con --fake-initial..."
            python manage.py migrate_schemas --schema="$TENANTS" --fake-initial --verbosity 1 || {
                echo "❌ ERROR: Fallo al aplicar migraciones del schema $TENANTS"
                exit 1
            }
        }
        echo "✅ Migraciones aplicadas para $TENANTS"
    fi
    
    # 9. Iniciar servidor de desarrollo (con logs normales)
    echo ""
    echo "✅ Iniciando servidor Django..."
    echo ""
    exec python manage.py runserver 0.0.0.0:8000

elif [ "$SERVICE_ROLE" = "celery" ]; then
    # ========================================================================
    # ROL: CELERY (Worker de tareas)
    # ========================================================================
    echo ""
    echo "📋 Configurando servicio CELERY..."
    echo ""
    echo "ℹ️  Celery NO ejecuta migraciones (ya las ejecuta el servicio web)"
    echo "ℹ️  Celery solo espera a que la BD y Redis estén listas"
    echo ""
    
    # ⚠️ CRÍTICO: Exportar DJANGO_SETTINGS_MODULE antes de ejecutar celery
    # Esto asegura que Django pueda cargar settings correctamente
    export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings}"
    echo "🔧 DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE}"
    
    # Celery NO ejecuta migraciones ni setup de tenants
    # El servicio web ya se encargó de eso
    
    # Iniciar Celery Worker
    echo "✅ Iniciando Celery Worker..."
    echo ""
    # Ejecutar el comando pasado como argumento (desde docker-compose)
    # El comando debe ser: celery -A config worker --loglevel=info --concurrency=4 -Q high_priority,default
    exec "$@"

else
    echo "❌ ERROR: SERVICE_ROLE desconocido: ${SERVICE_ROLE}"
    echo "   Valores válidos: 'web' o 'celery'"
    exit 1
fi
