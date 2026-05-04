"""
CRUD Service para Proyectos v3.5 - Persistence Layer

WARNING: SINTEL v3.5: Capa de Persistencia Pura
- Atomicidad: Uso de @transaction.atomic en todas las operaciones
- Zero Trust: Validación de empresa_id
- Aislamiento: Sin lógica de negocio compleja, solo persistencia
"""
from django.db import transaction
from ..models import Proyecto, AsignacionPersonal, PedidoProyecto

@transaction.atomic
def save_proyecto(proyecto, update_fields=None):
    """
    Guarda una instancia de Proyecto.
    Captura errores de integridad (como duplicados de código) para evitar 500.
    """
    from django.db import IntegrityError
    from rest_framework.exceptions import ValidationError
    
    try:
        proyecto.save(update_fields=update_fields)
    except IntegrityError as e:
        # Si es un error de unicidad del código, lanzar error de validación descriptivo
        if 'uniq_proyecto_codigo_empresa' in str(e):
            raise ValidationError({'codigo': f'El código "{proyecto.codigo}" ya está en uso para otro proyecto.'})
        # Otros errores de integridad
        raise ValidationError({'detail': f'Error de integridad al guardar el proyecto: {str(e)}'})
    
    return proyecto

@transaction.atomic
def delete_proyecto(proyecto):
    """
    Elimina una instancia de Proyecto.
    """
    proyecto.delete()
    return True

@transaction.atomic
def save_asignacion(asignacion):
    """
    Guarda una asignación de personal.
    """
    asignacion.save()
    return asignacion

@transaction.atomic
def delete_asignacion(asignacion):
    """
    Elimina una asignación.
    """
    asignacion.delete()
    return True

@transaction.atomic
def save_pedido(pedido):
    """
    Guarda un pedido de proyecto.
    """
    pedido.save()
    return pedido

@transaction.atomic
def delete_pedido(pedido):
    """
    Elimina un pedido.
    """
    pedido.delete()
    return True
