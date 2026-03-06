#!/usr/bin/env python
"""Script para verificar si las tablas de gastos existen en los esquemas."""
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

print("=== Verificando tablas de tenant_gastos ===\n")

for tenant in tenants:
    schema_name = tenant.schema_name
    print(f"Esquema: {schema_name}")
    
    with schema_context(schema_name):
        cursor = connection.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = current_schema() 
            AND table_name LIKE 'tenant_gastos%' 
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        if tables:
            print(f"  Tablas encontradas: {[t[0] for t in tables]}")
        else:
            print("  [NO HAY TABLAS]")
        
        # Verificar historial de migraciones
        cursor.execute("""
            SELECT name, applied 
            FROM django_migrations 
            WHERE app = 'tenant_gastos' 
            ORDER BY name;
        """)
        migrations = cursor.fetchall()
        
        if migrations:
            print(f"  Migraciones registradas: {[m[0] for m in migrations]}")
        else:
            print("  [NO HAY MIGRACIONES REGISTRADAS]")
    
    print()
