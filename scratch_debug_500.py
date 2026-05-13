import os
import django
from django.db import connection

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.public.tenants.models import Client
from django_tenants.utils import schema_context

# Try to find a tenant schema (not 'public')
tenant = Client.objects.exclude(schema_name='public').first()
if not tenant:
    print("No tenant found. Running in public schema...")
    schema_name = 'public'
else:
    schema_name = tenant.schema_name
    print(f"Running in tenant schema: {schema_name}")

with schema_context(schema_name):
    from apps.tenant.proyectos.models import Proyecto
    from apps.tenant.proyectos.services import selectors

    try:
        # 1. Test basic listing with .only() like in selectors.py
        print("Testing selectors.qs_list()...")
        
        # We need an empresa_id if it's required by the selector
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.first()
        
        if empresa:
            print(f"Using empresa_id: {empresa.id}")
            qs = selectors.qs_list(empresa_id=empresa.id)
        else:
            print("No empresa found in tenant. Creating a mock query...")
            # If no empresa, we might not get anything, but let's see
            qs = selectors.qs_list(empresa_id=1)

        print(f"Query count: {qs.count()}")
        
        # Test first few results
        for p in qs[:5]:
            print(f"ID: {p.id}, UUID: {p.uuid}, Nombre: {p.nombre}")

    except Exception as e:
        print(f"\n[ERROR DETECTED]\nType: {type(e).__name__}\nMessage: {str(e)}")
        import traceback
        traceback.print_exc()
