"""
Script rápido para verificar que un tenant específico tiene dominio activo y acceso web.

Uso:
    python manage.py shell < scripts/verificar_tenant_web.py
    O ejecutar directamente en el shell de Django:
    exec(open('scripts/verificar_tenant_web.py').read())
"""
from django.test import Client
from django.db import connection
from django_tenants.utils import schema_exists
from django.conf import settings

from apps.public.tenants.models import Client, Domain, TenantMembership

# Configurar tenant a verificar (cambiar según necesidad)
SCHEMA_NAME = 'ejemplo'  # Cambiar por el schema_name del tenant a verificar

print("=" * 80)
print(f"🔍 VERIFICACIÓN DE TENANT: {SCHEMA_NAME}")
print("=" * 80)
print("")

try:
    # 1. Verificar que el tenant existe
    tenant = Client.objects.get(schema_name=SCHEMA_NAME)
    print(f"[OK] Tenant encontrado: {tenant.nombre}")
    print(f"   - Schema: {tenant.schema_name}")
    print(f"   - Activo: {tenant.is_active}")
    print("")
    
    # 2. Verificar esquema PostgreSQL
    if schema_exists(tenant.schema_name):
        print(f"[OK] Esquema PostgreSQL '{tenant.schema_name}' existe")
    else:
        print(f"[ERROR] Esquema PostgreSQL '{tenant.schema_name}' NO existe")
    print("")
    
    # 3. Verificar dominios
    domains = Domain.objects.filter(tenant=tenant)
    primary_domain = domains.filter(is_primary=True).first()
    
    if not domains.exists():
        print("[ERROR] NO tiene dominios asociados")
    else:
        print(f"[OK] Tiene {domains.count()} dominio(s):")
        for d in domains:
            primary_mark = " (PRIMARY)" if d.is_primary else ""
            print(f"   - {d.domain}{primary_mark}")
    print("")
    
    # 4. Verificar dominio principal
    if not primary_domain:
        print("[ERROR] NO tiene dominio principal (is_primary=True)")
    else:
        print(f"[OK] Dominio principal: {primary_domain.domain}")
        
        # Verificar formato
        expected_domain = f"{tenant.schema_name}.{settings.TENANT_DOMAIN_BASE}"
        if primary_domain.domain != expected_domain:
            print(f"[WARNING]  Formato: '{primary_domain.domain}' (esperado: '{expected_domain}')")
        else:
            print(f"[OK] Formato correcto: {expected_domain}")
    print("")
    
    # 5. Verificar membresía admin
    admin_membership = TenantMembership.objects.filter(
        client=tenant,
        is_primary_admin=True
    ).first()
    
    if not admin_membership:
        print("[ERROR] NO tiene administrador principal asignado")
    else:
        print(f"[OK] Administrador principal: {admin_membership.user.email}")
        print(f"   - Activo: {admin_membership.is_active}")
    print("")
    
    # 6. Probar acceso web
    if primary_domain:
        print("🌐 Probando acceso web...")
        try:
            test_client = Client(HTTP_HOST=primary_domain.domain)
            response = test_client.get('/', follow=False)
            
            if response.status_code == 404:
                print(f"[ERROR] Acceso web falla: HTTP 404 (tenant no encontrado)")
            elif response.status_code in [200, 302, 301]:
                print(f"[OK] Acceso web funciona: HTTP {response.status_code}")
            else:
                print(f"[WARNING]  Acceso web retorna: HTTP {response.status_code}")
        except Exception as e:
            print(f"[ERROR] Error al probar acceso web: {e}")
    else:
        print("[WARNING]  No se puede probar acceso web (no hay dominio principal)")
    
    print("")
    print("=" * 80)
    print("[OK] VERIFICACIÓN COMPLETADA")
    print("=" * 80)
    
except Client.DoesNotExist:
    print(f"[ERROR] Tenant '{SCHEMA_NAME}' no encontrado")
except Exception as e:
    print(f"[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()
