#!/usr/bin/env bash
set -e

echo "🚀 Iniciando aplicación SINTEL en modo producción..."

# Esperar servicios externos (PostgreSQL, Redis, OpenSearch)
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
        break
    fi
    
    # Si psql no está disponible, intentar con nc como fallback
    if ! command -v psql >/dev/null 2>&1; then
        if command -v nc >/dev/null 2>&1; then
            if nc -z "$DB_HOST" "$DB_PORT" >/dev/null 2>&1; then
                echo "✅ PostgreSQL disponible (verificado con nc)."
                break
            fi
        fi
    fi
    
    if [ $i -eq 60 ]; then
        echo "❌ ERROR: No fue posible conectarse a PostgreSQL después de 60 intentos"
        echo "   Verifica que el servicio 'db' esté corriendo y saludable"
        exit 1
    fi
    
    echo "   Base de datos no disponible, esperando... (intento $i/60)"
    sleep 1
done

# Migraciones del esquema public (SHARED_APPS)
echo "📦 Aplicando migraciones del esquema public..."
python manage.py migrate --noinput

# Migraciones de django-tenants (esquema public)
echo "📦 Aplicando migrate_schemas --shared..."
python manage.py migrate_schemas --shared --fake-initial || true

# Opcional: crear tenant/domains iniciales desde variables de entorno
if [ -n "$SEED_TENANT_NAME" ] && [ -n "$SEED_TENANT_DOMAIN" ]; then
  echo "🌱 Creando tenant inicial: ${SEED_TENANT_NAME} (${SEED_TENANT_DOMAIN})..."
  python manage.py shell <<PY
from apps.public.tenants.models import Client, Domain
from django.contrib.auth import get_user_model

User = get_user_model()

# Obtener o crear tenant
schema_name = "${SEED_TENANT_SCHEMA:-sintel}"
c, created = Client.objects.get_or_create(
    schema_name=schema_name,
    defaults={
        "nombre": "${SEED_TENANT_NAME}",
        "auto_create_schema": True
    }
)

if created:
    print(f"✅ Tenant creado: {c.schema_name}")
    # Crear dominio
    Domain.objects.get_or_create(
        domain="${SEED_TENANT_DOMAIN}",
        tenant=c,
        defaults={"is_primary": True}
    )
    print(f"✅ Dominio creado: ${SEED_TENANT_DOMAIN}")
    
    # Migrar esquema del tenant
    from django.core.management import call_command
    call_command("migrate_schemas", "--schema", schema_name, "--fake-initial", verbosity=0)
    print(f"✅ Migraciones del tenant aplicadas")
else:
    print(f"ℹ️  Tenant ya existe: {c.schema_name}")
PY
fi

# System check (producción)
echo "🔍 Ejecutando system check..."
python manage.py check --deploy || true

# Iniciar Gunicorn
echo "🚀 Iniciando Gunicorn..."
exec gunicorn -c /app/gunicorn.conf.py config.wsgi:application
