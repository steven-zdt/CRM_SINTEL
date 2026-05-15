import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from apps.public.tenants.models import Client
from apps.tenant.empresa.models import Empresa
from django_tenants.utils import tenant_context

# Intentar obtener la empresa del esquema 'home'
try:
    tenant = Client.objects.get(schema_name='home')
    with tenant_context(tenant):
        empresa = Empresa.objects.first()
        if empresa:
            print(f"ID: {empresa.id}")
            print(f"NIT: {empresa.nit}")
            print(f"DV: {empresa.dv}")
            print(f"Razon Social: {empresa.razon_social}")
        else:
            print("No hay empresa configurada en el esquema 'home'.")
        print(f"Schema actual: {connection.schema_name}")
except Exception as e:
    print(f"Error: {e}")
