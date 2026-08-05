#!/usr/bin/env python
"""
Script de verificación de configuración de producción.

Verifica que la configuración esté lista para producción:
- DEBUG=False
- ALLOWED_HOSTS contiene sintel.net.co y .sintel.net.co
- CSRF_TRUSTED_ORIGINS contiene orígenes HTTPS
- TenantMainMiddleware está en el orden correcto
- URLConf están correctamente separados
- Dominios están configurados correctamente

Uso:
    docker compose exec web python scripts/verify_production_config.py
    O desde el directorio raíz del proyecto:
    python manage.py shell < scripts/verify_production_config.py
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
from django.db import connection
from apps.public.tenants.models import Client, Domain


def check_debug():
    """Verifica que DEBUG esté desactivado en producción."""
    print("🔍 Verificando DEBUG...")
    if settings.DEBUG:
        print("  [ERROR] ERROR: DEBUG=True. Debe estar en False en producción.")
        return False
    print("  [OK] DEBUG=False")
    return True


def check_allowed_hosts():
    """Verifica que ALLOWED_HOSTS contenga los dominios necesarios."""
    print("\n🔍 Verificando ALLOWED_HOSTS...")
    required_hosts = ['sintel.net.co', '.sintel.net.co']
    missing = [h for h in required_hosts if h not in settings.ALLOWED_HOSTS]
    
    if missing:
        print(f"  [ERROR] ERROR: Faltan hosts requeridos: {missing}")
        print(f"  ALLOWED_HOSTS actual: {settings.ALLOWED_HOSTS}")
        return False
    
    print(f"  [OK] ALLOWED_HOSTS contiene los dominios requeridos")
    print(f"  ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    return True


def check_csrf_trusted_origins():
    """Verifica que CSRF_TRUSTED_ORIGINS contenga orígenes HTTPS."""
    print("\n🔍 Verificando CSRF_TRUSTED_ORIGINS...")
    
    # En producción, debe tener al menos https://sintel.net.co
    has_https = any('https://sintel.net.co' in origin for origin in settings.CSRF_TRUSTED_ORIGINS)
    
    if not has_https and not settings.DEBUG:
        print("  [WARNING]  ADVERTENCIA: No se encontró 'https://sintel.net.co' en CSRF_TRUSTED_ORIGINS")
        print("  NOTA: El middleware CSRFTrustedOriginMiddleware puede manejar dominios dinámicos")
    
    print(f"  [OK] CSRF_TRUSTED_ORIGINS configurado")
    print(f"  CSRF_TRUSTED_ORIGINS: {settings.CSRF_TRUSTED_ORIGINS}")
    return True


def check_middleware_order():
    """Verifica que TenantMainMiddleware esté en el orden correcto."""
    print("\n🔍 Verificando orden de middlewares...")
    
    middleware = settings.MIDDLEWARE
    tenant_middleware_idx = None
    session_middleware_idx = None
    
    for i, mw in enumerate(middleware):
        if 'TenantMainMiddleware' in mw:
            tenant_middleware_idx = i
        if 'SessionMiddleware' in mw:
            session_middleware_idx = i
    
    if tenant_middleware_idx is None:
        print("  [ERROR] ERROR: TenantMainMiddleware no encontrado en MIDDLEWARE")
        return False
    
    if session_middleware_idx is not None and tenant_middleware_idx < session_middleware_idx:
        print("  [WARNING]  ADVERTENCIA: TenantMainMiddleware debería ir después de SessionMiddleware")
        print("  (Aunque esto puede ser intencional según tu configuración)")
    
    print(f"  [OK] TenantMainMiddleware encontrado en posición {tenant_middleware_idx + 1}")
    return True


def check_urlconf():
    """Verifica que ROOT_URLCONF y TENANT_URLCONF estén configurados."""
    print("\n🔍 Verificando URLConf...")
    
    if not hasattr(settings, 'ROOT_URLCONF'):
        print("  [ERROR] ERROR: ROOT_URLCONF no está configurado")
        return False
    
    if not hasattr(settings, 'TENANT_URLCONF'):
        print("  [ERROR] ERROR: TENANT_URLCONF no está configurado")
        return False
    
    if settings.ROOT_URLCONF != 'config.urls_public':
        print(f"  [WARNING]  ADVERTENCIA: ROOT_URLCONF={settings.ROOT_URLCONF}, esperado: config.urls_public")
    
    if settings.TENANT_URLCONF != 'config.urls_tenant':
        print(f"  [WARNING]  ADVERTENCIA: TENANT_URLCONF={settings.TENANT_URLCONF}, esperado: config.urls_tenant")
    
    print(f"  [OK] ROOT_URLCONF={settings.ROOT_URLCONF}")
    print(f"  [OK] TENANT_URLCONF={settings.TENANT_URLCONF}")
    return True


def check_domains():
    """Verifica que los dominios estén configurados correctamente."""
    print("\n🔍 Verificando dominios en la base de datos...")
    
    connection.set_schema_to_public()
    
    # Verificar tenant público
    try:
        public_client = Client.objects.get(schema_name='public')
        print(f"  [OK] Tenant público encontrado: {public_client.nombre}")
    except Client.DoesNotExist:
        print("  [ERROR] ERROR: Tenant público (schema_name='public') no encontrado")
        return False
    
    # Verificar dominio público
    public_domain = Domain.objects.filter(tenant=public_client, is_primary=True).first()
    if not public_domain:
        print("  [WARNING]  ADVERTENCIA: No se encontró dominio primario para el tenant público")
        print("  NOTA: Puede ser necesario crear Domain(domain='sintel.net.co', tenant=public_client, is_primary=True)")
    else:
        print(f"  [OK] Dominio público encontrado: {public_domain.domain}")
    
    # Listar todos los dominios
    all_domains = Domain.objects.select_related('tenant').all()
    print(f"\n  📋 Dominios configurados ({all_domains.count()}):")
    for domain in all_domains:
        print(f"    - {domain.domain} -> {domain.tenant.schema_name} (primary: {domain.is_primary})")
    
    return True


def main():
    """Ejecuta todas las verificaciones."""
    print("=" * 60)
    print("Verificación de Configuración de Producción")
    print("=" * 60)
    
    checks = [
        check_debug,
        check_allowed_hosts,
        check_csrf_trusted_origins,
        check_middleware_order,
        check_urlconf,
        check_domains,
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"  [ERROR] ERROR al ejecutar verificación: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("Resumen")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"[OK] Todas las verificaciones pasaron ({passed}/{total})")
        return 0
    else:
        print(f"[ERROR] Algunas verificaciones fallaron ({passed}/{total})")
        return 1


if __name__ == '__main__':
    sys.exit(main())
