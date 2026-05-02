"""
Manejadores de error personalizados para tenants.

# WARNING: POLÍTICA:
- Estos handlers se activan solo en TENANT_URLCONF
- Mantienen la identidad visual del tenant incluso en errores
- Usan branding dinámico desde BD (no hardcodes)
- # WARNING: v2.60: Devuelven JSON estructurado para peticiones API (Error Boundary Pattern)
"""
from django.http import JsonResponse
from django.shortcuts import render

from apps.tenant.core.branding import get_tenant_branding


def custom_page_not_found_view(request, exception):
    """
    Manejador personalizado para errores 404 (Página no encontrada).
    
    # WARNING: v2.60: Error Boundary Pattern - Devuelve JSON estructurado para peticiones API.
    
    Renderiza un template con el diseño del tenant, manteniendo la identidad visual.
    
    # WARNING: IMPORTANTE: Este handler solo se activa en TENANT_URLCONF.
    Para el esquema 'public', Django usa el handler por defecto.
    
    # WARNING: POLÍTICA: Usa branding dinámico desde BD (no hardcodes).
    
    Args:
        request: HttpRequest
        exception: Http404 exception
    
    Returns:
        JsonResponse si es petición API, HttpResponse con template si es HTML
    """
    # # WARNING: v2.60: Detectar si es petición API (AJAX o Content-Type: application/json)
    is_api_request = (
        request.path.startswith('/api/') or
        request.headers.get('Accept', '').startswith('application/json') or
        request.headers.get('Content-Type', '').startswith('application/json')
    )
    
    # Si es petición API, devolver JSON estructurado
    if is_api_request:
        return JsonResponse(
            {
                'detail': 'Recurso no encontrado (404). Verifica la URL y el tenant actual.',
                'status': 404,
                'code': 'NOT_FOUND'
            },
            status=404
        )
    
    # Si es petición HTML, renderizar template (comportamiento original)
    # Obtener información del tenant actual
    tenant = getattr(request, 'tenant', None)
    
    # Obtener branding dinámico desde BD
    branding = get_tenant_branding(request)
    empresa_nombre = branding.get('nombre', getattr(tenant, 'nombre', 'Sistema de Gestión') if tenant else 'Sistema de Gestión')
    tenant_name = getattr(tenant, 'nombre', 'Sistema de Gestión') if tenant else 'Sistema de Gestión'
    
    # Obtener información de la empresa si existe (para compatibilidad con templates)
    empresa = None
    try:
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.only('razon_social').first()
    except Exception:
        pass
    
    context = {
        'tenant_name': tenant_name,
        'empresa_nombre': empresa_nombre,
        'empresa': empresa,  # Pasar el objeto empresa completo para el template
        'user': getattr(request, 'user', None) if hasattr(request, 'user') and request.user.is_authenticated else None,
    }
    
    return render(
        request,
        'tenant/errors/404.html',
        context,
        status=404
    )


def custom_permission_denied_view(request, exception):
    """
    Manejador personalizado para errores 403 (Permiso denegado).
    
    # WARNING: v2.60: Error Boundary Pattern - Devuelve JSON estructurado para peticiones API.
    
    Renderiza un template con el diseño del tenant, mostrando un mensaje
    claro de que el usuario no tiene permisos para acceder a esta área.
    
    # WARNING: CASO DE USO PRINCIPAL: Usuario logueado que intenta entrar a un tenant
    del cual no es miembro (Cross-Tenant Access).
    
    # WARNING: POLÍTICA: Usa branding dinámico desde BD (no hardcodes).
    
    Args:
        request: HttpRequest
        exception: PermissionDenied exception
    
    Returns:
        JsonResponse si es petición API, HttpResponse con template si es HTML
    """
    # Mensaje de error personalizado
    error_message = str(exception) if exception else "No tienes permisos para acceder a esta área."
    
    # # WARNING: v2.60: Detectar si es petición API (AJAX o Content-Type: application/json)
    is_api_request = (
        request.path.startswith('/api/') or
        request.headers.get('Accept', '').startswith('application/json') or
        request.headers.get('Content-Type', '').startswith('application/json')
    )
    
    # Si es petición API, devolver JSON estructurado
    if is_api_request:
        return JsonResponse(
            {
                'detail': error_message,
                'status': 403,
                'code': 'PERMISSION_DENIED'
            },
            status=403
        )
    
    # Si es petición HTML, renderizar template (comportamiento original)
    # Obtener información del tenant actual
    tenant = getattr(request, 'tenant', None)
    
    # Obtener branding dinámico desde BD
    branding = get_tenant_branding(request)
    empresa_nombre = branding.get('nombre', getattr(tenant, 'nombre', 'Sistema de Gestión') if tenant else 'Sistema de Gestión')
    tenant_name = getattr(tenant, 'nombre', 'Sistema de Gestión') if tenant else 'Sistema de Gestión'
    
    # Obtener información de la empresa si existe (para compatibilidad con templates)
    empresa = None
    try:
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.only('razon_social').first()
    except Exception:
        pass
    
    context = {
        'tenant_name': tenant_name,
        'empresa_nombre': empresa_nombre,
        'empresa': empresa,  # Pasar el objeto empresa completo para el template
        'error_message': error_message,
        'user': getattr(request, 'user', None) if hasattr(request, 'user') and request.user.is_authenticated else None,
    }
    
    return render(
        request,
        'tenant/errors/403.html',
        context,
        status=403
    )
