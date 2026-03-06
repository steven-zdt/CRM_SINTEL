"""
Script de prueba para verificar el endpoint DataTables de Facturas.

Ejecutar con: python manage.py shell < ARTIFACTS/dt_test_script.py
O desde shell: exec(open('ARTIFACTS/dt_test_script.py').read())
"""

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from rest_framework.test import force_authenticate
from apps.tenant.facturas.api.datatables import facturas_dt
from apps.tenant.facturas.models import Factura
import json

User = get_user_model()

print("=" * 60)
print("🧪 Prueba del Endpoint DataTables Facturas")
print("=" * 60)

# Crear request factory
factory = RequestFactory()

# Crear request POST simulado
data = {
    "draw": 1,
    "start": 0,
    "length": 10,
    "search": {"value": "", "regex": False},
    "order": [{"column": 1, "dir": "desc"}],
    "columns": [
        {"data": "numero", "name": "numero", "searchable": True, "orderable": True},
        {"data": "fecha_emision", "name": "fecha_emision", "searchable": False, "orderable": True},
        {"data": "naturaleza", "name": "naturaleza", "searchable": False, "orderable": True},
        {"data": "emisor", "name": "emisor_razon_social", "searchable": True, "orderable": True},
        {"data": "receptor", "name": "receptor_razon_social", "searchable": True, "orderable": True},
        {"data": "total", "name": "total", "searchable": False, "orderable": True},
        {"data": "cufe", "name": "cufe", "searchable": True, "orderable": True},
    ],
}

request = factory.post(
    '/api/v1/facturas/dt/facturas/',
    data=json.dumps(data),
    content_type='application/json',
)

# Obtener un usuario (o crear uno de prueba si no existe)
try:
    user = User.objects.first()
    if not user:
        print("⚠️  No hay usuarios en la base de datos. Creando usuario de prueba...")
        user = User.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='testpass123'
        )
    print(f"✅ Usuario de prueba: {user.username}")
except Exception as e:
    print(f"❌ Error obteniendo usuario: {e}")
    exit(1)

# Autenticar request
force_authenticate(request, user=user)

# Agregar CSRF token (simulado)
request.META['HTTP_X_CSRFTOKEN'] = 'test-csrf-token'

print("\n📊 Datos de la petición:")
print(f"   - draw: {data['draw']}")
print(f"   - start: {data['start']}")
print(f"   - length: {data['length']}")
print(f"   - order: {data['order']}")

# Verificar que hay facturas en la base de datos
facturas_count = Factura.objects.count()
print(f"\n📦 Facturas en BD: {facturas_count}")

if facturas_count == 0:
    print("⚠️  No hay facturas en la base de datos. El endpoint funcionará pero retornará 0 registros.")

# Llamar al endpoint
print("\n🔄 Ejecutando endpoint...")
try:
    response = facturas_dt(request)
    print(f"✅ Status Code: {response.status_code}")
    
    if response.status_code == 200:
        response_data = json.loads(response.content.decode('utf-8'))
        print(f"\n📋 Respuesta DataTables:")
        print(f"   - draw: {response_data.get('draw')}")
        print(f"   - recordsTotal: {response_data.get('recordsTotal')}")
        print(f"   - recordsFiltered: {response_data.get('recordsFiltered')}")
        print(f"   - data: {len(response_data.get('data', []))} registros")
        
        # Verificar estructura de datos
        if response_data.get('data'):
            first_record = response_data['data'][0]
            print(f"\n📄 Primer registro:")
            print(f"   - id: {first_record.get('id')}")
            print(f"   - numero: {first_record.get('numero')}")
            print(f"   - fecha_emision: {first_record.get('fecha_emision')}")
            print(f"   - naturaleza: {first_record.get('naturaleza')}")
            print(f"   - emisor: {first_record.get('emisor')}")
            print(f"   - receptor: {first_record.get('receptor')}")
            print(f"   - total: {first_record.get('total')}")
            print(f"   - cufe: {first_record.get('cufe', 'N/A')[:20]}...")
        
        # Verificar contrato DataTables
        required_keys = ['draw', 'recordsTotal', 'recordsFiltered', 'data']
        missing_keys = [key for key in required_keys if key not in response_data]
        
        if missing_keys:
            print(f"\n❌ Faltan claves en la respuesta: {missing_keys}")
        else:
            print(f"\n✅ Contrato DataTables correcto (todas las claves presentes)")
            
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   Contenido: {response.content.decode('utf-8')}")
        
except Exception as e:
    print(f"❌ Error ejecutando endpoint: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ Prueba completada")
print("=" * 60)
