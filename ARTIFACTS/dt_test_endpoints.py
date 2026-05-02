"""
Script de prueba para verificar endpoints DataTables.

Ejecutar con: python manage.py shell < ARTIFACTS/dt_test_endpoints.py
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from rest_framework.test import force_authenticate
import json

User = get_user_model()

print("=" * 70)
print("🧪 PRUEBAS DE ENDPOINTS DATATABLES")
print("=" * 70)

# Crear request factory
factory = RequestFactory()

# Datos de prueba estándar para DataTables
test_data = {
    "draw": 1,
    "start": 0,
    "length": 10,
    "search": {"value": "", "regex": False},
    "order": [{"column": 0, "dir": "asc"}],
    "columns": [
        {"data": "codigo", "name": "codigo", "searchable": True, "orderable": True},
        {"data": "nombre", "name": "nombre", "searchable": True, "orderable": True},
    ],
}

# Obtener usuario de prueba
try:
    user = User.objects.first()
    if not user:
        print("[WARNING]  No hay usuarios en la base de datos. Creando usuario de prueba...")
        user = User.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='testpass123'
        )
    print(f"[OK] Usuario de prueba: {user.username}\n")
except Exception as e:
    print(f"[ERROR] Error obteniendo usuario: {e}")
    exit(1)

# Lista de endpoints a probar
endpoints = [
    {
        "name": "Contabilidad - Cuentas Contables",
        "url": "/api/v1/contabilidad/dt/cuentas-contables/",
        "function": None,  # Se importará dinámicamente
        "module": "apps.tenant.contabilidad.api.datatables",
        "func_name": "cuentas_contables_dt",
    },
    {
        "name": "Contabilidad - Asientos Contables",
        "url": "/api/v1/contabilidad/dt/asientos-contables/",
        "function": None,
        "module": "apps.tenant.contabilidad.api.datatables",
        "func_name": "asientos_contables_dt",
    },
    {
        "name": "Inventario - Catálogo",
        "url": "/api/v1/inventario/dt/catalogo/",
        "function": None,
        "module": "apps.tenant.inventario.api.datatables",
        "func_name": "catalogo_items_dt",
    },
    {
        "name": "Inventario - Activos Fijos",
        "url": "/api/v1/inventario/dt/activos-fijos/",
        "function": None,
        "module": "apps.tenant.inventario.api.datatables",
        "func_name": "activos_fijos_dt",
    },
    {
        "name": "Inventario - Movimientos",
        "url": "/api/v1/inventario/dt/movimientos/",
        "function": None,
        "module": "apps.tenant.inventario.api.datatables",
        "func_name": "movimientos_inventario_dt",
    },
    {
        "name": "Clientes",
        "url": "/api/v1/clientes/dt/clientes/",
        "function": None,
        "module": "apps.tenant.clientes.api.datatables",
        "func_name": "clientes_dt",
    },
]

# Importar funciones dinámicamente
for endpoint in endpoints:
    try:
        module = __import__(endpoint["module"], fromlist=[endpoint["func_name"]])
        endpoint["function"] = getattr(module, endpoint["func_name"])
        print(f"[OK] Importado: {endpoint['name']}")
    except Exception as e:
        print(f"[ERROR] Error importando {endpoint['name']}: {e}")
        endpoint["function"] = None

print("\n" + "=" * 70)
print("[CHART] PRUEBAS DE ENDPOINTS")
print("=" * 70 + "\n")

results = []

for endpoint in endpoints:
    if not endpoint["function"]:
        results.append({
            "name": endpoint["name"],
            "status": "SKIP",
            "error": "Función no disponible"
        })
        continue

    print(f"🔄 Probando: {endpoint['name']}")
    print(f"   URL: {endpoint['url']}")

    try:
        # Crear request
        request = factory.post(
            endpoint['url'],
            data=json.dumps(test_data),
            content_type='application/json',
        )

        # Autenticar
        force_authenticate(request, user=user)
        request.META['HTTP_X_CSRFTOKEN'] = 'test-csrf-token'

        # Llamar endpoint
        response = endpoint["function"](request)

        # Verificar respuesta
        if response.status_code == 200:
            response_data = json.loads(response.content.decode('utf-8'))
            
            # Verificar contrato DataTables
            required_keys = ['draw', 'recordsTotal', 'recordsFiltered', 'data']
            missing_keys = [key for key in required_keys if key not in response_data]
            
            if missing_keys:
                print(f"   [ERROR] Faltan claves: {missing_keys}")
                results.append({
                    "name": endpoint["name"],
                    "status": "FAIL",
                    "error": f"Faltan claves: {missing_keys}"
                })
            else:
                print(f"   [OK] Status: {response.status_code}")
                print(f"   [OK] draw: {response_data.get('draw')}")
                print(f"   [OK] recordsTotal: {response_data.get('recordsTotal')}")
                print(f"   [OK] recordsFiltered: {response_data.get('recordsFiltered')}")
                print(f"   [OK] data: {len(response_data.get('data', []))} registros")
                results.append({
                    "name": endpoint["name"],
                    "status": "PASS",
                    "recordsTotal": response_data.get('recordsTotal'),
                    "recordsFiltered": response_data.get('recordsFiltered'),
                })
        else:
            print(f"   [ERROR] Status: {response.status_code}")
            print(f"   [ERROR] Contenido: {response.content.decode('utf-8')[:200]}")
            results.append({
                "name": endpoint["name"],
                "status": "FAIL",
                "error": f"Status {response.status_code}"
            })

    except Exception as e:
        print(f"   [ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        results.append({
            "name": endpoint["name"],
            "status": "ERROR",
            "error": str(e)
        })

    print()

# Resumen
print("=" * 70)
print("📋 RESUMEN DE PRUEBAS")
print("=" * 70)

passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] in ["FAIL", "ERROR"])
skipped = sum(1 for r in results if r["status"] == "SKIP")

print(f"\n[OK] Pasadas: {passed}")
print(f"[ERROR] Fallidas: {failed}")
print(f"⏭️  Omitidas: {skipped}")

if failed > 0:
    print("\n[ERROR] Endpoints con errores:")
    for r in results:
        if r["status"] in ["FAIL", "ERROR"]:
            print(f"   - {r['name']}: {r.get('error', 'Error desconocido')}")

print("\n" + "=" * 70)
