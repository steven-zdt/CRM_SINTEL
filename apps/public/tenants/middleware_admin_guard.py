"""
Middleware guard-rail para bloquear rutas públicas en tenants privados.

⚠️ IMPORTANTE: Este middleware actúa como defensa en profundidad.
Bloquea /admin/, /console/ y /api/public/ en dominios de tenants privados,
incluso si alguien los incluye por error en el TENANT_URLCONF.

Debe ir DESPUÉS de:
- TenantMainMiddleware (para tener request.tenant)
"""
from django.http import HttpResponseNotFound
from django_tenants.utils import get_public_schema_name

PUBLIC_SCHEMA_NAME = get_public_schema_name()


def block_public_routes_on_tenants(get_response):
    """
    Bloquea el acceso a rutas públicas (/admin/, /console/, /api/public/) cuando el esquema activo NO es 'public'.
    
    Defensa en profundidad: aunque alguien incluya por error estas rutas en el TENANT_URLCONF,
    este middleware evita que aparezcan en dominios de tenants privados.
    
    Args:
        get_response: Función que obtiene la respuesta del siguiente middleware/view
    
    Returns:
        HttpResponse: HttpResponseNotFound (404) si se intenta acceder a rutas públicas en un tenant privado,
                     o continúa normalmente en otros casos
    """
    def middleware(request):
        tenant = getattr(request, "tenant", None)  # seteado por TenantMainMiddleware
        path = request.path
        
        # Solo bloquear rutas públicas si el tenant existe Y NO es el esquema público
        if tenant:
            schema_name = getattr(tenant, "schema_name", "")
            # Permitir rutas públicas solo en el esquema público
            if schema_name != PUBLIC_SCHEMA_NAME:
                # Bloquear /admin/, /console/ y /api/public/ en tenants privados
                if path.startswith("/admin/") or path.startswith("/console/") or path.startswith("/api/public/"):
                    return HttpResponseNotFound("Not Found")
        
        return get_response(request)
    
    return middleware


# Alias para compatibilidad con código existente
block_admin_on_tenants = block_public_routes_on_tenants
