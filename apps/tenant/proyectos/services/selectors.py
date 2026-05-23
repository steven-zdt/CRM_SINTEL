"""
Selectors para Proyectos v3.5 - Zero Waste Queries

WARNING: SINTEL v3.5: Capa de Lectura Optimizada
- SSoT: Centralización de campos (LIST_FIELDS, DETAIL_FIELDS)
- Zero Trust: Filtrado obligatorio por empresa_id
- Performance: Uso estricto de .only() y select_related/prefetch_related
"""
from django.db import models
from ..models import Proyecto

# ==============================================================================
# SSoT: CAMPOS CANÓNICOS (Zero Waste)
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
    'created_at', 'updated_at',
    'empresa_id'
]

DETAIL_FIELDS = LIST_FIELDS + [
    'responsable_comercial_id', 'responsable_comercial_nombre',
    'responsable_tecnico_id', 'responsable_tecnico_nombre',
    'responsable_operativo_id', 'responsable_operativo_nombre',
    'responsable_administrativo_id', 'responsable_administrativo_nombre',
    'descripcion', 'factura_ref',
    'contrato_archivo', 'acta_inicio_archivo', 'cronograma_archivo',
    'acta_entrega_archivo', 'informe_final_archivo',
]

def qs_list(empresa_id, search=None):
    """
    QuerySet optimizado para listados. Usa .only() para Zero Waste.
    """
    qs = Proyecto.objects.filter(
        empresa_id=empresa_id
    ).select_related('factura_costo', 'servicio_asociado').only(*LIST_FIELDS)

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
    ).only(*DETAIL_FIELDS).select_related('factura_costo', 'servicio_asociado').prefetch_related(
        'equipo_trabajo',
        'pedidos',
        'pedidos__items',
        'items_presupuesto'
    ).first()
