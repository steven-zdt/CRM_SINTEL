# Simple test script for DataTables endpoints
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from rest_framework.test import force_authenticate
import json

User = get_user_model()
factory = RequestFactory()

print("Testing DataTables endpoints...")

# Get user
user = User.objects.first()
if not user:
    user = User.objects.create_user(username='test', email='test@test.com', password='test123')

# Test endpoints
endpoints = [
    ('Contabilidad - Cuentas', 'apps.tenant.contabilidad.api.datatables', 'cuentas_contables_dt'),
    ('Contabilidad - Asientos', 'apps.tenant.contabilidad.api.datatables', 'asientos_contables_dt'),
    ('Inventario - Catalogo', 'apps.tenant.inventario.api.datatables', 'catalogo_items_dt'),
    ('Inventario - Activos', 'apps.tenant.inventario.api.datatables', 'activos_fijos_dt'),
    ('Inventario - Movimientos', 'apps.tenant.inventario.api.datatables', 'movimientos_inventario_dt'),
    ('Clientes', 'apps.tenant.clientes.api.datatables', 'clientes_dt'),
]

test_data = {
    "draw": 1, "start": 0, "length": 10,
    "search": {"value": "", "regex": False},
    "order": [{"column": 0, "dir": "asc"}],
    "columns": [{"data": "id", "name": "id", "searchable": True, "orderable": True}],
}

for name, module_path, func_name in endpoints:
    try:
        module = __import__(module_path, fromlist=[func_name])
        func = getattr(module, func_name)
        
        request = factory.post('/test/', data=json.dumps(test_data), content_type='application/json')
        force_authenticate(request, user=user)
        request.META['HTTP_X_CSRFTOKEN'] = 'test'
        
        response = func(request)
        if response.status_code == 200:
            data = json.loads(response.content.decode('utf-8'))
            if all(k in data for k in ['draw', 'recordsTotal', 'recordsFiltered', 'data']):
                print(f"OK: {name}")
            else:
                print(f"FAIL: {name} - Missing keys")
        else:
            print(f"FAIL: {name} - Status {response.status_code}")
    except Exception as e:
        print(f"ERROR: {name} - {e}")

print("Done!")
