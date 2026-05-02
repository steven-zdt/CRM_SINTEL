"""
Módulo central de branding para tenants.

# WARNING: POLÍTICA DE BRANDING AGNÓSTICO:
- NINGÚN nombre, logo ni texto de empresa hardcodeado
- Todo branding viene de la BASE DE DATOS del esquema activo (tenant)
- Fallback documentado cuando no hay datos de empresa

Este módulo proporciona un punto único de acceso para obtener
información de branding del tenant actual.
"""

from django.http import HttpRequest


def get_tenant_branding(request: HttpRequest) -> dict[str, str | None]:
    """
    Obtiene información de branding del tenant actual.
    
    # WARNING: POLÍTICA: Todo branding viene de la base de datos del tenant.
    No se permiten hardcodes de marca en ningún componente.
    
    Orden de prioridad:
    1. Datos de Empresa (apps.tenant.empresa.models.Empresa)
    2. Datos del Tenant (request.tenant)
    3. Fallback neutro (None o valores genéricos)
    
    Args:
        request: HttpRequest con tenant resuelto por django-tenants
        
    Returns:
        Dict con:
        - nombre: Nombre comercial/razón social de la empresa
        - logo_url: URL del logo (si existe)
        - website: URL del sitio web (si existe)
        - moneda: Código de moneda (default: 'COP')
        - tenant_name: Nombre del tenant (fallback)
        
    Performance:
        - Usa only()/defer() para evitar cargar campos innecesarios
        - Cache corto en request si aplica (evitar múltiples queries)
    """
    branding = {
        'nombre': None,
        'logo_url': None,
        'website': None,
        'moneda': 'COP',  # Default neutral
        'tenant_name': None,
    }
    
    # Obtener tenant del request (inyectado por django-tenants)
    tenant = getattr(request, 'tenant', None)
    
    if tenant:
        # Fallback 1: Nombre del tenant
        tenant_name = getattr(tenant, 'nombre', None)
        if tenant_name:
            branding['tenant_name'] = tenant_name
            branding['nombre'] = tenant_name  # Fallback inicial
    
    # Intentar obtener datos de Empresa (modelo del tenant)
    try:
        from apps.tenant.empresa.models import Empresa
        
        # Query optimizado: solo campos necesarios
        empresa = Empresa.objects.only(
            'razon_social',
            'logo',
            'website',
            'moneda'
        ).first()
        
        if empresa:
            # Prioridad: datos de Empresa sobre tenant
            if empresa.razon_social:
                branding['nombre'] = empresa.razon_social
            
            if empresa.logo:
                # Construir URL del logo
                branding['logo_url'] = empresa.logo.url
            
            if empresa.website:
                branding['website'] = empresa.website
            
            if empresa.moneda:
                branding['moneda'] = empresa.moneda
                
    except Exception:
        # Si no existe el modelo Empresa o hay error, usar fallback
        # No hacer logging aquí para evitar ruido en desarrollo
        pass
    
    # Fallback final: si no hay nombre, usar genérico
    if not branding['nombre']:
        branding['nombre'] = branding.get('tenant_name') or 'Sistema de Gestión'
    
    return branding


def get_tenant_branding_for_serializer(request: HttpRequest) -> dict[str, str | None]:
    """
    Versión de get_tenant_branding() optimizada para serializers DRF.
    
    # WARNING: USO: Solo en serializers cuando se necesita branding en respuestas JSON.
    Para templates, usar el templatetag {% tenant_branding_header %}.
    
    Args:
        request: HttpRequest del serializer (desde context['request'])
        
    Returns:
        Dict con información de branding (mismo formato que get_tenant_branding)
    """
    return get_tenant_branding(request)
