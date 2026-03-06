"""
Script para verificar que el admin de tenant NO muestra modelos del esquema público.

Ejecutar:
    docker compose exec web python manage.py shell < scripts/verificar_admin_tenant.py
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.tenant.core.admin import tenant_admin_site
from django.contrib import admin
from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura

print("=" * 80)
print("VERIFICACIÓN DE AISLAMIENTO DEL ADMIN DE TENANT")
print("=" * 80)

# 1. Verificar modelos registrados en tenant_admin_site
print("\n1. MODELOS REGISTRADOS EN tenant_admin_site:")
print("-" * 80)
tenant_models = list(tenant_admin_site._registry.keys())
if tenant_models:
    for model in sorted(tenant_models, key=lambda m: m.__name__):
        print(f"  ✅ {model.__name__:30s} (app: {model._meta.app_label})")
else:
    print("  ⚠️  No hay modelos registrados")

# 2. Verificar que modelos públicos NO están registrados
print("\n2. VERIFICACIÓN: Modelos del esquema público NO deben estar registrados:")
print("-" * 80)
public_models = [
    ('Client', Client),
    ('Domain', Domain),
    ('TenantMembership', TenantMembership),
]

all_ok = True
for name, model in public_models:
    is_registered = tenant_admin_site.is_registered(model)
    status = "❌ VULNERABILIDAD" if is_registered else "✅ OK"
    print(f"  {status}: {name:20s} registrado = {is_registered}")
    if is_registered:
        all_ok = False

# 3. Verificar que modelos de tenant SÍ están registrados
print("\n3. VERIFICACIÓN: Modelos de tenant SÍ deben estar registrados:")
print("-" * 80)
tenant_test_models = [
    ('Empresa', Empresa),
    ('Factura', Factura),
]

for name, model in tenant_test_models:
    is_registered = tenant_admin_site.is_registered(model)
    status = "✅ OK" if is_registered else "❌ FALTA"
    print(f"  {status}: {name:20s} registrado = {is_registered}")
    if not is_registered:
        all_ok = False

# 4. Comparar con admin.site
print("\n4. COMPARACIÓN: Modelos en admin.site (esquema público):")
print("-" * 80)
public_admin_models = [
    m for m in admin.site._registry.keys() 
    if m._meta.app_label in ['tenants', 'accounts']
]
for model in sorted(public_admin_models, key=lambda m: m.__name__)[:10]:
    print(f"  - {model.__name__:30s} (app: {model._meta.app_label})")

# 5. Resumen
print("\n" + "=" * 80)
if all_ok:
    print("✅ RESULTADO: AISLAMIENTO CORRECTO")
    print("   - Modelos públicos NO aparecen en tenant_admin_site")
    print("   - Modelos de tenant SÍ aparecen en tenant_admin_site")
else:
    print("❌ RESULTADO: PROBLEMA DETECTADO")
    print("   - Hay modelos públicos en tenant_admin_site o faltan modelos de tenant")
print("=" * 80)
