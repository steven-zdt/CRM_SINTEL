from django_tenants.utils import schema_context, get_tenant_model
from apps.tenant.gastos.models import DocumentoSoporte
from apps.tenant.empresa.models import Empresa
import os

TenantModel = get_tenant_model()
for t in TenantModel.objects.exclude(schema_name='public'):
    with schema_context(t.schema_name):
        try:
            e = Empresa.objects.first()
            c = DocumentoSoporte.objects.count()
            print(f"Tenant: {t.schema_name}, Empresa: {e.id if e else None}, Gastos: {c}")
        except Exception as err:
            print(f"Tenant: {t.schema_name}, Error: {str(err)}")
