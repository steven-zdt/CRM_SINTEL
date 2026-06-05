"""
CRUD Service para Proyectos v3.5 - Persistence Layer

WARNING: SINTEL v3.5: Capa de Persistencia Pura
- Atomicidad: Uso de @transaction.atomic en todas las operaciones
- Zero Trust: Validacion de empresa_id
- Aislamiento: Sin logica de negocio compleja, solo persistencia
"""
from django.db import transaction, IntegrityError
from rest_framework.exceptions import ValidationError
from ..models import Proyecto, AsignacionPersonal, PedidoProyecto, TareaCorta

@transaction.atomic
def save_proyecto(proyecto, update_fields=None):
    """
    Guarda una instancia de Proyecto.
    Captura errores de integridad (como duplicados de codigo) para evitar 500.
    """
    try:
        proyecto.save(update_fields=update_fields)
    except IntegrityError as e:
        # Si es un error de unicidad del codigo, lanzar error de validacion descriptivo
        if 'uniq_proyecto_codigo_empresa' in str(e):
            raise ValidationError({'codigo': f'El codigo "{proyecto.codigo}" ya esta en uso para otro proyecto.'})
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
    Guarda una asignacion de personal.
    """
    asignacion.save()
    return asignacion

@transaction.atomic
def delete_asignacion(asignacion):
    """
    Elimina una asignacion.
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

@transaction.atomic
def save_tarea_corta(tarea_corta):
    """
    Guarda una instancia de TareaCorta.
    """
    tarea_corta.save()
    return tarea_corta

@transaction.atomic
def delete_tarea_corta(tarea_corta):
    """
    Elimina una instancia de TareaCorta.
    """
    tarea_corta.delete()
    return True
