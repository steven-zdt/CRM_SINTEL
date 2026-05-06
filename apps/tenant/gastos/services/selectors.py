"""
Selectores de Gastos - Consultas GET optimizadas (read-only).

WARNING: SINTEL v2.61.4: Arquitectura Service Layer Modular.
- Este archivo contiene SOLO consultas de lectura optimizadas.
- Todas las funciones son @staticmethod.
- Usa .only() para cargar solo campos necesarios (Zero Waste).
"""
from django.db.models import Q, Sum, Count
from django.utils import timezone

from apps.tenant.gastos.models import Gasto, ResolucionDIAN, DocumentoSoporte


# ==============================================================================
# CONSTANTES SSoT - Campos para consultas optimizadas
# ==============================================================================

# Campos estrictamente necesarios para LISTAS (Tabulator)
GASTO_LIST_FIELDS = (
    'id', 'uuid', 'periodo', 'centro_costo', 'categoria_contable',
    'descripcion', 'empresa_id', 'created_at'
)

RESOLUCION_LIST_FIELDS = (
    'id', 'uuid', 'numero_resolucion', 'prefijo', 'vigente',
    'rango_desde', 'rango_hasta', 'fecha_inicio', 'fecha_fin',
    'empresa_id'
)

DOCUMENTO_LIST_FIELDS = (
    'id', 'uuid', 'consecutivo', 'prefijo', 'fecha', 'total',
    'anulado', 'empresa_id'
)

# Campos completos para DETALLE (formularios de edición)
GASTO_DETAIL_FIELDS = (
    'id', 'uuid', 'periodo', 'centro_costo', 'categoria_contable',
    'descripcion', 'observaciones', 'codigo_contable',
    'empresa_id', 'created_at', 'updated_at'
)

RESOLUCION_DETAIL_FIELDS = (
    'id', 'uuid', 'numero_resolucion', 'prefijo', 'vigente',
    'rango_desde', 'rango_hasta', 'fecha_resolucion',
    'fecha_inicio', 'fecha_fin', 'clave_tecnica',
    'empresa_id', 'created_at', 'updated_at'
)


# ==============================================================================
# SELECTOR CLASSES - Organizadas por modelo
# ==============================================================================

class GastoSelector:
    """Read-only selectors para modelo Gasto."""

    @staticmethod
    def get_list(empresa_id: int, search: str = None):
        """
        QuerySet optimizado para LISTAR Gastos.
        Incluye related DocumentoSoporte para mostrar consecutivo.
        """
        qs = Gasto.objects.filter(empresa_id=empresa_id).select_related(
            'documento_soporte', 'empresa'
        ).only(
            *GASTO_LIST_FIELDS,
            'documento_soporte__consecutivo',
            'documento_soporte__prefijo',
            'documento_soporte__vendedor_nombre',
            'documento_soporte__fecha',
            'documento_soporte__total',
            'documento_soporte__anulado'
        )

        if search:
            qs = qs.filter(
                Q(periodo__icontains=search) |
                Q(centro_costo__icontains=search) |
                Q(categoria_contable__icontains=search) |
                Q(documento_soporte__vendedor_nombre__icontains=search)
            )

        return qs.order_by('-created_at')

    @staticmethod
    def get_detail(empresa_id: int):
        """QuerySet optimizado para DETALLE de Gasto."""
        return Gasto.objects.filter(
            empresa_id=empresa_id
        ).select_related(
            'documento_soporte', 'empresa'
        ).only(*GASTO_DETAIL_FIELDS)

    @staticmethod
    def get_summary(empresa_id: int):
        """Calcula resumen de gastos para el mes actual."""
        hoy = timezone.now().date()
        mes_actual = hoy.strftime("%Y-%m")

        # Solo documentos NO anulados para el summary financiero
        qs_mes = DocumentoSoporte.objects.filter(
            empresa_id=empresa_id,
            fecha__year=hoy.year,
            fecha__month=hoy.month,
            anulado=False
        )

        from decimal import Decimal
        totales = qs_mes.aggregate(
            total_gastado=Sum('total') or Decimal('0.00'),
            count_documentos=Count('id')
        )

        return {
            "total_gastos_mes": str(totales['total_gastado']),
            "documentos_emitidos": totales['count_documentos'],
            "periodo_actual": mes_actual
        }


class ResolucionSelector:
    """Read-only selectors para modelo ResolucionDIAN."""

    @staticmethod
    def get_list(empresa_id: int, search: str = None, solo_vigentes: bool = False):
        """QuerySet optimizado para LISTAR Resoluciones DIAN."""
        qs = ResolucionDIAN.objects.filter(
            empresa_id=empresa_id
        ).only(*RESOLUCION_LIST_FIELDS)

        if solo_vigentes:
            qs = qs.filter(vigente=True)

        if search:
            qs = qs.filter(
                Q(numero_resolucion__icontains=search) |
                Q(prefijo__icontains=search)
            )

        return qs.order_by('-vigente', '-fecha_resolucion')

    @staticmethod
    def get_detail(empresa_id: int):
        """QuerySet optimizado para DETALLE de ResolucionDIAN."""
        return ResolucionDIAN.objects.filter(
            empresa_id=empresa_id
        ).only(*RESOLUCION_DETAIL_FIELDS)

    @staticmethod
    def get_vigente(empresa_id: int):
        """Obtiene la resolución vigente para una empresa."""
        return ResolucionDIAN.objects.filter(
            empresa_id=empresa_id,
            vigente=True
        ).first()


class DocumentoSelector:
    """Read-only selectors para modelo DocumentoSoporte."""

    @staticmethod
    def get_list(empresa_id: int, resolucion_id: int = None, search: str = None):
        """QuerySet optimizado para LISTAR Documentos Soporte."""
        qs = DocumentoSoporte.objects.filter(
            empresa_id=empresa_id
        ).select_related('resolucion_dian').only(
            *DOCUMENTO_LIST_FIELDS,
            'resolucion_dian__numero_resolucion',
            'resolucion_dian__prefijo'
        )

        if resolucion_id:
            qs = qs.filter(resolucion_dian_id=resolucion_id)

        if search:
            qs = qs.filter(
                Q(consecutivo__icontains=search) |
                Q(vendedor_nombre__icontains=search)
            )

        # Incluir TODOS los documentos (anulados y no anulados) para mantener consecutividad
        return qs.order_by('-consecutivo')

    @staticmethod
    def get_detail(empresa_id: int):
        """QuerySet optimizado para DETALLE de DocumentoSoporte."""
        return DocumentoSoporte.objects.filter(
            empresa_id=empresa_id
        ).select_related('resolucion_dian')


# Compatibilidad legacy - tuplas de campos por modelo
LIST_FIELDS = {
    'gasto': GASTO_LIST_FIELDS,
    'resolucion': RESOLUCION_LIST_FIELDS,
    'documento': DOCUMENTO_LIST_FIELDS,
}

DETAIL_FIELDS = {
    'gasto': GASTO_DETAIL_FIELDS,
    'resolucion': RESOLUCION_DETAIL_FIELDS,
}
