"""
Servicios de orquestación para datos de perfil.

# WARNING: POLÍTICA:
- Solo lectura/composición de datos
- NO duplica lógica de negocio de apps.tenant.perfil
- Usa ORM optimizado (only, select_related, prefetch_related)
"""
from typing import Any


def get_perfil_snapshot(user) -> dict[str, Any]:
    """
    Obtiene snapshot del perfil del usuario en el tenant actual.
    
    Args:
        user: Usuario autenticado
        
    Returns:
        Dict con datos del perfil (o None si no existe)
    """
    try:
        from apps.tenant.perfil.models import TenantProfile
        
        # # WARNING: IMPORTANTE: El campo es 'user', no 'usuario'
        perfil = TenantProfile.objects.filter(user=user).only(
            'id',
            'cargo',
            'departamento',
            'telefono_corporativo',
            'foto',
        ).first()
        
        if perfil:
            return {
                'id': perfil.id,
                'cargo': perfil.cargo,
                'departamento': perfil.departamento,
                'telefono': perfil.telefono_corporativo,
                'foto_url': perfil.foto.url if perfil.foto else None,
            }
        return None
    except Exception:
        return None
