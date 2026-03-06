#!/usr/bin/env python
"""
Script para agregar el dominio sintel.com al tenant público.

Uso:
    docker compose exec web python scripts/add_sintel_domain.py
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

from django.db import connection
from apps.public.tenants.models import Client, Domain

def main():
    connection.set_schema_to_public()
    
    # Obtener tenant público
    try:
        public = Client.objects.get(schema_name='public')
        print(f"✅ Tenant público encontrado: {public.nombre}")
    except Client.DoesNotExist:
        print("❌ ERROR: Tenant público (schema_name='public') no encontrado")
        return 1
    
    # Crear o obtener dominio sintel.com
    # ⚠️ IMPORTANTE: En producción, sintel.com debe ser el dominio primario
    # En desarrollo, localhost puede ser primario, pero sintel.com debe existir
    domain, created = Domain.objects.get_or_create(
        domain='sintel.com',
        defaults={'tenant': public, 'is_primary': True}
    )
    
    if created:
        print(f"✅ Dominio 'sintel.com' creado para el tenant público (primary: {domain.is_primary})")
    else:
        # Si el dominio ya existe pero no es primario, actualizarlo
        if domain.tenant != public:
            print(f"⚠️  El dominio 'sintel.com' está asociado a otro tenant. Actualizando...")
            domain.tenant = public
            domain.is_primary = True
            domain.save()
            print(f"✅ Dominio 'sintel.com' actualizado para el tenant público (primary: {domain.is_primary})")
        elif not domain.is_primary:
            # Si no es primario, hacerlo primario (en producción debe ser primario)
            print(f"⚠️  El dominio 'sintel.com' no es primario. Actualizando a primario...")
            # Primero desactivar otros dominios primarios del mismo tenant
            Domain.objects.filter(tenant=public, is_primary=True).exclude(pk=domain.pk).update(is_primary=False)
            domain.is_primary = True
            domain.save()
            print(f"✅ Dominio 'sintel.com' actualizado como primario para el tenant público")
        else:
            print(f"✅ Dominio 'sintel.com' ya existe para el tenant público (primary: {domain.is_primary})")
    
    # Listar todos los dominios del tenant público
    domains = Domain.objects.filter(tenant=public).order_by('-is_primary', 'domain')
    print(f"\n📋 Dominios del tenant público ({domains.count()}):")
    for d in domains:
        print(f"  - {d.domain} (primary: {d.is_primary})")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
