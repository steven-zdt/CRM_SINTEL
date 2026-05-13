import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django_tenants.utils import schema_context
from django.apps import apps

def run():
    with connection.cursor() as cursor:
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'home'")
        print("Tables in 'home' schema:")
        for row in cursor.fetchall():
            print(f"  {row[0]}")

    try:
        Proveedor = apps.get_model('tenant_proveedores', 'Proveedor')
        with schema_context('home'):
            print("\nProviders in 'home' schema:")
            for p in Proveedor.objects.all().values('id', 'uuid', 'razon_social'):
                print(f"  {p}")
    except Exception as e:
        print(f"\nError accessing Proveedor model: {e}")

if __name__ == "__main__":
    run()
