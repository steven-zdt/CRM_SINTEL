#!/usr/bin/env python
"""
Script de prueba para verificar el enrutamiento por hostname (TENANT_URLCONF).

Este script verifica que:
1. Requests a <schema>.sintel.net.co se resuelvan en TENANT_URLCONF
2. Requests a sintel.net.co se resuelvan en ROOT_URLCONF
3. La ruta /activate/ esté disponible en tenants privados

Uso:
    docker compose exec web python scripts/test_tenant_routing.py
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from django.urls import resolve, Resolver404
from django.conf import settings
from django_tenants.utils import schema_context
from apps.public.tenants.models import Client, Domain

def test_routing():
    """Prueba el enrutamiento por hostname."""
    print("=" * 60)
    print("🧪 PRUEBA: Enrutamiento por Hostname (TENANT_URLCONF)")
    print("=" * 60)
    
    factory = RequestFactory()
    results = []
    
    # 1. Verificar configuración
    print("\n1. Verificando configuración...")
    print(f"   ROOT_URLCONF: {settings.ROOT_URLCONF}")
    print(f"   TENANT_URLCONF: {settings.TENANT_URLCONF}")
    
    # Verificar orden de middleware
    middleware = settings.MIDDLEWARE
    tenant_middleware_idx = None
    force_no_port_idx = None
    
    for i, m in enumerate(middleware):
        if 'TenantMainMiddleware' in m:
            tenant_middleware_idx = i
        if 'ForceNoPortMiddleware' in m:
            force_no_port_idx = i
    
    print(f"\n   Orden de middleware:")
    print(f"   - ForceNoPortMiddleware: posición {force_no_port_idx}")
    print(f"   - TenantMainMiddleware: posición {tenant_middleware_idx}")
    
    if force_no_port_idx is not None and tenant_middleware_idx is not None:
        if force_no_port_idx < tenant_middleware_idx:
            print("   [OK] ForceNoPortMiddleware está ANTES de TenantMainMiddleware (correcto)")
        else:
            print("   [ERROR] ForceNoPortMiddleware está DESPUÉS de TenantMainMiddleware (incorrecto)")
            results.append(False)
    else:
        print("   [WARNING]  No se encontraron middlewares esperados")
        results.append(False)
    
    # 2. Verificar dominio público
    print("\n2. Verificando dominio público (sintel.net.co)...")
    with schema_context('public'):
        public = Client.objects.get(schema_name='public')
        sintel_domain = Domain.objects.filter(tenant=public, domain='sintel.net.co').first()
        
        if sintel_domain and sintel_domain.is_primary:
            print("   [OK] sintel.net.co existe y es primario")
        else:
            print("   [ERROR] sintel.net.co NO existe o NO es primario")
            print("   [IDEA] Ejecuta: python manage.py ensure_public_domains")
            results.append(False)
    
    # 3. Verificar tenant privado de prueba
    print("\n3. Verificando tenant privado de prueba...")
    with schema_context('public'):
        # Buscar un tenant privado (no public)
        test_tenant = Client.objects.exclude(schema_name='public').first()
        
        if test_tenant:
            test_domain = Domain.objects.filter(tenant=test_tenant, is_primary=True).first()
            if test_domain:
                print(f"   [OK] Tenant de prueba: {test_tenant.schema_name}")
                print(f"   [OK] Dominio: {test_domain.domain}")
                test_schema = test_tenant.schema_name
                test_domain_name = test_domain.domain
            else:
                print(f"   [WARNING]  Tenant {test_tenant.schema_name} sin dominio primario")
                test_schema = None
                test_domain_name = None
        else:
            print("   [WARNING]  No hay tenants privados para probar")
            test_schema = None
            test_domain_name = None
    
    # 4. Probar enrutamiento (simulación)
    print("\n4. Probando enrutamiento (simulación)...")
    print("   [WARNING]  Nota: Esta es una simulación. Para pruebas reales, usa curl o el navegador.")
    
    # Simular request a sintel.net.co (público)
    print("\n   a) Request a sintel.net.co/console/tenants/ (ROOT_URLCONF):")
    try:
        # Nota: No podemos simular completamente el middleware, pero podemos verificar las URLs
        from django.urls import reverse
        url = reverse('console:tenants-list')
        print(f"      [OK] URL resuelta: {url}")
        print(f"      [OK] Debe usar: {settings.ROOT_URLCONF}")
    except Exception as e:
        print(f"      [ERROR] Error: {e}")
        results.append(False)
    
    # Simular request a tenant privado (TENANT_URLCONF)
    if test_domain_name:
        print(f"\n   b) Request a {test_domain_name}/activate/ (TENANT_URLCONF):")
        try:
            # Verificar que la ruta existe en TENANT_URLCONF
            from config.urls_tenant import urlpatterns
            from apps.tenant.landing.urls import urlpatterns as landing_urls
            
            # Buscar la ruta activate
            activate_found = False
            for pattern in landing_urls:
                if hasattr(pattern, 'pattern') and 'activate' in str(pattern.pattern):
                    activate_found = True
                    break
            
            if activate_found:
                print(f"      [OK] Ruta /activate/ encontrada en TENANT_URLCONF")
                print(f"      [OK] Debe usar: {settings.TENANT_URLCONF}")
            else:
                print(f"      [ERROR] Ruta /activate/ NO encontrada en TENANT_URLCONF")
                results.append(False)
        except Exception as e:
            print(f"      [ERROR] Error: {e}")
            results.append(False)
    
    # 5. Verificar que TENANT_URLCONF incluye landing
    print("\n5. Verificando estructura de TENANT_URLCONF...")
    try:
        from config.urls_tenant import urlpatterns
        landing_included = any('landing' in str(p) for p in urlpatterns)
        
        if landing_included:
            print("   [OK] apps.tenant.landing.urls incluido en TENANT_URLCONF")
        else:
            print("   [ERROR] apps.tenant.landing.urls NO incluido en TENANT_URLCONF")
            results.append(False)
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
        results.append(False)
    
    # Resumen
    print("\n" + "=" * 60)
    print("📋 RESUMEN")
    print("=" * 60)
    
    if all(results) if results else True:
        print("[OK] Todas las verificaciones pasaron")
        print("\n[IDEA] Para pruebas reales de enrutamiento:")
        print("   1. Accede a http://sintel.net.co/console/tenants/ (debe usar ROOT_URLCONF)")
        if test_domain_name:
            print(f"   2. Accede a http://{test_domain_name}/activate/ (debe usar TENANT_URLCONF)")
        print("\n   Prueba con curl:")
        print("   curl -H 'Host: sintel.net.co' http://localhost:8000/console/tenants/")
        if test_domain_name:
            print(f"   curl -H 'Host: {test_domain_name}' http://localhost:8000/activate/")
        return 0
    else:
        print("[ERROR] Algunas verificaciones fallaron")
        print("   Revisa los errores arriba")
        return 1

if __name__ == '__main__':
    sys.exit(test_routing())
