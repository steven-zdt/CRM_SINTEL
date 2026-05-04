
from apps.tenant.clientes.models import Cliente
from apps.tenant.clientes.services.crud_service import ClienteCRUDService
from rest_framework.exceptions import ValidationError as DRFValidationError
from apps.tenant.empresa.models import Empresa

def run_test():
    empresa = Empresa.objects.first()
    if not empresa:
        print("No empresa found.")
        return

    cliente = Cliente.objects.create(
        empresa_id=empresa.id,
        tipo_persona="NATURAL",
        tipo_documento="CC",
        numero_documento="999888777",
        razon_social="Test Security Delete",
        regimen_tributario="SIMPLE",
        activo=True
    )
    print(f"CLIENTE CREADO (ACTIVO=TRUE): {cliente.id}")

    try:
        print("Intentando eliminar cliente activo...")
        ClienteCRUDService.delete_cliente(cliente)
        print("FALLO: El cliente activo fue eliminado.")
    except DRFValidationError as e:
        print(f"EXITO: Bloqueado correctamente. Error: {e.detail}")
    except Exception as e:
        print(f"ERROR INESPERADO: {type(e)} - {e}")

    # Cleanup
    cliente.activo = False
    cliente.save()
    ClienteCRUDService.delete_cliente(cliente)
    print("LIMPIEZA: Cliente inactivo eliminado.")

run_test()
