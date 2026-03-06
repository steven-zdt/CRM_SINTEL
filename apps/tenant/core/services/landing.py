"""
Servicio para obtener datos de landing (Core API).

⚠️ POLÍTICA:
- No duplicar lógica de negocio de apps/tenant/landing
- Solo orquestar/componer datos públicos de landing
- Mantener tenant-awareness (django-tenants maneja el aislamiento)
"""
from typing import Dict, Any, Optional
from django.db import connection
from django.conf import settings


def get_landing_resumen(tenant) -> Dict[str, Any]:
    """
    Obtiene resumen de datos públicos de landing del tenant.
    
    ⚠️ POLÍTICA: Usa la API de landing para obtener información pública.
    
    Args:
        tenant: Instancia del tenant (Client)
        
    Returns:
        Dict con datos públicos de landing (nombre, domain_url, login_url, etc.)
    """
    try:
        # Obtener información básica del tenant
        domain_url = None
        if hasattr(tenant, 'domains'):
            primary_domain = tenant.domains.filter(is_primary=True).first()
            if primary_domain:
                # Construir URL con protocolo correcto (https en producción)
                protocol = "https" if not settings.DEBUG and getattr(settings, 'SECURE_SSL_REDIRECT', False) else "http"
                domain_url = f"{protocol}://{primary_domain.domain}"
        
        # Construir URLs
        login_url = f"{domain_url}/" if domain_url else "/"
        dashboard_url = f"{domain_url}/workspace/" if domain_url else "/workspace/"
        
        return {
            'nombre': getattr(tenant, 'nombre', 'Sistema de Gestión'),
            'schema_name': getattr(tenant, 'schema_name', None),
            'domain_url': domain_url or '/',
            'login_url': login_url,
            'dashboard_url': dashboard_url,
            'is_active': getattr(tenant, 'is_active', True),
        }
    except Exception:
        pass
    
    return {
        'nombre': 'Sistema de Gestión',
        'schema_name': None,
        'domain_url': '/',
        'login_url': '/',
        'dashboard_url': '/workspace/',
        'is_active': True,
    }


def get_landing_snapshot(tenant) -> Dict[str, Any]:
    """
    Obtiene snapshot de datos de landing para el dashboard.
    
    ⚠️ POLÍTICA: Versión simplificada para uso en DashboardSectionsViewSet.
    
    Args:
        tenant: Instancia del tenant (Client)
        
    Returns:
        Dict con snapshot de landing
    """
    return get_landing_resumen(tenant)
