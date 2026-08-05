#!/usr/bin/env python
"""
Script de debug paso a paso para el flujo de activación de tenant.

Este script simula el flujo completo desde la creación del tenant hasta la activación
y verifica que el enrutamiento funcione correctamente.

Uso:
    docker compose exec web python scripts/debug_tenant_routing_activation.py
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from django.urls import resolve, Resolver404, reverse
from django.conf import settings
from django_tenants.utils import schema_context
from apps.public.tenants.models import Client as TenantClient, Domain, TenantMembership
from apps.public.tenants.services.invitations import generate_invitation_token, verify_invitation_token
from apps.services.onboarding.empresa_service import crear_tenant_con_owner

User = get_user_model()

def debug_step_by_step():
    """Debug paso a paso del flujo de activación."""
    print("=" * 80)
    print("🔍 DEBUG: Flujo de Activación de Tenant (Paso a Paso)")
    print("=" * 80)
    
    # PASO 1: Crear tenant de prueba
    print("\n" + "=" * 80)
    print("PASO 1: Crear Tenant de Prueba")
    print("=" * 80)
    
    test_schema = f"test_debug_{os.getpid()}"
    test_domain = f"{test_schema}.sintel.net.co"
    test_email = f"test_{os.getpid()}@sintel.net.co"
    
    print(f"📋 Parámetros de prueba:")
    print(f"   Schema: {test_schema}")
    print(f"   Dominio: {test_domain}")
    print(f"   Email: {test_email}")
    
    try:
        result = crear_tenant_con_owner(
            nombre="Tenant Debug",
            schema_name=test_schema,
            dominio_fqdn=test_domain,
            owner_email=test_email,
            on_trial=True,
        )
        
        tenant_id = result['client_id']
        print(f"[OK] Tenant creado: ID={tenant_id}")
        print(f"   Activation URL: {result.get('activation_url', 'N/A')}")
        
        # Obtener tenant y dominio
        with schema_context('public'):
            tenant = TenantClient.objects.get(id=tenant_id)
            domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
            user = User.objects.get(email=test_email)
            
            print(f"[OK] Tenant encontrado: {tenant.nombre} (schema: {tenant.schema_name})")
            print(f"[OK] Dominio encontrado: {domain.domain} (primary: {domain.is_primary})")
            print(f"[OK] Usuario encontrado: {user.email} (password usable: {user.has_usable_password()})")
            
    except Exception as e:
        print(f"[ERROR] Error al crear tenant: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # PASO 2: Verificar dominio en BD
    print("\n" + "=" * 80)
    print("PASO 2: Verificar Dominio en Base de Datos")
    print("=" * 80)
    
    with schema_context('public'):
        domain_check = Domain.objects.filter(domain=test_domain).first()
        if domain_check:
            print(f"[OK] Dominio existe en BD: {domain_check.domain}")
            print(f"   Tenant: {domain_check.tenant.nombre} (schema: {domain_check.tenant.schema_name})")
            print(f"   Primary: {domain_check.is_primary}")
        else:
            print(f"[ERROR] Dominio NO existe en BD: {test_domain}")
            return 1
    
    # PASO 3: Simular request a /activate/ con token
    print("\n" + "=" * 80)
    print("PASO 3: Simular Request a /activate/ con Token")
    print("=" * 80)
    
    # Generar token de activación
    token = generate_invitation_token(user.id, tenant.id)
    print(f"[OK] Token generado: {token[:50]}...")
    
    # Verificar token
    payload = verify_invitation_token(token)
    if payload:
        print(f"[OK] Token verificado: user_id={payload['user_id']}, tenant_id={payload['tenant_id']}")
    else:
        print(f"[ERROR] Token inválido")
        return 1
    
    # Simular request con HTTP_HOST correcto
    print(f"\n📋 Simulando request:")
    print(f"   URL: http://{test_domain}/activate/?token=...")
    print(f"   HTTP_HOST: {test_domain}")
    
    client = Client(HTTP_HOST=test_domain)
    
    # PASO 4: Verificar resolución de URL
    print("\n" + "=" * 80)
    print("PASO 4: Verificar Resolución de URL")
    print("=" * 80)
    
    try:
        # Intentar resolver /activate/ en TENANT_URLCONF
        from config.urls_tenant import urlpatterns
        print(f"[OK] TENANT_URLCONF cargado: config.urls_tenant")
        
        # Verificar que /activate/ está en landing.urls
        from apps.tenant.landing.urls import urlpatterns as landing_urls
        activate_found = any('activate' in str(p.pattern) for p in landing_urls)
        if activate_found:
            print(f"[OK] Ruta /activate/ encontrada en apps.tenant.landing.urls")
        else:
            print(f"[ERROR] Ruta /activate/ NO encontrada en apps.tenant.landing.urls")
            return 1
        
        # Intentar hacer request
        response = client.get(f'/activate/?token={token}')
        print(f"\n📋 Response:")
        print(f"   Status: {response.status_code}")
        print(f"   URLConf usado: {getattr(response, 'urlconf', 'N/A')}")
        
        if response.status_code == 200:
            print(f"[OK] Request exitoso (200 OK)")
        elif response.status_code == 302:
            print(f"[WARNING]  Redirect (302) - Verificar destino")
            print(f"   Location: {response.get('Location', 'N/A')}")
        else:
            print(f"[ERROR] Status inesperado: {response.status_code}")
            
    except Exception as e:
        print(f"[ERROR] Error al verificar resolución: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # PASO 5: Verificar middleware y URLConf
    print("\n" + "=" * 80)
    print("PASO 5: Verificar Middleware y URLConf")
    print("=" * 80)
    
    print(f"📋 Configuración:")
    print(f"   ROOT_URLCONF: {settings.ROOT_URLCONF}")
    print(f"   TENANT_URLCONF: {settings.TENANT_URLCONF}")
    
    # Verificar orden de middleware
    middleware = settings.MIDDLEWARE
    tenant_middleware_idx = next((i for i, m in enumerate(middleware) if 'TenantMainMiddleware' in m), None)
    if tenant_middleware_idx is not None:
        print(f"[OK] TenantMainMiddleware en posición {tenant_middleware_idx}")
    else:
        print(f"[ERROR] TenantMainMiddleware NO encontrado en MIDDLEWARE")
        return 1
    
    # PASO 6: Simular activación completa (POST)
    print("\n" + "=" * 80)
    print("PASO 6: Simular Activación Completa (POST)")
    print("=" * 80)
    
    try:
        # Obtener CSRF token
        csrf_response = client.get(f'/activate/?token={token}')
        csrf_token = csrf_response.cookies.get('csrftoken')
        
        if csrf_token:
            print(f"[OK] CSRF token obtenido")
        else:
            print(f"[WARNING]  CSRF token no encontrado (puede ser normal en tests)")
        
        # Simular POST de activación
        post_data = {
            'password1': 'TestPassword123!',
            'password2': 'TestPassword123!',
        }
        
        if csrf_token:
            post_data['csrfmiddlewaretoken'] = csrf_token.value
        
        response_post = client.post(
            f'/activate/?token={token}',
            data=post_data,
            HTTP_HOST=test_domain,
            follow=False  # No seguir redirects automáticamente
        )
        
        print(f"\n📋 Response POST:")
        print(f"   Status: {response_post.status_code}")
        print(f"   Location: {response_post.get('Location', 'N/A')}")
        
        if response_post.status_code == 302:
            location = response_post.get('Location', '')
            print(f"\n🔍 Análisis del Redirect:")
            print(f"   Location: {location}")
            
            # Verificar si el redirect apunta a una ruta pública o privada
            if location.startswith('/dashboard/'):
                print(f"   [OK] Redirect a ruta privada (/dashboard/)")
            elif location.startswith('/console/'):
                print(f"   [ERROR] PROBLEMA: Redirect a ruta pública (/console/)")
                print(f"   [WARNING]  El tenant está siendo direccionado al URLConf público")
                return 1
            elif 'sintel.net.co' in location and '/console/' in location:
                print(f"   [ERROR] PROBLEMA: Redirect a dominio público con ruta /console/")
                print(f"   [WARNING]  El tenant está siendo direccionado al URLConf público")
                return 1
            else:
                print(f"   [WARNING]  Redirect a: {location}")
        
    except Exception as e:
        print(f"[ERROR] Error al simular activación: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # PASO 7: Verificar después de activación
    print("\n" + "=" * 80)
    print("PASO 7: Verificar Estado Después de Activación")
    print("=" * 80)
    
    with schema_context('public'):
        user_check = User.objects.get(email=test_email)
        print(f"[OK] Usuario verificado: {user_check.email}")
        print(f"   Password usable: {user_check.has_usable_password()}")
        print(f"   Is active: {user_check.is_active}")
        
        membership = TenantMembership.objects.filter(user=user_check, client=tenant).first()
        if membership:
            print(f"[OK] Membresía encontrada: rol={membership.rol}, is_active={membership.is_active}")
        else:
            print(f"[ERROR] Membresía NO encontrada")
            return 1
    
    # PASO 8: Verificar acceso a dashboard después de login
    print("\n" + "=" * 80)
    print("PASO 8: Verificar Acceso a Dashboard Después de Login")
    print("=" * 80)
    
    # Login con las credenciales
    login_success = client.login(username=test_email, password='TestPassword123!')
    if login_success:
        print(f"[OK] Login exitoso")
        
        # Intentar acceder a dashboard
        dashboard_response = client.get('/dashboard/', HTTP_HOST=test_domain)
        print(f"\n📋 Dashboard Response:")
        print(f"   Status: {dashboard_response.status_code}")
        print(f"   URLConf: {getattr(dashboard_response, 'urlconf', 'N/A')}")
        
        if dashboard_response.status_code == 200:
            print(f"[OK] Dashboard accesible (200 OK)")
        elif dashboard_response.status_code == 404:
            print(f"[ERROR] Dashboard NO encontrado (404)")
            print(f"   [WARNING]  Posible problema: URLConf incorrecto")
            return 1
        else:
            print(f"[WARNING]  Status inesperado: {dashboard_response.status_code}")
    else:
        print(f"[ERROR] Login fallido")
        return 1
    
    print("\n" + "=" * 80)
    print("[OK] DEBUG COMPLETADO")
    print("=" * 80)
    print("\n[IDEA] Si todos los pasos pasaron, el flujo está funcionando correctamente.")
    print("   Si algún paso falló, revisa el error específico arriba.")
    
    return 0

if __name__ == '__main__':
    sys.exit(debug_step_by_step())
