"""
Servicios de orquestación para datos de contabilidad.

⚠️ POLÍTICA:
- Solo lectura/composición de datos
- NO duplica lógica de negocio de apps.tenant.contabilidad
- Usa ORM optimizado (only, select_related, prefetch_related)
"""
from typing import Dict, Any, List
from django.db.models import Sum, Count
from django.utils import timezone


def get_contabilidad_snapshot(tenant, user=None) -> Dict[str, Any]:
    """
    Obtiene snapshot de contabilidad del tenant.
    
    Args:
        tenant: Instancia del tenant (Client)
        user: Usuario autenticado (opcional, para filtros por permisos)
        
    Returns:
        Dict con estadísticas y asientos recientes
    """
    try:
        from apps.tenant.contabilidad.models import (
            CuentaContable,
            AsientoContable,
            MovimientoContable,
        )
        
        # Estadísticas generales
        total_cuentas = CuentaContable.objects.count()
        total_asientos = AsientoContable.objects.count()
        
        # Movimientos del mes actual
        hoy = timezone.now().date()
        inicio_mes = hoy.replace(day=1)
        movimientos_mes = MovimientoContable.objects.filter(
            fecha__gte=inicio_mes,
            fecha__lte=hoy
        )
        
        totales_mes = movimientos_mes.aggregate(
            total_debitos=Sum('debito'),
            total_creditos=Sum('credito')
        )
        
        # Últimos asientos (10 más recientes)
        asientos_recientes = list(
            AsientoContable.objects
            .only('id', 'numero', 'fecha', 'descripcion', 'estado', 'tipo')
            .order_by('-fecha')[:10]
            .values('id', 'numero', 'fecha', 'descripcion', 'estado', 'tipo')
        )
        
        return {
            'total_cuentas': total_cuentas,
            'total_asientos': total_asientos,
            'mes_actual': {
                'total_movimientos': movimientos_mes.count(),
                'total_debitos': float(totales_mes['total_debitos'] or 0),
                'total_creditos': float(totales_mes['total_creditos'] or 0),
            },
            'asientos_recientes': asientos_recientes,
        }
    except Exception:
        return {
            'total_cuentas': 0,
            'total_asientos': 0,
            'mes_actual': {
                'total_movimientos': 0,
                'total_debitos': 0.0,
                'total_creditos': 0.0,
            },
            'asientos_recientes': [],
        }
