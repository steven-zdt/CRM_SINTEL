"""
Template filters propios de la app impuestos (consola de administracion).
"""
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

_EM_OPEN = "\x00EM_OPEN\x00"
_EM_CLOSE = "\x00EM_CLOSE\x00"


@register.filter(name="highlight_safe")
def highlight_safe(value):
    """
    [SEC-M2] Escapa todo el contenido excepto las etiquetas <em>/</em> que genera
    el resaltado de busqueda de Elasticsearch (hits.highlight.*, tags por defecto).

    El texto resaltado proviene de documentos indexados (normativa/tributaria
    ingerida), cuyo contenido no es de confianza -- usarlo con |safe permitia que
    HTML/JS embebido en un documento se ejecutara al ver resultados de busqueda.
    """
    if value is None:
        return ""
    text = str(value)
    text = text.replace("<em>", _EM_OPEN).replace("</em>", _EM_CLOSE)
    text = escape(text)
    text = text.replace(_EM_OPEN, "<em>").replace(_EM_CLOSE, "</em>")
    return mark_safe(text)
