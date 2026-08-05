"""
Script para agregar el dominio sintel.net.co al tenant público.

Uso:
    python manage.py shell < scripts/agregar_dominio_publico.py
    o
    python scripts/agregar_dominio_publico.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.public.tenants.models import Client, Domain

def agregar_dominio_publico():
    """Agrega el dominio sintel.net.co al tenant público."""
    try:
        # Obtener el tenant público
        tenant = Client.objects.get(schema_name='public')
        print(f"[OK] Tenant público encontrado: {tenant.nombre}")
        
        # Crear o actualizar el dominio sintel.net.co
        domain, created = Domain.objects.get_or_create(
            domain='sintel.net.co',
            defaults={
                'tenant': tenant,
                'is_primary': False,
            }
        )
        
        if created:
            print(f"[OK] Dominio 'sintel.net.co' creado para el tenant público")
        else:
            # Actualizar si estaba asignado a otro tenant
            if domain.tenant != tenant:
                domain.tenant = tenant
                domain.is_primary = False
                domain.save()
                print(f"[OK] Dominio 'sintel.net.co' actualizado para el tenant público")
            else:
                print(f"INFO:  Dominio 'sintel.net.co' ya existe para el tenant público")
        
        # Mostrar todos los dominios del tenant público
        print("\n📋 Dominios del tenant público:")
        for d in Domain.objects.filter(tenant=tenant):
            print(f"   - {d.domain} (primary: {d.is_primary})")
        
        return domain
        
    except Client.DoesNotExist:
        print("[ERROR] Error: El tenant público no existe. Ejecuta primero: python manage.py setup_public_tenant")
        return None
    except Exception as e:
        print(f"[ERROR] Error al agregar dominio: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    agregar_dominio_publico()
