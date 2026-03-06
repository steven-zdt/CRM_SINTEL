#!/usr/bin/env python
"""
Script para verificar dominios registrados en la base de datos.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django_tenants.utils import get_public_schema_name, schema_context
from apps.public.tenants.models import Client, Domain

print("=" * 80)
print("VERIFICACIÓN DE DOMINIOS REGISTRADOS")
print("=" * 80)

with schema_context(get_public_schema_name()):
    domains = Domain.objects.select_related('tenant').all()
    
    print(f"\nTotal de dominios registrados: {domains.count()}\n")
    
    if domains.exists():
        print("DOMINIOS:")
        print("-" * 80)
        for d in domains:
            print(f"ID: {d.id:3d} | Domain: {d.domain:30s} | Tenant: {d.tenant.schema_name:20s} | Primary: {d.is_primary}")
        print("-" * 80)
        
        # Mostrar dominio principal de cada tenant
        print(f"\n📋 DOMINIOS PRINCIPALES POR TENANT:")
        print("-" * 80)
        tenants = Client.objects.all()
        for tenant in tenants:
            primary_domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
            if primary_domain:
                print(f"   {tenant.schema_name:20s} -> {primary_domain.domain}")
            else:
                print(f"   {tenant.schema_name:20s} -> (sin dominio principal)")
        print("-" * 80)
    else:
        print("⚠️  No hay dominios registrados en la base de datos")

print("\n" + "=" * 80)
