"""
Templatetags para branding del tenant.

# WARNING: POLÍTICA: Todo branding viene de la base de datos.
No se permiten hardcodes de marca en templates.
"""
from django import template

from apps.tenant.core.branding import get_tenant_branding

register = template.Library()


@register.inclusion_tag('tenant/partials/_branding_header.html', takes_context=True)
def tenant_branding_header(context):
    """
    Templatetag para inyectar header con branding del tenant.
    
    Uso en templates:
        {% load tenant_branding %}
        {% tenant_branding_header %}
    
    # WARNING: POLÍTICA: El branding viene de la BD (Empresa o tenant).
    No se permiten hardcodes de marca.
    
    Args:
        context: Context del template (debe incluir 'request')
        
    Returns:
        Dict con 'branding' para el partial _branding_header.html
    """
    request = context.get('request')
    if not request:
        # Fallback si no hay request (poco probable en templates)
        branding = {
            'nombre': 'Sistema de Gestión',
            'logo_url': None,
            'website': None,
            'moneda': 'COP',
            'tenant_name': None,
        }
    else:
        branding = get_tenant_branding(request)
    
    return {'branding': branding}


@register.simple_tag(takes_context=True)
def tenant_branding_name(context):
    """
    Templatetag para obtener solo el nombre del tenant/empresa.
    
    Uso en templates:
        {% load tenant_branding %}
        <h1>{% tenant_branding_name %}</h1>
    
    Returns:
        str: Nombre de la empresa o tenant
    """
    request = context.get('request')
    if not request:
        return 'Sistema de Gestión'
    
    branding = get_tenant_branding(request)
    return branding.get('nombre', 'Sistema de Gestión')


@register.simple_tag(takes_context=True)
def tenant_branding_logo(context):
    """
    Templatetag para obtener la URL del logo del tenant/empresa.
    
    Uso en templates:
        {% load tenant_branding %}
        <img src="{% tenant_branding_logo %}" alt="Logo">
    
    Returns:
        str: URL del logo o None
    """
    request = context.get('request')
    if not request:
        return None
    
    branding = get_tenant_branding(request)
    return branding.get('logo_url')


@register.simple_tag(takes_context=True)
def tenant_branding_website(context):
    """
    Templatetag para obtener la URL del sitio web del tenant/empresa.
    
    Uso en templates:
        {% load tenant_branding %}
        <a href="{% tenant_branding_website %}">Sitio Web</a>
    
    Returns:
        str: URL del sitio web o None
    """
    request = context.get('request')
    if not request:
        return None
    
    branding = get_tenant_branding(request)
    return branding.get('website')
