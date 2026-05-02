#!/usr/bin/env python
"""
Script de inicialización para crear el tenant público y asociar el dominio sintel.com.

[WARNING] IMPORTANTE: Este script debe ejecutarse SOLO una vez durante la configuración inicial.
Ejecuta las migraciones antes de usar este script.

Uso:
    python manage.py shell < scripts/setup_public_domain.py
    O ejecutar directamente:
    python scripts/setup_public_domain.py
    O desde Docker:
    docker exec -it crm_sintel-web-1 python scripts/setup_public_domain.py
"""

import os
import sys
import django

# 1. Calcular el directorio base (la raíz del proyecto /app)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 2. Inyectar la raíz en el path de Python
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# 3. Apuntar a los settings de SINTEL
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 4. Inicializar Django
django.setup()

from django_tenants.utils import get_public_schema_name
from apps.public.tenants.models import Client, Domain


def setup_public_tenant():
    """
    Crea el tenant público y asocia el dominio sintel.com si no existen.
    
    [WARNING] SEGURIDAD: Verifica que no exista antes de crear para evitar duplicados.
    """
    public_schema = get_public_schema_name()
    
    print(f"🔍 Verificando tenant público '{public_schema}'...")
    
    # Verificar si el tenant público ya existe
    try:
        public_tenant = Client.objects.get(schema_name=public_schema)
        print(f"[OK] Tenant público '{public_schema}' ya existe (ID: {public_tenant.id})")
    except Client.DoesNotExist:
        print(f"[NOTE] Creando tenant público '{public_schema}'...")
        public_tenant = Client.objects.create(
            schema_name=public_schema,
            nombre='SINTEL Public',  # [WARNING] CORRECCIÓN: El campo es 'nombre', no 'name'
            paid_until=None,
            on_trial=False
        )
        print(f"[OK] Tenant público '{public_schema}' creado exitosamente (ID: {public_tenant.id})")
    
    # Dominios permitidos para el esquema público
    allowed_domains = [
        'sintel.com',
        'localhost',
        '127.0.0.1',
        '0.0.0.0',
    ]
    
    print(f"\n🔍 Verificando dominios para '{public_schema}'...")
    
    for domain_name in allowed_domains:
        try:
            domain = Domain.objects.get(domain=domain_name)
            print(f"[OK] Dominio '{domain_name}' ya existe (ID: {domain.id}, Tenant: {domain.tenant.schema_name})")
            
            # Verificar que esté asociado al tenant público
            if domain.tenant != public_tenant:
                print(f"[WARNING]  ADVERTENCIA: Dominio '{domain_name}' está asociado a otro tenant ({domain.tenant.schema_name})")
                print(f"   Considera actualizar manualmente si es necesario.")
        except Domain.DoesNotExist:
            print(f"[NOTE] Creando dominio '{domain_name}' para tenant '{public_schema}'...")
            domain = Domain.objects.create(
                domain=domain_name,
                tenant=public_tenant,
                is_primary=(domain_name == 'sintel.com')  # sintel.com es el dominio principal
            )
            print(f"[OK] Dominio '{domain_name}' creado exitosamente (ID: {domain.id}, Primary: {domain.is_primary})")
    
    # Verificar que haya al menos un dominio primario
    primary_domains = Domain.objects.filter(tenant=public_tenant, is_primary=True)
    if not primary_domains.exists():
        print(f"\n[WARNING]  ADVERTENCIA: No hay dominio primario para '{public_schema}'")
        # Establecer sintel.com como primario si existe
        sintel_domain = Domain.objects.filter(domain='sintel.com', tenant=public_tenant).first()
        if sintel_domain:
            sintel_domain.is_primary = True
            sintel_domain.save()
            print(f"[OK] Dominio 'sintel.com' establecido como primario")
        else:
            # Si no existe sintel.com, establecer el primero disponible como primario
            first_domain = Domain.objects.filter(tenant=public_tenant).first()
            if first_domain:
                first_domain.is_primary = True
                first_domain.save()
                print(f"[OK] Dominio '{first_domain.domain}' establecido como primario")
    
    print(f"\n[OK] Configuración del tenant público completada")
    print(f"\n[CHART] Resumen:")
    print(f"   - Tenant: {public_tenant.schema_name} (ID: {public_tenant.id})")
    print(f"   - Nombre: {public_tenant.nombre}")  # [WARNING] CORRECCIÓN: El campo es 'nombre', no 'name'
    print(f"   - Dominios asociados: {Domain.objects.filter(tenant=public_tenant).count()}")
    
    # Listar todos los dominios
    print(f"\n📋 Dominios configurados:")
    for domain in Domain.objects.filter(tenant=public_tenant).order_by('-is_primary', 'domain'):
        primary_marker = "⭐ (PRIMARY)" if domain.is_primary else ""
        print(f"   - {domain.domain} {primary_marker}")
    
    return public_tenant


if __name__ == '__main__':
    try:
        setup_public_tenant()
        print(f"\n🎉 Script ejecutado exitosamente")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
