#!/usr/bin/env python
"""
Script de diagnóstico para errores 404 en /console/tenants/

Uso:
    docker compose exec web python scripts/diagnose_404_console.py
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
from django.urls import reverse, resolve, Resolver404
from django_tenants.utils import schema_context
from apps.public.tenants.models import Client, Domain

def main():
    print("=" * 60)
    print("🔍 DIAGNÓSTICO: Error 404 en /console/tenants/")
    print("=" * 60)
    
    # 1. Verificar dominio público
    print("\n1. Verificando dominio público...")
    with schema_context('public'):
        try:
            public = Client.objects.get(schema_name='public')
            print(f"   ✅ Tenant público encontrado: {public.nombre}")
            
            sintel_domain = Domain.objects.filter(tenant=public, domain='sintel.com').first()
            if sintel_domain:
                print(f"   ✅ Dominio sintel.com encontrado (primary: {sintel_domain.is_primary})")
            else:
                print("   ❌ Dominio sintel.com NO encontrado")
                print("   💡 Ejecuta: python scripts/set_sintel_as_primary_domain.py")
                return 1
        except Client.DoesNotExist:
            print("   ❌ Tenant público no encontrado")
            return 1
    
    # 2. Verificar ROOT_URLCONF
    print("\n2. Verificando ROOT_URLCONF...")
    print(f"   ROOT_URLCONF: {settings.ROOT_URLCONF}")
    if settings.ROOT_URLCONF == 'config.urls_public':
        print("   ✅ Configurado correctamente")
    else:
        print("   ❌ Debe ser 'config.urls_public'")
        return 1
    
    # 3. Verificar ALLOWED_HOSTS
    print("\n3. Verificando ALLOWED_HOSTS...")
    allowed = settings.ALLOWED_HOSTS
    has_sintel = 'sintel.com' in allowed or '.sintel.com' in allowed
    print(f"   ALLOWED_HOSTS: {allowed}")
    if has_sintel:
        print("   ✅ sintel.com está en ALLOWED_HOSTS")
    else:
        print("   ❌ sintel.com NO está en ALLOWED_HOSTS")
        return 1
    
    # 4. Verificar que la ruta existe
    print("\n4. Verificando ruta /console/tenants/...")
    try:
        # Probar reverse
        url = reverse('console:tenants-list')
        print(f"   ✅ reverse('console:tenants-list') = {url}")
        
        # Probar resolve
        match = resolve('/console/tenants/')
        print(f"   ✅ resolve('/console/tenants/') = {match.view_name}")
        print(f"      View: {match.func}")
    except Exception as e:
        print(f"   ❌ Error al resolver ruta: {e}")
        return 1
    
    # 5. Verificar que urls_public incluye console
    print("\n5. Verificando inclusión de console en urls_public...")
    try:
        from config.urls_public import urlpatterns
        console_paths = [p for p in urlpatterns if 'console' in str(p.pattern)]
        if console_paths:
            print(f"   ✅ Console incluido en urls_public: {console_paths}")
        else:
            print("   ❌ Console NO encontrado en urls_public")
            return 1
    except Exception as e:
        print(f"   ❌ Error al verificar urls_public: {e}")
        return 1
    
    # 6. Verificar middleware
    print("\n6. Verificando orden de middleware...")
    middleware = settings.MIDDLEWARE
    tenant_middleware_idx = None
    for i, m in enumerate(middleware):
        if 'TenantMainMiddleware' in m:
            tenant_middleware_idx = i
            break
    
    if tenant_middleware_idx is not None:
        print(f"   ✅ TenantMainMiddleware encontrado en posición {tenant_middleware_idx}")
        print(f"      Middleware antes: {middleware[:tenant_middleware_idx+1]}")
    else:
        print("   ❌ TenantMainMiddleware NO encontrado")
        return 1
    
    # Resumen
    print("\n" + "=" * 60)
    print("📋 RESUMEN")
    print("=" * 60)
    print("✅ Todas las verificaciones pasaron")
    print("\n💡 Si aún tienes 404, verifica:")
    print("   1. Estás accediendo desde http://sintel.com/ (NO desde localhost)")
    print("   2. Tu archivo hosts tiene: 127.0.0.1 sintel.com")
    print("   3. El servidor está corriendo y accesible")
    print("   4. Estás autenticado como usuario staff")
    print("\n🔗 URLs de prueba:")
    print("   - http://sintel.com/console/tenants/")
    print("   - http://sintel.com/admin/")
    print("   - http://sintel.com/console/")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
