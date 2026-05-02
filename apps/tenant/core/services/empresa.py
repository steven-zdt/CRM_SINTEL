"""
Servicios de orquestación para datos de empresa.

# WARNING: POLÍTICA:
- Solo lectura/composición de datos
- NO duplica lógica de negocio de apps.tenant.empresa
- Usa ORM optimizado (only, select_related, prefetch_related)
"""
from typing import Any


def get_mi_empresa(tenant) -> dict[str, Any] | None:
    """
    Obtiene la empresa del tenant (singleton) para el dashboard.
    
    # WARNING: PATRÓN SINGLETON: Solo existe una empresa por tenant.
    # WARNING: POLÍTICA SSoT: Usa el servicio provider de empresa.
    Retorna None si no existe (indica que falta setup).
    
    Args:
        tenant: Instancia del tenant (Client)
        
    Returns:
        Dict con datos de empresa o None si no existe
    """
    try:
        # # WARNING: POLÍTICA SSoT: Usar servicio provider en lugar de consulta ORM directa
        from apps.tenant.empresa.services import get_empresa_data
        
        empresa_data = get_empresa_data()
        
        if empresa_data:
            return {
                "id": empresa_data['id'],
                "razon_social": empresa_data['razon_social'],
                "nit": empresa_data['nit'],
                "dv": empresa_data['dv'],
                "nit_completo": empresa_data['nit_completo'],
                "email": empresa_data['email_contacto'],
                "telefono": empresa_data['telefono'],
                "logo": empresa_data['logo'],  # URL relativa
                "website": empresa_data['website'],
                "moneda": empresa_data['moneda'],
                "regimen_tributario": empresa_data['regimen_tributario'],
            }
        return None
    except Exception:
        return None


def get_empresas_snapshot(tenant) -> list[dict[str, Any]]:
    """
    Obtiene snapshot de empresas del tenant.
    
    # WARNING: PATRÓN SINGLETON: Solo existe una empresa por tenant.
    # WARNING: POLÍTICA SSoT: Usa el servicio provider de empresa.
    
    Args:
        tenant: Instancia del tenant (Client)
        
    Returns:
        List[Dict] con datos de empresa(s)
    """
    try:
        # # WARNING: POLÍTICA SSoT: Usar servicio provider en lugar de consulta ORM directa
        from apps.tenant.empresa.services import get_empresa_data
        
        empresa_data = get_empresa_data()
        
        if empresa_data:
            return [{
                'id': empresa_data['id'],
                'razon_social': empresa_data['razon_social'],
                'nit': empresa_data['nit'],
                'dv': empresa_data['dv'],
                'nit_completo': empresa_data['nit_completo'],
                'logo': empresa_data['logo'],  # URL relativa, el serializer la convierte a absoluta
                'website': empresa_data['website'],
                'moneda': empresa_data['moneda'],
                'regimen_tributario': empresa_data['regimen_tributario'],
            }]
        return []
    except Exception:
        return []
