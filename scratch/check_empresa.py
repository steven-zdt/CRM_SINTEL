from django.db import connection
from django_tenants.utils import schema_context
from apps.tenant.empresa.models import Empresa

try:
    with schema_context('home'):
        cursor = connection.cursor()
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'home' AND table_name LIKE 'empresa_%'")
        tables = cursor.fetchall()
        print(f"Tables found: {tables}")
        
        if Empresa.objects.exists():
            empresa = Empresa.objects.get()
            print(f"Empresa found: {empresa.nombre} (ID: {empresa.id})")
        else:
            print("No Empresa found in 'home' schema")
except Exception as e:
    print(f"Error: {e}")
