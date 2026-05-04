
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.tenant.clientes.models import Cliente
from apps.tenant.clientes.services.crud_service import ClienteCRUDService
from django.core.exceptions import ValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

def test_delete_active_cliente():
    # 1. Create an active client
    # Note: we need an empresa_id. Let's find one.
    from apps.tenant.empresa.models import Empresa
    empresa = Empresa.objects.first()
    if not empresa:
        print("No empresa found. Skipping test.")
        return

    cliente = Cliente.objects.create(
        empresa_id=empresa.id,
        tipo_persona="NATURAL",
        tipo_documento="CC",
        numero_documento="123456789",
        razon_social="Test Cliente Activo",
        regimen_tributario="SIMPLE",
        activo=True
    )
    print(f"Created active client: {cliente.id}")

    # 2. Try to delete it via service
    try:
        ClienteCRUDService.delete_cliente(cliente)
        print("ERROR: Active client was deleted!")
    except DRFValidationError as e:
        print(f"SUCCESS: Caught expected error: {e}")
    except Exception as e:
        print(f"Caught unexpected error type: {type(e)} - {e}")

    # 3. Cleanup
    cliente.activo = False
    cliente.save()
    ClienteCRUDService.delete_cliente(cliente)
    print("Cleanup: Deleted inactive client.")

if __name__ == "__main__":
    test_delete_active_cliente()
