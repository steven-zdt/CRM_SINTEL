#!/usr/bin/env python
"""
Script de verificación para acceso al dominio público (sintel.net.co).

Verifica:
1. Tenant público existe
2. Dominio sintel.net.co está registrado
3. ALLOWED_HOSTS incluye sintel.net.co
4. URLs públicas están configuradas
5. Middlewares están en orden correcto

Uso:
    docker compose exec web python scripts/verify_public_domain_access.py
"""
import os
import sys
from pathlib import Path

# Añadir el directorio raíz del proyecto al path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.urls import reverse, NoReverseMatch
from apps.public.tenants.models import Client, Domain


def check_public_tenant():
    """Verifica que el tenant público existe."""
    print("🔍 Verificando tenant público...")
    try:
        public = Client.objects.get(schema_name='public')
        print(f"  [OK] Tenant público encontrado: {public.nombre} (schema: {public.schema_name})")
        return public
    except Client.DoesNotExist:
        print("  [ERROR] ERROR: Tenant público (schema_name='public') no encontrado")
        print("     Ejecuta: python manage.py setup_public_tenant")
        return None


def check_public_domain(public):
    """Verifica que el dominio sintel.net.co está registrado."""
    print("\n🔍 Verificando dominio sintel.net.co...")
    try:
        domain = Domain.objects.get(domain='sintel.net.co', tenant=public)
        print(f"  [OK] Dominio 'sintel.net.co' encontrado:")
        print(f"     - Tenant: {domain.tenant.nombre}")
        print(f"     - Primary: {domain.is_primary}")
        return domain
    except Domain.DoesNotExist:
        print("  [ERROR] ERROR: Dominio 'sintel.net.co' no encontrado para el tenant público")
        print("     Ejecuta: python scripts/add_sintel_domain.py")
        return None


def check_allowed_hosts():
    """Verifica que ALLOWED_HOSTS incluye sintel.net.co."""
    print("\n🔍 Verificando ALLOWED_HOSTS...")
    allowed_hosts = settings.ALLOWED_HOSTS
    has_sintel = 'sintel.net.co' in allowed_hosts or '.sintel.net.co' in allowed_hosts
    
    if has_sintel:
        print(f"  [OK] ALLOWED_HOSTS incluye sintel.net.co")
        print(f"     ALLOWED_HOSTS: {allowed_hosts}")
    else:
        print(f"  [ERROR] ERROR: ALLOWED_HOSTS no incluye sintel.net.co")
        print(f"     ALLOWED_HOSTS actual: {allowed_hosts}")
        print("     Añade 'sintel.net.co' y '.sintel.net.co' a ALLOWED_HOSTS en config/settings.py")
    
    return has_sintel


def check_urlconf():
    """Verifica que las URLs públicas están configuradas."""
    print("\n🔍 Verificando URLConf público...")
    root_urlconf = settings.ROOT_URLCONF
    
    if root_urlconf == 'config.urls_public':
        print(f"  [OK] ROOT_URLCONF = '{root_urlconf}'")
    else:
        print(f"  [WARNING]  ROOT_URLCONF = '{root_urlconf}' (esperado: 'config.urls_public')")
    
    # Verificar que la ruta /console/tenants/ está disponible
    try:
        url = reverse('console:tenants-list')
        print(f"  [OK] Ruta /console/tenants/ disponible: {url}")
        return True
    except NoReverseMatch:
        print(f"  [ERROR] ERROR: Ruta /console/tenants/ no encontrada")
        print("     Verifica que config/urls_public.py incluye apps.public.console.urls")
        return False


def check_middleware_order():
    """Verifica que los middlewares están en orden correcto."""
    print("\n🔍 Verificando orden de middlewares...")
    middleware = settings.MIDDLEWARE
    
    # Verificar que ForceNoPortMiddleware está antes de TenantMainMiddleware
    try:
        force_no_port_idx = middleware.index('apps.public.core.middleware.ForceNoPortMiddleware')
        tenant_main_idx = middleware.index('django_tenants.middleware.main.TenantMainMiddleware')
        
        if force_no_port_idx < tenant_main_idx:
            print(f"  [OK] ForceNoPortMiddleware ({force_no_port_idx}) está antes de TenantMainMiddleware ({tenant_main_idx})")
        else:
            print(f"  [ERROR] ERROR: ForceNoPortMiddleware debe estar ANTES de TenantMainMiddleware")
            print(f"     ForceNoPortMiddleware: índice {force_no_port_idx}")
            print(f"     TenantMainMiddleware: índice {tenant_main_idx}")
            return False
    except ValueError as e:
        print(f"  [WARNING]  No se pudo verificar orden de middlewares: {e}")
        return False
    
    return True


def main():
    """Ejecuta todas las verificaciones."""
    print("=" * 60)
    print("🔍 VERIFICACIÓN DE ACCESO AL DOMINIO PÚBLICO (sintel.net.co)")
    print("=" * 60)
    
    # 1. Verificar tenant público
    public = check_public_tenant()
    if not public:
        return 1
    
    # 2. Verificar dominio sintel.net.co
    domain = check_public_domain(public)
    if not domain:
        return 1
    
    # 3. Verificar ALLOWED_HOSTS
    allowed_hosts_ok = check_allowed_hosts()
    
    # 4. Verificar URLConf
    urlconf_ok = check_urlconf()
    
    # 5. Verificar orden de middlewares
    middleware_ok = check_middleware_order()
    
    # Resumen
    print("\n" + "=" * 60)
    print("📋 RESUMEN DE VERIFICACIÓN")
    print("=" * 60)
    
    all_ok = all([public, domain, allowed_hosts_ok, urlconf_ok, middleware_ok])
    
    if all_ok:
        print("[OK] Todas las verificaciones pasaron correctamente")
        print("\n[IDEA] Si aún tienes problemas de acceso:")
        print("   1. Verifica que sintel.net.co apunta a tu servidor (DNS o /etc/hosts)")
        print("   2. Inicia sesión como usuario staff en http://sintel.net.co/admin/")
        print("   3. Accede a http://sintel.net.co/console/tenants/")
        print("   4. Verifica que las migraciones del esquema public están aplicadas:")
        print("      python manage.py migrate_schemas --shared")
        return 0
    else:
        print("[ERROR] Algunas verificaciones fallaron. Revisa los errores arriba.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
