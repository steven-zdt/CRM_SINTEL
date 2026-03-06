"""
Script de diagnóstico para verificar que las URLs de gastos estén correctamente registradas.

Uso: python manage.py shell < scripts/verify_gastos_urls.py
O: python scripts/verify_gastos_urls.py (si está configurado como comando)
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.urls import reverse, NoReverseMatch
from django.conf import settings

print("=" * 80)
print("DIAGNÓSTICO DE URLs DE GASTOS")
print("=" * 80)

# 1. Verificar que la app esté en TENANT_APPS
print("\n1. Verificando TENANT_APPS...")
if 'apps.tenant.gastos' in settings.TENANT_APPS:
    print("   ✅ apps.tenant.gastos está en TENANT_APPS")
else:
    print("   ❌ ERROR: apps.tenant.gastos NO está en TENANT_APPS")
    print(f"   TENANT_APPS actual: {settings.TENANT_APPS}")

# 2. Verificar importación del ViewSet
print("\n2. Verificando importación de GastoViewSet...")
try:
    from apps.tenant.gastos.api.viewsets import GastoViewSet
    print("   ✅ GastoViewSet importado correctamente")
    print(f"   Queryset: {GastoViewSet.queryset}")
    print(f"   Basename esperado: 'gastos'")
except ImportError as e:
    print(f"   ❌ ERROR: No se pudo importar GastoViewSet: {e}")
    sys.exit(1)

# 3. Verificar que el router esté configurado
print("\n3. Verificando configuración del router...")
try:
    from apps.tenant.gastos.api.urls import router, urlpatterns
    print("   ✅ Router importado correctamente")
    print(f"   URLs generadas por router: {len(router.urls)}")
    for url in router.urls:
        print(f"      - {url.pattern} -> {url.name}")
    print(f"   urlpatterns: {len(urlpatterns)} URLs")
except Exception as e:
    print(f"   ❌ ERROR: No se pudo importar router: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. Verificar que las URLs estén en config/api_urls.py
print("\n4. Verificando registro en config/api_urls.py...")
try:
    from config.api_urls import urlpatterns as api_urlpatterns
    gastos_found = False
    for pattern in api_urlpatterns:
        if hasattr(pattern, 'pattern') and 'gastos' in str(pattern.pattern):
            gastos_found = True
            print(f"   ✅ URL encontrada: {pattern.pattern}")
            break
    if not gastos_found:
        print("   ❌ ERROR: No se encontró 'gastos' en config/api_urls.py")
except Exception as e:
    print(f"   ⚠️  ADVERTENCIA: No se pudo verificar config/api_urls.py: {e}")

# 5. Verificar acciones del ViewSet
print("\n5. Verificando acciones del ViewSet...")
actions = ['list', 'retrieve', 'create', 'destroy', 'summary', 'resoluciones', 'anular', 'datatables']
for action_name in actions:
    if hasattr(GastoViewSet, action_name):
        print(f"   ✅ Acción '{action_name}' encontrada")
    else:
        print(f"   ⚠️  Acción '{action_name}' no encontrada")

# 6. Intentar resolver URLs (requiere tenant activo)
print("\n6. Intentando resolver URLs (requiere tenant activo)...")
test_urls = [
    'gastos-list',
    'gastos-detail',
    'gastos-summary',
    'gastos-resoluciones',
]
for url_name in test_urls:
    try:
        # Intentar con namespace
        full_name = f'api:{url_name}'
        url = reverse(full_name, kwargs={'pk': 1} if 'detail' in url_name else {})
        print(f"   ✅ {full_name} -> {url}")
    except NoReverseMatch:
        try:
            # Intentar sin namespace
            url = reverse(url_name, kwargs={'pk': 1} if 'detail' in url_name else {})
            print(f"   ✅ {url_name} -> {url}")
        except NoReverseMatch as e:
            print(f"   ❌ No se pudo resolver '{url_name}': {e}")

print("\n" + "=" * 80)
print("DIAGNÓSTICO COMPLETADO")
print("=" * 80)
print("\nSi todas las verificaciones pasaron, las URLs deberían estar disponibles.")
print("Si hay errores, revisa los logs del servidor al iniciar.")
