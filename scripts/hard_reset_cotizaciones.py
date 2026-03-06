"""
Script de Hard Reset para app Cotizaciones
Elimina todas las tablas de cotizaciones y crea una nueva migración inicial.
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django.core.management import call_command

def hard_reset_cotizaciones():
    """Elimina todas las tablas de cotizaciones y crea nueva migración."""
    
    print("=" * 60)
    print("HARD RESET - App Cotizaciones")
    print("=" * 60)
    
    # Tablas a eliminar
    tables = [
        'tenant_cotizaciones_producto',
        'tenant_cotizaciones_servicio',
        'tenant_cotizaciones_documento',
        'tenant_cotizaciones_item',
        'tenant_cotizaciones_configuracion',
    ]
    
    with connection.cursor() as cursor:
        # Obtener esquema actual
        cursor.execute("SELECT current_schema();")
        schema = cursor.fetchone()[0]
        print(f"\n📋 Esquema actual: {schema}")
        
        # Eliminar tablas si existen
        print("\n🗑️  Eliminando tablas...")
        for table in tables:
            try:
                cursor.execute(f'DROP TABLE IF EXISTS "{schema}"."{table}" CASCADE;')
                print(f"   ✅ Tabla {table} eliminada")
            except Exception as e:
                print(f"   ⚠️  Error eliminando {table}: {e}")
        
        # Eliminar registros de migraciones de Django
        print("\n🗑️  Eliminando registros de migraciones...")
        try:
            cursor.execute(f'DELETE FROM "{schema}"."django_migrations" WHERE app = %s;', ['tenant_cotizaciones'])
            print(f"   ✅ Registros de migraciones eliminados")
        except Exception as e:
            print(f"   ⚠️  Error eliminando registros: {e}")
    
    print("\n✅ Hard Reset completado")
    print("\n📝 Próximo paso: Ejecutar 'python manage.py makemigrations tenant_cotizaciones'")

if __name__ == '__main__':
    hard_reset_cotizaciones()
