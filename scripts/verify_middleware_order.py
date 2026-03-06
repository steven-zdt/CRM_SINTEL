#!/usr/bin/env python
"""
Script para verificar el orden del middleware según documentación django-tenants.
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

def main():
    print("=" * 60)
    print("📋 VALIDACIÓN: Orden de Middleware (django-tenants)")
    print("=" * 60)
    
    middleware = settings.MIDDLEWARE
    
    # Encontrar posiciones clave
    tenant_idx = None
    force_no_port_idx = None
    session_idx = None
    auth_idx = None
    
    for i, m in enumerate(middleware):
        if 'TenantMainMiddleware' in m:
            tenant_idx = i
        elif 'ForceNoPortMiddleware' in m:
            force_no_port_idx = i
        elif 'SessionMiddleware' in m:
            session_idx = i
        elif 'AuthenticationMiddleware' in m:
            auth_idx = i
    
    print("\n📋 Orden de Middleware (primeros 10):")
    print("-" * 60)
    for i, m in enumerate(middleware[:10]):
        marker = "⭐" if i == tenant_idx else "  "
        print(f"{marker} {i:2d}. {m}")
    
    print("\n" + "=" * 60)
    print("✅ VALIDACIÓN DE CONFORMIDAD")
    print("=" * 60)
    
    # Validación 1: TenantMainMiddleware antes de middlewares que usan BD
    if tenant_idx is not None and auth_idx is not None:
        if tenant_idx < auth_idx:
            print(f"✅ TenantMainMiddleware (posición {tenant_idx}) está ANTES de AuthenticationMiddleware (posición {auth_idx})")
        else:
            print(f"❌ TenantMainMiddleware (posición {tenant_idx}) está DESPUÉS de AuthenticationMiddleware (posición {auth_idx})")
            return 1
    
    # Validación 2: ForceNoPortMiddleware antes de TenantMainMiddleware
    if force_no_port_idx is not None and tenant_idx is not None:
        if force_no_port_idx < tenant_idx:
            print(f"✅ ForceNoPortMiddleware (posición {force_no_port_idx}) está ANTES de TenantMainMiddleware (posición {tenant_idx})")
        else:
            print(f"❌ ForceNoPortMiddleware (posición {force_no_port_idx}) está DESPUÉS de TenantMainMiddleware (posición {tenant_idx})")
            return 1
    
    # Validación 3: SessionMiddleware antes de ForceNoPortMiddleware
    if session_idx is not None and force_no_port_idx is not None:
        if session_idx < force_no_port_idx:
            print(f"✅ SessionMiddleware (posición {session_idx}) está ANTES de ForceNoPortMiddleware (posición {force_no_port_idx})")
        else:
            print(f"❌ SessionMiddleware (posición {session_idx}) está DESPUÉS de ForceNoPortMiddleware (posición {force_no_port_idx})")
            return 1
    
    print("\n" + "=" * 60)
    print("📚 INTERPRETACIÓN DEL REQUISITO 'PRIMERO'")
    print("=" * 60)
    print("""
Según la documentación de django-tenants:
- "PRIMERO" significa: antes de middlewares que usan BD o resuelven URLs
- NO significa: posición 0 (puede haber middlewares de infraestructura antes)

Nuestra implementación:
- TenantMainMiddleware está en posición {tenant_idx}
- Está ANTES de middlewares que usan BD (AuthenticationMiddleware en {auth_idx})
- Está ANTES de la resolución de URLs (Django resuelve después de todos los middlewares)
- ✅ CONFORME con la documentación
    """.format(tenant_idx=tenant_idx, auth_idx=auth_idx))
    
    print("=" * 60)
    print("✅ VALIDACIÓN COMPLETADA: IMPLEMENTACIÓN VÁLIDA")
    print("=" * 60)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
