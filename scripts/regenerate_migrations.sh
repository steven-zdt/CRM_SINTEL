#!/bin/bash
# Script para regenerar migraciones después de ejecutar fix_migrations.py
# 
# ⚠️ CRÍTICO: Este script DEBE ejecutarse en el orden exacto especificado
# para evitar errores de dependencias.

set -e  # Salir si cualquier comando falla

echo "=========================================="
echo "REGENERACION DE MIGRACIONES"
echo "=========================================="
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "manage.py" ]; then
    echo "ERROR: No se encontro manage.py en el directorio actual."
    echo "   Ejecuta este script desde la raiz del proyecto."
    exit 1
fi

echo "Paso 1/4: Creando migraciones para accounts (CRITICO - debe ser primero)..."
python manage.py makemigrations accounts
echo "✅ Migraciones de accounts creadas"
echo ""

echo "Paso 2/4: Creando migraciones para tenants (puede depender de accounts)..."
python manage.py makemigrations tenants
echo "✅ Migraciones de tenants creadas"
echo ""

echo "Paso 3/4: Creando migraciones para el resto de apps..."
python manage.py makemigrations
echo "✅ Migraciones del resto de apps creadas"
echo ""

echo "Paso 4/4: Aplicando migraciones al esquema public (shared)..."
python manage.py migrate_schemas --shared
echo "✅ Migraciones aplicadas al esquema public"
echo ""

echo "=========================================="
echo "REGENERACION COMPLETADA"
echo "=========================================="
echo ""
echo "✅ Todas las migraciones han sido regeneradas y aplicadas correctamente."
echo ""
