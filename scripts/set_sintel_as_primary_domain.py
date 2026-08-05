#!/usr/bin/env python
"""
Script para establecer sintel.net.co como dominio principal y definitivo del tenant público.

Uso:
    docker compose exec web python scripts/set_sintel_as_primary_domain.py
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

from django.db import transaction
from django_tenants.utils import schema_context
from apps.public.tenants.models import Client, Domain


def main():
    """Establece sintel.net.co como dominio principal del tenant público."""
    print("=" * 60)
    print("🔧 ESTABLECIENDO sintel.net.co COMO DOMINIO PRINCIPAL")
    print("=" * 60)
    
    with schema_context('public'):
        # 1. Obtener tenant público
        try:
            public = Client.objects.get(schema_name='public')
            print(f"\n[OK] Tenant público encontrado: {public.nombre}")
        except Client.DoesNotExist:
            print("\n[ERROR] ERROR: Tenant público (schema_name='public') no encontrado")
            print("   Ejecuta primero: python manage.py setup_public_tenant")
            return 1
        
        # 2. Desactivar otros dominios primarios
        print("\n🔍 Desactivando otros dominios primarios...")
        other_primary = Domain.objects.filter(tenant=public, is_primary=True).exclude(domain='sintel.net.co')
        if other_primary.exists():
            for domain in other_primary:
                domain.is_primary = False
                domain.save(update_fields=['is_primary'])
                print(f"  [WARNING]  Dominio '{domain.domain}' ya no es primario")
        else:
            print("  [OK] No hay otros dominios primarios")
        
        # 3. Crear o actualizar sintel.net.co como primario
        print("\n🔍 Configurando sintel.net.co...")
        with transaction.atomic():
            domain, created = Domain.objects.get_or_create(
                domain='sintel.net.co',
                defaults={
                    'tenant': public,
                    'is_primary': True,
                }
            )
            
            if created:
                print(f"  [OK] Dominio 'sintel.net.co' creado como primario")
            else:
                # Actualizar si ya existe
                if domain.tenant != public:
                    print(f"  [WARNING]  Dominio 'sintel.net.co' estaba asociado a otro tenant. Actualizando...")
                    domain.tenant = public
                
                if not domain.is_primary:
                    print(f"  [WARNING]  Dominio 'sintel.net.co' no era primario. Actualizando...")
                    domain.is_primary = True
                
                domain.save()
                print(f"  [OK] Dominio 'sintel.net.co' actualizado como primario")
        
        # 4. Verificar resultado
        print("\n📋 Verificación final:")
        sintel = Domain.objects.get(domain='sintel.net.co', tenant=public)
        print(f"  [OK] Dominio: {sintel.domain}")
        print(f"  [OK] Tenant: {sintel.tenant.nombre}")
        print(f"  [OK] Primary: {sintel.is_primary}")
        
        # 5. Listar todos los dominios del tenant público
        print("\n📋 Todos los dominios del tenant público:")
        all_domains = Domain.objects.filter(tenant=public).order_by('-is_primary', 'domain')
        for d in all_domains:
            status = "⭐ PRIMARIO" if d.is_primary else "  "
            print(f"  {status} {d.domain}")
        
        print("\n" + "=" * 60)
        print("[OK] CONFIGURACIÓN COMPLETADA")
        print("=" * 60)
        print("\n[IDEA] Próximos pasos:")
        print("   1. Verifica que sintel.net.co apunte a tu servidor (DNS o /etc/hosts)")
        print("   2. Accede a http://sintel.net.co/ para el dominio público")
        print("   3. Accede a http://sintel.net.co/console/tenants/ para la consola")
        print("   4. Los tenants privados usarán subdominios: cliente.sintel.net.co")
        
        return 0


if __name__ == '__main__':
    sys.exit(main())
