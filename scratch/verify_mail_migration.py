import os
import django

# Setup django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from apps.public.tenants.models import Client
from apps.tenant.empresa.models import MailInboxConfig
from apps.tenant.facturas.models import MailIngestionConfig

for tenant in Client.objects.exclude(schema_name='public'):
    connection.set_tenant(tenant)
    old_count = MailIngestionConfig.objects.count()
    new_count = MailInboxConfig.objects.count()
    print(f"Tenant {tenant.schema_name}: Old={old_count}, New={new_count}")
    if new_count > 0:
        for cfg in MailInboxConfig.objects.all():
            print(f"  - MailInboxConfig: {cfg.nombre} ({cfg.email_address})")
