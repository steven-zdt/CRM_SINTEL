"""
Servicio de Tareas Diarias (Fase 3 - Ejecucion) v3.5.4

Service Layer para gestion de tareas diarias (TareaDiariaProyecto).
Patron: CRUD Service + Business Service + Selector.

Validaciones criticas:
- fecha_inicio <= fecha_fin (rango coherente)
- [fecha_inicio, fecha_fin] intersecta con [proyecto.fecha_inicio, proyecto.fecha_fin_estimada]
- Proyecto en fase CIERRE -> Tareas INMUTABLES (no create, update, delete)
- DSV: empresa_id DEBE coincidir con proyecto.empresa_id
"""
from decimal import Decimal
from datetime import date

from django.db import models, transaction
from rest_framework.exceptions import ValidationError

from apps.tenant.empresa.models import Empresa
from ..models import Proyecto, TareaDiariaProyecto


# ==============================================================================
# SSoT: TAREA_FIELDS para Zero Waste (LIST/DETAIL)
# ==============================================================================

TAREA_FIELDS = [
    'id', 'uuid', 'proyecto_id', 'empresa_id', 'fecha_inicio', 'fecha_fin',
    'titulo', 'descripcion', 'estado', 'prioridad',
    'asignado_a', 'notas_progreso', 'created_at', 'updated_at'
]


# ==============================================================================
# CRUD SERVICE - Persistencia (v3.5.3)
# ==============================================================================

class TareasDiariasCRUDService:
    """
    Persistencia de TareaDiariaProyecto.
    Metodos transaccionales @transaction.atomic.
    """

    @staticmethod
    @transaction.atomic
    def save_tarea(tarea):
        """Guarda una TareaDiariaProyecto."""
        tarea.save()

    @staticmethod
    @transaction.atomic
    def delete_tarea(tarea):
        """Elimina una TareaDiariaProyecto."""
        tarea.delete()


# ==============================================================================
# BUSINESS SERVICE - Logica de Negocio (v3.5.3)
# ==============================================================================

class TareasDiariasBusinessService:
    """
    Logica de negocio: validacion, restricciones, y orquestacion.
    Responsable de:
    - Validacion de rango de fechas (fecha_inicio_real <= fecha <= fecha_fin_estimada)
    - Bloqueo de operaciones en fase CIERRE
    - DSV (Double Semantic Verification) - validar empresa_id
    """

    @staticmethod
    def _validar_fecha_en_rango(proyecto, fecha_inicio, fecha_fin):
        """
        Valida que el periodo de la tarea [fecha_inicio, fecha_fin] sea coherente y no exceda el fin del proyecto.

        Raises:
            ValidationError si el periodo es invalido o excede el fin del proyecto
        """
        if fecha_inicio > fecha_fin:
            raise ValidationError(
                f"La fecha de inicio ({fecha_inicio}) no puede ser posterior a la fecha de fin ({fecha_fin})"
            )
        if proyecto.fecha_inicio and fecha_inicio < proyecto.fecha_inicio:
            raise ValidationError(
                f"La fecha de inicio de la tarea ({fecha_inicio}) no puede ser anterior a la fecha de inicio del proyecto ({proyecto.fecha_inicio})."
            )
        if proyecto.fecha_fin_estimada and fecha_fin > proyecto.fecha_fin_estimada:
            raise ValidationError(
                f"La fecha de fin de la tarea ({fecha_fin}) no puede ser posterior a la fecha fin estimada ({proyecto.fecha_fin_estimada}). "
                f"Actualiza la fecha fin estimada del proyecto si es necesario."
            )

    @staticmethod
    def _validar_proyecto_no_cerrado(proyecto):
        """
        Valida que el proyecto NO este en fase CIERRE.

        Raises:
            ValidationError si proyecto esta en CIERRE
        """
        if proyecto.fase_actual == 'CIERRE':
            raise ValidationError(
                "No se pueden crear, modificar o eliminar tareas en fase Cierre. El proyecto esta cerrado."
            )

    @staticmethod
    def _validar_empresa_dsv(proyecto, empresa):
        """
        Valida que empresa_id coincida (DSV - Double Semantic Verification).

        Raises:
            ValidationError si hay mismatch
        """
        if proyecto.empresa_id != empresa.id:
            raise ValidationError(
                "La empresa de la tarea no coincide con la empresa del proyecto (DSV fallo)"
            )

    @staticmethod
    def crear_tarea(
        empresa,
        proyecto,
        fecha_inicio=None,
        fecha_fin=None,
        titulo='',
        descripcion='',
        prioridad='NORMAL',
        asignado_a='',
        fecha=None
    ):
        """
        Crea una nueva TareaDiariaProyecto.

        Validaciones:
        1. DSV: empresa_id debe coincidir con proyecto.empresa_id
        2. Rango: fecha_inicio <= fecha_fin
        3. Limite: fecha_fin <= proyecto.fecha_fin_estimada (no excede proyecto)
        4. Bloqueo: proyecto.fase_actual != 'CIERRE'

        Args:
            empresa: Empresa instance
            proyecto: Proyecto instance
            fecha_inicio: date object, primer dia de la tarea
            fecha_fin: date object, ultimo dia de la tarea
            titulo: str, requerido
            descripcion: str, opcional
            prioridad: str, default='NORMAL'
            asignado_a: str, opcional

        Returns:
            TareaDiariaProyecto instance (guardada)

        Raises:
            ValidationError por DSV, rango invalido, limites de proyecto, o fase bloqueada
        """
        if fecha is not None and fecha_inicio is None:
            fecha_inicio = fecha
        if fecha_fin is None:
            fecha_fin = fecha_inicio

        if not fecha_inicio or not fecha_fin:
            raise ValidationError("fecha_inicio y fecha_fin son requeridas.")

        TareasDiariasBusinessService._validar_empresa_dsv(proyecto, empresa)
        TareasDiariasBusinessService._validar_fecha_en_rango(proyecto, fecha_inicio, fecha_fin)
        TareasDiariasBusinessService._validar_proyecto_no_cerrado(proyecto)

        # Instancia tarea
        tarea = TareaDiariaProyecto(
            empresa=empresa,
            proyecto=proyecto,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            titulo=titulo,
            descripcion=descripcion,
            prioridad=prioridad,
            asignado_a=asignado_a,
            estado='PENDIENTE'
        )

        # Persiste
        TareasDiariasCRUDService.save_tarea(tarea)

        return tarea

    @staticmethod
    def cambiar_estado_tarea(tarea, nuevo_estado):
        """
        Cambia el estado de una tarea.

        Validaciones:
        1. Bloqueo: proyecto.fase_actual != 'CIERRE'
        2. nuevo_estado en ESTADO_CHOICES

        Args:
            tarea: TareaDiariaProyecto instance
            nuevo_estado: str, uno de ESTADO_CHOICES

        Raises:
            ValidationError si fase es CIERRE o estado invalido
        """
        TareasDiariasBusinessService._validar_proyecto_no_cerrado(tarea.proyecto)

        if nuevo_estado not in dict(TareaDiariaProyecto.Estado.choices):
            raise ValidationError(f"Estado invalido: {nuevo_estado}")

        tarea.estado = nuevo_estado
        TareasDiariasCRUDService.save_tarea(tarea)

        return tarea

    @staticmethod
    def actualizar_tarea(tarea, data):
        """
        Actualiza campos editables de una tarea.

        Campos permitidos: fecha_inicio, fecha_fin, descripcion, prioridad, notas_progreso, asignado_a

        Validaciones:
        1. Si se modifican fechas, validar rango
        2. Bloqueo: proyecto.fase_actual != 'CIERRE'

        Args:
            tarea: TareaDiariaProyecto instance
            data: dict con campos a actualizar

        Raises:
            ValidationError si fase es CIERRE o fechas son invalidas
        """
        TareasDiariasBusinessService._validar_proyecto_no_cerrado(tarea.proyecto)

        # Campos permitidos
        permitidos = ['fecha_inicio', 'fecha_fin', 'descripcion', 'prioridad', 'notas_progreso', 'asignado_a']
        for key, value in data.items():
            if key in permitidos:
                setattr(tarea, key, value)

        # Si se modificaron fechas, validar nuevo rango
        if 'fecha_inicio' in data or 'fecha_fin' in data:
            TareasDiariasBusinessService._validar_fecha_en_rango(
                tarea.proyecto,
                tarea.fecha_inicio,
                tarea.fecha_fin
            )

        TareasDiariasCRUDService.save_tarea(tarea)

        return tarea

    @staticmethod
    def eliminar_tarea(tarea):
        """
        Elimina una tarea.

        Validaciones:
        1. Bloqueo: proyecto.fase_actual != 'CIERRE'

        Args:
            tarea: TareaDiariaProyecto instance

        Raises:
            ValidationError si fase es CIERRE
        """
        TareasDiariasBusinessService._validar_proyecto_no_cerrado(tarea.proyecto)
        TareasDiariasCRUDService.delete_tarea(tarea)


# ==============================================================================
# SELECTOR - Queries Optimizadas (Zero Waste) (v3.5.3)
# ==============================================================================

class TareasDiariasSelector:
    """
    Queries de lectura optimizadas con .only() para Zero Waste.
    """

    @staticmethod
    def qs_por_proyecto(empresa_id, proyecto_uuid, fecha_inicio=None, fecha_fin=None):
        """
        QuerySet de tareas filtradas por proyecto y empresa.

        Filtros de fecha: busca tareas cuyo periodo [tarea.fecha_inicio, tarea.fecha_fin]
        intersecta con [fecha_inicio, fecha_fin] (si se proporcionan).

        Args:
            empresa_id: int, empresa_id para DSV
            proyecto_uuid: str, UUID del proyecto
            fecha_inicio: date optional, limite minimo de busqueda
            fecha_fin: date optional, limite maximo de busqueda

        Returns:
            QuerySet filtered y optimizado
        """
        qs = TareaDiariaProyecto.objects.filter(
            empresa_id=empresa_id,
            proyecto__uuid=proyecto_uuid
        ).only(*TAREA_FIELDS)

        if fecha_inicio:
            qs = qs.filter(fecha_fin__gte=fecha_inicio)
        if fecha_fin:
            qs = qs.filter(fecha_inicio__lte=fecha_fin)

        return qs.order_by('fecha_inicio', 'created_at')

    @staticmethod
    def qs_resumen_proyecto(empresa_id, proyecto_uuid):
        """
        Agregacion de tareas por estado.

        Returns:
            dict con conteos por estado
        """
        qs = TareaDiariaProyecto.objects.filter(
            empresa_id=empresa_id,
            proyecto__uuid=proyecto_uuid
        )

        resumen = qs.values('estado').annotate(
            count=models.Count('id')
        )

        # Formato: {ESTADO: count}
        return {item['estado']: item['count'] for item in resumen}

    @staticmethod
    def get_tarea(empresa_id, tarea_id):
        """
        Obtiene una tarea individual por ID.

        Args:
            empresa_id: int, para DSV
            tarea_id: int, ID de la tarea

        Returns:
            TareaDiariaProyecto or None
        """
        try:
            return TareaDiariaProyecto.objects.filter(
                empresa_id=empresa_id,
                id=tarea_id
            ).only(*TAREA_FIELDS).first()
        except TareaDiariaProyecto.DoesNotExist:
            return None
