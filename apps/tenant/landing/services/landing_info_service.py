"""
Servicio de información pública del tenant (Landing).

⚠️ POLÍTICA v2.30:
- Solo información pública del tenant (sin datos sensibles)
- Incluye branding desde Empresa (BD)
- No requiere autenticación
"""
import logging
from typing import Dict, Any
from django.http import HttpRequest

logger = logging.getLogger(__name__)


def get_public_info(request: HttpRequest) -> Dict[str, Any]:
    """
    Obtiene información pública del tenant actual.
    
    Args:
        request: HttpRequest con tenant inyectado por middleware
        
    Returns:
        Dict con datos públicos del tenant (nombre, schema, domain, branding)
        
    Raises:
        ValueError: Si no se puede determinar el tenant
    """
    tenant = getattr(request, 'tenant', None)
    
    if not tenant:
        raise ValueError("No se pudo determinar el tenant actual.")
    
    # El serializer TenantPublicInfoSerializer maneja la serialización completa
    # incluyendo branding desde Empresa. Este servicio solo retorna el tenant
    # para que el ViewSet lo pase al serializer.
    
    return {
        'tenant': tenant,
        'request': request,
    }
