#!/usr/bin/env python
"""
Script para verificar el acceso a un tenant desde la perspectiva del middleware.
Simula cómo django-tenants identifica el tenant desde el hostname.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from django_tenants.utils import get_public_schema_name, schema_context
from apps.public.tenants.models import Domain
from django_tenants.middleware.main import TenantMainMiddleware


def get_hostname_from_request(hostname):
    """Simula cómo django-tenants extrae el hostname de una request."""
    factory = RequestFactory()
    request = factory.get('/', HTTP_HOST=hostname)
    
    # django-tenants usa request.get_host() que incluye el puerto si está presente
    # pero luego lo normaliza quitando el puerto
    host = request.get_host()
    
    # django-tenants normaliza quitando el puerto
    if ':' in host:
        host = host.split(':')[0]
    
    return host


def check_domain_resolution(hostname):
    """Verifica si un hostname puede resolverse a un tenant."""
    print(f"\n{'='*80}")
    print(f"VERIFICACIÓN DE ACCESO PARA: {hostname}")
    print(f"{'='*80}\n")
    
    # Normalizar hostname (quitar puerto si existe)
    normalized_host = get_hostname_from_request(hostname)
    print(f"Hostname normalizado: {normalized_host}")
    
    with schema_context(get_public_schema_name()):
        # Buscar dominio en la base de datos
        domain = Domain.objects.filter(domain=normalized_host).first()
        
        if domain:
            print(f"\n[OK] Dominio encontrado en BD:")
            print(f"   - Domain: {domain.domain}")
            print(f"   - Tenant: {domain.tenant.schema_name} ({domain.tenant.nombre})")
            print(f"   - Primary: {domain.is_primary}")
            print(f"   - Is Active: {domain.tenant.is_active}")
            
            if not domain.tenant.is_active:
                print(f"\n[WARNING]  ADVERTENCIA: El tenant está SUSPENDIDO (is_active=False)")
                print(f"   El middleware TenantSecurityMiddleware bloqueará el acceso")
            
            return True
        else:
            print(f"\n[ERROR] Dominio NO encontrado en BD")
            print(f"   El middleware TenantMainMiddleware NO podrá identificar el tenant")
            print(f"   Se mostrará un error 404: 'No tenant for hostname {normalized_host}'")
            
            # Mostrar dominios similares
            similar = Domain.objects.filter(domain__icontains=normalized_host.split('.')[0])
            if similar.exists():
                print(f"\n   Dominios similares encontrados:")
                for d in similar:
                    print(f"   - {d.domain} (tenant: {d.tenant.schema_name})")
            
            return False


if __name__ == '__main__':
    # Ejemplo de uso: Verificar un dominio específico
    # Cambiar 'ejemplo.sintel.com' por el dominio que desees verificar
    DOMAIN_TO_CHECK = 'ejemplo.sintel.com'  # Cambiar según necesidad
    
    check_domain_resolution(DOMAIN_TO_CHECK)
    
    # Verificar con puerto (si se proporciona)
    check_domain_resolution(f'{DOMAIN_TO_CHECK.split(":")[0]}:80')
    check_domain_resolution(f'{DOMAIN_TO_CHECK.split(":")[0]}:8000')
