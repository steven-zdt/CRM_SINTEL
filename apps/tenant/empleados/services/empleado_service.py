"""
Servicios de negocio para empleados.

Service Layer: lógica de negocio sin presentación.
"""
from django.db import transaction
from ..models import Empleado


@transaction.atomic
def upsert_empleado(data):
    """
    Crea o actualiza un empleado por documento.
    
    Args:
        data: Dict con campos del empleado (incluye tipo_documento y numero_documento)
    
    Returns:
        Tupla (empleado, created)
    """
    tipo_doc = data.pop("tipo_documento")
    num_doc = data.pop("numero_documento")
    
    emp, created = Empleado.objects.update_or_create(
        tipo_documento=tipo_doc,
        numero_documento=num_doc,
        defaults=data
    )
    return emp, created
