#!/bin/bash
# ⚠️ HARD RESET DATABASE - SINTEL v2.40
# Script para limpiar completamente la base de datos y regenerar migraciones desde cero
# 
# ⚠️ ADVERTENCIA: Este script eliminará TODOS los datos de tenants y regenerará migraciones
# Solo ejecutar en desarrollo o cuando se requiera un reset completo

set -e  # Salir si cualquier comando falla

echo "🚨 HARD RESET DATABASE - SINTEL v2.40"
echo "======================================"
echo ""
echo "⚠️  ADVERTENCIA: Este script eliminará:"
echo "   - Todos los esquemas de tenants (excepto public e information_schema)"
echo "   - Todas las tablas de Client y Domain en el esquema public"
echo "   - Todos los archivos de migración (excepto __init__.py)"
echo ""
read -p "¿Estás seguro de continuar? (escribe 'SI' para confirmar): " confirmacion

if [ "$confirmacion" != "SI" ]; then
    echo "❌ Operación cancelada."
    exit 1
fi

echo ""
echo "📋 Paso 1: Limpiando archivos de migración..."
# Eliminar todos los archivos .py en carpetas migrations excepto __init__.py
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete
find . -path "*/migrations/__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
echo "✅ Archivos de migración eliminados"

echo ""
echo "📋 Paso 2: Limpiando base de datos PostgreSQL..."
# Conectar a PostgreSQL y ejecutar limpieza
docker-compose exec -T db psql -U sintel -d sintel <<EOF
-- ⚠️ CRÍTICO: Eliminar todos los esquemas de tenants (excepto public e information_schema)
DO \$\$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT schema_name FROM information_schema.schemata 
              WHERE schema_name NOT IN ('public', 'information_schema', 'pg_catalog', 'pg_toast', 'pg_temp_1', 'pg_toast_temp_1')
              AND schema_name NOT LIKE 'pg_%')
    LOOP
        EXECUTE 'DROP SCHEMA IF EXISTS ' || quote_ident(r.schema_name) || ' CASCADE';
        RAISE NOTICE 'Eliminado esquema: %', r.schema_name;
    END LOOP;
END \$\$;

-- Truncar tablas de tenants en el esquema public
TRUNCATE TABLE IF EXISTS tenants_client CASCADE;
TRUNCATE TABLE IF EXISTS tenants_domain CASCADE;

-- Verificar que las tablas estén vacías
SELECT 'Client count: ' || COUNT(*)::text FROM tenants_client;
SELECT 'Domain count: ' || COUNT(*)::text FROM tenants_domain;
EOF

echo "✅ Base de datos limpiada"

echo ""
echo "📋 Paso 3: Regenerando migraciones..."
docker-compose exec web python manage.py makemigrations
echo "✅ Migraciones regeneradas"

echo ""
echo "📋 Paso 4: Aplicando migraciones al esquema público..."
docker-compose exec web python manage.py migrate_schemas --shared
echo "✅ Migraciones del esquema público aplicadas"

echo ""
echo "📋 Paso 5: Verificando integridad de migraciones..."
docker-compose exec web python manage.py showmigrations --plan | head -20
echo "✅ Verificación completada"

echo ""
echo "✅ HARD RESET COMPLETADO"
echo ""
echo "📋 Próximos pasos:"
echo "   1. Crear superusuario: docker-compose exec web python manage.py createsuperuser"
echo "   2. Crear tenant público: docker-compose exec web python manage.py setup_public_tenant"
echo "   3. Probar onboarding de un tenant desde la consola"
echo ""
