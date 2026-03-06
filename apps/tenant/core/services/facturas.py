"""
Servicios de orquestación para datos de facturas.

⚠️ POLÍTICA:
- Solo lectura/composición de datos
- NO duplica lógica de negocio de apps.tenant.facturas
- Usa ORM optimizado (only, select_related, prefetch_related)
"""
from typing import Dict, Any, List
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta


def get_facturas_snapshot(tenant, user=None) -> Dict[str, Any]:
    """
    Obtiene snapshot de facturas del tenant.
    
    Args:
        tenant: Instancia del tenant (Client)
        user: Usuario autenticado (opcional, para filtros por permisos)
        
    Returns:
        Dict con estadísticas y facturas recientes
    """
    try:
        from apps.tenant.facturas.models import Factura
        
        # Total de facturas
        total = Factura.objects.count()
        
        # Facturas por estado
        por_estado = list(
            Factura.objects
            .values('estado')
            .annotate(cantidad=Count('id'))
            .order_by('estado')
        )
        
        # Facturas del mes actual
        hoy = timezone.now().date()
        inicio_mes = hoy.replace(day=1)
        facturas_mes = Factura.objects.filter(
            fecha_emision__gte=inicio_mes,
            fecha_emision__lte=hoy
        )
        
        # Últimas facturas (10 más recientes)
        recientes = list(
            Factura.objects
            .only('id', 'numero', 'prefijo', 'consecutivo', 'estado', 'fecha_emision', 'receptor_razon_social', 'total')
            .order_by('-fecha_emision')[:10]
            .values('id', 'numero', 'prefijo', 'consecutivo', 'estado', 'fecha_emision', 'receptor_razon_social', 'total')
        )
        
        return {
            'total': total,
            'por_estado': por_estado,
            'mes_actual': {
                'cantidad': facturas_mes.count(),
                'total': float(facturas_mes.aggregate(total=Sum('total'))['total'] or 0),
            },
            'recientes': recientes,
        }
    except Exception:
        return {
            'total': 0,
            'por_estado': [],
            'mes_actual': {
                'cantidad': 0,
                'total': 0.0,
            },
            'recientes': [],
        }
