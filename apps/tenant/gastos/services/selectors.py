"""
Selectores de Gastos - Consultas GET optimizadas (read-only).

WARNING: SINTEL v2.61.4: Arquitectura Service Layer Modular.
- Este archivo contiene SOLO consultas de lectura optimizadas.
- Todas las funciones son @staticmethod.
- Usa .only() para cargar solo campos necesarios (Zero Waste).
"""
from django.db.models import Q, Sum, Count
from django.utils import timezone

from apps.tenant.gastos.models import ResolucionDIAN, DocumentoSoporte


# ==============================================================================
# CONSTANTES SSoT - Campos para consultas optimizadas
# ==============================================================================

# Campos estrictamente necesarios para LISTAS (Tabulator)
# No GASTO_LIST_FIELDS needed, unified in DOCUMENTO

RESOLUCION_LIST_FIELDS = (
    'id', 'uuid', 'numero_resolucion', 'prefijo', 'vigente',
    'rango_desde', 'rango_hasta', 'fecha_resolucion',
    'fecha_inicio', 'fecha_fin', 'consecutivo',
    'empresa_id'
)

DOCUMENTO_LIST_FIELDS = (
    'id', 'uuid', 'consecutivo', 'subtotal',
    'fecha', 'total', 'categoria_contable', 'descripcion',
    'activo', 'anulado', 'numero_documento_proveedor', 'empresa_id',
    'cuenta_gasto_uuid',
    'producto_relacionado_id', 'servicio_relacionado_id', 'activo_relacionado_id'
)

# Campos completos para DETALLE (formularios de edicion)
DOCUMENTO_DETAIL_FIELDS = (
    'id', 'uuid', 'consecutivo', 'fecha', 'total', 'subtotal',
    'categoria_contable', 'descripcion', 'observaciones',
    'activo', 'anulado', 'numero_documento_proveedor', 'empresa_id',
    'cuenta_gasto_uuid',
    'resolucion_dian_id', 'proveedor_id',
    'producto_relacionado_id', 'servicio_relacionado_id', 'activo_relacionado_id',
    'created_at', 'updated_at'
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

# GastoSelector removed (Merged into DocumentoSelector)


class ResolucionSelector:
    """Read-only selectors para modelo ResolucionDIAN."""

    @staticmethod
    def get_list(empresa_id: int, search: str = None, solo_vigentes: bool = False):
        """QuerySet optimizado para LISTAR Resoluciones DIAN."""
        qs = ResolucionDIAN.objects.filter(
            empresa_id=empresa_id
        ).annotate(
            conteo_documentos=Count('documentos_soporte')
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
    def get_detail(empresa_id: int, resolucion_uuid=None):
        """QuerySet optimizado para DETALLE de ResolucionDIAN."""
        qs = ResolucionDIAN.objects.filter(
            empresa_id=empresa_id
        ).only(*RESOLUCION_DETAIL_FIELDS)

        if resolucion_uuid:
            return qs.filter(uuid=resolucion_uuid)
        return qs

    @staticmethod
    def get_vigente(empresa_id: int):
        """
        Obtiene la resolucion vigente para una empresa (Optimizado con Cache).
        """
        from django.core.cache import cache
        cache_key = f"resolucion_vigente_{empresa_id}"
        resolucion = cache.get(cache_key)
        
        if resolucion is None:
            resolucion = ResolucionDIAN.objects.filter(
                empresa_id=empresa_id,
                vigente=True
            ).first()
            if resolucion:
                # Cachear por 1 hora
                cache.set(cache_key, resolucion, timeout=3600)
        
        return resolucion


class DocumentoSelector:
    """Read-only selectors para modelo DocumentoSoporte."""

    @staticmethod
    def get_list(empresa_id: int, resolucion_id: int = None, search: str = None):
        """QuerySet optimizado para LISTAR Documentos Soporte."""
        qs = DocumentoSoporte.objects.filter(
            empresa_id=empresa_id
        ).select_related(
            'resolucion_dian',
            'proveedor',
            'producto_relacionado',
            'servicio_relacionado',
            'activo_relacionado'
        ).only(
            *DOCUMENTO_LIST_FIELDS,
            'resolucion_dian_id',
            'resolucion_dian__prefijo',
            'resolucion_dian__consecutivo',
            'proveedor__razon_social',
            'proveedor_id',
            'producto_relacionado__nombre',
            'servicio_relacionado__nombre',
            'activo_relacionado__nombre'
        )

        if resolucion_id:
            qs = qs.filter(resolucion_dian_id=resolucion_id)

        if search:
            qs = qs.filter(
                Q(descripcion__icontains=search) |
                Q(numero_documento_proveedor__icontains=search) |
                Q(proveedor__razon_social__icontains=search)
            )

        # Incluir TODOS los documentos (anulados y no anulados) para mantener consecutividad
        return qs.order_by('-fecha', '-consecutivo')

    @staticmethod
    def get_detail(empresa_id: int, documento_uuid=None):
        """QuerySet optimizado para DETALLE de DocumentoSoporte."""
        qs = DocumentoSoporte.objects.filter(
            empresa_id=empresa_id
        ).select_related(
            'resolucion_dian',
            'proveedor',
            'usuario_anulacion',
            'producto_relacionado',
            'servicio_relacionado',
            'activo_relacionado'
        )
        if documento_uuid:
            return qs.filter(uuid=documento_uuid)
        return qs

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
            total_gastado=Sum('total'),
            count_documentos=Count('id')
        )

        return {
            "total_gastos_mes": str(totales['total_gastado'] or Decimal('0.00')),
            "documentos_emitidos": totales['count_documentos'] or 0,
            "periodo_actual": mes_actual
        }



