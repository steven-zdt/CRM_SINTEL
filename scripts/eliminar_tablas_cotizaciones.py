"""
Script para eliminar tablas de cotizaciones directamente
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django_tenants.utils import get_tenant_model, schema_context

def eliminar_tablas_cotizaciones():
    """Elimina todas las tablas de cotizaciones de todos los tenants."""
    
    print("=" * 60)
    print("ELIMINACIÓN DE TABLAS - App Cotizaciones")
    print("=" * 60)
    
    # Tablas a eliminar
    tables = [
        'tenant_cotizaciones_item',
        'tenant_cotizaciones_documento',
        'tenant_cotizaciones_configuracion',
        'tenant_cotizaciones_producto',
        'tenant_cotizaciones_servicio',
    ]
    
    try:
        # Obtener todos los tenants
        TenantModel = get_tenant_model()
        tenants = TenantModel.objects.all()
        
        if not tenants.exists():
            print("\n⚠️  No se encontraron tenants. Intentando eliminar en esquema actual...")
            # Intentar en el esquema actual
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_schema();")
                schema = cursor.fetchone()[0]
                print(f"\n📋 Esquema actual: {schema}")
                
                # Eliminar tablas
                print("\n🗑️  Eliminando tablas...")
                for table in tables:
                    try:
                        cursor.execute(f'DROP TABLE IF EXISTS "{schema}"."{table}" CASCADE;')
                        print(f"   ✅ Tabla {table} eliminada del esquema {schema}")
                    except Exception as e:
                        print(f"   ⚠️  Error eliminando {table}: {e}")
                
                # Eliminar registros de migraciones
                print("\n🗑️  Eliminando registros de migraciones...")
                try:
                    cursor.execute(f'DELETE FROM "{schema}"."django_migrations" WHERE app = %s;', ['tenant_cotizaciones'])
                    deleted = cursor.rowcount
                    print(f"   ✅ {deleted} registros de migraciones eliminados del esquema {schema}")
                except Exception as e:
                    print(f"   ⚠️  Error eliminando registros: {e}")
        else:
            # Eliminar en cada tenant
            for tenant in tenants:
                print(f"\n📋 Procesando tenant: {tenant.schema_name}")
                
                with schema_context(tenant.schema_name):
                    with connection.cursor() as cursor:
                        # Eliminar tablas
                        print(f"   🗑️  Eliminando tablas en esquema {tenant.schema_name}...")
                        for table in tables:
                            try:
                                cursor.execute(f'DROP TABLE IF EXISTS "{tenant.schema_name}"."{table}" CASCADE;')
                                print(f"      ✅ Tabla {table} eliminada")
                            except Exception as e:
                                print(f"      ⚠️  Error eliminando {table}: {e}")
                        
                        # Eliminar registros de migraciones
                        try:
                            cursor.execute(f'DELETE FROM "{tenant.schema_name}"."django_migrations" WHERE app = %s;', ['tenant_cotizaciones'])
                            deleted = cursor.rowcount
                            print(f"      ✅ {deleted} registros de migraciones eliminados")
                        except Exception as e:
                            print(f"      ⚠️  Error eliminando registros: {e}")
        
        print("\n✅ Eliminación completada")
        print("\n📝 Próximo paso: Ejecutar 'python manage.py migrate tenant_cotizaciones'")
        
    except Exception as e:
        print(f"\n❌ Error general: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    eliminar_tablas_cotizaciones()
