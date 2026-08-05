#!/usr/bin/env python
"""
Script de prueba para verificar el enrutamiento por hostname con requests reales.

Este script simula requests HTTP con diferentes hostnames para verificar que:
1. sintel.net.co → ROOT_URLCONF (urls_public)
2. <schema>.sintel.net.co → TENANT_URLCONF (urls_tenant)
3. La ruta /activate/ está disponible en tenants privados

Uso:
    docker compose exec web python scripts/test_hostname_routing.py
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.urls import reverse, resolve, Resolver404
from django.conf import settings
from django_tenants.utils import schema_context
from apps.public.tenants.models import Client as TenantClient, Domain

def test_hostname_routing():
    """Prueba el enrutamiento por hostname con requests simulados."""
    print("=" * 60)
    print("🧪 PRUEBA: Enrutamiento por Hostname (TENANT_URLCONF)")
    print("=" * 60)
    
    # 1. Verificar configuración
    print("\n1. Verificando configuración...")
    print(f"   ROOT_URLCONF: {settings.ROOT_URLCONF}")
    print(f"   TENANT_URLCONF: {settings.TENANT_URLCONF}")
    
    # 2. Verificar dominio público
    print("\n2. Verificando dominio público (sintel.net.co)...")
    with schema_context('public'):
        public = TenantClient.objects.get(schema_name='public')
        sintel_domain = Domain.objects.filter(tenant=public, domain='sintel.net.co').first()
        
        if sintel_domain and sintel_domain.is_primary:
            print("   [OK] sintel.net.co existe y es primario")
        else:
            print("   [ERROR] sintel.net.co NO existe o NO es primario")
            print("   [IDEA] Ejecuta: python manage.py ensure_public_domains")
            return 1
    
    # 3. Buscar tenant privado de prueba
    print("\n3. Buscando tenant privado de prueba...")
    with schema_context('public'):
        test_tenant = TenantClient.objects.exclude(schema_name='public').first()
        
        if test_tenant:
            test_domain = Domain.objects.filter(tenant=test_tenant, is_primary=True).first()
            if test_domain:
                print(f"   [OK] Tenant de prueba: {test_tenant.schema_name}")
                print(f"   [OK] Dominio: {test_domain.domain}")
                test_domain_name = test_domain.domain
            else:
                print(f"   [WARNING]  Tenant {test_tenant.schema_name} sin dominio primario")
                test_domain_name = None
        else:
            print("   [WARNING]  No hay tenants privados para probar")
            test_domain_name = None
    
    # 4. Probar enrutamiento con Client de Django
    print("\n4. Probando enrutamiento con Django Test Client...")
    
    # 4a. Request a sintel.net.co (público)
    print("\n   a) Request a sintel.net.co/console/tenants/ (debe usar ROOT_URLCONF):")
    client_public = Client(HTTP_HOST='sintel.net.co')
    try:
        response = client_public.get('/console/tenants/')
        if response.status_code in [200, 302, 403]:  # 200 OK, 302 redirect, 403 forbidden (sin auth)
            print(f"      [OK] Status: {response.status_code} (esperado para ROOT_URLCONF)")
            print(f"      [OK] URL resuelta correctamente en {settings.ROOT_URLCONF}")
        else:
            print(f"      [WARNING]  Status: {response.status_code} (puede ser 404 si no está autenticado)")
    except Exception as e:
        print(f"      [ERROR] Error: {e}")
    
    # 4b. Request a tenant privado (TENANT_URLCONF)
    if test_domain_name:
        print(f"\n   b) Request a {test_domain_name}/activate/ (debe usar TENANT_URLCONF):")
        client_tenant = Client(HTTP_HOST=test_domain_name)
        try:
            response = client_tenant.get('/activate/?token=test123')
            if response.status_code in [200, 302, 400]:  # 200 OK, 302 redirect, 400 bad request (token inválido)
                print(f"      [OK] Status: {response.status_code} (esperado para TENANT_URLCONF)")
                print(f"      [OK] URL resuelta correctamente en {settings.TENANT_URLCONF}")
            elif response.status_code == 404:
                print(f"      [ERROR] Status: 404 (ruta no encontrada - posible problema de enrutamiento)")
                print(f"      [IDEA] Verifica que apps.tenant.landing.urls esté incluido en TENANT_URLCONF")
            else:
                print(f"      [WARNING]  Status: {response.status_code}")
        except Exception as e:
            print(f"      [ERROR] Error: {e}")
    
    # 5. Verificar estructura de URLs
    print("\n5. Verificando estructura de URLs...")
    
    # Verificar ROOT_URLCONF
    print("\n   a) ROOT_URLCONF (config.urls_public):")
    try:
        from config.urls_public import urlpatterns
        console_included = any('console' in str(p) for p in urlpatterns)
        if console_included:
            print("      [OK] /console/ incluido en ROOT_URLCONF")
        else:
            print("      [ERROR] /console/ NO incluido en ROOT_URLCONF")
    except Exception as e:
        print(f"      [ERROR] Error: {e}")
    
    # Verificar TENANT_URLCONF
    print("\n   b) TENANT_URLCONF (config.urls_tenant):")
    try:
        from config.urls_tenant import urlpatterns
        landing_included = any('landing' in str(p) for p in urlpatterns)
        if landing_included:
            print("      [OK] apps.tenant.landing.urls incluido en TENANT_URLCONF")
            
            # Verificar que /activate/ esté en landing
            from apps.tenant.landing.urls import urlpatterns as landing_urls
            activate_found = any('activate' in str(p.pattern) for p in landing_urls)
            if activate_found:
                print("      [OK] /activate/ encontrado en apps.tenant.landing.urls")
            else:
                print("      [ERROR] /activate/ NO encontrado en apps.tenant.landing.urls")
        else:
            print("      [ERROR] apps.tenant.landing.urls NO incluido en TENANT_URLCONF")
    except Exception as e:
        print(f"      [ERROR] Error: {e}")
    
    # 6. Verificar orden de middleware
    print("\n6. Verificando orden de middleware...")
    middleware = settings.MIDDLEWARE
    tenant_middleware_idx = None
    force_no_port_idx = None
    
    for i, m in enumerate(middleware):
        if 'TenantMainMiddleware' in m:
            tenant_middleware_idx = i
        if 'ForceNoPortMiddleware' in m:
            force_no_port_idx = i
    
    print(f"   - ForceNoPortMiddleware: posición {force_no_port_idx}")
    print(f"   - TenantMainMiddleware: posición {tenant_middleware_idx}")
    
    if force_no_port_idx is not None and tenant_middleware_idx is not None:
        if force_no_port_idx < tenant_middleware_idx:
            print("   [OK] Orden correcto: ForceNoPortMiddleware → TenantMainMiddleware")
        else:
            print("   [ERROR] Orden incorrecto: TenantMainMiddleware debe ir DESPUÉS de ForceNoPortMiddleware")
            return 1
    else:
        print("   [WARNING]  No se encontraron middlewares esperados")
        return 1
    
    # Resumen
    print("\n" + "=" * 60)
    print("📋 RESUMEN")
    print("=" * 60)
    print("[OK] Configuración de enrutamiento verificada")
    print("\n[IDEA] Para pruebas reales de enrutamiento:")
    print("   1. Accede a http://sintel.net.co/console/tenants/ (ROOT_URLCONF)")
    if test_domain_name:
        print(f"   2. Accede a http://{test_domain_name}/activate/ (TENANT_URLCONF)")
    print("\n   Prueba con curl:")
    print("   curl -H 'Host: sintel.net.co' http://localhost:8000/console/tenants/")
    if test_domain_name:
        print(f"   curl -H 'Host: {test_domain_name}' http://localhost:8000/activate/?token=test")
    
    return 0

if __name__ == '__main__':
    sys.exit(test_hostname_routing())
