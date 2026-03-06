#!/usr/bin/env python
"""
Helper seguro para ejecutar migraciones de tenants.

Acepta variable de entorno TENANTS:
- TENANTS=all → ejecuta `migrate_schemas --tenant --fake-initial`
- TENANTS=<schema_name> → ejecuta `migrate_schemas --schema=<schema_name> --fake-initial`

Uso:
    TENANTS=all python scripts/safe_migrate_tenants.py
    TENANTS=mi_empresa python scripts/safe_migrate_tenants.py
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management import call_command
from django.core.management.base import CommandError


def main():
    """Función principal."""
    tenants_mode = os.environ.get('TENANTS', 'all').strip()
    
    if tenants_mode == 'all':
        print("🔄 Aplicando migraciones de tenant (todos los tenants)...")
        try:
            call_command('migrate_schemas', '--tenant', '--fake-initial', verbosity=1)
            print("✅ Migraciones de tenant aplicadas")
            return 0
        except CommandError as e:
            print(f"❌ Error al aplicar migraciones de tenant: {e}")
            return 1
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            return 1
    else:
        # Modo específico: migrar un schema en particular
        schema_name = tenants_mode
        print(f"🔄 Aplicando migraciones de tenant (schema: {schema_name})...")
        try:
            call_command('migrate_schemas', '--schema', schema_name, '--fake-initial', verbosity=1)
            print(f"✅ Migraciones de tenant aplicadas para schema: {schema_name}")
            return 0
        except CommandError as e:
            print(f"❌ Error al aplicar migraciones de tenant para schema {schema_name}: {e}")
            return 1
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
