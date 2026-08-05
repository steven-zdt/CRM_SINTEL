"""
Script para verificar si un tenant ha sido eliminado completamente de la base de datos.

Verifica:
1. Si existe el Client en la tabla tenants_client
2. Si existe el Domain en la tabla tenants_domain
3. Si existe el esquema en PostgreSQL
4. Si hay TenantMembership asociadas
5. Si hay datos en el esquema del tenant

Uso:
    python manage.py shell < scripts/verificar_eliminacion_tenant.py
    o
    python scripts/verificar_eliminacion_tenant.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django_tenants.utils import schema_exists, get_public_schema_name, schema_context
from apps.public.tenants.models import Client, Domain, TenantMembership

SCHEMA_NAME = 'ejemplo'  # Cambiar por el schema_name del tenant a verificar
DOMAIN_NAME = 'ejemplo.sintel.net.co'  # Cambiar por el dominio del tenant a verificar

print("\n" + "=" * 60)
print(f"🔍 VERIFICACIÓN: Eliminación del Tenant '{SCHEMA_NAME}'")
print("=" * 60)

# 1. Verificar Client
print(f"\n📋 PASO 1: Verificando Client (schema_name='{SCHEMA_NAME}')...")
try:
    client = Client.objects.get(schema_name=SCHEMA_NAME)
    print(f"[ERROR] ERROR: El Client '{SCHEMA_NAME}' AÚN EXISTE")
    print(f"   - ID: {client.pk}")
    print(f"   - Nombre: {client.nombre}")
    print(f"   - Activo: {client.is_active}")
    print(f"   - Creado: {client.created_on}")
    client_exists = True
except Client.DoesNotExist:
    print(f"[OK] El Client '{SCHEMA_NAME}' NO existe (eliminado correctamente)")
    client_exists = False

# 2. Verificar Domain
print(f"\n📋 PASO 2: Verificando Domain (domain='{DOMAIN_NAME}')...")
try:
    domain = Domain.objects.get(domain=DOMAIN_NAME)
    print(f"[ERROR] ERROR: El Domain '{DOMAIN_NAME}' AÚN EXISTE")
    print(f"   - ID: {domain.pk}")
    print(f"   - Tenant: {domain.tenant.schema_name if domain.tenant else 'None'}")
    print(f"   - Es principal: {domain.is_primary}")
    domain_exists = True
except Domain.DoesNotExist:
    print(f"[OK] El Domain '{DOMAIN_NAME}' NO existe (eliminado correctamente)")
    domain_exists = False

# 3. Verificar TenantMembership
print(f"\n📋 PASO 3: Verificando TenantMembership asociadas...")
if client_exists:
    memberships = TenantMembership.objects.filter(client=client)
    if memberships.exists():
        print(f"[ERROR] ERROR: Existen {memberships.count()} TenantMembership asociadas:")
        for m in memberships:
            print(f"   - Usuario: {m.user.email} ({m.user.username}) - Rol: {m.rol}")
        membership_exists = True
    else:
        print(f"[OK] No hay TenantMembership asociadas al tenant '{SCHEMA_NAME}'")
        membership_exists = False
else:
    # Si el client no existe, verificar si hay membresías huérfanas
    memberships = TenantMembership.objects.filter(client__schema_name=SCHEMA_NAME)
    if memberships.exists():
        print(f"[WARNING]  ADVERTENCIA: Existen {memberships.count()} TenantMembership huérfanas (client eliminado pero membresías quedaron):")
        for m in memberships:
            print(f"   - Usuario: {m.user.email} ({m.user.username}) - Rol: {m.rol}")
        membership_exists = True
    else:
        print(f"[OK] No hay TenantMembership asociadas al tenant '{SCHEMA_NAME}'")
        membership_exists = False

# 4. Verificar esquema en PostgreSQL
print(f"\n📋 PASO 4: Verificando esquema en PostgreSQL (schema='{SCHEMA_NAME}')...")
try:
    schema_exist = schema_exists(SCHEMA_NAME)
    if schema_exist:
        print(f"[ERROR] ERROR: El esquema '{SCHEMA_NAME}' AÚN EXISTE en PostgreSQL")
        
        # Intentar verificar si hay tablas en el esquema
        with schema_context(SCHEMA_NAME):
            try:
                # Obtener lista de tablas en el esquema
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = %s
                        ORDER BY table_name
                    """, [SCHEMA_NAME])
                    tables = cursor.fetchall()
                    
                    if tables:
                        print(f"   [WARNING]  El esquema contiene {len(tables)} tablas:")
                        for table in tables[:10]:  # Mostrar solo las primeras 10
                            print(f"      - {table[0]}")
                        if len(tables) > 10:
                            print(f"      ... y {len(tables) - 10} más")
                    else:
                        print(f"   [WARNING]  El esquema existe pero está vacío (sin tablas)")
            except Exception as e:
                print(f"   [WARNING]  No se pudo acceder al esquema: {e}")
        
        schema_exists_flag = True
    else:
        print(f"[OK] El esquema '{SCHEMA_NAME}' NO existe en PostgreSQL (eliminado correctamente)")
        schema_exists_flag = False
except Exception as e:
    print(f"[WARNING]  Error al verificar el esquema: {e}")
    schema_exists_flag = None

# 5. Verificar otros dominios relacionados
print(f"\n📋 PASO 5: Verificando otros dominios relacionados...")
related_domains = Domain.objects.filter(domain__icontains=f'{SCHEMA_NAME}.sintel')
if related_domains.exists():
    print(f"[WARNING]  ADVERTENCIA: Existen {related_domains.count()} dominios relacionados:")
    for d in related_domains:
        print(f"   - {d.domain} (tenant: {d.tenant.schema_name if d.tenant else 'None'})")
else:
    print(f"[OK] No hay otros dominios relacionados con '{SCHEMA_NAME}.sintel'")

# Resumen final
print("\n" + "=" * 60)
print("[CHART] RESUMEN DE VERIFICACIÓN")
print("=" * 60)

if client_exists or domain_exists or membership_exists or schema_exists_flag:
    print("[ERROR] EL TENANT NO HA SIDO ELIMINADO COMPLETAMENTE")
    print("\n📋 Estado actual:")
    print(f"   - Client existe: {'SÍ' if client_exists else 'NO'}")
    print(f"   - Domain existe: {'SÍ' if domain_exists else 'NO'}")
    print(f"   - TenantMembership existen: {'SÍ' if membership_exists else 'NO'}")
    print(f"   - Esquema en PostgreSQL existe: {'SÍ' if schema_exists_flag else 'NO' if schema_exists_flag is not None else 'ERROR'}")
    
    print("\n🔧 COMANDOS PARA ELIMINAR COMPLETAMENTE:")
    print("   python manage.py shell")
    print("   >>> from apps.public.tenants.models import Client, Domain, TenantMembership")
    print("   >>> from django_tenants.utils import schema_context")
    print("   >>> from django.db import connection")
    print("   >>>")
    if client_exists:
        print("   >>> # 1. Eliminar TenantMembership")
        print(f"   >>> client = Client.objects.get(schema_name='{SCHEMA_NAME}')")
        print("   >>> TenantMembership.objects.filter(client=client).delete()")
        print("   >>>")
        print("   >>> # 2. Eliminar Domain")
        print("   >>> Domain.objects.filter(tenant=client).delete()")
        print("   >>>")
        print("   >>> # 3. Eliminar Client (esto puede eliminar el esquema si auto_drop_schema=True)")
        print("   >>> client.delete()")
        print("   >>>")
    if schema_exists_flag:
        print("   >>> # 4. Eliminar esquema manualmente si aún existe")
        print("   >>> with connection.cursor() as cursor:")
        print("   ...     cursor.execute(f\"DROP SCHEMA IF EXISTS {SCHEMA_NAME} CASCADE;\")")
        print("   >>>")
    print("   >>> # 5. Verificar eliminación")
    print("   >>> from django_tenants.utils import schema_exists")
    print(f"   >>> print(f'Esquema existe: {{schema_exists(\"{SCHEMA_NAME}\")}}')")
else:
    print("[OK] EL TENANT HA SIDO ELIMINADO COMPLETAMENTE")
    print("\n📋 Verificación completa:")
    print("   [OK] Client eliminado")
    print("   [OK] Domain eliminado")
    print("   [OK] TenantMembership eliminadas")
    print("   [OK] Esquema en PostgreSQL eliminado")

print("=" * 60 + "\n")
