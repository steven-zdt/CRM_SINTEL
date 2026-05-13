import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.public.tenants.models import Client, Domain, TenantMembership
from django.contrib.auth import get_user_model

User = get_user_model()

print("--- Tenants ---")
for tenant in Client.objects.all():
    print(f"Schema: {tenant.schema_name}, Name: {tenant.nombre}")
    domains = Domain.objects.filter(tenant=tenant)
    for d in domains:
        print(f"  - Domain: {d.domain}")
    
    # List users for this tenant
    memberships = TenantMembership.objects.filter(client=tenant)
    for m in memberships:
        print(f"    - User: {m.user.email}, Rol: {m.rol}")

print("\n--- Users (Public) ---")
for user in User.objects.all():
    print(f"Email: {user.email}, Username: {user.username}, Is Staff: {user.is_staff}")
