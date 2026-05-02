"""
Redirecciones de compatibilidad para rutas API.

# WARNING: POLÍTICA:
- Mantener compatibilidad con rutas antiguas (singular → plural)
- Redirecciones 301 (Permanent Redirect) para SEO y caché
"""
from django.http import HttpResponsePermanentRedirect


def empresa_singular_redirect(request):
    """
    Redirige /api/v1/empresa/ → /api/v1/empresas/
    
    # WARNING: COMPATIBILIDAD: Mantiene compatibilidad con código antiguo que usa singular.
    """
    # Preservar query parameters si existen
    query_string = request.META.get('QUERY_STRING', '')
    if query_string:
        return HttpResponsePermanentRedirect(f'/api/v1/empresas/?{query_string}')
    return HttpResponsePermanentRedirect('/api/v1/empresas/')
