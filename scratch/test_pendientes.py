import os
import sys
import django

# Añadir el directorio actual al path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.tenant.contabilidad.api.viewsets import DocumentosPendientesViewSet
from apps.public.tenants.models import Client
from django_tenants.utils import tenant_context
from rest_framework.test import APIRequestFactory

def test():
    try:
        tenant = Client.objects.get(schema_name='home')
        factory = APIRequestFactory()
        request = factory.get('/api/v1/contabilidad/pendientes/')
        
        with tenant_context(tenant):
            view = DocumentosPendientesViewSet.as_view({'get': 'list'})
            response = view(request)
            print(f'Status: {response.status_code}')
            if hasattr(response, 'data') and isinstance(response.data, list):
                print(f'Data length: {len(response.data)}')
                # Mostrar los primeros 2 items si existen
                for item in response.data[:2]:
                    print(f" - {item['tipo_doc']}: {item['numero']} ({item['fecha']})")
            elif hasattr(response, 'data') and isinstance(response.data, dict):
                 print(f"Response Data: {response.data}")
            else:
                print('No data in response or unexpected format')
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()
