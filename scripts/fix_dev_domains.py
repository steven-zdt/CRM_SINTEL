#!/usr/bin/env python
"""
Script de reparación de dominios en desarrollo.

Este script corrige los dominios existentes que no tienen puerto en modo DEBUG,
agregando automáticamente el puerto configurado en APP_PORT.

Uso:
    python scripts/fix_dev_domains.py
    # o desde el contenedor:
    docker compose exec web python scripts/fix_dev_domains.py
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from apps.public.tenants.models import Client, Domain
from django_tenants.utils import get_public_schema_name

# Colores para output (ANSI)
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


def print_step(message):
    print(f"{GREEN}✅ {message}{NC}")


def print_warning(message):
    print(f"{YELLOW}⚠️  {message}{NC}")


def print_error(message):
    print(f"{RED}❌ {message}{NC}")


def print_info(message):
    print(f"{BLUE}ℹ️  {message}{NC}")


def fix_dev_domains():
    """
    Repara los dominios existentes agregando el puerto en modo DEBUG.
    """
    print("=" * 80)
    print("🔧 REPARACIÓN DE DOMINIOS EN DESARROLLO")
    print("=" * 80)
    print()
    
    # Verificar que estamos en modo DEBUG
    if not settings.DEBUG:
        print_warning("Este script solo debe ejecutarse en modo DEBUG (settings.DEBUG=True)")
        print_warning("En producción, los dominios no deben incluir puerto.")
        response = input("¿Deseas continuar de todas formas? (s/N): ").lower().strip()
        if response != 's':
            print_info("Operación cancelada.")
            return
    
    # Obtener puerto de la configuración
    app_port = getattr(settings, 'APP_PORT', '8000')
    if not app_port or app_port in ['80', '443']:
        print_warning(f"APP_PORT está configurado como '{app_port}' (puerto estándar)")
        print_warning("No se agregará puerto a los dominios (puertos 80/443 son implícitos)")
        return
    
    print_info(f"Puerto configurado: {app_port}")
    print_info("Buscando dominios sin puerto...")
    print()
    
    # Obtener schema público para excluirlo
    public_schema = get_public_schema_name()
    
    # Obtener todos los tenants privados
    tenants = Client.objects.exclude(schema_name=public_schema)
    
    if not tenants.exists():
        print_warning("No se encontraron tenants privados para reparar.")
        return
    
    corrected_count = 0
    skipped_count = 0
    error_count = 0
    
    for tenant in tenants:
        print_info(f"Procesando tenant: {tenant.nombre} (schema: {tenant.schema_name})")
        
        # Obtener todos los dominios del tenant
        domains = Domain.objects.filter(tenant=tenant)
        
        for domain in domains:
            # Verificar si el dominio ya tiene puerto
            if ':' in domain.domain:
                print(f"   ⏭️  Dominio '{domain.domain}' ya tiene puerto, omitiendo...")
                skipped_count += 1
                continue
            
            # Verificar si ya existe un dominio con puerto para este tenant
            domain_with_port = f"{domain.domain}:{app_port}"
            existing_domain = Domain.objects.filter(
                tenant=tenant,
                domain=domain_with_port
            ).first()
            
            if existing_domain:
                print(f"   ⏭️  Dominio '{domain_with_port}' ya existe, omitiendo...")
                skipped_count += 1
                continue
            
            # Crear nuevo dominio con puerto
            try:
                new_domain = Domain.objects.create(
                    domain=domain_with_port,
                    tenant=tenant,
                    is_primary=False  # El dominio principal es el sin puerto
                )
                print(f"   ✅ Dominio corregido: {domain.domain} -> {domain_with_port}")
                corrected_count += 1
            except Exception as e:
                print_error(f"   ❌ Error al crear dominio '{domain_with_port}': {e}")
                error_count += 1
        
        print()
    
    # Resumen
    print("=" * 80)
    print("📊 RESUMEN DE REPARACIÓN")
    print("=" * 80)
    print(f"✅ Dominios corregidos: {corrected_count}")
    print(f"⏭️  Dominios omitidos: {skipped_count}")
    if error_count > 0:
        print(f"❌ Errores: {error_count}")
    print()
    
    if corrected_count > 0:
        print_step(f"Reparación completada. {corrected_count} dominio(s) corregido(s).")
        print_info("Los dominios con puerto ahora son accesibles desde el navegador.")
    else:
        print_info("No se encontraron dominios que requieran corrección.")
    
    print()


if __name__ == "__main__":
    try:
        fix_dev_domains()
    except KeyboardInterrupt:
        print()
        print_warning("Operación cancelada por el usuario.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
