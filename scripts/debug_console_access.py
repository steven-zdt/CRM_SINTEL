#!/usr/bin/env python
"""
Script de diagnóstico para problemas de acceso a la consola.

Uso:
    docker compose exec web python scripts/debug_console_access.py
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
from django.contrib.auth import get_user_model
from django.urls import reverse, resolve
from django.conf import settings
from apps.public.tenants.models import Client as TenantClient, Domain

User = get_user_model()

def main():
    print("=" * 60)
    print("🔍 DIAGNÓSTICO DE ACCESO A CONSOLA")
    print("=" * 60)
    
    # 1. Verificar dominio público
    print("\n1. Verificando dominio público...")
    try:
        public = TenantClient.objects.get(schema_name='public')
        domain = Domain.objects.filter(tenant=public, domain='sintel.net.co').first()
        if domain:
            print(f"  [OK] Dominio sintel.net.co encontrado (primary: {domain.is_primary})")
        else:
            print("  [ERROR] Dominio sintel.net.co NO encontrado")
            print("     Ejecuta: python scripts/add_sintel_domain.py")
            return 1
    except Exception as e:
        print(f"  [ERROR] Error: {e}")
        return 1
    
    # 2. Verificar URLConf
    print("\n2. Verificando URLConf...")
    print(f"  ROOT_URLCONF: {settings.ROOT_URLCONF}")
    print(f"  TENANT_URLCONF: {settings.TENANT_URLCONF}")
    
    # 3. Verificar rutas
    print("\n3. Verificando rutas...")
    try:
        url = reverse('console:tenants-list')
        print(f"  [OK] URL encontrada: {url}")
        
        # Intentar resolver
        match = resolve(url)
        print(f"  [OK] Vista resuelta: {match.func.__name__}")
        print(f"  [OK] App name: {match.app_name}")
    except Exception as e:
        print(f"  [ERROR] Error resolviendo URL: {e}")
        return 1
    
    # 4. Verificar usuarios staff
    print("\n4. Verificando usuarios staff...")
    staff_users = User.objects.filter(is_staff=True, is_active=True)
    print(f"  Usuarios staff activos: {staff_users.count()}")
    if staff_users.exists():
        for user in staff_users[:3]:
            print(f"    - {user.email} (id: {user.id})")
    else:
        print("  [WARNING]  No hay usuarios staff. Crea uno con:")
        print("     python manage.py createsuperuser")
    
    # 5. Probar acceso sin autenticación
    print("\n5. Probando acceso sin autenticación...")
    client = Client()
    response = client.get('/console/tenants/', HTTP_HOST='sintel.net.co')
    print(f"  Status code: {response.status_code}")
    if response.status_code == 302:
        print(f"  [OK] Redirección a: {response.url}")
        print("     (Esperado: redirige a login si no estás autenticado)")
    elif response.status_code == 403:
        print("  [WARNING]  403 Forbidden (requiere autenticación/staff)")
    elif response.status_code == 404:
        print("  [ERROR] 404 Not Found - Problema con routing")
        print("     Verifica:")
        print("     - Que estés accediendo desde sintel.net.co (no localhost)")
        print("     - Que el dominio esté registrado en la BD")
        print("     - Que las URLs estén correctamente configuradas")
    else:
        print(f"  Status inesperado: {response.status_code}")
    
    # 6. Verificar ALLOWED_HOSTS
    print("\n6. Verificando ALLOWED_HOSTS...")
    allowed = settings.ALLOWED_HOSTS
    has_sintel = 'sintel.net.co' in allowed or '.sintel.net.co' in allowed
    print(f"  ALLOWED_HOSTS: {allowed}")
    if has_sintel:
        print("  [OK] sintel.net.co está permitido")
    else:
        print("  [ERROR] sintel.net.co NO está permitido")
    
    print("\n" + "=" * 60)
    print("📋 RESUMEN")
    print("=" * 60)
    print("Si obtienes 404:")
    print("  1. Verifica que accedas desde http://sintel.net.co (no localhost)")
    print("  2. Añade sintel.net.co a /etc/hosts si es local:")
    print("     127.0.0.1 sintel.net.co")
    print("  3. Inicia sesión como staff en http://sintel.net.co/admin/")
    print("  4. Luego accede a http://sintel.net.co/console/tenants/")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
