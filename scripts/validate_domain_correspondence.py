"""
Script de validación: Verifica que el dominio mostrado en DataTables
corresponde al dominio almacenado en la base de datos.

Uso:
    python manage.py shell < scripts/validate_domain_correspondence.py
"""

from django.db import connection
from apps.public.tenants.models import Client, Domain
from apps.public.tenants.api_admin.serializers import TenantListSerializer

# Asegurar que estamos en esquema public
connection.set_schema_to_public()

print("=" * 80)
print("VALIDACIÓN: Correspondencia entre Dominio en BD y Dominio en DataTables")
print("=" * 80)
print()

# Obtener todos los tenants con sus dominios
clients = Client.objects.prefetch_related('domains').all()
serializer = TenantListSerializer()

errors = []
warnings = []

for client in clients:
    print(f"📋 Client ID: {client.id}")
    print(f"   Schema: {client.schema_name}")
    print(f"   Nombre: {client.nombre}")
    
    # Obtener dominios desde BD
    domains_from_db = list(client.domains.all())
    primary_domains = [d for d in domains_from_db if d.is_primary]
    
    print(f"   Dominios en BD: {[d.domain for d in domains_from_db]}")
    if primary_domains:
        primary_domain_db = primary_domains[0].domain
        print(f"   [OK] Dominio Primary en BD: {primary_domain_db}")
    else:
        primary_domain_db = None
        print(f"   [WARNING]  No hay dominio primary en BD")
    
    # Obtener dominio desde serializer (como lo hace DataTables)
    serialized_data = serializer.to_representation(client)
    domain_from_serializer = serialized_data[3]  # Columna 3 es el dominio
    
    print(f"   Dominio en Serializer: {domain_from_serializer}")
    
    # Validar correspondencia
    if primary_domain_db:
        if domain_from_serializer == primary_domain_db:
            print(f"   [OK] CORRECTO: El dominio del serializer corresponde al de la BD")
        else:
            error_msg = f"   [ERROR] ERROR: El dominio del serializer ('{domain_from_serializer}') NO corresponde al primary de BD ('{primary_domain_db}')"
            print(error_msg)
            errors.append({
                'client_id': client.id,
                'schema_name': client.schema_name,
                'domain_db': primary_domain_db,
                'domain_serializer': domain_from_serializer
            })
    elif domain_from_serializer == "-":
        print(f"   [OK] CORRECTO: No hay dominio en BD y serializer retorna '-'")
    else:
        warning_msg = f"   [WARNING]  ADVERTENCIA: No hay dominio primary en BD pero serializer retorna '{domain_from_serializer}'"
        print(warning_msg)
        warnings.append({
            'client_id': client.id,
            'schema_name': client.schema_name,
            'domain_serializer': domain_from_serializer
        })
    
    print()

print("=" * 80)
print("RESUMEN")
print("=" * 80)
print(f"Total de tenants validados: {clients.count()}")
print(f"Errores encontrados: {len(errors)}")
print(f"Advertencias: {len(warnings)}")

if errors:
    print("\n[ERROR] ERRORES:")
    for error in errors:
        print(f"   - Client ID {error['client_id']} ({error['schema_name']}): "
              f"BD tiene '{error['domain_db']}' pero serializer retorna '{error['domain_serializer']}'")

if warnings:
    print("\n[WARNING]  ADVERTENCIAS:")
    for warning in warnings:
        print(f"   - Client ID {warning['client_id']} ({warning['schema_name']}): "
              f"No hay dominio primary en BD pero serializer retorna '{warning['domain_serializer']}'")

if not errors and not warnings:
    print("\n[OK] TODOS LOS DOMINIOS CORRESPONDEN CORRECTAMENTE")
    sys.exit(0)
else:
    print("\n[ERROR] SE ENCONTRARON DISCREPANCIAS")
    sys.exit(1)
