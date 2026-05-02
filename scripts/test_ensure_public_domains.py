#!/usr/bin/env python
"""
Script de prueba para verificar que ensure_public_domains funciona correctamente.

Este script simula un reinicio verificando que los dominios se crean correctamente.

Uso:
    docker compose exec web python scripts/test_ensure_public_domains.py
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django_tenants.utils import schema_context
from apps.public.tenants.models import Client, Domain
from django.core.management import call_command
from io import StringIO

def main():
    print("=" * 60)
    print("🧪 PRUEBA: ensure_public_domains")
    print("=" * 60)
    
    # 1. Verificar estado inicial
    print("\n1. Estado inicial de dominios:")
    with schema_context('public'):
        public = Client.objects.get(schema_name='public')
        domains_before = list(Domain.objects.filter(tenant=public).values_list('domain', 'is_primary'))
        print(f"   Dominios existentes: {len(domains_before)}")
        for domain, is_primary in domains_before:
            status = "⭐ PRIMARIO" if is_primary else "  "
            print(f"   {status} {domain}")
    
    # 2. Ejecutar comando (simulando reinicio)
    print("\n2. Ejecutando ensure_public_domains (simulando reinicio)...")
    out = StringIO()
    try:
        call_command('ensure_public_domains', stdout=out, verbosity=2)
        output = out.getvalue()
        print(output)
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
        return 1
    
    # 3. Verificar estado final
    print("\n3. Estado final de dominios:")
    with schema_context('public'):
        domains_after = list(Domain.objects.filter(tenant=public).values_list('domain', 'is_primary'))
        print(f"   Dominios existentes: {len(domains_after)}")
        for domain, is_primary in domains_after:
            status = "⭐ PRIMARIO" if is_primary else "  "
            print(f"   {status} {domain}")
        
        # Verificar que sintel.com existe y es primario
        sintel = Domain.objects.filter(tenant=public, domain='sintel.com').first()
        if sintel and sintel.is_primary:
            print("\n   [OK] sintel.com existe y es primario")
        else:
            print("\n   [ERROR] sintel.com NO existe o NO es primario")
            return 1
    
    # 4. Verificar que es idempotente
    print("\n4. Verificando idempotencia (segunda ejecución)...")
    out2 = StringIO()
    try:
        call_command('ensure_public_domains', stdout=out2, verbosity=1)
        output2 = out2.getvalue()
        if "sin cambios" in output2.lower() or "ya existe" in output2.lower():
            print("   [OK] Idempotente: No crea duplicados")
        else:
            print("   [WARNING]  Advertencia: Puede no ser completamente idempotente")
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
        return 1
    
    print("\n" + "=" * 60)
    print("[OK] PRUEBA COMPLETADA")
    print("=" * 60)
    print("\n[IDEA] El comando ensure_public_domains está funcionando correctamente")
    print("   Se ejecutará automáticamente en cada reinicio (entrypoint.sh)")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
