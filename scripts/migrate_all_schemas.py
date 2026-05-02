#!/usr/bin/env python
"""
Script idempotente para aplicar migraciones en todos los esquemas (public + tenants).

[WARNING] USO: Solo en desarrollo. En producción, usa migrate_schemas manualmente con control.

Uso:
    python scripts/migrate_all_schemas.py

O desde manage.py:
    python manage.py shell < scripts/migrate_all_schemas.py
"""
import os
import sys
import django

# Configurar Django
if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

from django.core.management import call_command
from django_tenants.utils import get_tenant_model
from django.db import connection


def migrate_all_schemas():
    """
    Aplica migraciones en public y todos los esquemas de tenant.
    
    Idempotente: puede ejecutarse múltiples veces sin efectos adversos.
    """
    print("=" * 60)
    print("APLICANDO MIGRACIONES EN TODOS LOS ESQUEMAS")
    print("=" * 60)
    
    # 1. Migraciones en esquema public (SHARED_APPS)
    print("\n[1/3] Aplicando migraciones en esquema 'public' (SHARED_APPS)...")
    try:
        call_command('migrate_schemas', '--shared', '--fake-initial', verbosity=1)
        print("[OK] Migraciones de SHARED_APPS aplicadas en 'public'")
    except Exception as e:
        print(f"✗ Error en migraciones de public: {e}")
        return False
    
    # 2. Migraciones en todos los esquemas de tenant (TENANT_APPS)
    print("\n[2/3] Aplicando migraciones en todos los esquemas de tenant (TENANT_APPS)...")
    try:
        call_command('migrate_schemas', '--tenant', '--fake-initial', verbosity=1)
        print("[OK] Migraciones de TENANT_APPS aplicadas en todos los tenants")
    except Exception as e:
        print(f"✗ Error en migraciones de tenants: {e}")
        return False
    
    # 3. Crear esquemas faltantes (si hay nuevos tenants registrados)
    print("\n[3/3] Verificando esquemas faltantes...")
    try:
        Tenant = get_tenant_model()
        tenants = Tenant.objects.exclude(schema_name='public')
        
        for tenant in tenants:
            # Verificar si el esquema existe
            with connection.cursor() as c:
                c.execute("""
                    SELECT EXISTS(
                        SELECT 1 FROM information_schema.schemata 
                        WHERE schema_name = %s
                    )
                """, [tenant.schema_name])
                exists = c.fetchone()[0]
                
                if not exists:
                    print(f"  → Creando esquema faltante: {tenant.schema_name}")
                    tenant.save()  # django-tenants crea el esquema automáticamente
        
        call_command('create_missing_schemas', verbosity=1)
        print("[OK] Esquemas verificados/creados")
    except Exception as e:
        print(f"⚠ Advertencia al verificar esquemas: {e}")
        # No es crítico, continuar
    
    print("\n" + "=" * 60)
    print("[OK] MIGRACIONES COMPLETADAS")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = migrate_all_schemas()
    sys.exit(0 if success else 1)
