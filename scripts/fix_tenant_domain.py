#!/usr/bin/env python
"""
Script para diagnosticar y corregir problemas de dominio de tenant.

Uso:
    python scripts/fix_tenant_domain.py cliente.sintel.net.co
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django_tenants.utils import schema_context, get_public_schema_name
from apps.public.tenants.models import Client, Domain


def fix_tenant_domain(hostname):
    """
    Diagnostica y corrige el dominio de un tenant.
    
    Args:
        hostname: Hostname completo (ej: 'cliente.sintel.net.co')
    """
    # Normalizar hostname (quitar puerto si existe)
    normalized_host = hostname.split(':')[0]
    
    print(f"\n{'='*80}")
    print(f"DIAGNÓSTICO Y CORRECCIÓN DE DOMINIO: {normalized_host}")
    print(f"{'='*80}\n")
    
    with schema_context(get_public_schema_name()):
        # 1. Verificar si el dominio existe
        domain = Domain.objects.filter(domain=normalized_host).first()
        
        if domain:
            print(f"[OK] Dominio encontrado en BD:")
            print(f"   - Domain: {domain.domain}")
            print(f"   - Tenant: {domain.tenant.schema_name} ({domain.tenant.nombre})")
            print(f"   - Primary: {domain.is_primary}")
            print(f"   - Is Active: {domain.tenant.is_active}")
            return True
        
        # 2. El dominio no existe, intentar inferir el schema_name
        # Asumiendo formato: {schema_name}.{domain_base}
        schema_name = normalized_host.split('.')[0]
        
        print(f"[ERROR] Dominio NO encontrado en BD")
        print(f"   Hostname normalizado: {normalized_host}")
        print(f"   Schema inferido: {schema_name}")
        print()
        
        # 3. Buscar el tenant por schema_name
        tenant = Client.objects.filter(schema_name=schema_name).first()
        
        if not tenant:
            print(f"[ERROR] ERROR: No existe un tenant con schema_name='{schema_name}'")
            print()
            print("[IDEA] SOLUCIÓN:")
            print("   1. Verifica que el tenant existe en la base de datos")
            print("   2. Si no existe, créalo primero usando el proceso de onboarding")
            print("   3. O crea el tenant manualmente:")
            print()
            print(f"   from apps.public.tenants.models import Client")
            print(f"   Client.objects.create(")
            print(f"       schema_name='{schema_name}',")
            print(f"       nombre='{schema_name.title()}',")
            print(f"       on_trial=True")
            print(f"   )")
            return False
        
        print(f"[OK] Tenant encontrado:")
        print(f"   - Schema: {tenant.schema_name}")
        print(f"   - Nombre: {tenant.nombre}")
        print(f"   - Is Active: {tenant.is_active}")
        print()
        
        # 4. Crear el dominio
        print(f"🔧 Creando dominio...")
        domain, created = Domain.objects.get_or_create(
            domain=normalized_host,
            defaults={
                'tenant': tenant,
                'is_primary': True
            }
        )
        
        if created:
            print(f"[OK] Dominio creado exitosamente:")
            print(f"   - Domain: {domain.domain}")
            print(f"   - Tenant: {domain.tenant.schema_name}")
            print(f"   - Primary: {domain.is_primary}")
            print()
            print(f"🎉 El dominio {normalized_host} ahora está disponible")
            return True
        else:
            print(f"INFO:  El dominio ya existía (pero no se encontró en la búsqueda inicial)")
            print(f"   Esto puede indicar un problema de sincronización")
            return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python scripts/fix_tenant_domain.py <hostname>")
        print("Ejemplo: python scripts/fix_tenant_domain.py cliente.sintel.net.co")
        sys.exit(1)
    
    hostname = sys.argv[1]
    success = fix_tenant_domain(hostname)
    
    if not success:
        sys.exit(1)
