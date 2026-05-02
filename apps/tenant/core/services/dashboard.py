"""
Servicios de orquestación para datos de dashboard.

# WARNING: POLÍTICA:
- Solo lectura/composición de datos
- NO duplica lógica de negocio de apps.tenant.dashboard
- Usa servicios de otras apps para componer datos
"""
from typing import Any

from apps.tenant.core.services.contabilidad import get_contabilidad_snapshot
from apps.tenant.core.services.empresa import get_empresas_snapshot
from apps.tenant.core.services.facturas import get_facturas_snapshot
from apps.tenant.core.services.perfil import get_perfil_snapshot


def get_dashboard_resumen(tenant, user=None) -> dict[str, Any]:
    """
    Obtiene resumen de datos del dashboard del tenant.
    
    # WARNING: POLÍTICA: Composición de datos de múltiples apps.
    
    Args:
        tenant: Instancia del tenant (Client)
        user: Usuario autenticado (opcional, para filtros por permisos)
        
    Returns:
        Dict con resumen del dashboard
    """
    try:
        # Componer datos de todas las apps
        empresas_data = get_empresas_snapshot(tenant)
        facturas_data = get_facturas_snapshot(tenant, user)
        contabilidad_data = get_contabilidad_snapshot(tenant, user)
        perfil_data = get_perfil_snapshot(user) if user else None
        
        return {
            'empresas': empresas_data,
            'facturas': facturas_data,
            'contabilidad': contabilidad_data,
            'perfil': perfil_data,
        }
    except Exception:
        return {
            'empresas': [],
            'facturas': {
                'total': 0,
                'por_estado': [],
                'mes_actual': {'cantidad': 0, 'total': 0.0},
                'recientes': [],
            },
            'contabilidad': {
                'total_cuentas': 0,
                'total_asientos': 0,
                'mes_actual': {
                    'total_movimientos': 0,
                    'total_debitos': 0.0,
                    'total_creditos': 0.0,
                },
                'asientos_recientes': [],
            },
            'perfil': None,
        }


def get_dashboard_snapshot(tenant, user=None) -> dict[str, Any]:
    """
    Obtiene snapshot de datos del dashboard para el DashboardSectionsViewSet.
    
    # WARNING: POLÍTICA: Versión simplificada para uso en Core API.
    
    Args:
        tenant: Instancia del tenant (Client)
        user: Usuario autenticado (opcional)
        
    Returns:
        Dict con snapshot del dashboard
    """
    return get_dashboard_resumen(tenant, user)
