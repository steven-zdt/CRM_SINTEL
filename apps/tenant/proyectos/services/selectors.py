"""
Selectors para Proyectos v3.5 - Zero Waste Queries

WARNING: SINTEL v3.5: Capa de Lectura Optimizada
- SSoT: Centralizacion de campos (LIST_FIELDS, DETAIL_FIELDS)
- Zero Trust: Filtrado obligatorio por empresa_id
- Performance: Uso estricto de .only() y select_related/prefetch_related
"""
from django.db import models
from django.db.models import OuterRef, Subquery
from ..models import Proyecto, TareaCorta

try:
    from apps.tenant.empleados.models import Empleado as _Empleado
except ImportError:
    _Empleado = None

# ==============================================================================
# SSoT: CAMPOS CANONICOS (Zero Waste)
# ==============================================================================
LIST_FIELDS = [
    'id', 'uuid', 'codigo', 'nombre', 'tipo_servicio', 'descripcion',
    'fase_actual', 'estado_tarea',
    'fecha_inicio', 'fecha_fin_estimada',
    'cliente_id', 'cliente_nombre',
    'responsable_actual_id', 'responsable_actual_nombre',
    'proveedor_id', 'proveedor_nombre',
    'valor_contrato_proyectado', 'costo_mano_obra_real', 'costo_materiales_real',
    'utilidad_estimada', 'margen_rentabilidad',
    'costo_planeado_total', 'utilidad_planeada', 'margen_planeado',
    'porcentaje_avance', 'fecha_cierre_real',
    'factura_costo_id', 'factura_costo_numero',
    'servicio_asociado_id',
    'sede_id',   # sede_id = FK id, valido en ambos contextos
    'created_at', 'updated_at',
    'empresa_id'
]

# Traversals ORM SOLO para .only(); nunca en Meta.fields.
_SEDE_LIST_TRAVERSALS = ('sede__nombre',)

DETAIL_FIELDS = LIST_FIELDS + [
    'responsable_comercial_id', 'responsable_comercial_nombre',
    'responsable_tecnico_id', 'responsable_tecnico_nombre',
    'responsable_operativo_id', 'responsable_operativo_nombre',
    'responsable_administrativo_id', 'responsable_administrativo_nombre',
    'descripcion', 'factura_ref',
    'contrato_archivo', 'acta_inicio_archivo', 'cronograma_archivo',
    'acta_entrega_archivo', 'informe_final_archivo',
]

_SEDE_DETAIL_TRAVERSALS = ('sede__nombre', 'sede__uuid')

TAREA_CORTA_FIELDS = [
    'id', 'uuid', 'empresa_id', 'cliente_id', 'empleado_id',
    'fecha_inicio', 'fecha_fin', 'titulo', 'descripcion',
    'estado', 'prioridad', 'notas_progreso', 'created_at', 'updated_at'
]


def qs_list(empresa_id, search=None):
    """
    QuerySet optimizado para listados. Usa .only() para Zero Waste.
    """
    qs = Proyecto.objects.filter(
        empresa_id=empresa_id
    ).select_related(
        'factura_costo', 'servicio_asociado', 'sede'
    ).only(
        *LIST_FIELDS,
        *_SEDE_LIST_TRAVERSALS,
    )

    if _Empleado is not None:
        responsable_uuid = _Empleado.objects.filter(
            empresa_id=empresa_id,
            id=OuterRef('responsable_actual_id')
        ).values('uuid')[:1]
        qs = qs.annotate(responsable_empleado_uuid=Subquery(responsable_uuid))

    if search:
        qs = qs.filter(
            models.Q(nombre__icontains=search) |
            models.Q(codigo__icontains=search) |
            models.Q(cliente_nombre__icontains=search) |
            models.Q(responsable_actual_nombre__icontains=search)
        )

    return qs.order_by('-updated_at')

def qs_detail(empresa_id, uuid):
    """
    QuerySet de detalle con relaciones prefetch. Retorna None si no existe
    (el ViewSet lanza NotFound al recibir None).
    Filtra por uuid (no pk) para cumplir M-001 del Roadmap M3.
    v3.5.2: Agregado prefetch_related('items_presupuesto') para Zero Waste.
    """
    return Proyecto.objects.filter(
        empresa_id=empresa_id,
        uuid=uuid
    ).select_related(
        'factura_costo', 'servicio_asociado', 'sede'
    ).only(
        *DETAIL_FIELDS,
        *_SEDE_DETAIL_TRAVERSALS,
    ).prefetch_related(
        'equipo_trabajo',
        'pedidos',
        'pedidos__items',
        'items_presupuesto'
    ).first()


class TareaCortaSelector:
    """
    Queries de lectura optimizadas para TareaCorta con .only() para Zero Waste.
    """

    @staticmethod
    def qs_por_empleado(empresa_id, empleado_uuid=None, fecha_inicio=None, fecha_fin=None):
        """
        QuerySet de tareas cortas filtradas por empleado y empresa.
        Filtros de fecha: busca tareas cuyo periodo intersecta con [fecha_inicio, fecha_fin].
        """
        qs = TareaCorta.objects.filter(
            empresa_id=empresa_id
        ).select_related('cliente', 'empleado', 'empleado__empresa').only(
            *TAREA_CORTA_FIELDS,
            'cliente__id', 'cliente__uuid', 'cliente__empresa_id',
            'cliente__razon_social', 'cliente__numero_documento',
            'cliente__nombre_comercial',
            'empleado__id', 'empleado__uuid', 'empleado__empresa_id',
            'empleado__empresa__id',
            'empleado__primer_nombre', 'empleado__primer_apellido',
            'empleado__numero_documento', 'empleado__email'
        )

        if empleado_uuid:
            qs = qs.filter(empleado__uuid=empleado_uuid)

        if fecha_inicio:
            qs = qs.filter(fecha_fin__gte=fecha_inicio)
        if fecha_fin:
            qs = qs.filter(fecha_inicio__lte=fecha_fin)

        return qs.order_by('fecha_inicio', 'created_at')

    @staticmethod
    def qs_resumen_empleado(empresa_id, empleado_uuid):
        """
        Agregacion de tareas cortas por estado para un empleado.
        """
        qs = TareaCorta.objects.filter(
            empresa_id=empresa_id,
            empleado__uuid=empleado_uuid
        )

        resumen = qs.values('estado').annotate(
            count=models.Count('id')
        )

        return {item['estado']: item['count'] for item in resumen}

    @staticmethod
    def get_tarea_corta(empresa_id, tarea_uuid):
        """
        Obtiene una tarea corta individual por su UUID lookup.
        """
        try:
            return TareaCorta.objects.filter(
                empresa_id=empresa_id,
                uuid=tarea_uuid
            ).select_related('cliente', 'empleado', 'empleado__empresa').only(
                *TAREA_CORTA_FIELDS,
                'cliente__id', 'cliente__uuid', 'cliente__empresa_id',
                'cliente__razon_social', 'cliente__numero_documento',
                'cliente__nombre_comercial',
                'empleado__id', 'empleado__uuid', 'empleado__empresa_id',
                'empleado__empresa__id',
                'empleado__primer_nombre', 'empleado__primer_apellido',
                'empleado__numero_documento', 'empleado__email'
            ).first()
        except TareaCorta.DoesNotExist:
            return None

