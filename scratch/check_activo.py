
import json
from apps.tenant.clientes.models import Cliente
from apps.tenant.clientes.api.serializers import ClienteListSerializer
from django_tenants.utils import schema_context
from apps.public.tenants.models import Client as Tenant

def check_serialization():
    tenant = Tenant.objects.exclude(schema_name='public').first()
    if not tenant:
        return
    with schema_context(tenant.schema_name):
        c = Cliente.objects.first()
        if c:
            s = ClienteListSerializer(c)
            print(json.dumps(s.data, indent=2))

check_serialization()
