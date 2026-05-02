#!/bin/bash
# Script de Limpieza Total de Migraciones y Base de Datos
# ⚠️ ADVERTENCIA: Este script elimina todas las migraciones y la base de datos.
# Solo ejecutar en desarrollo o cuando se necesite un reset completo.

set -e  # Salir si hay algún error

echo "🔴 ADVERTENCIA: Este script eliminará todas las migraciones y la base de datos."
echo "Presiona Ctrl+C para cancelar, o Enter para continuar..."
read

echo "📦 Deteniendo contenedores..."
docker-compose down -v

echo "🗑️  Eliminando carpetas de migraciones..."

# Buscar y eliminar todas las carpetas migrations (excepto __pycache__)
find . -type d -name "migrations" -not -path "*/venv/*" -not -path "*/__pycache__/*" | while read dir; do
    if [ -d "$dir" ]; then
        echo "  Eliminando: $dir"
        # Mantener __init__.py pero eliminar todo lo demás
        find "$dir" -type f ! -name "__init__.py" -delete
        find "$dir" -type d -empty -delete
    fi
done

echo "🗑️  Eliminando archivos de base de datos..."
# Eliminar archivos .db, .sqlite, .sqlite3
find . -type f \( -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" \) -not -path "*/venv/*" -delete

echo "📁 Creando directorio estático si no existe..."
mkdir -p static
mkdir -p media

echo "✅ Limpieza completada."
echo ""
echo "📝 Próximos pasos:"
echo "1. Reconstruir contenedores: docker-compose up -d --build"
echo "2. Crear migraciones: docker-compose exec web python manage.py makemigrations"
echo "3. Aplicar migraciones: docker-compose exec web python manage.py migrate"
echo "4. Crear superusuario (opcional): docker-compose exec web python manage.py createsuperuser"
