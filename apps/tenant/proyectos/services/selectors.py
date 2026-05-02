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
    'id', 'codigo', 'nombre', 'tipo_servicio', 'descripcion',
    'fase_actual', 'estado_tarea',
    'fecha_inicio', 'fecha_fin_estimada',
    'cliente_id', 'cliente_nombre',
    'responsable_actual_id', 'responsable_actual_nombre',
    'valor_contrato_proyectado', 'costo_mano_obra_real', 'costo_materiales_real',
    'utilidad_estimada', 'margen_rentabilidad',
    'porcentaje_avance', 'fecha_cierre_real',
    'created_at', 'updated_at',
    'empresa_id'
]

DETAIL_FIELDS = LIST_FIELDS + []  # En este caso son los mismos por ahora

def qs_list(empresa_id, search=None):
    """
    QuerySet optimizado para listados de proyectos.
    """
    qs = Proyecto.objects.filter(empresa_id=empresa_id).only(*LIST_FIELDS)
    
    if search:
        qs = qs.filter(
            models.Q(nombre__icontains=search) |
            models.Q(codigo__icontains=search) |
            models.Q(descripcion__icontains=search) |
            models.Q(cliente_nombre__icontains=search) |
            models.Q(responsable_actual_nombre__icontains=search)
        )
    
    return qs.distinct().order_by('-updated_at')

def qs_detail(empresa_id, pk):
    """
    QuerySet optimizado para detalle de proyecto con relaciones.
    """
    return Proyecto.objects.filter(
        empresa_id=empresa_id,
        pk=pk
    ).select_related('empresa').prefetch_related(
        'equipo_trabajo',
        'pedidos',
        'pedidos__items'
    ).first()
