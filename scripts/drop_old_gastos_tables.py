#!/usr/bin/env python
"""Script para eliminar tablas antiguas de gastos antes de aplicar nueva migración."""
import os
import sys
import django

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django_tenants.utils import get_tenant_model, schema_context

Tenant = get_tenant_model()
tenants = Tenant.objects.all()

print("=== Eliminando tablas antiguas de tenant_gastos ===\n")

for tenant in tenants:
    schema_name = tenant.schema_name
    print(f"Esquema: {schema_name}")
    
    with schema_context(schema_name):
        cursor = connection.cursor()
        
        # Buscar tablas antiguas
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = current_schema() 
            AND table_name LIKE 'tenant_gastos%' 
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        if tables:
            for table in tables:
                table_name = table[0]
                print(f"  Eliminando tabla: {table_name}")
                try:
                    cursor.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE;')
                    print(f"    [OK] Tabla {table_name} eliminada")
                except Exception as e:
                    print(f"    [ERROR] Error eliminando {table_name}: {e}")
        else:
            print("  [NO HAY TABLAS PARA ELIMINAR]")
    
    print()

print("[OK] Proceso completado. Ahora puedes aplicar la migración 0001_initial.")
