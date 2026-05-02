#!/usr/bin/env python
"""
Verificación final: sintel.com como dominio principal y definitivo.

Uso:
    docker compose exec web python scripts/verify_sintel_primary.py
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django_tenants.utils import schema_context
from apps.public.tenants.models import Client, Domain

def main():
    print("=" * 60)
    print("[OK] VERIFICACIÓN: sintel.com COMO DOMINIO PRINCIPAL")
    print("=" * 60)
    
    # 1. Verificar TENANT_DOMAIN_BASE
    print(f"\n1. TENANT_DOMAIN_BASE: {settings.TENANT_DOMAIN_BASE}")
    if settings.TENANT_DOMAIN_BASE == 'sintel.com':
        print("   [OK] Configurado como sintel.com")
    else:
        print(f"   [WARNING]  Configurado como {settings.TENANT_DOMAIN_BASE} (debería ser sintel.com)")
    
    # 2. Verificar dominio en BD
    with schema_context('public'):
        public = Client.objects.get(schema_name='public')
        primary = Domain.objects.filter(tenant=public, is_primary=True).first()
        
        print(f"\n2. Dominio principal en BD:")
        print(f"   - Dominio: {primary.domain}")
        print(f"   - Primary: {primary.is_primary}")
        print(f"   - Tenant: {primary.tenant.nombre}")
        
        if primary.domain == 'sintel.com' and primary.is_primary:
            print("   [OK] sintel.com es el dominio principal")
        else:
            print("   [ERROR] sintel.com NO es el dominio principal")
            return 1
    
    # 3. Verificar ALLOWED_HOSTS
    print(f"\n3. ALLOWED_HOSTS:")
    has_sintel = 'sintel.com' in settings.ALLOWED_HOSTS
    has_wildcard = '.sintel.com' in settings.ALLOWED_HOSTS
    print(f"   - sintel.com: {'[OK]' if has_sintel else '[ERROR]'}")
    print(f"   - .sintel.com: {'[OK]' if has_wildcard else '[ERROR]'}")
    
    # 4. Verificar ROOT_URLCONF
    print(f"\n4. ROOT_URLCONF: {settings.ROOT_URLCONF}")
    if settings.ROOT_URLCONF == 'config.urls_public':
        print("   [OK] Configurado para dominio público")
    
    # Resumen
    print("\n" + "=" * 60)
    print("📋 RESUMEN")
    print("=" * 60)
    
    all_ok = (
        settings.TENANT_DOMAIN_BASE == 'sintel.com' and
        primary.domain == 'sintel.com' and
        primary.is_primary and
        has_sintel and
        has_wildcard
    )
    
    if all_ok:
        print("[OK] sintel.com ESTABLECIDO COMO DOMINIO PRINCIPAL Y DEFINITIVO")
        print("\n[IDEA] Acceso:")
        print("   - Dominio público: http://sintel.com/")
        print("   - Consola: http://sintel.com/console/tenants/")
        print("   - Admin: http://sintel.com/admin/")
        print("   - Tenants privados: http://cliente.sintel.com/")
        return 0
    else:
        print("[ERROR] Configuración incompleta. Revisa los puntos arriba.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
